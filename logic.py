"""
Tournament logic, ported 1:1 from the original HTML/JS build so behaviour
matches exactly: category-based ties for badminton (double elimination,
16 departments) and round-robin groups + single-elim knockout for
pickleball (22 pairs, 4 groups, top 4 advance to Round of 16).

All functions operate on plain dicts (JSON-serializable) so they can be
persisted straight into SQLite via db.get_state/set_state.
"""

import copy

# ───────────────────────── shared ─────────────────────────

BD_ROUND_INFO = {
    "W1": {"label": "WB Round 1", "pts": 15},
    "W2": {"label": "WB Quarter-Final", "pts": 15},
    "W3": {"label": "WB Semi-Final", "pts": 21},
    "W4": {"label": "WB Final", "pts": 21},
    "L1": {"label": "LB Round 1", "pts": 15},
    "L2": {"label": "LB Round 2", "pts": 15},
    "L3": {"label": "LB Round 3", "pts": 15},
    "L4": {"label": "LB Round 4", "pts": 15},
    "L5": {"label": "LB Semi-Final", "pts": 21},
    "L6": {"label": "LB Final", "pts": 21},
    "GF": {"label": "🏆 Grand Final", "pts": 21},
}
ALL_BD_ROUNDS = ["W1", "W2", "W3", "W4", "L1", "L2", "L3", "L4", "L5", "L6", "GF"]
BD_CATS = ["Mixed Doubles 1", "Men's Doubles", "Women's Doubles", "Mixed Doubles 2", "Tie-Breaker (Any Pairing)"]

ALL_PK_ROUNDS = ["GROUP", "K1", "K2", "K3", "GF"]
PK_ROUND_LABELS = {"GROUP": "Group Stage", "K1": "Round of 16", "K2": "Quarter-Final", "K3": "Semi-Final", "GF": "Final"}
PK_KO_ROUND_LABELS = {
    **{f"K1_{i}": "Round of 16" for i in range(8)},
    **{f"K2_{i}": "Quarter-Final" for i in range(4)},
    **{f"K3_{i}": "Semi-Final" for i in range(2)},
    "GF": "Final",
}


# ───────────────────────── badminton ─────────────────────────

def bd_blank_game():
    return {"p1": 0, "p2": 0, "finished": False}


def bd_blank_cat():
    return {"games": [bd_blank_game(), bd_blank_game(), bd_blank_game()]}


def bd_blank_tie(tie_id, wt=None, ws=0, lt=None, ls=0):
    return {
        "id": tie_id, "t1": "", "t2": "", "winner": None, "w1": 0, "w2": 0, "tbNeeded": False,
        "wt": wt, "ws": ws, "lt": lt, "ls": ls,
        "cats": [bd_blank_cat() for _ in range(5)],
    }


def bd_init():
    ties = {}

    def mk(tid, wt=None, ws=0, lt=None, ls=0):
        ties[tid] = bd_blank_tie(tid, wt, ws, lt, ls)

    mk("W1_0", "W2_0", 1, "L1_0", 1); mk("W1_1", "W2_0", 2, "L1_0", 2)
    mk("W1_2", "W2_1", 1, "L1_1", 1); mk("W1_3", "W2_1", 2, "L1_1", 2)
    mk("W1_4", "W2_2", 1, "L1_2", 1); mk("W1_5", "W2_2", 2, "L1_2", 2)
    mk("W1_6", "W2_3", 1, "L1_3", 1); mk("W1_7", "W2_3", 2, "L1_3", 2)
    mk("W2_0", "W3_0", 1, "L2_3", 2); mk("W2_1", "W3_0", 2, "L2_2", 2)
    mk("W2_2", "W3_1", 1, "L2_1", 2); mk("W2_3", "W3_1", 2, "L2_0", 2)
    mk("W3_0", "W4_0", 1, "L4_1", 2); mk("W3_1", "W4_0", 2, "L4_0", 2)
    mk("W4_0", "GF", 1, "L6_0", 2)
    mk("L1_0", "L2_0", 1); mk("L1_1", "L2_1", 1); mk("L1_2", "L2_2", 1); mk("L1_3", "L2_3", 1)
    mk("L2_0", "L3_0", 1); mk("L2_1", "L3_0", 2); mk("L2_2", "L3_1", 1); mk("L2_3", "L3_1", 2)
    mk("L3_0", "L4_0", 1); mk("L3_1", "L4_1", 1)
    mk("L4_0", "L5_0", 1); mk("L4_1", "L5_0", 2)
    mk("L5_0", "L6_0", 1)
    mk("L6_0", "GF", 2)
    mk("GF")
    return {"ties": ties, "open": {}}


