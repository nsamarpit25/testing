# 17 Message Queues, "soft clay" version: phones -> web server -> glass queue tube -> workers on a cream board.
# Motion follows Argon's per-line plan, timed to voice/timings.json next to this file. Bottom fifth stays clear for captions.
# usage: blender -b -P videos/17-message-queues/clay/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 32] [--stills 3,20] [--range a,b]
import bpy, bmesh, json, math, os, random, re, sys, heapq, wave
from collections import defaultdict
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
RES, FPS, SAMPLES = int(opt('--res', 480)), int(opt('--fps', 24)), int(opt('--samples', 32))
STILLS = [float(x) for x in opt('--stills', '').split(',') if x]
D = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f'{D}/voice/timings.json')); WORDS = json.load(open(f'{D}/voice/words.json'))
with wave.open(f'{D}/voice/voice.wav') as wv: VOICE = wv.getnframes() / wv.getframerate()
LS = {(x['li'], x['pi']): x['start'] for x in T}
L = lambda li, pi=0: LS[(li, pi)]
END = min(VOICE, T[-1]['end'] + 1.8)
F = lambda t: 1 + round(t * FPS)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
def W(tok, after=0.0):
    for w, s, e in WORDS:
        if s >= after - 1e-6 and norm(w).startswith(tok): return s
    raise KeyError(tok)
random.seed(3)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection
prefs = bpy.context.preferences.edit
FONT = bpy.data.fonts.load(os.path.join(os.environ.get('FONT_DIR', '/System/Library/Fonts/Supplemental'), 'Arial Rounded Bold.ttf'))
def hx(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

# ---------- materials: Soft Clay Pastel ----------
def mat(name, h, r=0.8, ss=0.15, e=0.0, a=1.0):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = hx(h); b.inputs['Roughness'].default_value = r; b.inputs['Subsurface Weight'].default_value = ss
    if e: b.inputs['Emission Color'].default_value = hx(h); b.inputs['Emission Strength'].default_value = e
    if a < 1: b.inputs['Alpha'].default_value = a; m.surface_render_method = 'BLENDED'
    return m
C = dict(bg='#F4EFE6', plinth='#EAE1D2', user='#94A3B8', screen='#E0F2FE', server='#10B981', worker='#6366F1', ring='#F59E0B',
         msg='#EC4899', label='#FFFFFF', ltext='#334155', line='#CBB9A0', ok='#34D399', err='#F87171', dead='#64748B', block='#F59E0B')
M = dict(floor=mat('floor', C['bg'], 0.85, 0), plinth=mat('plinth', C['plinth'], 0.8, 0.1), user=mat('user', C['user']),
         screen=mat('screen', C['screen'], 0.6, 0, 0.6), label=mat('label', C['label'], 0.8, 0), ltext=mat('ltext', C['ltext'], 0.8, 0),
         ring=mat('ring', C['ring'], 0.7, 0.1), tube=mat('tube', '#FFFFFF', 0.1, 0, 0, 0.22), msg=mat('msg', C['msg'], 0.7, 0.15, 0.4),
         ok=mat('ok', C['ok'], 0.7, 0.1, 0.3), err=mat('err', C['err'], 0.7, 0.1, 0.3), white=mat('white', '#FFFFFF', 0.7, 0),
         line=mat('line', C['line'], 0.8, 0), wire=mat('wire', C['line'], 0.8, 0), smoke=mat('smoke', '#FFFFFF', 0.9, 0, 0, 0.7),
         ghost=mat('ghost', C['msg'], 0.7, 0.1, 0.4, 0.35), buy=mat('buy', C['server'], 0.7, 0.1), indigo=mat('indigo', C['worker']))
SERVER_M = mat('serverm', C['server']); WORKER_M = [mat(f'worker{k}', C['worker']) for k in range(3)]
PHONE_SCR = mat('phonescr', C['screen'], 0.6, 0, 0.6)

# ---------- builders ----------
def link(ob, m, parent=None, bevel=0.0):
    col.objects.link(ob); ob.data.materials.append(m)
    if parent: ob.parent = parent
    if ob.type == 'MESH': ob.data.shade_smooth()
    if bevel:
        bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 4; bv.limit_method = 'ANGLE'; ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return ob
def box(name, loc, size, m, parent=None, bevel=0.05):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent, bevel)
def cyl(name, loc, r, h, m, parent=None, rot=(0, 0, 0), caps=True, seg=48):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=r, radius2=r, depth=h); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.rotation_euler = rot; return link(ob, m, parent)
def ball(name, loc, r, m, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=r); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent)
def torus(name, loc, m, R=0.31, r=0.045):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=(math.pi / 2, 0, 0))
    o = bpy.context.active_object; o.name = name; o.data.materials.append(m); o.data.shade_smooth(); return o
