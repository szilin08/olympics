from functools import partial

import streamlit as st

import auth
import db
import logic
import state
import ui

PK_PTS = 15  # pickleball is always best-of-3 to 15, per the tournament rules


# ───────────────────────── badminton callbacks ─────────────────────────

def _bd_team_change(tie_id, which, key):
    val = st.session_state[key]
    if val == ui.CLEAR_OPTION:
        # Sentinel picked from the dropdown to unassign a team — normalize
        # both the saved value and the widget's own state back to None so
        # the box shows its placeholder again on the next render, instead
        # of getting stuck displaying the literal "— Clear / unassign —" text.
        val = None
        st.session_state[key] = None
    bd = state.load_bd()
    logic.bd_set_team(bd, tie_id, which, val)
    state.save_bd(bd, actor=st.session_state.get("admin_name", "admin"), action=f"set_team:{tie_id}:{which}")


def _bd_point_cb(tie_id, ci, gi, who, delta):
    bd = state.load_bd()
    logic.bd_point(bd, tie_id, ci, gi, who, delta)
    state.save_bd(bd, actor=st.session_state.get("admin_name", "admin"), action=f"point:{tie_id}")


def _bd_finish_cb(tie_id, ci, gi):
    bd = state.load_bd()
    logic.bd_finish_game(bd, tie_id, ci, gi)
    state.save_bd(bd, actor=st.session_state.get("admin_name", "admin"), action=f"finish:{tie_id}")


def _bd_reopen_cb(tie_id, ci, gi):
    bd = state.load_bd()
    logic.bd_reopen_game(bd, tie_id, ci, gi)
    state.save_bd(bd, actor=st.session_state.get("admin_name", "admin"), action=f"reopen:{tie_id}")


def _bd_reset_tie_cb(tie_id):
    bd = state.load_bd()
    logic.bd_reset_tie(bd, tie_id)
    state.save_bd(bd, actor=st.session_state.get("admin_name", "admin"), action=f"reset_tie:{tie_id}")


import streamlit.components.v1 as components

import bracket_svg


def render_badminton_admin():
    auth.require_admin()
    ui.page_header("Home / Badminton", "Badminton — Admin",
                    "16 departments · Double elimination · First to 3 category wins · 15 pts (21 from semis)",
                    "Admin mode", "navy")

    bd = state.load_bd()

    top1, top2 = st.columns([3, 1])
    with top2:
        if st.button("↺ Reset entire bracket", use_container_width=True):
            st.session_state["confirm_bd_reset"] = True
        if st.session_state.get("confirm_bd_reset"):
            st.warning("This clears **all** teams and scores. This cannot be undone.")
            c1, c2 = st.columns(2)
            if c1.button("Yes, reset", key="bd_reset_yes", type="primary", use_container_width=True):
                state.reset_bd(actor=st.session_state.get("admin_name", "admin"))
                st.session_state["confirm_bd_reset"] = False
                st.rerun()
            if c2.button("Cancel", key="bd_reset_no", use_container_width=True):
                st.session_state["confirm_bd_reset"] = False
                st.rerun()

    champ = logic.bd_champion(bd)
    if champ:
        st.success(f"🏆 Champion: **{champ}**")

    view = st.radio("View", ["📋 List / Scoring", "🗂 Bracket View"], horizontal=True, label_visibility="collapsed")

    if view == "🗂 Bracket View":
        st.caption("Reference view — click a card's **Score ▸** button on List / Scoring to enter results.")
        html = bracket_svg.render_bracket_view_html(bd)
        components.html(html, height=bracket_svg.canvas_size()["h"] + 40, scrolling=True)
        return

    st.caption("💡 Team fields are searchable dropdowns of the LBS/MGB roster — start typing to filter, "
               "or type a name that isn't on the list and it'll be used as-is.")

    st.markdown('<div class="lb-cat">Winners Bracket</div>', unsafe_allow_html=True)
    _render_bd_round_columns(["W1", "W2", "W3", "W4"], bd)

    st.markdown('<div class="lb-cat" style="margin-top:22px">Losers Bracket</div>', unsafe_allow_html=True)
    _render_bd_round_columns(["L1", "L2", "L3", "L4", "L5", "L6"], bd)

    st.markdown('<div class="lb-cat" style="margin-top:22px">Grand Final</div>', unsafe_allow_html=True)
    gf_col = st.columns(4)[0]
    with gf_col:
        _render_bd_card("GF", bd["ties"]["GF"], 0)


