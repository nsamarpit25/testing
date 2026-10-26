"""Synthesised SFX bed (numpy only, no music): ice drips, wood/tin pops, slides, compressor hum, hiss, door thud, light click,
glass clinks and a final chime, plus a whoosh on every camera move; mixed under audio/voice.wav.
python3 sound.py -> audio/mix.wav (48 kHz stereo)"""
import json, os, re, subprocess, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
LINES = json.load(open(os.path.join(HERE, "audio/lines.json")))
WORDS = json.load(open(os.path.join(HERE, "audio/words.json")))
DUR = LINES[-1]["end"] + 1.1
N = int(SR * DUR)
rng = np.random.default_rng(26)
t_all = np.arange(N) / SR
_n = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())


def W(li, word=None, k=0):
    if word is None:
        return LINES[li - 1]["start"]
    ws = [w for w in WORDS if w[3] == li and _n(w[0]).startswith(word)]
    return ws[min(k, len(ws) - 1)][1]


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


def thunder(d=3.5):
    """a close strike: a tearing crack, then a long rolling rumble"""
    t = T(d)
    crk = band(rng.standard_normal(len(t)), 900, 9000) * np.exp(-t / 0.05)
    roll = band(rng.standard_normal(len(t)), 30, 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 2.3 * t) ** 2)
    roll *= np.minimum(1, t / 0.08) * np.exp(-t / 1.1)
    return norm(0.7 * norm(crk) + norm(roll))


def gurgle(d=1.2):
    """water rushing into hollow chambers: bubbles over a low churn"""
    t = T(d)
    y = band(rng.standard_normal(len(t)), 80, 900) * 0.6
    for tb in np.sort(rng.uniform(0, d - 0.1, 70)):
        f0 = rng.uniform(250, 900)
        bt = T(0.08)
        b = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 2.5 * bt / 0.08)) / SR) * np.exp(-bt / 0.02)
        i = int(tb * SR)
        y[i:i + len(b)] += b[:len(y) - i] * rng.uniform(0.2, 0.6)
    return norm(y * np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.2))


def pump(d=1.0):
    t = T(d)
    ph = 2 * np.pi * np.cumsum(110 + 20 * np.minimum(1, t / 0.3)) / SR
    hum = np.tanh(2 * np.sin(ph)) * (0.7 + 0.3 * np.sin(2 * np.pi * 6 * t))
    return norm(band(hum, 60, 1500) * np.minimum(1, t / 0.1) * np.minimum(1, (d - t) / 0.2))


def groan(d=1.4, f0=55):
    """a huge steel structure under load: a slow low grinding moan"""
    t = T(d)
    f = f0 * (1 + 0.15 * np.sin(2 * np.pi * 0.7 * t)) + 4 * np.sin(2 * np.pi * 9 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    g = np.tanh(2.5 * (np.sin(ph) + 0.4 * np.sin(2.01 * ph) + 0.2 * np.sin(3.03 * ph)))
    gr = band(rng.standard_normal(len(t)), 120, 1400) * (0.5 + 0.5 * np.sin(ph * 0.25) ** 2)
    e = np.minimum(1, t / 0.25) * np.minimum(1, (d - t) / 0.35)
    return norm(band(g, 30, 1200) * e + 0.35 * norm(gr) * e)




def pop(f=1.0):
    t = T(0.14)
    ff = 520 * f * (1 + 1.4 * np.exp(-t / 0.012))
    return norm(np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t / 0.035) + 0.3 * band(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t / 0.006))


def thud(f=1.0):
    t = T(0.5)
    return norm(np.sin(2 * np.pi * (70 * f + 90 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.09) + 0.4 * band(rng.standard_normal(len(t)), 100, 1600) * np.exp(-t / 0.03))


def hum(d, f0=50):
    t = T(d)
    ph = 2 * np.pi * f0 * t
    y = np.tanh(1.6 * (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph))) * (0.85 + 0.15 * np.sin(2 * np.pi * 7 * t))
    return norm(band(y, 40, 900) * np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.2))


def boing(d=0.35):
    t = T(d)
    f = 300 + 500 * (t / d) + 60 * np.sin(2 * np.pi * 18 * t)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.14))


