# Map the new voice's clock onto the clock video.html was timed against (the first, robotic take),
# and give every caption word the script's spelling with the new take's timing.
# usage: python3 voice/warp.py <ref_words.json> <words.json> <script.json> <warp.js>
# Writes window.WARP = [[new_t, ref_t], ...] and window.CAPW = [[word, start, end], ...].
import difflib, json, re, sys

ref, new, script = (json.load(open(p)) for p in sys.argv[1:4])
norm = lambda w: re.sub(r'[^a-z0-9]', '', w.lower())
match = lambda a, b: difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()

# time warp: anchors on the words both takes share
a, b = [norm(w[0]) for w in ref], [norm(w[0]) for w in new]
pairs = [[0.0, 0.0]]
for blk in match(a, b):
    for k in range(blk.size):
        r, n = ref[blk.a + k][1], new[blk.b + k][1]
        if n > pairs[-1][0] + 0.05 and r > pairs[-1][1] + 0.05: pairs.append([round(n, 3), round(r, 3)])
pairs.append([round(new[-1][2] + 2.0, 3), round(ref[-1][2] + 2.0, 3)])

# captions: the script's words, timed by whisper; unmatched words share the gap between their neighbours
toks = [w for line in script['lines'] for p in line for w in re.sub(r'[*\[\]]', '', p['show']).split()]
st = [None] * len(toks)
for blk in match([norm(w) for w in toks], b):
    for k in range(blk.size): st[blk.a + k] = (new[blk.b + k][1], new[blk.b + k][2])
i = 0
while i < len(toks):
    if st[i]: i += 1; continue
    j = i
    while j < len(toks) and not st[j]: j += 1
    t0 = st[i - 1][1] if i else 0.0
    t1 = st[j][0] if j < len(toks) else new[-1][2]
    for k in range(i, j):
        u0, u1 = (k - i) / (j - i), (k - i + 1) / (j - i)
        st[k] = (t0 + (t1 - t0) * u0, t0 + (t1 - t0) * u1)
    i = j
capw = [[w, round(s, 3), round(e, 3)] for w, (s, e) in zip(toks, st)]
open(sys.argv[4], 'w').write('window.WARP=%s;\nwindow.CAPW=%s;\n' % (json.dumps(pairs), json.dumps(capw, ensure_ascii=False)))
print(len(pairs), 'warp anchors of', len(b), 'words;', sum(1 for blk in match([norm(w) for w in toks], b) for _ in range(blk.size)), 'of', len(toks), 'caption words matched')
