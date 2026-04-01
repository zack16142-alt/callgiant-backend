"""
webhook.py — Flask server for CallGiant voice & DTMF handling.

Two endpoints:
    POST /voice  — Returns TwiML that speaks a message and gathers a keypress.
    POST /dtmf   — Handles the gathered digit (1 = transfer to agent).

Environment variables:
    BASE_URL  — Public URL Twilio can reach (required in production)
    PORT      — Port to listen on (default: 7000)
"""

import logging
import os
import sqlite3

from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather

# ---------------------------------------------------------------------------
#  Environment configuration
# ---------------------------------------------------------------------------
BASE_URL     = os.environ.get("BASE_URL", "")
PORT         = int(os.environ.get("PORT", "7000"))

# Webhook settings — read from env vars first (Render), DB fallback (local)
ENV_TTS_MESSAGE  = os.environ.get("TTS_MESSAGE", "")
ENV_AGENT_NUMBER = os.environ.get("AGENT_NUMBER", "")

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("callgiant.webhook")

app = Flask(__name__)

# ---------------------------------------------------------------------------
#  Database helper — reads settings from SQLite when running locally.
#  On Render, the DB won't exist so env vars take priority.
# ---------------------------------------------------------------------------
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "callgiant.db")

# Map DB setting keys → env var overrides
_ENV_OVERRIDES = {
    "tts_message":  ENV_TTS_MESSAGE,
    "agent_number": ENV_AGENT_NUMBER,
}


def _get_setting(key: str, default: str = "") -> str:
    """
    Read a setting value.
    Priority: environment variable → SQLite DB → default.
    """
    # 1. Check env var override
    env_val = _ENV_OVERRIDES.get(key, "")
    if env_val:
        return env_val

    # 2. Try SQLite (works locally, may not exist on Render)
    try:
        conn = sqlite3.connect(_DB_PATH)
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


# ---------------------------------------------------------------------------
#  /voice — initial call handler
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Health check — confirms the webhook server is alive."""
    return "CallGiant webhook is running.", 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "callgiant-webhook"}, 200


@app.route("/voice", methods=["POST"])
def handle_voice():
    """
    Twilio requests this URL when a call is answered.

    1. Reads the TTS message from the database.
    2. Speaks it via <Say>.
    3. Wraps it in <Gather> so the callee can press a digit.
    4. If no input is received, says goodbye and hangs up.
    """
    message = _get_setting("tts_message", "Hello, this is an automated call.")
    agent_number = _get_setting("agent_number", "")

    response = VoiceResponse()

    # Build <Gather> with the spoken message inside it
    gather = Gather(
        num_digits=1,
        action=f"/dtmf?agent={agent_number}",
        method="POST",
    )
    gather.say(message, voice="alice")
    response.append(gather)

    # No input fallback — repeat once, then hang up
    response.say("We didn't receive any input. Goodbye.", voice="alice")

    return Response(str(response), mimetype="text/xml")


# ---------------------------------------------------------------------------
#  /dtmf — digit handler (existing)
# ---------------------------------------------------------------------------


@app.route("/dtmf", methods=["POST"])
def handle_dtmf():
    """
    Twilio POSTs here after the callee presses a digit during <Gather>.

    The agent number is passed as a query parameter from /voice:
        action="/dtmf?agent=+15551234567"

    Digit "1"  →  mark transfer in DB, <Dial> agent
    Anything else  →  <Say> thank you, hang up
    """
    digits       = request.form.get("Digits", "")
    call_sid     = request.form.get("CallSid", "")
    caller_phone = request.form.get("From", "")

    agent_number = (
        request.args.get("agent")
        or request.form.get("agent_number")
        or ""
    )

    logger.info("DTMF received: %s  |  CallSid: %s  |  From: %s", digits, call_sid, caller_phone)

    # Persist the DTMF result in the database
    try:
        conn = sqlite3.connect(_DB_PATH)
        if digits == "1" and caller_phone:
            # Mark the most recent call_log for this phone as transferred
            conn.execute(
                """UPDATE call_logs
                      SET agent_transferred = 1,
                          call_status = 'transferred'
                    WHERE id = (
                        SELECT id FROM call_logs
                         WHERE phone_number = ?
                         ORDER BY timestamp DESC
                         LIMIT 1
                    )""",
                (caller_phone,),
            )
        # Log the raw DTMF event to settings as a lightweight audit trail
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (f"last_dtmf_{call_sid}", digits),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.error("DTMF DB write error: %s", exc)

    # Build TwiML response
    response = VoiceResponse()

    if digits == "1" and agent_number:
        response.say("Connecting you now. Please hold.", voice="alice")
        response.dial(agent_number)
    elif digits == "1":
        response.say(
            "Thank you for your interest. An agent will call you back shortly.",
            voice="alice",
        )
    else:
        response.say("Thank you. Goodbye.", voice="alice")

    return Response(str(response), mimetype="text/xml")


# ---------------------------------------------------------------------------
#  Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000))
    logger.info("Starting CallGiant webhook on port %d", port)
    logger.info("TTS_MESSAGE: %s", ENV_TTS_MESSAGE or "(from DB)")
    logger.info("AGENT_NUMBER: %s", ENV_AGENT_NUMBER or "(from DB)")
    app.run(host="0.0.0.0", port=port)
