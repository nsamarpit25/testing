"""Lay the voice lines on a timeline: timeline.json for Blender (with a smooth per-frame mouth envelope per line),
mix.wav, and subs.ass: captions phrase by phrase, each phrase filling in word by word as it is spoken, the word being
said highlighted in the speaker's colour (times from words.json, made by ep1_words.py).

python3 scripts/ep1_timeline.py [audio dir]
"""
import audioop, json, re, subprocess, sys, wave
d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep1b"
FPS, LEAD, GAP, TAIL = 30, 1.0, 0.5, 1.8
BEAT = {2: 0.5, 3: 0.4, 5: 0.3, 9: 0.2, 15: 1.0, 17: 1.0, 18: 0.3}  # extra pause before these lines (room for acting)


def envelope(wav):
    """Mouth opening per video frame: RMS per frame, normalised, smoothed, gated -> 0..1 with no frame-to-frame noise."""
    w = wave.open(wav)
    sr, sw = w.getframerate(), w.getsampwidth()
    data = w.readframes(w.getnframes())
    hop = sr // FPS
    rms = [audioop.rms(data[i * hop * sw:(i + 1) * hop * sw], sw) for i in range(len(data) // (hop * sw) + 1)]
    ref = sorted(rms)[int(len(rms) * 0.9)] or 1
    v = [min(r / ref, 1.0) for r in rms]
    v = [sum(v[max(0, i - 1):i + 2]) / len(v[max(0, i - 1):i + 2]) for i in range(len(v))]  # 3-frame average
    out, y = [], 0.0
    for x in v:  # gate quiet frames, then a one-pole follower: quick to open, a bit slower to close
        x = 0.0 if x < 0.18 else min((x - 0.18) / 0.6, 1.0)
        y += (x - y) * (0.6 if x > y else 0.4)
        out.append(round(y, 3))
    return out


rows = [l.split() for l in open(f"{d}/durs.txt")]
texts = [l.rstrip("\n").split("\t") for l in open(f"{d}/lines.tsv")]
t, lines = LEAD, []
for (n, who, dur), (_, txt) in zip(rows, texts):
    n, dur = int(n), float(dur)
    t += BEAT.get(n, 0)
    lines.append(dict(n=n, who=who, t0=round(t, 3), t1=round(t + dur, 3), f0=int(t * FPS) + 1, f1=int((t + dur) * FPS) + 1,
                      text=txt, env=envelope(f"{d}/l{n:02d}.wav")))
    t += dur + GAP
end_t = lines[-1]["t1"] + TAIL
json.dump(dict(fps=FPS, end=int(end_t * FPS), lines=lines), open(f"{d}/timeline.json", "w"))
ins = sum([["-i", f"{d}/l{L['n']:02d}.wav"] for L in lines], [])
fl = ";".join(f"[{i}]adelay={int(L['t0'] * 1000)}:all=1[a{i}]" for i, L in enumerate(lines))
fl += ";" + "".join(f"[a{i}]" for i in range(len(lines))) + f"amix=inputs={len(lines)}:normalize=0,apad=whole_dur={end_t}[out]"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", fl, "-map", "[out]", "-ar", "48000",
                f"{d}/mix.wav"], check=True)


def ts(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Liberation Sans,72,&H00FFFFFF,&H00FFFFFF,&H00303030,&H80000000,1,0,0,0,100,100,0,0,1,2.2,0,2,110,110,330,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
words = json.load(open(f"{d}/words.json"))
HI = {"cleo": r"\c&H0066D9FF&", "claude": r"\c&H005A9AFF&"}  # the word being said: warm yellow for Cleo, orange for Claude
SAID, CUR, TODO = r"{\alpha&H00&\c&HFFFFFF&}", "{\\alpha&H00&%s}", r"{\alpha&HFF&}"  # unsaid words keep their space
HOLD, JOIN = 0.35, 0.8


def phrases(ws):
    """Split a line into caption phrases: break after punctuation once there are 2+ words, never more than 6 words
    or ~30 characters, and never leave a lone word at the end."""
    out, cur = [], []
    for w in ws:
        cur.append(w)
        text = " ".join(x[0] for x in cur)
        if len(cur) >= 6 or len(text) >= 30 or (len(cur) >= 2 and re.search(r'[.,?!;:—]["”]?$', w[0])):
            out.append(cur)
            cur = []
    if cur:
        if len(cur) == 1 and out and len(out[-1]) < 7:
            out[-1] += cur
        else:
            out.append(cur)
    return out


for li, L in enumerate(lines):
    style, hi = "Cap", HI[L["who"]]
    ph = phrases(words[str(L["n"])])
    nxt_line = lines[li + 1]["t0"] if li + 1 < len(lines) else 1e9
    for pi_, p in enumerate(ph):
        last_end = L["t0"] + p[-1][2]
        nxt = L["t0"] + ph[pi_ + 1][0][1] if pi_ + 1 < len(ph) else nxt_line
        end = nxt if nxt - last_end < JOIN else min(last_end + HOLD, nxt)
        for k, (w, a, b) in enumerate(p):
            t_a = L["t0"] + a
            t_b = L["t0"] + p[k + 1][1] if k + 1 < len(p) else last_end
            txt = " ".join((SAID if m < k else (CUR % hi) if m == k else TODO) + x[0] for m, x in enumerate(p))
            ass += f"Dialogue: 0,{ts(t_a)},{ts(max(t_b, t_a + 0.05))},{style},,0,0,0,,{txt}\n"
        if end > last_end:  # the whole phrase in white for a beat after its last word
            ass += f"Dialogue: 0,{ts(last_end)},{ts(end)},{style},,0,0,0,," + " ".join(SAID + x[0] for x in p) + "\n"
open(f"{d}/subs.ass", "w").write(ass)
print("end", round(end_t, 2), "s", int(end_t * FPS), "frames")
for L in lines:
    print(L["n"], L["who"], L["f0"], L["f1"], L["text"])
