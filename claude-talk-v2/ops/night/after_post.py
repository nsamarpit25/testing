#!/usr/bin/env python3
"""Keep insights/talkingagents-reels.json in step with the 5-hour queue.
  after_post.py plan <last_post_epoch> 14 15 16 17   -> set Up next to these episodes with estimated times
  after_post.py posted 14 <permalink>                -> add the reel, drop it from Up next, re-time the rest
"""
import json, sys, time
from pathlib import Path

CAT = Path("/Users/samarpit/insta-automation/insights/talkingagents-reels.json")
GAP = 5 * 3600
d = json.loads(CAT.read_text())


def retime(eps, last):
    t = max(last + GAP, time.time())
    out = []
    for ep in eps:
        out.append({"ep": int(ep), "status": f"Queued, posts about {time.strftime('%d %b %H:%M', time.localtime(t))} IST (5 h after the previous post)"})
        t += GAP
    return out


cmd, args = sys.argv[1], sys.argv[2:]
if cmd == "plan":
    d["upcoming"] = retime(args[1:], int(args[0]))
elif cmd == "posted":
    ep, link = int(args[0]), args[1]
    d["reels"][link.rstrip("/").split("/")[-1]] = {"ep": ep, "kind": "original"}
    d["upcoming"] = retime([u["ep"] for u in d["upcoming"] if u["ep"] != ep], int(time.time()))
CAT.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
print(json.dumps(d["upcoming"]))
