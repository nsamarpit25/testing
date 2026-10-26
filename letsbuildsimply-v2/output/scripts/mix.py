"""mix.py: narration + sound effects + a light procedural music bed -> 48 kHz stereo WAV.

  python3 mix.py --voice narration.wav --events events.json --sfx SFX_DIR --out mix.wav

Cue names come from scene.py's events.json. Names that match a Kenney CC0 file in SFX_DIR are played from it;
the rest (whoosh, snap, creak, rumble, capstan clicks, phone buzz...) are synthesised here with numpy.
A 'name:seconds' cue is a loop of that length.
"""
import argparse, json, os, wave
import numpy as np

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument('--voice', required=True); ap.add_argument('--events', required=True)
ap.add_argument('--sfx', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
EV = json.load(open(a.events)); B = EV['beats']; DUR = EV['dur']
N = int(DUR * SR) + SR
rng = np.random.default_rng(3)

def read_wav(p):
    w = wave.open(p); sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32) / (2 ** (8 * sw - 1))
    x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) / SR * sr, np.arange(len(x)), x).astype(np.float32)
    return x
def resample(x, rate):
    if abs(rate - 1) < 1e-3: return x
    n = int(len(x) / rate); return np.interp(np.arange(n) * rate, np.arange(len(x)), x).astype(np.float32)
def env(n, att=0.005, rel=None):
    t = np.arange(n) / SR; e = np.minimum(1, t / max(att, 1e-4))
    if rel: e *= np.exp(-t / rel)
    return e
def lp(x, a_):   # one-pole low-pass, a_ in (0,1): smaller = darker
    y = np.empty_like(x); acc = 0.0
    # vectorised via cumulative filter on blocks is overkill here; signals are short
    for i in range(len(x)): acc += a_ * (x[i] - acc); y[i] = acc
    return y
