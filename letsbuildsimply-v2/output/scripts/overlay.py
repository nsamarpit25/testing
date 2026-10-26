"""overlay.py: burn HIE-style word-by-word captions + engineering labels onto the rendered frames and encode the reel.

  python3 overlay.py --frames DIR --labels labels.json --words narration.words.json --audio mix.wav --out final.mp4 [--srt subs.srt]
  python3 overlay.py ... --preview 12.5,30.0 --pdir previews/     (stills with the overlay, no encode)
  python3 overlay.py ... --thumb 50.8 --thumb-out thumbnail.png

Captions follow how.its.engineered: one phrase at a time near the top; each word fades in from a blur and rises a few
pixels at the moment it is spoken, until the line is complete; then the phrase lifts away. *key* words are bold
yellow and [pill] words sit in a yellow pill. White text with a soft shadow keeps it readable over the bright 3D scene.
"""
import argparse, json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
ap = argparse.ArgumentParser()
ap.add_argument('--frames'); ap.add_argument('--labels', required=True); ap.add_argument('--words', required=True)
ap.add_argument('--audio'); ap.add_argument('--out'); ap.add_argument('--srt')
ap.add_argument('--preview'); ap.add_argument('--pdir', default='previews')
ap.add_argument('--thumb'); ap.add_argument('--thumb-out', default='thumbnail.png'); ap.add_argument('--thumb-frame')
ap.add_argument('--handle', default='@letsbuildsimply')
ap.add_argument('--handle-size', type=float, default=34); ap.add_argument('--handle-y', type=float, default=0.88)
ap.add_argument('--handle-alpha', type=int, default=140); ap.add_argument('--speed', type=float, default=1.0)
a = ap.parse_args()

LB = json.load(open(a.labels)); FPS = LB['fps']; NF = LB['nf']; W, H = LB['w'], LB['h']
WORDS = json.load(open(a.words))
K = W / 1080.0
def font(name, px): return ImageFont.truetype(os.path.join(FD, name), int(round(px * K)))
F_CAP = font('Poppins-ExtraBold.ttf', 66); F_TAG = font('Poppins-SemiBold.ttf', 42); F_BIG = font('Poppins-Black.ttf', 150)
F_HANDLE = font('Poppins-SemiBold.ttf', a.handle_size); F_MSG = font('Poppins-SemiBold.ttf', 44); F_MSGH = font('Poppins-SemiBold.ttf', 30)
YEL = (255, 211, 64); DARK = (24, 24, 28)
COL = dict(y=(255, 211, 64), r=(255, 96, 76), b=(90, 175, 255), g=(90, 230, 125), o=(255, 152, 44))

def clamp(x, lo=0.0, hi=1.0): return lo if x < lo else hi if x > hi else x
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x, s=2.2): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1

# ------------------------------------------------------------------ caption phrases (markup aligned to the spoken words)
PHRASES = [
    "This rock weighs [100 tons.]", "His job? *Move it.*", "*No crane.*", "He pushes.", "The rock doesn't even *notice.*",
    "So he ties a *rope* and pulls.", "That rope is rated for *2 tons.*", "The rock weighs [50 times] more.", "*Snap.*",
    "So he grabs a *lever.*", "*Long side,* *short side.*", "[50 to 1.]", "He's too light,", "so he adds a *ton* of *sandbags.*",
    "And the edge *lifts.*", "Now slide *rollers* underneath.", "He's not *dragging* 100 tons anymore.", "He's *rolling* it.",
    "That only takes about [2 tons] of pull.", "A *pry bar* nudges it", "a few centimeters per heave.", "At this rate, it'll take *a week.*",
    "So he builds a [capstan.]", "*Long arms,* *skinny drum.*", "[20 to 1.]", "Loop the rope around a *pulley* on the rock,",
    "and that *doubles* it.", "One engineer,", "[40 times] stronger.", "The rollers move at *half* the rock's speed,",
    "so it just *keeps coming.*", "*Destination* reached.", "One guy, one rock,", "[zero cranes.]", "Then the *client* texts.",
]
def tokens(ph):
    out = []
    for m in re.finditer(r'\[[^\]]+\][.,!?]*|\*[^*]+\*[.,!?]*|\S+', ph):
        tk = m.group(0)
        if tk[0] == '[':
            out.append((tk.replace('[', '').replace(']', ''), 'pill', True))
        elif tk[0] == '*':
            for w in tk.replace('*', '').split(): out.append((w, 'key', False))
        else: out.append((tk, '', False))
    return out