def build():
    sfx = np.zeros(N)
    # camera moves (same shot list as fr.py)
    tb, ttray, t5, tswap, tliq, t7, t8 = W(3, "wooden"), W(3, "tray"), W(5), W(6, "swap"), W(6, "liquid"), W(7), W(8)
    tcomp, t10, t11, t12, tthermo, t14, t16 = W(9, "compressor"), W(10), W(11), W(12), W(13, "thermostat"), W(14), W(16)
    tdrip, tdry, t18, t19 = W(17, "drips"), W(17, "dries"), W(18), W(19)
    cuts = [W(2) - 0.1, tb - 0.25, ttray - 0.2, W(4) - 0.1, t5 - 0.1, tswap - 0.25, tliq - 0.2, t7 + 0.4, t8 - 0.1, tcomp - 0.3, t10 - 0.1,
            W(10, "thats") - 0.1, t11 - 0.1, W(11, "freezing") - 0.15, t12 - 0.1, tthermo - 0.25, t14 - 0.1, W(15, "rubber") - 0.2, t16 - 0.1,
            tdrip - 0.2, tdry - 0.4, t18 - 0.1, t19 - 0.1]
    for c in cuts:
        add(sfx, whoosh(0.42, 300, 2600), c - 0.05, 0.22)
    # L1-2 ice: a clink, then melt drips
    add(sfx, chime(2600, 0.6), 0.35, 0.12)
    for k in range(7):
        add(sfx, plip(0.4), W(2, "melts") + 0.28 * k + rng.uniform(0, 0.1), 0.3)
    # L3 icebox: wood pops, tin tinks, tray slide
    for k in range(10):
        add(sfx, clack(0.8 + 0.05 * k), tb + 0.05 * k, 0.35)
    for k in range(5):
        add(sfx, ping(2300 + 150 * k, 0.4), W(3, "tin") + 0.06 * k, 0.12)
    add(sfx, slide(0.5), ttray, 0.3); add(sfx, clack(1.3), ttray + 0.5, 0.35)
    for k in range(4):
        add(sfx, pop(1.2 + 0.1 * k), W(3, "tin") + 0.5 + 0.08 * k, 0.3)
    # L5: clock spins (fast ticks), crate slides in and lands
    for k in range(18):
        add(sfx, clack(2.2), t5 + 0.6 + 0.07 * k, 0.15)
    add(sfx, slide(0.6), W(5, "iceman") - 0.1, 0.35); add(sfx, thud(0.9), W(5, "iceman") + 0.55, 0.5)
    # L6 fridge assembles
    add(sfx, thud(1.1), tswap - 0.05, 0.4)
    for k in range(6):
        add(sfx, pop(0.9 + 0.08 * k), tswap + 0.03 * k * 3, 0.25)
    add(sfx, powerup(330, 0.9), tliq, 0.22)
    add(sfx, gurgle(1.2), tliq + 0.2, 0.18)
    # L7 food pops, heat rising
    for k in range(4):
        add(sfx, pop(1.1 + 0.12 * k), t7 + 0.1 + 0.08 * k, 0.3)
    add(sfx, riser(1.6, 300, 2500), W(7, "soaks") - 0.4, 0.12)
    add(sfx, sizzle(1.0), t8 + 0.2, 0.06)
    # L9 compressor: lands, hums while running
    add(sfx, thud(0.8), tcomp - 0.1, 0.55)
    toff = W(13, "off")
    add(sfx, hum(toff - W(9, "squeezes") + 0.1), W(9, "squeezes"), 0.2)
    add(sfx, hum(DUR - t14 - 0.5), t14 + 0.3, 0.12)
    add(sfx, sizzle(1.6), W(10, "dumps"), 0.08)
    add(sfx, sizzle(1.4), W(11, "tube") - 0.1, 0.1)
    add(sfx, chime(1900, 1.2), W(11, "freezing"), 0.12)
    # L12 milk freezes, L13 thermostat click
    for k in range(6):
        add(sfx, chime(2800 + 300 * k, 0.5), W(12, "ice") - 0.3 + 0.08 * k, 0.07)
    add(sfx, pop(1.0), tthermo - 0.1, 0.3)
    add(sfx, clack(1.8), W(13, "switches") + 0.3, 0.45)
    add(sfx, powerup(160, 0.6)[::-1], toff, 0.18)
    # L14-15 door: creak, cold air, seal, thud shut
    add(sfx, creak(0.7), t14, 0.25)
    add(sfx, whoosh(2.2, 200, 1200), t14 + 0.4, 0.12)
    for k in range(4):
        add(sfx, pop(0.7), W(15, "rubber") - 0.1 + 0.03 * k, 0.2)
    add(sfx, thud(0.75), W(15, "magnet") + 0.1, 0.65)
    # L16-17 frost, heater, drips, steam
    add(sfx, sweep_noise(2.0, 3000, 9000) * 0.6, t16 + 0.4, 0.08)
    add(sfx, powerup(120, 0.5), W(17, "heater"), 0.15)
    add(sfx, sizzle(2.0), W(17, "heater") + 0.2, 0.12)
    for k in range(8):
        add(sfx, plip(0.4), tdrip + 0.22 * k + 1.0, 0.32)
    add(sfx, sizzle(1.8), tdry, 0.16)
    # L18 shelves clink, food pops, door opens, light click
    for k in range(3):
        add(sfx, ping(3200 - 300 * k, 0.5), W(18, "shelves") - 0.15 + 0.12 * k, 0.15)
    for k in range(8):
        add(sfx, pop(1.0 + 0.07 * k), W(18, "shelves") + 0.25 + 0.09 * k, 0.25)
    add(sfx, creak(0.5), W(18, "open") - 0.35, 0.2)
    add(sfx, clack(2.5), W(18, "open"), 0.45)
    # L19 congratulations: sparkle + gnome hops
    for k, f in enumerate((1568, 1976, 2349, 3136)):
        add(sfx, chime(f, 1.4), t19 + 0.06 * k, 0.12)
    add(sfx, boing(), t19 + 0.02, 0.2); add(sfx, boing(0.3), t19 + 0.52, 0.16)
    return sfx


def main():
    sfx = build()
    v = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(HERE, "audio/voice.wav"), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True).stdout
    voice = np.frombuffer(v, np.float32)[:N]
    voice = np.pad(voice, (0, N - len(voice)))
    env = np.convolve(np.abs(voice), np.ones(2400) / 2400, "same")
    duck = 1 - 0.35 * np.clip(env / (env.max() * 0.3 + 1e-9), 0, 1)
    mix = voice + 0.55 * sfx * duck
    fade = np.clip((DUR - t_all) / 0.5, 0, 1)
    mix = mix * fade
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    st = np.stack([mix, mix], 1)
    with wave.open(os.path.join(HERE, "audio/mix_raw.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(HERE, "audio/mix_raw.wav"), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", str(SR), os.path.join(HERE, "audio/mix.wav")], check=True)
    print("mix", round(DUR, 2), "s")


main()
