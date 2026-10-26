Continue the @how.its.engineered (HIE) "ember" remake job in /Users/samarpit/insta-automation (working dir how-its-engineered/). Read insights/hie-remake-queue.md first. It holds every reel's status and link.

## Where things stand (2026-10-21 09:31 IST)
- Posted overnight as auto trial reels, links in the queue file:
  - 7 v2 remakes: Docker, Kubernetes, Reverse proxies, Rate limiting, Load balancing, Health checks, Idempotency.
  - 2 new topics: #19 Saga, #20 DLQ.
  - 6 hook variants (V1-V6): Saga B, Kubernetes B, Docker B, Reverse proxies B, Load balancing B, Health checks B.
  - Last post was Health checks B at 09:30 IST.
- READY but NOT posted. Their scheduled uploads were stopped at 09:31 when the chat was handed off. Each has a Codex final review PASS, plus media/<dir>/<dir>.mp4, cover.png and caption.txt:
  - V7 Idempotency B (03-idempotency-b)
  - N3 Cron jobs (21-cron-jobs), new topic #21 from TOPICS.md
  - Post them in that order, 30-45 min apart, the first one at least 30 min after the last post.
- Still owed: the morning summary (see the end of this file).
- The remake queue rows 8-15 (Caching onward) are paused by Sam's change of plan. New topics continue in TOPICS.md order: #22 is next. Variants of weak posted reels are allowed; pick them by early stats.

## Early stats (about 06:40 IST, for the summary)
- Trial-reel views (non-followers only, early):
  - Reverse proxies v2: 1574
  - Kubernetes v2: 1376
  - Docker v2: 1337
  - Rate limiting: 1274
  - Health checks v2: 885
  - Load balancing v2: 702
  - Idempotency v2: 322
  - Saga: 194
  - DLQ: 88
- Original posts:
  - Kubernetes "crashed at 3 AM": 17368
  - Docker "works on your laptop": 3094
  - Health "froze at 3 AM": 2616
  - Reverse proxy: about 1862
  - Idempotency "tapped Pay twice": 734
  - Load balancing "Ten million…": 228
- Trial views aren't directly comparable with views on normal posts. Say so in the summary.
- Reverse proxies v2 (posted) shows invalid nginx `proxy_pass api;`. Reverse proxies B fixes it, so suggest replacing v2 with B.

## Helper scripts (tools/remake/bin/, untracked)
- `zsh tools/remake/bin/tts.sh <dir>...`: Gemini voice (Puck, tempo 1.15) plus words.js. Prints `word@time`. Check that the last word is "skipped."
  - It uses ~/.config/gcloud/application_default_credentials.json unless GOOGLE_APPLICATION_CREDENTIALS is set.
- `zsh tools/remake/bin/rr.sh <dir> <reviewname>`: rsync to the PC, render there, scp to media/<dir>/, then the Codex final review into tools/remake/out/fr_<dir>.txt.
  - If the review file comes back empty, rerun `zsh tools/remake/final_review.sh media/<dir>/<dir>.mp4 videos/<dir>/voice/timings.json <name>`.
- `zsh tools/remake/bin/post_at.sh <dir> HH:MM`: waits until that IST time today, posts as an auto trial reel, redacts X-Amz, and lists the S3 bucket (it should be empty). Run it in the background, and add the link to the queue file.
- `zsh tools/remake/stills.sh <dir> t1,t2,...`: times are COMMA-separated. Writes a contact sheet at tools/remake/out/st/<dir>/sheet.png.
- `bash tools/remake/cover.sh <dir> <sec>` writes media/<dir>/cover.png.
- Stats:
  ```
  cd how-its-engineered; set -a; source ../.env; set +a; source ~/.instagram_tokens; python3 -I tools/ig.py stats --n 25
  ```

## Pipeline per topic
1. videos/<nn>-<slug>/script.json: lines of phrases, each {"say","show"}. In "show", *word* = coloured and [words] = pill.
   - Hook: "you + a time/number + a mystery", like the best originals ("Your app crashed at 3 AM…").
   - About 30-40s.
   - End with "If you're a vibe coder, follow for the system design your AI skipped."
