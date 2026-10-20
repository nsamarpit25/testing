# Small synthesized UI sound set for the Remotion reels (no samples, no licences): ticks, taps, whooshes, chimes, an error buzz.
# usage: .venv/bin/python tools/sfx.py <outdir>
import sys, wave
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)
T = lambda d: np.arange(int(SR * d)) / SR
env = lambda t, a, d: np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
bp = lambda x, lo, hi: sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)
lp = lambda x, f: sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)

def room(x, mix=0.18):  # a touch of space: a few soft early reflections
    y = x.copy()
    for ms, g in ((23, 0.5), (41, 0.35), (67, 0.22), (97, 0.12)):
        n = int(SR * ms / 1000); y[n:] += g * mix * 4 * x[:-n] if n < len(x) else 0
    return y
def save(name, x, peak=0.5):
    x = np.concatenate([x, np.zeros(int(SR * 0.12))]); x = room(x)
    x = x / (np.abs(x).max() + 1e-9) * peak
    w = wave.open(str(out / f'{name}.wav'), 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype(np.int16).tobytes()); w.close()

t = T(0.05); save('tick', bp(rng.standard_normal(len(t)), 2500, 7000) * env(t, 0.0005, 0.006) + 0.4 * np.sin(2 * np.pi * 3200 * t) * env(t, 0.0005, 0.01), 0.35)
t = T(0.12); save('tap', np.sin(2 * np.pi * (180 + 900 * np.exp(-t / 0.01)) * t) * env(t, 0.001, 0.03) + 0.3 * bp(rng.standard_normal(len(t)), 1500, 5000) * env(t, 0.0005, 0.008), 0.45)
t = T(0.55); f = 300 + 2600 * np.sin(np.pi * t / 0.55) ** 2
n = rng.standard_normal(len(t)); y = np.zeros_like(t)
for i in range(0, len(t), 480):  # time-varying band-pass, blockwise
    c = f[i]; y[i:i + 480] = bp(n[max(0, i - 2000):i + 480], c * 0.6, min(c * 1.6, 20000))[-len(n[i:i + 480]):]
save('whoosh', y * np.sin(np.pi * t / 0.55) ** 2, 0.3)
def chime(fs, gap=0.085, d=0.5):
    t = T(d + gap * len(fs)); y = np.zeros_like(t)
    for k, f0 in enumerate(fs):
        s = int(SR * gap * k); tt = t[: len(t) - s]
        y[s:] += (np.sin(2 * np.pi * f0 * tt) + 0.25 * np.sin(2 * np.pi * 2 * f0 * tt)) * env(tt, 0.003, 0.16)
    return y
save('ok', chime([880, 1318.5]), 0.4)
save('ok3', chime([659.3, 880, 1318.5], 0.07), 0.42)
t = T(0.32); sq = np.sign(np.sin(2 * np.pi * 146.8 * t)) + 0.6 * np.sign(np.sin(2 * np.pi * 155.6 * t))
save('err', lp(sq, 900) * (env(t, 0.004, 0.06) + 0.8 * env(np.maximum(0, t - 0.13), 0.004, 0.07) * (t > 0.13)), 0.38)
t = T(0.16); save('pop', np.sin(2 * np.pi * (260 + 520 * np.exp(-t / 0.025)) * t) * env(t, 0.002, 0.045), 0.42)
t = T(0.4); save('lock', bp(rng.standard_normal(len(t)), 2000, 6000) * (env(t, 0.0005, 0.005) + 0.7 * env(np.maximum(0, t - 0.07), 0.0005, 0.006) * (t > 0.07)) + 0.5 * np.sin(2 * np.pi * 420 * t) * env(np.maximum(0, t - 0.07), 0.001, 0.05) * (t > 0.07), 0.4)
for k in range(4):
    t = T(0.04); save(f'key{k}', bp(rng.standard_normal(len(t)), 1800 + 500 * k, 6500) * env(t, 0.0004, 0.004 + 0.001 * k), 0.22)
t = T(1.2); save('rise', bp(rng.standard_normal(len(t)), 600, 4000) * (t / 1.2) ** 2 * (1 - (t > 1.15)) + 0.15 * np.sin(2 * np.pi * (200 + 400 * t / 1.2) * t) * (t / 1.2) ** 2, 0.22)
print('sfx ->', out, sorted(p.name for p in out.glob('*.wav')))
