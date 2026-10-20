# HUD overlays for the Blender reel, in the style of the early HTML reels (08 Docker, 09 Kubernetes):
#  - top-left "SYSTEM DESIGN" kicker pill + chapter title in Instrument Serif with one coloured italic word
#  - the ending profile card: a cursor taps the Message Queues reel, then Follow -> Following, with confetti
# usage: python3 hud.py <out dir> [--res 480] [--fps 24]   -> <out>/hud.txt and <out>/card.txt (ffmpeg concat lists)
import json, math, random, re, sys, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = Path(__file__).parent; ROOT = D.parents[1]
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
RES, FPS = int(opt('--res', 480)), int(opt('--fps', 24))
Wd, Ht = RES, int(RES * 16 / 9) // 2 * 2
k = Wd / 540
T = json.loads((D / 'voice/timings.json').read_text())
WORDS = json.loads((D / 'voice/words.json').read_text())
with wave.open(str(D / 'voice/voice.wav')) as wv: END = min(wv.getnframes() / wv.getframerate(), T[-1]['end'] + 1.8)
L = lambda li, pi=0: next(x['start'] for x in T if x['li'] == li and x['pi'] == pi)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
def Wt(tok, after=0.0): return next(s for w, s, e in WORDS if s >= after - 1e-6 and norm(w) == tok)

NM = ROOT / 'node_modules'
def font(path, size, wght=None):
    f = ImageFont.truetype(str(path), round(size * k))
    if wght: f.set_variation_by_axes([wght])
    return f
INTER = NM / '@fontsource-variable/inter/files/inter-latin-wght-normal.woff2'
SERIF = NM / '@fontsource/instrument-serif/files/instrument-serif-latin-400-normal.woff2'
SERIF_I = NM / '@fontsource/instrument-serif/files/instrument-serif-latin-400-italic.woff2'
MONO = NM / '@fontsource/jetbrains-mono/files/jetbrains-mono-latin-700-normal.woff2'
C = dict(amber='#FFC34D', red='#FF4757', cyan='#38B6FF', green='#2ECC71', violet='#A78BFA', orange='#FF6A1F', white='#FFFFFF', grey='#8A93A6')
rgb = lambda h, a=255: tuple(int(h.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) + (a,)

# ---------- chapter titles ----------
TITLES = [  # (start, [(text, colour or None for plain / italic colour word)])
    (0.0, [('One post, ', None), ('2M', 'amber'), (' followers', None)]),
    (L(1, 0), [('The ', None), ('simple', 'amber'), (' way', None)]),
    (L(2, 0), [('The ', None), ('problem', 'red')]),
    (L(4, 0), [('A queue? ', None), ('Not quite', 'cyan')]),
    (L(5, 0), [('The ', None), ('fix', 'green')]),
    (Wt('publishes'), [('01 · ', None), ('Publish', 'violet')]),
    (L(6, 0), [('02 · ', None), ('Subscribe', 'violet')]),
    (L(7, 0), [('Like a ', None), ('radio', 'amber')]),
    (L(8, 0), [('03 · ', None), ('Add a feature', 'green')]),
    (L(9, 0), [('One publish, ', None), ('2M', 'green'), (' notified', None)]),
    (L(10, 0), [('In the ', None), ('real world', 'amber')]),
    (L(11, 0) - 0.15, None),
]
FK, FT, FTI = font(MONO, 11), font(SERIF, 38), font(SERIF_I, 38)
def top_shade(im):
    sh = Image.new('L', (1, Ht))
    for y in range(Ht): sh.putpixel((0, y), int(150 * max(0.0, 1 - y / (0.2 * Ht)) ** 1.6))
    black = Image.new('RGBA', (Wd, Ht), (4, 6, 11, 255)); black.putalpha(sh.resize((Wd, Ht)))
    im.alpha_composite(black)
def hud_frame(parts):
    im = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0))
    top_shade(im)
    if parts is None: return im
    d = ImageDraw.Draw(im)
    x0, y0 = 24 * k, 58 * k
    kt = 'SYSTEM DESIGN'
    kw = d.textlength(kt, font=FK)
    d.rounded_rectangle((x0, y0, x0 + kw + 14 * k, y0 + 19 * k), radius=4 * k, fill=rgb('#FF7A1A'))
    d.text((x0 + 7 * k, y0 + 9.5 * k), kt, font=FK, fill=rgb('#140A02'), anchor='lm')
    x, yb = x0, y0 + 64 * k
    for txt, col in parts:
        f = FTI if col else FT
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        ds.text((x, yb), txt, font=f, fill=(0, 0, 0, 200), anchor='ls')
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3 * k)))
        d.text((x, yb), txt, font=f, fill=rgb(C[col] if col else '#FFFFFF'), anchor='ls')
        x += d.textlength(txt, font=f)
    return im
hd = out / 'hud'; hd.mkdir(exist_ok=True)
lines = []
for i, (t0, parts) in enumerate(TITLES):
    t1 = TITLES[i + 1][0] if i + 1 < len(TITLES) else END
    p = hd / f'h_{i:02d}.png'; hud_frame(parts).save(p)
    lines += [f"file '{p}'", f'duration {t1 - t0:.3f}']
