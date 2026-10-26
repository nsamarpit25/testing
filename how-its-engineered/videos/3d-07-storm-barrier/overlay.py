"""words.json + labels_sb.json -> audio/overlay.ass: phrase captions, tracked 3D callouts, the 210 m and 10 m dimensions and the x-ray view tags. python3 overlay.py"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(os.path.join(HERE, "audio/words.json")))
LB = json.load(open(os.path.join(HERE, "labels_sb.json")))
FPS = 30
WHITE, AMBER, CYAN, GOLD, TEAL = "&HFFFFFF&", "&H1A6AFF&", "&HFFD62F&", "&H5AC4FF&", "&HC8E05A&"   # BGR

CHUNKS = [(0, 3), (4, 9), (10, 13), (14, 17), (18, 20), (21, 26), (27, 30), (31, 33), (34, 38), (39, 41), (42, 46),
          (47, 50), (51, 53), (54, 56), (57, 59), (60, 64), (65, 68), (69, 72), (73, 77), (78, 81), (82, 84), (85, 87),
          (88, 91), (92, 95)]
SHOW = {7: "3", 21: "210", 22: "", 23: "", 24: "", 54: "10", 55: "metres"}
COL = {2: AMBER, 7: AMBER, 8: AMBER, 9: AMBER, 15: CYAN, 16: CYAN, 17: CYAN, 21: GOLD, 25: GOLD, 32: TEAL, 33: TEAL,
       36: AMBER, 41: CYAN, 44: CYAN, 46: CYAN, 52: GOLD, 53: GOLD, 54: GOLD, 55: GOLD, 61: CYAN, 63: CYAN, 65: CYAN,
       71: GOLD, 72: GOLD, 76: AMBER, 77: AMBER, 83: CYAN, 84: CYAN, 87: TEAL}
CALLOUTS = {"plus3": "+3 M", "dock": "DRY DOCK", "sea": "NORTH SEA", "bed": "RIVERBED"}
STATS = []
TAGS = [(12.75, 14.94, "X-RAY VIEW", CYAN), (19.4, 21.1, "X-RAY VIEW", CYAN), (24.8, 25.8, "X-RAY VIEW", CYAN)]
DIMS = [("g0", "g1", "210 M"), ("b0", "b1", "10 M")]


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
    on = [p for p in LB[key] if 60 < p[1] < 1020 and 200 < p[2] < 1700]
    pts = on[:1]
    for p in on[1:]:             # stop the track at a jump on screen
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


# dimensions: a line between two anchors with end ticks, drawn on left to right, the figure above it
for k0, k1, txt in DIMS:
    P0, P1 = {f: (x, y) for f, x, y in LB[k0]}, {f: (x, y) for f, x, y in LB[k1]}
    fr = sorted(set(P0) & set(P1))
    for j, f in enumerate(fr):
        t0, t1 = (f - 1) / FPS, f / FPS
        age, left = j / FPS, (len(fr) - 1 - j) / FPS
        a = max(0.0, min(1.0, age / 0.2, left / 0.2))
        alpha = f"&H{int(255 * (1 - a)):02X}&"
        (bx, by), (tx, ty) = sorted((P0[f], P1[f]))
        g = min(1.0, max(0.0, (age - 0.1) / 0.45))
        ex, ey = bx + (tx - bx) * g, by + (ty - by) * g
        nx, ny = -(ty - by), tx - bx
        nn = max((nx * nx + ny * ny) ** 0.5, 1e-6)
        nx, ny = nx / nn * 18, ny / nn * 18
        path = (quad(bx - nx, by - ny, bx + nx, by + ny) + " " + quad(bx, by, ex, ey)
                + (" " + quad(tx - nx, ty - ny, tx + nx, ty + ny) if g >= 1 else ""))
        ev.append(f"Dialogue: 2,{ts(t0)},{ts(t1)},Ln,,0,0,0,,{{\\pos(0,0)\\alpha{alpha}\\bord1.2\\3c&H100A06&"
                  f"\\1c{GOLD}\\p1}}{path}{{\\p0}}")
        if g > 0.6:
            ta = min(a, (g - 0.6) / 0.3)
            ev.append(f"Dialogue: 3,{ts(t0)},{ts(t1)},Lbl,,0,0,0,,{{\\an2\\pos({(bx + tx) / 2:.1f},{min(by, ty) - 18:.1f})"
                      f"\\fs60\\alpha&H{int(255 * (1 - max(ta, 0))):02X}&}}{{\\c{GOLD}}}{txt}")

for a, b, text, col in STATS:
    ev.append(f"Dialogue: 4,{ts(a)},{ts(b)},Lbl,,0,0,0,,{{\\an5\\pos(540,620)\\fs96\\bord5\\fad(150,150)}}"
              f"{{\\c{col}}}{text}")

for a, b, text, col in TAGS:
    ev.append(f"Dialogue: 4,{ts(a + 0.05)},{ts(b - 0.05)},Tag,,0,0,0,,{{\\an7\\pos(72,250)\\fad(120,120)}}"
              f"{{\\c{col}}}●{{\\c{WHITE}}} {text}")

out = os.path.join(HERE, "audio/overlay.ass")
open(out, "w").write(head + "\n".join(ev) + "\n")
print("wrote", out, len(ev))
