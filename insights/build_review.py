#!/usr/bin/env python3
"""Build insights/review/index.html: every @talkingagents reel that was uploaded (live and deleted) and every finished
video that was never posted, each with a playable preview, its numbers, whether its views are climbing or flat, and a
short note on what is wrong with it. Serve it with insights/review_server.py (videos need a server with Range support).

    source ~/.instagram_tokens && python3 insights/build_review.py [--check]

--check runs claude-talk-v2/scripts/cutcheck.py on every video not checked yet (results cached by md5 in
insights/review/checks.json). Live numbers come from the Graph API when the token is set, else from history.jsonl.
"""
import glob, hashlib, html, json, os, re, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(DIR)
OUT = os.path.join(DIR, "review")
CTV = os.path.join(REPO, "claude-talk-v2")
IST = timezone(timedelta(hours=5, minutes=30))
CAT = json.load(open(os.path.join(DIR, "talkingagents-reels.json")))
KIND = {"original": "Original", "cold": "Cold open", "tight": "Tight re-cut", "remake": "Remake", "variant C": "Variant C"}

# the exact file that was uploaded (md5-matched with the poster's queue), or for Ep1-5 originals the final render made
# just before the upload time
FILE = {
    "DepT2tBz3rg": "output/ep1_full_hq.mp4", "DeqiIxDtMcS": "output/ep2_full_hq.mp4",
    "Der9pjFzBEp": "output/ep3_reupload.mp4", "DetP40XN2gp": "output/ep4_final_1080x1920.mp4",
    "DeuUvcZTh5S": "output/ep5_final_1080x1920_v3.mp4", "DeunDHHip1m": "output/posted/02_ep2_tight/video.mp4",
    "DeuqwlglNhh": "output/ep6_final_1080x1920_v2.mp4", "DeuuVtiDydl": "output/posted/04_ep4_tight/video.mp4",
    "Deux6JaiXiq": "output/posted/05_ep1_cold/video.mp4", "Deu1fH7AvxS": "output/posted/06_ep5_tight/video.mp4",
    "Deu5ENKDrUL": "output/posted/07_ep3_tight/video.mp4", "Deu8pHkjs7D": "output/posted/08_ep6_cold/video.mp4",
    "DevARh1ARzY": "output/posted/09_ep1_tight/video.mp4", "DevD1zyEZwB": "output/posted/10_ep6_tight/video.mp4",
    "DevHXkwjrkC": "output/posted/11_ep3_cold/video.mp4", "DevPU3XlBR8": "output/posted/12_ep2_cold/video.mp4",
    "DevS5AwilR6": "output/posted/13_ep5_cold/video.mp4", "DevWdzcD_YO": "output/new/ep8_final2.mp4",
    "DevZ_79E5-v": "output/new/ep9_final2.mp4", "Devdhj5gq_e": "output/new/ep7_final.mp4",
    "DevhFgPEbnV": "output/new/ep3b_final2.mp4", "DevksKyEzNv": "output/new/ep4b_final2.mp4",
    "DevoQ0dD6T3": "output/new/ep1b_final.mp4", "Devr1FTkoUb": "output/posted/20_ep8_cold/video.mp4",
    "Dev70uICnZI": "output/new/ep10_final2.mp4", "DewOPkTjG6E": "output/new/ep11_final.mp4",
    "DewrvfvDs_b": "output/new/ep12_final_sync.mp4",
    "DexWx3HiEfL": "output/new/ep5c_final.mp4", "DeyQHPbCTHj": "output/new/ep8_final2.mp4",
    "Deyz8hkCuGo": "output/new/ep10b_final.mp4",
}
# reels posted from a hold folder (ops/*_hold/post.log names the file and the shortcode), so new posts show up on their own
POSTED = {}
for log in glob.glob(os.path.join(CTV, "ops", "*_hold", "post.log")):
    txt = open(log).read()
    files, codes = re.findall(r" for (\S+\.mp4)", txt), re.findall(r"published: \S+/reel/([\w-]+)/", txt)
    if files and codes:
        POSTED[codes[-1]] = os.path.relpath(files[-1], CTV)
for sc, rel in POSTED.items():
    FILE.setdefault(sc, rel)
POSTED_FILES = {rel: sc for sc, rel in POSTED.items()}
MATCHED_BY_TIME = {"DepT2tBz3rg", "DeqiIxDtMcS", "Der9pjFzBEp", "DetP40XN2gp", "DeuUvcZTh5S"}

