# 18 Pub/Sub, studio look, v2: server racks, a cloud for the topic, a live code panel on the post service, a radio-tower set,
# a waiting timer on the creator's phone and a field of phones with a live counter. Timed to voice/words.json.
# usage: blender -b -P videos/18-pub-sub/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 24] [--stills 3,20] [--range a,b] [--skip] [--cutfix] [--cover t]
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

MONO = bpy.data.fonts.load(f'{D}/fonts/JetBrainsMono-Bold.ttf')
PINK, YELLOW = '#F472B6', '#FACC15'
for nm, h in (('pink', PINK), ('yellow', YELLOW)):
    M[nm] = mat(nm, h, 0.4, emit=3.0); M[f't_{nm}'] = mat(f't_{nm}', h, 0.4, emit=5.0)
M['t_white'] = mat('t_white', '#E8EEF8', 0.4, emit=4.0)
M['rackm'] = mat('rackm', '#1B2231', 0.32, 0.65)
M['unit'] = mat('unit', '#0E141F', 0.35, 0.4)
M['steel'] = mat('steel', '#8F9AB0', 0.32, 0.85)
M['cloud'] = mat('cloud', '#ECEAFF', 0.55, emit=0.6, eh='#B4A8FF', coat=0.2)

EM = defaultdict(list); BASE = {}          # emission events per material, written at the end
def flash(m, t, peak=12, dur=0.5):
    b = BASE.get(m, 3); EM[m] += [(t - 0.01, b), (t + 0.1, peak), (t + dur, b)]
def life(c, born, gone=None, s=(1, 1, 1)):
    pts = [(0, TINY), (born - 0.05, TINY), (born + 0.12, tuple(v * 1.1 for v in s)), (born + 0.2, s)]
    if gone is not None: pts += [(gone - 0.1, s), (gone, TINY)]
    keys(c, 'scale', pts)
def show(ob, ivs, pop=0.14):
    """visible during each (on, off) interval, with a pop on entry."""
    pts = [] if ivs[0][0] <= 0 else [(0, TINY)]
    for a_, b_ in ivs:
        if a_ <= 0: pts.append((0, (1, 1, 1)))
        else: pts += [(a_ - 0.05, TINY), (a_ + pop * 0.6, (1.08,) * 3), (a_ + pop, (1, 1, 1))]
        if b_ is not None: pts += [(b_ - 0.08, (1, 1, 1)), (b_, TINY)]
    keys(ob, 'scale', pts)
def swap(obs_times, end=None):
    """a run of objects shown one after another (counters, timers): each one visible until the next one starts."""
    for i, (ob, t0) in enumerate(obs_times):
        t1 = obs_times[i + 1][1] if i + 1 < len(obs_times) else end
        pts = [(0, TINY), (t0 - 1.0 / FPS, TINY), (t0, (1, 1, 1))] + ([(t1 - 1.0 / FPS, (1, 1, 1)), (t1, TINY)] if t1 is not None else [])
        keys(ob, 'scale', pts)   # one-frame switches (CONSTANT interpolation isn't applied to object keys here)
def drop(root, t0, home, pre=9):
    hx_, hy_, hz_ = home
    keys(root, 'location', [(0, (hx_, hy_, hz_ + pre)), (t0 - 0.3, (hx_, hy_, hz_ + pre)), (t0, (hx_, hy_, hz_ - 0.06)), (t0 + 0.1, (hx_, hy_, hz_ + 0.05)), (t0 + 0.2, home)])
def bev(ob, w=0.03):
    bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = w; bv.segments = 3; bv.limit_method = 'ANGLE'; ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); return ob
def mtext(name, body, loc, size, m, parent=None):
    """left-aligned monospace text facing -y (code)."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = MONO; cu.size = size
    cu.align_x = 'LEFT'; cu.align_y = 'CENTER'; cu.extrude = 0.002
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = (math.pi / 2, 0, 0); return link(ob, m, parent)
def beam(name, a, b, r, m, parent=None):
    """cylinder from a to b (in parent space); grows along its length with the root's z scale."""
    a, b = Vector(a), Vector(b); d = b - a
    root = empty(name, tuple(a), parent); root.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    cyl(f'{name}_c', (0, 0, d.length / 2), r, d.length, m, root)
    return root
def grow3(root, t_on, t_off=None, dur=0.3):
    pts = [(0, (1, 1, 0.001)), (t_on, (1, 1, 0.001)), (t_on + dur, (1, 1, 1))]
    if t_off is not None: pts += [(t_off, (1, 1, 1)), (t_off + 0.25, (1, 1, 0.001))]
    keys(root, 'scale', pts)

# blinking server LEDs: a small pool of materials with random on/off patterns
LEDM = []
for g, h in enumerate([GREEN] * 5 + [AMBER, CYAN, GREEN]):
    m = mat(f'led{g}', h, 0.4, emit=6.0); t = random.uniform(0, 0.4); pts = []
    while t < 70: pts.append((t, random.choice((0.6, 6, 6, 9)))); t += random.uniform(0.12, 0.5)
    emit_keys(m, pts); LEDM.append(m)

# ---------- server racks ----------
def rack(name, label, accent, x=0.0, y=0.0, parent=None, s=1.0):
    root = empty(name, (x, y, 0), parent); root.scale = (s, s, s)
    band = mat(f'{name}_band', accent, 0.4, emit=3.0); BASE[band] = 3
    rbox(f'{name}_plinth', (0, 0, 0.04), (1.4, 1.2, 0.08), M['plinth'], root, r=0.14)
    rbox(f'{name}_body', (0, 0, 1.03), (1.1, 0.9, 1.9), M['rackm'], root, r=0.07, bevel=0.02)
    rbox(f'{name}_cap', (0, 0, 1.985), (1.0, 0.8, 0.02), M['hatch'], root, r=0.05, bevel=0)
    rbox(f'{name}_caprim', (0, 0, 1.98), (1.06, 0.86, 0.02), band, root, r=0.07, bevel=0)
    for sx in (-0.535, 0.535):
        rbox(f'{name}_strip{sx}', (sx, -0.455, 1.0), (0.035, 0.02, 1.72), band, root, bevel=0)
    rbox(f'{name}_scr', (0, -0.46, 1.66), (0.9, 0.03, 0.36), M['glassblk'], root, r=0.06, axis=1, bevel=0.006)
    lbl = text(f'{name}_lbl', label, (0, -0.48, 1.69), 0.16 if len(label) < 7 else 0.13, M['white'], root)
    for i in range(4):
        z = 0.32 + i * 0.3
        rbox(f'{name}_u{i}', (0, -0.455, z), (0.92, 0.03, 0.24), M['unit'], root, r=0.03, axis=1, bevel=0)
        for v in range(2): rbox(f'{name}_v{i}{v}', (-0.18, -0.472, z - 0.04 + v * 0.08), (0.42, 0.006, 0.025), M['dark'], root, bevel=0)
        for q in range(3): sphere(f'{name}_l{i}{q}', (0.2 + q * 0.09, -0.475, z), 0.022, random.choice(LEDM), root)
    pl = point(f'{name}_pool', (0, 0, 0), 6, accent, 0.4); pl.parent = root; pl.location = (0, -1.0, 0.18)
    return root, band, lbl, pl

