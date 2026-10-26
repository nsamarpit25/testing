"""mix.py: narration + sound design + original procedural score -> 48 kHz stereo WAV (all sounds synthesised here).

  python3 mix.py --voice narration.wav --events events.json --out mix.wav

events.json (from scene.py) carries one-shot cues and per-frame control curves (hum, rate, roll, music, room).
Sound story: the hook opens on an unexpectedly smooth rolling hum; the rewind brings four muted corner knocks (and cup
clinks) on the flat road; on the matched road those knocks become a soft rhythmic click; the score dips during the
contact explanation; a gentle ceramic tick closes the loop. Music and beds duck under Puck.
"""
import argparse, json, wave
import numpy as np

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument('--voice', required=True); ap.add_argument('--events', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
EV = json.load(open(a.events)); B = EV['beats']; DUR = EV['dur']; FPS = EV['fps']; SH = EV['shots']
N = int(round(DUR * SR))
rng = np.random.default_rng(14)
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
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g *= np.clip((f - lo * (1 - soft)) / (lo * soft + 1e-9), 0, 1)
    if hi: g *= np.clip((hi * (1 + soft) - f) / (hi * soft + 1e-9), 0, 1)
    return np.fft.irfft(X * g, len(x)).astype(np.float32)
def norm(x, peak=0.9): m = np.abs(x).max() + 1e-9; return (x / m * peak).astype(np.float32)
def fade(x, fi=0.005, fo=0.03):
    n = len(x); a_ = min(n, int(fi * SR)); b_ = min(n, int(fo * SR))
    if a_: x[:a_] *= np.linspace(0, 1, a_)
    if b_: x[-b_:] *= np.linspace(1, 0, b_)
    return x
def reverb(x, secs=1.4, wet=0.3, bright=5000, seed=3):
    r = np.random.default_rng(seed); n = int(secs * SR)
    ir = fftf(r.standard_normal(n).astype(np.float32), None, bright) * np.exp(-np.arange(n) / SR / (secs / 5))
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    y = np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n), len(x) + n)[:len(x) + n].astype(np.float32)
    out = np.zeros(len(x) + n, np.float32); out[:len(x)] += x * (1 - wet); out += y * wet * 2.2
    return out
def partials(spec, n):
    t = np.arange(n) / SR
    return sum(amp * tone(f, n) * np.exp(-t / d) for f, amp, d in spec)

# ------------------------------------------------------------------ one-shots
def s_knock():                       # muted corner knock: aluminium plate corner on maple, damped
    n = int(0.35 * SR); t = np.arange(n) / SR
    thud = tone(118 * np.exp(-t * 9) + 74, n) * np.exp(-t / 0.075)
    wood = fftf(noise(n), 250, 2200) * np.exp(-t / 0.022)
    tok = tone(420 * np.exp(-t * 4) + 300, n) * np.exp(-t / 0.035)        # mid 'tok' body: audible on phone speakers
    ring = partials([(1240, 0.18, 0.05), (2310, 0.12, 0.035), (3570, 0.07, 0.02)], n)
    return norm(fade(reverb(thud * 0.8 + tok * 0.7 + wood * 0.8 + ring, 0.6, 0.12)[:n]), 0.9)
def s_clink():                       # porcelain cup rattling on its saucer
    n = int(0.4 * SR); out = np.zeros(n, np.float32)
    for k, (dt, g) in enumerate(((0.0, 1.0), (0.022, 0.45), (0.041, 0.2))):
        s0 = int(dt * SR); m = n - s0
        sp = [(2650 * (1 + 0.01 * k), 0.5, 0.09), (4110, 0.35, 0.06), (5930, 0.25, 0.04), (7350, 0.15, 0.025)]
        out[s0:] += g * (partials(sp, m) + 0.3 * fftf(noise(m), 3000, 10000) * np.exp(-np.arange(m) / SR / 0.003))
    return norm(fade(reverb(out, 0.7, 0.18)[:n]), 0.7)
def s_click():                       # soft rhythmic click: a corner settling into a join
    n = int(0.12 * SR); t = np.arange(n) / SR
    x = tone(780, n) * np.exp(-t / 0.018) * 0.6 + fftf(noise(n), 1500, 6000) * np.exp(-t / 0.004) * 0.5 + tone(1960, n) * np.exp(-t / 0.01) * 0.25
    return norm(fade(x), 0.6)
def s_tick():                        # gentle ceramic tick (loop seam)
    n = int(0.6 * SR)
    x = partials([(3180, 0.6, 0.12), (4920, 0.35, 0.08), (6810, 0.2, 0.05)], n) + 0.2 * fftf(noise(n), 3000, 9000) * np.exp(-np.arange(n) / SR / 0.002)
    return norm(fade(reverb(x, 1.0, 0.25)[:n]), 0.6)
