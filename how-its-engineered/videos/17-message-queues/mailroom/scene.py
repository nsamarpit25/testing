# 17 Message Queues, "mailroom" version: order slips on a conveyor, a glass queue tower, a rack of workers.
# Timed to voice/timings.json next to this file. Framing uses long lenses and keeps the bottom fifth for captions.
# usage: blender -b -P videos/17-message-queues/mailroom/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 24] [--stills 3,20] [--range a,b]
import bpy, bmesh, json, math, os, random, re, sys, heapq, wave
from collections import defaultdict
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
RES, FPS, SAMPLES = int(opt('--res', 480)), int(opt('--fps', 24)), int(opt('--samples', 24))
STILLS = [float(x) for x in opt('--stills', '').split(',') if x]
D = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f'{D}/voice/timings.json'))
WORDS = json.load(open(f'{D}/voice/words.json'))
with wave.open(f'{D}/voice/voice.wav') as wv: VOICE = wv.getnframes() / wv.getframerate()
LS = {(x['li'], x['pi']): x['start'] for x in T}
L = lambda li, pi=0: LS[(li, pi)]
END = min(VOICE, T[-1]['end'] + 1.8)
F = lambda t: 1 + round(t * FPS)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
def W(tok, after=0.0):
    for w, s, e in WORDS:
        if s >= after - 1e-6 and norm(w) == tok: return s
    raise KeyError(tok)
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection
prefs = bpy.context.preferences.edit
FONT = bpy.data.fonts.load(os.path.join(os.environ.get('FONT_DIR', '/System/Library/Fonts/Supplemental'), 'DIN Alternate Bold.ttf'))

def hx(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

# ---------- materials (Argon's palette) ----------
def mat(name, h, rough=0.5, metal=0.0, emit=0.0, alpha=1.0, eh=None):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = hx(h); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = hx(eh or h); b.inputs['Emission Strength'].default_value = emit
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.surface_render_method = 'BLENDED'
    return m
M = dict(
    body=mat('body', '#F4F1EA', 0.45), trim=mat('trim', '#2B3240', 0.4), wall=mat('wall', '#1A2130', 0.8), floor=mat('floor', '#12161F', 0.65),
    pillar=mat('pillar', '#232B3B', 0.6), brass=mat('brass', '#D9A441', 0.3, 1.0), panel=mat('panel', '#111111', 0.4),
    ltext=mat('ltext', '#FFFFFF', 0.4, emit=2.0), paper=mat('paper', '#FFFFFF', 0.55), coral=mat('coral', '#FF4757', 0.45),
    slate=mat('slate', '#2B3240', 0.45), ink=mat('ink', '#1A2130', 0.5), stamp=mat('stamp', '#FF4757', 0.35),
    alert=mat('alert', '#FF2A38', 0.4, emit=8.0), green=mat('green', '#2ECC71', 0.4, emit=6.0), warm=mat('warm', '#FFE9C7', 0.4, emit=5.0),
    glow=mat('glow', '#0E2A47', 0.4, emit=1.5, eh='#38B6FF'), glass=mat('glass', '#BFE6FF', 0.05, alpha=0.1), cyan=mat('cyan', '#38B6FF', 0.4, emit=5.0),
    bulb=mat('bulb', '#FFE2A8', 0.4, emit=10.0), dark=mat('dark', '#0B0E14', 0.6),
    strip=mat('strip', '#38B6FF', 0.4, emit=1.6), edge=mat('edge', '#38B6FF', 0.4, emit=3.0), grey=mat('grey', '#C9CED8', 0.5),
    button=mat('button', '#FFB020', 0.4, emit=2.5), vent=mat('vent', '#1C222D', 0.6), line=mat('line', '#B8BEC9', 0.6),
)

# ---------- builders ----------
def link(ob, m, parent=None, bevel=0.0):
    col.objects.link(ob); ob.data.materials.append(m)
    if parent: ob.parent = parent
    if ob.type == 'MESH': ob.data.shade_smooth()
    if bevel:
        bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'; ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return ob
def box(name, loc, size, m, parent=None, bevel=0.02):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent, bevel)
def cyl(name, loc, r, h, m, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r, radius2=r, depth=h); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent)
def sphere(name, loc, r, m, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent)
def text(name, body, loc, size, m, parent=None, extrude=0.004):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = extrude
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = (math.pi / 2, 0, 0); return link(ob, m, parent)
def empty(name, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None); ob.location = loc; col.objects.link(ob)
    if parent: ob.parent = parent
    return ob
