# Handoff: HIE trial variants (24 Oct 2026, ~21:45 IST)

## Goal
Grow @how.its.engineered by posting **trial-reel variants** of reels that are already live. Sam's rules:
- Trials only (`post_at.sh <dir> HH:MM trial`). Never post a variant as a normal reel. No brand-new topics.
- At least 20 min from any other HIE post. Any hour is fine.
- Every variant is a **real re-make**. Speed, trim and text-overlay tweaks get flagged by Instagram as "already uploaded" (that is why the first queue was stopped). Change all of these: script (story or paradox first), voice take, camera order and angles (re-render on the PC), music bed, cover and caption. The length must differ by at least 1–2 s.
- **Voice is always Gemini "Puck"** (the account's voice).
- Review with Argon/Codex is optional (my call). Tell Sam when a trial beats its original; Sam deletes the original and makes the trial live.
- Build one reel, schedule it, then start the next.
- Memory file: `hie-trial-variants.md`.

## Status
| Variant | Code / time | Notes |
|---|---|---|
| 30-maps-traffic-t2 | De4dSHkCURr, live | Charon voice; went out before the Puck rule. Offer Sam a Puck re-make. |
| 31-tap-to-pay-t2 | De4gvgMDvLH, live | Puck |
| 33-gps-t2 | De4jDiHjxmq, live (logged) | Puck, Argon PASS |
| 36-touchscreen-t2 | 22:09 trial | Puck, Argon PASS |
| 34-shazam-t2 | 22:29 trial | Puck, 49.4 s (orig 46.9), cutcheck clean, Argon PASS (`tools/remake/out/gem/check_sz2_reply.md`). |
| Sharding t1 | De4Z7ChEQRH, live | Old tweak-only variant |

The three scheduled posts run as `post_at.sh` background shells in the old chat. Check each one published (`insights/hie-reels.json` / `ig.py`). If one didn't, re-schedule it with `post_at.sh`. Then register them:
`python3 -I tools/remake/bin/log_variants.py <dir with the post logs>`. It needs lines like `posting <dir>-t2 (trial)` and `published: https://www.instagram.com/reel/<code>/`. If the logs are gone, add rows to `insights/hie-reels.json` by hand (kind `variant`, note from `media/<dir>/variant.txt`).

## Pipeline (run from how-its-engineered/)
1. `rsync -a --exclude voice videos/<d>/ videos/<d>-t2/; mkdir videos/<d>-t2/voice`
2. New `script.json` (lines of `{say, show}`): story or paradox hook first, then the original mechanism lines, no follow CTA.
3. Voice: source `../.env`; `GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json`; `WHISPER_PY=$PWD/tools/remake/bin/whisper_pc.py` (Whisper runs on the PC).
   - Generate: `"~/Developer/how its enginereed/.venv-fish/bin/python" voice/gemini_tts.py videos/<d>-t2/script.json <D> --voice Puck --vertex --tempo 1.15`
   - Gentle trim: `silenceremove=start_periods=1:start_threshold=-50dB:stop_periods=-1:stop_duration=0.4:stop_threshold=-50dB:stop_silence=0.32` on raw.wav.
   - Realign with `--reuse`, then build voice/words.js (`window.TIMINGS=…; window.WORDS=…;`).
   - To change length, run `atempo` on raw.wav and `--reuse` again.
   - DURATION = last TIMINGS end + 1.8.
4. Remap `video.html`:
   - T anchors: `at(word, n)` throws if the word is missing.
   - CUT order and the `cut()` list (CUTS must be in time order).
   - Order-dependent `inShot` ranges, plus absolute times inside scenes (offset them by the scene's CUT).
   - `tags()` a/b times, tools card, `T.last = WORDS[WORDS.length-1][2]`, `END: T.last + 0.35`, `follow: CUT.END + 0.9`, new `cover` text/time.
   - Shift camera angles (a) by about 0.15–0.3 for new pixels.
5. PC `sam@192.168.0.113` (ssh `-o BatchMode=yes -i ~/.ssh/id_ed25519`):
   - `rsync videos/<d>-t2` → `/mnt/ssd/hie/videos/`.
   - Stills: `cd /mnt/ssd/hie; export PATH=$HOME/.local/share/mise/shims:$PATH CHROMIUM_PATH=/usr/bin/chromium; node tools/render_gpu.mjs videos/<d>/video.html /tmp/x.mp4 --stills 0.0,1.5,... --outdir st/<x>`. Avoid dark or empty first frames.
   - Full render: `bash /mnt/ssd/hie/render_pc.sh <d> <d> 10` → `/mnt/ssd/hie/out/<d>.mp4` (~70 s).
6. Music bed:
   - `"~/Developer/how its enginereed/.venv/bin/python" tools/remake/bin/bed.py raw.mp4 b.mp4 --seed N --cuts <line starts-0.1> --db -21`
   - `ffmpeg -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=9 -ar 48000 -c:a aac -b:a 192k`
   - `python3 ../claude-talk-v2/scripts/cutcheck.py`
7. Optional Argon: `python3 ../claude-talk-v2/scripts/argon_video_check.py <mp4> <prompt.md> <reply.md> 5` (prompt examples in `tools/remake/out/gem/check_*_prompt.md`).
8. Write the media folder `media/<d>-t2/`:
   - `<d>-t2.mp4`
   - `cover.png`: render `video.html#cover` on the PC with `--stills <t>`.
   - `caption.txt`: new hook line, extra fact, question, 5 hashtags.
   - `approved.md5`: `md5 -q`.
   - `variant.txt`: topic line, then a note.
9. Schedule: `zsh tools/remake/bin/post_at.sh <d>-t2 HH:MM trial` (run it in the background), at least 20 min after the previous HIE post. The last slot is 22:29, so the next is 22:49 or later.

## Next
- More re-makes in the same style. Candidates are the system-design ember reels (Rate limiting, Cron jobs, N+1, Connection pooling, Load balancing, WebSockets, Retries), then Docker, Circuit breakers and others. Ask Argon for a story/paradox hook per reel; `tools/remake/out/gem/why_maps_reply.md` shows the format.
- Later: compare trial stats against the originals (views, `reels_skip_rate`, average watch) and tell Sam about any winners.

## Don'ts
- Don't commit or push unless asked; no AI attribution lines.
- Don't delete posts (Sam does).
- Don't kill jobs you didn't start.
- Leave `videos/_ember` untouched.
- No heavy jobs on the Mac.
- Never read `~/.ssh`.
- Ask in plain text, no option buttons.