CUES = []; wi = 0
for ph in PHRASES:
    toks = tokens(ph); items = []
    for text, cls, grp in toks:
        n = len(text.split())
        ws = WORDS[wi:wi + n]; wi += n
        items.append(dict(text=text, cls=cls, t=ws[0]['s'], e=ws[-1]['e']))
    CUES.append(dict(items=items, t=items[0]['t'] - 0.06, last=items[-1]['e'], plain=re.sub(r'[\[\]*]', '', ph)))
assert wi == len(WORDS), (wi, len(WORDS))
for i, c in enumerate(CUES):
    nxt = CUES[i + 1]['t'] if i + 1 < len(CUES) else c['last'] + 3.0
    c['end'] = min(nxt - 0.02, c['last'] + 1.3)

# ------------------------------------------------------------------ word sprites
_SPR = {}
def sprite(text, cls):
    key = (text, cls)
    if key in _SPR: return _SPR[key]
    f = F_CAP; bb = f.getbbox(text); tw, th = bb[2] - bb[0], f.getbbox('Hg')[3] - f.getbbox('Hg')[1]
    padx, pady = (int(20 * K), int(10 * K)) if cls == 'pill' else (int(4 * K), int(4 * K))
    m = int(24 * K); w, h = tw + 2 * padx + 2 * m, th + 2 * pady + 2 * m
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
        ds.text((ox, oy + int(5 * K)), text, font=f, fill=(0, 0, 0, 200), stroke_width=int(6 * K), stroke_fill=(0, 0, 0, 200))
        d.text((ox, oy), text, font=f, fill=col + (255,), stroke_width=int(3 * K), stroke_fill=(20, 20, 24, 255))
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
    """wrap words into centred lines; returns per-item (x, y) top-left of the visible box."""
    if 'lay' in c: return c['lay']
    maxw = int(0.86 * W); gap = int(16 * K); lines = [[]]; lw = 0
    for it in c['items']:
        _, m, bw, bh = sprite(it['text'], it['cls'])
        if lines[-1] and lw + gap + bw > maxw: lines.append([]); lw = 0
        lw += (gap if lines[-1] else 0) + bw; lines[-1].append((it, bw, bh))
    lh = int(92 * K); y0 = int(0.205 * H) - (len(lines) - 1) * lh // 2; pos = {}
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
def tag_img(text, color, strike=0.0):
    bb = F_TAG.getbbox(text); tw = bb[2] - bb[0]; th = F_TAG.getbbox('Hg')[3] - F_TAG.getbbox('Hg')[1]
    px, py, bar = int(22 * K), int(12 * K), int(8 * K); m = int(18 * K)
    w, h = tw + 2 * px + bar + 2 * m, th + 2 * py + 2 * m
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((m, m + int(4 * K), w - m, h - m + int(4 * K)), int(14 * K), fill=(0, 0, 0, 120))
    im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7 * K)), im); d = ImageDraw.Draw(im)
    d.rounded_rectangle((m, m, w - m, h - m), int(14 * K), fill=(22, 24, 30, 225))
    d.rounded_rectangle((m, m, m + bar + int(6 * K), h - m), int(14 * K), fill=color + (255,))
    d.rectangle((m + bar, m, m + bar + int(8 * K), h - m), fill=(22, 24, 30, 225))
    d.text((m + bar + px - bb[0], m + py - F_TAG.getbbox('Hg')[1]), text, font=F_TAG, fill=(255, 255, 255, 255))
    if strike > 0:
        y = h // 2; x0 = m + bar + px - int(6 * K); x1 = x0 + int((tw + int(12 * K)) * strike)
        d.line((x0, y, x1, y), fill=COL['r'] + (255,), width=int(7 * K))
    return im, m
