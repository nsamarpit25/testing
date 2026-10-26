"""overlay.py: burn word-by-word captions, labels, HUD and finishing FX onto the rendered frames and encode the reel.

  python3 overlay.py --frames DIR --labels labels.json --words narration.words.json --audio mix.wav --out preview.mp4 [--srt subs.srt]
  python3 overlay.py ... --preview 12.5,30.0 --pdir previews/     (stills with the overlay, no encode)

Captions borrow only an idea from how.its.engineered (low in the frame, with a line) and are styled for this series:
one short line at a time (<= 4 words / 24 characters) around y ~ 1496 of 1920, Poppins SemiBold with key words in
Instrument Serif italic (amber; green for 'smooth' ideas, warm red for 'bumpy' ones); each word rises in the moment it
is spoken and stays; an amber rule under the line draws itself word by word, a dot riding its head. Proof graphics come from scene.py's per-frame projections: the dotted axle-height
reference, the axle trail, the height bracket + pivot ring, the contact trail, the catenary profile drawn left to right,
powered-axle icons. Rewind/freeze FX, light bloom, vignette and grain, and the small @letsbuildsimply watermark at
bottom centre (y ~ 1740 of 1920), positioned independently of the captions.
"""
import argparse, json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
ap = argparse.ArgumentParser()
ap.add_argument('--frames'); ap.add_argument('--labels', required=True); ap.add_argument('--words', required=True)
ap.add_argument('--audio'); ap.add_argument('--out'); ap.add_argument('--srt')
ap.add_argument('--preview'); ap.add_argument('--pdir', default='previews')
ap.add_argument('--handle', default='@letsbuildsimply'); ap.add_argument('--crf', default='18')
ap.add_argument('--cap-y', type=float, default=1496 / 1920); ap.add_argument('--events'); ap.add_argument('--capvar', default='A')
ap.add_argument('--cap-delay', type=float, default=0.15)   # s: captions trail the word timestamps (they read early on phones)
a = ap.parse_args()

LB = json.load(open(a.labels)); FPS = LB['fps']; NF = LB['nf']; W, H = LB['w'], LB['h']
HUD = {int(k): v for k, v in LB.get('hud', {}).items()}
WORDS = json.load(open(a.words))
K = W / 1080.0
def font(name, px): return ImageFont.truetype(os.path.join(FD, name), max(6, int(round(px * K))))
F_TAG = font('Poppins-SemiBold.ttf', 25); F_NOTE = font('Poppins-SemiBold.ttf', 21)
F_HUDL = font('Poppins-SemiBold.ttf', 26); F_HUDV = font('Poppins-ExtraBold.ttf', 50); F_HUDS = font('Poppins-SemiBold.ttf', 30)
F_HANDLE = font('Poppins-SemiBold.ttf', 27)
YEL = (255, 211, 64); DARK = (24, 24, 28)
COL = dict(y=(255, 208, 128), r=(255, 112, 84), b=(150, 200, 232), g=(150, 222, 160), o=(255, 172, 64), m=(255, 70, 160), w=(230, 232, 240))

def clamp(x, lo=0.0, hi=1.0): return lo if x < lo else hi if x > hi else x
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x, s=2.2): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1

# ------------------------------------------------------------------ captions (how.its.engineered style)
PHRASES = [
    "These wheels are *square.*", "So why isn't the ride *bumpy?*", "On a *flat road,*", "the axle *climbs* and *drops*",
    "as each corner turns over.", "Now... *change the road.*", "These curved sections", "are shaped to *match the square,*",
    "keeping its center", "at the [same height]", "as it rolls.", "The road does the *smoothing.*",
    "Real square wheel demonstrations", "use this idea;", "the curve is called", "an [inverted catenary.]",
    "It still takes *energy* to move,", "and the wheel size", "has to *match the road.*", "The surprise isn't",
    "that squares became circles.", "It's that the road", "was [part of the machine.]",
]
O_, RED_, OK_, AMB_ = (255, 178, 74), (255, 122, 92), (160, 226, 168), (255, 208, 128)      # warm gallery palette (cart amber, wall green)
SPECIAL = {'bumpy?': RED_, 'climbs': RED_, 'drops': RED_, 'smoothing.': OK_, 'same': OK_, 'height': OK_, 'energy': AMB_}
CW = []                                                    # caption words: text, colour, spoken start/end
for ph in PHRASES:
    for m in re.finditer(r'\[[^\]]+\][.,!?;]*|\*[^*]+\*[.,!?;]*|\S+', ph):
        tk = m.group(0); star = tk[0] in '[*'
        for w in tk.replace('*', '').replace('[', '').replace(']', '').split():
            CW.append(dict(s=w, col=(SPECIAL.get(w.lower(), O_) if star else None)))
