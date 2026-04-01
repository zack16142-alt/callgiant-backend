"""
CallGiant - SQLite Database Layer
Two tables: call_logs and settings.
Leads are stored in a separate in-memory list imported from files.
"""

import sqlite3
import os
import sys


def _app_dir() -> str:
    """Return the directory where the app files live.

    When running as a PyInstaller --onefile exe, data files are
    extracted to a temporary folder pointed to by sys._MEIPASS.
    The database, however, should live *next to the .exe* so it
    persists across runs.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled exe — put DB beside the executable
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(_app_dir(), "callgiant.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            name TEXT DEFAULT '',
            company TEXT DEFAULT '',
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT,
            lead_name TEXT DEFAULT '',
            call_status TEXT,
            agent_transferred INTEGER DEFAULT 0,
            call_duration INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # Migrate old schema if needed — add missing columns silently
    _migrate(conn)
    conn.commit()
    conn.close()


def _migrate(conn):
    """Handle upgrades from older schemas gracefully."""
    try:
        cur = conn.execute("PRAGMA table_info(call_logs)")
        cols = {row["name"] for row in cur.fetchall()}
        # If old columns exist, drop and recreate
        if "pressed_1" in cols or "lead_id" in cols:
            conn.execute("DROP TABLE IF EXISTS call_logs")
            conn.execute("""
                CREATE TABLE call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT,
                    lead_name TEXT DEFAULT '',
                    call_status TEXT,
                    agent_transferred INTEGER DEFAULT 0,
                    call_duration INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception:
        pass


# --------------- Settings ---------------

def get_setting(key, default=""):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def save_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


# --------------- Leads ---------------

def add_leads(leads_list):
    """Insert leads. Each item: dict with keys phone, name, company."""
    conn = get_connection()
    cur = conn.cursor()
    for lead in leads_list:
        cur.execute(
            "INSERT INTO leads (phone, name, company) VALUES (?, ?, ?)",
            (lead.get("phone", ""), lead.get("name", ""), lead.get("company", "")),
        )
    conn.commit()
    conn.close()


def get_all_leads():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_leads():
    conn = get_connection()
    conn.execute("DELETE FROM leads")
    conn.commit()
    conn.close()


# --------------- Call Logs ---------------

def add_call_log(phone_number, lead_name, call_status,
                 agent_transferred=False, call_duration=0):
    conn = get_connection()
    conn.execute(
        """INSERT INTO call_logs
           (phone_number, lead_name, call_status, agent_transferred, call_duration)
           VALUES (?, ?, ?, ?, ?)""",
        (phone_number, lead_name, call_status,
         1 if agent_transferred else 0, call_duration),
    )
    conn.commit()
    conn.close()


def get_all_call_logs():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM call_logs ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_call_logs():
    conn = get_connection()
    conn.execute("DELETE FROM call_logs")
    conn.commit()
    conn.close()
