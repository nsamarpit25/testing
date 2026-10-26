"""Synthesised sound bed (numpy only, no samples): canyon wind and the river, the heat rumble and crackle of curing
concrete, the monolith creaking and cracking, columns thudding up lift by lift, an x-ray scan, water running through
the coils, the ice-cold chime, concrete shrinking, grout pouring, cut whooshes, sub hits and a pulse score; mixed under
audio/voice.wav with ducking. python3 sound.py  -> audio/mix.wav (48 kHz stereo)"""
import os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 35.1
N = int(SR * DUR)
rng = np.random.default_rng(31)
t_all = np.arange(N) / SR
CUTS = [2.3, 4.2, 6.25, 8.2, 11.25, 13.2, 15.9, 18.55, 20.0, 22.65, 25.6, 27.95, 29.5, 32.4]


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
    if i < 0:
        x, i = x[-i:], 0
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += g * x[:n]


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


def spans_gain(spans, fade=0.03):
    g = np.zeros(N)
    for a, b in spans:
        g = np.maximum(g, np.clip((t_all - a) / fade, 0, 1) * np.clip((b - t_all) / fade, 0, 1))
    return g


def sweep_noise(d, f_lo, f_hi, q=1.8):
    """noise through a band that glides from f_lo to f_hi (block-wise)"""
    t = T(d)
    n = rng.standard_normal(len(t))
    y = np.zeros_like(t)
    blk = 960
    f = f_lo * (f_hi / f_lo) ** (t / d)
    for i in range(0, len(t), blk):
        seg = n[max(0, i - 4000):i + blk]
        y[i:i + blk] = band(seg, f[i] / q, f[i] * q)[-len(n[i:i + blk]):]
    return norm(y)


def whoosh(d=0.4, lo=250, hi=3000):
    t = T(d)
    n = rng.standard_normal(len(t))
    y = np.zeros_like(t)
    blk = 960
    f = lo + (hi - lo) * np.sin(np.pi * t / d) ** 2
    for i in range(0, len(t), blk):
        seg = n[max(0, i - 4000):i + blk]
        y[i:i + blk] = band(seg, f[i] * 0.5, f[i] * 1.8)[-len(n[i:i + blk]):]
    return norm(y * np.sin(np.pi * t / d) ** 2)


def sub_hit(d=2.4, f0=38):
    t = T(d)
    sub = np.sin(2 * np.pi * (f0 + 70 * np.exp(-t / 0.06)) * t) * np.exp(-t / 0.8)
    body = band(rng.standard_normal(len(t)), 60, 900) * np.exp(-t / 0.12)
    snap = band(rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t / 0.015)
    return norm(sub + 0.45 * body + 0.35 * snap)


def hydraulic(d=0.6):
    """pressure build: rising hiss and whine before the launch"""
    t = T(d)
    hs = band(rng.standard_normal(len(t)), 2000, 8000) * (t / d) ** 2
    whine = np.sin(2 * np.pi * np.cumsum(300 + 900 * (t / d) ** 2) / SR) * (t / d) ** 1.5
    return norm(hs + 0.35 * whine)


def clack(f=1.0):
    t = T(0.12)
    return norm(band(rng.standard_normal(len(t)), 300 * f, 4000 * f) * np.exp(-t / 0.018)
                + 0.6 * np.sin(2 * np.pi * 180 * f * t) * np.exp(-t / 0.03))


def ping(f=2100, d=1.4):
    t = T(d)
    return norm(sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t / (0.5 / r)) / r for r in (1, 2.76, 5.4)))


def screech(d=2.0):
    """pad on plate: a scraping squeal with crackle"""
    t = T(d)
    f = 1900 + 300 * np.sin(2 * np.pi * 1.3 * t) + 120 * np.sin(2 * np.pi * 7.1 * t)
    sq = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * t))
    scrape = band(rng.standard_normal(len(t)), 900, 6000)
    crackle = (rng.random(len(t)) > 0.9985).astype(float)
    crackle = band(np.convolve(crackle, np.exp(-T(0.004) / 0.0008), "same"), 2000, 12000)
    e = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.3)
    return norm((0.35 * sq + 0.5 * norm(scrape) + 0.8 * norm(crackle)) * e)