FACE = (math.radians(45), 0, 0)   # faces the 45-degree camera
def text(name, body, loc, size, m, parent=None, rot=(math.pi / 2, 0, 0)):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.006
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = rot; return link(ob, m, parent)
def curve(name, pts, r, m):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts): p.co = c; p.handle_left_type = p.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu); return link(ob, m)
def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None); ob.location = loc; ob.rotation_euler = rot; col.objects.link(ob)
    if parent: ob.parent = parent
    return ob

def key(target, path, t, val, interp='BEZIER'):
    prefs.keyframe_new_interpolation_type = interp
    setattr(target, path, val); target.keyframe_insert(path, frame=F(t))
def keys(target, path, pts, interp='BEZIER'):
    for t, v in sorted(pts, key=lambda p: p[0]): key(target, path, t, v, interp)
TINY = (0.0001,) * 3
def pop(ob, on, off=None, s=1.0, dur=0.25, over=1.18):
    S3 = lambda v: (v, v, v)
    pts = [(0, TINY), (max(on - 0.001, 0), TINY), (on + dur * 0.6, S3(s * over)), (on + dur, S3(s))]
    if off is not None: pts += [(off - 0.15, S3(s)), (off, TINY)]
    keys(ob, 'scale', pts)
def colour(m, pts):
    s = m.node_tree.nodes.get('Principled BSDF').inputs['Base Color']
    for t, h in sorted(pts):
        prefs.keyframe_new_interpolation_type = 'BEZIER'; s.default_value = hx(h); s.keyframe_insert('default_value', frame=F(t))
def emis(m, pts, h=None):
    b = m.node_tree.nodes.get('Principled BSDF')
    if h: b.inputs['Emission Color'].default_value = hx(h)
    for t, v in sorted(pts):
        prefs.keyframe_new_interpolation_type = 'BEZIER'; b.inputs['Emission Strength'].default_value = v; b.inputs['Emission Strength'].keyframe_insert('default_value', frame=F(t))
def shake(ob, t0, t1, amp=0.05, base=None):
    base = Vector(base or ob.location); pts = [(t0, tuple(base))]; t = t0
    while t < t1: t += 0.05; pts.append((t, tuple(base + Vector((random.uniform(-amp, amp), random.uniform(-amp, amp) * 0.4, 0)))))
    pts.append((t1 + 0.05, tuple(base))); keys(ob, 'location', pts)

# badges: check / cross / question / retry, facing the camera
def badge(name, kind, loc, s=1.0):
    g = empty(name, loc, rot=FACE); g.scale = TINY
    m = {'check': M['ok'], 'x': M['err'], 'q': M['indigo'], 'retry': M['ok']}[kind]
    cyl(f'{name}_disc', (0, 0, 0), 0.2 * s, 0.06, m, g)
    if kind == 'check':
        box(f'{name}_a', (-0.05 * s, 0, 0.04), (0.11 * s, 0.035 * s, 0.035), M['white'], g, 0.01).rotation_euler = (0, 0, math.radians(-45))
        box(f'{name}_b', (0.04 * s, 0.02 * s, 0.04), (0.2 * s, 0.035 * s, 0.035), M['white'], g, 0.01).rotation_euler = (0, 0, math.radians(55))
    elif kind == 'x':
        for a in (45, -45): box(f'{name}_{a}', (0, 0, 0.04), (0.24 * s, 0.045 * s, 0.035), M['white'], g, 0.01).rotation_euler = (0, 0, math.radians(a))
    else:
        text(f'{name}_t', '?' if kind == 'q' else 'RETRY', (0, 0, 0.04), (0.3 if kind == 'q' else 0.09) * s, M['white'], g, rot=(0, 0, 0))
    return g

