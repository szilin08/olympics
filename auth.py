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
"""

import hashlib
import os

import streamlit as st

import theme

DEFAULT_PASSWORD = "olympics123"
DEFAULT_UMPIRE_PASSWORD = "umpire123"


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
            st.session_state["is_admin"] = False
            st.session_state["current_page"] = "Badminton"
            st.rerun()
        return

    with st.sidebar.expander("🔒 Admin login", expanded=False):
        st.caption(f"Password source: **{_password_source()}**")
        pw = st.text_input("Admin password", type="password", key="admin_pw_input")
        if st.button("Unlock admin mode", key="unlock_btn", use_container_width=True, type="primary"):
            if _hash(pw) == _hash(_get_admin_password()):
                st.session_state["is_admin"] = True
                st.session_state["admin_name"] = st.session_state.get("admin_name_input", "admin")
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
                st.rerun()
            else:
                st.error("Incorrect password.")


def require_scorer():
    """Call at the top of an umpiring page. Allows both umpires and full
    admins through; stops rendering for anyone else."""
    if not is_scorer():
        st.warning("🔒 This page is for umpires/admins only. Unlock umpire or admin mode from the sidebar to continue.")
        st.stop()