def bd_cat_winner(cat):
    w1 = w2 = 0
    for g in cat["games"]:
        if not g["finished"]:
            continue
        if g["p1"] > g["p2"]:
            w1 += 1
        elif g["p2"] > g["p1"]:
            w2 += 1
        if w1 == 2 or w2 == 2:
            break
    if w1 == 2:
        return 1
    if w2 == 2:
        return 2
    return None


def bd_tie_tally(tie):
    cw = [bd_cat_winner(c) for c in tie["cats"][:4]]
    w1 = cw.count(1)
    w2 = cw.count(2)
    if w1 >= 3:
        return {"winner": 1, "w1": w1, "w2": w2, "tbNeeded": False}
    if w2 >= 3:
        return {"winner": 2, "w1": w1, "w2": w2, "tbNeeded": False}
    if w1 == 2 and w2 == 2:
        tb = bd_cat_winner(tie["cats"][4])
        if tb:
            return {"winner": tb, "w1": w1 + (1 if tb == 1 else 0), "w2": w2 + (1 if tb == 2 else 0), "tbNeeded": False}
        return {"winner": None, "w1": w1, "w2": w2, "tbNeeded": True}
    return {"winner": None, "w1": w1, "w2": w2, "tbNeeded": False}


def bd_clear_downstream(bd, tie):
    if tie.get("wt"):
        nt = bd["ties"].get(tie["wt"])
        if nt:
            if tie["ws"] == 1:
                nt["t1"] = ""
            else:
                nt["t2"] = ""
            if nt["winner"] is not None:
                nt["winner"] = None
                bd_clear_downstream(bd, nt)
    if tie.get("lt"):
        nt = bd["ties"].get(tie["lt"])
        if nt:
            if tie["ls"] == 1:
                nt["t1"] = ""
            else:
                nt["t2"] = ""
            if nt["winner"] is not None:
                nt["winner"] = None
                bd_clear_downstream(bd, nt)


def bd_recompute(bd, tie_id):
    tie = bd["ties"].get(tie_id)
    if not tie:
        return
    prev = tie["winner"]
    st = bd_tie_tally(tie)
    tie["winner"], tie["w1"], tie["w2"], tie["tbNeeded"] = st["winner"], st["w1"], st["w2"], st["tbNeeded"]
    if st["winner"] and st["winner"] != prev:
        wn = tie["t1"] if st["winner"] == 1 else tie["t2"]
        ln = tie["t2"] if st["winner"] == 1 else tie["t1"]
        if tie.get("wt"):
            nt = bd["ties"].get(tie["wt"])
            if nt:
                if tie["ws"] == 1:
                    nt["t1"] = wn
                else:
                    nt["t2"] = wn
        if tie.get("lt") and ln:
            nt = bd["ties"].get(tie["lt"])
            if nt:
                if tie["ls"] == 1:
                    nt["t1"] = ln
                else:
                    nt["t2"] = ln
    elif not st["winner"] and prev:
        if tie.get("wt"):
            nt = bd["ties"].get(tie["wt"])
            if nt:
                if tie["ws"] == 1:
                    nt["t1"] = ""
                else:
                    nt["t2"] = ""
                bd_clear_downstream(bd, nt)
        if tie.get("lt"):
            nt = bd["ties"].get(tie["lt"])
            if nt:
                if tie["ls"] == 1:
                    nt["t1"] = ""
                else:
                    nt["t2"] = ""
                bd_clear_downstream(bd, nt)


def bd_point(bd, tie_id, ci, gi, who, delta):
    g = bd["ties"][tie_id]["cats"][ci]["games"][gi]
    if g["finished"]:
        return
    key = f"p{who}"
    g[key] = max(0, g[key] + delta)


