"""A/V check: lag of the final reel's audio against the episode's mix.wav, in 3 windows.  python3 sync.py final.mp4 mix.wav"""
import subprocess, sys
import numpy as np
def pcm(p):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.int16).astype(np.float32)
a, m = pcm(sys.argv[1]), pcm(sys.argv[2])
for t in (5, len(m) / 8000 / 2, len(m) / 8000 - 8):
    i = int(t * 8000); w = m[i:i + 8000 * 4]; best = None
    for lag in range(-800, 801, 4):
        s = a[i + lag:i + lag + len(w)]
        if len(s) == len(w):
            c = float(np.dot(s, w) / (np.linalg.norm(s) * np.linalg.norm(w) + 1e-9))
            if best is None or c > best[0]: best = (c, lag)
    print(f"at {t:5.1f}s: lag {best[1]/8000*1000:+.1f} ms  corr {best[0]:.3f}")
