"""Check single-call takes: every word (Whisper + Gemini transcripts against the script) and every line's speaker (voice pitch:
Leda/Cleo is high, Achird/Claude is low). Run with the faster-whisper venv:  <fw python> scripts/ep2_checktakes.py output/ep2_takes/take*.wav
"""
import base64, difflib, json, re, subprocess, sys, urllib.request
import numpy as np
from faster_whisper import WhisperModel
sys.path.insert(0, "scripts")
from ep4_onecall import TURNS, PROJECT, token

# the script as 17 lines (split the merged turns back at the pause tags)
LINES = []
for who, t in TURNS:
    for part in re.split(r"\[(?:long|medium) pause\]", t):
        if part.strip():
            LINES.append((who, part.strip()))


def norm(s):
    s = s.lower().replace("’", "'").replace("$2,000", "two thousand dollars").replace("2,000", "two thousand").replace("$2000", "two thousand dollars")
    s = s.replace("45,000", "forty five thousand").replace("forty-five", "forty five").replace("brand-new", "brand new")
    s = re.sub(r"\bd[- ]?d[- ]?o[- ]?s[- ]?(s?)ing\b", "ddosing", s).replace("use effect", "useeffect").replace("local host", "localhost")
    s = re.sub(r"\.?git[- ]?ignore", "git ignore", s).replace(".env", "dot env").replace("dot-env", "dot env")
    return re.findall(r"[a-z']+", s)


SCRIPT = [(w, i) for i, (_, t) in enumerate(LINES) for w in norm(t)]
TOK = token()
wm = WhisperModel("small.en", compute_type="int8")


def gemini_words(path):
    data = base64.b64encode(open(path, "rb").read()).decode()
    body = {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": "audio/wav", "data": data}},
                                                    {"text": "Transcribe this dialogue verbatim, every word exactly as spoken, no speaker labels."}]}]}
    req = urllib.request.Request(f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/gemini-3.8-flash:generateContent",
                                 json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": f"Bearer {TOK}", "x-goog-user-project": PROJECT})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    return norm(d["candidates"][0]["content"]["parts"][0]["text"])


def diffs(heard):
    ref = [w for w, _ in SCRIPT]
    out = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, ref, heard, autojunk=False).get_opcodes():
        if op != "equal":
            out.append(f"line {SCRIPT[min(a0, len(SCRIPT) - 1)][1] + 1}: '{' '.join(ref[a0:a1])}' -> '{' '.join(heard[b0:b1])}'")
    return out


def pitch(x, sr=16000):
    """median F0 (Hz) of the voiced 40 ms frames, by autocorrelation"""
    f, hop = 640, 320
    vals = []
    peak = np.abs(x).max() + 1e-9
    for s in range(0, len(x) - f, hop):
        fr = x[s:s + f] * np.hanning(f)
        if np.sqrt(np.mean(fr ** 2)) < 0.03 * peak:
            continue
        ac = np.fft.irfft(np.abs(np.fft.rfft(fr, 2 * f)) ** 2)[:f]
        lo, hi = sr // 400, sr // 70
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.3 * ac[0]:
            vals.append(sr / lag)
    return float(np.median(vals)) if vals else 0.0


for path in sys.argv[1:]:
    pcm = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"])
    x = np.frombuffer(pcm, np.float32)
    segs, _ = wm.transcribe(x, language="en", word_timestamps=True, beam_size=5)
    ww = [(n, w.start, w.end) for s in segs for w in s.words for n in norm(w.word)]
    heard_w = [w for w, _, _ in ww]
    # line spans from the Whisper words that match the script
    span = {}
    for a, b, size in difflib.SequenceMatcher(None, [w for w, _ in SCRIPT], heard_w, autojunk=False).get_matching_blocks():
        for k in range(size):
            li = SCRIPT[a + k][1]
            t0, t1 = ww[b + k][1], ww[b + k][2]
            s0, s1 = span.get(li, (t0, t1))
            span[li] = (min(s0, t0), max(s1, t1))
    wrong_spk = []
    f0s = []
    for i, (who, t) in enumerate(LINES):
        if i not in span:
            wrong_spk.append(f"line {i + 1}: not found")
            continue
        s0, s1 = span[i]
        f0 = pitch(x[int(s0 * 16000):int(s1 * 16000)])
        f0s.append(f"{i + 1}:{f0:.0f}")
        if (who == "Cleo") != (f0 > 165):
            wrong_spk.append(f"line {i + 1} ({who}) sounds like the other voice ({f0:.0f} Hz)")
    try:
        g = gemini_words(path)
    except Exception as e:  # rate limited: Whisper alone
        print('   gemini failed:', e)
        g = heard_w
    wd, gd = diffs(heard_w), diffs(g)
    both = [d for d in gd if d in wd]  # both transcribers disagree with the script the same way
    dur = len(x) / 16000
    print(f"== {path}  {dur:.1f}s")
    print("   speakers:", "OK" if not wrong_spk else "; ".join(wrong_spk))
    print("   gemini words:", "OK" if not gd else "; ".join(gd))
    print("   whisper words:", "OK" if not wd else "; ".join(wd))
    print("   pitch:", " ".join(f0s), flush=True)
