import datetime

import streamlit as st


def page_header(crumb, title, subtitle, right_label=None, right_kind="gold"):
    """Breadcrumb + title + subtitle on the left, a status chip + date on the right —
    styled to match the Home hero (gold DM Mono eyebrow, bold title with a Playfair
    italic accent on the part after an em dash) and the sidebar's brand mark, so
    every page in the app reads as the same product rather than a generic dashboard."""
    today = datetime.date.today().strftime("%A, %d %B %Y")
    chip_html = ""
    if right_label:
        chip_html = f'<span class="ph-chip ph-chip-{right_kind}">{right_label}</span>'
    if " — " in title:
        main, accent = title.split(" — ", 1)
        title_html = f'{main} — <em>{accent}</em>'
    else:
        title_html = title
    st.markdown(
        f"""
        <div class="ph-row">
          <div>
            <div class="ph-crumb">{crumb} · {today}</div>
            <div class="ph-title">{title_html}</div>
            <div class="ph-sub">{subtitle}</div>
          </div>
          <div>{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def leaderboard_card_start():
    st.markdown('<div class="lb-card">', unsafe_allow_html=True)


def leaderboard_card_end():
    st.markdown("</div>", unsafe_allow_html=True)


def leaderboard_category(label):
    st.markdown(f'<div class="lb-cat">{label}</div>', unsafe_allow_html=True)


def leaderboard_row(rank, name, subtitle, pills, pct, bar_color="#1a4fba", tag=""):
    """One leaderboard row: rank · name/subtitle · pills · progress bar · pct.
    pills: list of (text, kind) where kind in green/blue/gray/orange.
    pct: 0-100 float driving the progress bar width and the right-hand number.
    """
    pill_html = "".join(f'<span class="lb-pill lb-pill-{k}">{t}</span>' for t, k in pills)
    pct_clamped = max(0, min(100, pct))
    st.markdown(
        f"""
        <div class="lb-row">
          <div class="lb-rank">{rank}</div>
          <div>
            <div class="lb-name">{name}</div>
            <div class="lb-sub">{subtitle}</div>
          </div>
          <div>
            {pill_html}
            <div class="lb-bar-wrap"><div class="lb-bar-fill" style="width:{pct_clamped}%;background:{bar_color}"></div></div>
          </div>
          <div class="lb-avg" style="color:{bar_color}">{pct:.0f}%</div>
          <div class="lb-tag">{tag}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


CLEAR_OPTION = "— Clear / unassign —"


def dept_combobox(label, value, key, on_change, args, placeholder="Dept / Team"):
    """A dropdown that also accepts free-text (Streamlit's combobox mode).
    Pre-seeds session_state so a previously-saved custom (non-roster) name still
    shows correctly even though it isn't one of the dropdown options.

    Plain st.selectbox has no built-in way to clear a value once one is set —
    even with accept_new_options=True, there's no "x" to blank it back out
    (a long-standing Streamlit limitation, not something specific to this
    widget). CLEAR_OPTION is a sentinel entry pinned to the top of the list
    so admins have an explicit way to unassign a team; the on_change callback
    is responsible for translating it to None before saving (see
    pages_admin._bd_team_change).
    """
    import data
    if key not in st.session_state:
        st.session_state[key] = value or None
    options = [CLEAR_OPTION] + data.all_dept_names()
    return st.selectbox(
        label, options=options, key=key, accept_new_options=True,
        placeholder=placeholder, on_change=on_change, args=args, label_visibility="collapsed",
    )


def status_badge(text, kind="ok"):
    """Note the `!important` on background/color: this badge is also used
    inside the st.dialog scoring modal, which pins ALL text inside it to a
    fixed light color (via a `!important` CSS rule in theme.py) so the
    dialog's fixed-dark card stays legible regardless of light/dark mode.
    Without `!important` here, that page-wide rule would win over this
    inline style and turn the badge into near-white text on a near-white
    background — which is exactly what made the "Winner: ..." pill
    unreadable in light mode."""
    colors = {
        "ok": ("#f0fdf4", "#15803d", "#bbf7d0"),
        "warn": ("#fffbeb", "#b45309", "#fde68a"),
        "err": ("#fef2f2", "#b91c1c", "#fecaca"),
        "neutral": ("#f4f2ed", "#6b6960", "#dbd8d0"),
    }
    bg, fg, bd = colors.get(kind, colors["neutral"])
    st.markdown(
        f"<span style='display:inline-block;padding:2px 9px;border-radius:5px;font-size:12px;"
        f"font-weight:600;font-family:monospace;background:{bg} !important;color:{fg} !important;"
        f"border:1px solid {bd}'>{text}</span>",
        unsafe_allow_html=True,
    )


def score_row(label, g, on_minus, on_plus, on_finish, on_reopen, pts_target, key_prefix,
              editable=True, on_set=None, t1_name=None, t2_name=None):
    """Render one game's score row.

    Layout note (mobile fix): team name + score are grouped into ONE block
    per team — a caption, then that team's -/number/+ controls right below
    it — instead of the old single wide row of 9 skinny columns (label, -,
    score, +, "vs", -, score, +, finish). On a phone, Streamlit stacks
    columns that don't fit side-by-side; with the old layout that meant an
    umpire scrolling saw a bare column of numbers and +/- buttons with the
    "vs" separator and team identity scrolled out of view. Grouping keeps
    "<team name>  [-] 15 [+]" together as one unit no matter how narrow the
    screen is or how the columns reflow.

    on_minus / on_plus: (callable, callable) no-arg callbacks for the -1/+1
    buttons (bound via functools.partial), same as before.
    on_set: optional (callable, callable) callbacks for typing a score
    directly into a number box instead of tapping +/- repeatedly. Each is
    called as callback(number_input_key) — i.e. bind the fixed args with
    functools.partial and the session_state key of the changed widget is
    appended automatically by Streamlit's `args=`.
    t1_name / t2_name: display names shown above each team's score so it's
    always clear whose points are whose, even once columns stack.
    """
    locked = g["finished"]
    name1 = t1_name or "Team A"
    name2 = t2_name or "Team B"

    top_l, top_r = st.columns([3, 1])
    top_l.markdown(f"**{label}**")
    if editable:
        can_finish = (not locked) and (g["p1"] != g["p2"]) and (g["p1"] >= pts_target or g["p2"] >= pts_target)
        if locked:
            top_r.button("↺ Reopen", key=f"{key_prefix}_reopen", on_click=on_reopen, use_container_width=True)
        else:
            top_r.button("Finish ✓", key=f"{key_prefix}_finish", on_click=on_finish,
                          disabled=not can_finish, use_container_width=True)

    c1, c2 = st.columns(2)
    for col, who, name, val, minus_cb, plus_cb, set_cb in (
        (c1, 1, name1, g["p1"], on_minus[0], on_plus[0], on_set[0] if on_set else None),
        (c2, 2, name2, g["p2"], on_minus[1], on_plus[1], on_set[1] if on_set else None),
    ):
        with col:
            st.markdown(
                f"<div style='font-size:12px;font-weight:700;opacity:.8;margin-bottom:2px;"
                f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{name}</div>",
                unsafe_allow_html=True,
            )
            if editable and not locked:
                b1, b2, b3 = st.columns([1, 1.6, 1])
                b1.button("–", key=f"{key_prefix}_m{who}", on_click=minus_cb, use_container_width=True)
                if set_cb is not None:
                    # Key includes the current value so the widget always
                    # refreshes to match state after +/- taps too — Streamlit
                    # otherwise keeps showing whatever the user last typed.
                    num_key = f"{key_prefix}_num{who}_{val}"
                    b2.number_input(
                        name, value=val, min_value=0, step=1, key=num_key,
                        on_change=set_cb, args=(num_key,), label_visibility="collapsed",
                    )
                else:
                    b2.markdown(
                        f"<div style='text-align:center;font-family:monospace;font-size:20px;"
                        f"font-weight:800'>{val}</div>",
                        unsafe_allow_html=True,
                    )
                b3.button("+", key=f"{key_prefix}_p{who}", on_click=plus_cb, use_container_width=True)
            else:
                st.markdown(
                    f"<div style='text-align:center;font-family:monospace;font-size:20px;"
                    f"font-weight:800'>{val}</div>",
                    unsafe_allow_html=True,
                )


def team_vs_line(t1, t2, winner=None):
    n1 = t1 or "TBD"
    n2 = t2 or "TBD"
    b1 = "**" if winner == 1 else ""
    b2 = "**" if winner == 2 else ""
    st.markdown(f"{b1}{n1}{b1} &nbsp;vs&nbsp; {b2}{n2}{b2}", unsafe_allow_html=True)
