"""
SQLite persistence layer.

Design note: the tournament state (bracket ties, group standings, scores)
is a nested, fast-changing structure that mirrors what the original HTML
kept in localStorage. Rather than exploding it into a dozen relational
tables (which buys nothing here since nothing is ever queried by SQL —
every read pulls the *whole* bracket), we store it as JSON documents in a
simple key/value table. This keeps the port faithful to the original
logic, keeps writes atomic (one row = one consistent snapshot), and is
trivial to swap for MongoDB later (same get_state/set_state interface,
one collection instead of one table).
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager

DB_PATH = os.environ.get("TOURNEY_DB_PATH", os.path.join(os.path.dirname(__file__), "tournament.db"))

_lock = threading.Lock()


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT,
                action TEXT,
                detail TEXT,
                ts TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def get_state(key: str, default=None):
    with _lock, _conn() as conn:
        row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row[0])


def set_state(key: str, value, actor: str = "system", action: str = "update"):
    with _lock, _conn() as conn:
        conn.execute(
            """INSERT INTO state (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
            (key, json.dumps(value)),
        )
        conn.execute(
            "INSERT INTO audit_log (actor, action, detail) VALUES (?, ?, ?)",
            (actor, action, key),
        )


def get_audit_log(limit: int = 50):
    with _lock, _conn() as conn:
        rows = conn.execute(
            "SELECT actor, action, detail, ts FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"actor": r[0], "action": r[1], "detail": r[2], "ts": r[3]} for r in rows]