assert len(CW) == len(WORDS), (len(CW), len(WORDS))
for c_, w_ in zip(CW, WORDS): c_['a'], c_['b'] = w_['s'] + a.cap_delay, w_['e'] + a.cap_delay
WEAK = {'a', 'an', 'the', 'are', 'on', 'in', 'it', 'and', 'at', 'is', 'of', 'to', 'for', 'with', 'by', 'its', 'has', 'that', 'so', 'but', 'or', 'if', 'your', 'you'}
CHUNKS = []; cur = []
def flush():
    global cur
    if not cur: return
    carry = []
    while len(carry) < 2 and len(cur) >= 2 and not re.search(r'[.,?:!;]$', cur[-1]['s']) and cur[-1]['s'].lower() in WEAK: carry.insert(0, cur.pop())
    CHUNKS.append(cur); cur = carry
for w in CW:
    prev = cur[-1] if cur else None; ln = sum(len(x['s']) + 1 for x in cur)
    if prev and (re.search(r'[.?:!;]$', prev['s']) or (prev['s'].endswith(',') and len(cur) >= 3) or len(cur) >= 4 or ln + len(w['s']) > 24 or w['a'] - prev['b'] > 0.6): flush()
    cur.append(w)
flush()
for i in range(len(CHUNKS) - 1, 0, -1):
    c, p = CHUNKS[i], CHUNKS[i - 1]; ln = sum(len(x['s']) + 1 for x in p + c)
    if len(c) <= 2 and len(p) + len(c) <= 5 and not re.search(r'[.?!]$', p[-1]['s']) and ln <= 30: p.extend(c); CHUNKS.pop(i)
for i, c in enumerate(CHUNKS):
    c_t0 = c[0]['a'] - 0.04
    c_t1 = min(CHUNKS[i + 1][0]['a'] - 0.04, c[-1]['b'] + 0.9) if i + 1 < len(CHUNKS) else NF / FPS
    CHUNKS[i] = dict(words=c, t0=c_t0, t1=c_t1, plain=' '.join(x['s'] for x in c))
# Our own look (only the idea is borrowed: low in the frame, with a line): no band. Plain words in Poppins sit on a soft
# shadow; key words switch to Instrument Serif italic in amber. Under the line an amber rule draws itself left to right
# as the words are spoken, with a small dot at its head, like the axle line and contact dot in the film.
CAPVARS = {   # A: sans + serif-italic keys   B: all bold sans   C: all serif italic (editorial)   D: sans, keys in caps + tracking
    'A': ('Poppins-SemiBold.ttf', 50, 'InstrumentSerif-Italic.woff2', 74),
    'B': ('Poppins-ExtraBold.ttf', 54, 'Poppins-ExtraBold.ttf', 54),
    'C': ('InstrumentSerif-Italic.woff2', 72, 'InstrumentSerif-Italic.woff2', 72),
    'D': ('Poppins-Medium.ttf', 48, 'Poppins-ExtraBold.ttf', 48)}
_cv = CAPVARS[a.capvar]
def _f(name, px):
    return font(name if os.path.exists(os.path.join(FD, name)) else 'Poppins-SemiBold.ttf', px)
F_W = _f(_cv[0], _cv[1]); F_K = _f(_cv[2], _cv[3])
CAP_CY = int(a.cap_y * H)
_WS = {}
def word_img(text, col):
    key = (text, col)
    if key not in _WS:
        f = F_K if col else F_W; asc, desc = f.getmetrics(); m = int(16 * K)
        tw = int(f.getlength(text)); w, h = tw + 2 * m, asc + desc + 2 * m
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = im.copy()
        ImageDraw.Draw(sh).text((m, m + int(3 * K)), text, font=f, fill=(0, 0, 0, 215))
        sh = sh.filter(ImageFilter.GaussianBlur(7 * K))
        ImageDraw.Draw(im).text((m, m), text, font=f, fill=(col or (250, 246, 238)) + (255,))
        _WS[key] = (Image.alpha_composite(sh, im), m, tw, asc)       # asc: baseline offset from the top margin
    return _WS[key]
