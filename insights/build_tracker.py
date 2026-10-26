#!/usr/bin/env python3
"""Build insights/reels-tracker.html: every @talkingagents reel (live and deleted), what it is (original, cold open,
tight cut, remake), its latest stats and a short verdict. Live numbers come from the Graph API; deleted reels keep
their last known numbers from talkingagents-reels.json. Growth per hour comes from ta-tracker-snapshots.jsonl.

    source ~/.instagram_tokens && python3 insights/build_tracker.py
"""
import html, json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(os.path.join(DIR, "talkingagents-reels.json")))
SNAPS = os.path.join(DIR, "ta-tracker-snapshots.jsonl")  # one line per build: {t, views: {shortcode: n}}
OUT = os.path.join(DIR, "reels-tracker.html")
IST = timezone(timedelta(hours=5, minutes=30))
API = "https://graph.instagram.com/v26.0/"
TOKEN = os.environ["IG_TALKINGAGENTS_TOKEN"]
KIND = {"original": "Original", "cold": "Cold open", "tight": "Tight cut 1.1×", "remake": "Remake (new script)", "variant C": "Variant C (new opening)"}


def get(path, **q):
    q["access_token"] = TOKEN
    try:
        return json.load(urllib.request.urlopen(API + path + "?" + urllib.parse.urlencode(q), timeout=60))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error on {path}: {e.code} {e.read().decode()[:200].replace(TOKEN, '***')}")


now = datetime.now(IST)
me = get("me", fields="followers_count,media_count")
media = get("me/media", fields="id,timestamp,caption,permalink", limit=100)["data"]
live = {}
for m in media:
    sc = m["permalink"].rstrip("/").split("/")[-1]
    ins = get(m["id"] + "/insights", metric="views,reach,likes,shares,saved,comments,reels_skip_rate,ig_reels_avg_watch_time")
    d = {i["name"]: i["values"][0]["value"] for i in ins.get("data", [])}
    live[sc] = dict(posted=m["timestamp"], caption=(m.get("caption") or "").split("\n")[0], views=d.get("views", 0),
                    likes=d.get("likes", 0), shares=d.get("shares", 0), saves=d.get("saved", 0), comments=d.get("comments", 0),
                    skip=d.get("reels_skip_rate"), avg=d.get("ig_reels_avg_watch_time", 0) / 1000)

