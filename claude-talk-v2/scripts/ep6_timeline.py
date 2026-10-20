"""Episode 6 ("Make it worse"). Lay the voice lines on a timeline: timeline.json for Blender (with a smooth per-frame mouth
envelope per line), mix.wav, and subs.ass: captions phrase by phrase, filling in word by word as they are spoken (times
from words.json, made by ep2_words.py).

python3 scripts/ep6_timeline.py [audio dir]

Also places the story beats between lines as timeline events and monitor image changes: the three clicks on PRESS, each
playing a synthesized trumpet fanfare that collapses into a squeak; the cursor going to close the tab; her glance at the
PORTFOLIO tab; the jump cut to her typing a second button; the click on WORSE and its much worse trumpet; the last click
and the cut to black on its first note (the encode adds the black tail, with one tiny squeak on it).
"""
import audioop, json, random, re, subprocess, sys, wave
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep6"
FPS, LEAD, GAP = 30, 1.3, 0.45
SR = 48000
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



# ---------------------------------------------------------------- sounds, synthesized
def wav_out(name, x):
    x = np.clip(x, -1, 1)
    w = wave.open(f"{d}/{name}.wav", "w")
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
    w.writeframes((x * 32767).astype("<i2").tobytes())
    w.close()


rnd = np.random.default_rng(6)


def click(amp=0.16):
    """a mouse click: a short bright tick with a tiny body"""
    k = np.arange(int(SR * 0.03))
    return amp * (rnd.uniform(-1, 1, len(k)) * np.exp(-k / 90) + 0.6 * np.sin(2 * np.pi * 2400 * k / SR) * np.exp(-k / 120))