def _render_bd_round_columns(round_ids, bd):
    cols = st.columns(len(round_ids))
    for col, r in zip(cols, round_ids):
        with col:
            info = logic.BD_ROUND_INFO[r]
            st.markdown(f"**{info['label']}**")
            st.caption(f"{info['pts']}pt games")
            tie_ids = sorted([tid for tid in bd["ties"] if tid.split("_")[0] == r],
                              key=lambda t: int(t.split("_")[1]))
            for i, tid in enumerate(tie_ids):
                _render_bd_card(tid, bd["ties"][tid], i)


def _render_bd_card(tid, tie, match_no):
    with st.container(border=True):
        top1, top2 = st.columns([1, 1])
        top1.caption(f"M{match_no + 1}" if tid != "GF" else "🏆 GF")
        color = "#1f7a4c" if tie["winner"] else "#12203a"
        top2.markdown(
            f"<div style='text-align:right;font-family:monospace;font-weight:800;color:{color}'>"
            f"{tie['w1']}–{tie['w2']}</div>", unsafe_allow_html=True,
        )
        k1, k2 = f"bdc_{tid}_t1", f"bdc_{tid}_t2"
        ui.dept_combobox("Team A", tie["t1"], k1, _bd_team_change, (tid, "t1", k1), "Dept / Team A")
        ui.dept_combobox("Team B", tie["t2"], k2, _bd_team_change, (tid, "t2", k2), "Dept / Team B")
        if tie["winner"]:
            st.caption("✅ Complete")
        elif tie["tbNeeded"]:
            st.caption("⚠️ Tie-breaker")
        if st.button("Score ▸", key=f"bdc_{tid}_open", use_container_width=True):
            _bd_score_dialog(tid)


@st.dialog("Match scoring", width="large")
def _bd_score_dialog(tid):
    bd = state.load_bd()
    tie = bd["ties"][tid]
    round_id = tid.split("_")[0] if tid != "GF" else "GF"
    pts = logic.BD_ROUND_INFO[round_id]["pts"]
    st.caption(logic.BD_ROUND_INFO[round_id]["label"])
    _render_bd_tie_editor(tid, tie, pts)
    if st.button("Close", use_container_width=True):
        st.rerun()


def _render_bd_tie_editor(tid, tie, pts):
    c1, c2 = st.columns(2)
    k1, k2 = f"bd_{tid}_t1", f"bd_{tid}_t2"
    with c1:
        ui.dept_combobox("Team A", tie["t1"], k1, _bd_team_change, (tid, "t1", k1), "Dept / Team A")
    with c2:
        ui.dept_combobox("Team B", tie["t2"], k2, _bd_team_change, (tid, "t2", k2), "Dept / Team B")

    if tie["winner"]:
        ui.status_badge(f"Winner: {tie['t1'] if tie['winner'] == 1 else tie['t2']}", "ok")
    elif tie["tbNeeded"]:
        ui.status_badge("Tie-breaker needed (2–2)", "warn")
    st.caption(f"Category wins: {tie['w1']} – {tie['w2']}")
    st.markdown("")

    for ci, catname in enumerate(logic.BD_CATS):
        cat = tie["cats"][ci]
        is_tb = ci == 4
        if is_tb and not (tie["tbNeeded"] or any(g["finished"] for g in cat["games"])):
            continue
        st.markdown(f"**{catname}**")
        for gi in logic.visible_games(cat["games"]):
            g = cat["games"][gi]
            key_prefix = f"bd_{tid}_{ci}_{gi}"
            ui.score_row(
                f"Game {gi + 1}", g,
                on_minus=(partial(_bd_point_cb, tid, ci, gi, 1, -1), partial(_bd_point_cb, tid, ci, gi, 2, -1)),
                on_plus=(partial(_bd_point_cb, tid, ci, gi, 1, 1), partial(_bd_point_cb, tid, ci, gi, 2, 1)),
                on_finish=partial(_bd_finish_cb, tid, ci, gi),
                on_reopen=partial(_bd_reopen_cb, tid, ci, gi),
                pts_target=pts, key_prefix=key_prefix,
            )

    st.button("↺ Reset this tie", key=f"bd_{tid}_reset", on_click=partial(_bd_reset_tie_cb, tid))


