# @talkingagents handoff 6 (written 22 Oct 2026, ~01:40 IST)

Read `insights/talkingagents-handoff-5.md`, then `-4.md`, `-3.md` and `-2.md` for the pipeline, review gate, posting and
rules. This file covers what changed after handoff 5.

## IN PROGRESS: the Ep10b render (finish this first)
Ep10b = Ep10 with a new opening, a new line 3 and a new ending. Only those parts are rendered; the middle is reused from the old video.
- **New lines** (owner picked them): line 1 Cleo "Claude, how do I unsend one email... from forty thousand inboxes?"
  (opening O2), line 3 re-recorded without the laughing voice (the old take laughed right after a panicked opening),
  line 16 Claude "Tell them it took years of practice." (ending E2). Audio dir `claude-talk-v2/audio/ep10b`.
  Complete audio sent to and approved by the owner (`output/new/ep10b_full_audio.m4a`); the owner said "ok render".
- **Timing:** `audio/ep10b/durs.txt` is hand-set so every middle line shifts by exactly 36 frames: line 1 = 5.50034,
  line 3 = 4.58870, line 10 = 0.722 (the stale value the Ep10 render used). Don't re-run `ep1_trim.py` without restoring these.
- **Splice:** new frames 1-390 + old Ep10 frames 355-1400 (`output/new/ep10_final2.mp4`, its captions already burned)
  + new frames 1437-1562, with fade, 0.5 s black and `audio/ep10b/mix.wav`. Captions are burned on the new parts only,
  with Arial from the Mac (the same font the AWS encodes used).
- **Render, running on two machines:**
  - PC `sam@192.168.0.112` (the owner's PC; its old address .103 is dead). Work dir `~/ctv2_ep10b`. `run.sh` renders
    1-390, then 1437-1562, into `out/frames` and writes `DONE` or `FAILED`; log `run.log`. Placeholders mean it skips
    frames that already exist.
  - AWS **g5.xlarge `i-06bad1c3f6c640688`, us-east-1**, 35.175.248.27 (g6e/g6 had no capacity), tag ctv2-ep10b.
    `ssh -F claude-talk-v2/ops/ep10b/aws_ssh_config aws10`. `~/ctv2/run.sh` renders 300-390, then 1437-1562, then
    250-299, and touches `~/ctv2/DONE`. **Terminate it when its frames are copied** (keys in the repo `.env`, `unset
    AWS_PROFILE`, `--region us-east-1`). It also shuts itself down after 8 h (shutdown behaviour = terminate).
  - Relay: `claude-talk-v2/ops/ep10b/relay.sh` copies AWS's finished frames to the PC every 20 s (via the Mac). It was
    running in the old session; if it stopped, run it again. If no frames get relayed, the PC renders them itself, just slower.
  - At 01:37 IST: 243/516 frames, about 29 frames/min combined, expected done about 01:47.
- **Then:**
  1. Check all 516 frames exist on the PC: `ls ~/ctv2_ep10b/out/frames | wc -l`, with 1-390 and 1437-1562 non-empty.
  2. Terminate the AWS instance and confirm with describe-instances.
  3. On the PC, run `~/ctv2_ep10b/splice.sh` to get `ep10b_final.mp4`. Copy it to `claude-talk-v2/output/new/ep10b_final.mp4`.
  4. QA:
     - `python3 claude-talk-v2/scripts/cutcheck.py` on it.
     - A/V sync: cross-correlate the line wavs against the video audio. Every line should land on its timeline t0 (the
       method is in the old session: envelope cross-correlation; Ep10 had been exactly 1.00 s early before the mixer fix).
     - Look at frames around both joins (new frame 390/391 and 1436/1437) and compare the caption look.
     - Argon is optional and unreliable on timing: on the fixed Ep10 it claimed a 0.5-0.8 s lead that frame checks disproved.
  5. Send the video to the owner (SendUserFile) and add it to the review page (`DRAFTS` in `insights/build_review.py`,
     kind "review"), then rebuild the page. Nothing posts without the owner's explicit yes.

## Other changes this session
- **Ep10 timing fix:** `output/new/ep10_final_sync.mp4` is the old Ep10 picture with the corrected mix (it was 1.00 s
  early). It's in "Waiting for review" on the page. Ep10b replaces it if the owner likes Ep10b.
- **Ep8 Original** (`output/new/ep8_final2.mp4`) was added to Up next as #2 after Ep5 Variant C, at the owner's
  request ("there is no issue"). Cutcheck still flags "For seven years?" cut off at 33.1 s and a 0.47 s shot at 8.5 s.
  The owner was told and hasn't asked for a fix. It's the same file as the deleted Ep8 Original (DevWdzcD_YO).
- Review server: a stale `review_server.py` was killed and restarted via `preview_start reel-review`.
- Numbers at 00:15 IST: 8 live, 136 followers, 15,604 total views. Ep12 had 412 views at 3.7 h, swipe-away down from 63% to 48%.

## Queue / timing
- Up next: #1 Ep5 Variant C, #2 Ep8 Original. Neither has a caption or cover yet, and neither is approved.
- Earliest next upload 06:33 IST 22 Oct, then at least 10 h between uploads.

## Uncommitted
`insights/build_review.py`, `claude-talk-v2/audio/ep10b/`, `claude-talk-v2/ops/ep10b/`, the new outputs and this file. Commit only when asked.

## Rules
Never print tokens. Never edit `how-its-engineered/tools/ig.py`. Nothing is uploaded, reposted or deleted without the
owner's explicit "yes" in chat. Terminate every AWS instance you launch. At least 10 h between uploads. Captions are
keyword-rich with 5 hashtags. No AI attribution in commits. No option buttons at the end of a turn; ask in plain text.
