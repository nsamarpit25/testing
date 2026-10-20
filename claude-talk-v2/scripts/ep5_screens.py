"""Screen images for episode 5 (monitor 1600x944, phone 600x1290), drawn with PIL.

Monitor: her task app on localhost:5173 with the stubborn blue "Add task" button (app_blue); her CSS with !important on
everything (code_important); the button text changed to PLEASE WORK (code_please); three terminals running three dev
servers (term, term_n1..n3 with the folder names lit one by one, term_ports with the ports and Vite's "in use" lines);
the mismatch, editor on my-app-final vs browser on my-app (split_0, split_1); typing localhost:5175 (url_a, url_b);
the reveal, a giant neon-green PLEASE WORK button (final_green).
Main content sits in the middle ~60% of the width so the close-up insert can crop the sides.
python3 scripts/ep5_screens.py [out dir]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "audio/ep5/screens"
os.makedirs(out, exist_ok=True)
W, H = 1600, 944
SF = "/Library/Fonts/SF-Pro-Display-%s.otf"
MONO = "/System/Library/Fonts/Menlo.ttc"


def font(size, w="Bold"):
    return ImageFont.truetype(SF % w, size)


def mono(size, bold=False):
    return ImageFont.truetype(MONO, size, index=1 if bold else 0)


TXT, DIM, GREEN, RED, AMBER, BLUE = (230, 237, 243), (139, 148, 158), (63, 185, 80), (248, 81, 73), (227, 179, 65), (88, 166, 255)
ORANGE, PURPLE = (217, 119, 87), (124, 92, 230)
BTN_BLUE, NEON = (29, 78, 216), (16, 196, 36)
X0, X1 = 320, 1280                 # the part of the screen the close-up keeps


def bar(d, title, dark=False, url=None, sel=False, cursor=False):
    d.rectangle((0, 0, W, 64), fill=(34, 38, 46) if dark else (225, 222, 235))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((24 + i * 38, 20, 48 + i * 38, 44), fill=c)
    if url is None:
        d.text((W // 2, 32), title, font=font(30, "Medium"), fill=DIM if dark else (110, 104, 130), anchor="mm")
        return
    # a browser address field, big enough to read in the insert
    d.rounded_rectangle((X0 + 20, 10, X1 - 20, 56), 23, fill=(255, 255, 255), outline=(190, 184, 210), width=2)
    f = mono(32, True)
    tw = d.textlength(url, font=f)
    x = W // 2 - tw / 2
    if sel:
        d.rectangle((x - 6, 15, x + tw + 6, 51), fill=(180, 210, 255))
    d.text((x, 33), url, font=f, fill=(30, 30, 40), anchor="lm")
    if cursor:
        d.rectangle((x + tw + 4, 15, x + tw + 7, 51), fill=(30, 30, 40))


def app(d, label="Add task", green=False, y0=64, scale=1.0, x0=X0, x1=X1):
    """her task app: header, three tasks, the button"""
    cx = (x0 + x1) // 2
    s = scale
    d.rectangle((0, y0, W, y0 + int(110 * s)), fill=PURPLE)
    d.text((cx, y0 + int(55 * s)), "My Tasks", font=font(int(58 * s)), fill=(255, 255, 255), anchor="mm")
    y = y0 + int(150 * s)
    for name in ("Fix the button", "Buy groceries", "Call mom"):
        h = int(78 * s)
        d.rounded_rectangle((x0 + int(60 * s), y, x1 - int(60 * s), y + h), int(18 * s), fill=(255, 255, 255), outline=(225, 220, 240), width=3)
        bx = x0 + int(100 * s)
        d.rounded_rectangle((bx, y + h // 2 - int(17 * s), bx + int(34 * s), y + h // 2 + int(17 * s)), 7, fill=(255, 255, 255),
                            outline=(180, 170, 210), width=4)
        d.text((bx + int(60 * s), y + h // 2), name, font=font(int(38 * s), "Medium"), fill=(40, 36, 60), anchor="lm")
        y += h + int(18 * s)
    if green:  # !important everywhere: background green, 64px text, the whole width
        d.rounded_rectangle((x0 + 30, y + 10, x1 - 30, H - 30), 30, fill=NEON, outline=(20, 140, 10), width=8)
        d.text((cx, (y + 10 + H - 30) // 2), "PLEASE WORK", font=font(118, "Black"), fill=(255, 255, 255), anchor="mm",
               stroke_width=4, stroke_fill=(20, 120, 10))
    else:
        bw, bh = int(360 * s), int(96 * s)
        d.rounded_rectangle((cx - bw // 2, y + int(30 * s), cx + bw // 2, y + int(30 * s) + bh), int(16 * s), fill=BTN_BLUE)
        d.text((cx, y + int(30 * s) + bh // 2), "+ " + label, font=font(int(44 * s)), fill=(255, 255, 255), anchor="mm")


def page(name, url, **kw):
    im = Image.new("RGB", (W, H), (250, 248, 255))
    d = ImageDraw.Draw(im)
    bar(d, None, url=url, sel=kw.pop("sel", False), cursor=kw.pop("cursor", False))
    app(d, **kw)
    im.save(f"{out}/{name}.png")


page("app_blue", "localhost:5173")
page("url_a", "localhost:5173", sel=True)
page("url_b", "localhost:5175", cursor=True)
page("final_green", "localhost:5175", green=True)

# ---------------------------------------------------------------- editor
KW, FN, STR, PROP, VAL, IMP = (198, 120, 221), (97, 175, 239), (152, 195, 121), (224, 108, 117), (209, 154, 102), (255, 92, 92)


def editor(name, title, rows, hi=None):
    """rows: lists of (text, colour); colour None marks the highlighted bit (boxed)"""
    im = Image.new("RGB", (W, H), (30, 30, 38))
    d = ImageDraw.Draw(im)
    bar(d, title, dark=True)
    y = 110
    for n, toks in enumerate(rows, 1):
        d.text((X0 - 20, y + 4), str(n), font=mono(36), fill=(90, 92, 110), anchor="ra")
        x = X0 + 10
        for t, c in toks:
            f = mono(40, c is None)
            w = d.textlength(t, font=f)
            if c is None:
                d.rounded_rectangle((x - 6, y - 6, x + w + 6, y + 52), 8, fill=(110, 24, 30), outline=IMP, width=3)
                d.text((x, y), t, font=f, fill=(255, 210, 200))
            else:
                d.text((x, y), t, font=f, fill=c)
            x += w
        y += 66
    if hi:
        d.rounded_rectangle((X0, H - 110, X1, H - 30), 20, fill=ORANGE)
        d.text((W // 2, H - 70), hi, font=font(40, "Medium"), fill=(255, 255, 255), anchor="mm")
    im.save(f"{out}/{name}.png")


I = ("!important", None)
editor("code_important", "styles.css  —  my-app-final", [
    [(".add-btn", FN), (" {", TXT)],
    [("  background", PROP), (": ", TXT), ("green ", VAL), I, (";", TXT)],
    [("  color", PROP), (": ", TXT), ("white ", VAL), I, (";", TXT)],
    [("  border", PROP), (": ", TXT), ("none ", VAL), I, (";", TXT)],
    [("  font-size", PROP), (": ", TXT), ("64px ", VAL), I, (";", TXT)],
    [("  width", PROP), (": ", TXT), ("100% ", VAL), I, (";", TXT)],
    [("}", TXT)],
    [("button", FN), (" { ", TXT), ("background", PROP), (": ", TXT), ("green ", VAL), I, (" }", TXT)],
    [("/* PLEASE */", (106, 115, 135))],
])
editor("code_please", "App.jsx  —  my-app-final", [
    [("function ", KW), ("AddButton", FN), ("() {", TXT)],
    [("  return ", KW), ("(", TXT)],
    [("    <", TXT), ("button ", PROP), ("className", VAL), ("=", TXT), ('"add-btn"', STR), (">", TXT)],
    [("      ", TXT), ("PLEASE WORK", None)],
    [("    </", TXT), ("button", PROP), (">", TXT)],
    [("  )", TXT)],
    [("}", TXT)],
])

# ---------------------------------------------------------------- the three terminals
TERMS = [("my-app", [], 5173), ("my-app-v2", [5173], 5174), ("my-app-final", [5173, 5174], 5175)]


def terminals(name, lit_names=0, ports=False):
    im = Image.new("RGB", (W, H), (16, 18, 24))
    d = ImageDraw.Draw(im)
    bar(d, "Terminal  —  3 tabs", dark=True)
    ph = (H - 64 - 24) // 3
    for i, (folder, busy, port) in enumerate(TERMS):
        y0 = 64 + 6 + i * (ph + 6)
        d.rectangle((0, y0, W, y0 + ph), fill=(24, 26, 34))
        d.rectangle((0, y0, W, y0 + 44), fill=(36, 39, 50))
        lit = i < lit_names
        tf = mono(34, True)
        tag = f"~/{folder}"
        tw = d.textlength(tag, font=tf)
        if lit:
            d.rounded_rectangle((X0 - 8, y0 + 3, X0 + tw + 8, y0 + 41), 8, fill=(120, 80, 10), outline=AMBER, width=3)
        d.text((X0, y0 + 22), tag, font=tf, fill=(255, 225, 140) if lit else DIM, anchor="lm")
        d.ellipse((X1 - 30, y0 + 12, X1 - 10, y0 + 32), fill=GREEN)  # running
        y = y0 + 54
        f = mono(33)
        d.text((X0, y), "$ npm run dev", font=f, fill=TXT)
        y += 43
        for b in busy:
            msg = f"Port {b} is in use, trying another one..."
            if ports:
                d.rectangle((X0 - 6, y - 4, X0 + d.textlength(msg, font=f) + 6, y + 38), fill=(90, 20, 24))
            d.text((X0, y), msg, font=f, fill=(255, 130, 120) if ports else AMBER)
            y += 43
        d.text((X0, y), "VITE ready", font=f, fill=GREEN)
        y += 43
        pre = "➜  Local: "
        d.text((X0, y), pre, font=f, fill=TXT)
        x = X0 + d.textlength(pre, font=f)
        url = f"localhost:{port}"
        fb = mono(33, True)
        if ports:
            d.rounded_rectangle((x - 6, y - 4, x + d.textlength(url, font=fb) + 6, y + 38), 6, fill=(20, 70, 110), outline=BLUE, width=2)
        d.text((x, y), url, font=fb, fill=(150, 210, 255) if ports else (120, 190, 255))
    im.save(f"{out}/{name}.png")


terminals("term")
for k in (1, 2, 3):
    terminals(f"term_n{k}", k)
terminals("term_ports", 0, True)


# ---------------------------------------------------------------- the mismatch: what she edits vs what she sees
def split(name, both):
    im = Image.new("RGB", (W, H), (30, 30, 38))
    d = ImageDraw.Draw(im)
    bar(d, "", dark=True)
    hh = (H - 64) // 2
    # top: the editor
    d.rectangle((0, 64, W, 64 + hh), fill=(30, 30, 38))
    d.text((X0, 100), "EDITING", font=font(34), fill=DIM, anchor="lm")
    tag = "~/my-app-final"
    f = mono(52, True)
    tw = d.textlength(tag, font=f)
    d.rounded_rectangle((X0 - 10, 140, X0 + tw + 10, 216), 12, fill=(28, 80, 40), outline=GREEN, width=4)
    d.text((X0, 178), tag, font=f, fill=(170, 255, 180), anchor="lm")
    d.text((X0, 290), '<button>PLEASE WORK</button>', font=mono(38), fill=(200, 200, 215), anchor="lm")
    d.text((X0, 350), 'background: green !important', font=mono(38), fill=(200, 200, 215), anchor="lm")
    d.rectangle((0, 64 + hh - 3, W, 64 + hh + 3), fill=(70, 72, 90))
    # bottom: the browser
    y0 = 64 + hh
    d.rectangle((0, y0, W, H), fill=(250, 248, 255))
    d.text((X0, y0 + 36), "BROWSER  ·  localhost:5173", font=font(34), fill=(110, 104, 130), anchor="lm")
    tag = "~/my-app"
    if both:
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle((X0 - 10, y0 + 76, X0 + tw + 10, y0 + 152), 12, fill=(110, 24, 30), outline=RED, width=4)
        d.text((X0, y0 + 114), tag, font=f, fill=(255, 200, 200), anchor="lm")
        d.text((X0 + tw + 50, y0 + 114), "(the original)", font=font(40, "Medium"), fill=(150, 60, 70), anchor="lm")
    else:
        d.text((X0, y0 + 114), "serving ...", font=mono(52, True), fill=(170, 165, 185), anchor="lm")
    cx = W // 2
    d.rounded_rectangle((cx - 180, y0 + 220, cx + 180, y0 + 316), 16, fill=BTN_BLUE)
    d.text((cx, y0 + 268), "+ Add task", font=font(44), fill=(255, 255, 255), anchor="mm")
    im.save(f"{out}/{name}.png")


split("split_0", False)
split("split_1", True)

# phone: face up on the desk, screen off
Image.new("RGB", (600, 1290), (6, 7, 10)).save(f"{out}/phone_off.png")
print("screens in", out, len(os.listdir(out)))
