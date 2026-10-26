"""Synthesised sound bed (numpy only, no samples): thin Martian wind, the descent-stage engines (a far rumble, the
ground blast with rocks clattering, the steady sky-crane burn), the winch paying out, wheels clunking down, touchdown,
three pyro pops, the stage roaring away and a distant crash; a studio thud on the airbag; cut whooshes and a pulse score,
mixed under audio/voice.wav with ducking.  python3 sound.py  -> audio/mix.wav (48 kHz stereo)"""
import os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 32.2
N = int(SR * DUR)
rng = np.random.default_rng(66)
t_all = np.arange(N) / SR
CUTS = [2.1, 3.55, 4.95, 6.45, 8.5, 10.6, 12.5, 14.55, 16.97, 19.36, 20.92, 22.19, 24.2, 26.28, 29.27]


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


def passby(d=1.4, peak=0.6, f0=140):
    """a train rushing past: a broadband roar that swells to the pass and drops in pitch after it"""
    t = T(d)
    e = np.exp(-((t - peak) / (0.22 * d)) ** 2)
    roar = sweep_noise(d, 2600, 500, 1.6)
    f = f0 * np.where(t < peak, 1.12, 0.88)
    hum = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return norm((roar + 0.25 * hum) * e)


def chirp(f=3800, d=0.09):
    t = T(d)
    return norm(np.sin(2 * np.pi * np.cumsum(f * (1 + 0.35 * np.sin(np.pi * t / d))) / SR) * np.sin(np.pi * t / d) ** 2)


def plip(d=0.5):
    """the beak entering the water: one small clean drop, almost no splash"""
    t = T(d)
    f = 900 + 1700 * (1 - np.exp(-t / 0.03))
    bub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05)
    hs = band(rng.standard_normal(len(t)), 2500, 9000) * np.exp(-t / 0.02)
    return norm(bub + 0.25 * norm(hs))


def rocket(d, f_lo=35, f_hi=2200):
    """rocket roar: broadband rumble with crackle"""
    t = T(d)
    r = band(rng.standard_normal(len(t)), f_lo, f_hi)
    cr = (rng.random(len(t)) > 0.997).astype(float)
    cr = band(np.convolve(cr, np.exp(-T(0.004) / 0.001), "same"), 800, 7000)
    return norm(np.tanh(1.6 * norm(r)) + 0.35 * norm(cr))


def winch(d=1.5):
    """cable paying out: a geared whine sliding down with a light ratchet"""
    t = T(d)
    f = 520 - 160 * t / d
    ph = 2 * np.pi * np.cumsum(f) / SR
    wh = np.sin(ph) + 0.3 * np.sin(3 * ph)
    rat = band((np.sin(2 * np.pi * 34 * t) > 0.97).astype(float), 1500, 8000)
    e = np.minimum(1, t / 0.1) * np.minimum(1, (d - t) / 0.2)
    return norm((0.6 * wh + 0.5 * norm(rat)) * e)