def s_rewind():
    n = int(0.5 * SR); t = np.arange(n) / SR
    f = 700 + 2600 * (t / 0.5) ** 0.7
    chirp = tone(f + 260 * np.sin(2 * np.pi * 34 * t), n, 'saw') * 0.25
    tape = fftf(noise(n), 1500, 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * 24 * t) ** 2)
    return norm(fade(fftf(chirp + tape, None, 3800) * np.minimum(1, t / 0.03)), 0.45)
def s_freeze():
    n = int(0.7 * SR); t = np.arange(n) / SR
    stop = fftf(tone(240 * (1 - t / 0.7) ** 2 + 25, n, 'saw'), None, 2000) * (1 - t / 0.7) * 0.5
    air = fftf(noise(n), 2000, 9000) * np.exp(-t / 0.05) * 0.4
    return norm(fade(reverb(stop + air, 0.9, 0.25)[:n]), 0.6)
def s_slide():                       # flat plank sinking into the plinth
    n = int(0.8 * SR); t = np.arange(n) / SR
    x = fftf(noise(n), 90, 900) * np.sin(np.pi * t / 0.8) ** 1.5 + tone(60, n) * np.sin(np.pi * t / 0.8) * 0.4
    return norm(fade(x), 0.6)
def s_clack():                       # a maple arc seating into place
    n = int(0.25 * SR); t = np.arange(n) / SR
    x = tone(190 * np.exp(-t * 6) + 120, n) * np.exp(-t / 0.05) + fftf(noise(n), 400, 3000) * np.exp(-t / 0.012) * 0.7
    return norm(fade(reverb(x, 0.5, 0.15)[:n]), 0.7)
def s_shimmer():
    n = int(1.6 * SR); t = np.arange(n) / SR
    x = sum(tone(f, n) * (0.3 + 0.7 * np.sin(np.pi * t / 1.6)) for f in (1318.5, 1760.0, 2217.5)) * 0.3
    return norm(fade(reverb(x * np.minimum(1, t / 0.25), 1.6, 0.4)[:n], 0.01, 0.3), 0.35)
def s_motor_start():                 # tiny DC gearmotor spinning up
    n = int(0.9 * SR); t = np.arange(n) / SR
    f = 120 + 260 * (1 - np.exp(-t * 5))
    x = tone(f, n, 'saw') * 0.4 + tone(f * 3.0, n) * 0.25 + tone(f * 5.02, n) * 0.1
    return norm(fade(fftf(x, 80, 3000) * np.minimum(1, t / 0.06) * np.exp(-np.maximum(0, t - 0.5) / 0.3)), 0.5)
def s_swish():
    n = int(0.45 * SR); t = np.arange(n) / SR
    return norm(fade(fftf(noise(n), 500, 5000) * np.sin(np.pi * t / 0.45) ** 2), 0.4)
SYN = dict(knock=s_knock, clink=s_clink, click=s_click, tick=s_tick, rewind=s_rewind, freeze=s_freeze, slide=s_slide,
           clack=s_clack, shimmer=s_shimmer, motor_start=s_motor_start, swish=s_swish)
CACHE = {}
def resample(x, rate):
    n = int(len(x) / rate); return np.interp(np.arange(n) * rate, np.arange(len(x)), x).astype(np.float32)
L = np.zeros(N + SR * 4, np.float32); Rc = np.zeros_like(L)
def place(x, t0, gain=1.0, pan=0.0):
    s0 = int(round(t0 * SR))
    if s0 < 0: x = x[-s0:]; s0 = 0
    x = x[:len(L) - s0]; gl = gain * np.sqrt(0.5 * (1 - pan)); gr = gain * np.sqrt(0.5 * (1 + pan))
    L[s0:s0 + len(x)] += x * gl; Rc[s0:s0 + len(x)] += x * gr
for e in EV['events']:
    nm = e['name']
    if nm not in CACHE: CACHE[nm] = [SYN[nm]() for _ in range(3)]          # three variations per cue
    x = CACHE[nm][int(rng.integers(3))]
    if e.get('rate', 1.0) != 1.0: x = resample(x, e['rate'])
    place(x, e['t'], e['gain'] * rng.uniform(0.88, 1.0), e.get('pan', 0.0) + rng.uniform(-0.1, 0.1))

# ------------------------------------------------------------------ beds from control curves
def curve(name, smooth=0.05):
    c = np.asarray(EV['curves'][name], np.float32); ft = np.arange(len(c)) / FPS
    y = np.interp(T, ft, c).astype(np.float32)
    k = int(smooth * SR); return np.convolve(y, np.ones(k) / k, mode='same').astype(np.float32)
