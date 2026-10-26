#!/usr/bin/env python3
"""Add a registry row (insights/hie-reels.json, kind "variant") for every trial variant whose post log says "published:".

usage: python3 -I tools/remake/bin/log_variants.py <logdir> [--wait N]   # N = how many posts to wait for, polling every 60 s
  Logs are the post_at.sh outputs (post_<dir>.log or any *.output). The tweak note comes from media/<dir>/variant.txt.
"""
import glob, json, os, re, sys, time

HIE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REG = os.path.join(HIE, '..', 'insights', 'hie-reels.json')


def scan(logdir):
    found = {}
    for f in glob.glob(os.path.join(logdir, '*.log')) + glob.glob(os.path.join(logdir, '*.output')):
        t = open(f, errors='ignore').read()
        d, c = re.search(r'posting (\S+-t\d+) \(trial\) at (\S+ \S+)', t), re.search(r'published: https://www.instagram.com/reel/([\w-]+)/', t)
        if d and c: found[d.group(1)] = (c.group(1), d.group(2))
    return found


def log(found):
    reg = json.load(open(REG))
    have = {r.get('code') for r in reg['reels']}
    added = 0
    for d, (code, when) in found.items():
        if code in have: continue
        vt = os.path.join(HIE, 'media', d, 'variant.txt')
        topic, note = (open(vt).read().strip().split('\n', 1) + [''])[:2] if os.path.exists(vt) else (d, '')
        md5 = open(os.path.join(HIE, 'media', d, 'approved.md5')).read().strip()
        row = next((r for r in reg['reels'] if r.get('dir') == d), None)
        if row is None:
            row = {}
            reg['reels'].append(row)
        row.update({'code': code, 'topic': topic, 'kind': 'variant', 'dir': d,
                    'note': f"Trial variant, auto trial scheduled {when} IST. {note} md5 {md5}."})
        row.pop('scheduled', None)
        have.add(code)
        added += 1
    if added:
        tmp = REG + '.tmp'; json.dump(reg, open(tmp, 'w'), indent=1, ensure_ascii=False); os.replace(tmp, REG)
    return added


logdir = sys.argv[1]
want = int(sys.argv[sys.argv.index('--wait') + 1]) if '--wait' in sys.argv else 0
while True:
    f = scan(logdir); n = log(f)
    if n: print(time.strftime('%H:%M'), f'logged {n}, {len(f)} published so far', flush=True)
    if len(f) >= want: break
    time.sleep(60)
print('published:', ' '.join(f'{d}={c}' for d, (c, _) in sorted(f.items(), key=lambda x: x[1][1])))
