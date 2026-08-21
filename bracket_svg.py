"""
Badminton "Bracket View" — connected-line tree, ported from the original
HTML's bdBVMatchPos / bdDrawLines / bdRenderBracketView so match positions
and line routing match exactly. Renders as one self-contained HTML+SVG
fragment (via st.components.v1.html) since it needs absolute positioning
that doesn't fit Streamlit's normal flow layout.
"""

import html as htmllib

import logic

MW, MH, CW, HDR, PAD, WBH, LBH, SG = 220, 68, 260, 32, 22, 800, 800, 36

# same palette as the badminton Live Now monitor (pages_public._bd_mon_tile_html)
BD_BG = "#111110"
BD_CARD_BG = "#1c1c19"
BD_BORDER = "#2a2a24"
BD_BORDER_DONE = "#2f4f3a"
BD_MUTED = "#8a877d"
BD_TEXT = "#e8e6df"
BD_WIN = "#4ade80"
BD_LOSE = "#6b6960"
BD_TBD = "#5f5d55"
BD_GOLD = "#d99a2b"


def _lb_counts(n=16):
    if n == 16:
        return [4, 4, 2, 2, 1, 1]
    if n == 8:
        return [2, 2, 1, 1]
    return []


def _match_pos(tie_id):
    if tie_id == "GF":
        return _gf_pos()
    sec = tie_id[0]
    round_, pos = (int(x) for x in tie_id[1:].split("_"))
    x = PAD + (round_ - 1) * CW
    if sec == "W":
        cnt = 16 >> round_
        slot_h = WBH / cnt
        body_y = PAD + HDR
        return {"x": x, "y": body_y + pos * slot_h + (slot_h - MH) / 2}
    else:
        cnt = _lb_counts(16)[round_ - 1]
        slot_h = LBH / cnt
        body_y = PAD + HDR + WBH + SG + HDR
        return {"x": x, "y": body_y + pos * slot_h + (slot_h - MH) / 2}


def _gf_pos():
    lb_r = len(_lb_counts(16))
    wbf = _match_pos("W4_0")
    lbf = _match_pos("L6_0")
    x = PAD + lb_r * CW
    cy = (wbf["y"] + MH / 2 + lbf["y"] + MH / 2) / 2
    return {"x": x, "y": cy - MH / 2}


def _canvas_size():
    lb_r = len(_lb_counts(16))
    return {"w": PAD + lb_r * CW + MW + PAD, "h": PAD + HDR + WBH + SG + HDR + LBH + PAD}


def _esc(s):
    return htmllib.escape(s or "")


def _card_html(tie, num, pos):
    done = tie["winner"] is not None
    is_gf = tie["id"] == "GF"
    champion = is_gf and done

    def team_row(name, slot):
        is_tbd = not name
        is_win = done and tie["winner"] == slot
        is_lose = done and tie["winner"] != slot
        if is_tbd:
            color, weight = BD_TBD, "400"
        elif is_win:
            color, weight = BD_WIN, "700"
        elif is_lose:
            color, weight = BD_LOSE, "400"
        else:
            color, weight = BD_TEXT, "500"
        icon = "✓" if is_win else ("✕" if is_lose else "")
        icon_color = BD_WIN if is_win else BD_TBD
        label = _esc(name) or "TBD"
        return (
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 14px;'
            f'font-size:14px;color:{color};font-weight:{weight};font-style:{"italic" if is_tbd else "normal"}">'
            f'<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{label}</span>'
            f'<span style="color:{icon_color};font-weight:800;font-size:13px">{icon}</span></div>'
        )

    lbl = "🏆 GRAND FINAL" if is_gf else f"M{num}"
    score_pill = (
        f'<span style="position:absolute;top:6px;right:12px;font-size:11px;font-family:\'DM Mono\',monospace;'
        f'font-weight:700;color:{BD_MUTED}">{tie["w1"] or 0}–{tie["w2"] or 0}{" · TB" if tie["tbNeeded"] else ""}</span>'
    )
    champ_overlay = (
        f'<div style="position:absolute;inset:0;background:rgba(217,154,43,.08);pointer-events:none;'
        f'display:flex;align-items:center;justify-content:flex-end;padding:0 10px">'
        f'<span style="font-size:20px">🏆</span></div>'
    ) if champion else ""
    border = f"2px solid {BD_GOLD}" if champion else (f"1px solid {BD_BORDER}" if not done else f"1px solid {BD_BORDER_DONE}")
    return (
        f'<div style="position:absolute;left:{pos["x"]}px;top:{pos["y"]}px;width:{MW}px;'
        f'background:{BD_CARD_BG};border:{border};border-radius:10px;overflow:hidden;'
        f'box-shadow:0 4px 14px rgba(0,0,0,.45)">'
        f'<div style="padding:6px 14px;background:rgba(255,255,255,.03);font-size:11px;font-weight:800;'
        f'color:{BD_MUTED};font-family:\'DM Mono\',monospace;letter-spacing:.04em;text-transform:uppercase">{lbl}</div>'
        f'{team_row(tie["t1"], 1)}{team_row(tie["t2"], 2)}{score_pill}{champ_overlay}'
        f'</div>'
    )


