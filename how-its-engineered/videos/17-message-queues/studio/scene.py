# 17 Message Queues, "studio" version: one dark stage, the flow runs down the screen.
# Phone (you) -> ORDER pod -> [direct cable | glass message queue] -> PAYMENT worker pods. Holographic chips for status.
# Timed to voice/words.json next to this file; the bottom fifth of the frame is kept clear for captions.
# usage: blender -b -P videos/17-message-queues/studio/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 24] [--stills 3,20] [--range a,b]
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
random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection
prefs = bpy.context.preferences.edit
FONT = bpy.data.fonts.load(os.path.join(os.environ.get('FONT_DIR', '/System/Library/Fonts/Supplemental'), 'DIN Alternate Bold.ttf'))

def hx(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

GLOW = 0.3  # global multiplier on every emissive strength
AMBER, VIOLET, CYAN, GREEN, RED, WHITE = '#FFB020', '#8C7BFF', '#26B8FF', '#22D38A', '#FF3B4E', '#FFFFFF'

# ---------- materials ----------
def mat(name, h, rough=0.5, metal=0.0, emit=0.0, alpha=1.0, eh=None, coat=0.0):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = hx(h); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.08
    if emit: b.inputs['Emission Color'].default_value = hx(eh or h); b.inputs['Emission Strength'].default_value = emit * GLOW
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.surface_render_method = 'BLENDED'
    return m
M = dict(
    ceramic=mat('ceramic', '#E8EBF1', 0.32, coat=0.35), plinth=mat('plinth', '#151B28', 0.45, 0.3), glassblk=mat('glassblk', '#05080F', 0.12),
    hatch=mat('hatch', '#0B0F18', 0.3), floor=mat('floor', '#0A0E16', 0.6), paper=mat('paper', '#F5F6F8', 0.4, coat=0.2),
    ink=mat('ink', '#1A2130', 0.5), white=mat('white', WHITE, 0.4, emit=2.2), phone=mat('phone', '#1A202D', 0.28, 0.7),
    screen=mat('screen', '#070B14', 0.2, emit=0.4, eh='#0C1424'), card=mat('card', '#1C2436', 0.4, emit=0.6, eh='#1C2436'),
    grey=mat('grey', '#8A93A6', 0.4, emit=1.2), chipbg=mat('chipbg', '#0A1120', 0.25, alpha=0.88), lane=mat('lane', '#0B1220', 0.15),
    glass=mat('glass', '#BFE6FF', 0.05, alpha=0.12), dark=mat('dark', '#06080D', 0.6),
    amber=mat('amber', AMBER, 0.4, emit=2.5), violet=mat('violet', VIOLET, 0.4, emit=3.0), cyan=mat('cyan', CYAN, 0.4, emit=3.0),
    green=mat('green', GREEN, 0.4, emit=3.0), red=mat('red', RED, 0.4, emit=4.0), btn=mat('btn', AMBER, 0.35, emit=1.6),
)
for nm, h in (('t_amber', AMBER), ('t_violet', VIOLET), ('t_cyan', CYAN), ('t_green', GREEN), ('t_red', RED), ('t_grey', '#8A93A6')):
    M[nm] = mat(nm, h, 0.4, emit=5.0)  # chip / screen text

# ---------- builders ----------
def link(ob, m, parent=None, bevel=0.0):
    col.objects.link(ob); ob.data.materials.append(m)
    if parent: ob.parent = parent
    if ob.type == 'MESH':
        ob.data.shade_smooth()
        if bevel:
            bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'; ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return ob
def rbox(name, loc, size, m, parent=None, r=0.0, axis=2, bevel=0.015):
    """box with the edges along `axis` rounded to radius r (pill / rounded-rect prisms)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if r > 0:
        es = [e for e in bm.edges if abs((e.verts[0].co - e.verts[1].co)[axis]) > 1e-6]
        bmesh.ops.bevel(bm, geom=es, offset=r, segments=8, profile=0.5, affect='EDGES', clamp_overlap=True)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent, bevel)
def cyl(name, loc, r, h, m, parent=None, seg=32):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent)
def sphere(name, loc, r, m, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent)
def torus(name, loc, R, r, m, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    segs, rs = 48, 10
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs; ring = []
        for j in range(rs):
            b = 2 * math.pi * j / rs
            ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), r * math.sin(b), (R + r * math.cos(b)) * math.sin(a))))
        rings.append(ring)
    for i in range(segs):
        for j in range(rs):
            bm.faces.new((rings[i][j], rings[(i + 1) % segs][j], rings[(i + 1) % segs][(j + 1) % rs], rings[i][(j + 1) % rs]))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, parent)
def text(name, body, loc, size, m, parent=None, extrude=0.003, flat=False):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = extrude
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = (0, 0, 0) if flat else (math.pi / 2, 0, 0); return link(ob, m, parent)
def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None); ob.location = loc; ob.rotation_euler = rot; col.objects.link(ob)
    if parent: ob.parent = parent
    return ob
def area(name, loc, aim, size, power, h, sx=None):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = power; ld.color = hx(h)[:3]
    if sx: ld.shape = 'RECTANGLE'; ld.size = sx; ld.size_y = size
    else: ld.size = size
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
def vis(ob, on, off=None, pop=0.18, s=(1, 1, 1), over=1.12):
    """scale-pop in (with a little overshoot) and optionally out."""
    so = tuple(v * over for v in s)
    pts = [(0, TINY), (max(on - 0.001, 0), TINY), (on + pop * 0.6, so), (on + pop, s)]
    if off is not None: pts += [(off - 0.12, s), (off, TINY)]
    keys(ob, 'scale', pts)
def sock(m, name): return m.node_tree.nodes.get('Principled BSDF').inputs[name]
def emit_keys(m, pts, interp='CONSTANT'):
    b = sock(m, 'Emission Strength')
    for t, v in sorted(pts):
        prefs.keyframe_new_interpolation_type = interp; b.default_value = v * GLOW; b.keyframe_insert('default_value', frame=F(t))
def color_keys(m, pts):
    b = sock(m, 'Emission Color')
    for t, h in sorted(pts):
        prefs.keyframe_new_interpolation_type = 'CONSTANT'; b.default_value = hx(h); b.keyframe_insert('default_value', frame=F(t))

# ---------- stage ----------
nt = M['floor'].node_tree; fb = nt.nodes['Principled BSDF']
br = nt.nodes.new('ShaderNodeTexBrick'); tcn = nt.nodes.new('ShaderNodeTexCoord')
br.offset = 0.0; br.squash = 1.0
br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.012; br.inputs['Mortar Smooth'].default_value = 0.3
br.inputs['Brick Width'].default_value = 1.0; br.inputs['Row Height'].default_value = 1.0
br.inputs['Color1'].default_value = hx('#0A0E16'); br.inputs['Color2'].default_value = hx('#0B1018'); br.inputs['Mortar'].default_value = hx('#1A2436')
nt.links.new(tcn.outputs['Object'], br.inputs['Vector']); nt.links.new(br.outputs['Color'], fb.inputs['Base Color'])
fl = rbox('floor', (0, 4, -0.05), (80, 80, 0.1), M['floor'], bevel=0)
w = bpy.data.worlds.new('w'); sc.world = w
try: w.use_nodes = True
except Exception: pass
w.node_tree.nodes['Background'].inputs['Color'].default_value = hx('#04060B'); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
vs = w.node_tree.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Density'].default_value = 0.0015; vs.inputs['Anisotropy'].default_value = 0.4
w.node_tree.links.new(vs.outputs['Volume'], w.node_tree.nodes['World Output'].inputs['Volume'])

CEN = Vector((0, 3.8, 0.6))
TOP = area('top', (0, 3.5, 11), (0, 3.5, 0), 9.0, 2600, '#EEF3FF')
KEYL = area('key', (-6.5, -5.5, 7.5), CEN, 5.0, 1700, '#FFF1E0')
area('rimC', (-7, 12, 4.5), CEN, 6.0, 650, CYAN)
area('rimV', (7, 12, 4.5), CEN, 6.0, 650, VIOLET)
area('fill', (6.5, -4, 3), CEN, 5.0, 450, '#9DB8FF')

# ---------- service pods ----------
def pod(name, label, sub, x, y, accent, z=0.0):
    root = empty(name, (x, y, z))
    band = mat(f'{name}_band', accent, 0.4, emit=3.0)
    rbox(f'{name}_plinth', (0, 0, 0.05), (1.75, 1.55, 0.1), M['plinth'], root, r=0.34)
    rbox(f'{name}_body', (0, 0, 0.8), (1.5, 1.3, 1.4), M['ceramic'], root, r=0.3, bevel=0.06)
    rbox(f'{name}_band', (0, 0, 0.3), (1.53, 1.33, 0.05), band, root, r=0.31, bevel=0)
    rbox(f'{name}_hatch', (0, 0.05, 1.505), (0.72, 0.5, 0.02), M['hatch'], root, r=0.1, bevel=0)
    rbox(f'{name}_hrim', (0, 0.05, 1.5), (0.8, 0.58, 0.02), band, root, r=0.13, bevel=0)
    rbox(f'{name}_scr', (0, -0.655, 0.93), (1.16, 0.03, 0.64), M['glassblk'], root, r=0.1, axis=1, bevel=0.008)
    text(f'{name}_lbl', label, (0, -0.675, 1.02), 0.19, M['white'], root)
    subs = []
    for i, (s_txt, s_m) in enumerate(sub):
        o = text(f'{name}_sub{i}', s_txt, (0, -0.675, 0.82), 0.085, s_m, root); subs.append(o)
    sphere(f'{name}_led', (0.56, -0.48, 1.5), 0.045, band, root)
    pl = point(f'{name}_pool', (x, y - 1.0, 0.18), 5, accent, 0.4)
    return root, band, subs, pl

PHONE = Vector((-2.05, 7.0, 1.3))
OX, OY = 0.0, 7.0
o_root, o_band, o_subs, o_pool = pod('ORDER', 'ORDER', [('SERVICE', M['t_amber'])], OX, OY, AMBER)
WP = [(0.0, 0.55), (-2.05, 0.85), (2.05, 0.85)]
WT = [W('more') - 0.15, W('workers') - 0.1]
workers = []
for k, (wx, wy) in enumerate(WP):
    subs = [('SERVICE', M['t_violet']), (f'WORKER {k + 1}', M['t_violet'])] if k == 0 else [(f'WORKER {k + 1}', M['t_violet'])]
    workers.append(pod(f'W{k}', 'PAYMENT', subs, wx, wy, VIOLET))
p_root, p_band, p_subs, p_pool = workers[0]
t_worker = W('worker', L(4, 0))
vis(p_subs[0], 0, t_worker, pop=0.01, over=1.0); vis(p_subs[1], t_worker + 0.02)
for k in (1, 2):
    r = workers[k][0]; wx, wy = WP[k]; t0 = WT[k - 1]
    keys(r, 'location', [(0, (wx, wy, 9)), (t0, (wx, wy, 9)), (t0 + 0.32, (wx, wy, -0.06)), (t0 + 0.42, (wx, wy, 0.05)), (t0 + 0.52, (wx, wy, 0))])
    keys(workers[k][3].data, 'energy', [(0, 0), (t0 + 0.3, 0), (t0 + 0.32, 5)], 'CONSTANT')
    emit_keys(workers[k][1], [(0, 3), (t0 + 0.25, 3), (t0 + 0.3, 12), (t0 + 0.7, 3)], 'BEZIER')

# payment load meter (on its screen)
rbox('load_bg', (0, -0.675, 0.69), (0.8, 0.008, 0.05), M['card'], p_root, r=0.024, axis=1, bevel=0)
lf = empty('load_anchor', (-0.4, -0.68, 0.69), p_root)
lmat = mat('loadfill', VIOLET, 0.4, emit=4.0)
lfill = rbox('load_fill', (0.4, 0, 0), (0.8, 0.008, 0.05), lmat, lf, r=0.024, axis=1, bevel=0)

# ---------- phone (you) ----------
ph = empty('phone', PHONE, rot=(math.radians(-14), 0, math.radians(-12)))
rbox('ph_body', (0, 0, 0), (0.76, 0.07, 1.48), M['phone'], ph, r=0.12, axis=1, bevel=0.02)
rbox('ph_scr', (0, -0.036, 0), (0.68, 0.005, 1.4), M['screen'], ph, r=0.09, axis=1, bevel=0)
rbox('ph_notch', (0, -0.04, 0.63), (0.18, 0.004, 0.045), M['dark'], ph, r=0.022, axis=1, bevel=0)
SY = -0.042
def ui(name): return empty(name, (0, 0, 0), ph)
s0 = ui('ui_checkout')
text('u0_t', 'CHECKOUT', (0, SY, 0.5), 0.075, M['t_grey'], s0)
rbox('u0_card', (0, SY + 0.002, 0.16), (0.56, 0.004, 0.44), M['card'], s0, r=0.05, axis=1, bevel=0)
rbox('u0_img', (0, SY - 0.001, 0.24), (0.3, 0.004, 0.2), M['amber'], s0, r=0.04, axis=1, bevel=0)
text('u0_p', 'SNEAKERS', (0, SY - 0.002, 0.07), 0.06, M['white'], s0)
text('u0_pr', '$89', (0, SY - 0.002, -0.0), 0.075, M['t_amber'], s0)
btn = empty('u0_btn', (0, SY - 0.002, -0.38), s0)
rbox('u0_b', (0, 0, 0), (0.54, 0.004, 0.15), M['btn'], btn, r=0.074, axis=1, bevel=0)
text('u0_bt', 'BUY NOW', (0, -0.003, 0), 0.07, M['ink'], btn)
s1 = ui('ui_wait')
spin = empty('u1_spin', (0, SY, 0.12), s1)
for i in range(10):
    a = 2 * math.pi * i / 10
    sphere(f'u1_d{i}', (0.13 * math.cos(a), 0, 0.13 * math.sin(a)), 0.012 + 0.0025 * i, M['white'] if i > 4 else M['grey'], spin)
text('u1_t', 'PROCESSING', (0, SY, -0.14), 0.065, M['white'], s1)
text('u1_t2', 'please wait...', (0, SY, -0.24), 0.05, M['t_grey'], s1)
s2 = ui('ui_error')
torus('u2_ring', (0, SY, 0.14), 0.13, 0.016, M['red'], s2)
text('u2_x', '!', (0, SY, 0.14), 0.16, M['t_red'], s2)
text('u2_t', 'ERROR 503', (0, SY, -0.12), 0.075, M['t_red'], s2)
text('u2_t2', 'try again later', (0, SY, -0.22), 0.05, M['t_grey'], s2)
s3 = ui('ui_ok')
torus('u3_ring', (0, SY, 0.16), 0.13, 0.016, M['green'], s3)
text('u3_ok', 'OK', (0, SY, 0.16), 0.1, M['t_green'], s3)
text('u3_t', 'ORDER', (0, SY, -0.08), 0.075, M['t_green'], s3)
text('u3_t1', 'RECEIVED', (0, SY, -0.17), 0.075, M['t_green'], s3)
text('u3_t2', '#1042', (0, SY, -0.27), 0.05, M['t_grey'], s3)

t_buy, t_pay, t_wait = W('buy'), W('payment'), W('wait')
t_slow, t_pile, t_crash = W('slows'), W('pile'), W('crashes')
t_fix, t_mq = L(2, 0), W('message', L(2, 0))
t_drop, t_recv = W('drops'), W('received')
vis(s0, 0, t_buy + 0.28, pop=0.01, over=1.0)
keys(btn, 'scale', [(t_buy - 0.06, (1, 1, 1)), (t_buy + 0.04, (0.88, 1, 0.82)), (t_buy + 0.2, (1, 1, 1))])
vis(s1, t_buy + 0.3, t_crash)
keys(spin, 'rotation_euler', [(0, (0, 0, 0)), (END, (0, -2 * math.pi * END * 1.4, 0))], 'LINEAR')
vis(s2, t_crash + 0.02, t_fix + 0.5)
keys(s0, 'scale', [(t_fix + 0.5, TINY), (t_fix + 0.62, (1.08,) * 3), (t_fix + 0.7, (1, 1, 1)), (t_recv - 0.12, (1, 1, 1)), (t_recv, TINY)])
keys(btn, 'scale', [(t_drop - 0.5, (1, 1, 1)), (t_drop - 0.4, (0.88, 1, 0.82)), (t_drop - 0.25, (1, 1, 1))])
vis(s3, t_recv + 0.02, None)
keys(ph, 'location', [(t, PHONE + Vector((0, 0, 0.05 * math.sin(t * 1.7)))) for t in [i * 0.5 for i in range(int(END * 2) + 2)]])

# ---------- chips (holographic status tags) ----------
CHIP_TILT = math.radians(-18)
CUT_ = 1.0 / FPS
def chip(name, body, loc, colname, size=0.2, az=0.0):
    root = empty(name, loc, rot=(CHIP_TILT, 0, math.radians(az)))
    t = text(f'{name}_t', body, (0, -0.035, 0), size, M[f't_{colname}'], root)
    bpy.context.view_layer.update()
    wd, h = t.dimensions.x + size * 1.3, size * 1.75
    rbox(f'{name}_bg', (0, 0, 0), (wd, 0.03, h), M['chipbg'], root, r=h / 2 * 0.98, axis=1, bevel=0)
    rbox(f'{name}_rim', (0, 0.012, 0), (wd + 0.035, 0.02, h + 0.035), M[colname], root, r=(h + 0.035) / 2 * 0.98, axis=1, bevel=0)
    return root

# ---------- order tiles ----------
NT = [0]
def tile(stripe=None):
    n = NT[0]; NT[0] += 1
    c = rbox(f'tile{n}', (0, 0, -5), (0.5, 0.3, 0.06), M['paper'], r=0.06, bevel=0.012)
    rbox(f'tile{n}_s', (-0.19, 0, 0.004), (0.07, 0.24, 0.06), stripe or M['amber'], c, r=0.03, bevel=0)
    text(f'tile{n}_t', f'#{1000 + n}', (0.05, 0, 0.032), 0.085, M['ink'], c, extrude=0.002, flat=True)
    return c
O_OUT = Vector((OX, OY - 0.75, 0.8))            # mouth on the order pod's front
HOVER = lambda k: Vector((WP[k][0], WP[k][1] + 0.05, 2.05))
SINK = lambda k: Vector((WP[k][0], WP[k][1] + 0.05, 1.45))

# ---------- part 1: direct call, then the pile-up ----------
cable = empty('cable', (0, 3.8, 0.25))
cb = cyl('cable_c', (0, 0, 0), 0.04, 5.0, M['violet'], cable); cb.rotation_euler = (math.pi / 2, 0, 0)
for yy in (-2.2, 0, 2.2): cyl(f'cable_post{yy}', (0, yy, -0.12), 0.05, 0.25, M['plinth'], cable)
keys(cable, 'scale', [(0, (1, 1, 1)), (t_fix + 0.05, (1, 1, 1)), (t_fix + 0.35, (1, 0.001, 1))])

c0 = tile()
keys(c0, 'location', [(0, O_OUT), (t_pay - 0.55, O_OUT), (t_pay - 0.35, (0, 6.0, 0.36)), (t_pay + 0.45, (0, 1.6, 0.36)),
                      (t_pay + 0.75, HOVER(0)), (t_wait + 0.5, HOVER(0)), (t_wait + 0.8, SINK(0))])
keys(c0, 'scale', [(0, TINY), (t_pay - 0.56, TINY), (t_pay - 0.4, (1, 1, 1)), (t_wait + 0.7, (1, 1, 1)), (t_wait + 0.82, TINY)])
keys(c0, 'rotation_euler', [(t_pay + 0.45, (0, 0, 0)), (t_pay + 0.75, (1.15, 0, 0)), (t_wait + 0.6, (1.15, 0, 0)), (t_wait + 0.8, (0, 0, 0))])

PILE = []
t_bf = L(1, 0)
for i in range(44):
    c = tile(); t0 = t_bf + 0.15 + i * 0.066
    yrest = 1.75 + i * 0.085 + random.uniform(-0.25, 0.25)
    rest = (random.uniform(-0.75, 0.75), min(yrest, 6.0), 0.05 + random.uniform(0, 0.28) + (0.12 if i > 25 else 0))
    dur = 0.25 + (6.0 - rest[1]) * 0.06
    keys(c, 'location', [(t0, O_OUT), (t0 + 0.12, (0, 6.0, 0.4)), (t0 + 0.12 + dur, (rest[0] * 0.4, rest[1] + 0.3, 0.45)), (t0 + 0.25 + dur, rest)])
    keys(c, 'rotation_euler', [(t0 + 0.12 + dur, (0, 0, 0)), (t0 + 0.3 + dur, (random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25), random.uniform(-1.2, 1.2)))])
    tg = t_fix + 0.05 + (rest[1] - 1.7) * 0.06
    keys(c, 'scale', [(0, TINY), (t0 - 0.001, TINY), (t0 + 0.08, (1, 1, 1)), (tg, (1, 1, 1)), (tg + 0.15, TINY)])
    PILE.append(c)
# overload: load meter fills, payment goes amber then red, the whole app goes down
keys(lf, 'scale', [(0, (0.15, 1, 1)), (t_pay + 0.75, (0.15, 1, 1)), (t_pay + 1.0, (0.55, 1, 1)), (t_wait + 0.8, (0.2, 1, 1)),
                   (t_bf + 0.3, (0.3, 1, 1)), (t_slow + 0.3, (0.75, 1, 1)), (t_crash, (1, 1, 1)), (t_fix + 0.4, (1, 1, 1)), (t_fix + 0.8, (0.2, 1, 1))])
color_keys(lmat, [(0, VIOLET), (t_slow, AMBER), (t_crash, RED), (t_fix + 0.5, VIOLET)])
color_keys(p_band, [(0, VIOLET), (t_slow, AMBER), (t_crash, RED), (t_fix + 0.5, VIOLET)])
color_keys(o_band, [(0, AMBER), (t_crash, RED), (t_fix + 0.5, AMBER)])
color_keys(M['violet'], [(0, VIOLET), (t_crash, RED), (t_fix + 0.5, VIOLET)])
fl_pts = [(0, 3)]; t = t_crash
while t < t_fix + 0.3: fl_pts += [(t, 6), (t + 0.18, 0.6)]; t += 0.36
emit_keys(p_band, fl_pts + [(t_fix + 0.5, 3)]); emit_keys(o_band, fl_pts + [(t_fix + 0.5, 3)])
for pl, h in ((p_pool, VIOLET), (o_pool, AMBER)):
    keys(pl.data, 'color', [(0, hx(h)[:3]), (t_crash, hx(RED)[:3]), (t_fix + 0.5, hx(h)[:3])], 'CONSTANT')
alarm = point('alarm', (0, 3.6, 5.5), 0, RED, 0.5, kind='SPOT')
alarm.data.spot_size = math.radians(80)
apts = [(0, 0)]; t = t_crash
while t < t_fix + 0.2: apts += [(t, 1400), (t + 0.2, 200)]; t += 0.4
apts.append((t_fix + 0.25, 0)); keys(alarm.data, 'energy', apts, 'CONSTANT')
keys(TOP.data, 'energy', [(0, 2600), (t_crash - 0.01, 2600), (t_crash, 1600), (t_fix + 0.3, 1600), (t_fix + 0.5, 2600)], 'CONSTANT')
down = chip('chip_down', 'APP DOWN', (0, 3.9, 2.25), 'red', 0.42)
vis(down, t_crash, t_fix + 0.3, pop=0.22, over=1.25)
over = chip('chip_over', 'OVERLOADED', (0, 0.4, 2.45), 'amber', 0.16)
vis(over, t_slow + 0.1, t_crash)

# ---------- part 2: the queue drops in between ----------
lane = empty('lane', (0, 0, 6))
LY0, LY1 = 1.95, 6.15                        # head (near payment) .. tail (near order)
LC, LLEN = (LY0 + LY1) / 2, LY1 - LY0
rbox('lane_base', (0, LC, 0.07), (1.05, LLEN + 0.2, 0.14), M['lane'], lane, r=0.12, bevel=0.02)
lstrip = mat('lane_strip', CYAN, 0.4, emit=0.7)
rbox('lane_glow', (0, LC, 0.142), (0.82, LLEN, 0.006), lstrip, lane, r=0.05, bevel=0)
for sx in (-0.5, 0.5):
    rbox(f'lane_wall{sx}', (sx, LC, 0.25), (0.035, LLEN + 0.2, 0.3), M['glass'], lane, bevel=0)
    rbox(f'lane_edge{sx}', (sx, LC, 0.405), (0.04, LLEN + 0.2, 0.012), M['cyan'], lane, bevel=0)
for i in range(9):  # direction chevrons on the lane floor
    for s in (-1, 1):
        o = rbox(f'chev{i}{s}', (s * 0.07, LY0 + 0.2 + i * 0.47, 0.147), (0.16, 0.025, 0.004), M['cyan'], lane, bevel=0)
        o.rotation_euler = (0, 0, s * math.radians(35))
keys(lane, 'location', [(0, (0, 0, 6)), (t_mq - 0.12, (0, 0, 6)), (t_mq + 0.22, (0, 0, -0.04)), (t_mq + 0.32, (0, 0, 0.03)), (t_mq + 0.42, (0, 0, 0))])
emit_keys(lstrip, [(0, 0.7), (t_mq + 0.1, 0.7), (t_mq + 0.2, 8), (t_mq + 0.7, 0.7)], 'BEZIER')
qlight = point('qlight', (0, LC, 0.8), 0, CYAN, 1.5)
keys(qlight.data, 'energy', [(0, 0), (t_mq + 0.2, 0), (t_mq + 0.3, 300), (t_mq + 0.8, 60)])
mq = chip('chip_mq', 'MESSAGE QUEUE', (1.55, LC + 0.2, 0.75), 'cyan', 0.19)
vis(mq, t_mq + 0.35, None, pop=0.22, over=1.2)
for a_, b_ in ((L(4, 0), L(4, 1)), (L(6, 0), L(7, 0))):   # hidden in the close shots, where it would sit on the frame edge
    keys(mq, 'scale', [(a_ - CUT_, (1, 1, 1)), (a_, TINY), (b_ - CUT_, TINY), (b_, (1, 1, 1))], 'CONSTANT')
recv = chip('chip_recv', 'ORDER RECEIVED', (0, OY - 0.3, 2.15), 'green', 0.15)
vis(recv, t_recv, L(4, 0) + 0.3)
for nm, x, tok in (('RabbitMQ', -1.15, 'rabbitmq'), ('Amazon SQS', 1.25, 'amazon')):
    c = chip(f'chip_{nm}', nm, (x * 1.2, 4.2, 2.6), 'amber', 0.32)
    vis(c, W(tok, L(7, 0)) - 0.12, None, pop=0.22, over=1.2)
crash = chip('chip_crash', 'CRASHED', (WP[1][0], WP[1][1], 2.75), 'red', 0.16)
done = chip('chip_done', 'DONE', (WP[2][0], WP[2][1], 2.6), 'green', 0.18)
t_dies, t_done, t_back = W('dies', L(6, 0)), W('done', L(6, 0)), W('back', L(6, 1))
t_rec = L(7, 0) + 0.3
vis(crash, t_dies, t_rec)
vis(done, t_done - 0.05, t_done + 1.3, over=1.25)
w1band = workers[1][1]
flick = [(0, 3)]; t = t_dies
while t < t_rec: flick += [(t, 6), (t + 0.1, 0.3), (t + 0.22, 4), (t + 0.3, 0.3)]; t += 0.7
emit_keys(w1band, flick + [(t_rec, 3)])
color_keys(w1band, [(0, VIOLET), (t_dies, RED), (t_rec, VIOLET)])
w1pool = workers[1][3]
keys(w1pool.data, 'color', [(0, hx(VIOLET)[:3]), (t_dies, hx(RED)[:3]), (t_rec, hx(VIOLET)[:3])], 'CONSTANT')
ackmat = [workers[k][1] for k in range(3)]

# queue simulation: tiles enter from the order pod, wait in line, get pulled by free workers
SLOT = lambda i: Vector((0, LY0 + 0.12 + i * 0.4, 0.2))
CAP = 10
LOC = defaultdict(dict); ROT = defaultdict(dict); GONE = {}; BORN = {}
def at(c, t):
    ks = sorted(LOC[c]);
    if t <= ks[0]: return LOC[c][ks[0]]
    for a, b in zip(ks, ks[1:]):
        if a <= t <= b: return LOC[c][a].lerp(LOC[c][b], (t - a) / (b - a) if b > a else 1)
    return LOC[c][ks[-1]]
def path(c, t, pts):
    """replace c's motion after t with pts [(t, loc)]."""
    for k_ in [k_ for k_ in LOC[c] if k_ > t + 1e-6]: del LOC[c][k_]
    LOC[c][round(t, 3)] = at(c, t)
    for tt, p in pts: LOC[c][round(tt, 3)] = Vector(p)
queue, inflight, ev = [], [0], []
def push(t, kind, *a): heapq.heappush(ev, (t, len(ev), kind, a))
def relayout(t):
    for i, c in enumerate(queue): path(c, t, [(t + 0.22, SLOT(i))])
def enq(t, stripe=None): push(t, 'enq', stripe)
WORK = defaultdict(list)                     # worker k -> [(start, end)] windows when it pulls normally
FORCE = []                                   # (t, k, mode) forced pulls: 'fail' holds the tile, 'done' finishes at a set time
PROC = 0.75
t_q0 = t_mq + 0.6
LOCK = {}
enq(t_q0); enq(t_q0 + 0.45); enq(t_q0 + 0.9)
enq(t_drop - 0.05)                           # your order
t = L(4, 0) + 0.6
while t < L(4, 1): enq(t); t += 1.25
t = L(4, 1) + 0.15
for i in range(14): enq(t + i * 0.16)
t = L(4, 1) + 2.6
while t < L(6, 0) + 0.5: enq(t); t += 0.55
t = L(6, 0) + 0.5
while t < L(7, 0): enq(t); t += 0.8
t = L(7, 0)
while t < END: enq(t); t += 0.42
WORK[0] = [(L(4, 0) + 0.25, END)]
WORK[1] = [(WT[0] + 0.55, t_dies - 2.3), (t_rec + 0.4, END)]
WORK[2] = [(WT[1] + 0.55, t_done - 3.4), (t_done + 0.35, END)]
FORCE += [(t_dies - 0.75, 1, 'fail'), (t_done - 0.5 - PROC - 0.05, 2, 'done')]
busy = [False] * 3
for k in range(3):
    for a, b in WORK[k]: push(a, 'try', k, b)
for tf, k, mode in FORCE: push(tf, 'force', k, mode)

def take(t, k, fail=False):
    c = queue.pop(0); relayout(t)
    p0 = at(c, t); mid = (p0 + HOVER(k)) / 2 + Vector((0, 0, 0.9))
    path(c, t, [(t + 0.25, mid), (t + 0.5, HOVER(k))])
    ROT[c][round(t, 3)] = (0, 0, 0); ROT[c][round(t + 0.5, 3)] = (1.15, 0, 0)
    busy[k] = True
    if fail: return c
    tdone = t + 0.5 + PROC
    path(c, tdone, [(tdone + 0.18, SINK(k))]); GONE[c] = tdone + 0.16; ROT[c][round(tdone, 3)] = (1.15, 0, 0); ROT[c][round(tdone + 0.15, 3)] = (0, 0, 0)
    emit_keys(ackmat[k], [(tdone, 3), (tdone + 0.12, 11), (tdone + 0.45, 3)], 'BEZIER')
    push(tdone + 0.2, 'free', k)
    return c
held = None
while ev:
    t, _, kind, a = heapq.heappop(ev)
    if kind == 'enq':
        if len(queue) + inflight[0] >= CAP: continue
        c = tile(a[0]); BORN[c] = t; inflight[0] += 1
        LOC[c][round(t, 3)] = O_OUT; LOC[c][round(t + 0.22, 3)] = Vector((0, LY1 - 0.1, 0.45))
        push(t + 0.22, 'arrive', c)
    elif kind == 'arrive':
        c = a[0]; inflight[0] -= 1; queue.append(c)
        d = (LY1 - 0.1) - SLOT(len(queue) - 1).y
        path(c, t, [(t + 0.12 + d * 0.09, SLOT(len(queue) - 1))])
    elif kind == 'try':
        k, until = a
        if t > until: continue
        if busy[k]: continue
        if queue and LOCK.get(queue[0], 0) <= t: take(t, k)
        else: push(t + 0.12, 'try', k, until)
    elif kind == 'free':
        k = a[0]; busy[k] = False
        for s_, e_ in WORK[k]:
            if s_ <= t <= e_: push(t + 0.1, 'try', k, e_)
    elif kind == 'force':
        k, mode = a
        if not queue: push(t + 0.1, 'force', k, mode); continue
        if mode == 'fail':
            held = take(t, k, fail=True)
        else:
            take(t, k)
    if held is not None and kind == 'force' and a[1] == 'fail':
        push(t_back - 0.25, 'return', held)
    if kind == 'return':
        c = a[0]; queue.insert(0, c); relayout(t)
        p0 = at(c, t); mid = (p0 + SLOT(0)) / 2 + Vector((0, 0, 1.0))
        path(c, t, [(t + 0.3, mid), (t + 0.6, SLOT(0))]); ROT[c][round(t, 3)] = (1.15, 0, 0); ROT[c][round(t + 0.6, 3)] = (0, 0, 0)
        LOCK[c] = t + 0.75
        busy[1] = False
for c, pts in LOC.items():
    for tt in sorted(pts): key(c, 'location', tt, tuple(pts[tt]))
    b = BORN[c]; keys(c, 'scale', [(0, TINY), (b - 0.001, TINY), (b + 0.12, (1.1,) * 3), (b + 0.2, (1, 1, 1))] + ([(GONE[c] - 0.1, (1, 1, 1)), (GONE[c], TINY)] if c in GONE else []))
for c, pts in ROT.items():
    for tt in sorted(pts): key(c, 'rotation_euler', tt, pts[tt])

# ---------- camera ----------
tgt = empty('tgt'); camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd)
col.objects.link(cam); sc.camera = cam
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
camd.dof.use_dof = True; camd.dof.focus_object = tgt; camd.dof.aperture_fstop = 3.2; camd.clip_end = 200
CUT = 1.0 / FPS
def place(c, width, lens, el, az, lift):
    d = width * lens / 20.25; vh = width * 36 / 20.25
    g = Vector(c) - Vector((0, 0, lift * vh))
    p = g + d * Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    return tuple(p), tuple(g)
