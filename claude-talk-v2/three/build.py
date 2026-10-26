"""Lay the voice lines on a timeline: trim silence, keep the first N phrases, tighten pauses, then write
<dir>/voice.wav and <dir>/timeline.js (window.TIMELINE: line/phrase times + per-frame mouth levels for each speaker).
python3 three/build.py three/ep_test
"""
import json, re, sys, wave
import numpy as np
d = sys.argv[1]
E = json.load(open(f"{d}/lines.json"))
SR, FPS, LEAD, GAP, MAXPAUSE = 24000, 30, 0.2, 0.28, 0.22


def load(i):
    w = wave.open(f"{d}/l{i + 1:02d}.wav")
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def phrases(x):
    """Voiced runs split at pauses >= 0.1 s, as (start, end) sample pairs."""
    hop = SR // 100
    loud = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) > 0.01 for i in range(0, len(x), hop)])
    runs, start, quiet = [], None, 0
    for k, v in enumerate(loud):
        if v:
            if start is None: start = k
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet >= 10: runs.append((start, k - quiet + 1)); start, quiet = None, 0
    if start is not None: runs.append((start, len(loud) - quiet))
    return [(a * hop, min(len(x), b * hop + hop)) for a, b in runs]


out, lines, t = [np.zeros(int(LEAD * SR), np.float32)], [], LEAD
for i, L in enumerate(E["lines"]):
    x, runs = load(i), phrases(load(i))
    texts = re.split(r"(?<=[.,?!])\s+", L["say"])
    while len(runs) > len(texts):  # merge across the shortest pause until there is one run per caption chunk
        k = min(range(1, len(runs)), key=lambda k: runs[k][0] - runs[k - 1][1])
        runs[k - 1:k + 1] = [(runs[k - 1][0], runs[k][1])]
    runs, texts = runs[: L.get("phrases", 99)], texts[: L.get("phrases", 99)]
    segs, ph = [], []
    for k, (a, b) in enumerate(runs):
        if k: segs.append(np.zeros(int(min(MAXPAUSE, (a - runs[k - 1][1]) / SR) * SR), np.float32))
        st = t + sum(len(s) for s in segs) / SR
        segs.append(x[a:b])
        ph.append([round(st, 3), round(st + (b - a) / SR, 3)])
    clip = np.concatenate(segs)
    # one caption chunk per phrase when the counts match, else the whole line
    caps = [[*ph[k], texts[k]] for k in range(len(ph))] if len(texts) == len(ph) else [[ph[0][0], ph[-1][1], L["say"]]]
    lines.append({**L, "start": round(t, 3), "end": round(t + len(clip) / SR, 3), "caps": caps})
    out.append(clip); t += len(clip) / SR
    if i < len(E["lines"]) - 1: out.append(np.zeros(int(GAP * SR), np.float32)); t += GAP
tail = E.get("tail", {}); hold = tail.get("hold", 0.8)
out.append(np.zeros(int(hold * SR), np.float32))
voice = np.concatenate(out); dur = len(voice) / SR

# mouth level per frame per speaker: RMS in a 1/30 s window, normalised to the line's 90th percentile
n = int(np.ceil(dur * FPS)); mouth = {w: [0.0] * n for w in ("Cleo", "Claude")}
for L in lines:
    for f in range(int(L["start"] * FPS), min(n, int(np.ceil(L["end"] * FPS)))):
        a = int(f / FPS * SR); mouth[L["who"]][f] = float(np.sqrt(np.mean(voice[a:a + SR // FPS] ** 2)))
for w, m in mouth.items():
    m = np.array(m); ref = np.percentile(m[m > 0], 90) if (m > 0).any() else 1
    m = np.clip(m / ref, 0, 1); m = np.convolve(m, [0.25, 0.5, 0.25], "same")
    mouth[w] = [round(float(v), 2) for v in m]

w = wave.open(f"{d}/voice.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(voice, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
T = {"duration": round(dur, 3), "lines": lines, "tail": tail, "mouth": mouth}
open(f"{d}/timeline.js", "w").write("window.TIMELINE = " + json.dumps(T) + ";\n")
for L in lines: print(f'{L["start"]:6.2f}-{L["end"]:6.2f} {L["who"]:6} {[c[2] for c in L["caps"]]}')
print("duration", round(dur, 2))
