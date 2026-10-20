"""Per-word timings for every voice line, for word-by-word captions.

Whisper (faster-whisper, word timestamps) listens to each clip; its words are matched onto the script's own words
(so captions keep the script's spelling and punctuation). Script words it missed get times interpolated between
their neighbours.  Writes <audio dir>/words.json: {"<n>": [[word, start, end], ...]} in seconds from the clip start.

python scripts/ep1_words.py [audio dir]     (needs faster-whisper; the medium.en model is read from the HF cache)
"""
import difflib, json, os, re, subprocess, sys
import numpy as np
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from faster_whisper import WhisperModel

d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep1b"
texts = [l.rstrip("\n").split("\t") for l in open(f"{d}/lines.tsv")]
model = WhisperModel("medium.en", device="cpu", compute_type="int8")


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


# hand-checked against the clip's loudness where Whisper merged words: line 9 opens with a short breathy chuckle
FIX = {9: {0: (0.05, 0.25), 1: (0.50, 1.10)}}

out = {}
for i, (who, text) in enumerate(texts, 1):
    wav = f"{d}/l{i:02d}.wav"
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), language="en", word_timestamps=True, initial_prompt=text, beam_size=5)
    heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    script = text.split()
    times = [None] * len(script)
    sm = difflib.SequenceMatcher(a=[norm(w) for w in script], b=[norm(h[0]) for h in heard], autojunk=False)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            times[a + k] = (heard[b + k][1], heard[b + k][2])
    # fill gaps: spread the unmatched script words evenly between the matched neighbours
    end_all = heard[-1][2] if heard else 1.0
    k = 0
    while k < len(script):
        if times[k] is not None:
            k += 1
            continue
        j = k
        while j < len(script) and times[j] is None:
            j += 1
        t0 = times[k - 1][1] if k else 0.0
        t1 = times[j][0] if j < len(script) else end_all
        step = (t1 - t0) / (j - k)
        for m in range(k, j):
            times[m] = (t0 + step * (m - k), t0 + step * (m - k + 1))
        k = j
    for m, t in FIX.get(i, {}).items():
        times[m] = t
    out[str(i)] = [[w, round(a, 3), round(b, 3)] for w, (a, b) in zip(script, times)]
    matched = sum(size for _, _, size in sm.get_matching_blocks())
    print(f"{i:02d} {matched}/{len(script)} matched | " + " ".join(f"{w}@{a:.2f}" for w, (a, _) in zip(script, times)))
json.dump(out, open(f"{d}/words.json", "w"), indent=0)
