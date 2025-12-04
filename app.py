#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Naeilum (내일:음) - Korean Name Recommendation App
A Flask application that recommends Korean names for foreigners
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import secrets
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    session,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_GENDERS = {"male", "female"}

THEME_CHOICES = {"light", "dark", "system"}
DEFAULT_THEME = "system"
THEME_COOKIE_NAME = "theme"
THEME_COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year
CSRF_HEADER_NAME = "X-CSRF-Token"

HANGUL_BASE = 0xAC00
HANGUL_LAST = 0xD7A3
CHO_ROMA = [
    "g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "",
    "j", "jj", "ch", "k", "t", "p", "h",
]
JUNG_ROMA = [
    "a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe",
    "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i",
]
JONG_ROMA = [
    "", "k", "k", "ks", "n", "nj", "nh", "t", "l", "lk", "lm", "lp", "lt",
    "lp", "lh", "m", "p", "ps", "t", "t", "ng", "t", "t", "k", "t", "p", "t", "h",
]

app = Flask(__name__)
app.secret_key = os.environ.get("NAEILUM_SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=7)
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("NAEILUM_SESSION_COOKIE_SECURE", "false").lower()
    in {"1", "true", "yes"},
    SESSION_COOKIE_HTTPONLY=True,
)


def error_response(message: str, status: int = 400, code: Optional[str] = None) -> Tuple[Response, int]:
    """Return a standardized JSON error response."""
    payload: Dict[str, Any] = {"success": False, "error": {"message": message}}
    if code:
        payload["error"]["code"] = code
    return jsonify(payload), status


def generate_fallback_names() -> Dict[str, List[Dict[str, Any]]]:
    """Generate fallback name data if JSON files are not available."""
    return {
        "male": [
            {
                "name": "지훈",
                "hanja": "志勳",
                "romanization": ["Jihun", "Ji-hoon"],
                "category": "Honor",
                "meaning": "Ambitious and meritorious",
                "initial": "J",
            },
        ],
        "female": [
            {
                "name": "서윤",
                "hanja": "瑞允",
                "romanization": ["Seoyun", "Seo-yoon"],
                "category": "Grace",
                "meaning": "A graceful blessing that shines brightly",
                "initial": "S",
            },
        ],
    }


