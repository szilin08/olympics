import streamlit as st

import assets
import auth
import db
import theme
import pages_public
import pages_admin

st.set_page_config(page_title="LBS × MGB Sports Tournament", page_icon="🏆", layout="wide")
db.init_db()
theme.inject_css()

VIEWER_PAGES = [
    ("Home", "🏠", pages_public.render_overview),
    ("Badminton", "🏸", pages_public.render_badminton_monitor),
    ("Pickleball", "🏓", pages_public.render_pickleball_monitor),
]

ADMIN_PAGES = [
    ("Badminton — Admin", "🎯", pages_admin.render_badminton_admin),
    ("Pickleball — Admin", "📝", pages_admin.render_pickleball_admin),
]


def _nav_button(label, icon, active):
    clicked = st.button(
        label, key=f"navbtn_{label}", use_container_width=True,
        type="primary" if active else "secondary",
    )
    if clicked:
        st.session_state["current_page"] = label
        st.rerun()


def main():
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Home"

    available = dict((label, fn) for label, _, fn in VIEWER_PAGES)
    if auth.is_admin():
        available.update((label, fn) for label, _, fn in ADMIN_PAGES)

    # Bounce back to Home if the current page no longer exists — either the
    # admin logged out while on an admin-only page, or (as with the removed
    # Schedule & Settings page) a page was retired while someone's session
    # still pointed at it.
    if st.session_state["current_page"] not in available:
        st.session_state["current_page"] = "Home"

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sb-partner-logo">
                <img src="data:image/png;base64,{assets.LBS_LOGO_B64}" alt="LBS 65 Years">
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="sb-logo-wrap">
                <div class="sb-logo-title">LBS <span class="sb-logo-x">×</span> MGB</div>
                <div class="sb-logo-sub">Sports Tournament</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="nav-label">Viewer</div>', unsafe_allow_html=True)
        for label, icon, _ in VIEWER_PAGES:
            _nav_button(label, icon, st.session_state["current_page"] == label)

        if auth.is_admin():
            st.markdown('<div class="nav-label">Admin</div>', unsafe_allow_html=True)
            for label, icon, _ in ADMIN_PAGES:
                _nav_button(label, icon, st.session_state["current_page"] == label)

        # ── bottom block: admin login, then the user chip with the
        # dark/light toggle sitting right beside it in a narrow column ──
        st.markdown('<hr class="sb-bottom-divider">', unsafe_allow_html=True)
        auth.login_widget()

        who = st.session_state.get("admin_name", "Viewer") if auth.is_admin() else "Viewer"
        role = "Admin" if auth.is_admin() else "Viewer"
        user_col, toggle_col = st.columns([4, 1])
        with user_col:
            st.markdown(
                f"""
                <div class="sb-user-row">
                    <div class="sb-avatar">{who[:2].upper()}</div>
                    <div>
                        <div class="sb-user-name">{who}</div>
                        <div class="sb-user-role">{role.upper()}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with toggle_col:
            theme.toggle_widget()

    available[st.session_state["current_page"]]()


if __name__ == "__main__":
    main()