_GLOW = {}
def glow(w):
    if w not in _GLOW:                                     # a very soft dark pool behind the line, not a band
        hh = int(150 * K); ww = w + int(160 * K)
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        al = np.exp(-(((xx - ww / 2) / (ww * 0.42)) ** 4 + ((yy - hh / 2) / (hh * 0.36)) ** 2)) * 120
        arr = np.zeros((hh, ww, 4), np.uint8); arr[..., 0:3] = (10, 9, 7); arr[..., 3] = al.astype(np.uint8)
        _GLOW[w] = Image.fromarray(arr)
    return _GLOW[w]
def draw_captions(canvas, t):
    for c in CHUNKS:
        if not (c['t0'] <= t < c['t1']): continue
        fo = clamp((c['t1'] - t) / 0.16)
        gap = int(15 * K); items = []
        for w in c['words']:
            txt = re.sub(r'[.,:;]+$', '', w['s'])
            if a.capvar == 'D' and w['col']: txt = txt.upper()
            items.append((w,) + word_img(txt, w['col']))
        tot = sum(x[3] for x in items) + gap * (len(items) - 1); x0 = (W - tot) // 2
        g = glow(tot); ga = clamp((t - c['t0']) / 0.12) * fo
        if ga < 0.999: g = g.copy(); g.putalpha(g.getchannel('A').point(lambda v, al=ga: int(v * al)))
        canvas.alpha_composite(g, ((W - g.width) // 2, CAP_CY - g.height // 2))
        base = CAP_CY + int(14 * K); x = x0; heads = []
        for w, im, m, tw, asc in items:
            p = clamp((t - (w['a'] - 0.05)) / 0.16)
            if p > 0:
                e = 1 - (1 - p) ** 3; al = p * fo
                if al < 0.999: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v, a_=al: int(v * a_)))
                canvas.alpha_composite(im, (x - m, base - asc - m + int((1 - e) * 10 * K)))
            heads.append((x, x + tw, w['a'], w['b'])); x += tw + gap
        # the amber rule: its head follows the spoken word, a dot rides the head until the line is complete
        ly = base + int(20 * K); lx0 = x0 - int(18 * K); lx1 = x0 + tot + int(18 * K)
        if t < heads[0][2]: hx = lx0
        else:
            hx = lx1
            for xa, xb, wa, wb in heads:
                if t < wb: hx = xa + (xb - xa) * clamp((t - wa) / max(0.05, wb - wa)); break
            if t >= heads[-1][3]: hx = lx1
            hx = max(lx0, min(lx1, hx + (int(18 * K) if t >= heads[-1][3] else 0)))
        d = ImageDraw.Draw(canvas); lw = max(2, int(3 * K))
        d.line((lx0, ly, lx1, ly), fill=(255, 255, 255, int(38 * fo)), width=max(1, int(2 * K)))
        if hx > lx0:
            d.line((lx0, ly, hx, ly), fill=(226, 142, 44, int(235 * fo)), width=lw)
            r = int(5 * K)
            if t < heads[-1][3]: d.ellipse((hx - r, ly - r, hx + r, ly + r), fill=(255, 196, 110, int(255 * fo)))

