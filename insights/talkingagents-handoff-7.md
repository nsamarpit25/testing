# @talkingagents handoff 7 (22 Oct, 09:30 IST)

Rules (owner's words): never print tokens, never edit how-its-engineered/tools/ig.py, nothing is uploaded, reposted or deleted without an explicit "yes" in chat, captions are keyword-rich with 5 hashtags, no AI attribution in commits, no option buttons at the end of a turn (ask in plain text). Commit only when asked. Terminate every AWS instance you launch (keys from repo .env, `unset AWS_PROFILE`). Codex is the final reviewer; if Codex is unavailable, run only the Gemini/Argon review.

## Posting
- Ep5 Variant C was posted at 02:49: https://www.instagram.com/reel/DexWx3HiEfL/
- Ep8 is NOT scheduled anymore: the owner had the 12:00 job cancelled (CANCEL file in ops/ep8_hold, poster stopped). Ep8 is still Up next #1, unposted.

## AWS
- No EC2 instances left in any region (n1, n2 and n3 all terminated; checked every region on 22 Oct ~09:40 IST).

## The 3 overnight episodes (claude-talk-v2)

### Ep14 (normal: fetch() doesn't reject on a 500; "confetti")
- `output/new/ep14_final.mp4`, 60.5 s.
- Sync is 0 ms and there are no hard audio stops. The handle fades out.
- One flash cut: a 0.47 s shot at 44.93–45.40 s (see `scripts/cutcheck.py`).
  - Fix it in `audio/ep14/direct.json`: merge or move that cut.
  - Then re-run `scripts/epx_timeline.py audio/ep14` and re-render only the changed frames on the PC.
- Not yet reviewed by Codex or Gemini. The Gemini prompt is ready: `ops/night/qa/prompt_ep14.md`.

### Ep15 (experiment: CORS taught on a desk whiteboard)
- **Not finished.**
  - Have: `ops/night/ep15_seg_1.mp4` (frames 1–1250) and `ops/night/ep15_seg_1715.mp4` (frames 1715–2014).
  - Lost with n1: the segment for frames **1251–1714** (464 frames).
- Next: render frames 1251–1714 on the PC and encode a video-only segment.
  - PC: `sam@192.168.0.112`, Blender at `~/apps/blender-5.2.2-linux-x64/blender`, work dir `~/ctv2_test`, layout `ctv2_test/ep15/` = `audio/ep15`. Its disk is 98% full, so pull frames off as they finish.
  - Render: `animhq <dir> 1920 64 1251-1714`, 2 processes.
  - Encode: `ffmpeg -framerate 30 -start_number 1251 -i f_%04d.png -frames:v 464 -c:v libx264 -crf 8 -pix_fmt yuv420p`.
- Join the three segments the way `ops/night/fin.sh` does: concat, fade, black tail, `audio/ep15/subs.ass` captions, `mix.wav`.
  - fin.sh needs ffmpeg with libass; the Mac's ffmpeg lacks it and the PC's has it.
  - `audio/ep15/subs.ass` already has the fading handle.
- The Gemini prompt is ready: `ops/night/qa/prompt_ep15.md`.

### Ep16 (experiment: a git bisect nature documentary)
- `output/new/ep16_final.mp4` is v3: 72.1 s, sync 0 ms, 17 cuts, none under 0.6 s, no hard audio stops.
- v3 fixed:
  - Monitor ghosting: unsorted screen keys. `blender/epx.py` `screen_states` now sorts them, which also protects future episodes.
  - A stray "t" blip at 13.15 s: the start of `audio/ep16/l03.wav` is silenced.
  - Cleo frozen in the DOC shots: she now types in lines 2–3.
- v3 has not been viewed frame by frame or reviewed yet.
- History:
  - v1: `output/new/ep16_final_v1.mp4`.
  - v2: Gemini 6.5/10, FIX (`ops/night/qa/argon_ep16_v2.md`).
- Known and left alone: small TTS splices on "habitat"/"earlier", and the long pauses in lines 2–3.

## QA tools
- A/V sync: `python3 ops/night/qa/sync.py video audio/epN/mix.wav`.
- Cut check: `python3 scripts/cutcheck.py video outdir`. No shot under 0.6 s.
- Gemini: `python3 -I scripts/argon_video_check.py video ops/night/qa/prompt_epN.md out.md 2`.
- Codex: `zsh ops/night/qa/codex_review.sh <name> <video> audio/epN "<premise>"`.
  - The script is new. Codex was back at 04:10 (it said "OK"), but the script hasn't been run yet.
- Fix and re-review until PASS.

## Still to do
1. Ep15: render frames 1251–1714 on the PC, join, then QA.
2. Ep14: fix the flash cut, then QA.
3. Ep16 v3: contact sheets, then Codex and Gemini review, then fix.
4. Covers: a text-free close-up of Cleo, eyes visible, hands DOWN. Every rendered frame has burned captions, so render clean frames with `frameshq` on the PC.
5. Add Ep14–16 to Waiting for review.
   - `insights/build_review.py` DRAFTS already list them as "review"; rebuild the page.
   - Captions are in `ops/night/captions.md`.
7. Optional: clean the PC's `~/ctv2_test`.
