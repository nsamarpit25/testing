#!/usr/bin/env python3
"""Print the newest @talkingagents post as "<epoch> <permalink>". The token is read from ~/.instagram_tokens and never printed."""
import json, sys, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

tok = next(v.strip().strip('"') for l in (Path.home() / ".instagram_tokens").read_text().splitlines()
           for k, _, v in [l.removeprefix("export ").partition("=")] if k.strip() == "IG_TALKINGAGENTS_TOKEN")
q = urllib.parse.urlencode({"fields": "timestamp,permalink", "limit": 1, "access_token": tok})
try:
    with urllib.request.urlopen(f"https://graph.instagram.com/v26.0/me/media?{q}", timeout=60) as r:
        m = json.load(r)["data"][0]
except Exception as e:
    sys.exit(f"last_post: {type(e).__name__}")  # no URL in the message, so the token can't leak
print(int(datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp()), m["permalink"])
