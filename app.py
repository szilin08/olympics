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


def _intro_overlay_html():
    """One-time cinematic welcome splash, shown only on the very first
    render of a session (gated by session_state in main(), not here).
    Built as pure CSS keyframe animation — no <script> tag and no onclick
    JS, since st.markdown injects via innerHTML, which browsers do not
    execute embedded <script> tags for (a real Streamlit quirk hit earlier
    in this project — components.html's iframe does execute scripts,
    plain st.markdown does not). A purely CSS-driven auto-dismiss sidesteps
    that entirely: the outer overlay carries its own keyframe animation
    that holds it opaque for ~3.6s then fades it to invisible AND
    pointer-events:none over the final ~0.9s, so it never blocks clicks
    on the dashboard underneath once it's done. Built as one unbroken
    concatenation (no literal blank lines) for the same reason the crest
    SVG was — a blank line inside a multi-line HTML string fed to
    st.markdown ends the raw-HTML block early under Streamlit's CommonMark
    parser, even with unsafe_allow_html=True."""
    crest_b64 = assets.CREST_LOGO_B64
    style = (
        "<style>"
        "@keyframes lbsIntroFade{0%{opacity:0;transform:translateY(8px);}100%{opacity:1;transform:translateY(0);}}"
        "@keyframes lbsIntroScale{0%{opacity:0;transform:scale(.6);}100%{opacity:1;transform:scale(1);}}"
        "@keyframes lbsOverlayOut{0%{opacity:1;}80%{opacity:1;}100%{opacity:0;visibility:hidden;pointer-events:none;}}"
        "</style>"
    )
    overlay = (
        '<div style="position:fixed;inset:0;z-index:999999;'
        'background:radial-gradient(circle at 50% 35%,#151b2c 0%,#0a0e17 65%);'
        'display:flex;align-items:center;justify-content:center;flex-direction:column;'
        'animation:lbsOverlayOut 4.5s ease forwards;">'
        '<div style="animation:lbsIntroScale .9s cubic-bezier(.2,.8,.2,1) both;">'
        f'<img src="data:image/png;base64,{crest_b64}" alt="LBS Olympics Championship" '
        'style="width:150px;height:150px;filter:drop-shadow(0 6px 24px rgba(217,154,43,.35));">'
        '</div>'
        '<div style="margin-top:26px;font-family:\'DM Mono\',monospace;font-size:13px;letter-spacing:.35em;'
        'color:#d99a2b;text-transform:uppercase;opacity:0;animation:lbsIntroFade .8s ease .5s forwards;">Welcome to</div>'
        '<div style="margin-top:10px;font-size:44px;font-weight:800;color:#fdf3e4;letter-spacing:-0.01em;'
        'text-align:center;opacity:0;animation:lbsIntroFade .9s ease .8s forwards;">LBS '
        '<span style="font-style:italic;font-family:\'Playfair Display\',serif;color:#e2984a;font-weight:600;">'
        'Olympics</span> 2026</div>'
        '<div style="margin-top:14px;font-family:\'DM Mono\',monospace;font-size:11px;letter-spacing:.2em;'
        'color:#8b93a6;text-transform:uppercase;opacity:0;animation:lbsIntroFade .8s ease 1.2s forwards;">'
        'Badminton &times; Pickleball Championship</div>'
        '<div style="margin-top:34px;width:64px;height:2px;'
        'background:linear-gradient(90deg,transparent,#d99a2b,transparent);'
        'opacity:0;animation:lbsIntroFade .8s ease 1.6s forwards;"></div>'
        '</div>'
    )
    return style + overlay


def main():
    if "intro_played" not in st.session_state:
        st.session_state["intro_played"] = True
        st.markdown(_intro_overlay_html(), unsafe_allow_html=True)

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
            f"""
            <div class="sb-logo-wrap">
                <div class="sb-crest"><img src="data:image/png;base64,{assets.CREST_LOGO_B64}" alt="LBS Olympics Championship"></div>
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