"""Episode 2. Lay the voice lines on a timeline: timeline.json for Blender (with a smooth per-frame mouth envelope per line),
mix.wav, and subs.ass: captions phrase by phrase, each phrase filling in word by word as it is spoken, the word being
said highlighted in the speaker's colour (times from words.json, made by ep1_words.py).

python3 scripts/ep2_timeline.py [audio dir]\n\nAlso places the story beats between lines (phone buzz, key mashing, stars ticking up, Claude's agent run) as\ntimeline events and monitor/phone image changes, and mixes synthesized sound effects for them under the voices.
"""
import audioop, json, random, re, subprocess, sys, wave
import numpy as np
d = sys.argv[1] if len(sys.argv) > 1 else "audio/ep2"
FPS, LEAD, GAP, TAIL = 30, 1.0, 0.5, 1.8
BEAT = {3: 0.1, 7: 0.3, 9: 1.9, 11: 3.4, 12: 2.4, 13: 0.2, 14: 0.9, 15: 2.6, 16: 0.5, 17: 0.3}  # extra pause before these lines (room for the beats)


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
buzz = L[9]["t0"] - 1.7                       # the phone lights up and buzzes
mash0, mash1 = L[10]["t1"] + 0.15, L[11]["t0"] - 0.45   # she hammers the keyboard
stars0 = L[11]["t1"] + 0.35                   # the star count starts climbing again
agent0 = L[14]["t1"] + 0.25                   # Claude's agent run starts
STARS = [90, 97, 104, 112, 119, 126, 133, 140]
mon = [(0.0, "term_push"), (L[6]["t0"] - 0.25, "repo_90"),
       (mash0 + 0.9, "keys_revoked"), (mash0 + 1.6, "keys_new"), (mash0 + 2.3, "term_push2")]
mon += [(stars0 + 0.25 * i, f"repo_{s}") for i, s in enumerate(STARS)]
checks = [agent0 + 0.55 + 0.5 * i for i in range(4)]
mon += [(agent0, "agent_0")] + [(t, f"agent_{i + 1}") for i, t in enumerate(checks)]
phone = [(0.0, "phone_off"), (buzz, "phone_alert")]
ev = dict(buzz=fr(buzz), mash0=fr(mash0), mash1=fr(mash1), stars0=fr(stars0), agent0=fr(agent0), checks=[fr(t) for t in checks])
json.dump(dict(fps=FPS, end=int(end_t * FPS), lines=lines, ev=ev,
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


sfx = []
# phone buzz: two rattly pulses
t = np.arange(int(SR * 1.2)) / SR
pulse = ((t % 0.6) < 0.42).astype(float)
pulse = np.convolve(pulse, np.ones(480) / 480, "same")
buzz_w = 0.22 * pulse * (np.sin(2 * np.pi * 155 * t) + 0.5 * np.sin(2 * np.pi * 310 * t)) * (0.75 + 0.25 * np.sin(2 * np.pi * 31 * t))
wav_out("sfx_buzz", buzz_w)
sfx.append(("sfx_buzz", buzz))
# key mashing: dense random clicks
n = int(SR * (mash1 - mash0))
x = np.zeros(n)
p = 0
while p < n - 2000:
    a = rnd.uniform(0.10, 0.30)
    k = np.arange(500)
    x[p:p + 500] += a * np.diff(np.random.default_rng(p).standard_normal(501)) * np.exp(-k / 70)
    x[p:p + 500] += a * 0.6 * np.sin(2 * np.pi * rnd.uniform(1800, 2600) * k / SR) * np.exp(-k / 40)
    p += int(SR * rnd.uniform(0.035, 0.085))
wav_out("sfx_mash", x)
sfx.append(("sfx_mash", mash0))
# star ticks and agent check dings
wav_out("sfx_tick", tone(2400, 0.06, 0.16, 70) + tone(3600, 0.06, 0.06, 90))
for i in range(1, len(STARS)):
    sfx.append(("sfx_tick", stars0 + 0.25 * i))
wav_out("sfx_ding", tone(1320, 0.5, 0.13, 9) + tone(1980, 0.5, 0.07, 12))
for tc in checks:
    sfx.append(("sfx_ding", tc))

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
