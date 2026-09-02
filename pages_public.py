import html as _html

import streamlit as st
import streamlit.components.v1 as components

import bracket_svg
import logic
import state
import ui


def _truncate_name(name, maxlen=22):
    """Hard-cap a team/pair name's rendered length with an ellipsis.

    The monitor tiles size themselves responsively (CSS grid, flex), which
    is necessary for the layout to adapt from a single full-width spotlight
    card down to a 4-5-per-row mobile grid. But a raw HTML <table> with
    `white-space:nowrap` name cells (needed so scores don't wrap awkwardly)
    will happily force the whole table WIDER than its card to fit a long
    department name in full, and CSS-only ellipsis truncation on table
    cells needs `table-layout:fixed` with hand-tuned column widths — fragile
    to get right across every card size these tiles render at. Truncating
    the string itself in Python is a hard guarantee: the table can never be
    forced wider than intended by name length, at any screen size, without
    depending on any particular CSS layout mode holding up.
    Escaped via html.escape since these strings go straight into raw HTML."""
    name = name or ""
    if len(name) > maxlen:
        name = name[: maxlen - 1].rstrip() + "…"
    return _html.escape(name)


def render_overview():
    st.markdown(
        """
        <div class="cc-eyebrow">Tournament Command Center · Internal Use Only</div>
        <div class="cc-hero-title">LBS × MGB <em>Sports Tournament</em></div>
        <div class="cc-hero-sub">Live badminton and pickleball draw, scoring, and standings for the LBS × MGB
        interdepartmental sports day. Viewers get read-only monitors; admins get one login for everything.</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    hc1, hc2, _ = st.columns([1.1, 1.1, 3])
    with hc1:
        if st.button("🏸  View Badminton", type="primary", use_container_width=True):
            st.session_state["current_page"] = "Badminton"
            st.rerun()
    with hc2:
        if st.button("🏓  View Pickleball", use_container_width=True):
            st.session_state["current_page"] = "Pickleball"
            st.rerun()

    bd = state.load_bd()
    pk = state.load_pk()
    bd_champ = logic.bd_champion(bd)
    pk_champ = logic.pk_champion(pk)
    bd_live = len(_bd_live_ties(bd))
    bd_done = sum(1 for t in bd["ties"].values() if t["winner"])
    pk_done = sum(1 for t in pk["ko"].values() if t["winner"])

    tags = (
        f'<span class="cc-tag">✓ Badminton: {"🏆 " + bd_champ if bd_champ else f"{bd_live} live · {bd_done} ties done"}</span>'
        f'<span class="cc-tag">✓ Pickleball: {"🏆 " + pk_champ if pk_champ else f"{pk_done} knockout matches done"}</span>'
        f'<span class="cc-tag">✓ Scores save instantly — everyone sees live updates on refresh</span>'
    )
    st.markdown(
        f"""
        <div class="cc-panel">
          <span class="cc-badge">● System Overview — Start Here</span>
          <h2>Two live tournaments, tracked in <em>real time</em></h2>
          <p>Every score entered by an admin saves straight to the tournament database. Viewers watching
          the monitor or bracket view see it on their next refresh — no manual syncing, no separate export.</p>
          {tags}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cc-modules-label">Where to go</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    modules = [
        (m1, "cc-card-gold", "🏸", "View 01", "Badminton", "Live monitor and bracket view for the 16-department double-elimination draw.",
         "💡 Toggle between the connected-line bracket and the dark live monitor.", "Badminton"),
        (m2, "cc-card-teal", "🏓", "View 02", "Pickleball", "Group-stage standings and knockout bracket for all 22 pairs across 4 groups.",
         "💡 Top 4 per group advance automatically once standings are updated.", "Pickleball"),
        (m3, "cc-card-purple", "🔐", "View 03", "Admin Login", "Score entry and team setup — behind the shared admin password.",
         "💡 Unlock admin mode from the sidebar to see this.", None),
    ]
    for col, cls, icon, step, title, desc, tip, target in modules:
        with col:
            st.markdown(
                f"""
                <div class="cc-card {cls}">
                  <div class="cc-card-icon">{icon}</div>
                  <div class="cc-card-step">{step}</div>
                  <div class="cc-card-title">{title}</div>
                  <div class="cc-card-desc">{desc}</div>
                  <div class="cc-card-tip">{tip}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if target:
                if st.button(f"Go to {title}", key=f"cc_go_{title}", use_container_width=True):
                    st.session_state["current_page"] = target
                    st.rerun()
            else:
                st.caption("Use the 🔒 Admin login box in the sidebar")


def _bd_live_ties(bd):
    live = []
    for tid, tie in bd["ties"].items():
        if tie["winner"]:
            continue
        if not tie["t1"] or not tie["t2"]:
            continue
        started = any(g["finished"] for c in tie["cats"] for g in c["games"])
        if started:
            live.append((tid, tie))
    return live


def _bd_tie_status(tie):
    if tie["winner"] is not None:
        return "done"
    if not tie["t1"] or not tie["t2"]:
        return "pending"
    active = any(g["finished"] or g["p1"] > 0 or g["p2"] > 0 for c in tie["cats"] for g in c["games"])
    return "live" if active else "scheduled"


def _bd_score_table_html(tie, current_ci, compact=True, show_names=False, show_tally=False):
    """Real scoreboard table: one column-group per category (colspan = number
    of games played/live in that category), one row per team, each cell is
    that team's own point total for that game — e.g. MD1 becomes two columns
    (Game 1, Game 2) with HR's row reading 18, 4 and BI's row reading 21, 21,
    instead of a single cramped '18-21 · 4-21' string.

    When show_names/show_tally are set, the team name and the running tie
    tally (category wins) become the first/last column of this *same* table
    — so the name, every per-game score, and the tally sit in one row and
    line up automatically via normal table layout, rather than being three
    separately-positioned flex boxes that have to be manually kept in sync."""
    cats_info = []
    for ci in range(5):
        cat = tie["cats"][ci]
        started = any(g["finished"] or g["p1"] > 0 or g["p2"] > 0 for g in cat["games"])
        if ci == 4 and not (tie["tbNeeded"] or started):
            continue  # hide the tie-breaker column unless it's actually in play
        vis = logic.bd_visible_games(cat["games"])
        games = [cat["games"][gi] for gi in vis]
        winner = logic.bd_cat_winner(cat)
        cats_info.append({"ci": ci, "abbr": logic.BD_CAT_ABBR[ci], "games": games, "winner": winner})
    if not cats_info:
        return ""

    hdr_size = "8.5px" if compact else "13px"
    cell_size = "10.5px" if compact else "20px"
    cell_pad = "3px 5px" if compact else "10px 16px"
    name_size = "11px" if compact else "16px"

    t1, t2 = tie["t1"] or "TBD", tie["t2"] or "TBD"
    t1_color = "#4ade80" if tie["winner"] == 1 else ("#6b6960" if tie["winner"] == 2 else "#e8e6df")
    t2_color = "#60a5fa" if tie["winner"] == 2 else ("#6b6960" if tie["winner"] == 1 else "#e8e6df")

    name_hdr = f'<th style="padding:{cell_pad}"></th>' if show_names else ""
    hdr_cells = name_hdr
    for c in cats_info:
        n = max(len(c["games"]), 1)
        if c["winner"] == 1:
            color = "#4ade80"
        elif c["winner"] == 2:
            color = "#60a5fa"
        elif c["ci"] == current_ci:
            color = "#f59e0b"
        else:
            color = "#8a877d"
        hdr_cells += (
            f'<th colspan="{n}" style="font-size:{hdr_size};font-family:\'DM Mono\',monospace;color:{color};'
            f'font-weight:800;text-transform:uppercase;letter-spacing:.04em;padding:{cell_pad};'
            f'border-bottom:1px solid #2a2a24;border-left:1px solid #2a2a24;text-align:center">{c["abbr"]}</th>'
        )
    tally_hdr = (
        f'<th style="font-size:{hdr_size};font-family:\'DM Mono\',monospace;color:#d99a2b;font-weight:800;'
        f'text-transform:uppercase;letter-spacing:.04em;padding:{cell_pad};border-bottom:1px solid #2a2a24;'
        f'border-left:1px solid #2a2a24;text-align:center;white-space:nowrap">Total Wins</th>'
    ) if show_tally else ""
    hdr_cells += tally_hdr

    def team_row(slot, name, color, weight, tally):
        cells = ""
        if show_names:
            cells += (
                f'<td class="bd-name-cell" style="padding:{cell_pad};font-size:{name_size};font-weight:800;color:{color};'
                f'white-space:nowrap;text-align:left">{_truncate_name(name)}</td>'
            )
        for c in cats_info:
            if not c["games"]:
                cells += (
                    f'<td style="padding:{cell_pad};text-align:center;color:#4a4a44;border-left:1px solid #2a2a24;'
                    f'font-family:\'DM Mono\',monospace;font-size:{cell_size}">–</td>'
                )
                continue
            for gi, g in enumerate(c["games"]):
                border = "border-left:1px solid #2a2a24;" if gi == 0 else ""
                val = g["p1"] if slot == 1 else g["p2"]
                cells += (
                    f'<td style="padding:{cell_pad};text-align:center;color:{color};font-weight:{weight};'
                    f'font-family:\'DM Mono\',monospace;font-size:{cell_size};{border}">{val}</td>'
                )
        if show_tally:
            cells += (
                f'<td class="bd-tally-cell" style="padding:{cell_pad};text-align:center;color:{color};font-weight:800;'
                f'font-family:\'DM Mono\',monospace;font-size:{cell_size};border-left:1px solid #2a2a24">{tally}</td>'
            )
        return cells

    row1 = team_row(1, t1, t1_color, "800" if tie["winner"] == 1 else "600", tie["w1"] or 0)
    row2 = team_row(2, t2, t2_color, "800" if tie["winner"] == 2 else "600", tie["w2"] or 0)

    return f"""
    <table style="border-collapse:collapse;width:{"100%" if show_names else "auto"};margin-top:8px">
      <thead><tr>{hdr_cells}</tr></thead>
      <tbody>
        <tr>{row1}</tr>
        <tr>{row2}</tr>
      </tbody>
    </table>
    """


def _bd_mon_tile_html(tie, big=False):
    status = _bd_tie_status(tie)
    t1, t2 = _truncate_name(tie["t1"] or "TBD"), _truncate_name(tie["t2"] or "TBD")
    w1, w2 = tie["w1"] or 0, tie["w2"] or 0
    border = "1px solid #f59e0b" if status == "live" else ("1px solid #2a2a24" if status != "done" else "1px solid #2f4f3a")
    badge = ('<span style="background:#f59e0b;color:#111;font-size:9px;font-weight:800;padding:2px 6px;'
             'border-radius:3px;letter-spacing:.03em">● LIVE</span>') if status == "live" else (
             '<span style="color:#4ade80;font-size:10px;font-weight:700">✓ FINAL</span>' if status == "done" else "")
    t1_color = "#4ade80" if (status == "done" and tie["winner"] == 1) else ("#6b6960" if (status == "done" and tie["winner"] == 2) else "#e8e6df")
    t2_color = "#4ade80" if (status == "done" and tie["winner"] == 2) else ("#6b6960" if (status == "done" and tie["winner"] == 1) else "#e8e6df")
    t1_weight = "700" if not (status == "done" and tie["winner"] == 2) else "400"
    t2_weight = "700" if not (status == "done" and tie["winner"] == 1) else "400"
    pad = "14px" if big else "10px"
    name_size = "16px" if big else "13px"
    score_size = "22px" if big else "17px"

    activity_line = ""
    activity_banner = ""
    current_ci = None
    if status == "live":
        act = logic.bd_current_activity(tie)
        if act:
            current_ci = act["ci"]
            act_size = "13px" if big else "11px"
            pt_size = "16px" if big else "13px"
            activity_line = f"""
            <div style="margin-top:8px;padding-top:8px;border-top:1px solid #2a2a24;font-size:{act_size};
                        color:#c9c6bd;font-family:'DM Mono',monospace;display:flex;justify-content:space-between;align-items:center">
              <span>{act["cat_name"]} · Game {act["game_no"]}</span>
              <span style="font-weight:800;font-size:{pt_size};color:#f5c518">{act["p1"]}–{act["p2"]}</span>
            </div>
            """
            # Prominent "Currently Playing" banner for the spotlight tile —
            # a dedicated block (not just a footer line) so the category in
            # play and its live score read clearly at a glance, and scales
            # further via the .bd-activity-* classes in jumbotron mode.
            activity_banner = f"""
            <div class="bd-activity" style="margin-top:14px;padding:12px 18px;border-radius:8px;
                        background:linear-gradient(90deg,rgba(245,158,11,.14),rgba(245,158,11,.03));
                        border:1px solid rgba(245,158,11,.35);display:flex;justify-content:space-between;
                        align-items:center;gap:14px">
              <div>
                <div class="bd-activity-label" style="font-size:10px;color:#f5c518;font-weight:800;
                            text-transform:uppercase;letter-spacing:.08em;font-family:'DM Mono',monospace">
                  ● Currently Playing</div>
                <div class="bd-activity-cat" style="font-size:18px;color:#fff;font-weight:800;margin-top:3px">
                  {act["cat_name"]}
                  <span style="color:#8a877d;font-weight:600;font-size:13px">&nbsp;·&nbsp;Game {act["game_no"]}</span>
                </div>
              </div>
              <div class="bd-activity-score" style="font-family:'DM Mono',monospace;font-weight:800;
                          font-size:32px;color:#f5c518;white-space:nowrap;flex-shrink:0">{act["p1"]}–{act["p2"]}</div>
            </div>
            """
        elif tie["tbNeeded"]:
            current_ci = 4
            act_size = "13px" if big else "11px"
            activity_line = f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #2a2a24;font-size:{act_size};color:#f59e0b">Tie-Breaker decides it</div>'
            activity_banner = (
                '<div class="bd-activity" style="margin-top:14px;padding:12px 18px;border-radius:8px;'
                'background:rgba(245,158,11,.10);border:1px solid rgba(245,158,11,.35);color:#f59e0b;'
                'font-weight:800;font-size:15px;text-align:center;font-family:\'DM Mono\',monospace;'
                'text-transform:uppercase;letter-spacing:.04em">⚡ Tie-Breaker decides it</div>'
            )

    cat_strip = _bd_score_table_html(tie, current_ci, compact=True) if status in ("live", "done") else ""

    header_and_teams = f"""
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-size:9px;color:#8a877d;font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.06em">
          {logic.BD_ROUND_INFO[tie["id"].split("_")[0]]["label"]}</span>
        {badge}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:{name_size};font-weight:{t1_weight};color:{t1_color}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:8px">{t1}</span>
        <span style="font-family:'DM Mono',monospace;font-size:{score_size};font-weight:800;flex-shrink:0">{w1}</span>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:{name_size};font-weight:{t2_weight};color:{t2_color}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:8px">{t2}</span>
        <span style="font-family:'DM Mono',monospace;font-size:{score_size};font-weight:800;flex-shrink:0">{w2}</span>
      </div>
      {activity_line}
    """

    if big:
        # Spotlight layout: one real table for the whole scoreboard — team
        # name is the table's first column, per-game scores are the middle
        # columns, category tally is the last column. Same rows, so names
        # and numbers line up by construction instead of three separately
        # positioned boxes that had to be kept in sync by hand.
        header_row = f"""
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-size:10px;color:#8a877d;font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.06em">
              {logic.BD_ROUND_INFO[tie["id"].split("_")[0]]["label"]}</span>
            {badge}
          </div>
        """
        cat_table = _bd_score_table_html(tie, current_ci, compact=False, show_names=True, show_tally=True)
        return f"""
        <div style="background:#1c1c19;border:{border};border-radius:10px;padding:{pad};min-width:200px;max-width:100%;overflow-x:auto" class="mon-tile-card">
          {header_row}
          {cat_table}
          {activity_banner}
        </div>
        """

    return f"""
    <div style="background:#1c1c19;border:{border};border-radius:10px;padding:{pad};min-width:200px;max-width:100%;overflow-x:auto" class="mon-tile-card">
      {header_and_teams}
      {cat_strip}
    </div>
    """


def _render_bd_monitor_html(bd, rounds):
    live = [t for t in bd["ties"].values() if _bd_tie_status(t) == "live" and t["id"].split("_")[0] in rounds]
    if live:
        # Only spotlight-treat a SINGLE live tie as a full-width "big" jumbo
        # card (wide table, huge fonts) — that layout assumes one card gets
        # the whole row. With several ties live at once (common once WB and
        # LB rounds run in parallel), forcing every one of them into that
        # same wide layout then squeezing them into a flex row was the bug:
        # each card shrank to ~260px, far narrower than the big table needs,
        # so team names overflowed the card's edge and most of the score
        # columns were clipped off-screen — exactly the "names not in the
        # box" / "only shows one game" symptoms. With 2+ simultaneous live
        # ties, fall back to the compact tile (smaller fonts, same full
        # per-game breakdown) sized for a multi-column grid instead.
        # CSS grid with auto-fit/minmax also replaces the old flex+min-width
        # row: grid computes column count from the ACTUAL rendered
        # container width, so it can't produce the same overflow-past-the-
        # viewport squeeze flexbox did on narrow/mobile widths.
        if len(live) == 1:
            tiles = f'<div style="width:100%;max-width:520px">{_bd_mon_tile_html(live[0], big=True)}</div>'
            live_section = f'<div style="margin-bottom:22px">{tiles}</div>'
        else:
            tiles = "".join(_bd_mon_tile_html(t) for t in live)
            live_section = (
                '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));'
                f'gap:12px;margin-bottom:22px">{tiles}</div>'
            )
    else:
        live_section = '<div style="color:#8a877d;font-size:13px;margin-bottom:22px">No matches currently in progress.</div>'

    sections = ""
    for r in logic.ALL_BD_ROUNDS:
        if r not in rounds:
            continue
        ties = [t for tid, t in bd["ties"].items() if tid.split("_")[0] == r]
        if not ties:
            continue
        # CSS grid instead of a fixed 230px flex tile: badminton's compact
        # score table can need up to 5 category columns (vs. pickleball's
        # max 3 game columns), so a hard 230px was routinely too narrow and
        # fell back to the horizontal-scrollbar safety net on nearly every
        # card — which looked cluttered/inconsistent next to pickleball's
        # tiles, which almost never needed to scroll. minmax(260px,...)
        # gives the wider table breathing room; auto-fit still collapses to
        # a single column on mobile, same as the "Live Now" grid above.
        tiles = "".join(_bd_mon_tile_html(t) for t in ties)
        sections += f"""
        <div style="margin-bottom:20px">
          <div style="font-size:11px;color:#8a877d;text-transform:uppercase;letter-spacing:.08em;
                      font-family:'DM Mono',monospace;margin-bottom:10px">{logic.BD_ROUND_INFO[r]["label"]}</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px">{tiles}</div>
        </div>
        """

    # The fullscreen button uses the standard Fullscreen API on the #bd-live-now
    # element. A JS listener toggles a `bd-fs` class on that element (in
    # addition to the native :fullscreen pseudo-class) purely so the CSS below
    # can use plain, high-specificity class selectors with !important to
    # override the inline per-cell font-sizes set by Python — the jumbotron
    # look needs everything bigger and centered, which inline styles alone
    # can't be overridden by without !important.
    return f"""
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <div style="color-scheme:dark;background:#111110;padding:20px;border-radius:12px;font-family:'Inter',sans-serif;min-height:850px">
      <div id="bd-live-now">
        <div class="bd-fs-topbar" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:6px">
          <div style="display:flex;align-items:center;gap:8px">
            <span style="width:8px;height:8px;border-radius:50%;background:#f43f5e;display:inline-block"></span>
            <span style="color:#e8e6df;font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">Live Now</span>
            <span class="bd-fs-brand" style="display:none;color:#8a877d;font-size:12px;font-family:'DM Mono',monospace;
                        letter-spacing:.1em;text-transform:uppercase;margin-left:10px">LBS × MGB — Sports Tournament</span>
          </div>
          <div style="display:flex;gap:14px;font-size:9.5px;color:#8a877d;font-family:'DM Mono',monospace;align-items:center">
            <span class="bd-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#4ade80;margin-right:4px"></span>Team A won cat.</span>
            <span class="bd-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#60a5fa;margin-right:4px"></span>Team B won cat.</span>
            <span class="bd-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#f59e0b;margin-right:4px"></span>Live now</span>
            <span class="bd-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#3a3a34;margin-right:4px"></span>Not started</span>
            <button id="bd-fs-btn" onclick="bdToggleFullscreen()" style="background:rgba(255,255,255,.06);
                    color:#e8e6df;border:1px solid rgba(255,255,255,.16);border-radius:6px;padding:5px 10px;
                    font-size:10px;font-weight:700;font-family:'DM Mono',monospace;cursor:pointer;letter-spacing:.04em">
              ⛶ Full Screen
            </button>
          </div>
        </div>
        <div class="bd-fs-hero" style="display:none;text-align:center;margin:6px 0 30px">
          <div style="font-size:13px;font-weight:800;letter-spacing:.16em;color:#8a877d;text-transform:uppercase;
                      font-family:'DM Mono',monospace;margin-bottom:10px">LBS × MGB Sports Tournament</div>
          <div style="font-size:46px;font-weight:800;color:#fff;letter-spacing:-0.01em;line-height:1.1">
            🏸 LBS Olympics <span style="color:#d99a2b">Badminton!</span>
          </div>
          <div id="bd-fs-datetime" style="margin-top:12px;font-size:17px;color:#a8a59e;font-family:'DM Mono',monospace;
                      letter-spacing:.05em"></div>
        </div>
        <div class="bd-fs-stage">
          {live_section}
        </div>
      </div>
      <div style="color:#8a877d;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
                  font-family:'DM Mono',monospace;margin-bottom:12px">Tournament Overview</div>
      {sections}
    </div>
    <script>
      function bdSetFsUi(active) {{
        var el = document.getElementById('bd-live-now');
        var btn = document.getElementById('bd-fs-btn');
        if (el) el.classList.toggle('bd-fs', active);
        if (btn) btn.innerHTML = active ? '⛶ Exit Full Screen' : '⛶ Full Screen';
        var brand = document.querySelectorAll('.bd-fs-brand');
        for (var i = 0; i < brand.length; i++) brand[i].style.display = active ? 'inline' : 'none';
        var hero = document.querySelector('.bd-fs-hero');
        if (hero) hero.style.display = active ? 'block' : 'none';
      }}
      function bdToggleFullscreen() {{
        var el = document.getElementById('bd-live-now');
        if (!document.fullscreenElement && !document.webkitFullscreenElement) {{
          if (el.requestFullscreen) {{ el.requestFullscreen(); }}
          else if (el.webkitRequestFullscreen) {{ el.webkitRequestFullscreen(); }}
        }} else {{
          if (document.exitFullscreen) {{ document.exitFullscreen(); }}
          else if (document.webkitExitFullscreen) {{ document.webkitExitFullscreen(); }}
        }}
      }}
      document.addEventListener('fullscreenchange', function() {{
        bdSetFsUi(!!document.fullscreenElement);
      }});
      document.addEventListener('webkitfullscreenchange', function() {{
        bdSetFsUi(!!document.webkitFullscreenElement);
      }});
      setInterval(function() {{
        var dt = document.getElementById('bd-fs-datetime');
        if (dt && dt.closest('#bd-live-now').classList.contains('bd-fs')) {{
          var now = new Date();
          var dateStr = now.toLocaleDateString([], {{weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}});
          var timeStr = now.toLocaleTimeString([], {{hour: '2-digit', minute: '2-digit', second: '2-digit'}});
          dt.textContent = dateStr + '  ·  ' + timeStr;
        }}
      }}, 1000);
    </script>
    <style>
      /* Jumbotron mode: vertically centered, warm gradient backdrop, and
         everything scaled up via !important since the per-cell sizes were
         set inline in Python for the normal (embedded) monitor view. */
      #bd-live-now.bd-fs {{
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        min-height: 100vh !important;
        padding: 48px 64px !important;
        background: radial-gradient(circle at 50% 10%, #1c1a14 0%, #0a0a08 65%) !important;
        box-sizing: border-box !important;
      }}
      #bd-live-now.bd-fs .bd-fs-topbar {{ margin-bottom: 0 !important; }}
      #bd-live-now.bd-fs .bd-fs-legend {{ font-size: 13px !important; }}
      #bd-live-now.bd-fs #bd-fs-btn {{ font-size: 13px !important; padding: 8px 16px !important; }}
      #bd-live-now.bd-fs .bd-fs-stage {{ display: flex !important; flex-direction: column !important; gap: 22px !important; }}
      #bd-live-now.bd-fs .bd-fs-stage > div {{ margin-bottom: 0 !important; }}
      #bd-live-now.bd-fs table {{ width: 100% !important; }}
      #bd-live-now.bd-fs table th {{
        font-size: 22px !important; padding: 16px 26px !important;
      }}
      #bd-live-now.bd-fs table td {{
        font-size: 34px !important; padding: 18px 26px !important;
      }}
      #bd-live-now.bd-fs table td.bd-name-cell {{ font-size: 40px !important; }}
      #bd-live-now.bd-fs table td.bd-tally-cell {{ font-size: 40px !important; color: #d99a2b !important; }}
      #bd-live-now.bd-fs .bd-activity {{ padding: 22px 32px !important; margin-top: 24px !important; border-radius: 12px !important; }}
      #bd-live-now.bd-fs .bd-activity-label {{ font-size: 15px !important; }}
      #bd-live-now.bd-fs .bd-activity-cat {{ font-size: 30px !important; }}
      #bd-live-now.bd-fs .bd-activity-cat span {{ font-size: 20px !important; }}
      #bd-live-now.bd-fs .bd-activity-score {{ font-size: 56px !important; }}
      #bd-live-now.bd-fs [style*="min-width:200px"] {{
        border-radius: 18px !important; padding: 32px 36px !important;
        box-shadow: 0 20px 60px rgba(0,0,0,.55) !important;
      }}
      #bd-live-now:fullscreen {{ background: #0a0a08; }}
      #bd-live-now:-webkit-full-screen {{ background: #0a0a08; }}
      /* Themed scrollbar fallback: the compact category table only needs
         to scroll in rare edge cases now (5 categories + an in-progress
         tie-breaker, all at once), but when it does, a slim dark scrollbar
         blends into the card instead of a jarring default OS scrollbar. */
      .mon-tile-card {{ scrollbar-width: thin; scrollbar-color: #3a3a34 transparent; }}
      .mon-tile-card::-webkit-scrollbar {{ height: 4px; }}
      .mon-tile-card::-webkit-scrollbar-track {{ background: transparent; }}
      .mon-tile-card::-webkit-scrollbar-thumb {{ background: #3a3a34; border-radius: 4px; }}
    </style>
    """


def render_badminton_monitor():
    ui.page_header("Home / Badminton", "Badminton — Live Monitor",
                    "16 departments · Double elimination · First to 3 category wins", "Live", "green")
    bd = state.load_bd()
    champ = logic.bd_champion(bd)
    if champ:
        st.markdown(
            f"<div style='text-align:center;padding:16px;background:linear-gradient(135deg,#0f1e33,#16283f);"
            f"border-radius:12px;border:2px solid #d99a2b;color:#f5c518;font-size:20px;font-weight:800'>"
            f"🏆 Champion — {champ}</div>", unsafe_allow_html=True,
        )
        st.markdown("")

    view = st.radio("View", ["🗂 Bracket View", "📺 Live Monitor"], horizontal=True, label_visibility="collapsed")

    if view == "🗂 Bracket View":
        st.caption("Solid lines route winners forward; dashed lines route losers down to the losers bracket. "
                    "This view is read-only — score from the Admin pages.")
        html = bracket_svg.render_bracket_view_html(bd)
        components.html(html, height=bracket_svg.canvas_size()["h"] + 40, scrolling=True)
    else:
        rounds = st.multiselect("Show rounds", logic.ALL_BD_ROUNDS, default=logic.ALL_BD_ROUNDS,
                                 format_func=lambda r: logic.BD_ROUND_INFO[r]["label"], key="bd_mon_rounds")
        html = _render_bd_monitor_html(bd, rounds)
        components.html(html, height=900, scrolling=True)


def _pk_display(t1, t2, winner, games, label):
    """Uniform display record for a pickleball match, whichever structure it
    came from (group-stage match dict has no t1/t2 of its own — the pair
    names live on the group roster — while a knockout tie carries t1/t2
    directly). Every renderer below only ever touches this shape."""
    return {"t1": t1, "t2": t2, "winner": winner, "games": games, "label": label}


def _pk_status(d):
    if d["winner"] is not None:
        return "done"
    if not d["t1"] or not d["t2"]:
        return "pending"
    active = any(g["finished"] or g["p1"] > 0 or g["p2"] > 0 for g in d["games"])
    return "live" if active else "scheduled"


def _pk_tally(games):
    w1 = w2 = 0
    for g in games:
        if not g["finished"]:
            continue
        if g["p1"] > g["p2"]:
            w1 += 1
        elif g["p2"] > g["p1"]:
            w2 += 1
    return w1, w2


def _pk_score_table_html(d, compact=True, show_names=False, show_tally=False):
    """Same real-scoreboard-table approach as the badminton monitor's
    _bd_score_table_html, minus the category grouping — a pickleball match
    is just one best-of-3 game group, so each column is a single game."""
    vis = logic.visible_games(d["games"])
    games = [(gi, d["games"][gi]) for gi in vis]
    if not games:
        return ""

    hdr_size = "9px" if compact else "13px"
    cell_size = "11px" if compact else "20px"
    cell_pad = "3px 7px" if compact else "10px 16px"
    name_size = "11px" if compact else "16px"

    t1name, t2name = d["t1"] or "TBD", d["t2"] or "TBD"
    winner = d["winner"]
    t1_color = "#4ade80" if winner == 1 else ("#6b6960" if winner == 2 else "#e8e6df")
    t2_color = "#60a5fa" if winner == 2 else ("#6b6960" if winner == 1 else "#e8e6df")

    current_gi = None
    if winner is None:
        last_gi, last = games[-1]
        if not last["finished"] and (last["p1"] > 0 or last["p2"] > 0):
            current_gi = last_gi

    name_hdr = f'<th style="padding:{cell_pad}"></th>' if show_names else ""
    hdr_cells = name_hdr
    for gi, g in games:
        if g["finished"]:
            color = "#4ade80" if g["p1"] > g["p2"] else ("#60a5fa" if g["p2"] > g["p1"] else "#8a877d")
        elif gi == current_gi:
            color = "#f59e0b"
        else:
            color = "#8a877d"
        hdr_cells += (
            f'<th style="font-size:{hdr_size};font-family:\'DM Mono\',monospace;color:{color};'
            f'font-weight:800;text-transform:uppercase;letter-spacing:.04em;padding:{cell_pad};'
            f'border-bottom:1px solid #2a2a24;border-left:1px solid #2a2a24;text-align:center">G{gi+1}</th>'
        )
    tally_hdr = (
        f'<th style="font-size:{hdr_size};font-family:\'DM Mono\',monospace;color:#d99a2b;font-weight:800;'
        f'text-transform:uppercase;letter-spacing:.04em;padding:{cell_pad};border-bottom:1px solid #2a2a24;'
        f'border-left:1px solid #2a2a24;text-align:center;white-space:nowrap">Games</th>'
    ) if show_tally else ""
    hdr_cells += tally_hdr

    def team_row(slot, name, color, weight, tally):
        cells = ""
        if show_names:
            cells += (
                f'<td class="pk-name-cell" style="padding:{cell_pad};font-size:{name_size};font-weight:800;color:{color};'
                f'white-space:nowrap;text-align:left">{_truncate_name(name)}</td>'
            )
        for idx, (gi, g) in enumerate(games):
            border = "border-left:1px solid #2a2a24;" if idx == 0 else ""
            val = g["p1"] if slot == 1 else g["p2"]
            cells += (
                f'<td style="padding:{cell_pad};text-align:center;color:{color};font-weight:{weight};'
                f'font-family:\'DM Mono\',monospace;font-size:{cell_size};{border}">{val}</td>'
            )
        if show_tally:
            cells += (
                f'<td class="pk-tally-cell" style="padding:{cell_pad};text-align:center;color:{color};font-weight:800;'
                f'font-family:\'DM Mono\',monospace;font-size:{cell_size};border-left:1px solid #2a2a24">{tally}</td>'
            )
        return cells

    w1, w2 = _pk_tally(d["games"])
    row1 = team_row(1, t1name, t1_color, "800" if winner == 1 else "600", w1)
    row2 = team_row(2, t2name, t2_color, "800" if winner == 2 else "600", w2)

    return f"""
    <table style="border-collapse:collapse;width:{"100%" if show_names else "auto"};margin-top:8px">
      <thead><tr>{hdr_cells}</tr></thead>
      <tbody>
        <tr>{row1}</tr>
        <tr>{row2}</tr>
      </tbody>
    </table>
    """


def _pk_mon_tile_html(d, big=False):
    status = _pk_status(d)
    t1, t2 = _truncate_name(d["t1"] or "TBD"), _truncate_name(d["t2"] or "TBD")
    w1, w2 = _pk_tally(d["games"])
    border = "1px solid #f59e0b" if status == "live" else ("1px solid #2a2a24" if status != "done" else "1px solid #2f4f3a")
    badge = ('<span style="background:#f59e0b;color:#111;font-size:9px;font-weight:800;padding:2px 6px;'
             'border-radius:3px;letter-spacing:.03em">● LIVE</span>') if status == "live" else (
             '<span style="color:#4ade80;font-size:10px;font-weight:700">✓ FINAL</span>' if status == "done" else "")
    t1_color = "#4ade80" if (status == "done" and d["winner"] == 1) else ("#6b6960" if (status == "done" and d["winner"] == 2) else "#e8e6df")
    t2_color = "#4ade80" if (status == "done" and d["winner"] == 2) else ("#6b6960" if (status == "done" and d["winner"] == 1) else "#e8e6df")
    t1_weight = "700" if not (status == "done" and d["winner"] == 2) else "400"
    t2_weight = "700" if not (status == "done" and d["winner"] == 1) else "400"
    pad = "14px" if big else "10px"
    name_size = "16px" if big else "13px"
    score_size = "22px" if big else "17px"

    activity_line = ""
    activity_banner = ""
    if status == "live":
        vis = logic.visible_games(d["games"])
        gi = vis[-1]
        g = d["games"][gi]
        act_size = "13px" if big else "11px"
        pt_size = "16px" if big else "13px"
        activity_line = f"""
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid #2a2a24;font-size:{act_size};
                    color:#c9c6bd;font-family:'DM Mono',monospace;display:flex;justify-content:space-between;align-items:center">
          <span>Game {gi + 1}</span>
          <span style="font-weight:800;font-size:{pt_size};color:#f5c518">{g["p1"]}–{g["p2"]}</span>
        </div>
        """
        activity_banner = f"""
        <div class="pk-activity" style="margin-top:14px;padding:12px 18px;border-radius:8px;
                    background:linear-gradient(90deg,rgba(245,158,11,.14),rgba(245,158,11,.03));
                    border:1px solid rgba(245,158,11,.35);display:flex;justify-content:space-between;
                    align-items:center;gap:14px">
          <div>
            <div class="pk-activity-label" style="font-size:10px;color:#f5c518;font-weight:800;
                        text-transform:uppercase;letter-spacing:.08em;font-family:'DM Mono',monospace">
              ● Currently Playing</div>
            <div class="pk-activity-cat" style="font-size:18px;color:#fff;font-weight:800;margin-top:3px">
              Game {gi + 1}
            </div>
          </div>
          <div class="pk-activity-score" style="font-family:'DM Mono',monospace;font-weight:800;
                      font-size:32px;color:#f5c518;white-space:nowrap;flex-shrink:0">{g["p1"]}–{g["p2"]}</div>
        </div>
        """

    strip = _pk_score_table_html(d, compact=True) if status in ("live", "done") else ""

    header_and_teams = f"""
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-size:9px;color:#8a877d;font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.06em">
          {d["label"]}</span>
        {badge}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:{name_size};font-weight:{t1_weight};color:{t1_color}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:8px">{t1}</span>
        <span style="font-family:'DM Mono',monospace;font-size:{score_size};font-weight:800;flex-shrink:0">{w1}</span>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:{name_size};font-weight:{t2_weight};color:{t2_color}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-right:8px">{t2}</span>
        <span style="font-family:'DM Mono',monospace;font-size:{score_size};font-weight:800;flex-shrink:0">{w2}</span>
      </div>
      {activity_line}
    """

    if big:
        header_row = f"""
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-size:10px;color:#8a877d;font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.06em">
              {d["label"]}</span>
            {badge}
          </div>
        """
        table = _pk_score_table_html(d, compact=False, show_names=True, show_tally=True)
        return f"""
        <div style="background:#1c1c19;border:{border};border-radius:10px;padding:{pad};min-width:200px;max-width:100%;overflow-x:auto" class="mon-tile-card">
          {header_row}
          {table}
          {activity_banner}
        </div>
        """

    return f"""
    <div style="background:#1c1c19;border:{border};border-radius:10px;padding:{pad};min-width:200px;max-width:100%;overflow-x:auto" class="mon-tile-card">
      {header_and_teams}
      {strip}
    </div>
    """


def _pk_group_standings_html(pk):
    cards = ""
    for grp in ["A", "B", "C", "D"]:
        standings = logic.pk_standings(pk, grp)
        rows = ""
        for r, s in enumerate(standings):
            name = s["name"] or f"Pair {s['idx']+1}"
            color = "#4ade80" if r < 4 else "#8a877d"
            weight = "700" if r < 4 else "400"
            rows += f"""
            <tr>
              <td style="padding:5px 8px;font-family:'DM Mono',monospace;color:{color};font-weight:{weight};font-size:11px">{r+1}</td>
              <td style="padding:5px 8px;color:{color};font-weight:{weight};font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:150px">{name}</td>
              <td style="padding:5px 8px;font-family:'DM Mono',monospace;color:{color};font-weight:{weight};font-size:11px;text-align:right">{s['mw']}-{s['ml']}</td>
            </tr>
            """
        cards += f"""
        <div style="background:#1c1c19;border:1px solid #2a2a24;border-radius:10px;padding:14px;min-width:210px">
          <div style="font-size:11px;font-weight:800;letter-spacing:.06em;color:#d99a2b;text-transform:uppercase;
                      font-family:'DM Mono',monospace;margin-bottom:8px">Group {grp}</div>
          <table style="width:100%;border-collapse:collapse">{rows}</table>
        </div>
        """
    return f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px">{cards}</div>'


def _render_pk_monitor_html(pk, rounds):
    show_group = "GROUP" in rounds
    live = []

    if show_group:
        for grp in ["A", "B", "C", "D"]:
            pairs = pk["groups"][grp]
            n = len(pairs)
            for i in range(n):
                for j in range(i + 1, n):
                    m = logic.pk_get_match_if_exists(pk, grp, i, j)
                    if not m:
                        continue
                    t1 = pairs[i]["name"] or f"Pair {i+1}"
                    t2 = pairs[j]["name"] or f"Pair {j+1}"
                    d = _pk_display(t1, t2, m["winner"], m["games"], f"Group {grp}")
                    if _pk_status(d) == "live":
                        live.append(d)

    for tid, tie in pk["ko"].items():
        r = "GF" if tid == "GF" else tid.split("_")[0]
        if r not in rounds:
            continue
        d = _pk_display(tie["t1"], tie["t2"], tie["winner"], tie["games"], logic.PK_ROUND_LABELS[r])
        if _pk_status(d) == "live":
            live.append(d)

    if live:
        # Same fix as the badminton monitor: only spotlight a single live
        # match as a full "big" jumbo card. Pickleball's group stage
        # routinely has several matches live at once across 4 groups — with
        # the old code every one of them was forced into the wide "big"
        # layout, then squeezed into a flex row, causing team names to
        # overflow each card's edge and the score table to get clipped so
        # only a sliver (often just the last game's column) stayed visible.
        if len(live) == 1:
            tiles = f'<div style="width:100%;max-width:520px">{_pk_mon_tile_html(live[0], big=True)}</div>'
            live_section = f'<div style="margin-bottom:22px">{tiles}</div>'
        else:
            tiles = "".join(_pk_mon_tile_html(d) for d in live)
            live_section = (
                '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));'
                f'gap:12px;margin-bottom:22px">{tiles}</div>'
            )
    else:
        live_section = '<div style="color:#8a877d;font-size:13px;margin-bottom:22px">No matches currently in progress.</div>'

    sections = ""
    if show_group:
        sections += f"""
        <div style="margin-bottom:20px">
          <div style="font-size:11px;color:#8a877d;text-transform:uppercase;letter-spacing:.08em;
                      font-family:'DM Mono',monospace;margin-bottom:10px">Group Standings</div>
          {_pk_group_standings_html(pk)}
        </div>
        """

    for r in ["K1", "K2", "K3", "GF"]:
        if r not in rounds:
            continue
        ids = [tid for tid in pk["ko"] if (tid.startswith(r + "_") or (r == "GF" and tid == "GF"))]
        if not ids:
            continue
        ids = sorted(ids, key=lambda t: int(t.split("_")[1]) if "_" in t else 0)
        tiles = ""
        for tid in ids:
            tie = pk["ko"][tid]
            d = _pk_display(tie["t1"], tie["t2"], tie["winner"], tie["games"],
                             bracket_svg.PK_MATCH_LABELS.get(tid, tid))
            tiles += _pk_mon_tile_html(d)
        sections += f"""
        <div style="margin-bottom:20px">
          <div style="font-size:11px;color:#8a877d;text-transform:uppercase;letter-spacing:.08em;
                      font-family:'DM Mono',monospace;margin-bottom:10px">{logic.PK_ROUND_LABELS[r]}</div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px">{tiles}</div>
        </div>
        """

    return f"""
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <div style="color-scheme:dark;background:#111110;padding:20px;border-radius:12px;font-family:'Inter',sans-serif;min-height:850px">
      <div id="pk-live-now">
        <div class="pk-fs-topbar" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:6px">
          <div style="display:flex;align-items:center;gap:8px">
            <span style="width:8px;height:8px;border-radius:50%;background:#f43f5e;display:inline-block"></span>
            <span style="color:#e8e6df;font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase">Live Now</span>
            <span class="pk-fs-brand" style="display:none;color:#8a877d;font-size:12px;font-family:'DM Mono',monospace;
                        letter-spacing:.1em;text-transform:uppercase;margin-left:10px">LBS × MGB — Sports Tournament</span>
          </div>
          <div style="display:flex;gap:14px;font-size:9.5px;color:#8a877d;font-family:'DM Mono',monospace;align-items:center">
            <span class="pk-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#4ade80;margin-right:4px"></span>Pair A won game</span>
            <span class="pk-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#60a5fa;margin-right:4px"></span>Pair B won game</span>
            <span class="pk-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#f59e0b;margin-right:4px"></span>Live now</span>
            <span class="pk-fs-legend"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#3a3a34;margin-right:4px"></span>Not started</span>
            <button id="pk-fs-btn" onclick="pkToggleFullscreen()" style="background:rgba(255,255,255,.06);
                    color:#e8e6df;border:1px solid rgba(255,255,255,.16);border-radius:6px;padding:5px 10px;
                    font-size:10px;font-weight:700;font-family:'DM Mono',monospace;cursor:pointer;letter-spacing:.04em">
              ⛶ Full Screen
            </button>
          </div>
        </div>
        <div class="pk-fs-hero" style="display:none;text-align:center;margin:6px 0 30px">
          <div style="font-size:13px;font-weight:800;letter-spacing:.16em;color:#8a877d;text-transform:uppercase;
                      font-family:'DM Mono',monospace;margin-bottom:10px">LBS × MGB Sports Tournament</div>
          <div style="font-size:46px;font-weight:800;color:#fff;letter-spacing:-0.01em;line-height:1.1">
            🏓 LBS Olympics <span style="color:#d99a2b">Pickleball!</span>
          </div>
          <div id="pk-fs-datetime" style="margin-top:12px;font-size:17px;color:#a8a59e;font-family:'DM Mono',monospace;
                      letter-spacing:.05em"></div>
        </div>
        <div class="pk-fs-stage">
          {live_section}
        </div>
      </div>
      <div style="color:#8a877d;font-size:11px;text-transform:uppercase;letter-spacing:.08em;
                  font-family:'DM Mono',monospace;margin-bottom:12px">Tournament Overview</div>
      {sections}
    </div>
    <script>
      function pkSetFsUi(active) {{
        var el = document.getElementById('pk-live-now');
        var btn = document.getElementById('pk-fs-btn');
        if (el) el.classList.toggle('pk-fs', active);
        if (btn) btn.innerHTML = active ? '⛶ Exit Full Screen' : '⛶ Full Screen';
        var brand = document.querySelectorAll('.pk-fs-brand');
        for (var i = 0; i < brand.length; i++) brand[i].style.display = active ? 'inline' : 'none';
        var hero = document.querySelector('.pk-fs-hero');
        if (hero) hero.style.display = active ? 'block' : 'none';
      }}
      function pkToggleFullscreen() {{
        var el = document.getElementById('pk-live-now');
        if (!document.fullscreenElement && !document.webkitFullscreenElement) {{
          if (el.requestFullscreen) {{ el.requestFullscreen(); }}
          else if (el.webkitRequestFullscreen) {{ el.webkitRequestFullscreen(); }}
        }} else {{
          if (document.exitFullscreen) {{ document.exitFullscreen(); }}
          else if (document.webkitExitFullscreen) {{ document.webkitExitFullscreen(); }}
        }}
      }}
      document.addEventListener('fullscreenchange', function() {{
        pkSetFsUi(!!document.fullscreenElement);
      }});
      document.addEventListener('webkitfullscreenchange', function() {{
        pkSetFsUi(!!document.webkitFullscreenElement);
      }});
      setInterval(function() {{
        var dt = document.getElementById('pk-fs-datetime');
        if (dt && dt.closest('#pk-live-now').classList.contains('pk-fs')) {{
          var now = new Date();
          var dateStr = now.toLocaleDateString([], {{weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}});
          var timeStr = now.toLocaleTimeString([], {{hour: '2-digit', minute: '2-digit', second: '2-digit'}});
          dt.textContent = dateStr + '  ·  ' + timeStr;
        }}
      }}, 1000);
    </script>
    <style>
      #pk-live-now.pk-fs {{
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        min-height: 100vh !important;
        padding: 48px 64px !important;
        background: radial-gradient(circle at 50% 10%, #1c1a14 0%, #0a0a08 65%) !important;
        box-sizing: border-box !important;
      }}
      #pk-live-now.pk-fs .pk-fs-topbar {{ margin-bottom: 0 !important; }}
      #pk-live-now.pk-fs .pk-fs-legend {{ font-size: 13px !important; }}
      #pk-live-now.pk-fs #pk-fs-btn {{ font-size: 13px !important; padding: 8px 16px !important; }}
      #pk-live-now.pk-fs .pk-fs-stage {{ display: flex !important; flex-direction: column !important; gap: 22px !important; }}
      #pk-live-now.pk-fs .pk-fs-stage > div {{ margin-bottom: 0 !important; }}
      #pk-live-now.pk-fs table {{ width: 100% !important; }}
      #pk-live-now.pk-fs table th {{
        font-size: 22px !important; padding: 16px 26px !important;
      }}
      #pk-live-now.pk-fs table td {{
        font-size: 34px !important; padding: 18px 26px !important;
      }}
      #pk-live-now.pk-fs table td.pk-name-cell {{ font-size: 40px !important; }}
      #pk-live-now.pk-fs table td.pk-tally-cell {{ font-size: 40px !important; color: #d99a2b !important; }}
      #pk-live-now.pk-fs .pk-activity {{ padding: 22px 32px !important; margin-top: 24px !important; border-radius: 12px !important; }}
      #pk-live-now.pk-fs .pk-activity-label {{ font-size: 15px !important; }}
      #pk-live-now.pk-fs .pk-activity-cat {{ font-size: 30px !important; }}
      #pk-live-now.pk-fs .pk-activity-score {{ font-size: 56px !important; }}
      #pk-live-now.pk-fs [style*="min-width:200px"] {{
        border-radius: 18px !important; padding: 32px 36px !important;
        box-shadow: 0 20px 60px rgba(0,0,0,.55) !important;
      }}
      #pk-live-now:fullscreen {{ background: #0a0a08; }}
      #pk-live-now:-webkit-full-screen {{ background: #0a0a08; }}
      .mon-tile-card {{ scrollbar-width: thin; scrollbar-color: #3a3a34 transparent; }}
      .mon-tile-card::-webkit-scrollbar {{ height: 4px; }}
      .mon-tile-card::-webkit-scrollbar-track {{ background: transparent; }}
      .mon-tile-card::-webkit-scrollbar-thumb {{ background: #3a3a34; border-radius: 4px; }}
    </style>
    """


def render_pickleball_monitor():
    ui.page_header("Home / Pickleball", "Pickleball — Live Monitor",
                    "22 pairs · 4 groups · Top 4 advance · Mixed doubles", "Live", "green")
    pk = state.load_pk()
    champ = logic.pk_champion(pk)
    if champ:
        st.markdown(
            f"<div style='text-align:center;padding:16px;background:linear-gradient(135deg,#0f1e33,#16283f);"
            f"border-radius:12px;border:2px solid #d99a2b;color:#f5c518;font-size:20px;font-weight:800'>"
            f"🏆 Champion — {champ}</div>", unsafe_allow_html=True,
        )
        st.markdown("")

    view = st.radio("View", ["🗂 Bracket View", "📺 Live Monitor"], horizontal=True, label_visibility="collapsed")

    if view == "🗂 Bracket View":
        st.caption("Solid lines route winners forward through the Round of 16 → Quarter-Final → Semi-Final → Final. "
                    "This view is read-only — score from the Admin pages.")
        html = bracket_svg.render_pk_bracket_view_html(pk)
        components.html(html, height=bracket_svg.pk_canvas_size()["h"] + 40, scrolling=True)
    else:
        rounds = st.multiselect("Show rounds", logic.ALL_PK_ROUNDS, default=logic.ALL_PK_ROUNDS,
                                 format_func=lambda r: logic.PK_ROUND_LABELS[r], key="pk_mon_rounds")
        html = _render_pk_monitor_html(pk, rounds)
        components.html(html, height=900, scrolling=True)