def vrrr(d=1.3, f0=95, f1=40):
    """magnetic brake: a growling buzz that drops in pitch as the train slows"""
    t = T(d)
    f = f0 * (f1 / f0) ** (t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    buzz = np.tanh(2.5 * (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)))
    gr = band(rng.standard_normal(len(t)), 80, 900) * (0.5 + 0.5 * np.sin(ph * 0.5))
    e = np.minimum(1, t / 0.12) * np.minimum(1, (d - t) / 0.35)
    return norm(band(buzz, 30, 2500) * e + 0.3 * norm(gr) * e)


def powerup(f=220, d=0.9):
    t = T(d)
    ff = f * (1 + 0.5 * np.minimum(1, t / 0.25))
    ph = 2 * np.pi * np.cumsum(ff) / SR
    return norm((np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.minimum(1, t / 0.03) * np.exp(-t / 0.35))


def sizzle(d):
    t = T(d)
    n = band(rng.standard_normal(len(t)), 3000, 11000) * (0.6 + 0.4 * rng.random(len(t)))
    return norm(n * np.minimum(1, t / 0.2) * np.minimum(1, (d - t) / 0.2))


def riser(d=1.6, lo=200, hi=3500):
    t = T(d)
    return norm(sweep_noise(d, lo, hi) * (t / d) ** 2 + 0.3 * np.sin(2 * np.pi * np.cumsum(80 + 300 * (t / d) ** 2) / SR)
                * (t / d) ** 2)


def tone(f, d, decay=0.6, harm=(1, 2.01, 3.03), amp=(1, 0.35, 0.15)):
    t = T(d)
    return norm(sum(a * np.sin(2 * np.pi * f * h * t) for h, a in zip(harm, amp)) * np.exp(-t / decay)
                * np.minimum(1, t / 0.004))


def chime(f=1760, d=1.6):
    """glassy crystal shimmer: inharmonic partials, slow decay"""
    t = T(d)
    return norm(sum(np.sin(2 * np.pi * f * r * t + r) * np.exp(-t / (0.9 / r ** 0.5)) / r
                    for r in (1, 2.32, 4.25, 6.63)) * np.minimum(1, t / 0.002))


def crack(d=0.9):
    """sharp fracture: a snap, a splintering burst and a ringing metallic tail"""
    t = T(d)
    snap = band(rng.standard_normal(len(t)), 1200, 14000) * np.exp(-t / 0.01)
    spl = (rng.random(len(t)) > 0.996).astype(float) * np.exp(-t / 0.12)
    spl = band(np.convolve(spl, np.exp(-T(0.003) / 0.0006), "same"), 1500, 10000)
    ring = sum(np.sin(2 * np.pi * f * t) for f in (1180, 2710, 4130)) * np.exp(-t / 0.25)
    low = np.sin(2 * np.pi * (60 + 80 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.18)
    return norm(norm(snap) + 0.6 * norm(spl) + 0.18 * norm(ring) + 0.6 * low)


def creak(d=1.0):
    t = T(d)
    f = 140 + 60 * t / d
    ph = 2 * np.pi * np.cumsum(f) / SR
    g = np.tanh(3 * np.sin(ph)) * (0.5 + 0.5 * (rng.random(len(t)) > 0.7))
    return norm(band(g, 200, 3000) * np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.1))


def slide(d=1.1):
    """metal sliding out of a tight slot: a filtered scrape that rises, then a release ping"""
    t = T(d)
    s = band(rng.standard_normal(len(t)), 600, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t))
    return norm(s * np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.25))


