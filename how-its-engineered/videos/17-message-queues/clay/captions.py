# Word-group captions as transparent PNGs + an ffmpeg concat list, overlaid on the Blender render.
# usage: .venv/bin/python videos/17-message-queues/captions.py <out dir> [--res 360]
import json, re, sys, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).parent
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
RES = int(sys.argv[sys.argv.index('--res') + 1]) if '--res' in sys.argv else 360
Wd, Ht = RES, int(RES * 16 / 9) // 2 * 2
words = json.loads((D / 'voice/words.json').read_text())
timings = json.loads((D / 'voice/timings.json').read_text())
with wave.open(str(D / 'voice/voice.wav')) as wv: END = min(wv.getnframes() / wv.getframerate(), timings[-1]['end'] + 1.8)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())

# emphasised words per phrase: *word* and [pill phrase]
emph = []
for p in timings:
    toks = set()
    for m in re.findall(r'\*([^*]+)\*|\[([^\]]+)\]', p['show']):
        for w in (m[0] or m[1]).split(): toks.add(norm(w))
    emph.append((p['start'], p['end'] + 0.3, toks))
def is_emph(w, t):
    return any(a <= t <= b and norm(w) in toks for a, b, toks in emph)

# groups of up to 3 words, broken at punctuation and pauses
groups, cur = [], []
for i, (w, s, e) in enumerate(words):
    cur.append((w.strip(), s, e))
    nxt = words[i + 1][1] if i + 1 < len(words) else None
    if len(cur) == 3 or re.search(r'[.,?!:]$', w.strip()) or nxt is None or nxt - e > 0.3:
        groups.append(cur); cur = []

def font(size):
    for idx in range(12):
        try:
            f = ImageFont.truetype('/System/Library/Fonts/Avenir Next.ttc', size, index=idx)
            if f.getname()[1] in ('Bold', 'Heavy'): return f
        except Exception: break
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', size)
F = font(int(Wd * 0.072))
PAD, GAP = int(Wd * 0.018), int(Wd * 0.018)
RED = (139, 22, 38, 255)

def render(g, path):
    im = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ws = [w.strip('.,?!:') if not re.search(r'\d', w) else w.rstrip('.,?!:') for w, _, _ in g]
    widths = [d.textlength(w, font=F) for w in ws]
    total = sum(widths) + GAP * (len(ws) - 1)
    x, y = (Wd - total) / 2, Ht * 0.72
    for (w, s, e), txt, wd in zip(g, ws, widths):
        if is_emph(w, s):
            asc, desc = F.getmetrics()
            d.rounded_rectangle([x - PAD, y - PAD * 0.6, x + wd + PAD, y + asc + desc * 0.4], radius=PAD, fill=RED)
            d.text((x, y), txt, font=F, fill='white')
        else:
            d.text((x, y), txt, font=F, fill='white', stroke_width=max(2, Wd // 160), stroke_fill=(0, 0, 0, 200))
        x += wd + GAP
    im.save(path)

blank = out / 'blank.png'; Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)).save(blank)
lines, t = [], 0.0
for k, g in enumerate(groups):
    s = g[0][1]; e = groups[k + 1][0][1] if k + 1 < len(groups) else g[-1][2] + 0.4
    e = min(e, g[-1][2] + 0.6)
    if s > t: lines += [f"file '{blank}'", f'duration {s - t:.3f}']
    p = out / f'cap_{k:03d}.png'; render(g, p)
    lines += [f"file '{p}'", f'duration {e - s:.3f}']; t = e
lines += [f"file '{blank}'", f'duration {max(END - t, 0.1):.3f}', f"file '{blank}'"]
(out / 'captions.txt').write_text('\n'.join(lines) + '\n')
print(len(groups), 'caption groups')