2. Codex script review: tools/remake/codex_script_prompt.txt with the script appended:
   `/Users/samarpit/.local/bin/codex exec --skip-git-repo-check --ephemeral -s read-only -o out.txt - < prompt`
   Apply the accuracy fixes, and keep the CTA.
3. Voice: run tts.sh.
   - Whisper mishears some words: set→sit/said, truck→Trek, builds→built, skipped→skit/skip, idempotency→"item potency", "health check" split into 2 words.
   - Fix by rewording, regenerating, or remapping `at()`.
4. video.html: copy the structure of videos/21-cron-jobs/video.html or videos/20-dead-letter-queues/video.html. The shared template is in videos/_ember/.
   - `at(word, n)` normalizes the word to lowercase alphanumerics and throws "no word X #n" if it's missing. Re-check occurrence counts after any hook change.
   - SHOTS `{t,d,f:[x,y,z],s,a,e,sy}`. A larger f x moves content LEFT on screen. s is zoom.
   - Don't name a variable `el`: it clashes with a global.
   - Cover: `cover: { t: 'TOPIC', at: <sec>, zoom: 1, dy: 40 }`, title only.
5. Stills, fix the framing (nothing clipped at the edges, tags readable), then rr.sh. Loop until VERDICT: PASS. NEVER upload before PASS.
6. Cover, then caption.txt:
   - Story hook first line, short explanation, a comment question, at most 1 emoji, 5 broad hashtags (#coding #programming #systemdesign + 2 topical).
7. post_at.sh, at least 30-45 min after the previous post. Sam authorized trial posts without approving each caption.

## Rules
- Render on the PC (sam@192.168.0.103, /mnt/ssd/hie), never on the Mac.
- Never print tokens or keys. Redact X-Amz signatures.
- Ask before deleting anything. Sam deletes old Instagram posts themself.
- Don't commit or push unless Sam asks. No Co-Authored-By or AI attribution lines.
- Don't end a turn with option buttons. Ask questions in plain text.

## Uncommitted changes
- tools/ig.py, voice/gemini_tts.py, videos/_ember/, videos/*-v2/ and *-b/, videos/19-*, 20-*, 21-cron-jobs, tools/remake/ (including bin/), insights files.

## Morning summary (owed to Sam)
- Run stats. Then for every reel posted on 2026-10-21, give its link and early views.
- Compare each one with the original reel on the same topic, and with its v2/B sibling.
- Suggest replacing an original when a remake beats it. Mention the Reverse proxies v2 nginx bug.

## Reel tracker (added 2026-10-21 12:13, Sam asked for it)
- Page: insights/hie-reels.html (local file, not published), generated by `python3 -I tools/remake/bin/tracker.py` (run from how-its-engineered/ with ../.env + ~/.instagram_tokens sourced).
- Registry: insights/hie-reels.json (topic, kind, notes, deleted/scheduled rows). Add a row for every new reel; scheduled rows auto-match by the first caption line.
- Refresh it after every stats fetch and every post.
- PC down since ~09:50: render on the Mac with tools/remake/bin/rr_mac.sh <dir> <reviewname> 8 (Sam OK'd). Covers: node tools/render.mjs 'videos/<dir>/video.html#cover' x.mp4 --stills <t> --outdir <tmp>.

## New workflow (Sam, 2026-10-21 evening) — this replaces "post without approval"
- One topic at a time. Build it (script → Codex script review → voice → video → stills → render → Codex final PASS → cover → caption), then SHOW Sam the mp4 (SendUserFile), the cover and the caption, and wait.
- Only when Sam approves in chat does it go into the upload queue. Nothing is ever uploaded without that approval. No reposts or remakes are uploaded on Claude's own initiative.
- Gaps: at least 8 hours between live uploads (new topics), at least 4 hours between trial uploads (variants/remakes).
- After an approved reel is queued/uploaded, start the next topic in TOPICS.md order.
- In between: check old reels with stats + the tracker. If a reel has stalled but has good engagement (save/share rate above the account average), suggest a repost with a better hook / first line / cover. Suggest only; Sam decides.
- Render: try the PC first (rr.sh); if it's unreachable use the Mac (rr_mac.sh).

## State at 19:30 IST, 2026-10-21
- Account: 333 followers, 39 reels (21 live on the grid, 18 trials). Last upload: Retries v2 trial at 18:30 IST (https://www.instagram.com/reel/Dewd6RjFaG6/). Last live upload: Server-sent events at 13:21 IST.
- Ready, Codex PASS, NOT uploaded, waiting for Sam's approval (new topics → live): 25-database-indexing, 26-query-optimization, 27-n-plus-one (mp4 + cover + caption in media/<dir>/).
- Next new topic: #28 Connection pooling.
- Tracker to-do at 19:30 (Sam does these in the app): delete Caching original (345), Message queues original (498), Load balancing B, Docker B, Health checks v2, DLQ B; make live (one at a time) Caching v2, Message queues v2, Load balancing v2, DLQ, Cron jobs, WebSockets. Re-check before acting; the numbers move.
- Watch: CI/CD v2 (1,165 in 2 h, original 1,353), Service discovery v2, Retries v2. Flat so far: API gateway v2 (164), Circuit breakers v2 (424).

## State at 20:10 IST, 2026-10-21
- Sam deleted 15 reels in the app between 19:30 and 20:00 (Docker v2/B, Kubernetes B, Health v2/B, Idempotency v2, LB B, DLQ B, Service discovery v2, API gateways v2, Circuit breakers v2, the Caching/MQ/CI-CD/Retries originals). 24 reels remain (18 on the grid). Caching v2 and CI/CD v2 are now live.
- **Reel library page (Sam's main view now):** `tools/remake/bin/library.py` writes `tools/remake/out/library.html`; `tools/remake/bin/serve.py 8766` serves it with HTTP Range, so videos play and seek (iPhone too). Open it with preview_start name `hie-library` (.claude/launch.json) → http://localhost:8766/; on the phone: http://192.168.0.101:8766/. Rebuild with `python3 -I tools/remake/bin/library.py` (needs ../.env + ~/.instagram_tokens), then reload.
  - Layout (Sam, 20:30: "like the talkingagents page", insights/review/index.html): same CSS/JS — tiles (views + followers sparklines, fastest, counts), call-outs (waiting for your OK → Watch button; repost idea), tabs Uploaded/Live/Trial/Not uploaded/Deleted/All, one sortable table (thumbnail + name, status pill, views bar, views/h, trend sparkline, last 3 h, watch, likes, shares %, saves %, uploaded, ↗), note chips under each row, click a thumbnail → inline player + full caption under the row, light/dark toggle. Thumbnails cached in tools/remake/out/t/; the first originals play from outputs/<dir> (ORIG in library.py). serve.py allows /media, /outputs, voice wavs and thumbnails.
  - Hand-kept lists in library.py: MADE / WIP (not-uploaded reels), KNOWN (problems the numbers don't show), DIRS (shortcode → media dir for older reels). Update MADE/WIP when a reel is built or posted.
- Waiting for Sam's OK (Codex PASS + cutcheck clean): 25-database-indexing, 26-query-optimization, 27-n-plus-one. Proposed live slots: 21:30 / 05:30 / 13:30 or 21:30 / 09:30 / 21:30 (8 h gap; last live was SSE at 13:21).
- #28 Connection pooling: videos/28-connection-pooling/script.json + voice done (36.5 s; whisper large-v3 hears "follow for … skip." — the usual skipped mishear). NOT done: Codex script review (Codex hit its usage limit until 21:59 IST), video.html, stills, render, final review, cover, caption.
- PC (192.168.0.103) refuses SSH → render on the Mac (rr_mac.sh).
- **post_at.sh bug:** if HH:MM is already past today it posts IMMEDIATELY. Add a date check (or roll to tomorrow) before scheduling any slot after midnight.
- cutcheck: run it with plain `python3` (not -I; it needs numpy): `python3 ../claude-talk-v2/scripts/cutcheck.py media/<dir>/<dir>.mp4 <outdir>`.
- Repo pulled at ~19:50 (27 insights fetches came in); local-only history lines were appended back to insights/history.jsonl. Nothing committed.
- Repost ideas (suggest only): Docker, Service discovery, API gateways, Circuit breakers, Health checks originals are stalled with 1.6–2.2% saves (typical 0.9%).