# ------------------------------------------------------------------ labels
def tag_img(text, color, fnt=None, bg=235):
    """gallery placard: letter-spaced Poppins caps on a warm near-black chip with an accent bar on the left."""
    fnt = fnt or F_TAG; sp = 2.0 * K * (fnt.size / F_TAG.size)
    widths = [fnt.getlength(ch) for ch in text]; tw = int(sum(widths) + sp * (len(text) - 1))
    asc = fnt.getbbox('HG'); th = asc[3] - asc[1]
    px, py, m = int(18 * K), int(13 * K), int(22 * K); bar = int(7 * K)
    w, h = tw + 2 * px + bar + 2 * m, th + 2 * py + 2 * m
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((m, m + int(8 * K), w - m, h - m + int(8 * K)), int(10 * K), fill=(8, 6, 4, 150))
    im = sh.filter(ImageFilter.GaussianBlur(12 * K)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((m, m, w - m, h - m), int(10 * K), fill=(18, 17, 13, bg))
    d.rounded_rectangle((m, m, m + bar + int(10 * K), h - m), int(10 * K), fill=color + (255,)); d.rectangle((m + bar, m, m + bar + int(10 * K), h - m), fill=(18, 17, 13, bg))
    x = m + bar + px; y = m + py - asc[1]
    for ch, cw in zip(text, widths):
        d.text((x, y), ch, font=fnt, fill=(246, 238, 222, 255)); x += cw + sp
    return im
_LC = {}
def cached(key, fn):
    if key not in _LC: _LC[key] = fn()
    return _LC[key]
def scaled(im, s, alpha):
    if abs(s - 1) > 0.01: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if alpha < 0.999: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    return im
def place(canvas, im, cx, cy):
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    x = max(int(10 * K), min(W - im.width - int(10 * K), x)); y = max(int(0.12 * H), min(int(0.735 * H) - im.height, y))
    canvas.alpha_composite(im, (x, y))
def draw_labels(canvas, f, t):
    for L in LB['labels']:
        p = L['pts'].get(str(f))
        if p is None: continue
        age = t - L['t0']; left = L['t1'] - t
        pop = back(age / 0.22); fade = clamp(age / 0.12) * clamp(left / 0.15)
        if L['style'] == 'note':
            im = cached(('note', L['text']), lambda: tag_img(L['text'], COL[L['color']], F_NOTE, 170))
            place(canvas, scaled(im, 1.0, fade * 0.92), p[0] * W, p[1] * H)
        else:
            im = cached(('tag', L['text'], L['color']), lambda: tag_img(L['text'], COL[L['color']]))
            place(canvas, scaled(im, 0.6 + 0.4 * pop, fade), p[0] * W, p[1] * H)

# ------------------------------------------------------------------ proof graphics (scene.py projects them per frame)
EV = json.load(open(a.events)) if a.events else None
SHOTS = EV['shots'] if EV else {}
def px(p): return (p[0] * W * 2, p[1] * H * 2)            # drawn on a 2x layer, downsampled for clean anti-aliasing
def dashed(d, p0, p1, col, w, dash=16, gap=11):
    (x0, y0), (x1, y1) = px(p0), px(p1); L_ = math.hypot(x1 - x0, y1 - y0)
    if L_ < 1: return
    ux, uy = (x1 - x0) / L_, (y1 - y0) / L_; s_ = 0.0; dd, gg = dash * K * 2, gap * K * 2
    while s_ < L_:
        e = min(L_, s_ + dd); d.line((x0 + ux * s_, y0 + uy * s_, x0 + ux * e, y0 + uy * e), fill=col, width=w); s_ = e + gg
def poly(d, pts, col, w, fade=True):
    P = [px(p) for p in pts]
    for i in range(1, len(P)):
        al = (i / len(P)) ** 0.8 if fade else 1.0
        d.line((P[i - 1], P[i]), fill=col[:3] + (int(col[3] * al),), width=w)
def dot(d, p, r, fill=None, outline=None, w=1):
    x, y = px(p); r *= K * 2; d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=w)
def bolt(d, cx, cy, s, col):
    pts = [(0.15, -1.0), (-0.55, 0.15), (-0.05, 0.15), (-0.25, 1.0), (0.55, -0.2), (0.05, -0.2), (0.3, -1.0)]
    d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=col)
def shot_of(t):
    cur = 'A'
    for k, v in sorted(SHOTS.items(), key=lambda kv: kv[1]):
        if t >= v: cur = k
    return cur
