"""Episode 4. Lay the voice lines on a timeline: timeline.json for Blender (with a smooth per-frame mouth envelope per line),
mix.wav, and subs.ass: captions phrase by phrase, each phrase filling in word by word as it is spoken, the word being
said highlighted in the speaker's colour (times from words.json, made by ep1_words.py).

python3 scripts/ep4_timeline.py [audio dir]

Also places the story beats between lines (the reads climbing on her phone, the Network tab counting, the useEffect, Claude's fix, the phone buzz) as
timeline events and monitor image changes, and mixes synthesized sound effects for them under the voices.
"""
import audioop, json, random, re, subprocess, sys, wave
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep4"
FPS, LEAD, GAP, TAIL = 30, 1.4, 0.45, 1.8
BEAT = {3: 0.2, 6: 0.15, 9: 2.2, 12: 0.5, 14: 2.8, 16: 1.5, 17: 0.25, 18: 0.4}  # extra pause before these lines (room for the beats)


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
for x in lines:  # line 19 opens with her sigh: keep the mouth shut through it
    if x["n"] == 19:
        x["env"][:int(1.3 * FPS)] = [0.0] * int(1.3 * FPS)
end_t = lines[-1]["t1"] + TAIL
L = {x["n"]: x for x in lines}
fr = lambda t: int(t * FPS) + 1
# story beats, in seconds
net0 = L[8]["t1"] + 0.1                       # Claude opens the Network tab: the counter is running
code0 = L[12]["t0"] - 0.4                     # the useEffect with [tasks]
fix0 = L[13]["t1"] + 0.35                     # Claude fixes it
fix1, one = fix0 + 0.6, fix0 + 1.7            # [tasks] -> [], then one request
buzz = L[15]["t1"] + 0.4                      # her phone buzzes: daily limit
mon = [(0.0, "app_ok")]
t = net0
while t < code0:                              # the counter keeps spinning (16 pictures, cycled)
    mon.append((t, f"net_{len(mon) % 16}"))
    t += 4 / FPS
t, k = code0, 0
while t < fix1:                               # [tasks] pulses
    mon.append((t, "code_loop_hi" if k % 2 else "code_loop"))
    t += 9 / FPS; k += 1
mon += [(fix1, "code_fixed"), (one, "net_one"), (L[15]["t0"], "app_ok")]
phone = []
t = 0.0
while t < L[3]["t0"]:                         # the reads climbing on her dashboard
    phone.append((t, f"dash_{len(phone) % 6}"))
    t += 0.3
phone += [(L[6]["t1"], "phone_off"), (buzz, "alert")]
pglow = [(1, 0.25), (fr(L[6]["t1"]), 0.0), (fr(buzz), 0.35)]
ev = dict(net0=fr(net0), code0=fr(code0), fix0=fr(fix0), fix1=fr(fix1), one=fr(one), buzz=fr(buzz))
glow = [(1, [0.55, 0.68, 1.0])]
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
# the request counter: fast soft ticks while the Network tab is up and she stares
n = int(SR * (L[9]["t1"] - net0))
x = np.zeros(n)
for p in range(0, n - 600, int(SR * 0.045)):
    k = np.arange(600)
    x[p:p + 600] += 0.05 * np.sin(2 * np.pi * 3200 * k / SR) * np.exp(-k / 60)
x *= np.minimum(1, np.linspace(0, 6, n)) * np.minimum(1, np.linspace(4, 0, n))
wav_out("sfx_tick", x)
sfx.append(("sfx_tick", net0))
wav_out("sfx_ding", tone(1320, 0.5, 0.13, 9) + tone(1980, 0.5, 0.07, 12))
sfx.append(("sfx_ding", fix1))
wav_out("sfx_back", np.concatenate([tone(880, 0.12, 0.12, 8), tone(1320, 0.5, 0.13, 7)]))
sfx.append(("sfx_back", one))
# the phone buzzing on the desk: two rattly pulses
t = np.arange(int(SR * 0.38)) / SR
pulse = (0.30 * np.sign(np.sin(2 * np.pi * 150 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t))) * np.minimum(1, t / 0.02) * np.minimum(1, (0.38 - t) / 0.03)
wav_out("sfx_buzz", np.concatenate([pulse, np.zeros(int(SR * 0.16)), pulse]) * 0.5)
sfx.append(("sfx_buzz", buzz))

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
Style: Handle,Liberation Sans,44,&H40FFFFFF,&H40FFFFFF,&H60202020,&H00000000,1,0,0,0,100,100,1,0,1,1.6,0,2,60,60,110,1

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
ass += f"Dialogue: 1,{ts(0)},{ts(end_t)},Handle,,0,0,0,,@talkingagents\n"  # the Insta handle, all the way through
open(f"{d}/subs.ass", "w").write(ass)
print("end", round(end_t, 2), "s", int(end_t * FPS), "frames")
for L in lines:
    print(L["n"], L["who"], L["f0"], L["f1"], L["text"])
