"""
CallGiant - Calling Engine
Handles real Twilio outbound calls via the REST API.
"""

import os
import threading
import time
import queue

from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

import database as db

BASE_URL = os.environ.get("BASE_URL", "")


# ──────────────────────────────────────────────
#  Call Engine
# ──────────────────────────────────────────────

class CallEngine:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.running = False
        self._thread = None

    # --- event helpers ---
    def emit(self, event_type, data=None):
        self.message_queue.put((event_type, data))

    # --- public API ---
    def start_calling(self):
        if self.running:
            return
        # Ensure previous thread is fully done
        if self._thread is not None and self._thread.is_alive():
            return
        self.running = True
        self._thread = threading.Thread(target=self._call_loop, daemon=True)
        self._thread.start()

    def stop_calling(self):
        self.running = False
        self.emit("log", "STOP requested — finishing current call...")

    # --- main loop ---
    def _call_loop(self):
        leads = db.get_all_leads()
        if not leads:
            self.emit("log", "No leads to call.")
            self.emit("complete", None)
            self.running = False
            return

        # Load settings
        account_sid   = db.get_setting("twilio_sid")
        auth_token    = db.get_setting("twilio_token")
        twilio_number = db.get_setting("twilio_number")
        delay         = max(1, float(db.get_setting("call_delay", "5")))

        if not account_sid or not auth_token or not twilio_number:
            self.emit("log", "[ERROR] Twilio credentials missing — cannot make calls.")
            self.emit("log", "Please set Account SID, Auth Token, and Twilio Number in Call Settings.")
            self.emit("complete", None)
            self.running = False
            return

        # Authenticate with Twilio
        try:
            twilio_client = TwilioClient(account_sid, auth_token)
            # Verify credentials by fetching the account
            twilio_client.api.accounts(account_sid).fetch()
            self.emit("log", "Twilio authenticated successfully")
        except TwilioRestException as e:
            self.emit("log", f"[ERROR] Twilio authentication failed: {e.msg}")
            self.emit("complete", None)
            self.running = False
            return
        except Exception as e:
            self.emit("log", f"[ERROR] Failed to connect to Twilio: {e}")
            self.emit("complete", None)
            self.running = False
            return

        voice_url = BASE_URL + "/voice"
        self.emit("log", f"Voice webhook: {voice_url}")
        self.emit("log", f"Calling from: {twilio_number}")

        total = len(leads)
        self.emit("log", f"{total} leads queued\n{'='*40}")

        for i, lead in enumerate(leads):
            if not self.running:
                self.emit("log", "\nStopped by user.")
                break

            phone = lead["phone"]
            name  = lead.get("name", "") or "Unknown"

            self.emit("progress", (i, total))
            self.emit("log", f"\n[{i+1}/{total}] Calling {name} ({phone}) ...")

            try:
                result = self._twilio_call(
                    twilio_client, phone, twilio_number, voice_url,
                )

                status   = result.get("status", "unknown")
                call_sid = result.get("call_sid", "")
                duration = result.get("duration", 0)

                self.emit("log", f"  Call SID: {call_sid}")
                self.emit("log", f"  Final status: {status}")

                db.add_call_log(
                    phone_number=phone,
                    lead_name=name,
                    call_status=status,
                    agent_transferred=False,
                    call_duration=duration,
                )

            except TwilioRestException as e:
                error_msg = self._classify_twilio_error(e)
                self.emit("log", f"  [ERROR] {error_msg}")
                db.add_call_log(
                    phone_number=phone,
                    lead_name=name,
                    call_status=f"error: {error_msg}",
                )
            except Exception as e:
                self.emit("log", f"  [ERROR] Network/unexpected: {e}")
                db.add_call_log(
                    phone_number=phone,
                    lead_name=name,
                    call_status=f"error: {e}",
                )

            # Delay between calls (check stop flag every 100ms)
            if self.running and i < total - 1:
                self.emit("log", f"  Waiting {delay}s before next call...")
                for _ in range(int(delay * 10)):
                    if not self.running:
                        break
                    time.sleep(0.1)

        self.emit("progress", (total, total))
        self.emit("log", f"\n{'='*40}\nCalling session complete.")
        self.emit("complete", None)
        self.running = False
        self._thread = None

    # --- Twilio call ---
    def _twilio_call(self, client, to_number, from_number, voice_url):
        """Place one real Twilio call using url= to the hosted /voice endpoint."""
        call = client.calls.create(
            to=to_number,
            from_=from_number,
            url=voice_url,
        )
        self.emit("log", f"  Call initiated — SID: {call.sid}")
        self.emit("log", f"  Status: {call.status}")

        # Poll Twilio for terminal status (up to ~2 min)
        for _ in range(60):
            if not self.running:
                break
            time.sleep(2)
            call = client.calls(call.sid).fetch()
            self.emit("log", f"  Polling — status: {call.status}")
            if call.status in ("completed", "busy", "no-answer", "failed", "canceled"):
                break
        return {
            "status": call.status,
            "call_sid": call.sid,
            "duration": int(call.duration or 0),
        }

    @staticmethod
    def _classify_twilio_error(exc: TwilioRestException) -> str:
        """Return a human-readable message for common Twilio error codes."""
        code = exc.code
        if code == 21211:
            return f"Invalid phone number: {exc.msg}"
        elif code == 21214:
            return f"Non-mobile number or unreachable: {exc.msg}"
        elif code == 21217:
            return f"Phone number not verified (trial account): {exc.msg}"
        elif code == 20003:
            return f"Authentication failed — check SID/token: {exc.msg}"
        elif code == 20404:
            return f"Resource not found: {exc.msg}"
        elif code in (21215, 21216):
            return f"Geographic permission error: {exc.msg}"
        else:
            return f"Twilio error {code}: {exc.msg}"