# ---------- the board ----------
box('ground', (0, 0, -0.06), (80, 80, 0.1), M['floor'], bevel=0)
box('plinth', (0, 0.1, 0.05), (3.8, 7.6, 0.12), M['plinth'], bevel=0.05)
UX = [-1.2, -0.6, 0.0, 0.6, 1.2]; PHONES = []; BUYS = []
for i, x in enumerate(UX):
    p = box(f'phone{i}', (x, -3.0, 0.42), (0.34, 0.07, 0.6), M['user'], bevel=0.06)
    box(f'phonescr{i}', (0, -0.04, 0.02), (0.27, 0.01, 0.48), PHONE_SCR, p, 0.02)
    b = empty(f'buy{i}', (0, -0.05, -0.12), p); b.scale = TINY
    box(f'buyb{i}', (0, 0, 0), (0.22, 0.02, 0.1), M['buy'], b, 0.03); text(f'buyt{i}', 'BUY', (0, -0.012, 0), 0.06, M['white'], b)
    BUYS.append(b); PHONES.append(p)
    curve(f'uline{i}', [(x, -2.9, 0.3), (x * 0.5, -2.35, 0.32), (0, -1.95, 0.45)], 0.016, M['line'])
SV = Vector((0, -1.5, 0.77))
server = empty('server', tuple(SV))
box('server_b', (0, 0, 0), (1.1, 0.8, 1.3), SERVER_M, server, 0.08)
box('server_lbl', (0, -0.41, 0.24), (0.86, 0.02, 0.24), M['label'], server, 0.02)
text('server_t', 'WEB SERVER', (0, -0.425, 0.24), 0.11, M['ltext'], server)
for j in range(3): box(f'server_s{j}', (0, -0.41, -0.15 - j * 0.13), (0.68, 0.02, 0.055), M['ring'], server, 0.01)
WX = [0.0, -1.15, 1.15]; WY = 2.9; WORKERS = []; WSTAT = []
for k, x in enumerate(WX):
    wk = empty(f'worker{k}', (x, WY, 0.62)); WORKERS.append(wk)
    box(f'worker{k}_b', (0, 0, 0), (0.85, 0.7, 1.0), WORKER_M[k], wk, 0.08)
    box(f'worker{k}_lbl', (0, -0.36, 0.18), (0.66, 0.02, 0.2), M['label'], wk, 0.02)
    text(f'worker{k}_t', 'WORKER', (0, -0.375, 0.18), 0.09, M['ltext'], wk)
    st = mat(f'wstat{k}', C['ok'], 0.6, 0, 1.0); WSTAT.append(st)
    box(f'worker{k}_st', (0.25, -0.36, -0.2), (0.12, 0.02, 0.07), st, wk, 0.01)
for k in (1, 2): WORKERS[k].scale = TINY
direct = curve('direct', [(0, -1.1, 1.0), (0.0, 0.4, 1.25), (0, 2.5, 0.9)], 0.02, M['wire'])
QUEUE = empty('queue', (0, 0, 8))
tube = cyl('tube', (0, 0.45, 0.75), 0.3, 3.1, M['tube'], QUEUE, rot=(math.pi / 2, 0, 0), caps=False, seg=64)
for j, y in enumerate((-1.1, 0.45, 2.0)): torus(f'ring{j}', (0, y, 0.75), M['ring']).parent = QUEUE
qlbl = box('q_lbl', (0, -0.3, 1.33), (1.3, 0.04, 0.28), M['label'], QUEUE, 0.03)
text('q_t', 'MESSAGE QUEUE', (0, -0.025, 0), 0.12, M['ltext'], qlbl)
QW = [curve(f'qwire{k}', [(0, 2.05, 0.75), (x * 0.6, 2.3, 0.7), (x, 2.5, 0.55)], 0.016, M['line']) for k, x in enumerate(WX)]
for k in (1, 2): QW[k].scale = TINY
for k, x in enumerate(WX): QW[k].location = (0, 0, 0)

