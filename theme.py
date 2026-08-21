"""
Visual theme: a "command center" aesthetic with two selectable palettes —

  · Dark  — near-black background, gold accent (the original look)
  · Light — warm white background, orange accent

Both share the same structure (translucent cards, thin gradient top border,
uppercase mono-spaced eyebrow labels, glossy sidebar) so switching modes
never changes layout, only color.

Honest limitation: this is CSS layered onto Streamlit's real components —
it does not rebuild them as custom components. Buttons/inputs/expanders
are still Streamlit elements underneath. A few native browser widgets
(e.g. the date-picker popover chrome) may not fully re-skin in light mode
since Streamlit's own base theme is fixed at startup via config.toml.
"""

import streamlit as st

MODE_KEY = "theme_mode"

# ─────────────────────────── palettes ───────────────────────────

DARK = {
    "bg": "#0a0e17",
    "bg_grad": "radial-gradient(circle at 20% 0%, #101a2e 0%, #0a0e17 55%)",
    "card": "#111725",
    "card_2": "#151d30",
    "border": "rgba(255,255,255,0.08)",
    "border_2": "rgba(255,255,255,0.14)",
    "accent": "#d99a2b",
    "accent_lt": "#f0c874",
    "accent_dk": "#a97a1e",
    "accent_ink": "#0d1425",
    "ink": "#e8eaf0",
    "muted": "#8b93a6",
    "sidebar_grad": "linear-gradient(165deg, #0d1425 0%, #131b30 55%, #0f1728 100%)",
    "sidebar_sheen": "rgba(255,255,255,.05)",
    "sidebar_text": "#b7c0d1",
    "sidebar_text_hi": "#ffffff",
    "sidebar_border": "rgba(255,255,255,0.08)",
    "input_bg": "#0a1120",
    "shadow": "0 10px 30px rgba(0,0,0,.45)",
    "pill_green_bg": "rgba(74,222,128,.14)", "pill_green_fg": "#7ee0a3",
    "pill_blue_bg": "rgba(96,150,255,.14)", "pill_blue_fg": "#8fb4ff",
    "pill_gray_bg": "rgba(255,255,255,.06)", "pill_gray_fg": "#8b93a6",
    "pill_orange_bg": "rgba(245,158,11,.14)", "pill_orange_fg": "#f5b94f",
}

LIGHT = {
    "bg": "#fffaf5",
    "bg_grad": "radial-gradient(circle at 20% 0%, #fff1e4 0%, #fffaf5 55%)",
    "card": "#ffffff",
    "card_2": "#fff6ee",
    "border": "rgba(30,20,10,0.09)",
    "border_2": "rgba(30,20,10,0.16)",
    "accent": "#ff6a13",
    "accent_lt": "#ff8c42",
    "accent_dk": "#d6570c",
    "accent_ink": "#ffffff",
    "ink": "#241708",
    "muted": "#6b5643",
    "sidebar_grad": "linear-gradient(165deg, #fff4e9 0%, #ffe4c9 55%, #ffd9b3 100%)",
    "sidebar_sheen": "rgba(255,255,255,.55)",
    "sidebar_text": "#5a4630",
    "sidebar_text_hi": "#211405",
    "sidebar_border": "rgba(30,20,10,0.08)",
    "input_bg": "#ffffff",
    "shadow": "0 10px 26px rgba(214,87,12,.12)",
    "pill_green_bg": "rgba(22,163,74,.12)", "pill_green_fg": "#0f6b31",
    "pill_blue_bg": "rgba(37,99,235,.12)", "pill_blue_fg": "#1642ad",
    "pill_gray_bg": "rgba(30,20,10,.07)", "pill_gray_fg": "#6b5643",
    "pill_orange_bg": "rgba(255,106,19,.16)", "pill_orange_fg": "#b8480a",
}


def get_mode() -> str:
    return st.session_state.get(MODE_KEY, "light")


def set_mode(mode: str):
    st.session_state[MODE_KEY] = mode


def toggle_widget():
    """A single circular icon button. Sized and styled entirely via CSS
    (targeting .st-key-theme_toggle_btn in inject_css) as a fixed 38px gold
    gradient circle matching the sidebar avatar chip's brand look, regardless
    of how wide its containing column is."""
    mode = get_mode()
    icon = "🌙" if mode == "light" else "☀️"
    next_mode = "dark" if mode == "light" else "light"
    if st.button(icon, key="theme_toggle_btn", help="Switch theme", use_container_width=True):
        set_mode(next_mode)
        st.rerun()


