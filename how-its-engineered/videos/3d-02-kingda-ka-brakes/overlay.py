"""words.json + labels.json -> audio/overlay.ass: phrase captions, tracked 3D callouts, the launch speed HUD and
view tags. python3 overlay.py"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(os.path.join(HERE, "audio/words.json")))
LB = json.load(open(os.path.join(HERE, "labels.json")))
FPS = 30
WHITE, AMBER, CYAN, COPPER = "&HFFFFFF&", "&H1A6AFF&", "&HFFE319&", "&H5A83D0&"   # ASS colours are BGR

CHUNKS = [(0, 7), (8, 13), (14, 19), (20, 25), (26, 31), (32, 36), (37, 40), (41, 44), (45, 47), (48, 54), (55, 60),
          (61, 63), (64, 65), (66, 71), (72, 74), (75, 80), (81, 82), (83, 85), (86, 88), (89, 93), (94, 98),
          (99, 104), (105, 112)]
SHOW = {2: "", 3: "", 4: "128", 5: "mph,", 6: "", 7: "", 9: "3.5", 10: "", 11: "", 12: ""}
COL = {4: AMBER, 5: AMBER, 9: AMBER, 13: AMBER, 24: AMBER, 39: CYAN, 40: CYAN, 46: COPPER, 47: COPPER, 58: CYAN,
       64: CYAN, 65: CYAN, 73: CYAN, 74: CYAN, 80: AMBER, 82: CYAN, 85: CYAN, 88: CYAN, 99: COPPER, 100: COPPER}
CALLOUTS = {"height": "456 FT TALL", "pads": "BRAKE PADS", "magnets": "RARE-EARTH MAGNETS", "fins": "COPPER FINS",
            "eddy": "EDDY CURRENTS", "motion": "MAGNET MOVES", "drag": "MAGNETIC DRAG"}
SPEED = {"drag": 2.2}       # callouts on screen briefly animate faster
TAGS = [(19.8, 23.8, "X-RAY VIEW"), (28.75, 29.95, "THERMAL VIEW")]


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


head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans,56,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,150,150,380,1
Style: Lbl,Noto Sans,44,&H00FFFFFF,&H00FFFFFF,&H00100A06,&HA0000000,-1,0,0,0,100,100,3,0,1,3,1,7,0,0,0,1
Style: Ln,Noto Sans,20,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,7,0,0,0,1
Style: Hud,JetBrainsMono Nerd Font,150,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,8,0,0,0,1
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
    for p in LB[key][1:]:             # stop the track at a whip pan (a jump on screen)
        if abs(p[1] - pts[-1][1]) + abs(p[2] - pts[-1][2]) > 40:
            break
        pts.append(p)
    flip = pts[0][1] > 600            # anchor on the right half: lead out to the left
    n = len(pts)
    sp = SPEED.get(key, 1.0)
    for j, (f, x, y) in enumerate(pts):
        t0, t1 = (f - 1) / FPS, f / FPS
        age, left = j / FPS * sp, (n - 1 - j) / FPS * sp
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

# launch HUD: speed counter and launch clock
hud = LB["hud"]
for j, (f, mph, tl) in enumerate(hud):
    t0, t1 = (f - 1) / FPS, f / FPS
    fade = min(1.0, (len(hud) - 1 - j) / 6)
    al = f"&H{int(255 * (1 - fade)):02X}&"
    ev.append(f"Dialogue: 4,{ts(t0)},{ts(t1)},Hud,,0,0,0,,{{\\an8\\pos(540,250)\\alpha{al}}}"
              f"{{\\c{AMBER if mph > 120 else WHITE}}}{mph:.0f}{{\\c{WHITE}\\fs44\\fnNoto Sans}} MPH")
    ev.append(f"Dialogue: 4,{ts(t0)},{ts(t1)},Tag,,0,0,0,,{{\\an8\\pos(540,430)\\alpha{al}\\fs30}}"
              f"T+ {tl:4.2f} S")

for a, b, text in TAGS:
    ev.append(f"Dialogue: 4,{ts(a + 0.05)},{ts(b - 0.05)},Tag,,0,0,0,,{{\\an7\\pos(72,250)\\fad(120,120)}}"
              f"{{\\c{CYAN}}}●{{\\c{WHITE}}} {text}")

out = os.path.join(HERE, "audio/overlay.ass")
open(out, "w").write(head + "\n".join(ev) + "\n")
print("wrote", out, len(ev))
