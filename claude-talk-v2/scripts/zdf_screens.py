# Monitor pictures for the Zack D.-style test: a dark code editor with a big day counter (legible in-scene text, like the
# reference's wall calendar) that climbs through the year, and a "shipped" store page at the end.
# usage: python3 scripts/zdf_screens.py <ep>   -> audio/<ep>/screens/d1, d92, d183, d274, ship.png (+ p1.png phone)
import random, shutil, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
out = HERE / 'audio' / sys.argv[1] / 'screens'
out.mkdir(parents=True, exist_ok=True)
W, H = 1600, 944
SF, MONO = '/System/Library/Fonts/SFNS.ttf', '/System/Library/Fonts/Menlo.ttc'


def font(size, mono=False):
    f = ImageFont.truetype(MONO if mono else SF, size)
    if not mono:
        f.set_variation_by_axes([700, 0, 0][:len(f.get_variation_axes())])  # bold weight
    return f


def editor(day, lines, seed):
    rnd = random.Random(seed)
    im = Image.new('RGB', (W, H), '#1e2230')
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 70), fill='#151824')
    for i, c in enumerate(('#ff5f57', '#febc2e', '#28c840')):
        d.ellipse((28 + i * 40, 22, 54 + i * 40, 48), fill=c)
    d.text((170, 18), 'my-first-app / main.py', font=font(30), fill='#8c93a8')
    cols = ('#7fd1c7', '#f2c94c', '#e88aa8', '#a3b8ff', '#c9d1e6')
    y = 110
    for n in range(lines):
        d.text((40, y), f'{n + 1:>3}', font=font(26, True), fill='#4a5168')
        x = 120 + rnd.choice((0, 0, 40, 80))
        for _ in range(rnd.randint(2, 5)):
            w = rnd.randint(60, 220)
            d.rounded_rectangle((x, y + 6, x + w, y + 26), 8, fill=rnd.choice(cols))
            x += w + 18
            if x > 880:
                break
        y += 44
    # the day counter card, top right: big and high contrast so it reads at phone size
    d.rounded_rectangle((1010, 120, 1560, 470), 34, fill='#2fd27a')
    d.text((1285, 205), 'DAY', font=font(70), fill='#0f3a22', anchor='mm')
    d.text((1285, 345), str(day), font=font(170), fill='#ffffff', anchor='mm')
    d.rounded_rectangle((1010, 510, 1560, 600), 24, fill='#2a3044')
    d.text((1285, 555), '20 min  ✓', font=font(52), fill='#2fd27a', anchor='mm')
    return im


for i, day in enumerate((1, 92, 183, 274)):
    editor(day, 8 + i * 4 if i < 3 else 18, 30 + i).save(out / f'd{day}.png')

im = Image.new('RGB', (W, H), '#f4f6fb')
d = ImageDraw.Draw(im)
d.rectangle((0, 0, W, 70), fill='#e3e7f0')
d.rounded_rectangle((120, 150, 520, 550), 80, fill='#2fd27a')
d.text((320, 350), '✓', font=font(260), fill='#ffffff', anchor='mm')
d.text((600, 210), 'My First App', font=font(96), fill='#1a1f2e')
d.text((604, 330), '★★★★★   1,204 downloads', font=font(48), fill='#5a6378')
d.rounded_rectangle((600, 420, 1020, 530), 55, fill='#2f7bf5')
d.text((810, 475), 'LIVE', font=font(64), fill='#ffffff', anchor='mm')
d.rounded_rectangle((120, 640, 1480, 860), 30, fill='#2fd27a')
d.text((800, 750), 'SHIPPED  \U0001F680'.replace('\U0001F680', '→ Day 365'), font=font(90), fill='#ffffff', anchor='mm')
im.save(out / 'ship.png')
shutil.copy(HERE / 'audio/ep21/screens/p1.png', out / 'p1.png')
print('screens in', out)
