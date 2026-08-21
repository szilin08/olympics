"""
Simple shared-password admin auth.

Anyone can view the dashboard/monitors. To reach the input/scoring pages,
a user must unlock "Admin mode" with a shared password for the session.

The password is never stored in plain text in code: it's compared as a
SHA-256 hash. Set it via (in priority order):
  1. Streamlit secrets:  st.secrets["admin_password"]
  2. Environment var:    TOURNEY_ADMIN_PASSWORD
  3. Fallback default:   "changeme123"  (⚠ change this before real use)
"""

import hashlib
import os

import streamlit as st

import theme

DEFAULT_PASSWORD = "olympics123"


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


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def is_admin() -> bool:
    return bool(st.session_state.get("is_admin", False))


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
            st.session_state["current_page"] = "Home"
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