# what is wrong with each live reel, in plain words (deleted reels use the catalog's "why")
NOTES = {
    "DetP40XN2gp": ["Most views on the account.", "Mouth is the old loudness-driven oval, so lip sync is loose."],
    "Der9pjFzBEp": ["Second-best reel.", "Old oval mouth: lip sync is loose."],
    "DeuqwlglNhh": ["Still the fastest-growing reel.", "Old oval mouth: lip sync is loose."],
    "DeqiIxDtMcS": ["Weak opening: about half of viewers swipe away in the first seconds.", "The phone buzz is the sound that stops dead.",
                    "Old oval mouth: lip sync is loose."],
    "DevksKyEzNv": ["Best hook on the account (fewest swipe-aways).", "Old oval mouth: lip sync is loose."],
    "DevZ_79E5-v": ["The phone buzz is the sound that stops dead.", "Old oval mouth: lip sync is loose."],
    "Devdhj5gq_e": ["Choppy cuts: three quick shots back to back.", "Old oval mouth: lip sync is loose."],
    "DevoQ0dD6T3": ["Old oval mouth: lip sync is loose."],
    "Deyz8hkCuGo": ["Ep10b: new opening, new line 3 and new ending on the Ep10 middle. Codex PASS before upload.",
                    "Old oval mouth: lip sync is loose."],
    "DeyQHPbCTHj": ["Re-post of the deleted Ep8 Original (same file); you approved it with the known cut-off \"For seven years?\" at 33 s.",
                    "Old oval mouth: lip sync is loose."],
    "DewrvfvDs_b": ["Posted as a normal reel: trial reels need more followers.", "Voice timing fixed (final sync).",
                    "Old oval mouth: lip sync is loose."],
}
# finished videos that were never uploaded
DRAFTS = [
    ("output/new/ep5c_final.mp4", 5, "old",
     ["Posted 22 Oct 02:49 IST as DexWx3HiEfL (your yes in chat); now on the Live tab.", "Variant C opening: \"Claude. Either my CSS is haunted, or I am.\" / \"What happened?\" / \"I made this button green eleven times...\" (new voice take, lines 1-3).",
      "New render for lines 1-4 only, spliced at the line 5 camera cut onto the Ep5 Original from \"I saved!\" on; old-screen flashes covered.", "Old oval mouth: lip sync is loose."]),
    ("output/new/ep8_final2.mp4", 8, "old",
     ["Posted 22 Oct 11:09 IST as DeyQHPbCTHj (your yes in chat); now on the Live tab.",
      "Same file as the deleted Ep8 Original (DevWdzcD_YO, 1,673 views, 33% swipe away).", "Old oval mouth: lip sync is loose."]),
    ("output/new/ep10b_final.mp4", 10, "old",
     ["Posted 22 Oct 16:22 IST as Deyz8hkCuGo (your yes in chat); now on the Live tab. Codex PASS; text-free cover in ops/ep10b_hold.",
      "Ep10b: new opening \"Claude, how do I unsend one email... from forty thousand inboxes?\", line 3 re-recorded without the laugh, new ending \"Tell them it took years of practice.\"",
      "New render for frames 1-390 and 1437-1562 only, spliced at camera cuts onto the Ep10 middle; voice timing measured within 0.01 s on every line.",
      "Old oval mouth: lip sync is loose.", "Pace: 92 words in 49.5 s (about 1.86/s), slower than the kept reels (about 2.1)."]),
    ("output/new/ep14_final.mp4", 14, "review",
     ["New, made overnight (normal format): fetch() resolves on a 500, so the failed checkout shows confetti; Claude adds the response.ok check.",
      "Sunset look, teal hoodie. Script picked from Codex + Argon reviews.", "22 Oct fix: the red \"Order failed\" screen flashed for 0.47 s at 45 s; the cut to Cleo now comes on \"It actually failed!\" so the screen holds 1.2 s (53 frames re-rendered and spliced).", "Codex PASS (22 Oct) after fixes: code now shows the POST and the throw line no longer runs off the screen; \"failure\" at 29 s no longer cut off. Gemini still hears a stumble at 30-31 s that I could not confirm; worth a listen.", "Cover: text-free Cleo close-up (ops/night/covers/ep14_cover.jpg). Caption draft in ops/night/captions.md.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep15_final.mp4", 15, "review",
     ["New, made overnight (experiment): Claude teaches CORS on a little whiteboard on the desk (new BOARD camera), guest-list idea.",
      "Morning look, mustard hoodie. Board drawing changes only on cuts.", "Finished 22 Oct: frames 1251-1714 rendered on the PC and AWS, joined with captions and audio; sync 0 ms.", "Codex PASS (22 Oct, round 3) after fixes: six whiteboard close-ups (new BOARDCU camera), full localhost URL on the console, captions keep \"unless your origin...\" together with a thicker outline, stray \"t\" before \"New address\" removed.", "Cover: text-free Cleo close-up (ops/night/covers/ep15_cover.jpg). Caption draft in ops/night/captions.md.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep16_final.mp4", 16, "review",
     ["New, made overnight (experiment): Claude narrates Cleo like a nature documentary, to camera (new DOC camera), then teaches git bisect.",
      "Night look, green hoodie. Hushed narration is slower than usual on purpose.", "v3: monitor ghosting, a stray \"t\" blip and frozen Cleo in the DOC shots fixed.", "Codex PASS (22 Oct). Gemini 7.8: flags the known TTS splice on \"earlier\" at 29.5 s.", "Cover: text-free Cleo close-up (ops/night/covers/ep16_cover.jpg). Caption draft in ops/night/captions.md.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep17_final.mp4", 17, "review",
     ["New (emotional, no lesson): \"Battery 3%\". A storm cuts the power; Claude stays on his own battery to keep Cleo company, nudges her to answer her mom, goes quiet at zero, the lights come back, two goodnights, Mom replies.",
      "Night look, lavender hoodie. Slow rain in the window, rain sound at 5%. New: room lights, Claude's glow and the power cut are animated (power_track).",
      "Codex PASS on v1 and v2 (22 Oct; nits: Mom's text is small in the phone insert, the opening wide shot runs 9 s). Gemini 7.5 FIX on v1; v2 fixes: the \"Claude?\" shot in the dark showed only two eye dots (room floor raised), Cleo glances at her phone on \"I'll answer her\", softer phone buzz, no stiff hand gesture on lines 1 and 13.",
      "Cover: text-free Cleo close-up lit by Claude's glow (ops/night/covers/ep17_cover.jpg).", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep19_final.mp4", 19, "review",
     ["New overnight (23 Oct): \"Management Material\". Cleo has to explain Claude's deck to the execs; her vision was \"make something good\" and she asked \"done yet?\" eleven times, so Mark proposes her for Team Lead. Claude: \"Apparently, we're management now.\"",
      "Sunset look, blue hoodie. Script picked from Codex + Argon reviews of viral reel formats (ops/night/ideas/viral2/reels.md).",
      "Codex PASS and Argon 9.5 PASS (23 Oct, v9; nits: the promotion screen and the opening email are a bit dense to read in time). Fixed along the way: a Cleo fragment spliced into Claude's line 12, the HR email chime now lands before \"He already wrote it down\", varied hand gestures (no repeated chop, no clipping clasped hands), Cleo's arm no longer in the promotion-screen shot, and the cut back to Claude comes as he starts talking. Sync 0 ms, no flash cuts.",
      "Cover: text-free frame (ops/ep19_hold/cover.jpg). Caption in ops/ep19_hold/caption.txt.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep20_final.mp4", 20, "next",
     ["New overnight (23 Oct): \"Past Me Is A Hater\". At 1:14 AM Claude blocks Cleo's card on a seventh $89 planner; daytime Cleo left a note, \"Rules for 1 AM me\", that predicts every excuse, including the last one.",
      "Night look, rust hoodie.",
      "Codex PASS (23 Oct; nits: Cleo's two-hands-up gesture repeats, the final slump could be bigger). Argon 7.5-8.2 across runs; its audio flags (\"now\", \"gift\", line 12) were each re-checked clip by clip and came back clean. Fixed from Argon: smoother opening head turn, Claude's \"Rule three\" comes in right away, no frozen hands after line 3, a stray \"t\" splice removed. Sync 0 ms, no flash cuts.",
      "Cover: text-free frame (ops/ep20_hold/cover.jpg). Caption in ops/ep20_hold/caption.txt.", "Up next (owner, 23 Oct). Not scheduled; it posts only after your yes."]),
    ("output/new/ep21_final.mp4", 21, "next",
     ["New overnight (23 Oct): \"Quitting Tomorrow\". Cleo quits AI for 24 hours from midnight (Claude wrote the announcement); with 30 seconds left she sets her clock to Hawaii so it's \"still today\" and asks for one more email. Claude: \"Aloha. Who are we emailing?\"",
      "Night look, blue hoodie.",
      "Codex PASS (23 Oct). Argon 9.2 PASS on v3, 8.5 on v5; its \"AI-free\" audio flag re-checked clean. Fixed from Argon: no dead beat before \"Wait\", the ending now shows Cleo typing and then holds the \"Per my last email...\" screen ~1.3 s before the fade (was a 0.4 s flash of Cleo). Sync 0 ms, no flash cuts.",
      "Cover: text-free frame (ops/ep21_hold/cover.jpg). Caption in ops/ep21_hold/caption.txt.", "Up next after Ep20 (owner, 23 Oct). Not scheduled; it posts only after your yes."]),
    ("output/new/ep23_final.mp4", 23, "review",
     ["New (24 Oct): \"The Whole Team\". Cleo's \"twelve employees\" are Claude in four tabs (design, finance, legal); the client's legal team replies with \"Sure! Here's your legal reply.\" Claude: \"Then this meeting could have been two prompts.\"",
      "Sunset look, purple hoodie. Picked from fresh research on the top-running reels (the \"my team is just Claude\" trend), scripts judged by Codex + Argon (ops/night/ideas/viral3).",
      "Codex PASS and Argon 9 PASS (v3). Fixed along the way: a split leak between lines 11 and 12, the MON cut moved so no shot flashes, Cleo's hand no longer clips into the monitor shot, big readable email text. Sync 0 ms, no flash cuts.",
      "Cover: text-free frame (ops/ep23_hold/cover.jpg). Caption in ops/ep23_hold/caption.txt.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep24_final.mp4", 24, "review",
     ["New (24 Oct): \"I Asked For A Grocery List\". The list says only water; Claude logged nine Tuesdays of spinach (nine bought, zero eaten) and already ordered her usual Pad Thai. \"The water is for the spice.\"",
      "Night look, green hoodie. Picked from the same research + Codex/Argon judging.",
      "Codex PASS (v2 and v3). Argon 8.5 on v2; fixed from it: \"Claude\" no longer sounds like \"Clode\", the glitchy \"Thai\" re-recorded, the cut-off \"spice\" (split leak) fixed, the final receipt now holds longer with bigger text. Still there: the phone screen sits a little off its body (model issue from earlier episodes). Sync 0 ms, no flash cuts.",
      "Cover: text-free frame (ops/ep24_hold/cover.jpg). Caption in ops/ep24_hold/caption.txt.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep22_final.mp4", 22, "review",
     ["New (24 Oct): \"Explain The Cloud Like I'm Five\". Rule: no computer words, first one loses. The cloud is a big company's giant basement; Cleo blurts \"someone else's computer\" and loses; her box holds 12,000 money-saving screenshots that have only made the basement rich.",
      "Morning look, coral hoodie, whiteboard on the desk (BOARD/BOARDCU). Picked from the same research + Codex/Argon judging.",
      "Codex PASS and Argon 9 PASS (v2; nit: the caption splits \"someone else's computer\" across two chunks). Fixed from v1: a split leak between lines 10 and 11, the board drawings (a real cloud outline), the ending now holds on the whiteboard close-up. Sync 0 ms, no flash cuts.",
      "Cover: text-free frame (ops/ep22_hold/cover.jpg). Caption in ops/ep22_hold/caption.txt.", "Not in any queue; it posts only after your yes."]),
    ("output/new/ep10_final_sync.mp4", 10, "variant",
     ["Not used: Ep10b replaced it.", "Voice timing fixed: the deleted upload played every line 1.0 s early (mixer bug). Same picture, new audio mix; measured 0.00 s off.",
      "Old oval mouth: lip sync is loose (no m/b/p closes, no \"oo\" rounding).", "Pace: 88 words in 50 s (about 1.75/s), slower than the kept reels (about 2.1)."]),
    ("output/new/ep5_from_claude.mp4", 5, "variant",
     ["Not used: you picked variant C.", "Ep5 Original trimmed to start when she says \"Claude\" (the repeated cold-open line is gone).",
      "The two 2-frame old-screen flashes (16.3 s, 43.3 s) are covered.", "Old oval mouth: lip sync is loose."]),
    ("output/new/ep12_final.mp4", 12, "old", ["Replaced by ep12_final_sync: voice played 1 s early (mixer bug)."]),
    ("output/new/ep10_final.mp4", 10, "old", ["First Ep10 render; the uploaded one was ep10_final2."]),
    ("output/new/ep9_final.mp4", 9, "old", ["First Ep9 render; the uploaded one was ep9_final2."]),
    ("output/new/ep8_final.mp4", 8, "variant", ["First Ep8 render; ep8_final2 replaced it."]),
    ("output/ep6_final_1080x1920.mp4", 6, "old", ["Earlier Ep6 render; replaced by v2 (uploaded)."]),
    ("output/ep6_clean_1080x1920.mp4", 6, "old", ["Ep6 render without captions."]),
    ("output/ep5_final_1080x1920.mp4", 5, "variant", ["Ep5 v1; replaced by v3 (uploaded)."]),
    ("output/ep5_final_1080x1920_v2.mp4", 5, "variant", ["Ep5 v2; replaced by v3 (uploaded)."]),
    ("output/ep4_1080p.mp4", 4, "old", ["Early Ep4 encode; replaced by the 1080x1920 final (uploaded)."]),
    ("output/ep3_full_hq.mp4", 3, "old", ["Ep3 v1; replaced by the re-upload version."]),
    ("output/ep3_full_hq_v2.mp4", 3, "old", ["Ep3 v2; replaced by the re-upload version."]),
]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def api_live():
    tok = os.environ.get("IG_TALKINGAGENTS_TOKEN")
    if not tok:
        return None, None
    base = "https://graph.instagram.com/v26.0/"

    def get(path, **q):
        q["access_token"] = tok
        try:
            return json.load(urllib.request.urlopen(base + path + "?" + urllib.parse.urlencode(q), timeout=60))
        except Exception as e:  # never echo the URL (it carries the token)
            raise SystemExit(f"API error on {path}: {type(e).__name__}")
    me = get("me", fields="followers_count")
    live = {}
    for m in get("me/media", fields="id,timestamp,caption,permalink", limit=100)["data"]:
        sc = m["permalink"].rstrip("/").split("/")[-1]
        ins = get(m["id"] + "/insights", metric="views,reach,likes,shares,saved,comments,reels_skip_rate,ig_reels_avg_watch_time")
        d = {i["name"]: i["values"][0]["value"] for i in ins.get("data", [])}
        live[sc] = dict(posted=m["timestamp"], caption=(m.get("caption") or "").split("\n")[0], views=d.get("views", 0),
                        likes=d.get("likes", 0), comments=d.get("comments", 0), shares=d.get("shares", 0),
                        saves=d.get("saved", 0), skip=d.get("reels_skip_rate"), avg=d.get("ig_reels_avg_watch_time", 0) / 1000,
                        permalink=m["permalink"])
    return me["followers_count"], live


# ---------------------------------------------------------------- history: views over time per reel, followers
rows = [json.loads(l) for l in open(os.path.join(DIR, "history.jsonl")) if l.strip()]
ta = [r for r in rows if r.get("account") == "talkingagents"]
series = {}
for r in ta:
    if r["type"] == "reel" and r.get("views") is not None:
        sc = r["permalink"].rstrip("/").split("/")[-1]
        series.setdefault(sc, []).append((datetime.fromisoformat(r["t"]), r["views"]))
for v in series.values():
    v.sort()
fol = sorted((datetime.fromisoformat(r["t"]), r["followers"]) for r in ta if r["type"] == "account")

now = datetime.now(IST)
followers, live = api_live()
if live is None:  # no token: the newest fetch in history stands in for the API
    last_t = max(t for v in series.values() for t, _ in v)
    live = {}
    for r in ta:
        if r["type"] == "reel" and datetime.fromisoformat(r["t"]) == last_t:
            sc = r["permalink"].rstrip("/").split("/")[-1]
            live[sc] = dict(posted=r["posted"], caption=r.get("caption", ""), views=r["views"], likes=r.get("likes"),
                            comments=r.get("comments"), shares=r.get("shares"), saves=r.get("saves"), skip=None,
                            avg=r.get("avg_watch_s"), permalink=r["permalink"])
    followers, now = fol[-1][1], last_t
else:
    for sc, m in live.items():  # this build's numbers count as a point in the series
        series.setdefault(sc, []).append((now, m["views"]))


def trend(sc):
    """views gained over the newest window of at least 3 h, as (gain, hours, per hour)"""
    pts = series.get(sc, [])
    if len(pts) < 2:
        return None
    t1, v1 = pts[-1]
    older = [p for p in pts if (t1 - p[0]).total_seconds() >= 3 * 3600]
    t0, v0 = older[-1] if older else pts[0]
    h = (t1 - t0).total_seconds() / 3600
    return (v1 - v0, h, (v1 - v0) / h) if h > 0.2 else None


def status(rate, age_h):
    if age_h < 3:
        return "new", "New"
    if rate is None:
        return "flat", "No data"
    if rate >= 20:
        return "up", "Climbing"
    if rate >= 5:
        return "slow", "Slowing"
    return "flat", "Stalled"


# ---------------------------------------------------------------- cutcheck results, cached by md5
os.makedirs(os.path.join(OUT, "v"), exist_ok=True)
os.makedirs(os.path.join(OUT, "t"), exist_ok=True)
CK = os.path.join(OUT, "checks.json")
checks = json.load(open(CK)) if os.path.exists(CK) else {}


def check(path):
    key = md5(path)
    if key not in checks and "--check" in sys.argv:
        p = subprocess.run([sys.executable, os.path.join(CTV, "scripts/cutcheck.py"), path, os.path.join(OUT, "cuts", key[:8])],
                           capture_output=True, text=True)
        short = re.findall(r"^\s+([\d.]+)-\s*([\d.]+)s\s+\(([\d.]+)s\)", p.stdout, re.M)
        chops = re.findall(r"^\s+([\d.]+)s\s+sound cut off", p.stdout, re.M)
        checks[key] = dict(short=[[float(a), float(c)] for a, _, c in short], chops=[float(t) for t in chops])
        json.dump(checks, open(CK, "w"), indent=1)
    return checks.get(key)


def media(key, rel):
    """symlink the video into the site and make a small poster frame; returns (video url, poster url) or None"""
    src = os.path.join(CTV, rel)
    if not os.path.exists(src):
        return None
    v, t = os.path.join(OUT, "v", key + ".mp4"), os.path.join(OUT, "t", key + ".jpg")
    if os.path.islink(v) or os.path.exists(v):
        os.remove(v)
    os.symlink(src, v)
    cover = COVERS.get(rel)
    if cover and os.path.exists(os.path.join(CTV, cover)):  # the chosen cover is the poster
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(CTV, cover), "-vf", "scale=360:-2", "-q:v", "4", t])
    elif not os.path.exists(t):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2.5", "-i", src, "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", t])
    return f"v/{key}.mp4", f"t/{key}.jpg"


# text-free covers (Cleo close-up, eyes visible, hands down), rendered clean on the PC
COVERS = {f"output/new/ep{n}_final.mp4": f"ops/night/covers/ep{n}_cover.jpg" for n in (14, 15, 16, 17)}

# short "shots" that are only the phone lighting up in a held shot (checked by eye on the cutcheck strips)
SCREEN_ONLY = {"output/ep4_final_1080x1920.mp4": [66.37], "output/ep2_full_hq.mp4": [26.33]}


def check_notes(c, rel):
    if c is None:
        return []
    short = [(a, d) for a, d in c["short"] if round(a, 2) not in SCREEN_ONLY.get(rel, [])]
    out = [f"1-frame flash at {a:.1f} s: the old screen shows for a frame after a cut." if d < 0.15 else
           f"Very short shot ({d:.2f} s) at {a:.1f} s." for a, d in short]
    if c["chops"]:
        out.append("Sound stops dead (no fade) at " + " and ".join(f"{t:.1f} s" for t in c["chops"]) + ".")
    return out or ["Cut check passed: no flash cuts, no chopped audio."]


def ist(s):
    return datetime.fromisoformat(s.replace("+0000", "+00:00")).astimezone(IST)


# ---------------------------------------------------------------- cards
# "variant": other versions of an Up next episode; they show only as chips on its Up next row
cards = {"live": [], "next": [], "review": [], "deleted": [], "old": [], "variant": []}
DRAFT_NOTES = {rel: notes for rel, _, _, notes in DRAFTS}
for sc, c in CAT["reels"].items():
    key = sc.replace("-", "_")
    rel = FILE.get(sc)
    m = media(key, rel) if rel else None
    ck = check(os.path.join(CTV, rel)) if m else None
    title = f"Ep{c['ep']} · {KIND[c['kind']]}"
    topic = CAT["episodes"].get(str(c["ep"]), "")
    if sc in live:
        L = live[sc]
        age = (now - ist(L["posted"])).total_seconds() / 3600
        tr = trend(sc)
        k, word = status(tr[2] if tr else None, age)
        notes = (NOTES.get(sc) or [n for n in DRAFT_NOTES.get(rel, []) if not n.startswith("Not in any queue")]) + check_notes(ck, rel)
        cards["live"].append(dict(sc=sc, title=title, topic=topic, m=m, views=L["views"], tr=tr, k=k, word=word, age=age,
                                  likes=L.get("likes"), comments=L.get("comments"), shares=L.get("shares"), saves=L.get("saves"),
                                  skip=L.get("skip"), avg=L.get("avg"), link=L["permalink"], notes=notes,
                                  caption=L.get("caption", ""), byt=sc in MATCHED_BY_TIME,
                                  posted=L["posted"]))
    else:
        last = c.get("last") or {}
        if not last and sc in series:
            last = {"views": series[sc][-1][1]}
        notes = [c.get("why", "Deleted")] + ([f"Known bug: {c['flag']}."] if c.get("flag") and c["flag"] not in c.get("why", "") else [])
        cards["deleted"].append(dict(sc=sc, title=title, topic=topic, m=m, views=last.get("views"), skip=last.get("skip"),
                                     posted=last.get("posted"), notes=notes, byt=sc in MATCHED_BY_TIME))
for i, (rel, ep, kind, notes) in enumerate(DRAFTS):
    key = "d_" + re.sub(r"\W", "_", os.path.basename(rel)[:-4])
    m = media(key, rel)
    if not m:
        continue
    ck = check(os.path.join(CTV, rel))
    if rel in POSTED_FILES and kind in ("next", "review"):  # posted since: it lives on the Live tab now
        P = live.get(POSTED_FILES[rel])
        when = f" {ist(P['posted']):%d %b %H:%M} IST" if P else ""
        kind, notes = "old", [f"Posted{when} as {POSTED_FILES[rel]}; now on the Live tab."] + [n for n in notes if not n.startswith("Not in any queue")]
    label = re.sub(r"^ep\d+_|\.mp4$", "", os.path.basename(rel)).replace("_1080x1920", "").replace("_", " ")
    label = {"ep5c_final.mp4": "Variant C", "ep5_from_claude.mp4": "Trimmed to start on \"Claude\"",
             "ep5_final_1080x1920.mp4": "v1 render", "ep5_final_1080x1920_v2.mp4": "v2 render",
             "ep8_final2.mp4": "Original", "ep8_final.mp4": "First render", "ep10_final_sync.mp4": "Timing fixed",
             "ep10b_final.mp4": "Ep10b new opening + ending",
             "ep14_final.mp4": "fetch confetti", "ep15_final.mp4": "CORS whiteboard (experiment)", "ep16_final.mp4": "git bisect documentary (experiment)",
             "ep17_final.mp4": "Battery 3% (emotional)", "ep19_final.mp4": "Management Material",
             "ep20_final.mp4": "Past Me Is A Hater", "ep21_final.mp4": "Quitting Tomorrow",
             "ep22_final.mp4": "Explain The Cloud Like I'm Five", "ep23_final.mp4": "The Whole Team",
             "ep24_final.mp4": "I Asked For A Grocery List"}.get(os.path.basename(rel), label)
    cards[kind].append(dict(title=f"Ep{ep} · {label}", ep=ep, topic=f'{CAT["episodes"].get(str(ep), "")} · {os.path.basename(rel)}', m=m,
                            made=datetime.fromtimestamp(os.path.getmtime(os.path.join(CTV, rel)), IST),
                            notes=notes + (check_notes(ck, rel) if kind in ("next", "review") else [])))

cards["live"].sort(key=lambda x: -x["views"])
cards["deleted"].sort(key=lambda x: -(x["views"] or 0))

# ---------------------------------------------------------------- headline numbers and the plain-words summary
today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
f0 = [f for t, f in fol if t <= today0] or [fol[0][1]]
fol_today = followers - f0[-1]
total = sum(x["views"] for x in cards["live"])
gain = sum(x["tr"][0] for x in cards["live"] if x["tr"])
hrs = max((x["tr"][1] for x in cards["live"] if x["tr"]), default=0)
up = [x for x in cards["live"] if x["k"] == "up"]
slow = [x for x in cards["live"] if x["k"] == "slow"]
flat = [x for x in cards["live"] if x["k"] == "flat"]


def nm(x):
    return x["title"].replace(" · ", " ")


summary = [f"{len(cards['live'])} reels live, {total:,} views in all; {gain:+,} views in the last {hrs:.1f} h. "
           f"Followers {followers} ({fol_today:+d} today)."]
if up:
    summary.append("Climbing: " + ", ".join(f"{nm(x)} (+{x['tr'][2]:.0f}/h)" for x in up) + ".")
if slow:
    summary.append("Slowing: " + ", ".join(f"{nm(x)} (+{x['tr'][2]:.0f}/h)" for x in slow) + ".")
if flat:
    summary.append("Stalled: " + ", ".join(f"{nm(x)} ({x['views']:,})" for x in flat) + ".")
REPOST = {"DeqiIxDtMcS": "Ep2 Original has stalled but people who watched it engaged (42 likes, 5 comments). Suggestion only: "
                         "a remake with a stronger first line (as a normal reel: this account can't post Trial Reels yet). "
                         "Its problem is the opening, not the story."}
sugg = [REPOST[x["sc"]] for x in flat if x["sc"] in REPOST]
summary.append(f"{len(cards['next'])} up next, {len(cards['review'])} waiting for your review. Nothing is queued; nothing will post without your yes.")
summary.append(f"{len(cards['deleted'])} uploaded reels were deleted (tap a row for the reason).")


# ---------------------------------------------------------------- page: one list, in upload order, then the unposted ones
E = html.escape


def ago(dt):
    h = (now - dt).total_seconds() / 3600
    d, hh = int(h // 24), int(h % 24)
    return (f"{d} d {hh} h ago" if d else f"{hh} h ago" if hh else f"{int(h * 60)} min ago")


items = []
for x in cards["live"] + cards["deleted"]:
    dt = ist(x["posted"]) if x.get("posted") else now
    live_ = "k" in x
    tr = x.get("tr")
    items.append(dict(
        title=x["title"], topic=x["topic"], m=x["m"], notes=x["notes"], dt=dt,
        k=x["k"] if live_ else "gone", word=x["word"] if live_ else "Deleted",
        when=f"Uploaded {ago(dt)} · {dt.strftime('%-d %b, %H:%M')} IST", short=f"Uploaded {ago(dt)}",
        views=x.get("views"), rate=(f"+{tr[2]:.0f}/h" if live_ and tr else ""),
        stats=[] if not live_ else [
            ("Views", f"{x['views']:,}"), ("Recent", f"+{tr[0]:,} in {tr[1]:.1f} h" if tr else "–"),
            ("Swipe away", f"{x['skip']:.0f}%" if x.get("skip") is not None else "–"),
            ("Avg watch", f"{x['avg']:.0f} s" if x.get("avg") else "–"), ("Likes", f"{x['likes']:,}"),
            ("Comments", f"{x['comments']:,}"), ("Shares", f"{x['shares']:,}"), ("Saves", f"{x['saves']:,}")],
        last=(f"Last seen {x['views']:,} views" + (f" · {x['skip']:.0f}% swipe away" if x.get("skip") is not None else "")
              if not live_ and x.get("views") else "Views were not recorded before it was deleted." if not live_ else ""),
        link=x.get("link"), byt=x.get("byt"), ep=int(re.match(r"Ep(\d+)", x["title"]).group(1)),
        sc=x["sc"], r=tr[2] if live_ and tr else None, skip=x.get("skip"), avg=x.get("avg") if live_ else None,
        likes=x.get("likes"), comments=x.get("comments"), shares=x.get("shares"), saves=x.get("saves"),
        caption=x.get("caption", "")))
items.sort(key=lambda i: i["dt"])
for n, i in enumerate(items, 1):
    i["n"] = n
unposted = []


def drafts(kind, word):
    # Up next keeps the queue order from DRAFTS; the other lists show the newest file first
    rows = cards[kind] if kind == "next" else sorted(cards[kind], key=lambda x: x["made"], reverse=True)
    for q, x in enumerate(rows, 1):
        pre = f"#{q} in queue · " if kind == "next" else ""
        vs = [v for v in sorted(cards["variant"], key=lambda v: v["made"], reverse=True) if v["ep"] == x["ep"]] if kind == "next" else []
        unposted.append(dict(title=x["title"], topic=x["topic"], m=x["m"], notes=x["notes"], k=kind, word=word,
                             ep=x["ep"], vars=vs,
                             dt=x["made"], when=f"Made {ago(x['made'])} · {x['made'].strftime('%-d %b, %H:%M')} IST", short=f"{pre}Made {ago(x['made'])}",
                             views=None, rate="",
                             stats=[], last="", link=None, byt=False, n="", gone=False))


# the 10 h gap between uploads sets the earliest time the next reel can go up
next_ok = max(i["dt"] for i in items) + timedelta(hours=10)
drafts("next", "Up next")
drafts("review", "Waiting for review")
# topics that were uploaded but have no live reel now (every version deleted): they still need a good version
live_eps = {i["ep"] for i in items if i["k"] != "gone"} | {x["ep"] for x in cards["next"]}
for ep in sorted({i["ep"] for i in items} - live_eps):
    vs = [i for i in items if i["ep"] == ep]
    best = max(vs, key=lambda i: i["views"] or 0)
    unposted.append(dict(
        title=f"Ep{ep} · needs a new version", topic=CAT["episodes"].get(str(ep), ""), m=best["m"], k="nolive", word="Needs new version",
        when=f"{len(vs)} version{'s' if len(vs) > 1 else ''} uploaded, all deleted. Preview: {best['title']} (most views).",
        short=f"Uploaded {len(vs)}×, every version deleted", views=None, rate="", stats=[], ep=ep,
        notes=[f"#{i['n']} {i['title'].split(' · ')[1]}: {i['notes'][0]}" for i in vs],
        last="", link=None, byt=False, n="", gone=False))
drafts("old", "Old file")


allrows = items + unposted
# ---------------------------------------------------------------- page: headline tiles, then one sortable table
def pts(p, cap=90):
    """[(datetime, value)] -> [[ms, value]], thinned to about cap points (the newest is always kept)"""
    step = max(1, len(p) // cap)
    out = p[::-1][::step][::-1]
    return [[int(t.timestamp() * 1000), v] for t, v in out]


live_scs = [x["sc"] for x in cards["live"]]
total_series = []
for T in sorted({t for sc in live_scs for t, _ in series.get(sc, [])}):
    s = 0
    for sc in live_scs:
        seen = [v for t, v in series.get(sc, []) if t <= T]
        s += seen[-1] if seen else 0
    total_series.append((T, s))
fol_series = fol + ([(now, followers)] if fol and fol[-1][0] < now else [])

GROUP = {"up": "live", "slow": "live", "flat": "live", "new": "live", "gone": "deleted",
         "next": "next", "review": "review", "nolive": "redo", "old": "old"}
ICON = {"up": "↑", "slow": "→", "flat": "–", "new": "★", "gone": "×", "next": "⏭", "review": "●", "nolive": "↻", "old": "·"}
# uploads per episode, so every row can say which other reels are the same idea
by_ep = {}
for j, u in enumerate(items):
    by_ep.setdefault(u["ep"], []).append((j, u))


def same_idea(idx, i):
    others = [(j, u) for j, u in by_ep.get(i["ep"], []) if j != idx]
    if not others:
        return "" if idx < len(items) else '<li class="idea"><span>New idea, never uploaded</span></li>'
    label = "Same idea, also uploaded as" if idx < len(items) else "Same idea, uploaded as"
    chips = "".join(f'<button class="jump ic{" on" if u["k"] != "gone" else ""}" data-i="{j}">'
                    f'#{u["n"]} {E(u["title"].split(" · ")[1])} · {"live" if u["k"] != "gone" else "deleted"}</button>'
                    for j, u in others)
    return f'<li class="idea"><span>{label}</span>{chips}</li>'


def num(v, fmt="{:,}"):
    return ("–", "") if v is None else (fmt.format(v), v)


def cell(v, fmt="{:,}", cls="n"):
    txt, key = num(v, fmt)
    return f'<td class="{cls}" data-s="{key}">{txt}</td>'


vmax = max((i["views"] or 0) for i in items)
rows_html, detail = [], []
for idx, i in enumerate(allrows):
    grp = GROUP[i["k"]]
    kind = i["title"].split(" · ", 1)[1] if " · " in i["title"] else ""
    thumb = f'<img src="{i["m"][1]}" alt="" loading="lazy">' if i["m"] else '<span class="nothumb"></span>'
    play = '<span class="play" aria-hidden="true">▶</span>' if i["m"] else ""
    v = i.get("views")
    bar = f'<span class="bar"><span style="width:{100 * v / vmax:.1f}%"></span></span>' if v else ""
    spark = (f'<svg class="spark" data-p="{E(json.dumps(pts(series[i["sc"]], 40)))}" width="96" height="28"></svg>'
             if grp == "live" and len(series.get(i.get("sc"), [])) > 1 else "")
    notes = same_idea(idx, i) + "".join(f"<li>{E(n)}</li>" for n in i["notes"])
    if i.get("vars"):
        notes = (f'<li class="idea"><span>This one is final.</span><button class="vbtn" data-i="{idx}">'
                 f'Variants <b>{len(i["vars"])}</b></button></li>') + notes
    ts = int(i["dt"].timestamp()) if i.get("dt") else ""
    meta = (f"#{i['n']} · " if i["n"] else "") + i["short"]
    link = f'<a class="ig" href="{i["link"]}" target="_blank" rel="noopener" title="Open on Instagram">↗</a>' if i["link"] else ""
    rows_html.append(
        f'<tbody data-g="{grp}" data-i="{idx}"><tr class="r {i["k"]}">'
        f'<td class="reel" data-s="{i["ep"] * 1000 + (i["n"] or 999)}"><button class="open" aria-expanded="false" aria-label="Play {E(i["title"])}">{thumb}{play}</button>'
        f'<span class="nm"><b>{E(i["title"].split(" · ")[0])}</b> <span class="kd">{E(kind)}</span>'
        f'<span class="tp">{E(i["topic"])}</span><span class="mt">{E(meta)}</span></span></td>'
        f'<td data-s="{"0123456789"["up slow new flat next review nolive old gone".split().index(i["k"])]}">'
        f'<span class="pill {i["k"]}"><i>{ICON[i["k"]]}</i>{E(i["word"])}</span></td>'
        f'<td class="n views" data-s="{v if v is not None else ""}">{f"<b>{v:,}</b>" if v else "–"}{bar}</td>'
        + cell(i.get("r"), "+{:.0f}") + f'<td class="sp">{spark}</td>'
        + cell(i.get("skip"), "{:.0f}%") + cell(i.get("avg"), "{:.0f} s")
        + cell(i.get("likes")) + cell(i.get("comments")) + cell(i.get("shares")) + cell(i.get("saves"))
        + f'<td class="when" data-s="{ts}" title="{E(i["when"])}">{E(i["short"])}</td>'
        f'<td>{link}</td></tr><tr class="iss {i["k"]}"><td colspan="13"><ul>{notes}</ul></td></tr>'
        f'<tr class="xd" hidden><td colspan="13"></td></tr></tbody>')
    detail.append(dict(video=i["m"][0] if i["m"] else None, poster=i["m"][1] if i["m"] else None, title=i["title"],
                       when=i["when"], caption=i.get("caption", ""), last=i["last"], byt=i["byt"], link=i["link"],
                       topic=i["topic"], notes=i["notes"] if i.get("vars") else [],
                       vars=[dict(video=v["m"][0], poster=v["m"][1], title=v["title"], topic=v["topic"], notes=v["notes"],
                                  when=f"Made {v['made'].strftime('%-d %b, %H:%M')} IST") for v in i.get("vars", [])]))

cnt = {g: sum(GROUP[i["k"]] == g for i in allrows) for g in ("live", "next", "deleted", "review", "redo", "old")}
TABS = [("live", "Live"), ("next", "Up next"), ("deleted", "Deleted"), ("review", "Waiting for review"), ("redo", "Needs new version"), ("old", "Old files")]
tabs = "".join(f'<button role="tab" data-t="{g}">{w}<span>{cnt[g]}</span></button>' for g, w in TABS if cnt[g] or g in ("live", "deleted"))
tabs += f'<button role="tab" data-t="all">All<span>{len(allrows)}</span></button>'
best = max(cards["live"], key=lambda x: x["tr"][2] if x["tr"] else -1, default=None)
best_idx = next((k for k, i in enumerate(allrows) if best and i.get("sc") == best["sc"]), None)
next_idx = next((k for k, i in enumerate(allrows) if i["k"] == "next"), None)
review_idx = next((k for k, i in enumerate(allrows) if i["k"] == "review"), None)
review_name = allrows[review_idx]["title"].split(" · ")[0] if review_idx is not None else ""


def tile(label, value, sub, spark=None, cls=""):
    sp = f'<svg class="spark big" data-p="{E(json.dumps(pts(spark)))}" height="36"></svg>' if spark and len(spark) > 1 else ""
    return f'<div class="tile {cls}"><span class="lb">{label}</span><b class="val">{value}</b><span class="dl">{sub}</span>{sp}</div>'


tiles = (tile("Views on live reels", f"{total:,}", f'<span class="pos">{gain:+,}</span> in the last {hrs:.1f} h', total_series, "hero")
         + tile("Followers", f"{followers:,}", f'<span class="pos">{fol_today:+d}</span> today', fol_series)
         + (tile("Fastest right now",
                 f'<button class="jump" data-i="{best_idx}">{E(nm(best))}</button>',
                 f'<span class="pos">+{best["tr"][2]:.0f}</span> views/h') if best and best["tr"] else "")
         + tile("Reels", f'{cnt["live"]} <small>live</small>',
                f'{cnt["next"]} up next · {cnt["deleted"]} deleted · {len(cards["review"])} waiting for you'))
callouts = ""
if next_idx is not None:
    t0 = allrows[next_idx]["title"].replace(" · ", " ")
    callouts += (f'<div class="call next"><span><b>Up next: {E(t0)}.</b> '
                 + (f'Then {cnt["next"] - 1} more in the queue. ' if cnt["next"] > 1 else '')
                 + f'Earliest upload {next_ok.strftime("%-d %b, %H:%M")} IST (10 h after the last one). '
                 f'Not scheduled yet; nothing posts without your yes.</span>'
                 f'<button class="jump btn" data-i="{next_idx}">▶ Watch {E(t0)}</button></div>')
if review_idx is not None:
    callouts += (f'<div class="call review"><span><b>{E(review_name)} is waiting for your review.</b> '
                 f'Nothing is queued; nothing posts without your yes.</span>'
                 f'<button class="jump btn" data-i="{review_idx}">▶ Watch {E(review_name)}</button></div>')
for s in sugg:
    callouts += f'<div class="call tip"><span><b>Repost idea.</b> {E(s)}</span></div>'

COLS = [("Reel", "n"), ("Status", ""), ("Views", "n"), ("Views/h", "n"), ("Trend", "nosort"), ("Swipe away", "n"),
        ("Watch", "n"), ("Likes", "n"), ("Comments", "n"), ("Shares", "n"), ("Saves", "n"), ("Uploaded", "n"), ("", "nosort")]
thead = "".join(f'<th class="{c}" data-c="{k}"{"" if "nosort" in c else " tabindex=0"}>{h}</th>' for k, (h, c) in enumerate(COLS))

TEMPLATE = r"""<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8">
<script>try { const t = localStorage.getItem('theme'); if (t === 'dark') document.documentElement.dataset.theme = 'dark'; } catch (e) {}</script>
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Talkingagents Reels</title>
<style>
:root{color-scheme:light;--bg:#f4f3ef;--card:#fcfcfb;--ink:#0b0b0b;--dim:#52514e;--mute:#8a8984;--line:#e4e2dc;--hover:#efeee9;
--accent:#2a78d6;--accent-soft:#cde2fb;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--violet:#6250d6;--pos:#0a7d0a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#111110;--card:#1a1a19;--ink:#f0efec;
--dim:#c3c2b7;--mute:#8d8c85;--line:#2e2e2b;--hover:#242422;--accent:#3987e5;--accent-soft:#184f95;--violet:#9085e9;--pos:#3fc23f}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#111110;--card:#1a1a19;--ink:#f0efec;--dim:#c3c2b7;--mute:#8d8c85;--line:#2e2e2b;
--hover:#242422;--accent:#3987e5;--accent-soft:#184f95;--violet:#9085e9;--pos:#3fc23f}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Inter",system-ui,sans-serif}
main{max-width:1440px;margin:0 auto;padding:20px 16px 40px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:14px}
h1{font-size:26px;margin:0;letter-spacing:-.02em} h1 span{color:var(--mute);font-weight:500}
.sub{margin:2px 0 0;color:var(--dim);font-size:13px} .legend{font-size:12px;color:var(--mute);margin:0} .hr{display:flex;align-items:center;gap:12px;flex-wrap:wrap} .theme{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:5px 12px;font:600 12.5px/1 inherit;cursor:pointer} .theme:hover{background:var(--hover)} .theme:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tiles{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;display:flex;flex-direction:column;min-width:0}
.lb{font-size:12.5px;color:var(--dim)} .val{font-size:26px;font-weight:650;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2;margin:2px 0}
.hero .val{font-size:36px} .val small{font-size:14px;font-weight:500;color:var(--dim)} .dl{font-size:12.5px;color:var(--dim)}
.pos{color:var(--pos);font-weight:600} .tile .spark{width:100%;margin-top:8px}
.jump{all:unset;cursor:pointer;color:var(--ink);border-bottom:2px solid var(--accent)} .jump:hover{color:var(--accent)}
.call{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px;padding:10px 14px;border-radius:12px;
background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent)}
.call.review{border-left-color:var(--violet)} .call.tip{border-left-color:var(--warn)}
.btn{border:0;background:var(--violet);color:#fff;padding:7px 14px;border-radius:99px;font-weight:600;white-space:nowrap}
.btn:hover{filter:brightness(1.1);color:#fff}
.bar-row{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:22px 0 8px;flex-wrap:wrap}
.tabs{display:flex;gap:4px;background:var(--card);border:1px solid var(--line);border-radius:99px;padding:3px}
.tabs button{all:unset;cursor:pointer;padding:6px 14px;border-radius:99px;font-weight:600;font-size:13px;color:var(--dim)}
.tabs button span{font-weight:500;color:var(--mute);margin-left:4px} .tabs button[aria-selected=true]{background:var(--ink);color:var(--card)}
.tabs button[aria-selected=true] span{color:inherit;opacity:.7} .tabs button:focus-visible{outline:2px solid var(--accent)}
.hint{font-size:12px;color:var(--mute)}
.wrap{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:980px}
th{position:sticky;top:0;background:var(--card);text-align:left;font-size:11.5px;font-weight:600;color:var(--dim);text-transform:uppercase;
letter-spacing:.04em;padding:10px 8px;border-bottom:1px solid var(--line);white-space:nowrap;cursor:pointer;user-select:none}
th.nosort{cursor:default} th.n{text-align:right} th:first-child{text-align:left} th[aria-sort]::after{content:" ↓";color:var(--accent)} th[aria-sort=ascending]::after{content:" ↑"}
td{padding:10px 8px 6px;border-top:1px solid var(--line);vertical-align:middle;white-space:nowrap}
tbody:first-of-type tr.r td{border-top:0} tbody:hover td{background:var(--hover)}
td.n{text-align:right;font-variant-numeric:tabular-nums} td.num{color:var(--mute);font-size:12px;width:28px}
tr.gone td{color:var(--mute)} tr.gone img{filter:grayscale(1);opacity:.6}
td.reel{position:sticky;left:0;z-index:1;background:var(--card);width:300px;min-width:260px;max-width:300px;white-space:normal} th:first-child{position:sticky;left:0;z-index:2}
td.reel{display:table-cell} td.reel>*{vertical-align:middle}
.open{all:unset;position:relative;cursor:pointer;flex:none;display:inline-block;border-radius:8px;overflow:hidden;margin-right:10px}
.open img,.nothumb{display:block;width:44px;height:78px;object-fit:cover;background:#000}
.open:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.play{position:absolute;inset:0;display:grid;place-items:center;color:#fff;font-size:15px;background:rgba(0,0,0,.25);opacity:0;transition:opacity .15s}
.open:hover .play,.open[aria-expanded=true] .play{opacity:1}
.nm{display:inline-block;width:calc(100% - 58px);white-space:normal} .nm b{font-size:14.5px}
.kd{font-size:12.5px;color:var(--dim);font-weight:500} .kd::before{content:"· "} .tp,.mt{display:block;font-size:12.5px;color:var(--mute);line-height:1.35} .tp{color:var(--dim)}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;padding:3px 10px 3px 8px;border-radius:99px;
background:color-mix(in srgb,var(--c) 16%,transparent);color:var(--ink);border:1px solid color-mix(in srgb,var(--c) 40%,transparent)}
.pill i{font-style:normal;color:var(--c);font-weight:800}
.pill.up{--c:var(--good)} .pill.slow{--c:var(--warn)} .pill.flat{--c:var(--crit)} .pill.new{--c:var(--accent)} .pill.gone{--c:var(--mute)}
.call.next{border-left-color:var(--good)} .pill.next{--c:var(--good)} .pill.review{--c:var(--violet)} .pill.nolive{--c:var(--warn)} .pill.old{--c:var(--mute)}
.views b{font-size:15px} .bar{display:block;height:4px;margin-top:4px;background:var(--line);border-radius:2px;min-width:70px}
.bar span{display:block;height:100%;background:var(--accent);border-radius:2px}
tr.gone .bar span{background:var(--mute)}
.sp{width:104px} .spark{display:block;overflow:visible} .spark path.l{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.spark path.a{fill:var(--accent);opacity:.12} .spark circle{fill:var(--accent);stroke:var(--card);stroke-width:2}
.spark .hv{fill:var(--ink)} .when{color:var(--dim);font-size:12.5px}
tr.iss td{border-top:0;padding:0 8px 10px 72px;white-space:normal} .iss ul{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:4px 6px;position:sticky;left:72px;max-width:min(1100px,calc(100vw - 130px))} .iss li{font-size:12px;color:var(--dim);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:1px 7px} tr.iss.gone li{color:var(--mute)} .iss li.idea{background:none;border:0;padding:0;display:flex;flex-wrap:wrap;align-items:center;gap:4px;width:100%;color:var(--ink);font-weight:600} .ic{border:1px dashed var(--mute);background:var(--card);color:var(--dim);border-radius:99px;padding:1px 9px;font:500 12px/1.5 inherit;cursor:pointer} .ic.on{border:1px solid var(--good);color:var(--ink);background:color-mix(in srgb,var(--good) 12%,var(--card))} .ic:hover{border-color:var(--accent)} td.reel+td{padding-left:12px}
.ig{text-decoration:none;color:var(--accent);font-weight:700;font-size:16px;padding:4px}
tr.xd td{background:var(--bg);white-space:normal;padding:14px}
.xbox{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}
.xbox video{height:min(70vh,560px);aspect-ratio:9/16;background:#000;border-radius:12px;display:block;max-width:100%}
.xinfo{max-width:460px;font-size:13.5px} .xinfo h3{margin:0 0 4px;font-size:17px} .xinfo p{margin:4px 0;color:var(--dim)}
.xinfo .cap{color:var(--ink);font-style:italic} .xinfo a{color:var(--accent);font-weight:600;text-decoration:none}
.close{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:5px 12px;cursor:pointer;margin-top:8px}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--card);font-size:12px;padding:4px 8px;border-radius:6px;
white-space:nowrap;z-index:9;display:none;font-variant-numeric:tabular-nums}
.empty{padding:30px;text-align:center;color:var(--mute)}
.vbtn{border:1px solid var(--good);background:color-mix(in srgb,var(--good) 12%,var(--card));color:var(--ink);border-radius:99px;padding:2px 11px;
font:600 12px/1.5 inherit;cursor:pointer} .vbtn b{font-weight:600;color:var(--dim);margin-left:3px} .vbtn:hover{border-color:var(--accent)}
#vm{border:1px solid var(--line);border-radius:16px;background:var(--card);color:var(--ink);padding:0;width:min(1000px,calc(100vw - 32px));max-height:calc(100vh - 48px)}
#vm::backdrop{background:rgba(0,0,0,.55)} .vmh{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:16px 18px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--card);z-index:1}
.vmh h2{margin:0;font-size:18px} .vmh p{margin:3px 0 0;font-size:13px;color:var(--dim)} .vmh .close{margin:0}
.vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;padding:16px 18px 20px}
.vc{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:10px;font-size:12.5px} .vc.final{border-color:var(--good)}
.vc video{width:100%;aspect-ratio:9/16;background:#000;border-radius:8px;display:block}
.vc h3{margin:8px 0 2px;font-size:14px;display:flex;gap:6px;align-items:center;flex-wrap:wrap} .vc p{margin:3px 0;color:var(--dim)} .vc .f{color:var(--mute)}
@media (max-width:900px){.tiles{grid-template-columns:repeat(3,1fr)}.hero{grid-column:1/-1}.hero .spark{height:40px}}
@media (max-width:600px){.tiles{grid-template-columns:1fr 1fr}.tiles .tile:last-child{grid-column:1/-1}}
@media (max-width:520px){.hero .val{font-size:32px}.call{flex-direction:column;align-items:flex-start}
td.reel{width:220px;min-width:220px;max-width:220px} tr.iss td{padding-left:8px}}
</style></head><body><main>
<header><div><h1>@talkingagents <span>reels</span></h1><p class="sub">Numbers as of __ASOF__ IST</p></div>
<div class="hr"><p class="legend">↑ Climbing ≥ 20 views/h · → Slowing 5–20 · – Stalled &lt; 5 (over the last 3+ h)</p>
<button id="theme" class="theme" aria-label="Switch theme"></button></div></header>
<section class="tiles">__TILES__</section>
__CALLS__
<div class="bar-row"><div class="tabs" role="tablist">
__TABS__</div>
<span class="hint">Click a column to sort · click a thumbnail to play</span></div>
<div class="wrap"><table><thead><tr>__THEAD__</tr></thead>__ROWS__</table><div class="empty" hidden>Nothing here.</div></div>
</main><div id="tip"></div>
<dialog id="vm" aria-labelledby="vmt"><div class="vmh"><div><h2 id="vmt"></h2><p></p></div><button class="close">Close</button></div><div class="vgrid"></div></dialog>
<script>
const D = __DATA__;
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const table = $('table'), tip = $('#tip');
const fmtT = ms => new Date(ms).toLocaleString('en-GB', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata'});

// sparklines: line + soft area, newest point marked, hover shows the value at the nearest point
function spark(svg) {
  const p = JSON.parse(svg.dataset.p), W = svg.clientWidth || +svg.getAttribute('width'), H = +svg.getAttribute('height'), pad = 3;
  const t0 = p[0][0], t1 = p[p.length - 1][0], lo = Math.min(...p.map(q => q[1])), hi = Math.max(...p.map(q => q[1]));
  const X = t => pad + (W - 2 * pad) * (t - t0) / Math.max(1, t1 - t0), Y = v => H - pad - (H - 2 * pad) * (v - lo) / Math.max(1, hi - lo);
  const d = p.map((q, k) => (k ? 'L' : 'M') + X(q[0]).toFixed(1) + ' ' + Y(q[1]).toFixed(1)).join('');
  const last = p[p.length - 1];
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = `<path class="a" d="${d}L${X(t1)} ${H}L${X(t0)} ${H}Z"/><path class="l" d="${d}"/>` +
    `<circle r="3.5" cx="${X(last[0])}" cy="${Y(last[1])}"/><circle class="hv" r="3" style="display:none"/>`;
  const hv = svg.querySelector('.hv');
  svg.onmousemove = e => {
    const r = svg.getBoundingClientRect(), t = t0 + (e.clientX - r.left - pad) / (r.width - 2 * pad) * (t1 - t0);
    const q = p.reduce((a, b) => Math.abs(b[0] - t) < Math.abs(a[0] - t) ? b : a);
    hv.setAttribute('cx', X(q[0])); hv.setAttribute('cy', Y(q[1])); hv.style.display = '';
    tip.textContent = fmtT(q[0]) + ' · ' + q[1].toLocaleString('en-US'); tip.style.display = 'block';
    tip.style.left = Math.min(innerWidth - tip.offsetWidth - 8, e.clientX + 12) + 'px'; tip.style.top = (e.clientY - 30) + 'px';
  };
  svg.onmouseleave = () => { hv.style.display = 'none'; tip.style.display = 'none'; };
}
const drawAll = () => $$('svg.spark').forEach(s => { if (s.getBoundingClientRect().width) spark(s); });
addEventListener('resize', drawAll);

// tabs
let tab = 'live';
try { tab = localStorage.getItem('tab') || 'live'; } catch (e) {}
function setTab(t) {
  tab = t;
  $$('.tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.t === t));
  let shown = 0;
  $$('tbody').forEach(b => { const on = t === 'all' || b.dataset.g === t; b.hidden = !on; shown += on; });
  $('.empty').hidden = shown > 0;
  try { localStorage.setItem('tab', t); } catch (e) {}
  drawAll();
}
$$('.tabs button').forEach(b => b.onclick = () => setTab(b.dataset.t));

// sorting: numbers high to low first, text A to Z first; empty values always last
let sortC = 2, asc = false;
function sortBy(c, a) {
  sortC = c; asc = a;
  $$('th').forEach((h, k) => k === c ? h.setAttribute('aria-sort', a ? 'ascending' : 'descending') : h.removeAttribute('aria-sort'));
  const cv = (b, k) => b.rows[0].cells[k].dataset.s ?? b.rows[0].cells[k].textContent, val = b => cv(b, c);
  const bodies = $$('tbody').sort((x, y) => {
    const u = val(x), v = val(y);
    if (u === '' || v === '') return (u === '') - (v === '');
    const r = isNaN(u) || isNaN(v) ? String(u).localeCompare(v) : u - v;
    if (r === 0 && c === 1) return (+cv(y, 3) || 0) - (+cv(x, 3) || 0) || (+cv(y, 2) || 0) - (+cv(x, 2) || 0);  // same status: fastest first
    return a ? r : -r;
  });
  bodies.forEach(b => table.appendChild(b));
}
$$('th').forEach((h, k) => {
  if (h.classList.contains('nosort')) return;
  const go = () => sortBy(k, sortC === k ? !asc : k === 0);
  h.onclick = go; h.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } };
});

// inline player: one open at a time, right under its row
function closeAll() {
  $$('tr.xd').forEach(x => { if (!x.hidden) { const v = $('video', x); if (v) v.pause(); x.hidden = true; x.cells[0].innerHTML = ''; } });
  $$('.open').forEach(b => b.setAttribute('aria-expanded', 'false'));
}
function openRow(i, scroll) {
  const b = $(`tbody[data-i="${i}"]`), x = $('tr.xd', b), btn = $('.open', b), was = !x.hidden;
  closeAll();
  if (was) return;
  const r = D[i];
  let h = '<div class="xbox">' + (r.video ? `<video controls playsinline autoplay preload="auto" poster="${r.poster}" src="${r.video}"></video>` : '');
  h += `<div class="xinfo"><h3>${esc(r.title)}</h3><p>${esc(r.topic)}</p><p>${esc(r.when)}</p>`;
  if (r.caption) h += `<p class="cap">“${esc(r.caption)}”</p>`;
  if (r.last) h += `<p>${esc(r.last)}</p>`;
  if (r.byt) h += '<p>Preview is the final render made just before the upload (matched by time).</p>';
  if (r.link) h += `<p><a href="${r.link}" target="_blank" rel="noopener">Open on Instagram ↗</a></p>`;
  h += '<button class="close">Close</button></div></div>';
  x.cells[0].innerHTML = h; x.hidden = false; btn.setAttribute('aria-expanded', 'true');
  $('.close', x).onclick = closeAll;
  if (scroll) requestAnimationFrame(() => x.scrollIntoView({behavior: 'smooth', block: 'center'}));
}
$$('.open').forEach(b => b.onclick = () => openRow(+b.closest('tbody').dataset.i));
// variants modal: the final version first, then every other version of the same episode
const vm = $('#vm');
function card(r, final) {
  return `<div class="vc${final ? ' final' : ''}"><video controls playsinline preload="none" poster="${r.poster}" src="${r.video}"></video>`
    + `<h3>${esc(r.title.split(' · ')[1])}${final ? ' <span class="pill next"><i>⏭</i>Final · up next</span>' : ''}</h3>`
    + `<p class="f">${esc(r.topic.split(' · ').pop())} · ${esc(r.when)}</p>`
    + (r.notes || []).map(n => `<p>${esc(n)}</p>`).join('') + '</div>';
}
$$('.vbtn').forEach(b => b.onclick = () => {
  const r = D[+b.dataset.i];
  closeAll();
  $('#vmt', vm).textContent = `${r.title.split(' · ')[0]} variants`;
  $('.vmh p', vm).textContent = `${r.vars.length + 1} versions. ${r.title.split(' · ')[1]} is final; the others won't be posted.`;
  $('.vgrid', vm).innerHTML = card(r, true) + r.vars.map(v => card(v)).join('');
  vm.showModal();
});
$('.close', vm).onclick = () => vm.close();
vm.addEventListener('click', e => { if (e.target === vm) vm.close(); });
vm.addEventListener('close', () => $$('video', vm).forEach(v => v.pause()));
$$('.jump').forEach(b => b.onclick = () => {
  const i = +b.dataset.i, g = $(`tbody[data-i="${i}"]`).dataset.g;
  if (tab !== 'all' && tab !== g) setTab(g);
  openRow(i, true);
});
addEventListener('keydown', e => { if (e.key === 'Escape') closeAll(); });

// theme: light unless the viewer picked dark
const themeBtn = $('#theme'), root = document.documentElement;
const paintTheme = () => { themeBtn.textContent = root.dataset.theme === 'dark' ? '☀ Light' : '☾ Dark'; };
themeBtn.onclick = () => {
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
  paintTheme();
};
paintTheme();

setTab($(`.tabs [data-t="${tab}"]`) ? tab : 'live');
sortBy(1, true);
</script></body></html>"""

page = (TEMPLATE.replace("__ASOF__", now.strftime("%-d %b %Y, %H:%M")).replace("__TILES__", tiles).replace("__CALLS__", callouts)
        .replace("__TABS__", tabs).replace("__THEAD__", thead).replace("__ROWS__", "".join(rows_html))
        .replace("__DATA__", json.dumps(detail).replace("</", "<\\/")))
open(os.path.join(OUT, "index.html"), "w").write(page)
print("wrote", os.path.join(OUT, "index.html"), "-", len(items), "uploaded,", len(unposted), "not uploaded")
