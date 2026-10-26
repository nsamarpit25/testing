"""pad.py <take.wav> <take.words.json> <out.wav> <out.words.json>: build the narration from a TTS take without touching speech.
Cuts the take at the end of its last word (Gemini adds a noise burst after it), adds LEAD s of room tone before the first
word, and lengthens chosen sentence pauses to TARGET s by inserting silence at the quietest point of the gap.
Word timestamps are shifted to match."""
import sys, json, wave, numpy as np
src, wsrc, dst, wdst = sys.argv[1:5]
LEAD = 0.05
TARGET = {'bumpy?': 0.60, 'over.': 0.70, 'road.': 0.72, 'rolls.': 0.50, 'smoothing.': 0.75, 'catenary.': 0.50, 'circles.': 0.42}
w = wave.open(src); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
W = json.load(open(wsrc))
end = int((W[-1]['e'] + 0.12) * sr); x = x[:end].copy(); n = int(0.08 * sr); x[-n:] *= np.linspace(1, 0, n) ** 2
ins = []                                                     # (sample position, seconds inserted)
seen = set()
for i in range(len(W) - 1):
    key = W[i]['w']
    if key in TARGET:
        if key == 'road.' and 'road.' in seen: continue      # only the first "road." ("Now change the road.")
        seen.add(key)
        g0, g1 = W[i]['e'], W[i + 1]['s']; gap = g1 - g0; add = TARGET[key] - gap
        if add <= 0.01: continue
        a, b = int((g0 + 0.04) * sr), int((g1 - 0.04) * sr); hop = int(0.01 * sr)
        e = [np.sqrt(np.mean(x[j:j + hop] ** 2)) for j in range(a, max(a + hop, b - hop), hop)]
        p = a + int(np.argmin(e)) * hop + hop // 2
        print(f"{key:12s} gap {gap:.2f} -> {TARGET[key]:.2f} (+{add:.2f}) at {p / sr:.2f}s, floor {20 * np.log10(min(e) + 1e-9):.0f} dB")
        ins.append((p, add, i))
out = [np.zeros(int(LEAD * sr), np.float32)]; pos = 0
for p, add, _ in ins:
    out += [x[pos:p], np.zeros(int(add * sr), np.float32)]; pos = p
out.append(x[pos:]); y = np.concatenate(out)
shift = LEAD; k = 0; NW = []
for i, wd in enumerate(W):
    while k < len(ins) and ins[k][2] < i: shift += ins[k][1]; k += 1
    NW.append(dict(wd, s=round(wd['s'] + shift, 3), e=round(wd['e'] + shift, 3)))
o = wave.open(dst, 'wb'); o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()); o.close()
json.dump(NW, open(wdst, 'w'))
sp = NW[-1]['e'] - NW[0]['s']
print(f"{dst}: {len(y) / sr:.2f}s, words {NW[0]['s']:.2f}..{NW[-1]['e']:.2f}, {len(NW) / sp * 60:.0f} wpm")
