"""Synthesised sound bed (numpy only, no samples): valley wind and birds, train pass-bys, the tunnel roar under the x-ray,\nthe squeeze racing to the exit, the two booms and the soft one, the river, a single plip for the dive, the studio,\npantograph sparks, cut whooshes, sub hits and a pulse score; mixed under audio/voice.wav with ducking.\npython3 sound.py  -> audio/mix.wav (48 kHz stereo)"""
import os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 33.2
N = int(SR * DUR)
rng = np.random.default_rng(53)
t_all = np.arange(N) / SR
CUTS = [1.8, 3.3, 4.62, 6.25, 7.85, 9.1, 10.3, 11.75, 12.42, 14.0, 16.0, 17.3, 19.05, 21.0, 22.1, 22.8, 25.1, 26.34, 28.0, 29.7]


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


def build():
    fx = np.zeros(N)
    out = spans_gain([(0, 4.62), (11.75, 12.42), (22.1, 22.8), (25.1, DUR)], 0.05)
    bore = spans_gain([(4.62, 11.75), (22.8, 25.1)], 0.06)
    riv = spans_gain([(12.42, 19.05)], 0.15)
    stu = spans_gain([(19.05, 22.1)], 0.1)
    # the valley: wind over the terraces, birds far off
    fx += norm(band(rng.standard_normal(N), 150, 2400)) * 0.08 * out
    fx += norm(band(rng.standard_normal(N), 40, 300)) * 0.10 * out
    for tb in (0.5, 1.1, 2.6, 26.6, 27.3, 30.2, 31.0, 31.8):
        add(fx, chirp(rng.uniform(3200, 4600)), tb, 0.04)
    # inside the tunnel: a deep roar that climbs as the squeeze builds toward the exit
    roar = norm(band(rng.standard_normal(N), 30, 700))
    fx += roar * 0.22 * bore * env_curve([(0, 0.5), (4.62, 0.6), (7.85, 0.8), (10.3, 1.0), (11.75, 1.0),
                                          (22.8, 0.45), (25.1, 0.45), (DUR, 0.45)])
    # the river: lapping water, close birds
    lap = band(rng.standard_normal(N), 180, 2200) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.7 * t_all))
    fx += norm(lap) * 0.10 * riv
    for tb in (12.7, 13.4, 13.55, 14.6, 15.8, 16.5):
        add(fx, chirp(rng.uniform(3600, 5200), 0.07), tb, 0.06)
    # the studio: a quiet room tone
    fx += norm(band(rng.standard_normal(N), 60, 500)) * 0.04 * stu
    for tc in CUTS:
        add(fx, whoosh(0.3), tc - 0.17, 0.14)
    add(fx, passby(1.6, 0.75), 1.8, 0.45)               # train A blasts past
    add(fx, sub_hit(1.6, 40), 4.0, 0.45)                # the first boom, heard from the houses
    add(fx, powerup(140, 1.0), 4.62, 0.16)              # x-ray on
    add(fx, riser(1.6, 120, 1500), 6.25, 0.10)          # air piling up on the face
    add(fx, sweep_noise(1.2, 400, 4000) * np.hanning(int(SR * 1.2)), 7.85, 0.14)   # the front breaks away
    add(fx, riser(1.9, 200, 4200), 9.9, 0.20)           # racing for the exit
    add(fx, sub_hit(3.0, 30), 11.93, 1.0)               # BOOM
    add(fx, crack(0.8), 11.93, 0.35)
    add(fx, sweep_noise(1.5, 3000, 300) * np.exp(-T(1.5) / 0.4), 11.95, 0.18)
    add(fx, whoosh(0.9, 300, 2600), 15.85, 0.16)        # the dive
    add(fx, plip(0.6), 17.55, 0.22)                     # barely a splash
    add(fx, chime(2349, 1.8), 19.1, 0.06)               # into the studio
    add(fx, sweep_noise(1.4, 300, 2400) * np.hanning(int(SR * 1.4)), 19.55, 0.10)   # beak grows into the nose
    add(fx, tone(1568, 1.6, 0.6), 21.1, 0.06)           # fifteen metres
    add(fx, passby(0.9, 0.45, 160), 22.0, 0.40)         # the 500 Series rockets past
    add(fx, powerup(140, 1.0), 22.8, 0.12)
    add(fx, sub_hit(1.4, 46), 25.35, 0.10)              # the boom fades: only a soft thump
    add(fx, passby(1.6, 0.4, 170), 26.3, 0.30)          # out into the light
    sp = np.zeros(N)                                    # pantograph sparks
    for ts_ in np.arange(28.05, 29.6, 2 * np.pi / 41.0):
        add(sp, crack(0.15), ts_, 0.5)
    fx += band(sp, 2500, 12000) * 0.25
    fx += norm(band(rng.standard_normal(N), 4000, 11000)) * 0.03 * spans_gain([(28.0, 29.7)], 0.1)
    add(fx, riser(1.5, 150, 2600), 30.9, 0.08)
    add(fx, sub_hit(2.6, 32), 29.7, 0.4)                # crane up and away
    return fx, music()


def music():
    """E minor pulse that drops out for the boom, a gentle river section, then lifts from the studio to the end."""
    t = t_all
    bpm = 108
    beat = 60 / bpm
    y = np.zeros(N)
    chords = [(0.0, (82.41, 164.81, 196.0, 246.94)), (4.62, (65.41, 130.81, 196.0, 261.63)),
              (7.85, (73.42, 146.83, 185.0, 220.0)), (11.93, (82.41, 164.81, 196.0, 246.94)),
              (12.42, (65.41, 130.81, 164.81, 196.0)), (19.05, (73.42, 146.83, 185.0, 220.0)),
              (22.1, (82.41, 164.81, 207.65, 246.94)), (26.34, (65.41, 130.81, 196.0, 261.63)),
              (29.7, (82.41, 164.81, 207.65, 246.94))]
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
    lvl = env_curve([(0, 0.5), (4.62, 0.6), (10.3, 0.8), (11.6, 0.8), (11.85, 0.0), (12.3, 0.0), (12.6, 0.45),
                     (19.05, 0.55), (22.1, 0.8), (26.34, 0.9), (29.7, 1.0), (DUR - 0.8, 0.9), (DUR, 0)])
    pll = env_curve([(0, 0), (1.75, 0), (1.8, 0.6), (11.6, 0.8), (11.85, 0), (14.0, 0), (14.1, 0.3), (19.0, 0.3),
                     (19.05, 0.5), (22.1, 0.85), (29.7, 0.9), (DUR - 0.6, 0.5), (DUR, 0)])
    kick = np.zeros(N)
    kt = T(0.35)
    k1 = np.sin(2 * np.pi * (46 + 100 * np.exp(-kt / 0.025)) * kt) * np.exp(-kt / 0.13)
    for a, b in ((1.8, 11.7), (22.1, 25.1), (26.34, 32.6)):
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
