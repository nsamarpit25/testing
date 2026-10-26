"""overlay.py: burn word-by-word captions, labels, HUD and finishing FX onto the rendered frames and encode the reel.

  python3 overlay.py --frames DIR --labels labels.json --words narration.words.json --audio mix.wav --out preview.mp4 [--srt subs.srt]
  python3 overlay.py ... --preview 12.5,30.0 --pdir previews/     (stills with the overlay, no encode)

Captions reuse the how.its.engineered / letsbuildsimply-v2 system: one phrase at a time; each word fades in from a
blur and rises a few pixels the moment it is spoken, previous words stay until the line is complete, then the phrase
lifts away. *key* words are bold yellow, [pill] words sit in a yellow pill. Here they sit in the lower centre, inside
Instagram's safe area. On top: depth/temperature and speed readouts, an oscillation trace, rewind/freeze/flash FX,
a soft bloom and vignette, and a small @letsbuildsimply watermark.
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
ap.add_argument('--cap-y', type=float, default=0.695)
a = ap.parse_args()

LB = json.load(open(a.labels)); FPS = LB['fps']; NF = LB['nf']; W, H = LB['w'], LB['h']
HUD = {int(k): v for k, v in LB.get('hud', {}).items()}
WORDS = json.load(open(a.words))
K = W / 1080.0
def font(name, px): return ImageFont.truetype(os.path.join(FD, name), max(6, int(round(px * K))))
F_CAP = font('Poppins-ExtraBold.ttf', 64); F_TAG = font('Poppins-SemiBold.ttf', 40); F_NOTE = font('Poppins-SemiBold.ttf', 30)
F_HUDL = font('Poppins-SemiBold.ttf', 26); F_HUDV = font('Poppins-ExtraBold.ttf', 50); F_HUDS = font('Poppins-SemiBold.ttf', 30)
F_HANDLE = font('Poppins-SemiBold.ttf', 22 / K * K if False else 26)
YEL = (255, 211, 64); DARK = (24, 24, 28)
COL = dict(y=(255, 211, 64), r=(255, 96, 76), b=(90, 200, 255), g=(90, 230, 125), o=(255, 152, 44), m=(255, 70, 160), w=(230, 232, 240))

def clamp(x, lo=0.0, hi=1.0): return lo if x < lo else hi if x > hi else x
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x, s=2.2): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1

# ------------------------------------------------------------------ caption phrases (markup aligned to the spoken words)
PHRASES = [
    "What if you drilled straight through the *Earth...*", "and *jumped in?*", "First, the *drill.*",
    "It rips through the crust", "like *nothing.*", "But the *deeper* you go,", "the *hotter* it gets.",
    "The *mantle* isn't lava.", "It's [solid rock,]", "*glowing hot*", "under *crushing pressure.*",
    "Your drill starts to *fail.*", "Below that,", "a sea of [liquid iron]", "around a *solid core*",
    "as hot as the *Sun's surface.*", "Your drill? *Gone.*", "But suppose the *tunnel* existed.",
    "*No air,* *no friction.*", "You *jump.*", "You fall *faster.*", "And *faster.*", "At the *center,*",
    "there's [no net pull.]", "But you're at [top speed.]", "You fly straight *past,*", "slowing down",
    "until you just reach", "the *other side.*", "Then you fall *back.*", "Without *friction,*",
    "back and forth", "[forever.]",
]
def tokens(ph):
    out = []
    for m in re.finditer(r'\[[^\]]+\][.,!?]*|\*[^*]+\*[.,!?]*|\S+', ph):
        tk = m.group(0)
        if tk[0] == '[': out.append((tk.replace('[', '').replace(']', ''), 'pill'))
        elif tk[0] == '*':
            for w in tk.replace('*', '').split(): out.append((w, 'key'))
        else: out.append((tk, ''))
    return out
CUES = []; wi = 0
for ph in PHRASES:
    items = []
    for text, cls in tokens(ph):
        n = len(text.split()); ws = WORDS[wi:wi + n]; wi += n
        items.append(dict(text=text, cls=cls, t=ws[0]['s'], e=ws[-1]['e']))
    CUES.append(dict(items=items, t=items[0]['t'] - 0.06, last=items[-1]['e'], plain=re.sub(r'[\[\]*]', '', ph)))
assert wi == len(WORDS), (wi, len(WORDS))
for i, c in enumerate(CUES):
    nxt = CUES[i + 1]['t'] if i + 1 < len(CUES) else c['last'] + 3.0
    c['end'] = min(nxt - 0.02, c['last'] + 1.3)

# ------------------------------------------------------------------ word sprites (as in letsbuildsimply-v2)
_SPR = {}
def sprite(text, cls):
    key = (text, cls)
    if key in _SPR: return _SPR[key]
    f = F_CAP; bb = f.getbbox(text); tw, th = bb[2] - bb[0], f.getbbox('Hg')[3] - f.getbbox('Hg')[1]
    padx, pady = (int(20 * K), int(10 * K)) if cls == 'pill' else (int(4 * K), int(4 * K))
    m = int(24 * K) + 2; w, h = tw + 2 * padx + 2 * m, th + 2 * pady + 2 * m
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); ds = ImageDraw.Draw(sh)
    ox, oy = m + padx - bb[0], m + pady - f.getbbox('Hg')[1]
    if cls == 'pill':
        r = (m, m, w - m, h - m)
        ds.rounded_rectangle((r[0], r[1] + int(5 * K), r[2], r[3] + int(5 * K)), radius=int(18 * K), fill=(0, 0, 0, 150))
        d.rounded_rectangle(r, radius=int(18 * K), fill=YEL + (255,))
        d.text((ox, oy), text, font=f, fill=DARK + (255,))
    else:
        col = YEL if cls == 'key' else (255, 255, 255)
        ds.text((ox, oy + int(5 * K)), text, font=f, fill=(0, 0, 0, 210), stroke_width=max(1, int(7 * K)), stroke_fill=(0, 0, 0, 210))
        d.text((ox, oy), text, font=f, fill=col + (255,), stroke_width=max(1, int(3 * K)), stroke_fill=(20, 20, 24, 255))
    sh = sh.filter(ImageFilter.GaussianBlur(9 * K))
    out = Image.alpha_composite(sh, img)
    _SPR[key] = (out, m, tw + 2 * padx, th + 2 * pady)
    return _SPR[key]
_BL = {}
def blurred(text, cls, q):
    key = (text, cls, q)
    if key not in _BL:
        im = sprite(text, cls)[0]
        _BL[key] = im.filter(ImageFilter.GaussianBlur(q * 2.0 * K)) if q else im
    return _BL[key]
def layout(c):
    if 'lay' in c: return c['lay']
    maxw = int(0.86 * W); gap = int(16 * K); lines = [[]]; lw = 0
    for it in c['items']:
        _, m, bw, bh = sprite(it['text'], it['cls'])
        if lines[-1] and lw + gap + bw > maxw: lines.append([]); lw = 0
        lw += (gap if lines[-1] else 0) + bw; lines[-1].append((it, bw, bh))
    lh = int(90 * K); y0 = int(a.cap_y * H) - (len(lines) - 1) * lh // 2; pos = {}
    for li, ln in enumerate(lines):
        tot = sum(bw for _, bw, _ in ln) + gap * (len(ln) - 1); x = (W - tot) // 2
        for it, bw, bh in ln:
            pos[id(it)] = (x, y0 + li * lh); x += bw + gap
    c['lay'] = pos; return pos
def draw_captions(canvas, t):
    for c in CUES:
        if not (c['t'] <= t < c['end']): continue
        pos = layout(c)
        out = eo((t - (c['end'] - 0.22)) / 0.22) if t > c['end'] - 0.22 else 0.0
        for it in c['items']:
            p = clamp((t - it['t']) / 0.2)
            if p <= 0: continue
            q = int(round((1 - p) * 6))
            im = blurred(it['text'], it['cls'], q); _, m, _, _ = sprite(it['text'], it['cls'])
            x, y = pos[id(it)]
            y += int((1 - p) * 12 * K - out * 16 * K)
            alpha = p * (1 - out)
            if alpha < 1:
                im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v, al=alpha: int(v * al)))
            canvas.alpha_composite(im, (x - m, y - m))

# ------------------------------------------------------------------ labels
def tag_img(text, color, fnt=None, bg=225):
    fnt = fnt or F_TAG
    bb = fnt.getbbox(text); tw = bb[2] - bb[0]; th = fnt.getbbox('Hg')[3] - fnt.getbbox('Hg')[1]
    px, py, bar = int(22 * K), int(11 * K), int(8 * K); m = int(18 * K)
    w, h = tw + 2 * px + bar + 2 * m, th + 2 * py + 2 * m
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((m, m + int(4 * K), w - m, h - m + int(4 * K)), int(14 * K), fill=(0, 0, 0, 120))
    im = sh.filter(ImageFilter.GaussianBlur(7 * K)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((m, m, w - m, h - m), int(14 * K), fill=(18, 20, 26, bg))
    d.rounded_rectangle((m, m, m + bar + int(6 * K), h - m), int(14 * K), fill=color + (255,))
    d.rectangle((m + bar, m, m + bar + int(8 * K), h - m), fill=(18, 20, 26, bg))
    d.text((m + bar + px - bb[0], m + py - fnt.getbbox('Hg')[1]), text, font=fnt, fill=(255, 255, 255, 255))
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
    x = max(int(10 * K), min(W - im.width - int(10 * K), x)); y = max(int(0.12 * H), min(int(0.60 * H) - im.height, y))
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

# ------------------------------------------------------------------ HUD
def card(canvas, x, y, w, h, alpha=1.0):
    im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 24, 20 + w, 24 + h), int(18 * K), fill=(0, 0, 0, int(110 * alpha)))
    im = im.filter(ImageFilter.GaussianBlur(8 * K)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), int(18 * K), fill=(14, 16, 22, int(200 * alpha)), outline=(255, 255, 255, int(40 * alpha)), width=max(1, int(2 * K)))
    canvas.alpha_composite(im, (x - 20, y - 20)); return ImageDraw.Draw(canvas)
def fmt(n): return f'{int(round(n)):,}'
def hud_vis(f, key):
    """fade in/out for a HUD key over a few frames."""
    on = lambda k: key in HUD.get(k, {})
    if not on(f): return 0.0
    n_in = sum(1 for k in range(f - 6, f + 1) if on(k)) / 7; n_out = sum(1 for k in range(f, f + 7) if on(k)) / 7
    return min(n_in, n_out) ** 1.5
OSC_HIST = {}
def draw_hud(canvas, f, t):
    h = HUD.get(f, {})
    va = hud_vis(f, 'depth')
    if va > 0:
        x, y, w, hh = int(0.055 * W), int(0.125 * H), int(0.38 * W), int(0.115 * H)
        d = card(canvas, x, y, w, hh, va)
        A_ = int(255 * va)
        d.text((x + int(26 * K), y + int(14 * K)), 'DEPTH', font=F_HUDL, fill=(200, 205, 215, A_))
        d.text((x + int(26 * K), y + int(40 * K)), f"{fmt(h['depth'])} km", font=F_HUDV, fill=(255, 255, 255, A_))
        tc = h['temp']; heat = clamp(tc / 4300)
        col = (255, int(220 - 150 * heat), int(120 - 110 * heat))
        d.text((x + int(26 * K), y + int(96 * K)), f"{fmt(tc)} °C", font=F_HUDS, fill=col + (A_,))
        bx = x + w - int(34 * K); by0, by1 = y + int(18 * K), y + hh - int(18 * K)
        d.rounded_rectangle((bx, by0, bx + int(12 * K), by1), int(6 * K), fill=(255, 255, 255, int(40 * va)))
        fy = by0 + int((by1 - by0) * clamp(h['depth'] / 3500))
        d.rounded_rectangle((bx, by0, bx + int(12 * K), max(by0 + 2, fy)), int(6 * K), fill=col + (A_,))
    vs = hud_vis(f, 'speed')
    if vs > 0:
        x, y, w, hh = int(0.565 * W), int(0.125 * H), int(0.38 * W), int(0.115 * H)
        d = card(canvas, x, y, w, hh, vs); A_ = int(255 * vs)
        d.text((x + int(26 * K), y + int(14 * K)), 'SPEED', font=F_HUDL, fill=(200, 205, 215, A_))
        d.text((x + int(26 * K), y + int(40 * K)), fmt(h['speed']), font=F_HUDV, fill=(255, 255, 255, A_))
        d.text((x + int(26 * K), y + int(96 * K)), 'km/h', font=F_HUDS, fill=COL['b'] + (A_,))
        bx0, bx1, by = x + int(120 * K), x + w - int(24 * K), y + int(112 * K)
        d.rounded_rectangle((bx0, by, bx1, by + int(10 * K)), int(5 * K), fill=(255, 255, 255, int(40 * vs)))
        d.rounded_rectangle((bx0, by, bx0 + max(2, int((bx1 - bx0) * h['speed'] / 28400)), by + int(10 * K)), int(5 * K), fill=COL['b'] + (A_,))
    vo = hud_vis(f, 'osc')
    if vo > 0:
        x, y, w, hh = int(0.12 * W), int(0.12 * H), int(0.76 * W), int(0.10 * H)
        d = card(canvas, x, y, w, hh, vo); A_ = int(255 * vo)
        d.text((x + int(22 * K), y + int(10 * K)), 'POSITION  ·  sped up', font=F_HUDL, fill=(200, 205, 215, A_))
        px0, px1 = x + int(70 * K), x + w - int(26 * K); py0, py1 = y + int(46 * K), y + hh - int(14 * K)
        d.text((x + int(26 * K), py0 - int(12 * K)), 'N', font=F_HUDL, fill=(200, 205, 215, A_))
        d.text((x + int(26 * K), py1 - int(24 * K)), 'S', font=F_HUDL, fill=(200, 205, 215, A_))
        d.line((px0, (py0 + py1) // 2, px1, (py0 + py1) // 2), fill=(255, 255, 255, int(50 * vo)), width=1)
        ks = sorted(k for k in HUD if 'osc' in HUD[k] and k <= f)
        span = 4.2 * FPS
        pts = [(px0 + (px1 - px0) * (1 - (f - k) / span), py0 + (py1 - py0) * (1 - HUD[k]['osc']) / 2) for k in ks if f - k <= span]
        if len(pts) > 1:
            pts = [(p[0] - (pts[-1][0] - px1), p[1]) for p in pts]
            d.line(pts, fill=COL['b'] + (A_,), width=max(2, int(4 * K)), joint='curve')
            r = int(7 * K); cx, cy = pts[-1]; d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, A_))

_HANDLE = None
def draw_handle(canvas):
    global _HANDLE
    if _HANDLE is None:
        bb = F_HANDLE.getbbox(a.handle); m = 6
        _HANDLE = Image.new('RGBA', (bb[2] - bb[0] + 2 * m, bb[3] - bb[1] + 2 * m), (0, 0, 0, 0))
        ImageDraw.Draw(_HANDLE).text((m - bb[0], m - bb[1]), a.handle, font=F_HANDLE, fill=(255, 255, 255, 120), stroke_width=1, stroke_fill=(0, 0, 0, 60))
    canvas.alpha_composite(_HANDLE, ((W - _HANDLE.width) // 2, int(0.955 * H) - _HANDLE.height // 2))

# ------------------------------------------------------------------ finishing FX on the raw frame
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.32 * np.clip(((XX / W - 0.5) ** 2 / 0.3 + (YY / H - 0.5) ** 2 / 0.42) - 0.15, 0, 1) ** 1.3)[..., None]
CAPSHADE = (1 - 0.22 * np.exp(-((YY / H - a.cap_y - 0.01) / 0.12) ** 2))[..., None]
def finish(img, f, t):
    x = np.asarray(img, np.float32) / 255.0
    lum = x.mean(axis=2, keepdims=True)
    hi = np.clip((lum - 0.62) / 0.38, 0, 1) * x
    bl = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(22 * K)), np.float32) / 255.0
    bl2 = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6 * K)), np.float32) / 255.0
    mean = float(lum.mean())
    if mean > 0.42: x = x * (0.42 / mean) ** 0.75                       # tame frames that are mostly glowing core
    k = 1.0 - clamp((mean - 0.35) / 0.3) * 0.6
    x = x + bl * 0.42 * k + bl2 * 0.18 * k
    band = x[int((a.cap_y - 0.1) * H):int((a.cap_y + 0.12) * H)].mean()
    cs = 1 - (1 - CAPSHADE) * (1 + 0.9 * clamp((band - 0.35) / 0.3))
    x = x * VIG * cs
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
        d = 0.75 * (1 - clamp((u - 0.15) / 0.85)); x = x * (1 - d) + g * d * 1.05
        x = x + max(0.0, 1 - u / 0.12) * 0.7
    if 'flash' in h:
        u = h['flash']; x = x + (1 - u) ** 2 * 0.65 * np.array([1.0, 0.9, 0.75], np.float32)
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
    base = Image.open(os.path.join(a.frames, f'f_{f:05d}.png')).convert('RGB')
    if base.size != (W, H): base = base.resize((W, H), Image.LANCZOS)
    base = finish(base, f, t)
    draw_hud(base, f, t); draw_labels(base, f, t); draw_captions(base, t); rewind_icon(base, f); draw_handle(base)
    return base

def write_srt(path):
    def ts(x):
        ms = int(round(x * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(path, 'w') as fh:
        for i, c in enumerate(CUES, 1): fh.write(f"{i}\n{ts(max(0, c['t']))} --> {ts(c['end'])}\n{c['plain']}\n\n")

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
