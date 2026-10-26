# @talkingagents handoff 4 (written 21 Oct 2026, ~21:30 IST)

Read `insights/talkingagents-handoff-3.md`, then `insights/talkingagents-handoff-2.md`. They cover the pipeline, the
review gate and why 18 reels were deleted. This file only covers what changed after them.

## First thing: open the review page
1. `source ~/.instagram_tokens && python3 -I .claude/skills/ig-insights/fetch.py`
2. `source ~/.instagram_tokens && python3 insights/build_review.py` (add `--check` to run cutcheck on new videos)
3. `preview_start {name: "reel-review"}` opens http://localhost:8770. If the port is busy, kill the stale `review_server.py`.
4. Give a short status (live reels, views, climbing/stalled, changes since 21:30 IST 21 Oct), then wait for instructions.

## The page now (the owner asked for this; keep it this way)
- It's a sortable table, not popups. There are stat tiles on top. The tabs are Live / Deleted / Waiting for review /
  Needs a new version / Old files / All, and a tab with 0 rows is hidden. Issues show as chips under each row, and the
  video plays inline under its row. The page is light by default, with a ☾ Dark toggle (saved in localStorage `theme`).
- Rows that aren't uploaded show "same idea" chips that jump to the uploaded or deleted reels of the same episode.
  A row with no other uploads says "New idea, never uploaded".
- In the builder: `GROUP` maps statuses to tabs. `DRAFTS` lists unposted videos as (file, ep, kind, notes), `FILE` maps
  each shortcode to its exact uploaded file, and `NOTES` holds the issues for each live reel.

## What happened this session
- **Ep12 "center a div" went live** on 21 Oct ~20:33 IST as reel `DewrvfvDs_b` (file `output/new/ep12_final_sync.mp4`).
  It went up as a NORMAL reel: this account can't post Trial Reels yet (Graph API error subcode 2207081, follower
  requirement, at 133 followers). The owner approved the normal upload. Caption: `claude-talk-v2/ops/ep12_hold/caption.txt`.
- **Captions** are SEO keyword-rich, 1–2 lines, always 5 hashtags, at most 1 emoji. The owner confirms every caption.
- **Posting** uses a scratchpad copy of `how-its-engineered/tools/ig.py` with sed swapping `TOKEN_VAR` to
  `IG_TALKINGAGENTS_TOKEN` (the original is never edited). S3 staging uses `hie-reel-staging-30c239` (ap-south-1),
  with keys from the repo `.env` (`set -a; source .env; unset AWS_PROFILE`).
- **Ep5 has two versions waiting for review (neither uploaded):**
  - `output/new/ep5_from_claude.mp4` (81.7 s) is the Ep5 Original trimmed to start on "Claude". The repeated cold-open
    line is gone and the two old-screen flashes are covered.
  - `output/new/ep5c_final.mp4` (82.4 s) is **variant C, which the owner picked**. It opens with "Claude. Either my CSS is
    haunted, or I am." / "What happened?" / "I made this button green eleven times. It's been blue for forty minutes. It's
    doing it on purpose." ("forty minutes" stays for line 19's callback.) Lines 1–3 are a new Gemini TTS take
    (`scripts/ep5c_onecall.py`, take 3; checked with `scripts/ep5c_checktakes.py`; cut with `scripts/ep5c_cuttake.py`).
    The audio dir is `audio/ep5c`.
    - Only frames 1–470 were rendered on AWS. They're spliced at the line 5 camera cut (new frame 449 / v3 frame 387)
      onto `output/ep5_final_1080x1920_v3.mp4`, and the v3 old-screen flashes are covered.
    - The Mac ffmpeg has no libass, so the captions for the new part were burned with **mpv**. It uses
      `audio/ep5c/subs_v3match.ass`, whose Handle style is 36 px / MarginV 108 to match v3. mpv drops the last frame, so
      feed it one extra.
    - Cut check passes, A/V lengths match, and the splice was checked by eye. Lip sync is still the old oval mouth.
  - History of earlier Ep5 uploads, all deleted: #5 Original 1,560 views / 45% swipe away, #10 Tight 1,375 / 37%,
    #17 Cold open 1,633 / 29%.
- **AWS:** one g6e.2xlarge (`i-0a200de4b8b7d7d10`, ap-south-1) was launched with the owner's OK and **terminated**.
  Nothing is running in ap-south-1 or us-east-1. The launch script is `claude-talk-v2/ops/launch.sh` (point `L=` at your
  scratchpad). Tip: for a change to the opening only, render just the frames up to a camera cut and splice. Don't
  re-render the whole episode.

## State at handoff
- Live (8 + Ep12): Ep4 Original 2,944, Ep3 Original 2,777, Ep6 Original 2,493, Ep2 Original 2,067, Ep9 1,699,
  Ep7 1,498, Ep11 1,417, Ep12 just posted. 133 followers. Ep4 Remake (DevksKyEzNv) was deleted by the owner on 21 Oct
  at 1,863 views.
- **Next upload no earlier than ~06:33 IST on 22 Oct** (10 h after Ep12). Nothing is queued and the poster isn't running.
- Still planned, not started: Ep13 "tests fail only between midnight and 5:30 AM" (UTC vs IST date; ending "Ask your
  mom"), and the phoneme/viseme lip-sync upgrade in `blender/epx.py`.
- Uncommitted: `insights/build_review.py`, `insights/talkingagents-reels.json`, `insights/review_server.py`,
  `.claude/launch.json`, the new ep5c scripts and audio, and the handoff files. Commit only when asked.

## Rules
Never print tokens. Never edit `how-its-engineered/tools/ig.py`. Nothing is uploaded, reposted or deleted without the
owner's explicit "yes" in chat. No AWS launch until the owner says so, and terminate every instance you launch.
At least 10 h between @talkingagents uploads. No AI attribution in commits. Don't end a turn with option buttons;
ask questions in plain text.
