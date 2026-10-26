#!/usr/bin/env python3
"""HIE reel tracker: every reel with its version, live/trial/deleted status, views, growth and a note.

usage (from how-its-engineered/, after `set -a; source ../.env; set +a; source ~/.instagram_tokens`):
  python3 -I tools/remake/bin/tracker.py            # fetch, snapshot, write ../insights/hie-reels.html
Registry: ../insights/hie-reels.json (topic, kind, notes, deleted/scheduled rows). Snapshots: ../insights/hie-tracker-snapshots.jsonl.
Scheduled rows are matched to their post by the first line of media/<dir>/caption.txt once they go up.
"""
import html, json, os, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
HERE = os.path.dirname(os.path.abspath(__file__))
HIE = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
INS = os.path.join(HIE, '..', 'insights')
REG, SNAP, OUT, HIST = (os.path.join(INS, f) for f in ('hie-reels.json', 'hie-tracker-snapshots.jsonl', 'hie-reels.html', 'history.jsonl'))
KIND = {'original': 'Original', 'v2': 'Remake v2', 'B': 'Remake B', 'new': 'New topic', 'new-B': 'New topic B', 'copy': 'Extra copy', 'variant': 'Trial variant'}


def graph(path, **p):
    p['access_token'] = os.environ['IG_HOWITSENGINEERED_TOKEN']
    err = None
    for host in ('graph.instagram.com', 'graph.facebook.com'):
        try:
            return json.load(urllib.request.urlopen(f'https://{host}/v21.0/{path}?' + urllib.parse.urlencode(p), timeout=30))
        except Exception as e:  # never print the URL: it carries the token
            err = type(e).__name__
    sys.exit('graph request failed: ' + err)


