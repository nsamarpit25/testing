#!/usr/bin/env python3
"""Schedule one finished trial variant and reconcile its registry row after posting.
usage: python3 -I tools/remake/bin/schedule_variant.py DIR 'YYYY-MM-DD HH:MM'
"""
import datetime, hashlib, json, os, pathlib, re, subprocess, sys

hie = pathlib.Path(__file__).resolve().parents[3]
d, when = sys.argv[1:]
if not re.fullmatch(r'[a-zA-Z0-9_-]+-t\d+', d):
    sys.exit('Expected a variant directory ending -tN')
zone = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
slot = datetime.datetime.strptime(when, '%Y-%m-%d %H:%M').replace(tzinfo=zone)
if slot <= datetime.datetime.now(zone):
    sys.exit('Requested slot has already passed')
p = hie / 'media' / d
for name in [d + '.mp4', 'cover.png', 'caption.txt', 'variant.txt', 'approved.md5']:
    if not (p / name).is_file(): sys.exit('Missing media file: ' + name)
md5 = hashlib.md5((p / (d + '.mp4')).read_bytes()).hexdigest()
if md5 != (p / 'approved.md5').read_text().strip():
    sys.exit('Video differs from approved.md5')
jobfile = p / 'post-job.json'
if jobfile.exists():
    job = json.loads(jobfile.read_text())
    try: os.kill(job['pid'], 0)
    except ProcessLookupError: pass
    else: sys.exit('Posting job already active: ' + str(job['pid']))
regfile = hie.parent / 'insights/hie-reels.json'
reg = json.loads(regfile.read_text())
row = next((x for x in reg['reels'] if x.get('dir') == d), None)
if row and row.get('code'): sys.exit('Variant already registered as published: ' + row['code'])
if row is None:
    row = {}; reg['reels'].append(row)
topic, note = (p / 'variant.txt').read_text().strip().split('\n', 1)
row.update(code='', topic=topic, kind='variant', dir=d, scheduled=when,
           note=note + ' md5 ' + md5 + '.')
regfile.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + '\n')
log = hie / 'tools/remake/out' / ('post_' + d + '.log')
with log.open('ab', buffering=0) as f:
    job = subprocess.Popen(['zsh', '-c',
        'zsh tools/remake/bin/post_at.sh "$1" "$2" trial; python3 -I tools/remake/bin/log_variants.py tools/remake/out',
        '--', d, when], cwd=hie, stdout=f, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, start_new_session=True)
jobfile.write_text(json.dumps({'pid':job.pid, 'scheduled':when, 'mode':'trial', 'md5':md5, 'log':str(log)}, indent=2)+'\n')
print(f'Scheduled {d} as trial at {when} IST; PID {job.pid}')
