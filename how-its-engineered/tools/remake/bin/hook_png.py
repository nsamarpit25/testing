#!/usr/bin/env python3
"""Transparent 1080x1920 PNG with a big hook line for the first seconds of a trial variant.

usage: python3 tools/remake/bin/hook_png.py "Line one|line *two*" out.png [--y 300] [--size 76] [--accent ff7a2f] [--band]
  | breaks lines, *word* gets the accent colour. Text sits in the top third (below the IG header, above most props).
"""
import argparse, os, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HIE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FONT = os.path.join(HIE, 'videos', '20-canary-releases', 'fonts', 'Inter-ExtraBold.ttf')

p = argparse.ArgumentParser()
p.add_argument('text'); p.add_argument('out')
p.add_argument('--y', type=int, default=300); p.add_argument('--size', type=int, default=76)
p.add_argument('--accent', default='ff7a2f')
p.add_argument('--band', action='store_true', help='dark rounded panel behind the text, to sit over busy UI')
a = p.parse_args()

W, H = 1080, 1920
font = ImageFont.truetype(FONT, a.size)
accent = tuple(int(a.accent[i:i + 2], 16) for i in (0, 2, 4))
lines = a.text.split('|')
lh = int(a.size * 1.18)

# measure each line as runs of (text, colour); shrink the font until the widest line fits 960 px
while True:
    rows = []
    for ln in lines:
        runs = [(t, accent if i % 2 else (245, 245, 242)) for i, t in enumerate(re.split(r'\*', ln)) if t]
        w = sum(font.getlength(t) for t, _ in runs)
        rows.append((runs, w))
    if max(w for _, w in rows) <= 960 or font.size <= 36:
        break
    font = ImageFont.truetype(FONT, font.size - 2); lh = int(font.size * 1.18)

img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
if a.band:
    bw = max(max(w for _, w in rows) + 80, 1000)  # wide enough to hide the top UI panels
    ImageDraw.Draw(img).rounded_rectangle(((W - bw) / 2, a.y - 40, (W + bw) / 2, a.y + len(rows) * lh + 60), 28, fill=(12, 12, 14, 248))
# soft dark shadow so the line reads on any frame
sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
txt = Image.new('RGBA', (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(txt)
for i, (runs, w) in enumerate(rows):
    x, y = (W - w) / 2, a.y + i * lh
    for t, col in runs:
        sd.text((x, y + 4), t, font=font, fill=(0, 0, 0, 200))
        td.text((x, y), t, font=font, fill=col + (255,))
        x += font.getlength(t)
sh = sh.filter(ImageFilter.GaussianBlur(14))
img = Image.alpha_composite(img, sh); img = Image.alpha_composite(img, sh)
img = Image.alpha_composite(img, txt)
img.save(a.out)
print(a.out)
