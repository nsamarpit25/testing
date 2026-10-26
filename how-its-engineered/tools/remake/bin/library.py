#!/usr/bin/env python3
"""HIE reel library: every uploaded reel (views, climbing or flat, link, local preview, what's wrong) plus every reel
that is made but not uploaded, in one sortable table with tabs, sparklines and an inline player (same design as insights/review/).

usage (from how-its-engineered/, after `set -a; source ../.env; set +a; source ~/.instagram_tokens`):
  python3 -I tools/remake/bin/library.py        # fetch, write tools/remake/out/library.html
  python3 -I tools/remake/bin/serve.py          # serve it at http://<this mac>:8765/ (videos need a server)
"""
import html, json, os, re, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tracker as T  # fetch(), registry/history paths

OUT = os.path.join(T.HIE, 'tools', 'remake', 'out', 'library.html')
KIND = {'original': 'Original', 'v2': 'Remake v2', 'B': 'Remake B', 'new': 'New topic', 'new-B': 'New topic B', 'copy': 'Extra copy', 'variant': 'Trial variant'}

# shortcode → media/<dir> for reels posted before the registry kept dirs
DIRS = {
    'DeuoSE4iFmj': '08-docker-v2', 'DevT_PBgJZY': '08-docker-v2b', 'DeusEvgCfo1': '09-kubernetes-v2', 'DevP_yLjBjp': '09-kubernetes-v2b',
    'Deuv8O2DG8g': '05-reverse-proxies-v2', 'DevYDm4jtwu': '05-reverse-proxies-b', 'Deuz-jtD7GN': '01-rate-limiting-v2',
    'Deu389jCI7v': '04-load-balancing-v2', 'DevcEv4gqn3': '04-load-balancing-b', 'Deht-Qwy_gy': '04-load-balancing',
    'Deu77PfkquT': '11-health-checks-v2', 'Devf-dXjxew': '11-health-checks-b', 'DeoNZd-ypXG': '11-health-checks',
    'DevACd5n0hc': '03-idempotency-v2', 'DevkAnzDIbu': '03-idempotency-b', 'Dehel-4ySze': '03-idempotency',
    'DevEBHCEzQv': '19-saga-pattern', 'DevL9S8CCb7': '19-saga-pattern-b', 'DevH-HaDygZ': '20-dead-letter-queues',
    'DevwH0gCQ0_': '20-dead-letter-queues-b', 'Devn_rdFG6z': '21-cron-jobs', 'Devr_8Ej1Y-': '22-websockets',
    'Deuh_3nD3Z_': '20-canary-releases', 'Deml8FfStFb': '10-service-discovery', 'DepTLH1yW8M': '13-circuit-breakers',
    'DepoIsTybkw': '15-timeouts', 'DeqWBdySvAD': '16-retries', 'Der9kXjyueH': '17-message-queues', 'DetdqQXSM9L': '18-pub-sub',
    'Det1RFaS76L': '19-event-driven',
}
# originals posted before media/ existed (by topic)
ORIG = {'Docker': 'outputs/08-docker', 'Kubernetes': 'outputs/09-kubernetes', 'API gateways': 'outputs/06-api-gateways',
        'Reverse proxies': 'outputs/05-reverse-proxies', 'CI/CD': 'outputs/07-ci-cd'}
