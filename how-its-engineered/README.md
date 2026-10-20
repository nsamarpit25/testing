# How It's Engineered

Code for the faceless Instagram Reels channel @how.its.engineered: system design topics as animated isometric line drawings with a voiceover.

## Layout

- `videos/<nn-topic>/`: one folder per reel. `script.json` (voiceover lines), `video.html` (the animation, driven by `voice/timings.js`), `cover.html`, `caption.txt`.
- `tools/`: `render.mjs` (Playwright → MP4), `iso.js` (isometric drawing kit), `lib.js`, `build_preview.py` (single-file preview with audio), `sheet.sh` (contact sheet of stills).
- `voice/`: `gemini_tts.py` (Gemini TTS + Whisper word alignment).
- `tests/`, `legacy/`: style prototypes and the templates for videos 01 and 02.
- `TOPICS.md`: the 110-topic plan. `HANDOFF.md`: working notes.
- `refs/`: reference videos. Two outside style references plus our own reels 01, 02 and 04 for comparison.
- `media/` (git-ignored): full-quality rendered MP4s and covers.

## Setup

```bash
npm install && npx playwright install chromium
cp .env.example .env   # add GEMINI_API_KEY
```

## Make a reel

```bash
.venv-fish/bin/python voice/gemini_tts.py videos/04-load-balancing/script.json videos/04-load-balancing/voice
node tools/render.mjs videos/04-load-balancing/video.html media/04-load-balancing/load_balancing.mp4 --audio videos/04-load-balancing/voice/voice.wav
node tools/render.mjs videos/04-load-balancing/cover.html /dev/null --stills 0 --outdir media/04-load-balancing
```

Requires Node, Python 3.11, and ffmpeg.