def area(name, loc, aim, size, power, h):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = power; ld.size = size; ld.color = hx(h)[:3]
    ob = bpy.data.objects.new(name, ld); ob.location = loc; col.objects.link(ob)
    ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return ob
def point(name, loc, power, h, r=0.2, kind='POINT'):
    ld = bpy.data.lights.new(name, kind); ld.energy = power; ld.color = hx(h)[:3]; ld.shadow_soft_size = r
    ob = bpy.data.objects.new(name, ld); ob.location = loc; col.objects.link(ob); return ob

def key(target, path, t, val, interp='BEZIER'):
    prefs.keyframe_new_interpolation_type = interp
    setattr(target, path, val); target.keyframe_insert(path, frame=F(t))
def keys(target, path, pts, interp='BEZIER'):
    for t, v in sorted(pts, key=lambda p: p[0]): key(target, path, t, v, interp)
TINY = (0.001,) * 3
def vis(ob, on, off=None, pop=0.15, s=(1, 1, 1)):
    pts = [(0, TINY), (max(on - 0.001, 0), TINY), (on + pop, s)]
    if off is not None: pts += [(off - pop, s), (off, TINY)]
    keys(ob, 'scale', pts)
def emit_keys(m, pts):
    b = m.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength']
    for t, v in pts:
        prefs.keyframe_new_interpolation_type = 'CONSTANT'; b.default_value = v; b.keyframe_insert('default_value', frame=F(t))

# ---------- the room ----------
nt = M['floor'].node_tree; fb = nt.nodes['Principled BSDF']; fb.inputs['Roughness'].default_value = 0.42
ck = nt.nodes.new('ShaderNodeTexChecker'); tcn = nt.nodes.new('ShaderNodeTexCoord'); ck.inputs['Scale'].default_value = 0.5
ck.inputs['Color1'].default_value = hx('#12161F'); ck.inputs['Color2'].default_value = hx('#171C27')
nt.links.new(tcn.outputs['Object'], ck.inputs['Vector']); nt.links.new(ck.outputs['Color'], fb.inputs['Base Color'])
box('floor', (18, 0, -0.05), (90, 40, 0.1), M['floor'], bevel=0)
box('wall', (18, 5.2, 4.5), (90, 0.3, 9), M['wall'], bevel=0)
box('ceiling', (18, 0, 9.1), (90, 40, 0.2), M['dark'], bevel=0)
box('wainscot', (18, 5.0, 0.6), (90, 0.2, 1.2), M['trim'], bevel=0)
box('wainrail', (18, 4.88, 1.22), (90, 0.08, 0.06), M['brass'], bevel=0)
for i, x in enumerate(range(-8, 46, 4)):
    box(f'pillar{i}', (x, 4.6, 4.5), (0.6, 0.6, 9), M['pillar'], bevel=0.03)
    box(f'pcap{i}', (x, 4.6, 6.0), (0.72, 0.72, 0.18), M['brass'], bevel=0.02)
    box(f'pstrip{i}', (x, 4.29, 3.6), (0.035, 0.02, 4.6), M['strip'], bevel=0)
PEND = []
for i, x in enumerate(range(-6, 40, 4)):
    cyl(f'rope{i}', (x, 2.6, 7.6), 0.012, 3.0, M['dark'])
    cyl(f'shade{i}', (x, 2.6, 6.05), 0.3, 0.2, M['brass'])
    sphere(f'bulb{i}', (x, 2.6, 5.88), 0.1, M['bulb'])
    PEND.append(point(f'pl{i}', (x, 2.6, 5.6), 60, '#FFB46B', 0.15))