def fetch():
    uid = os.environ['IG_HOWITSENGINEERED_ID']
    me = graph(uid, fields='followers_count,media_count')
    media = graph(f'{uid}/media', fields='id,timestamp,permalink,caption,is_shared_to_feed', limit=100)['data']
    out = subprocess.run([sys.executable, '-I', os.path.join(HIE, 'tools', 'ig.py'), 'stats', '--n', '100', '--json'], capture_output=True, text=True, cwd=HIE).stdout
    stats = {r['url'].split('/')[-2]: r for r in json.loads(out[out.index('['):])}
    rows = {}
    for m in media:
        c = m['permalink'].rstrip('/').split('/')[-1]
        s = stats.get(c, {})
        rows[c] = {'code': c, 'url': m['permalink'], 'posted': datetime.strptime(m['timestamp'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc),
                   'caption': (m.get('caption') or '').split('\n')[0], 'live': bool(m.get('is_shared_to_feed')),
                   'views': s.get('views', 0), 'likes': s.get('likes', 0), 'shares': s.get('shares', 0), 'saved': s.get('saved', 0)}
    return me, rows


def prior(now):
    """latest earlier view count per shortcode, at least 25 minutes old: tracker snapshots first, then insights history"""
    best = {}
    def add(c, t, v):
        if now - t >= timedelta(minutes=25) and (c not in best or t > best[c][0]): best[c] = (t, v)
    for f, tk in ((SNAP, 't'), (HIST, 't')):
        if not os.path.exists(f): continue
        for ln in open(f):
            try:
                r = json.loads(ln); c = r.get('code') or r.get('permalink', '').rstrip('/').split('/')[-1]
                add(c, datetime.fromisoformat(r[tk]), r['views'])
            except Exception: pass
    return best


def main():
    now = datetime.now(IST)
    reg = json.load(open(REG))
    me, rows = fetch()
    with open(SNAP, 'a') as f:
        for c, r in rows.items(): f.write(json.dumps({'t': now.isoformat(timespec='seconds'), 'code': c, 'views': r['views']}) + '\n')
    pv = prior(now)
    # match scheduled rows to their post by caption
    for e in reg['reels']:
        if not e['code'] and e.get('dir'):
            cap = os.path.join(HIE, 'media', e['dir'], 'caption.txt')
            first = open(cap).read().split('\n')[0][:40] if os.path.exists(cap) else None
            for c, r in rows.items():
                if first and r['caption'].startswith(first): e['code'] = c; e.pop('scheduled', None)
    known = {e['code'] for e in reg['reels'] if e['code']}
    for c, r in rows.items():
        if c not in known: reg['reels'].append({'code': c, 'topic': '(not in registry)', 'kind': 'new', 'note': r['caption'][:60]})
    items = []
    for e in reg['reels']:
        r = rows.get(e['code'])
        it = dict(e, url=f"https://www.instagram.com/reel/{e['code']}/" if e['code'] else '', views=e.get('views', 0), rate=None, age=None, trend='')
        if e.get('scheduled'): it['status'] = 'scheduled'
        elif r is None: it['status'] = 'deleted'
        else:
            it.update(status='live' if r['live'] else 'trial', views=r['views'], shares=r['shares'], saved=r['saved'])
            it['age'] = (now - r['posted']).total_seconds() / 3600
            if e['code'] in pv:
                t0, v0 = pv[e['code']]; h = (now - t0).total_seconds() / 3600
                it['rate'] = (r['views'] - v0) / h if h > 0 else None
            rate = it['rate']
            it['trend'] = 'new' if it['age'] < 3 else 'growing' if rate is None or rate >= 60 else 'slowing' if rate >= 15 else 'stalled'
        items.append(it)
    # per-topic verdicts and actions
    topics = {}
    for it in items: topics.setdefault(it['topic'], []).append(it)
    todo = []
    for tp, group in topics.items():
        up = [i for i in group if i['status'] in ('live', 'trial')]
        live = [i for i in up if i['status'] == 'live']; trial = [i for i in up if i['status'] == 'trial']
        lb = max(live, key=lambda i: i['views'], default=None); bt = max(trial, key=lambda i: i['views'], default=None)
        for i in up: i['action'] = ''
        if bt:
            chasing = [i for i in trial if i is not bt and i['trend'] in ('growing', 'new') and i['views'] >= 0.7 * bt['views']]
            if lb and bt['views'] > lb['views']:
                bt['action'] = 'make live'; todo.append(('live', bt, f"beats the live {KIND[lb['kind']].lower()}"))
                for i in live:
                    if i['views'] < bt['views']: i['action'] = 'delete'; todo.append(('delete', i, f"{KIND[bt['kind']]} has more views"))
            elif not lb:
                if chasing: bt['action'] = 'wait'; bt['why'] = f"{KIND[chasing[0]['kind']]} is catching up"
                elif bt['age'] >= 3 and bt['trend'] in ('slowing', 'stalled'): bt['action'] = 'make live'; todo.append(('live', bt, 'trial views have levelled off, and nothing on the grid covers this topic'))
                elif bt['views'] >= 1200 and len(trial) > 1: bt['action'] = 'make live'; todo.append(('live', bt, 'past the trial ceiling and leading its topic, which has nothing on the grid'))
                else: bt['action'] = 'wait'; bt['why'] = 'still growing in trial'
            for i in trial:
                if i is bt: continue
                if i['trend'] == 'stalled' and i['age'] >= 3: i['action'] = 'delete'; todo.append(('delete', i, f"stalled, {KIND[bt['kind']]} ahead"))
                elif not i['action']: i['action'] = 'wait'; i.setdefault('why', f"{KIND[bt['kind']]} ahead, still moving")
        for i in group:
            if i['status'] in ('live', 'trial') and not i.get('note'):
                if i['kind'] == 'original' and bt and i['status'] == 'live' and i['views'] >= bt['views']: i['note'] = 'Original still ahead of every remake.'
    write(me, items, topics, todo, now)


SHORT = {'original': 'Orig', 'v2': 'v2', 'B': 'B', 'new': 'New', 'new-B': 'New B', 'copy': 'Copy'}
TREND = {'growing': ('▲', 'Growing'), 'slowing': ('▸', 'Slowing'), 'stalled': ('■', 'Stalled'), 'new': ('●', 'Too new'), '': ('', '')}
RANK = {'act': 0, 'wait': 1, 'sched': 2, 'ok': 3}


def verdict(group):
    acts = [i for i in group if i.get('action') in ('delete', 'make live')]
    if acts: return 'act', ' · '.join(f"{'Delete' if i['action'] == 'delete' else 'Make live'} {SHORT[i['kind']]}" for i in acts)
    waits = [i for i in group if i.get('action') == 'wait']
    if waits: return 'wait', 'Wait' + (f": {waits[0]['why']}" if waits[0].get('why') else '')
    if any(i['status'] == 'scheduled' for i in group) and not any(i['status'] in ('live', 'trial') for i in group): return 'sched', 'Scheduled' if any(i.get('scheduled', '')[:1].isdigit() for i in group) else 'Awaiting OK'
    return 'ok', 'OK'


def chip(i):
    e = html.escape
    st = i['status']; ar, tw = TREND[i['trend']]
    rate = '' if i['rate'] is None or st not in ('live', 'trial') else f"{i['rate']:+.0f}/h"
    sc = i.get('scheduled', '')
    val = (f"posts {sc[11:]}" if sc[:1].isdigit() else sc) if st == 'scheduled' else f"{i['views']:,}"
    tr = f'<span class="tr tr-{i["trend"]}" title="{tw}">{ar} {rate or tw}</span>' if st in ('live', 'trial') else ''
    act = ''
    if i.get('action') in ('delete', 'make live'):
        act = f'<span class="flag flag-{i["action"].split()[0]}">{i["action"]}</span>'
    tag = 'a' if i['url'] and st != 'deleted' else 'span'
    href = f' href="{e(i["url"])}"' if tag == 'a' else ''
    tip = e(' · '.join(x for x in [i.get('note', ''), i.get('why', '')] if x))
    return (f'<{tag} class="chip c-{st}"{href} title="{tip}"><span class="dot"></span>'
            f'<span class="k">{e(SHORT[i["kind"]])}</span><span class="v">{val}</span>{tr}{act}</{tag}>')


def write(me, items, topics, todo, now):
    e = html.escape
    counts = {s: sum(1 for i in items if i['status'] == s) for s in ('live', 'trial', 'deleted', 'scheduled')}
    slot = now + timedelta(minutes=5); todo_html = ''                                  # make-lives spaced 35 min apart
    for kind, it, why in sorted(todo, key=lambda t: t[0] != 'delete'):
        when = ''
        if kind == 'live': when = f'<span class="when">{slot.strftime("%H:%M")}</span>'; slot += timedelta(minutes=35)
        verb, cls = ('Make live', 'live') if kind == 'live' else ('Delete', 'del')
        todo_html += (f'<li><a class="do do-{cls}" href="{e(it["url"])}">{verb}</a>'
                      f'<span class="do-what"><b>{e(it["topic"])} · {e(SHORT[it["kind"]])}</b> <span class="num">{it["views"]:,}</span><small>{e(why)}</small></span>{when}</li>')
    if not todo_html: todo_html = '<li class="none">Nothing to delete or make live right now.</li>'
    rows = []
    for tp, group in topics.items():
        vk, vt = verdict(group)
        best = max((i['views'] for i in group if i['status'] != 'deleted'), default=0)
        rows.append((RANK[vk], -best, tp, vk, vt, group))
    rows.sort(key=lambda r: r[:3])
    body = ''
    for _, _, tp, vk, vt, group in rows:
        order = sorted(group, key=lambda i: ({'live': 0, 'trial': 1, 'scheduled': 2, 'deleted': 3}[i['status']], -i['views']))
        notes = [f"{SHORT[i['kind']]}: {i['note']}" for i in order if i.get('note') and i['status'] != 'deleted']
        sts = ' '.join(sorted({i['status'] for i in group}))
        body += (f'<article class="topic v-{vk}" data-v="{vk}" data-st="{sts}"><div class="th"><h2>{e(tp)}</h2><span class="verdict">{e(vt)}</span></div>'
                 f'<div class="chips">{"".join(chip(i) for i in order)}</div>' + (f'<p class="note">{e(" · ".join(notes))}</p>' if notes else '') + '</article>')
    fill = {'FETCHED': now.strftime('%d %b, %H:%M IST'), 'FOLLOWERS': f"{me.get('followers_count', 0):,}", 'GRID': str(me.get('media_count', 0)),
            'LIVE': str(counts['live']), 'TRIAL': str(counts['trial']), 'DELETED': str(counts['deleted']), 'SCHED': str(counts['scheduled']),
            'NACT': str(sum(1 for r in rows if r[3] == 'act')), 'TOPICS': str(len(rows)), 'TODO': todo_html, 'GROUPS': body}
    page = TEMPLATE
    for k, v in fill.items(): page = page.replace('{{' + k + '}}', v)
    open(OUT, 'w').write(page)
    print(OUT)


TEMPLATE = r'''<title>HIE Reel Tracker</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap">
<style>
/* layout: slim header, a to-do strip, then one compact card per topic in an auto grid (2-3 columns on desktop, 1 on phones); each version is a chip */
:root {
  --bg: #f4f1ed; --panel: #fffdfa; --fg: #201b17; --muted: #776b62; --line: #e2d9cf;
  --ember: #cf5318; --live: #1b8547; --trial: #3866b0; --warn: #9c6100; --bad: #c23a2b; --on: #ffffff;
  --display: 'Instrument Serif', Georgia, serif; --body: 'Inter', system-ui, -apple-system, sans-serif; --mono: 'JetBrains Mono', ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #110e0c; --panel: #1a1512; --fg: #efe7df; --muted: #9a8d82; --line: #2e2621;
  --ember: #ff7a33; --live: #63dc91; --trial: #7fa9f0; --warn: #f2bf4c; --bad: #ff6a5a; --on: #110e0c; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #110e0c; --panel: #1a1512; --fg: #efe7df; --muted: #9a8d82; --line: #2e2621;
  --ember: #ff7a33; --live: #63dc91; --trial: #7fa9f0; --warn: #f2bf4c; --bad: #ff6a5a; --on: #110e0c; color-scheme: dark }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--fg); font: 14px/1.45 var(--body); }
.wrap { max-width: 1320px; margin: 0 auto; padding-block: 18px 40px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 14px; }
header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; }
h1 { font: 400 30px/1 var(--display); margin: 0; }
.handle { font: 700 11px var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ember); }
.fetched { color: var(--muted); font: 500 12px var(--mono); }
.kpis { display: flex; flex-wrap: wrap; gap: 6px; }
.kpi { font: 500 12px var(--mono); color: var(--muted); background: var(--panel); border: 1px solid var(--line); border-radius: 999px; padding: 4px 10px; }
.kpi b { color: var(--fg); font-weight: 700; }
.todo { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; display: grid; gap: 10px; }
.cap { margin: 0; font: 700 10.5px/1 var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.todo ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px 18px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); }
.todo li { display: flex; align-items: center; gap: 10px; min-width: 0; }
.do { flex: none; font: 700 11px/1 var(--mono); text-transform: uppercase; letter-spacing: .05em; padding: 8px 10px; border-radius: 7px; color: var(--on); text-decoration: none; }
.do-live { background: var(--live); } .do-del { background: var(--bad); }
.do-what { min-width: 0; display: grid; gap: 1px; } .do-what small { color: var(--muted); font-size: 12px; }
.num { font: 500 12px var(--mono); font-variant-numeric: tabular-nums; color: var(--muted); }
.when { margin-left: auto; font: 700 12px var(--mono); color: var(--ember); }
.none { color: var(--muted); }
.bar { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; justify-content: space-between; }
.filters { display: flex; flex-wrap: wrap; gap: 6px; }
.filters button { font: 600 12px var(--body); color: var(--fg); background: transparent; border: 1px solid var(--line); border-radius: 999px; padding: 6px 12px; cursor: pointer; }
.filters button[aria-pressed="true"] { background: var(--fg); color: var(--bg); border-color: var(--fg); }
.filters button:focus-visible, a:focus-visible { outline: 2px solid var(--ember); outline-offset: 2px; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; color: var(--muted); }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; vertical-align: -1px; }
.grid { display: grid; gap: 8px; grid-template-columns: repeat(auto-fill, minmax(min(100%, 390px), 1fr)); align-items: start; }
.topic { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; display: grid; gap: 8px; min-width: 0; }
.topic.v-act { border-color: var(--bad); }
.th { display: flex; align-items: baseline; gap: 10px; justify-content: space-between; }
.th h2 { margin: 0; font: 600 15px/1.25 var(--body); }
.verdict { font: 700 10.5px/1.3 var(--mono); text-transform: uppercase; letter-spacing: .05em; text-align: right; color: var(--muted); }
.v-act .verdict { color: var(--bad); } .v-wait .verdict { color: var(--warn); } .v-ok .verdict { color: var(--live); } .v-sched .verdict { color: var(--ember); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 6px; font: 500 12px/1 var(--mono); font-variant-numeric: tabular-nums; color: var(--fg); background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 7px 8px; text-decoration: none; max-width: 100%; }
a.chip:hover { border-color: var(--ember); }
.dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }
.c-live .dot, .l-live { background: var(--live); }
.c-trial .dot, .l-trial { background: transparent; box-shadow: inset 0 0 0 2px var(--trial); }
.c-scheduled .dot, .l-sched { background: var(--ember); }
.c-deleted .dot, .l-del { background: var(--line); }
.c-deleted { color: var(--muted); } .c-deleted .v { text-decoration: line-through; }
.k, .v { font-weight: 700; }
.tr { font-size: 11px; }
.tr-growing { color: var(--live); } .tr-slowing { color: var(--warn); } .tr-stalled { color: var(--bad); } .tr-new { color: var(--muted); }
.flag { font: 700 10px/1 var(--mono); text-transform: uppercase; padding: 3px 5px; border-radius: 4px; color: var(--on); }
.flag-delete { background: var(--bad); } .flag-make { background: var(--live); }
.note { margin: 0; font-size: 12px; color: var(--muted); }
.foot { font-size: 12px; color: var(--muted); max-width: 80ch; margin: 0; }
@media (max-width: 480px) { h1 { font-size: 26px; } .chip { font-size: 11.5px; padding: 7px; } }
</style>
<div class="wrap">
<header><h1>Reel tracker</h1><span class="handle">@how.its.engineered</span><span class="fetched">last fetch {{FETCHED}}</span></header>
<div class="kpis"><span class="kpi"><b>{{FOLLOWERS}}</b> followers</span><span class="kpi"><b>{{GRID}}</b> on grid</span><span class="kpi"><b>{{LIVE}}</b> live</span><span class="kpi"><b>{{TRIAL}}</b> trial</span><span class="kpi"><b>{{SCHED}}</b> scheduled</span><span class="kpi"><b>{{DELETED}}</b> deleted</span><span class="kpi"><b>{{NACT}}</b> of {{TOPICS}} topics need action</span></div>
<section class="todo"><h3 class="cap">To do now</h3><ul>{{TODO}}</ul></section>
<div class="bar">
  <div class="filters" role="group" aria-label="Filter topics">
    <button id="f-all" data-f="all" aria-pressed="true">All</button><button id="f-act" data-f="act" aria-pressed="false">Needs action</button>
    <button id="f-live" data-f="live" aria-pressed="false">Live</button><button id="f-trial" data-f="trial" aria-pressed="false">Trial</button>
    <button id="f-sched" data-f="scheduled" aria-pressed="false">Scheduled</button><button id="f-del" data-f="deleted" aria-pressed="false">Show deleted</button></div>
  <div class="legend"><span><i class="l-live"></i>Live</span><span><i class="l-trial"></i>Trial</span><span><i class="l-sched"></i>Scheduled</span><span><i class="l-del"></i>Deleted</span><span>▲ growing · ▸ slowing · ■ stalled · ● under 3h</span></div>
</div>
<main class="grid">{{GROUPS}}</main>
<p class="foot">Tap a chip to open the reel. Live reels are on the grid and shown to followers. Trial reels are shown only to non-followers and mostly level off around 1.2–1.4k views. Growth is views per hour since the previous fetch: growing is 60+/h, stalled is under 15/h. Space make-lives 30–45 min apart.</p>
</div>
<script>
(function () {
  var btns = Array.from(document.querySelectorAll('.filters button')), topics = Array.from(document.querySelectorAll('.topic'));
  var f = 'all', showDel = false;
  try { f = localStorage.getItem('hie-f') || 'all'; showDel = localStorage.getItem('hie-del') === '1'; } catch (e) {}
  function apply() {
    btns.forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.f === 'deleted' ? String(showDel) : String(b.dataset.f === f)); });
    topics.forEach(function (t) {
      var st = t.dataset.st.split(' '), live = st.filter(function (s) { return s !== 'deleted'; });
      var match = f === 'all' ? (showDel || live.length > 0) : f === 'act' ? t.dataset.v === 'act' : st.indexOf(f) >= 0;
      t.hidden = !match;
      t.querySelectorAll('.chip.c-deleted').forEach(function (c) { c.hidden = !showDel; });
    });
    try { localStorage.setItem('hie-f', f); localStorage.setItem('hie-del', showDel ? '1' : '0'); } catch (e) {}
  }
  btns.forEach(function (b) { b.addEventListener('click', function () { if (b.dataset.f === 'deleted') showDel = !showDel; else f = b.dataset.f; apply(); }); });
  apply();
})();
</script>
'''

if __name__ == '__main__':
    main()
