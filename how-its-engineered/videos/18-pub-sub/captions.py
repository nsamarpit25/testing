# Captions in the house style of the HTML reels (16-retries): Inter ExtraBold, white with a dark outline and soft shadow,
# key words coloured, words popping in one by one as they're spoken. Text comes from script.json "show" (timing from Whisper).
# Writes one transparent PNG per caption state + an ffmpeg concat list, overlaid on the Blender render.
# usage: .venv/bin/python videos/17-message-queues/mailroom/captions.py <out dir> [--res 480]
import json, re, sys, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = Path(__file__).parent
ROOT = D.parents[1]
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
RES = int(sys.argv[sys.argv.index('--res') + 1]) if '--res' in sys.argv else 480
Wd, Ht = RES, int(RES * 16 / 9) // 2 * 2
k = Wd / 540  # the HTML reels are laid out on a 540 x 960 stage
words = json.loads((D / 'voice/words.json').read_text())
timings = json.loads((D / 'voice/timings.json').read_text())
with wave.open(str(D / 'voice/voice.wav')) as wv: END = min(wv.getnframes() / wv.getframerate(), timings[-1]['end'] + 1.8)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())

# display words from the script's "show" text, with *word* / [phrase] marking key words
shown = []
for p in timings:
    for m in re.finditer(r'\*([^*]+)\*|\[([^\]]+)\]|(\S+)', p['show']):
        key = m.group(3) is None
        for w in (m.group(1) or m.group(2) or m.group(3)).split(): shown.append((w, key))
# match script words to whisper words; a hyphenated script word may be two whisper words ("mid-order" = "mid" "order")
pairs, j = [], 0
for w, key in shown:
    if j >= len(words): break
    s_, e_ = words[j][1], words[j][2]
    if norm(w) != norm(words[j][0]) and j + 1 < len(words) and norm(w) == norm(words[j][0] + words[j + 1][0]):
        e_ = words[j + 1][2]; j += 1
    pairs.append(((w, key), (w, s_, e_))); j += 1
shown, words = [p_[0] for p_ in pairs], [p_[1] for p_ in pairs]
HL = {'red': '#FF4757', 'cyan': '#38B6FF', 'green': '#2ECC71', 'amber': '#FFC34D', 'orange': '#FF6A1F'}
CAT = {**dict.fromkeys('slow waits rewriting problem itself again keeps spinning'.split(), 'red'),
       **dict.fromkeys('pubsub topic publishes publish subscribes subscribe own copy radio station broadcasts once hears it google cloud amazon sns message queues'.split(), 'cyan'),
       **dict.fromkeys('stops never changes everyone notified'.split(), 'green'),
       **dict.fromkeys('vibe coder ai skipped follow'.split(), 'orange')}
ws = [dict(s=w, a=s, b=e, col=(HL[CAT.get(norm(w), 'amber')] if key else None)) for (w, key), (_, s, e) in zip(shown, words)]
for i, w in enumerate(ws):
    if norm(w['s']) == 'follow': w['col'] = HL['orange']
    if norm(w['s']) == 'rewriting':
        for x in ws[i:i + 4]: x['col'] = HL['red']
    if norm(w['s']) == 'stops':
        for x in ws[i:i + 2]: x['col'] = HL['green']

# short chunks (<=4 words, <=24 chars), break at sentence ends and pauses, weak trailing words carried forward
WEAK = set('a an the are on in it and at is of to for with by its has that so but you your if or'.split())
chunks, cur = [], []
def flush():
    global cur
    if not cur: return
    carry = []
    while len(carry) < 2 and len(cur) >= 2 and not re.search(r'[.,?:!]$', cur[-1]['s']) and cur[-1]['s'].lower() in WEAK: carry.insert(0, cur.pop())
    chunks.append(cur); cur = carry
for w in ws:
    prev = cur[-1] if cur else None
    ln = sum(len(x['s']) + 1 for x in cur)
    if prev and (re.search(r'[.?:!]$', prev['s']) or (prev['s'].endswith(',') and len(cur) >= 2) or len(cur) >= 4 or ln + len(w['s']) > 26 or w['a'] - prev['b'] > 0.6): flush()
    cur.append(w)
flush()
# no orphans: a lone sentence-ending word borrows the previous chunk's last word
for i in range(1, len(chunks)):
    p_, c_ = chunks[i - 1], chunks[i]
    if len(c_) == 1 and len(p_) >= 3 and not re.search(r'[.,?:!]$', p_[-1]['s']): c_.insert(0, p_.pop())

fp = str(ROOT / 'node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2')
F = ImageFont.truetype(fp, round(23 * k)); F.set_variation_by_axes([800])
GAP, STROKE, CY = 8 * k, max(2, round(2 * k)), 822 * k * (Ht / Wd) / (960 / 540)

def render(chunk, n, path):
    """chunk with its first n words visible; layout always uses the whole chunk so words don't shift."""
    txt = [re.sub(r'[.,:;]+$', '', w['s']) for w in chunk]
    wid = [F.getlength(t) for t in txt]
    x0 = (Wd - sum(wid) - GAP * (len(txt) - 1)) / 2
    asc, desc = F.getmetrics(); y = CY - (asc + desc) / 2
    shadow = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    im = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = x0
    for i, (w, t, wd) in enumerate(zip(chunk, txt, wid)):
        if i < n:
            sd.text((x, y + 2 * k), t, font=F, fill=(0, 0, 0, 205), stroke_width=STROKE, stroke_fill=(0, 0, 0, 205))
            d.text((x, y), t, font=F, fill=w['col'] or '#FFFFFF', stroke_width=STROKE, stroke_fill='#0B0A09')
        x += wd + GAP
    Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5 * k)), im).save(path)

blank = out / 'blank.png'; Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)).save(blank)
states = []  # (start, image)
for ci, c in enumerate(chunks):
    t1 = min(chunks[ci + 1][0]['a'] - 0.04, c[-1]['b'] + 0.9) if ci + 1 < len(chunks) else END
    for i, w in enumerate(c):
        p = out / f'cap_{ci:03d}_{i}.png'; render(c, i + 1, p); states.append((w['a'] - 0.04, p))
    states.append((t1, blank))
lines, t = [], 0.0
if states[0][0] > 0: states.insert(0, (0.0, blank))
for (s, p), nxt in zip(states, states[1:] + [(END, None)]):
    s = max(s, t); e = max(nxt[0], s + 0.001)
    lines += [f"file '{p}'", f'duration {e - s:.3f}']; t = e
lines.append(f"file '{states[-1][1]}'")
(out / 'captions.txt').write_text('\n'.join(lines) + '\n')
print(len(chunks), 'chunks,', len(states), 'states')
if '--json' in sys.argv:  # chunks for the live Three.js page
    cj = []
    for ci, c in enumerate(chunks):
        t1 = min(chunks[ci + 1][0]['a'] - 0.04, c[-1]['b'] + 0.9) if ci + 1 < len(chunks) else END
        cj.append({'t1': t1, 'w': [{'s': re.sub(r'[.,:;]+$', '', w['s']), 'a': w['a'], 'col': w['col']} for w in c]})
    Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(cj))
if '--show' in sys.argv: print(' | '.join(' '.join(w['s'] for w in c) for c in chunks))
