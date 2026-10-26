"""3D-series cover: a key frame with the topic in big Futura Bold (white lines, then accent lines), like ep 2.
python3 cover3d.py <frame.png> <out.png> "WHITE LINE|..." "ACCENT LINE|..." [y_top] [accent_hex]"""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

src, out, white, accent = sys.argv[1:5]
y = int(sys.argv[5]) if len(sys.argv) > 5 else 380
acc = sys.argv[6] if len(sys.argv) > 6 else "#18e0ff"
W, H = 1080, 1920
im = Image.open(src).convert("RGB")
s = max(W / im.width, H / im.height)
im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
lines = [(t, "#ffffff") for t in white.split("|") if t] + [(t, acc) for t in accent.split("|") if t]
F = "/System/Library/Fonts/Supplemental/Futura.ttc"
# one size for all lines: the largest that fits every line in 960 px
size = 150
while size > 60 and any(ImageFont.truetype(F, size, index=2).getlength(t) > 960 for t, _ in lines):
    size -= 2
font = ImageFont.truetype(F, size, index=2)
lh = int(size * 1.08)
# soft dark band behind the text so it reads on any frame
band = Image.new("L", (W, H), 0)
ImageDraw.Draw(band).rectangle([0, y - 60, W, y + lh * len(lines) + 40], fill=120)
band = band.filter(ImageFilter.GaussianBlur(70))
im = Image.composite(Image.new("RGB", (W, H), (6, 8, 14)), im, band)
d = ImageDraw.Draw(im)
for i, (t, c) in enumerate(lines):
    x = (W - font.getlength(t)) / 2
    d.text((x, y + i * lh), t, font=font, fill=c, stroke_width=max(4, size // 22), stroke_fill="#0a0d14")
im.save(out)
print(out, size)