def lp_fast(x, cutoff):
    """FFT brick-ish low-pass (cosine roll-off) for long noise beds."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= np.clip((cutoff * 1.5 - f) / (cutoff * 0.5), 0, 1); return np.fft.irfft(X, len(x)).astype(np.float32)
def bp_fast(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= ((f > lo) & (f < hi)); return np.fft.irfft(X, len(x)).astype(np.float32)
def noise(n): return rng.standard_normal(n).astype(np.float32)
def tone(freq, n, kind='sin'):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, (n,)) / SR)
    if kind == 'sin': return np.sin(ph).astype(np.float32)
    if kind == 'saw': return (2 * ((ph / (2 * np.pi)) % 1) - 1).astype(np.float32)
    if kind == 'sq': return np.sign(np.sin(ph)).astype(np.float32)
def norm(x, peak=0.9): m = np.abs(x).max() + 1e-9; return (x / m * peak).astype(np.float32)

def s_whoosh(d=0.45, lo=False):
    n = int(d * SR); x = noise(n); t = np.linspace(0, 1, n)
    c = (300 + 2500 * np.sin(np.pi * t) ** 2) if not lo else (120 + 700 * np.sin(np.pi * t) ** 2)
    y = np.zeros(n, np.float32); acc = 0.0; aa = 1 - np.exp(-2 * np.pi * c / SR)
    for i in range(n): acc += aa[i] * (x[i] - acc); y[i] = acc
    return norm(y * np.sin(np.pi * t) ** 1.5, 0.8)
def s_snap():
    n = int(0.5 * SR); t = np.arange(n) / SR
    crack = noise(n) * np.exp(-t / 0.012); click = tone(2800, n) * np.exp(-t / 0.004)
    thump = tone(90 * np.exp(-t * 6), n) * np.exp(-t / 0.08); whip = bp_fast(noise(n), 1500, 7000) * np.exp(-t / 0.05) * 0.6
    return norm(crack + 0.6 * click + 0.8 * thump + whip, 0.95)
def s_creak(d):
    n = int(d * SR); t = np.arange(n) / SR
    f = 95 + 40 * np.sin(2 * np.pi * 0.7 * t) + 25 * np.sin(2 * np.pi * 2.3 * t)
    pulses = tone(f, n, 'saw') * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t) ** 8)
    y = bp_fast(pulses, 200, 2500) * np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.1)
    rise = 0.4 + 0.6 * t / d
    return norm(y * rise, 0.7)
def s_rumble(d):
    n = int(d * SR); t = np.arange(n) / SR
    y = lp_fast(noise(n), 90) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7
    return norm(y, 0.9)
def s_scrape(d):
    n = int(d * SR); t = np.arange(n) / SR
    y = bp_fast(noise(n), 300, 2200) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 2.6 * t))) * np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.1)
    return norm(y, 0.5)
def s_zoom():
    n = int(0.5 * SR); t = np.arange(n) / SR
    return norm(tone(300 + 1400 * (t / 0.5) ** 1.6 + 30 * np.sin(2 * np.pi * 18 * t), n) * np.minimum(1, t / 0.02) * (1 - t / 0.5) ** 0.3, 0.45)
def s_horn():   # sad "wah wah wahhh"
    out = []
    for f0, d in ((311, 0.32), (294, 0.32), (277, 0.7)):
        n = int(d * SR); t = np.arange(n) / SR
        f = f0 * (1 + 0.012 * np.sin(2 * np.pi * 6 * t)) * (1 - (0.06 * t / d if d > 0.5 else 0))
        x = tone(f, n, 'saw') * np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.06)
        out.append(lp_fast(x, 1400))
    return norm(np.concatenate(out), 0.6)
def s_tweety():
    n = int(1.0 * SR); y = np.zeros(n, np.float32)
    for k in range(5):
        s0 = int((0.05 + 0.18 * k) * SR); m = int(0.09 * SR); t = np.arange(m) / SR
        y[s0:s0 + m] += tone(2600 + 900 * np.sin(np.pi * t / 0.09), m) * np.sin(np.pi * t / 0.09)
    return norm(y, 0.4)
def s_ding(f):
    n = int(0.8 * SR); t = np.arange(n) / SR
    return norm((tone(f, n) + 0.4 * tone(f * 2.76, n) * np.exp(-t / 0.08)) * np.exp(-t / 0.35) * np.minimum(1, t / 0.003), 0.5)
def s_pop():
    n = int(0.12 * SR); t = np.arange(n) / SR
    return norm(tone(900 * np.exp(-t * 18) + 200, n) * np.exp(-t / 0.04), 0.6)
def s_buzzer():
    n = int(0.35 * SR); t = np.arange(n) / SR
    return norm(lp_fast(tone(110, n, 'sq'), 1800) * np.minimum(1, t / 0.01) * np.minimum(1, (0.35 - t) / 0.03), 0.35)
def s_scratch():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 600 + 1800 * np.abs(np.sin(2 * np.pi * 2.2 * t))
    return norm(bp_fast(noise(n), 400, 3000) * tone(f, n) * np.exp(-t / 0.25), 0.5)
def s_speedup():
    n = int(0.7 * SR); t = np.arange(n) / SR
    return norm(tone(200 * 2 ** (t / 0.7 * 2.5), n, 'saw') * np.minimum(1, t / 0.05) * (1 - t / 0.7) * 0.6, 0.35)
def s_buzz():
    n = int(0.9 * SR); t = np.arange(n) / SR
    gate = ((t % 0.3) < 0.2).astype(np.float32)
    return norm(lp_fast(tone(165, n, 'sq'), 600) * gate, 0.5)
def s_msg():
    n1 = int(0.09 * SR); t = np.arange(n1) / SR
    a1 = tone(1320, n1) * np.exp(-t / 0.05); a2 = tone(1760, n1) * np.exp(-t / 0.08)
    return norm(np.concatenate([a1, np.zeros(int(0.03 * SR), np.float32), a2]), 0.5)
def s_whomp():
    n = int(0.45 * SR); t = np.arange(n) / SR
    return norm(tone(140 * np.exp(-t * 5), n) * np.exp(-t / 0.15), 0.8)
def s_rope_tie():
    w = s_whoosh(0.3); n = int(0.25 * SR); t = np.arange(n) / SR
    return np.concatenate([w * 0.6, norm(tone(180, n, 'saw') * np.exp(-t / 0.05), 0.3)])
def s_roll_in():
    n = int(0.38 * SR); t = np.arange(n) / SR
    return norm(lp_fast(noise(n), 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * t)) * np.sin(np.pi * t / 0.38), 0.6)
def s_capstan(d, clicks):
    """ratchet clicks at a rate that follows the capstan speed + a rolling rumble that grows in the time-lapse."""
    n = int(d * SR); y = np.zeros(n, np.float32); t0 = 0.0
    tl = B['forty'] + 0.75 - (EV_T['capstan'])
    t = 0.0
    while t < d:
        rate = 2.2 if t < tl else 2.2 + 12 * min(1, (t - tl) / 0.8)
        if t > d - 1.0: rate = max(2.0, rate * (d - t))
        s0 = int(t * SR); c = clicks[int(t * 7) % len(clicks)]
        e = min(n, s0 + len(c)); y[s0:e] += c[:e - s0] * 0.7; t += 1 / rate
    tt = np.arange(n) / SR
    r = lp_fast(noise(n), 160) * np.clip((tt - tl) / 0.8, 0.05, 1) * np.minimum(1, (d - tt) / 0.8)
    return y + norm(r, 0.5)

SFX = {}
def kenney(name):
    if name not in SFX:
        p = os.path.join(a.sfx, name + '.wav'); SFX[name] = read_wav(p) if os.path.exists(p) else None
    return SFX[name]
EV_T = {}
for e in EV['events']:
    EV_T.setdefault(e['s'].split(':')[0], e['t'])
CLICKS = [norm(kenney(n), 0.6) for n in ('click_001', 'click_002', 'click_003', 'tick_001', 'tick_002') if kenney(n) is not None]
def cue(name):
    base, _, arg = name.partition(':'); d = float(arg) if arg else None
    k = kenney(base)
    if k is not None: return k
    return dict(whoosh=lambda: s_whoosh(), whoosh_low=lambda: s_whoosh(0.7, True), snap=s_snap, zoom=s_zoom, sad_horn=s_horn,
                tweety=s_tweety, ding_low=lambda: s_ding(660), ding_high=lambda: s_ding(990), pop=s_pop, buzzer=s_buzzer,
                record_scratch=s_scratch, speedup=s_speedup, buzz=s_buzz, msg=s_msg, whomp=s_whomp, rope_tie=s_rope_tie,
                roll_in=s_roll_in, creak_short=lambda: s_creak(0.6), creak_loop=lambda: s_creak(d), rumble=lambda: s_rumble(d),
                scrape_loop=lambda: s_scrape(d), capstan=lambda: s_capstan(d, CLICKS))[base]()

L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
def add(x, t, g, pan=0.0):
    s0 = int(t * SR); e = min(N, s0 + len(x))
    if e <= s0: return
    L[s0:e] += x[:e - s0] * g * (1 - max(0, pan)); R[s0:e] += x[:e - s0] * g * (1 + min(0, pan))
for e in EV['events']:
    x = cue(e['s'])
    x = resample(x, e.get('r', 1.0))
    add(x, e['t'], 0.55 * e['g'], pan=float(rng.uniform(-0.25, 0.25)))

# ------------------------------------------------------------------ music bed: plucky, light, 112 bpm (stops for the punchline)
BPM = 112; beat = 60 / BPM
def pluck(f, d=0.9):
    n = int(d * SR); t = np.arange(n) / SR; y = np.zeros(n, np.float32)
    for h in range(1, 7): y += (1 / h) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (2.5 + 2.2 * h))
    return y * np.minimum(1, t / 0.004)
def bass(f, d):
    n = int(d * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 3) * np.minimum(1, t / 0.01)
NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)
CHORDS = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]     # C G Am F
mus = np.zeros(N, np.float32); M_END = B['client'] - 0.65
t = 0.15; step = 0
while t < M_END:
    ch = CHORDS[(step // 8) % 4]
    patt = [0, 2, 1, 2, 0, 2, 1, 2]
    m = ch[patt[step % 8]] + 12
    x = pluck(NOTE(m), 0.8) * (0.5 if step % 2 else 0.7)
    s0 = int(t * SR); e = min(N, s0 + len(x)); mus[s0:e] += x[:e - s0]
    if step % 4 == 0:
        bb = bass(NOTE(ch[0] - 24), beat * 2); e = min(N, s0 + len(bb)); mus[s0:e] += 0.9 * bb[:e - s0]
    if step % 2 == 1:
        hh = bp_fast(noise(int(0.05 * SR)), 6000, 12000) * np.exp(-np.arange(int(0.05 * SR)) / SR / 0.012)
        e = min(N, s0 + len(hh)); mus[s0:e] += 0.25 * hh[:e - s0]
    t += beat / 2; step += 1
# button chord on "zero cranes"
for m in (60, 64, 67, 72):
    x = pluck(NOTE(m), 1.6); s0 = int(B['zero'] * SR); mus[s0:s0 + len(x)] += 0.6 * x[:max(0, N - s0)][:len(x)]
fade_end = int(M_END * SR); mus[fade_end:fade_end + int(0.25 * SR)] *= np.linspace(1, 0, int(0.25 * SR)); mus[fade_end + int(0.25 * SR):] = 0

# ------------------------------------------------------------------ voice + ducking
v = read_wav(a.voice); v = v / (np.sqrt(np.mean(v[np.abs(v) > 0.01] ** 2)) + 1e-9) * 0.16
vv = np.zeros(N, np.float32); vv[:min(N, len(v))] = v[:N]
envv = np.convolve(np.abs(vv), np.ones(int(0.12 * SR)) / int(0.12 * SR), 'same')
duck = 1 - 0.55 * np.clip(envv / 0.05, 0, 1)
mus = norm(mus, 1.0) * 0.12 * duck
L += vv + mus; R += vv + mus
st = np.stack([L, R], 1)[:int(DUR * SR)]
st = np.tanh(st * 1.1) / np.tanh(1.1)
st = st / max(1.0, np.abs(st).max() / 0.95)
w = wave.open(a.out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
print('mix', a.out, f'{len(st) / SR:.2f}s', 'peak', float(np.abs(st).max()))