def build():
    fx = np.zeros(N)
    mars = 1 - spans_gain([(4.95, 6.45)], 0.04)
    stu = spans_gain([(4.95, 6.45)], 0.04)
    # Mars: thin, high wind (the air is 1% of Earth's), a low moan under it
    gust = 0.7 + 0.3 * np.sin(2 * np.pi * 0.23 * t_all) * np.sin(2 * np.pi * 0.07 * t_all + 1)
    fx += norm(band(rng.standard_normal(N), 300, 3200)) * 0.05 * gust * mars
    fx += norm(band(rng.standard_normal(N), 30, 220)) * 0.08 * mars
    fx += norm(band(rng.standard_normal(N), 60, 500)) * 0.03 * stu
    for tc in CUTS:
        add(fx, whoosh(0.3), tc - 0.17, 0.12)
    # the engines: one long roar with a level curve over the story
    eng = rocket(DUR)
    lvl = env_curve([(0, 0.25), (2.1, 0.45), (4.9, 0.45), (4.95, 0), (6.45, 0), (6.5, 1.0), (10.55, 0.9),
                     (10.6, 0.35), (12.0, 0.35), (12.6, 0.22), (19.36, 0.2), (20.9, 0.25), (21.2, 0.25), (21.4, 0.9),
                     (22.6, 0.85), (24.2, 0.35), (24.6, 0.1), (24.75, 0), (DUR, 0)])
    fx += eng * 0.42 * lvl
    add(fx, sub_hit(2.2, 34), 6.45, 0.7)                 # ignition next to the ground
    add(fx, sweep_noise(2.5, 300, 3000) * np.hanning(int(SR * 2.5)), 6.6, 0.16)    # dust surging out
    for tr in rng.uniform(6.9, 10.2, 22):                # stones clattering
        add(fx, clack(rng.uniform(0.8, 1.8)), tr, rng.uniform(0.05, 0.14))
    add(fx, sweep_noise(1.0, 1600, 300) * np.exp(-T(1.0) / 0.4), 12.0, 0.10)       # four engines throttle down
    add(fx, winch(1.6), 14.6, 0.12)                      # the bridles pay out
    add(fx, clack(0.7), 17.5, 0.20)                      # wheels lock down
    add(fx, clack(0.6), 18.4, 0.22)
    add(fx, sub_hit(1.2, 52), 20.05, 0.35)               # touchdown
    add(fx, sweep_noise(0.9, 2000, 400) * np.exp(-T(0.9) / 0.3), 20.05, 0.10)
    for k in range(3):                                   # pyro cutters
        add(fx, crack(0.4), 21.15 + 0.035 * k, 0.32)
    add(fx, riser(1.2, 150, 1800), 21.2, 0.14)           # throttle up
    add(fx, sub_hit(3.0, 30), 24.75, 0.7)                # the crash, far off
    add(fx, crack(0.9), 24.75, 0.12)
    add(fx, sweep_noise(2.5, 900, 150) * np.exp(-T(2.5) / 0.9), 24.8, 0.14)
    add(fx, chime(1760, 1.6), 4.95, 0.06)                # into the studio
    add(fx, sub_hit(1.0, 60), 5.55, 0.45)                # rover lands on the airbag
    add(fx, creak(0.5), 5.6, 0.08)
    add(fx, powerup(300, 1.0), 26.5, 0.08)               # the mast stands up
    add(fx, tone(1318.5, 1.4, 0.5), 26.35, 0.05)
    add(fx, sub_hit(2.6, 32), 29.27, 0.35)               # crane up and away
    add(fx, riser(1.4, 150, 2400), 30.4, 0.06)
    return fx, music()


def music():
    """D minor pulse: tense under the descent, a lift at touchdown, open on the ending."""
    t = t_all
    bpm = 104
    beat = 60 / bpm
    y = np.zeros(N)
    chords = [(0.0, (73.42, 146.83, 174.61, 220.0)), (4.95, (58.27, 116.54, 174.61, 233.08)),
              (6.45, (65.41, 130.81, 196.0, 233.08)), (10.6, (73.42, 146.83, 174.61, 220.0)),
              (14.55, (58.27, 116.54, 174.61, 233.08)), (19.36, (87.31, 174.61, 220.0, 261.63)),
              (22.19, (65.41, 130.81, 196.0, 261.63)), (26.28, (58.27, 116.54, 174.61, 233.08)),
              (29.27, (73.42, 146.83, 220.0, 293.66))]
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
    lvl = env_curve([(0, 0.55), (4.95, 0.5), (6.45, 0.75), (10.6, 0.6), (19.36, 0.75), (21.1, 0.8), (24.6, 0.9),
                     (24.75, 0.3), (25.4, 0.7), (29.27, 1.0), (DUR - 0.8, 0.9), (DUR, 0)])
    pll = env_curve([(0, 0.3), (4.9, 0.4), (6.45, 0.7), (10.5, 0.7), (10.6, 0.35), (19.3, 0.45), (19.36, 0.7),
                     (24.6, 0.85), (24.75, 0.2), (26.28, 0.6), (29.27, 0.9), (DUR - 0.6, 0.5), (DUR, 0)])
    kick = np.zeros(N)
    kt = T(0.35)
    k1 = np.sin(2 * np.pi * (46 + 100 * np.exp(-kt / 0.025)) * kt) * np.exp(-kt / 0.13)
    for a, b in ((6.45, 10.55), (19.36, 24.7), (26.28, 32.0)):
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