def _draw_lines():
    C, D, J = "rgba(255,255,255,.18)", "rgba(255,255,255,.30)", 16
    lb_counts = _lb_counts(16)
    wb_r, lb_r = 4, len(lb_counts)
    s = ""

    def ln(x1, y1, x2, y2, col=C, sw="2"):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"/>'

    def path(d, col=C, sw="2"):
        return f'<path d="{d}" stroke="{col}" stroke-width="{sw}" fill="none"/>'

    for r in range(1, wb_r):
        next_cnt = 16 >> (r + 1)
        for i in range(next_cnt):
            pa, pb, pc = _match_pos(f"W{r}_{i*2}"), _match_pos(f"W{r}_{i*2+1}"), _match_pos(f"W{r+1}_{i}")
            ax, ay = pa["x"] + MW, pa["y"] + MH / 2
            bx, by = pb["x"] + MW, pb["y"] + MH / 2
            cx, cy = pc["x"], pc["y"] + MH / 2
            jx = ax + J
            s += ln(ax, ay, jx, ay) + ln(bx, by, jx, by) + ln(jx, ay, jx, by) + ln(jx, cy, cx, cy)

    for r in range(1, lb_r):
        cnt, next_cnt = lb_counts[r - 1], lb_counts[r]
        if next_cnt < cnt:
            for i in range(next_cnt):
                pa, pb, pc = _match_pos(f"L{r}_{i*2}"), _match_pos(f"L{r}_{i*2+1}"), _match_pos(f"L{r+1}_{i}")
                ax, ay = pa["x"] + MW, pa["y"] + MH / 2
                bx, by = pb["x"] + MW, pb["y"] + MH / 2
                cx, cy = pc["x"], pc["y"] + MH / 2
                jx = ax + J
                s += ln(ax, ay, jx, ay) + ln(bx, by, jx, by) + ln(jx, ay, jx, by) + ln(jx, cy, cx, cy)
        else:
            for i in range(min(cnt, next_cnt)):
                pa, pb = _match_pos(f"L{r}_{i}"), _match_pos(f"L{r+1}_{i}")
                ax, ay = pa["x"] + MW, pa["y"] + MH / 2
                bx, by = pb["x"], pb["y"] + MH * 0.28
                jx = ax + J
                if abs(ay - by) < 3:
                    s += ln(ax, ay, bx, ay)
                else:
                    s += path(f"M{ax},{ay} H{jx} V{by} H{bx}")

    wbf_p, lbf_p, gf_p = _match_pos("W4_0"), _match_pos("L6_0"), _gf_pos()
    gf_cy, jx_gf = gf_p["y"] + MH / 2, gf_p["x"] - J
    s += path(f'M{wbf_p["x"]+MW},{wbf_p["y"]+MH/2} H{jx_gf} V{gf_cy} H{gf_p["x"]}')
    s += path(f'M{lbf_p["x"]+MW},{lbf_p["y"]+MH/2} H{jx_gf} V{gf_cy}')

    def drop(from_id, to_id):
        nonlocal s
        fp, tp = _match_pos(from_id), _match_pos(to_id)
        x1, y1 = fp["x"] + MW, fp["y"] + MH * 0.73
        x2, y2 = tp["x"], tp["y"] + MH * 0.73
        s += (f'<path d="M{x1},{y1} C{x1+40},{y1} {x2-40},{y2} {x2},{y2}" '
              f'stroke="{D}" stroke-width="1.5" stroke-dasharray="5,4" fill="none" opacity="0.7"/>')

    drop("W2_0", "L2_3"); drop("W2_1", "L2_2"); drop("W2_2", "L2_1"); drop("W2_3", "L2_0")
    drop("W3_0", "L4_1"); drop("W3_1", "L4_0")
    drop("W4_0", "L6_0")
    return s


