# @how.its.engineered — session handoff (2026-10-15)

## Channel (unchanged brief)
- Faceless Instagram Reels, handle @how.its.engineered, name "How It's Engineered | System Design".
- 45–60 sec English system-design explainers told as stories (not interview prep). One idea per scene.
- Goal: a fully automated pipeline. The user only reviews and posts.
- Posted: 01 Rate Limiting and 02 Caching (both in the light "Apple keynote" style).
- Script formula:
  1. Hook
  2. "One word. X."
  3. The naive way
  4. "But wait… can you spot the problem?" (0.9 s pause)
  5. The failure
  6. The smarter way, with an everyday analogy
  7. One-line recap
  8. A question to comment on + "And follow for more!"
- Never promise the next topic.
- Numbers appear as digits on screen and are spelled out in the voice.
- Always show the script and hook options before generating audio or video.
- Caption format: hook first, 2–3 short lines, a question, ~7 hashtags:
  `#systemdesign #softwareengineering #backend #<topic> #coding #programming #techexplained`

## New direction: black line-art style (from reference @speedy_devv)
The user chose this style for new videos. It replaces the light style.
- Pure black background with thin white isometric line drawings that draw themselves in. The scene turns slightly with a moving pointer.
- Captions at the top (y≈150px of 540×960 CSS), centered, Inter 24px gray #a3a3a3. Words appear one by one with a blur-in. Key words are bold white (`*word*`); the most important ones go in a pill (`[word]`).
- IG glyph + "@HOW.ITS.ENGINEERED" watermark near the drawing (top-right; moves left when the scene would cover it).
- Accents used sparingly: red #FF453A for failures, green #32D74B for success. Mono font: JetBrains Mono.
- Thin 4-segment progress bar at the top.
- Terminal box (typing commands) near the end, then a comment box at the end.
- The second reference (@adilet.fndr, navy UI cards + a cartoon presenter) was also prototyped (tests/navy.html), but the user picked black for now.

## Reference videos (in `refs/`, committed)
- `refs/ref_black_speedy_devv.mp4`: THE style reference for new videos (37 s, 720×1280). It promotes "Hairline", a set of animated isometric line drawings for the web. Voiceover summary: "These animated line drawings are going viral… 27 of them for free… a skill that works in any AI agent… isometric figures that move with your cursor… zero dependencies, about 50 KB, MIT… comment 'lines' to get the link."
  - Look: black background, white isometric line art drawing itself in, captions at the top with the key word bold or in a pill, typing terminal boxes, the IG handle near the drawing, a cut about every 2 s.
- `refs/ref_navy_adilet_fndr.mp4`: second reference (39 s). It promotes "Doc", an AI agent team. A cartoon presenter sits bottom-right; it opens on cream paper and switches to dark navy with glowing UI cards; big left-aligned top captions; a `// 03 - topic` chapter label with a live counter; a "Your team" widget that fills up; ends with "comment DOCK for the link". Prototype: tests/navy.html → out/test_navy.mp4.
- Channel's own videos for comparison: `refs/ours_01_rate_limiting.mp4`, `refs/ours_02_caching.mp4`, `refs/ours_04_load_balancing.mp4` (current style, compressed copy). Old cover: `media/legacy/cover_02_caching.png` (git-ignored).
- Old voice comparison: `out/voice_caching_bench/voice.wav` (local re-generation) vs `original_from_video.m4a`.
- To view a reference quickly: `ffmpeg -i refs/ref_black_speedy_devv.mp4 -vf "fps=1/2.3,scale=240:-1,tile=8x2" -frames:v 1 sheet.png`, then look at the image.

