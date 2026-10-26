# @talkingagents — reel review and trial-reel plan (2026-10-21)

92 followers · 5 reels · ~10k total views. Stats fetched 2026-10-21 00:33 IST.

| Ep | Reel | Length | Views | Reach | Skip rate | Avg watch | Watched % | Shares | Saves | Comments |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 1 | who really built it, me or the ai? | 62s | 1,600 | 1,324 | 44.2% | 18.8s | 30% | 9 | 8 | 0 |
| 2 | She pushed the key. Then she pushed the new key. | 77s | 2,059 | 1,486 | 46.9% | 30.4s | 39% | 1 | 2 | 4 |
| 3 | She asked for a quick cleanup. Claude rewrote everything. | 82s | 2,514 | 1,775 | **36.1%** | 33.4s | **41%** | **28** | 7 | 2 |
| 4 | 45,000 database reads. 1 user. It was me. | 91s | 2,411 | 1,924 | 42.6% | 34.0s | 37% | 3 | **14** | 1 |
| 5 | 40 minutes. 11 tries. The button stayed blue. | 82s | 1,337 | 923 | 42.0% | 27.6s | 34% | 0 | 1 | 0 |

Ep 5 is ~7 hours old and still climbing; the others have flattened.

## Most underrated: Ep 3, "Clean it up real quick"

Best on every quality signal: lowest skip rate (36% vs 42–47%), highest watch-through (41%), and 28 shares, about 1.6% of reach. The other four reels have 0–9 shares between them. Shares are the strongest push signal, yet it stalled at the same ~1.8k reach as the rest. The content works; the packaging (first frame, length) stops it from leaving the first test pool.

Runner-up: Ep 1. It has the weakest opening ("My senior told…", 30% watched), but 17 shares+saves on 1.3k reach. The emotional topic lands with the people who stay.

## What every reel has in common (the levers)

1. **Same first frame every time.** Wide shot of Cleo at the desk (Ep 4 and 5 open on a screen insert). Someone who has seen one episode reads it as "seen this" and skips. 36–47% skip in the first seconds.
2. **No burned-in text hook.** The scripts plan one ("Never say 'clean it up' before git commit", "45,000 database reads. 1 user."), but it isn't on the first frame of the renders.
3. **Captions sit low** (~85–90% down the frame, over the keyboard), where Instagram's caption/username overlay covers them on phones.
4. **Long: 62–91s.** Average watch is 19–34s. Most viewers never reach the punchline, which is where shares come from.
5. **Audio is voice + synthesized SFX only.** No music bed, no trending sound.
6. **One format only:** 3D two-character dialogue. Trial reels go to non-followers, so "Ep. 3" framing and series callbacks mean nothing to that audience.

## Trial-reel experiments (in priority order)

Each trial changes one *family* of things, so the result tells us something. Judge each against its parent after 48–72h on skip rate, watch %, and shares/reach.

### T1 — Ep 3 short cut, cold open (ffmpeg only, Mac)
- Open on the red error screen + "But the architecture is gorgeous." Then "3 hours earlier…" and jump back.
- Burned-in text hook on frame 1: **"I asked AI to 'clean up' my working code"**.
- Cut to ~35–40s: drop the 19-console-logs and git-checkout beats, keep checkpoint rewind → "Nobody move, I'm committing" → "I liked you better when you panicked."
- Captions moved up to ~65% height, bigger.
- Tests: hook + length. If this beats the parent, re-cut everything this way.

### T2 — Ep 3 loop meme, 10–12s (ffmpeg only)
- Just: "Clean it up real quick" → "Done! I merged your helpers, renamed every variable…" → red screen → "It's broken right now, obviously. But the architecture is gorgeous." Hard cut back to the start so it loops.
- Text: "POV: you let AI 'refactor' before committing".
- Tests: whether a short, rewatchable format beats the story format. Short loops get high completion and replays.

### T3 — Ep 2 with a new hook and audio (ffmpeg + one new insert)
- Ep 2 had the most comments (4) but the worst skip rate (46.9%). It opens on a terminal, a quiet frame.
- New first frame: phone lighting up with **"$2,000 bill"** + text "POV: you pushed your .env to GitHub". Open on the line "Claude. I just got a bill for two thousand dollars."
- Add a low music bed or a trending sound (trending sounds have to be added in the Instagram app; the API can't attach library audio).
- Tests: changing the opening line + adding audio, on a topic that's universal (leaked keys).

### T4 — Ep 1 rewritten opening line (re-render on the PC)
- Replace "My senior told…" with a first line that is the whole conflict: **"Claude wrote all my code. Is this even my project?"** — big text, close-up on Cleo.
- Cut to ≤40s.
- Tests: whether the emotional/identity topic (best saves+shares per viewer after Ep 3) can get reach with a real hook.

### T5 — New video type: Claude solo, talking to camera (new render on the PC)
- The orange mascot alone, facing camera: "Things I said right before breaking your code" — 4–5 one-liners, 15–20s. No Cleo, no desk setup.
- Tests: a character-led meme format that's cheap to make in bulk and doesn't need series context.

### T6 — Ep 6 two ways (not posted yet)
- Post the 54s cut as a trial vs a 20s cut that opens on the bad trumpet ("I spent three hours making this." → trumpet). The quieter, emotional tone is a different flavor; trial first instead of main feed.

## Also worth doing
- Add `reels_skip_rate` to `fetch.py`. The API returns it, and it's the one number that judges a hook.
- Write each trial's parent permalink + what changed into a log, so results can be compared later.
