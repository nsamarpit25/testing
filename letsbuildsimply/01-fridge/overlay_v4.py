"""overlay_v4.py <timings.json> <anchors.json> <out.ass>
Captions in the How It's Engineered style: short lines (≤4 words) that fill in word by word, the spoken word lit
amber with a small pop, part names in orange. Part labels pop in pinned to their part and only show while it is on screen."""
import json, re, sys

TIM, ANC = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
W, H, FPS = ANC['w'], ANC['h'], ANC['fps']; FR = ANC['frames']; T = ANC['T']
s = W / 540  # designed against HIE's 540x960 stage
def ts(t):
    t = max(0, t); return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'
def col(hexrgb):  # '#RRGGBB' -> ASS &HBBGGRR&
    h = hexrgb.lstrip('#'); return f'&H{h[4:6]}{h[2:4]}{h[0:2]}&'
WHITE, AMB, ORG = col('#FFFFFF'), col('#FFC34D'), col('#FF6A1F')
hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins Black,{31 * s:.0f},&H00FFFFFF,&H00FFFFFF,&H000A0B0B,&H80000000,0,0,0,0,100,100,0,0,1,{3.4 * s:.1f},{1.6 * s:.1f},5,10,10,10,1
Style: Lab,Poppins Black,{24 * s:.0f},&H004DC3FF,&H004DC3FF,&H00000000,&H78000000,0,0,0,0,100,100,1,0,1,{3.0 * s:.1f},{1.2 * s:.1f},2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
# ---------------------------------------------------------------- captions (same chunking rules as HIE overlay.js)
PART = {'evaporator', 'compressor', 'condenser', 'capillary', 'tube', 'thermostat'}
WEAK = {'a', 'an', 'the', 'are', 'on', 'in', 'it', 'and', 'at', 'is', 'of', 'to', 'for', 'with', 'by', 'its', 'has', 'that', 'so', 'but', 'or', 'if', 'your', 'you'}
words = []
for l in TIM['lines']:
    for w in l['words']:
        words.append(dict(s=w['w'], a=w['s'], b=w['e'], part=re.sub(r'[^a-z]', '', w['w'].lower()) in PART))
chunks, cur = [], []
def flush():
    global cur
    if not cur: return
    carry = []
    while len(carry) < 2 and len(cur) >= 2 and not re.search(r'[.,?:!…]$', cur[-1]['s']) and cur[-1]['s'].lower() in WEAK:
        carry.insert(0, cur.pop())
    chunks.append(cur); cur = carry
for w in words:
    if cur:
        prev = cur[-1]; ln = sum(len(x['s']) + 1 for x in cur)
        if re.search(r'[.?:!]$', prev['s']) or (prev['s'].endswith(',') and len(cur) >= 3) or len(cur) >= 4 or ln + len(w['s']) > 24 or w['a'] - prev['b'] > 0.6:
            flush()
    cur.append(w)
flush()
i = len(chunks) - 1
while i > 0:
    c, p = chunks[i], chunks[i - 1]; ln = sum(len(x['s']) + 1 for x in p + c)
    if len(c) <= 2 and len(p) + len(c) <= 5 and not re.search(r'[.?!]$', p[-1]['s']) and ln <= 30:
        p.extend(c); chunks.pop(i)
    i -= 1
CAP_Y = 0.79 * H
for ci, c in enumerate(chunks):
    t0 = c[0]['a'] - 0.04
    t1 = min(chunks[ci + 1][0]['a'] - 0.04, c[-1]['b'] + 0.9) if ci + 1 < len(chunks) else c[-1]['b'] + 0.9
    # one event per word interval: words so far visible, current word amber + pop, future words invisible (keeps the line centred)
    for k, w in enumerate(c):
        a = max(t0, w['a'] - 0.04); b = (c[k + 1]['a'] - 0.04) if k + 1 < len(c) else t1
        if b <= a: continue
        parts = []
        for j, x in enumerate(c):
            txt = re.sub(r'[.,:;]+$', '', x['s']).replace('...', '…')
            base = ORG if x['part'] else WHITE
            if j < k: parts.append(f'{{\\alpha&H00&\\c{base}\\fscy100}}{txt}')
            elif j == k: parts.append(f'{{\\alpha&H00&\\c{ORG if x["part"] else AMB}\\fscy122\\t(0,140,\\fscy106)}}{txt}')
            else: parts.append(f'{{\\alpha&HFF&}}{txt}')
        ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({W / 2:.0f},{CAP_Y:.0f})}}" + ' '.join(parts))
        # after the last word is spoken, settle it back to white/orange until the line ends
        if k == len(c) - 1 and t1 > w['b'] + 0.15:
            pass

# ---------------------------------------------------------------- part labels
def frame_at(t): return FR[min(len(FR) - 1, max(0, int(round(t * FPS))))]
def label(text, anchor, t0, dur=2.2, dy=-16):
    n = int(dur * FPS / 2)
    for k in range(n):
        a = t0 + k * 2 / FPS; b = a + 2 / FPS
        x, y, on = frame_at(a)[anchor]
        if not on: continue
        x = min(max(x, 96 * s), W - 96 * s); y = min(max(y + dy * s, 70 * s), CAP_Y - 50 * s)
        fade = r'\alpha&H00&' if k < n - 4 else r'\alpha&H%02X&' % int(255 * (k - (n - 4)) / 4)
        anim = r'\fscx40\fscy40\t(0,110,\fscx112\fscy112)\t(110,180,\fscx100\fscy100)' if k == 0 else ''
        ev.append(f"Dialogue: 3,{ts(a)},{ts(b)},Lab,,0,0,0,,{{\\pos({x:.0f},{y:.0f}){anim}{fade}}}{text}")
label('EVAPORATOR', 'evap', T['evap'])
label('COMPRESSOR', 'comp', T['comp'], dy=-30)
label('CONDENSER', 'cond', T['cond'])
label('CAPILLARY TUBE', 'capil', T['cap'])
label('THERMOSTAT', 'thermo', T['thermo'], dy=-26)
for text, anc, dy in (('EVAPORATOR', 'evap', -10), ('COMPRESSOR', 'comp', -22), ('CONDENSER', 'cond', -10),
                      ('CAPILLARY TUBE', 'capil', 30), ('THERMOSTAT', 'thermo', -18)):
    label(text, anc, T['congrats2'] - 0.2, dur=T['just'] - T['congrats2'] + 0.1, dy=dy)
open(sys.argv[3], 'w').write(hdr + '\n'.join(ev) + '\n')
print('chunks', len(chunks), 'events', len(ev))