# known problems, by shortcode or media dir (things the numbers alone don't show)
KNOWN = {
    'Deuv8O2DG8g': 'Showed invalid nginx (`proxy_pass api;`) on screen, so it was deleted. B fixed it.',
    'DeuoSE4iFmj': 'Went up with the old subtitle cover, not the title-only one.',
    'DewQD2ekj6b': 'The "stranger saw everyone\'s orders" hook isn\'t landing: lowest watch time on the account.',
    'DevwH0gCQ0_': 'The new hook did worse than version A.',
    'DevcEv4gqn3': 'The "100,000 people" hook trails v2.',
    '28-connection-pooling-v2': '✅ Codex PASS · ✅ Gemini PASS (Argon on Vertex: beginners get all 6 ideas) · cutcheck clean · ✅ you approved it for Up next (22 Oct); not scheduled yet. New 3D look: a 100-socket database wall, cables per request, refused connections past the limit, a 5-cable pool that requests borrow and hand back, a taxi rank, 3 servers × 5 = 15 of 100.',
    'DeyBc55EpfN': 'Live 22 Oct, 09:00 IST. ✅ Codex PASS · ✅ Gemini PASS (beginners get all 6 ideas). Take 3, GPU render: DROP INDEX hook, "may scan the whole table", primary key gets its own index.',
    '26-query-optimization-v2': '✅ Codex PASS · ✅ Gemini PASS (Argon on Vertex: beginners get all 6 ideas) · ✅ you approved it for Up next (22 Oct) · posted live 22 Oct 19:37 IST on your OK ("upload right now", 4.7 h after Shazam) as DezKT3NCMK0. Replaces v1. 3D: 1,000,000 rows to show 10 → ten newest kept, rest burned; better query filters the table; EXPLAIN Seq Scan → Index Scan. Final polish render (md5 37e8b79ae65e3d78a9a8e09a5b73c8c3): Codex PASS, Gemini PASS (rechecked 22 Oct 19:40), cutcheck clean.',
    '27-n-plus-one-v2': '✅ Codex PASS · ✅ Gemini PASS (Argon on Vertex: beginners get all 6 ideas) · ✅ you approved it for Up next (22 Oct); not scheduled yet. Replaces v1. New 3D look: a trips counter, couriers between app and database, 100 order tiles filling one trip at a time, a wait tower that grows per trip; waiter card; fix = orders + customers WHERE id IN (2 trips), eager loading, query log.',
    'Deypq6Sj5Pw': 'Live 22 Oct, 14:52 IST, posted early on your OK (5.9 h after indexing). ✅ Codex PASS · ✅ Gemini PASS (Argon) · cutcheck clean. New topic (3D): spectrogram → brightest points as stars → paired codes → fingerprint match; 2002 dial-2580 story.',
    'DexOEQLAA-J': 'Live 22 Oct, 01:33 IST. ✅ Codex PASS · ✅ Gemini PASS (Argon) · cutcheck clean. New voice (3.8 Flash), rebuilt AirTag and phones, her bag at the dumpsters.',
    '29-read-replicas': '✅ Codex PASS · ✅ Gemini PASS (Argon on Vertex: beginners get all 6 ideas) · cutcheck clean · made overnight 22 Oct, ✅ you approved it for Up next (23 Oct). New 3D look: a primary cylinder with blue replica copies, orange writes and blue reads, a replica 1 change behind (replication lag), your own reads go to the primary, copying the board.',
    '30-sharding': '✅ Codex PASS · ✅ Gemini PASS (Argon on Vertex: beginners get all 6 ideas) · cutcheck clean · made overnight 22 Oct, ✅ you approved it for Up next (23 Oct). New 3D look: a cube block that overflows, splits into 4 coloured shards by userId % 4, user 42 → shard 2, a library of A–M / N–Z buildings, scatter-gather, a hot shard, % 4 → % 5 moves 48 of 64 users.',
    '31-partitioning': '✅ Gemini PASS (Argon on Vertex: beginners get all 6 ideas; round-1 fix done: the app box now fades before the shard servers land) · Codex not run: out of credits until 03:36, Gemini-only on your OK · cutcheck: 1 flag at 21.45 s = the natural "p" stop inside "skips", not a cut · made overnight 22 Oct, ✅ you approved it for Up next (23 Oct). New 3D look: one long orders slab cut into 36 monthly partitions, last week lights one month and skips 35, a filing cabinet (March folder), the oldest month drops in one step, no-date sweeps every partition, thousands of slivers, partitions vs shards.',
    'Dezf1n6AgQ6': 'Live 22 Oct, 22:44 IST: GPS (3D), on your OK. ✅ Codex PASS · ✅ Gemini PASS (Argon) · cutcheck clean · md5 e0160df8c093d7d2734550872b6bb552.',
    'DezYCTmEn14': 'Live 22 Oct, 21:37 IST: Google Maps traffic (3D), on your OK. ✅ Codex PASS · ✅ Gemini PASS (Argon; flagged a possible voice wobble on "phones" at 30 s, levels measured normal) · cutcheck clean · md5 29cae33042975131f434243ff22c157c.',
    'DezKT3NCMK0': 'Live 22 Oct, 19:37 IST: Query optimization v2 (3D). ✅ Codex PASS · ✅ Gemini PASS · cutcheck clean · md5 37e8b79ae65e3d78a9a8e09a5b73c8c3.',
    'DezGPkuiY-N': 'Trial 22 Oct, 19:02 IST: AirTag B (story first, 45.7 s, AWS render). ✅ Codex PASS · ✅ Gemini PASS · cutcheck clean.',
    '29-airtag-b': 'Re-cut of AirTag (DexOEQLAA-J: 38.6% skip, 19 s avg watch of 57 s, 1 share, 2 saves). Story first (airline said safe, her AirTag showed an apartment complex), "even yours", callback "knew more than the airline", 45.7 s. Rendered on AWS. ✅ Codex PASS · ✅ Gemini PASS (Argon) · cutcheck clean · md5 ff5c243334d8cfc42349d68e162d0846 · posted as a trial 22 Oct 19:02 IST (DezGPkuiY-N).',
    '21-distributed-transactions': 'Paused with the old remake queue. The 1.1x fast cut still needs a final review and a caption.',
    '40-replication': '✅ Codex PASS (round 3; fixed: backup now holds last night\'s records, config switches to \'\' for "right away", the leader visibly fails in the lost-writes what-if) · ✅ Gemini PASS (Argon on Vertex: beginners get all 7 ideas; optional polish: the 24 s power-cut flicker) · cutcheck: no cuts, 1 flag at 6.51 s = natural stop before "gone" in the single voice take · md5 c5caf1486b7aa045ceba5b3234be84e8 · TOPICS.md #32, made overnight 23 Oct, ✅ you approved it for Up next (23 Oct). 3D: one server dies with its disk and every record falls; leader + 2 live copies, every change flies to both; safes in 3 buildings, one floods; copies move to another rack / data center / city, power cut; failover promotes copy A; wait-for-a-copy vs say-done-right-away (postgresql.conf); lost newest writes; a mistaken DELETE wipes every copy, last night\'s backup survives.',
    '41-leader-election': '✅ Codex PASS (round 2; fixed: "YOUR APP" label so it doesn\'t read as a 6th server, wider shot so all 5 servers fit) · ✅ Gemini PASS on the final render (Argon on Vertex: beginners get all 9 ideas, fixes: none; round-1 fixes done: other timers no longer hit zero before the vote request, pills moved off the S4 / S2 names) · cutcheck clean · md5 132bcc2afd818ab3de957cb972119452 · TOPICS.md #33, made overnight 23 Oct, ✅ you approved it for Up next (23 Oct). 3D: five servers in a ring, S1 leader takes every write and sends heartbeats, goes silent; heartbeat card (I\'m alive → flatline); random timers, S5 runs out first and asks for votes (term 2); 3 of 5 votes = new leader; class-monitor card; what-if two leaders = split brain; network cut 3 | 2, only the 3 side has a leader and saves writes; S1 comes back, sees term 2, steps down; etcd uses Raft.',
    '35-face-id': '✅ Codex final PASS (v4, rebuilt 23 Oct) · ✅ Gemini PASS (Argon on Vertex: all 8 ideas clear, interactivity 9/10, feels very premium) · cutcheck clean (v4) · md5 6c27fc10c0199d82072396c2c879af3e (v5: v4 + clean oval mask edge and a lighter fake-face shot; only the mask parts re-rendered and spliced in, no checks run on your say) · v4 polish: smooth head shading, saved cloud in frame, mask prints from the start of the story · rebuilt on your feedback ("very less interactive", "the person is bad"): real 3D head scan (Lee Perry-Smith, CC BY 3.0, credited in caption), live infrared-camera window, dot counter to 30,000+, live nose/cheek distances, dots lift into a turning 3D point cloud, saved face data lines up and the meter says Match; flat photo fails; the mask prints layer by layer, $150 claimed, unverified. Waiting for your OK; not in Up next.',
    '36-touchscreen': '✅ Codex final PASS (round 5 render) · ✅ Gemini PASS (Argon on Vertex: all 7 ideas clear, feels premium) · Codex premium check: NOT YET (wants a more sculpted finger, less toy-like sausage, more edge light, smaller plinth) · cutcheck clean · md5 8ae143e6199a57c33cac9a4097934f74 · premium everyday-tech batch, made overnight 23 Oct, ✅ you approved it for Up next (23 Oct). 3D: phone on a dark plinth, display stack lifts apart to show the sensor grid; glove, finger, nail, water drop and a snack sausage tap it (Feb 2010 South Korea story).',
    '3d-02-kingda-ka-brakes': '✅ Gemini PASS after fixes (Argon: arrow labels added, screech and hum lowered, fin-pop sound added; flagged low-poly trees/buildings, not changed) · Codex not run · 3D series ep 2 (after Taipei 101), sped up 1.25x on your ask, 34.4 s. Kingda Ka 0→128 mph launch HUD, friction pads wear, rare-earth magnets under the cars, copper fins on the track, x-ray eddy currents, magnetic drag, thermal view, rollback fins pop up. ✅ you put it in Up next (24 Oct).',
    '3d-03-jet-blades': '✅ Codex final PASS (round 5; fixed: 200°C caption kept whole, nacelle cutaway in shot B shows the hot turbine core with a tracked HOT TURBINE BLADES INSIDE callout, bluer and longer cool-air film, first line re-voiced from "Jet engine blades" to "Hot turbine blades") · Gemini not run · 3D series ep 3, 32.0 s. Airliner above clouds, single-crystal blade, x-ray cooling channels, film cooling holes, ceramic coat. Not approved for upload yet.',
    '3d-05-shinkansen-kingfisher': '✅ Codex final PASS (round 3; fixed: a full kingfisher (head, body, wings, eye) instead of a lone beak, clearer dive and ripple, a 400 m line from a home to the exit portal in the opening, the −15% POWER figure no longer points at the pantograph, an outside shot of the boom ring sweeping over the homes, the pointed nose shown entering the portal before the gentle x-ray) · Gemini not run · 3D series ep 5, 33.0 s. Made overnight 24 Oct. Not approved for upload yet.',
    '43-eventual-consistency': '✅ Codex final PASS (round 3; fixed: C tag now 98, "always up" softened, city labels dropped so DynamoDB strong reads stay one-region) · Gemini not run · new topic #35, made 24 Oct evening, 62.4 s · weak spots: the phone\'s lower half sits under the caption bar in wide shots ("LIKE FAILED" is hidden there, the tags repeat it), copy C is faded on the cover · md5 62fb9539aca001a8c097e6cb4fdf7076. Waiting for your review.',
    '44-optimistic-locking': '✅ Codex final PASS (round 2; fixed: the Wikipedia line now says only overlapping edits conflict) · Gemini not run · new topic #36, made 24 Oct evening, 56.4 s · weak spots: small labels on the row panel and phone screens (the top counter repeats them) · md5 d34ba97f66b9ba1a8ddcb4fd23baaffe. Waiting for your review.',
    '3d-04-hoover-dam-cooling': '✅ Codex final PASS (round 3; fixed: the cracks on "and it cracks" now glow and hold before the cut) · Gemini not run · 3D series ep 4, made overnight 24 Oct, 35.1 s. Golden-hour canyon, thermal view of one giant pour (hot core vs cooling skin, cracks), columns rising in 5 ft lifts, x-ray 1-inch cooling coils, river then ice water, columns shrink apart, grout fills the gaps. Not approved yet.',
    '37-qr-code': '✅ Codex final PASS (round 3 render) · ✅ Gemini PASS (Argon on Vertex: all 6 ideas clear, feels premium) · Codex premium check: NOT YET (wants brighter paper and key light, fewer similar tilted-menu angles, a more realistic stain, a simpler end card) · cutcheck clean · md5 84c19aca3a8a7f78a49a4637b5655367 · premium everyday-tech batch, made overnight 23 Oct, ✅ you approved it for Up next (23 Oct). 3D: café menu with a real, scannable QR code on an oak table; corner squares, straightening, backup squares rebuild a coffee stain; Denso 1994 story with a Go board and the 1:1:3:1:1 corner stripes.',
}
# made, not uploaded: the "Waiting for review" tab (in order of what's next)
MADE = [
    ('41-leader-election', 'Leader election (3D)', 'Codex + Gemini PASS · approved, up next → live'),
    ('43-eventual-consistency', 'Eventual consistency (3D)', 'New topic · Codex PASS · made 24 Oct, waiting for your review'),
    ('44-optimistic-locking', 'Optimistic locking (3D)', 'New topic · Codex PASS · made 24 Oct, waiting for your review'),
    ('3d-04-hoover-dam-cooling', 'Hoover Dam cooling (3D)', '3D series ep 4 · Codex PASS · approved 24 Oct, up next → live'),
    ('3d-05-shinkansen-kingfisher', 'Shinkansen kingfisher nose (3D)', '3D series ep 5 · Codex PASS · approved 24 Oct, up next → live'),
]
WIP = []
# the upload queue, first = the next reel to go up (still only after Codex PASS and Sam's OK in chat)
NEXT = []


