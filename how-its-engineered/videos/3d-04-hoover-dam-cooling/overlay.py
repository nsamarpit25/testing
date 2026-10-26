"""words.json + labels_hd.json -> audio/overlay.ass: phrase captions, tracked 3D callouts, view tags and the thermal
scale bar during the thermal shots. python3 overlay.py"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(os.path.join(HERE, "audio/words.json")))
LB = json.load(open(os.path.join(HERE, "labels_hd.json")))
FPS = 30
WHITE, AMBER, CYAN, GOLD, ICE = "&HFFFFFF&", "&H1A6AFF&", "&HFFD62F&", "&H5AC4FF&", "&HFFE6BF&"   # BGR

CHUNKS = [(0, 4), (5, 9), (10, 13), (14, 16), (17, 20), (21, 24), (25, 27), (28, 30), (31, 34), (35, 37), (38, 39),
          (40, 44), (45, 49), (50, 52), (53, 55), (56, 60), (61, 63), (64, 67), (68, 71), (72, 73), (74, 77),
          (78, 82), (83, 85), (86, 89), (90, 93)]
SHOW = {0: "125", 1: "", 2: "", 3: "", 42: "1-inch", 46: "580", 47: "", 48: "", 81: "2"}
COL = {0: AMBER, 4: AMBER, 15: AMBER, 22: AMBER, 23: AMBER, 26: CYAN, 27: CYAN, 30: AMBER, 36: GOLD, 37: GOLD,
       42: CYAN, 43: CYAN, 44: CYAN, 46: AMBER, 49: AMBER, 50: CYAN, 51: CYAN, 54: ICE, 55: ICE, 66: GOLD, 67: GOLD,
       68: GOLD, 75: GOLD, 76: GOLD, 81: AMBER, 82: AMBER, 85: AMBER}
CALLOUTS = {"core": "HOT CORE", "skin": "COOLING SKIN", "col": "COLUMN · 5 FT LIFTS", "coil": "1-INCH STEEL PIPE",
            "grout": "GROUT"}
TAGS = [(4.6, 11.25, "THERMAL VIEW", AMBER), (13.25, 22.65, "X-RAY VIEW", CYAN), (22.65, 26.0, "THERMAL VIEW", AMBER)]
THERMAL = [(0.0, "05010f"), (0.22, "2a0b5c"), (0.42, "8e0f4a"), (0.58, "d8242a"), (0.72, "ff6a0e"), (0.85, "ffb21c"),
           (0.94, "ffe9a0"), (1.0, "fffaf0")]


def quad(x0, y0, x1, y1, w=1.6):
    """a thin filled bar from (x0, y0) to (x1, y1): ASS drawings are filled shapes, so lines are drawn as quads"""
    dx, dy = x1 - x0, y1 - y0
    n = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    px, py = -dy / n * w, dx / n * w
    return (f"m {x0 + px:.1f} {y0 + py:.1f} l {x1 + px:.1f} {y1 + py:.1f} l {x1 - px:.1f} {y1 - py:.1f} "
            f"l {x0 - px:.1f} {y0 - py:.1f}")


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ramp(u):
    for (a, ca), (b, cb) in zip(THERMAL, THERMAL[1:]):
        if u <= b:
            k = (u - a) / (b - a)
            rgb = [int(int(ca[i:i + 2], 16) * (1 - k) + int(cb[i:i + 2], 16) * k) for i in (0, 2, 4)]
            return f"&H{rgb[2]:02X}{rgb[1]:02X}{rgb[0]:02X}&"
    return "&HF0FAFF&"


head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans,56,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,150,150,380,1
Style: Lbl,Noto Sans,40,&H00FFFFFF,&H00FFFFFF,&H00100A06,&HA0000000,-1,0,0,0,100,100,3,0,1,3,1,7,0,0,0,1
Style: Ln,Noto Sans,20,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,7,0,0,0,1
Style: Tag,Noto Sans,38,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H00000000,-1,0,0,0,100,100,6,0,1,2.5,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []

# phrase captions
for k, (a, b) in enumerate(CHUNKS):
    t0 = W[a][1] - 0.05
    end = W[b][2] + 0.25
    if k + 1 < len(CHUNKS):
        nxt = W[CHUNKS[k + 1][0]][1] - 0.05
        end = nxt if nxt - W[b][2] < 0.6 else end
    words = []
    for i in range(a, b + 1):
        s = SHOW.get(i, W[i][0])
        if s:
            words.append(f"{{\\c{COL[i]}}}{s}{{\\c{WHITE}}}" if i in COL else s)
    ev.append(f"Dialogue: 0,{ts(t0)},{ts(end)},Cap,,0,0,0,,{{\\fad(60,60)}}{' '.join(words)}")

# tracked callouts: a dot on the anchor, a leader that draws on, then the text; one event per frame
for key, text in CALLOUTS.items():
    pts = LB[key][:1]
    for p in LB[key][1:]:             # stop the track at a jump on screen
        if abs(p[1] - pts[-1][1]) + abs(p[2] - pts[-1][2]) > 40:
            break
        pts.append(p)
    flip = pts[0][1] > 600            # anchor on the right half: lead out to the left
    n = len(pts)
    for j, (f, x, y) in enumerate(pts):
        t0, t1 = (f - 1) / FPS, f / FPS
        age, left = j / FPS, (n - 1 - j) / FPS
        a = min(1.0, age / 0.25, left / 0.2 + 0.0001)
        alpha = f"&H{int(255 * (1 - max(a, 0))):02X}&"
        grow = min(1.0, age / 0.35)
        dx, dy, run = (-70, -110, -230) if flip else (70, -110, 230)
        ex, ey = dx * grow, dy * grow
        hx = run * max(0.0, min(1.0, (age - 0.2) / 0.3))
        path = quad(0, 0, ex, ey) + (" " + quad(ex, ey, ex + hx, ey) if hx else "")
        ev.append(f"Dialogue: 2,{ts(t0)},{ts(t1)},Ln,,0,0,0,,{{\\pos({x:.1f},{y:.1f})\\alpha{alpha}\\bord2\\3c&H100A06&"
                  f"\\p1}}m -8 0 b -8 -10.5 8 -10.5 8 0 b 8 10.5 -8 10.5 -8 0{{\\p0}}")
        ev.append(f"Dialogue: 1,{ts(t0)},{ts(t1)},Ln,,0,0,0,,{{\\pos({x:.1f},{y:.1f})\\alpha{alpha}\\bord1.2"
                  f"\\3c&H100A06&\\p1}}{path}{{\\p0}}")
        if age > 0.3:
            ta = min(a, (age - 0.3) / 0.25)
            talpha = f"&H{int(255 * (1 - max(ta, 0))):02X}&"
            an, tx = (3, x + dx - 6) if flip else (1, x + dx + 6)
            ev.append(f"Dialogue: 3,{ts(t0)},{ts(t1)},Lbl,,0,0,0,,{{\\an{an}\\pos({tx:.1f},{y + dy - 10:.1f})"
                      f"\\alpha{talpha}}}{text}")

for a, b, text, col in TAGS:
    ev.append(f"Dialogue: 4,{ts(a + 0.05)},{ts(b - 0.05)},Tag,,0,0,0,,{{\\an7\\pos(72,250)\\fad(120,120)}}"
              f"{{\\c{col}}}●{{\\c{WHITE}}} {text}")

# thermal scale: a vertical bar on the right, cold at the bottom
X0, Y0, BW, BH, NS = 960, 520, 26, 640, 64
for a, b, text, col in TAGS:
    if text != "THERMAL VIEW":
        continue
    fd = "\\fad(150,120)"
    t0, t1 = ts(a + 0.05), ts(b - 0.05)
    for i in range(NS):
        u = (i + 0.5) / NS
        y1 = Y0 + BH * (1 - i / NS)
        y0 = Y0 + BH * (1 - (i + 1) / NS) - 0.6
        ev.append(f"Dialogue: 4,{t0},{t1},Ln,,0,0,0,,{{\\pos(0,0){fd}\\bord0\\1c{ramp(u)}\\p1}}"
                  f"m {X0} {y0:.1f} l {X0 + BW} {y0:.1f} l {X0 + BW} {y1:.1f} l {X0} {y1:.1f}{{\\p0}}")
    ev.append(f"Dialogue: 5,{t0},{t1},Tag,,0,0,0,,{{\\an2\\pos({X0 + BW // 2},{Y0 - 14})\\fs26{fd}}}HOT")
    ev.append(f"Dialogue: 5,{t0},{t1},Tag,,0,0,0,,{{\\an8\\pos({X0 + BW // 2},{Y0 + BH + 14})\\fs26{fd}}}COOL")

out = os.path.join(HERE, "audio/overlay.ass")
open(out, "w").write(head + "\n".join(ev) + "\n")
print("wrote", out, len(ev))