# ---------- lights / world ----------
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(15); sun.color = hx('#FFF5E1')[:3]
so = bpy.data.objects.new('sun', sun); so.rotation_euler = (math.radians(40), 0, math.radians(-35)); col.objects.link(so)
sky = bpy.data.lights.new('sky', 'AREA'); sky.energy = 500; sky.size = 10; sky.color = hx('#E0F2FE')[:3]
ko = bpy.data.objects.new('sky', sky); ko.location = (0, 0, 8); col.objects.link(ko)
w = bpy.data.worlds.new('w'); sc.world = w
try: w.use_nodes = True
except Exception: pass
w.node_tree.nodes['Background'].inputs['Color'].default_value = hx(C['bg']); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9

# ---------- story helpers ----------
CUBES = []
def cube(t_on, loc, m=None):
    o = box(f'cube{len(CUBES)}', tuple(loc), (0.26, 0.2, 0.22), m or M['msg'], bevel=0.04); CUBES.append(o)
    keys(o, 'scale', [(0, TINY), (max(t_on - 0.001, 0), TINY), (t_on + 0.1, (1, 1, 1))]); return o
def gone(o, t): keys(o, 'scale', [(t - 0.12, (1, 1, 1)), (t, TINY)])
PH_TOP = [Vector((x, -2.92, 0.8)) for x in UX]
SV_IN, SV_TOP = Vector((0, -1.95, 0.9)), Vector((0, -1.45, 1.55))
ENTRY = Vector((0, -1.0, 0.75)); EXIT = Vector((0, 2.15, 0.75))
WIN = [Vector((x, WY - 0.45, 0.85)) for x in WX]
def via(o, t, pts, step=0.18):
    for j, p in enumerate(pts): key(o, 'location', t + j * step, tuple(p))
    return t + (len(pts) - 1) * step
def pulse(ob, t, s=1.12):
    keys(ob, 'scale', [(t, (1, 1, 1)), (t + 0.12, (s, s, s)), (t + 0.3, (1, 1, 1))])

# ---- line 0: viral, the backend dies. Why? ----
t_died = W('died'); t_why = L(0, 1)
for i in range(22):
    t = 0.15 + i * 0.08; ph = i % 5
    o = cube(t, PH_TOP[ph])
    pile = Vector((random.uniform(-0.45, 0.45), WY - random.uniform(0.45, 0.9), 0.3 + random.uniform(0, 0.5)))
    via(o, t, [PH_TOP[ph], SV_IN, SV_TOP, Vector((0, 0.4, 1.4)), pile], 0.2)
    gone(o, t_why + 0.35)
for ob, m, base in ((server, SERVER_M, C['server']), (WORKERS[0], WORKER_M[0], C['worker'])):
    keys(ob, 'scale', [(0, (1, 1, 1)), (t_died - 1.0, (1, 1, 1)), (t_died - 0.3, (1.15, 1.15, 1.15)), (t_died, (1, 1, 1))])
    shake(ob, t_died - 0.8, t_died + 0.3)
    colour(m, [(0, base), (t_died - 0.3, base), (t_died, C['dead']), (t_why + 0.25, C['dead']), (t_why + 0.45, base)])
for nm, loc in (('x_sv0', SV + Vector((0.45, -0.5, 0.95))), ('x_wk0', Vector((0.45, WY - 0.5, 1.4)))):
    pop(badge(nm, 'x', loc), t_died, t_why + 0.3)
for i in range(6):
    s = ball(f'smoke{i}', (random.uniform(-0.4, 0.4), random.choice([-1.5, WY]), 1.4), 0.12, M['smoke'])
    keys(s, 'scale', [(0, TINY), (t_died, TINY), (t_died + 0.5, (1.6, 1.6, 1.6)), (t_died + 0.9, TINY)])
    keys(s, 'location', [(t_died, tuple(s.location)), (t_died + 0.9, tuple(s.location + Vector((0, 0, 0.6))))])