def build():
    fx = np.zeros(N)
    ext = spans_gain([(0, 4.2), (27.95, DUR)], 0.05)
    therm = spans_gain([(4.6, 11.25), (22.65, 26.0)], 0.08)
    site = spans_gain([(11.25, 22.65)], 0.05)
    # the canyon: wind over the rim and the river at the foot of the dam
    fx += norm(band(rng.standard_normal(N), 150, 2200)) * 0.10 * ext
    fx += norm(band(rng.standard_normal(N), 40, 400)) * 0.16 * ext
    # building site air under the construction shots
    fx += norm(band(rng.standard_normal(N), 100, 1500)) * 0.05 * site
    # curing heat: deep rumble and a sparse crackle, swelling as the block heats
    crk = (rng.random(N) > 0.9993).astype(float)
    crk = band(np.convolve(crk, np.exp(-T(0.004) / 0.0008), "same"), 1500, 12000)
    heat = env_curve([(0, 0), (4.6, 0), (5.4, 0.5), (8.2, 1.0), (11.25, 1.0), (22.65, 1.0), (25.3, 0.4), (26.0, 0),
                      (DUR, 0)])
    fx += (norm(band(rng.standard_normal(N), 25, 160)) * 0.28 + norm(crk) * 0.10) * therm * heat
    add(fx, sub_hit(2.4, 34), 0.0, 0.7)                  # open on the hook
    for tc in CUTS:
        add(fx, whoosh(0.34), tc - 0.19, 0.18)
    add(fx, sub_hit(1.8, 38), 4.2, 0.45)                # one pour
    add(fx, powerup(110, 1.0), 4.6, 0.2)                # thermal view on
    add(fx, riser(1.8, 120, 1800), 6.4, 0.12)           # heat builds
    add(fx, sizzle(1.6) * 0.6, 8.4, 0.06)
    add(fx, creak(1.2), 9.6, 0.2)                       # skin pulls against the core
    add(fx, crack(1.0), 10.5, 0.6)
    add(fx, crack(0.7), 10.85, 0.35)
    for i in range(9):                                  # columns thud up lift by lift
        add(fx, clack(0.35), 11.35 + 0.13 * i, 0.22 - 0.012 * i)
    add(fx, sub_hit(1.2, 44), 11.25, 0.3)
    add(fx, sweep_noise(1.0, 3000, 300) * np.hanning(int(SR * 1.0)), 13.25, 0.12)   # x-ray scan
    add(fx, tone(880, 1.2, 0.4, (1, 1.5, 2)), 13.25, 0.05)
    add(fx, whoosh(1.6, 120, 900), 15.9, 0.22)          # pull back over the miles of pipe
    # water through the coils: a steady rush with a bubbling edge, colder and brighter on the ice water
    flow = band(rng.standard_normal(N), 250, 3500) * (0.7 + 0.3 * np.sin(2 * np.pi * 6.3 * t_all))
    fx += norm(flow) * 0.10 * env_curve([(0, 0), (18.6, 0), (19.2, 0.9), (22.4, 1.0), (22.65, 0), (DUR, 0)])
    add(fx, whoosh(0.8, 200, 2000), 18.6, 0.2)
    add(fx, chime(1976, 2.0), 20.1, 0.10)               # ice water
    add(fx, chime(2637, 1.6), 20.2, 0.06)
    fx += norm(band(rng.standard_normal(N), 4000, 12000)) * 0.035 * spans_gain([(20.1, 22.65)], 0.3)
    add(fx, vrrr(1.6, 90, 45) * 0.5, 23.7, 0.12)        # concrete shrinking apart
    add(fx, creak(1.0), 24.2, 0.14)
    add(fx, sub_hit(1.2, 48), 22.65, 0.25)
    # grout: a thick low pour rising in the joints
    pour = band(rng.standard_normal(N), 60, 700) * (0.7 + 0.3 * np.sin(2 * np.pi * 3.1 * t_all))
    fx += norm(pour) * 0.12 * env_curve([(0, 0), (25.9, 0), (26.3, 1), (27.7, 1), (27.95, 0), (DUR, 0)])
    add(fx, sub_hit(2.6, 34), 27.95, 0.65)              # one solid dam
    add(fx, whoosh(1.2, 100, 1000), 27.8, 0.3)
    add(fx, tone(1318, 2.0, 0.8), 29.55, 0.06)          # under two years
    add(fx, riser(1.6, 150, 2600), 30.8, 0.1)
    add(fx, sub_hit(3.0, 32), 32.4, 0.5)                # rise away
    return fx, music()


