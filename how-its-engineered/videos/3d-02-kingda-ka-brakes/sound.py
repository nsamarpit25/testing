"""Synthesised sound bed (numpy only, no samples): hydraulic launch, track roar that follows the train's speed, wind,
cut whooshes, friction screech and sparks, magnet power-ups, the magnetic-brake "vrrr", eddy hum, heat sizzle, fin
pops, sub hits and a pulsing documentary score; then mixed under audio/voice.wav with ducking.
python3 sound.py  -> audio/mix.wav (48 kHz stereo)"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 43.0
N = int(SR * DUR)
rng = np.random.default_rng(23)
t_all = np.arange(N) / SR
CUTS = [1.25, 2.8, 4.7, 6.4, 7.25, 9.3, 11.3, 14.8, 17.4, 19.8, 23.8, 24.85, 28.75, 29.95, 31.3, 32.65, 33.85, 35.0,
        36.7, 37.95, 39.55]
LAUNCH = 0.55


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


def ride_speed():
    """train speed (mph) along the timeline, from the baked HUD for the launch and a rough curve after it"""
    hud = json.load(open(os.path.join(HERE, "labels.json")))["hud"]
    ts = [(f - 1) / 30 for f, _, _ in hud]
    vs = [v for _, v, _ in hud]
    pts = list(zip(ts, vs)) + [(4.7, 125), (6.4, 70), (7.25, 48), (9.3, 118)]
    return env_curve(sorted(pts) + [(9.31, 0), (DUR, 0)])


def music():
    """E minor documentary pulse: pad + 16th-note filtered pluck + kick; drops out for 'Nothing touches',
    returns for the rollback and resolves on the outro."""
    t = t_all
    bpm = 112
    beat = 60 / bpm
    y = np.zeros(N)
    chords = [(0.0, (82.41, 123.47, 164.81, 196.0)), (9.3, (65.41, 130.81, 164.81, 196.0)),
              (14.8, (73.42, 146.83, 185.0, 220.0)), (17.4, (82.41, 123.47, 164.81, 196.0)),
              (24.85, (65.41, 130.81, 164.81, 246.94)), (28.75, (73.42, 146.83, 185.0, 220.0)),
              (31.3, (61.74, 123.47, 185.0, 246.94)), (35.0, (82.41, 123.47, 164.81, 196.0)),
              (37.95, (65.41, 130.81, 164.81, 196.0)), (39.55, (82.41, 123.47, 164.81, 207.65))]
    pl = np.zeros(N)
    for k, (t0, fs) in enumerate(chords):
        t1 = chords[k + 1][0] if k + 1 < len(chords) else DUR
        g = np.clip((t - t0 + 0.2) / 0.4, 0, 1) * np.clip((t1 + 0.2 - t) / 0.4, 0, 1)
        for i, f in enumerate(fs):
            y += g * (np.sin(2 * np.pi * f * t + i) + 0.25 * np.sin(2 * np.pi * f * 2.004 * t)) / (1 + i * 0.4)
        # pluck arpeggio on 16ths through the chord, an octave up
        st = beat / 4
        nt = T(st * 1.5)
        for j, b in enumerate(np.arange(t0, t1, st)):
            f = fs[[1, 2, 3, 2][j % 4]] * 2
            ph = 2 * np.pi * f * nt
            saw = sum(np.sin(h * ph) / h for h in range(1, 7))
            add(pl, saw * np.exp(-nt / 0.07), b, 1.0 if j % 4 == 0 else 0.6)
    y = band(y, 40, 1500)
    pl = band(pl, 200, 2600)
    lvl = env_curve([(0, 0.0), (0.5, 0.5), (4.7, 0.7), (9.3, 0.45), (17.3, 0.55), (17.45, 0.85), (31.0, 0.85),
                     (31.3, 0.25), (34.9, 0.25), (35.0, 0.7), (39.5, 0.8), (39.6, 1.0), (DUR - 0.8, 0.9), (DUR, 0)])
    pll = env_curve([(0, 0), (LAUNCH, 0), (LAUNCH + 0.05, 0.8), (9.3, 0.5), (11.3, 0.2), (17.3, 0.3), (17.45, 0.9),
                     (31.25, 0.9), (31.3, 0.0), (35.0, 0.0), (35.05, 0.6), (39.5, 0.9), (41.5, 0.5), (DUR, 0)])
    kick = np.zeros(N)
    kt = T(0.35)
    k1 = np.sin(2 * np.pi * (46 + 100 * np.exp(-kt / 0.025)) * kt) * np.exp(-kt / 0.13)
    for a, b in ((LAUNCH, 9.3), (17.4, 31.3), (35.0, 41.5)):
        for bt in np.arange(a, b, beat):
            add(kick, k1, bt)
    return norm(y) * lvl * 0.8 + norm(pl) * pll * 0.45 + 0.5 * kick * spans_gain([(0.5, 9.3), (17.35, 31.3), (34.95, 41.6)])


def build():
    fx = np.zeros(N)
    ride = spans_gain([(0, 9.3), (31.3, 31.3), (32.65, 35.0), (35.0, 39.55), (39.55, DUR)])
    # track roar: low rumble + rail whine whose pitch and level follow the train speed
    v = ride_speed() / 128
    rum = band(rng.standard_normal(N), 30, 260)
    whine_f = 120 + 900 * v
    whine = np.sin(2 * np.pi * np.cumsum(whine_f) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(whine_f * 1.5) / SR)
    wind = band(rng.standard_normal(N), 400, 5000)
    fx += (norm(rum) * 0.2 * np.sqrt(v) + whine * 0.03 * v + norm(wind) * 0.13 * v ** 1.5) * spans_gain([(0, 9.3)])
    # night ambience on the ride, room tone in the studios
    amb = band(rng.standard_normal(N), 150, 1200)
    room = band(rng.standard_normal(N), 60, 400)
    fx += norm(amb) * 0.03 * ride + norm(room) * 0.025 * (1 - ride)
    add(fx, hydraulic(), LAUNCH - 0.6, 0.35)
    add(fx, sub_hit(2.6, 34), LAUNCH, 0.9)
    for tc in CUTS:
        add(fx, whoosh(0.36), tc - 0.2, 0.22)
    add(fx, whoosh(0.9, 150, 1500), 6.35, 0.3)          # over the crest
    add(fx, riser(1.6), 7.7, 0.2)
    add(fx, vrrr(1.4, 110, 55), 7.9, 0.4)               # the train hits the brakes coming at us
    add(fx, sub_hit(1.6, 42), 9.3, 0.55)
    add(fx, screech(2.0), 9.3, 0.2)                     # friction pads
    for i in range(4):
        add(fx, powerup(196 * 1.26 ** i), 12.75 + 0.3 * i, 0.32)
    add(fx, ping(2400), 15.6, 0.16)
    add(fx, riser(1.5, 150, 2800), 15.9, 0.2)
    add(fx, sub_hit(2.0, 40), 17.4, 0.6)
    # eddy hum in the macro set: grows with the rings, pulses
    hum_f = 70 + 15 * np.sin(2 * np.pi * t_all * 0.7)
    hum = np.sin(2 * np.pi * np.cumsum(hum_f) / SR) + 0.3 * np.sin(2 * np.pi * np.cumsum(hum_f * 2) / SR)
    hum *= 0.7 + 0.3 * np.sin(2 * np.pi * 4 * t_all)
    fx += hum * 0.045 * env_curve([(0, 0), (17.4, 0), (19.8, 0.4), (23.8, 1), (28.7, 1), (28.75, 0.3), (29.95, 0.8),
                                  (31.3, 0), (DUR, 0)])
    for tw in (18.0, 20.4, 22.4):
        add(fx, whoosh(0.8, 120, 1100), tw, 0.25)       # magnet sweeping over the fin
    add(fx, sub_hit(2.0, 36), 27.95, 0.5)               # pushes back
    add(fx, sizzle(1.3), 28.8, 0.12)
    add(fx, sizzle(1.4), 29.95, 0.14)
    add(fx, vrrr(1.3, 80, 50), 32.6, 0.4)               # cars glide over the fins
    add(fx, ping(1600, 2.2), 31.35, 0.12)
    add(fx, whoosh(1.2, 120, 900), 35.05, 0.25)         # rollback
    rb = band(rng.standard_normal(N), 30, 240)
    fx += norm(rb) * 0.18 * env_curve([(0, 0), (35.0, 0), (35.6, 0.6), (37.95, 0.8), (39.4, 0.9), (39.55, 0.3),
                                       (DUR, 0)])
    for i in range(14):
        add(fx, clack(1 + 0.04 * i), 38.02 + 0.42 * i / 13, 0.3)
        add(fx, sizzle(0.25) * np.exp(-T(0.25) / 0.06), 37.99 + 0.42 * i / 13, 0.05)   # pneumatic puff per fin
    add(fx, sub_hit(0.8, 60), 38.02, 0.3)
    add(fx, vrrr(0.6, 90, 60), 39.0, 0.35)
    add(fx, sub_hit(3.0, 33), 39.55, 0.75)
    return fx, music()


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
    bed = (fx * 0.8 + mus * 0.22) * duck
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