def _load_json_file(filename: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Attempt to load a JSON file and return success flag with data."""
    json_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                return True, data
            logger.warning("JSON structure unexpected in %s", filename)
    except FileNotFoundError:
        logger.warning("JSON file not found: %s", filename)
    except json.JSONDecodeError as exc:
        logger.error("JSON decode error in %s: %s", filename, exc)
    except Exception:
        logger.exception("Unexpected error loading %s", filename)
    return False, []


def load_names() -> Dict[str, List[Dict[str, Any]]]:
    """Load Korean names from JSON files, with fallback data."""
    names_data = generate_fallback_names()
    for gender, filename in (("male", "names_male.json"), ("female", "names_female.json")):
        success, data = _load_json_file(filename)
        if success:
            names_data[gender] = data
    return names_data


def load_fortunes() -> List[Dict[str, Any]]:
    """Load fortune messages from JSON file."""
    success, data = _load_json_file("fortunes.json")
    if success:
        return data

    logger.info("Using fallback fortunes.")
    return [
        {"category": "Love", "category_ko": "사랑", "messages": [{"en": "Love finds you when you're true to yourself", "ko": "진정한 나 자신일 때 사랑이 찾아옵니다"}]},
        {"category": "Career", "category_ko": "직업", "messages": [{"en": "Your dedication will be recognized soon", "ko": "당신의 헌신이 곧 인정받을 것입니다"}]},
        {"category": "Wealth", "category_ko": "재물", "messages": [{"en": "Financial wisdom comes through patient planning", "ko": "재정적 지혜는 인내심 있는 계획에서 옵니다"}]},
        {"category": "Health", "category_ko": "건강", "messages": [{"en": "Your body thanks you for mindful choices", "ko": "당신의 몸이 현명한 선택에 감사합니다"}]},
        {"category": "Wisdom", "category_ko": "지혜", "messages": [{"en": "A lesson from the past illuminates your path", "ko": "과거의 교훈이 당신의 길을 밝힙니다"}]},
    ]


# Load data on startup
NAMES_DATA = load_names()
FORTUNES_DATA = load_fortunes()


def normalize_name(name: str) -> str:
    """Normalize name for matching: strip spaces, diacritics, and punctuation."""
    normalized = unicodedata.normalize("NFD", name)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^a-zA-Z0-9]", "", normalized).lower()
    return normalized


def get_name_initial(name: str) -> str:
    """Extract the first alphabetic letter of the first word."""
    parts = name.strip().split()
    if not parts:
        return "A"
    first_name = parts[0]
    clean_name = re.sub(r"[^a-zA-Z]", "", first_name)
    if clean_name:
        return clean_name[0].upper()
    return "A"


def generate_session_id() -> str:
    """Generate anonymous session ID."""
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:16]


@lru_cache(maxsize=4096)
def romanize_syllable(char: str) -> str:
    """Romanize a single Hangul syllable to Latin letters."""
    code_point = ord(char)
    if HANGUL_BASE <= code_point <= HANGUL_LAST:
        index = code_point - HANGUL_BASE
        cho = index // 588
        jung = (index % 588) // 28
        jong = index % 28
        return (CHO_ROMA[cho] + JUNG_ROMA[jung] + JONG_ROMA[jong]).rstrip()
    return char


def romanize_korean_text(text: str) -> str:
    """Romanize a full Hangul string."""
    return "".join(romanize_syllable(ch) for ch in text)


def get_candidate_romanization(name_entry: Dict[str, Any]) -> List[str]:
    """Return all romanization candidates for a name entry."""
    candidates: List[str] = []
    romanized = name_entry.get("romanization")
    if isinstance(romanized, str):
        romanized = [romanized]
    if isinstance(romanized, Sequence):
        for value in romanized:
            if isinstance(value, str) and value:
                candidates.append(value)
    hangul_name = name_entry.get("name", "")
    if hangul_name:
        candidates.append(romanize_korean_text(hangul_name))
    seen: set[str] = set()
    deduped: List[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped or [hangul_name]


@lru_cache(maxsize=4096)
def normalize_romanization(text: str) -> str:
    """Normalize romanized text for similarity comparison."""
    normalized = unicodedata.normalize("NFD", text)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = re.sub(r"[^a-zA-Z]", "", normalized).lower()
    return normalized


def compute_similarity_score(english_name: str, name_entry: Dict[str, Any]) -> float:
    """Compute a phonetic similarity score between an English name and a Korean entry."""
    english_norm = normalize_romanization(english_name)
    if not english_norm:
        return 0.0

    best_score = 0.0
    for candidate in get_candidate_romanization(name_entry):
        candidate_norm = normalize_romanization(candidate)
        if not candidate_norm:
            continue
        ratio = SequenceMatcher(None, english_norm, candidate_norm).ratio()
        if english_norm[:1] == candidate_norm[:1]:
            ratio += 0.08
        if english_norm[-1:] == candidate_norm[-1:]:
            ratio += 0.04
        ratio -= min(0.15, abs(len(english_norm) - len(candidate_norm)) * 0.015)
        best_score = max(best_score, ratio)

    if name_entry.get("initial", "").upper() == english_norm[:1].upper():
        best_score += 0.03

    return round(best_score, 6)


def select_korean_names(original_name: str, gender: str) -> List[Dict[str, Any]]:
    """Select Korean names based on English input and similarity scoring."""
    gender_names = NAMES_DATA.get(gender, [])
    if not gender_names:
        return []

    normalized_input = normalize_name(original_name)
    selections: List[Dict[str, Any]] = []

    # Prefer exact special matches if provided in the dataset
    for entry in gender_names:
        special = entry.get("special_match")
        if special and normalize_name(special) == normalized_input:
            selections.append(entry)
            break

    scored_candidates: List[Tuple[float, float, Dict[str, Any]]] = []
    for entry in gender_names:
        if entry in selections or entry.get("special_match"):
            continue
        score = compute_similarity_score(original_name, entry)
        scored_candidates.append((score, random.random(), entry))

    scored_candidates.sort(key=lambda item: (-item[0], item[1]))

    seen_initials: set[str] = set()
    seen_categories: set[str] = set()
    seen_korean_names: set[str] = set()

    for score, _, entry in scored_candidates:
        if len(selections) >= 5:
            break
        korean_name = entry.get("name", "")
        if korean_name in seen_korean_names:
            continue
        initial = entry.get("initial", "")
        category = entry.get("category", "")
        if initial in seen_initials and len(selections) < 3:
            continue
        if category in seen_categories and len(selections) >= 3:
            continue
        selections.append(entry)
        if korean_name:
            seen_korean_names.add(korean_name)
        if initial:
            seen_initials.add(initial)
        if category:
            seen_categories.add(category)

    if len(selections) < 5:
        leftovers = [entry for entry in gender_names if entry not in selections and entry.get("name", "") not in seen_korean_names]
        random.shuffle(leftovers)
        selections.extend(leftovers[: 5 - len(selections)])

    return selections[:5]


def get_daily_fortune(korean_name: str) -> List[Dict[str, str]]:
    """Generate daily fortune based on Korean name."""
    today = datetime.now().strftime("%Y-%m-%d")
    seed_string = f"{korean_name}{today}"
    rng = random.Random(hashlib.md5(seed_string.encode(), usedforsecurity=False).hexdigest())

    fortunes: List[Dict[str, str]] = []
    for category_data in FORTUNES_DATA:
        category = category_data.get("category", "")
        category_ko = category_data.get("category_ko", category)
        messages = category_data.get("messages", [])
        if messages:
            message_obj = rng.choice(messages)
            if isinstance(message_obj, dict):
                message_en = message_obj.get("en", "")
                message_ko = message_obj.get("ko", "")
            else:
                message_en = str(message_obj)
                message_ko = ""
            fortunes.append({
                "category": category,
                "category_ko": category_ko,
                "message": message_en,
                "message_ko": message_ko
            })

    return fortunes


def validate_gender(raw_gender: Optional[str]) -> str:
    """Validate gender input and fall back to 'male' if invalid."""
    if raw_gender not in ALLOWED_GENDERS:
        logger.warning("Invalid gender value received: %s", raw_gender)
        return "male"
    return raw_gender


def ensure_csrf_token() -> str:
    """Ensure a CSRF token exists in the session and return it."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
        logger.debug("Generated new CSRF token for session %s", session.get("session_id"))
    return token


def enforce_csrf(strict: bool) -> bool:
    """Validate CSRF token from header."""
    provided = request.headers.get(CSRF_HEADER_NAME)
    expected = session.get("csrf_token")

    if not provided:
        if strict:
            logger.warning("CSRF token missing for strict endpoint %s", request.path)
        return not strict

    if not expected:
        logger.warning("CSRF token not initialized for request %s", request.path)
        return False

    if not secrets.compare_digest(provided, expected):
        logger.warning("CSRF token mismatch for request %s", request.path)
        return False

    return True


def resolve_theme() -> Tuple[str, str]:
    """Resolve the current theme preference and its source."""
    session_theme = session.get("theme")
    if session_theme in THEME_CHOICES:
        return session_theme, "session"

    cookie_theme = request.cookies.get(THEME_COOKIE_NAME)
    if cookie_theme in THEME_CHOICES:
        return cookie_theme, "cookie"

    return DEFAULT_THEME, "default"


def persist_theme(theme: str, response: Response) -> Response:
    """Persist theme preference to session and cookie."""
    session["theme"] = theme
    session.modified = True
    secure_cookie = app.config.get("SESSION_COOKIE_SECURE", True)
    response.set_cookie(
        THEME_COOKIE_NAME,
        theme,
        max_age=THEME_COOKIE_MAX_AGE,
        secure=secure_cookie,
        httponly=False,
        samesite="Lax",
        path="/",
    )
    logger.info("Theme persisted as '%s' for session %s", theme, session.get("session_id"))
    return response


def validate_theme_value(theme: Optional[str]) -> bool:
    """Check if the provided theme value is allowed."""
    return theme in THEME_CHOICES


@app.before_request
def apply_before_request() -> None:
    """Set up session defaults before each request."""
    session.permanent = True
    if "session_id" not in session:
        session["session_id"] = generate_session_id()
        logger.debug("Assigned new session_id %s", session["session_id"])
    ensure_csrf_token()


@app.context_processor
def inject_theme_context() -> Dict[str, Any]:
    """Inject theme-related context into all templates."""
    theme, _ = resolve_theme()
    return {"theme": theme, "is_dark": theme == "dark"}


@app.after_request
def apply_security_headers(response: Response) -> Response:
    """Append basic security headers to every response."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Cache-Control", "public, max-age=300")
    return response


@app.route("/")
def index() -> Response:
    """Main page."""
    return render_template("index.html")


@app.route("/privacy")
def privacy() -> Response:
    """Privacy policy page."""
    return render_template("privacy.html", page_class="legal")


@app.route("/about")
def about() -> Response:
    """About page."""
    return render_template("about.html", page_class="legal")


@app.route("/health")
def health() -> Response:
    """Health check endpoint."""
    return jsonify({"success": True, "status": "ok"})


@app.route("/api/csrf_token", methods=["GET"])
def csrf_token() -> Response:
    """Return the current CSRF token."""
    token = ensure_csrf_token()
    return jsonify({"success": True, "token": token})


@app.route("/api/theme", methods=["GET"])
def get_theme() -> Response:
    """Return the current theme preference."""
    theme, source = resolve_theme()
    logger.info("Theme resolved as '%s' from %s", theme, source)
    return jsonify({"success": True, "theme": theme, "source": source})


@app.route("/api/theme", methods=["POST"])
def set_theme() -> Response:
    """Set the theme preference to light, dark, or system."""
    if not enforce_csrf(strict=True):
        return error_response("Invalid CSRF token", status=403, code="CSRF_FAILED")

    data = request.get_json(silent=True) or {}
    theme = data.get("theme")

    if not validate_theme_value(theme):
        logger.warning("Invalid theme value received: %s", theme)
        return error_response("Invalid theme value", status=400, code="INVALID_THEME")

    response = jsonify({"success": True, "theme": theme})
    response = persist_theme(theme, response)
    return response


@app.route("/api/theme/toggle", methods=["POST"])
def toggle_theme() -> Response:
    """Toggle between light and dark themes (system becomes light)."""
    if not enforce_csrf(strict=True):
        return error_response("Invalid CSRF token", status=403, code="CSRF_FAILED")

    current_theme, _ = resolve_theme()
    if current_theme == "dark":
        new_theme = "light"
    elif current_theme == "light":
        new_theme = "dark"
    else:
        new_theme = "light"

    response = jsonify({"success": True, "theme": new_theme})
    response = persist_theme(new_theme, response)
    return response


@app.route("/recommend", methods=["POST"])
def recommend() -> Tuple[Response, int] | Response:
    """Process name and return recommendations."""
    if not enforce_csrf(strict=False):
        return error_response("Invalid CSRF token", status=403, code="CSRF_FAILED")

    data = request.get_json(silent=True)

    if not data:
        return error_response("No data provided", status=400, code="NO_DATA")

    original_name = data.get("name", "").strip()
    gender = validate_gender(data.get("gender"))

    if not original_name:
        return error_response("Name is required", status=400, code="NAME_REQUIRED")

    if len(original_name) > 100:
        return error_response("Name is too long", status=400, code="NAME_TOO_LONG")

    session["original_name"] = original_name
    session["gender"] = gender

    korean_names = select_korean_names(original_name, gender)

    if not korean_names:
        logger.error("No Korean names generated for %s (%s)", original_name, gender)
        return error_response("Could not generate names", status=500, code="NAME_GENERATION_FAILED")

    session["recommendations"] = korean_names

    return jsonify({"success": True, "names": korean_names})


@app.route("/select", methods=["POST"])
def select() -> Tuple[Response, int] | Response:
    """Handle name selection."""
    if not enforce_csrf(strict=False):
        return error_response("Invalid CSRF token", status=403, code="CSRF_FAILED")

    data = request.get_json(silent=True)
    if not data:
        return error_response("No data provided", status=400, code="NO_DATA")

    try:
        selected_index = int(data.get("index", 0))
    except (TypeError, ValueError):
        return error_response("Invalid selection index", status=400, code="INVALID_INDEX")

    recommendations = session.get("recommendations", [])

    if selected_index < 0 or selected_index >= len(recommendations):
        return error_response("Invalid selection", status=400, code="INVALID_SELECTION")

    selected_name = recommendations[selected_index]
    session["selected_name"] = selected_name

    fortune = get_daily_fortune(selected_name["name"])
    session["fortune"] = fortune

    return jsonify({"success": True, "name": selected_name, "fortune": fortune})


@app.route("/save_preference", methods=["POST"])
def save_preference() -> Tuple[Response, int] | Response:
    """Save user preference (stored in session only)."""
    if not enforce_csrf(strict=False):
        return error_response("Invalid CSRF token", status=403, code="CSRF_FAILED")

    data = request.get_json(silent=True)
    if not data:
        return error_response("No data provided", status=400, code="NO_DATA")

    save = data.get("save", False)
    session["save_preference"] = save

    if save:
        session["saved_data"] = {
            "timestamp": datetime.now().isoformat(),
            "original_name": session.get("original_name"),
            "selected_name": session.get("selected_name"),
            "session_id": session.get("session_id"),
        }

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
