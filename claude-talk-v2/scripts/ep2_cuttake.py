"""Cut a single-call take of the whole dialogue into the 17 line clips (audio/ep2/lNN.pcm), so the rest of the pipeline
(trim, word timing, timeline, Blender) runs as with per-line voices. Line edges come from Whisper word times matched to
the script; each cut sits in the middle of the silence between two lines. Then run scripts/ep1_trim.py audio/ep2.
<fw python> scripts/ep2_cuttake.py output/ep2_takes/take1.wav [audio dir]
"""
import difflib, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

take, d = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "audio/ep2")
lines = [l.rstrip("\n").split("\t") for l in open(f"{d}/lines.tsv")]


def norm(s):
    s = s.lower().replace("’", "'").replace("$2,000", "two thousand dollars").replace("2,000", "two thousand")
    s = re.sub(r"\b90\b", "ninety", s)
    s = re.sub(r"\.?git[- ]?ignore", "git ignore", s).replace(".env", "dot env").replace("dot-env", "dot env")
    return re.findall(r"[a-z']+", s)


script = [(w, i) for i, (_, t) in enumerate(lines) for w in norm(t)]
raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", take, "-f", "s16le", "-ac", "1", "-ar", "24000", "-"])
x24 = np.frombuffer(raw, np.int16)
x16 = np.frombuffer(subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", take, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"]), np.float32)
segs, _ = WhisperModel("small.en", compute_type="int8").transcribe(x16, language="en", word_timestamps=True, beam_size=5)
ww = [(n, w.start, w.end) for s in segs for w in s.words for n in norm(w.word)]
span = {}
for a, b, size in difflib.SequenceMatcher(None, [w for w, _ in script], [w for w, _, _ in ww], autojunk=False).get_matching_blocks():
    for k in range(size):
        li, t0, t1 = script[a + k][1], ww[b + k][1], ww[b + k][2]
        s0, s1 = span.get(li, (t0, t1))
        span[li] = (min(s0, t0), max(s1, t1))
missing = [i + 1 for i in range(len(lines)) if i not in span]
if missing:
    sys.exit(f"lines not found in the take: {missing}")
# cut points in the middle of each gap between lines
cuts = [0.0] + [(span[i][1] + span[i + 1][0]) / 2 for i in range(len(lines) - 1)] + [len(x24) / 24000]
for i in range(len(lines)):
    a, b = int(cuts[i] * 24000), int(cuts[i + 1] * 24000)
    open(f"{d}/l{i + 1:02d}.pcm", "wb").write(x24[a:b].tobytes())
    print(f"{i + 1:02d} {lines[i][0]:6s} cut {cuts[i]:6.2f}-{cuts[i + 1]:6.2f}  speech {span[i][0]:6.2f}-{span[i][1]:6.2f} | {lines[i][1]}")
