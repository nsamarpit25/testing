# Phone screen textures for reel 20: v1 (blue app), v2 (canary-yellow app), crash. Rounded corners are baked in (black outside).
from PIL import Image, ImageDraw, ImageFont
import os
D = os.path.dirname(os.path.abspath(__file__)); W, H = 600, 1300; R = 70
FB = lambda s: ImageFont.truetype(f'{D}/fonts/Inter-Bold.ttf', s); FS = lambda s: ImageFont.truetype(f'{D}/fonts/Inter-SemiBold.ttf', s)
def base(bg):
    im = Image.new('RGB', (W, H), (0, 0, 0)); m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W - 1, H - 1), R, fill=255)
    im.paste(Image.new('RGB', (W, H), bg), (0, 0), m); return im, ImageDraw.Draw(im)
def app(acc, deep, ver, name):
    im, d = base((246, 247, 250))
    d.text((48, 34), '9:41', font=FS(30), fill=(30, 30, 34))
    d.rounded_rectangle((W - 120, 42, W - 52, 66), 8, outline=(30, 30, 34), width=3); d.rectangle((W - 116, 46, W - 70, 62), fill=(30, 30, 34))
    d.rounded_rectangle((28, 100, W - 28, 470), 44, fill=acc)
    d.text((70, 150), name, font=FB(76), fill=deep)
    d.rounded_rectangle((70, 262, 214, 316), 27, fill=deep); d.text((142, 289), ver, font=FB(34), fill=acc, anchor='mm')
    d.rounded_rectangle((70, 360, W - 70, 400), 20, fill=tuple(int(c * 0.86) for c in acc))
    for i in range(3):
        y = 510 + i * 200
        d.rounded_rectangle((28, y, W - 28, y + 170), 34, fill=(255, 255, 255))
        d.rounded_rectangle((52, y + 24, 174, y + 146), 26, fill=acc)
        d.rounded_rectangle((200, y + 44, W - 70, y + 74), 15, fill=(214, 217, 224))
        d.rounded_rectangle((200, y + 96, W - 170, y + 122), 13, fill=(232, 234, 239))
    d.rounded_rectangle((28, 1130, W - 28, 1250), 60, fill=deep)
    d.text((W // 2, 1190), 'Buy now', font=FB(46), fill=acc, anchor='mm')
    return im
app((47, 107, 255), (12, 32, 92), 'v1', 'Shop').save(f'{D}/tex/v1.png')
app((255, 194, 26), (66, 44, 0), 'v2', 'Shop').save(f'{D}/tex/v2.png')
im, d = base((12, 12, 14))
d.ellipse((W // 2 - 120, 400, W // 2 + 120, 640), fill=(255, 69, 58))
d.rounded_rectangle((W // 2 - 16, 448, W // 2 + 16, 560), 14, fill=(255, 255, 255)); d.ellipse((W // 2 - 19, 576, W // 2 + 19, 614), fill=(255, 255, 255))
d.text((W // 2, 740), 'App stopped', font=FB(62), fill=(255, 255, 255), anchor='mm')
d.text((W // 2, 820), 'Shop keeps crashing', font=FS(36), fill=(150, 150, 158), anchor='mm')
d.rounded_rectangle((90, 1100, W - 90, 1200), 50, fill=(44, 44, 48)); d.text((W // 2, 1150), 'Close app', font=FB(40), fill=(255, 255, 255), anchor='mm')
im.save(f'{D}/tex/crash.png')
print('ok')
