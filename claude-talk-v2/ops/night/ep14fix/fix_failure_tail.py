"""Ep14 audio fix (22 Oct): l08/l09 were cut from take1 at 27.34 s while Claude was still saying "failure", so the word stopped
dead and its last 0.15 s played again at the start of Cleo's line 9 (heard as a stutter before "So"). This moves that tail back
onto the end of line 8 in mix.wav only, so no timing or picture changes:  python3 ops/night/ep14fix/fix_failure_tail.py
"""
import json, wave
import numpy as np

D = "audio/ep14"
TAIL = 0.15  # seconds of "failure" at the head of l09.wav


def rd(f):
    w = wave.open(f)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, w.getnchannels()), w.getframerate()


mix, sr = rd(f"{D}/mix.wav")
l8, s8 = rd(f"{D}/l08.wav"); l9, s9 = rd(f"{D}/l09.wav")
assert s8 == s9 == sr
L = {x["n"]: x for x in json.load(open(f"{D}/timeline.json"))["lines"]}
a8, a9 = int(round(L[8]["t0"] * sr)), int(round(L[9]["t0"] * sr))
# the voice's gain in the mix (least squares over line 8)
seg = mix[a8:a8 + len(l8), 0]; v = l8[:, 0]
g = float(seg @ v / (v @ v))
n = int(TAIL * sr)
tail = l9[:n, 0] * np.linspace(1, 0, n) ** 2  # fade the tail out so the word ends softly
for c in range(mix.shape[1]):
    mix[a9:a9 + n, c] = 0  # take it off the start of line 9 (nothing else plays there)
    mix[a9 + n:a9 + n + sr // 100, c] *= np.linspace(0, 1, sr // 100)
    mix[a8 + len(l8):a8 + len(l8) + n, c] += g * tail             # and put it after line 8's last sample
print(f"gain {g:.3f}; moved {TAIL}s from {a9 / sr:.2f}s to {(a8 + len(l8)) / sr:.2f}s")
w = wave.open(f"{D}/mix.wav", "w"); w.setnchannels(mix.shape[1]); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((np.clip(mix, -1, 1) * 32767).round().astype(np.int16).tobytes()); w.close()
