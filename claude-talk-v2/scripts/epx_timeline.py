"""Generic timeline (Ep 7 on): voice lines + the episode's direct.json -> timeline.json for blender/epx.py, mix.wav and
subs.ass (captions phrase by phrase, word by word, as ep6_timeline.py).

python3 scripts/epx_timeline.py audio/ep7

direct.json:
  look      {base: night|sunset|morning, colors: {material: hex}}      the room's look (blender/epx.py)
  lead, gap, hold, fade, black      seconds: before line 1, between lines, after the last line, its fade, the black tail
  beats     {"n": s}      extra pause before line n
  open      [shot, cleo-cmd...]   the first shot and what Cleo does before line 1 (default CLEO, typing)
  lines     {"n": {shot, cut, cleo: [cmd...], claude: [cmd...], auto}}   per line; cmd = "<when> <command> <args>"
  cuts      [[when, cam]]          extra cuts (inserts); the next line's shot cuts back
  mon       [[when, screen]]       monitor pictures (screens/<name>.png); phone the same, pglow follows phone_off or not
  sfx       [[when, kind]]         click | type | buzz | softbuzz | chime | pop | error | ding | whoosh
  glow      {screen: [r, g, b, energy]}   monitor glow per picture (default by brightness)
  lights    [[when, room|moon|claude, value, ramp s]]   a power cut, lightning: room/moon scale their lamps, claude = his glow (W)
  bed       "rain"                 a quiet rain bed under the whole reel;  pglow: phone glow when its screen is on (0.6)
  rain      {speed, density, alpha}   slow streaks of rain outside the window (blender/epx.py build_rain)
when: "t1.2" absolute seconds; "7" line 7 start; "7.w3" its 4th word (0-based); "7.end"; "7.gap" (mid gap before it);
"7.u0.5" fraction through it; any of them + or - seconds ("7.w3-0.1").  Commands: see blender/epx.py.
"""
import audioop, json, re, subprocess, sys, wave
import numpy as np

d = sys.argv[1]
D = json.load(open(f"{d}/direct.json"))
FPS, SR = 30, 48000
LEAD, GAP, HOLD = D.get("lead", 1.0), D.get("gap", 0.45), D.get("hold", 1.3)
FADE, TAIL = D.get("fade", 0.9), D.get("black", 0.5)