OX, OY = 0.0, 7.0                     # POST service rack (far end, top of frame)
HY, R = 3.6, 3.4                      # topic centre on the floor, subscriber ring radius
POST2 = Vector((OX, OY))
PHONE = Vector((-2.05, 7.0, 1.3))
o_root, o_band, o_lbl, o_pool = rack('POST', 'POST', AMBER, OX, OY)
SUBS = [('NOTIFY', CYAN, 'cyan'), ('EMAIL', GREEN, 'green'), ('FEED', PINK, 'pink'), ('BADGES', YELLOW, 'yellow')]
TH0 = [-50, 0, 50, 60]                # angles before the new feature (BADGES not there yet)
TH1 = [-60, -20, 20, 60]              # after it joins
SP = 0.8                              # subscriber rack scale
arms, sracks = [], []
for k, (nm, h, _) in enumerate(SUBS):
    arm = empty(f'arm{k}', (0, HY, 0), rot=(0, 0, math.radians(TH0[k])))
    rk = rack(nm, nm, h, 0, -R, parent=arm, s=SP); rk[0].rotation_euler = (0, 0, -math.radians(TH0[k]))
    arms.append(arm); sracks.append(rk)
POS0 = [Vector((R * math.sin(math.radians(a)), HY - R * math.cos(math.radians(a)))) for a in TH0]
sband = [r_[1] for r_ in sracks]
SHOVER, SSINK = 2.05, 1.45            # tile hover / sink heights over a subscriber rack

# ---------- floor cables (direct calls) ----------
def cable(name, a, b, m, a_off=0.8, b_off=0.7, z=0.22, r=0.035, parent=None):
    d = b - a; Ln = d.length; th = math.atan2(d.x, -d.y)
    root = empty(name, (a.x, a.y, z), parent, rot=(0, 0, th))
    ln = Ln - a_off - b_off
    c = cyl(f'{name}_c', (0, -(a_off + ln / 2), 0), r, ln, m, root); c.rotation_euler = (math.pi / 2, 0, 0)
    for f_ in (0.15, 0.5, 0.85): cyl(f'{name}_p{f_}', (0, -(a_off + ln * f_), -0.1), 0.045, 0.22, M['plinth'], root)
    return root
def grow(root, t_on, t_off=None, dur=0.3):
    pts = [(0, (1, 0.001, 1)), (t_on, (1, 0.001, 1)), (t_on + dur, (1, 1, 1))]
    if t_off is not None: pts += [(t_off, (1, 1, 1)), (t_off + 0.25, (1, 0.001, 1))]
    keys(root, 'scale', pts)

