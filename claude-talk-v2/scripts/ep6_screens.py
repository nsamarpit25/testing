"""Screen images for episode 6 (monitor 1600x944, phone 600x1290), drawn with PIL.

Monitor: her silly page with one huge PRESS button (press, press_down while clicked), the cursor going to close the tab
(press_close), her other tab, PORTFOLIO, lit (portfolio), the code for a second button (code_worse), then the page with
PRESS and WORSE (worse, worse_down while clicked).
Main content sits in the middle ~60% of the width so the close-up insert can crop the sides.
python3 scripts/ep6_screens.py [out dir]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "audio/ep6/screens"
os.makedirs(out, exist_ok=True)
W, H = 1600, 944
SF = "/Library/Fonts/SF-Pro-Display-%s.otf"
MONO = "/System/Library/Fonts/Menlo.ttc"


def font(size, w="Bold"):
    return ImageFont.truetype(SF % w, size)


def mono(size, bold=False):
    return ImageFont.truetype(MONO, size, index=1 if bold else 0)


TXT, DIM = (230, 237, 243), (139, 148, 158)
X0, X1 = 320, 1280                 # the part of the screen the close-up keeps
PAGE = (246, 236, 214)             # warm paper
RED, RED_D = (214, 52, 40), (150, 30, 22)
MUD, MUD_D = (112, 92, 28), (70, 56, 14)
TAB_Y = 74


def tabs(d, hover_close=False, portfolio=False):
    """the browser's tab strip: her page (active) and PORTFOLIO, big enough to read in the insert"""
    d.rectangle((0, 0, W, TAB_Y), fill=(206, 200, 214))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + i * 38, 25, 48 + i * 38, 49), fill=c)
    f = font(34, "Semibold")
    # active tab
    a0, a1 = X0 - 40, X0 + 400
    d.rounded_rectangle((a0, 10, a1, TAB_Y + 20), 16, fill=PAGE)
    d.text((a0 + 34, 44), "press.html", font=f, fill=(60, 50, 40), anchor="lm")
    cx = a1 - 44
    if hover_close:
        d.ellipse((cx - 24, 20, cx + 24, 68), fill=(200, 186, 166))
    d.text((cx, 44), "×", font=font(44, "Medium"), fill=(60, 50, 40), anchor="mm")
    # the other tab
    p0, p1 = a1 + 16, a1 + 470
    if portfolio:
        d.rounded_rectangle((p0, 12, p1, TAB_Y - 8), 14, fill=(46, 64, 120), outline=(120, 150, 240), width=4)
        d.text((p0 + 30, 43), "PORTFOLIO", font=font(36, "Bold"), fill=(235, 240, 255), anchor="lm")
    else:
        d.text((p0 + 30, 43), "PORTFOLIO", font=font(34, "Semibold"), fill=(120, 112, 130), anchor="lm")
    return cx


def cursor(d, x, y, s=1.4):
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (26, 24)]
    pts = [(x + px * s, y + py * s) for px, py in pts]
    d.polygon(pts, fill=(255, 255, 255))
    d.line(pts + [pts[0]], fill=(10, 10, 10), width=3)


def button(d, cx, cy, w, h, label, col, dark, down=False, size=120):
    off = 12 if down else 0
    if not down:
        d.rounded_rectangle((cx - w // 2, cy - h // 2 + 18, cx + w // 2, cy + h // 2 + 18), 40, fill=dark)
    d.rounded_rectangle((cx - w // 2, cy - h // 2 + off + (6 if down else 0), cx + w // 2, cy + h // 2 + off + 6), 40,
                        fill=dark if down else col)
    d.text((cx, cy + off + 6), label, font=font(size, "Black"), fill=(255, 255, 255), anchor="mm")


def page(name, n=1, down=None, cur=None, **kw):
    im = Image.new("RGB", (W, H), PAGE)
    d = ImageDraw.Draw(im)
    close_x = tabs(d, **kw)
    cy = (TAB_Y + H) // 2 + 10
    if n == 1:
        button(d, W // 2, cy, 640, 300, "PRESS", RED, RED_D, down == 0, 150)
        if cur == "btn":
            cursor(d, W // 2 + 150, cy + 60)
    else:
        button(d, W // 2 - 240, cy, 430, 250, "PRESS", RED, RED_D, down == 0, 104)
        button(d, W // 2 + 240, cy, 430, 250, "WORSE", MUD, MUD_D, down == 1, 104)
        if cur == "worse":
            cursor(d, W // 2 + 330, cy + 50)
    if cur == "close":
        cursor(d, close_x + 6, 50)
    im.save(f"{out}/{name}.png")


page("press", cur="btn")
page("press_down", down=0, cur="btn")
page("press_close", cur="close", hover_close=True)
page("portfolio", portfolio=True)
page("worse", n=2, cur="worse")
page("worse_down", n=2, down=1, cur="worse")

# the code for the second button, mid-typing
KW, FN, STR, PROP, VAL = (198, 120, 221), (97, 175, 239), (152, 195, 121), (224, 108, 117), (209, 154, 102)


def editor(name, rows):
    im = Image.new("RGB", (W, H), (30, 30, 38))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, TAB_Y), fill=(34, 38, 46))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + i * 38, 25, 48 + i * 38, 49), fill=c)
    d.text((W // 2, 37), "press.html", font=font(32, "Medium"), fill=DIM, anchor="mm")
    y = 130
    for k, toks in enumerate(rows, 1):
        d.text((X0 - 30, y + 4), str(k), font=mono(36), fill=(90, 92, 110), anchor="ra")
        x = X0
        for t, c in toks:
            f = mono(40, c == STR)
            d.text((x, y), t, font=f, fill=c)
            x += d.textlength(t, font=f)
        y += 70
    d.rectangle((x + 4, y - 66, x + 8, y - 20), fill=(230, 230, 240))  # the caret, end of the last line
    im.save(f"{out}/{name}.png")


editor("code_worse", [
    [("<button", PROP), (">", TXT), ("PRESS", TXT), ("</button>", PROP)],
    [("  play(", FN), ('"trumpet"', STR), (")", FN)],
    [("", TXT)],
    [("<button", PROP), (">", TXT), ("WORSE", TXT), ("</button>", PROP)],
    [("  play(", FN), ('"trumpet"', STR), (", ", TXT), ("slower", VAL), (": ", TXT), ("true", KW), (",", TXT)],
    [("    sadder", VAL), (": ", TXT), ("true", KW), (", ", TXT), ("extraSqueak", VAL), (": ", TXT), ("true", KW), (")", FN)],
])

Image.new("RGB", (600, 1290), (6, 7, 10)).save(f"{out}/phone_off.png")
print("screens in", out, len(os.listdir(out)))
