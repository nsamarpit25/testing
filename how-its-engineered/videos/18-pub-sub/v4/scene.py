# 18 Pub/Sub, v3: isometric diorama (orthographic camera), neon-edged machines, services that react
# (NOTIFY bell rings, EMAIL mailbox flag pops, FEED card slides in, BADGES medal spins), a task-list screen on the post
# service, plug-in subscriptions on a topic hub, copies flying out together. Timed to voice/words.json.
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
INTER = {w: bpy.data.fonts.load(f'{D}/fonts/Inter-{w}.ttf') for w in ('Medium', 'SemiBold', 'Bold', 'ExtraBold')}
FONT = INTER['SemiBold']                     # every label, chip and phone screen uses Inter
PINK, YELLOW, BLUE, GOLD = '#F472B6', '#FACC15', '#3B82F6', '#F5C542'
for nm, h in (('pink', PINK), ('yellow', YELLOW), ('blue', BLUE)):
    M[nm] = mat(nm, h, 0.4, emit=3.0); M[f't_{nm}'] = mat(f't_{nm}', h, 0.4, emit=5.0)
M['t_white'] = mat('t_white', '#E8EEF8', 0.4, emit=4.0)
M['navy'] = mat('navy', '#2A3243', 0.36, 0.25, coat=0.35)
M['navy2'] = mat('navy2', '#232A39', 0.4, 0.25)
M['gold'] = mat('gold', GOLD, 0.25, 0.9, emit=0.4)
M['mailblue'] = mat('mailblue', '#2F6BEA', 0.3, 0.35, coat=0.4)
M['flagred'] = mat('flagred', '#FF3B4E', 0.35, emit=1.5)
M['steel'] = mat('steel', '#8F9AB0', 0.32, 0.85)
M['core'] = mat('core', VIOLET, 0.3, emit=6.0)
M['frost'] = mat('frost', '#EEF2F7', 0.45, emit=1.1, eh='#EEF2F7', coat=0.3)
M['inkt'] = mat('inkt', '#0F172A', 0.5)
M['dimt'] = mat('dimt', '#5B6475', 0.5)
M['gw'] = mat('gw', '#FFFFFF', 0.4, emit=3.0)
M['t_dim'] = mat('t_dim', '#8A93A6', 0.4, emit=2.5)
M['glassdk'] = mat('glassdk', '#0B111D', 0.22, alpha=0.92)

M['hazard'] = mat('hazard', AMBER, 0.4, emit=2.0)

# re-dress the stage: navy floor with a brighter grid, lights centred on this layout
br.inputs['Color1'].default_value = hx('#0D1322'); br.inputs['Color2'].default_value = hx('#0E1424'); br.inputs['Mortar'].default_value = hx('#18223A')
br.inputs['Mortar Size'].default_value = 0.009
w.node_tree.nodes['Background'].inputs['Color'].default_value = hx('#070B16')
def bev(ob, w=0.03):
    bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = w; bv.segments = 3; bv.limit_method = 'ANGLE'; ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); return ob
def aim(ob, loc, target): ob.location = loc; ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()

EM = defaultdict(list); BASE = {}          # emission events per material, written at the end
def flash(m, t, peak=12, dur=0.5):
    b = BASE.get(m, 3); EM[m] += [(t - 0.01, b), (t + 0.1, peak), (t + dur, b)]
def life(c, born, gone=None, s=(1, 1, 1)):
    pts = [(0, TINY), (born - 0.05, TINY), (born + 0.12, tuple(v * 1.1 for v in s)), (born + 0.2, s)]
    if gone is not None: pts += [(gone - 0.1, s), (gone, TINY)]
    keys(c, 'scale', pts)
def show(ob, ivs, pop=0.14, s=(1, 1, 1)):
    pts = [] if ivs[0][0] <= 0 else [(0, TINY)]
    for a_, b_ in ivs:
        if a_ <= 0: pts.append((0, s))
        else: pts += [(a_ - 0.05, TINY), (a_ + pop * 0.6, tuple(v * 1.08 for v in s)), (a_ + pop, s)]
        if b_ is not None: pts += [(b_ - 0.08, s), (b_, TINY)]
    keys(ob, 'scale', pts)
def swap(obs_times, end=None):
    for i, (ob, t0) in enumerate(obs_times):
        t1 = obs_times[i + 1][1] if i + 1 < len(obs_times) else end
        pts = [(0, TINY), (t0 - 1.0 / FPS, TINY), (t0, (1, 1, 1))] + ([(t1 - 1.0 / FPS, (1, 1, 1)), (t1, TINY)] if t1 is not None else [])
        keys(ob, 'scale', pts)