def bd_finish_game(bd, tie_id, ci, gi):
    g = bd["ties"][tie_id]["cats"][ci]["games"][gi]
    if g["p1"] == g["p2"]:
        return
    g["finished"] = True
    bd_recompute(bd, tie_id)


def bd_reopen_game(bd, tie_id, ci, gi):
    bd["ties"][tie_id]["cats"][ci]["games"][gi]["finished"] = False
    bd_recompute(bd, tie_id)


def bd_set_team(bd, tie_id, which, val):
    bd["ties"][tie_id][which] = val


def bd_reset_tie(bd, tie_id):
    tie = bd["ties"][tie_id]
    bd_clear_downstream(bd, tie)
    tie["cats"] = [bd_blank_cat() for _ in range(5)]
    tie["winner"], tie["w1"], tie["w2"], tie["tbNeeded"] = None, 0, 0, False


def bd_visible_games(games):
    show = [0]
    if games[0]["finished"]:
        show.append(1)
    if games[0]["finished"] and games[1]["finished"]:
        w0 = 1 if games[0]["p1"] > games[0]["p2"] else 2
        w1 = 1 if games[1]["p1"] > games[1]["p2"] else 2
        if w0 != w1:
            show.append(2)
    return show


def bd_current_activity(tie):
    """What's actually being played right now within a tie: which category,
    which game number, and the live score — for the monitor's 'Live Now' tiles."""
    for ci in range(4):
        cat = tie["cats"][ci]
        if bd_cat_winner(cat) is not None:
            continue
        vis = bd_visible_games(cat["games"])
        gi = vis[-1]
        g = cat["games"][gi]
        if g["finished"] and len(vis) < 3:
            continue  # that game's done; next game not opened yet
        return {"ci": ci, "cat_name": BD_CATS[ci], "game_no": gi + 1, "p1": g["p1"], "p2": g["p2"]}
    if tie["tbNeeded"]:
        cat = tie["cats"][4]
        vis = bd_visible_games(cat["games"])
        gi = vis[-1]
        g = cat["games"][gi]
        return {"ci": 4, "cat_name": BD_CATS[4], "game_no": gi + 1, "p1": g["p1"], "p2": g["p2"]}
    return None


BD_CAT_ABBR = ["MD1", "MD", "WD", "MD2", "TB"]


def bd_category_breakdown(tie):
    """Per-category status for every category in the tie, in order — used to
    render a historical strip (decided / live / not started) on monitor tiles.
    Includes finished_scores (list of 'p1-p2' strings, one per completed game)
    and current_score (the in-progress game's live 'p1-p2', or None)."""
    out = []
    for ci in range(5):
        cat = tie["cats"][ci]
        started = any(g["finished"] or g["p1"] > 0 or g["p2"] > 0 for g in cat["games"])
        if ci == 4 and not (tie["tbNeeded"] or started):
            continue  # hide the tie-breaker slot unless it's actually in play
        winner = bd_cat_winner(cat)

        finished_scores = [f'{g["p1"]}-{g["p2"]}' for g in cat["games"] if g["finished"]]
        current_score = None
        if winner is None:
            vis = bd_visible_games(cat["games"])
            last = cat["games"][vis[-1]]
            if not last["finished"] and (last["p1"] > 0 or last["p2"] > 0):
                current_score = f'{last["p1"]}-{last["p2"]}'

        out.append({
            "ci": ci, "abbr": BD_CAT_ABBR[ci], "name": BD_CATS[ci],
            "winner": winner, "started": started,
            "finished_scores": finished_scores, "current_score": current_score,
        })
    return out


visible_games = bd_visible_games  # alias: same best-of-3 reveal logic used by pickleball matches too


def bd_champion(bd):
    gf = bd["ties"].get("GF")
    if gf and gf["winner"]:
        return gf["t1"] if gf["winner"] == 1 else gf["t2"]
    return None


# ───────────────────────── pickleball ─────────────────────────

def pk_blank_game():
    return {"p1": 0, "p2": 0, "finished": False}


def pk_blank_match():
    return {"games": [pk_blank_game(), pk_blank_game(), pk_blank_game()], "winner": None}