w = bpy.data.worlds.new('w'); sc.world = w
try: w.use_nodes = True
except Exception: pass
w.node_tree.nodes['Background'].inputs['Color'].default_value = hx('#0B0E14'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5
vs = w.node_tree.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Density'].default_value = 0.012; vs.inputs['Anisotropy'].default_value = 0.35
w.node_tree.links.new(vs.outputs['Volume'], w.node_tree.nodes['World Output'].inputs['Volume'])

def three_point(tag, c):
    c = Vector(c)
    k = area(f'{tag}_key', c + Vector((-4.5, -6.5, 5.5)), c, 5.0, 1400, '#FFF5E4')
    f = area(f'{tag}_fill', c + Vector((5.0, -6.0, 2.5)), c, 5.0, 350, '#90B4FF')
    r = area(f'{tag}_rim', c + Vector((0.5, 3.2, 6.0)), c + Vector((0, -0.5, 0)), 4.0, 900, '#FFE2BF')
    return k, f, r
KEY_A = three_point('A', (1.5, 0.6, 1.2))
KEY_B = three_point('B', (30.6, 0.0, 2.2))

def machine(name, label, x, y=1.3, z=0.0, lampmat=None, s=1.0):
    root = empty(name, (x, y, z)); root.scale = (s, s, s)
    box(f'{name}_body', (0, 0, 1.0), (1.6, 1.2, 2.0), M['body'], root, 0.05)
    box(f'{name}_band', (0, 0, 0.15), (1.66, 1.26, 0.3), M['trim'], root, 0.02)
    box(f'{name}_cap', (0, 0, 2.05), (1.7, 1.3, 0.1), M['trim'], root, 0.02)
    box(f'{name}_plate', (0, -0.6, 1.6), (1.36, 0.04, 0.4), M['panel'], root, 0.015)
    text(f'{name}_lbl', label, (0, -0.625, 1.6), 0.24 if len(label) < 10 else 0.18, M['ltext'], root)
    box(f'{name}_slot', (0, -0.6, 0.78), (0.95, 0.04, 0.3), M['dark'], root, 0.01)
    sphere(f'{name}_lamp', (0, 0, 2.22), 0.12, lampmat or M['warm'], root)
    box(f'{name}_edge', (0, -0.655, 2.0), (1.62, 0.015, 0.03), M['edge'], root, 0)
    box(f'{name}_scr', (-0.28, -0.6, 1.22), (0.62, 0.035, 0.18), M['panel'], root, 0.01)
    for j in range(4): box(f'{name}_bar{j}', (-0.5 + j * 0.15, -0.62, 1.22), (0.1, 0.01, 0.07 + 0.03 * (j % 2)), M['strip'], root, 0)
    for j, bx in enumerate((0.3, 0.48)):
        b = cyl(f'{name}_btn{j}', (bx, -0.61, 1.22), 0.055, 0.04, M['button'] if j else M['grey'], root); b.rotation_euler = (math.pi / 2, 0, 0)
    for side in (-1, 1):
        for j in range(5): box(f'{name}_vent{side}{j}', (side * 0.805, 0, 0.55 + j * 0.13), (0.02, 0.8, 0.05), M['vent'], root, 0)
    return root

# ---------- area A: the synchronous chain ----------
box('belt', (1.5, 0, 0.72), (5.6, 0.9, 0.1), M['trim'], bevel=0.02)
box('beltrimF', (1.5, -0.47, 0.78), (5.6, 0.05, 0.08), M['brass'])
box('beltrimB', (1.5, 0.47, 0.78), (5.6, 0.05, 0.08), M['brass'])
for i in range(6): box(f'leg{i}', (-1 + i, 0, 0.33), (0.08, 0.7, 0.66), M['dark'])
lampA = mat('lampA', '#2ECC71', 0.4, emit=5.0)
CHAIN = [('ORDER', 0), ('PAYMENT', 3)]
STAMPS = {}
for nm, x in CHAIN:
    machine(f'A_{nm}', nm, x, lampmat=lampA)
    box(f'A_{nm}_arm', (x, 0.25, 1.4), (0.24, 1.0, 0.1), M['brass'], bevel=0.02)
    STAMPS[nm] = box(f'A_{nm}_stamp', (x, -0.05, 1.27), (0.34, 0.34, 0.2), M['stamp'], bevel=0.03)
board = box('board', (2.0, 2.4, 3.5), (4.4, 0.2, 1.0), M['panel'], bevel=0.03)
box('boardframe', (2.0, 2.46, 3.5), (4.6, 0.14, 1.2), M['brass'], bevel=0.02)
def btext(body, t0, t1, m=None, size=0.42):
    o = text(f'bt_{body}', body, (2.0, 2.28, 3.5), size, m or M['warm']); vis(o, t0, t1, pop=0.08); return o

# ---------- order slips ----------
def card(n, loc, tab=None):
    c = box(f'card{n}', loc, (0.9, 0.06, 0.24), M['paper'], bevel=0.01)
    box(f'card{n}_tab', (0.32, -0.008, 0), (0.16, 0.07, 0.17), tab or random.choice([M['coral'], M['slate']]), c, 0.01)
    text(f'card{n}_t', f'#{1000 + n}', (-0.17, -0.038, 0.035), 0.11, M['ink'], c, extrude=0.002)
    for j in range(2): box(f'card{n}_l{j}', (-0.13, -0.032, -0.05 - j * 0.04), (0.42 - j * 0.12, 0.004, 0.018), M['line'], c, 0)
    return c

# hook: order service hands the slip straight to payment, and the user waits for the stamp
a_words = [W('payment')]
c0 = card(0, (0, -0.05, 0.92), tab=M['coral'])
vis(c0, 0.2, None)
pts = [(0.0, (-0.6, -0.05, 0.92)), (0.6, (0, -0.05, 0.92))]
for (nm, x), tw in zip(CHAIN[1:], a_words):
    pts += [(tw - 0.2, (x, -0.05, 0.92)), (tw + 0.2, (x, -0.05, 0.92))]
keys(c0, 'location', pts)
t_wait = L(0, 1); t_ok = W('done', t_wait)
keys(STAMPS['PAYMENT'], 'location', [(t_ok - 0.3, (3, -0.05, 1.27)), (t_ok - 0.05, (3, -0.05, 1.14)), (t_ok + 0.25, (3, -0.05, 1.27))])
btext('PLEASE WAIT . . .', t_wait, L(1, 0))
t_hits = W('hits'); t_down = W('down', L(1, 1))
btext('TRAFFIC: 100', L(1, 0), t_hits)
btext('TRAFFIC: 1,000,000', t_hits, t_down, M['alert'], 0.36)
btext('APP DOWN', t_down, L(2, 0) + 1.0, M['alert'], size=0.6)
t_pile = L(1, 1)
for i in range(46):
    t = t_pile + i * 0.075
    c = card(100 + i, (0, -0.05, 0.92))
    rest = (random.uniform(0.6, 2.6), random.uniform(-0.45, 0.35), 0.82 + min(i, 40) * 0.016 + random.uniform(0, 0.25))
    vis(c, t, None, pop=0.05)
    keys(c, 'location', [(t, (0, -0.05, 1.1)), (t + 0.45, rest)])
    keys(c, 'rotation_euler', [(t, (0, 0, 0)), (t + 0.45, (random.uniform(-0.5, 0.5), random.uniform(-0.6, 0.6), random.uniform(-0.9, 0.9)))])
alarm = point('alarm', (1.6, -1.2, 4.6), 0, '#FF1E27', 0.3, kind='SPOT')
alarm.data.spot_size = math.radians(70); alarm.rotation_euler = (math.radians(15), 0, 0)
apts = [(0, 0)]; t = t_pile
while t < L(2, 0): apts += [(t, 2500), (t + 0.25, 0)]; t += 0.5
keys(alarm.data, 'energy', apts, 'CONSTANT')
emit_keys(lampA, [(0, 5), (t_down, 0)])
lampA.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = hx('#2ECC71')
keys(KEY_A[0].data, 'energy', [(0, 1400), (t_down, 1400), (t_down + 0.4, 400)])

# ---------- area B: the queue ----------
TX, PX, RX = 30.0, 28.0, 31.9
t_mq = W('message', L(2, 0))
tower = empty('tower', (TX, 0, 12))
box('tw_base', (0, 0, 0.12), (1.6, 0.8, 0.24), M['trim'], tower, 0.03)
for dx in (-0.65, 0.65):
    for dy in (-0.3, 0.3): box(f'tw_col{dx}{dy}', (dx, dy, 2.75), (0.08, 0.08, 5.3), M['brass'], tower, 0.01)
box('tw_back', (0, 0.28, 2.75), (1.3, 0.04, 5.2), M['glow'], tower, 0)
box('tw_glass', (0, -0.32, 2.75), (1.3, 0.02, 5.2), M['glass'], tower, 0)
for zz in (1.35, 2.7, 4.05): box(f'tw_band{zz}', (0, -0.33, zz), (1.42, 0.04, 0.05), M['brass'], tower, 0.01)
for dx in (-0.6, 0.6): box(f'tw_glowedge{dx}', (dx, 0.25, 2.75), (0.025, 0.02, 5.1), M['edge'], tower, 0)
box('tw_hdr', (0, 0, 5.55), (1.9, 0.9, 0.55), M['panel'], tower, 0.03)
box('tw_hdrtrim', (0, 0, 5.25), (2.0, 1.0, 0.08), M['brass'], tower, 0.01)
text('tw_lbl', 'MESSAGE', (0, -0.46, 5.66), 0.2, M['cyan'], tower)
text('tw_lbl2', 'QUEUE', (0, -0.46, 5.44), 0.2, M['cyan'], tower)
text('tw_fifo', 'FIRST IN, FIRST OUT', (0, -0.42, 0.12), 0.09, M['ltext'], tower)
keys(tower, 'location', [(0, (TX, 0, 12)), (t_mq - 0.1, (TX, 0, 12)), (t_mq + 0.4, (TX, 0, -0.05)), (t_mq + 0.52, (TX, 0, 0.06)), (t_mq + 0.62, (TX, 0, 0))])
qglow = point('qglow', (TX, 0.0, 2.6), 0, '#38B6FF', 1.0)
keys(qglow.data, 'energy', [(0, 0), (t_mq + 0.4, 0), (t_mq + 0.9, 80)])

lampP = mat('lampP', '#2ECC71', 0.4, emit=5.0)
machine('B_ORDER', 'ORDER SERVICE', PX, y=0.0, lampmat=lampP, s=0.8)
t_recv = W('received')
sign = box('recv_plate', (PX, -0.1, 2.3), (1.5, 0.1, 0.34), M['panel'], bevel=0.03)
box('recv_rim', (0, 0.02, 0), (1.56, 0.08, 0.4), M['green'], sign, 0.03)
text('recv_txt', 'ORDER RECEIVED', (0, -0.06, 0), 0.15, M['green'], sign)
vis(sign, t_recv - 0.1, None)

# rack of workers next to the tower (stacked so the vertical frame holds them all)
CZ = [0.0, 1.75, 3.5]; S_W = 0.72
for zz in (1.68, 3.43): box(f'rack_shelf{zz}', (RX, 0.0, zz), (1.5, 1.0, 0.08), M['trim'], bevel=0.01)
for dx in (-0.72, 0.72): box(f'rack_post{dx}', (RX + dx, -0.42, 2.6), (0.07, 0.07, 5.2), M['brass'], bevel=0.01)
t_more = W('workers', L(5, 0)) - 0.3
LAMPC = [mat(f'lampC{k}', '#2ECC71', 0.4, emit=4.0) for k in range(3)]
for k, lbl in enumerate(['PAYMENT #1', 'PAYMENT #2', 'PAYMENT #3']):
    z = CZ[k] + (0.08 if k else 0)
    m = machine(f'B_C{k}', lbl, RX, y=0.0, z=z, lampmat=LAMPC[k], s=S_W)
    if k: keys(m, 'location', [(0, (RX, 0, z + 9)), (t_more + 0.25 * (k - 1), (RX, 0, z + 9)), (t_more + 0.25 * (k - 1) + 0.45, (RX, 0, z))])
whdr = box('wk_hdr', (RX, 0.0, 5.62), (1.9, 0.9, 0.5), M['panel'], bevel=0.03)
box('wk_hdrtrim', (0, 0, -0.29), (2.0, 1.0, 0.08), M['brass'], whdr, 0.01)
text('wk_lbl', 'PAYMENT', (0, -0.46, 0.1), 0.19, M['green'], whdr)
text('wk_lbl2', 'WORKERS', (0, -0.46, -0.11), 0.19, M['green'], whdr)
vis(whdr, W('worker', L(4, 0)) - 0.1, None)
ack = box('ack_plate', (RX + 1.05, -0.2, 0.95), (0.62, 0.08, 0.28), M['panel'], bevel=0.02)
box('ack_rim', (0, 0.02, 0), (0.68, 0.06, 0.34), M['green'], ack, 0.02)
text('ack_txt', 'DONE', (0, -0.05, 0), 0.15, M['green'], ack)
xmark = box('x_plate', (RX + 1.05, -0.2, CZ[1] + 0.9), (0.5, 0.08, 0.5), M['panel'], bevel=0.04)
text('x_txt', 'X', (0, -0.05, 0), 0.4, M['alert'], xmark)

for nm, x, tok in (('RabbitMQ', 29.5, 'rabbitmq'), ('Amazon SQS', 32.4, 'amazon')):
    p = box(f'plq_{nm}', (x, 0.6, 6.7), (2.6, 0.12, 0.72), M['panel'], bevel=0.03)
    box(f'plqf_{nm}', (0, 0.03, 0), (2.7, 0.1, 0.82), M['brass'], p, 0.02)
    text(f'plqt_{nm}', nm, (0, -0.07, 0), 0.38, M['warm'], p)
    vis(p, W(tok, L(7, 0)) - 0.1, None)

# queue simulation
SLOT = lambda i: (TX, -0.05, 0.42 + i * 0.3)
MOUTH = lambda k, d=0.85: (RX - d * S_W, -0.25, CZ[k] + 0.6)
LOC = defaultdict(dict); queue, ev, n = [], [], [200]
def push(t, kind, *a): heapq.heappush(ev, (t, len(ev), kind, a))
def last(c, t):
    ks = [k for k in LOC[c] if k <= t + 1e-6]; return LOC[c][max(ks)]
def relayout(t):
    for i, c in enumerate(queue): LOC[c][round(t, 3)] = last(c, t); LOC[c][round(t + 0.25, 3)] = SLOT(i)
GONE = {}
def enq(t): push(t, 'enq')
def deq(t, k, fail_at=None, back_at=None): push(t, 'deq', k, fail_at, back_at)
for t in (t_mq + 0.8, t_mq + 1.15, t_mq + 1.5): enq(t)
for i in range(4): enq(W('drops', L(3, 0)) - 0.2 + i * 0.5)
t = L(4, 0) + 0.4
while t < t_more + 1.0: deq(t, 0); t += 1.2
for i in range(13): enq(L(4, 1) + 0.15 + i * 0.25)
t = t_more + 0.8
while t < L(6, 0) - 0.3:
    for k in range(3): deq(t + k * 0.33, k)
    t += 1.0
for t in (t_more + 1.0, t_more + 1.8, t_more + 2.6): enq(t)
t_dies = W('dies', L(6, 0)); t_done = W('done', L(6, 0))
deq(L(6, 0) + 0.2, 1, fail_at=t_dies + 0.1, back_at=W('back', L(6, 1)) - 0.3)
deq(t_done - 1.1, 0)
vis(ack, t_done - 0.05, t_done + 1.6)
vis(xmark, t_dies + 0.1, L(7, 1))
LAMPC[1].node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = hx('#2ECC71')
flick = [(0, 4)]; t = t_dies + 0.1
while t < L(7, 1): flick += [(t, 0), (t + 0.12, 0)]; t += 0.6
flick.append((L(7, 1), 4)); emit_keys(LAMPC[1], flick)
dead = mat('dead', '#FF2A38', 0.4, emit=0.0)
t = L(7, 0) + 0.3
while t < END:
    enq(t); deq(t + 0.45, (0, 2, 1)[int(t * 10) % 3] if t > L(7, 1) else (0, 2)[int(t * 10) % 2]); t += 0.7

while ev:
    t, _, kind, a = heapq.heappop(ev)
    if kind == 'enq':
        c = card(n[0], (PX, 0, 2.3)); n[0] += 1
        vis(c, t, None, pop=0.06)
        LOC[c][round(t, 3)] = (PX + 0.4, -0.3, 1.5); LOC[c][round(t + 0.4, 3)] = (TX - 0.75, -0.5, 5.0)
        push(t + 0.75, 'arrive', c)
    elif kind == 'arrive':
        c = a[0]
        if len(queue) >= 16: GONE[c] = t; continue
        queue.append(c); LOC[c][round(t, 3)] = SLOT(len(queue) - 1)
    elif kind == 'deq':
        k, fail_at, back_at = a
        if not queue: continue
        c = queue.pop(0)
        LOC[c][round(t, 3)] = SLOT(0); LOC[c][round(t + 0.35, 3)] = MOUTH(k); LOC[c][round(t + 0.6, 3)] = MOUTH(k, 0.45)
        relayout(t)
        if fail_at:
            LOC[c][round(back_at, 3)] = MOUTH(k, 0.45); LOC[c][round(back_at + 0.35, 3)] = MOUTH(k, 1.4)
            push(back_at + 0.6, 'front', c)
        else:
            GONE[c] = t + 0.9
            if not (k == 1 and t_dies < t < L(7, 1)): emit_keys(LAMPC[k], [(t + 0.9, 15), (t + 1.15, 4)])
    elif kind == 'front':
        c = a[0]; queue.insert(0, c); relayout(t - 0.2)
for c, pts in LOC.items():
    for tt in sorted(pts): key(c, 'location', tt, pts[tt])
for c, tg in GONE.items(): keys(c, 'scale', [(tg - 0.1, (1, 1, 1)), (tg, TINY)])

# ---------- camera: frame by width, long lenses, subject lifted above the caption zone ----------
tgt = empty('tgt'); camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd)
col.objects.link(cam); sc.camera = cam
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
camd.dof.use_dof = True; camd.dof.focus_object = tgt; camd.dof.aperture_fstop = 4.0; camd.clip_end = 200
CUT = 1.0 / FPS
def place(c, width, lens, el, az, lift):
    d = width * lens / 20.25; vh = width * 36 / 20.25
    g = Vector(c) - Vector((0, 0, lift * vh))
    p = g + d * Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    return tuple(p), tuple(g)