# ───────────────────────── pickleball callbacks ─────────────────────────

def _pk_pair_name_change(grp, idx, key):
    pk = state.load_pk()
    logic.pk_set_pair_name(pk, grp, idx, st.session_state[key])
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"set_pair:{grp}:{idx}")


def _pk_add_pair_cb(grp):
    pk = state.load_pk()
    logic.pk_add_pair(pk, grp)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"add_pair:{grp}")


def _pk_remove_pair_cb(grp):
    pk = state.load_pk()
    logic.pk_remove_pair(pk, grp)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"remove_pair:{grp}")


def _pk_point_cb(grp, i, j, gi, who, delta):
    pk = state.load_pk()
    logic.pk_point(pk, grp, i, j, gi, who, delta)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"point:{grp}")


def _pk_finish_cb(grp, i, j, gi):
    pk = state.load_pk()
    logic.pk_finish_game(pk, grp, i, j, gi)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"finish:{grp}")


def _pk_reopen_cb(grp, i, j, gi):
    pk = state.load_pk()
    logic.pk_reopen_game(pk, grp, i, j, gi)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"reopen:{grp}")


def _pk_auto_seed_cb():
    pk = state.load_pk()
    logic.pk_auto_seed_ko(pk)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action="auto_seed_ko")


def _pk_ko_team_change(tid, which, key):
    pk = state.load_pk()
    logic.pk_ko_set_team(pk, tid, which, st.session_state[key])
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"ko_set_team:{tid}")


def _pk_ko_point_cb(tid, gi, who, delta):
    pk = state.load_pk()
    logic.pk_ko_point(pk, tid, gi, who, delta)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"ko_point:{tid}")


def _pk_ko_finish_cb(tid, gi):
    pk = state.load_pk()
    logic.pk_ko_finish_game(pk, tid, gi)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"ko_finish:{tid}")


def _pk_ko_reopen_cb(tid, gi):
    pk = state.load_pk()
    logic.pk_ko_reopen_game(pk, tid, gi)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"ko_reopen:{tid}")


def _pk_ko_reset_tie_cb(tid):
    pk = state.load_pk()
    logic.pk_ko_reset_tie(pk, tid)
    state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action=f"ko_reset:{tid}")


