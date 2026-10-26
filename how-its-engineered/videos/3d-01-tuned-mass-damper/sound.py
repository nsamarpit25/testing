"""Synthesised sound bed (numpy only, no samples): storm, wind, thunder, whooshes, ruler twang, office creaks, the reveal
boom, hydraulic hiss, a tick for the one-metre mark and a low music pad; then mixed under audio/voice.wav with ducking.
python3 sound.py  -> audio/mix.wav (48 kHz stereo)"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 40.4
N = int(SR * DUR)
rng = np.random.default_rng(11)
t_all = np.arange(N) / SR


def band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo:
        m *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi:
        m *= 1 / np.sqrt(1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def env_curve(points):
    """piecewise-linear gain over the whole timeline: [(t, g), ...]"""
    ts, gs = zip(*points)
    return np.interp(t_all, ts, gs)


def T(d):
    return np.arange(int(SR * d)) / SR


def add(buf, x, at, g=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += g * x[:n]


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


def whoosh(d=0.45, lo=300, hi=3200):
    t = T(d)
    n = rng.standard_normal(len(t))
    y = np.zeros_like(t)
    blk = 960
    f = lo + (hi - lo) * np.sin(np.pi * t / d) ** 2
    for i in range(0, len(t), blk):
        seg = n[max(0, i - 4000):i + blk]
        y[i:i + blk] = band(seg, f[i] * 0.5, f[i] * 1.8)[-len(n[i:i + blk]):]
    return norm(y * np.sin(np.pi * t / d) ** 2)


def thunder(d=3.0, crack=True):
    t = T(d)
    rum = band(rng.standard_normal(len(t)), 25, 180) * np.exp(-t / 0.9) * (1 + 0.6 * np.sin(2 * np.pi * 3.3 * t))
    y = norm(rum)
    if crack:
        y += 1.4 * norm(band(rng.standard_normal(len(t)), 1500, 9000)) * np.exp(-t / 0.035)
        y += 0.8 * norm(band(rng.standard_normal(len(t)), 400, 3000)) * np.exp(-t / 0.18)
    return norm(y)


def boom(d=2.6):
    t = T(d)
    sub = np.sin(2 * np.pi * (34 + 60 * np.exp(-t / 0.08)) * t) * np.exp(-t / 0.9)
    clang = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / dd) for f, dd in ((311, 0.7), (467, 0.5), (622, 0.35), (933, 0.22)))
    hit = band(rng.standard_normal(len(t)), 200, 4000) * np.exp(-t / 0.03)
    return norm(sub + 0.18 * clang + 0.5 * hit)


def twang(d=1.9):
    t = T(d)
    f0 = 150 + 90 * (1 - np.exp(-t / 0.5))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    am = 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 3.2 * t))
    buzz = np.sign(np.sin(ph)) * 0.6 + np.sin(2 * ph) * 0.4
    knock = band(rng.standard_normal(len(t)), 150, 2500) * np.exp(-t / 0.02)
    slap = band(rng.standard_normal(len(t)), 800, 6000) * np.exp(-t / 0.012)
    return norm(band(buzz, 120, 3500) * am * np.exp(-t / 0.7) + 0.7 * knock + 0.9 * slap)


def creak(d=0.9):
    t = T(d)
    f = 90 + 60 * np.sin(np.pi * t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    pulses = (np.sin(ph) > 0.92).astype(float)
    return norm(band(pulses, 200, 2400) * np.sin(np.pi * t / d))


def hiss(d=3.3):
    t = T(d)
    n = band(rng.standard_normal(len(t)), 1200, 6000)
    pump = 0.55 + 0.45 * np.sin(2 * np.pi * t / 2.1 * 2) ** 2
    thump = band(rng.standard_normal(len(t)), 40, 200) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 2.1 * 2))
    return norm(n * pump * np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.3) + 0.5 * thump)


def tick():
    t = T(0.6)
    return norm(np.sin(2 * np.pi * 1760 * t) * np.exp(-t / 0.12) + 0.4 * np.sin(2 * np.pi * 2637 * t) * np.exp(-t / 0.08))


def music():
    """D minor drone pad with a slow pulse; lifts at the reveal, resolves warm at the end."""
    t = t_all
    y = np.zeros(N)
    chords = [(0.0, (73.42, 110.0, 146.83, 174.61)), (13.4, (58.27, 116.54, 146.83, 174.61)),
              (17.15, (73.42, 110.0, 146.83, 220.0)), (27.5, (65.41, 130.81, 164.81, 196.0)),
              (33.0, (58.27, 116.54, 174.61, 233.08)), (37.5, (73.42, 146.83, 185.0, 220.0))]
    for k, (t0, fs) in enumerate(chords):
        t1 = chords[k + 1][0] if k + 1 < len(chords) else DUR
        g = np.clip((t - t0 + 0.4) / 0.8, 0, 1) * np.clip((t1 + 0.4 - t) / 0.8, 0, 1)
        for i, f in enumerate(fs):
            y += g * (np.sin(2 * np.pi * f * t + i) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t)) / (1 + i * 0.4)
    y = band(y, 40, 1400)
    pulse = 0.75 + 0.25 * np.cos(2 * np.pi * t / (60 / 92)) ** 8
    lvl = env_curve([(0, 0.35), (7.5, 0.5), (17.0, 0.55), (17.2, 0.95), (27.5, 0.8), (33, 0.8), (37.5, 1.0), (DUR, 0.7)])
    kick = np.zeros(N)
    beat = 60 / 92
    kt = T(0.35)
    k1 = np.sin(2 * np.pi * (48 + 90 * np.exp(-kt / 0.03)) * kt) * np.exp(-kt / 0.12)
    for b in np.arange(17.18, 37.4, beat * 2):
        add(kick, k1, b)
    return norm(y) * pulse * lvl + 0.55 * kick


# shot spans of each set -> storm level and muffling
CITY = [(0, 5.95), (7.5, 9.45), (13.4, 16.2), (21.75, 27.5), (30.8, 33.0), (37.5, DUR)]
INSIDE = [(5.95, 7.5), (16.2, 21.75), (27.5, 30.8), (33.0, 35.35)]
OFFICE = [(11.3, 13.4), (35.35, 37.5)]


def spans_gain(spans, fade=0.04):
    g = np.zeros(N)
    for a, b in spans:
        g = np.maximum(g, np.clip((t_all - a) / fade, 0, 1) * np.clip((b - t_all) / fade, 0, 1))
    return g


def build():
    fx = np.zeros(N)
    rain = band(rng.standard_normal(N), 500, 4500)
    rain_m = band(rng.standard_normal(N), 120, 900)
    wmod = 0.6 + 0.4 * np.sin(2 * np.pi * t_all / 3.1) * np.sin(2 * np.pi * t_all / 1.7)
    wind = band(rng.standard_normal(N), 180, 900) * wmod
    howl = np.sin(2 * np.pi * np.cumsum(420 + 140 * np.sin(2 * np.pi * t_all / 2.3)) / SR) * 0.3 * wmod
    gc, gi, go = spans_gain(CITY), spans_gain(INSIDE), spans_gain(OFFICE)
    storm_lvl = env_curve([(0, 1), (21.0, 1), (21.75, 0.45), (23.75, 0.55), (24.0, 1.1), (25.4, 0.6), (30.8, 0.9),
                           (37.5, 0.5), (DUR, 0.25)])
    fx += norm(rain) * 0.05 * gc * storm_lvl + norm(rain_m) * 0.04 * (gi + go)
    fx += (norm(wind) * 0.14 + norm(howl) * 0.05) * gc * storm_lvl + norm(band(rng.standard_normal(N), 80, 400)) * 0.03 * (gi + go)
    for tf, a in ((1.75, 1.0), (5.86, 0.7), (16.12, 0.45), (30.8, 0.8)):
        add(fx, thunder(), tf, 0.75 * a)
    add(fx, thunder(4.0, False), 0.0, 0.35)
    for tw, g in ((2.5, 0.35), (3.78, 0.3), (5.5, 0.45), (11.12, 0.5), (19.32, 0.45), (21.57, 0.45), (32.82, 0.45),
                  (35.17, 0.45), (7.18, 0.55), (16.1, 0.3), (27.45, 0.3)):
        add(fx, whoosh(0.42), tw, g)
    add(fx, whoosh(0.9, 120, 900), 6.3, 0.35)        # the ball swinging past in the dark
    for tc in (11.4, 12.55):
        add(fx, creak(), tc, 0.22)
    add(fx, creak(1.4), 16.3, 0.2)
    add(fx, boom(), 17.16, 0.85)
    for g, tg in enumerate((17.33, 17.48)):
        add(fx, boom(1.2) * 0.5, tg, 0.35)
    add(fx, hiss(), 27.5, 0.6)
    add(fx, boom(1.0), 27.55, 0.3)
    add(fx, tick(), 35.02, 0.35)
    add(fx, whoosh(1.6, 150, 1200), 37.6, 0.25)
    mus = music()
    return fx, mus


def read_wav(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    if w.getnchannels() == 2:
        x = x.reshape(-1, 2).mean(1)
    assert w.getframerate() == SR, w.getframerate()
    return x


def main():
    fx, mus = build()
    spot = np.zeros(N)
    add(spot, twang(), 9.47, 0.6)
    v = read_wav(os.path.join(HERE, "audio/voice.wav"))
    voice = np.zeros(N)
    voice[:min(N, len(v))] = v[:N]
    # ducking: follow the voice envelope
    e = np.abs(voice)
    k = int(SR * 0.08)
    e = np.convolve(e, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(e / (e.max() * 0.25 + 1e-9), 0, 1)
    bed = (fx * 0.9 + mus * 0.16) * duck + spot
    L = voice + bed * 1.0
    # slight stereo: the bed decorrelated by a few ms
    d = int(SR * 0.006)
    R = voice + np.concatenate([np.zeros(d), bed[:-d]])
    st = np.stack([L, R], 1)
    st *= 0.89 / np.abs(st).max()
    fade = np.clip((DUR - t_all) / 0.6, 0, 1)
    st *= fade[:, None]
    out = os.path.join(HERE, "audio/mix.wav")
    w = wave.open(out, "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
    w.close()
    print("wrote", out)


if __name__ == "__main__":
    main()
