"""tighten.py <in.wav> <out.wav> [--cut END_S]: shorten long pauses in a TTS take (cuts land inside true silence only).
Pauses over 0.40 s become 0.36 s; pauses marked dramatic (by start time) keep 0.55 s. Ends at --cut with a 60 ms fade."""
import sys, wave, numpy as np
src, dst = sys.argv[1], sys.argv[2]
cut = float(sys.argv[sys.argv.index('--cut') + 1]) if '--cut' in sys.argv else None
KEEP = [float(x) for x in sys.argv[sys.argv.index('--keep') + 1].split(',')] if '--keep' in sys.argv else []
w = wave.open(src); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
if cut: x = x[:int(cut * sr)]; n = int(0.06 * sr); x[-n:] *= np.linspace(1, 0, n) ** 2
hop = int(0.01 * sr); e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
quiet = 20 * np.log10(e + 1e-9) < -50
segs = []; i = 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]: j += 1
        segs.append((i * hop, j * hop)); i = j
    else: i += 1
out = []; pos = 0; removed = 0
for a, b in segs:
    d = (b - a) / sr
    if a == 0 or d <= 0.40: continue
    tgt = 0.55 if any(abs(a / sr - k) < 0.6 for k in KEEP) else 0.36
    tgt = min(tgt, d); keep = int(tgt * sr); mid = a + keep // 2
    out.append(x[pos:mid]); pos = b - (keep - keep // 2); removed += (b - a - keep) / sr
    print(f'pause {a / sr:6.2f} {d:.2f}s -> {tgt:.2f}s')
out.append(x[pos:]); y = np.concatenate(out)
o = wave.open(dst, 'wb'); o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()); o.close()
print(f'{dst}: {len(y) / sr:.2f}s (removed {removed:.2f}s)')
