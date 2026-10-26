# @talkingagents handoff 3 (written 21 Oct 2026, ~20:30 IST)

Read `insights/talkingagents-handoff-2.md` too: it has the pipeline, the review gate, and why 18 reels were deleted.

## First thing: open the review page
The owner reviews reels on a local page; it is NOT an artifact.
1. Rebuild it with fresh numbers: `source ~/.instagram_tokens && python3 -I .claude/skills/ig-insights/fetch.py` then
   `source ~/.instagram_tokens && python3 insights/build_review.py` (add `--check` to run cutcheck on any new video).
2. Start the server with the Browser preview tool: `preview_start {name: "reel-review"}` (config in `.claude/launch.json`,
   runs `python3 insights/review_server.py 8770`, which supports HTTP Range so the videos play and seek). It opens http://localhost:8770.
3. Then wait for the owner's instructions. Don't start making episodes or launching AWS until they say so.

## The page (insights/build_review.py → insights/review/index.html, git-ignored)
- One list, in upload order (#1 Ep1 Original … #26 Ep11). Each row: thumbnail, episode and type, topic, "Uploaded X d Y h ago",
  a status pill (Climbing ≥ 20 views/h, Slowing 5–20, Stalled < 5 over the last 3+ h, or Deleted), views and views/h.
  Tap a row → popup with the video, full stats, issues and the Instagram link.
- "Show deleted" toggle hides the 18 deleted reels (remembered in localStorage).
- "Made, not uploaded": Ep12 final sync (Waiting for review), then topics with no live reel (Ep5, Ep8, Ep10, Ep11: every
  version deleted), then older replaced renders.
- In the builder: `FILE` maps each shortcode to the exact uploaded file (md5-matched; Ep1-5 originals matched by render time),
  `NOTES` holds the plain-words issues per live reel, `DRAFTS` the unposted videos, `SCREEN_ONLY` the cutcheck
  false positives (phone lighting up). Cutcheck results are cached by md5 in `insights/review/checks.json`.
- Uploaded videos were copied from an old /tmp scratchpad to `claude-talk-v2/output/posted/` (git-ignored).

## State at handoff
- 8 live: Ep4 Original 2,941 (slowing), Ep3 Original 2,776 (slowing, +5/h), Ep6 Original 2,464 (climbing, +59/h),
  Ep2 Original 2,067 (stalled, 47% swipe away), Ep4 Remake 1,860, Ep9 1,692, Ep7 1,494, Ep1 Remake 1,411. 133 followers (+42 today).
- Cut-check findings on live reels (checked by eye): 1-frame flashes in Ep4/Ep3/Ep6 originals (the monitor shows the old
  screen for a frame after a cut), the phone buzz stops dead in Ep2 and Ep9, quick choppy cuts in Ep7. Ep1/Ep4 remakes and Ep12 pass.
  Every reel still has the old loudness-driven oval mouth.
- Repost suggestion already given (suggestion only): Ep2 remake with a stronger first line, as a Trial Reel.
- Ep12 (`claude-talk-v2/output/new/ep12_final_sync.mp4`) is still waiting for the owner's review. Nothing is queued; the poster is not running.
- No AWS EC2 instance is running (all regions checked). Nothing was launched.
- Planned but not started: Ep13 topic "tests fail only between midnight and 5:30 AM" (India's date is a day ahead of the
  UTC server's; fix = store UTC, convert on display; ending callback "Ask your mom"), and the lip-sync upgrade (phoneme/viseme
  mouth shapes from words.json in `blender/epx.py`).
- Uncommitted: `insights/history.jsonl` (merged with 165 local-only rows after pulling), `insights/build_review.py`,
  `insights/review_server.py`, `.gitignore` (+ insights/review/), `.claude/launch.json`, this file. Commit only when asked.

## Rules
Never print tokens. Never edit `how-its-engineered/tools/ig.py`. Nothing is uploaded, reposted or deleted without the
owner's explicit yes in chat. Blender renders only on AWS; terminate any instance you launch. No AI attribution in commits.
Don't end a turn with option buttons; ask questions in plain text.