def draw_hud(canvas, f, t):
    h = HUD.get(f)
    if not h: return
    lay = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    S = shot_of(t); lw = max(2, int(4 * K * 2))
    RED, GRN, Y, WH = (255, 96, 76), (90, 230, 125), (255, 211, 64), (255, 255, 255)
    ra = h.get('ref_a', 1.0)
    for key in ('ref', 'ref2'):
        if key in h: dashed(d, h[key][0], h[key][1], WH + (int(185 * ra),), max(2, int(3 * K * 2)))
    for key, col in (('trail', RED if (S in ('B', 'C') or 'ref2' in h) else GRN), ('trail2', GRN)):
        if key in h and len(h[key]) > 1:
            poly(d, h[key], (0, 0, 0, 110), lw + int(4 * K * 2)); poly(d, h[key], col + (255,), lw)
            dot(d, h[key][-1], 7, fill=col + (255,), outline=WH + (255,), w=max(2, int(3 * K * 2)))
    if 'bracket' in h:
        (x0, y0), (x1, y1) = px(h['bracket'][0]), px(h['bracket'][1]); bx = x0 + 34 * K * 2
        tw = 12 * K * 2
        for c, w_ in (((0, 0, 0, 120), lw + int(4 * K * 2)), (Y + (255,), lw)):
            d.line((bx, y0, bx, y1), fill=c, width=w_); d.line((bx - tw, y0, bx + tw, y0), fill=c, width=w_); d.line((bx - tw, y1, bx + tw, y1), fill=c, width=w_)
        dot(d, h['bracket'][0], 6, fill=Y + (255,), outline=(20, 20, 24, 255), w=max(2, int(2 * K * 2)))
    if 'pivot' in h:
        pr = 13 + 3 * math.sin(t * 9)
        dot(d, h['pivot'], pr, outline=(0, 0, 0, 120), w=lw + int(4 * K * 2)); dot(d, h['pivot'], pr, outline=RED + (255,), w=lw)
    if 'ctrail' in h and len(h['ctrail']) > 1:
        poly(d, h['ctrail'], (255, 150, 50, 90), lw + int(8 * K * 2)); poly(d, h['ctrail'], (255, 170, 70, 255), max(2, int(3 * K * 2)))
    if 'prof' in h:
        P = h['prof']; n = int(round(h['prof_u'] * (len(P) - 1))); al = h.get('prof_a', 1.0)
        if n >= 1:
            poly(d, P[:n + 1], (0, 0, 0, int(110 * al)), lw + int(6 * K * 2), False); poly(d, P[:n + 1], WH + (int(255 * al),), lw + int(1 * K * 2), False)
            if h['prof_u'] < 1: dot(d, P[n], 9, fill=Y + (255,), outline=WH + (255,), w=max(2, int(2 * K * 2)))
    if 'motor' in h:
        for mx, my, ang in h['motor']:
            cx, cy = px((mx, my)); r = 30 * K * 2
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(18, 20, 26, 215), outline=Y + (255,), width=max(2, int(3 * K * 2)))
            bolt(d, cx, cy, r * 0.62, Y + (255,))
            R_ = r + 12 * K * 2; a0 = math.degrees(ang) % 360
            d.arc((cx - R_, cy - R_, cx + R_, cy + R_), a0, a0 + 250, fill=Y + (230,), width=max(2, int(4 * K * 2)))
            ae = math.radians(a0 + 250); hx, hy = cx + R_ * math.cos(ae), cy + R_ * math.sin(ae); tx, ty = -math.sin(ae), math.cos(ae)
            hs = 11 * K * 2
            d.polygon([(hx + tx * hs, hy + ty * hs), (hx - math.cos(ae) * hs * 0.8, hy - math.sin(ae) * hs * 0.8), (hx + math.cos(ae) * hs * 0.8, hy + math.sin(ae) * hs * 0.8)], fill=Y + (230,))
    canvas.alpha_composite(lay.resize((W, H), Image.LANCZOS))

