# @talkingagents handoff 8 (22 Oct, 18:35 IST)

Rules (owner's words): never print tokens, never edit how-its-engineered/tools/ig.py, nothing is uploaded, reposted or deleted without an explicit "yes" in chat, captions are keyword-rich with 5 hashtags, no AI attribution in commits, no option buttons at the end of a turn (ask in plain text). Commit only when asked. Terminate every AWS instance you launch (keys from repo .env, `unset AWS_PROFILE`). Codex is the final reviewer; if Codex is unavailable, run only the Gemini/Argon review. NEW: never run anything heavy on the Mac (Blender builds/renders/test stills, long encodes, Whisper); use AWS. The owner is the final reviewer: send the video and wait for their OK before posting.

## Posting
- Ep8 was posted 22 Oct 11:09: https://www.instagram.com/reel/DeyQHPbCTHj/
- Ep10b was posted 22 Oct 16:22 with a new caption and cover: https://www.instagram.com/reel/Deyz8hkCuGo/
- **Up next is empty.**
- Each post goes through `ops/<ep>_hold/post_once.sh "YYYY-MM-DD HH:MM"`. It posts only when the file's md5 matches `APPROVED_MD5`. See `ops/ep10b_hold` as the template.
- After every post: rebuild and republish the tracker (`insights/build_tracker.py`, artifact https://claude.ai/artifact/47QhpBSPsXri1aTkyDJbcC) and add the reel to `insights/talkingagents-reels.json`.

## Waiting for review (owner decides; all have Codex PASS; none posted)
- **Ep14 "fetch confetti"**: `output/new/ep14_final.mp4`. Cover: `ops/night/covers/ep14_cover.jpg`.
  - Gemini claims a stumble at 30–31 s; I couldn't confirm it.
  - The `audio/ep14/mix.wav` fix is mix-only (`ops/night/ep14fix/fix_failure_tail.py`). Re-apply it if `epx_timeline` is ever re-run for ep14.
- **Ep15 "CORS whiteboard"**: `output/new/ep15_final.mp4`. Cover: `ep15_cover.jpg`.
- **Ep16 "git bisect documentary"**: `output/new/ep16_final.mp4`. Cover: `ep16_cover.jpg`.
- Captions for Ep14–16 are in `ops/night/captions.md`.
- **Ep17 "Battery 3%"**: emotional, no lesson (the owner asked for this style). `output/new/ep17_final.mp4` is v2, 57.9 s, md5 `3f567c96a7217084d2d2263f3a2659e0`.
  - It has been sent to the owner. Their answer is pending; I asked "post as is, or enlarge Mom's text in the phone shot first?"
  - Story: a storm cuts the power. Claude stays on his own battery, nudges Cleo to answer her mom, and goes quiet at 0%. The lights flicker back on, they say two goodnights, and Mom replies.
  - Reviews: Codex PASS on v1 and v2. Its nits: Mom's text is small in the PHONE insert, and the 9 s opening wide shot. Gemini scored v1 7.5 FIX. v2 fixed the eyes-only dark shot (room floor 0.09, moon 1.1), Cleo's glance at the phone on "I'll answer her", the softer `softbuzz`, and the auto hand gesture on lines 1 and 13.
  - QA: sync 0 ms. The two "short shots" at 48.07–48.23 s are the intended lights-on flicker, not cuts.
  - Cover: `ops/night/covers/ep17_cover.jpg` (frame 700, glow-lit close-up).
  - **Not done yet:** caption (add it to `ops/night/captions.md`) and an `ops/ep17_hold` folder.
  - Files:
    - `ops/ep17/`: `ep17.blend` (the v2 blend), the render scripts `full17.sh`, `fix17.sh` and `fix17b.sh`, and v1 backups in `v1bak/`.
    - `audio/ep17/`: `lines.tsv`, `direct.json`, `timeline.json`, `mix.wav`, `subs.ass`.
  - If you change Mom's text, edit `audio/ep17/screens.json` p2, then rebuild the blend and re-render only the PHONE shots (cuts at frames 1010–1057 and 1608–1667). Re-render whole shots: a new blend can shift poses slightly, and a split shot pops.

## Pipeline notes (new this session)
- `scripts/epx_timeline.py` adds:
  - direct keys `bed: "rain"`, `lights: [[when, room|moon|claude, value, ramp_s]]`, `pglow`, `rain: {speed, density, alpha}`.
  - sfx `thunder`, `powerdown`, `powerup`, `softbuzz`.
  - Rain sound at 5% level.
  - Caption style: outline 4, shadow 1.5.
  - Phrase merging (JOINERS).
- Auto hand gestures alternate on Cleo lines with 5+ words. Setting `hands` on one line shifts the alternation for later lines, so pin them (`N hands rest 10`).
- `blender/epx.py` adds `power_track()` (room/moon/Claude-glow light animation), `build_rain()` (slow window rain) and the BOARDCU camera, and sorts screen keys.
- `scripts/epx_screens.py` adds the `off` screen kind.

## AWS
- n3, n4, n5 and n6 are all terminated. Ep17 was rendered on n6 (a g6.2xlarge with an L4 GPU, us-east-1, about $1/h).
- Launch with `zsh ops/night/launch.sh nN`; it shuts itself down after 8 h. SSH with `ssh -F <abs>/ops/night/nN/ssh_config nN`.
- Watch out: in zsh, never use remote globs like `nN:path/*.mp4`, and use `&&` before any terminate.
- Still running and NOT mine: `i-01f28d16fd2dfe90f` (c7i.4xlarge, ap-south-1, Name `hie-airtag-b`, launched 17:39 IST by another session). Leave it alone.
- Credits: `test-user` can't read billing, and the `manmeet` profile session expired. The owner runs `aws login --profile manmeet` or checks the console (Billing → Credits).

## QA tools
- Sync: `python3 ops/night/qa/sync.py video audio/epN/mix.wav`.
- Cut check: `python3 scripts/cutcheck.py video outdir`.
- Codex: `zsh ops/night/qa/codex_review.sh <name> <video> audio/epN "<premise>"`. Its brief assumes comedy, so for emotional episodes say so in the premise (see the Ep17 premise in `ops/night/qa/codex_ep17_v2.log` / the transcript).
- Gemini: `python3 -I scripts/argon_video_check.py video ops/night/qa/prompt_epN.md out.md 2`.
- Splice check: per-frame PSNR at each join versus the frame-to-frame change in v1.

## Still to do
1. Get the owner's answer on Ep17: post as is, or enlarge Mom's text first.
2. Write Ep17's caption: keyword-rich, 5 hashtags.
3. Post only on an explicit "yes", via a hold folder with `APPROVED_MD5`. Then rebuild and republish the tracker.
4. Ep14–16: waiting on the owner's review.
5. Optional: clean the PC's `~/ctv2_test`. Its disk is about 98% full.
