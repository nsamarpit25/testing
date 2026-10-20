# Small account name at the bottom of the frame, as a transparent PNG laid over the finished render at encode time,
# so the handle can change without re-rendering.  usage: python3 watermark.py <out.png> [--res 1080] [--name @how.its.engineered]
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

argv = sys.argv[1:]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
OUT, RES, NAME = Path(argv[0]), int(opt('--res', 1080)), opt('--name', '@how.its.engineered')
W, H = RES, int(RES * 16 / 9) // 2 * 2; k = RES / 540
INTER = Path(__file__).resolve().parents[2] / 'node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2'
f = ImageFont.truetype(str(INTER), round(11 * k)); f.set_variation_by_axes([600])
im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
xy = (W / 2, H - 22 * k)
d.text((xy[0], xy[1] + 0.6 * k), NAME, font=f, fill=(0, 0, 0, 90), anchor='mm')   # soft drop shadow for bright frames
d.text(xy, NAME, font=f, fill=(255, 255, 255, 150), anchor='mm')
OUT.parent.mkdir(parents=True, exist_ok=True); im.save(OUT); print('watermark', NAME, W, 'x', H)
