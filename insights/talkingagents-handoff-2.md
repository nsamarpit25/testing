# @talkingagents handoff (written 21 Oct 2026, evening IST)

## Where things stand
- 8 reels live, 18 deleted by the owner. Nothing is queued and the poster is not running.
- Last upload: Ep11, 21 Oct 16:15 IST (DewOPkTjG6E). The owner deleted it for slow pace and lip sync. The newest reel still live is the Ep1 remake (DevoQ0dD6T3), posted 21 Oct 10:43 IST.
- Ep12 ("Two hours to center a box") is finished but on hold: `claude-talk-v2/output/new/ep12_final_sync.mp4`. Its caption and cover are in `claude-talk-v2/ops/ep12_hold/`. It has not been approved; the owner is reviewing it.
- Tracker page: `insights/reels-tracker.html` (local file, not published). Build it with `source ~/.instagram_tokens && python3 insights/build_tracker.py`. Catalog: `insights/talkingagents-reels.json`.

## Why the owner deleted 18 of 26 reels (avoid every one of these)
1. Lip sync. Cleo's mouth is a single oval scaled by voice loudness (`blender/epx.py`, the per-frame mouth loop). It never closes on b/m/p or rounds on "oo". On top of that, Ep10-12 had the voice 1.0 s early. That came from a mixer bug in `scripts/epx_timeline.py` and is now fixed with a silent bed from t=0. Always measure line alignment in mix.wav.
2. Cold opens that start with a hook line which is said again later in the video. Never make these again.
3. Too many cuts, flash cuts (shots under 0.6 s, 1-frame screen flashes) and chopped audio (cut-off words, a buzz SFX that stops dead).
4. Copies: shorter "tight" re-cuts and cold-open re-edits of the same episode. 12 of 12 were deleted. Only 2 of 3 full remakes survived. Post one good version per story.
5. Slow pace that drags. Ep10 and Ep11 ran 1.75-1.95 words/s; the kept reels run about 2.1-2.2. This is a guide, not a rule: a pause is fine when the joke needs it.

## Review gate (in this order)
1. `python3 claude-talk-v2/scripts/cutcheck.py <video>`: frame-accurate short shots plus audio hard stops. It must pass.
2. Argon watches the whole video with sound: `python3 claude-talk-v2/scripts/argon_video_check.py <video> <prompt.md> <reply.md> 10`. Use gemini-4-argon on Vertex with ADC auth, about $0.30 per reel. The prompt starts from `claude-talk-v2/ops/argon_lipsync_prompt.md`; extend it with the publish-check list in `ops/publish_check.sh`. Argon caught the 1 s offset that Codex and Claude both missed.
3. Codex (`ops/publish_check.sh`, gpt-6-astra) is optional. It hit its usage limit on 21 Oct after about 180k tokens per video.
4. **The owner is the final reviewer.** Send them the video (SendUserFile) and wait for an explicit yes before queueing anything.

## Pipeline (claude-talk-v2)
Gemini TTS multi-speaker take (Cleo=Leda, Claude=Achird) → take check (`epx_checktakes.py`) → cut into lines → `epx_words.py` (words.json) → `epx_screens.py` → write direct.json → `epx_timeline.py audio/epN` (timeline.json, mix.wav, subs.ass) → Blender 5.2.2 `blender/epx.py` → render on AWS → ffmpeg encode with burned captions (ass filter).
- Heavy work (Blender renders) runs on AWS only, never on the Mac. Use `ops/launch.sh` (loops over regions and instance types; us-east-1 g6.2xlarge worked), `ops/aws_run.sh` and `ops/ssh_config`. The AWS keys are in the repo's `.env`; run `unset AWS_PROFILE` first. The key pair is ctv2-bench (`~/.ssh/ctv2-bench.pem`). Terminate every instance you launch.
- The scripts in `claude-talk-v2/ops/` were copied from old /private/tmp scratchpads, so update the paths inside them (`S=`) before use.

## Posting
- `ops/poster.sh` posts the queue in name order through a copy of `how-its-engineered/tools/ig.py`. Don't edit that file; it belongs to another session. `ig.py --trial manual|auto` posts as an Instagram Trial Reel, which is shown to non-followers first.
- It needs a READY file and an approved md5 in `passed/`. It leaves no files in S3 (bucket hie-reel-staging-30c239, ap-south-1).
- New rule: at least 10 hours between uploads, and only after the owner approves.
- Captions: short, SEO hashtags, different for every reel, at most 1 emoji. No text hook overlay in the first scene. Covers: a text-free close-up of Cleo with eyes visible and hands DOWN (never hands up).

## Live reels at handoff (views at about 20:00 IST)
Ep4 original 2,932 · Ep3 original 2,773 · Ep6 original 2,435 (still growing) · Ep2 original 2,067 (stalled, 47% swipe away) · Ep4 remake 1,846 (32% swipe away, the best hook) · Ep9 original 1,684 (buzz cuts off) · Ep7 original 1,488 (choppy cuts) · Ep1 remake 1,408.

## Rules
Never print tokens. No Co-Authored-By or AI attribution in commits or PRs. Don't end a turn with option buttons; ask questions in plain text. Deleting reels is the owner's job, done in the app.
