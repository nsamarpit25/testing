#!/usr/bin/env python3
"""Frame-accurate cut check for a finished reel (the Codex review samples only 2 frames/s).

    python3 scripts/cutcheck.py video.mp4 [outdir] [--min 0.6]

Finds every hard cut (ffmpeg scene score), flags shots shorter than --min seconds,
and writes outdir/cut_NN.jpg strips (10 fps, 0.3 s before to 0.3 s after each short shot)
for a human/Codex look. Also flags audio that stops dead at full volume.
Exit 1 if any short shot or hard audio stop is found, so it can gate a queue.
In-shot screen changes (a phone lighting up) also register as cuts; check the strips.
"""
import argparse, os, re, subprocess, sys

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("outdir", nargs="?"); ap.add_argument("--min", type=float, default=0.6)
a = ap.parse_args()
video, mn = a.video, a.min
out = a.outdir or os.path.splitext(video)[0] + "_cuts"
os.makedirs(out, exist_ok=True)

dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video]))
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-vf", "select='gt(scene,0.2)',showinfo", "-an", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
cuts = [0.0] + [float(t) for t in re.findall(r"pts_time:([0-9.]+)", log)] + [dur]
short = [(a, b) for a, b in zip(cuts, cuts[1:]) if b - a < mn and b < dur - 0.05]

print(f"{video}: {dur:.1f}s, {len(cuts) - 2} cuts, {len(short)} shot(s) under {mn}s")
for i, (a, b) in enumerate(short):
    s = max(0.0, a - 0.3)
    jpg = os.path.join(out, f"cut_{i:02d}.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.2f}", "-t", f"{b - s + 0.3:.2f}", "-i", video,
                    "-vf", "fps=10,scale=160:-1,tile=12x1", "-frames:v", "1", jpg], check=True)
    print(f"  {a:6.2f}-{b:6.2f}s  ({b - a:.2f}s)  {jpg}")
# Audio: sound still loud (> -25 dBFS) that drops to digital silence (< -65) within ~10 ms = a chopped word or clicky edit.
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
n = 80; db = 20 * np.log10(np.sqrt((x[: len(x) // n * n].reshape(-1, n) ** 2).mean(1)) + 1e-7)
chops = []
for i in range(2, len(db) - 2):
    t = i * n / 16000
    if db[i - 2] > -25 and db[i + 1] < -65 and t < dur - 1.0 and (not chops or t - chops[-1] > 0.2):
        chops.append(t)
print(f"  audio: {len(chops)} hard stop(s)" + "".join(f"\n  {t:6.2f}s  sound cut off at full volume (chopped word or SFX with no fade)" for t in chops))
sys.exit(1 if short or chops else 0)
