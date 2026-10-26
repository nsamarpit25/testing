#!/usr/bin/env python3
"""Instagram API (Instagram Login) helper for @letsbuildsimply (copy of how-its-engineered/tools/ig.py).

  python3 tools/ig.py check                      # token works? which account?
  python3 tools/ig.py stats [--n 10]             # account + per-reel numbers
  python3 tools/ig.py refresh                    # extend the 60-day token
  python3 tools/ig.py post VIDEO --cover PNG --caption TXT --yes
  python3 tools/ig.py post VIDEO ... --trial manual|auto --yes   # trial reel: non-followers only at first
  python3 tools/ig.py post VIDEO --video-url URL --cover-url URL ...   # files already public, no S3

The token is IG_LETSBUILDSIMPLY_TOKEN in the repo .env and is never printed.
Instagram fetches the video and cover from a URL, so `post` stages them in a private
S3 bucket (presigned links valid 1 h). They're deleted as soon as Instagram has processed
the video; the bucket's 1-day expiry is only a fallback.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

API = "https://graph.instagram.com/v26.0"
TOKEN_FILE, TOKEN_VAR = Path(__file__).resolve().parents[2] / ".env", "IG_LETSBUILDSIMPLY_TOKEN"
BUCKET, REGION, PROFILE = "hie-reel-staging-30c239", "ap-south-1", "manmeet"
REEL_METRICS = ["views", "reach", "likes", "comments", "shares", "saved",
                "total_interactions", "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


def token():
    if not TOKEN_FILE.exists():
        sys.exit(f"No token file at {TOKEN_FILE}.")
    for line in TOKEN_FILE.read_text().splitlines():
        k, _, v = line.removeprefix("export ").partition("=")
        if k.strip() == TOKEN_VAR and v.strip().strip('"'):
            return v.strip().strip('"')
    sys.exit(f"{TOKEN_VAR} not set in {TOKEN_FILE}.")


def call(method, path, params=None, base=API):
    params = dict(params or {})
    params["access_token"] = token()
    q = urllib.parse.urlencode(params)
    url = f"{base}/{path}" if method == "POST" else f"{base}/{path}?{q}"
    req = urllib.request.Request(url, data=q.encode() if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").replace(params["access_token"], "<token>")
        raise RuntimeError(f"{method} {path} -> {e.code}: {body}") from None


def me():
    return call("GET", "me", {"fields": "user_id,username,account_type,followers_count,media_count"})


def cmd_check(a):
    m = me()
    print(json.dumps(m, indent=2))
    lim = call("GET", f"{m['user_id']}/content_publishing_limit", {"fields": "quota_usage,config"})
    print("publishing limit:", json.dumps(lim.get("data", lim)))


def reel_insights(media_id):
    try:
        d = call("GET", f"{media_id}/insights", {"metric": ",".join(REEL_METRICS)})
        return {x["name"]: x["values"][0]["value"] for x in d["data"]}
    except RuntimeError:  # one unsupported metric fails the batch, so fall back to one by one
        out = {}
        for m in REEL_METRICS:
            try:
                d = call("GET", f"{media_id}/insights", {"metric": m})
                out[m] = d["data"][0]["values"][0]["value"]
            except RuntimeError:
                pass
        return out


def cmd_stats(a):
    m = me()
    print(f"@{m['username']}  followers {m.get('followers_count')}  posts {m.get('media_count')}\n")
    media = call("GET", f"{m['user_id']}/media",
                 {"fields": "id,caption,media_product_type,timestamp,permalink", "limit": a.n})["data"]
    rows = []
    for x in media:
        s = reel_insights(x["id"])
        title = (x.get("caption") or "").split("\n")[0][:38]
        rows.append({"date": x["timestamp"][:10], "title": title, **s, "url": x["permalink"]})
    if a.json:
        print(json.dumps(rows, indent=2)); return
    cols = ["views", "reach", "likes", "comments", "shares", "saved"]
    print(f"{'date':10}  {'title':38}  " + "  ".join(f"{c:>8}" for c in cols) + "  avg watch")
    for r in rows:
        aw = r.get("ig_reels_avg_watch_time")
        aw = f"{aw / 1000:.1f}s" if isinstance(aw, (int, float)) else "-"
        print(f"{r['date']:10}  {r['title']:38}  " + "  ".join(f"{r.get(c, '-'):>8}" for c in cols) + f"  {aw:>9}")


def cmd_refresh(a):
    d = call("GET", "refresh_access_token", {"grant_type": "ig_refresh_token"}, base="https://graph.instagram.com")
    lines = [f"export {TOKEN_VAR}={d['access_token']}" if l.removeprefix("export ").startswith(TOKEN_VAR + "=") else l
             for l in TOKEN_FILE.read_text().splitlines()]
    TOKEN_FILE.write_text("\n".join(lines) + "\n"); TOKEN_FILE.chmod(0o600)
    print(f"Token refreshed, valid for {d.get('expires_in', 0) // 86400} more days.")


# keys in the environment (e.g. from .env) win; otherwise use the named profile
AWS = ["aws", "--region", REGION] + ([] if os.environ.get("AWS_ACCESS_KEY_ID") else ["--profile", PROFILE])
STAGED = []  # S3 keys uploaded by this run, deleted once Instagram has fetched them


def stage(path):
    key = f"{int(time.time())}-{Path(path).name}"
    subprocess.run(AWS + ["s3", "cp", str(path), f"s3://{BUCKET}/{key}", "--only-show-errors"], check=True)
    STAGED.append(key)
    return subprocess.run(AWS + ["s3", "presign", f"s3://{BUCKET}/{key}", "--expires-in", "3600"],
                          check=True, capture_output=True, text=True).stdout.strip()


def unstage():
    for key in STAGED:
        subprocess.run(AWS + ["s3", "rm", f"s3://{BUCKET}/{key}", "--only-show-errors"], check=True)
    if STAGED:
        print(f"deleted {len(STAGED)} staged file(s) from S3")
    STAGED.clear()


def cmd_post(a):
    caption = Path(a.caption).read_text().strip()
    if not a.yes:
        sys.exit("Refusing to post without --yes.")
    uid = me()["user_id"]
    is_variant = bool(a.trial and re.search(r'-t\d+\.mp4$', a.video))
    if is_variant:
        recent = call("GET", f"{uid}/media", {"fields": "caption,permalink", "limit": 100})["data"]
        duplicate = next((m for m in recent if m.get("caption", "").strip() == caption), None)
        if duplicate:
            print("Already published; skipping duplicate:", duplicate["permalink"], flush=True)
            return
    params = {"media_type": "REELS", "caption": caption, "share_to_feed": "true"}
    if a.video_url:  # already hosted somewhere public (e.g. a temporary tunnel), so skip S3
        params["video_url"] = a.video_url
        if a.cover_url:
            params["cover_url"] = a.cover_url
    else:
        params["video_url"] = stage(a.video)
        if a.cover:
            params["cover_url"] = stage(a.cover)
    if a.trial:  # trial reel: shown to non-followers first; graduate in the app (manual) or on performance (auto)
        params["trial_params"] = json.dumps({"graduation_strategy": {"manual": "MANUAL", "auto": "SS_PERFORMANCE"}[a.trial]})
    try:
        cid = call("POST", f"{uid}/media", params)["id"]
    except RuntimeError:
        unstage()
        raise
    print("container", cid, "- waiting for Instagram to process the video")
    for _ in range(60):
        st = call("GET", cid, {"fields": "status_code,status"})
        if st["status_code"] == "FINISHED":
            unstage()  # Instagram has its copy now
            break
        if st["status_code"] in ("ERROR", "EXPIRED"):
            unstage()
            sys.exit(f"Processing failed: {st}")
        time.sleep(10)
    else:
        # Instagram may still be downloading, so the staged files stay; the bucket expires them after 1 day.
        sys.exit("Still processing after 10 min; re-run publish later with the container id.")
    if is_variant:
        # Compare actual publication times, not scheduler start times. Recheck
        # after waiting because another HIE post may have gone live meanwhile.
        while True:
            recent = call("GET", f"{uid}/media", {"fields": "timestamp", "limit": 10})["data"]
            latest = max((datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp()
                          for m in recent), default=0)
            delay = latest + 20 * 60 + 5 - time.time()
            if delay <= 0:
                break
            print(f"Publication spacing: waiting {delay:.0f}s after latest HIE post", flush=True)
            time.sleep(min(delay, 60))
    mid = call("POST", f"{uid}/media_publish", {"creation_id": cid})["id"]
    print("published:", call("GET", mid, {"fields": "permalink"})["permalink"])


p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("check").set_defaults(f=cmd_check)
s = sub.add_parser("stats"); s.add_argument("--n", type=int, default=10); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_stats)
sub.add_parser("refresh").set_defaults(f=cmd_refresh)
s = sub.add_parser("post"); s.add_argument("video"); s.add_argument("--cover"); s.add_argument("--caption", required=True)
s.add_argument("--trial", choices=["manual", "auto"])
s.add_argument("--video-url", help="public URL of the video; skips S3 staging")
s.add_argument("--cover-url", help="public URL of the cover, used with --video-url")
s.add_argument("--yes", action="store_true"); s.set_defaults(f=cmd_post)
a = p.parse_args()
try:
    a.f(a)
except RuntimeError as e:
    sys.exit(str(e))