lines.append(f"file '{p}'")
(out / 'hud.txt').write_text('\n'.join(lines) + '\n')

# ---------- ending profile card ----------
T0 = L(11, 0) - 0.15
t_mq, t_follow = Wt('queues', L(11, 0)), Wt('follow', L(11, 0))
FH, FS, FB = font(INTER, 17, 800), font(INTER, 11.5, 500), font(INTER, 13, 750)
FM, FMs = font(MONO, 10), font(MONO, 9)
CX0, CY0, CX1, CY1 = 34, 300, 506, 600              # card box on the 540 x 960 stage
TILES = [('MESSAGE QUEUES', 'cyan', 'queue'), ('RETRIES', 'amber', 'retry'), ('TIMEOUTS', 'violet', 'clock')]
TX = [CX0 + 18 + i * 150 for i in range(3)]; TY, TW, TH_ = 404, 136, 168
BTN = (CX1 - 112, 324, CX1 - 18, 356)
ease = lambda u: 1 - (1 - max(0.0, min(1.0, u))) ** 3
def lerp(a, b, u): return a + (b - a) * u
def cursor_pos(t):
    pts = [(T0 + 0.2, (560, 760)), (t_mq - 0.25, (TX[0] + TW * 0.6, TY + TH_ * 0.42)), (t_follow - 0.45, (TX[0] + TW * 0.6, TY + TH_ * 0.42)),
           (t_follow - 0.05, ((BTN[0] + BTN[2]) / 2 + 8, (BTN[1] + BTN[3]) / 2 + 6)), (99, ((BTN[0] + BTN[2]) / 2 + 8, (BTN[1] + BTN[3]) / 2 + 6))]
    if t <= pts[0][0]: return pts[0][1]
    for (ta, pa), (tb, pb) in zip(pts, pts[1:]):
        if ta <= t <= tb:
            u = ease((t - ta) / (tb - ta)) if tb > ta else 1
            return (lerp(pa[0], pb[0], u), lerp(pa[1], pb[1], u))
    return pts[-1][1]
random.seed(4)
CONF = [(random.uniform(-1, 1), random.uniform(-1.6, -0.4), random.choice(list(C.values())[:5]), random.uniform(0, 6.28)) for _ in range(40)]
S = lambda *v: tuple(x * k for x in v)
def icon(d, kind, cx, cy, col):
    c = rgb(C[col])
    if kind == 'queue':
        for i in range(3): d.rounded_rectangle(S(cx - 34 + i * 24, cy - 9, cx - 16 + i * 24, cy + 9), radius=3 * k, fill=c if i < 2 else rgb(C[col], 110))
        d.polygon([S(cx + 40, cy), S(cx + 31, cy - 7), S(cx + 31, cy + 7)], fill=c)
    elif kind == 'retry':
        d.arc(S(cx - 20, cy - 20, cx + 20, cy + 20), 30, 320, fill=c, width=round(4 * k))
        d.polygon([S(cx + 19, cy - 14), S(cx + 8, cy - 15), S(cx + 17, cy - 3)], fill=c)
    else:
        d.ellipse(S(cx - 20, cy - 20, cx + 20, cy + 20), outline=c, width=round(4 * k))
        d.line([S(cx, cy), S(cx, cy - 12)], fill=c, width=round(3 * k)); d.line([S(cx, cy), S(cx + 9, cy + 4)], fill=c, width=round(3 * k))
