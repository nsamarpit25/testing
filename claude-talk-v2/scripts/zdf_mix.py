# Captions and sound for the Zack D.-style test (light work, runs on the Mac).
#   subs.ass: 1-3 word white captions at ~78% height, swapped on the words; green glowing keyword pops
#   mix.wav:  the narrator, a soft synth pluck bed under it, typing while she types, whooshes on the time lapse, a ding
# usage: python3 scripts/zdf_mix.py <ep>
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ep = sys.argv[1]
d = HERE / 'audio' / ep
lines = json.load(open(d / 'lines.json'))
END = 10.0
POPS = [(0.35, 1.95, '20 MIN'), (4.00, 7.00, '1 YEAR')]   # green keyword cards (seconds)
WHOOSH = [4.70, 5.53, 6.37]                                # the three season dissolves
DING = 7.20                                                # the store page


def ts(t):
    cs = int(round(t * 100))
    return f'{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}'


ass = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1080', 'PlayResY: 1920', 'WrapStyle: 2', '',
       '[V4+ Styles]',
       'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, '
       'StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
       'Style: Cap,Arial,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,0,5,5,60,60,0,1',
       'Style: Pop,Arial,150,&H007AE03F,&H007AE03F,&H007AE03F,&H00000000,1,0,0,0,100,100,2,0,1,6,0,5,60,60,0,1',
       '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
for L in lines:  # each line's caption chunks share its spoken span by letter count
    n = sum(len(c) for c in L['caps'])
    t = L['start']
    for i, c in enumerate(L['caps']):
        t1 = L['end'] if i == len(L['caps']) - 1 else t + (L['end'] - L['start']) * len(c) / n
        nxt = lines[lines.index(L) + 1]['start'] if L is not lines[-1] else END
        hold = min(nxt, t1 + 0.35) if i == len(L['caps']) - 1 else t1
        ass.append(f'Dialogue: 1,{ts(t)},{ts(hold)},Cap,,0,0,0,,{{\\pos(540,1500)\\blur1.5}}{c}')
        t = t1
for t0, t1, txt in POPS:  # glow: a blurred green copy underneath, a crisp one on top, both popping 140% -> 100%
    pop = '\\fscx140\\fscy140\\t(0,160,\\fscx100\\fscy100)\\fad(60,120)'
    ass.append(f'Dialogue: 0,{ts(t0)},{ts(t1)},Pop,,0,0,0,,{{\\pos(540,560){pop}\\bord14\\blur16\\alpha&H40&}}{txt}')
    ass.append(f'Dialogue: 1,{ts(t0)},{ts(t1)},Pop,,0,0,0,,{{\\pos(540,560){pop}\\bord3\\blur2\\3c&H5AC02A&\\1c&HB4FFCF&}}{txt}')
(d / 'subs.ass').write_text('\n'.join(ass) + '\n')

# a soft pluck bed: C-major-7 arpeggio, eighth notes at 96 bpm, each note decaying, with a quiet sub pad
NOTES = [261.63, 329.63, 392.00, 493.88, 392.00, 329.63, 293.66, 392.00]
step = 60 / 96 / 2
expr = '+'.join(f'(between(mod(t,{step * len(NOTES):.4f}),{i * step:.4f},{(i + 1) * step:.4f})*'
                f'sin(2*PI*{f}*t)*exp(-6*(mod(t,{step * len(NOTES):.4f})-{i * step:.4f})))' for i, f in enumerate(NOTES))
expr = f'0.30*({expr})+0.08*sin(2*PI*130.81*t)+0.05*sin(2*PI*196*t)'
expr = expr.replace(',', '\\,')  # commas inside the expression would split the filter's options
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', f'aevalsrc={expr}:s=48000:d={END}',
                '-af', f'lowpass=f=2400,aecho=0.6:0.5:180:0.25,afade=t=in:d=0.4,afade=t=out:st={END - 0.8}:d=0.8,volume=0.35',
                '-ac', '2', str(d / 'bed.wav')], check=True)

type_wav = HERE / 'audio/ep21/sfx_00_type.wav'
whoosh = HERE / 'audio/ep3b/sfx_02_whoosh.wav'
ding = HERE / 'audio/ep16/sfx_01_ding.wav'
ins = [d / 'voice.wav', d / 'bed.wav', type_wav, type_wav, type_wav] + [whoosh] * len(WHOOSH) + [ding]
starts = [0, 0, 0.1, 1.5, 2.9] + WHOOSH + [DING]
vols = [1.0, 2.0, 0.30, 0.30, 0.35] + [0.35] * len(WHOOSH) + [0.45]
cmd = ['ffmpeg', '-loglevel', 'error', '-y']
for p in ins:
    cmd += ['-i', str(p)]
fl = ''.join(f'[{k}]aformat=channel_layouts=stereo:sample_rates=48000,volume={v},adelay={int(s * 1000)}:all=1[a{k}];'
             for k, (s, v) in enumerate(zip(starts, vols)))
fl += ''.join(f'[a{k}]' for k in range(len(ins))) + f'amix=inputs={len(ins)}:normalize=0:duration=first,atrim=0:{END},alimiter=limit=0.89[o]'
subprocess.run(cmd + ['-filter_complex', fl, '-map', '[o]', '-ar', '48000', str(d / 'mix.wav')], check=True)
print('wrote', d / 'subs.ass', d / 'mix.wav')