def music():
    """D minor pulse: warm pad, 16th-note pluck from the first cut, kick on the big sections, resolves at the end."""
    t = t_all
    bpm = 104
    beat = 60 / bpm
    y = np.zeros(N)
    chords = [(0.0, (73.42, 146.83, 174.61, 220.0)), (4.2, (58.27, 116.54, 174.61, 233.08)),
              (8.2, (65.41, 130.81, 155.56, 196.0)), (11.25, (87.31, 130.81, 174.61, 220.0)),
              (15.9, (73.42, 146.83, 174.61, 220.0)), (22.65, (58.27, 116.54, 174.61, 233.08)),
              (25.6, (65.41, 130.81, 164.81, 196.0)), (27.95, (73.42, 146.83, 185.0, 220.0))]
    pl = np.zeros(N)
    for k, (t0, fs) in enumerate(chords):
        t1 = chords[k + 1][0] if k + 1 < len(chords) else DUR
        g = np.clip((t - t0 + 0.2) / 0.4, 0, 1) * np.clip((t1 + 0.2 - t) / 0.4, 0, 1)
        for i, f in enumerate(fs):
            y += g * (np.sin(2 * np.pi * f * t + i) + 0.25 * np.sin(2 * np.pi * f * 2.004 * t)) / (1 + i * 0.4)
        st = beat / 4
        nt = T(st * 1.5)
        for j, b in enumerate(np.arange(t0, t1, st)):
            f = fs[[1, 2, 3, 2][j % 4]] * 2
            ph = 2 * np.pi * f * nt
            saw = sum(np.sin(h * ph) / h for h in range(1, 7))
            add(pl, saw * np.exp(-nt / 0.07), b, 1.0 if j % 4 == 0 else 0.6)
    y = band(y, 40, 1500)
    pl = band(pl, 200, 2600)
    lvl = env_curve([(0, 0.5), (4.2, 0.6), (8.2, 0.5), (11.25, 0.6), (15.9, 0.75), (25.6, 0.85), (27.95, 1.0),
                     (DUR - 0.8, 0.9), (DUR, 0)])
    pll = env_curve([(0, 0), (2.25, 0), (2.3, 0.6), (8.15, 0.6), (8.2, 0.3), (11.25, 0.5), (15.9, 0.85),
                     (25.55, 0.9), (25.6, 0.4), (27.95, 0.9), (DUR - 0.6, 0.5), (DUR, 0)])
    kick = np.zeros(N)
    kt = T(0.35)
    k1 = np.sin(2 * np.pi * (46 + 100 * np.exp(-kt / 0.025)) * kt) * np.exp(-kt / 0.13)
    for a, b in ((2.3, 8.2), (15.9, 25.6), (27.95, 33.6)):
        for bt in np.arange(a, b, beat):
            add(kick, k1, bt)
    return norm(y) * lvl * 0.8 + norm(pl) * pll * 0.45 + 0.5 * kick


def read_wav(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    if w.getnchannels() == 2:
        x = x.reshape(-1, 2).mean(1)
    assert w.getframerate() == SR, w.getframerate()
    return x


def main():
    fx, mus = build()
    v = read_wav(os.path.join(HERE, "audio/voice.wav"))
    voice = np.zeros(N)
    voice[:min(N, len(v))] = v[:N]
    e = np.abs(voice)
    k = int(SR * 0.08)
    e = np.convolve(e, np.ones(k) / k, mode="same")
    duck = 1 - 0.5 * np.clip(e / (e.max() * 0.25 + 1e-9), 0, 1)
    bed = (fx * 0.8 + mus * 0.24) * duck
    d = int(SR * 0.007)
    L = voice + bed
    R = voice + np.concatenate([np.zeros(d), bed[:-d]])
    st = np.stack([L, R], 1)
    st *= 0.89 / np.abs(st).max()
    st *= np.clip((DUR - t_all) / 0.6, 0, 1)[:, None]
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
