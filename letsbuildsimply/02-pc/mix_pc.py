"""mix.py <anchors.json> <voice.wav> <out.wav>: voice + plucky music bed (ducked) + sound effects on the scene's key times.
No samples except the CC0 Kenney impacts in assets/sfx; everything else is synthesized here (numpy only)."""
import json, subprocess, sys
import numpy as np

SR = 48000
A = json.load(open(sys.argv[1])); T = A['T']; FR = A['frames']
SFX = '/Users/samarpit/insta-automation/letsbuildsimply/assets/sfx/'
rng = np.random.default_rng(3)

def load(path, mono=True):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1' if mono else '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)
voice = load(sys.argv[2])
DUR = max(len(voice) / SR, FR[-1]['t']) + 1.2
N = int(DUR * SR); t_all = np.arange(N) / SR
out_v = np.zeros(N); out_v[:len(voice)] = voice
bus_m = np.zeros(N); bus_s = np.zeros(N)

def db(x): return 10 ** (x / 20)
def put(bus, sig, at, gain_db=0.0):
    i = int(at * SR)
    if i >= N or i + len(sig) <= 0: return
    j = min(N, i + len(sig)); s0 = max(0, -i)
    bus[max(i, 0):j] += sig[s0:s0 + j - max(i, 0)] * db(gain_db)
def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
def env(n, a, r):  # attack/release in seconds over n samples
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e
def noise(d): return rng.standard_normal(int(d * SR))
def hiss(d, lo=2000, hi=9000, a=0.05, r=0.3): return bandpass(noise(d), lo, hi) * env(int(d * SR), a, r)
def whoosh(d=0.6, lo=300, hi=3500):
    x = noise(d); n = len(x); out = np.zeros(n); k = 8
    for i in range(k):  # sweeping band, crossfaded slices
        seg = bandpass(x, lo * (1 + i * 0.5), hi * (1 + i * 0.3)); w = np.zeros(n)
        c = int(n * (i + 0.5) / k); half = n // k
        w[max(0, c - half):min(n, c + half)] = np.hanning(min(n, c + half) - max(0, c - half))
        out += seg * w
    return out / (np.abs(out).max() + 1e-9) * 0.6
def chirp(f0, f1, d, decay=30.0):
    tt = np.arange(int(d * SR)) / SR; f = f0 * (f1 / f0) ** (tt / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * decay)
def drip(): return chirp(1800, 700, 0.07, 45) * 0.5
def popp(): return chirp(900, 260, 0.09, 30) * 0.7
def sizzle(d):
    x = bandpass(noise(d), 3000, 12000); crack = (rng.random(len(x)) < 0.004) * rng.uniform(1, 4, len(x))
    return x * (0.25 + crack) * env(len(x), 0.05, 0.2) * 0.35
def bubbles(d, rate=14):
    x = np.zeros(int(d * SR))
    for at in np.sort(rng.uniform(0, d - 0.08, int(d * rate))):
        b = chirp(rng.uniform(350, 900), rng.uniform(900, 1600), 0.05, 60) * 0.25; i = int(at * SR); x[i:i + len(b)] += b
    return x
def riser(d):
    tt = np.arange(int(d * SR)) / SR; f = 200 * (4 ** (tt / d))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 + bandpass(noise(d), 800, 6000) * 0.25) * (tt / d) ** 2
def kenney(name, rate=1.0):
    x = load(SFX + name + '.wav')
    if rate != 1.0: x = np.interp(np.arange(0, len(x), rate), np.arange(len(x)), x)
    return x

# ---------------------------------------------------------------- sound effects 
# ---------------------------------------------------------------- sound effects (ep 02 beats)
END = FR[-1]['t'] - 1.0
LS = [l['s'] for l in json.load(open('voice/timings.json'))['lines']]
def beep(f=2400, d=0.07): return chirp(f, f, d, 25) * 0.4
def whir(d, f0=90):  # fan noise: low band noise with a blade tone
    tt = np.arange(int(d * SR)) / SR
    return (bandpass(noise(d), 150, 1500) * 0.5 + np.sin(2 * np.pi * f0 * tt) * 0.2) * env(len(tt), 0.4, 0.4)
fx = []
for k, at in enumerate((0.2, 0.45, 0.7, 1.0)): fx.append((beep(2200 + 200 * k), at, -12))
for k in range(3): fx.append((beep(2600), LS[1] + 0.9 + k * 0.18, -14))
fx += [(whoosh(0.8, 300, 4000), T['pack'], -12), (riser(1.4), T['billions'] - 0.3, -16), (kenney('confirmation_001'), T['cpu'], -14)]
fx += [(whoosh(0.5, 200, 2500), T['plug'] - 0.2, -14), (kenney('impactPlate_medium_001'), T['plug'] + 0.2, -8), (kenney('glass_003', 1.4), T['copper'], -16),
       (kenney('confirmation_001'), T['mobo'], -14)]
