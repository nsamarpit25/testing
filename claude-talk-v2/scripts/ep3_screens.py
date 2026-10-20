"""Screen images for episode 3 (monitor 1600x944, phone 600x1290), drawn with PIL.

Monitor: her working app, Claude's cleanup run (0..3 items done), the red runtime error, the terminal showing the last
commit was 3 hours ago, Claude rewinding to his checkpoint (0..2), and her commit. Phone: off (it plays no part).
Main content sits in the middle ~60% of the width so the close-up insert can crop the sides.
python3 scripts/ep3_screens.py [out dir]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "audio/ep3/screens"
os.makedirs(out, exist_ok=True)
W, H = 1600, 944
SF = "/Library/Fonts/SF-Pro-Display-%s.otf"
MONO = "/System/Library/Fonts/Menlo.ttc"


def font(size, w="Bold"):
    return ImageFont.truetype(SF % w, size)


def mono(size, bold=False):
    return ImageFont.truetype(MONO, size, index=1 if bold else 0)


BG, PANEL, LINE = (13, 17, 23), (22, 27, 34), (48, 54, 61)
TXT, DIM, GREEN, RED, AMBER, BLUE = (230, 237, 243), (139, 148, 158), (63, 185, 80), (248, 81, 73), (227, 179, 65), (88, 166, 255)
ORANGE = (217, 119, 87)
PURPLE, LILAC = (124, 92, 230), (238, 233, 255)


def check(d, cx, cy, r, fill):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
    w = max(3, int(r * 0.28))
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)], fill=BG, width=w, joint="curve")


def window(title, bg=BG, bar=PANEL):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 64), fill=bar)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + i * 38, 20, 48 + i * 38, 44), fill=c)
    d.text((W // 2, 32), title, font=font(30, "Medium"), fill=DIM, anchor="mm")
    return im, d


# her app: a little budget tracker in the browser, working
im, d = window("localhost:5173  —  Pocket Budget", bg=(250, 248, 255), bar=(225, 222, 235))
d.rectangle((0, 64, W, 190), fill=PURPLE)
d.text((W // 2, 127), "Pocket Budget", font=font(64), fill=(255, 255, 255), anchor="mm")
d.rounded_rectangle((330, 230, 1270, 420), 30, fill=LILAC)
d.text((W // 2, 290), "Left this month", font=font(40, "Medium"), fill=(110, 96, 160), anchor="mm")
d.text((W // 2, 365), "$1,284.50", font=font(96), fill=(60, 40, 140), anchor="mm")
for i, (name, amt) in enumerate((("Groceries", "-$62.10"), ("Coffee", "-$4.75"), ("Rent", "-$900.00"))):
    y = 470 + i * 105
    d.rounded_rectangle((330, y, 1270, y + 85), 20, fill=(255, 255, 255), outline=(225, 220, 240), width=3)
    d.text((380, y + 42), name, font=font(44, "Medium"), fill=(40, 36, 60), anchor="lm")
    d.text((1220, y + 42), amt, font=font(44, "Medium"), fill=(200, 70, 90), anchor="rm")
d.rounded_rectangle((560, 805, 1040, 885), 40, fill=GREEN)
d.text((W // 2, 845), "it works!", font=font(44), fill=(255, 255, 255), anchor="mm")
im.save(f"{out}/app_ok.png")


def agent(name, title, status, items, n_done, footer=None):
    im = Image.new("RGB", (W, H), (24, 22, 21))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 120), fill=ORANGE)
    d.rounded_rectangle((250, 22, 326, 98), 22, fill=(255, 244, 236))  # a little Claude badge
    d.ellipse((272, 48, 286, 66), fill=(40, 30, 28))
    d.ellipse((290, 48, 304, 66), fill=(40, 30, 28))
    d.text((350, 60), title, font=font(52), fill=(255, 255, 255), anchor="lm")
    d.text((1350, 60), status, font=font(40, "Medium"), fill=(255, 236, 224), anchor="rm")
    y = 230
    for i, it in enumerate(items):
        done = i < n_done
        if done:
            check(d, 300, y, 34, GREEN)
        else:
            d.ellipse((266, y - 34, 334, y + 34), outline=(90, 84, 80), width=4)
        d.text((370, y), it, font=font(52, "Bold" if done else "Medium"), fill=(240, 236, 232) if done else (110, 104, 100), anchor="lm")
        y += 145
    if footer:
        d.text((W // 2, 840), footer, font=font(44, "Medium"), fill=(200, 190, 182), anchor="mm")
    im.save(f"{out}/{name}.png")


CLEAN = ["Merged helpers into utils.js", "Renamed 48 variables", "Rewrote the state logic"]
for n in range(len(CLEAN) + 1):
    agent(f"clean_{n}", "Claude  ·  cleanup", "done" if n == len(CLEAN) else "working...", CLEAN, n,
          "6 files edited" if n == len(CLEAN) else None)
REWIND = ["src/state.js", "src/utils.js", "src/App.jsx + 3 more"]
for n in range(len(REWIND) + 1):
    agent(f"rewind_{n}", "Rewind to checkpoint", "restored" if n == len(REWIND) else "rewinding...", REWIND, n,
          "before your last prompt  ·  6 files restored" if n == len(REWIND) else "before your last prompt")

# the red runtime error over her app
im = Image.new("RGB", (W, H), (60, 8, 12))
d = ImageDraw.Draw(im)
d.rectangle((0, 0, W, 64), fill=(90, 14, 20))
d.text((W // 2, 32), "localhost:5173  —  Pocket Budget", font=font(30, "Medium"), fill=(220, 160, 160), anchor="mm")
d.rectangle((0, 64, W, 200), fill=(200, 30, 40))
d.text((W // 2, 132), "Unhandled Runtime Error", font=font(66), fill=(255, 255, 255), anchor="mm")
d.text((300, 260), "TypeError: Cannot read properties", font=mono(46, True), fill=(255, 190, 190))
d.text((300, 325), "of undefined (reading 'map')", font=mono(46, True), fill=(255, 190, 190))
d.rounded_rectangle((280, 430, 1320, 760), 20, fill=(30, 6, 8))
code = [("src/state.js (42:17)", (255, 140, 140)), ("40 |  const s = useStore()", (200, 170, 170)),
        ("41 |  return (", (200, 170, 170)), ("42 |    s.itms.map(row =>", (255, 255, 255)), ("   |      ^", (255, 90, 90))]
for i, (t, c) in enumerate(code):
    d.text((320, 460 + i * 58), t, font=mono(40), fill=c)
d.text((W // 2, 840), "6 errors", font=font(44, "Medium"), fill=(255, 150, 150), anchor="mm")
im.save(f"{out}/app_error.png")


def terminal(name, rows):
    im, d = window("Terminal")
    y = 120
    for txt, col, big in rows:
        d.text((250, y), txt, font=mono(70 if big else 46, big), fill=col)
        y += 110 if big else 78
    im.save(f"{out}/{name}.png")


terminal("term_log", [
    ("$ git status", TXT, False),
    ("   6 files modified", AMBER, False),
    ("$ git log -1", TXT, False),
    ("   \"set up project\"", DIM, False),
    ("   committed", DIM, False),
    ("   3 hours ago", AMBER, True),
    ("$ _", TXT, False),
])
terminal("term_commit", [
    ("$ git add .", TXT, False),
    ("$ git commit -m \"it works", TXT, False),
    ("    do not breathe\"", TXT, False),
    ("   6 files changed", GREEN, False),
    ("   committed ✓", GREEN, True),
    ("$ _", TXT, False),
])

PW, PH = 600, 1290
Image.new("RGB", (PW, PH), (6, 7, 10)).save(f"{out}/phone_off.png")
print("screens in", out, sorted(os.listdir(out)))