def brass(f, a, wob=0.0):
    """a cheap toy trumpet: sawtooth-ish harmonics whose brightness follows the loudness, a little vibrato and breath.
    f, a: per-sample frequency and amplitude curves"""
    t = np.arange(len(f)) / SR
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t))
    if wob:
        a = a * (1 - wob * (0.5 + 0.5 * np.sin(2 * np.pi * 17 * t)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.zeros(len(f))
    for k in range(1, 15):
        x += np.sin(k * ph) * k ** -0.75 * np.clip(a, 0, 1) ** (0.25 * k) * (k * f < SR / 2.2)
    x = x / 3.2 * a
    x += 0.012 * a * rnd.standard_normal(len(f))
    return x


def seq(parts):
    """parts: (freq or (f0, f1), dur, level) -> smooth note-by-note curves, short tongued attacks"""
    F, A = [], []
    for fq, dur, lv in parts:
        n = int(dur * SR)
        f0, f1 = (fq, fq) if not isinstance(fq, tuple) else fq
        F.append(np.geomspace(f0, f1, n))
        env = np.ones(n) * lv
        att, rel = min(int(0.025 * SR), n // 3), min(int(0.04 * SR), n // 3)
        env[:att] *= np.linspace(0, 1, att)
        env[n - rel:] *= np.linspace(1, 0, rel)
        A.append(env)
    return np.concatenate(F), np.concatenate(A)


def squeak(f=1150, dur=0.13, lv=0.5):
    f_, a_ = seq([((f, f * 1.35), dur, lv)])
    return brass(f_, a_)


def fanfare():
    """ta-ta-ta-TAAA ... and the last note sags, wobbles and gives up into a squeak"""
    f, a = seq([(392, 0.13, 0.8), (392, 0.13, 0.8), (523, 0.13, 0.85), (659, 0.55, 1.0)])
    sag_f, sag_a = seq([((659, 300), 0.75, 0.9)])
    sag_a *= np.linspace(1, 0.35, len(sag_a))
    x = np.concatenate([brass(f, a), brass(sag_f, sag_a, 0.35), np.zeros(int(0.22 * SR)), squeak()])
    return 0.42 * x


def fanfare_worse():
    """lower, slower, longer: the big note collapses into a long deep groan, a pause, one tiny late squeak"""
    f, a = seq([(262, 0.2, 0.8), (262, 0.2, 0.8), (349, 0.2, 0.85), (440, 0.7, 1.0)])
    sag_f, sag_a = seq([((440, 62), 1.9, 1.0)])
    sag_a *= np.linspace(1, 0.5, len(sag_a))
    x = np.concatenate([brass(f, a), brass(sag_f, sag_a, 0.55), np.zeros(int(0.65 * SR)), squeak(1300, 0.09, 0.35)])
    return 0.48 * x


A_, B_ = fanfare(), fanfare_worse()
wav_out("sfx_trumpet", A_)
wav_out("sfx_worse", B_)
wav_out("sfx_squeak", 0.3 * squeak(1300, 0.09, 0.35))
wav_out("sfx_click", click(0.16))
DA, DB = len(A_) / SR, len(B_) / SR
ty = np.zeros(int(SR * 1.6))
for p in (0.0, 0.11, 0.2, 0.34, 0.43, 0.6, 0.69, 0.8, 0.97, 1.05, 1.18, 1.3):
    c = click(0.06)
    ty[int(p * SR):int(p * SR) + len(c)] += c
wav_out("sfx_type", ty)

# ---------------------------------------------------------------- the timeline
rows = [l.split() for l in open(f"{d}/durs.txt")]
texts = [l.rstrip("\n").split("\t") for l in open(f"{d}/lines.tsv")]
W_ = json.load(open(f"{d}/words.json"))
t, lines, sfx, mon, ev = LEAD, [], [], [(0.0, "press")], dict(clicks=[], trumpets=[])


def press(tc, worse=False):
    """a click at tc: the button goes down for a moment, the trumpet plays"""
    sfx.append(("sfx_click", tc))
    sfx.append(("sfx_worse" if worse else "sfx_trumpet", tc + 0.04))
    mon.append((tc, "worse_down" if worse else "press_down"))
    mon.append((tc + 0.16, "worse" if worse else "press"))
    ev["clicks"].append(tc)
    ev["trumpets"].append((tc + 0.04, tc + 0.04 + (DB if worse else DA)))
    return tc + 0.04 + (DB if worse else DA)


LAUGH15 = 1.4            # the laugh starts this far into line 15
for (n, who, dur), (_, txt) in zip(rows, texts):
    n, dur = int(n), float(dur)
    if n == 3:                                   # "Show me." -> click, trumpet, a beat -> "Again."
        t = press(t - GAP + 0.45) + 0.75
    elif n == 4:                                 # "Again." -> click, trumpet -> she laughs it off
        t = press(t - GAP + 0.3) + 0.45
    elif n == 8:                                 # "I know." -> the cursor comes back, one more click
        mon.append((t - GAP + 0.05, "press"))
        t = press(t - GAP + 0.55) + 0.55
    elif n == 12:                                # "Why'd you stop?" -> she looks at the PORTFOLIO tab
        ev["port"] = t - GAP + 0.25
        mon.append((ev["port"], "portfolio"))
        t += 1.1
    elif n == 13:                                # a quiet beat before the dare
        t += 1.0
    elif n == 15:                                # jump cut: typing the second button, then WORSE
        ev["jump"] = t - GAP + 0.35
        mon.append((ev["jump"], "code_worse"))
        sfx.append(("sfx_type", ev["jump"] + 0.15))
        ev["type"] = (ev["jump"] + 0.1, ev["jump"] + 1.5)
        mon.append((ev["jump"] + 1.75, "worse"))
        ev["worse_page"] = ev["jump"] + 1.75
        end_worse = press(ev["jump"] + 2.45, worse=True)
        t = end_worse - 0.85 - LAUGH15           # she cracks up on the late squeak
    elif n == 16:
        t += 0.2
    lines.append(dict(n=n, who=who, t0=round(t, 3), t1=round(t + dur, 3), f0=int(t * FPS) + 1, f1=int((t + dur) * FPS) + 1,
                      text=txt, env=envelope(f"{d}/l{n:02d}.wav")))
    if n == 4:
        ev["close"] = t + W_["4"][1][1]          # "Back to something useful": the cursor goes to close the tab
        mon.append((ev["close"], "press_close"))
    t += dur + GAP
L = {x["n"]: x for x in lines}
# the last click on WORSE plays all the way through; she cracks up again (a second laugh from her take, line 15), and
# after the squeak the picture holds on the two of them laughing, then fades to black (the fade and the black are added at
# the encode)
ev["last"] = L[16]["t1"] + 0.75
end_last = press(ev["last"], worse=True)
LAUGH_SRC = (3.80, 4.80)                         # the laugh after "disgusting" in line 15's clip
w = wave.open(f"{d}/l15.wav")
sr15 = w.getframerate()
x15 = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
seg = x15[int(LAUGH_SRC[0] * sr15):int(LAUGH_SRC[1] * sr15)]
seg = np.interp(np.arange(int(len(seg) * SR / sr15)) * sr15 / SR, np.arange(len(seg)), seg) * 0.85
seg[:480] *= np.linspace(0, 1, 480)
seg[-2400:] *= np.linspace(1, 0, 2400)
wav_out("sfx_laugh", seg)
ev["laugh2"] = end_last - 1.45                   # over the end of the groan, into the squeak
sfx.append(("sfx_laugh", ev["laugh2"]))
# her small laughs between the lines (Gemini TTS, Leda, output/ep6_laughs): the snort after the second trumpet, the soft
# laugh after the third, a chuckle after "Keep it".  Leading silence trimmed so the sound starts on the frame her laugh
# animation starts (blender/ep6.py: t2[1]-22, t3[1]-20, l16.f1+4); (take, level, start time, mouth scale)
SMALL = {"sfx_snort": ("snort_3", 0.85, ev["trumpets"][1][1] - 22 / FPS, 0.5),
         "sfx_soft": ("soft_1", 0.9, ev["trumpets"][2][1] - 20 / FPS, 0.7),
         "sfx_chuckle": ("snort_1", 1.2, (L[16]["f1"] + 3) / FPS, 0.4)}
extra = []
for nm, (take, lv, tt, ms) in SMALL.items():
    w = wave.open(f"output/ep6_laughs/{take}.wav")
    srl = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    on = max(0, int(np.argmax(np.abs(x) > 0.03)) - int(0.03 * srl))
    x = x[on:]
    x = np.interp(np.arange(int(len(x) * SR / srl)) * srl / SR, np.arange(len(x)), x)
    x = x / np.abs(x).max() * 0.5 * lv
    x[:240] *= np.linspace(0, 1, 240)
    x[-1440:] *= np.linspace(1, 0, 1440)
    wav_out(nm, x)
    sfx.append((nm, tt))
    extra.append(dict(who="cleo", f0=int(tt * FPS) + 1, env=[round(v * ms, 3) for v in envelope(f"{d}/{nm}.wav")]))
FADE, TAIL = 1.2, 0.8
end_t = end_last + 1.6                           # the hold, the fade is its last FADE seconds
cut_t = end_t
fr = lambda t: int(t * FPS) + 1
mon.sort()
evf = {k: (fr(v) if isinstance(v, float) else [fr(x) for x in v] if k == "clicks" else
           [[fr(a), fr(b)] for a, b in v] if k == "trumpets" else [fr(v[0]), fr(v[1])]) for k, v in ev.items()}
glow = [(1, [1.0, 0.92, 0.80], 1.1), (evf["jump"], [0.60, 0.66, 1.0], 0.8), (evf["worse_page"], [1.0, 0.92, 0.80], 1.1)]
extra.append(dict(who="cleo", f0=fr(ev["laugh2"]), env=envelope(f"{d}/sfx_laugh.wav")))  # her mouth on the second laugh
json.dump(dict(fps=FPS, end=fr(end_t) - 1, lines=lines, extra=extra, fade=FADE, tail=TAIL, ev=evf, glow=glow, pglow=[(1, 0.0)],
               mon=[(fr(t), n) for t, n in mon], phone=[(1, "phone_off")]), open(f"{d}/timeline.json", "w"))

# the mix: everything fades out with the picture, then the black tail is silent
srcs = [(f"{d}/l{x['n']:02d}.wav", x["t0"]) for x in lines] + [(f"{d}/{nm}.wav", tt) for nm, tt in sfx]
ins = sum([["-i", s] for s, _ in srcs], [])
fl = ";".join(f"[{i}]aresample=48000,adelay={int(tt * 1000)}:all=1[a{i}]" for i, (_, tt) in enumerate(srcs))
fl += ";" + "".join(f"[a{i}]" for i in range(len(srcs))) + f"amix=inputs={len(srcs)}:normalize=0,atrim=0:{end_t},afade=t=out:st={end_t - FADE}:d={FADE},apad=whole_dur={end_t + TAIL}[out]"
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
Style: Cap,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00303030,&H80000000,1,0,0,0,100,100,0,0,1,2.2,0,2,110,110,330,1
Style: End,Arial,80,&H00FFFFFF,&H00FFFFFF,&H00202020,&H90000000,1,0,0,0,100,100,0,0,1,3,0,5,90,90,0,1
Style: Handle,Arial,34,&H28FFFFFF,&H28FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,1,0,1,0,1.5,2,60,60,114,1

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
            ass += f"Dialogue: 0,{ts(last_end)},{ts(min(end, cut_t))},{style},,0,0,0,," + " ".join(SAID + x[0] for x in p) + "\n"
ass += f"Dialogue: 1,{ts(0)},{ts(end_t + TAIL)},Handle,,0,0,0,,@talkingagents\n"  # the Insta handle, all the way through
open(f"{d}/subs.ass", "w").write(ass)
print("end", round(end_t, 2), "s (fade", FADE, ") +", TAIL, "black;", fr(end_t) - 1, "frames rendered")
for L in lines:
    print(L["n"], L["who"], L["f0"], L["f1"], L["text"])
print({k: v for k, v in evf.items()})
print(mon)