pop(badge('why', 'q', (0, 0.2, 1.9), 2.4), t_why - 0.05, L(1) - 0.05)

# ---- line 1: synchronous hand-off, everyone waits ----
t1 = L(1); t_dir = W('directly', t1); t_wait = W('waiting', t1); t_fin = W('finish', t1)
big = cube(t1 + 0.2, PH_TOP[2])
t = via(big, t1 + 0.2, [PH_TOP[2], SV_IN, SV_TOP], 0.3)
via(big, t_dir - 0.2, [SV_TOP, Vector((0, 0.4, 1.45)), WIN[0] + Vector((0, 0, 0.3)), Vector((0, WY, 0.7))], 0.25)
gone(big, t_dir + 0.8)
emis(M['wire'], [(0, 0), (t_dir, 0), (t_dir + 0.3, 2.5), (t_fin + 0.4, 2.5), (t_fin + 0.6, 0)], C['block'])
colour(M['wire'], [(0, C['line']), (t_dir, C['line']), (t_dir + 0.3, C['block']), (t_fin + 0.4, C['block']), (t_fin + 0.6, C['line'])])
def spinner(name, loc, t0, t1):
    g = empty(name, loc, rot=FACE)
    for i in range(8):
        a = i * math.pi / 4; ball(f'{name}{i}', (0.13 * math.cos(a), 0.13 * math.sin(a), 0), 0.022 + 0.004 * i, M['indigo'], g)
    pop(g, t0, t1)
    keys(g, 'rotation_euler', [(t0, FACE), (t1, (FACE[0], 0, -math.radians(360 * (t1 - t0))))], 'LINEAR')
spinner('spin_sv', SV + Vector((0, -0.2, 1.05)), t_wait - 0.2, t_fin + 0.4)
spinner('spin_ph', PH_TOP[2] + Vector((0, -0.1, 0.35)), t_wait - 0.1, t_fin + 0.4)
t = t_dir + 0.9
while t < t_fin: pulse(WORKERS[0], t, 1.06); t += 0.6
ck = badge('ck1', 'check', WIN[0] + Vector((0, 0, 0.7)))
pop(ck, t_fin + 0.3, L(2) - 0.1)
keys(ck, 'location', [(t_fin + 0.45, tuple(WIN[0] + Vector((0, 0, 0.7)))), (t_fin + 1.0, tuple(SV_TOP + Vector((0, 0, 0.4)))), (L(2) - 0.4, tuple(PH_TOP[2] + Vector((0, 0, 0.45))))])

# ---- line 2: ten thousand users click buy, worker chokes, everything crashes ----
t2 = L(2); t_click = W('click', t2); t_choke = W('chokes', t2); t_crash = W('crashes', t2)
for i, b in enumerate(BUYS):
    pop(b, t2 + 0.1 + i * 0.05, L(3) - 0.1)
    keys(b, 'location', [(t_click, (0, -0.05, -0.12)), (t_click + 0.1, (0, 0.0, -0.12)), (t_click + 0.25, (0, -0.05, -0.12))])
cnt = empty('counter', (-1.25, -2.35, 1.25), rot=FACE)
box('cnt_b', (0, 0, 0), (0.9, 0.36, 0.06), M['white'], cnt, 0.12).rotation_euler = (0, 0, 0)
for v, (a, b) in (('100', (t2 + 0.3, t2 + 0.9)), ('1,000', (t2 + 0.9, t2 + 1.4)), ('10,000', (t2 + 1.4, L(3) - 0.1))):
    o = text(f'cnt_{v}', v, (0, 0, 0.04), 0.2, M['ltext'], cnt, rot=(0, 0, 0)); o.scale = TINY
    for fr, v in ((1, TINY), (F(a) - 1, TINY), (F(a), (1, 1, 1)), (F(b) - 1, (1, 1, 1)), (F(b), TINY)):
        o.scale = v; o.keyframe_insert('scale', frame=fr)
