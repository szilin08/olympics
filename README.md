# LBS × MGB Sports Tournament — Streamlit App

A Streamlit port of the tournament draw/scoring HTML, split into two access levels:

- **Viewer (no login):** live monitors, bracket status, group standings, department rosters. No input controls.
- **Admin (shared password):** everything viewers see, plus team entry, live score entry, resets, and round scheduling.

Data is stored in **SQLite** (one file, `tournament.db`), so it works out of the box with zero external
services. Every score button click writes straight to the database, so anyone with the page open sees the
latest state on their next refresh — no separate "save" step.

## 1. Run it locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and set your real admin_password
streamlit run app.py
```

Open the sidebar → **🔒 Admin login** → enter the password from `secrets.toml` to unlock the input pages.
Anyone without the password only ever sees the read-only viewer pages.

## 2. Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repo (`tournament.db` will be created automatically on first run — don't
   commit a stale one, or add it to `.gitignore`).
2. On [share.streamlit.io](https://share.streamlit.io), point a new app at `app.py`.
3. In the app's **Settings → Secrets**, paste:
   ```toml
   admin_password = "your-real-password"
   ```
4. Deploy. That's it — SQLite lives on the app's own disk, no database server needed.

**Important caveat for Community Cloud:** the filesystem is not guaranteed to persist across redeploys or
app restarts/sleeps on the free tier. For a one-off event this is usually fine (the app stays awake while
people are using it), but if you want guaranteed durability across restarts, see the MongoDB note below.

## 3. Swapping in MongoDB later

Everything reads/writes through `db.get_state(key)` / `db.set_state(key, value)` in `db.py`. To move to
MongoDB: replace the body of those two functions with `collection.find_one({"_id": key})` /
`collection.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)` using `pymongo`. Nothing
in `logic.py`, `state.py`, or the page files needs to change, since they only ever call `db.get_state` /
`db.set_state`.

## Visual theme

Restyled to match a navy-sidebar / gold-accent / white-card dashboard look:
- Dark navy sidebar with a logo block, gold section labels, and a user/role chip at the bottom.
- Gold primary buttons, gold-underlined active tabs.
- Card-style expanders (rounded, bordered, subtle shadow) instead of flat Streamlit defaults.
- A breadcrumb + title + subtitle header block at the top of every page, with a status chip on the right
  (e.g. "Live" / "Admin mode").
- Standings and bracket-status lists now render as leaderboard rows — rank, name, colored pills, a
  progress bar, and a percentage — instead of plain tables.

**Honest limitation:** this is CSS layered onto Streamlit's real components (`theme.py`), not a rebuilt
component library. Buttons, inputs, and expanders are still Streamlit elements underneath, so spacing and
interaction quirks are Streamlit-native even though the palette/card language now matches. The one thing
that genuinely can't be replicated in Streamlit is a hand-drawn SVG bracket-line view (connecting lines
between matches) — that needs custom canvas/SVG, which doesn't fit Streamlit's component model.

## Badminton views (matches your reference screenshots)

- **Admin → List / Scoring**: a card grid, one column per round (WB Round 1, WB Quarter-Final, …), each
  card showing the two team-name fields and a live score. Click **Score ▸** on any card to open a modal
  with the full category-by-category, game-by-game scoring — same interaction as "click a match to open
  its scoreboard" in the original.
- **Admin & Viewer → Bracket View**: the connected-line tree (winners bracket on top, losers bracket below,
  solid lines routing winners forward, dashed lines routing losers down), geometry ported directly from the
  original HTML's positioning math so it lines up the same way.
- **Viewer → Live Monitor**: a dark "big screen" grid — a "Live Now" strip at the top for in-progress ties,
  then every round laid out as a card grid below, read-only.

Pickleball still uses the earlier expander-based admin layout — say the word if you'd like the same
card-grid/dialog/bracket-view treatment applied there too.

## Architecture

```
app.py            entrypoint, sidebar nav, routes to viewer or admin pages
auth.py           shared-password admin unlock (session-based)
db.py             SQLite key/value store (JSON blobs) + audit log
logic.py          pure bracket/scoring logic, ported 1:1 from the original JS
                     - badminton: fixed 16-team double-elimination bracket,
                       5-category ties (first to 3 category wins, 2-2 → tie-breaker)
                     - pickleball: 4 round-robin groups (22 pairs) + single-elim
                       Round of 16 → QF → SF → Final, cross-seeded from group standings
state.py          load/save helpers bridging logic.py structures and db.py
data.py           LBS/MGB department roster reference data (view-only)
ui.py             shared score-entry row / status badge widgets
pages_public.py   viewer pages (Overview, Badminton Monitor, Pickleball Monitor, Standings)
pages_admin.py    admin-only pages (Badminton Admin, Pickleball Admin, Schedule & Settings)
```

## Known limitations / things to double-check before the event

- **One shared admin password**, not per-person accounts. Anyone with the password has full input access
  (matches what you asked for — say the word if you'd rather have named admin accounts with separate
  passwords later, it's a small change to `auth.py`).
- If two admins are editing **the exact same field** in the same second, last write wins (normal for a
  live-scoring tool; there's an audit log on the Settings page to see who changed what).
- Team-name text boxes: because of how Streamlit widgets remember typed values, if a name is changed from
  a *different device* while you have that same tie's edit box open, your box won't visually refresh until
  you collapse/reopen that tie's expander. The saved data itself is always correct — this only affects the
  live text box display.
- Change `admin_password` in secrets before your real event — the fallback default is `changeme123`.
