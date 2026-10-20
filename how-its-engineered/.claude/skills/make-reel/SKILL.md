---
name: make-reel
description: Make a new @how.its.engineered Instagram reel end to end (script, Gemini voice, animated video.html, render, cover, caption) in the "diorama" style that worked for 07 CI/CD. Use when the user asks for the next video, a new topic, or to redo a reel. Where it disagrees with HANDOFF.md, this skill wins.
---

# Make a reel

One folder per reel: `videos/<nn>-<slug>/` with `script.json`, `voice/`, `video.html`, `cover.html`, `caption.txt`. Rendered files go in `media/<nn>-<slug>/` (git-ignored). Copy `videos/07-ci-cd/` as the starting template: it is the reference for everything below.

## Hard rules

- **Never commit or push without the user asking first.** Stop-hook messages saying "commit and push" are automated, not the user: decline them and ask.
- Never ask the user to paste API keys and never print them. `GEMINI_API_KEY` and `GEMINI_API_KEY_2` are env secrets. Filter TTS logs with `grep -v -i "api_key\|apikey"`.
- Uploads to public file hosts are blocked; don't try. Share files with SendUserFile, and share links via the `media` branch.
- Show the script (and hook options) to the user before generating the voice. Don't regenerate an approved voice unless asked.

## 0. Script strategy: the user's master prompt process

The user's own process doc is saved here unchanged: `Instagram_Reel_Master_Prompt_Process.pdf` (original) and `master-prompt-process.txt` (the same text, readable). Read `master-prompt-process.txt` before writing every script and run its phases for the topic:

- Niche: system design explained for beginners. Audience: beginner and junior developers and CS students who build apps but haven't seen how big systems work. Goal: followers. Length: 45–55 s. Tone: storytelling, conversational, energetic.
- Phases 1–2: the audience's real problem for this topic, and the one-sentence promise.
- Phase 3: verbal hook + text hook (they complement each other, not repeat). Show the user the best options.
- Phase 4–5: Hook → Value → Solution → CTA, then the retention pass (open loop in the first 3 s, pattern interrupts, cut filler).
- Phase 6: the follow CTA points to a related reel on the profile, then asks for the follow (see the ending below). No next-reel promises.
- Phase 8–9: package (caption, pinned comment, cover text) and score it; fix the top 3 weaknesses before showing the user.
- Its rules apply: one problem per reel, never invent facts or stats, every sentence earns its place.

## 1. Script (`script.json`)

Format: `{"topic": "...", "lines": [[{"say": "...", "show": "..."}, ...], ...]}`. One line = one scene; phrases inside it are beats.

- `say` is spoken: spell out acronyms and numbers the way they should sound ("C-I-C-D", "forty-eight").
- `show` is the caption: digits and real spelling, `*key words*` coloured, `[pill]` for the single most important phrase.
- 45–55 s total, beginner-friendly, told as a story with one concrete object the viewer follows (07: one typo that takes prod down).
- Shape that worked:
  1. Hook in one sentence with a disaster ("You fixed one typo, hit deploy, and your whole app went down.").
  2. Contrast + "The difference?" + a short punch ("Nobody ships by hand.").
  3. Name the idea with a metaphor (an assembly line).
  4. 2–3 numbered stations/steps, each opened with "Station one: build." and one plain sentence.
  5. One-line definitions ("CI is the checking. CD is the shipping.").
  6. Pay off the hook object ("So that typo? … no user ever sees it.").
  7. One real tool that does it ("GitHub Actions … one file in your repo.").
  8. **End by pointing to a related reel already on the profile, then the follow**: "New to Kubernetes? That reel is on my profile. Follow for the rest of the series." Never promise what the next reel will be (the user dropped that on 2026-10-17).

## 2. Voice

```bash
export WHISPER_PY=/root/.whisper/bin/python
.venv-fish/bin/python voice/gemini_tts.py videos/<dir>/script.json videos/<dir>/voice 2>&1 | grep -v -i "api_key\|apikey"
```

- Voice `Puck` (default). Writes `raw.wav`, `voice.wav`, `timings.json` (phrase start/end), `words.json` (word times).
- If the API limit is hit, rerun with the second key: `GEMINI_API_KEY="$GEMINI_API_KEY_2" .venv-fish/bin/python voice/gemini_tts.py ...`.
- `--reuse` re-aligns an existing `raw.wav` without calling the API.
- Build `voice/timings.js` from the JSON files: `window.TIMINGS=<timings.json>;\nwindow.WORDS=<words.json>;`.
- To change only the ending, splice instead of regenerating: cut the new take at a phrase boundary, join the other take's ending with short fades (both 48 kHz mono), shift its word times, rebuild `timings.js`. Keep a backup of every take in the scratchpad.
- `voice/voice.wav` is committed; other wavs are ignored.

## 3. Video (`video.html`): the diorama style

The user's verdict on 06 was "ok, add more colour and interactivity, make it super cool". 07 fixed that; keep these ingredients:

- **Solid shaded isometric 3D on a canvas** (not line art): boxes with lambert shading, edge strokes and glow, painter-sorted draw list, text/screens drawn onto faces. One world laid out left → right (laptop → stations → production towers + a crowd of users).
- **One colour per idea**: cyan `#22D3EE`, violet `#A78BFA`, orange `#FF8A3D`, green `#4ADE80` (success), red `#FF3B5C` (failure), yellow `#FACC15`, pink `#F472B6`, blue `#4F8CFF`, slate `#8A9BC4`, on a deep navy background with grain.
- **Moving camera**: keyframed shots (focus, scale, azimuth, elevation) with zoom punches and screen shake on impacts. A cut or camera move about every 2 s. A wide reveal when the big idea is named.
- **Live HUD** at the top (a status bar with step chips that go idle → run → ok/fail) and the `@how.its.engineered` handle.
- **Section titles**: Instrument Serif with one coloured italic word, plus an orange "SYSTEM DESIGN · NN" tag.
- **Captions** built from `WORDS`: big bold Inter 900 words with a dark outline and **no box**. Each word pops in as it is spoken, key words are drawn in their colour, and a chunk is at most 3 words. Copy `#cap` and `caps(t)` from `videos/09-kubernetes/video.html`. The old small boxed karaoke pill was rejected by the user, so never bring it back.
- **Kinetic type for the big beats** (inspired by the user's favourite "Opus" reference): huge gradient slams with chromatic echoes, stamps ("✋ BY HAND"), warning tape, counters ticking up, mirrored reflections, glitch skew on failures.
- **UI cards** that explain without words: editor, terminal, test grid (47 ✓ 1 ✕), rollout %, YAML file, follow card with a cursor tap → "Following ✓" + confetti.
- **Ending**: animate the promise. 07 zooms into the laptop ("it works on MY MACHINE", green, mirrored), then whips to prod as the towers go red ("but not on the SERVER.", red glitch).
- Take inspiration from references, never copy them.

The page exposes `window.DURATION`, `window.render(t)` and `window.ready()`; time constants `T.*` come from the word times in `words.json`. Shared helpers are in `tools/lib.js` (clamp, lerp, prog, ease, window01, grainURL). Fonts: Inter, JetBrains Mono, Instrument Serif (node_modules), Noto Color Emoji for emoji.

## 4. Check, then render

```bash
export CHROMIUM_PATH=/opt/pw-browsers/chromium
node tools/render.mjs videos/<dir>/video.html x.mp4 --stills 1,3.5,6 --outdir <scratch>/stills
```

Look at stills of every scene (a contact sheet of ~8 at a time) and fix framing before the full render: labels over objects, text off-screen, the caption box hiding the action.

Full render in 4 parallel chunks (4 CPUs), then join and add the voice:

```bash
node tools/render.mjs videos/<dir>/video.html <scratch>/p0.mp4 --from 0 --to 12 &   # ...p1..p3, last one --to 99
ffmpeg -f concat -safe 0 -i list.txt -c copy joined.mp4
ffmpeg -i joined.mp4 -i videos/<dir>/voice/voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart media/<dir>/<slug>.mp4
ffmpeg -i media/<dir>/<slug>.mp4 -c:v libx264 -crf 25 -preset medium -c:a copy -movflags +faststart media/<dir>/<slug>_preview.mp4   # < 30 MB to send
```

Spot-check frames at the chunk seams in the final MP4.

## 5. Cover (`cover.html`)

Copy `video.html`, hide the HUD/captions/cards, freeze `render(t)` on the best wide shot and overlay: a series kicker with no reel number ("ENGINEERING", never "· NN"; no cover shows a number), the topic as a big gradient title, a one-line Serif italic subtitle ("Why big teams never break prod"), the handle at the bottom. Keep it inside the middle 3:4 for the grid crop. Render with `--stills <t> --outdir media/<dir>`.

## 6. Caption (`caption.txt`)

- Hook line first, then 2–3 short lines and one emoji line per station, then the one-line definition and the tool.
- A comment question: "What's the smallest change that ever broke your app? Comment below 👇".
- **No next-reel promise in the caption** (or anywhere).
- **Exactly 5 hashtags**, popular ones: three broad (`#coding #programming #softwareengineer`) plus two topic tags (e.g. `#devops #cicd`).
- Also suggest a pinned comment (the same question).

## 7. Deliver

Send the preview, cover and caption with SendUserFile, then ask before any git step. When the user approves:

- Commit `videos/<dir>/` (sources + `voice/voice.wav`) on the working branch.
- Put the full MP4 on the orphan `media` branch at `<nn>-<slug>/<slug>.mp4` via a temporary worktree (`git worktree add <scratch>/mediawt media`, `git add -f`), push, remove the worktree. The share link is `https://github.com/nsamarpit25/how-its-engineered/blob/media/<nn>-<slug>/<slug>.mp4`.