def series():
    """views over time per shortcode, from the insights history and the tracker snapshots"""
    s = {}
    for f in (T.HIST, T.SNAP):
        if not os.path.exists(f): continue
        for ln in open(f):
            try: r = json.loads(ln)
            except Exception: continue
            if r.get('type', 'reel') != 'reel' or (r.get('account') and not r['account'].startswith('how')): continue
            c = r.get('code') or r.get('permalink', '').rstrip('/').split('/')[-1]
            if c and r.get('views'): s.setdefault(c, []).append((datetime.fromisoformat(r['t']), r['views']))
    for v in s.values(): v.sort()
    return s


def ago(pts, now, h):
    """latest point at least h hours old"""
    old = [p for p in pts if now - p[0] >= timedelta(hours=h)]
    return old[-1] if old else None


def fmt_age(h):
    return f'{h * 60:.0f} min' if h < 1 else f'{h:.0f} h' if h < 48 else f'{h / 24:.0f} days'


def main():
    now = datetime.now(T.IST)
    reg = json.load(open(T.REG))['reels']
    me, rows = T.fetch()
    ser = series()
    for c, r in rows.items():  # today's fetch joins the series
        if r['views']: ser.setdefault(c, []).append((now, r['views']))
    # registry rows that went up later are matched by their caption's first line
    for e in reg:
        if not e['code'] and e.get('dir'):
            cap = os.path.join(T.HIE, 'media', e['dir'], 'caption.txt')
            first = open(cap).read().split('\n')[0][:40] if os.path.exists(cap) else None
            for c, r in rows.items():
                if first and r['caption'].startswith(first): e['code'] = c
    # …or, once deleted, by the captions kept in the insights history
    hcap = {}
    for ln in open(T.HIST):
        if '"how.its' in ln and '"type": "reel"' in ln:
            r = json.loads(ln); hcap[(r.get('caption') or '')[:40]] = r['permalink'].rstrip('/').split('/')[-1]
    for e in reg:
        if not e['code'] and e.get('dir'):
            cap = os.path.join(T.HIE, 'media', e['dir'], 'caption.txt')
            first = open(cap).read().split('\n')[0][:40] if os.path.exists(cap) else None
            if first and first in hcap: e['code'] = hcap[first]
    byc = {e['code']: e for e in reg if e['code']}
    up = []
    for c, r in rows.items():
        e = byc.get(c, {'topic': '(not in registry)', 'kind': 'new', 'note': ''})
        pts = ser.get(c, [])
        views = r['views'] or (pts[-1][1] if pts else 0)
        age = (now - r['posted']).total_seconds() / 3600
        p1, p3 = ago(pts, now, 0.9), ago(pts, now, 2.5)
        rate = (views - p1[1]) / ((now - p1[0]).total_seconds() / 3600) if p1 and now > p1[0] else views / age if age > 0.05 else None   # under an hour old: views since posting
        g3 = views - p3[1] if p3 else views if age < 3 else None
        if rate is None: tr = 'new' if age < 6 else 'flat'
        else: tr = 'climbing' if rate >= 60 else 'slow' if rate >= 15 else 'new' if age < 2 else 'flat'
        today0 = next((v for t, v in pts if t.date() == now.date()), None)
        st = stats_of(c)
        up.append(dict(code=c, url=r['url'], topic=e['topic'], kind=e['kind'], live=r['live'], views=views, age=age, rate=rate, g3=g3, trend=tr,
                       today=(views - today0) if today0 is not None and r['posted'].astimezone(T.IST).date() < now.date() else views if r['posted'].astimezone(T.IST).date() == now.date() else None,
                       dir=e.get('dir') or DIRS.get(c) or (ORIG.get(e['topic']) if e['kind'] == 'original' else None), note=e.get('note', ''), caption=r['caption'], posted=r['posted'], **st))
    # account averages for the "what's wrong" lines
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else 0   # medians, so the 20k Kubernetes reel doesn't set the bar
    avg_save = med([u['saves'] / u['reach'] for u in up if u['reach']]); avg_share = med([u['shares'] / u['reach'] for u in up if u['reach']])
    avg_watch = med([u['watch'] for u in up if u['watch']])
    best = {}
    for u in up: best[u['topic']] = max(best.get(u['topic'], 0), u['views'])
    for u in up: u['issue'] = issue(u, best, avg_save, avg_share, avg_watch)
    hinfo = {}
    for ln in open(T.HIST):
        if '"how.its' in ln and '"type": "reel"' in ln:
            r = json.loads(ln); hinfo[r['permalink'].rstrip('/').split('/')[-1]] = r
    def posted_of(c):
        p = hinfo.get(c, {}).get('posted')
        if not p: return None
        try: return datetime.fromisoformat(p.replace('+0000', '+00:00')) if 'T' in p else datetime.fromisoformat(p + 'T12:00:00+05:30')
        except ValueError: return None
    deleted = [dict(e, last=(ser.get(e['code']) or [(None, 0)])[-1][1], posted=posted_of(e['code']), caption=hinfo.get(e['code'], {}).get('caption', ''))
               for e in reg if e['code'] and e['code'] not in rows]
    write(me, up, deleted, now, avg_save, avg_share, avg_watch, ser)