def card_frame(t):
    im = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0))
    u = ease((t - T0) / 0.4); dy = (1 - u) * 60
    lay = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle(S(CX0, CY0 + dy + 8, CX1, CY1 + dy + 14), radius=18 * k, fill=(0, 0, 0, 170))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14 * k)))
    d.rounded_rectangle(S(CX0, CY0 + dy, CX1, CY1 + dy), radius=18 * k, fill=rgb('#0D1322', 238), outline=rgb('#2A3550'), width=max(1, round(k)))
    # header: avatar, handle, follow button
    ax, ay = CX0 + 40, CY0 + 40 + dy
    av = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); da = ImageDraw.Draw(av)
    for i in range(24):
        r = 24 - i; col = tuple(int(lerp(a, b, i / 23)) for a, b in zip(rgb('#26B8FF')[:3], rgb('#8C7BFF')[:3])) + (255,)
        da.ellipse(S(ax - r, ay - r, ax + r, ay + r), fill=col)
    lay.alpha_composite(av)
    d.text(S(ax, ay), '{ }', font=FB, fill=rgb('#FFFFFF'), anchor='mm')
    d.text(S(ax + 36, ay - 9), '@how.its.engineered', font=FH, fill=rgb('#FFFFFF'), anchor='lm')
    d.text(S(ax + 36, ay + 12), 'System design for vibe coders', font=FS, fill=rgb(C['grey']), anchor='lm')
    b = (BTN[0], BTN[1] + dy, BTN[2], BTN[3] + dy)
    followed = t >= t_follow
    press = 0.9 if t_follow - 0.02 <= t < t_follow + 0.1 else 1.0
    bc = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2); bw, bh = (b[2] - b[0]) / 2 * press, (b[3] - b[1]) / 2 * press
    d.rounded_rectangle(S(bc[0] - bw, bc[1] - bh, bc[0] + bw, bc[1] + bh), radius=9 * k, fill=rgb('#232C40') if followed else rgb('#3B82F6'))
    d.text(S(bc[0] - (6 if followed else 0), bc[1]), 'Following' if followed else 'Follow', font=FB if not followed else font(INTER, 12, 700), fill=rgb('#FFFFFF'), anchor='mm')
    if followed: d.line([S(bc[0] + 30, bc[1]), S(bc[0] + 34, bc[1] + 4), S(bc[0] + 41, bc[1] - 4)], fill=rgb(C['green']), width=max(1, round(2 * k)))
    d.line(S(CX0 + 16, CY0 + 78 + dy, CX1 - 16, CY0 + 78 + dy), fill=rgb('#1F2840'), width=max(1, round(k)))
    # reel tiles
    hot = t >= t_mq
    for i, (name, col, kind) in enumerate(TILES):
        x0, y0 = TX[i], TY + dy
        sel = hot and i == 0
        if sel:
            g = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); ImageDraw.Draw(g).rounded_rectangle(S(x0 - 4, y0 - 4, x0 + TW + 4, y0 + TH_ + 4), radius=14 * k, fill=rgb(C[col], 150))
            lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(8 * k)))
        d.rounded_rectangle(S(x0, y0, x0 + TW, y0 + TH_), radius=12 * k, fill=rgb('#141C2E'), outline=rgb(C[col]) if sel else rgb('#273250'), width=max(1, round((2 if sel else 1) * k)))
        icon(d, kind, x0 + TW / 2, y0 + 62, col)
        d.text(S(x0 + TW / 2, y0 + 122), name, font=FM, fill=rgb('#E8EEF8'), anchor='mm')
        d.text(S(x0 + TW / 2, y0 + 142), 'SYSTEM DESIGN', font=FMs, fill=rgb(C['grey']), anchor='mm')
    if hot:
        pu = ease((t - t_mq) / 0.25)
        tx, ty = TX[0] + TW / 2, TY + dy - 16 - (1 - pu) * 8
        tw = d.textlength('WATCH THIS FIRST', font=FMs) / k + 22
        d.rounded_rectangle(S(tx - tw / 2, ty - 10, tx + tw / 2, ty + 10), radius=10 * k, fill=rgb(C['cyan'], int(255 * pu)))
        d.text(S(tx, ty), 'WATCH THIS FIRST', font=FMs, fill=rgb('#04121F', int(255 * pu)), anchor='mm')
    im.alpha_composite(lay)
    # confetti from the follow button
    if t >= t_follow:
        dc = ImageDraw.Draw(im); s_ = t - t_follow
        if s_ < 1.4:
            for vx, vy, col, rot in CONF:
                px = bc[0] + vx * 160 * s_; py = bc[1] + vy * 260 * s_ + 300 * s_ * s_
                a = int(255 * max(0, 1 - s_ / 1.4))
                r = 4
                pts = [(px + r * math.cos(rot + s_ * 8 + q * 1.57), py + r * 0.5 * math.sin(rot + s_ * 8 + q * 1.57)) for q in range(4)]
                dc.polygon([S(*p) for p in pts], fill=rgb(col, a))
    # cursor (with click ripple)
    cx, cy = cursor_pos(t)
    dc = ImageDraw.Draw(im)
    for tc in (t_mq - 0.1, t_follow):
        s_ = t - tc
        if 0 <= s_ < 0.45:
            r = 8 + 40 * s_; dc.ellipse(S(cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, int(220 * (1 - s_ / 0.45))), width=max(1, round(2 * k)))
    sc_ = 0.85 if any(0 <= t - tc < 0.12 for tc in (t_mq - 0.1, t_follow)) else 1.0
    arrow = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]
    pts = [S(cx + x * sc_, cy + y * sc_) for x, y in arrow]
    shd = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); ImageDraw.Draw(shd).polygon([(x + 2 * k, y + 3 * k) for x, y in pts], fill=(0, 0, 0, 150))
    im.alpha_composite(shd.filter(ImageFilter.GaussianBlur(2 * k)))
    dc = ImageDraw.Draw(im); dc.polygon(pts, fill=rgb('#FFFFFF'), outline=rgb('#0B0F18'))
    a = min(1.0, (t - T0) / 0.3)
    if a < 1: im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    return im
cd = out / 'card'; cd.mkdir(exist_ok=True)
blank = cd / 'blank.png'; Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)).save(blank)
lines = [f"file '{blank}'", f'duration {T0:.3f}']
n = int((END - T0) * FPS) + 1
for i in range(n):
    p = cd / f'c_{i:04d}.png'; card_frame(T0 + i / FPS).save(p)
    lines += [f"file '{p}'", f'duration {1 / FPS:.5f}']
lines.append(f"file '{p}'")
(out / 'card.txt').write_text('\n'.join(lines) + '\n')
print('hud', len(TITLES), 'titles; card', n, 'frames from', round(T0, 2))