def canvas_size():
    return _canvas_size()


# ── pickleball knockout bracket (single elimination) ──
# Ported from the original HTML's pkBVMatchPos / pkDrawKOLines / pkMkBVCard,
# but sized and colored to match the pickleball "Live Now" monitor rather
# than reusing the badminton view's tighter MW/MH/CW module constants —
# a single-elim, 4-round tree has far more horizontal room to spend per
# card than badminton's 11-column double-elim tree does.

PK_MW, PK_MH, PK_CW, PK_HDR, PK_PAD = 280, 82, 360, 46, 34
PK_KOH = 860  # canvas height for the KO visual (8 first-round matches)

# same palette as the pickleball Live Now monitor (pages_public._pk_mon_tile_html)
PK_BG = "#111110"
PK_CARD_BG = "#1c1c19"
PK_BORDER = "#2a2a24"
PK_BORDER_DONE = "#2f4f3a"
PK_MUTED = "#8a877d"
PK_TEXT = "#e8e6df"
PK_WIN = "#4ade80"
PK_LOSE = "#6b6960"
PK_TBD = "#5f5d55"
PK_GOLD = "#d99a2b"

PK_MATCH_LABELS = {
    "K1_0": "R16-1", "K1_1": "R16-2", "K1_2": "R16-3", "K1_3": "R16-4",
    "K1_4": "R16-5", "K1_5": "R16-6", "K1_6": "R16-7", "K1_7": "R16-8",
    "K2_0": "QF1", "K2_1": "QF2", "K2_2": "QF3", "K2_3": "QF4",
    "K3_0": "SF1", "K3_1": "SF2", "GF": "F",
}


def _pk_match_pos(tie_id):
    if tie_id == "GF":
        x = PK_PAD + 3 * PK_CW
        return {"x": x, "y": PK_PAD + PK_HDR + PK_KOH / 2 - PK_MH / 2}
    round_, pos = (int(x) for x in tie_id[1:].split("_"))
    x = PK_PAD + (round_ - 1) * PK_CW
    cnt = 16 >> round_
    slot_h = PK_KOH / cnt
    return {"x": x, "y": PK_PAD + PK_HDR + pos * slot_h + (slot_h - PK_MH) / 2}


def pk_canvas_size():
    return {"w": PK_PAD + 3 * PK_CW + PK_MW + PK_PAD, "h": PK_PAD + PK_HDR + PK_KOH + PK_PAD}


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