def envelope(wav):
    w = wave.open(wav)
    sw = w.getsampwidth()
    data = w.readframes(w.getnframes())
    hop = w.getframerate() // FPS
    rms = [audioop.rms(data[i * hop * sw:(i + 1) * hop * sw], sw) for i in range(len(data) // (hop * sw) + 1)]
    ref = sorted(rms)[int(len(rms) * 0.9)] or 1
    v = [min(r / ref, 1.0) for r in rms]
    v = [sum(v[max(0, i - 1):i + 2]) / len(v[max(0, i - 1):i + 2]) for i in range(len(v))]
    out, y = [], 0.0
    for x in v:
        x = 0.0 if x < 0.18 else min((x - 0.18) / 0.6, 1.0)
        y += (x - y) * (0.6 if x > y else 0.4)
        out.append(round(y, 3))
    return out


rows = [l.split() for l in open(f"{d}/durs.txt")]
texts = [l.rstrip("\n").split("\t") for l in open(f"{d}/lines.tsv")]
W_ = json.load(open(f"{d}/words.json"))
t, lines = LEAD, []
for (n, who, dur), (_, txt) in zip(rows, texts):
    n, dur = int(n), float(dur)
    t += D.get("beats", {}).get(str(n), 0)
    lines.append(dict(n=n, who=who, t0=round(t, 3), t1=round(t + dur, 3), f0=int(t * FPS) + 1, f1=int((t + dur) * FPS) + 1,
                      text=txt, env=envelope(f"{d}/l{n:02d}.wav")))
    t += dur + GAP
L = {x["n"]: x for x in lines}
last = lines[-1]["n"]
end_t = lines[-1]["t1"] + HOLD
fr = lambda s: int(round(s * FPS)) + 1


def when(s):
    """a time spec -> seconds"""
    m = re.fullmatch(r"(t[\d.]+|\d+(?:\.(?:w\d+|end|gap|u[\d.]+))?)([+-][\d.]+)?", s.strip())
    if not m:
        raise SystemExit(f"bad time spec {s!r}")
    base, off = m.group(1), float(m.group(2) or 0)
    if base.startswith("t"):
        return float(base[1:]) + off
    n, _, part = base.partition(".")
    x = L[int(n)]
    if not part:
        v = x["t0"]
    elif part == "end":
        v = x["t1"]
    elif part == "gap":
        i = [y["n"] for y in lines].index(x["n"])
        v = ((lines[i - 1]["t1"] if i else 0.0) + x["t0"]) / 2
    elif part[0] == "u":
        v = x["t0"] + float(part[1:]) * (x["t1"] - x["t0"])
    else:
        v = x["t0"] + W_[str(x["n"])][int(part[1:])][1]
    return v + off


def cmd_list(items):
    """["7.w3 look monitor 8", ...] -> [[frame, cmd, args...]] (numbers parsed)"""
    out = []
    for it in items:
        w, c, *a = it.split()
        a = [float(x) if re.fullmatch(r"-?[\d.]+", x) else x for x in a]
        f = fr(when(w))
        if c == "typing" and a:  # typing <seconds> [step]
            a[0] = f + int(a[0] * FPS)
        out.append([f, c, *a])
    return out


# ---------------------------------------------------------------- acting: per-line defaults, unless the line directs them
cleo, claude = [], []
CLEO_CH = {"look": "look", "hands": "hands", "typing": "hands", "lean": "lean", "smile": "smile", "brow": "brow"}
CLAUDE_CH = {"face": "face", "tilt": "tilt", "lean": "lean", "nod": "lean", "nod2": "lean", "hop": "hop", "puff": "puff", "shake": "face"}
op = D.get("open", ["CLEO", "t0.05 typing", "t0.0 look monitor 1"])
cuts = [[1, op[0]]]
cleo += cmd_list([c.replace("<f0>", "") for c in op[1:]])
# before line 1 she types (if the opening says so) up to just before she turns to him
for c in cleo:
    if c[1] == "typing" and len(c) == 2:
        c.append(L[lines[0]["n"]]["f0"] - 10)
claude += [[1, "face", "mon", 1]]
k_open, k_tilt = 0, 1
for x in lines:
    n, who, f0, f1 = x["n"], x["who"], x["f0"], x["f1"]
    spec = D["lines"].get(str(n), {})
    nw = len(x["text"].split())
    c_ex = cmd_list(spec.get("cleo", []))
    a_ex = cmd_list(spec.get("claude", []))
    c_has = {CLEO_CH[c[1]] for c in c_ex}
    a_has = {CLAUDE_CH[c[1]] for c in a_ex}
    cleo += c_ex
    claude += a_ex
    cuts.append([fr(when(spec["cut"])) if "cut" in spec else f0 - 4, spec.get("shot", "CLEO" if who == "cleo" else "CLAUDE")])
    if not spec.get("auto", True):
        continue
    if who == "cleo":
        if "look" not in c_has:
            cleo.append([f0 - 6, "look", "claude", 10])
        if "hands" not in c_has and nw >= 5:
            k_open += 1
            if k_open % 2:
                cleo += [[f0 + int(0.25 * (f1 - f0)), "hands", "open", 10], [f1 + 4, "hands", "rest", 12]]
        if "brow" not in c_has:
            cleo.append([f0, "brow", 0.004 + 0.003 * (n % 2), 8])
        if "face" not in a_has:
            claude.append([f0 - 2, "face", "her", 10])
        if "tilt" not in a_has:
            k_tilt = -k_tilt or 1
            claude.append([f0 + int(0.4 * (f1 - f0)), "tilt", 0.08 * k_tilt, 12])
        if "lean" not in a_has:
            claude.append([f0, "lean", 0.0, 10])
    else:
        if "face" not in a_has:
            claude.append([f0 - 6, "face", "her", 8])
        if "lean" not in a_has:
            claude.append([f0, "lean", 0.06, 8])
            if nw >= 4:
                claude.append([f0 + int(0.5 * (f1 - f0)), "nod"])
            claude.append([f1 + 2, "lean", 0.0, 10])
        if "tilt" not in a_has:
            claude.append([f0, "tilt", 0.0, 8])
        if "look" not in c_has:
            cleo.append([f0 - 2, "look", "claude", 8])
        if "hands" not in c_has:
            cleo.append([f0 + 2, "hands", "rest", 12])
cuts += [[fr(when(w)), cam] for w, cam in D.get("cuts", [])]
cleo += cmd_list(D.get("tail_cleo", []))
claude += cmd_list(D.get("tail_claude", []))
# blinks: a steady rhythm plus one in each pause the other one speaks through
blinks = list(range(25, fr(end_t), 97)) + [int((x["f0"] + x["f1"]) / 2) for x in lines if x["who"] == "claude"]
cblinks = list(range(40, fr(end_t), 83)) + [int((x["f0"] + x["f1"]) / 2) + 3 for x in lines if x["who"] == "cleo"][::2]

# ---------------------------------------------------------------- screens
mon = [[fr(when(w)) if w != "0" else 1, s] for w, s in D["mon"]]
phone = [[fr(when(w)) if w != "0" else 1, s] for w, s in D.get("phone", [["0", "phone_off"]])]
pglow = [[f, 0.0 if s == "phone_off" else D.get("pglow", 0.6)] for f, s in phone]
board = [[fr(when(w)) if w != "0" else 1, s] for w, s in D.get("board", [])]  # Claude's whiteboard pictures, if he has one
GL = D.get("glow", {})
glow = [[f, GL.get(s, [0.62, 0.70, 1.0, 0.9])[:3], GL.get(s, [0, 0, 0, 0.9])[3]] for f, s in mon]

# ---------------------------------------------------------------- sound effects, synthesized
rnd = np.random.default_rng(7)


def wav_out(name, x):
    x = np.clip(x, -1, 1)
    w = wave.open(f"{d}/{name}.wav", "w")
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
    w.writeframes((x * 32767).astype("<i2").tobytes())
    w.close()


def tone(f, dur, amp, decay):
    tt = np.arange(int(SR * dur)) / SR
    return amp * np.sin(2 * np.pi * f * tt) * np.exp(-tt * decay)


def click(amp=0.16):
    k = np.arange(int(SR * 0.03))
    return amp * (rnd.uniform(-1, 1, len(k)) * np.exp(-k / 90) + 0.6 * np.sin(2 * np.pi * 2400 * k / SR) * np.exp(-k / 120))


def typing_sfx(dur=1.4):
    x = np.zeros(int(SR * (dur + 0.1)))
    p = 0.0
    while p < dur:
        c = click(0.05 + 0.02 * rnd.random())
        x[int(p * SR):int(p * SR) + len(c)] += c
        p += rnd.uniform(0.07, 0.16)
    return x


def buzz():
    tt = np.arange(int(SR * 0.9)) / SR
    ph = tt % 0.45  # two 0.28 s pulses; 25 ms ramps so each pulse starts and stops without a click
    gate = np.clip(np.minimum(ph, 0.28 - ph) / 0.025, 0, 1) * (ph < 0.28)
    return 0.10 * np.sign(np.sin(2 * np.pi * 150 * tt)) * gate * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt))


