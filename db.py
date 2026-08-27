"""
MongoDB persistence layer — drop-in replacement for the SQLite db.py.

Same public interface (init_db, get_state, set_state, get_audit_log) so
nothing in state.py, logic.py, or the page files needs to change — this
was the whole point of routing every read/write through db.py in the
first place (see the README's "Swapping in MongoDB later" section).

Connection string comes from Streamlit secrets (st.secrets["mongo_uri"])
or the MONGO_URI environment variable, in that priority order — mirroring
how auth.py resolves the admin password.
"""

import os

import streamlit as st
from pymongo import MongoClient
from pymongo.errors import PyMongoError

_client = None
_db = None


def _get_uri() -> str:
    try:
        if "mongo_uri" in st.secrets:
            return str(st.secrets["mongo_uri"])
    except Exception:
        pass
    uri = os.environ.get("MONGO_URI")
    if not uri:
        raise RuntimeError(
            "No MongoDB connection string found. Set st.secrets['mongo_uri'] "
            "(Streamlit Cloud Secrets) or the MONGO_URI environment variable."
        )
    return uri


def _get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(_get_uri())
        _db = _client.get_default_database()
        if _db is None:  # URI had no db name path segment — fall back to a fixed name
            _db = _client["tournament"]
    return _db


def init_db():
    # Nothing to create up front — Mongo creates collections/indexes
    # lazily on first write. This exists only so app.py's db.init_db()
    # call keeps working unchanged.
    _get_db()


def get_state(key: str, default=None):
    doc = _get_db()["state"].find_one({"_id": key})
    if doc is None:
        return default
    return doc["value"]


def set_state(key: str, value, actor: str = "system", action: str = "update"):
    import datetime

    now = datetime.datetime.utcnow().isoformat() + "Z"
    _get_db()["state"].update_one(
        {"_id": key},
        {"$set": {"value": value, "updated_at": now}},
        upsert=True,
    )
    _get_db()["audit_log"].insert_one(
        {"actor": actor, "action": action, "detail": key, "ts": now}
    )


def get_audit_log(limit: int = 50):
    cursor = (
        _get_db()["audit_log"]
        .find({}, {"_id": 0})
        .sort("ts", -1)
        .limit(limit)
    )
    return list(cursor)
