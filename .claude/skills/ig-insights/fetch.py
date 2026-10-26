"""Fetch Instagram stats for all tracked accounts.

Appends one line per account and one per reel to insights/history.jsonl (never
rewritten), then regenerates insights/latest.md from it, with the change since
the previous fetch in brackets.

Run from anywhere:  source ~/.instagram_tokens && python3 -I .claude/skills/ig-insights/fetch.py
Saves into the repo's own insights/ folder; times are recorded in IST (Asia/Kolkata).
"""
import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

API = "https://graph.instagram.com/v26.0"
# The repo root is three folders up from .claude/skills/ig-insights/, wherever the repo is checked out.
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "insights")
DIR = os.path.normpath(DIR)
IST = ZoneInfo("Asia/Kolkata")
HISTORY = os.path.join(DIR, "history.jsonl")
LATEST = os.path.join(DIR, "latest.md")
ACCOUNTS = ["AGENTINLOOP", "HOWITSENGINEERED", "LETSBUILDSIMPLY"]
METRICS = ["views", "reach", "likes", "comments", "shares", "saves"]


def get(path, token, **params):
    params["access_token"] = token
    with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(params)}", timeout=30) as r:
        return json.load(r)


def fetch(t):
    rows = []
    for acct in ACCOUNTS:
        token = os.environ[f"IG_{acct}_TOKEN"]
        me = get("me", token, fields="username,followers_count,follows_count,media_count")
        user = me["username"]
        rows.append({"t": t, "type": "account", "account": user, "followers": me["followers_count"],
                     "follows": me["follows_count"], "media_count": me["media_count"]})
        page = get("me/media", token, fields="id,caption,timestamp,permalink", limit=100)
        media = page["data"]
        while page.get("paging", {}).get("next"):
            with urllib.request.urlopen(page["paging"]["next"], timeout=30) as r:
                page = json.load(r)
            media += page["data"]
        for m in media:
            ins = get(f"{m['id']}/insights", token,
                      metric="views,reach,likes,comments,shares,saved,ig_reels_avg_watch_time")
            v = {x["name"]: x["values"][0]["value"] for x in ins["data"]}
            rows.append({"t": t, "type": "reel", "account": user, "id": m["id"], "permalink": m["permalink"],
                         "posted": m["timestamp"], "caption": (m.get("caption") or "").split("\n")[0][:80],
                         "views": v.get("views", 0), "reach": v.get("reach", 0), "likes": v.get("likes", 0),
                         "comments": v.get("comments", 0), "shares": v.get("shares", 0), "saves": v.get("saved", 0),
                         "avg_watch_s": round(v.get("ig_reels_avg_watch_time", 0) / 1000, 1)})
    return rows


def load_history():
    if not os.path.exists(HISTORY):
        return []
    with open(HISTORY) as f:
        return [json.loads(line) for line in f if line.strip()]


def fmt(new, old):
    if old is None or new == old:
        return f"{new:,}"
    return f"{new:,} ({'+' if new > old else ''}{new - old:,})"


def write_latest(history):
    # Sort as real times, not text: "+00:00" and "+05:30" stamps don't sort correctly as strings.
    times = sorted({r["t"] for r in history}, key=datetime.datetime.fromisoformat)
    now, prev_t = times[-1], (times[-2] if len(times) > 1 else None)
    key = lambda r: (r["type"], r["account"], r.get("permalink"))
    prev = {key(r): r for r in history if r["t"] == prev_t}
    cur = [r for r in history if r["t"] == now]
    when = datetime.datetime.fromisoformat(now).astimezone(IST).strftime("%Y-%m-%d %H:%M")
    since = f" since {datetime.datetime.fromisoformat(prev_t).astimezone(IST).strftime('%H:%M')}" if prev_t else ""
    out = ["# Instagram insights", "",
           f"Updated {when}. Change{since} is in brackets. Every fetch is kept in `history.jsonl`.", ""]
    for acct in [r for r in cur if r["type"] == "account"]:
        reels = [r for r in cur if r["type"] == "reel" and r["account"] == acct["account"]]
        old = prev.get(key(acct), {})
        total = sum(r["views"] for r in reels)
        old_total = sum(p["views"] for r in reels if (p := prev.get(key(r)))) if prev else None
        out += [f"## @{acct['account']}", "",
                f"**{fmt(acct['followers'], old.get('followers'))} followers** · {acct['media_count']} posts · "
                f"{fmt(total, old_total)} total views", "",
                "| Posted | Post | Views | Reach | Likes | Comments | Shares | Saves | Avg watch |",
                "|---|---|--:|--:|--:|--:|--:|--:|--:|"]
        for r in reels:
            p = prev.get(key(r), {})
            cells = " | ".join(fmt(r[m], p.get(m)) for m in METRICS)
            out.append(f"| {r['posted'][:10]} | [{r['caption'][:70]}]({r['permalink']}) | {cells} | {r['avg_watch_s']}s |")
        out.append("")
    with open(LATEST, "w") as f:
        f.write("\n".join(out))
    return cur, prev, key


if __name__ == "__main__":
    os.makedirs(DIR, exist_ok=True)
    t = datetime.datetime.now(IST).isoformat(timespec="seconds")
    rows = fetch(t)
    with open(HISTORY, "a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cur, prev, key = write_latest(load_history())
    # Print what moved since the previous fetch.
    for r in cur:
        p = prev.get(key(r))
        if r["type"] == "account":
            print(f"@{r['account']}: {fmt(r['followers'], p and p['followers'])} followers")
        elif p:
            moved = [f"{m} {fmt(r[m], p[m])}" for m in METRICS if r[m] != p[m]]
            if moved:
                print(f"  {r['caption'][:55]} | " + ", ".join(moved))