def render_pickleball_admin():
    auth.require_admin()
    ui.page_header("Home / Pickleball", "Pickleball — Admin",
                    "22 pairs · 4 groups · Top 4 per group advance · Mixed doubles · Best of 3 to 15 pts",
                    "Admin mode", "navy")

    top1, top2 = st.columns([3, 1])
    with top2:
        if st.button("↺ Reset everything", use_container_width=True):
            st.session_state["confirm_pk_reset"] = True
        if st.session_state.get("confirm_pk_reset"):
            st.warning("This clears **all** pairs, groups and scores. This cannot be undone.")
            c1, c2 = st.columns(2)
            if c1.button("Yes, reset", key="pk_reset_yes", type="primary", use_container_width=True):
                state.reset_pk(actor=st.session_state.get("admin_name", "admin"))
                st.session_state["confirm_pk_reset"] = False
                st.rerun()
            if c2.button("Cancel", key="pk_reset_no", use_container_width=True):
                st.session_state["confirm_pk_reset"] = False
                st.rerun()

    pk = state.load_pk()
    champ = logic.pk_champion(pk)
    if champ:
        st.success(f"🏆 Champion: **{champ}**")

    tab1, tab2, tab3 = st.tabs(["👥 Pairs & Groups", "🔁 Group Matches", "🏆 Knockout Bracket"])

    with tab1:
        cols = st.columns(2)
        for i, grp in enumerate(["A", "B", "C", "D"]):
            with cols[i % 2]:
                st.subheader(f"Group {grp}")
                pairs = pk["groups"][grp]
                for idx, p in enumerate(pairs):
                    key = f"pk_{grp}_{idx}_name"
                    st.text_input(f"Pair {idx + 1}", value=p["name"], key=key,
                                  on_change=_pk_pair_name_change, args=(grp, idx, key))
                bc1, bc2 = st.columns(2)
                bc1.button(f"− Remove pair (Group {grp})", key=f"pk_{grp}_remove",
                           on_click=partial(_pk_remove_pair_cb, grp), use_container_width=True,
                           disabled=len(pairs) <= 4)
                bc2.button(f"+ Add pair (Group {grp})", key=f"pk_{grp}_add",
                           on_click=partial(_pk_add_pair_cb, grp), use_container_width=True,
                           disabled=len(pairs) >= 10)
                st.markdown("---")

    with tab2:
        grp = st.selectbox("Group", ["A", "B", "C", "D"], key="pk_matches_group")
        pairs = pk["groups"][grp]
        n = len(pairs)
        st.markdown("**Standings**")
        standings = logic.pk_standings(pk, grp)
        st.dataframe(
            [{"#": r + 1, "Pair": s["name"] or f"Pair {s['idx']+1}", "W-L": f"{s['mw']}-{s['ml']}",
              "Diff": f"{'+' if s['diff']>0 else ''}{s['diff']}", "Advances": "✅" if r < 4 else ""}
             for r, s in enumerate(standings)],
            hide_index=True, use_container_width=True,
        )
        st.markdown("**Matches**")
        for i in range(n):
            for j in range(i + 1, n):
                t1 = pairs[i]["name"] or f"Pair {i+1}"
                t2 = pairs[j]["name"] or f"Pair {j+1}"
                m = logic.pk_get_match(pk, grp, i, j)
                badge = " ✅" if m["winner"] else ""
                with st.expander(f"{t1}  vs  {t2}{badge}"):
                    for gi in logic.visible_games(m["games"]):
                        g = m["games"][gi]
                        key_prefix = f"pk_{grp}_{i}_{j}_{gi}"
                        ui.score_row(
                            f"Game {gi + 1}", g,
                            on_minus=(partial(_pk_point_cb, grp, i, j, gi, 1, -1), partial(_pk_point_cb, grp, i, j, gi, 2, -1)),
                            on_plus=(partial(_pk_point_cb, grp, i, j, gi, 1, 1), partial(_pk_point_cb, grp, i, j, gi, 2, 1)),
                            on_finish=partial(_pk_finish_cb, grp, i, j, gi),
                            on_reopen=partial(_pk_reopen_cb, grp, i, j, gi),
                            pts_target=PK_PTS, key_prefix=key_prefix,
                        )
        # persist any match dicts created on-the-fly by pk_get_match
        state.save_pk(pk, actor=st.session_state.get("admin_name", "admin"), action="touch_matches")

    with tab3:
        st.button("⚡ Auto-seed Round of 16 from current group standings", on_click=_pk_auto_seed_cb)
        st.caption("Cross-seeds so an A/D-side qualifier always meets a B/C-side qualifier in the quarter-finals.")
        st.markdown("---")
        for r in ["K1", "K2", "K3", "GF"]:
            ids = sorted([tid for tid in pk["ko"] if (tid.startswith(r + "_") or (r == "GF" and tid == "GF"))])
            if not ids:
                continue
            st.subheader(logic.PK_ROUND_LABELS[r])
            for tid in ids:
                tie = pk["ko"][tid]
                badge = " ✅" if tie["winner"] else ""
                with st.expander(f"{tie['t1'] or 'TBD'}  vs  {tie['t2'] or 'TBD'}{badge}"):
                    k1, k2 = f"pkko_{tid}_t1", f"pkko_{tid}_t2"
                    c1, c2 = st.columns(2)
                    c1.text_input("Pair A", value=tie["t1"], key=k1, on_change=_pk_ko_team_change, args=(tid, "t1", k1))
                    c2.text_input("Pair B", value=tie["t2"], key=k2, on_change=_pk_ko_team_change, args=(tid, "t2", k2))
                    for gi in logic.visible_games(tie["games"]):
                        g = tie["games"][gi]
                        key_prefix = f"pkko_{tid}_{gi}"
                        ui.score_row(
                            f"Game {gi + 1}", g,
                            on_minus=(partial(_pk_ko_point_cb, tid, gi, 1, -1), partial(_pk_ko_point_cb, tid, gi, 2, -1)),
                            on_plus=(partial(_pk_ko_point_cb, tid, gi, 1, 1), partial(_pk_ko_point_cb, tid, gi, 2, 1)),
                            on_finish=partial(_pk_ko_finish_cb, tid, gi),
                            on_reopen=partial(_pk_ko_reopen_cb, tid, gi),
                            pts_target=PK_PTS, key_prefix=key_prefix,
                        )
                    st.button("↺ Reset this match", key=f"pkko_{tid}_reset", on_click=partial(_pk_ko_reset_tie_cb, tid))


