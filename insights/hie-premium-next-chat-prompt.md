Continue @how.its.engineered. Repo /Users/samarpit/insta-automation, work in how-its-engineered/.

Read memory first (it lives in ~/.claude-3; don't create new memory files):
/Users/samarpit/.claude-3/projects/-Users-samarpit-insta-automation/memory/MEMORY.md, then hie-overnight-batch.md, hie-library-page.md, reel-qa-gate.md, hie-approval-cadence.md, user-final-reviewer.md, gcp-budget-cutoff.md.

GOAL (22 Oct night → morning of 23 Oct)
Build three new "everyday tech" experiment reels, one at a time, each the best version you can make before starting the next:
  35-face-id      How Face ID recognises you in the dark
  36-touchscreen  How your touchscreen knows it's your finger
  37-qr-code      How a scratched QR code still scans
They go to the library's "Waiting for review" tab (MADE in tools/remake/bin/library.py, not NEXT). Sam reviews in the morning. Never upload or schedule anything.

THE BAR: PREMIUM, NOT CHILDISH
Sam's verdict on our current reels: they feel childish, not premium. These three must feel premium: simple, calm, expensive. Think Apple product film / keynote reveal, not a cartoon explainer.
- Colour: pull the saturation down. Near-black or deep graphite backgrounds, one restrained accent colour per reel, neutral greys and whites. No rainbow palettes, no candy colours, no glow everywhere.
- Objects: real-looking, well-made props (brushed aluminium, glass, matte ceramic, soft rubber), with proper materials, soft studio lighting, subtle reflections, soft shadows and shallow depth of field. Fewer objects, each one beautiful. Add an object only if it makes the idea clearer or the frame richer.
- Motion: slow, eased, deliberate camera moves (dolly, orbit, rack focus). No bouncy or springy easing, no jitter, no popping in. One idea per shot, with breathing room.
- Type: one clean typeface, restrained sizes and weights, plenty of negative space. Captions are quiet, not shouting. No emoji-style icons or clip art.
- Interactivity stays: like GPS, Shazam, AirTag and Maps, the mechanism is SHOWN in 3D plus phone UI, in sync with the voice. Premium does not mean static.
Before building each reel, render 2–3 style stills (hook frame, mechanism frame, story frame) and look at them hard. Ask yourself: does this look like it cost money? Send the stills to Sam with SendUserFile and keep going; adjust if Sam replies.

STUDY FIRST
Open the existing experiment reels and learn what worked and what didn't: videos/29-airtag, 29-airtag-b, 30-maps-traffic, 31-tap-to-pay, 32-noise-cancelling, 33-gps, 34-shazam. Read their scenes.js, kit.js, script.json and video.html, the finished mp4s in media/<dir>/, and the reviewer notes in tools/remake/out/fr_<dir>.txt and tools/remake/out/gem/gem*_reply.md. Check how they did on Instagram in insights/hie-reels.json, insights/history.jsonl and the library.py NOTES. For example, AirTag v1 had a 38.6% skip rate, so the re-cut put the story first. Reuse the build and render machinery; replace the look.

TOPIC NOTES (from Codex + Argon, saved in tools/remake/out/gem/topics_next2_{codex,argon,prompt}.md)
Each reel: a relatable hook, a mechanism shown in 4–6 visual beats, ONE real documented story, and a twist ending. About 45–55 s.
- Face ID: an infrared flood light plus about 30,000 invisible dots build a 3D map of your face, so a flat photo fails. Story: Nov 2017, the Vietnamese security firm Bkav beat iPhone X Face ID with a mask that cost about $150. Twist: "your phone doesn't know what your face looks like, it knows its shape." Say "3D face unlock". Many Android phones only use a 2D camera.
- Touchscreen: an invisible grid with a weak electric field under the glass. A finger (salty water) disturbs it at one spot; a pen or fingernail doesn't; a raindrop touches many spots at once. Story: the South Korean snack-sausage stylus (winter 2010). Verify it in reputable sources first; if it isn't solid, use CERN 1972–73 (Bent Stumpe and Frank Beck). Say "capacitive" in the script only if it helps. Twist: "you've never pressed a button; your finger becomes part of the circuit."
- QR code: the three corner squares find the code and its angle; the grid straightens; the cells are bits; backup (error-correction) data rebuilds missing parts. Story: 1994, Masahiro Hara at Denso Wave took the grid idea from Go, and the team studied printed matter to find a corner pattern that almost never occurs by chance. Fact traps: only the highest level (H) survives about 30% damage, and many codes use less. Set it on a menu or poster so it doesn't overlap tap-to-pay.

PIPELINE (per reel; finish one completely before the next)
1. Script → Codex review (tools/remake/codex_script_prompt.txt pattern, codex exec) and Argon review (gemini-4-argon on Vertex; claude-talk-v2/scripts/argon_video_check.py for video; a text-only call for scripts). Fix and re-review until both are happy. Check every fact in the story against reputable sources.
2. Voice: tools/remake/bin/tts.sh <dir>, Vertex only (gemini-3.8-flash-tts, region global, style in a [bracketed] tag, --tempo 1.15). Re-take any line that ends at full volume (epx_timeline.py warning).
3. Build videos/<dir>/ (three.js scenes in the premium look). Check timing on the Mac only with quick stills or low-res previews.
4. Render on the PC: tools/remake/bin/rr.sh <dir> <name> (rsync to sam@192.168.0.112, render_pc.sh, pull back to media/<dir>/, Codex final review into tools/remake/out/fr_<dir>.txt). Cover: tools/remake/cover.sh <dir> <time>. Caption: media/<dir>/caption.txt.
5. QA gate: claude-talk-v2/scripts/cutcheck.py on the mp4; Codex final review must say PASS; Argon watch with audio (write a gem<dir>_prompt.md like gem33gps_prompt.md, with topic-understanding questions plus confusion, safe zones and audio checks) must PASS. Also ask both reviewers directly: "Does this feel premium or childish? What would make it feel more premium?" Fix and re-render until all pass. Any re-render reruns cutcheck + Codex + Argon.
6. Record the final md5 in the library.py NOTES, add the reel to MADE ("Waiting for review"), rebuild with python3 -I tools/remake/bin/library.py, and SendUserFile the mp4 + cover to Sam.

PC
If sam@192.168.0.112 isn't reachable over SSH, try again later. AWS rendering is allowed when the PC is down (memory aws-render-ec2.md: reuse a running instance, terminate any you launch). Never run heavy renders, Blender, long encodes or Whisper on the Mac.

STATE CONTEXT
- Live tonight (another session, on Sam's OK): 26-query-optimization-v2 19:37, 30-maps-traffic 21:37, 33-gps 22:44 IST. Up next (NEXT): 27-n-plus-one-v2, 28-connection-pooling-v2, 31-tap-to-pay, 32-noise-cancelling. Don't touch the queue.
- Vertex may fail on billing if the GCP budget cutoff fired (see gcp-budget-cutoff.md). Check the function logs and tell Sam; don't re-link billing yourself.

RULES
- Never upload or schedule. Nothing goes in NEXT without Sam's OK.
- No commits or pushes without asking. No Co-Authored-By or AI attribution.
- Never print API keys. Never read ~/.ssh.
- Never kill jobs you didn't start.
- Leave videos/_ember/ untouched.
- Another session also edits library.py, so keep edits small.
- Share files with SendUserFile. End turns with a plain-text question, no option buttons.
- In the morning, report for each reel: the md5, reviewer verdicts, what you'd still improve, and the reel itself.