PH = tuple(PHONE)
SHOTS = [  # (t, centre, visible width, lens, elevation, azimuth, lift, cut)
    (0.0, (PH[0] + 0.05, PH[1], PH[2] - 0.05), 1.75, 50, 10, -12, 0.1, False),
    (t_buy + 0.5, (PH[0] + 0.05, PH[1], PH[2] - 0.05), 1.6, 50, 10, -12, 0.1, False),
    (t_buy + 0.55, (0.1, 4.0, 0.9), 5.0, 40, 36, -2, 0.1, True),
    (t_pay + 0.5, (-0.1, 3.6, 0.9), 5.2, 40, 36, -4, 0.1, False),
    (t_wait - 0.12, (0.0, 3.3, 1.0), 5.0, 40, 34, -2, 0.1, False),
    (t_wait - 0.08, (PH[0] + 0.05, PH[1], PH[2] - 0.05), 1.55, 50, 10, -12, 0.1, True),
    (L(1, 0) - 0.05, (PH[0] + 0.05, PH[1], PH[2] - 0.05), 1.45, 50, 10, -12, 0.1, False),
    (L(1, 0), (0.0, 4.0, 0.8), 6.4, 40, 40, 14, 0.12, True),
    (t_pile, (0.0, 3.8, 0.8), 6.0, 40, 40, 10, 0.12, False),
    (t_crash, (0.0, 3.7, 1.0), 5.8, 40, 38, 8, 0.12, False),
    (t_fix - 0.06, (0.0, 3.7, 1.0), 5.6, 40, 38, 8, 0.12, False),
    (t_fix, (0.0, 3.9, 0.6), 5.4, 40, 50, -10, 0.05, True),
    (t_mq + 0.5, (0.0, 4.0, 0.6), 4.9, 40, 46, -8, 0.05, False),
    (L(3, 0) - 0.05, (0.0, 4.2, 0.6), 4.6, 40, 44, -6, 0.05, False),
    (L(3, 0), (-0.8, 6.3, 1.0), 3.9, 50, 24, -12, 0.06, True),
    (t_recv + 0.2, (-0.9, 6.5, 1.1), 3.5, 50, 22, -12, 0.06, False),
    (L(4, 0) - 0.05, (-0.9, 6.5, 1.1), 3.4, 50, 22, -12, 0.06, False),
    (L(4, 0), (0.0, 1.9, 1.0), 3.3, 50, 26, 14, 0.07, True),
    (L(4, 1) - 0.05, (0.0, 2.1, 1.0), 3.0, 50, 26, 10, 0.07, False),
    (L(4, 1), (0.0, 4.0, 0.5), 5.0, 40, 56, -18, 0.04, True),
    (L(5, 0) - 0.05, (0.0, 3.9, 0.5), 4.6, 40, 56, -12, 0.04, False),
    (L(5, 0), (0.0, 1.9, 1.0), 6.2, 50, 26, 0, 0.06, True),
    (W('share') + 0.3, (0.0, 2.1, 1.0), 6.0, 50, 28, 4, 0.06, False),
    (L(6, 0) - 0.05, (0.0, 2.1, 1.0), 5.9, 50, 28, 4, 0.06, False),
    (L(6, 0), (-1.5, 1.3, 1.5), 3.5, 50, 22, -8, 0.07, True),
    (t_done - 0.5, (-0.8, 1.4, 1.5), 3.8, 50, 22, -2, 0.07, False),
    (t_done - 0.2, (1.2, 1.4, 1.4), 3.4, 50, 22, 10, 0.07, False),
    (L(6, 1) - 0.05, (1.0, 1.4, 1.4), 3.3, 50, 22, 10, 0.07, False),
    (L(6, 1), (-1.1, 1.9, 1.3), 4.0, 50, 30, -8, 0.07, True),
    (L(7, 0) - 0.05, (-1.0, 2.0, 1.3), 3.8, 50, 30, -6, 0.07, False),
    (L(7, 0), (0.0, 3.6, 1.5), 6.6, 45, 32, -16, 0.11, True),
    (END, (0.0, 3.6, 1.5), 6.2, 45, 32, 16, 0.11, False),
]
prev = None
for t, c, wd, lens, el, az, lift, cut in SHOTS:
    p, g = place(c, wd, lens, el, az, lift)
    if cut and prev:
        key(cam, 'location', t - CUT, prev[0]); key(tgt, 'location', t - CUT, prev[1]); key(camd, 'lens', t - CUT, prev[2], 'CONSTANT')
    key(cam, 'location', t, p); key(tgt, 'location', t, g); key(camd, 'lens', t, lens, 'CONSTANT')
    prev = (p, g, lens)
