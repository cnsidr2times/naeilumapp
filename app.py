#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Naeilum (내일:음) - Korean Name Recommendation App
A Flask application that recommends Korean names for foreigners
"""

from flask import Flask, render_template, request, session, jsonify
import json
import random
import hashlib
import os
from datetime import datetime, timedelta
import secrets
import unicodedata
import re
import logging
from typing import Dict, List, Any, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_GENDERS = {"male", "female"}

app = Flask(__name__)
app.secret_key = os.environ.get("NAEILUM_SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(days=7)


def error_response(message: str, status: int = 400, code: Optional[str] = None):
    payload = {
        "success": False,
        "error": {
            "message": message,
        },
    }
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
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
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
    """Load Korean names from JSON files."""
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
    """Normalize name for matching - remove spaces, convert to lowercase."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(char for char in name if unicodedata.category(char) != "Mn")
    name = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
    return name


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
    rng = random.Random(hashlib.md5(seed_string.encode()).hexdigest())

    fortunes = []
    for category_data in FORTUNES_DATA:
        category = category_data["category"]
        messages = category_data.get("messages", [])
        if messages:
            message = rng.choice(messages)
            fortunes.append({"category": category, "message": message})

    return fortunes


def validate_gender(raw_gender: Optional[str]) -> str:
    if raw_gender not in ALLOWED_GENDERS:
        logger.warning("Invalid gender value received: %s", raw_gender)
        return "male"
    return raw_gender  # type: ignore[return-value]


@app.route("/")
def index():
    """Main page."""
    session.permanent = True
    if "session_id" not in session:
        session["session_id"] = generate_session_id()
    return render_template("index.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    """Process name and return recommendations."""
    data = request.get_json()

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
def select():
    """Handle name selection."""
    data = request.get_json()
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
def save_preference():
    """Save user preference (stored in session only)."""
    data = request.get_json()
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


@app.route("/privacy")
def privacy():
    """Privacy policy page."""
    return render_template("privacy.html")


@app.route("/about")
def about():
    """About page."""
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
