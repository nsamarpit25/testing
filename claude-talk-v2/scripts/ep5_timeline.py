"""Episode 5. Lay the voice lines on a timeline: timeline.json for Blender (with a smooth per-frame mouth envelope per line),
mix.wav, and subs.ass: captions phrase by phrase, each phrase filling in word by word as it is spoken, the word being
said highlighted in the speaker's colour (times from words.json, made by ep2_words.py).

python3 scripts/ep5_timeline.py [audio dir]

Also places the story beats between lines (her CSS, the button text, the three terminals with the folder names lit one by
one, the editor-vs-browser mismatch, the ports, typing localhost:5175, the giant green reveal) as timeline events and
monitor image changes, mixes synthesized sound effects for them under the voices, and adds the end card text.
"""
import audioop, json, random, re, subprocess, sys, wave
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep5"
FPS, LEAD, GAP, TAIL = 30, 1.7, 0.45, 3.0
BEAT = {6: 0.25, 9: 0.5, 10: 0.2, 13: 0.15, 14: 0.2, 18: 1.9, 22: 0.5}  # extra pause before these lines (room for the beats)
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
W_ = json.load(open(f"{d}/words.json"))
def wt(n, k):  # start time of word k of line n
    return L[n]["t0"] + W_[str(n)][k][1]
# story beats, in seconds
imp0 = wt(5, 9) - 0.25                         # "...put important on everything": her CSS
please0 = wt(7, 6) - 0.15                      # "PLEASE WORK": the button text in the code
look0 = wt(7, 8)                               # "Look!": the page, still "Add task"
cut7 = wt(7, 14) - 0.1                         # "You broke CSS": back to her
term0 = L[8]["t1"] + 0.25                      # the terminals open
names = [L[10]["t0"] + W_["10"][k][1] for k in range(3)]   # each folder name lights as he reads it
split0 = L[13]["t0"] - 0.25                    # editing final / browser on the original
split1 = wt(13, 3)                             # "Your browser..."
ports0 = wt(15, 2) - 0.1                       # "When 5173 was taken..."
url0 = wt(17, 3) - 0.1                         # "Open 5175": the address bar
url1 = L[17]["t1"] + 0.15                      # typed
reveal = L[17]["t1"] + 0.75                    # enter: the giant green button
mon = [(0.0, "app_blue"), (imp0, "code_important"), (please0, "code_please"), (look0, "app_blue"), (term0, "term")]
mon += [(t, f"term_n{k + 1}") for k, t in enumerate(names)]
mon += [(split0, "split_0"), (split1, "split_1"), (L[14]["t1"], "term"), (ports0, "term_ports"), (L[16]["t0"], "app_blue"),
        (url0, "url_a"), (url1, "url_b"), (reveal, "final_green")]
phone = [(0.0, "phone_off")]
pglow = [(1, 0.0)]
ev = dict(imp0=fr(imp0), please0=fr(please0), look0=fr(look0), cut7=fr(cut7), term0=fr(term0), names=[fr(t) for t in names],
          split0=fr(split0), split1=fr(split1), ports0=fr(ports0), url0=fr(url0), url1=fr(url1), reveal=fr(reveal))
glow = [(1, [0.80, 0.84, 1.0], 1.1), (fr(imp0), [0.55, 0.62, 1.0], 0.8), (fr(look0), [0.80, 0.84, 1.0], 1.1),
        (fr(term0), [0.55, 0.62, 1.0], 0.7), (fr(L[16]["t0"]), [0.80, 0.84, 1.0], 1.1), (fr(reveal), [0.45, 1.0, 0.35], 2.4)]
json.dump(dict(fps=FPS, end=int(end_t * FPS), lines=lines, ev=ev, glow=glow, pglow=pglow,
               mon=[(fr(t), n) for t, n in mon], phone=[(fr(t), n) for t, n in phone]), open(f"{d}/timeline.json", "w"))

# sound effects, synthesized
SR = 48000


def wav_out(name, x):
    x = np.clip(x, -1, 1)
    w = wave.open(f"{d}/{name}.wav", "w")
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
    w.writeframes((x * 32767).astype("<i2").tobytes())
    w.close()


def tone(f, dur, amp, decay):
    t = np.arange(int(SR * dur)) / SR
    return amp * np.sin(2 * np.pi * f * t) * np.exp(-t * decay)


sfx = []
rnd = random.Random(5)


def click(amp=0.16):
    """a mouse click: a short bright tick with a tiny body"""
    n = int(SR * 0.03)
    k = np.arange(n)
    return amp * (np.array([rnd.uniform(-1, 1) for _ in k]) * np.exp(-k / 90) + 0.6 * np.sin(2 * np.pi * 2400 * k / SR) * np.exp(-k / 120))


# opening: she clicks the stubborn button, three times, harder each time
for i, t in enumerate((0.45, 0.85, 1.2)):
    wav_out(f"sfx_click{i}", click(0.10 + 0.04 * i))
    sfx.append((f"sfx_click{i}", t))
# the folder names lighting up: soft pops, rising
for i, t in enumerate(names):
    wav_out(f"sfx_pop{i}", tone(660 * 1.26 ** i, 0.25, 0.10, 14))
    sfx.append((f"sfx_pop{i}", t))
wav_out("sfx_mismatch", tone(330, 0.35, 0.12, 8) + tone(311, 0.35, 0.10, 8))
sfx.append(("sfx_mismatch", split1))
# typing 5175, then enter
ty = np.zeros(int(SR * 0.9))
for p in (0.0, 0.14, 0.27, 0.42, 0.62):
    c = click(0.07)
    ty[int(p * SR):int(p * SR) + len(c)] += c
wav_out("sfx_type", ty)
sfx.append(("sfx_type", url0 + 0.25))
wav_out("sfx_enter", click(0.14))
sfx.append(("sfx_enter", reveal - 0.05))
# the reveal: a big bright major chord
rv = sum(tone(f, 1.6, a, 2.2) for f, a in ((523, 0.09), (659, 0.07), (784, 0.07), (1047, 0.05)))
wav_out("sfx_reveal", rv)
sfx.append(("sfx_reveal", reveal))

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


L_last = lines[-1]
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
END_TXT = r'{\fad(300,0)\pos(540,400)}Send this to your\N"final_final" friend'
ass += f"Dialogue: 2,{ts(L_last['t1'] + 0.5)},{ts(end_t)},End,,0,0,0,,{END_TXT}\n"  # the end card
ass += f"Dialogue: 1,{ts(0)},{ts(end_t)},Handle,,0,0,0,,@talkingagents\n"  # the Insta handle, all the way through
open(f"{d}/subs.ass", "w").write(ass)
print("end", round(end_t, 2), "s", int(end_t * FPS), "frames")
for L in lines:
    print(L["n"], L["who"], L["f0"], L["f1"], L["text"])