snaps = [json.loads(l) for l in open(SNAPS)] if os.path.exists(SNAPS) else []
# baseline: the newest snapshot at least 45 min old (else the oldest one), so rates are views per hour over a real interval
old = [x for x in snaps if (now - datetime.fromisoformat(x["t"])).total_seconds() >= 2700]
prev = old[-1] if old else (snaps[0] if snaps else {})
base_h = (now - datetime.fromisoformat(prev["t"])).total_seconds() / 3600 if prev else 0
rows = []
for sc, c in CAT["reels"].items():
    r = dict(sc=sc, **c)
    if sc in live:
        r.update(live[sc]); r["status"] = "live"
    else:
        r.update(c.get("last") or {"views": next((x["views"][sc] for x in reversed(snaps) if sc in x["views"]), 0), "skip": None,
                                     "posted": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")})
        r["status"] = "deleted"
        r.setdefault("why", "Deleted")
        for k in ("likes", "shares", "saves", "avg", "caption"):
            r.setdefault(k, None)
    r["posted_dt"] = datetime.fromisoformat(r["posted"].replace("+0000", "+00:00")).astimezone(IST)
    r["age_h"] = (now - r["posted_dt"]).total_seconds() / 3600
    p = prev.get("views", {}).get(sc)
    r["delta"] = None if p is None or r["status"] != "live" else r["views"] - p
    r["rate"] = None if r["delta"] is None or base_h < 0.25 else r["delta"] / base_h
    rows.append(r)
for sc, m in live.items():  # a live reel missing from the catalog still shows up, so nothing is hidden
    if sc not in CAT["reels"]:
        dt = datetime.fromisoformat(m["posted"].replace("+0000", "+00:00")).astimezone(IST)
        rows.append(dict(sc=sc, ep=0, kind="original", status="live", posted_dt=dt, age_h=(now - dt).total_seconds() / 3600, delta=None, rate=None, **m))

orig = {r["ep"]: r for r in rows if r["kind"] == "original"}


def verdict(r):
    """(tone, short note): tone is good | ok | weak | early | gone."""
    if r["status"] == "deleted":
        return "gone", r.get("why", "")
    if r["age_h"] < 3 or r["skip"] is None:
        return "early", f"{r['age_h']:.0f} h old"
    s = r["skip"]
    flat = r["rate"] is not None and r["rate"] < 15 and r["age_h"] > 12
    tail = ", views flat" if flat else ""
    if r["kind"] == "original":
        word = "Strong hook" if s <= 33 else "Average hook" if s <= 40 else "Weak hook"
        return ("good" if s <= 33 else "ok" if s <= 40 else "weak"), word + tail
    o = orig.get(r["ep"])
    if not o or o.get("skip") is None:
        return "ok", "No original to compare" + tail
    d = o["skip"] - s
    if d >= 5:
        return "good", f"Hooks {d:.0f} pts better than original" + tail
    if d > -3:
        return ("weak" if flat else "ok"), "Same as original" + tail
    return "weak", f"Hooks {-d:.0f} pts worse than original" + tail


for r in rows:
    r["tone"], r["note"] = verdict(r)

with open(SNAPS, "a") as f:
    f.write(json.dumps({"t": now.isoformat(), "views": {r["sc"]: r["views"] for r in rows if r["status"] == "live"}}) + "\n")

# ---------- decisions: what to delete, what to wait on ----------
SHORT = {"original": "Original", "cold": "Cold open", "tight": "Tight 1.1×", "remake": "Remake", "variant C": "Variant C"}


def trend(r):
    if r["status"] != "live":
        return "", ""
    if r["age_h"] < 3:
        return "new", "● new"
    if r["rate"] is None:
        return "", ""
    k = "up" if r["rate"] >= 60 else "slow" if r["rate"] >= 15 else "stall"
    return k, f'{"▲" if k == "up" else "▸" if k == "slow" else "■"} +{r["rate"]:.0f}/h'


todo = []
for r in rows:
    r["tk"], r["tt"] = trend(r)
    r["act"] = None
    if r["status"] != "live" or r["kind"] == "original" or r["tone"] == "early":
        continue
    sib = [x for x in rows if x["ep"] == r["ep"] and x is not r and x["status"] == "live" and x.get("skip") is not None]
    better = min(sib, key=lambda x: x["skip"]) if sib else None
    if r.get("flag") and better and better["skip"] <= r["skip"] - 3:
        r["act"] = f'Has a glitch and the {SHORT[better["kind"]].lower()} hooks better ({better["skip"]:.0f}% vs {r["skip"]:.0f}%)'
    elif r["tone"] == "weak" and r["tk"] == "stall" and better and better["skip"] < r["skip"] and better["views"] > r["views"]:
        r["act"] = "No better than the original and views have stopped"
    if r["act"]:
        todo.append(r)


def ep_verdict(rs, ep):
    lv = [r for r in rs if r["status"] == "live"]
    if any(r["act"] for r in lv):
        k = next(r for r in lv if r["act"])
        return "act", f'Delete {SHORT[k["kind"]].lower()}?'
    if any(r["tk"] in ("new", "up") for r in lv):
        k = next(r for r in lv if r["tk"] in ("new", "up"))
        return "wait", f'Wait: {SHORT[k["kind"]].lower()} still growing'
    best = min((r for r in lv if r.get("skip") is not None), key=lambda r: r["skip"], default=None)
    if best and best["tone"] == "good":
        return "ok", f'Keep · best: {SHORT[best["kind"]].lower()}'
    return "ok", "Keep"


# ---------- page: a plain "right now" box, what to do, then one short line per live reel grouped by episode ----------
# Each line shows only: original or copy, views, and one status word. Tap a line for the details.
E = html.escape
WORD = {"good": "Good", "ok": "OK", "weak": "Weak", "early": "New"}
COPY = {"cold": "Copy · cold open", "tight": "Copy · shorter cut", "remake": "Copy · remake", "variant C": "Copy · new opening (variant C)"}
order = {"original": 0, "cold": 1, "tight": 2, "remake": 3, "variant C": 4}
live_rows = [r for r in rows if r["status"] == "live"]
gone_rows = sorted([r for r in rows if r["status"] == "deleted"], key=lambda r: (r["ep"], order[r["kind"]]))
total = sum(r["views"] for r in live_rows)
copies = [r for r in live_rows if r["kind"] != "original"]
bugs = [r for r in live_rows if r.get("flag")]
stories = sorted({r["ep"] for r in live_rows})
since = datetime.fromisoformat(prev["t"]).strftime("%H:%M") if prev else None
grow = sum(r["delta"] or 0 for r in live_rows)
nxt = CAT.get("upcoming", [])


def k(n):
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


def line(r):
    orig_ = r["kind"] == "original"
    label = "Original" if orig_ else COPY[r["kind"]]
    bug = '<span class="bug">⚠ bug</span>' if r.get("flag") else ""
    sk = "–" if r.get("skip") is None else f'{r["skip"]:.0f}%'
    det = [f'{E(r["note"])}.', f'{sk} swipe away in the first seconds (lower is better).',
           f'Posted {r["posted_dt"].strftime("%d %b %H:%M")}' + (f', {r["tt"].split(" ", 1)[-1]}' if r["tt"] and r["tk"] != "new" else "") + "."]
    if r.get("flag"):
        det.append(f'<b class="bugt">Bug: {E(r["flag"])}</b>')
    if r["act"]:
        det.append(f'<b class="bugt">Suggest delete: {E(r["act"])}</b>')
    return (f'<details class="r{" o" if orig_ else ""}"><summary><span class="lab">{label}</span>'
            f'<span class="vw">{r["views"]:,}</span><span class="st {r["tone"]}">{WORD[r["tone"]]}</span>{bug}</summary>'
            f'<div class="det">{" ".join(f"<p>{d}</p>" for d in det)}'
            f'<a href="https://www.instagram.com/reel/{r["sc"]}/">Open on Instagram</a></div></details>')


groups = []
for ep in stories:
    rs = sorted([r for r in live_rows if r["ep"] == ep], key=lambda r: (order[r["kind"]], r["posted_dt"]))
    n = sum(r["kind"] != "original" for r in rs)
    tag = "" if n <= 0 else f'<span class="cp">+{n} cop{"y" if n == 1 else "ies"}</span>'
    if not any(r["kind"] == "original" for r in rs):
        tag += '<span class="cp">original deleted</span>'
    groups.append(f'<section class="g"><h3><span class="epn">Ep {ep}</span><span class="t">{E(CAT["episodes"].get(str(ep), "?"))}</span>{tag}</h3>'
                  f'{"".join(line(r) for r in rs)}</section>')
for u in nxt:
    groups.append(f'<section class="g soon"><h3><span class="epn">Ep {u["ep"]}</span><span class="t">{E(CAT["episodes"].get(str(u["ep"]), ""))}</span>'
                  f'<span class="cp">not posted</span></h3><p class="up">{E(u["status"])}.</p></section>')

todo_html = "".join(f'<li><a class="do" href="https://www.instagram.com/reel/{r["sc"]}/">Delete</a><span><b>Ep {r["ep"]} {("original" if r["kind"] == "original" else COPY[r["kind"]].split(" · ")[1])}</b>'
                    f'<small>{E(r["act"])}</small></span></li>' for r in todo)
posting = ("Up next: " +" ".join(f'Ep {u["ep"]}: {E(u["status"])}.' for u in nxt)) if nxt else "Nothing is posting and nothing is queued."
gone_html = "".join(f'<li><span>Ep {r["ep"]} {"original" if r["kind"] == "original" else COPY[r["kind"]].split(" · ")[1]}</span>'
                    f'<span class="vw">{r["views"]:,}</span><small>{E(r.get("why", ""))}</small></li>' for r in gone_rows)

page = f"""<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>talkingagents Reel Tracker</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {{
  --bg: #eef0f3; --panel: #ffffff; --fg: #1b2130; --muted: #5f687a; --line: #e1e4ea;
  --accent: #d9622b; --good: #187148; --good-bg: #dff2e7; --ok: #7a5a0c; --ok-bg: #f5ead0;
  --weak: #a3362a; --weak-bg: #f6dfdb; --early: #3f4b66; --early-bg: #e4e8f0; --on: #ffffff;
  --display: "Bricolage Grotesque", "Avenir Next", system-ui, sans-serif;
  --body: "IBM Plex Sans", "Helvetica Neue", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #111419; --panel: #1a1e26; --fg: #e8ebf1; --muted: #9aa3b5; --line: #2a303b;
  --accent: #f0814a; --good: #7dd8a5; --good-bg: #16321f; --ok: #e8c66a; --ok-bg: #342b12;
  --weak: #f4998b; --weak-bg: #3a1c18; --early: #b9c3d7; --early-bg: #252b37; --on: #111419; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --bg: #111419; --panel: #1a1e26; --fg: #e8ebf1; --muted: #9aa3b5; --line: #2a303b;
  --accent: #f0814a; --good: #7dd8a5; --good-bg: #16321f; --ok: #e8c66a; --ok-bg: #342b12;
  --weak: #f4998b; --weak-bg: #3a1c18; --early: #b9c3d7; --early-bg: #252b37; --on: #111419; color-scheme: dark }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.4 var(--body); margin: 0;
  padding: 16px max(16px, env(safe-area-inset-right, 0px)) 32px max(16px, env(safe-area-inset-left, 0px)); }}
.wrap {{ max-width: 640px; margin: 0 auto; display: grid; gap: 14px; }}
h1 {{ font: 700 24px/1.1 var(--display); margin: 0; }} h1 b {{ color: var(--accent); }}
.stamp {{ color: var(--muted); font: 12px var(--mono); margin-top: 4px; }}
.box {{ background: var(--panel); border-radius: 12px; padding: 14px; display: grid; gap: 10px; }}
.nums {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; text-align: center; }}
.nums b {{ display: block; font: 700 22px/1.1 var(--display); font-variant-numeric: tabular-nums; }}
.nums span {{ color: var(--muted); font-size: 12px; }}
.nums .warn b {{ color: var(--weak); }}
.say {{ margin: 0; padding-top: 10px; border-top: 1px solid var(--line); color: var(--muted); font-size: 14px; }}
.say b {{ color: var(--fg); font-weight: 600; }}
h2 {{ margin: 0; font: 600 12px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
.todo ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
.todo li {{ display: flex; gap: 10px; align-items: center; }}
.todo li span {{ display: grid; }} .todo small {{ color: var(--muted); font-size: 13px; }}
.do {{ flex: none; font: 600 12px/1 var(--mono); text-transform: uppercase; padding: 9px 11px; border-radius: 8px; color: var(--on); background: var(--weak); text-decoration: none; }}
.g {{ background: var(--panel); border-radius: 12px; padding: 4px 14px; }}
.g h3 {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 8px; margin: 0; padding: 10px 0 8px; font: 600 15px/1.3 var(--body); border-bottom: 1px solid var(--line); }}
.epn {{ font: 600 13px var(--mono); color: var(--accent); }}
.t {{ flex: 1 1 60%; min-width: 0; }}
.cp {{ font: 500 12px var(--mono); color: var(--muted); }}
.r {{ border-bottom: 1px solid var(--line); }} .r:last-child {{ border-bottom: 0; }}
summary {{ list-style: none; display: grid; grid-template-columns: 1fr auto 56px; grid-template-areas: "lab vw st" "bug bug bug"; gap: 0 12px; align-items: center; padding: 10px 0; cursor: pointer; }}
summary::-webkit-details-marker {{ display: none; }}
summary:focus-visible, a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.lab {{ grid-area: lab; color: var(--muted); }} .o .lab {{ color: var(--fg); font-weight: 600; }}
.vw {{ grid-area: vw; font: 500 15px var(--mono); font-variant-numeric: tabular-nums; text-align: right; }}
.st {{ grid-area: st; justify-self: end; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }}
.st.good {{ color: var(--good); background: var(--good-bg); }} .st.ok {{ color: var(--ok); background: var(--ok-bg); }}
.st.weak {{ color: var(--weak); background: var(--weak-bg); }} .st.early {{ color: var(--early); background: var(--early-bg); }}
.bug {{ grid-area: bug; font-size: 12px; font-weight: 600; color: var(--weak); }}
.det {{ padding: 0 0 12px; font-size: 13px; color: var(--muted); }} .det p {{ margin: 0 0 4px; }}
.bugt {{ color: var(--weak); font-weight: 600; }}
.det a {{ color: var(--accent); font-weight: 600; }}
.soon {{ background: transparent; border: 1px dashed var(--line); }}
.up {{ margin: 8px 0 10px; color: var(--muted); font-size: 13px; }}
.gone summary {{ display: block; padding: 0; color: var(--muted); font-size: 14px; }}
.gone ul {{ list-style: none; margin: 10px 0 0; padding: 0; display: grid; gap: 8px; }}
.gone li {{ display: grid; grid-template-columns: 1fr auto; font-size: 14px; }}
.gone small {{ grid-column: 1 / -1; color: var(--muted); font-size: 12px; }}
.key {{ color: var(--muted); font-size: 12px; margin: 0; }}
@media (min-width: 900px) {{ .wrap {{ max-width: 1100px; grid-template-columns: 1fr 1fr; align-items: start; }} .full {{ grid-column: 1 / -1; }} }}
</style>
<div class="wrap">
<div class="full"><h1>@talkingagents <b>reels</b></h1><div class="stamp">Updated {now.strftime("%d %b, %H:%M")} IST</div></div>
<section class="box full">
 <div class="nums"><div><b>{len(live_rows)}</b><span>reels live</span></div><div><b>{len(stories)}</b><span>stories</span></div>
  <div><b>{len(copies)}</b><span>copies</span></div><div><b>{k(total)}</b><span>views</span></div></div>
 <p class="say"><b>{posting}</b> {len(bugs)} live reels have a bug (marked ⚠).{f" Views +{grow:,} since {since}." if since else ""} {me.get("followers_count", 0):,} followers.</p>
</section>
{f'<section class="box todo full"><h2>Do now</h2><ul>{todo_html}</ul></section>' if todo else ""}
{"".join(groups)}
<details class="box gone full"><summary>Deleted ({len(gone_rows)}) ▾</summary><ul>{gone_html}</ul></details>
<p class="key full">Status: Good = most people keep watching. Weak = many swipe away early. Copies are compared with their original. Tap any line for details.</p>
</div>
"""
open(OUT, "w").write(page)
print(f"wrote {OUT}: {len(live_rows)} live, {len(rows) - len(live_rows)} deleted, {total:,} views, {len(todo)} to-do")