_STATS = None
def stats_of(code):
    """reach / saves / shares / avg watch from `ig.py stats --json` (cached once per run)"""
    global _STATS
    if _STATS is None:
        import subprocess
        out = subprocess.run([sys.executable, '-I', os.path.join(T.HIE, 'tools', 'ig.py'), 'stats', '--n', '100', '--json'], capture_output=True, text=True, cwd=T.HIE).stdout
        _STATS = {r['url'].split('/')[-2]: r for r in json.loads(out[out.index('['):])}
    r = _STATS.get(code, {})
    return dict(reach=r.get('reach', 0) or 0, saves=r.get('saved', 0) or 0, shares=r.get('shares', 0) or 0, likes=r.get('likes', 0) or 0,
                watch=(r.get('ig_reels_avg_watch_time') or 0) / 1000)


def issue(u, best, avg_save, avg_share, avg_watch):
    out = []
    k = KNOWN.get(u['code']) or KNOWN.get(u['dir'] or '')
    if k: out.append(k)
    rch = u['reach'] or 1
    sv, sh = u['saves'] / rch, u['shares'] / rch
    if u['trend'] == 'flat' and u['age'] >= 3:
        if not u['live'] and 1100 <= u['views'] <= 1800: out.append('Stopped at the usual trial ceiling (~1.2–1.6k). Make it live or let it go.')
        elif u['views'] < 1000: out.append(f"Stalled under 1k after {fmt_age(u['age'])}.")
        else: out.append('Views have levelled off.')
    if best.get(u['topic'], 0) > u['views'] * 1.3 and best[u['topic']] != u['views']: out.append(f"Another version of this topic has {best[u['topic']]:,} views.")
    if u['watch'] and u['watch'] < avg_watch - 3: out.append(f"People leave early: {u['watch']:.1f} s average watch (typical {avg_watch:.1f} s).")
    if u['views'] >= 800 and sv < avg_save * 0.5 and sh < avg_share * 0.5: out.append('Gets views but almost no saves or shares.')
    if (sv > avg_save * 1.3 or sh > avg_share * 1.5) and u['trend'] == 'flat': out.append(f"Strong engagement ({sv * 100:.1f}% saves, {sh * 100:.1f}% shares), so it's worth a repost with a new hook.")
    if not out: out.append('No problems. Climbing.' if u['trend'] == 'climbing' else 'Too new to judge.' if u['trend'] == 'new' else 'No problems.')
    return out


def media(d):
    """(video, cover) paths relative to the served root, or (None, None)"""
    if not d: return None, None
    rel = d if '/' in d else f'media/{d}'            # 'outputs/<dir>' for the first originals
    base = os.path.join(T.HIE, rel)
    if not os.path.isdir(base): return None, None
    files = os.listdir(base)
    vids = [f for f in files if f.lower().endswith('.mp4') and 'preview' not in f and '480p' not in f and '360p' not in f]
    pref = [f for f in vids if f == d + '.mp4'] or sorted(vids, key=len)
    cov = [f for f in files if f == 'cover.png'] or [f for f in files if f.startswith('cover') and f.endswith('.png')]
    return (f'/{rel}/{pref[0]}' if pref else None), (f'/{rel}/{cov[0]}' if cov else None)


def review(d):
    f = os.path.join(T.HIE, 'tools', 'remake', 'out', f'fr_{d}.txt')
    if not os.path.exists(f): return 'No Codex final review yet.'
    txt = open(f).read().strip()
    m = re.search(r'VERDICT:\s*(\w+)', txt)
    return f"Codex final: {m.group(1) if m else '?'}."