SHOTS = [  # (t, centre, visible width, lens, elevation, azimuth, lift, cut)
    (0.0, (0.0, 0.5, 1.35), 2.6, 50, 8, -8, 0.1, False),
    (0.6, (0.1, 0.5, 1.35), 2.6, 50, 8, -8, 0.1, False),
    (a_words[0] - 0.2, (0.3, 0.5, 1.35), 2.6, 50, 8, -8, 0.1, False),
    (a_words[0] + 0.5, (2.9, 0.5, 1.4), 2.7, 50, 9, -6, 0.1, False),
    (t_wait - 0.05, (2.9, 0.5, 1.4), 2.7, 50, 9, -6, 0.1, False),
    (t_wait, (1.5, 0.6, 2.1), 5.0, 35, 14, 14, 0.06, True),
    (L(1, 0) - 0.1, (1.5, 0.6, 2.1), 4.8, 35, 14, 12, 0.06, False),
    (L(1, 0), (1.8, 1.2, 2.4), 4.8, 50, 9, 0, 0.08, True),
    (L(1, 1), (1.8, 1.1, 2.3), 4.6, 50, 9, 0, 0.08, False),
    (L(1, 1) + 0.7, (1.6, 0.4, 2.0), 3.6, 50, 14, 8, 0.0, False),
    (t_down, (1.6, 0.4, 2.0), 3.5, 50, 14, 8, 0.0, False),
    (t_down + 0.08, (1.68, 0.4, 2.06), 3.5, 50, 14, 8, 0.0, False),
    (t_down + 0.16, (1.52, 0.4, 1.95), 3.5, 50, 14, 8, 0.0, False),
    (t_down + 0.24, (1.6, 0.4, 2.0), 3.5, 50, 14, 8, 0.0, False),
    (L(2, 0) - 0.05, (1.6, 0.4, 2.0), 3.6, 50, 14, 8, 0.0, False),
    (L(2, 0) + 0.25, (30.2, 0.0, 2.2), 5.6, 50, 6, 0, 0.06, True),
    (t_mq + 0.5, (30.2, 0.0, 2.4), 5.4, 50, 6, 0, 0.06, False),
    (L(3, 0) - 0.1, (30.0, 0.0, 2.7), 4.8, 50, 6, 0, 0.06, False),
    (L(3, 0) + 0.4, (29.0, 0.0, 2.2), 4.0, 50, 8, -6, 0.08, False),
    (L(4, 0) - 0.1, (29.1, 0.0, 2.2), 4.0, 50, 8, -6, 0.08, False),
    (L(4, 0) + 0.4, (31.0, 0.0, 1.6), 3.8, 50, 8, 6, 0.08, False),
    (L(4, 1) - 0.1, (31.0, 0.0, 1.7), 3.8, 50, 8, 6, 0.08, False),
    (L(4, 1) + 0.6, (30.6, 0.0, 3.2), 3.7, 50, 6, 0, 0.06, False),
    (L(5, 0) - 0.1, (30.6, 0.0, 3.3), 3.7, 50, 6, 0, 0.06, False),
    (L(5, 0) + 0.5, (31.0, 0.0, 3.0), 4.7, 50, 6, 4, 0.06, False),
    (L(6, 0) - 0.1, (31.0, 0.0, 3.0), 4.7, 50, 6, 4, 0.06, False),
    (L(6, 0) + 0.5, (31.5, 0.0, 2.5), 3.2, 50, 6, 8, 0.06, False),
    (L(6, 1) - 0.1, (31.3, 0.0, 2.2), 3.3, 50, 6, 6, 0.06, False),
    (L(6, 1) + 0.5, (30.9, 0.0, 1.6), 3.4, 50, 6, 4, 0.08, False),
    (L(7, 0) - 0.1, (30.9, 0.0, 1.7), 3.4, 50, 6, 4, 0.08, False),
    (L(7, 0) + 0.6, (30.95, 0.3, 3.9), 6.2, 85, 4, 0, 0.0, False),
    (L(7, 1), (30.95, 0.3, 3.8), 6.2, 85, 4, 0, 0.0, False),
    (END, (30.95, 0.2, 3.6), 5.9, 85, 4, 0, 0.0, False),
]
for i in range(1, len(SHOTS)):
    a, b = SHOTS[i - 1], SHOTS[i]
    if not b[7] and (Vector(a[1]) - Vector(b[1])).length < 0.35 and abs(a[2] - b[2]) < 0.4:
        SHOTS[i] = (b[0], b[1], min(b[2], a[2]) * 0.93, *b[3:])