for k in range(6): fx.append((kenney('tick_002', 0.8), LS[4] + 0.2 + k * 0.4, -16))
fx += [(kenney('click_002'), T['desk'] + 0.15, -6), (kenney('click_003'), T['desk'] + 0.3, -6), (kenney('confirmation_001'), T['ram'], -14)]
fx += [(chirp(900, 120, 0.6, 4), T['off'], -8), (whoosh(0.5, 800, 6000), T['off'] + 0.1, -16)]
fx += [(kenney('switch_002'), T['drive'] + 0.5, -8), (kenney('confirmation_001'), T['ssd'], -14)]
fx += [(kenney('impactSoft_heavy_000', 1.4), T['egg'] - 0.05, -8), (kenney('impactGlass_light_002', 1.6), T['egg'] - 0.04, -14), (sizzle(2.6), T['egg'], -9)]
fx += [(kenney('impactMetal_heavy_002', 1.1), T['bolt'] + 0.25, -7), (whir(3.0), T['fan'], -14), (kenney('confirmation_001'), T['cooler'], -14)]
for k in range(8): fx.append((kenney('tick_001', 0.7), LS[10] + 0.3 + k * 0.45, -15))
fx += [(kenney('impactMetal_medium_001'), T['card'] + 0.3, -7), (whir(3.5, 70), T['gpu'] - 0.2, -14), (riser(1.0), T['cores'] - 0.4, -16),
       (kenney('confirmation_002'), T['gpu'], -12)]
for k in range(6): fx.append((bandpass(noise(0.08), 80, 400) * 0.6, T['flicker'] - 0.2 + k * 0.22, -10))
fx += [(kenney('impactMetal_heavy_000'), T['box'] + 0.25, -7), (kenney('switch_001'), T['psu'] - 0.3, -8), (kenney('confirmation_001'), T['psu'], -14)]
fx += [(whoosh(0.6, 200, 2500), T['glass'], -12), (kenney('impactGlass_heavy_002', 0.9), T['glass'] + 0.35, -7),
       (kenney('confirmation_002'), T['rainbow'], -12), (kenney('confirmation_002', 0.9), T['congrats2'], -10)]
fx += [(popp(), T['mine'], -8), (kenney('pluck_002', 1.2), T['mine'] + 0.15, -12)]
for sig, at, g in fx: put(bus_s, sig, at, g)
# ---------------------------------------------------------------- music: light plucky arpeggio bed, 100 bpm
BPM = 100; beat = 60 / BPM
def pluck(f, d=0.6, bright=1.0):
    tt = np.arange(int(d * SR)) / SR; x = np.zeros_like(tt)
    for h in range(1, 7):
        x += np.sin(2 * np.pi * f * h * tt + h) / h ** (1.6 - 0.4 * bright) * np.exp(-tt * (5 + 3 * h))
    return x * np.minimum(1, tt / 0.004)
def nf(m): return 440 * 2 ** ((m - 69) / 12)
chords = [(60, 64, 67, 72), (57, 60, 64, 69), (53, 57, 60, 65), (55, 59, 62, 67)]  # C Am F G
pat = [0, 2, 1, 3, 2, 1, 3, 2]
end_music = END + 0.6
bar = 0; tb = 0.0
while tb < end_music:
    ch = chords[bar % 4]
    for i in range(8):
        at = tb + i * beat / 2
        if at > end_music: break
        put(bus_m, pluck(nf(ch[pat[i]] + 12), 0.5), at, -4 + (-3 if i % 2 else 0))
    put(bus_m, pluck(nf(ch[0] - 12), 1.6, 0.4), tb, 0)
    put(bus_m, pluck(nf(ch[0] - 12), 0.8, 0.4), tb + 2 * beat, -4)
    for i in range(8):  # shaker
        s = bandpass(noise(0.05), 5000, 12000) * env(int(0.05 * SR), 0.003, 0.04)
        put(bus_m, s, tb + i * beat / 2 + beat / 4, -22 if i % 2 else -26)
    tb += 4 * beat; bar += 1
# last chord rings out
for m in chords[0]: put(bus_m, pluck(nf(m + 12), 2.0), end_music, -6)

# duck music under the voice
vk = int(0.12 * SR); venv = np.sqrt(np.convolve(out_v ** 2, np.ones(vk) / vk, mode='same'))
duck = 1 - 0.55 * np.clip(venv / (venv.max() * 0.25), 0, 1)
k = int(0.15 * SR); duck = np.convolve(duck, np.ones(k) / k, mode='same')
dim = 1 - 0.85 * ((t_all > T['off'] + 0.05) & (t_all < T['off'] + 0.6))
music = bus_m / (np.abs(bus_m).max() + 1e-9) * db(-21) * duck * dim

v = out_v / (np.abs(out_v).max() + 1e-9) * db(-3)
bus_s = np.tanh(bus_s / (np.percentile(np.abs(bus_s), 99.9) + 1e-9))
s = bus_s / (np.abs(bus_s).max() + 1e-9) * db(-9)
mixd = v + music + s
fade = np.ones(N); fn = int(0.4 * SR); fade[-fn:] = np.linspace(1, 0, fn)
mixd *= fade
st = np.stack([mixd, mixd], 1).astype(np.float32)
p = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', str(SR), sys.argv[3]], input=st.tobytes(), check=True)
print('wrote', sys.argv[3], f'{N / SR:.1f}s')