pop(cnt, t2 + 0.25, L(3) - 0.1)
for i in range(26):
    t = t_click + 0.2 + i * 0.07; ph = i % 5
    o = cube(t, PH_TOP[ph])
    pile = Vector((random.uniform(-0.5, 0.5), WY - random.uniform(0.45, 1.0), 0.3 + random.uniform(0, 0.75)))
    via(o, t, [PH_TOP[ph], SV_IN, SV_TOP, Vector((0, 0.4, 1.4)), pile], 0.18)
    gone(o, L(3) + 0.2)
colour(WORKER_M[0], [(t_choke - 0.2, C['worker']), (t_choke + 0.2, C['err']), (L(3) + 0.1, C['err']), (L(3) + 0.35, C['worker'])])
shake(WORKERS[0], t_choke, t_crash + 0.3)
pop(badge('x_wk2', 'x', (0.45, WY - 0.5, 1.4)), t_choke + 0.1, L(3))
colour(M['wire'], [(t_choke + 0.2, C['line']), (t_choke + 0.6, C['err']), (L(3), C['err']), (L(3) + 0.2, C['line'])])
colour(SERVER_M, [(t_crash - 0.3, C['server']), (t_crash, C['err']), (L(3) + 0.1, C['err']), (L(3) + 0.35, C['server'])])
colour(PHONE_SCR, [(0, C['screen']), (t_crash, C['screen']), (t_crash + 0.3, C['err']), (L(3) + 0.1, C['err']), (L(3) + 0.35, C['screen'])])
pop(badge('x_sv2', 'x', SV + Vector((0.45, -0.5, 0.95))), t_crash, L(3))

# ---- line 3: enter the message queue ----
t3 = L(3); t_mq = W('message', t3); t_rmq = W('rabbitmq', t3)
keys(direct, 'scale', [(0, (1, 1, 1)), (t3 + 0.2, (1, 1, 1)), (t3 + 0.4, TINY)])
keys(QUEUE, 'location', [(0, (0, 0, 8)), (t_mq - 0.25, (0, 0, 8)), (t_mq + 0.15, (0, 0, -0.06)), (t_mq + 0.28, (0, 0, 0.05)), (t_mq + 0.4, (0, 0, 0))])
for k, (txt, x) in enumerate((('RabbitMQ', -1.35), ('Amazon SQS', 1.35))):
    g = empty(f'brand{k}', (x, 0.45, 1.35), rot=FACE)
    box(f'brand{k}_b', (0, 0, 0), (1.0, 0.34, 0.06), M['white'], g, 0.1)
    text(f'brand{k}_t', txt, (0, 0, 0.04), 0.12, M['ltext'], g, rot=(0, 0, 0))
    pop(g, t_rmq + 0.5 * k, L(4) - 0.1)

# ---- queue simulation from line 4 on ----
PITCH = 0.34
SLOT = lambda i: Vector((0, 1.82 - i * PITCH, 0.75))
NS = 8
LOC = defaultdict(dict); queue, ev = [], []
def push(t, kind, *a): heapq.heappush(ev, (t, len(ev), kind, a))
def last(o, t):
    ks = [k for k in LOC[o] if k <= t + 1e-6]; return LOC[o][max(ks)] if ks else None
def relayout(t):
    for i, o in enumerate(queue):
        p = last(o, t)
        if p is not None: LOC[o][round(t, 3)] = p
        LOC[o][round(t + 0.22, 3)] = tuple(SLOT(i))
