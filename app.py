"""Flask server for HackStart pages and team registrations."""

from __future__ import annotations

import hmac
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge


PARTICIPANTS_FILE = Path(
    os.environ.get("PARTICIPANTS_FILE", os.path.join(os.path.dirname(__file__), "participants.json"))
)
MAX_BODY_BYTES = 16 * 1024
TOPICS = {"a", "b", "c", "d", "open-track"}
PHONE_PATTERN = re.compile(r"^[+()0-9.\-\s]{7,32}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
FILE_LOCK = threading.Lock()

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES


def authorized(token_name: str) -> bool:
    authorization = request.headers.get("Authorization", "")
    scheme, separator, provided = authorization.partition(" ")
    expected = os.environ.get(token_name, "")
    return bool(
        separator
        and scheme.casefold() == "bearer"
        and len(expected.encode("utf-8")) >= 32
        and hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
    )


def read_text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} is required.")
    text = value.strip()
    if not text or len(text) > maximum:
        raise ValueError(f"{label} must be between 1 and {maximum} characters.")
    return text


def validate_registration(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Registration must be a JSON object.")
    team_lead = value.get("teamLead")
    if not isinstance(team_lead, dict):
        raise ValueError("Team lead details are required.")
    participants = value.get("participants")
    if not isinstance(participants, list) or not 3 <= len(participants) <= 4:
        raise ValueError("A team must have 3 or 4 participants in addition to the team lead.")
    topic = value.get("topic")
    if not isinstance(topic, str) or topic not in TOPICS:
        raise ValueError("Choose a valid topic.")

    email = read_text(team_lead.get("email"), "Team lead email", 254)
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid team lead email address.")
    lead_phone = read_text(team_lead.get("phone"), "Team lead phone", 32)
    if not PHONE_PATTERN.fullmatch(lead_phone):
        raise ValueError("Enter a valid team lead phone number.")

    validated_participants = []
    for index, participant in enumerate(participants, start=1):
        if not isinstance(participant, dict):
            raise ValueError(f"Participant {index} must include a name and phone.")
        phone = read_text(participant.get("phone"), f"Participant {index} phone", 32)
        if not PHONE_PATTERN.fullmatch(phone):
            raise ValueError(f"Enter a valid phone number for participant {index}.")
        validated_participants.append({
            "name": read_text(participant.get("name"), f"Participant {index} name", 100),
            "phone": phone,
        })

    return {
        "id": str(uuid.uuid4()),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "teamName": read_text(value.get("teamName"), "Team name", 80),
        "teamLead": {
            "name": read_text(team_lead.get("name"), "Team lead name", 100),
            "phone": lead_phone,
            "email": email,
        },
        "participants": validated_participants,
        "topic": topic,
    }


def load_participants() -> list[dict[str, Any]]:
    try:
        with PARTICIPANTS_FILE.open(encoding="utf-8") as data_file:
            records = json.load(data_file)
    except FileNotFoundError:
        return []
    if not isinstance(records, list):
        raise ValueError("Participants file must contain a JSON array.")
    return records


def append_participant(participant: dict[str, Any]) -> None:
    PARTICIPANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with FILE_LOCK:
        records = load_participants()
        records.append(participant)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=PARTICIPANTS_FILE.parent,
                prefix=f"{PARTICIPANTS_FILE.name}.",
                suffix=".tmp",
                delete=False,
            ) as data_file:
                temporary_path = Path(data_file.name)
                json.dump(records, data_file, ensure_ascii=False, indent=2)
                data_file.write("\n")
            os.replace(temporary_path, PARTICIPANTS_FILE)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_error: RequestEntityTooLarge):
    return jsonify(error="Request body is too large.", maxBytes=MAX_BODY_BYTES), 413


@app.route("/api/participants", methods=["GET", "POST"])
def participants_api():
    token_name = "HACKSTART_ADMIN_TOKEN" if request.method == "GET" else "HACKSTART_REGISTRATION_TOKEN"
    if not authorized(token_name):
        return jsonify(error="A valid bearer token is required."), 401
    if request.method == "GET":
        try:
            return jsonify(load_participants())
        except (OSError, ValueError, json.JSONDecodeError):
            app.logger.exception("Could not read participant records")
            return jsonify(error="Could not read participant records."), 500
    if not request.is_json:
        return jsonify(error="Content-Type must be application/json."), 415
    try:
        registration = validate_registration(request.get_json())
        append_participant(registration)
    except (BadRequest, ValueError) as error:
        return jsonify(error=str(error) or "Request body must be valid JSON."), 400
    except (OSError, json.JSONDecodeError):
        app.logger.exception("Could not save participant record")
        return jsonify(error="Could not save registration."), 500
    return jsonify(id=registration["id"], message="Registration saved."), 201


if __name__ == "__main__":
    registration_token = os.environ.get("HACKSTART_REGISTRATION_TOKEN", "")
    admin_token = os.environ.get("HACKSTART_ADMIN_TOKEN", "")
    if min(len(registration_token.encode()), len(admin_token.encode())) < 32:
        raise SystemExit("Configure separate registration and admin tokens of at least 32 bytes.")
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "3000")))