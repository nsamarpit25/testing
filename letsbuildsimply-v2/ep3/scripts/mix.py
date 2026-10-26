"""mix.py: narration + sound design + procedural score -> 48 kHz stereo WAV.

  python3 mix.py --voice narration.wav --events events.json --sfx SFX_DIR --out mix.wav

events.json (from scene.py) carries one-shot cues (name, time, gain) and per-frame control curves
(drill, rumble, heat, liquid, wind, music). One-shots that match a Kenney CC0 file in SFX_DIR play from it;
everything else is synthesised here with numpy. 'name:seconds' cues are that long. Music and ambience duck
under the voice; the voice stays on top.
"""
import argparse, json, os, wave
import numpy as np

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument('--voice', required=True); ap.add_argument('--events', required=True)
ap.add_argument('--sfx', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
EV = json.load(open(a.events)); B = EV['beats']; DUR = EV['dur']; FPS = EV['fps']
N = int(DUR * SR)
rng = np.random.default_rng(7)
T = np.arange(N) / SR

def read_wav(p):
    w = wave.open(p); sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32) / (2 ** (8 * sw - 1))
    x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) / SR * sr, np.arange(len(x)), x).astype(np.float32)
    return x
def noise(n): return rng.standard_normal(n).astype(np.float32)
def tone(freq, n, kind='sin', ph0=0.0):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(np.asarray(freq, np.float64), (n,)) / SR) + ph0
    if kind == 'sin': return np.sin(ph).astype(np.float32)
    if kind == 'saw': return (2 * ((ph / (2 * np.pi)) % 1) - 1).astype(np.float32)
    if kind == 'tri': return (2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1).astype(np.float32)
