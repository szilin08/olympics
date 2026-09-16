"""
Simple shared-password admin + umpire auth.

Anyone can view the dashboard/monitors. To reach the input/scoring pages,
a user must unlock either:
  - "Admin mode" — full access: team/pair names, resets, backup/restore,
    schedule, and scoring.
  - "Umpire mode" — scoring only. Umpires can open the same List/Scoring
    (badminton) and Group Matches / Knockout Bracket (pickleball) views
    and enter/adjust points, but every control that changes who's playing
    or wipes data (team/pair name fields, resets, backup/restore, auto-seed)
    is hidden or disabled for them.

Both passwords are never stored in plain text in code: they're compared as
SHA-256 hashes. Set each via (in priority order):
  Admin:
    1. Streamlit secrets:  st.secrets["admin_password"]
    2. Environment var:    TOURNEY_ADMIN_PASSWORD
    3. Fallback default:   "changeme123"  (⚠ change this before real use)
  Umpire:
    1. Streamlit secrets:  st.secrets["umpire_password"]
    2. Environment var:    TOURNEY_UMPIRE_PASSWORD
    3. Fallback default:   "umpire123"    (⚠ change this before real use)

Staying logged in across refreshes
-----------------------------------
Plain st.session_state does NOT reliably survive a real browser reload —
Streamlit reconnects with a brand-new session whenever the underlying
WebSocket actually drops (flaky event wifi, a phone browser backgrounding
the tab and reloading it fresh when switched back to, the Streamlit Cloud
app waking from sleep), which silently logs everyone back out even though
nothing about "logging out" was intended. That's the "why do I keep
getting logged out on refresh" complaint this fixes.

The fix: on a successful login, a random token is generated and (a) saved
server-side (via db.get_state/set_state, alongside its role/name and a
12-hour expiry) and (b) written into the page's URL as a query parameter
(?auth=<token>). Query params ARE part of the URL, so they survive a real
full-page reload the way session_state can't — the browser just re-requests
that same URL, token included. restore_session_from_token(), called once
at the top of app.py's main() before anything else checks is_admin()/
is_umpire(), looks for that query param and — if it names a still-valid
token — restores the session's admin/umpire state from it, with no
password re-entry needed. Logging out explicitly revokes the token and
clears the query param, so it can't be used to log back in afterward.

Trade-off, worth knowing: since the token lives in the URL, anyone who
gets hold of that exact URL (screenshot, shared link, browser history on
a shared device) has admin/umpire access for up to 12 hours without a
password. For a short internal event with trusted staff this trade favors
convenience; it would NOT be an appropriate pattern for anything
higher-stakes.
"""

import datetime as _dt
import hashlib
import os
import secrets as _secrets

import streamlit as st

import db
import theme

DEFAULT_PASSWORD = "olympics123"
DEFAULT_UMPIRE_PASSWORD = "umpire123"
LOGIN_TOKEN_TTL_HOURS = 12


def _password_source() -> str:
    """Which source is actually supplying the password right now — for the
    diagnostic line in the login box. Never reveals the password itself."""
    try:
        if "admin_password" in st.secrets:
            return "secrets.toml"
    except Exception:
        pass
    if os.environ.get("TOURNEY_ADMIN_PASSWORD"):
        return "environment variable"
    return "built-in default (changeme123)"


def _get_admin_password() -> str:
    try:
        if "admin_password" in st.secrets:
            return str(st.secrets["admin_password"])
    except Exception:
        pass
    return os.environ.get("TOURNEY_ADMIN_PASSWORD", DEFAULT_PASSWORD)


def _umpire_password_source() -> str:
    try:
        if "umpire_password" in st.secrets:
            return "secrets.toml"
    except Exception:
        pass
    if os.environ.get("TOURNEY_UMPIRE_PASSWORD"):
        return "environment variable"
    return "built-in default (umpire123)"


def _get_umpire_password() -> str:
    try:
        if "umpire_password" in st.secrets:
            return str(st.secrets["umpire_password"])
    except Exception:
        pass
    return os.environ.get("TOURNEY_UMPIRE_PASSWORD", DEFAULT_UMPIRE_PASSWORD)


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# ───────────────────────── "stay logged in" tokens ─────────────────────────

def _load_tokens() -> dict:
    return db.get_state("login_tokens", {}) or {}


def _save_tokens(tokens: dict):
    db.set_state("login_tokens", tokens, actor="system", action="touch_login_tokens")


def _create_login_token(role: str, name: str) -> str:
    """Mints a fresh token for a just-completed login, valid for
    LOGIN_TOKEN_TTL_HOURS. Also opportunistically drops any already-expired
    tokens from the store while it's here, rather than needing a separate
    cleanup job — logins are infrequent enough that this is plenty."""
    now = _dt.datetime.utcnow()
    tokens = {
        t: v for t, v in _load_tokens().items()
        if _dt.datetime.fromisoformat(v["expires"]) > now
    }
    token = _secrets.token_urlsafe(24)
    tokens[token] = {
        "role": role,
        "name": name,
        "expires": (now + _dt.timedelta(hours=LOGIN_TOKEN_TTL_HOURS)).isoformat(),
    }
    _save_tokens(tokens)
    return token


