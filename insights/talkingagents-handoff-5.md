# @talkingagents handoff 5 (written 22 Oct 2026, ~00:15 IST)

Read `insights/talkingagents-handoff-4.md`, then `-3.md` and `-2.md`. They cover the pipeline, the review gate, posting,
AWS and why 18 reels were deleted. This file only covers what changed after handoff 4.

## First thing: open the review page
1. `source ~/.instagram_tokens && python3 -I .claude/skills/ig-insights/fetch.py`
2. `source ~/.instagram_tokens && python3 insights/build_review.py` (add `--check` to run cutcheck on new videos)
3. `preview_start {name: "reel-review"}` opens http://localhost:8770. If the port is busy, kill the stale `review_server.py`.
4. Give a short status (live reels, views, climbing/stalled, how Ep12 is doing, changes since the last fetch at 21:36 IST
   21 Oct), then wait for instructions.

## What changed this session (review page only; nothing posted, rendered or launched)
- **New "Up next" tab** (after Live), modelled on the one in `how-its-engineered/tools/remake/bin/library.py`. A `DRAFTS`
  entry with kind `"next"` goes there with a green "⏭ Up next" pill and "#N in queue". A green banner on top says
  "Up next: …", the earliest upload time (last upload + 10 h, computed) and "nothing posts without your yes", with a Watch button.
- **Ep5 Variant C** (`output/new/ep5c_final.mp4`) is the only Up next item. The owner calls it the final Ep5 version.
- **Variants:** DRAFTS kind `"variant"` = other versions of an Up next episode. They appear nowhere else on the page; the
  Up next row has a "Variants N" button that opens a modal (`<dialog id="vm">`) with every version as a playable card,
  the final one first with a "Final · up next" badge. Ep5 variants: `ep5_from_claude.mp4` (was in Waiting for review),
  `output/ep5_final_1080x1920.mp4` and `_v2.mp4` (were in Old files).
- An episode with an Up next version no longer shows in "Needs new version" (Ep5 dropped out). "Waiting for review" is
  now empty, so its tab and banner are hidden.
- The three deleted Ep5 uploads (#5, #10, #17) still sit in the Deleted tab as history. The owner was asked whether to
  hide them there too and hasn't answered.
- Friendly labels for these files are set by filename in the `label = {...}` map in the DRAFTS loop.

## State at handoff (numbers from 21:36 IST 21 Oct)
- 8 live, 133 followers: Ep4 Original 2,948 (slowing), Ep3 Original 2,783 (slowing), Ep6 Original 2,547 (climbing,
  ~+58/h), Ep2 Original 2,067 (stalled, 47% swipe away), Ep9 1,705, Ep7 1,506, Ep1 Remake 1,419 (imposter syndrome;
  handoff 4 mislabeled this as "Ep11"), Ep12 160.
- **Ep12** (`DewrvfvDs_b`, posted 20:33 IST 21 Oct) started weak: 160 views at ~1 h (Ep6 had 260, Ep9 234 at the same
  age), 63% swipe away and 7.8 s average watch, the worst on the account. Judge it in the morning.
- **Next upload no earlier than 06:33 IST on 22 Oct.** Ep5 Variant C is up next but NOT approved for posting, NOT queued,
  and has no caption or cover yet. Before posting it needs: an SEO caption (1–2 lines, 5 hashtags, at most 1 emoji) that
  the owner confirms, a cover (text-free Cleo close-up, eyes visible, hands down), and the owner's explicit "yes".
- No AWS instance running. Poster not running. Ep13 ("tests fail only between midnight and 5:30 AM") and the viseme
  lip-sync upgrade are still planned, not started. Don't start either until the owner says so.
- Uncommitted: `insights/build_review.py` (all of the above), plus everything listed in handoff 4 and this file.
  Commit only when asked.

## Rules
Never print tokens. Never edit `how-its-engineered/tools/ig.py`. Nothing is uploaded, reposted or deleted without the
owner's explicit "yes" in chat. No AWS launch until the owner says so; terminate every instance you launch. At least
10 h between @talkingagents uploads. Captions keyword-rich with 5 hashtags. No AI attribution in commits. Don't end a
turn with option buttons; ask questions in plain text.