# shake on the crash
sh = empty('shake', (0, 0, 0)); cam.parent = sh
for i, dt in enumerate([0, 0.05, 0.1, 0.15, 0.2, 0.26, 0.34, 0.45]):
    a = 0.07 * (1 - i / 8)
    key(sh, 'location', t_crash + dt, (random.uniform(-a, a), 0, random.uniform(-a, a)) if 0 < i < 7 else (0, 0, 0))
key(sh, 'location', 0, (0, 0, 0))

# ---------- render ----------
sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = SAMPLES
ee.use_shadows = True; ee.use_raytracing = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
ee.volumetric_tile_size = '8'; ee.volumetric_samples = 48; ee.volumetric_end = 60; ee.use_volumetric_shadows = True
sc.render.resolution_x, sc.render.resolution_y = RES, int(RES * 16 / 9) // 2 * 2
sc.render.resolution_percentage = 100; sc.render.fps = FPS
a, b = [int(x) for x in opt('--range', f'1,{F(END)}').split(',')]
sc.frame_start, sc.frame_end = a, b
sc.render.image_settings.file_format = 'PNG'
if '--skip' in argv: sc.render.use_overwrite = False; sc.render.use_placeholder = True  # several renderers can share one frame folder
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new('CompositorNodeRLayers'); gl = ng.nodes.new('CompositorNodeGlare'); go = ng.nodes.new('NodeGroupOutput')
gl.inputs['Type'].default_value = 'Bloom'; gl.inputs['Threshold'].default_value = 0.9; gl.inputs['Size'].default_value = 0.6; gl.inputs['Strength'].default_value = 0.7
ng.links.new(rl.outputs['Image'], go.inputs[0])  # no bloom
if '--cover' in argv:   # cover art: one fixed wide shot of the whole system, framed low so the title has the top of the frame
    t = float(opt('--cover', 21.8))
    for ob in (cam, tgt, sh): ob.animation_data_clear()
    camd.animation_data_clear()
    p, g = place((0.0, 3.0, 0.9), 7.0, 45, 34, -14, -0.2)
    cam.location = p; tgt.location = g; camd.lens = 45; camd.dof.aperture_fstop = 5.6
    sc.render.use_motion_blur = False
    sc.frame_set(F(t)); sc.render.filepath = f'{OUT}/cover_art.png'; bpy.ops.render.render(write_still=True)
elif '--cutfix' in argv:   # the 2 frames around each camera cut, re-rendered without motion blur (blur would smear across the jump)
    sc.render.use_motion_blur = False
    for t in [sh[0] for sh in SHOTS if sh[7]]:
        for fr in (F(t) - 1, F(t)):
            sc.frame_set(fr); sc.render.filepath = f'{OUT}/f_{fr:04d}.png'; bpy.ops.render.render(write_still=True)
elif STILLS:
    for s in STILLS:
        sc.frame_set(F(s)); sc.render.filepath = f'{OUT}/still_{s:05.2f}.png'; bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = f'{OUT}/f_'; bpy.ops.render.render(animation=True)
