# Screen textures for reel 20: portrait airport departure screens (v1 navy header, v2 canary-yellow header), the blue crash
# screen, the "installing update" toast, kiosk / ATM / ward-monitor screens, and three wall-wide images.
# usage: python3 videos/20-canary-releases/ui.py
from PIL import Image, ImageDraw, ImageFont
import math, os, random
D = os.path.dirname(os.path.abspath(__file__)); T = f'{D}/tex'; os.makedirs(T, exist_ok=True)
F = lambda n, s: ImageFont.truetype(f'{D}/fonts/{n}', s)
IB, ISB, IM, IX = (lambda s: F('Inter-Bold.ttf', s)), (lambda s: F('Inter-SemiBold.ttf', s)), (lambda s: F('Inter-Medium.ttf', s)), (lambda s: F('Inter-ExtraBold.ttf', s))
DIN, MONO = (lambda s: F('DINAlternate-Bold.ttf', s)), (lambda s: F('JetBrainsMono-Bold.ttf', s))
W, H = 540, 960
NAVY, HEAD1, HEAD2 = (8, 16, 38), (20, 52, 120), (255, 194, 26)
CITIES = ['LONDON', 'DUBAI', 'SINGAPORE', 'NEW YORK', 'TOKYO', 'PARIS', 'SYDNEY', 'FRANKFURT', 'DELHI', 'TORONTO', 'MUMBAI', 'SEOUL',
          'ISTANBUL', 'AMSTERDAM', 'MADRID', 'ROME', 'CHICAGO', 'DOHA', 'BANGKOK', 'ZURICH', 'LISBON', 'OSLO', 'CAIRO', 'BOSTON']
def plane(d, x, y, s, c):
    d.polygon([(x - 1.0 * s, y - 0.1 * s), (x + 0.95 * s, y - 0.12 * s), (x + 1.15 * s, y), (x + 0.95 * s, y + 0.12 * s), (x - 1.0 * s, y + 0.1 * s)], fill=c)
    for sg in (-1, 1):
        d.polygon([(x + 0.25 * s, y + sg * 0.08 * s), (x - 0.2 * s, y + sg * 0.8 * s), (x + 0.02 * s, y + sg * 0.8 * s), (x + 0.55 * s, y + sg * 0.08 * s)], fill=c)
        d.polygon([(x - 0.75 * s, y + sg * 0.06 * s), (x - 1.0 * s, y + sg * 0.38 * s), (x - 0.86 * s, y + sg * 0.38 * s), (x - 0.55 * s, y + sg * 0.06 * s)], fill=c)
def fids(seed, v2):
    rnd = random.Random(seed); im = Image.new('RGB', (W, H), NAVY); d = ImageDraw.Draw(im)
    hc, tc = (HEAD2, (40, 26, 0)) if v2 else (HEAD1, (255, 255, 255))
    d.rectangle((0, 0, W, 112), fill=hc)
    plane(d, 50, 56, 24, tc); d.text((90, 56), 'DEPARTURES', font=IX(44), fill=tc, anchor='lm')
    d.text((W - 28, 56), '04:09', font=DIN(40), fill=tc, anchor='rm')
    g = (120, 134, 170)
    d.text((30, 140), 'TIME', font=MONO(17), fill=g, anchor='lm'); d.text((128, 140), 'DESTINATION', font=MONO(17), fill=g, anchor='lm')
    d.text((W - 30, 140), 'STATUS', font=MONO(17), fill=g, anchor='rm')
    hh, mm = 5, rnd.randrange(0, 50, 5); cities = rnd.sample(CITIES, 8)
    for i, city in enumerate(cities):
        y = 170 + i * 90
        if i % 2 == 0: d.rectangle((0, y - 4, W, y + 82), fill=(12, 23, 52))
        mm += rnd.choice((5, 10, 15)); hh += mm // 60; mm %= 60
        d.text((30, y + 26), f'{hh:02d}:{mm:02d}', font=DIN(36), fill=(255, 196, 64), anchor='lm')
        d.text((128, y + 26), city, font=IB(34), fill=(240, 244, 252), anchor='lm')
        code = f'{rnd.choice("AXQNVK")}{rnd.choice("ZRLJ")} {rnd.randrange(100, 999)}'
        d.text((128, y + 62), f'{code}   GATE {rnd.choice("ABC")}{rnd.randrange(1, 40)}', font=ISB(21), fill=(138, 152, 186), anchor='lm')
        st = rnd.choice(['ON TIME', 'BOARDING', 'ON TIME', 'ON TIME'])
        col = (52, 211, 153) if st == 'ON TIME' else (255, 176, 46)
        tw = d.textlength(st, font=IB(20)) + 26
        d.rounded_rectangle((W - 30 - tw, y + 47, W - 30, y + 77), 15, fill=tuple(int(c * 0.22) for c in col), outline=col, width=2)
        d.text((W - 30 - tw / 2, y + 62), st, font=IB(20), fill=col, anchor='mm')
    d.rectangle((0, 900, W, H), fill=(5, 10, 26)); d.text((30, 930), 'FREE WI-FI  ·  ALL GATES', font=MONO(16), fill=(96, 110, 148), anchor='lm')
    if v2:
        d.rounded_rectangle((W - 92, 912, W - 26, 948), 18, fill=HEAD2); d.text((W - 59, 930), 'v2', font=IB(22), fill=(40, 26, 0), anchor='mm')
    return im
