"""Synthesised sound bed (numpy only, no samples): turbofan roar and spool whine, the turbine disc's blade-pass
whine, thermal crackle, the blade sliding out of its slot, crystal shimmer, the crack, an x-ray scan sweep, cooling air
rushing through the channels and hissing from the holes, ceramic clinks, cut whooshes, sub hits and a premium pulse
score; mixed under audio/voice.wav with ducking. python3 sound.py  -> audio/mix.wav (48 kHz stereo)"""
import os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 32.0
N = int(SR * DUR)
rng = np.random.default_rng(31)
t_all = np.arange(N) / SR
CUTS = [1.6, 2.9, 4.85, 6.4, 8.15, 10.9, 13.4, 15.5, 17.55, 18.75, 19.95, 21.45, 23.1, 24.55, 26.0, 28.6]


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
    eng = spans_gain([(0, 2.9), (28.6, DUR)], 0.05)
    disc = spans_gain([(2.9, 4.85), (26.0, 28.6)], 0.04)
    therm = spans_gain([(2.9, 4.85), (26.0, 28.6)], 0.05)
    # turbofan: low roar, fan buzz-saw and a high spool whine
    roar = band(rng.standard_normal(N), 30, 700)
    fan_f = 210 + 8 * np.sin(2 * np.pi * 0.3 * t_all)
    fan = np.tanh(2 * np.sin(2 * np.pi * np.cumsum(fan_f) / SR))
    spool = np.sin(2 * np.pi * np.cumsum(np.full(N, 2350.0)) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(np.full(N, 3525.0)) / SR)
    fx += (norm(roar) * 0.32 + band(fan, 100, 2500) * 0.05 + spool * 0.012) * eng
    # turbine disc: blade-pass whine and hot gas rush
    bp = 1600 + 40 * np.sin(2 * np.pi * 0.5 * t_all)
    bpw = np.sin(2 * np.pi * np.cumsum(bp) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(bp * 2) / SR)
    gas = band(rng.standard_normal(N), 200, 6000)
    fx += (bpw * 0.02 + norm(gas) * 0.13) * disc
    # thermal: deep heat rumble and crackle
    crk = (rng.random(N) > 0.9993).astype(float)
    crk = band(np.convolve(crk, np.exp(-T(0.004) / 0.0008), "same"), 1500, 12000)
    fx += (norm(band(rng.standard_normal(N), 25, 160)) * 0.25 + norm(crk) * 0.12) * therm
    # the hero blade sits in the gas stream: a low, steady flame rush under every macro shot
    fx += norm(band(rng.standard_normal(N), 60, 900)) * 0.06 * spans_gain([(4.85, 26.0)], 0.05)
    # cruise wind on the exterior shots
    fx += norm(band(rng.standard_normal(N), 150, 2500)) * 0.10 * eng
    add(fx, sub_hit(2.4, 34), 0.0, 0.7)                 # open on the hook
    for tc in CUTS:
        add(fx, whoosh(0.34), tc - 0.19, 0.18)
    add(fx, whoosh(1.0, 120, 1400), 1.45, 0.3)          # push in on the engine
    add(fx, riser(1.2, 150, 3000), 1.75, 0.12)
    add(fx, sub_hit(1.6, 40), 2.9, 0.5)                 # into the flame
    add(fx, sub_hit(1.2, 46), 4.85, 0.25)               # the hero blade
    add(fx, tone(2640, 1.4, 0.5), 6.1, 0.12)
    add(fx, sub_hit(1.4, 44), 6.4, 0.35)
    for i, f in enumerate((1568, 1976, 2349, 2794)):    # grains appear
        add(fx, chime(f, 1.4), 8.3 + 0.18 * i, 0.06)
    add(fx, sizzle(1.2) * 0.6, 9.9, 0.08)               # boundaries heat up
    add(fx, creak(0.9), 11.15, 0.18)                    # strain
    add(fx, crack(1.0), 11.6, 0.6)
    add(fx, crack(0.7), 12.15, 0.3)
    add(fx, riser(2.0, 120, 2400), 13.45, 0.16)         # crystal grows
    add(fx, chime(1318, 2.6), 15.45, 0.14)              # one flawless crystal
    add(fx, chime(1976, 2.2), 15.5, 0.08)
    add(fx, sweep_noise(1.0, 3000, 300) * np.hanning(int(SR * 1.0)), 17.6, 0.12)   # x-ray scan
    add(fx, tone(880, 1.2, 0.4, (1, 1.5, 2)), 17.6, 0.05)
    air = band(rng.standard_normal(N), 300, 4000)
    fx += norm(air) * 0.09 * env_curve([(0, 0), (18.75, 0), (19.0, 0.8), (19.9, 1), (21.4, 1), (23.0, 0.6),
                                        (23.1, 0), (DUR, 0)])
    hiss = band(rng.standard_normal(N), 3500, 12000)
    fx += norm(hiss) * 0.05 * env_curve([(0, 0), (20.0, 0), (20.4, 1), (23.0, 0.8), (23.1, 0), (DUR, 0)])
    for tw in (18.8, 19.4):
        add(fx, whoosh(0.7, 200, 2200), tw, 0.18)       # air through the passes
    add(fx, tone(3100, 0.5, 0.12, (1, 2.7, 5.1)), 23.6, 0.12)   # ceramic coat lifts off
    add(fx, tone(2700, 0.5, 0.12, (1, 2.7, 5.1)), 23.7, 0.1)
    add(fx, sub_hit(1.2, 48), 24.55, 0.25)
    add(fx, sub_hit(2.4, 36), 26.0, 0.6)               # payoff: back in the flame
    add(fx, sub_hit(3.0, 32), 28.6, 0.55)               # out to the airliner
    add(fx, whoosh(1.4, 100, 900), 28.45, 0.3)
    return fx, music()


def music():
    """D minor pulse: warm pad, 16th-note pluck from the first cut, kick on the big sections, resolves at the end."""
    t = t_all
    bpm = 104
    beat = 60 / bpm
    y = np.zeros(N)
    chords = [(0.0, (73.42, 146.83, 174.61, 220.0)), (4.85, (58.27, 116.54, 174.61, 233.08)),
              (8.15, (65.41, 130.81, 155.56, 196.0)), (13.4, (87.31, 130.81, 174.61, 220.0)),
              (17.55, (73.42, 146.83, 174.61, 220.0)), (23.1, (58.27, 116.54, 174.61, 233.08)),
              (26.0, (65.41, 130.81, 164.81, 196.0)), (28.6, (73.42, 146.83, 185.0, 220.0))]
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
    lvl = env_curve([(0, 0.5), (4.85, 0.6), (8.15, 0.5), (13.4, 0.6), (17.55, 0.75), (26.0, 0.85), (28.6, 1.0),
                     (DUR - 0.8, 0.9), (DUR, 0)])
    pll = env_curve([(0, 0), (1.55, 0), (1.6, 0.6), (8.1, 0.6), (8.15, 0.3), (13.4, 0.5), (17.55, 0.85),
                     (25.95, 0.9), (26.0, 0.4), (28.6, 0.9), (DUR - 0.6, 0.5), (DUR, 0)])
    kick = np.zeros(N)
    kt = T(0.35)
    k1 = np.sin(2 * np.pi * (46 + 100 * np.exp(-kt / 0.025)) * kt) * np.exp(-kt / 0.13)
    for a, b in ((1.6, 8.15), (17.55, 26.0), (28.6, 31.2)):
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