def big_img(text):
    bb = F_BIG.getbbox(text); m = int(30 * K); w, h = bb[2] - bb[0] + 2 * m, bb[3] - bb[1] + 2 * m
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh = im.copy()
    ImageDraw.Draw(sh).text((m - bb[0], m - bb[1] + int(8 * K)), text, font=F_BIG, fill=(0, 0, 0, 170), stroke_width=int(10 * K), stroke_fill=(0, 0, 0, 170))
    d = ImageDraw.Draw(im); d.text((m - bb[0], m - bb[1]), text, font=F_BIG, fill=YEL + (255,), stroke_width=int(7 * K), stroke_fill=DARK + (255,))
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * K)), im)
_LC = {}
def cached(key, fn):
    if key not in _LC: _LC[key] = fn()
    return _LC[key]
def scaled(im, s, alpha):
    if abs(s - 1) > 0.01:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    return im
def place(canvas, im, cx, cy, keep=True):
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if keep:
        x = max(int(10 * K), min(W - im.width - int(10 * K), x)); y = max(int(0.29 * H), min(int(0.80 * H) - im.height, y))
    canvas.alpha_composite(im, (x, y))
def msg_card(t, t0):
    w = int(0.80 * W); pad = int(30 * K)
    head = 'Client'; body = ['Love it!! Can we move it', '2 m to the left?']
    lh = int(58 * K); h = pad * 2 + int(44 * K) + lh * len(body)
    im = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0)); sh = im.copy()
    ImageDraw.Draw(sh).rounded_rectangle((30, 36, 30 + w, 36 + h), int(34 * K), fill=(0, 0, 0, 140))
    im = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12 * K)), im); d = ImageDraw.Draw(im)
    d.rounded_rectangle((30, 30, 30 + w, 30 + h), int(34 * K), fill=(250, 250, 252, 250))
    cx, cy, r = 30 + pad + int(20 * K), 30 + pad + int(18 * K), int(20 * K)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(90, 175, 255, 255))
    d.text((cx + r + int(14 * K), cy - int(20 * K)), head + '  ·  now', font=F_MSGH, fill=(120, 120, 128, 255))
    typing = t - t0 < 0.5
    if typing:
        for k in range(3):
            ph = math.sin((t - t0) * 12 - k * 0.9) * 0.5 + 0.5
            x = 30 + pad + k * int(30 * K) + int(10 * K); y = 30 + pad + int(70 * K)
            d.ellipse((x, y - int(6 * K * ph), x + int(18 * K), y + int(18 * K) - int(6 * K * ph)), fill=(150, 150, 158, 255))
    else:
        for i, ln in enumerate(body):
            d.text((30 + pad, 30 + pad + int(48 * K) + i * lh), ln, font=F_MSG, fill=DARK + (255,))
    return im
def draw_labels(canvas, f, t):
    for L in LB['labels']:
        pts = L['pts']; p = pts.get(str(f))
        if p is None: continue
        age = t - L['t0']; left = L['t1'] - t
        pop = back(age / 0.22); fade = clamp(age / 0.12) * clamp(left / 0.15)
        cx, cy = p[0] * W, p[1] * H
        st = L['style']
        if st in ('tag', 'strike'):
            strike = clamp((age - 0.45) / 0.35) if st == 'strike' else 0.0
            im, m = tag_img(L['text'], COL[L['color']], strike) if strike > 0 else cached(('tag', L['text'], L['color']), lambda: tag_img(L['text'], COL[L['color']]))
            place(canvas, scaled(im, 0.6 + 0.4 * pop, fade), cx, cy)
        elif st == 'big':
            im = cached(('big', L['text']), lambda: big_img(L['text']))
            place(canvas, scaled(im, 0.4 + 0.6 * pop, fade), cx, cy, keep=False)
        elif st == 'badge':
            im = cached(('badge',), lambda: tag_img('TIME-LAPSE  ×30', COL['r'])[0])
            blink = 0.55 + 0.45 * (math.sin(t * 8) > 0)
            canvas.alpha_composite(scaled(im, 0.85, fade * blink), (int(24 * K), int(0.285 * H)))
        elif st == 'text':
            im = msg_card(t, L['t0'])
            dy = (1 - eo(age / 0.3)) * 80 * K
            place(canvas, scaled(im, 1.0, clamp(age / 0.2)), cx, cy + dy, keep=False)