def mtext(name, body, loc, size, m, parent=None, align='LEFT', font=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = font or MONO; cu.size = size
    cu.align_x = align; cu.align_y = 'CENTER'; cu.extrude = 0.002
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = (math.pi / 2, 0, 0); return link(ob, m, parent)
def beam(name, a, b, r, m, parent=None):
    a, b = Vector(a), Vector(b); d = b - a
    root = empty(name, tuple(a), parent); root.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    cyl(f'{name}_c', (0, 0, d.length / 2), r, d.length, m, root, 12)
    return root
def grow3(root, t_on, t_off=None, dur=0.3):
    pts = [(0, (1, 1, 0.001)), (t_on, (1, 1, 0.001)), (t_on + dur, (1, 1, 1))]
    if t_off is not None: pts += [(t_off, (1, 1, 1)), (t_off + 0.25, (1, 1, 0.001))]
    keys(root, 'scale', pts)
def prism(name, pts2, depth, m, parent=None, loc=(0, 0, 0)):
    """flat polygon (x, z) extruded along y, facing -y."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    f = bm.faces.new([bm.verts.new((x, -depth / 2, z)) for x, z in pts2])
    bmesh.ops.extrude_face_region(bm, geom=[f]);
    for v in bm.verts:
        if abs(v.co.y + depth / 2) < 1e-6 and v not in f.verts: pass
    bm.verts.ensure_lookup_table()
    n = len(pts2)
    for v in bm.verts[n:]: v.co.y += depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc
    col.objects.link(ob); ob.data.materials.append(m)
    if parent: ob.parent = parent
    return ob
def outline(name, size, m, parent, c=(0, 0, 0), r=0.016):
    """neon edges on a box: 12 thin bars."""
    sx, sy, sz = size; cx, cy, cz = c
    for i, (ax, L_) in enumerate(((0, sx), (1, sy), (2, sz))):
        for a in (-1, 1):
            for b in (-1, 1):
                p = [0, 0, 0]; o = [i_ for i_ in range(3) if i_ != ax]
                p[o[0]] = a * size[o[0]] / 2; p[o[1]] = b * size[o[1]] / 2
                dims = [r * 2] * 3; dims[ax] = L_ + r * 2
                rbox(f'{name}_e{i}{a}{b}', (cx + p[0], cy + p[1], cz + p[2]), dims, m, parent, bevel=0)

# ---------- camera geometry: isometric, orthographic ----------
AZd, EL = -40.0, 42.0
AZ = math.radians(AZd)
RV = Vector((math.cos(AZ), math.sin(AZ), 0))   # screen-right on the floor
FW = Vector((-math.sin(AZ), math.cos(AZ), 0))  # screen-up on the floor (away from camera)
def S(u, v, z=0.0): p = RV * u + FW * v; return Vector((p.x, p.y, z))
FACE = AZ                                      # z rotation that turns a -y front straight at the camera
MROT = AZ + math.radians(14)                   # machines: front nearly at camera, one side face showing
CHIP_TILT = -math.radians(EL * 0.75)
for ob, loc, tg in ((TOP, S(0, -0.5, 12), S(0, -0.5, 0)), (KEYL, S(-6, -7, 8), S(0, -0.5, 0.6))):
    aim(ob, tuple(loc), tuple(tg))
for nm, loc, h in (('rimA', S(-6, 7, 5), CYAN), ('rimB', S(6, 7, 5), VIOLET)):
    area(nm, tuple(loc), tuple(S(0, 0, 0.5)), 7.0, 700, h)
area('fillF', tuple(S(5, -6, 4)), tuple(S(0, -1, 0.5)), 6.0, 500, '#9DB8FF')

def chip(name, body, loc, colname, size=0.2, parent=None, mono=False):
    root = empty(name, loc, parent, rot=(CHIP_TILT, 0, FACE if parent is None else 0))
    t = text(f'{name}_t', body, (0, -0.035, 0), size, M[f't_{colname}'], root)
    if mono: t.data.font = MONO
    bpy.context.view_layer.update()
    wd, h = t.dimensions.x + size * 1.3, size * 1.75
    rbox(f'{name}_bg', (0, 0, 0), (wd, 0.03, h), M['glassdk'], root, r=h / 2 * 0.98, axis=1, bevel=0)
    rbox(f'{name}_rim', (0, 0.012, 0), (wd + 0.022, 0.02, h + 0.022), M[colname], root, r=(h + 0.022) / 2 * 0.98, axis=1, bevel=0)
    return root
def ltext(name, body, loc, size, m, parent=None, w='SemiBold', align='LEFT'):
    return mtext(name, body, loc, size, m, parent, align, INTER[w])

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
t_radio, t_bcast, t_once = L(7, 0), W('broadcasts'), W('once', L(7, 0))
t_nf, t_sub2, t_never = L(8, 0), W('subscribe', L(8, 0)), W('never')
t_pay, t_onepub, t_everyone = L(9, 0), W('publish', L(9, 0)), W('everyone')
t_tools = L(10, 0)

# ---------- envelopes (the messages) ----------
NE = [0]
def envelope(stripe='amber'):
    n = NE[0]; NE[0] += 1
    root = empty(f'env{n}', (0, 0, -5), rot=(CHIP_TILT * 0.6, 0, FACE))
    rbox(f'env{n}_b', (0, 0, 0), (0.44, 0.04, 0.3), M['paper'], root, r=0.035, axis=1, bevel=0.006)
    prism(f'env{n}_f', [(-0.2, 0.13), (0.2, 0.13), (0, -0.01)], 0.006, mat(f'env{n}_fm', '#D9DEE8', 0.5), root, loc=(0, -0.024, 0))
    rbox(f'env{n}_a', (0, -0.028, -0.115), (0.4, 0.006, 0.025), M[stripe], root, r=0.01, axis=1, bevel=0)
    return root
def fly(e, pts, born, gone, spin=0.0):
    keys(e, 'location', [(t, tuple(p)) for t, p in pts])
    life(e, born, gone)
def arc(a, b, t0, t1, h=1.0, n=6):
    a, b = Vector(a), Vector(b); out = []
    for i in range(n + 1):
        u = i / n; p = a.lerp(b, u); p.z += h * 4 * u * (1 - u); out.append((t0 + (t1 - t0) * u, p))
    return out

# ---------- small white glyphs for app-style icon tiles ----------
def glyph(name, kind, parent, loc, s, bg='#FFFFFF'):
    g = empty(name, loc, parent)
    if kind == 'bell':
        prism(f'{name}_b', [(x * s, z * s) for x, z in [(-0.62, -0.42), (0.62, -0.42), (0.5, -0.28), (0.44, 0.18), (0.3, 0.44), (0, 0.56), (-0.3, 0.44), (-0.44, 0.18), (-0.5, -0.28)]], 0.01, M['gw'], g)
        c = cyl(f'{name}_c', (0, 0, -0.56 * s), 0.13 * s, 0.01, M['gw'], g, 16); c.rotation_euler = (math.pi / 2, 0, 0)
    elif kind == 'mail':
        rbox(f'{name}_r', (0, 0, 0), (1.3 * s, 0.01, 0.9 * s), M['gw'], g, r=0.08 * s, axis=1, bevel=0)
        prism(f'{name}_v', [(-0.62 * s, 0.42 * s), (0.62 * s, 0.42 * s), (0, -0.08 * s)], 0.006, mat(f'{name}_vm', bg, 0.4, emit=1.6), g, loc=(0, -0.009, 0))
    elif kind == 'feed':
        for i, (wd, z) in enumerate(((1.3, 0.42), (1.3, 0.0), (0.8, -0.42))):
            rbox(f'{name}_l{i}', ((wd - 1.3) / 2 * s, 0, z * s), (wd * s, 0.01, 0.22 * s), M['gw'], g, r=0.1 * s, axis=1, bevel=0)
    elif kind == 'badge':
        c = cyl(f'{name}_c', (0, 0, 0.18 * s), 0.46 * s, 0.01, M['gw'], g, 32); c.rotation_euler = (math.pi / 2, 0, 0)
        for sx in (-1, 1): prism(f'{name}_r{sx}', [(sx * 0.08 * s, -0.1 * s), (sx * 0.42 * s, -0.1 * s), (sx * 0.5 * s, -0.66 * s), (sx * 0.28 * s, -0.5 * s), (sx * 0.12 * s, -0.66 * s)], 0.01, M['gw'], g)
    elif kind == 'post':
        prism(f'{name}_p', [(x * s, z * s) for x, z in [(-0.6, -0.1), (0.62, 0.5), (0.1, -0.6), (-0.05, -0.15)]], 0.01, M['gw'], g)
    return g

# ---------- the post service: a sleek unit with a task screen ----------
PP = S(0, 3.7)
post = empty('post', tuple(PP), rot=(0, 0, MROT))
pband = mat('post_band', AMBER, 0.4, emit=4.0); BASE[pband] = 4
rbox('post_plinth', (0, 0, 0.04), (2.1, 1.6, 0.08), M['plinth'], post, r=0.16)
bev(rbox('post_body', (0, 0, 0.73), (1.9, 1.4, 1.3), M['navy'], post, r=0.14, bevel=0), 0.02)
rbox('post_cap', (0, 0, 1.385), (1.7, 1.2, 0.02), M['hatch'], post, r=0.1, bevel=0)
pr_ = torus('post_port', (0, 0.1, 1.4), 0.26, 0.025, pband, post); pr_.rotation_euler = (math.pi / 2, 0, 0)
rbox('post_strip', (0, -0.705, 0.15), (1.6, 0.02, 0.03), pband, post, r=0.012, axis=1, bevel=0)
SCR = empty('post_scr', (0, -0.71, 0.8), post)
rbox('scr_bg', (0, 0.005, 0), (1.7, 0.02, 0.96), M['glassblk'], SCR, r=0.08, axis=1, bevel=0)
pt_ = rbox('scr_tile', (-0.7, -0.012, 0.35), (0.16, 0.01, 0.16), mat('post_tile', AMBER, 0.4, emit=1.8), SCR, r=0.04, axis=1, bevel=0)
glyph('scr_gl', 'post', SCR, (-0.7, -0.02, 0.35), 0.06)
ltext('scr_title', 'Post service', (-0.58, -0.012, 0.35), 0.085, M['t_white'], SCR, 'Bold')
ltext('scr_sub', 'create_post()', (0.75, -0.012, 0.35), 0.06, M['t_dim'], SCR, 'Medium', 'RIGHT')
rbox('scr_sep', (0, -0.012, 0.25), (1.56, 0.004, 0.006), M['card'], SCR, bevel=0)
RZ = [0.13, -0.02, -0.17, -0.32, -0.47 + 0.08]
RZ = [0.13, -0.01, -0.15, -0.29, -0.41]
TASKS = [('Notify followers', 't_white'), ('Send emails', 't_white'), ('Update feeds', 't_white'), ('Award badges', 't_red'), ('New feature #5', 't_red')]
rows, fills, checks, rowm = [], [], [], []
for i, (txt, tm) in enumerate(TASKS):
    r_ = empty(f'row{i}', (0, -0.01, RZ[i]), SCR)
    rbox(f'row{i}_box', (-0.7, 0, 0), (0.075, 0.006, 0.075), M['grey'], r_, r=0.018, axis=1, bevel=0)
    rbox(f'row{i}_boxin', (-0.7, -0.004, 0), (0.052, 0.006, 0.052), M['glassblk'], r_, r=0.012, axis=1, bevel=0)
    ck = rbox(f'row{i}_ck', (-0.7, -0.008, 0), (0.075, 0.006, 0.075), M['green'], r_, r=0.018, axis=1, bevel=0)
    ltext(f'row{i}_t', txt, (-0.6, -0.006, 0), 0.068, M[tm], r_, 'Medium')
    rbox(f'row{i}_bar', (0.45, 0, 0), (0.42, 0.006, 0.036), M['card'], r_, r=0.018, axis=1, bevel=0)
    fa = empty(f'row{i}_fa', (0.24, -0.006, 0), r_)
    fm = mat(f'row{i}_fill', AMBER, 0.4, emit=4.0)
    rbox(f'row{i}_fill', (0.21, 0, 0), (0.42, 0.006, 0.036), fm, fa, r=0.018, axis=1, bevel=0)
    rows.append(r_); fills.append(fa); checks.append(ck); rowm.append(fm)
pubrow = empty('pubrow', (0, -0.01, 0.1), SCR)
mtext('pub_t', 'publish("new-post")', (-0.6, -0.006, 0), 0.075, M['t_violet'], pubrow)
rbox('pub_box', (-0.7, 0, 0), (0.075, 0.006, 0.075), M['grey'], pubrow, r=0.018, axis=1, bevel=0)
pck = rbox('pub_ck', (-0.7, -0.008, 0), (0.075, 0.006, 0.075), M['green'], pubrow, r=0.018, axis=1, bevel=0)
donet = ltext('pub_done', 'Done.', (-0.6, -0.006, -0.12), 0.08, M['t_green'], SCR, 'Bold')
zero = ltext('zero', '0 lines changed', (-0.6, -0.006, -0.3), 0.068, M['t_green'], SCR, 'Medium')
def fill(i, t0, t1, col=AMBER):
    keys(fills[i], 'scale', [(0, (0.001, 1, 1)), (t0, (0.001, 1, 1)), (t1, (1, 1, 1))])
for i in range(5): keys(checks[i], 'scale', [(0, TINY)])

# ---------- the creator's phone ----------
PH = S(-2.15, 3.9, 1.05)
ph = empty('phone', tuple(PH), rot=(math.radians(-16), 0, FACE))
rbox('ph_body', (0, 0, 0), (0.76, 0.07, 1.48), M['phone'], ph, r=0.12, axis=1, bevel=0.02)
rbox('ph_scr', (0, -0.036, 0), (0.68, 0.005, 1.4), M['screen'], ph, r=0.09, axis=1, bevel=0)
rbox('ph_notch', (0, -0.04, 0.63), (0.18, 0.004, 0.045), M['dark'], ph, r=0.022, axis=1, bevel=0)
SY = -0.042
def ui(name): return empty(name, (0, 0, 0), ph)
s0 = ui('ui_compose')
text('u0_t', 'NEW POST', (0, SY, 0.55), 0.07, M['t_grey'], s0)
rbox('u0_card', (0, SY + 0.002, 0.15), (0.58, 0.004, 0.62), M['card'], s0, r=0.05, axis=1, bevel=0)
rbox('u0_img', (0, SY - 0.001, 0.25), (0.5, 0.004, 0.34), M['violet'], s0, r=0.04, axis=1, bevel=0)
sphere('u0_sun', (0.13, SY - 0.004, 0.33), 0.045, M['amber'], s0)
rbox('u0_l1', (-0.03, SY - 0.001, 0.0), (0.42, 0.004, 0.035), M['grey'], s0, r=0.017, axis=1, bevel=0)
btn = empty('u0_btn', (0, SY - 0.002, -0.4), s0)
rbox('u0_b', (0, 0, 0), (0.56, 0.004, 0.16), M['btn'], btn, r=0.078, axis=1, bevel=0)
text('u0_bt', 'SHARE', (0, -0.003, 0), 0.075, M['ink'], btn)
tapr = torus('u0_tap', (0, SY - 0.01, -0.4), 0.12, 0.012, M['white'], ph)
keys(tapr, 'scale', [(0, TINY), (t_post - 0.06, TINY), (t_post, (0.4, 0.4, 0.4)), (t_post + 0.35, (2.2, 1, 2.2)), (t_post + 0.36, TINY)])
s1 = ui('ui_wait')
spin = empty('u1_spin', (0, SY, 0.3), s1)
for i in range(10):
    a = 2 * math.pi * i / 10
    sphere(f'u1_d{i}', (0.13 * math.cos(a), 0, 0.13 * math.sin(a)), 0.012 + 0.0025 * i, M['white'] if i > 4 else M['grey'], spin)
text('u1_t', 'SHARING...', (0, SY, 0.06), 0.07, M['white'], s1)
text('u1_t2', 'notifying followers', (0, SY, -0.06), 0.045, M['t_grey'], s1)
rbox('u1_bar', (0, SY, -0.18), (0.5, 0.004, 0.04), M['card'], s1, r=0.02, axis=1, bevel=0)
pfa = empty('u1_fa', (-0.25, SY - 0.002, -0.18), s1)
rbox('u1_fill', (0.25, 0, 0), (0.5, 0.004, 0.04), M['amber'], pfa, r=0.02, axis=1, bevel=0)
keys(pfa, 'scale', [(0, (0.02, 1, 1)), (t_stops - 0.4, (0.09, 1, 1)), (t_stops, (1, 1, 1))])
TIMER = empty('u1_timer', (0, SY - 0.002, -0.42), s1)
rbox('u1_tbg', (0, 0.002, 0), (0.5, 0.004, 0.16), M['chipbg'], TIMER, r=0.078, axis=1, bevel=0)
runs, t = [], t_post + 0.2
while t < t_stops:
    sec = int((t - t_post) * 4.2)
    runs.append((text(f'tm_{len(runs)}', f'{sec // 60}:{sec % 60:02d}', (0, -0.004, 0), 0.085, M['t_red'], TIMER), t)); t += 0.25
swap(runs, t_stops)
s3 = ui('ui_ok')
torus('u3_ring', (0, SY, 0.22), 0.15, 0.018, M['green'], s3)
text('u3_ok', 'OK', (0, SY, 0.22), 0.11, M['t_green'], s3)
text('u3_t', 'SHARED', (0, SY, -0.05), 0.08, M['t_green'], s3)
text('u3_t2', 'to 2M followers', (0, SY, -0.16), 0.05, M['t_grey'], s3)
show(s0, [(0, t_post + 0.12)]); show(s1, [(t_post + 0.14, t_stops)]); show(s3, [(t_stops + 0.02, None)])
keys(btn, 'scale', [(0, (1, 1, 1)), (t_post - 0.12, (1, 1, 1)), (t_post - 0.02, (0.88, 1, 0.82)), (t_post + 0.12, (1, 1, 1))])
keys(spin, 'rotation_euler', [(0, (0, 0, 0)), (END, (0, -2 * math.pi * END * 1.4, 0))], 'LINEAR')
pcount = [('3', t_post + 0.3), ('9', t_two + 0.6), ('14', L(0, 2)), ('22', t_btn), ('31', t_spinning)]
cnt_runs = [(text(f'pc_{i}', f'{v} of 2,000,000', (0, SY, 0.52), 0.052, M['t_white'], s1), tt) for i, (v, tt) in enumerate(pcount)]
swap(cnt_runs, t_stops)
still = chip('chip_still', 'STILL SHARING...', tuple(PH + Vector((0, 0, 1.0))), 'red', 0.12)
vis(still, t_spinning, t_why)

# ---------- subscriber services: sleek modules that pop a notification card ----------
SV = [('Notify', CYAN, 'cyan', S(-1.35, -2.35), 'bell', ('New post', '@creator just posted')),
      ('Email', BLUE, 'blue', S(1.35, -2.35), 'mail', ('Email sent', 'New post from @creator')),
      ('Feed', PINK, 'pink', S(-1.35, -4.85), 'feed', ('Feed updated', '1 new post on top')),
      ('Badges', YELLOW, 'yellow', S(1.35, -4.85), 'badge', ('Badge unlocked', 'Top creator'))]
svc, sband, stile = [], [], []
def module(k):
    title, accent, cn, pos, kind, _ = SV[k]; name = title.upper()
    root = empty(name, tuple(pos), rot=(0, 0, MROT))
    band = mat(f'{name}_band', accent, 0.4, emit=4.0); BASE[band] = 4
    tm = mat(f'{name}_tile', accent, 0.4, emit=1.8); BASE[tm] = 1.8
    rbox(f'{name}_plinth', (0, 0, 0.03), (1.3, 1.1, 0.06), M['plinth'], root, r=0.12)
    bev(rbox(f'{name}_body', (0, 0, 0.56), (1.12, 0.92, 1.0), M['navy'], root, r=0.11, bevel=0), 0.015)
    rbox(f'{name}_cap', (0, 0, 1.065), (0.96, 0.76, 0.02), M['hatch'], root, r=0.08, bevel=0)
    pr_ = torus(f'{name}_port', (0, 0.05, 1.075), 0.17, 0.02, band, root); pr_.rotation_euler = (math.pi / 2, 0, 0)
    rbox(f'{name}_strip', (0, -0.465, 0.12), (0.96, 0.02, 0.025), band, root, r=0.012, axis=1, bevel=0)
    rbox(f'{name}_panel', (0, -0.465, 0.64), (0.98, 0.02, 0.66), M['glassblk'], root, r=0.07, axis=1, bevel=0)
    rbox(f'{name}_tilet', (-0.27, -0.478, 0.74), (0.3, 0.015, 0.3), tm, root, r=0.07, axis=1, bevel=0)
    glyph(f'{name}_gl', kind, root, (-0.27, -0.49, 0.74), 0.1, accent)
    ltext(f'{name}_t', title, (-0.08, -0.48, 0.79), 0.12, M['t_white'], root, 'Bold')
    ltext(f'{name}_s', 'subscriber', (-0.08, -0.48, 0.66), 0.065, M['t_dim'], root, 'Medium')
    rbox(f'{name}_bar', (0, -0.48, 0.44), (0.8, 0.01, 0.028), M['card'], root, r=0.014, axis=1, bevel=0)
    rbox(f'{name}_barl', (0, -0.485, 0.44), (0.8, 0.01, 0.028), band, root, r=0.014, axis=1, bevel=0)
    sphere(f'{name}_led', (0.36, -0.48, 0.86), 0.022, band, root)
    pl = point(f'{name}_pool', (0, 0, 0), 4, accent, 0.4); pl.parent = root; pl.location = (0, -0.9, 0.3)
    return root, band, tm
for k in range(4):
    r_, b_, t_ = module(k); svc.append(r_); sband.append(b_); stile.append(t_)
nb, eb, fb_, bb = svc
eband = sband[1]
NP = [0]
def popup(k, t, hold=1.15):
    """an iOS-style notification card rising out of service k."""
    title, accent, cn, pos, kind, (l1, l2) = SV[k]; n = NP[0]; NP[0] += 1
    c = empty(f'pop{n}', (0, 0, -5), rot=(CHIP_TILT, 0, FACE))
    rbox(f'pop{n}_bg', (0, 0, 0), (1.42, 0.03, 0.44), M['frost'], c, r=0.12, axis=1, bevel=0)
    rbox(f'pop{n}_tile', (-0.5, -0.02, 0), (0.26, 0.015, 0.26), stile[k], c, r=0.06, axis=1, bevel=0)
    glyph(f'pop{n}_gl', kind, c, (-0.5, -0.03, 0), 0.085, accent)
    ltext(f'pop{n}_t', l1, (-0.32, -0.03, 0.065), 0.095, M['inkt'], c, 'Bold')
    ltext(f'pop{n}_s', l2, (-0.32, -0.03, -0.085), 0.068, M['dimt'], c, 'Medium')
    ltext(f'pop{n}_n', 'now', (0.62, -0.03, 0.065), 0.06, M['dimt'], c, 'Medium', 'RIGHT')
    base_ = pos + Vector((0, 0, 1.7)) - FW * 0.15
    P_ = 1.5                                   # big enough to read at 480p
    keys(c, 'location', [(t - 0.01, tuple(base_)), (t + 0.3, tuple(base_ + Vector((0, 0, 0.45)))), (t + hold, tuple(base_ + Vector((0, 0, 0.55))))])
    keys(c, 'scale', [(0, TINY), (t - 0.01, TINY), (t + 0.16, (P_ * 1.06,) * 3), (t + 0.26, (P_,) * 3), (t + hold - 0.12, (P_,) * 3), (t + hold, TINY)])
def react(k, t, card=True):
    flash(sband[k], t, 14, 0.6); flash(stile[k], t, 7, 0.6)
    if card: popup(k, t + 0.05)
RECV = {k: SV[k][3] + Vector((0, 0, 1.7)) for k in range(4)}
SINK = {k: SV[k][3] + Vector((0, 0, 1.08)) for k in range(4)}
OUTP = PP + Vector((0, 0, 1.45))
def deliver(k, t_arr, src=None, t0=None, h=1.0, stripe='amber'):
    src = Vector(src) if src is not None else OUTP
    t0 = t0 if t0 is not None else t_arr - 0.75
    e = envelope(stripe)
    pts = ([(t0 - 0.12, src - Vector((0, 0, 0.3)))] if src == OUTP else []) + arc(src, RECV[k], t0, t_arr, h) + [(t_arr + 0.18, SINK[k])]
    fly(e, pts, pts[0][0], t_arr + 0.18)
    react(k, t_arr + 0.12)
    return e

# BADGES is not part of the system until "new feature"
keys(bb, 'scale', [(0, TINY), (t_sub2 - 0.35, TINY), (t_sub2 - 0.3, (1, 1, 1))])
keys(bb, 'location', [(0, tuple(SV[3][3] + Vector((0, 0, 7)))), (t_sub2 - 0.3, tuple(SV[3][3] + Vector((0, 0, 7)))), (t_sub2, tuple(SV[3][3] - Vector((0, 0, 0.05)))),
                      (t_sub2 + 0.1, tuple(SV[3][3] + Vector((0, 0, 0.04)))), (t_sub2 + 0.2, tuple(SV[3][3]))])
# the empty slot for a future feature: a dashed outline
slot = empty('slot', tuple(SV[3][3]), rot=(0, 0, MROT))
slm = mat('slotm', '#5A6B8F', 0.4, emit=1.5)
for i in range(4):
    for j in range(5):
        a_ = i * math.pi / 2; L_ = 1.12 if i % 2 == 0 else 0.92; o_ = (0.92 if i % 2 == 0 else 1.12) / 2
        d_ = -L_ / 2 + (j + 0.5) * L_ / 5
        x_, y_ = (d_, -o_) if i == 0 else (o_, d_) if i == 1 else (-d_, o_) if i == 2 else (-o_, -d_)
        rbox(f'slot{i}{j}', (x_, y_, 0.02), (0.13 if i % 2 == 0 else 0.03, 0.03 if i % 2 == 0 else 0.13, 0.02), slm, slot, bevel=0)
plus = text('slot_plus', '+', (0, 0, 0.03), 0.5, mat('slotplus', '#5A6B8F', 0.4, emit=2), slot, flat=True)
keys(slot, 'scale', [(0, (1, 1, 1)), (t_sub2 - 0.1, (1, 1, 1)), (t_sub2, TINY)])

# ---------- part 1: the post service does every job itself, one after another ----------
dm = mat('dwire', AMBER, 0.4, emit=1.8)
dwire = []
for k in range(3):
    a_, b_ = PP + Vector((0, 0, 0.06)), SV[k][3] + Vector((0, 0, 0.06))
    d = (b_ - a_); d.z = 0; a2 = a_ + d.normalized() * 0.95; b2 = b_ - d.normalized() * 0.65
    wr = beam(f'dwire{k}', a2, b2, 0.018, dm); dwire.append(wr)
    grow3(wr, t_why + 0.5 + k * 0.15, t_q, 0.4)
show(rows[0], [(t_why + 0.3, t_fix + 0.9)]); show(rows[1], [(t_why + 0.45, t_fix + 0.95)]); show(rows[2], [(t_why + 0.6, t_fix + 1.0)])
show(rows[3], [(t_rewrite, t_fix + 1.05)], pop=0.2); show(rows[4], [(t_again, t_fix + 1.1)], pop=0.2)
for i, tt in enumerate((t_n, t_e, t_f)):
    fill(i, tt - 0.6, tt + 0.1)
    deliver(i, tt + 0.15, t0=tt - 0.55)
    keys(checks[i], 'scale', [(0, TINY), (tt + 0.1, TINY), (tt + 0.22, (1.2, 1, 1.2)), (tt + 0.3, (1, 1, 1)), (t_spot + 1.3, (1, 1, 1)), (t_spot + 1.35, TINY)])
# "one after another": the rows blink in order
for i in range(3): flash(rowm[i], t_oaa + i * 0.28, 14, 0.35)
seq = chip('chip_seq', 'ONE AFTER ANOTHER', tuple(PP + Vector((0, 0, 2.05))), 'amber', 0.16)
vis(seq, t_oaa, t_spot)
# spot the problem: the room dims, a spot on the task list
spot = point('spot', tuple(S(0, 1.2, 6.0)), 0, '#FFFFFF', 0.3, kind='SPOT')
spot.data.spot_size = math.radians(26); spot.data.spot_blend = 0.5
aim(spot, tuple(S(0, 1.2, 6.0)), tuple(PP + Vector((0, 0, 0.8))))
keys(spot.data, 'energy', [(0, 0), (t_spot - 0.01, 0), (t_spot, 1600), (L(3, 0) - 0.01, 1600), (L(3, 0), 0)])
keys(TOP.data, 'energy', [(0, 2600), (t_spot - 0.01, 2600), (t_spot, 600), (L(3, 0) - 0.01, 600), (L(3, 0), 2600)])
keys(KEYL.data, 'energy', [(0, 1700), (t_spot - 0.01, 1700), (t_spot, 450), (L(3, 0) - 0.01, 450), (L(3, 0), 1700)])
qmark = chip('chip_spotq', '?', tuple(PP + RV * 1.35 + Vector((0, 0, 1.95)) - FW * 0.6), 'red', 0.26)
vis(qmark, t_spot + 0.15, L(3, 0), pop=0.22, over=1.3)
# email is slow: the bar crawls red, an hourglass over the mailbox, the post waits
for i in range(3): keys(fills[i], 'scale', [(t_spot + 1.3, (1, 1, 1)), (t_spot + 1.36, (0.001, 1, 1))])
fill(0, L(3, 0) + 0.05, L(3, 0) + 0.45)
keys(checks[0], 'scale', [(L(3, 0) + 0.45, TINY), (L(3, 0) + 0.55, (1, 1, 1)), (t_fix + 0.8, (1, 1, 1))])
keys(fills[1], 'scale', [(L(3, 0) + 0.5, (0.001, 1, 1)), (t_slow, (0.1, 1, 1)), (t_q, (0.32, 1, 1))], 'LINEAR')
color_keys(rowm[1], [(0, AMBER), (t_slow, RED), (t_fix, AMBER)])
deliver(0, L(3, 0) + 0.4, t0=L(3, 0) - 0.1)
eslow = envelope()
pts = [(L(3, 0) + 0.35, OUTP - Vector((0, 0, 0.3)))] + arc(OUTP, RECV[1] + Vector((0, 0, 0.35)), L(3, 0) + 0.45, t_slow, 1.0)
fly(eslow, pts + [(t_q - 0.3, RECV[1] + Vector((0, 0, 0.35))), (t_q - 0.1, SINK[1])], pts[0][0], t_q - 0.1)
spn = empty('slowspin', tuple(SV[1][3] + Vector((0, 0, 1.38)) - FW * 0.05), rot=(CHIP_TILT, 0, FACE))
for q in range(10):
    a = 2 * math.pi * q / 10
    sphere(f'ssp{q}', (0.16 * math.cos(a), 0, 0.16 * math.sin(a)), 0.014 + 0.003 * q, M['amber'] if q > 4 else M['grey'], spn)
show(spn, [(t_slow, t_q)], pop=0.2)
keys(spn, 'rotation_euler', [(t_slow, (CHIP_TILT, 0, FACE)), (t_q, (CHIP_TILT, -2 * math.pi * (t_q - t_slow) * 1.2, FACE))], 'LINEAR')
color_keys(stile[1], [(0, BLUE), (t_slow, AMBER), (t_q, BLUE)])
color_keys(eband, [(0, BLUE), (t_slow, AMBER), (t_q, BLUE)])
slow = chip('chip_slow', 'SLOW', tuple(SV[1][3] + Vector((0, 0, 2.2))), 'amber', 0.2)
vis(slow, t_slow + 0.05, t_q)
waitc = chip('chip_wait', 'POST WAITS...', tuple(PP + Vector((0, 0, 2.05))), 'red', 0.16)
vis(waitc, t_waits, t_rewrite - 0.05)
# every new feature means rewriting the post service. again.
color_keys(pband, [(0, AMBER), (t_rewrite, RED), (t_q, AMBER)])
t = t_rewrite
while t < t_q - 0.3: EM[pband] += [(t, 4), (t + 0.1, 12), (t + 0.3, 1.5)]; t += 0.4
EM[pband].append((t_q, 4))
rew = chip('chip_rewrite', 'REWRITE + REDEPLOY', tuple(PP + Vector((0, 0, 2.15))), 'red', 0.15)
vis(rew, t_rewrite + 0.1, t_q)
again = chip('chip_again', 'AGAIN', tuple(PP + Vector((0.0, 0, 2.55))), 'red', 0.16)
vis(again, t_again, t_q, over=1.3)
def shake(ob, t, base_loc, a=0.05):
    pts = [(t - 0.02, base_loc)]
    for q in range(7): pts.append((t + 0.04 * (q + 1), tuple(Vector(base_loc) + Vector((random.uniform(-a, a), random.uniform(-a, a), 0)) * (1 - q / 7))))
    pts.append((t + 0.33, base_loc)); keys(ob, 'location', pts)
keys(post, 'location', [(0, tuple(PP))]); shake(post, t_rewrite, tuple(PP)); shake(post, t_again, tuple(PP))
ghost_s = chip('chip_slotnew', 'NEW FEATURE?', tuple(SV[3][3] + Vector((0, 0, 0.9))), 'grey', 0.14)
vis(ghost_s, t_new, t_q)

# ---------- part 2: a queue gives each message to just one worker ----------
conv = empty('conv', tuple(S(0, 0.6, -1.2)), rot=(0, 0, AZ))
rbox('cv_base', (0, 0, 0.14), (0.8, 3.6, 0.18), M['navy2'], conv, r=0.05, bevel=0.01)
cvm = mat('cv_edge', CYAN, 0.4, emit=3.0)
for sx in (-0.41, 0.41): rbox(f'cv_e{sx}', (sx, 0, 0.24), (0.03, 3.6, 0.03), cvm, conv, bevel=0)
ROLL = []
for i in range(12):
    rl_ = cyl(f'cv_r{i}', (0, -1.65 + i * 0.3, 0.25), 0.05, 0.72, M['steel'], conv, 16); rl_.rotation_euler = (0, math.pi / 2, 0); ROLL.append(rl_)
keys(conv, 'location', [(0, tuple(S(0, 0.6, -1.2))), (t_queue - 0.15, tuple(S(0, 0.6, -1.2))), (t_queue + 0.15, tuple(S(0, 0.6, 0.04))), (t_queue + 0.25, tuple(S(0, 0.6, 0))),
                        (t_fix + 0.1, tuple(S(0, 0.6, 0))), (t_fix + 0.45, tuple(S(0, 0.6, -1.2)))])
for rl_ in ROLL: keys(rl_, 'rotation_euler', [(t_queue, (0, math.pi / 2, 0)), (t_fix, (-20, math.pi / 2, 0))], 'LINEAR')
mq = chip('chip_mq', 'MESSAGE QUEUE', tuple(S(1.25, 0.9, 0.7)), 'cyan', 0.16)
vis(mq, t_queue + 0.3, t_fix)
tq = t_q + 1.2
eq = envelope('cyan')
qa, qb = S(0, 2.3, 0.45), S(0, -1.0, 0.45)
pts = [(tq - 0.1, OUTP - Vector((0, 0, 0.3))), (tq + 0.15, OUTP)] + arc(OUTP, qa, tq + 0.15, tq + 0.6, 0.6)[1:] + [(t_one - 0.7, qb)] + arc(qb, RECV[1], t_one - 0.7, t_one, 0.9)[1:] + [(t_one + 0.18, SINK[1])]
fly(eq, pts, tq - 0.1, t_one + 0.18)
react(1, t_one + 0.12)
for k in (0, 2):
    q_ = chip(f'chip_nope{k}', '?', tuple(SV[k][3] + Vector((0, 0, 2.0 if k == 0 else 1.9))), 'grey', 0.24)
    vis(q_, t_one + 0.15 + k * 0.05, t_fix)
only = chip('chip_only', 'ONLY ONE GETS IT', tuple(S(0, -3.6, 2.55)), 'amber', 0.17)
vis(only, t_one + 0.2, t_fix)

# ---------- part 3: pub/sub ----------
HP = S(0, 0.2)
hub = empty('hub', tuple(HP - Vector((0, 0, 1.4))), rot=(0, 0, MROT))
hband = mat('hub_band', VIOLET, 0.4, emit=4.0); BASE[hband] = 4
bev(cyl('hub_plinth', (0, 0, 0.04), 1.05, 0.08, M['plinth'], hub, 48), 0.02)
bev(cyl('hub_body', (0, 0, 0.3), 0.85, 0.44, M['navy'], hub, 48), 0.02)
for z_ in (0.08, 0.52):
    tr_ = torus(f'hub_ring{z_}', (0, 0, z_), 0.86, 0.022, hband, hub); tr_.rotation_euler = (math.pi / 2, 0, 0)
dome = sphere('hub_dome', (0, 0, 0.52), 0.62, M['glass'], hub); dome.scale = (1, 1, 0.75)
core = sphere('hub_core', (0, 0, 0.78), 0.2, M['core'], hub); BASE[M['core']] = 6
hub_lbl = chip('chip_topic', 'TOPIC: new-post', (0, -0.98, 0.3), 'violet', 0.12, parent=hub)
hub_lbl.rotation_euler = (CHIP_TILT * 0.4, 0, FACE - MROT)
keys(hub, 'location', [(0, tuple(HP - Vector((0, 0, 1.4)))), (t_ps - 0.25, tuple(HP - Vector((0, 0, 1.4)))), (t_ps, tuple(HP + Vector((0, 0, 0.08)))), (t_ps + 0.12, tuple(HP - Vector((0, 0, 0.03)))), (t_ps + 0.22, tuple(HP))])
hpool = point('hub_pool', tuple(HP + Vector((0, 0, 1.6))), 0, VIOLET, 0.8)
keys(hpool.data, 'energy', [(0, 0), (t_ps - 0.05, 0), (t_ps + 0.05, 160), (t_ps + 0.8, 40)])
flash(M['core'], t_ps, 18, 0.8)
for i in range(2):
    rm = mat(f'puff{i}', VIOLET, 0.4, emit=5.0)
    pr = torus(f'puff{i}', tuple(HP + Vector((0, 0, 0.04))), 1.0, 0.03, rm); pr.rotation_euler = (math.pi / 2, 0, 0)
    t0 = t_ps + 0.05 + i * 0.15
    keys(pr, 'scale', [(0, TINY), (t0 - 0.05, TINY), (t0, (0.9, 0.9, 0.9)), (t0 + 0.8, (3.4, 1, 3.4)), (t0 + 0.85, TINY)], 'LINEAR')
    emit_keys(rm, [(t0, 6), (t0 + 0.8, 0.3)], 'LINEAR')
pss = chip('chip_pubsub', 'PUB/SUB', tuple(HP + Vector((0, 0, 2.1))), 'violet', 0.32)
vis(pss, t_ps + 0.1, t_pub - 0.1, pop=0.22, over=1.25)
HUBIN = HP + Vector((0, 0, 0.85))
def hub_pulse(t):
    flash(M['core'], t, 20, 0.5); flash(hband, t, 12, 0.5)
    keys(core, 'scale', [(t - 0.02, (1, 1, 1)), (t + 0.1, (1.5, 1.5, 1.5)), (t + 0.4, (1, 1, 1))])
# the task list collapses into one publish line
for i in range(5): keys(rows[i], 'location', [(t_fix + 0.6, (0, -0.01, RZ[i])), (t_fix + 0.9 + i * 0.05, (-1.4, -0.01, RZ[i]))])
show(pubrow, [(t_pub - 0.3, None)], pop=0.2)
keys(pck, 'scale', [(0, TINY), (t_done - 0.05, TINY), (t_done + 0.1, (1.2, 1, 1.2)), (t_done + 0.2, (1, 1, 1))])
show(donet, [(t_done, None)], pop=0.2)
show(zero, [(t_never, t_pay)], pop=0.2)
# publish: one envelope, POST -> topic
def publish(t0, t_arr, ks, t_c, t_h, stripe='amber'):
    e = envelope(stripe)
    pts = [(t0 - 0.12, OUTP - Vector((0, 0, 0.3)))] + arc(OUTP, HUBIN, t0, t_arr, 1.1)
    fly(e, pts, t0 - 0.12, t_arr + 0.02)
    hub_pulse(t_arr)
    for k in ks:
        c = envelope('violet')
        p2 = arc(HUBIN + Vector((0, 0, 0.1)), RECV[k], t_c, t_h, 0.9) + [(t_h + 0.18, SINK[k])]
        fly(c, p2, t_c, t_h + 0.18)
        react(k, t_h + 0.12)
    if ks: hub_pulse(t_c)
publish(t_pub, t_topic, (0, 1, 2), t_copy - 0.05, t_same - 0.05)
dn = chip('chip_done', 'DONE', tuple(PP + Vector((0, 0, 2.05))), 'green', 0.2)
vis(dn, t_done, t_subs, over=1.25)
flash(pband, t_done, 12)
# subscribe: every service plugs a cable into the topic
SOCK, PLUG = [], []
for k in range(4):
    d = (SV[k][3] - HP); d.z = 0; d = d.normalized()
    sp = HP + d * 0.87 + Vector((0, 0, 0.26))
    so = empty(f'sock{k}', tuple(sp), rot=(0, 0, math.atan2(d.x, -d.y)))
    sm = mat(f'sock{k}', '#3A4566', 0.4, emit=1.0); BASE[sm] = 1.0
    rbox(f'sock{k}_b', (0, 0, 0), (0.2, 0.06, 0.16), M['dark'], so, r=0.03, axis=1, bevel=0)
    tr_ = torus(f'sock{k}_r', (0, -0.035, 0), 0.1, 0.014, sm, so)
    keys(so, 'scale', [(0, TINY), (t_ps, TINY), (t_ps + 0.25, (1, 1, 1))])
    a_ = SV[k][3] + Vector((0, 0, 0.12)) - d * 0.55
    pl = empty(f'plug{k}', tuple(a_), rot=(0, 0, math.atan2(d.x, -d.y)))
    rbox(f'plug{k}_b', (0, 0, 0), (0.16, 0.2, 0.12), mat(f'plugm{k}', SV[k][1], 0.4, emit=1.5), pl, r=0.03, bevel=0)
    for s in (-1, 1): rbox(f'plug{k}_p{s}', (s * 0.035, 0.13, 0), (0.02, 0.08, 0.02), M['steel'], pl, bevel=0)
    SOCK.append((sp, sm, d)); PLUG.append((pl, a_))
smat = mat('scab', VIOLET, 0.4, emit=2.2)
def plug_in(k, t):
    sp, sm, d = SOCK[k]; pl, a_ = PLUG[k]
    end = sp - d * 0.17
    mid = a_.lerp(end, 0.5) + Vector((0, 0, 0.6))
    keys(pl, 'location', [(0, tuple(a_)), (t - 0.01, tuple(a_)), (t + 0.25, tuple(mid)), (t + 0.45, tuple(end - d * (-0.06))), (t + 0.5, tuple(end))])
    keys(pl, 'scale', [(0, TINY), (t - 0.05, TINY), (t, (1, 1, 1))])
    cb = beam(f'scab{k}', a_, end, 0.025, smat); grow3(cb, t + 0.1, None, 0.4)
    color_keys(sm, [(0, '#3A4566'), (t + 0.5, VIOLET)]); EM[sm] += [(t + 0.49, 1.0), (t + 0.55, 12), (t + 0.9, 4)]
    clk = chip(f'chip_click{k}', 'CLICK', tuple(sp + Vector((0, 0, 0.55))), 'violet', 0.09)
    vis(clk, t + 0.5, t + 1.1, pop=0.15, over=1.3)
for k in range(3): plug_in(k, t_subs + k * 0.22)
cp = chip('chip_copy', 'EVERYONE GETS A COPY', tuple(HP + Vector((0, 0, 2.1))), 'violet', 0.16)
vis(cp, t_copy - 0.05, t_radio)
# new feature: BADGES drops into the empty slot and plugs in. POST: 0 lines changed
plug_in(3, t_sub2 + 0.35)
nc = chip('chip_nochange', 'NO CHANGES', tuple(PP + Vector((0, 0, 2.05))), 'green', 0.19)
vis(nc, t_never, t_pay)
flash(pband, t_never, 10, 0.8); color_keys(pband, [(t_never, GREEN), (t_pay, AMBER)])
# payoff + ending
publish(t_onepub - 0.3, t_onepub + 0.25, (0, 1, 2, 3), t_onepub + 0.3, t_everyone - 0.05)
t = t_tools + 0.2
while t < END - 1.6:
    publish(t, t + 0.7, (0, 1, 2, 3), t + 0.78, t + 1.45); t += 2.2
for nm, z, sz in (('Google Cloud Pub/Sub', 1.95, 0.2), ('Amazon SNS', 1.5, 0.24)):
    c = chip(f'chip_{nm}', nm, tuple(HP + Vector((0, 0, z))), 'amber', sz)
    vis(c, W(nm.split()[0].lower(), t_tools) - 0.12, None, pop=0.22, over=1.2)

# ---------- the field of phones (hook + payoff) ----------
FC = S(-14, 0)
fbanner = mat('fbanner', WHITE, 0.4, emit=3.0)
FG = 6
fscr = [mat(f'fscr{g}', '#070B14', 0.2, emit=0.15, eh='#4FB8FF') for g in range(FG)]
fbody = mat('fbody', '#121826', 0.45, 0.25)
BUZZ = t_everyone + 0.04
for g, m in enumerate(fscr):
    d_ = BUZZ + g * 0.035
    emit_keys(m, [(0, 0.15), (d_ - 0.01, 0.15), (d_ + 0.06, 4.5), (d_ + 0.6, 1.4)], 'BEZIER')
EARLY = random.sample([(i, j) for i in range(9) for j in range(11)], 6)
for i in range(9):
    for j in range(11):
        p = FC + RV * ((i - 4) * 0.6 + random.uniform(-0.08, 0.08)) + FW * ((j - 5) * 0.72 + random.uniform(-0.1, 0.1))
        g = random.randrange(FG)
        r_ = empty(f'fp{i}_{j}', (p.x, p.y, 0), rot=(math.radians(-12), 0, FACE + random.uniform(-0.12, 0.12)))
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
area('ftop', tuple(FC + Vector((0, 0, 9))), tuple(FC), 8.0, 550, '#EEF3FF')
area('fkey', tuple(FC + S(-4, -6, 6)), tuple(FC + Vector((0, 0, 0.4))), 5.0, 450, '#FFF1E0')
area('frim', tuple(FC + S(3, 7, 4)), tuple(FC + Vector((0, 0, 0.4))), 6.0, 500, CYAN)
CNT = tuple(FC + FW * (-3.4) + Vector((0, 0, 2.3)))
DB = empty('dash', CNT, rot=(CHIP_TILT, 0, FACE))
rbox('db_bg', (0, 0, 0), (2.7, 0.03, 1.08), M['glassdk'], DB, r=0.16, axis=1, bevel=0)
rbox('db_rim', (0, 0.012, 0), (2.72, 0.02, 1.1), mat('db_rim', '#3A4A6B', 0.4, emit=1.5), DB, r=0.17, axis=1, bevel=0)
ltext('db_lbl', 'FOLLOWERS NOTIFIED', (-1.18, -0.035, 0.34), 0.085, M['t_dim'], DB, 'SemiBold')
dlive = sphere('db_live', (1.12, -0.035, 0.345), 0.03, M['red'], DB)
ltext('db_of', 'of 2,000,000', (1.18, -0.035, -0.02), 0.1, M['t_dim'], DB, 'Medium', 'RIGHT')
rbox('db_bar', (0, -0.03, -0.32), (2.36, 0.01, 0.06), M['card'], DB, r=0.03, axis=1, bevel=0)
dfa = empty('db_fa', (-1.18, -0.035, -0.32), DB)
dfm = mat('db_fill', AMBER, 0.4, emit=3.5)
rbox('db_fill', (1.18, 0, 0), (2.36, 0.01, 0.06), dfm, dfa, r=0.03, axis=1, bevel=0)
show(DB, [(t_two, t_why), (t_pay, None)], pop=0.18)
def nums(tag, vals, green_last=False):
    out = []
    for i, (v, t) in enumerate(vals):
        m_ = M['t_green'] if (green_last and i == len(vals) - 1) else M['t_white']
        out.append((ltext(f'db_{tag}{i}', f'{v:,}', (-1.18, -0.035, -0.02), 0.34, m_, DB, 'ExtraBold'), t))
    return out
hook_v = [(0, t_two), (3, t_two + 0.55), (9, t_two + 0.93), (14, t_two + 1.31), (22, t_two + 1.69), (31, t_two + 2.07)]
swap(nums('a', hook_v), t_why)
pay_v = [(0, t_pay)] + [(int(2_000_000 * (1 - (1 - q / 14) ** 3)), BUZZ + 0.02 + q * 0.045) for q in range(1, 15)]
swap(nums('b', pay_v, True), None)
fpts = [(0, (0.002, 1, 1)), (t_two, (0.002, 1, 1)), (t_why, (0.004, 1, 1)), (t_pay, (0.002, 1, 1)), (BUZZ, (0.002, 1, 1)), (BUZZ + 0.65, (1, 1, 1))]
keys(dfa, 'scale', fpts)
color_keys(dfm, [(0, AMBER), (BUZZ + 0.65, GREEN)])
done_t = ltext('db_done', 'Delivered', (1.18, -0.035, 0.34), 0.085, M['t_green'], DB, 'Bold', 'RIGHT')
keys(done_t, 'scale', [(0, TINY), (BUZZ + 0.66, TINY), (BUZZ + 0.8, (1, 1, 1))])
keys(dlive, 'scale', [(0, (1, 1, 1)), (BUZZ + 0.64, (1, 1, 1)), (BUZZ + 0.66, TINY)])

# ---------- the radio station (metaphor) ----------
RC = S(14, 0)
cyl('rt_plinth', (RC.x, RC.y, 0.05), 1.1, 0.1, M['plinth'], None, 48)
LEG0, LEG1 = 0.6, 0.1
lp = lambda sx, sy, z: Vector((RC.x + sx * (LEG0 + (LEG1 - LEG0) * z / 3.4), RC.y + sy * (LEG0 + (LEG1 - LEG0) * z / 3.4), z))
for sx in (-1, 1):
    for sy in (-1, 1): beam(f'rt_leg{sx}{sy}', lp(sx, sy, 0.1), lp(sx, sy, 3.4), 0.035, M['steel'])
ZL = (0.9, 1.7, 2.5, 3.2)
for zi, z in enumerate(ZL):
    ring = [lp(-1, -1, z), lp(1, -1, z), lp(1, 1, z), lp(-1, 1, z)]
    for q in range(4): beam(f'rt_b{zi}{q}', ring[q], ring[(q + 1) % 4], 0.02, M['steel'])
    if zi < 3:
        for (s1, s2) in (((-1, -1), (1, -1)), ((-1, -1), (-1, 1))):
            beam(f'rt_x{zi}{s1}{s2}a', lp(*s1, z), lp(*s2, ZL[zi + 1]), 0.015, M['steel']); beam(f'rt_x{zi}{s1}{s2}b', lp(*s2, z), lp(*s1, ZL[zi + 1]), 0.015, M['steel'])
beam('rt_mast', (RC.x, RC.y, 3.4), (RC.x, RC.y, 4.3), 0.03, M['steel'])
tbeacon = mat('rt_beacon', VIOLET, 0.4, emit=5.0); BASE[tbeacon] = 4
sphere('rt_beacon', (RC.x, RC.y, 4.35), 0.11, tbeacon)
t = 0.0
while t < 70: flash(tbeacon, t, 9, 0.35); t += 0.9
RADIOS = []
for i in range(10):
    phi = [-80, -55, -30, -5, 20, 45, 70, 140, 175, 210][i]; rr = [2.7, 2.5, 2.8, 2.5, 2.8, 2.5, 2.7, 3.0, 3.1, 3.0][i]
    p = RC + RV * (rr * math.sin(math.radians(phi))) - FW * (rr * math.cos(math.radians(phi)))
    r_ = empty(f'radio{i}', (p.x, p.y, 0), rot=(0, 0, FACE + math.radians(random.uniform(-14, 14))))
    rbox(f'rd{i}_pl', (0, 0, 0.03), (0.78, 0.44, 0.06), M['plinth'], r_, r=0.08)
    rbox(f'rd{i}_body', (0, 0, 0.3), (0.66, 0.32, 0.44), M['navy'], r_, r=0.07, bevel=0.015)
    sp_ = cyl(f'rd{i}_spk', (-0.14, -0.155, 0.3), 0.12, 0.02, M['hatch'], r_); sp_.rotation_euler = (math.pi / 2, 0, 0)
    rm = mat(f'rd{i}_ring', CYAN, 0.4, emit=0.6); BASE[rm] = 0.6
    torus(f'rd{i}_ring', (-0.14, -0.166, 0.3), 0.13, 0.012, rm, r_)
    rbox(f'rd{i}_scr', (0.16, -0.16, 0.36), (0.22, 0.02, 0.12), M['glassblk'], r_, r=0.02, axis=1, bevel=0)
    beam(f'rd{i}_ant', (0.24, 0.05, 0.5), (0.36, 0.08, 0.95), 0.008, M['steel'], r_)
    sphere(f'rd{i}_tip', (0.36, 0.08, 0.96), 0.02, M['steel'], r_)
    bars = [rbox(f'rd{i}_bar{q}', (-0.2 + q * 0.07, -0.05, 0.62), (0.04, 0.02, 0.18), rm, r_, r=0.015, axis=1, bevel=0) for q in range(3)]
    RADIOS.append((rr, rm, bars))
rmat = mat('rt_wave', VIOLET, 0.4, emit=6.0)
wave = torus('rt_wave', (RC.x, RC.y, 0.35), 1.0, 0.035, rmat); wave.rotation_euler = (math.pi / 2, 0, 0)
keys(wave, 'scale', [(0, TINY), (t_bcast - 0.05, TINY), (t_bcast, (0.7, 0.7, 0.7)), (t_bcast + 1.3, (4.2, 1, 4.2)), (t_bcast + 1.36, TINY)], 'LINEAR')
emit_keys(rmat, [(t_bcast, 7), (t_bcast + 1.3, 0.5)], 'LINEAR')
wave2 = torus('rt_wave2', (RC.x, RC.y, 3.7), 1.0, 0.025, rmat); wave2.rotation_euler = (math.pi / 2, 0, 0)
keys(wave2, 'scale', [(0, TINY), (t_bcast - 0.05, TINY), (t_bcast, (0.3, 0.3, 0.3)), (t_bcast + 0.9, (2.4, 1, 2.4)), (t_bcast + 0.95, TINY)], 'LINEAR')
flash(tbeacon, t_bcast, 20, 0.6)
for rr, rm, bars in RADIOS:
    ta = t_bcast + (rr - 0.7) / 3.5 * 1.3
    color_keys(rm, [(0, CYAN), (ta, GREEN)])
    EM[rm] += [(ta - 0.01, 0.6), (ta + 0.08, 9), (ta + 0.5, 4)]
    for q, b_ in enumerate(bars):
        pts = [(0, TINY), (ta - 0.01, TINY)]; t = ta
        while t < t_nf + 0.2: pts.append((t, (1, 1, random.uniform(0.25, 1.6)))); t += random.uniform(0.09, 0.16)
        keys(b_, 'scale', pts)
area('rtop', tuple(RC + Vector((0, 0, 9))), tuple(RC), 8.0, 700, '#EEF3FF')
area('rkey', tuple(RC + S(-5, -7, 6)), tuple(RC + Vector((0, 0, 1.2))), 5.0, 600, '#FFF1E0')
area('rrim', tuple(RC + S(5, 7, 4)), tuple(RC + Vector((0, 0, 1.2))), 6.0, 500, VIOLET)
bc = chip('chip_bcast', 'BROADCAST ONCE', tuple(RC + Vector((0, 0, 4.85))), 'violet', 0.24)
vis(bc, t_once, t_nf)
tt = chip('chip_station', 'STATION = TOPIC', tuple(RC - FW * 1.2 + Vector((0, 0, 0.6))), 'violet', 0.16)
vis(tt, W('station') - 0.05, t_nf)
rt2 = chip('chip_tuned', 'RADIOS = SUBSCRIBERS', tuple(RC - FW * 3.4 + Vector((0, 0, 1.15))), 'cyan', 0.15)
vis(rt2, W('tuned') - 0.1, t_nf)

for m, pts in EM.items():
    seen = {}
    for t, v in sorted(pts): seen[F(t)] = (t, v)
    emit_keys(m, [(0, BASE.get(m, 3))] + list(seen.values()), 'BEZIER')

# ---------- camera: orthographic iso, moving between close-ups ----------
tgt = empty('tgt'); camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd)
col.objects.link(cam); sc.camera = cam
tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
camd.type = 'ORTHO'; camd.clip_end = 300; camd.clip_start = 0.5
CUT = 1.0 / FPS
def place(c, H, el, az):
    g = Vector(c); a_ = math.radians(az); e_ = math.radians(el)
    p = g + 40 * Vector((math.sin(a_) * math.cos(e_), -math.cos(a_) * math.cos(e_), math.sin(e_)))
    return tuple(p), tuple(g), H * 9 / 16 if False else H
def V(u, v, z=0.0): return tuple(S(u, v, z))
PHV = tuple(PH + Vector((0, 0, -0.05)))
FLD = tuple(FC + Vector((0, 0, 0.4)))
RAD = tuple(RC + Vector((0, 0, 2.0)) - FW * 0.6)
SCRV = tuple(PP + Vector((0, 0, 0.85)) - FW * 0.2)
SHOTS = [  # (t, centre, ortho height, elevation, azimuth, cut)
    (0.0, PHV, 3.04, 14, AZd, False),
    (t_two - 0.06, PHV, 2.64, 14, AZd + 4, False),
    (t_two - 0.02, FLD, 7.35, 26, AZd - 6, True),
    (L(0, 2) - 0.05, FLD, 8.19, 28, AZd + 2, False),
    (L(0, 2), PHV, 2.9, 14, AZd - 4, True),
    (t_why - 0.05, PHV, 2.64, 14, AZd + 2, False),
    (t_why, SCRV, 4.61, 22, AZd + 4, True),
    (t_n - 0.6, SCRV, 4.35, 22, AZd + 2, False),
    (t_n - 0.1, V(0, 0.0, 0.7), 11.0, EL, AZd, False),
    (t_spot - 0.25, V(0, -0.2, 0.7), 11.0, EL, AZd + 4, False),
    (t_spot, SCRV, 3.71, 20, AZd + 2, False),
    (L(3, 0) - 0.05, SCRV, 3.46, 20, AZd + 4, False),
    (L(3, 0) + 0.25, V(0.6, 0.8, 0.8), 9.68, EL, AZd + 6, False),
    (t_rewrite - 0.4, V(0.6, 0.8, 0.8), 9.2, EL, AZd + 2, False),
    (t_rewrite - 0.1, V(-0.1, 3.4, 1.1), 5.43, 28, AZd - 4, False),
    (t_q - 0.25, V(-0.1, 3.4, 1.1), 5.07, 28, AZd, False),
    (t_q + 0.15, V(0, -0.4, 0.7), 11.0, EL, AZd - 4, False),
    (t_fix - 0.1, V(0, -0.4, 0.7), 11.0, EL, AZd + 2, False),
    (t_fix + 0.3, V(0, 1.0, 0.8), 8.26, 34, AZd + 2, False),
    (t_topic, V(0, 1.6, 0.9), 8.73, 36, AZd - 2, False),
    (W('button', t_done) - 0.05, V(0, 1.6, 0.9), 8.73, 36, AZd - 4, False),
    (W('button', t_done), PHV, 2.9, 14, AZd, True),
    (L(6, 0) - 0.05, PHV, 2.64, 14, AZd + 3, False),
    (L(6, 0), V(0, -1.0, 0.7), 11.0, EL, AZd - 6, True),
    (t_radio - 0.05, V(0, -1.0, 0.7), 11.0, EL, AZd + 2, False),
    (t_radio, RAD, 8.74, 26, AZd - 10, True),
    (t_nf - 0.05, RAD, 9.66, 28, AZd + 8, False),
    (t_nf, V(0, -1.2, 0.7), 11.0, EL, AZd + 4, True),
    (t_never - 0.3, V(0, -1.2, 0.7), 11.0, EL, AZd, False),
    (t_never + 0.05, SCRV, 4.61, 22, AZd + 2, False),
    (t_pay - 0.05, SCRV, 4.35, 22, AZd + 4, False),
    (t_pay, FLD, 7.35, 26, AZd - 4, True),
    (t_onepub - 0.05, FLD, 7.98, 28, AZd + 2, False),
    (t_onepub, V(0, -0.8, 0.7), 11.0, EL, AZd - 4, True),
    (t_everyone - 0.05, V(0, -0.8, 0.7), 11.0, EL, AZd, False),
    (t_everyone, FLD, 7.77, 28, AZd + 4, True),
    (t_tools - 0.05, FLD, 8.61, 30, AZd - 2, False),
    (t_tools, V(0, -0.6, 1.2), 11.6, EL - 4, AZd - 8, True),
    (END, V(0, -0.6, 1.2), 11.2, EL - 4, AZd + 8, False),
]
prev = None
for t, c, H, el, az, cut in SHOTS:
    p, g, _ = place(c, H, el, az)
    if cut and prev:
        key(cam, 'location', t - CUT, prev[0]); key(tgt, 'location', t - CUT, prev[1]); key(camd, 'ortho_scale', t - CUT, prev[2])
    key(cam, 'location', t, p); key(tgt, 'location', t, g); key(camd, 'ortho_scale', t, H)
    prev = (p, g, H)
sh = empty('shake', (0, 0, 0)); cam.parent = sh
for tt in (t_rewrite, t_again):
    for i, dt in enumerate([0, 0.05, 0.1, 0.15, 0.2, 0.26, 0.34]):
        a = 0.05 * (1 - i / 7)
        key(sh, 'location', tt + dt, (random.uniform(-a, a), 0, random.uniform(-a, a)) if 0 < i < 6 else (0, 0, 0))
key(sh, 'location', 0, (0, 0, 0))

# ---------- render ----------
sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = SAMPLES
ee.use_shadows = True; ee.use_raytracing = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
ee.volumetric_tile_size = '8'; ee.volumetric_samples = 48; ee.volumetric_end = 120; ee.use_volumetric_shadows = True
sc.render.resolution_x, sc.render.resolution_y = RES, int(RES * 16 / 9) // 2 * 2
sc.render.resolution_percentage = 100; sc.render.fps = FPS
a, b = [int(x) for x in opt('--range', f'1,{F(END)}').split(',')]
sc.frame_start, sc.frame_end = a, b
sc.render.image_settings.file_format = 'PNG'
if '--skip' in argv: sc.render.use_overwrite = False; sc.render.use_placeholder = True
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new('CompositorNodeRLayers'); go = ng.nodes.new('NodeGroupOutput')
ng.links.new(rl.outputs['Image'], go.inputs[0])  # no bloom
if '--cover' in argv:
    t = float(opt('--cover', t_same + 0.1))
    for ob in (cam, tgt, sh): ob.animation_data_clear()
    camd.animation_data_clear()
    p, g, _ = place(V(0, -1.4, 0.7), 10.5, EL, AZd)
    cam.location = p; tgt.location = g; camd.ortho_scale = 10.5
    sc.render.use_motion_blur = False
    sc.frame_set(F(t)); sc.render.filepath = f'{OUT}/cover_art.png'; bpy.ops.render.render(write_still=True)
elif '--cutfix' in argv:
    sc.render.use_motion_blur = False
    for t in [s_[0] for s_ in SHOTS if s_[5]]:
        for fr in (F(t) - 1, F(t)):
            sc.frame_set(fr); sc.render.filepath = f'{OUT}/f_{fr:04d}.png'; bpy.ops.render.render(write_still=True)
elif STILLS:
    for s in STILLS:
        sc.frame_set(F(s)); sc.render.filepath = f'{OUT}/still_{s:05.2f}.png'; bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = f'{OUT}/f_'; bpy.ops.render.render(animation=True)