def _pk_card_html(tie, lbl, pos):
    done = tie["winner"] is not None
    is_gf = tie["id"] == "GF"
    champion = is_gf and done
    w1, w2 = _pk_tally(tie["games"])

    def team_row(name, slot):
        is_tbd = not name
        is_win = done and tie["winner"] == slot
        is_lose = done and tie["winner"] != slot
        if is_tbd:
            color, weight = PK_TBD, "400"
        elif is_win:
            color, weight = PK_WIN, "700"
        elif is_lose:
            color, weight = PK_LOSE, "400"
        else:
            color, weight = PK_TEXT, "500"
        icon = "✓" if is_win else ("✕" if is_lose else "")
        icon_color = PK_WIN if is_win else PK_TBD
        label = _esc(name) or "TBD"
        return (
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 14px;'
            f'font-size:14px;color:{color};font-weight:{weight};font-style:{"italic" if is_tbd else "normal"}">'
            f'<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{label}</span>'
            f'<span style="color:{icon_color};font-weight:800;font-size:13px">{icon}</span></div>'
        )

    header_lbl = "🏆 FINAL" if is_gf else lbl
    score_pill = (
        f'<span style="position:absolute;top:6px;right:12px;font-size:11px;font-family:\'DM Mono\',monospace;'
        f'font-weight:700;color:{PK_MUTED}">{w1}–{w2}</span>'
    )
    champ_overlay = (
        f'<div style="position:absolute;inset:0;background:rgba(217,154,43,.08);pointer-events:none;'
        f'display:flex;align-items:center;justify-content:flex-end;padding:0 10px">'
        f'<span style="font-size:20px">🏆</span></div>'
    ) if champion else ""
    border = f"2px solid {PK_GOLD}" if champion else (f"1px solid {PK_BORDER}" if not done else f"1px solid {PK_BORDER_DONE}")
    return (
        f'<div style="position:absolute;left:{pos["x"]}px;top:{pos["y"]}px;width:{PK_MW}px;'
        f'background:{PK_CARD_BG};border:{border};border-radius:10px;overflow:hidden;'
        f'box-shadow:0 4px 14px rgba(0,0,0,.45)">'
        f'<div style="padding:6px 14px;background:rgba(255,255,255,.03);font-size:11px;font-weight:800;'
        f'color:{PK_MUTED};font-family:\'DM Mono\',monospace;letter-spacing:.04em;text-transform:uppercase">{header_lbl}</div>'
        f'{team_row(tie["t1"], 1)}{team_row(tie["t2"], 2)}{score_pill}{champ_overlay}'
        f'</div>'
    )


def _pk_draw_lines():
    C = "rgba(255,255,255,.18)"
    J = 16

    def ln(x1, y1, x2, y2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C}" stroke-width="2"/>'

    s = ""
    KOR = 4
    for r in range(1, KOR):
        next_cnt = 16 >> (r + 1)
        for i in range(next_cnt):
            pa, pb = _pk_match_pos(f"K{r}_{i*2}"), _pk_match_pos(f"K{r}_{i*2+1}")
            pc = _pk_match_pos("GF") if r + 1 == KOR else _pk_match_pos(f"K{r+1}_{i}")
            ax, ay = pa["x"] + PK_MW, pa["y"] + PK_MH / 2
            bx, by = pb["x"] + PK_MW, pb["y"] + PK_MH / 2
            cx, cy = pc["x"], pc["y"] + PK_MH / 2
            jx = ax + J
            s += ln(ax, ay, jx, ay) + ln(bx, by, jx, by) + ln(jx, ay, jx, by) + ln(jx, cy, cx, cy)
    return s


def render_pk_bracket_view_html(pk):
    """Returns a self-contained HTML fragment for st.components.v1.html —
    the pickleball single-elimination knockout tree (Round of 16 → QF → SF → Final),
    styled to match the pickleball Live Now monitor (same background, card, and
    text colors) rather than the badminton bracket's navy/gold palette."""
    size = pk_canvas_size()
    w, h = size["w"], size["h"]

    round_lbls = ["Round of 16", "Quarter-Final", "Semi-Final"]
    hdrs = ""
    for i in range(3):
        hdrs += (f'<div style="position:absolute;left:{PK_PAD+i*PK_CW}px;top:{PK_PAD}px;width:{PK_MW}px;'
                 f'font-size:12px;font-weight:800;letter-spacing:.08em;color:{PK_MUTED};text-transform:uppercase;'
                 f'font-family:\'DM Mono\',monospace">{round_lbls[i]}</div>')
    hdrs += (f'<div style="position:absolute;left:{PK_PAD+3*PK_CW}px;top:{PK_PAD}px;width:{PK_MW}px;'
              f'font-size:12px;font-weight:800;letter-spacing:.08em;color:{PK_GOLD};text-transform:uppercase;'
              f'font-family:\'DM Mono\',monospace">🏆 Final</div>')

    cards = "".join(
        _pk_card_html(tie, PK_MATCH_LABELS.get(tid, tid), _pk_match_pos(tid))
        for tid, tie in pk["ko"].items()
    )
    lines = _pk_draw_lines()

    return f"""
    <div style="width:100%;min-height:{h+16}px;background:{PK_BG};padding:8px 0 8px 8px;box-sizing:border-box">
      <div style="color-scheme:dark;position:relative;width:{w}px;min-width:{w}px;height:{h}px;font-family:'Inter',sans-serif">
        <svg width="{w}" height="{h}" style="position:absolute;left:0;top:0">{lines}</svg>
        {hdrs}
        {cards}
      </div>
    </div>
    """