def ago_txt(h):
    """'40 min ago', '5 h ago', '1 day 6 h ago', '5 days ago'"""
    if h < 1: return f'{max(1, round(h * 60))} min ago'
    if h < 24: return f'{h:.0f} h ago'
    d, r = int(h // 24), round(h % 24)
    if d < 3 and r: return f"{d} day{'s' if d > 1 else ''} {r} h ago"
    return f"{d} day{'s' if d > 1 else ''} ago"


STATUS = {'climbing': ('↑', 'Climbing', 'up', 0), 'slow': ('→', 'Slow', 'slow', 1), 'new': ('●', 'Just posted', 'new', 2), 'flat': ('–', 'Stalled', 'flat', 3),
          'ready': ('▶', 'Waiting for you', 'review', 4), 'paused': ('‖', 'Paused', 'old', 5), 'wip': ('◌', 'In progress', 'new', 6), 'next': ('⏭', 'Up next', 'review', 3.5), 'deleted': ('×', 'Deleted', 'gone', 7)}
THUMBS = os.path.join(T.HIE, 'tools', 'remake', 'out', 't')


def thumb(d):
    """small jpg of the cover (or a frame of the video), cached in tools/remake/out/t/"""
    import subprocess
    v, c = media(d)
    if not (v or c): return None
    os.makedirs(THUMBS, exist_ok=True)
    name = d.replace('/', '_')
    out, src = os.path.join(THUMBS, name + '.jpg'), T.HIE + (c or v)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        subprocess.run(['ffmpeg', '-v', 'error', '-y'] + ([] if c else ['-ss', '1']) + ['-i', src, '-frames:v', '1', '-vf', 'scale=132:-2', '-q:v', '4', out])
    return f'/tools/remake/out/t/{name}.jpg' if os.path.exists(out) else None


def length(v):
    import subprocess
    try: return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', T.HIE + v], capture_output=True, text=True).stdout)
    except (ValueError, OSError): return None


def pts_json(pts, n=60):
    """[[ms, value], …], thinned to about n points, last point kept"""
    pts = [(t, v) for t, v in pts if v]
    if len(pts) > n:
        th = pts[::-(-len(pts) // n)]
        pts = th + ([pts[-1]] if th[-1] != pts[-1] else [])
    return json.dumps([[int(t.timestamp() * 1000), v] for t, v in pts]) if len(pts) > 1 else ''


def total_series(ser, codes, since):
    """sum of the latest known views of each reel, at every fetch time since `since`"""
    import bisect
    s = {c: [p for p in ser.get(c, [])] for c in codes}
    ts = sorted({t.replace(second=0, microsecond=0) for v in s.values() for t, _ in v if t >= since})
    out = []
    for t in ts:
        tot = 0
        for v in s.values():
            k = bisect.bisect_right([p[0] for p in v], t + timedelta(minutes=1)) - 1
            if k >= 0: tot += v[k][1]
        out.append((t, tot))
    return out


def write(me, up, deleted, now, avg_save, avg_share, avg_watch, ser):
    e = html.escape
    up.sort(key=lambda u: u['posted'])                     # first upload first
    for n, u in enumerate(up, 1): u['n'] = n
    climbing = sorted([u for u in up if u['trend'] == 'climbing'], key=lambda u: -(u['rate'] or 0))
    today_total = sum(u['today'] or 0 for u in up)
    acc = [json.loads(l) for l in open(T.HIST) if 'how.its' in l and '"type": "account"' in l]
    f0 = next((a['followers'] for a in acc if a['t'][:10] == now.strftime('%Y-%m-%d')), None)
    fol = me.get('followers_count', 0)
    since = now - timedelta(hours=24)
    fser = [(datetime.fromisoformat(a['t']), a['followers']) for a in acc if datetime.fromisoformat(a['t']) >= since] + [(now, fol)]
    vser = total_series(ser, [u['code'] for u in up], since)
    D, bodies = [], []
    vmax = max([u['views'] for u in up] + [1])

    def body(g, cls, order, st, views, rate, spark, g3, watch, likes, shares, saves, when, link, notes, thumb_src, nm, item):
        i = len(D); D.append(item)
        ic, lbl, pc, so = STATUS[st]
        cell = lambda x, s='', c='n': f'<td class="{c}" data-s="{s}">{x}</td>'
        tb = (f'<img src="{e(thumb_src)}" alt="" loading="lazy">' if thumb_src else '<span class="nothumb"></span>')
        btn = f'<button class="open" aria-expanded="false" aria-label="Play {e(item["title"])}">{tb}<span class="play" aria-hidden="true">▶</span></button>'
        bar = f'<span class="bar"><span style="width:{views / vmax * 100:.1f}%"></span></span>' if views else ''
        pct = lambda x, r: f'{x}<small>{r * 100:.1f}%</small>' if r is not None else (str(x) if x != '' else '–')
        tds = (f'<td class="reel" data-s="{order}">{btn}<span class="nm">{nm}</span></td>'
               + f'<td data-s="{so}"><span class="pill {pc}"><i>{ic}</i>{lbl}</span></td>'
               + cell(f'<b>{views:,}</b>{bar}' if views else '–', views or '', 'n views')
               + cell(f'+{rate:.0f}' if rate is not None else '–', f'{rate:.1f}' if rate is not None else '')
               + f'<td class="sp">' + (f'<svg class="spark" data-p="{e(spark)}" height="28"></svg>' if spark else '') + '</td>'
               + cell(f'+{g3:,}' if g3 is not None else '–', g3 if g3 is not None else '')
               + cell(f'{watch:.1f} s' if watch else '–', f'{watch:.1f}' if watch else '')
               + cell(likes if likes != '' else '–', likes) + cell(pct(*shares), f'{shares[1]:.5f}' if shares[1] is not None else '')
               + cell(pct(*saves), f'{saves[1]:.5f}' if saves[1] is not None else '')
               + f'<td class="when" data-s="{when[0]}" title="{e(when[2])}">{e(when[1])}</td>'
               + f'<td>' + (f'<a class="ig" href="{e(link)}" target="_blank" rel="noopener" aria-label="Open on Instagram">↗</a>' if link else '') + '</td>')
        chips = ''.join(f'<li>{e(x)}</li>' for x in notes if x)
        bodies.append(f'<tbody data-g="{g}" data-i="{i}"><tr class="r {cls}">{tds}</tr>'
                      + (f'<tr class="iss {cls}"><td colspan="12"><ul>{chips}</ul></td></tr>' if chips else '')
                      + '<tr class="xd" hidden><td colspan="12"></td></tr></tbody>')
        return i

    def full_caption(d, fallback=''):
        cap = os.path.join(T.HIE, 'media', d or '', 'caption.txt')
        return open(cap).read().strip() if d and os.path.exists(cap) else fallback

    idx = {}
    for u in up:   # uploaded
        v, c = media(u['dir'])
        rch = u['reach'] or 0
        p = u['posted'].astimezone(T.IST)
        where = 'live' if u['live'] else 'trial'
        nm = (f'<b>{e(u["topic"])}</b> <span class="kd">{e(KIND[u["kind"]])}</span><span class="tp">{e(u["caption"])}</span>'
              f'<span class="mt">#{u["n"]} · {where} · Uploaded {e(ago_txt(u["age"]))}</span>')
        item = dict(video=v, poster=c, title=f"{u['topic']} · {KIND[u['kind']]}", when=f"Uploaded {ago_txt(u['age'])} · {p.strftime('%d %b, %H:%M IST')} · {where}",
                    caption=full_caption(u['dir'], u['caption']), last=f"{u['likes']} likes · {u['saves']} saves · {u['shares']} shares · reach {u['reach']:,}", link=u['url'])
        idx[u['code']] = body(where, u['trend'], int(u['posted'].timestamp()), u['trend'], u['views'], u['rate'], pts_json(ser.get(u['code'], [])), u['g3'], u['watch'],
                              u['likes'], (u['shares'], u['shares'] / rch if rch else None), (u['saves'], u['saves'] / rch if rch else None),
                              (int(u['posted'].timestamp()), ago_txt(u['age']), p.strftime('%d %b, %H:%M IST')), u['url'], u['issue'], thumb(u['dir']) if u['dir'] else None, nm, item)
    waiting, nexts = [], []
    for k, (d, topic, what) in enumerate(MADE + WIP):   # made, not uploaded, in the order they're next
        wip = (d, topic, what) in WIP
        v, c = media(d)
        capt = full_caption(d)
        rv = review(d)
        q = NEXT.index(d) + 1 if d in NEXT else 0
        st = 'next' if q else 'wip' if wip else 'ready' if 'PASS' in rv else 'paused'
        if q: nexts.append((topic, len(D), q))
        if st == 'ready': waiting.append((topic, len(D)))
        ln = length(v) if v else None
        wav = os.path.join(T.HIE, 'videos', d, 'voice', 'voice.wav')
        notes = ([f'#{q} in the upload queue' + ('' if 'PASS' in rv else ' · uploads after Codex PASS and your OK')] if q else []) + ([] if wip else [rv]) + [KNOWN.get(d) or ('Passed the cut/audio check. Waiting for your OK.' if st == 'ready' else '')] + ([f'{ln:.0f} s long'] if ln else [])
        nm = (f'<b>{e(topic)}</b> <span class="kd">{e(what)}</span><span class="tp">{e(capt.split(chr(10))[0]) if capt else ""}</span>'
              f'<span class="mt">{f"Up next · #{q} in queue" if q else "In progress" if wip else "Waiting for your review"} · {e(d)}</span>')
        item = dict(video=v, poster=c, audio=f'/videos/{d}/voice/voice.wav' if not v and os.path.exists(wav) else None, title=f'{topic} · {what}',
                    when='Waiting for review', caption=capt, last=' '.join(n for n in notes if n), link=None)
        body('next' if q else 'unposted', '', (8_000_000_000 + q) if q else 9_000_000_000 + k, st, 0, None, '', None, None, '', ('', None), ('', None), ('', '–', ''), None, notes, thumb(d), nm, item)
    for d in sorted(deleted, key=lambda d: d.get('posted') or now):   # deleted
        dd = d.get('dir') or DIRS.get(d['code']) or (ORIG.get(d['topic']) if d['kind'] == 'original' else None)
        v, c = media(dd)
        p = d.get('posted')
        a = ago_txt((now - p).total_seconds() / 3600) if p else ''
        nm = (f'<b>{e(d["topic"])}</b> <span class="kd">{e(KIND[d["kind"]])}</span><span class="tp">{e((d.get("caption") or "").split(chr(10))[0])}</span>'
              f'<span class="mt">Deleted' + (f' · uploaded {e(a)}' if a else '') + '</span>')
        note = d.get('note') if d.get('deleted') else 'Deleted today.'
        item = dict(video=v, poster=c, title=f"{d['topic']} · {KIND[d['kind']]}", when=f"Uploaded {a} · {p.astimezone(T.IST).strftime('%d %b, %H:%M IST')}" if p else 'Deleted',
                    caption=d.get('caption') or '', last=f"Last seen {d['last']:,} views. {note or ''}", link=f"https://www.instagram.com/reel/{d['code']}/")
        body('deleted', 'gone', int(p.timestamp()) if p else 0, 'deleted', d['last'], None, pts_json(ser.get(d['code'], [])), None, None, '', ('', None), ('', None),
             (int(p.timestamp()) if p else '', f'Uploaded {a}' if a else '–', p.astimezone(T.IST).strftime('%d %b, %H:%M IST') if p else ''), None, [note], thumb(dd) if dd else None, nm, item)

    nlive, ntrial = sum(u['live'] for u in up), sum(not u['live'] for u in up)
    tile = lambda lb, val, dl, sp='', cls='': (f'<div class="tile {cls}"><span class="lb">{lb}</span><b class="val">{val}</b><span class="dl">{dl}</span>'
                                               + (f'<svg class="spark big" data-p="{e(sp)}" height="36"></svg>' if sp else '') + '</div>')
    fast = climbing[0] if climbing else None
    tiles = (tile('Views on all reels', f'{sum(u["views"] for u in up):,}', f'<span class="pos">+{today_total:,}</span> today', pts_json(vser), 'hero')
             + tile('Followers', f'{fol:,}', (f'<span class="pos">{fol - f0:+d}</span> today' if f0 is not None else ''), pts_json(fser))
             + tile('Fastest right now', f'<button class="jump" data-i="{idx[fast["code"]]}">{e(fast["topic"])} {e(short(fast["kind"]))}</button>' if fast else '–',
                    f'<span class="pos">+{fast["rate"]:.0f}</span> views/h' if fast else 'nothing climbing')
             + tile('Reels', f'{nlive} <small>live</small>', f'{ntrial} trial · {len(deleted)} deleted · {len(waiting)} waiting for you'))
    calls = ''
    if nexts:
        t0, i0, _ = min(nexts, key=lambda x: x[2])
        calls += (f'<div class="call review"><span><b>Up next: {e(t0)}.</b> ' + (f'Then {len(nexts) - 1} more in the queue. ' if len(nexts) > 1 else '')
                  + f'Not scheduled yet; nothing posts without your yes.</span><button class="jump btn" data-i="{i0}">▶ Watch {e(t0)}</button></div>')
    if waiting:
        names = [t for t, _ in waiting]
        names = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]
        calls += (f'<div class="call review"><span><b>{e(names)} {"is" if len(waiting) == 1 else "are"} waiting for your OK.</b> '
                  f'Nothing is queued; nothing posts without your yes.</span><button class="jump btn" data-i="{waiting[0][1]}">▶ Watch {e(waiting[0][0])}</button></div>')
    rep = sorted([u for u in up if u['trend'] == 'flat' and u['reach'] and u['saves'] / u['reach'] > avg_save * 1.3], key=lambda u: -u['saves'] / u['reach'])[:5]
    if rep:
        calls += ('<div class="call tip"><span><b>Repost idea.</b> ' + ', '.join(f"{e(u['topic'])} {e(short(u['kind']))} ({u['saves'] / u['reach'] * 100:.1f}% saves)" for u in rep)
                  + f' have stalled, but people saved them more than usual (typical {avg_save * 100:.1f}%). Suggestion only: a new first line and cover.</span></div>')
    ng = lambda g: sum(f'data-g="{g}"' in b for b in bodies)
    page = (TEMPLATE.replace('{{NOW}}', now.strftime('%d %b %Y, %H:%M IST')).replace('{{TILES}}', tiles).replace('{{CALLS}}', calls)
            .replace('{{BODIES}}', ''.join(bodies)).replace('{{NUP}}', str(len(up))).replace('{{NLIVE}}', str(ng('live'))).replace('{{NTRIAL}}', str(ng('trial')))
            .replace('{{NMADE}}', str(ng('unposted'))).replace('{{NNEXT}}', str(ng('next'))).replace('{{NGONE}}', str(ng('deleted'))).replace('{{NALL}}', str(len(bodies)))
            .replace('{{DATA}}', json.dumps(D, ensure_ascii=False).replace('</', '<\\/'))
            .replace('{{AVG}}', f'Typical reel (median): {avg_save * 100:.1f}% saves, {avg_share * 100:.1f}% shares per reach, {avg_watch:.1f} s watch.'))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w').write(page)
    print(OUT)


def short(k): return {'original': 'Orig', 'v2': 'v2', 'B': 'B', 'new': 'New', 'new-B': 'New B', 'copy': 'Copy', 'variant': 'Variant'}[k]


TEMPLATE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>HIE Reel Library</title>
<script>try{const t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
<style>
:root{color-scheme:light;--bg:#f4f3ef;--card:#fcfcfb;--ink:#0b0b0b;--dim:#52514e;--mute:#8a8984;--line:#e4e2dc;--hover:#efeee9;
--accent:#2a78d6;--accent-soft:#cde2fb;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--violet:#6250d6;--pos:#0a7d0a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#111110;--card:#1a1a19;--ink:#f0efec;
--dim:#c3c2b7;--mute:#8d8c85;--line:#2e2e2b;--hover:#242422;--accent:#3987e5;--accent-soft:#184f95;--violet:#9085e9;--pos:#3fc23f}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#111110;--card:#1a1a19;--ink:#f0efec;--dim:#c3c2b7;--mute:#8d8c85;--line:#2e2e2b;
--hover:#242422;--accent:#3987e5;--accent-soft:#184f95;--violet:#9085e9;--pos:#3fc23f}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Inter",system-ui,sans-serif}
main{max-width:1440px;margin:0 auto;padding:20px 16px 40px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:14px}
h1{font-size:26px;margin:0;letter-spacing:-.02em} h1 span{color:var(--mute);font-weight:500}
.sub{margin:2px 0 0;color:var(--dim);font-size:13px} .legend{font-size:12px;color:var(--mute);margin:0} .hr{display:flex;align-items:center;gap:12px;flex-wrap:wrap} .theme{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:5px 12px;font:600 12.5px/1 inherit;cursor:pointer} .theme:hover{background:var(--hover)} .theme:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tiles{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;display:flex;flex-direction:column;min-width:0}
.lb{font-size:12.5px;color:var(--dim)} .val{font-size:26px;font-weight:650;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2;margin:2px 0}
.hero .val{font-size:36px} .val small{font-size:14px;font-weight:500;color:var(--dim)} .dl{font-size:12.5px;color:var(--dim)}
.pos{color:var(--pos);font-weight:600} .tile .spark{width:100%;margin-top:8px}
.jump{all:unset;cursor:pointer;color:var(--ink);border-bottom:2px solid var(--accent)} .jump:hover{color:var(--accent)}
.call{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px;padding:10px 14px;border-radius:12px;
background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent)}
.call.review{border-left-color:var(--violet)} .call.tip{border-left-color:var(--warn)}
.btn{border:0;background:var(--violet);color:#fff;padding:7px 14px;border-radius:99px;font-weight:600;white-space:nowrap}
.btn:hover{filter:brightness(1.1);color:#fff}
.bar-row{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:22px 0 8px;flex-wrap:wrap}
.tabs{display:flex;gap:4px;background:var(--card);border:1px solid var(--line);border-radius:99px;padding:3px}
.tabs button{all:unset;cursor:pointer;padding:6px 14px;border-radius:99px;font-weight:600;font-size:13px;color:var(--dim);white-space:nowrap} .tabs{max-width:100%;overflow-x:auto;scrollbar-width:none}
.tabs button span{font-weight:500;color:var(--mute);margin-left:4px} .tabs button[aria-selected=true]{background:var(--ink);color:var(--card)}
.tabs button[aria-selected=true] span{color:inherit;opacity:.7} .tabs button:focus-visible{outline:2px solid var(--accent)}
.hint{font-size:12px;color:var(--mute)}
.wrap{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:1060px}
th{position:sticky;top:0;background:var(--card);text-align:left;font-size:11.5px;font-weight:600;color:var(--dim);text-transform:uppercase;
letter-spacing:.04em;padding:10px 8px;border-bottom:1px solid var(--line);white-space:nowrap;cursor:pointer;user-select:none}
th.nosort{cursor:default} th.n{text-align:right} th:first-child{text-align:left} th[aria-sort]::after{content:" ↓";color:var(--accent)} th[aria-sort=ascending]::after{content:" ↑"}
td{padding:10px 8px 6px;border-top:1px solid var(--line);vertical-align:middle;white-space:nowrap}
tbody:first-of-type tr.r td{border-top:0} tbody:hover td{background:var(--hover)}
td.n{text-align:right;font-variant-numeric:tabular-nums} td.num{color:var(--mute);font-size:12px;width:28px}
tr.gone td{color:var(--mute)} tr.gone img{filter:grayscale(1);opacity:.6}
td.reel{position:sticky;left:0;z-index:1;background:var(--card);width:300px;min-width:260px;max-width:300px;white-space:normal} th:first-child{position:sticky;left:0;z-index:2}
td.reel{display:table-cell} td.reel>*{vertical-align:middle}
.open{all:unset;position:relative;cursor:pointer;flex:none;display:inline-block;border-radius:8px;overflow:hidden;margin-right:10px}
.open img,.nothumb{display:block;width:44px;height:78px;object-fit:cover;background:#000}
.open:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.play{position:absolute;inset:0;display:grid;place-items:center;color:#fff;font-size:15px;background:rgba(0,0,0,.25);opacity:0;transition:opacity .15s}
.open:hover .play,.open[aria-expanded=true] .play{opacity:1}
.nm{display:inline-block;width:calc(100% - 58px);white-space:normal} .nm b{font-size:14.5px}
.kd{font-size:12.5px;color:var(--dim);font-weight:500} .kd::before{content:"· "} .tp,.mt{display:block;font-size:12.5px;color:var(--mute);line-height:1.35} .tp{color:var(--dim)}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;padding:3px 10px 3px 8px;border-radius:99px;
background:color-mix(in srgb,var(--c) 16%,transparent);color:var(--ink);border:1px solid color-mix(in srgb,var(--c) 40%,transparent)}
.pill i{font-style:normal;color:var(--c);font-weight:800}
.pill.up{--c:var(--good)} .pill.slow{--c:var(--warn)} .pill.flat{--c:var(--crit)} .pill.new{--c:var(--accent)} .pill.gone{--c:var(--mute)}
.pill.review{--c:var(--violet)} .pill.nolive{--c:var(--crit)} .pill.old{--c:var(--mute)}
.views b{font-size:15px} .bar{display:block;height:4px;margin-top:4px;background:var(--line);border-radius:2px;min-width:70px}
.bar span{display:block;height:100%;background:var(--accent);border-radius:2px}
tr.gone .bar span{background:var(--mute)}
.sp{width:104px} .spark{display:block;overflow:visible} .spark path.l{fill:none;stroke:var(--accent);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.spark path.a{fill:var(--accent);opacity:.12} .spark circle{fill:var(--accent);stroke:var(--card);stroke-width:2}
.spark .hv{fill:var(--ink)} .when{color:var(--dim);font-size:12.5px}
tr.iss td{border-top:0;padding:0 8px 10px 72px;white-space:normal} .iss ul{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:4px 6px;position:sticky;left:72px;max-width:min(1100px,calc(100vw - 130px))} .iss li{font-size:12px;color:var(--dim);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:1px 7px} tr.iss.gone li{color:var(--mute)} td.reel+td{padding-left:12px}
.ig{text-decoration:none;color:var(--accent);font-weight:700;font-size:16px;padding:4px}
tr.xd td{background:var(--bg);white-space:normal;padding:14px}
.xbox{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}
.xbox video{height:min(70vh,560px);aspect-ratio:9/16;background:#000;border-radius:12px;display:block;max-width:100%}
.xinfo{max-width:460px;font-size:13.5px} .xinfo h3{margin:0 0 4px;font-size:17px} .xinfo p{margin:4px 0;color:var(--dim)}
.xinfo .cap{color:var(--ink);white-space:pre-wrap;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px} .xinfo audio{width:100%} .xinfo a{color:var(--accent);font-weight:600;text-decoration:none}
.close{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:5px 12px;cursor:pointer;margin-top:8px}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--card);font-size:12px;padding:4px 8px;border-radius:6px;
white-space:nowrap;z-index:9;display:none;font-variant-numeric:tabular-nums}
.empty{padding:30px;text-align:center;color:var(--mute)}
@media (max-width:900px){.tiles{grid-template-columns:repeat(3,1fr)}.hero{grid-column:1/-1}.hero .spark{height:40px}}
@media (max-width:600px){.tiles{grid-template-columns:1fr 1fr}.tiles .tile:last-child{grid-column:1/-1}}
@media (max-width:520px){.hero .val{font-size:32px}.call{flex-direction:column;align-items:flex-start}
td.reel{width:220px;min-width:220px;max-width:220px} tr.iss td{padding-left:8px}}

td small{display:block;font-size:11.5px;color:var(--mute)} .foot{font-size:12px;color:var(--mute);margin:12px 0 0}
</style>
</head><body><main>
<header><div><h1>@how.its.engineered <span>reels</span></h1><p class="sub">Numbers as of {{NOW}}</p></div>
<div class="hr"><p class="legend">↑ Climbing ≥ 60 views/h · → Slow 15–60 · – Stalled &lt; 15 (over the last hour)</p>
<button id="theme" class="theme" aria-label="Switch theme"></button></div></header>
<section class="tiles">{{TILES}}</section>
{{CALLS}}
<div class="bar-row"><div class="tabs" role="tablist">
<button role="tab" data-t="up">Uploaded<span>{{NUP}}</span></button><button role="tab" data-t="live">Live<span>{{NLIVE}}</span></button><button role="tab" data-t="trial">Trial<span>{{NTRIAL}}</span></button><button role="tab" data-t="next">Up next<span>{{NNEXT}}</span></button><button role="tab" data-t="unposted">Waiting for review<span>{{NMADE}}</span></button><button role="tab" data-t="deleted">Deleted<span>{{NGONE}}</span></button><button role="tab" data-t="all">All<span>{{NALL}}</span></button></div>
<span class="hint">Click a column to sort · click a thumbnail to play</span></div>
<div class="wrap"><table><thead><tr><th data-c="0" tabindex=0>Reel</th><th data-c="1" tabindex=0>Status</th><th class="n" data-c="2" tabindex=0>Views</th><th class="n" data-c="3" tabindex=0>Views/h</th><th class="nosort" data-c="4">Trend</th><th class="n" data-c="5" tabindex=0>Last 3 h</th><th class="n" data-c="6" tabindex=0>Watch</th><th class="n" data-c="7" tabindex=0>Likes</th><th class="n" data-c="8" tabindex=0>Shares</th><th class="n" data-c="9" tabindex=0>Saves</th><th class="n" data-c="10" tabindex=0>Uploaded</th><th class="nosort" data-c="11"></th></tr></thead>{{BODIES}}</table><div class="empty" hidden>Nothing here.</div></div>
<p class="foot">{{AVG}} Trial reels are shown only to non-followers. Shares and saves show the count and the share of reach.</p>
<div id="tip"></div>
</main>
<script>
const D = {{DATA}};
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const table = $('table'), tip = $('#tip');
const fmtT = ms => new Date(ms).toLocaleString('en-GB', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata'});

// sparklines: line + soft area, newest point marked, hover shows the value at the nearest point
function spark(svg) {
  const p = JSON.parse(svg.dataset.p), W = svg.clientWidth || +svg.getAttribute('width'), H = +svg.getAttribute('height'), pad = 3;
  const t0 = p[0][0], t1 = p[p.length - 1][0], lo = Math.min(...p.map(q => q[1])), hi = Math.max(...p.map(q => q[1]));
  const X = t => pad + (W - 2 * pad) * (t - t0) / Math.max(1, t1 - t0), Y = v => H - pad - (H - 2 * pad) * (v - lo) / Math.max(1, hi - lo);
  const d = p.map((q, k) => (k ? 'L' : 'M') + X(q[0]).toFixed(1) + ' ' + Y(q[1]).toFixed(1)).join('');
  const last = p[p.length - 1];
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = `<path class="a" d="${d}L${X(t1)} ${H}L${X(t0)} ${H}Z"/><path class="l" d="${d}"/>` +
    `<circle r="3.5" cx="${X(last[0])}" cy="${Y(last[1])}"/><circle class="hv" r="3" style="display:none"/>`;
  const hv = svg.querySelector('.hv');
  svg.onmousemove = e => {
    const r = svg.getBoundingClientRect(), t = t0 + (e.clientX - r.left - pad) / (r.width - 2 * pad) * (t1 - t0);
    const q = p.reduce((a, b) => Math.abs(b[0] - t) < Math.abs(a[0] - t) ? b : a);
    hv.setAttribute('cx', X(q[0])); hv.setAttribute('cy', Y(q[1])); hv.style.display = '';
    tip.textContent = fmtT(q[0]) + ' · ' + q[1].toLocaleString('en-US'); tip.style.display = 'block';
    tip.style.left = Math.min(innerWidth - tip.offsetWidth - 8, e.clientX + 12) + 'px'; tip.style.top = (e.clientY - 30) + 'px';
  };
  svg.onmouseleave = () => { hv.style.display = 'none'; tip.style.display = 'none'; };
}
const drawAll = () => $$('svg.spark').forEach(s => { if (s.getBoundingClientRect().width) spark(s); });
addEventListener('resize', drawAll);

// tabs
let tab = 'up';
try { tab = localStorage.getItem('hie-tab') || 'up'; } catch (e) {}
function setTab(t) {
  tab = t;
  $$('.tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.t === t));
  let shown = 0;
  $$('tbody').forEach(b => { const on = t === 'all' || b.dataset.g === t || (t === 'up' && (b.dataset.g === 'live' || b.dataset.g === 'trial')); b.hidden = !on; shown += on; });
  $('.empty').hidden = shown > 0;
  try { localStorage.setItem('hie-tab', t); } catch (e) {}
  drawAll();
}
$$('.tabs button').forEach(b => b.onclick = () => setTab(b.dataset.t));

// sorting: numbers high to low first, text A to Z first; empty values always last
let sortC = 2, asc = false;
function sortBy(c, a) {
  sortC = c; asc = a;
  $$('th').forEach((h, k) => k === c ? h.setAttribute('aria-sort', a ? 'ascending' : 'descending') : h.removeAttribute('aria-sort'));
  const cv = (b, k) => b.rows[0].cells[k].dataset.s ?? b.rows[0].cells[k].textContent, val = b => cv(b, c);
  const bodies = $$('tbody').sort((x, y) => {
    const u = val(x), v = val(y);
    if (u === '' || v === '') return (u === '') - (v === '');
    const r = isNaN(u) || isNaN(v) ? String(u).localeCompare(v) : u - v;
    if (r === 0 && c === 1) return (+cv(y, 3) || 0) - (+cv(x, 3) || 0) || (+cv(y, 2) || 0) - (+cv(x, 2) || 0);  // same status: fastest first
    return a ? r : -r;
  });
  bodies.forEach(b => table.appendChild(b));
}
$$('th').forEach((h, k) => {
  if (h.classList.contains('nosort')) return;
  const go = () => sortBy(k, sortC === k ? !asc : k === 0);
  h.onclick = go; h.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } };
});

// inline player: one open at a time, right under its row
function closeAll() {
  $$('tr.xd').forEach(x => { if (!x.hidden) { const v = $('video', x); if (v) v.pause(); x.hidden = true; x.cells[0].innerHTML = ''; } });
  $$('.open').forEach(b => b.setAttribute('aria-expanded', 'false'));
}
function openRow(i, scroll) {
  const b = $(`tbody[data-i="${i}"]`), x = $('tr.xd', b), btn = $('.open', b), was = !x.hidden;
  closeAll();
  if (was) return;
  const r = D[i];
  let h = '<div class="xbox">' + (r.video ? `<video controls playsinline autoplay preload="auto" ${r.poster ? `poster="${esc(r.poster)}"` : ''} src="${esc(r.video)}"></video>` : '');
  h += `<div class="xinfo"><h3>${esc(r.title)}</h3><p>${esc(r.topic)}</p><p>${esc(r.when)}</p>`;
  if (r.audio) h += `<p>Voice only so far:</p><audio controls src="${esc(r.audio)}"></audio>`;
  if (r.caption) h += `<p class="cap">${esc(r.caption)}</p>`;
  if (r.last) h += `<p>${esc(r.last)}</p>`;
  if (r.link) h += `<p><a href="${r.link}" target="_blank" rel="noopener">Open on Instagram ↗</a></p>`;
  h += '<button class="close">Close</button></div></div>';
  x.cells[0].innerHTML = h; x.hidden = false; btn.setAttribute('aria-expanded', 'true');
  $('.close', x).onclick = closeAll;
  if (scroll) requestAnimationFrame(() => x.scrollIntoView({behavior: 'smooth', block: 'center'}));
}
$$('.open').forEach(b => b.onclick = () => openRow(+b.closest('tbody').dataset.i));
$$('.jump').forEach(b => b.onclick = () => {
  const i = +b.dataset.i, g = $(`tbody[data-i="${i}"]`).dataset.g;
  if (tab !== 'all' && tab !== g && !(tab === 'up' && (g === 'live' || g === 'trial'))) setTab(g);
  openRow(i, true);
});
addEventListener('keydown', e => { if (e.key === 'Escape') closeAll(); });

// theme: light unless the viewer picked dark
const themeBtn = $('#theme'), root = document.documentElement;
const paintTheme = () => { themeBtn.textContent = root.dataset.theme === 'dark' ? '☀ Light' : '☾ Dark'; };
themeBtn.onclick = () => {
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
  paintTheme();
};
paintTheme();

setTab(['up', 'live', 'trial', 'deleted', 'next', 'unposted', 'all'].includes(tab) ? tab : 'up');
sortBy(1, true);
</script></body></html>'''


if __name__ == '__main__':
    main()
