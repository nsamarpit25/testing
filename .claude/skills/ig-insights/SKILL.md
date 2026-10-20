---
name: ig-insights
description: Instagram stats (views, likes, followers, etc.) for @talkingagents and @how.its.engineered via the Instagram Graph API.
---

Tokens and account IDs are in `~/.instagram_tokens` (`IG_TALKINGAGENTS_*`, `IG_HOWITSENGINEERED_*`). Source it; never print the tokens.

API: `https://graph.instagram.com/v26.0` (e.g. `me`, `me/media`, `{media-id}/insights`).

Save what you find to `~/insta-automation/insights/`.

To fetch, run `source ~/.instagram_tokens && python3 -I .claude/skills/ig-insights/fetch.py` (it works from any folder and saves into this repo's `insights/`, times in IST). It appends every fetch to `insights/history.jsonl` (one line per account and per reel, never rewritten), regenerates `insights/latest.md` with the change since the previous fetch, and prints what moved. Use the history file for growth over time.
