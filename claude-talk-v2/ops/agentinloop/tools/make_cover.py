#!/usr/bin/env python3
"""Cover for @agentinloop reels: a clean, professional title over the frame.

    make_cover.py out.jpg "Title, a few words" ["one quiet subtitle"] --base frame.png [--align center|left]

A soft dark gradient rises from the bottom of the 3:4 grid area (y 240-1680) so white text reads on
any frame; the title is SF Pro Bold, the subtitle SF Pro Regular in light grey, with a short coral rule
above the title. No emoji, no tilt, no boxes, no episode numbers.
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
GRID_BOTTOM = 1680
SF = "/System/Library/Fonts/SFNS.ttf"
ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("title"); ap.add_argument("sub", nargs="?")
ap.add_argument("--base", required=True)
ap.add_argument("--align", default="center", choices=["center", "left"])
a = ap.parse_args()


def sf(weight, size):
    f = ImageFont.truetype(SF, size)
    f.set_variation_by_name(weight)
    return f


img = Image.open(a.base).convert("RGBA").resize((W, H), Image.LANCZOS)
d = ImageDraw.Draw(img)

# title wraps to at most two lines, balanced by length
ft, fs = sf("Bold", 104), sf("Regular", 50)
words = a.title.split()
lines = [a.title]
if d.textlength(a.title, font=ft) > W - 160 and len(words) > 1:
    cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    lines = [" ".join(words[:cut]), " ".join(words[cut:])]
lh = int(ft.size * 1.08)
block = 30 + lh * len(lines) + (int(fs.size * 1.5) if a.sub else 0)
top = GRID_BOTTOM - 120 - block

# gradient: clear above the text, about 82% black behind it
g0 = top - 300
grad = Image.new("RGBA", (W, H))
gd = ImageDraw.Draw(grad)
for y in range(g0, H):
    t = min(1, (y - g0) / (top + 40 - g0))  # fully dark by the top of the title
    gd.line([(0, y), (W, y)], fill=(8, 8, 12, int(210 * t ** 1.3)))
img.alpha_composite(grad)
d = ImageDraw.Draw(img)

x = W // 2 if a.align == "center" else 80
anchor = "mt" if a.align == "center" else "lt"
rule_x = (W // 2 - 40) if a.align == "center" else 80
d.rounded_rectangle((rule_x, top, rule_x + 80, top + 8), radius=4, fill=(217, 119, 87))
y = top + 30
for line in lines:
    d.text((x, y), line, font=ft, fill=(255, 255, 255), anchor=anchor)
    y += lh
if a.sub:
    d.text((x, y + 14), a.sub, font=fs, fill=(214, 214, 220), anchor=anchor)
img.convert("RGB").save(a.out, quality=93)