# ──────────────────────────────────────────────
#  Standalone helper: make_real_call()
# ──────────────────────────────────────────────

def make_real_call(phone_number: str, lead_name: str = "") -> dict:
    """
    Place a single real outbound call via Twilio.

    Twilio fetches TwiML from BASE_URL + "/voice" when the call
    connects. The hosted endpoint controls the call flow (message,
    gather, transfer).

    Returns a dict:
        {
            "success":  bool,
            "status":   str,        # e.g. "completed", "no-answer", "error"
            "call_sid": str,
            "duration": int,        # seconds
            "error":    str | None,
        }
    """
    result = {
        "success": False,
        "status": "error",
        "call_sid": "",
        "duration": 0,
        "error": None,
    }

    # ── 1. Load settings from DB ──
    account_sid   = db.get_setting("twilio_sid")
    auth_token    = db.get_setting("twilio_token")
    twilio_number = db.get_setting("twilio_number")
    voice_url     = BASE_URL + "/voice"

    if not account_sid or not auth_token or not twilio_number:
        result["error"] = (
            "Twilio credentials are incomplete. "
            "Please set Account SID, Auth Token, and Twilio Phone Number in Call Settings."
        )
        _log_call_result(phone_number, lead_name, result)
        return result

    if not phone_number or not phone_number.strip():
        result["error"] = "Phone number is empty."
        _log_call_result(phone_number, lead_name, result)
        return result

    # ── 2. Create Twilio client ──
    try:
        client = TwilioClient(account_sid, auth_token)
    except Exception as exc:
        result["error"] = f"Failed to create Twilio client: {exc}"
        _log_call_result(phone_number, lead_name, result)
        return result

    # ── 3. Place the call ──
    try:
        call = client.calls.create(
            to=phone_number.strip(),
            from_=twilio_number,
            url=voice_url,
        )
        result["call_sid"] = call.sid

        # Poll Twilio for a terminal status (up to ~2 min)
        for _ in range(60):
            time.sleep(2)
            call = client.calls(call.sid).fetch()
            if call.status in ("completed", "busy", "no-answer", "failed", "canceled"):
                break

        result["status"]   = call.status
        result["duration"] = int(call.duration or 0)
        result["success"]  = call.status == "completed"

    except TwilioRestException as exc:
        result["error"]  = CallEngine._classify_twilio_error(exc)
        result["status"] = "error"
    except Exception as exc:
        result["error"]  = f"Network/unexpected error: {exc}"
        result["status"] = "error"

    # ── 4. Log to database ──
    _log_call_result(phone_number, lead_name, result)
    return result


def _log_call_result(phone: str, name: str, result: dict):
    """Persist a call result in the call_logs table."""
    try:
        status_text = result.get("status", "error")
        if result.get("error"):
            status_text = f"error: {result['error']}"

        db.add_call_log(
            phone_number=phone or "",
            lead_name=name or "",
            call_status=status_text,
            agent_transferred=result.get("pressed_1", False),
            call_duration=result.get("duration", 0),
        )
    except Exception:
        pass  # Never crash on logging failure