prev = None
for t, c, wd, lens, el, az, lift, cut in SHOTS:
    p, g = place(c, wd, lens, el, az, lift)
    if cut and prev:
        key(cam, 'location', t - CUT, prev[0]); key(tgt, 'location', t - CUT, prev[1]); key(camd, 'lens', t - CUT, prev[2], 'CONSTANT')
    key(cam, 'location', t, p); key(tgt, 'location', t, g); key(camd, 'lens', t, lens, 'CONSTANT')
    prev = (p, g, lens)

# ---------- render ----------
sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = SAMPLES
ee.use_shadows = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
ee.volumetric_tile_size = '8'; ee.volumetric_samples = 48; ee.volumetric_end = 60; ee.use_volumetric_shadows = True
sc.render.resolution_x, sc.render.resolution_y = RES, int(RES * 16 / 9) // 2 * 2
sc.render.resolution_percentage = 100; sc.render.fps = FPS
a, b = [int(x) for x in opt('--range', f'1,{F(END)}').split(',')]
sc.frame_start, sc.frame_end = a, b
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new('CompositorNodeRLayers'); gl = ng.nodes.new('CompositorNodeGlare'); go = ng.nodes.new('NodeGroupOutput')
gl.inputs['Type'].default_value = 'Bloom'; gl.inputs['Threshold'].default_value = 1.0; gl.inputs['Size'].default_value = 0.6; gl.inputs['Strength'].default_value = 0.6
ng.links.new(rl.outputs['Image'], gl.inputs['Image']); ng.links.new(gl.outputs['Image'], go.inputs[0])
if STILLS:
    for s in STILLS:
        sc.frame_set(F(s)); sc.render.filepath = f'{OUT}/still_{s:05.2f}.png'; bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = f'{OUT}/f_'; bpy.ops.render.render(animation=True)