for i in range(6):
    fids(100 + i, False).save(f'{T}/fids{i}.png'); fids(100 + i, True).save(f'{T}/fidsv{i}.png')
BL = (16, 104, 204)
def bsod(w, h, s=1.0):
    im = Image.new('RGB', (w, h), BL); d = ImageDraw.Draw(im); x = int(48 * s)
    d.text((x, int(h * 0.30)), ':(', font=IM(int(170 * s)), fill=(255, 255, 255), anchor='ls')
    d.text((x, int(h * 0.40)), 'Something went wrong.', font=ISB(int(32 * s)), fill=(255, 255, 255), anchor='ls')
    d.text((x, int(h * 0.40) + int(44 * s)), 'Restarting...', font=ISB(int(32 * s)), fill=(255, 255, 255), anchor='ls')
    d.text((x, int(h * 0.40) + int(110 * s)), '0% complete', font=IM(int(26 * s)), fill=(214, 230, 250), anchor='ls')
    d.text((x, int(h * 0.62)), 'Stop code: PAGE_FAULT', font=MONO(int(17 * s)), fill=(190, 214, 245), anchor='ls')
    return im
bsod(W, H).save(f'{T}/bsod.png'); bsod(800, 600, 0.95).save(f'{T}/bsod_l.png')
# "installing update" toast (RGBA); the bar fill is drawn in the shader over x 60..480, y 846..866
im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
d.rounded_rectangle((24, 742, W - 24, 892), 22, fill=(6, 9, 18, 244), outline=(60, 76, 112, 255), width=2)
d.ellipse((50, 772, 86, 808), outline=(255, 255, 255, 255), width=4); d.line((68, 781, 68, 795), fill=(255, 255, 255, 255), width=4)
d.polygon([(61, 792), (75, 792), (68, 800)], fill=(255, 255, 255, 255))
d.text((100, 790), 'Installing update', font=IB(28), fill=(255, 255, 255, 255), anchor='lm')
d.text((100, 822), 'Security sensor  ·  file 291', font=ISB(19), fill=(140, 154, 190, 255), anchor='lm')
d.rounded_rectangle((60, 846, 480, 866), 10, fill=(42, 53, 80, 255))
im.save(f'{T}/toast.png')
im = Image.new('RGB', (800, 600), (244, 246, 250)); d = ImageDraw.Draw(im)
d.rectangle((0, 0, 800, 90), fill=HEAD1); plane(d, 60, 45, 22, (255, 255, 255)); d.text((100, 45), 'Self check-in', font=IB(38), fill=(255, 255, 255), anchor='lm')
d.text((60, 190), 'Welcome', font=IX(64), fill=(16, 24, 48), anchor='lm'); d.text((60, 262), 'Scan your boarding pass', font=ISB(32), fill=(90, 100, 130), anchor='lm')
d.rounded_rectangle((60, 420, 740, 530), 55, fill=HEAD1); d.text((400, 475), 'Start', font=IB(42), fill=(255, 255, 255), anchor='mm')
im.save(f'{T}/kiosk.png')
im = Image.new('RGB', (800, 600), (6, 44, 52)); d = ImageDraw.Draw(im)
d.text((400, 150), 'Welcome', font=IX(80), fill=(255, 255, 255), anchor='mm'); d.text((400, 245), 'Please insert your card', font=ISB(38), fill=(150, 220, 214), anchor='mm')
d.rounded_rectangle((300, 340, 500, 470), 16, outline=(150, 220, 214), width=6); d.rectangle((330, 380, 470, 396), fill=(150, 220, 214))
im.save(f'{T}/atm.png')
im = Image.new('RGB', (800, 600), (4, 6, 8)); d = ImageDraw.Draw(im)
for row, (col, amp, y0, per) in enumerate((((60, 230, 110), 70, 130, 160), ((70, 200, 255), 30, 300, 120), ((255, 220, 80), 25, 450, 200))):
    pts = []
    for x in range(20, 560, 3):
        u = (x % per) / per
        if row == 0: yv = -amp if 0.42 < u < 0.46 else (amp * 0.35 if 0.46 <= u < 0.5 else (-amp * 0.15 if 0.2 < u < 0.28 else 0))
        else: yv = amp * math.sin(2 * math.pi * x / per)
        pts.append((x, y0 + yv))
    d.line(pts, fill=col, width=4)
