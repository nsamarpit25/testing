"""Whiteboard pictures for Claude's desk board (1200x785, the board face's ratio) from <audio dir>/board.json:
{"name": [[op, ...], ...]}, drawn in marker strokes with a little wobble so they read as hand-drawn:
  ["text", x, y, "str", size, color]        centred at x, y
  ["box", x, y, w, h, color]                 centred rounded box
  ["arrow", x0, y0, x1, y1, color]
  ["x", x, y, size, color] | ["tick", x, y, size, color]
  ["line", x0, y0, x1, y1, color]
  ["cloud", x, y, w, color]                  a puffy cloud outline, centred, w wide
colors: black, blue, red, green, orange. Each picture is drawn on its own clean board (no build-up), so list every op.
python3 scripts/epx_board.py audio/ep15   -> audio/ep15/screens/<name>.png
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

d = sys.argv[1]
B = json.load(open(f"{d}/board.json"))
os.makedirs(f"{d}/screens", exist_ok=True)
W, H = 1200, 785
INK = {"black": (38, 42, 52), "blue": (28, 92, 196), "red": (214, 48, 49), "green": (34, 139, 68), "orange": (226, 110, 20)}
FONT = "/System/Library/Fonts/MarkerFelt.ttc"


def wob(rnd, pts, amp=2.2):
    return [(x + rnd.uniform(-amp, amp), y + rnd.uniform(-amp, amp)) for x, y in pts]


def stroke(dr, rnd, pts, col, w=9):
    p = wob(rnd, pts)
    dr.line(p, fill=col, width=w, joint="curve")
    for x, y in (p[0], p[-1]):  # round ends
        dr.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)


def seg(a, b, n=8):
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


for name, ops in B.items():
    rnd = random.Random(name)
    im = Image.new("RGB", (W, H), (247, 248, 246))
    dr = ImageDraw.Draw(im)
    for _ in range(5):  # faint ghosts of old erased drawings
        x, y = rnd.uniform(100, 1100), rnd.uniform(80, 700)
        dr.ellipse((x - 120, y - 40, x + 120, y + 40), fill=(238, 240, 238))
    for op in ops:
        k, a = op[0], op[1:]
        if k == "text":
            x, y, s, size, col = a
            f = ImageFont.truetype(FONT, int(size))
            dr.text((x, y), s, font=f, fill=INK[col], anchor="mm")
        elif k == "box":
            x, y, w, h, col = a
            l, t, r, b = x - w / 2, y - h / 2, x + w / 2, y + h / 2
            stroke(dr, rnd, seg((l, t), (r, t)) + seg((r, t), (r, b))[1:] + seg((r, b), (l, b))[1:] + seg((l, b), (l, t + 4))[1:], INK[col])
        elif k in ("arrow", "line"):
            x0, y0, x1, y1, col = a
            stroke(dr, rnd, seg((x0, y0), (x1, y1), 10), INK[col])
            if k == "arrow":
                ang = math.atan2(y1 - y0, x1 - x0)
                for s in (0.5, -0.5):
                    stroke(dr, rnd, [(x1, y1), (x1 - 34 * math.cos(ang + s), y1 - 34 * math.sin(ang + s))], INK[col])
        elif k == "cloud":  # the outline of a few overlapping puffs over a flat base, traced as one ray-cast loop
            x, y, w, col = a
            puffs = [(-0.28, 0.06, 0.18), (-0.08, -0.08, 0.24), (0.18, -0.03, 0.21), (0.33, 0.08, 0.14)]
            inside = lambda px, py: py <= 0.2 and (any((px - cx) ** 2 + (py - cy) ** 2 <= r * r for cx, cy, r in puffs) or (abs(px) <= 0.33 and py >= 0.0))
            pts = []
            for i in range(73):
                t, r = math.radians(i * 5), 0.0
                while r < 0.6 and inside(r * math.cos(t), r * math.sin(t)):
                    r += 0.004
                pts.append((x + r * math.cos(t) * w, y + r * math.sin(t) * w))
            stroke(dr, rnd, pts, INK[col])
        elif k == "x":
            x, y, s, col = a
            stroke(dr, rnd, [(x - s, y - s), (x + s, y + s)], INK[col], 11)
            stroke(dr, rnd, [(x + s, y - s), (x - s, y + s)], INK[col], 11)
        elif k == "tick":
            x, y, s, col = a
            stroke(dr, rnd, [(x - s, y), (x - s / 3, y + s * 0.7), (x + s, y - s * 0.8)], INK[col], 11)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(f"{d}/screens/{name}.png")
    print("board", name)
