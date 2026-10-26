#!/usr/bin/env python3
"""Mix a quiet synthesized music bed and soft whooshes under a rendered reel (no samples, no licences).

usage: "~/Developer/how its enginereed/.venv/bin/python" tools/remake/bin/bed.py <in.mp4> <out.mp4> [--seed N] [--cuts 5.4,7.3,...] [--db -22]
  The bed is a slow evolving pad (a minor chord picked by --seed, soft LFO, filtered air) that fades in over 0.4 s and
  sits --db under the voice; each cut gets a short filtered-noise whoosh. Video is copied, audio re-encoded.
"""
import argparse, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
p = argparse.ArgumentParser()
p.add_argument('src'); p.add_argument('out')
p.add_argument('--seed', type=int, default=1); p.add_argument('--cuts', default=''); p.add_argument('--db', type=float, default=-22)
a = p.parse_args()

voice = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', a.src, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                                     capture_output=True, check=True).stdout, dtype=np.float32).reshape(-1, 2).astype(np.float64)
n = len(voice); t = np.arange(n) / SR; rng = np.random.default_rng(a.seed)
lp = lambda x, f: sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
bp = lambda x, lo, hi: sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)

# pad: root picked by seed, minor triad + 9th spread over two octaves, each voice slightly detuned left/right
root = [98.0, 110.0, 123.47, 130.81, 146.83][a.seed % 5]
notes = [root, root * 1.189, root * 1.498, root * 2, root * 2.245]
pad = np.zeros((n, 2))
for k, f in enumerate(notes):
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.05 + 0.03 * k) * t + rng.uniform(0, 6))
    for ch, d in enumerate((-0.6, 0.6)):
        pad[:, ch] += lfo * np.sin(2 * np.pi * (f + d) * t + rng.uniform(0, 6)) / (1 + k * 0.6)
air = lp(rng.standard_normal(n), 900) * 0.25
pad += air[:, None]
pad = np.stack([lp(pad[:, 0], 1800), lp(pad[:, 1], 1800)], 1)
pad *= np.minimum(1, t / 0.4)[:, None] * np.minimum(1, (t[-1] - t) / 1.2)[:, None]

# whooshes on the cuts
for c in [float(x) for x in a.cuts.split(',') if x]:
    i0, L = int((c - 0.28) * SR), int(0.5 * SR)
    if i0 < 0 or i0 + L > n: continue
    tt = np.arange(L) / SR; env = np.sin(np.pi * tt / 0.5) ** 2
    w = bp(rng.standard_normal(L), 600, 5000) * env * 0.5
    pad[i0:i0 + L, 0] += w * (1 - tt / 0.5); pad[i0:i0 + L, 1] += w * (tt / 0.5)

rms = lambda x: np.sqrt(np.mean(x ** 2)) + 1e-12
v_rms = rms(voice[np.abs(voice).max(1) > 0.02]) if (np.abs(voice).max(1) > 0.02).any() else rms(voice)
pad *= v_rms * 10 ** (a.db / 20) / rms(pad)
mix = voice + pad
mix /= max(1.0, np.abs(mix).max() / 0.97)
r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.src, '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', a.out],
                   input=mix.astype(np.float32).tobytes())
sys.exit(r.returncode)