def softbuzz():  # phone vibrating on a wooden desk: the buzz with its edge filtered off, for quiet scenes
    return 0.6 * lowpass(lowpass(buzz(), 0.06), 0.12)


def chime():  # a soft two-note message chime (the "ding" is too sharp under dialogue)
    def note(f, dur, at):
        tt = np.arange(int(SR * dur)) / SR
        return np.pad(np.minimum(tt / 0.012, 1) * np.exp(-tt * 9) * (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)), (int(SR * at), 0))
    a, b = note(1046.5, 0.5, 0), note(1318.5, 0.6, 0.11)
    a = np.pad(a, (0, len(b) - len(a)))
    return 0.022 * lowpass(a + b, 0.5)


def lowpass(x, a):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):  # one-pole; fine for the few seconds these need
        acc += a * (v - acc); y[i] = acc
    return y


def thunder():
    n = int(SR * 3.2); tt = np.arange(n) / SR
    rumble = lowpass(lowpass(rnd.standard_normal(n), 0.02), 0.05)
    rumble /= np.abs(rumble).max() + 1e-9
    env = np.minimum(tt / 0.08, 1) * np.exp(-tt * 1.1) * (1 + 0.5 * np.sin(2 * np.pi * 1.7 * tt) ** 2)
    crack = lowpass(rnd.standard_normal(n), 0.3) * np.exp(-tt * 9) * 0.4
    return 0.30 * (rumble * env + crack * np.minimum(tt / 0.01, 1))


