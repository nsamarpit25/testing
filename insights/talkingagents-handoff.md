# Handoff: @talkingagents 10-video round (2026-10-21, 09:30 IST)

Paste this whole file into the new chat as the first message. Never print tokens.

## Goal
The user approved a round of 10 @talkingagents reels:
- 3 new episodes: Ep7, Ep8, Ep9
- 2 cold opens of older episodes: Ep2, Ep5
- 3 remakes with slightly new scripts: Ep3b, Ep4b, Ep1b
- 2 variants of the new episodes: Ep8 cold open, Ep7 at 1.1×

Post them 30 min apart, then **terminate the AWS instance** (the user said "choke that" when done).

## Status at handoff
**Posted (5 of 10):**

| Item | Reel | Time |
|---|---|---|
| 12_ep2_cold | DevPU3XlBR8 | 07:05 |
| 13_ep5_cold | DevS5AwilR6 | 07:36 |
| 14_ep8 | DevWdzcD_YO | 08:07 |
| 15_ep9 | DevZ_79E5-v | 08:38 |
| 16_ep7 | Devdhj5gq_e | 09:09 |

**Queued** in `$S/queue`. Each has video.mp4, caption.txt, cover.jpg and READY, and has passed the Codex review.
- 17_ep3b: about 09:39
- 18_ep4b: about 10:09

**Held** in `$S/hold`. Both have passed Codex. Move each into `$S/queue` when it is its turn; the queue posts in name order and a head item without READY blocks the queue.
- 20_ep8_cold
- 21_ep7_tight

**Not done: Ep1b** (credit / imposter remake).
- It is rendering on AWS: 1521 of 1899 frames at 09:30, and should finish around 09:37.
- `aws_run.sh` encodes it to `~/ctv2/out/ep1b_final.mp4`, already trimmed by 0.5 s at the start. The log line in `~/ctv2/run2.log` is `ep1b DONE` and then `ALLDONE`.

Paths:
```
S=/private/tmp/claude-501/-Users-samarpit-insta-automation/090cc81c-2b8e-489f-b1db-92f85c47225e/scratchpad   # old session scratchpad; files persist
C=~/.ssh/ctv2_reels.conf   # ssh -F $C awsr  (ubuntu@65.2.141.194, instance i-05dabedf65d80d645, ap-south-1, g6e.2xlarge)
Repo: /Users/samarpit/insta-automation/claude-talk-v2
```

## Remaining steps
1. **Check the poster is alive** with `pgrep -fl poster.sh`. It is `$S/poster.sh` and logs to `$S/poster.log`. It may die when the old chat closes. If it did, restart it:
   ```
   nohup zsh $S/poster.sh >/dev/null 2>&1 &
   ```
   It honours `$S/last_post` and `$S/next_gap`, so it keeps the 30 min spacing. STOP_AT is 15:30.

2. **When Ep1b is done:**
   - Pull it: `scp -F $C awsr:ctv2/out/ep1b_final.mp4 output/new/`.
   - Run the Codex final review:
     ```
     $S/new/codex_review.sh ep1b output/new/ep1b_final.mp4 audio/ep1b/timeline.json "<premise>" -0.5 "Caption styling is the channel's fixed house style; don't flag caption contrast."
     ```
     The premise: Cleo's team lead praised her project, but Claude wrote most of the code and she feels like a fraud. Claude shows her she tested it, decided what to change and kept rejecting his attempts, so it's hers too. Ending: "Now teach me how it works." / "Finally."
   - If it fails, fix the screens or direction in `audio/ep1b`, then:
     - Upload the changed files to `~/ctv2/ep1b/`.
     - Build `ep1bfix.blend` on AWS:
       ```
       blender -b --factory-startup -P blender/epx.py -- ~/ctv2/ep1bfix.blend ~/ctv2/ep1b/timeline.json
       ```
     - Run `bash aws_fix.sh ep1b 0.5 <a-b> ...`. It re-renders only those frame ranges and encodes `out/ep1b_final2.mp4`.
     - Re-review. Repeat until you get `VERDICT: PASS`.
   - Cover: a text-free raw frame from `~/ctv2/out/ep1b/frames/f_NNNN.png` showing Cleo's face (eyes visible, expressive).
   - Caption:
     ```
     AI helped build the project; imposter syndrome took all the credit.
     #AICoding #ImposterSyndrome #DeveloperHumor
     ```
   - Queue it as `$S/queue/19_ep1b`.