# ---------- the topic: a cloud ----------
CLOUD = Vector((0, HY, 2.8))
cloud = empty('cloud', (CLOUD.x, CLOUD.y, CLOUD.z + 9))
for i, (x, y, z, r) in enumerate([(0, 0, 0, 0.62), (-0.62, 0, -0.12, 0.48), (0.62, 0, -0.1, 0.5), (-1.05, 0.02, -0.26, 0.33), (1.05, 0.02, -0.25, 0.35),
                                  (-0.3, 0.15, 0.3, 0.45), (0.35, 0.1, 0.28, 0.42), (0, -0.22, -0.2, 0.46), (0, 0.3, -0.1, 0.5), (-0.55, -0.1, 0.1, 0.4), (0.5, -0.12, 0.08, 0.4)]):
    me = bpy.data.meshes.new(f'cl{i}'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(f'cl{i}', me); ob.location = (x, y, z); link(ob, M['cloud'], cloud)
cmark = mat('cmark', VIOLET, 0.4, emit=3.0); BASE[cmark] = 3
cring = torus('cloud_ring', (0, HY, 0.03), 1.0, 0.025, cmark); cring.rotation_euler = (math.pi / 2, 0, 0)
cpool = point('cloud_pool', (0, HY, 1.2), 0, VIOLET, 0.8)

# ---------- phone (the creator) ----------
ph = empty('phone', PHONE, rot=(math.radians(-14), 0, math.radians(-12)))
rbox('ph_body', (0, 0, 0), (0.76, 0.07, 1.48), M['phone'], ph, r=0.12, axis=1, bevel=0.02)
rbox('ph_scr', (0, -0.036, 0), (0.68, 0.005, 1.4), M['screen'], ph, r=0.09, axis=1, bevel=0)
rbox('ph_notch', (0, -0.04, 0.63), (0.18, 0.004, 0.045), M['dark'], ph, r=0.022, axis=1, bevel=0)
SY = -0.042
def ui(name): return empty(name, (0, 0, 0), ph)
s0 = ui('ui_compose')
text('u0_t', 'NEW POST', (0, SY, 0.5), 0.075, M['t_grey'], s0)
rbox('u0_card', (0, SY + 0.002, 0.12), (0.56, 0.004, 0.56), M['card'], s0, r=0.05, axis=1, bevel=0)
rbox('u0_img', (0, SY - 0.001, 0.22), (0.46, 0.004, 0.28), M['violet'], s0, r=0.04, axis=1, bevel=0)
sphere('u0_sun', (0.12, SY - 0.004, 0.28), 0.04, M['amber'], s0)
rbox('u0_l1', (-0.03, SY - 0.001, 0.0), (0.4, 0.004, 0.035), M['grey'], s0, r=0.017, axis=1, bevel=0)
rbox('u0_l2', (-0.08, SY - 0.001, -0.07), (0.3, 0.004, 0.035), M['grey'], s0, r=0.017, axis=1, bevel=0)
btn = empty('u0_btn', (0, SY - 0.002, -0.38), s0)
rbox('u0_b', (0, 0, 0), (0.54, 0.004, 0.15), M['btn'], btn, r=0.074, axis=1, bevel=0)
text('u0_bt', 'POST', (0, -0.003, 0), 0.075, M['ink'], btn)
s1 = ui('ui_wait')
spin = empty('u1_spin', (0, SY, 0.14), s1)
for i in range(10):
    a = 2 * math.pi * i / 10
    sphere(f'u1_d{i}', (0.13 * math.cos(a), 0, 0.13 * math.sin(a)), 0.012 + 0.0025 * i, M['white'] if i > 4 else M['grey'], spin)
text('u1_t', 'POSTING', (0, SY, -0.12), 0.065, M['white'], s1)
text('u1_t2', 'please wait...', (0, SY, -0.22), 0.05, M['t_grey'], s1)
rbox('u1_b', (0, SY - 0.001, -0.42), (0.54, 0.004, 0.15), M['card'], s1, r=0.074, axis=1, bevel=0)
text('u1_bt', 'POSTING...', (0, SY - 0.003, -0.42), 0.06, M['t_grey'], s1)
s3 = ui('ui_ok')
torus('u3_ring', (0, SY, 0.16), 0.13, 0.016, M['green'], s3)
text('u3_ok', 'OK', (0, SY, 0.16), 0.1, M['t_green'], s3)
text('u3_t', 'POSTED', (0, SY, -0.08), 0.075, M['t_green'], s3)
text('u3_t2', 'to 2M followers', (0, SY, -0.18), 0.045, M['t_grey'], s3)

# ---------- chips (holographic status tags) ----------
CHIP_TILT = math.radians(-18)
CUT_ = 1.0 / FPS
def chip(name, body, loc, colname, size=0.2, az=0.0, parent=None, mono=False):
    root = empty(name, loc, parent, rot=(CHIP_TILT, 0, math.radians(az)))
    t = text(f'{name}_t', body, (0, -0.035, 0), size, M[f't_{colname}'], root)
    if mono: t.data.font = MONO
    bpy.context.view_layer.update()
    wd, h = t.dimensions.x + size * 1.3, size * 1.75
    rbox(f'{name}_bg', (0, 0, 0), (wd, 0.03, h), M['chipbg'], root, r=h / 2 * 0.98, axis=1, bevel=0)
    rbox(f'{name}_rim', (0, 0.012, 0), (wd + 0.035, 0.02, h + 0.035), M[colname], root, r=(h + 0.035) / 2 * 0.98, axis=1, bevel=0)
    return root

# ---------- message tiles ----------
NT = [0]
def tile(num, stripe=None):
    n = NT[0]; NT[0] += 1
    c = rbox(f'tile{n}', (0, 0, -5), (0.5, 0.3, 0.06), M['paper'], r=0.06, bevel=0.012)
    rbox(f'tile{n}_s', (-0.19, 0, 0.004), (0.07, 0.24, 0.06), stripe or M['amber'], c, r=0.03, bevel=0)
    text(f'tile{n}_t', f'#{num}', (0.05, 0, 0.032), 0.085, M['ink'], c, extrude=0.002, flat=True)
    return c
O_OUT = Vector((OX, OY - 0.6, 1.0))   # where messages leave the post rack
UP = (1.15, 0, 0)                      # tile tilted to face the camera while it hovers
def deliver(k, t_arr, num, hold=None):
    """direct call: POST -> subscriber k along its floor cable (phase 1 positions)."""
    P = POS0[k]; d = (P - POST2).normalized(); a_ = POST2 + d * 0.95; b_ = P - d * 0.85
    c = tile(num); t0 = t_arr - 0.8; tg = (hold or t_arr) + 0.22
    keys(c, 'location', [(t0, O_OUT), (t0 + 0.15, (a_.x, a_.y, 0.36)), (t_arr - 0.32, (b_.x, b_.y, 0.36)),
                         (t_arr - 0.12, (b_.x, b_.y, 2.1)), (t_arr, (P.x, P.y, SHOVER)), ((hold or t_arr) + 0.05, (P.x, P.y, SHOVER)), (tg, (P.x, P.y, SSINK))])
    keys(c, 'rotation_euler', [(t_arr - 0.2, (0, 0, 0)), (t_arr, UP), ((hold or t_arr) + 0.05, UP), (tg, (0, 0, 0))])
    life(c, t0, tg)
    if hold is None: flash(sband[k], tg)
    return c
def publish(t0, t_arr, num, ks=(), t_c=None, t_h=None):
    """POST -> up into the cloud; then one copy per subscriber in ks, raining down its beam from t_c, over its rack at t_h."""
    c = tile(num)
    keys(c, 'location', [(t0, O_OUT), (t0 + 0.2, (0, OY - 1.2, 1.9)), (t_arr - 0.25, (0, HY + 1.0, 3.0)), (t_arr, tuple(CLOUD))])
    keys(c, 'rotation_euler', [(t0, (0, 0, 0)), (t_arr, (0.5, 0, 0))])
    life(c, t0, t_arr + 0.02)
    flash(cmark, t_arr, 12); keys(cloud, 'scale', [(t_arr - 0.02, (1, 1, 1)), (t_arr + 0.1, (1.08, 1.08, 1.12)), (t_arr + 0.35, (1, 1, 1))])
    for k in ks:
        cc = tile(num); cc.parent = arms[k]; dt = t_h - t_c
        keys(cc, 'location', [(t_c, (0, -0.45, 2.45)), (t_c + 0.5 * dt, (0, -R * 0.62, 2.25)), (t_c + 0.85 * dt, (0, -R, 2.15)),
                              (t_h, (0, -R, SHOVER)), (t_h + 0.22, (0, -R, SSINK))])
        keys(cc, 'rotation_euler', [(t_c + 0.6 * dt, (0, 0, 0)), (t_h, UP), (t_h + 0.05, UP), (t_h + 0.22, (0, 0, 0))])
        life(cc, t_c, t_h + 0.2); flash(sband[k], t_h + 0.2)
    return c

# ---------- timing ----------
t_post, t_two, t_notif = W('post'), W('two'), W('notification')
t_btn, t_spinning = W('button'), W('spinning')
t_why, t_itself = L(1, 0), W('itself')
t_n, t_e, t_f, t_oaa = W('notify'), W('emails'), W('feeds'), W('one', W('feeds'))
t_spot, t_slow, t_waits = L(2, 0), W('slow'), W('waits')
t_new, t_rewrite, t_again = W('new', L(3, 1)), W('rewriting'), W('again')
t_q, t_queue, t_one = L(4, 0), W('queue', L(4, 0)), W('one', W('just', L(4, 0)))
t_fix, t_ps, t_pub, t_topic, t_done = L(5, 0), W('pubsub'), W('publishes'), W('topic', L(5, 0)), W('done')
t_stops = W('stops')
t_subs, t_copy, t_same = W('subscribes'), W('copy'), W('same')
t_radio, t_bcast, t_once, t_hears = L(7, 0), W('broadcasts'), W('once', L(7, 0)), W('hears')
t_nf, t_sub2, t_never = L(8, 0), W('subscribe', L(8, 0)), W('never')
t_pay, t_onepub, t_everyone = L(9, 0), W('publish', L(9, 0)), W('everyone')
t_tools, t_goog, t_amz = L(10, 0), W('google'), W('amazon')
t_end = L(11, 0)

# ---------- the creator's phone: one post, spinning until pub/sub ----------
show(s0, [(0, t_post + 0.12)])
show(s1, [(t_post + 0.14, t_stops)])
show(s3, [(t_stops + 0.02, None)])
keys(btn, 'scale', [(0, (1, 1, 1)), (t_post - 0.12, (1, 1, 1)), (t_post - 0.02, (0.88, 1, 0.82)), (t_post + 0.12, (1, 1, 1))])
keys(spin, 'rotation_euler', [(0, (0, 0, 0)), (END, (0, -2 * math.pi * END * 1.4, 0))], 'LINEAR')
keys(ph, 'location', [(t, PHONE + Vector((0, 0, 0.05 * math.sin(t * 1.7)))) for t in [i * 0.5 for i in range(int(END * 2) + 2)]])
flash(sracks[0][1], t_stops, 3)                      # (keeps BASE entries consistent)
# the waiting timer next to the phone, fast-forwarded
TM = empty('timer', PHONE + Vector((0.78, -0.12, 0.62)), rot=(CHIP_TILT, 0, math.radians(-12)))
rbox('tm_bg', (0, 0, 0), (0.62, 0.03, 0.34), M['chipbg'], TM, r=0.16, axis=1, bevel=0)
tmrim = mat('tm_rim', RED, 0.4, emit=3.0)
rbox('tm_rim', (0, 0.012, 0), (0.655, 0.02, 0.375), tmrim, TM, r=0.18, axis=1, bevel=0)
text('tm_lbl', 'WAITING', (0, -0.035, 0.09), 0.055, M['t_grey'], TM)
runs, t = [], t_post + 0.2
while t < t_stops:
    sec = int((t - t_post) * 4.2)
    runs.append((text(f'tm_{len(runs)}', f'{sec // 60}:{sec % 60:02d}', (0, -0.035, -0.04), 0.13, M['t_red'], TM), t)); t += 0.25
swap(runs, t_stops)
vis(TM, t_post + 0.15, t_stops + 0.3, pop=0.2, over=1.2)
emit_keys(tmrim, [(0, 3), (t_stops, 3), (t_stops + 0.02, 12), (t_stops + 0.3, 0)], 'BEZIER')
still = chip('chip_still', 'STILL POSTING...', (PHONE.x, PHONE.y - 0.1, 2.35), 'red', 0.13)
vis(still, t_spinning, t_why)

# ---------- hook + payoff: two million phones ----------
FC = Vector((-12.0, 4.5, 0.0))
fbanner = mat('fbanner', WHITE, 0.4, emit=3.0)
FG = 6
fscr = [mat(f'fscr{g}', '#070B14', 0.2, emit=0.15, eh='#4FB8FF') for g in range(FG)]
fbody = mat('fbody', '#121826', 0.45, 0.25)
BUZZ = t_everyone + 0.04
for g, m in enumerate(fscr):
    d_ = BUZZ + g * 0.035
    emit_keys(m, [(0, 0.15), (d_ - 0.01, 0.15), (d_ + 0.06, 4.5), (d_ + 0.6, 1.4)], 'BEZIER')
EARLY = random.sample([(i, j) for i in range(9) for j in range(11)], 6)    # the few that do get notified in the hook
for i in range(9):
    for j in range(11):
        x = FC.x + (i - 4) * 0.6 + random.uniform(-0.08, 0.08); y = 1.6 + j * 0.72 + random.uniform(-0.1, 0.1)
        g = random.randrange(FG)
        r_ = empty(f'fp{i}_{j}', (x, y, 0), rot=(math.radians(-12), 0, random.uniform(-0.12, 0.12)))
        rbox(f'fp{i}_{j}_b', (0, 0, 0.33), (0.32, 0.035, 0.6), fbody, r_, r=0.05, axis=1, bevel=0.008)
        sm = fscr[g]
        if (i, j) in EARLY:
            te = t_two + 0.5 + EARLY.index((i, j)) * 0.38
            sm = mat(f'fscrE{i}{j}', '#070B14', 0.2, emit=0.15, eh='#4FB8FF')
            emit_keys(sm, [(0, 0.15), (te, 0.15), (te + 0.06, 4.5), (te + 0.6, 1.4), (t_why, 1.4), (t_why + 0.05, 0.15), (BUZZ, 0.15), (BUZZ + 0.06, 4.5), (BUZZ + 0.6, 1.4)], 'BEZIER')
        rbox(f'fp{i}_{j}_s', (0, -0.018, 0.33), (0.28, 0.004, 0.54), sm, r_, r=0.04, axis=1, bevel=0)
        bn = rbox(f'fp{i}_{j}_n', (0, -0.022, 0.5), (0.24, 0.004, 0.08), fbanner, r_, r=0.03, axis=1, bevel=0)
        on = [(BUZZ + g * 0.035 + 0.04, BUZZ + 2.2)]
        if (i, j) in EARLY: on = [(te + 0.04, t_why)] + on
        show(bn, on, pop=0.1)
        z0 = r_.rotation_euler.z; d_ = BUZZ + g * 0.035
        wig = [(d_ - 0.01, z0)] + [(d_ + 0.05 * (q + 1), z0 + (0.09 if q % 2 == 0 else -0.09) * (1 - q / 7)) for q in range(7)] + [(d_ + 0.42, z0)]
        keys(r_, 'rotation_euler', [(t, (math.radians(-12), 0, z)) for t, z in wig])
area('ftop', (FC.x, 5.0, 9), (FC.x, 5.0, 0), 8.0, 550, '#EEF3FF')
area('fkey', (FC.x - 5, -3.5, 6), (FC.x, 4.0, 0.4), 5.0, 450, '#FFF1E0')
area('frim', (FC.x + 4, 12, 4), (FC.x, 5, 0.4), 6.0, 500, CYAN)
CNT = (FC.x, 2.2, 1.75)
nlab = chip('chip_notified', 'NOTIFIED', (CNT[0], CNT[1], CNT[2] + 0.42), 'grey', 0.11)
show(nlab, [(t_two, t_why), (t_pay, None)])
cnt = [('0', t_two), ('3', t_two + 0.55), ('9', t_two + 0.93), ('14', t_two + 1.31), ('22', t_two + 1.69), ('31', t_two + 2.07)]
runs = [(chip(f'cnt{i}', f'{v} / 2,000,000', CNT, 'amber', 0.22, mono=True), t) for i, (v, t) in enumerate(cnt)]
runs[-1] = (runs[-1][0], runs[-1][1])
swap(runs, t_why)
cnt2 = [('0', t_pay), ('184,302', BUZZ + 0.02), ('761,950', BUZZ + 0.14), ('1,412,077', BUZZ + 0.26)]
runs = [(chip(f'cntB{i}', f'{v} / 2,000,000', CNT, 'amber', 0.22, mono=True), t) for i, (v, t) in enumerate(cnt2)]
runs.append((chip('cntDone', '2,000,000 / 2,000,000', CNT, 'green', 0.22, mono=True), BUZZ + 0.38))
swap(runs, None)

# ---------- the code on the post service: a holographic panel ----------
PANEL = empty('panel', (2.3, OY + 0.15, 1.75), rot=(CHIP_TILT, 0, math.radians(-8)))
rbox('pn_bg', (0, 0, 0), (2.5, 0.03, 1.78), M['chipbg'], PANEL, r=0.1, axis=1, bevel=0)
prim = mat('pn_rim', AMBER, 0.4, emit=2.2); BASE[prim] = 2.2
rbox('pn_rim', (0, 0.012, 0), (2.54, 0.02, 1.82), prim, PANEL, r=0.11, axis=1, bevel=0)
for i, h in enumerate((RED, AMBER, GREEN)): sphere(f'pn_dot{i}', (-1.1 + i * 0.1, -0.03, 0.74), 0.028, mat(f'pn_d{i}', h, 0.4, emit=3), PANEL)
mtext('pn_title', 'post_service.py', (-0.78, -0.035, 0.74), 0.075, M['t_grey'], PANEL)
rbox('pn_sep', (0, -0.02, 0.65), (2.36, 0.006, 0.008), M['grey'], PANEL, bevel=0)
LZ = [0.48, 0.27, 0.06, -0.15, -0.36, -0.57]
X0, CS = -1.1, 0.12
hlm = mat('pn_hl', AMBER, 0.4, emit=1.2, alpha=0.35); BASE[hlm] = 1.2
HL = rbox('pn_hl', (0, -0.022, LZ[2]), (2.34, 0.004, 0.19), hlm, PANEL, r=0.04, axis=1, bevel=0)
code1 = empty('code1', (0, 0, 0), PANEL); code2 = empty('code2', (0, 0, 0), PANEL)
for i, (s_, m_) in enumerate([('def create_post(p):', 't_violet'), ('    db.save(p)', 't_white'), ('    notify(p)', 't_white'),
                              ('    send_email(p)', 't_white'), ('    update_feed(p)', 't_white')]):
    mtext(f'c1_{i}', s_, (X0, -0.035, LZ[i]), CS, M[m_], code1)
bad = mtext('c1_new', '+   award_badge(p)', (X0, -0.035, LZ[5]), CS, M['t_red'], code1)
waitc = mtext('c1_wait', '# waiting...', (X0 + 18 * CS * 0.6, -0.035, LZ[3]), CS * 0.85, M['t_red'], code1)
for i, (s_, m_) in enumerate([('def create_post(p):', 't_violet'), ('    db.save(p)', 't_white'), ('    publish("new-post", p)', 't_violet'),
                              ('    return "done"', 't_green')]):
    mtext(f'c2_{i}', s_, (X0, -0.035, LZ[i]), CS, M[m_], code2)
t_swap = t_pub - 0.35
show(code1, [(0, t_swap)], pop=0.01); show(code2, [(t_swap + 0.08, None)])
show(bad, [(t_rewrite + 0.05, None)]); show(waitc, [(t_waits, t_q)])
# highlight bar walks the lines as each call runs
hl_pts = [(0, LZ[1]), (t_n - 0.35, LZ[1]), (t_n - 0.25, LZ[2]), (t_e - 0.35, LZ[2]), (t_e - 0.25, LZ[3]), (t_f - 0.35, LZ[3]), (t_f - 0.25, LZ[4]),
          (t_slow - 0.75, LZ[4]), (t_slow - 0.65, LZ[3]), (t_rewrite, LZ[3]), (t_rewrite + 0.1, LZ[5]), (t_q, LZ[5]), (t_q + 0.1, LZ[1]),
          (t_pub - 0.05, LZ[1]), (t_pub + 0.05, LZ[2]), (t_done - 0.1, LZ[2]), (t_done, LZ[3])]
for t, z in hl_pts: key(HL, 'location', t, (0, -0.022, z), 'CONSTANT')
color_keys(hlm, [(0, AMBER), (t_slow - 0.65, RED), (t_q, AMBER), (t_pub, VIOLET), (t_done, GREEN)])
show(HL, [(t_n - 0.3, t_spot), (t_slow - 0.7, t_q), (t_pub, t_subs)])
color_keys(prim, [(0, AMBER), (t_rewrite, RED), (t_q, AMBER), (t_never, GREEN), (t_pay, AMBER)])
flash(prim, t_rewrite, 7, 0.4); flash(prim, t_never, 8, 0.8)
same = chip('chip_unchanged', 'UNCHANGED', (2.3, OY + 0.15, 2.95), 'green', 0.2)
vis(same, t_never, t_pay, over=1.25)

# ---------- part 1: the post service calls every feature itself ----------
dmat = [mat(f'dcab{k}', AMBER, 0.4, emit=2.0) for k in range(3)]
dcab = [cable(f'dcab{k}', POST2, POS0[k], dmat[k], b_off=0.8) for k in range(3)]
for k in range(3): grow(dcab[k], t_why + 0.4 + k * 0.12, t_q)
deliver(0, t_n + 0.3, 1001); deliver(1, t_e + 0.3, 1001); deliver(2, t_f + 0.3, 1001)
itself = chip('chip_itself', 'DOES EVERY JOB', (0, OY - 0.4, 2.55), 'amber', 0.16)
vis(itself, t_itself, t_spot)
oaa = chip('chip_oaa', '1 > 2 > 3', (0, OY - 0.4, 2.55), 'amber', 0.17, mono=True)
vis(oaa, t_oaa, t_spot)
keys(itself, 'scale', [(t_oaa - 0.05, (1, 1, 1)), (t_oaa, TINY)], 'CONSTANT')
# spot the problem: the stage dims, a spot finds the code
spot = point('spot', (1.2, 4.6, 5.4), 0, '#FFFFFF', 0.3, kind='SPOT')
spot.data.spot_size = math.radians(34); spot.data.spot_blend = 0.6
spot.rotation_euler = (Vector((1.1, OY, 1.2)) - spot.location).to_track_quat('-Z', 'Y').to_euler()
keys(spot.data, 'energy', [(0, 0), (t_spot - 0.01, 0), (t_spot, 1500), (L(3, 0) - 0.01, 1500), (L(3, 0), 0)], 'CONSTANT')
keys(TOP.data, 'energy', [(0, 2600), (t_spot - 0.01, 2600), (t_spot, 700), (L(3, 0) - 0.01, 700), (L(3, 0), 2600)], 'CONSTANT')
keys(KEYL.data, 'energy', [(0, 1700), (t_spot - 0.01, 1700), (t_spot, 500), (L(3, 0) - 0.01, 500), (L(3, 0), 1700)], 'CONSTANT')
# email is slow -> the post waits
deliver(1, t_slow, 1002, hold=t_q - 0.3)
deliver(0, t_slow - 0.6, 1002)
color_keys(sband[1], [(0, GREEN), (t_slow, AMBER), (t_q, GREEN)])
color_keys(dmat[1], [(0, AMBER), (t_slow, RED)])
t = t_slow
while t < t_q - 0.3: EM[sband[1]] += [(t, 3), (t + 0.3, 8), (t + 0.6, 3)]; t += 0.6
slow = chip('chip_slow', 'SLOW', (POS0[1].x, POS0[1].y, 2.75), 'amber', 0.2)
vis(slow, t_slow + 0.05, t_q)
# every new feature means rewriting the post service
GH = Vector((-3.1, 4.6))
ghost = empty('ghost', (GH.x, GH.y, 9))
gband = mat('ghost_band', YELLOW, 0.4, emit=3.0)
rbox('gh_plinth', (0, 0, 0.04), (1.2, 1.05, 0.08), M['plinth'], ghost, r=0.12)
rbox('gh_body', (0, 0, 0.85), (0.92, 0.78, 1.55), M['glass'], ghost, r=0.06, bevel=0)
rbox('gh_cap', (0, 0, 1.63), (0.95, 0.81, 0.03), gband, ghost, r=0.07, bevel=0)
text('gh_plus', '+', (0, -0.42, 1.05), 0.42, M['t_yellow'], ghost)
text('gh_lbl', 'BADGES', (0, -0.42, 0.68), 0.13, M['white'], ghost)
drop(ghost, t_new + 0.1, (GH.x, GH.y, 0))
keys(ghost, 'scale', [(t_q - 0.05, (1, 1, 1)), (t_q + 0.2, TINY)])
gmat = mat('gcab', RED, 0.4, emit=2.5)
gcab = cable('gcab', POST2, GH, gmat, b_off=0.75)
grow(gcab, t_rewrite + 0.25, t_q - 0.1, dur=0.45)
color_keys(o_band, [(0, AMBER), (t_rewrite, RED), (t_q, AMBER)])
t = t_rewrite
while t < t_q - 0.3: EM[o_band] += [(t, 3), (t + 0.1, 9), (t + 0.3, 1)]; t += 0.4
EM[o_band].append((t_q, 3))
rew = chip('chip_rewrite', 'REWRITE + REDEPLOY', (0, OY - 0.4, 2.55), 'red', 0.16)
vis(rew, t_rewrite + 0.05, t_q)
again = chip('chip_again', 'AGAIN.', (-0.2, OY - 0.4, 2.95), 'red', 0.14)
vis(again, t_again, t_q, over=1.3)

# ---------- part 2: a message queue gives each message to just one worker ----------
lane = empty('lane', (0, 0, 6))
LY0, LY1 = 3.0, 6.15
LC, LLEN = (LY0 + LY1) / 2, LY1 - LY0
rbox('lane_base', (0, LC, 0.07), (1.05, LLEN + 0.2, 0.14), M['lane'], lane, r=0.12, bevel=0.02)
lstrip = mat('lane_strip', CYAN, 0.4, emit=0.7)
rbox('lane_glow', (0, LC, 0.142), (0.82, LLEN, 0.006), lstrip, lane, r=0.05, bevel=0)
for sx in (-0.5, 0.5):
    rbox(f'lane_wall{sx}', (sx, LC, 0.25), (0.035, LLEN + 0.2, 0.3), M['glass'], lane, bevel=0)
    rbox(f'lane_edge{sx}', (sx, LC, 0.405), (0.04, LLEN + 0.2, 0.012), M['cyan'], lane, bevel=0)
for i in range(6):
    for s in (-1, 1):
        o = rbox(f'chev{i}{s}', (s * 0.07, LY0 + 0.25 + i * 0.5, 0.147), (0.16, 0.025, 0.004), M['cyan'], lane, bevel=0)
        o.rotation_euler = (0, 0, s * math.radians(35))
keys(lane, 'location', [(0, (0, 0, 6)), (t_queue - 0.12, (0, 0, 6)), (t_queue + 0.22, (0, 0, -0.04)), (t_queue + 0.32, (0, 0, 0.03)),
                        (t_queue + 0.42, (0, 0, 0)), (t_fix + 0.05, (0, 0, 0)), (t_fix + 0.4, (0, 0, 7))])
keys(lane, 'scale', [(0, (1, 1, 1)), (t_fix + 0.36, (1, 1, 1)), (t_fix + 0.42, TINY)], 'CONSTANT')
emit_keys(lstrip, [(0, 0.7), (t_queue + 0.1, 0.7), (t_queue + 0.2, 8), (t_queue + 0.7, 0.7)], 'BEZIER')
mq = chip('chip_mq', 'MESSAGE QUEUE', (1.55, LC + 0.2, 0.75), 'cyan', 0.19)
vis(mq, t_queue + 0.35, t_fix)
tq0 = t_q + 1.4
c = tile(1003)
P1 = POS0[1]
keys(c, 'location', [(tq0, O_OUT), (tq0 + 0.22, (0, LY1 - 0.1, 0.45)), (tq0 + 0.5, (0, LY1 - 0.4, 0.2)), (t_one - 0.75, (0, LY0 + 0.15, 0.2)),
                     (t_one - 0.4, (0, (LY0 + P1.y) / 2, 2.1)), (t_one, (P1.x, P1.y, SHOVER)), (t_one + 0.05, (P1.x, P1.y, SHOVER)),
                     (t_one + 0.27, (P1.x, P1.y, SSINK))])
keys(c, 'rotation_euler', [(t_one - 0.2, (0, 0, 0)), (t_one, UP), (t_one + 0.05, UP), (t_one + 0.27, (0, 0, 0))])
life(c, tq0, t_one + 0.25); flash(sband[1], t_one + 0.25)
for k in (0, 2):
    q_ = chip(f'chip_nope{k}', '?', (POS0[k].x, POS0[k].y, 2.5), 'grey', 0.26)
    vis(q_, t_one + 0.1 + k * 0.05, t_fix)
only = chip('chip_only', 'ONLY ONE GETS IT', (0, HY - 0.9, 2.5), 'amber', 0.19)
vis(only, t_one + 0.15, t_fix)

# ---------- part 3: pub/sub, the topic is a cloud ----------
drop(cloud, t_ps, tuple(CLOUD), pre=8)
keys(cpool.data, 'energy', [(0, 0), (t_ps, 0), (t_ps + 0.05, 120), (t_ps + 0.7, 25)])
keys(cring, 'scale', [(0, TINY), (t_ps - 0.05, TINY), (t_ps + 0.15, (1.3, 1.3, 1.3)), (t_ps + 0.4, (1, 1, 1))])
flash(cmark, t_ps + 0.05, 14, 0.8)
for i in range(2):   # landing shock rings
    rm = mat(f'puff{i}', VIOLET, 0.4, emit=5.0)
    pr = torus(f'puff{i}', (0, HY, 0.05), 1.0, 0.03, rm); pr.rotation_euler = (math.pi / 2, 0, 0)
    t0 = t_ps + 0.05 + i * 0.15
    keys(pr, 'scale', [(0, TINY), (t0 - 0.05, TINY), (t0, (0.8, 0.8, 0.8)), (t0 + 0.8, (3.6, 1, 3.6)), (t0 + 0.85, TINY)], 'LINEAR')
    emit_keys(rm, [(t0, 6), (t0 + 0.8, 0.3)], 'LINEAR')
pss = chip('chip_pubsub', 'PUB/SUB', (0, HY - 0.3, 4.05), 'violet', 0.34)
vis(pss, t_ps + 0.1, t_pub - 0.1, pop=0.22, over=1.25)
tch = chip('chip_topic', 'TOPIC: new-post', (0, -0.95, -0.15), 'violet', 0.15, parent=cloud)
vis(tch, t_topic, None)
pbeam = beam('pbeam', (0, OY - 0.55, 2.0), (0, HY + 0.85, 2.85), 0.03, mat('pbeam', AMBER, 0.4, emit=2.0))
grow3(pbeam, t_pub - 0.45)
publish(t_pub, t_topic, 1004, ks=(0, 1, 2), t_c=t_copy - 0.05, t_h=t_same - 0.05)
dn = chip('chip_done', 'DONE', (0, OY - 0.4, 2.55), 'green', 0.2)
vis(dn, t_done, t_subs, over=1.25)
flash(o_band, t_done, 10)
# subscriptions: a beam from the cloud down to every rack
smat = mat('scab', VIOLET, 0.4, emit=2.0)
sbeam = [beam(f'sbeam{k}', (0, -0.45, 2.42), (0, -R, 2.0 * SP + 0.02), 0.03, smat, arms[k]) for k in range(4)]
for k in range(3): grow3(sbeam[k], t_subs + k * 0.12); flash(sband[k], t_subs + k * 0.12 + 0.3)
cp = chip('chip_copy', 'EACH GETS A COPY', (0, HY + 0.2, 4.05), 'violet', 0.18)
vis(cp, t_copy - 0.05, t_radio)
# a new feature just subscribes; the post service never changes
t_sl = t_nf + 0.05
for k in range(3):
    keys(arms[k], 'rotation_euler', [(0, (0, 0, math.radians(TH0[k]))), (t_sl, (0, 0, math.radians(TH0[k]))), (t_sl + 0.7, (0, 0, math.radians(TH1[k])))])
    keys(sracks[k][0], 'rotation_euler', [(0, (0, 0, -math.radians(TH0[k]))), (t_sl, (0, 0, -math.radians(TH0[k]))), (t_sl + 0.7, (0, 0, -math.radians(TH1[k])))])
b_root = sracks[3][0]
keys(b_root, 'location', [(0, (0, -R, 9)), (t_sub2 - 0.3, (0, -R, 9)), (t_sub2, (0, -R, -0.06)), (t_sub2 + 0.1, (0, -R, 0.05)), (t_sub2 + 0.2, (0, -R, 0))])
keys(b_root, 'scale', [(0, TINY), (t_sub2 - 0.35, TINY), (t_sub2 - 0.3, (SP,) * 3)], 'CONSTANT')
keys(sracks[3][3].data, 'energy', [(0, 0), (t_sub2 - 0.02, 0), (t_sub2, 6)], 'CONSTANT')
grow3(sbeam[3], t_sub2 + 0.25); flash(sband[3], t_sub2 + 0.05, 12, 0.7)
nc = chip('chip_nochange', 'NO CHANGES', (0, OY - 0.4, 2.55), 'green', 0.19)
vis(nc, t_never, t_pay)
# payoff: one publish, everyone notified
publish(t_onepub - 0.25, t_onepub + 0.3, 1005, ks=(0, 1, 2, 3), t_c=t_onepub + 0.35, t_h=t_everyone - 0.06)
# ending: it keeps running
t, n = t_tools + 0.2, 1006
while t < END - 1.5:
    publish(t, t + 0.75, n, ks=(0, 1, 2, 3), t_c=t + 0.85, t_h=t + 1.55); t += 2.2; n += 1
for nm, z, tok, sz in (('Google Cloud Pub/Sub', 4.6, 'google', 0.26), ('Amazon SNS', 4.0, 'amazon', 0.3)):
    c = chip(f'chip_{nm}', nm, (0, HY + 0.4, z), 'amber', sz)
    vis(c, W(tok, t_tools) - 0.12, None, pop=0.22, over=1.2)

# ---------- metaphor set: a radio station ----------
RC = Vector((12.0, 4.4, 0.0))
cyl('rt_plinth', (RC.x, RC.y, 0.05), 1.1, 0.1, M['plinth'], None, 48)
LEG0, LEG1 = 0.6, 0.1
legs = [(sx, sy) for sx in (-1, 1) for sy in (-1, 1)]
lp = lambda sx, sy, z: Vector((RC.x + sx * (LEG0 + (LEG1 - LEG0) * z / 3.4), RC.y + sy * (LEG0 + (LEG1 - LEG0) * z / 3.4), z))
for sx, sy in legs: beam(f'rt_leg{sx}{sy}', lp(sx, sy, 0.1), lp(sx, sy, 3.4), 0.035, M['steel'])
for zi, z in enumerate((0.9, 1.7, 2.5, 3.2)):
    ring = [lp(-1, -1, z), lp(1, -1, z), lp(1, 1, z), lp(-1, 1, z)]
    for q in range(4): beam(f'rt_b{zi}{q}', ring[q], ring[(q + 1) % 4], 0.02, M['steel'])
    if zi < 3:
        z2 = (0.9, 1.7, 2.5, 3.2)[zi + 1]
        beam(f'rt_x{zi}a', lp(-1, -1, z), lp(1, -1, z2), 0.016, M['steel']); beam(f'rt_x{zi}b', lp(1, -1, z), lp(-1, -1, z2), 0.016, M['steel'])
beam('rt_mast', (RC.x, RC.y, 3.4), (RC.x, RC.y, 4.3), 0.03, M['steel'])
tbeacon = mat('rt_beacon', VIOLET, 0.4, emit=5.0); BASE[tbeacon] = 4
sphere('rt_beacon', (RC.x, RC.y, 4.35), 0.11, tbeacon)
for zz in (3.55, 3.85):
    tr_ = torus(f'rt_dish{zz}', (RC.x, RC.y, zz), 0.16, 0.02, tbeacon); tr_.rotation_euler = (math.pi / 2, 0, 0)
t = 0.0
while t < 70: flash(tbeacon, t, 9, 0.35); t += 0.9
RADIOS = []
rpos = [(-75, 2.8), (-50, 2.6), (-25, 2.9), (0, 2.6), (25, 2.9), (50, 2.6), (75, 2.8), (145, 3.0), (180, 3.1), (215, 3.0)]
for i, (phi, rr) in enumerate(rpos):
    x, y = RC.x + rr * math.sin(math.radians(phi)), RC.y - rr * math.cos(math.radians(phi))
    r_ = empty(f'radio{i}', (x, y, 0), rot=(0, 0, math.radians(random.uniform(-12, 12))))
    rbox(f'rd{i}_pl', (0, 0, 0.03), (0.78, 0.44, 0.06), M['plinth'], r_, r=0.08)
    rbox(f'rd{i}_body', (0, 0, 0.3), (0.66, 0.32, 0.44), M['ceramic'], r_, r=0.07, bevel=0.015)
    sp = cyl(f'rd{i}_spk', (-0.14, -0.155, 0.3), 0.12, 0.02, M['hatch'], r_); sp.rotation_euler = (math.pi / 2, 0, 0)
    rm = mat(f'rd{i}_ring', CYAN, 0.4, emit=0.6); BASE[rm] = 0.6
    torus(f'rd{i}_ring', (-0.14, -0.166, 0.3), 0.13, 0.012, rm, r_)
    rbox(f'rd{i}_scr', (0.16, -0.16, 0.36), (0.22, 0.02, 0.12), M['glassblk'], r_, r=0.02, axis=1, bevel=0)
    text(f'rd{i}_fm', 'FM', (0.16, -0.172, 0.36), 0.06, M['t_cyan'], r_)
    cyl(f'rd{i}_knob', (0.16, -0.17, 0.2), 0.035, 0.03, M['ink'], r_).rotation_euler = (math.pi / 2, 0, 0)
    beam(f'rd{i}_ant', (0.24, 0.05, 0.5), (0.36, 0.08, 0.95), 0.008, M['steel'], r_)
    sphere(f'rd{i}_tip', (0.36, 0.08, 0.96), 0.02, M['steel'], r_)
    bars = [rbox(f'rd{i}_bar{q}', (-0.2 + q * 0.07, -0.05, 0.62), (0.04, 0.02, 0.18), rm, r_, r=0.015, axis=1, bevel=0) for q in range(3)]
    RADIOS.append((rr, rm, bars))
RING_T = t_bcast
rmat = mat('rt_wave', VIOLET, 0.4, emit=6.0)
wave = torus('rt_wave', (RC.x, RC.y, 0.35), 1.0, 0.035, rmat); wave.rotation_euler = (math.pi / 2, 0, 0)
keys(wave, 'scale', [(0, TINY), (RING_T - 0.05, TINY), (RING_T, (0.7, 0.7, 0.7)), (RING_T + 1.3, (4.2, 1, 4.2)), (RING_T + 1.36, TINY)], 'LINEAR')
emit_keys(rmat, [(RING_T, 7), (RING_T + 1.3, 0.5)], 'LINEAR')
wave2 = torus('rt_wave2', (RC.x, RC.y, 3.7), 1.0, 0.025, rmat); wave2.rotation_euler = (math.pi / 2, 0, 0)
keys(wave2, 'scale', [(0, TINY), (RING_T - 0.05, TINY), (RING_T, (0.3, 0.3, 0.3)), (RING_T + 0.9, (2.4, 1, 2.4)), (RING_T + 0.95, TINY)], 'LINEAR')
flash(tbeacon, RING_T, 20, 0.6)
for rr, rm, bars in RADIOS:
    ta = RING_T + (rr - 0.7) / 3.5 * 1.3
    color_keys(rm, [(0, CYAN), (ta, GREEN)])
    EM[rm] += [(ta - 0.01, 0.6), (ta + 0.08, 9), (ta + 0.5, 4)]; BASE[rm] = 0.6
    for q, b_ in enumerate(bars):
        pts = [(0, TINY), (ta - 0.01, TINY)]; t = ta
        while t < t_nf + 0.2: pts.append((t, (1, 1, random.uniform(0.25, 1.6)))); t += random.uniform(0.09, 0.16)
        keys(b_, 'scale', pts)
area('rtop', (RC.x, RC.y + 0.5, 9), (RC.x, RC.y, 0), 8.0, 700, '#EEF3FF')
area('rkey', (RC.x - 5, RC.y - 7.5, 6), (RC.x, RC.y, 1.2), 5.0, 600, '#FFF1E0')
area('rrim', (RC.x + 5, RC.y + 7, 4), (RC.x, RC.y, 1.2), 6.0, 500, VIOLET)
bc = chip('chip_bcast', 'BROADCAST ONCE', (RC.x, RC.y - 0.7, 4.45), 'violet', 0.24)
vis(bc, t_once, t_nf)
tt = chip('chip_station', 'STATION = TOPIC', (RC.x, RC.y - 1.3, 0.75), 'violet', 0.16)
vis(tt, W('station') - 0.05, t_nf)
rt2 = chip('chip_tuned', 'RADIOS = SUBSCRIBERS', (RC.x, RC.y - 3.4, 1.25), 'cyan', 0.15)
vis(rt2, W('tuned') - 0.1, t_nf)

for m, pts in EM.items():
    seen = {}
    for t, v in sorted(pts): seen[F(t)] = (t, v)
    emit_keys(m, [(0, BASE.get(m, 3))] + list(seen.values()), 'BEZIER')

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
PHc = (PHONE.x + 0.05, PHONE.y, PHONE.z - 0.05)
PHt = (PHONE.x + 0.35, PHONE.y, PHONE.z + 0.1)
FLD = (FC.x, 4.4, 0.6)
RAD = (RC.x, RC.y - 0.6, 1.4)
SHOTS = [  # (t, centre, visible width, lens, elevation, azimuth, lift, cut)
    (0.0, PHc, 1.75, 50, 10, -12, 0.1, False),
    (t_two - 0.08, PHc, 1.6, 50, 10, -12, 0.1, False),
    (t_two - 0.04, FLD, 4.6, 35, 18, -10, 0.06, True),
    (L(0, 2) - 0.05, FLD, 5.4, 35, 22, -2, 0.06, False),
    (L(0, 2), PHt, 2.3, 50, 10, -14, 0.06, True),
    (t_why - 0.05, PHt, 2.0, 50, 10, -8, 0.06, False),
    (t_why, (0.3, 4.6, 1.0), 7.4, 40, 36, 12, 0.1, True),
    (t_n, (0.4, 4.4, 1.0), 7.3, 40, 38, 6, 0.1, False),
    (t_spot - 0.05, (0.4, 4.3, 1.0), 7.2, 40, 38, 2, 0.1, False),
    (t_spot, (1.4, 7.0, 1.4), 3.7, 50, 14, -10, 0.04, True),
    (L(3, 0) - 0.05, (1.4, 7.0, 1.4), 3.4, 50, 14, -6, 0.04, False),
    (L(3, 0), (0.7, 4.7, 1.1), 6.2, 40, 32, -4, 0.1, True),
    (L(3, 1) - 0.05, (0.7, 4.8, 1.1), 6.0, 40, 32, -2, 0.1, False),
    (L(3, 1), (0.0, 5.6, 1.2), 7.2, 40, 30, -12, 0.1, True),
    (t_q - 0.05, (0.0, 5.6, 1.2), 6.8, 40, 30, -6, 0.1, False),
    (t_q, (0.0, 3.9, 0.8), 6.0, 40, 46, -10, 0.06, True),
    (t_fix - 0.05, (0.0, 3.8, 0.8), 5.6, 40, 46, -4, 0.06, False),
    (t_fix, (0.0, 4.4, 1.8), 6.0, 40, 22, 8, 0.06, True),
    (t_pub, (0.6, 5.0, 1.6), 6.8, 40, 28, 4, 0.06, False),
    (W('button', t_done) - 0.05, (0.6, 5.0, 1.6), 6.6, 40, 28, 0, 0.06, False),
    (W('button', t_done), PHt, 2.2, 50, 10, -12, 0.06, True),
    (L(6, 0) - 0.05, PHt, 2.0, 50, 10, -8, 0.06, False),
    (L(6, 0), (0.0, 2.6, 1.4), 7.4, 40, 36, -10, 0.08, True),
    (t_radio - 0.05, (0.0, 2.7, 1.4), 7.0, 40, 36, 4, 0.08, False),
    (t_radio, RAD, 6.4, 35, 20, -16, 0.04, True),
    (t_bcast, RAD, 7.4, 35, 24, -6, 0.04, False),
    (t_nf - 0.05, RAD, 7.8, 35, 24, 10, 0.04, False),
    (t_nf, (0.0, 4.0, 1.3), 8.0, 40, 34, -6, 0.1, True),
    (t_pay - 0.05, (0.0, 4.0, 1.3), 7.8, 40, 34, 4, 0.1, False),
    (t_pay, FLD, 5.2, 35, 22, -6, 0.06, True),
    (t_onepub - 0.05, FLD, 5.8, 35, 24, 2, 0.06, False),
    (t_onepub, (0.0, 4.2, 1.4), 8.2, 40, 34, -10, 0.1, True),
    (t_everyone - 0.05, (0.0, 4.2, 1.4), 8.0, 40, 34, -6, 0.1, False),
    (t_everyone, FLD, 5.6, 35, 26, 8, 0.06, True),
    (t_tools - 0.05, FLD, 6.4, 35, 26, 2, 0.06, False),
    (t_tools, (0.0, 4.2, 1.9), 8.6, 45, 30, -18, 0.11, True),
    (END, (0.0, 4.2, 1.9), 8.4, 45, 30, 18, 0.11, False),
]
prev = None
for t, c, wd, lens, el, az, lift, cut in SHOTS:
    p, g = place(c, wd, lens, el, az, lift)
    if cut and prev:
        key(cam, 'location', t - CUT, prev[0]); key(tgt, 'location', t - CUT, prev[1]); key(camd, 'lens', t - CUT, prev[2], 'CONSTANT')
    key(cam, 'location', t, p); key(tgt, 'location', t, g); key(camd, 'lens', t, lens, 'CONSTANT')
    prev = (p, g, lens)
sh = empty('shake', (0, 0, 0)); cam.parent = sh
for i, dt in enumerate([0, 0.05, 0.1, 0.15, 0.2, 0.26, 0.34]):   # a small jolt on "rewriting"
    a = 0.04 * (1 - i / 7)
    key(sh, 'location', t_rewrite + dt, (random.uniform(-a, a), 0, random.uniform(-a, a)) if 0 < i < 6 else (0, 0, 0))
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
rl = ng.nodes.new('CompositorNodeRLayers'); go = ng.nodes.new('NodeGroupOutput')
ng.links.new(rl.outputs['Image'], go.inputs[0])  # no bloom
if '--cover' in argv:   # cover art: one fixed wide shot of the whole system, framed low so the title has the top of the frame
    t = float(opt('--cover', t_same + 0.1))
    for ob in (cam, tgt, sh): ob.animation_data_clear()
    camd.animation_data_clear()
    p, g = place((0.0, 3.4, 1.4), 8.0, 45, 30, -14, -0.2)
    cam.location = p; tgt.location = g; camd.lens = 45; camd.dof.aperture_fstop = 5.6
    sc.render.use_motion_blur = False
    sc.frame_set(F(t)); sc.render.filepath = f'{OUT}/cover_art.png'; bpy.ops.render.render(write_still=True)
elif '--cutfix' in argv:   # the 2 frames around each camera cut, re-rendered without motion blur (blur would smear across the jump)
    sc.render.use_motion_blur = False
    for t in [s_[0] for s_ in SHOTS if s_[7]]:
        for fr in (F(t) - 1, F(t)):
            sc.frame_set(fr); sc.render.filepath = f'{OUT}/f_{fr:04d}.png'; bpy.ops.render.render(write_still=True)
elif STILLS:
    for s in STILLS:
        sc.frame_set(F(s)); sc.render.filepath = f'{OUT}/still_{s:05.2f}.png'; bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = f'{OUT}/f_'; bpy.ops.render.render(animation=True)