def pk_init_default():
    groups = {
        "A": [{"name": ""} for _ in range(6)],
        "B": [{"name": ""} for _ in range(6)],
        "C": [{"name": ""} for _ in range(5)],
        "D": [{"name": ""} for _ in range(5)],
    }
    pk = {"groups": groups, "matches": {}, "ko": {}}
    pk["ko"] = pk_init_ko()
    return pk


def pk_init_ko():
    K = {}

    def mk(tid, wt=None, ws=0):
        K[tid] = {"id": tid, "t1": "", "t2": "", "wt": wt, "ws": ws, "winner": None,
                   "games": [pk_blank_game(), pk_blank_game(), pk_blank_game()]}

    mk("K1_0", "K2_0", 1); mk("K1_1", "K2_0", 2)
    mk("K1_2", "K2_1", 1); mk("K1_3", "K2_1", 2)
    mk("K1_4", "K2_2", 1); mk("K1_5", "K2_2", 2)
    mk("K1_6", "K2_3", 1); mk("K1_7", "K2_3", 2)
    mk("K2_0", "K3_0", 1); mk("K2_1", "K3_0", 2)
    mk("K2_2", "K3_1", 1); mk("K2_3", "K3_1", 2)
    mk("K3_0", "GF", 1); mk("K3_1", "GF", 2)
    mk("GF")
    return K


def pk_get_match(pk, grp, i, j):
    pk["matches"].setdefault(grp, {})
    key = f"{i}-{j}"
    if key not in pk["matches"][grp]:
        pk["matches"][grp][key] = pk_blank_match()
    return pk["matches"][grp][key]


def pk_get_match_if_exists(pk, grp, i, j):
    return pk["matches"].get(grp, {}).get(f"{i}-{j}")


def pk_match_winner(m):
    w1 = w2 = 0
    for g in m["games"]:
        if not g["finished"]:
            continue
        if g["p1"] > g["p2"]:
            w1 += 1
        elif g["p2"] > g["p1"]:
            w2 += 1
        if w1 == 2 or w2 == 2:
            break
    if w1 == 2:
        return 1
    if w2 == 2:
        return 2
    return None


def pk_point(pk, grp, i, j, gi, who, delta):
    m = pk_get_match(pk, grp, i, j)
    g = m["games"][gi]
    if g["finished"]:
        return
    key = f"p{who}"
    g[key] = max(0, g[key] + delta)


def pk_finish_game(pk, grp, i, j, gi):
    m = pk_get_match(pk, grp, i, j)
    g = m["games"][gi]
    if g["p1"] == g["p2"]:
        return
    g["finished"] = True
    m["winner"] = pk_match_winner(m)


def pk_reopen_game(pk, grp, i, j, gi):
    m = pk_get_match(pk, grp, i, j)
    m["games"][gi]["finished"] = False
    m["winner"] = pk_match_winner(m)


def pk_standings(pk, grp):
    pairs = pk["groups"][grp]
    n = len(pairs)
    stats = [{"idx": idx, "name": p["name"], "mw": 0, "ml": 0, "gw": 0, "gl": 0, "pf": 0, "pa": 0} for idx, p in enumerate(pairs)]
    for i in range(n):
        for j in range(i + 1, n):
            m = pk_get_match_if_exists(pk, grp, i, j)
            if not m:
                continue
            for g in m["games"]:
                if not g["finished"]:
                    continue
                stats[i]["pf"] += g["p1"]; stats[i]["pa"] += g["p2"]
                stats[j]["pf"] += g["p2"]; stats[j]["pa"] += g["p1"]
                if g["p1"] > g["p2"]:
                    stats[i]["gw"] += 1; stats[j]["gl"] += 1
                else:
                    stats[j]["gw"] += 1; stats[i]["gl"] += 1
            w = pk_match_winner(m)
            if w == 1:
                stats[i]["mw"] += 1; stats[j]["ml"] += 1
            elif w == 2:
                stats[j]["mw"] += 1; stats[i]["ml"] += 1
    for s in stats:
        s["diff"] = s["pf"] - s["pa"]
    stats.sort(key=lambda s: (-s["mw"], -s["gw"], -s["diff"]))
    return stats


def pk_add_pair(pk, grp):
    if len(pk["groups"][grp]) < 10:
        pk["groups"][grp].append({"name": ""})