def inject_css():
    mode = get_mode()
    T = LIGHT if mode == "light" else DARK

    BG, BG_GRAD = T["bg"], T["bg_grad"]
    CARD, CARD_2 = T["card"], T["card_2"]
    BORDER, BORDER_2 = T["border"], T["border_2"]
    GOLD, GOLD_LT, GOLD_DK = T["accent"], T["accent_lt"], T["accent_dk"]
    ACCENT_INK = T["accent_ink"]
    INK, MUTED = T["ink"], T["muted"]
    SB_GRAD, SB_SHEEN = T["sidebar_grad"], T["sidebar_sheen"]
    SB_TEXT, SB_TEXT_HI, SB_BORDER = T["sidebar_text"], T["sidebar_text_hi"], T["sidebar_border"]
    INPUT_BG = T["input_bg"]
    SHADOW = T["shadow"]

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&family=Playfair+Display:ital,wght@1,600&display=swap');

        html {{ color-scheme: {mode}; }}
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
        .stApp {{ background: {BG_GRAD}; background-color: {BG}; transition: background .25s ease; }}
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stAppViewContainer"] {{ color: {INK}; }}
        p, span, div, label {{ color: {INK}; }}

        /* ── SIDEBAR: glossy gradient panel with a soft diagonal sheen ── */
        [data-testid="stSidebar"] {{
            background: {SB_GRAD};
            border-right: 1px solid {SB_BORDER};
            position: relative;
            box-shadow: inset -1px 0 0 rgba(255,255,255,.02), 4px 0 24px rgba(0,0,0,.12);
        }}
        [data-testid="stSidebar"]::before {{
            content: ''; position: absolute; inset: 0; pointer-events: none;
            background: linear-gradient(115deg, {SB_SHEEN} 0%, transparent 30%, transparent 70%, {SB_SHEEN} 100%);
            opacity: .5; mix-blend-mode: overlay;
        }}
        [data-testid="stSidebar"] * {{ color: {SB_TEXT} !important; }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            color: {SB_TEXT_HI} !important;
        }}
        [data-testid="stSidebar"] hr {{ border-color: {SB_BORDER}; }}

        [data-testid="stSidebar"] .stButton button {{
            border-radius: 9px; margin-bottom: 3px;
            box-shadow: none; transition: all .15s ease;
        }}
        [data-testid="stSidebar"] .stButton button[kind="secondary"] {{
            background: rgba(127,127,127,.08); color: {SB_TEXT} !important;
            border: 1px solid {SB_BORDER};
        }}
        [data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {{
            background: rgba(127,127,127,.16); color: {SB_TEXT_HI} !important;
            border-color: {GOLD};
        }}
        [data-testid="stSidebar"] .stButton button[kind="primary"] {{
            background: linear-gradient(135deg, {GOLD} 0%, {GOLD_DK} 100%) !important;
            color: {ACCENT_INK} !important; border: 1px solid {GOLD_DK};
            font-weight: 700; box-shadow: 0 3px 10px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.25);
        }}

        /* nav section label — a centered small-caps label flanked by two
           thin rules ("— VIEWER —") rather than a left label with one
           trailing rule, to match the more boutique, centered nav below. */
        .nav-label {{
            font-size: 9.5px; font-weight: 700; letter-spacing: .22em; color: {MUTED};
            text-transform: uppercase; font-family: 'DM Mono', monospace; margin: 24px 0 10px;
            display: flex; align-items: center; gap: 10px; justify-content: center;
        }}
        .nav-label::before, .nav-label::after {{
            content: ''; flex: 1; max-width: 26px; height: 1px; background: {SB_BORDER};
        }}

        /* sidebar nav — ghost text links, not boxed buttons: no fill, no
           border, generous uppercase letter-spacing, centered. The active
           page is marked only by gold text weight and a short underline
           rather than a solid block, which reads as a quiet members-list
           menu rather than a row of call-to-action buttons. Scoped to
           [class*="st-key-navbtn_"] (the stable per-key container class
           Streamlit adds) so the admin login/logout buttons — which still
           want normal button chrome — are left untouched. */
        [data-testid="stSidebar"] [class*="st-key-navbtn_"] button {{
            background: transparent !important; border: none !important; box-shadow: none !important;
            border-radius: 0 !important; margin-bottom: 0 !important;
            padding: 13px 8px !important; justify-content: center !important; text-align: center !important;
            font-size: 11.5px !important; font-weight: 500 !important;
            letter-spacing: .16em !important; text-transform: uppercase !important;
            transition: color .2s ease, letter-spacing .2s ease !important;
        }}
        [data-testid="stSidebar"] [class*="st-key-navbtn_"] button[kind="secondary"] {{
            color: {SB_TEXT} !important;
        }}
        [data-testid="stSidebar"] [class*="st-key-navbtn_"] button[kind="secondary"]:hover {{
            color: {SB_TEXT_HI} !important; letter-spacing: .2em !important;
        }}
        [data-testid="stSidebar"] [class*="st-key-navbtn_"] button[kind="primary"] {{
            background: transparent !important; border: none !important; box-shadow: none !important;
            color: {GOLD} !important; font-weight: 700 !important; letter-spacing: .2em !important;
            position: relative !important;
        }}
        [data-testid="stSidebar"] [class*="st-key-navbtn_"] button[kind="primary"]::after {{
            content: ''; position: absolute; left: 50%; bottom: 7px; transform: translateX(-50%);
            width: 26px; height: 2px; border-radius: 2px;
            background: linear-gradient(90deg, {GOLD}, {GOLD_DK});
        }}

        /* theme toggle — a circular gold/orange gradient icon button matching
           the sidebar avatar chip's brand gradient, targeted via the stable
           .st-key-<key> container class Streamlit adds for keyed widgets
           (confirmed via DOM inspection — .st-key-theme_toggle_btn wraps the
           button). Fixed circular size regardless of its narrow column width,
           so it reads as a deliberate icon toggle rather than a stray button. */
        .st-key-theme_toggle_btn div[data-testid="stButton"] {{
            display: flex; justify-content: center;
        }}
        .st-key-theme_toggle_btn button {{
            width: 38px !important; min-width: 38px !important; height: 38px !important;
            padding: 0 !important; border-radius: 50% !important;
            background: linear-gradient(135deg, {GOLD} 0%, {GOLD_DK} 100%) !important;
            border: 1px solid {GOLD_DK} !important;
            box-shadow: 0 2px 6px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.35) !important;
            display: flex !important; align-items: center; justify-content: center;
            transition: transform .15s ease, filter .15s ease;
        }}
        .st-key-theme_toggle_btn button p {{
            font-size: 15px !important; line-height: 1 !important; margin: 0 !important;
        }}
        .st-key-theme_toggle_btn button:hover {{
            filter: brightness(1.08); transform: scale(1.06);
            border-color: {GOLD_DK} !important;
        }}

        /* sidebar text input (admin password box etc) */
        [data-testid="stSidebar"] .stTextInput input {{
            background: {INPUT_BG}; color: {SB_TEXT_HI} !important; border: 1px solid {BORDER_2};
        }}
        [data-testid="stSidebar"] [data-testid="stExpander"] {{
            background: rgba(127,127,127,.06); border: 1px solid {SB_BORDER}; border-radius: 10px;
        }}

        /* ── MAIN BUTTONS ── */
        .stButton button[kind="primary"] {{
            background: linear-gradient(135deg, {GOLD} 0%, {GOLD_DK} 100%) !important;
            border-color: {GOLD_DK} !important; color: {ACCENT_INK} !important; font-weight: 700;
            box-shadow: 0 3px 10px rgba(0,0,0,.12), inset 0 1px 0 rgba(255,255,255,.25);
        }}
        .stButton button[kind="primary"]:hover {{ filter: brightness(1.06); }}
        .stButton button {{
            border-radius: 8px; font-weight: 600; background: {CARD}; color: {INK}; border: 1px solid {BORDER_2};
        }}
        .stButton button:hover {{ border-color: {GOLD}; color: {GOLD_DK}; }}

        /* ── INPUTS ── */
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"], .stMultiSelect [data-baseweb="select"] {{
            background: {CARD} !important; color: {INK} !important; border-color: {BORDER_2} !important;
        }}
        .stTextInput input::placeholder {{ color: {MUTED} !important; }}

        /* selectbox dropdown popover (Team A / Team B dept picker) — this
           overlay always renders with a fixed dark-navy background no
           matter which light/dark mode is toggled (confirmed via computed
           styles: rgb(10,14,23) either way), but the option text was
           following the page's global `p, span, div, label {{ color: INK }}`
           rule above, which flips to a dark brown in light mode — dark text
           on a dark box, unreadable. Pin this popover to fixed, always-legible
           colors instead of the theme variable so it's correct in both modes. */
        [data-testid="stSelectboxVirtualDropdown"] {{
            background: #0a0e17 !important; border: 1px solid rgba(255,255,255,.16) !important;
        }}
        [data-testid="stSelectboxVirtualDropdown"] [role="option"],
        [data-testid="stSelectboxVirtualDropdown"] [role="option"] * {{
            color: #e8eaf0 !important; background: transparent !important;
        }}
        [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
        [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {{
            background: rgba(217,154,43,.20) !important;
        }}
        [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover *,
        [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] * {{
            color: #f0c874 !important;
        }}

        /* st.dialog modal (the "Match scoring" popup) — same root cause as
           the dropdown above: the dialog's content card sits directly on
           the page <body>'s background, which Streamlit fixes to dark navy
           via config.toml's base="dark" independent of our light/dark
           toggle. Confirmed via computed styles: the card is rgb(10,14,23)
           regardless of mode, so in light mode all its text — headings,
           captions, category labels, score numbers — was inheriting the
           light-mode dark-brown ink from the global `p, span, div, label`
           rule and going nearly invisible on that dark card. Pin the card
           and its text to fixed, always-legible dark-theme colors.
           Buttons get their own explicit dark-styled rule (below, higher
           specificity so it wins) rather than being excluded from the text
           rule — an earlier version tried excluding them with :not() but
           still let their background fall through to the light-mode CARD
           (white), which combined with this rule's light text produced
           invisible white-on-white +/- buttons. */
        [data-testid="stDialog"] > div {{
            background: #0a0e17 !important;
        }}
        [data-testid="stDialog"] :is(p, span, div, label, h1, h2, h3, h4, input) {{
            color: #e8eaf0 !important;
        }}
        [data-testid="stDialog"] hr {{ border-color: rgba(255,255,255,.16) !important; }}
        [data-testid="stDialog"] .stButton button {{
            background: #171d2e !important; color: #e8eaf0 !important;
            border: 1px solid rgba(255,255,255,.18) !important;
        }}
        [data-testid="stDialog"] .stButton button * {{ color: inherit !important; }}
        [data-testid="stDialog"] .stButton button:hover {{
            border-color: {GOLD} !important; color: {GOLD_LT} !important;
        }}
        [data-testid="stDialog"] .stButton button:disabled {{ opacity: .4 !important; }}

        /* ── TABS ── */
        button[data-baseweb="tab"] {{ border-radius: 8px 8px 0 0; font-weight: 700; color: {MUTED}; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: {GOLD_DK} !important; border-bottom: 3px solid {GOLD} !important; }}

        /* ── EXPANDERS AS CARDS ── */
        [data-testid="stExpander"] {{
            border: 1px solid {BORDER}; border-radius: 12px; background: {CARD};
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 8px; overflow: hidden;
        }}
        [data-testid="stExpander"] summary {{ font-weight: 600; color: {INK}; }}
        [data-testid="stExpander"] summary:hover {{ color: {GOLD_DK}; }}

        /* container(border=True) cards */
        [data-testid="stVerticalBlockBorderWrapper"] > div {{
            background: {CARD}; border-color: {BORDER} !important; border-radius: 10px;
        }}

        /* ── METRICS ── */
        [data-testid="stMetric"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 12px 16px; }}
        [data-testid="stMetricValue"] {{ color: {INK}; }}
        [data-testid="stMetricLabel"] {{ color: {MUTED}; }}

        /* ── DATAFRAMES ── */
        [data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 10px; overflow: hidden; }}

        /* ── alerts ── */
        [data-testid="stAlert"] {{ background: {CARD}; border: 1px solid {BORDER}; }}

        /* ── breadcrumb / page header ── */
        .ph-crumb {{ font-size: 11px; font-weight: 800; letter-spacing: .12em; color: {GOLD_DK};
                     text-transform: uppercase; font-family:'DM Mono',monospace; margin-bottom: 6px; }}
        .ph-row {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:20px; flex-wrap:wrap; }}
        .ph-title {{ font-size: 30px; font-weight: 800; color: {INK}; margin: 0 0 8px; letter-spacing:-0.01em; }}
        .ph-title em {{ font-style: italic; font-family:'Playfair Display',serif; color: {GOLD_DK}; font-weight: 600; }}
        .ph-sub {{ font-size: 13px; color: {MUTED}; }}
        .ph-chip {{ display:inline-flex; align-items:center; gap:6px; padding:7px 14px; border-radius:9px; font-size:11px; font-weight:800;
                    white-space:nowrap; border:1px solid transparent; letter-spacing:.04em; text-transform:uppercase; font-family:'DM Mono',monospace; }}
        .ph-chip-gold {{ background:{GOLD}22; color:{GOLD_DK}; border-color:{GOLD}55; }}
        .ph-chip-navy {{ background:{CARD_2}; color:{INK}; border-color:{BORDER_2}; }}
        .ph-chip-green {{ background:{T["pill_green_bg"]}; color:{T["pill_green_fg"]}; border-color:{T["pill_green_fg"]}55; }}

        /* ── leaderboard rows ── */
        .lb-cat {{ font-size:11px; font-weight:800; letter-spacing:.08em; color:{GOLD_DK}; text-transform:uppercase; margin:18px 0 6px; font-family:'DM Mono',monospace; }}
        .lb-card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:12px; padding:4px 14px; }}
        .lb-row {{ display:grid; grid-template-columns: 26px 1fr 220px 64px 40px; gap:14px; align-items:center; padding:11px 0; border-bottom:1px solid {BORDER}; }}
        .lb-row:last-child {{ border-bottom:none; }}
        .lb-rank {{ color:{MUTED}; font-weight:800; font-family:'DM Mono',monospace; }}
        .lb-name {{ font-weight:700; color:{INK}; font-size:13.5px; }}
        .lb-sub {{ font-size:11px; color:{MUTED}; margin-top:1px; }}
        .lb-pill {{ display:inline-block; padding:3px 8px; border-radius:6px; font-size:10px; font-weight:800; margin-right:4px; font-family:'DM Mono',monospace;}}
        .lb-pill-green {{ background:{T["pill_green_bg"]}; color:{T["pill_green_fg"]}; }}
        .lb-pill-blue {{ background:{T["pill_blue_bg"]}; color:{T["pill_blue_fg"]}; }}
        .lb-pill-gray {{ background:{T["pill_gray_bg"]}; color:{T["pill_gray_fg"]}; }}
        .lb-pill-orange {{ background:{T["pill_orange_bg"]}; color:{T["pill_orange_fg"]}; }}
        .lb-bar-wrap {{ height:6px; border-radius:4px; background:{BORDER}; overflow:hidden; margin-top:6px; }}
        .lb-bar-fill {{ height:100%; border-radius:4px; }}
        .lb-avg {{ font-weight:800; text-align:right; font-family:'DM Mono',monospace; font-size:13px; }}
        .lb-tag {{ font-size:10px; color:{MUTED}; text-align:right; font-family:'DM Mono',monospace;}}

        /* ── command-center hero (home page) ── */
        .cc-eyebrow {{ font-size:10px; font-weight:800; letter-spacing:.12em; color:{GOLD_DK}; text-transform:uppercase; font-family:'DM Mono',monospace; margin-bottom:6px; }}
        .cc-hero-title {{ font-size:38px; font-weight:800; color:{INK}; margin:0 0 8px; letter-spacing:-0.01em; }}
        .cc-hero-title em {{ font-style:italic; font-family:'Playfair Display',serif; color:{GOLD_DK}; font-weight:600; }}
        .cc-hero-sub {{ font-size:14px; color:{MUTED}; max-width:640px; line-height:1.6; }}
        .cc-panel {{ background:{CARD}; border:1px solid {BORDER}; border-radius:14px; padding:26px 28px; margin:22px 0; box-shadow:{SHADOW}; }}
        .cc-badge {{ display:inline-flex; align-items:center; gap:6px; padding:5px 12px; border-radius:20px; font-size:10px;
                     font-weight:800; letter-spacing:.08em; text-transform:uppercase; background:{CARD_2};
                     border:1px solid {BORDER_2}; color:{MUTED}; font-family:'DM Mono',monospace; margin-bottom:14px; }}
        .cc-panel h2 {{ font-size:22px; font-weight:800; color:{INK}; margin:0 0 8px; }}
        .cc-panel h2 em {{ font-style:italic; font-family:'Playfair Display',serif; color:{GOLD_DK}; font-weight:600; }}
        .cc-panel p {{ font-size:13px; color:{MUTED}; max-width:680px; line-height:1.6; margin-bottom:14px; }}
        .cc-tag {{ display:inline-flex; align-items:center; gap:6px; padding:5px 10px; border-radius:7px; font-size:11px;
                   font-weight:600; margin:0 8px 0 0; background:{CARD_2}; border:1px solid {BORDER}; color:{INK}; }}
        .cc-modules-label {{ text-align:center; font-size:10px; font-weight:800; letter-spacing:.14em; color:{MUTED};
                              text-transform:uppercase; font-family:'DM Mono',monospace; margin:8px 0 16px; }}
        .cc-card {{
            position:relative; background:{CARD}; border:1px solid {BORDER}; border-radius:14px; padding:20px 20px 16px;
            height:100%; display:flex; flex-direction:column; transition: transform .15s ease, box-shadow .15s ease;
        }}
        .cc-card:hover {{ transform: translateY(-2px); box-shadow:{SHADOW}; }}
        .cc-card::before {{
            content:''; position:absolute; top:0; left:14px; right:14px; height:2px; border-radius:2px;
        }}
        .cc-card-gold::before {{ background:linear-gradient(90deg,{GOLD},transparent); }}
        .cc-card-teal::before {{ background:linear-gradient(90deg,#2dd4bf,transparent); }}
        .cc-card-blue::before {{ background:linear-gradient(90deg,#60a5fa,transparent); }}
        .cc-card-purple::before {{ background:linear-gradient(90deg,#a78bfa,transparent); }}
        .cc-card-icon {{ font-size:22px; margin-bottom:12px; }}
        .cc-card-step {{ font-size:10px; font-weight:800; letter-spacing:.1em; color:{GOLD_DK}; text-transform:uppercase; font-family:'DM Mono',monospace; margin-bottom:4px; }}
        .cc-card-title {{ font-size:17px; font-weight:800; color:{INK}; margin-bottom:8px; }}
        .cc-card-desc {{ font-size:12.5px; color:{MUTED}; line-height:1.6; flex-grow:1; margin-bottom:12px; }}
        .cc-card-tip {{ font-size:11px; color:{INK}; background:{CARD_2}; border:1px solid {BORDER};
                        border-radius:8px; padding:8px 10px; line-height:1.5; }}

        /* ── sidebar identity block + bottom user/toggle row (glossy avatar ring) ── */
        /* partner logo strip — sits above everything else in the sidebar,
           full-bleed to the sidebar's own padding, gently rounded so it
           reads as a deliberate banner rather than a stray image. */
        .sb-partner-logo {{ margin: -4px 0 18px 0; border-radius: 10px; overflow: hidden;
                             box-shadow: 0 2px 8px rgba(0,0,0,.18); }}
        .sb-partner-logo img {{ width: 100%; display: block; }}

        .sb-logo-wrap {{ padding:8px 0 22px 0; border-bottom:1px solid {SB_BORDER}; margin-bottom:16px; text-align:center; }}
        .sb-crest {{ display:flex; justify-content:center; margin-bottom:12px; filter:drop-shadow(0 3px 8px rgba(0,0,0,.25)); }}
        .sb-logo-title {{ font-weight:700; color:{SB_TEXT_HI}; font-size:21px; line-height:1.2; letter-spacing:.01em; }}
        .sb-logo-title .sb-logo-x {{ color:{GOLD}; font-weight:600; font-style:italic; font-family:'Playfair Display',serif; padding:0 3px; }}
        .sb-logo-sub {{ font-size:10px; color:{GOLD_DK}; letter-spacing:.28em; font-weight:700; margin-top:6px;
                        font-family:'DM Mono',monospace; text-transform:uppercase; }}
        .sb-bottom-divider {{ border:none; border-top:1px solid {SB_BORDER}; margin:18px 0 14px; }}
        .sb-user-row {{ display:flex; align-items:center; gap:9px; }}
        .sb-avatar {{
            width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
            font-weight:800; font-size:11px; color:{ACCENT_INK};
            background:linear-gradient(135deg,{GOLD},{GOLD_DK});
            box-shadow:0 2px 6px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.35);
            flex-shrink:0;
        }}
        .sb-user-name {{ font-size:12px; font-weight:700; color:{SB_TEXT_HI}; }}
        .sb-user-role {{ font-size:10px; color:{MUTED}; letter-spacing:.04em; }}
        </style>
        """,
        unsafe_allow_html=True,
    )