def enq(t, ph, ok=True): push(t, 'enq', ph, ok)
def deq(t, k, fail=None): push(t, 'deq', k, fail)
CHECKS = []
t4 = L(4); t_got = W('we', W('user', t4))
enq(t4 + 0.2, 2, False)
ck4 = badge('ck4', 'check', SV + Vector((0, -0.45, 1.0)))
pop(ck4, t_got - 0.05, L(5) - 0.1)
keys(ck4, 'location', [(t_got + 0.1, tuple(SV + Vector((0, -0.45, 1.0)))), (t_got + 0.5, tuple(PH_TOP[2] + Vector((0, 0, 0.45))))])
t5 = L(5); t_spike = W('spike', t5); t_pace = W('own', t5)
for i in range(9): enq(t_spike + 0.1 + i * 0.25, (i * 3) % 5)
t = t5 + 2.4
while t < L(6) + 0.6: deq(t, 0); t += 1.5
t6 = L(6); t_more = W('more', t6)
for k in (1, 2):
    pop(WORKERS[k], t_more - 0.1 + 0.15 * k, dur=0.35, over=1.2)
    keys(WORKERS[k], 'location', [(0, (WX[k], WY, 2.5)), (t_more - 0.1 + 0.15 * k, (WX[k], WY, 2.5)), (t_more + 0.25 + 0.15 * k, (WX[k], WY, 0.62))])
    keys(QW[k], 'scale', [(0, TINY), (t_more + 0.3, TINY), (t_more + 0.5, (1, 1, 1))])
t = t_more + 0.7
while t < L(7) - 1.6:
    for k in (1, 0, 2): deq(t + (1, 0, 2).index(k) * 0.3, k)
    t += 1.0
for t in (L(7) - 1.4, L(7) - 1.0, L(7) - 0.6): enq(t, int(t * 7) % 5)
t7 = L(7); t_wc = W('crashes', t7); t_another = W('another', t7); t_finish = W('finishes', t7)
deq(t7 + 0.4, 1, fail=(t_wc + 0.1, t_another - 0.3))
deq(t_another, 0)
t8 = L(8)
pop(badge('retry', 'retry', (WX[1] + 0.0, WY - 0.3, 1.55), 1.4), t8 + 0.2, t8 + 2.2)
t = t8 + 0.3; rr = 0
while t < END - 0.6:
    enq(t, rr % 5); deq(t + 0.5, (1, 0, 2)[rr % 3]); t += 0.45; rr += 1

GHOST = None
while ev:
    t, _, kind, a = heapq.heappop(ev)
    if kind == 'enq':
        ph, ok = a
        pending = sum(1 for x in ev if x[2] == 'arrive')
        if len(queue) + pending >= NS: continue
        o = cube(t, PH_TOP[ph])
        for j, p in enumerate([PH_TOP[ph], SV_IN, SV_TOP, ENTRY]): LOC[o][round(t + j * 0.18, 3)] = tuple(p)
        push(t + 0.54 + 0.35, 'arrive', o)
        if ok and t5 <= t < L(6):
            c = badge(f'ckp{len(CHECKS)}', 'check', PH_TOP[ph] + Vector((0, 0, 0.42)), 0.6); CHECKS.append(c); pop(c, t + 0.6, t + 1.3)
    elif kind == 'arrive':
        o = a[0]; queue.append(o); LOC[o][round(t, 3)] = tuple(SLOT(len(queue) - 1))
    elif kind == 'deq':
        k, fail = a
        if not queue: continue
        o = queue.pop(0)
        LOC[o][round(t, 3)] = tuple(SLOT(0)); LOC[o][round(t + 0.2, 3)] = tuple(EXIT)
        LOC[o][round(t + 0.45, 3)] = tuple(WIN[k] + Vector((0, 0, 0.3))); LOC[o][round(t + 0.65, 3)] = tuple(WIN[k] + Vector((0, 0.3, 0.0)))
        if fail:
            t_dead, t_solid = fail
            g = cube(t, SLOT(0), M['ghost']); GHOST = g
            LOC[g][round(t, 3)] = tuple(SLOT(0)); queue.insert(0, g)
            relayout(t)
            LOC[o][round(t_dead, 3)] = tuple(WIN[k] + Vector((0, 0.3, 0.0))); gone(o, t_dead + 0.25)
            colour(WORKER_M[k], [(0, C['worker']), (t_dead, C['worker']), (t_dead + 0.25, C['dead']), (t8 + 0.1, C['dead']), (t8 + 0.4, C['worker'])])
            shake(WORKERS[k], t_dead, t_dead + 0.5, 0.05, (WX[k], WY, 0.62))
            pop(badge('x_w7', 'x', (WX[k] + 0.4, WY - 0.5, 1.35)), t_dead + 0.1, t8 + 0.1)
            emis(WSTAT[k], [(0, 1.0), (t_dead, 1.0), (t_dead + 0.1, 0.0), (t8 + 0.2, 0.0), (t8 + 0.3, 1.0)])
            b = M['ghost'].node_tree.nodes['Principled BSDF'].inputs['Alpha']
            for tt, v in ((0, 0.35), (t_solid, 0.35), (t_solid + 0.3, 1.0)):
                prefs.keyframe_new_interpolation_type = 'BEZIER'; b.default_value = v; b.keyframe_insert('default_value', frame=F(tt))
            lock = badge('lock', 'check', SLOT(0) + Vector((0, 0, 0.45)), 0.5); pop(lock, t + 0.2, t_solid + 0.2)
        else:
            relayout(t)
            gone(o, t + 0.8); pulse(WORKERS[k], t + 0.7)
            emis(WSTAT[k], [(t + 0.7, 1.0), (t + 0.8, 6.0), (t + 1.1, 1.0)])
            if o is GHOST:
                c = badge('ck7', 'check', WIN[k] + Vector((0, 0, 0.8)), 1.2); pop(c, t + 0.8, L(8) + 0.2)