_HANDLE = None
def draw_handle(canvas):
    global _HANDLE
    if _HANDLE is None:
        bb = F_HANDLE.getbbox(a.handle); m = 6
        _HANDLE = Image.new('RGBA', (bb[2] - bb[0] + 2 * m, bb[3] - bb[1] + 2 * m), (0, 0, 0, 0))
        ImageDraw.Draw(_HANDLE).text((m - bb[0], m - bb[1]), a.handle, font=F_HANDLE, fill=(255, 255, 255, 115), stroke_width=1, stroke_fill=(0, 0, 0, 55))
    canvas.alpha_composite(_HANDLE, ((W - _HANDLE.width) // 2, int(1740 / 1920 * H) - _HANDLE.height // 2))

# ------------------------------------------------------------------ finishing FX on the raw frame (photographic, light-handed)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.26 * np.clip(((XX / W - 0.5) ** 2 / 0.3 + (YY / H - 0.5) ** 2 / 0.42) - 0.15, 0, 1) ** 1.3)[..., None]
CAPSHADE = np.ones((H, W, 1), np.float32)
GR = np.random.default_rng(5)
def finish(img, f, t):
    x = np.asarray(img, np.float32) / 255.0
    lum = x.mean(axis=2, keepdims=True)
    hi = np.clip((lum - 0.7) / 0.3, 0, 1) * x
    bl = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18 * K)), np.float32) / 255.0
    x = x + bl * 0.22
    x = x * VIG * CAPSHADE
    h = HUD.get(f, {})
    if 'rewind' in h:
        u = h['rewind']; amt = math.sin(math.pi * u)
        g = x.mean(axis=2, keepdims=True); x = x * (1 - 0.5 * amt) + g * 0.5 * amt
        s = int(8 * K * amt) + 1
        x[..., 0] = np.roll(x[..., 0], s, axis=1); x[..., 2] = np.roll(x[..., 2], -s, axis=1)
        band = ((YY + f * 37) % (H * 0.23) < H * 0.025)[..., None]
        x = np.where(band, np.roll(x, int(14 * K * amt), axis=1) * 1.15, x)
        x = x * (0.92 + 0.08 * (np.sin(YY * 1.4)[..., None] > 0))
    if 'freeze' in h:
        u = h['freeze']; g = x.mean(axis=2, keepdims=True)
        dsat = 0.45 * (1 - clamp((u - 0.2) / 0.8)); x = x * (1 - dsat) + g * dsat
    x = x + GR.normal(0, 0.010, (H, W, 1)).astype(np.float32)
    x = np.clip(x, 0, 1)
    return Image.fromarray((x * 255 + 0.5).astype(np.uint8)).convert('RGBA')
def rewind_icon(canvas, f):
    h = HUD.get(f, {})
    if 'rewind' not in h: return
    d = ImageDraw.Draw(canvas); s = int(34 * K); x0, y0 = int(0.78 * W), int(0.14 * H)
    for k in range(2):
        xo = x0 + k * int(s * 0.75)
        d.polygon([(xo + s, y0), (xo + s, y0 + s), (xo + int(s * 0.25), y0 + s // 2)], fill=(255, 255, 255, 230))

def compose(f):
    t = f / FPS
    pth = os.path.join(a.frames, f'f_{f:05d}.png')
    if not os.path.exists(pth): pth = pth[:-4] + '.jpg'                # frames shipped between machines as max-quality JPEG
    base = Image.open(pth).convert('RGB')
    if base.size != (W, H): base = base.resize((W, H), Image.LANCZOS)
    base = finish(base, f, t)
    draw_hud(base, f, t); draw_labels(base, f, t); draw_captions(base, t); rewind_icon(base, f); draw_handle(base)
    return base

def write_srt(path):
    def ts(x):
        ms = int(round(x * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(path, 'w') as fh:
        for i, c in enumerate(CHUNKS, 1): fh.write(f"{i}\n{ts(max(0, c['t0']))} --> {ts(c['t1'])}\n{c['plain']}\n\n")

if a.srt: write_srt(a.srt); print('srt', a.srt)
if a.preview:
    os.makedirs(a.pdir, exist_ok=True)
    for ts_ in a.preview.split(','):
        f = int(round(float(ts_) * FPS)); compose(f).convert('RGB').save(os.path.join(a.pdir, f'p_{float(ts_):06.2f}.jpg'), quality=90)
    print('previews', a.pdir); sys.exit(0)

cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-i', a.audio, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', a.crf, '-profile:v', 'high',
       '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{NF / FPS:.3f}', '-movflags', '+faststart', a.out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for f in range(NF):
    pr.stdin.write(compose(f).convert('RGB').tobytes())
    if f % 150 == 0: print('frame', f, flush=True)
pr.stdin.close(); pr.wait(); print('ENCODED', a.out, pr.returncode)