def powerdown():
    n = int(SR * 0.7); tt = np.arange(n) / SR
    hum = np.sin(2 * np.pi * np.cumsum(110 - 80 * np.minimum(tt / 0.6, 1)) / SR) * np.exp(-tt * 4)
    return 0.07 * hum + np.pad(click(0.12), (0, n - len(click())))[:n]


def powerup():
    n = int(SR * 0.9); tt = np.arange(n) / SR
    hum = np.sin(2 * np.pi * 60 * tt) * np.minimum(tt / 0.3, 1) * np.exp(-np.maximum(tt - 0.4, 0) * 5)
    whine = np.sin(2 * np.pi * np.cumsum(2000 + 4000 * np.minimum(tt / 0.5, 1)) / SR) * np.exp(-tt * 6)
    return 0.05 * hum + 0.012 * whine + np.pad(click(0.10), (0, n - len(click())))[:n]


def rain(dur):
    n = int(SR * dur); tt = np.arange(n) / SR
    x = rnd.standard_normal(n)
    hiss = lowpass(x, 0.35) - lowpass(x, 0.02)  # band-limited: no rumble, no fizz
    drops = np.zeros(n)
    for p in rnd.integers(0, n - 400, int(dur * 10)):
        drops[p:p + 400] += rnd.uniform(0.2, 1) * np.exp(-np.arange(400) / 60) * rnd.standard_normal(400)
    y = hiss / (np.sqrt((hiss ** 2).mean()) + 1e-9) + 0.3 * drops
    return 0.0011 * y * np.minimum(tt / 1.0, 1)  # 5% of the first version's level (owner: rain only a hint) * np.clip((dur - tt) / 1.0, 0, 1)


SFX = {"click": lambda: click(0.16), "thunder": thunder, "powerdown": powerdown, "powerup": powerup, "type": typing_sfx, "buzz": buzz, "softbuzz": softbuzz, "chime": chime, "pop": lambda: tone(880, 0.25, 0.10, 14),
       "error": lambda: np.concatenate([tone(330, 0.22, 0.13, 6), tone(262, 0.35, 0.13, 6)]),
       "ding": lambda: tone(1320, 0.8, 0.09, 5) + tone(1980, 0.8, 0.04, 7),
       "whoosh": lambda: 0.08 * rnd.standard_normal(int(SR * 0.4)) * np.sin(np.linspace(0, np.pi, int(SR * 0.4))) ** 2}
sfx = []
for i, (w, kind) in enumerate(D.get("sfx", [])):
    nm = f"sfx_{i:02d}_{kind}"
    wav_out(nm, SFX[kind]())
    sfx.append((nm, when(w)))
if D.get("bed") == "rain":  # a quiet rain bed under the whole reel
    wav_out("bed_rain", rain(end_t + TAIL))
    sfx.append(("bed_rain", 0.0))
# lights [[when, target, value, ramp seconds]]: room / moon as a fraction of their built level, claude = his glow in watts
lights = [[fr(when(w)) if w != "0" else 1, tgt, float(v), int(round(float(r[0] if r else 0) * FPS))] for w, tgt, v, *r in D.get("lights", [])]

json.dump(dict(fps=FPS, end=fr(end_t) - 1, lines=lines, look=D.get("look", {}), cuts=cuts, cleo=cleo, claude=claude,
               blinks=blinks, cblinks=cblinks, mon=mon, phone=phone, glow=glow, pglow=pglow, board=board, lights=lights, rain=D.get("rain"), fade=FADE, tail=TAIL),
          open(f"{d}/timeline.json", "w"))

srcs = [(f"{d}/l{x['n']:02d}.wav", x["t0"]) for x in lines] + [(f"{d}/{nm}.wav", tt) for nm, tt in sfx]
ins = sum([["-i", s] for s, _ in srcs], [])
for s, _ in srcs:  # a voice take that ends mid-word sounds chopped; the edge fades below hide the click, not the missing word
    w = wave.open(s); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    tail = a[-int(w.getframerate() * w.getnchannels() * 0.02):]
    if 20 * np.log10(np.sqrt((tail ** 2).mean()) + 1e-7) > -35:
        print(f"WARNING {s}: ends at full volume (chopped take?) - re-take or trim at a pause")
