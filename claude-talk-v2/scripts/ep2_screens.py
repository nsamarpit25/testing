"""Screen and phone images for episode 2 (monitor 1600x944, phone 600x1290), drawn with PIL.

Monitor: terminal after the first push, repo page at several star counts, the key dashboard (revoked / new key),
terminal after the second push, Claude's agent panel with 0..4 items done. Phone: off, and the billing alert.
Main content sits in the middle ~60% of the width so the close-up insert can crop the sides.
python3 scripts/ep2_screens.py [out dir]
"""
import os, sys
from math import cos, sin, pi
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "audio/ep2/screens"
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


def star(d, cx, cy, r, fill):
    pts = [(cx + (r if i % 2 == 0 else r * 0.45) * sin(i * pi / 5), cy - (r if i % 2 == 0 else r * 0.45) * cos(i * pi / 5))
           for i in range(10)]
    d.polygon(pts, fill=fill)


def check(d, cx, cy, r, fill, ring=True):
    if ring:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
        col = BG
    else:
        col = fill
    w = max(3, int(r * 0.28))
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)], fill=col, width=w, joint="curve")


def cross(d, cx, cy, r, fill):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
    w = max(3, int(r * 0.26))
    d.line([(cx - r * 0.4, cy - r * 0.4), (cx + r * 0.4, cy + r * 0.4)], fill=BG, width=w)
    d.line([(cx - r * 0.4, cy + r * 0.4), (cx + r * 0.4, cy - r * 0.4)], fill=BG, width=w)


def window(title):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 64), fill=PANEL)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + i * 38, 20, 48 + i * 38, 44), fill=c)
    d.text((W // 2, 32), title, font=font(30, "Medium"), fill=DIM, anchor="mm")
    return im, d


def terminal(name, rows):
    im, d = window("Terminal")
    y = 120
    for txt, col in rows:
        d.text((250, y), txt, font=mono(46), fill=col)
        y += 78
    im.save(f"{out}/{name}.png")


terminal("term_push", [
    ("$ git add .", TXT),
    ("$ git commit -m \"it finally works\"", TXT),
    ("   new file:  .env", AMBER),
    ("   new file:  src/app.js", DIM),
    ("$ git push", TXT),
    ("   main -> main   done", GREEN),
    ("$ _", TXT),
])
terminal("term_push2", [
    ("$ git commit -am \"new key\"", TXT),
    ("   modified:  .env", AMBER),
    ("$ git push", TXT),
    ("   main -> main   done", GREEN),
    ("$ _", TXT),
])


def repo(stars, private=False):
    im, d = window("cleo / expense-tracker")
    d.text((250, 110), "cleo / expense-tracker", font=font(64), fill=BLUE)
    badge = "Private" if private else "Public"
    bw = d.textlength(badge, font=font(34, "Medium")) + 44
    d.rounded_rectangle((250, 200, 250 + bw, 254), 27, outline=AMBER if private else GREEN, width=3)
    d.text((250 + bw / 2, 227), badge, font=font(34, "Medium"), fill=AMBER if private else GREEN, anchor="mm")
    # the big star counter, centre of the screen
    d.rounded_rectangle((520, 300, 1080, 470), 30, fill=PANEL, outline=LINE, width=3)
    star(d, 620, 385, 52, AMBER)
    d.text((700, 385), f"{stars}", font=font(120), fill=TXT, anchor="lm")
    d.text((1000, 385), "stars", font=font(34, "Medium"), fill=DIM, anchor="mm")
    files = [("src/", DIM), ("package.json", DIM), (".env", AMBER), ("README.md", DIM)]
    y = 520
    for f, c in files:
        d.line((250, y - 12, 1350, y - 12), fill=LINE, width=2)
        d.text((280, y), f, font=mono(40, bold=f == ".env"), fill=c)
        if f == ".env":
            d.text((620, y), "API_KEY=sk-live-4f9a...", font=mono(40), fill=RED)
        y += 90
    im.save(f"{out}/repo_{stars}{'_private' if private else ''}.png")


for s in (90, 97, 104, 112, 119, 126, 133, 140):
    repo(s)


def keys(name, title, row_txt, status, col, ok):
    im, d = window("API keys - dashboard")
    d.text((W // 2, 170), title, font=font(84), fill=TXT, anchor="mm")
    (check if ok else cross)(d, W // 2, 340, 70, col)
    d.rounded_rectangle((330, 470, 1270, 590), 22, fill=PANEL, outline=LINE, width=3)
    d.text((380, 530), row_txt, font=mono(44), fill=TXT, anchor="lm")
    d.text((1230, 530), status, font=font(40), fill=col, anchor="rm")
    im.save(f"{out}/{name}.png")


keys("keys_revoked", "Key revoked", "sk-live-...4f9a", "REVOKED", RED, False)
keys("keys_new", "New key created", "sk-live-...c71e", "ACTIVE", GREEN, True)

ITEMS = ["Revoked key  ...4f9a", "Revoked key  ...c71e", "Repo set to private", "Support ticket opened: the bill"]


def agent(n):
    im = Image.new("RGB", (W, H), (24, 22, 21))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 120), fill=ORANGE)
    # a little Claude badge: an orange-on-white rounded square with two eyes
    d.rounded_rectangle((250, 22, 326, 98), 22, fill=(255, 244, 236))
    d.ellipse((272, 48, 286, 66), fill=(40, 30, 28))
    d.ellipse((290, 48, 304, 66), fill=(40, 30, 28))
    d.text((350, 60), "Claude", font=font(56), fill=(255, 255, 255), anchor="lm")
    d.text((1350, 60), "done" if n == len(ITEMS) else "working...", font=font(40, "Medium"), fill=(255, 236, 224), anchor="rm")
    y = 220
    for i, it in enumerate(ITEMS):
        done = i < n
        if done:
            check(d, 300, y, 34, GREEN)
        else:
            d.ellipse((266, y - 34, 334, y + 34), outline=(90, 84, 80), width=4)
        d.text((370, y), it, font=font(54, "Bold" if done else "Medium"), fill=(240, 236, 232) if done else (110, 104, 100), anchor="lm")
        y += 150
    im.save(f"{out}/agent_{n}.png")


for n in range(len(ITEMS) + 1):
    agent(n)

# phone (portrait)
PW, PH = 600, 1290
im = Image.new("RGB", (PW, PH), (6, 7, 10))
im.save(f"{out}/phone_off.png")
im = Image.new("RGB", (PW, PH), (32, 28, 58))
d = ImageDraw.Draw(im)
for y in range(PH):  # a soft wallpaper gradient
    t = y / PH
    d.line((0, y, PW, y), fill=(int(40 + 60 * t), int(30 + 20 * t), int(80 + 30 * t)))
d.text((PW // 2, 190), "2:14", font=font(150), fill=(255, 255, 255), anchor="mm")
d.rounded_rectangle((30, 440, PW - 30, 860), 40, fill=(245, 245, 247))
d.text((70, 500), "BILLING ALERT", font=font(34, "Bold"), fill=RED, anchor="lm")
d.text((70, 570), "API usage this month", font=font(38, "Medium"), fill=(60, 60, 67), anchor="lm")
d.text((PW // 2, 700), "$2,000", font=font(150), fill=(20, 20, 24), anchor="mm")
d.text((PW // 2, 800), "and counting", font=font(36, "Medium"), fill=(110, 110, 118), anchor="mm")
im.save(f"{out}/phone_alert.png")
print("screens in", out, sorted(os.listdir(out)))