def _lookup_login_token(token: str):
    """Returns the token's {role, name, expires} dict if it exists and
    hasn't expired yet, else None."""
    entry = _load_tokens().get(token)
    if not entry:
        return None
    if _dt.datetime.fromisoformat(entry["expires"]) <= _dt.datetime.utcnow():
        return None
    return entry


def _revoke_login_token(token: str):
    tokens = _load_tokens()
    if token in tokens:
        del tokens[token]
        _save_tokens(tokens)


def restore_session_from_token():
    """Call once, at the very top of app.py's main() — before anything else
    checks is_admin()/is_umpire() — to auto-restore a login that a real
    page reload would otherwise have silently dropped (see the module
    docstring's "Staying logged in across refreshes" section). A no-op if
    the session is already authenticated, or if there's no valid ?auth=
    token to restore from."""
    if is_admin() or is_umpire():
        return
    token = st.query_params.get("auth")
    if not token:
        return
    entry = _lookup_login_token(token)
    if not entry:
        # Stale/expired/invalid token left over in the URL — clear it so
        # it doesn't keep getting (uselessly) checked on every rerun.
        try:
            del st.query_params["auth"]
        except KeyError:
            pass
        return
    if entry["role"] == "admin":
        st.session_state["is_admin"] = True
    else:
        st.session_state["is_umpire"] = True
    st.session_state["admin_name"] = entry["name"]
    st.session_state["_login_token"] = token


def is_admin() -> bool:
    return bool(st.session_state.get("is_admin", False))


def is_umpire() -> bool:
    return bool(st.session_state.get("is_umpire", False))


def is_scorer() -> bool:
    """True for anyone allowed to open a scoring page: full admins and
    umpires alike. Use this to gate access to umpiring pages."""
    return is_admin() or is_umpire()


def can_edit_structure() -> bool:
    """True only for full admins. Gates anything that changes *who's
    playing* or destroys data — team/pair name fields, resets, auto-seed,
    backup/restore — as opposed to just entering points, which umpires can
    also do."""
    return is_admin()


def actor_name() -> str:
    """Display/audit-log name for whoever is currently allowed to score —
    admin or umpire, whichever is active."""
    return st.session_state.get("admin_name", "admin")


def login_widget():
    """Renders a small login form in the sidebar. Returns nothing; sets session state."""
    if is_admin():
        T = theme.LIGHT if theme.get_mode() == "light" else theme.DARK
        st.sidebar.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{T["pill_green_fg"]};margin-bottom:6px">'
            f'🔓 Admin mode active</div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Log out of admin", key="logout_btn", use_container_width=True, type="primary"):
            token = st.session_state.pop("_login_token", None)
            if token:
                _revoke_login_token(token)
                try:
                    del st.query_params["auth"]
                except KeyError:
                    pass
            st.session_state["is_admin"] = False
            st.session_state["current_page"] = "Badminton"
            st.rerun()
        return

    with st.sidebar.expander("🔒 Admin login", expanded=False):
        st.caption(f"Password source: **{_password_source()}**")
        pw = st.text_input("Admin password", type="password", key="admin_pw_input")
        if st.button("Unlock admin mode", key="unlock_btn", use_container_width=True, type="primary"):
            if _hash(pw) == _hash(_get_admin_password()):
                name = st.session_state.get("admin_name_input", "admin")
                st.session_state["is_admin"] = True
                st.session_state["admin_name"] = name
                token = _create_login_token("admin", name)
                st.session_state["_login_token"] = token
                st.query_params["auth"] = token
                st.rerun()
            else:
                st.error("Incorrect password.")


def require_admin():
    """Call at the top of an admin-only page. Stops rendering if not logged in."""
    if not is_admin():
        st.warning("🔒 This page is for tournament admins only. Unlock admin mode from the sidebar to continue.")
        st.stop()


def umpire_login_widget():
    """Renders the umpire login/status box in the sidebar. A logged-in admin
    already has full scoring access, so this box only needs to appear for
    people who aren't already admins."""
    if is_admin():
        return

    if is_umpire():
        T = theme.LIGHT if theme.get_mode() == "light" else theme.DARK
        st.sidebar.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{T["pill_green_fg"]};margin-bottom:6px">'
            f'🎙️ Umpire mode active</div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Log out of umpire", key="logout_umpire_btn", use_container_width=True, type="primary"):
            token = st.session_state.pop("_login_token", None)
            if token:
                _revoke_login_token(token)
                try:
                    del st.query_params["auth"]
                except KeyError:
                    pass
            st.session_state["is_umpire"] = False
            st.session_state["current_page"] = "Badminton"
            st.rerun()
        return

    with st.sidebar.expander("🎙️ Umpire login", expanded=False):
        pw = st.text_input("Umpire password", type="password", key="umpire_pw_input")
        if st.button("Unlock umpire mode", key="unlock_umpire_btn", use_container_width=True, type="primary"):
            if _hash(pw) == _hash(_get_umpire_password()):
                st.session_state["is_umpire"] = True
                st.session_state["admin_name"] = "umpire"
                token = _create_login_token("umpire", "umpire")
                st.session_state["_login_token"] = token
                st.query_params["auth"] = token
                st.rerun()
            else:
                st.error("Incorrect password.")


def require_scorer():
    """Call at the top of an umpiring page. Allows both umpires and full
    admins through; stops rendering for anyone else."""
    if not is_scorer():
        st.warning("🔒 This page is for umpires/admins only. Unlock umpire or admin mode from the sidebar to continue.")
        st.stop()