3. **Move the variants into the queue:** move `hold/20_ep8_cold` and `hold/21_ep7_tight` into `$S/queue` (after 19). Then `touch $S/QUEUE_CLOSED`, so the poster exits once the queue is empty.

4. **Terminate EC2** once Ep1b, and any fix, is pulled:
   ```
   set -a; source /Users/samarpit/insta-automation/.env; set +a; unset AWS_PROFILE
   aws ec2 terminate-instances --instance-ids i-05dabedf65d80d645 --region ap-south-1
   ```
   Confirm the instance state.

5. **After the last post:** check that S3 bucket `hie-reel-staging-30c239` (ap-south-1) has no leftover staged files from our posts. Delete only our own files; the other session's files stay. Then report the URLs.

6. **Tonight:** fetch stats:
   ```
   source ~/.instagram_tokens && python3 -I .claude/skills/ig-insights/fetch.py
   ```
   Also get `reels_skip_rate` per reel from `/{media-id}/insights?metric=reels_skip_rate`.
   - Compare each variant with its original.
   - Decide on the Ep3 cold open (DevHXkwjrkC) and the Ep5 cold open (DevS5AwilR6).
   - Judge the new episodes.

## Pending decision from the user
The 08:30 summary recommended deleting 3 variants:
- Ep6 cold open: Deu8pHkjs7D, 57% skip, 230 views
- Ep1 tight: DevARh1ARzY
- Ep2 tight: DeunDHHip1m

Ep4 tight (DeuuVtiDydl) was optional. The user hasn't answered. Deleting is their call, done in the app.

Learnings so far:
- A cold open on a strong line cut the skip rate sharply. Ep2's cold open had 25.5% skip, against 47% for the original.
- The 1.1× tight cuts helped only on the slower episodes (Ep5, Ep6).

## Rules (user)
**Posting**
- 30 min between uploads.
- Captions short with SEO hashtags, different for each version, at most 1 emoji.

**Content**
- No text hook in the first frame or scene. Burned-in dialogue captions and the @talkingagents handle are fine.
- The user likes openings where Cleo starts with "Claude…".
- Covers are text-free frames.
- The Codex full-video review (`codex_review.sh`, frames at 2/s plus timed dialogue) must PASS before any upload.

**Infra and handling**
- Never print tokens.
- No Co-Authored-By or AI attribution in commits or PRs.
- Don't end a turn with option buttons; ask questions in plain text.
- Don't edit `how-its-engineered/tools/ig.py`; it belongs to another session. The poster uses a sed copy, `$S/ig_ta.py`.
- Render heavy work on AWS or the PC (`sam@192.168.0.103`, `/mnt/ssd/claude-talk-v2`); quick ffmpeg edits are fine on the Mac. The Mac's ffmpeg has no `ass` filter, so burn captions on the PC or AWS.
- With `pkill -f`, don't use a pattern that also matches your own ssh command line. That killed the shell twice; put remote jobs in small script files instead.

## Pipeline notes
**Episode data and scripts**
- Episode folders are under `claude-talk-v2/audio/<ep>/`: lines.tsv, tts.json, screens.json, direct.json, clips, words.json, timeline.json, mix.wav, subs.ass, screens/.
- Scripts: `scripts/epx_onecall.py`, `epx_checktakes.py`, `ep6_cuttake.py`, `ep1_trim.py`, `epx_words.py`, `epx_screens.py`, `epx_timeline.py`, and `blender/epx.py`.

**Screens**
- The MON camera pushes in, so only about x 300–1150 of the 1600-wide screen stays visible. Keep text inside that area.
- `term` screens now centre themselves there.
- `term` line prefixes: `!` red, `+` green, `*` plain white.

**AWS scripts** (in `~/ctv2`): `aws_run.sh` renders a full episode, `aws_range.sh` renders a frame range, `aws_fix.sh` re-renders ranges and encodes with a lead trim.

**Finished files:** in `claude-talk-v2/output/new/` and `output/trials/`.