## Machine / setup (all done)
- Apple M3 Pro, so Chatterbox runs on GPU via `device="mps"`.
- Project folder: `/Users/samarpit/Developer/how its enginereed` (not a git repo).
- `.venv` (uv, Python 3.11): chatterbox-tts 0.1.7, torch 2.6.0, setuptools<81. Perth (Chatterbox's watermark) needs `pkg_resources`.
- Node v24 + Playwright with Chromium. Fonts come from npm: `@fontsource-variable/inter`, `@fontsource/jetbrains-mono`, `@fontsource/instrument-serif`.
- ffmpeg 9 (Homebrew).
- Whisper for checking takes: `~/Developer/reel-builder/.whisper/bin/python` with faster_whisper; models are already in the HF cache (small.en, medium.en).
- Cloudflare WARP was uninstalled. It had leaked about 2,300 processes and caused "fork failed" shell errors.
- The user freed about 175 GB, so disk space is fine now.

## Files
- `voice/zac.wav`: the exact reference clip (10.5 s, 24 kHz, made with Orpheus "zac").
- `voice/generate.py`: the "young custom B" voice. Chatterbox clones zac.wav one phrase at a time.
  - Settings: exaggeration=0.6, cfg_weight=0.3; trims silence (threshold 0.01, keeps 10 ms before and 50 ms after).
  - Pauses: 0.3 s between phrases, 0.55 s at line end, 0.45 s after "...", 0.9 s after "spot the ...".
  - Seed per phrase: seed + li*100 + pi (default 1234).
  - Saved takes live in `<out>/takes/LL_PP.wav` and are reused on reruns.
  - Writes `raw.wav`, `timings.json` (li, pi, say, show, start, end) and `voice.wav`. voice.wav goes through the ffmpeg post chain: pitch ×1.07, EQ, compressor, loudnorm −14, 2 s pad.
  - Usage: `.venv/bin/python voice/generate.py <script.json> <outdir> [--seed N] [--redo 6.2,4.5]`
  - To fix a bad take: `--redo li.pi --seed <new>`, then check it with Whisper.
  - Speed: about 13 s to load and about 5 min to generate 60 s of audio. The old cloud CPU took about 16 min.
- `tools/render.mjs`: renders an HTML page (window.DURATION + window.render(t)) to MP4.
  - Viewport 540×960 at deviceScaleFactor 2, so 1080×1920 at 30 fps. PNG frames are piped to ffmpeg (libx264 crf 19, yuv420p, aac 192k).
  - `node tools/render.mjs page.html out.mp4 [--audio voice.wav]`
  - `--stills 1.3,5,9.2 --outdir dir` writes preview PNGs. Their names aren't zero-padded, so sort them numerically.
- `tools/lib.js`: shared helpers (clamp/lerp/prog/ease/ep/window01, el(), makeCaptions(container, cues), mouthOpen, grainURL).
  - Cues: `{t, end, text, dur}`. With `dur` set, words are spread over the spoken phrase by length.
  - Caption markup: `*key words*`, `[pill]`, `_serif emphasis_`, `|` for a line break.
- `tools/iso.js`: the isometric line-art engine.
  - Camera: CAM {yaw, scale}, P(), aim(focus, sx, sy).
  - Primitives: box() returns the visible faces; fpoly/fline/fdot/ftext work on faces; cylinder(), rack(), packet(), tileDots().
  - `emit(obj, drawProgress, opacity)` draws an object with a staggered line draw-in. Running the progress from 1 to 0 draws it out.
  - ftext puts text flat on a face. Use flipV(F) for upright text on vertical faces.
- `tests/black.html`, `tests/navy.html`: the 20 s style tests. Rendered to `out/test_black.mp4` and `out/test_navy.mp4`.
- `legacy/`: everything from the previous chat. The old templates for videos 01 and 02, style.css, generate_voice_caching.py, timings_caching.json, both posted MP4s, and cover_02_caching.png (the old light-style cover layout).
- `out/voice_caching_bench/`: the Caching voice regenerated locally, for A/B against the original.

## Video 03 — Idempotency (IN PROGRESS)
- Folder: `videos/03-idempotency/`
- `script.json`: the approved script (hook 1: "You tapped Pay twice... Why weren't you charged twice?"). Each phrase has `say` (spoken) and `show` (caption markup with digits).
- `voice/`: done, 58.2 s (voice.wav is 60.15 s with padding). Whisper checked every phrase.
  - Phrase 6.2 "Yes?" was garbled and was regenerated with seed 77. Don't regenerate the voice unless asked.
- `timings.js`: built from voice/timings.json (`window.TIMINGS=[...]`). Rebuild it if the voice changes.
- `video.html`: the full render(t) page.
  - Objects: phone (with a "PAY $50" screen) at world (0,150), payment server (2 racks) at (0,−150), elevator at (0,0).
  - Scenes:
    - L0–1: close-up on the phone, double tap.
    - L2: wide shot; the request travels, gets charged, "OK" comes back.
    - L3: dim for "spot the problem".
    - L4: slow network, the reply is lost, a retry, two charges (red receipt, TOTAL −$100).
    - L5: ID 7F3A tag, the request is charged and the "SEEN PAYMENT IDS" ledger appears.
    - L6: a retry with the same ID, the ledger shows ✓ SEEN, "same answer" comes back, "CHARGED ONCE ✓".
    - L7: the phone and server draw out, the elevator draws in, its button is pressed ×10, the doors open, "ARRIVES ONCE".
    - L8: back to the wide shot plus a terminal: POST /pay id=7F3A, "charged $50 ✓", then "already done · no charge ✓".
    - L9: a comment box types "API retries".
  - Previews looked good. Two fixes were pending when the session ended (check whether they're already in the file):
    1. Move the "SLOW NETWORK" and "2 REQUESTS" labels off the phone: `mp[0] - 105, mp[1] - 58` and `mp[0] - 105, mp[1] - 36`.
    2. From L8 on, move the watermark to the left (left 42px, align flex-start), because the server rack covers it in the final wide shot.

## Next steps
1. Apply or verify the two fixes. Then render: `node tools/render.mjs videos/03-idempotency/video.html media/03-idempotency/idempotency.mp4 --audio videos/03-idempotency/voice/voice.wav` (about 2–3 min).
2. Check the stills, then send the MP4 to the user.
3. Cover (1080×1920) in the black style: "SYSTEM DESIGN · 03" (small caps, gray/white), big title "Idempotency", a one-line subtitle (e.g. "Why you're never charged twice"), and a simple isometric line drawing (phone + PAY button, or the elevator button) with the handle at the bottom. Keep everything inside the middle 3:4 for the grid crop. Render it as a still from an HTML page.
4. Caption text in the format above (hook first, short lines, a question, 7 hashtags with #idempotency).
5. Send the user all four for review: video, cover, caption, and a voice note if needed.
6. Later: automate one video a day from the 110-topic list in `TOPICS.md` (script → approval → voice → video → cover → caption).