def pk_remove_pair(pk, grp):
    if len(pk["groups"][grp]) > 4:
        pk["groups"][grp].pop()


def pk_set_pair_name(pk, grp, idx, val):
    pk["groups"][grp][idx]["name"] = val


def pk_ko_clear_downstream(pk, tie):
    if tie.get("wt"):
        nt = pk["ko"].get(tie["wt"])
        if nt:
            if tie["ws"] == 1:
                nt["t1"] = ""
            else:
                nt["t2"] = ""
            if nt["winner"] is not None:
                nt["winner"] = None
                pk_ko_clear_downstream(pk, nt)


def pk_ko_recompute(pk, tie_id):
    tie = pk["ko"].get(tie_id)
    if not tie:
        return
    prev = tie["winner"]
    w = pk_match_winner(tie)
    tie["winner"] = w
    if w and w != prev:
        wn = tie["t1"] if w == 1 else tie["t2"]
        if tie.get("wt"):
            nt = pk["ko"].get(tie["wt"])
            if nt:
                if tie["ws"] == 1:
                    nt["t1"] = wn
                else:
                    nt["t2"] = wn
    elif not w and prev:
        if tie.get("wt"):
            nt = pk["ko"].get(tie["wt"])
            if nt:
                if tie["ws"] == 1:
                    nt["t1"] = ""
                else:
                    nt["t2"] = ""
                pk_ko_clear_downstream(pk, nt)


def pk_ko_point(pk, tie_id, gi, who, delta):
    g = pk["ko"][tie_id]["games"][gi]
    if g["finished"]:
        return
    key = f"p{who}"
    g[key] = max(0, g[key] + delta)


def pk_ko_finish_game(pk, tie_id, gi):
    g = pk["ko"][tie_id]["games"][gi]
    if g["p1"] == g["p2"]:
        return
    g["finished"] = True
    pk_ko_recompute(pk, tie_id)


def pk_ko_reopen_game(pk, tie_id, gi):
    pk["ko"][tie_id]["games"][gi]["finished"] = False
    pk_ko_recompute(pk, tie_id)


def pk_ko_set_team(pk, tie_id, which, val):
    pk["ko"][tie_id][which] = val


def pk_ko_reset_tie(pk, tie_id):
    tie = pk["ko"][tie_id]
    pk_ko_clear_downstream(pk, tie)
    tie["games"] = [pk_blank_game(), pk_blank_game(), pk_blank_game()]
    tie["winner"] = None


def pk_champion(pk):
    gf = pk["ko"].get("GF")
    if gf and gf["winner"]:
        return gf["t1"] if gf["winner"] == 1 else gf["t2"]
    return None


def pk_group_qualified(pk):
    """Returns dict grp -> list of top-4 pair names (in standings order)."""
    out = {}
    for grp in ["A", "B", "C", "D"]:
        st = pk_standings(pk, grp)
        out[grp] = [(s["name"] or f"Pair {s['idx']+1}") for s in st[:4]]
    return out


def pk_auto_seed_ko(pk):
    """Auto-fill Round-of-16 slots from group standings (top 4 of each group),
    following the same A/D vs B/C cross-seeding used in the original design."""
    q = pk_group_qualified(pk)
    a, b, c, d = q["A"], q["B"], q["C"], q["D"]
    seed_pairs = [
        ("K1_0", a[0] if len(a) > 0 else ""), ("K1_1", b[3] if len(b) > 3 else ""),
        ("K1_2", c[0] if len(c) > 0 else ""), ("K1_3", d[3] if len(d) > 3 else ""),
        ("K1_4", b[0] if len(b) > 0 else ""), ("K1_5", a[3] if len(a) > 3 else ""),
        ("K1_6", d[0] if len(d) > 0 else ""), ("K1_7", c[3] if len(c) > 3 else ""),
    ]
    slots = {
        "K1_0": "t1", "K1_1": "t2", "K1_2": "t1", "K1_3": "t2",
        "K1_4": "t1", "K1_5": "t2", "K1_6": "t1", "K1_7": "t2",
    }
    for tid, name in seed_pairs:
        pk["ko"][tid][slots[tid]] = name
