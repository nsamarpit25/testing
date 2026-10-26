"""Word timings (absolute seconds) for every line: faster-whisper on each trimmed clip, matched onto the script words.
~/Developer/reel-builder/.whisper/bin/python words.py  -> audio/words.json [[word, start, end, line], ...]"""
import difflib, json, os, re, subprocess
from pathlib import Path
import numpy as np
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from faster_whisper import WhisperModel
HERE = Path(__file__).resolve().parent
lines = json.load(open(HERE / "audio/lines.json"))
m = WhisperModel("medium.en", device="cpu", compute_type="int8")
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
out = []
for i, L in enumerate(lines, 1):
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(HERE / f"audio/l{i:02d}.wav"), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = m.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, language="en")
    hw = [w for s in segs for w in s.words]
    sw = L["say"].split()
    t = [None] * len(sw)
    sm = difflib.SequenceMatcher(a=[norm(w) for w in sw], b=[norm(w.word) for w in hw], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            t[a + k] = (hw[b + k].start, hw[b + k].end)
    dur = L["end"] - L["start"]
    known = [k for k in range(len(sw)) if t[k]]
    for k in range(len(sw)):
        if not t[k]:  # interpolate between neighbours
            p = max([j for j in known if j < k], default=None); q = min([j for j in known if j > k], default=None)
            s0 = t[p][1] if p is not None else 0.0; s1 = t[q][0] if q is not None else dur
            np_ = (q if q is not None else len(sw)) - (p if p is not None else -1)
            f = (k - (p if p is not None else -1)) / np_
            t[k] = (s0 + (s1 - s0) * (f - 1 / np_), s0 + (s1 - s0) * f)
    out += [[w, round(L["start"] + a, 3), round(L["start"] + b, 3), i] for w, (a, b) in zip(sw, t)]
    print(i, " ".join(f"{w}@{a:.2f}" for w, a, b, _ in out[-len(sw):]))
(HERE / "audio/words.json").write_text(json.dumps(out))
