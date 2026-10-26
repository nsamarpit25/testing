"""align.py <script.json> <words.json> <out.json>: put whisper word times onto the script's own words (difflib on normalised tokens)."""
import json, re, sys, difflib
lines = json.load(open(sys.argv[1]))['lines']; W = json.load(open(sys.argv[2]))
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower().replace('26', 'twentysix'))
sw = [(li, w) for li, l in enumerate(lines) for w in l.split()]
a = [norm(w) for _, w in sw]; b = [norm(x['w']) for x in W]
# glue "twenty six" so it lines up with whisper's "26"
a = ['twentysix' if x == 'twenty' and i + 1 < len(a) and a[i + 1] == 'six' else ('' if x == 'six' and i and a[i - 1] == 'twenty' else x) for i, x in enumerate(a)]
t = [None] * len(sw)
for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
    for k in range(blk.size): t[blk.a + k] = (W[blk.b + k]['s'], W[blk.b + k]['e'])
for i in range(len(t)):  # fill gaps between neighbours
    if t[i] is None:
        p = next((t[j][1] for j in range(i - 1, -1, -1) if t[j]), 0.0); n = next((t[j][0] for j in range(i + 1, len(t)) if t[j]), p + 0.3)
        t[i] = (p, max(p + 0.05, (p + n) / 2))
out = []
for li, l in enumerate(lines):
    ws = [dict(w=w, s=t[i][0], e=t[i][1]) for i, (lj, w) in enumerate(sw) if lj == li]
    out.append(dict(text=l, s=ws[0]['s'], e=ws[-1]['e'], words=ws))
miss = sum(1 for i, x in enumerate(a) if x and not any(True for _ in [0]) )
json.dump(dict(lines=out, dur=W[-1]['e'] + 0.6), open(sys.argv[3], 'w'), indent=0)
for l in out: print(f"{l['s']:6.2f}-{l['e']:6.2f} {l['text'][:60]}")