EDGE = "afade=t=in:d=0.005,areverse,afade=t=in:d=0.06,areverse"  # no hard starts/stops at clip edges
fl = ";".join(f"[{i}]aresample=48000,{EDGE},adelay={int(tt * 1000)}:all=1[a{i}]" for i, (_, tt) in enumerate(srcs))
# a silent bed from t=0: with the edge fades, adelay only shifts timestamps and amix started at the first line, so
# every voice played LEAD seconds early (Ep10-12). The bed pins the mix to the video's t=0.
ins += ["-f", "lavfi", "-t", f"{end_t + TAIL}", "-i", "anullsrc=r=48000:cl=mono"]
fl += f";[{len(srcs)}]anull[bed]"
fl += ";[bed]" + "".join(f"[a{i}]" for i in range(len(srcs))) + (f"amix=inputs={len(srcs) + 1}:normalize=0,atrim=0:{end_t},"
                                                            f"afade=t=out:st={end_t - FADE}:d={FADE},apad=whole_dur={end_t + TAIL}[out]")
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
Style: Cap,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,1.5,2,110,110,330,1
Style: Handle,Arial,34,&H28FFFFFF,&H28FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,1,0,1,0,1.5,2,60,60,114,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
HI = {"cleo": r"\c&H0066D9FF&", "claude": r"\c&H005A9AFF&"}
SAID, CUR, TODO = r"{\alpha&H00&\c&HFFFFFF&}", "{\\alpha&H00&%s}", r"{\alpha&HFF&}"
HOLD_CAP, JOIN = 0.35, 0.8
JOINERS = set("unless if and or but so because the a an to of for with your my his her its their than when while".split())


def phrases(ws):
    out, cur = [], []
    for w in ws:
        cur.append(w)
        text = " ".join(x[0] for x in cur)
        if len(cur) >= 2 and re.search(r'[.,?!;:—]["”]?$', w[0]):
            out.append(cur)
            cur = []
        elif len(cur) >= 6 or len(text) >= 30:  # a length break never leaves a joining word ("unless", "the") dangling
            keep = [cur.pop()] if len(cur) > 2 and cur[-1][0].lower() in JOINERS else []
            out.append(cur)
            cur = keep
    if cur:
        out.append(cur)
    merged = []  # a 1-2 word scrap joins the phrase before it when the two still fit on screen
    for i, p in enumerate(out):
        if merged and len(p) <= 2 and len(merged[-1]) + len(p) <= 7 and len(" ".join(x[0] for x in merged[-1] + p)) <= 40 \
                and (not re.search(r'[.?!]["”]?$', merged[-1][-1][0]) or (i == len(out) - 1 and len(p) == 1)):
            merged[-1] = merged[-1] + p
        else:
            merged.append(p)
    return merged


for li, x in enumerate(lines):
    hi = HI[x["who"]]
    ph = phrases(W_[str(x["n"])])
    nxt_line = lines[li + 1]["t0"] if li + 1 < len(lines) else 1e9
    for pi_, p in enumerate(ph):
        last_end = x["t0"] + p[-1][2]
        nxt = x["t0"] + ph[pi_ + 1][0][1] if pi_ + 1 < len(ph) else nxt_line
        e = nxt if nxt - last_end < JOIN else min(last_end + HOLD_CAP, nxt)
        e = min([e] + [(c[0] - 1) / FPS for c in cuts if (c[0] - 1) / FPS > last_end + 0.05])  # a held caption clears on the next cut
        for k, (w, a, b) in enumerate(p):
            t_a = x["t0"] + a
            t_b = x["t0"] + p[k + 1][1] if k + 1 < len(p) else last_end
            txt = " ".join((SAID if m < k else (CUR % hi) if m == k else TODO) + y[0] for m, y in enumerate(p))
            ass += f"Dialogue: 0,{ts(t_a)},{ts(max(t_b, t_a + 0.05))},Cap,,0,0,0,,{txt}\n"
        if e > last_end:
            ass += f"Dialogue: 0,{ts(last_end)},{ts(min(e, end_t - FADE))},Cap,,0,0,0,," + " ".join(SAID + y[0] for y in p) + "\n"
ass += f"Dialogue: 1,{ts(0)},{ts(end_t)},Handle,,0,0,0,,{{\\fad(0,{int(FADE * 1000)})}}@talkingagents\n"  # fades out with the picture, gone on the black tail
open(f"{d}/subs.ass", "w").write(ass)
print("end", round(end_t, 2), "s +", TAIL, "black;", fr(end_t) - 1, "frames")
for x in lines:
    print(x["n"], x["who"], x["f0"], x["f1"], x["text"])
print("cuts", sorted(cuts))
