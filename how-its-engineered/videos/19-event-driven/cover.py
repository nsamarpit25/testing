# Cover for the Blender reels, in the house layout of the HTML covers (16 Retries): a frame of the video with a dark fade at the top,
# "SYSTEM DESIGN" kicker, a big title, a serif subtitle with one italic coloured phrase, and the handle at the bottom. No reel number.
# usage: .venv/bin/python videos/18-pub-sub/cover.py <frame.png> <out.png> --title PUB/SUB --sub "How one post reaches|*2 million* followers"
#        [--accent "#E0543C"] [--title-top "#F4E7CF"] [--title-bot "#E0A95E"] [--shift 0.0]
import re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]; NM = ROOT / 'node_modules'
a = sys.argv; opt = lambda k, d: a[a.index(k) + 1] if k in a else d
src, dst = Path(a[1]), Path(a[2])
TITLE, SUB = opt('--title', 'PUB/SUB'), opt('--sub', 'Title|*here*')
ACC, T0, T1 = opt('--accent', '#E0543C'), opt('--title-top', '#F4E7CF'), opt('--title-bot', '#E0A95E')
SHIFT = float(opt('--shift', 0.0))
W, H = 1080, 1920; k = W / 540
INTER = NM / '@fontsource-variable/inter/files/inter-latin-wght-normal.woff2'
SERIF = NM / '@fontsource/instrument-serif/files/instrument-serif-latin-400-normal.woff2'
SERIF_I = NM / '@fontsource/instrument-serif/files/instrument-serif-latin-400-italic.woff2'
MONO = NM / '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-700-normal.woff2'
def font(p, size, wght=None):
    f = ImageFont.truetype(str(p), round(size * k))
    if wght: f.set_variation_by_axes([wght])
    return f
hx = lambda h: tuple(int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))

bg = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
if SHIFT: bg = bg.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -SHIFT * H), resample=Image.BICUBIC)
im = bg.convert('RGBA')
# top fade: dark warm ink, solid behind the type, gone by ~52 %
fade = Image.new('RGBA', (W, H)); fd = ImageDraw.Draw(fade)
for y in range(H):
    u = y / H; al = 0.93 if u < 0.30 else max(0.0, 0.93 * (1 - (u - 0.30) / 0.22))
    fd.line([(0, y), (W, y)], fill=(14, 12, 10, int(255 * al ** 1.1)))
bot = Image.new('RGBA', (W, H)); bd = ImageDraw.Draw(bot)
for y in range(int(H * 0.82), H):
    u = (y - H * 0.82) / (H * 0.18); bd.line([(0, y), (W, y)], fill=(14, 12, 10, int(200 * u)))
im = Image.alpha_composite(Image.alpha_composite(im, fade), bot)
d = ImageDraw.Draw(im)
def ctext(y, s, f, fill, spacing=0):
    if spacing:
        ws = [d.textlength(c, font=f) for c in s]; tw = sum(ws) + spacing * (len(s) - 1); x = (W - tw) / 2
        for c, w in zip(s, ws): d.text((x, y), c, font=f, fill=fill); x += w + spacing
    else: d.text(((W - d.textlength(s, font=f)) / 2, y), s, font=f, fill=fill)
ctext(160 * k, 'SYSTEM DESIGN', font(MONO, 13), hx('#E0A95E') + (255,), spacing=3.5 * k)
# title: vertical gradient + soft glow
ft = font(INTER, 72, 900); tw = d.textlength(TITLE, font=ft)
if tw > 470 * k: ft = font(INTER, 72 * 470 * k / tw, 900); tw = d.textlength(TITLE, font=ft)  # long titles fit the frame
tx, ty = (W - tw) / 2, 186 * k + (72 * k - ft.size) * 0.6
mask = Image.new('L', (W, H)); ImageDraw.Draw(mask).text((tx, ty), TITLE, font=ft, fill=255)
bb = mask.getbbox(); grad = Image.new('RGBA', (W, H))
gd = ImageDraw.Draw(grad); c0, c1 = hx(T0), hx(T1)
for y in range(bb[1], bb[3] + 1):
    u = (y - bb[1]) / max(1, bb[3] - bb[1]); u = min(1, u / 0.7)
    gd.line([(0, y), (W, y)], fill=tuple(round(c0[i] + (c1[i] - c0[i]) * u) for i in range(3)) + (255,))
glow = Image.new('RGBA', (W, H), hx(T1) + (0,)); glow.putalpha(mask.filter(ImageFilter.GaussianBlur(22 * k)).point(lambda v: v * 0.45))
im = Image.alpha_composite(im, glow); title = Image.new('RGBA', (W, H)); title.paste(grad, (0, 0), mask)
im = Image.alpha_composite(im, title); d = ImageDraw.Draw(im)
# subtitle lines ("|" splits lines, *x* = italic accent)
fs, fi = font(SERIF, 34), font(SERIF_I, 34); y = 286 * k
for line in SUB.split('|'):
    segs = [(m.group(1) or m.group(2), m.group(1) is not None) for m in re.finditer(r'\*([^*]+)\*|([^*]+)', line)]
    tw = sum(d.textlength(t, font=fi if it else fs) for t, it in segs); x = (W - tw) / 2
    for t, it in segs:
        d.text((x, y), t, font=fi if it else fs, fill=hx(ACC) if it else hx('#F4EEE2')); x += d.textlength(t, font=fi if it else fs)
    y += 38 * k
ctext(H - 82 * k - 11 * k, '@HOW.ITS.ENGINEERED', font(MONO, 11), hx('#B5AA9A') + (255,), spacing=2 * k)
dst.parent.mkdir(parents=True, exist_ok=True); im.convert('RGB').save(dst); print('cover', dst)