# ───────────────────────── settings / schedule ─────────────────────────

def render_settings():
    auth.require_admin()
    ui.page_header("Home / Settings", "Schedule & Settings",
                    "Round dates, password setup, and the recent-activity audit log", "Admin mode", "navy")

    sched = state.load_schedule()

    st.subheader("Round schedule")
    st.caption("Tag each round with a date. Viewers can filter monitors down to \"today's rounds\" on event day.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Badminton rounds**")
        for r in logic.ALL_BD_ROUNDS:
            val = sched["bd"].get(r, "")
            new_val = st.text_input(logic.BD_ROUND_INFO[r]["label"], value=val, key=f"sched_bd_{r}",
                                     placeholder="YYYY-MM-DD")
            sched["bd"][r] = new_val
    with c2:
        st.markdown("**Pickleball rounds**")
        for r in logic.ALL_PK_ROUNDS:
            val = sched["pk"].get(r, "")
            new_val = st.text_input(logic.PK_ROUND_LABELS[r], value=val, key=f"sched_pk_{r}",
                                     placeholder="YYYY-MM-DD")
            sched["pk"][r] = new_val

    if st.button("💾 Save schedule", type="primary"):
        state.save_schedule(sched, actor=st.session_state.get("admin_name", "admin"))
        st.success("Schedule saved.")

    st.markdown("---")
    st.subheader("Admin password")
    st.info(
        "The shared admin password is set outside the app for security — via `st.secrets['admin_password']` "
        "(recommended for Streamlit Community Cloud, in `.streamlit/secrets.toml`) or the `TOURNEY_ADMIN_PASSWORD` "
        "environment variable. See the README for setup steps."
    )

    st.markdown("---")
    st.subheader("Recent activity")
    log = db.get_audit_log(limit=30)
    if log:
        st.dataframe(log, hide_index=True, use_container_width=True)
    else:
        st.caption("No activity yet.")
