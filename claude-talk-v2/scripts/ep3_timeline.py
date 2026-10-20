"""Episode 3. Lay the voice lines on a timeline: timeline.json for Blender (with a smooth per-frame mouth envelope per line),
mix.wav, and subs.ass: captions phrase by phrase, each phrase filling in word by word as it is spoken, the word being
said highlighted in the speaker's colour (times from words.json, made by ep1_words.py).

python3 scripts/ep3_timeline.py [audio dir]

Also places the story beats between lines (Claude's cleanup run, the red error, her git log, the rewind, her commit) as
timeline events and monitor image changes, and mixes synthesized sound effects for them under the voices.
"""
import audioop, json, random, re, subprocess, sys, wave
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep3"
FPS, LEAD, GAP, TAIL = 30, 1.0, 0.5, 1.8
BEAT = {2: 2.6, 3: 1.0, 6: 1.2, 7: 0.3, 10: 0.4, 12: 2.0, 13: 0.2, 14: 0.9, 16: 0.5}  # extra pause before these lines (room for the beats)


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
L = {x["n"]: x for x in lines}
fr = lambda t: int(t * FPS) + 1
# story beats, in seconds
clean0 = L[1]["t1"] + 0.3                     # Claude's cleanup run starts
cchecks = [clean0 + 0.5 + 0.6 * i for i in range(3)]
error = L[2]["t1"] + 0.35                     # the app reloads into the red error
type0, type1 = L[5]["t1"] + 0.1, L[5]["t1"] + 1.0   # she types git status / git log
rewind0 = L[11]["t1"] - 0.5                   # the rewind starts on "rewinding my edits now"
rchecks = [L[11]["t1"] + 0.2 + 0.5 * i for i in range(3)]
back = rchecks[-1] + 0.6                      # her app is back
type2, type3 = L[13]["t0"] + 0.4, L[13]["t1"] - 0.1  # she types the commit
commit = L[13]["t1"] + 0.15
mon = [(0.0, "app_ok"), (clean0, "clean_0")] + [(t, f"clean_{i + 1}") for i, t in enumerate(cchecks)]
mon += [(error, "app_error"), (type1, "term_log"), (rewind0, "rewind_0")] + [(t, f"rewind_{i + 1}") for i, t in enumerate(rchecks)]
mon += [(back, "app_ok"), (commit, "term_commit"), (L[15]["t0"], "app_ok")]
phone = [(0.0, "phone_off")]
ev = dict(clean0=fr(clean0), cchecks=[fr(t) for t in cchecks], error=fr(error), type0=fr(type0), type1=fr(type1),
          rewind0=fr(rewind0), rchecks=[fr(t) for t in rchecks], back=fr(back), type2=fr(type2), type3=fr(type3), commit=fr(commit))
# monitor glow colour over time: red while the error is up
glow = [(1, [0.55, 0.68, 1.0]), (fr(error), [1.0, 0.22, 0.22]), (fr(type1), [0.55, 0.68, 1.0])]
json.dump(dict(fps=FPS, end=int(end_t * FPS), lines=lines, ev=ev, glow=glow,
               mon=[(fr(t), n) for t, n in mon], phone=[(fr(t), n) for t, n in phone]), open(f"{d}/timeline.json", "w"))

# sound effects, synthesized
SR = 48000
rnd = random.Random(5)


def wav_out(name, x):
    x = np.clip(x, -1, 1)
    w = wave.open(f"{d}/{name}.wav", "w")
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
    w.writeframes((x * 32767).astype("<i2").tobytes())
    w.close()


def tone(f, dur, amp, decay):
    t = np.arange(int(SR * dur)) / SR
    return amp * np.sin(2 * np.pi * f * t) * np.exp(-t * decay)


def typing(name, dur, seed):
    """calm typing: clicks every 70-150 ms"""
    n = int(SR * dur)
    x = np.zeros(n)
    p = 0
    r = random.Random(seed)
    while p < n - 2000:
        a = r.uniform(0.07, 0.16)
        k = np.arange(500)
        x[p:p + 500] += a * np.diff(np.random.default_rng(p + seed).standard_normal(501)) * np.exp(-k / 70)
        x[p:p + 500] += a * 0.6 * np.sin(2 * np.pi * r.uniform(1800, 2600) * k / SR) * np.exp(-k / 40)
        p += int(SR * r.uniform(0.07, 0.15))
    wav_out(name, x)


sfx = []
wav_out("sfx_ding", tone(1320, 0.5, 0.13, 9) + tone(1980, 0.5, 0.07, 12))
for tc in cchecks + rchecks + [commit]:
    sfx.append(("sfx_ding", tc))
# the error: a low thud with a soft buzz
t = np.arange(int(SR * 0.9)) / SR
thud = 0.5 * np.sin(2 * np.pi * (70 - 25 * t) * t) * np.exp(-t * 6) + 0.06 * np.sign(np.sin(2 * np.pi * 110 * t)) * np.exp(-t * 4)
wav_out("sfx_thud", thud)
sfx.append(("sfx_thud", error))
# the app coming back: a rising two-note chime
wav_out("sfx_back", np.concatenate([tone(880, 0.12, 0.12, 8), tone(1320, 0.5, 0.13, 7)]))
sfx.append(("sfx_back", back))
typing("sfx_type1", type1 - type0, 1)
sfx.append(("sfx_type1", type0))
typing("sfx_type2", type3 - type2, 2)
sfx.append(("sfx_type2", type2))

srcs = [(f"{d}/l{x['n']:02d}.wav", x["t0"]) for x in lines] + [(f"{d}/{nm}.wav", tt) for nm, tt in sfx]
ins = sum([["-i", s] for s, _ in srcs], [])
fl = ";".join(f"[{i}]aresample=48000,adelay={int(tt * 1000)}:all=1[a{i}]" for i, (_, tt) in enumerate(srcs))
fl += ";" + "".join(f"[a{i}]" for i in range(len(srcs))) + f"amix=inputs={len(srcs)}:normalize=0,apad=whole_dur={end_t}[out]"
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