ch, crt, crl, cm, crm = curve('hum'), curve('rate', 0.08), curve('roll'), curve('music', 0.25), curve('room')
fm = 330 * crt
hum = tone(fm, N, 'saw') * 0.25 + tone(fm * 2.0, N) * 0.25 + tone(fm * 3.0 * 1.003, N) * 0.12 + tone(fm * 0.5, N) * 0.2
hum = fftf(hum, 90, 2400) * (0.8 + 0.2 * fftf(noise(N), None, 8)) * ch
roll = fftf(noise(N), 45, 380) * (0.75 + 0.25 * np.sin(2 * np.pi * 1.43 * T)) * 2.2 + fftf(noise(N), 400, 1500) * 0.25
roll = roll * crl
room = fftf(noise(N), 60, 4000) * 0.05 * crm
amb = hum * 0.22 + roll * 0.35 + room

# ------------------------------------------------------------------ score: original, gentle, curious (88 bpm, D major)
bpm = 88; q_ = 60 / bpm; bar = 4 * q_
def ep(fr, n, bright=1.0):           # electric-piano-ish tine: sine + soft FM bell, slow decay
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * fr * 14 * t) * 0.9 * np.exp(-t / 0.15) * bright
    return (np.sin(2 * np.pi * fr * t + mod) * np.exp(-t / 1.6) + 0.15 * np.sin(2 * np.pi * fr * 2 * t) * np.exp(-t / 0.5)).astype(np.float32)
def pluck(fr, n):                    # soft marimba-like pluck
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * fr * t) * np.exp(-t / 0.28) + 0.3 * np.sin(2 * np.pi * fr * 3.98 * t) * np.exp(-t / 0.05)).astype(np.float32)
CH = [(146.8, (293.7, 370.0, 440.0, 659.3)), (123.5, (293.7, 370.0, 440.0, 554.4)),
      (98.0, (246.9, 293.7, 370.0, 493.9)), (110.0, (277.2, 329.6, 440.0, 493.9))]
ARP = [(587.3, 740.0, 880.0, 740.0), (554.4, 740.0, 880.0, 1108.7), (493.9, 587.3, 740.0, 987.8), (493.9, 659.3, 880.0, 740.0)]
music = np.zeros(N + SR * 3, np.float32); perc = np.zeros_like(music)
t_in = 0.0; nb = int(DUR / bar) + 2
for k in range(nb):
    s0 = int((t_in + k * bar) * SR); bass, chord = CH[k % 4]
    m = int(bar * 1.6 * SR)
    if s0 >= N: break
    seg = ep(bass, m, 0.6) * 0.5 + sum(ep(f, m, 0.8) for f in chord) * 0.22
    music[s0:s0 + m] += seg[:len(music) - s0]
    for j in range(8):                                                    # eighth-note arpeggio
        p0 = s0 + int(j * q_ / 2 * SR); pm = int(0.7 * SR)
        if p0 + pm > len(music): break
        fr = ARP[k % 4][j % 4] * (2 if j >= 4 and k % 2 else 1)
        music[p0:p0 + pm] += pluck(fr, pm) * (0.16 if j % 2 == 0 else 0.11)
    for j in range(4):                                                    # the ceramic tick on the beats
        p0 = s0 + int(j * q_ * SR); pm = int(0.3 * SR)
        if p0 + pm > len(perc): break
        tt = np.arange(pm) / SR
        perc[p0:p0 + pm] += (np.sin(2 * np.pi * 3180 * tt) * np.exp(-tt / 0.03) * (0.22 if j % 2 else 0.12)).astype(np.float32)
music = reverb(music[:N], 2.2, 0.32)[:N] + reverb(perc[:N], 1.0, 0.25)[:N]
music = fftf(music, 70, 9000)
music *= np.clip(cm, 0, 1)
music *= np.minimum(1, T / 0.35)

# ------------------------------------------------------------------ voice, ducking, master
voice = read_wav(a.voice); voice = voice / (np.abs(voice).max() + 1e-9) * 0.9
vo = np.zeros(N, np.float32); vo[:min(N, len(voice))] = voice[:N]
k = int(0.15 * SR); venv = np.sqrt(np.convolve(vo ** 2, np.ones(k) / k, mode='same'))
vact = np.clip(venv / 0.08, 0, 1)
duck = 1 - 0.5 * vact
bed = (norm(amb, 0.5) * 0.55 + norm(music, 0.5) * 0.62) * duck
sfx_l = L[:N] * (1 - 0.35 * vact); sfx_r = Rc[:N] * (1 - 0.35 * vact)
mixL = vo + bed * 0.55 + sfx_l * 0.30
mixR = vo + bed * 0.55 + sfx_r * 0.30
st = np.stack([mixL, mixR], 1)
st = np.tanh(st * 1.1) / np.tanh(1.1)
st = st / (np.abs(st).max() + 1e-9) * 0.84
n_f = int(0.04 * SR); st[-n_f:] *= np.linspace(1, 0, n_f)[:, None]        # no fade-out: the reel loops
o = wave.open(a.out, 'wb'); o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR)
o.writeframes((st * 32767).astype(np.int16).tobytes()); o.close()
print(a.out, f'{N / SR:.2f}s')