HANDLE = None
def draw_handle(canvas):
    global HANDLE
    if HANDLE is None:
        bb = F_HANDLE.getbbox(a.handle); m = 10
        HANDLE = Image.new('RGBA', (bb[2] - bb[0] + 2 * m, bb[3] - bb[1] + 2 * m), (0, 0, 0, 0))
        ImageDraw.Draw(HANDLE).text((m - bb[0], m - bb[1]), a.handle, font=F_HANDLE, fill=(255, 255, 255, a.handle_alpha), stroke_width=1, stroke_fill=(0, 0, 0, a.handle_alpha // 2))
    canvas.alpha_composite(HANDLE, ((W - HANDLE.width) // 2, int(a.handle_y * H)))

def compose(f):
    t = f / FPS
    base = Image.open(os.path.join(a.frames, f'f_{f:05d}.png')).convert('RGBA')
    if base.size != (W, H): base = base.resize((W, H), Image.LANCZOS)
    draw_labels(base, f, t); draw_captions(base, t); draw_handle(base)
    return base

def write_srt(path):
    def ts(x):
        ms = int(round(x * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    with open(path, 'w') as fh:
        for i, c in enumerate(CUES, 1):
            fh.write(f"{i}\n{ts(max(0, c['t']))} --> {ts(c['end'])}\n{c['plain']}\n\n")

if a.srt: write_srt(a.srt); print('srt', a.srt)
if a.preview:
    os.makedirs(a.pdir, exist_ok=True)
    for ts_ in a.preview.split(','):
        f = int(round(float(ts_) * FPS)); compose(f).convert('RGB').save(os.path.join(a.pdir, f'p_{float(ts_):06.2f}.jpg'), quality=88)
    print('previews', a.pdir); sys.exit(0)
if a.thumb:
    f = int(round(float(a.thumb) * FPS))
    src = a.thumb_frame or os.path.join(a.frames, f'f_{f:05d}.png')
    im = Image.open(src).convert('RGBA').resize((W, H), Image.LANCZOS)
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(shade)
    for y in range(int(0.42 * H)): ds.line((0, y, W, y), fill=(0, 0, 0, int(150 * (1 - y / (0.42 * H)))))
    im = Image.alpha_composite(im, shade)
    F1 = font('Poppins-Black.ttf', 120); F2 = font('Poppins-ExtraBold.ttf', 76)
    d = ImageDraw.Draw(im)
    for i, (txt, fnt, col) in enumerate([('100-TON ROCK', F1, YEL), ('NO CRANE', F1, (255, 255, 255)), ('just physics', F2, (255, 255, 255))]):
        bb = fnt.getbbox(txt); y = int(0.07 * H) + [0, int(140 * K), int(290 * K)][i]
        d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], y), txt, font=fnt, fill=col, stroke_width=int(8 * K), stroke_fill=DARK)
    im.convert('RGB').save(a.thumb_out); print('thumb', a.thumb_out); sys.exit(0)

cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
       '-i', a.audio, '-filter_complex', f'[0:v]setpts=PTS/{a.speed},fps={FPS}[v];[1:a]atempo={a.speed}[a]',
       '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-profile:v', 'high',
       '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{NF / FPS / a.speed:.3f}', '-movflags', '+faststart', a.out]
pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for f in range(NF):
    pr.stdin.write(compose(f).convert('RGB').tobytes())
    if f % 150 == 0: print('frame', f, flush=True)
pr.stdin.close(); pr.wait(); print('ENCODED', a.out, pr.returncode)
