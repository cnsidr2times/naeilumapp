##!/usr/bin/env python
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
from typing import Any, Dict, List, Optional, Tuple

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

app = Flask(__name__)
app.secret_key = os.environ.get("NAEILUM_SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=7)
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("NAEILUM_SESSION_COOKIE_SECURE", "true").lower()
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
                "name": "송월선",
                "hanja": "宋蔚宣",
                "category": "Wisdom",
                "meaning": "One who proclaims great wisdom like a pine tree",
                "initial": "W",
                "special_match": "Wilson Smith",
            },
            {
                "name": "박지후",
                "hanja": "朴智厚",
                "category": "Wisdom",
                "meaning": "Wise and profound like a thick forest",
                "initial": "J",
            },
        ],
        "female": [
            {
                "name": "김서윤",
                "hanja": "金瑞允",
                "category": "Grace",
                "meaning": "A graceful blessing that shines brightly",
                "initial": "S",
            },
            {
                "name": "이하린",
                "hanja": "李夏凜",
                "category": "Creativity",
                "meaning": "A creative spirit as refreshing as summer dew",
                "initial": "H",
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
    except Exception:  # noqa: BLE001
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
        {"category": "Love", "messages": ["Love finds you when you're true to yourself"]},
        {"category": "Career", "messages": ["Your dedication will be recognized soon"]},
        {"category": "Wealth", "messages": ["Financial wisdom comes through patient planning"]},
        {"category": "Health", "messages": ["Your body thanks you for mindful choices"]},
        {"category": "Wisdom", "messages": ["A lesson from the past illuminates your path"]},
    ]


# Load data on startup
NAMES_DATA = load_names()
FORTUNES_DATA = load_fortunes()


def normalize_name(name: str) -> str:
    """Normalize name for matching - remove spaces and diacritics, convert to lowercase."""
    normalized = unicodedata.normalize("NFD", name)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^a-zA-Z0-9]", "", normalized).lower()
    return normalized


def get_name_initial(name: str) -> str:
    """Extract the first letter of the first name."""
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


def select_korean_names(original_name: str, gender: str) -> List[Dict[str, Any]]:
    """Select Korean names based on the original name."""
    names: List[Dict[str, Any]] = []
    normalized_input = normalize_name(original_name)

    if normalized_input == "wilsonsmith":
        for name in NAMES_DATA.get("male", []):
            if name.get("special_match") == "Wilson Smith":
                names.append(name)
                break
        gender_names = NAMES_DATA.get("male", [])
        available_names = [n for n in gender_names if not n.get("special_match")]
        if available_names:
            random.shuffle(available_names)
            names.extend(available_names[:4])
        return names[:5]

    gender_names = NAMES_DATA.get(gender, [])
    if not gender_names:
        return []

    initial = get_name_initial(original_name)
    matching_names = [
        name for name in gender_names if not name.get("special_match") and name.get("initial") == initial
    ]

    if not matching_names:
        matching_names = [n for n in gender_names if not n.get("special_match")]

    if matching_names:
        random.shuffle(matching_names)
        names = matching_names[:5]

    return names


def get_daily_fortune(korean_name: str) -> List[Dict[str, str]]:
    """Generate daily fortune based on Korean name."""
    today = datetime.now().strftime("%Y-%m-%d")
    seed_string = f"{korean_name}{today}"
    rng = random.Random(hashlib.md5(seed_string.encode(), usedforsecurity=False).hexdigest())

    fortunes = []
    for category_data in FORTUNES_DATA:
        category = category_data["category"]
        messages = category_data.get("messages", [])
        if messages:
            message = rng.choice(messages)
            fortunes.append({"category": category, "message": message})

    return fortunes


def validate_gender(raw_gender: Optional[str]) -> str:
    """Validate gender input and fall back to 'male' if invalid."""
    if raw_gender not in ALLOWED_GENDERS:
        logger.warning("Invalid gender value received: %s", raw_gender)
        return "male"
    return raw_gender  # type: ignore[return-value]


def ensure_csrf_token() -> str:
    """Ensure a CSRF token exists in the session and return it."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
        logger.debug("Generated new CSRF token for session %s", session.get("session_id"))
    return token


def enforce_csrf(strict: bool) -> bool:
    """
    Validate CSRF token from header.

    When strict=True, the header must be present and valid.
    When strict=False, validation occurs only if the header is provided.
    """
    provided = request.headers.get(CSRF_HEADER_NAME)
    expected = session.get("csrf_token")

    if not provided:
        if strict:
            logger.warning("CSRF token missing for strict endpoint %s", request.path)
            return False
        return True

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

    # Example curl:
    # curl -X POST http://localhost:5000/api/theme \
    #      -H "Content-Type: application/json" \
    #      -H "X-CSRF-Token: <token>" \
    #      -d '{"theme": "dark"}'
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