for o, pts in LOC.items():
    for tt in sorted(pts): key(o, 'location', tt, pts[tt])

# ---------- camera: orthographic, 45 degrees, board kept above the caption zone ----------
tgt = empty('tgt'); camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd)
col.objects.link(cam); sc.camera = cam; camd.type = 'ORTHO'; camd.clip_end = 200
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
EL = math.radians(45); OFF = Vector((0, -math.cos(EL), math.sin(EL))) * 30
def shot(t, y, scale, x=0.0, interp='BEZIER'):
    g = Vector((x, y, 0.55)); key(tgt, 'location', t, tuple(g), interp); key(cam, 'location', t, tuple(g + OFF), interp)
    key(camd, 'ortho_scale', t, scale, interp)
FULL = (-1.4, 7.6)
SH = [(0, *FULL), (t_why - 0.2, *FULL), (t_why + 0.3, -1.25, 7.6), (L(1) - 0.1, -1.25, 7.6), (L(1) + 0.5, -1.0, 7.2),
      (L(2) - 0.1, -1.0, 7.2), (L(2) + 0.4, *FULL), (t_crash - 0.05, *FULL)]
for t, y, s in SH: shot(t, y, s)
for j in range(5): shot(t_crash + 0.05 + j * 0.06, FULL[0] + random.uniform(-0.08, 0.08), FULL[1], random.uniform(-0.08, 0.08))
for t, y, s in [(t_crash + 0.4, *FULL), (L(3) + 0.1, *FULL), (t_mq + 0.6, -0.55, 6.2), (L(4) - 0.1, -0.55, 6.2), (L(4) + 0.5, -1.95, 5.2),
                (L(5) - 0.1, -1.95, 5.2), (L(5) + 0.6, *FULL), (t_pace - 0.6, -1.2, 7.4), (L(6) - 0.2, -0.5, 7.2), (L(6) + 0.5, 1.75, 6.6),
                (L(7) - 0.1, 1.75, 6.6), (L(7) + 0.5, 1.85, 4.4), (L(8) - 0.2, 1.85, 4.4), (L(8) + 1.0, *FULL), (END, -1.4, 7.4)]:
    shot(t, y, s, -0.4 if (L(7) + 0.4 < t < L(8)) else 0.0)

# ---------- render ----------
sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = SAMPLES; ee.use_raytracing = True; ee.use_shadows = True; ee.use_fast_gi = True
sc.render.resolution_x, sc.render.resolution_y = RES, int(RES * 16 / 9) // 2 * 2
sc.render.resolution_percentage = 100; sc.render.fps = FPS
a, b = [int(x) for x in opt('--range', f'1,{F(END)}').split(',')]
sc.frame_start, sc.frame_end = a, b
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = 0.15
if STILLS:
    for s in STILLS:
        sc.frame_set(F(s)); sc.render.filepath = f'{OUT}/still_{s:05.2f}.png'; bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = f'{OUT}/f_'; bpy.ops.render.render(animation=True)