def render_bracket_view_html(bd):
    """Returns a self-contained HTML fragment for st.components.v1.html."""
    size = _canvas_size()
    w, h = size["w"], size["h"]

    num = 1
    nums = {}
    for r in range(1, 5):
        c = 16 >> r
        for p in range(c):
            nums[f"W{r}_{p}"] = num
            num += 1
    lb_counts = _lb_counts(16)
    for r in range(1, len(lb_counts) + 1):
        for p in range(lb_counts[r - 1]):
            nums[f"L{r}_{p}"] = num
            num += 1
    nums["GF"] = num

    wb_hdrs = ["WB R1", "WB R2", "WB Semi-Final", "WB Final"]
    lb_hdrs = ["LB R1", "LB R2", "LB R3", "LB R4", "LB Semi-Final", "LB Final"]
    hdrs = ""
    for i in range(4):
        hdrs += (f'<div style="position:absolute;left:{PAD+i*CW}px;top:{PAD}px;width:{MW}px;'
                 f'font-size:12px;font-weight:800;letter-spacing:.08em;color:#8fb4ff;text-transform:uppercase;'
                 f'font-family:\'DM Mono\',monospace">{wb_hdrs[i]}</div>')
    lb_top = PAD + HDR + WBH + SG
    for i in range(len(lb_counts)):
        hdrs += (f'<div style="position:absolute;left:{PAD+i*CW}px;top:{lb_top}px;width:{MW}px;'
                 f'font-size:12px;font-weight:800;letter-spacing:.08em;color:#7ee0a3;text-transform:uppercase;'
                 f'font-family:\'DM Mono\',monospace">{lb_hdrs[i]}</div>')
    hdrs += (f'<div style="position:absolute;left:{PAD+len(lb_counts)*CW}px;top:{lb_top}px;width:{MW}px;'
              f'font-size:12px;font-weight:800;letter-spacing:.08em;color:{BD_GOLD};text-transform:uppercase;'
              f'font-family:\'DM Mono\',monospace">Grand Final</div>')

    sec_lbls = (
        f'<div style="position:absolute;left:{PAD}px;top:{PAD+HDR-18}px;font-size:12px;font-weight:800;'
        f'letter-spacing:.08em;color:#8fb4ff;font-family:\'DM Mono\',monospace">▲ WINNERS BRACKET</div>'
        f'<div style="position:absolute;left:0;right:0;top:{PAD+HDR+WBH+SG/2-1}px;height:1px;background:{BD_BORDER}"></div>'
        f'<div style="position:absolute;left:{PAD}px;top:{lb_top+HDR-18}px;font-size:12px;font-weight:800;'
        f'letter-spacing:.08em;color:#7ee0a3;font-family:\'DM Mono\',monospace">▼ LOSERS BRACKET</div>'
    )

    cards = "".join(_card_html(tie, nums.get(tie["id"], "?"), _match_pos(tie["id"])) for tie in bd["ties"].values())
    lines = _draw_lines()

    return f"""
    <div style="width:100%;min-height:{h+16}px;background:{BD_BG};padding:8px 0 8px 8px;box-sizing:border-box">
      <div style="color-scheme:dark;position:relative;width:{w}px;min-width:{w}px;height:{h}px;font-family:'Inter',sans-serif">
        <svg width="{w}" height="{h}" style="position:absolute;left:0;top:0">{lines}</svg>
        {sec_lbls}
        {hdrs}
        {cards}
      </div>
    </div>
    """