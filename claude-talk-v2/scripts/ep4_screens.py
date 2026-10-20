"""Screen images for episode 4 (monitor 1600x944, phone 600x1290), drawn with PIL.

Monitor: her calm task app; DevTools Network with the request counter running (net_0..net_15, cycled); the useEffect
with [tasks] (code_loop / code_loop_hi pulse); Claude's fix to [] (code_fixed); one request (net_one).
Phone: the database dashboard with reads climbing (dash_0..dash_5), off, and the daily-limit notification (alert).
Main content sits in the middle ~60% of the width so the close-up insert can crop the sides.
python3 scripts/ep4_screens.py [out dir]
"""
import os, random, sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "audio/ep4/screens"
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
TASKS = [("Fix login button", True), ("Write README", False), ("Call mom", False), ("Ship v1 (!!)", False)]


def bar(d, title, dark=False):
    d.rectangle((0, 0, W, 64), fill=(34, 38, 46) if dark else (225, 222, 235))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + i * 38, 20, 48 + i * 38, 44), fill=c)
    d.text((W // 2, 32), title, font=font(30, "Medium"), fill=DIM if dark else (110, 104, 130), anchor="mm")


def app(d, x0, x1, scale=1.0):
    """her task app between x0 and x1, calm and still"""
    cx = (x0 + x1) // 2
    d.rectangle((x0, 64, x1, 64 + int(120 * scale)), fill=PURPLE)
    d.text((cx, 64 + int(60 * scale)), "My Tasks", font=font(int(60 * scale)), fill=(255, 255, 255), anchor="mm")
    y = 64 + int(170 * scale)
    for name, done in TASKS:
        h = int(92 * scale)
        d.rounded_rectangle((x0 + int(40 * scale), y, x1 - int(40 * scale), y + h), int(20 * scale), fill=(255, 255, 255), outline=(225, 220, 240), width=3)
        bx = x0 + int(80 * scale)
        d.rounded_rectangle((bx, y + h // 2 - int(20 * scale), bx + int(40 * scale), y + h // 2 + int(20 * scale)), 8,
                            fill=GREEN if done else (255, 255, 255), outline=GREEN if done else (180, 170, 210), width=4)
        d.text((bx + int(70 * scale), y + h // 2), name, font=font(int(42 * scale), "Medium"), fill=(150, 146, 165) if done else (40, 36, 60), anchor="lm")
        y += h + int(22 * scale)


# her app, whole screen
im = Image.new("RGB", (W, H), (250, 248, 255))
d = ImageDraw.Draw(im)
bar(d, "localhost:5173  —  My Tasks")
app(d, 260, 1340)
im.save(f"{out}/app_ok.png")


def network(name, count, rows_seed, one=False):
    im = Image.new("RGB", (W, H), (250, 248, 255))
    d = ImageDraw.Draw(im)
    bar(d, "localhost:5173  —  My Tasks")
    app(d, 0, 560, 0.62)
    x0 = 560
    d.rectangle((x0, 64, W, H), fill=(30, 31, 36))
    d.rectangle((x0, 64, W, 130), fill=(41, 42, 48))
    for i, t in enumerate(("Elements", "Console", "Network", "Sources")):
        x = x0 + 40 + i * 230
        d.text((x, 97), t, font=font(34, "Medium"), fill=TXT if t == "Network" else DIM, anchor="lm")
        if t == "Network":
            d.rectangle((x - 6, 124, x + 160, 130), fill=BLUE)
    # the counter: big, in the middle of the crop
    d.rounded_rectangle((x0 + 40, 160, 1340, 290), 18, fill=(28, 70, 40) if one else (90, 20, 24))
    d.text((x0 + 80, 225), f"{count:,} request{'s' if count != 1 else ''}", font=mono(64, True),
           fill=(140, 240, 160) if one else (255, 120, 110), anchor="lm")
    y = 320
    d.text((x0 + 40, y), "Name", font=mono(30, True), fill=DIM)
    d.text((x0 + 420, y), "Status", font=mono(30, True), fill=DIM)
    d.text((x0 + 600, y), "Type", font=mono(30, True), fill=DIM)
    y += 50
    rnd = random.Random(rows_seed)
    nrows = 1 if one else 9
    for r in range(nrows):
        d.rectangle((x0, y - 6, W, y + 46), fill=(36, 37, 43) if r % 2 else (30, 31, 36))
        d.text((x0 + 40, y), "tasks", font=mono(34), fill=TXT)
        d.text((x0 + 420, y), "200", font=mono(34), fill=GREEN)
        d.text((x0 + 600, y), "fetch", font=mono(34), fill=DIM)
        w = rnd.randint(40, 140)  # waterfall bars, staggered
        xs = 1310 + (r * 37 + rows_seed * 13) % 140
        d.rectangle((xs, y + 12, xs + w, y + 30), fill=BLUE)
        y += 56
    im.save(f"{out}/{name}.png")


base = 4512
for i in range(16):
    network(f"net_{i}", base + i * 3 + (i * 7) % 3, i)
network("net_one", 1, 0, one=True)


def code(name, deps, hi, footer=None):
    im = Image.new("RGB", (W, H), (30, 30, 38))
    d = ImageDraw.Draw(im)
    bar(d, "TaskList.jsx  —  my-tasks", dark=True)
    rows = [
        ("1", [("function ", (198, 120, 221)), ("TaskList", (97, 175, 239)), ("() {", TXT)]),
        ("2", [("  const ", (198, 120, 221)), ("[tasks, setTasks] = ", TXT), ("useState", (97, 175, 239)), ("([])", TXT)]),
        ("3", []),
        ("4", [("  useEffect", (97, 175, 239)), ("(() => {", TXT)]),
        ("5", [("    fetch", (97, 175, 239)), ("(", TXT), ("'/api/tasks'", (152, 195, 121)), (")", TXT)]),
        ("6", [("      .then(r => r.", TXT), ("json", (97, 175, 239)), ("())", TXT)]),
        ("7", [("      .then(setTasks)", TXT)]),
        ("8", [("  }, ", TXT), (deps, None), (")", TXT)]),
    ]
    y = 150
    for n, toks in rows:
        d.text((250, y), n, font=mono(44), fill=(90, 92, 110), anchor="ra")
        x = 300
        for t, c in toks:
            f = mono(50, c is None)
            w = d.textlength(t, font=f)
            if c is None:  # the dependency array
                col = GREEN if deps == "[]" else RED
                pad = 14 if hi else 8
                d.rounded_rectangle((x - pad, y - pad, x + w + pad, y + 62 + pad), 10,
                                    fill=(40, 70, 46) if deps == "[]" else ((120, 24, 30) if hi else (80, 20, 26)), outline=col, width=5 if hi else 3)
                d.text((x, y), t, font=f, fill=(170, 255, 180) if deps == "[]" else (255, 200, 200))
            else:
                d.text((x, y), t, font=f, fill=c)
            x += w
        y += 82
    if footer:
        d.rounded_rectangle((300, 820, 1300, 900), 20, fill=ORANGE)
        d.text((800, 860), footer, font=font(40, "Medium"), fill=(255, 255, 255), anchor="mm")
    elif deps != "[]":
        d.text((800, 860), "runs every time  tasks  changes", font=font(40, "Medium"), fill=(255, 140, 130), anchor="mm")
    im.save(f"{out}/{name}.png")


code("code_loop", "[tasks]", False)
code("code_loop_hi", "[tasks]", True)
code("code_fixed", "[]", False, "Claude  ·  fixed: fetch once on load")

# phone
PW, PH = 600, 1290
Image.new("RGB", (PW, PH), (6, 7, 10)).save(f"{out}/phone_off.png")


def dash(name, reads, k):
    im = Image.new("RGB", (PW, PH), (18, 20, 28))
    d = ImageDraw.Draw(im)
    d.text((PW // 2, 110), "my-tasks-db", font=font(40, "Medium"), fill=DIM, anchor="mm")
    d.text((PW // 2, 230), "Reads today", font=font(46, "Medium"), fill=TXT, anchor="mm")
    d.text((PW // 2, 340), f"{reads:,}", font=font(118), fill=(255, 200, 90), anchor="mm")
    d.text((PW // 2, 440), "▲ last 3 min", font=font(40, "Medium"), fill=GREEN, anchor="mm")
    # the graph: flat, then straight up
    x0, x1, yb, yt = 60, 540, 1000, 560
    d.line([(x0, yb), (x1, yb)], fill=LINE, width=3)
    pts = [(x0 + (x1 - x0) * i / 40, yb - 8 - (0 if i < 30 else (yt - yb + 8) * -((i - 30) / 10) ** 1.6)) for i in range(41)]
    pts = [(x, min(yb - 8, y)) for x, y in pts]
    d.line(pts, fill=(255, 200, 90), width=8, joint="curve")
    d.text((PW // 2, 1100), "Free tier: 50,000 reads / day", font=font(32, "Medium"), fill=DIM, anchor="mm")
    im.save(f"{out}/{name}.png")


for i in range(6):
    dash(f"dash_{i}", 45112 + i * 257 + (i * 31) % 97, i)

im = Image.new("RGB", (PW, PH), (24, 22, 40))
d = ImageDraw.Draw(im)
d.text((PW // 2, 230), "1:12", font=font(150, "Bold"), fill=(240, 240, 250), anchor="mm")
d.rounded_rectangle((30, 420, 570, 760), 36, fill=(245, 244, 250))
d.rounded_rectangle((60, 450, 120, 510), 14, fill=(255, 160, 60))
d.text((140, 480), "my-tasks-db  ·  now", font=font(32, "Medium"), fill=(110, 108, 120), anchor="lm")
d.text((60, 560), "Daily read limit", font=font(46), fill=(20, 20, 26), anchor="lm")
d.text((60, 620), "reached", font=font(46), fill=(20, 20, 26), anchor="lm")
d.text((60, 700), "Reads blocked until tomorrow.", font=font(34, "Medium"), fill=(200, 50, 60), anchor="lm")
im.save(f"{out}/alert.png")
print("screens in", out, len(os.listdir(out)))
