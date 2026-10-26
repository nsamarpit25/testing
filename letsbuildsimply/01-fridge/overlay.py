"""overlay.py <timings.json> <anchors.json> <script.json> <out.ass>
One-word captions (Poppins ExtraBold, white + black outline, key words yellow), pop-in term labels pinned to their part,
and a live temperature readout above the thermometer."""
import json, re, sys

TIM, ANC, SCR = (json.load(open(p)) for p in sys.argv[1:4])
W, H, FPS = ANC['w'], ANC['h'], ANC['fps']; FR = ANC['frames']; T = ANC['T']
s = W / 480  # scale everything from a 480-wide design

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
    return f'{h}:{m:02d}:{sec:05.2f}'
hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins ExtraBold,{42 * s:.0f},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,{4.2 * s:.1f},{1.6 * s:.1f},5,10,10,10,1
Style: Lab,Poppins Black,{27 * s:.0f},&H0030D8FF,&H0030D8FF,&H00000000,&H78000000,0,0,0,0,100,100,1,0,1,{3.4 * s:.1f},{1.4 * s:.1f},2,10,10,10,1
Style: Tmp,Poppins ExtraBold,{23 * s:.0f},&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,0,0,0,0,100,100,0,0,1,{3.0 * s:.1f},{1.0 * s:.1f},2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
KEY = {'evaporator', 'compressor', 'condenser', 'capillary', 'tube', 'thermostat', 'fridge', 'twist', 'freezing', 'cold', 'warm', 'hot',
       'heat', 'spaghetti', 'below', 'solid', 'ice', 'cheese'}
CAP_Y = 0.655 * H
words = [w for l in TIM['lines'] for w in l['words']]
for i, w in enumerate(words):
    txt = re.sub(r"[^\w'’\-]", '', w['w'])
    if not txt: continue
    txt = txt[0].upper() + txt[1:]
    nxt = words[i + 1]['s'] if i + 1 < len(words) else w['e'] + 0.5
    end = min(nxt, w['e'] + 0.45) if nxt - w['e'] < 0.6 else w['e'] + 0.3
    col = r'{\c&H0030D8FF&}' if re.sub(r'\W', '', w['w']).lower() in KEY else ''
    pop = r'{\fscx72\fscy72\t(0,90,\fscx106\fscy106)\t(90,150,\fscx100\fscy100)}'
    ev.append(f"Dialogue: 2,{ts(w['s'])},{ts(end)},Cap,,0,0,0,,{{\\pos({W / 2:.0f},{CAP_Y:.0f})}}{pop}{col}{txt}")

def frame_at(t): return FR[min(len(FR) - 1, max(0, int(round(t * FPS))))]
def label(text, anchor, t0, dur=2.3, dy=-14):
    # a label follows its anchor (camera can move); one event per 2 frames, pop-in on the first
    n = int(dur * FPS / 2)
    for k in range(n):
        a = t0 + k * 2 / FPS; b = a + 2 / FPS
        x, y = frame_at(a)[anchor]
        x = min(max(x, 92 * s), W - 92 * s); y = min(max(y + dy * s, 60 * s), H - 30 * s)
        fade = r'\alpha&H00&' if k < n - 4 else r'\alpha&H%02X&' % int(255 * (k - (n - 4)) / 4)
        anim = r'\fscx40\fscy40\t(0,110,\fscx112\fscy112)\t(110,180,\fscx100\fscy100)' if k == 0 else ''
        dur_ev = (180 / 1000) if k == 0 else 2 / FPS
        ev.append(f"Dialogue: 3,{ts(a)},{ts(a + max(dur_ev, 2 / FPS) if k == 0 else b)},Lab,,0,0,0,,{{\\pos({x:.0f},{y:.0f}){anim}{fade}}}{text}")
label('EVAPORATOR', 'evap', T['evap'])
label('COMPRESSOR', 'comp', T['comp'], dy=-26)
label('CONDENSER', 'cond', T['cond'])
label('CAPILLARY TUBE', 'capil', T['cap'])
label('THERMOSTAT', 'thermo', T['thermo'], dy=-22)
# final hero: all five labels together for the save-worthy freeze
for text, anc, dy in (('EVAPORATOR', 'evap', -10), ('COMPRESSOR', 'comp', -22), ('CONDENSER', 'cond', -10), ('THERMOSTAT', 'thermo', -18)):
    label(text, anc, T['congrats'] + 0.2, dur=T['could'] - T['congrats'] - 0.1, dy=dy)

# temperature readout (°C) above the thermometer, shown from the start until the wrap
last = None; start = 0.0
show_until = FR[-1]['t']
for i, r in enumerate(FR):
    if r['t'] > show_until: break
    val = round(r['temp']); x, y = r['therm']
    key = (val, round(x / 2), round(y / 2))
    if key != last:
        if last is not None:
            ev.append(f"Dialogue: 1,{ts(start)},{ts(r['t'])},Tmp,,0,0,0,,{{\\pos({px:.0f},{py:.0f})}}{lv}°C")
        last = key; start = r['t']; px, py, lv = min(max(x, 34 * s), W - 34 * s), y - 4 * s, val
ev.append(f"Dialogue: 1,{ts(start)},{ts(show_until)},Tmp,,0,0,0,,{{\\pos({px:.0f},{py:.0f})}}{lv}°C")
open(sys.argv[4], 'w').write(hdr + '\n'.join(ev) + '\n')
print('events', len(ev))