for lab, val, col, y in (('HR', '72', (60, 230, 110), 130), ('SpO2', '98', (70, 200, 255), 300), ('RESP', '16', (255, 220, 80), 450)):
    d.text((600, y - 40), lab, font=IB(28), fill=col, anchor='lm'); d.text((600, y + 20), val, font=DIN(90), fill=col, anchor='lm')
im.save(f'{T}/ward.png')
# wall-wide images (the wall is 6.45 x 11.12 m)
SW_, SH2 = 1160, 2000
def wall(kind):
    im = Image.new('RGB', (SW_, SH2), (6, 10, 24)); d = ImageDraw.Draw(im)
    if kind == 'stages':
        d.text((SW_ / 2, 300), 'UPDATES', font=IX(160), fill=(255, 255, 255), anchor='mm')
        d.text((SW_ / 2, 470), 'IN STAGES', font=IX(160), fill=HEAD2, anchor='mm')
        for i, (lab, p) in enumerate((('1%', 0.01), ('5%', 0.05), ('25%', 0.25), ('100%', 1.0))):
            y = 700 + i * 300
            d.text((120, y + 90), lab, font=DIN(150), fill=HEAD2 if i == 0 else (255, 255, 255), anchor='lm')
            d.rounded_rectangle((560, y + 50, 1040, y + 130), 40, fill=(30, 40, 70))
            d.rounded_rectangle((560, y + 50, 560 + max(80, 480 * p), y + 130), 40, fill=HEAD2)
            if i < 3: d.polygon([(800 - 30, y + 205), (800 + 30, y + 205), (800, y + 245)], fill=(90, 110, 160))
    else:
        top, bot = (('AWS', 'CODEDEPLOY') if kind == 'aws' else ('ARGO', 'ROLLOUTS'))
        d.text((SW_ / 2, 840), top, font=IX(300), fill=(255, 255, 255), anchor='mm')
        d.text((SW_ / 2, 1090), bot, font=IX(150 if kind == 'argo' else 130), fill=HEAD2, anchor='mm')
        d.text((SW_ / 2, 1290), 'canary releases, built in', font=ISB(60), fill=(140, 154, 190), anchor='mm')
    return im
for k in ('stages', 'argo', 'aws'): wall(k).save(f'{T}/wall_{k}.png')
print('ok')
# patient chart for the clipboard
im = Image.new('RGB', (430, 560), (246, 243, 234)); d = ImageDraw.Draw(im); rnd = random.Random(5)
d.text((24, 34), 'PATIENT CHART', font=IX(34), fill=(20, 24, 40), anchor='lm'); d.text((24, 70), 'WARD 4  ·  BED 12', font=MONO(18), fill=(90, 96, 110), anchor='lm')
for i in range(12):
    y = 110 + i * 38; d.line((20, y, 410, y), fill=(170, 190, 215), width=2)
    d.text((26, y + 19), f'0{4 + i // 6}:{(i % 6) * 10:02d}', font=MONO(15), fill=(120, 126, 140), anchor='lm')
    x = 110; pts = []
    for k in range(rnd.randrange(6, 14)):
        x += rnd.uniform(10, 22); pts.append((x, y + 19 + rnd.uniform(-8, 8)))
    d.line(pts, fill=(28, 52, 140), width=3)
im.save(f'{T}/chart.png')
print('chart ok')