def fftf(x, lo=None, hi=None, soft=0.25):
    """FFT band filter with soft edges (lo/hi in Hz, either may be None)."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g *= np.clip((f - lo * (1 - soft)) / (lo * soft + 1e-9), 0, 1)
    if hi: g *= np.clip((hi * (1 + soft) - f) / (hi * soft + 1e-9), 0, 1)
    return np.fft.irfft(X * g, len(x)).astype(np.float32)
def norm(x, peak=0.9): m = np.abs(x).max() + 1e-9; return (x / m * peak).astype(np.float32)
def env_ad(n, att, dec): t = np.arange(n) / SR; return (np.minimum(1, t / max(att, 1e-4)) * np.exp(-t / dec)).astype(np.float32)
def fade(x, fi=0.01, fo=0.05):
    n = len(x); a_ = min(n, int(fi * SR)); b_ = min(n, int(fo * SR))
    if a_: x[:a_] *= np.linspace(0, 1, a_)
    if b_: x[-b_:] *= np.linspace(1, 0, b_)
    return x
def reverb(x, secs=1.6, wet=0.3, bright=4000):
    n = int(secs * SR); ir = fftf(noise(n), None, bright) * np.exp(-np.arange(n) / SR / (secs / 5))
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    y = np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n), len(x) + n)[:len(x) + n].astype(np.float32)
    out = np.zeros(len(x) + n, np.float32); out[:len(x)] += x * (1 - wet); out += y * wet * 2.5
    return out
def sweep_noise(d, f0, f1, q=0.5, shape=None):
    """noise through a moving band (block-wise FFT filter) from f0 to f1 Hz."""
    n = int(d * SR); x = noise(n); out = np.zeros(n, np.float32); blk = 2048
    win = np.hanning(blk * 2).astype(np.float32)
    for i in range(0, n, blk):
        u = i / max(1, n - 1); fc = f0 * (f1 / f0) ** u
        seg = x[max(0, i - blk // 2): i + blk + blk // 2]
        y = fftf(seg, fc * (1 - q), fc * (1 + q), 0.5)
        k = min(blk, n - i); st = i - max(0, i - blk // 2)
        out[i:i + k] += y[st:st + k]
    e = shape if shape is not None else np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return norm(out * e, 0.8)

# ------------------------------------------------------------------ one-shot designs
def s_whoosh(d=0.5): return sweep_noise(d, 400, 2600, 0.6)
def s_whoosh_low(d=0.6): return sweep_noise(d, 120, 700, 0.6)
def s_whoosh_big(d=1.1):
    x = sweep_noise(d, 150, 3200, 0.7, np.sin(np.pi * np.linspace(0, 1, int(d * SR))) ** 2.2)
    return norm(reverb(x, 1.2, 0.3), 0.9)
def s_impact_low():
    n = int(1.4 * SR); t = np.arange(n) / SR
    return norm(tone(70 * np.exp(-t * 2.5) + 28, n) * np.exp(-t / 0.35) + 0.25 * fftf(noise(n), None, 300) * np.exp(-t / 0.08), 0.9)
def s_impact_big():
    n = int(2.2 * SR); t = np.arange(n) / SR
    sub = tone(95 * np.exp(-t * 3.0) + 30, n) * np.exp(-t / 0.55)
    crack = fftf(noise(n), 800, 9000) * np.exp(-t / 0.03)
    body = fftf(noise(n), 60, 900) * np.exp(-t / 0.25)
    return norm(reverb(sub * 1.0 + crack * 0.6 + body * 0.7, 1.8, 0.25), 0.98)
def s_core_boom():
    n = int(3.5 * SR); t = np.arange(n) / SR
    sub = tone(60 * np.exp(-t * 1.5) + 24, n) * np.exp(-t / 1.0)
    roar = fftf(noise(n), 40, 500) * np.exp(-t / 0.9) * np.minimum(1, t / 0.05)
    hiss = fftf(noise(n), 2000, 9000) * np.exp(-t / 0.4) * 0.3
    return norm(reverb(sub + 0.8 * roar + hiss, 2.5, 0.35), 0.98)
def s_rewind():
    n = int(0.55 * SR); t = np.arange(n) / SR
    f = 900 + 2400 * (t / 0.55) ** 0.7
    chirp = tone(f + 300 * np.sin(2 * np.pi * 38 * t), n, 'saw') * 0.3
    tape = fftf(noise(n), 1500, 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * 26 * t) ** 2)
    return norm(fade((chirp + tape) * np.minimum(1, t / 0.03)), 0.7)
def s_tape_stop():
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = 220 * (1 - t / 0.6) ** 2 + 20
    return norm(fade(fftf(tone(f, n, 'saw'), None, 2500) * (1 - t / 0.6)), 0.6)
def s_motor_start():
    n = int(1.4 * SR); t = np.arange(n) / SR
    f = 25 + 85 * (1 - np.exp(-t * 2.2))
    m = tone(f, n, 'saw') * 0.6 + tone(f * 2.01, n, 'saw') * 0.3 + tone(f * 4.5, n) * 0.2
    return norm(fade(fftf(m, None, 1800) * np.minimum(1, t / 0.3)), 0.7)
def s_ball_drop():
    n = int(0.6 * SR); t = np.arange(n) / SR
    return norm(tone(1250, n) * np.exp(-t / 0.15) + 0.5 * tone(1875, n) * np.exp(-t / 0.08), 0.4)
def s_riser(d=1.4):
    n = int(d * SR); t = np.arange(n) / SR
    x = sweep_noise(d, 300, 4000, 0.5, (t / d) ** 2) + 0.4 * tone(110 * 2 ** (2 * t / d), n, 'saw') * (t / d) ** 2
    return norm(fftf(x, None, 6000), 0.6)
def s_metal_groan(d=1.6):
    n = int(d * SR); t = np.arange(n) / SR
    f = 60 + 25 * np.sin(2 * np.pi * 0.9 * t) + 12 * np.sin(2 * np.pi * 3.1 * t)
    car = tone(f * 3.0 + 40 * tone(f * 1.41, n), n, 'saw')
    y = fftf(car, 150, 2500) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 1.7 * t))) * np.minimum(1, t / 0.2) * np.minimum(1, (d - t) / 0.2)
    return norm(reverb(y, 1.0, 0.25), 0.7)
def s_crunch():
    n = int(0.8 * SR); t = np.arange(n) / SR
    grains = np.zeros(n, np.float32)
    for k in range(40):
        s0 = int(rng.uniform(0, 0.35) * SR); m = int(0.02 * SR)
        grains[s0:s0 + m] += noise(m) * np.exp(-np.arange(m) / SR / 0.004) * rng.uniform(0.3, 1)
    return norm(fftf(grains, 300, 7000) + 0.6 * tone(80 * np.exp(-t * 4), n) * np.exp(-t / 0.15), 0.85)
def s_metal_snap():
    n = int(0.6 * SR); t = np.arange(n) / SR
    ring = sum(tone(f, n) * np.exp(-t / dd) for f, dd in ((1830, 0.15), (2950, 0.1), (4100, 0.06)))
    return norm(fftf(noise(n), 1500, 9000) * np.exp(-t / 0.01) + 0.4 * ring, 0.8)
def s_alarm(d=1.8):
    n = int(d * SR); t = np.arange(n) / SR
    f = np.where((t % 0.5) < 0.25, 660, 520)
    return norm(fade(fftf(tone(f, n, 'saw'), None, 2500)), 0.5)
def s_splash():
    n = int(1.6 * SR); t = np.arange(n) / SR
    body = fftf(noise(n), 80, 1200) * np.exp(-t / 0.35) * np.minimum(1, t / 0.02)
    bub = np.zeros(n, np.float32)
    for k in range(18):
        s0 = int(rng.uniform(0.05, 1.2) * SR); m = int(0.12 * SR); tt = np.arange(m) / SR
        f0 = rng.uniform(90, 260)
        bub[s0:s0 + m] += tone(f0 * (1 + 2.5 * tt / 0.12), m) * np.exp(-tt / 0.04) * rng.uniform(0.3, 1)
    return norm(reverb(body + 0.6 * bub, 1.2, 0.3), 0.9)
def s_shimmer(d=3.0):
    n = int(d * SR); t = np.arange(n) / SR
    x = sum(tone(f * (1 + 0.003 * np.sin(2 * np.pi * (0.3 + i * 0.17) * t)), n) / (i + 1) for i, f in enumerate((880, 1318.5, 1760, 2637)))
    return norm(reverb(x * np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 1.2), 2.0, 0.45), 0.5)
def s_fizzle():
    n = int(1.6 * SR); t = np.arange(n) / SR
    hiss = fftf(noise(n), 2500, 11000) * np.exp(-t / 0.45)
    crackle = np.zeros(n, np.float32)
    for k in range(120):
        s0 = int(rng.uniform(0, 1.2) * SR); crackle[s0] += rng.uniform(-1, 1)
    crackle = fftf(crackle, 1000, 9000) * 6
    return norm(hiss + crackle + 0.6 * tone(140 * np.exp(-t * 2), n) * np.exp(-t / 0.2), 0.85)
def s_scan(d=0.9):
    n = int(d * SR); t = np.arange(n) / SR
    return norm(tone(500 + 900 * t / d, n) * (0.6 + 0.4 * np.sin(2 * np.pi * 24 * t)) * np.sin(np.pi * t / d), 0.4)
def s_jump():
    n = int(0.45 * SR); t = np.arange(n) / SR
    return norm(sweep_noise(0.45, 600, 2200, 0.6) + 0.3 * tone(200 + 300 * t / 0.45, n) * np.exp(-t / 0.1), 0.6)
def s_pass():
    d = 1.3; n = int(d * SR); t = np.arange(n) / SR
    e = np.exp(-((t - 0.55) / 0.22) ** 2)
    x = sweep_noise(d, 300, 2500, 0.6, e) + 0.4 * fftf(tone(180 * np.where(t < 0.55, 1.15, 0.85), n, 'saw'), None, 1200) * e
    return norm(reverb(x, 1.0, 0.3), 0.9)
def s_slowmo():
    n = int(1.2 * SR); t = np.arange(n) / SR
    return norm(reverb(fftf(tone(120 * (1 - 0.5 * t / 1.2), n, 'saw'), None, 600) * np.sin(np.pi * t / 1.2), 1.5, 0.4), 0.6)
def s_pop():
    n = int(0.25 * SR); t = np.arange(n) / SR
    return norm(tone(500 * np.exp(-t * 12) + 180, n) * np.exp(-t / 0.05), 0.6)
def s_chime():
    n = int(1.8 * SR); t = np.arange(n) / SR
    return norm(reverb((tone(1174.7, n) + 0.5 * tone(1760, n)) * np.exp(-t / 0.5) * np.minimum(1, t / 0.005), 1.5, 0.35), 0.4)
def s_resolve():
    n = int(3.0 * SR); t = np.arange(n) / SR
    x = sum(tone(f, n) * (0.9 ** i) for i, f in enumerate((146.8, 220.0, 293.7, 370.0, 440.0)))
    return norm(reverb(fftf(x, None, 3000) * np.minimum(1, t / 0.4) * np.exp(-np.maximum(0, t - 1.0) / 0.9), 2.0, 0.4), 0.6)
def s_drone_hook(d=3.6):
    n = int(d * SR); t = np.arange(n) / SR
    x = tone(36.7, n) + 0.6 * tone(73.4 * (1 + 0.002 * np.sin(t * 2)), n, 'saw') + 0.3 * tone(110, n, 'tri')
    return norm(fftf(x, None, 900) * np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.4), 0.7)
def s_debris(d=1.4):
    out = np.zeros(int((d + 1.0) * SR), np.float32)
    for k in range(14):
        nm = ['impactMining_000', 'impactMining_001', 'impactMining_002', 'impactPlate_medium_001', 'impactSoft_heavy_001'][k % 5]
        x = kenney(nm)
        if x is None: continue
        x = resample(x, rng.uniform(0.75, 1.25)) * rng.uniform(0.3, 0.9) * (1 - k / 18)
        s0 = int(rng.uniform(0, d) * SR); out[s0:s0 + len(x)] += x[:len(out) - s0]
    return norm(out, 0.8)
def resample(x, rate):
    n = int(len(x) / rate); return np.interp(np.arange(n) * rate, np.arange(len(x)), x).astype(np.float32)
_K = {}
def kenney(name):
    p = os.path.join(a.sfx, name + '.wav')
    if not os.path.exists(p): return None
    if name not in _K: _K[name] = read_wav(p)
    return _K[name]
SYN = dict(whoosh=s_whoosh, whoosh_low=s_whoosh_low, whoosh_big=s_whoosh_big, impact_low=s_impact_low, impact_big=s_impact_big,
           core_boom=s_core_boom, rewind=s_rewind, freeze_drop=s_tape_stop, motor_start=s_motor_start, ball_drop=s_ball_drop,
           riser=s_riser, metal_groan=s_metal_groan, crunch=s_crunch, metal_snap=s_metal_snap, alarm=s_alarm, splash=s_splash,
           shimmer=s_shimmer, fizzle=s_fizzle, scan=s_scan, jump=s_jump, pass_whoosh=s_pass, slowmo=s_slowmo, pop_out=s_pop,
           chime=s_chime, resolve=s_resolve, drone_hook=s_drone_hook, debris=s_debris, fall_whoosh=lambda d=2.8: sweep_noise(d, 150, 3000, 0.6, (np.linspace(0, 1, int(d * SR)) ** 1.5) * np.minimum(1, (d - np.arange(int(d * SR)) / SR) / 0.3)))

L = np.zeros(N + SR * 4, np.float32); Rc = np.zeros_like(L)
def place(x, t0, gain=1.0, pan=0.0):
    s0 = int(t0 * SR)
    if s0 < 0: x = x[-s0:]; s0 = 0
    x = x[:len(L) - s0]; gl = gain * np.sqrt(0.5 * (1 - pan)); gr = gain * np.sqrt(0.5 * (1 + pan))
    L[s0:s0 + len(x)] += x * gl; Rc[s0:s0 + len(x)] += x * gr
for e in EV['events']:
    nm = e['name']; d = None
    if ':' in nm: nm, d = nm.split(':'); d = float(d)
    if nm in SYN: x = SYN[nm](d) if d else SYN[nm]()
    else:
        x = kenney(nm)
        if x is None: print('missing cue', nm); continue
        x = resample(x, e.get('rate', 1.0))
    place(x, e['t'], e['gain'] * 0.8, rng.uniform(-0.25, 0.25))

# ------------------------------------------------------------------ continuous beds from control curves
def curve(name):
    c = np.asarray(EV['curves'][name], np.float32); ft = np.arange(len(c)) / FPS
    y = np.interp(T, ft, c).astype(np.float32)
    k = int(0.04 * SR); return np.convolve(y, np.ones(k) / k, mode='same').astype(np.float32)
cd, cr, ch, cl, cw, cm = (curve(k) for k in ('drill', 'rumble', 'heat', 'liquid', 'wind', 'music'))
# drill: motor + grinding rock, pitch follows spin
f = 38 + 70 * cd
motor = tone(f, N, 'saw') * 0.5 + tone(f * 2.02, N, 'saw') * 0.25 + tone(f * 6, N) * 0.08
grind = fftf(noise(N), 200, 3500) * (0.55 + 0.45 * np.abs(np.sin(2 * np.pi * (f / 6) * T)))
drill = (fftf(motor, None, 1500) * 0.6 + grind * 0.35) * cd
rumble = fftf(noise(N), 25, 140) * 3.0 * cr
hiss = fftf(noise(N), 1800, 9000) * (0.6 + 0.4 * fftf(noise(N), None, 6)) * 0.25 * ch
bubbles = np.zeros(N, np.float32)
for k in range(int(DUR * 12)):
    t0 = rng.uniform(0, DUR); s0 = int(t0 * SR); m = int(0.15 * SR)
    if s0 + m >= N: continue
    tt = np.arange(m) / SR; bubbles[s0:s0 + m] += tone(rng.uniform(60, 170) * (1 + 2 * tt / 0.15), m) * np.exp(-tt / 0.05) * 0.5
gloop = (fftf(noise(N), 30, 300) * 1.2 + bubbles) * cl
wn = noise(N); wind = (fftf(wn, 200, 900) * (1 - cw) + fftf(wn, 400, 4000) * cw) * cw * 0.9
amb = drill * 0.5 + rumble * 0.6 + hiss * 0.5 + gloop * 0.45 + wind * 0.55

# ------------------------------------------------------------------ score: ominous drone -> driving pulse -> silence -> wonder
def note(fr, n, kind='saw', det=0.004):
    return (tone(fr * (1 - det), n, kind) + tone(fr * (1 + det), n, kind)) * 0.5
music = np.zeros(N, np.float32)
t_dig, t_tw = B['first'] + 0.2, B['but2'] - 0.06
# A: drone (hook)
n1 = int(t_dig * SR); music[:n1] += fftf(note(73.4, n1) + 0.5 * note(110, n1, 'tri') + 0.25 * note(440, n1, 'sin'), None, 1200)[:n1] * 0.35
# B: minor pulse, 116 bpm eighths, chords Dm Bb Gm A
bpm = 116; e8 = 60 / bpm / 2
chords = [(73.4, 146.8, 174.6, 220.0), (58.3, 116.5, 146.8, 174.6), (49.0, 98.0, 116.5, 146.8), (55.0, 110.0, 138.6, 164.8)]
i0, i1 = int(t_dig * SR), int(t_tw * SR); nB = i1 - i0
bar = 8 * e8
pad = np.zeros(nB, np.float32); pulse = np.zeros(nB, np.float32); kick = np.zeros(nB, np.float32)
tb = np.arange(nB) / SR
for k in range(int(nB / SR / bar) + 1):
    c = chords[k % 4]; s0 = int(k * bar * SR); m = min(nB - s0, int(bar * SR))
    if m <= 0: break
    env = np.minimum(1, np.arange(m) / SR / 0.08) * np.minimum(1, (m / SR - np.arange(m) / SR) / 0.08)
    pad[s0:s0 + m] += sum(note(fr, m) for fr in c[1:]) * env * 0.2
    for j in range(8):
        p0 = s0 + int(j * e8 * SR); pm = int(e8 * 0.9 * SR)
        if p0 + pm > nB: break
        tt = np.arange(pm) / SR
        pulse[p0:p0 + pm] += note(c[0] * 2, pm, 'saw') * np.exp(-tt / 0.09) * 0.5
        if j % 2 == 0: kick[p0:p0 + pm] += tone(55 * np.exp(-tt * 18) + 40, pm) * np.exp(-tt / 0.18)
grow = np.clip((tb - 0.0) / (nB / SR), 0, 1)
music[i0:i1] += (fftf(pad, None, 1600) * (0.5 + 0.5 * grow) + (fftf(pulse, None, 900) * (1 - grow) + fftf(pulse, None, 2700) * grow) * (0.35 + 0.65 * grow) + kick * 0.5 * (0.3 + 0.7 * grow)) * 0.55
# C: wonder (D major add9 arpeggio + pad), from after the freeze to the end
i2 = int((t_tw + 0.75) * SR); nC = N - i2; tc = np.arange(nC) / SR
padC = sum(note(fr, nC, 'tri', 0.003) for fr in (146.8, 220.0, 293.7, 329.6, 370.0)) * 0.16
padC *= np.minimum(1, tc / 1.5)
arp = np.zeros(nC, np.float32); seq = (587.3, 740.0, 880.0, 659.3, 740.0, 987.8, 880.0, 740.0)
for k in range(int(nC / SR / e8)):
    p0 = int(k * e8 * SR); pm = int(0.5 * SR)
    if p0 + pm > nC: break
    tt = np.arange(pm) / SR
    arp[p0:p0 + pm] += tone(seq[k % 8], pm) * np.exp(-tt / 0.22) * 0.22 * min(1.0, k / 16)
music[i2:] += fftf(padC, None, 2200) + reverb(arp, 1.6, 0.4)[:nC] * 0.8
music *= np.clip(cm, 0, 1)

# ------------------------------------------------------------------ voice, ducking, master
voice = read_wav(a.voice); voice = voice / (np.abs(voice).max() + 1e-9) * 0.92
vo = np.zeros(N, np.float32); vo[:min(N, len(voice))] = voice[:N]
k = int(0.12 * SR); venv = np.sqrt(np.convolve(vo ** 2, np.ones(k) / k, mode='same'))
duck = 1 - 0.55 * np.clip(venv / 0.12, 0, 1)
bed = (norm(amb, 0.5) * 0.85 + norm(music, 0.5) * 0.55) * duck
sfx_l, sfx_r = L[:N] * (1 - 0.3 * np.clip(venv / 0.12, 0, 1)), Rc[:N] * (1 - 0.3 * np.clip(venv / 0.12, 0, 1))
mixL = vo * 1.0 + bed * 0.55 + sfx_l * 0.42
mixR = vo * 1.0 + bed * 0.55 + sfx_r * 0.42
st = np.stack([mixL, mixR], 1)
st = np.tanh(st * 1.15) / np.tanh(1.15)          # soft limiter
st = st / (np.abs(st).max() + 1e-9) * 0.95
n_f = int(0.6 * SR); st[-n_f:] *= np.linspace(1, 0, n_f)[:, None]
o = wave.open(a.out, 'wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR)
o.writeframes((st * 32767).astype(np.int16).tobytes()); o.close()
print(a.out, f'{N / SR:.2f}s')
