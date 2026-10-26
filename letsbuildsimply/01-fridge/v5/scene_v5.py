"""@letsbuildsimply ep: How a block of ice becomes a fridge (v5).  Cold open on the finished fridge, then the icebox grows into it in one cutaway.

blender -b -y -P scene.py -- --timings voice/timings.json --out out [--frames A:B] [--stills 1.0,20.5] [--samples 48] [--res 480]
Everything is driven by state(t) per frame (no keyframes), so render runs frame by frame inside this script.
Also writes out/anchors.json (screen positions of label anchors + thermometer reading) for the overlay.
"""
import bpy, json, math, os, random, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None):
    return argv[argv.index(k) + 1] if k in argv else d
TIM = json.load(open(arg('--timings', 'voice/timings.json')))
OUT = arg('--out', 'out'); os.makedirs(OUT, exist_ok=True)
FPS = 30; RES = int(arg('--res', '480')); SAMPLES = int(arg('--samples', '48'))
DUR = TIM['dur'] + 0.6
NF = int(math.ceil(DUR * FPS))
random.seed(7)

# ---------------------------------------------------------------- timing helpers
LS = [l['s'] for l in TIM['lines']]; LE = [l['e'] for l in TIM['lines']]
norm = lambda s: ''.join(c for c in s.lower() if c.isalpha())
def ws(li, word, nth=0):
    hits = [w for w in TIM['lines'][li]['words'] if norm(w['w']).startswith(norm(word))]
    return hits[nth]['s']
def we(li, word, nth=0):
    hits = [w for w in TIM['lines'][li]['words'] if norm(w['w']).startswith(norm(word))]
    return hits[nth]['e']
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
def ss(t, a, b):  # smootherstep 0..1 between a and b
    if b <= a: return 1.0 if t >= b else 0.0
    x = clamp((t - a) / (b - a)); return x * x * x * (x * (x * 6 - 15) + 10)
def lin(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= b)
def win(t, a, b, fi=0.25, fo=0.25): return ss(t, a, a + fi) * (1 - ss(t, b - fo, b))
def back_out(x, s=1.70158):  # overshoot ease for pop-ins
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def pop(t, a, d=0.35): return back_out(lin(t, a, a + d)) if t >= a else 0.0
def mix(a, b, f): return tuple(x + (y - x) * f for x, y in zip(a, b))
def sched(t, pts):  # piecewise smooth through (time, value)
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1: return v0 + (v1 - v0) * ss(t, t0, t1)
    return pts[-1][1]

# ---------------------------------------------------------------- key times (v5 script, Puck take 2)
T = dict(
    hundred=ws(1, 'hundred'), wooden=ws(1, 'wooden'), iceblk=ws(1, 'block'), slam=LE[1] - 0.05,
    brill=ws(2, 'brilliantly'), twod=ws(2, 'two'), days=ws(2, 'days'),
    then=LS[3], puddle=ws(3, 'puddle'), yog=ws(3, 'yogurt'),
    thing=LS[4], cant=ws(4, 'cant'), only=ws(4, 'only'), heatout=ws(4, 'heat'),
    swap=ws(5, 'swap'), pipe=ws(5, 'pipe'), filled=ws(5, 'filled'), minus=ws(5, 'minus'),
    boiling=LS[6], drinks=ws(6, 'drinks'), food=ws(6, 'food'), evap=ws(6, 'evaporator'),
    gas=ws(7, 'gas'), escape=ws(7, 'escape'),
    trap=ws(8, 'trap'), crush=ws(8, 'crush'), pump=ws(8, 'pump'), comp=ws(8, 'compressor'),
    hot=LS[9], burn=ws(9, 'burn'), fingers=ws(9, 'fingers'),
    perfect=LS[10], snake=ws(10, 'snake'), pours=ws(10, 'pours'), cond=ws(10, 'condenser'),
    warmline=LS[11], warm=ws(11, 'warm'),
    cools=LS[12], liquid=ws(12, 'liquid'), tight=ws(12, 'tight'),
    push=LS[13], spaghetti=ws(13, 'spaghetti'), pressure=ws(13, 'pressure'), drops=ws(13, 'drops'), cap=ws(13, 'capillary'),
    round=LS[14], forever=ws(14, 'forever'),
    problem=LS[15], lettuce=ws(15, 'lettuce'), glass=ws(15, 'glass'),
    sensor=ws(16, 'sensor'), cuts=ws(16, 'cuts'), thermo=ws(16, 'thermostat'),
    click=ws(17, 'click'), hum=ws(17, 'hum'), stop=ws(17, 'stops'), night=ws(17, 'night'),
    foam=ws(18, 'foam'), seal=ws(18, 'seal'), light=ws(18, 'light'), congrats=ws(18, 'congratulations'),
    never=LS[19], moves=ws(19, 'moves'), milk=ws(19, 'milk'), kitchen=ws(19, 'kitchen'),
)
END = LE[19]
# ---------------------------------------------------------------- scene reset + render setup
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.render.resolution_x, sc.render.resolution_y = (RES, int(round(RES * 16 / 9 / 2)) * 2)
sc.render.resolution_percentage = 100
sc.render.fps = FPS
sc.render.film_transparent = False
sc.render.use_persistent_data = True
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.cycles.transmission_bounces = 6; sc.cycles.glossy_bounces = 3
sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.cycles.blur_glossy = 1.0
try:
    pr = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            pr.compute_device_type = kind; pr.get_devices()
            if any(d.type == kind for d in pr.devices):
                for d in pr.devices: d.use = d.type == kind
                sc.cycles.device = 'GPU'; print('GPU', kind); break
        except TypeError:
            pass
except Exception as e:
    print('no gpu', e)
try:
    sc.cycles.denoiser = 'OPTIX' if sc.cycles.device == 'GPU' else 'OPENIMAGEDENOISE'
except Exception:
    pass
sc.view_settings.view_transform = 'AgX'
for look in ('AgX - Medium High Contrast', 'AgX - Punchy', 'Medium High Contrast'):
    try: sc.view_settings.look = look; break
    except TypeError: pass
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'

# ---------------------------------------------------------------- materials
def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']
def pset(b, **kw):
    names = {'color': 'Base Color', 'metal': 'Metallic', 'rough': 'Roughness', 'trans': 'Transmission Weight', 'ior': 'IOR',
             'emit': 'Emission Color', 'estr': 'Emission Strength', 'alpha': 'Alpha', 'coat': 'Coat Weight', 'sss': 'Subsurface Weight',
             'sssr': 'Subsurface Radius', 'spec': 'Specular IOR Level'}
    for k, v in kw.items():
        sock = b.inputs[names[k]]
        sock.default_value = (*v, 1.0) if k in ('color', 'emit') and len(v) == 3 else v
def mat(name, color, rough=0.5, **kw):
    m, n, l, b = node_mat(name); pset(b, color=color, rough=rough, **kw); return m
def P(m): return m.node_tree.nodes['Principled BSDF']

def wood_mat(name, c1, c2, scale=(60, 60, 1.2)):
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = scale
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.0; nz.inputs['Detail'].default_value = 8
    wv = n.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 0.35; wv.inputs['Distortion'].default_value = 1.2
    wv.inputs['Detail'].default_value = 4
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*c1, 1); ramp.color_ramp.elements[1].color = (*c2, 1)
    l.new(tc.outputs['Object'], mp.inputs['Vector']); l.new(mp.outputs['Vector'], nz.inputs['Vector']); l.new(mp.outputs['Vector'], wv.inputs['Vector'])
    mx = n.new('ShaderNodeMix'); mx.data_type = 'FLOAT'; mx.inputs['Factor'].default_value = 0.65
    l.new(nz.outputs['Fac'], mx.inputs[2]); l.new(wv.outputs['Fac'], mx.inputs[3]); l.new(mx.outputs[0], ramp.inputs['Fac'])
    # 'steel' factor: wood -> white enamel (driven per frame)
    final = n.new('ShaderNodeMix'); final.data_type = 'RGBA'; final.inputs['Factor'].default_value = 0.0
    final.inputs[7].default_value = (0.93, 0.94, 0.95, 1)
    l.new(ramp.outputs['Color'], final.inputs[6]); l.new(final.outputs[2], b.inputs['Base Color'])
    pset(b, rough=0.5, coat=0.15); m['mixnode'] = final.name
    return m
def set_steel(m, f):
    m.node_tree.nodes[m['mixnode']].inputs['Factor'].default_value = f
    pset(P(m), rough=0.55 - 0.33 * f, coat=0.6 * f)

def dot_mat():  # emissive dot colored per object (Object Info color, alpha)
    m, n, l, b = node_mat('dot')
    oi = n.new('ShaderNodeObjectInfo')
    l.new(oi.outputs['Color'], b.inputs['Base Color']); l.new(oi.outputs['Color'], b.inputs['Emission Color'])
    pset(b, rough=0.3, estr=0.9)
    return m
def wisp_mat():  # soft translucent puff colored per object; alpha from object color alpha
    m, n, l, b = node_mat('wisp')
    out = n['Material Output']; oi = n.new('ShaderNodeObjectInfo')
    em = n.new('ShaderNodeEmission'); tr = n.new('ShaderNodeBsdfTransparent'); mx = n.new('ShaderNodeMixShader')
    lw = n.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.45
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    l.new(lw.outputs['Facing'], inv.inputs[1]); l.new(inv.outputs[0], mul.inputs[0]); l.new(oi.outputs['Alpha'], mul.inputs[1])
    l.new(oi.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.2
    l.new(mul.outputs[0], mx.inputs['Fac']); l.new(tr.outputs[0], mx.inputs[1]); l.new(em.outputs[0], mx.inputs[2])
    l.new(mx.outputs[0], out.inputs['Surface'])
    return m

M = dict(
    wall=mat('wall', (0.22, 0.45, 0.47), 0.85),
    base=mat('baseboard', (0.95, 0.94, 0.9), 0.4),
    floor=wood_mat('floor', (0.2, 0.1, 0.045), (0.36, 0.2, 0.09), scale=(1.5, 30, 30)),
    slab=mat('slab', (0.42, 0.40, 0.38), 0.9),
    box=wood_mat('box', (0.28, 0.13, 0.05), (0.5, 0.27, 0.11)),
    cut=wood_mat('cut', (0.6, 0.38, 0.19), (0.78, 0.55, 0.32), scale=(20, 20, 20)),
    foam=mat('foam', (0.95, 0.78, 0.25), 0.9),
    ice=mat('ice', (0.62, 0.84, 1.0), 0.08, alpha=0.6, emit=(0.5, 0.78, 1.0), estr=0.25, coat=1.0),
    water=mat('water', (0.45, 0.68, 0.92), 0.03, alpha=0.7, coat=1.0),
    glass=mat('glass', (0.95, 0.98, 1.0), 0.04, alpha=0.18, coat=1.0),
    shelfm=mat('shelfm', (0.9, 0.95, 0.97), 0.15, alpha=0.55, coat=1.0),
    milk=mat('milk', (0.97, 0.97, 0.95), 0.35, sss=0.15, sssr=(0.3, 0.3, 0.25)),
    cap=mat('cap', (0.15, 0.45, 0.85), 0.35),
    copper=mat('copper', (0.92, 0.5, 0.32), 0.28, metal=1.0),
    capil=mat('capillary', (0.95, 0.55, 0.35), 0.25, metal=1.0),
    cond=mat('condenser', (0.12, 0.12, 0.13), 0.4, metal=0.6),
    comp=mat('compressor', (0.06, 0.065, 0.07), 0.22, metal=0.3, coat=0.8),
    rubber=mat('rubber', (0.05, 0.05, 0.05), 0.8),
    steelm=mat('steel', (0.75, 0.76, 0.78), 0.25, metal=1.0),
    tray=mat('tray', (0.7, 0.72, 0.75), 0.3, metal=1.0),
    frost=mat('frost', (0.92, 0.96, 1.0), 0.9, sss=0.4, sssr=(0.5, 0.6, 0.8)),
    red=mat('red', (0.85, 0.08, 0.06), 0.3),
    white=mat('white', (0.95, 0.95, 0.95), 0.35),
    black=mat('black', (0.03, 0.03, 0.03), 0.4),
    apple=mat('apple', (0.75, 0.06, 0.05), 0.3, coat=0.5),
    leaf=mat('leaf', (0.25, 0.6, 0.15), 0.5),
    jam=mat('jam', (0.55, 0.05, 0.12), 0.1, trans=0.6, ior=1.4),
    cheese=mat('cheese', (1.0, 0.78, 0.25), 0.5),
    heater=mat('heater', (0.3, 0.3, 0.3), 0.4, metal=0.8),
    spag=mat('spaghetti', (0.98, 0.82, 0.45), 0.5),
    wire=mat('wire', (0.1, 0.1, 0.1), 0.5),
    dot=dot_mat(), wisp=wisp_mat(), dialm=mat('dialm', (0.96, 0.96, 0.96), 0.3), tbackm=mat('tbackm', (0.95, 0.95, 0.95), 0.35),
)

# ---------------------------------------------------------------- geometry helpers
def link(o):
    sc.collection.objects.link(o); return o
def box(name, x0, x1, y0, y1, z0, z1, m, bev=0.006, cutm=None):
    me = bpy.data.meshes.new(name)
    vs = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    vs = [(v[0] - (x0 + x1) / 2, v[1] - (y0 + y1) / 2, v[2] - (z0 + z1) / 2) for v in vs]
    fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(vs, [], fs); me.update()
    o = link(bpy.data.objects.new(name, me)); o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    o.data.materials.append(m)
    if cutm:  # face facing the camera (-Y) gets the section material
        o.data.materials.append(cutm)
        for p in o.data.polygons:
            if p.normal.y < -0.9: p.material_index = 1
    if bev:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bev; md.segments = 3; md.limit_method = 'ANGLE'
    for p in o.data.polygons: p.use_smooth = False
    return o
def prim(kind, name, loc, m, **kw):
    getattr(bpy.ops.mesh, f'primitive_{kind}_add')(location=loc, **kw)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(m)
    return o
def smooth(o, sub=0):
    for p in o.data.polygons: p.use_smooth = True
    if sub: o.modifiers.new('sub', 'SUBSURF').levels = sub; o.modifiers['sub'].render_levels = sub
    return o
def fillet(pts, r=0.04, seg=6):
    """rounded corners for a polyline of (x,z) or (x,y,z)"""
    P3 = [Vector(p if len(p) == 3 else (p[0], 0, p[1])) for p in pts]
    out = [P3[0]]
    for a, b, c in zip(P3, P3[1:], P3[2:]):
        d1 = (b - a); d2 = (c - b)
        rr = min(r, d1.length / 2.01, d2.length / 2.01)
        p0 = b - d1.normalized() * rr; p2 = b + d2.normalized() * rr
        for i in range(seg + 1):
            u = i / seg; out.append((1 - u) ** 2 * p0 + 2 * (1 - u) * u * b + u * u * p2)
    out.append(P3[-1]); return out
class Path:
    def __init__(s, pts):
        s.p = [Vector(p) for p in pts]; s.cum = [0.0]
        for a, b in zip(s.p, s.p[1:]): s.cum.append(s.cum[-1] + (b - a).length)
        s.L = s.cum[-1]
    def at(s, d):
        d = clamp(d, 0, s.L)
        lo, hi = 0, len(s.cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if s.cum[mid] <= d: lo = mid
            else: hi = mid
        seg = s.cum[hi] - s.cum[lo] or 1e-9
        return s.p[lo].lerp(s.p[hi], (d - s.cum[lo]) / seg)
    def atf(s, f): return s.at(f * s.L)
def tube(name, pts, r, m, y=0.10):
    pts3 = [Vector((p.x, y if p.y == 0 else p.y, p.z)) for p in pts]
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts3) - 1)
    for i, p in enumerate(pts3): sp.points[i].co = (p.x, p.y, p.z, 1)
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    cu.bevel_factor_mapping_end = 'SPLINE'
    o = link(bpy.data.objects.new(name, cu)); o.data.materials.append(m)
    return o, Path(pts3)

# ---------------------------------------------------------------- the set
box('floor', -4, 4, -5.0, 1.2, -0.03, 0.0, M['floor'], bev=0)
box('slab', -4, 4, -5.0, 1.2, -0.45, -0.03, M['slab'], bev=0)
box('wall', -4, 4, 0.62, 0.7, 0.0, 3.6, M['wall'], bev=0)
box('baseboard', -3, 3, 0.58, 0.62, 0.0, 0.08, M['base'], bev=0.004)
# clock
clock = prim('cylinder', 'clock', (-0.12, 0.58, 1.98), M['white'], radius=0.085, depth=0.02, vertices=48)
clock.rotation_euler = (math.radians(90), 0, 0); smooth(clock)
rim = prim('torus', 'clockrim', (-0.12, 0.565, 1.98), M['black'], major_radius=0.087, minor_radius=0.008)
rim.rotation_euler = (math.radians(90), 0, 0); smooth(rim)
hands = []
for nm, ln, w in (('hour', 0.045, 0.008), ('minute', 0.068, 0.005)):
    h = box(nm, -w / 2, w / 2, 0.555, 0.56, 0, ln, M['black'], bev=0); h.location = (-0.12, 0.557, 1.98)
    h.data.transform(__import__('mathutils').Matrix.Translation((0, 0, ln / 2))); hands.append(h)
# a framed picture to the right
box('frame', 0.26, 0.5, 0.585, 0.6, 1.86, 2.08, M['black'], bev=0.003)
box('picture', 0.275, 0.485, 0.58, 0.585, 1.875, 2.065, mat('pic', (0.95, 0.75, 0.35), 0.6), bev=0)

# fridge cabinet (section). door = left wall, back = right wall
X0, X1, Z0, Z1, Y0, Y1, TH = -0.40, 0.40, 0.08, 1.74, -0.32, 0.34, 0.05
walls = dict(
    back=box('w_back', X1 - TH, X1, Y0, Y1, Z0, Z1, M['box'], cutm=M['cut']),
    bottom=box('w_bottom', X0, X1, Y0, Y1, Z0, Z0 + TH, M['box'], cutm=M['cut']),
    rear=box('w_rear', X0, X1, Y1 - TH, Y1, Z0, Z1, M['box'], cutm=M['cut']),
)
door = box('w_door', -0.025, 0.025, -0.66, 0.0, 0, Z1 - Z0, M['box'], cutm=M['cut'])   # pivot at hinge (far corner)
door.data.transform(__import__('mathutils').Matrix.Translation((0, -0.33, 0)))
door.location = (X0 + 0.025, Y1, (Z0 + Z1) / 2)
lid = box('w_top', 0, X1 - X0, Y0, Y1, -TH / 2, TH / 2, M['box'], cutm=M['cut'])   # pivot at left end
lid.data.transform(__import__('mathutils').Matrix.Translation(((X1 - X0) / 2, 0, 0)))
lid.location = (X0, (Y0 + Y1) / 2, Z1 - TH / 2)
feet = [box(f'foot{i}', x - 0.03, x + 0.03, -0.25, 0.28, 0.0, Z0, M['rubber'], bev=0.01) for i, x in enumerate((-0.33, 0.33))]
# foam cores on the section faces (appear when we "wrap it in foam and steel")
foam = [box('foam_back', X1 - TH + 0.008, X1 - 0.008, Y0 - 0.004, Y0 - 0.001, Z0 + 0.008, Z1 - 0.008, M['foam'], bev=0),
        box('foam_bottom', X0 + 0.008, X1 - 0.008, Y0 - 0.004, Y0 - 0.001, Z0 + 0.008, Z0 + TH - 0.008, M['foam'], bev=0),
        box('foam_top', X0 + 0.008, X1 - 0.008, Y0 - 0.004, Y0 - 0.001, Z1 - TH + 0.008, Z1 - 0.008, M['foam'], bev=0),
        box('foam_door', X0 + 0.008, X0 + TH - 0.008, Y0 - 0.004, Y0 - 0.001, Z0 + 0.008, Z1 - 0.008, M['foam'], bev=0)]
handle = box('handle', X0 - 0.035, X0 - 0.015, -0.2, -0.17, 1.0, 1.45, M['steelm'], bev=0.006)

# shelf + food
shelf = box('shelf', X0 + TH, X1 - TH, -0.28, Y1 - TH, 0.90, 0.912, M['shelfm'], bev=0.002)
def bottle(name, x, z, m_in):
    prof = [(0.0, 0), (0.045, 0), (0.047, 0.005), (0.047, 0.16), (0.03, 0.2), (0.024, 0.23), (0.024, 0.25)]
    me = bpy.data.meshes.new(name); me.from_pydata([(r, 0, h) for r, h in prof], [(i, i + 1) for i in range(len(prof) - 1)], [])
    o = link(bpy.data.objects.new(name, me)); sc_ = o.modifiers.new('scr', 'SCREW'); sc_.steps = 48; sc_.render_steps = 48
    sc_.use_smooth_shade = True; so = o.modifiers.new('sol', 'SOLIDIFY'); so.thickness = 0.003
    o.data.materials.append(M['glass']); o.location = (x, 0.02, z)
    milk = prim('cylinder', name + '_milk', (x, 0.02, z + 0.085), m_in, radius=0.042, depth=0.16, vertices=48); smooth(milk)
    milk.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.08))); milk.location.z = z + 0.006
    d = milk.modifiers.new('lumps', 'DISPLACE'); tex = bpy.data.textures.new('lumps', 'CLOUDS'); tex.noise_scale = 0.012; d.texture = tex; d.strength = 0
    sub = milk.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    milk.modifiers.move(1, 0)  # subdivide before displacing
    cap = prim('cylinder', name + '_cap', (x, 0.02, z + 0.255), M['cap'], radius=0.027, depth=0.014, vertices=32); smooth(cap)
    return o, milk, cap
bottle_o, milk_o, cap_o = bottle('bottle', -0.12, 0.912, M['milk'])
apple = smooth(prim('uv_sphere', 'apple', (0.12, 0.05, 0.955), M['apple'], radius=0.045, segments=32, ring_count=16))
apple.scale = (1, 1, 0.92)
stem = prim('cylinder', 'stem', (0.12, 0.05, 1.005), M['wire'], radius=0.004, depth=0.03)
cheese = box('cheese', 0.04, 0.24, -0.05, 0.12, Z0 + TH, Z0 + TH + 0.08, M['cheese'], bev=0.008)
jar = smooth(prim('cylinder', 'jar', (-0.2, 0.05, Z0 + TH + 0.07), M['jam'], radius=0.05, depth=0.14, vertices=40))
jarlid = smooth(prim('cylinder', 'jarlid', (-0.2, 0.05, Z0 + TH + 0.15), M['red'], radius=0.052, depth=0.02, vertices=40))
lettuce = smooth(prim('ico_sphere', 'lettuce', (0.27, 0.06, Z0 + TH + 0.06), M['leaf'], radius=0.065, subdivisions=3), 1)

# ice + tray + puddle
ice = box('ice', -0.15, 0.15, -0.12, 0.2, 0, 0.3, M['ice'], bev=0.025)
ice.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.15)))
ICE_Z = 1.235
icetray = box('icetray', -0.22, 0.22, -0.2, 0.28, 1.215, 1.235, M['tray'], bev=0.004)
extra_ice = []
for k in range(3):
    e = box(f'ice{k}', -0.12, 0.12, -0.1, 0.16, 0, 0.24, M['ice'], bev=0.02)
    e.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.12))); extra_ice.append(e)
puddle = smooth(prim('cylinder', 'puddle', (-0.38, -0.05, 0.002), M['water'], radius=0.5, depth=0.006, vertices=64))

# thermometer on the inner rear wall
TH_X, TH_Z0, TH_H = -0.31, 0.42, 0.40
tglass = smooth(prim('cylinder', 'tglass', (TH_X, 0.27, TH_Z0 + TH_H / 2), M['glass'], radius=0.014, depth=TH_H, vertices=24))
tbulb = smooth(prim('uv_sphere', 'tbulb', (TH_X, 0.27, TH_Z0 - 0.005), M['red'], radius=0.022))
tliq = smooth(prim('cylinder', 'tliq', (TH_X, 0.27, TH_Z0), M['red'], radius=0.008, depth=1, vertices=16))
tliq.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.5)))
tback = box('tback', TH_X - 0.03, TH_X + 0.03, 0.285, 0.29, TH_Z0 - 0.04, TH_Z0 + TH_H + 0.02, M['tbackm'], bev=0.004)
TMIN, TMAX = -15.0, 30.0
def temp_h(c): return 0.02 + (TH_H - 0.03) * clamp((c - TMIN) / (TMAX - TMIN))
zero_mark = box('zero', TH_X + 0.016, TH_X + 0.03, 0.283, 0.285, 0, 0.004, M['black'], bev=0)
zero_mark.location.z = TH_Z0 + temp_h(0)

# ---------------------------------------------------------------- the refrigerant loop
Y = 0.10
EVAP = fillet([(0.37, Y, 1.60), (-0.27, Y, 1.60), (-0.27, Y, 1.50), (0.27, Y, 1.50), (0.27, Y, 1.40), (-0.27, Y, 1.40),
               (-0.27, Y, 1.30), (0.37, Y, 1.30)], r=0.05, seg=8)
SUCT = fillet([(0.37, Y, 1.30), (0.45, Y, 1.30), (0.45, Y, 0.40), (0.53, Y, 0.36), (0.53, Y, 0.26)], r=0.04)
DISCH = fillet([(0.68, Y, 0.16), (0.755, Y, 0.16), (0.755, Y, 1.64), (0.70, Y, 1.64)], r=0.04)
rows = []; z = 1.64; side = 0
while z >= 0.56:
    xa, xb = (0.70, 0.535) if side == 0 else (0.535, 0.70)
    rows += [(xa, Y + 0.05, z), (xb, Y + 0.05, z)]; z -= 0.09; side ^= 1
end = rows[-1]
COND = fillet([(0.70, Y, 1.64), (0.70, Y + 0.05, 1.64)] + rows[1:] + [(end[0], Y + 0.05, end[2] - 0.05), (0.49, Y, end[2] - 0.05), (0.49, Y, 0.47)], r=0.04)
CAPIL = fillet([(0.49, Y, 0.47), (0.49, Y, 0.43), (0.475, Y, 0.43), (0.475, Y, 1.66), (0.40, Y, 1.66), (0.37, Y, 1.60)], r=0.025)
evap_o, evap_p = tube('evap', EVAP, 0.012, M['copper'])
suct_o, suct_p = tube('suction', SUCT, 0.012, M['copper'])
disch_o, disch_p = tube('discharge', DISCH, 0.012, M['copper'])
cond_o, cond_p = tube('condenser', COND, 0.009, M['cond'])
capil_o, capil_p = tube('capillary', CAPIL, 0.0045, M['capil'])
frost_o, _ = tube('frost', EVAP, 0.012, M['frost'])
heater_o, heater_p = tube('heater', [Vector((-0.27, Y - 0.01, 1.25)), Vector((0.30, Y - 0.01, 1.25))], 0.0075, M['heater'])
# condenser fins (thin vertical wires)
fins = [tube(f'fin{i}', [Vector((x, Y + 0.065, 0.50)), Vector((x, Y + 0.065, 1.70))], 0.0025, M['cond'])[0]
        for i, x in enumerate([0.545 + 0.0235 * k for k in range(7)])]
stub = smooth(prim('uv_sphere', 'stub', (0.49, Y, 0.47), M['copper'], radius=0.016))
# compressor
CX, CZ = 0.58, 0.07
comp = smooth(prim('cylinder', 'comp', (CX, Y, CZ + 0.08), M['comp'], radius=0.10, depth=0.16, vertices=48), 0)
dome = smooth(prim('uv_sphere', 'dome', (CX, Y, CZ + 0.16), M['comp'], radius=0.10, segments=48, ring_count=24)); dome.scale.z = 0.62
cbase = box('cbase', CX - 0.13, CX + 0.13, Y - 0.12, Y + 0.12, 0.0, 0.02, M['steelm'], bev=0.004)
cterm = box('cterm', CX + 0.07, CX + 0.12, Y - 0.07, Y - 0.02, CZ + 0.05, CZ + 0.11, M['black'], bev=0.006)
comp_parts = [comp, dome, cbase, cterm]
COMP_REST = {o.name: o.location.copy() for o in comp_parts}
dtray = box('dtray', 0.565, 0.685, Y - 0.06, Y + 0.06, 0.285, 0.31, M['tray'], bev=0.003)
dwater = box('dwater', 0.57, 0.68, Y - 0.055, Y + 0.055, 0.292, 0.302, M['water'], bev=0)
DRAIN = fillet([(0.0, 0.2, 1.235), (0.31, 0.2, 1.235), (0.31, 0.2, 0.40), (0.42, 0.2, 0.40), (0.62, 0.2, 0.40), (0.62, 0.2, 0.37)], r=0.03)
drain_o, drain_p = tube('drain', DRAIN, 0.007, mat('drainm', (0.85, 0.85, 0.85), 0.3), y=0.2)
# thermostat dial + wire
dial = smooth(prim('cylinder', 'dial', (0.25, 0.27, 1.08), M['dialm'], radius=0.04, depth=0.025, vertices=40))
dial.rotation_euler = (math.radians(90), 0, 0)
dptr = box('dptr', 0.247, 0.253, 0.252, 0.258, 1.08, 1.115, M['red'], bev=0)
WIRE = fillet([(0.25, 0.25, 1.08), (0.415, 0.25, 1.08), (0.415, 0.25, 0.14), (0.49, 0.25, 0.14)], r=0.03)
wire_o, wire_p = tube('twire', WIRE, 0.004, M['wire'], y=0.25)
spag = tube('spaghetti', [Vector((0.40, 0.0, 0.62)), Vector((0.40, 0.0, 1.02))], 0.0085, M['spag'], y=0.0)[0]

# ---------------------------------------------------------------- dots (flow) + orbs + wisps + rings
dot_mesh = None
def make_dot(name, r):
    global dot_mesh
    if dot_mesh is None:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=12, ring_count=8)
        o = bpy.context.active_object; dot_mesh = o.data; smooth(o); o.data.materials.append(M['dot'])
        o.name = name; o.scale = (r, r, r); return o
    o = link(bpy.data.objects.new(name, dot_mesh)); o.scale = (r, r, r); return o
COLD = (0.0, 0.3, 1.0); GAS = (0.2, 0.75, 1.0); HOT = (1.0, 0.1, 0.02); WARM = (1.0, 0.72, 0.04)
class Flow:
    def __init__(s, name, path, spacing, r, front=0.012):
        s.path, s.sp = path, spacing; s.n = int(path.L / spacing) + 1
        s.dots = [make_dot(f'{name}{i}', r) for i in range(s.n)]; s.front = front
    def update(s, phase, grow, vis, colf, bright=1.0, jitter=0.0):
        for i, o in enumerate(s.dots):
            d = (i * s.sp + phase) % (s.n * s.sp)
            f = d / s.path.L
            on = vis > 0.01 and f <= grow and d <= s.path.L
            o.hide_render = not on
            if not on: continue
            p = s.path.at(d)
            if jitter: p = p + Vector((0, 0, jitter * math.sin(i * 7.1 + phase * 40)))
            o.location = (p.x, p.y - s.front, p.z)
            c = colf(f); o.color = (c[0] * bright, c[1] * bright, c[2] * bright, 1)
            o.scale = (s.r_ * vis,) * 3
flows = {}
for key, path, sp, r, fr in (('evap', evap_p, 0.045, 0.010, 0.010), ('suct', suct_p, 0.05, 0.009, 0.010),
                             ('disch', disch_p, 0.05, 0.009, 0.010), ('cond', cond_p, 0.045, 0.008, 0.008),
                             ('capil', capil_p, 0.035, 0.005, 0.004)):
    fl = Flow('d_' + key, path, sp, r, fr); fl.r_ = r; flows[key] = fl
bubbles = Flow('bub', evap_p, 0.03, 0.006, 0.013); bubbles.r_ = 0.006

class Pool:  # generic short-lived spheres (orbs, wisps)
    def __init__(s, name, n, m, sharedr=1.0):
        s.objs = []
        for i in range(n):
            if m is M['dot']: o = make_dot(f'{name}{i}', 0.01)
            else:
                bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=16, ring_count=10)
                o = bpy.context.active_object; o.name = f'{name}{i}'; o.data.materials.append(m); smooth(o)
            o.hide_render = True; s.objs.append(o)
        s.i = 0
    def reset(s):
        for o in s.objs: o.hide_render = True
        s.i = 0
    def put(s, loc, r, color, alpha=1.0, stretch=(1, 1, 1)):
        if s.i >= len(s.objs): return
        o = s.objs[s.i]; s.i += 1
        o.hide_render = r <= 0.0005; o.location = loc; o.scale = (r * stretch[0], r * stretch[1], r * stretch[2])
        o.color = (*color, alpha)
orbs = Pool('orb', 60, M['dot'])
wisps = Pool('wisp', 70, M['wisp'])
rings = []
for i in range(3):
    rg = prim('torus', f'ring{i}', (CX, Y, 0.17), M['wisp'], major_radius=1, minor_radius=0.03, major_segments=48, minor_segments=8)
    rg.rotation_euler = (math.radians(90), 0, 0); rg.hide_render = True; rings.append(rg)

# ---------------------------------------------------------------- lights + camera
def area(name, loc, rot, size, power, color):
    li = bpy.data.lights.new(name, 'AREA'); li.size = size; li.energy = power; li.color = color
    o = link(bpy.data.objects.new(name, li)); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; return o
key = area('key', (-1.6, -2.2, 2.8), (55, 0, -35), 1.4, 330, (1.0, 0.93, 0.84))
fill = area('fill', (2.2, -2.0, 1.2), (75, 0, 45), 2.5, 90, (0.8, 0.88, 1.0))
top = area('top', (0.2, 0.0, 2.9), (0, 0, 0), 1.6, 60, (1.0, 0.97, 0.92))
inside = area('inside', (0.0, -0.1, 1.66), (0, 0, 0), 0.5, 4, (1.0, 0.95, 0.85))
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.62, 0.66, 0.72, 1); bg.inputs['Strength'].default_value = 0.3
KEYP, FILLP, TOPP, WORLDS = key.data.energy, fill.data.energy, top.data.energy, 0.3

cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 50; cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24 * 1.5
cam = link(bpy.data.objects.new('cam', cam_d)); sc.camera = cam
cam.rotation_euler = (math.radians(90), 0, 0)
C_BASE = Vector((0.18, -3.30, 0.93)); C_COND = Vector((0.52, -1.75, 1.08)); C_CAP = Vector((0.36, -2.25, 1.02))
C_COMP = Vector((0.48, -2.1, 0.55)); C_WIDE = Vector((0.18, -3.75, 0.98)); C_DOOR = Vector((0.02, -2.9, 0.95))
def colf_evap(t):
    def c(f):
        boil = ss(f, 0.25, 0.9)
        return mix(COLD, GAS, boil)
    return c
def colf_cond(f):
    if f < 0.5: return mix(HOT, (1.0, 0.45, 0.08), f / 0.5)
    return mix((1.0, 0.45, 0.08), WARM, (f - 0.5) / 0.5)
def colf_capil(t):
    return lambda f: mix(WARM, COLD, ss(f, 0.75, 1.0)) if t > T['drops'] - 0.2 else WARM


# ================================================================ v4 additions: a real kitchen around the box + new props
M.update(
    cab=mat('cab', (0.9, 0.88, 0.82), 0.45), cabdoor=mat('cabdoor', (0.86, 0.84, 0.78), 0.35, coat=0.3),
    stone=mat('stone', (0.16, 0.17, 0.19), 0.25, coat=0.5), knob=mat('knob', (0.7, 0.7, 0.72), 0.2, metal=1.0),
    sky=mat('sky', (0.6, 0.8, 1.0), 0.5, emit=(0.6, 0.82, 1.0), estr=2.5), pot=mat('pot', (0.75, 0.42, 0.28), 0.6),
    plant=mat('plant', (0.18, 0.5, 0.2), 0.6), kettle=mat('kettle', (0.85, 0.2, 0.15), 0.2, coat=0.8),
    panelm=mat('panelm', (0.92, 0.93, 0.94), 0.3), piston=mat('piston', (0.6, 0.62, 0.65), 0.25, metal=1.0),
    dropm=mat('dropm', (0.7, 0.88, 1.0), 0.02, trans=1.0, ior=1.33),
)
box('ctr_l', -1.95, -0.62, 0.02, 0.6, 0.0, 0.86, M['cab'], bev=0.006)
box('ctop_l', -2.0, -0.58, -0.03, 0.62, 0.86, 0.9, M['stone'], bev=0.004)
for i, (a, b) in enumerate(((-1.92, -1.29), (-1.27, -0.65))):
    box(f'cdoor{i}', a, b, -0.005, 0.02, 0.06, 0.82, M['cabdoor'], bev=0.008)
    box(f'cknob{i}', b - 0.06, b - 0.04, -0.02, -0.005, 0.66, 0.74, M['knob'], bev=0.004)
box('ctr_r', 1.02, 2.4, 0.02, 0.6, 0.0, 0.86, M['cab'], bev=0.006)
box('ctop_r', 0.98, 2.45, -0.03, 0.62, 0.86, 0.9, M['stone'], bev=0.004)
box('cdoor_r', 1.05, 1.68, -0.005, 0.02, 0.06, 0.82, M['cabdoor'], bev=0.008)
box('up_l', -1.95, -0.7, 0.3, 0.6, 1.62, 2.3, M['cab'], bev=0.006)
box('up_r', 1.08, 2.4, 0.3, 0.6, 1.62, 2.3, M['cab'], bev=0.006)
box('win_frame', -1.62, -0.9, 0.585, 0.6, 1.0, 1.52, M['white'], bev=0.006)
box('win_sky', -1.58, -0.94, 0.6, 0.605, 1.04, 1.48, M['sky'], bev=0)
box('win_bar', -1.27, -1.25, 0.58, 0.585, 1.04, 1.48, M['white'], bev=0)
kettle = smooth(prim('cylinder', 'kettle', (-1.05, 0.3, 0.98), M['kettle'], radius=0.08, depth=0.16, vertices=40))
smooth(prim('uv_sphere', 'kettle_top', (-1.05, 0.3, 1.06), M['kettle'], radius=0.08, segments=32, ring_count=16)).scale.z = 0.45
smooth(prim('cylinder', 'pot', (1.35, 0.3, 0.97), M['pot'], radius=0.075, depth=0.14, vertices=32))
smooth(prim('ico_sphere', 'plant', (1.35, 0.3, 1.12), M['plant'], radius=0.12, subdivisions=3), 1)

drop = smooth(prim('uv_sphere', 'drop', (0.08, -0.12, 0.925), M['dropm'], radius=0.03, segments=32, ring_count=16))
DROP_C = Vector((0.08, -0.12, 0.925))
frost_ring = smooth(prim('torus', 'frostring', (0.08, -0.12, 0.914), M['frost'], major_radius=0.034, minor_radius=0.005))
ice_shards = [box(f'ishard{i}', -0.02, 0.02, -0.02, 0.02, -0.02, 0.02, M['ice'], bev=0.004) for i in range(9)]
glass_shards = [box(f'gshard{i}', -0.008, 0.008, -0.002, 0.002, -0.012, 0.012, M['glass'], bev=0) for i in range(7)]
piston = smooth(prim('cylinder', 'piston', (CX, Y, 0.16), M['piston'], radius=0.05, depth=0.05, vertices=32))
rod = prim('cylinder', 'rod', (CX, Y, 0.11), M['piston'], radius=0.012, depth=0.08, vertices=12)
panel = box('sidepanel', 0.505, 0.79, -0.035, -0.01, 0.0, 1.22, M['panelm'], bev=0.006)
panel.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.61)))
spagA = tube('spagA', [Vector((0, 0, 0)), Vector((0, 0, 0.2))], 0.0085, M['spag'], y=0.0)[0]
spagB = tube('spagB', [Vector((0, 0, 0)), Vector((0, 0, -0.2))], 0.0085, M['spag'], y=0.0)[0]
ice2 = box('ice2', -0.15, 0.15, -0.12, 0.2, 0, 0.3, M['ice'], bev=0.025)
ice2.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.15)))
for o in (door, drain_o, dtray, dwater, heater_o, frost_o, spag): o.hide_render = True
cam_d.clip_start = 0.004
for o in (key, fill, top, inside): o.visible_camera = False; o.visible_glossy = False


# ---------------------------------------------------------------- look presets (--look A golden hour | B moody night | C deep pastel)
LOOK = arg('--look', 'A'); WALLC = (0.22, 0.45, 0.47); SUN = None; SUNP = 0.0
if LOOK == 'A':
    WALLC = (0.07, 0.2, 0.21)
    pset(P(M['cab']), color=(0.62, 0.55, 0.45)); pset(P(M['cabdoor']), color=(0.58, 0.5, 0.4))
    sl = bpy.data.lights.new('sun', 'SUN'); sl.energy = 4.2; sl.color = (1.0, 0.68, 0.4); sl.angle = 0.06
    SUN = link(bpy.data.objects.new('sun', sl)); SUN.rotation_euler = (math.radians(62), 0, math.radians(-58)); SUNP = sl.energy
    key.data.energy = 90; fill.data.energy = 35; fill.data.color = (0.55, 0.7, 1.0); top.data.energy = 18
    bg.inputs['Color'].default_value = (0.25, 0.35, 0.55, 1)
    KEYP, FILLP, TOPP, WORLDS = 90, 35, 18, 0.12
    # Argon tweaks: cool rim on the compressor, icy interior, brighter flow dots, calmer condenser glow
    rl = bpy.data.lights.new('rim', 'AREA'); rl.size = 0.5; rl.energy = 40; rl.color = (0.75, 0.88, 1.0)
    RIM = link(bpy.data.objects.new('rim', rl)); RIM.location = (1.05, 0.45, 0.75)
    RIM.rotation_euler = (Vector((0.58, 0.1, 0.2)) - RIM.location).to_track_quat('-Z', 'Y').to_euler(); RIM.visible_camera = False
    inside.data.energy = 9; inside.data.color = (0.6, 0.8, 1.0)
    pset(P(M['dot']), estr=1.2)
elif LOOK == 'B':
    WALLC = (0.035, 0.045, 0.075)
    pset(P(M['cab']), color=(0.18, 0.2, 0.24)); pset(P(M['cabdoor']), color=(0.15, 0.17, 0.21))
    pl = bpy.data.lights.new('pendant', 'POINT'); pl.energy = 95; pl.color = (1.0, 0.7, 0.42); pl.shadow_soft_size = 0.12
    SUN = link(bpy.data.objects.new('pendant', pl)); SUN.location = (0.05, -0.75, 2.35); SUNP = pl.energy
    shade = smooth(prim('cone', 'shade', (0.05, -0.75, 2.42), M['black'], radius1=0.16, radius2=0.04, depth=0.14, vertices=32))
    cord = prim('cylinder', 'cord', (0.05, -0.75, 3.0), M['black'], radius=0.004, depth=1.1)
    key.data.energy = 25; fill.data.energy = 55; fill.data.color = (0.45, 0.6, 1.0); top.data.energy = 8
    bg.inputs['Color'].default_value = (0.1, 0.14, 0.3, 1)
    KEYP, FILLP, TOPP, WORLDS = 25, 55, 8, 0.06
else:
    WALLC = (0.13, 0.3, 0.32)
    key.data.energy = 200; fill.data.energy = 50; top.data.energy = 30
    KEYP, FILLP, TOPP, WORLDS = 200, 50, 30, 0.18
ORB_PIECES = None
def orb_path():
    global ORB_PIECES
    if ORB_PIECES is None:
        pts = [Vector((-0.12, -0.02, 1.02)), evap_p.atf(0.75), evap_p.atf(1.0)] + [suct_p.atf(k / 6) for k in range(7)] + \
              [disch_p.atf(k / 8) for k in range(9)] + [cond_p.atf(k / 12) for k in range(4)] + [Vector((0.95, -0.1, 1.45)), Vector((1.25, -0.3, 1.75))]
        ORB_PIECES = Path(fillet([(p.x, -0.02, p.z) for p in pts], r=0.04, seg=4))
    return ORB_PIECES


# ================================================================ v5: cold open on the finished fridge, then the build, one readable cutaway
OPEN = '--open' in argv            # render the finished fridge for the hook (dissolved into the old icebox on "A hundred years ago")
SWAP = LS[1] - 0.1; SWAP_D = 0.5   # dissolve window [SWAP, SWAP + SWAP_D]
TB_FINAL = T['moves']              # build time the cold open shows
door.hide_render = False
for o in (panel, ice2, drop, frost_ring, spag, drain_o, dtray, dwater, heater_o, *extra_ice, *ice_shards, *glass_shards):
    o.hide_render = True
M['lett'] = mat('lett', (0.25, 0.6, 0.15), 0.5); lettuce.data.materials[0] = M['lett']
M['hotcu'] = mat('hotcu', (0.92, 0.5, 0.32), 0.28, metal=1.0); disch_o.data.materials[0] = M['hotcu']
M['bulb'] = mat('bulb', (1.0, 0.92, 0.75), 0.3, emit=(1.0, 0.85, 0.6), estr=0.0)
seal = box('seal', X0 + TH, X0 + TH + 0.016, Y0 + 0.004, Y1 - TH, Z0 + TH, Z1 - TH, M['rubber'], bev=0.004)
bulb = smooth(prim('uv_sphere', 'bulb', (0.05, 0.22, Z1 - TH - 0.035), M['bulb'], radius=0.022, segments=24, ring_count=12))
sock = smooth(prim('cylinder', 'socket', (0.05, 0.22, Z1 - TH - 0.008), M['steelm'], radius=0.014, depth=0.02, vertices=24))
gl = bpy.data.lights.new('backglow', 'POINT'); gl.color = (1.0, 0.45, 0.15); gl.shadow_soft_size = 0.3; gl.energy = 0
BACKGLOW = link(bpy.data.objects.new('backglow', gl)); BACKGLOW.location = (0.64, 0.4, 1.0)
CONDP = 0.28
for m_ in (M['box'], M['cut']): m_.node_tree.nodes[m_['mixnode']].inputs[7].default_value = (0.8, 0.81, 0.83, 1)   # soft grey enamel, not blown-out white
pset(P(M['spag']), color=(0.95, 0.66, 0.18))
# lettuce: crinkly core + leaves (was a plain ball)
lettuce.hide_render = True; LETT = []
LC = Vector((0.27, 0.06, Z0 + TH + 0.065))
core = smooth(prim('ico_sphere', 'lett_core', LC, M['lett'], radius=0.05, subdivisions=4))
dl = core.modifiers.new('crinkle', 'DISPLACE'); tx = bpy.data.textures.new('crinkle', 'VORONOI'); tx.noise_scale = 0.018; dl.texture = tx; dl.strength = 0.012
LETT.append(core)
for k in range(7):
    a = k * 2 * math.pi / 7
    lf = smooth(prim('uv_sphere', f'leaf{k}', LC + Vector((0.035 * math.cos(a), 0.035 * math.sin(a), -0.01)), M['lett'], radius=0.045, segments=20, ring_count=12))
    lf.scale = (1.0, 0.32, 1.15); lf.rotation_euler = (0, -0.5, a + math.pi / 2); lf.rotation_euler = (0.45 * math.cos(a + math.pi / 2), 0.45 * math.sin(a + math.pi / 2), a + math.pi / 2)
    d2 = lf.modifiers.new('crinkle', 'DISPLACE'); d2.texture = tx; d2.strength = 0.006; LETT.append(lf)
# melt water pools on the box floor (with drips) instead of a puddle under the box
pool = box('pool', X0 + TH + 0.004, X1 - TH - 0.004, Y0 + 0.004, Y1 - TH - 0.004, 0, 0.035, M['water'], bev=0)
pool.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.0175))); pool.location.z = Z0 + TH
puddle.hide_render = True
pset(P(M['water']), color=(0.3, 0.6, 1.0), emit=(0.3, 0.6, 1.0), estr=0.15)
_FU = Flow.update
def _upd(s, phase, grow, vis, colf, bright=1.0, jitter=0.0, sizef=None):
    _FU(s, phase, grow, vis, colf, bright, jitter)
    if sizef:
        for i, o in enumerate(s.dots):
            if not o.hide_render:
                d = (i * s.sp + phase) % (s.n * s.sp); o.scale = (o.scale[0] * sizef(d / s.path.L),) * 3
Flow.update = _upd
pset(P(M['floor']), coat=0.0, rough=0.6)   # no sharp window glint on the floor
TMIN, TMAX = -20.0, 30.0
zero_mark.location.z = TH_Z0 + temp_h(0)

def flow_speed(t):
    if T['cuts'] < t < T['thermo'] + 0.6: return 0.0            # the thermostat cuts the pump
    if T['stop'] < t < LS[18]: return 0.0                        # and the hum stops at night
    return 0.22 * (1.0 + 1.4 * win(t, T['round'], T['glass'], 0.4, 0.5))
PHASE = [0.0]
for f in range(1, NF + 2): PHASE.append(PHASE[-1] + flow_speed(f / FPS) / FPS)
def comp_on(tb, t): return tb >= T['crush'] and flow_speed(t) > 0.05
def temp(tb):
    return sched(tb, [(0.0, 4), (SWAP, 4), (SWAP + 0.4, 21), (T['iceblk'], 21), (T['days'], 5), (T['then'], 5), (T['yog'], 22),
                      (T['boiling'], 22), (T['evap'] + 0.3, 5), (T['gas'], 5), (T['trap'], 14), (T['drops'], 14), (T['cap'], 4),
                      (T['forever'], 4), (T['glass'], -18), (T['cuts'], -18), (T['thermo'] + 0.5, 4), (END + 2, 4)])
def colf_capil(tb):
    return lambda f: mix(WARM, COLD, ss(f, 0.75, 1.0)) if tb > T['drops'] - 0.2 else WARM

# ---------------------------------------------------------------- camera: framings (target, distance, yaw°, pitch°, lens), eased in sequence + slow drift
V = Vector
def F(tg, d, yaw, pitch, lens=40): return (V(tg), d, yaw, pitch, lens)
def lerpF(a, b, k): return (a[0].lerp(b[0], k),) + tuple(x + (y - x) * k for x, y in zip(a[1:], b[1:]))
OPEN0 = F((-0.1, 0.02, 1.06), 1.15, -20, 6)   # hook: close on the milk, heat leaving it; dolly back to reveal the fridge
HERO = F((0.2, 0.1, 0.82), 3.25, -12, 7)
CAMK = [
    (0.0, 4.2, HERO),
    (SWAP + 0.3, 2.4, F((0.0, 0.05, 0.98), 2.5, -6, 8)),                 # the icebox
    (T['iceblk'] - 0.5, 0.8, F((0.0, 0.05, 1.1), 2.1, -4, 11)),           # ice lands
    (T['brill'], 2.4, F((0.05, 0.05, 0.92), 2.8, -16, 6)),                # two days pass
    (T['then'] - 0.1, 1.1, F((-0.12, 0.0, 0.62), 2.4, -20, 13)),          # puddle
    (T['yog'] - 0.45, 0.55, F((-0.12, 0.02, 1.04), 1.3, -14, 5)),         # yogurt
    (T['thing'] - 0.1, 1.4, F((0.2, 0.1, 1.0), 3.9, -4, 4)),              # heat only moves
    (T['swap'] - 0.2, 1.2, F((0.0, 0.1, 1.38), 1.8, -12, 9)),             # pipe replaces the ice
    (T['evap'] - 0.4, 0.8, F((0.02, 0.1, 1.42), 1.55, -6, 7)),
    (T['gas'] - 0.2, 0.9, F((0.4, 0.1, 1.25), 1.6, 16, 5)),               # gas escapes at the back
    (T['trap'], 1.2, F((0.55, 0.1, 0.45), 1.6, 22, 12)),                  # compressor
    (T['hot'] - 0.2, 0.8, F((0.62, 0.1, 0.3), 1.15, 28, 10)),             # hot
    (T['snake'] - 0.2, 1.6, F((0.6, 0.1, 1.05), 2.3, 30, 5)),             # condenser
    (T['warmline'] - 0.2, 1.0, F((0.66, 0.1, 1.0), 1.8, 50, 3)),          # warm back
    (T['cools'] - 0.1, 1.2, F((0.55, 0.1, 0.62), 1.6, 26, 6)),            # liquid again
    (T['push'] - 0.1, 1.4, F((0.47, 0.1, 1.0), 1.7, 16, 4)),              # capillary
    (T['pressure'] - 0.25, 0.8, F((0.36, 0.1, 1.42), 1.5, 8, 6)),         # spray into the evaporator
    (T['round'] - 0.2, 1.4, F((0.2, 0.1, 0.85), 3.4, -8, 6)),             # round and round
    (T['problem'] + 0.2, 1.0, F((0.2, 0.06, 0.36), 1.3, -10, 14)),        # lettuce
    (T['sensor'] - 0.2, 1.0, F((0.22, 0.2, 0.95), 1.6, -6, 6)),           # thermostat
    (T['click'] - 0.3, 1.0, HERO),
    (T['foam'] - 0.2, 2.0, F((0.2, 0.1, 0.85), 3.0, -18, 7)),
    (T['congrats'] - 0.1, 1.2, HERO),
    (T['never'], 1.6, F((0.45, 0.1, 1.1), 2.3, 10, 6)),                   # follow the heat out
    (T['milk'] - 0.2, END + 0.8 - T['milk'], OPEN0),                     # end where the hook starts (loops)
]
IMPACTS = [(T['iceblk'], 0.016), (T['slam'], 0.02), (T['crush'], 0.02), (T['spaghetti'] + 0.5, 0.004), (T['cuts'], 0.004)]
def cam_state(t):
    cur = OPEN0
    for t0, dur, fr in CAMK:
        if t < t0: break
        cur = lerpF(cur, fr, ss(t, t0, t0 + dur))
    tg, d, yaw, pitch, lens = cur
    dr = ss(t, 0.0, 1.5) * (1 - ss(t, END - 1.0, END + 0.6))   # drift fades out at both ends so the loop is seamless
    yaw += dr * 2.5 * math.sin(0.5 * t); pitch += dr * 1.0 * math.sin(0.37 * t + 1); d *= 1 + dr * 0.012 * math.sin(0.6 * t + 2)
    ya, pa = math.radians(yaw), math.radians(pitch)
    p = tg + d * V((math.sin(ya) * math.cos(pa), -math.cos(ya) * math.cos(pa), math.sin(pa)))
    sh = V((0, 0, 0))
    for t0, a in IMPACTS:
        if t0 <= t < t0 + 0.6:
            e = a * math.exp(-(t - t0) * 9); sh += V((e * math.sin(t * 71), 0, e * math.sin(t * 53 + 1)))
    return p + sh, tg + sh * 0.5, lens
def apply_cam(t):
    p, g, l = cam_state(t)
    cam.location = p; cam.rotation_euler = (g - p).to_track_quat('-Z', 'Y').to_euler(); cam_d.lens = l

# ---------------------------------------------------------------- per-frame state.  tb = build time (what exists), t = real time (camera, motion)
def state(t):
    f_idx = int(round(t * FPS))
    tb = TB_FINAL if OPEN else t
    apply_cam(t)
    # --- light: two quick days, night for the hum
    night = win(tb, T['night'] - 0.3, LS[18] + 0.1, 0.4, 0.4)
    cyc = 0.5 + 0.5 * math.cos(2 * math.pi * 2 * ss(tb, T['twod'] - 0.3, T['days'] + 0.5)) if T['twod'] - 0.3 < tb < T['days'] + 0.5 else 1.0
    dimf = (0.35 + 0.65 * cyc) * (1 - 0.8 * night)
    blue = mix((1.0, 0.93, 0.84), (0.55, 0.65, 1.0), max(night, 1 - cyc))
    key.data.energy = KEYP * dimf; key.data.color = blue
    fill.data.energy = FILLP * (1 - 0.5 * night); top.data.energy = TOPP * dimf
    bg.inputs['Strength'].default_value = WORLDS * (1 - 0.6 * night) * (0.5 + 0.5 * cyc)
    sk = mix((0.6, 0.82, 1.0), (0.05, 0.08, 0.25), max(night, 1 - cyc))
    pset(P(M['sky']), color=sk, emit=sk, estr=2.5 * (1 - 0.6 * max(night, 1 - cyc)))
    pset(P(M['wall']), color=WALLC)
    if SUN: SUN.data.energy = SUNP * dimf
    spin = ss(tb, T['twod'] - 0.3, T['days'] + 0.5)
    hands[0].rotation_euler.y = math.radians(60) + spin * 2 * math.pi * 2
    hands[1].rotation_euler.y = math.radians(-30) + spin * 2 * math.pi * 24

    # --- the icebox: lid open, ice block drops in, lid slams; melts over two days; restocked; swapped for a pipe
    lid.rotation_euler.y = -math.radians(108) * win(tb, T['iceblk'] - 0.75, T['slam'] + 0.02, 0.25, 0.18)
    melt = ss(tb, T['twod'] - 0.6, T['puddle'] + 0.3)
    restock = pop(tb, T['thing'] + 0.5, 0.4) if tb > T['thing'] + 0.5 else 0.0
    out_ = ss(tb, T['swap'], T['pipe'] + 0.2)
    if tb < T['thing'] + 0.5:
        u = clamp((tb - (T['iceblk'] - 0.4)) / 0.4)
        ice.location = (0, 0.04, ICE_Z + 1.6 * (1 - u * u)); s = 1 - 0.75 * melt
        ice.scale = (s, s, max(0.001, 1 - melt)); ice.hide_render = tb < T['iceblk'] - 0.4 or melt > 0.995
    else:
        s = max(0.001, restock * (1 - out_)); ice.location = (0, 0.04, ICE_Z + 0.25 * out_)
        ice.scale = (s, s, s); ice.hide_render = s < 0.01
    icetray.hide_render = not (SWAP - 0.2 < tb < T['pipe'] + 0.3); icetray.scale = (max(0.001, 1 - out_),) * 3
    pud = ss(tb, T['twod'], T['puddle'] + 0.5) * (1 - ss(tb, T['thing'] - 0.1, T['thing'] + 0.5))
    pool.scale = (1, 1, max(0.35 * pud, 0.001)); pool.hide_render = pud < 0.02

    # --- milk: yogurt (cap pops off), fresh bottle, freezes with the lettuce, thaws
    spoil = ss(tb, T['yog'] - 0.4, T['yog'] + 0.2) * (1 - ss(tb, T['thing'] + 0.1, T['thing'] + 0.35))
    froz = ss(tb, T['lettuce'] - 0.4, T['glass']) * (1 - ss(tb, T['cuts'], T['thermo'] + 1.0))
    mc = mix((0.97, 0.97, 0.95), (0.93, 0.86, 0.55), spoil); mc = mix(mc, (0.75, 0.88, 1.0), froz)
    pset(P(M['milk']), color=mc, rough=0.35 + 0.4 * froz)
    milk_o.modifiers['lumps'].strength = 0.035 * spoil
    reset = (1 - ss(tb, T['thing'] - 0.2, T['thing'] + 0.05)) if tb < T['thing'] + 0.1 else (pop(tb, T['thing'] + 0.1, 0.4) if tb < T['thing'] + 0.6 else 1.0)
    for o in (bottle_o, milk_o): o.scale = (max(0.001, reset),) * 3
    cap_rest = V((-0.12, 0.02, 0.912 + 0.255))
    if T['yog'] - 0.1 < tb < T['thing'] + 0.1:
        u = clamp((tb - T['yog'] + 0.1) / 0.45)
        cap_o.location = cap_rest.lerp(V((0.06, -0.24, 0.925)), u) + V((0, 0, 0.03 * math.sin(u * math.pi)))
        cap_o.rotation_euler = (u * 7.5, u * 2, 0); cap_o.scale = (max(reset, 0.001),) * 3; cap_o.hide_render = False
    else:
        cap_o.location = cap_rest; cap_o.rotation_euler = (0, 0, 0); cap_o.scale = (max(reset, 0.001),) * 3; cap_o.hide_render = False
    pset(P(M['glass']), rough=0.04 + 0.3 * froz, alpha=0.18 + 0.25 * froz)
    # lettuce turns into a glass sculpture, then thaws
    for o in LETT: o.hide_render = False
    lg = ss(tb, T['lettuce'] - 0.1, T['lettuce'] + 0.5) * (1 - ss(tb, T['cuts'] + 0.2, T['thermo'] + 1.2))
    pset(P(M['lett']), color=mix((0.25, 0.6, 0.15), (0.3, 0.62, 1.0), lg), rough=0.5 - 0.47 * lg, coat=lg, alpha=1 - 0.45 * lg,
         emit=(0.5, 0.8, 1.0), estr=1.1 * lg)

    # --- thermometer
    tc = temp(tb); tliq.scale.z = temp_h(tc)
    pset(P(M['red']), color=mix((0.85, 0.08, 0.06), (0.2, 0.45, 1.0), clamp((8 - tc) / 20)))

    # --- the loop grows
    g_evap = ss(tb, T['pipe'] - 0.1, T['pipe'] + 1.6)
    g_suct = ss(tb, T['trap'] - 0.1, T['trap'] + 0.7)
    g_disch = 0.12 * ss(tb, T['crush'], T['crush'] + 0.3) + 0.88 * ss(tb, T['snake'] - 0.1, T['snake'] + 0.6)
    g_cond = ss(tb, T['snake'] + 0.3, T['pours'] + 0.3)
    g_capil = ss(tb, T['push'] + 0.1, T['spaghetti'] + 0.3)
    for o, g in ((evap_o, g_evap), (suct_o, g_suct), (disch_o, g_disch), (cond_o, g_cond), (capil_o, g_capil)):
        o.data.bevel_factor_end = max(g, 0.0005); o.hide_render = g < 0.002
    for i, fo in enumerate(fins):
        g = ss(tb, T['snake'] + 0.3 + i * 0.08, T['pours'] + 0.3 + i * 0.08); fo.data.bevel_factor_end = max(g, 0.0005); fo.hide_render = g < 0.002
    fr = clamp((2 - tc) / 14) * g_evap
    frost_o.hide_render = fr < 0.05; frost_o.data.bevel_depth = 0.012 + 0.009 * fr; frost_o.data.bevel_factor_end = max(g_evap, 0.0005)
    stub_s = ss(tb, T['liquid'] - 0.2, T['liquid'] + 0.2) * (1 - ss(tb, T['push'] + 0.4, T['push'] + 0.7))
    bulge = 1 + 0.5 * win(tb, T['tight'] - 0.5, T['push'] + 0.2, 0.3, 0.2) * (0.5 + 0.5 * math.sin(t * 22))
    stub.scale = (max(stub_s * bulge, 0.001),) * 3; stub.hide_render = stub_s < 0.01
    sg = win(tb, T['spaghetti'] - 0.15, T['pressure'] - 0.1, 0.2, 0.25); snap = ss(tb, T['spaghetti'] + 0.5, T['spaghetti'] + 0.75)
    for o, sgn in ((spagA, 1), (spagB, -1)):
        o.hide_render = sg < 0.02; o.data.bevel_factor_end = max(sg, 0.0005)
        o.location = (0.515 + 0.02 * sgn * snap, -0.02, 0.86 - 0.05 * snap); o.rotation_euler = (0, sgn * 0.5 * snap, 0)

    # --- compressor: drops in on "crush", x-ray piston, shudders while running
    cd = clamp((tb - (T['crush'] - 0.3)) / 0.3)
    drop_ = 0.0 if tb >= T['crush'] else (0.3 * (1 - cd * cd) if tb > T['crush'] - 0.3 else 9)
    cgrow = 0.55 + 0.45 * cd
    sq = 1 - 0.12 * math.sin(clamp((tb - T['crush']) / 0.25) * math.pi) * (tb > T['crush'])
    on = comp_on(tb, t)
    shake = 0.0025 * math.sin(t * 95) if on else 0.0
    for o in comp_parts:
        r = COMP_REST[o.name]; o.location = (r.x + shake, r.y, r.z + drop_ + (sq - 1) * 0.05); o.hide_render = drop_ > 5
        o.scale = (cgrow,) * 3 if o is not dome else (cgrow, cgrow, 0.62 * sq * cgrow)
    xr = win(tb, T['crush'] + 0.1, T['fingers'] + 0.4, 0.3, 0.4)
    pset(P(M['comp']), alpha=1 - 0.78 * xr)
    pz = 0.17 + 0.025 * math.sin(t * 2 * math.pi * 3) if on else 0.17
    piston.hide_render = rod.hide_render = xr < 0.02 or drop_ > 5
    piston.location = (CX + shake, Y, pz); rod.location = (CX + shake, Y, pz - 0.05)
    hot = ss(tb, T['hot'] - 0.1, T['burn']) * (1 - 0.85 * ss(tb, T['perfect'], T['cools']))
    pset(P(M['piston']), emit=(1.0, 0.25, 0.04), estr=3.0 * hot * xr)
    pset(P(M['hotcu']), emit=(1.0, 0.22, 0.03), estr=4.0 * hot, color=mix((0.92, 0.5, 0.32), (1.0, 0.3, 0.1), hot))
    pset(P(M['copper']), emit=(1.0, 0.3, 0.05), estr=0.0)
    pset(P(M['cond']), emit=(1.0, 0.35, 0.05), estr=CONDP * ss(tb, T['snake'] + 0.5, T['pours']))
    def hl(m, at, col=(1.0, 0.85, 0.2)):
        k = win(tb, at - 0.1, at + 0.9, 0.12, 0.4)
        if k > 0.001: pset(P(m), emit=col, estr=2.5 * k)
    hl(M['copper'], T['evap']); hl(M['cond'], T['cond']); hl(M['capil'], T['cap']); hl(M['dialm'], T['thermo'])
    if not (T['thermo'] - 0.2 < tb < T['thermo'] + 1.0): pset(P(M['dialm']), estr=0.0)
    if not (T['cap'] - 0.2 < tb < T['cap'] + 1.0): pset(P(M['capil']), estr=0.0)
    BACKGLOW.data.energy = 9 * ss(tb, T['pours'] - 0.3, T['pours'] + 0.6) + 45 * win(tb, T['warmline'] - 0.2, T['cools'] + 0.1, 0.4, 0.5) * (0.85 + 0.15 * math.sin(t * 6))

    # --- thermostat: dial pops in, wire runs to the pump; clicks the pump off
    th = pop(tb, T['sensor'], 0.35)
    for o in (dial, dptr): o.scale = (max(th, 0.001),) * 3; o.hide_render = th < 0.01
    dptr.rotation_euler.y = -math.radians(70) * ss(tb, T['cuts'] - 0.2, T['cuts'] + 0.15) + math.radians(25) * win(tb, T['click'] - 0.1, T['click'] + 0.5, 0.08, 0.2)
    gw = ss(tb, T['sensor'] + 0.1, T['cuts']); wire_o.data.bevel_factor_end = max(gw, 0.0005); wire_o.hide_render = gw < 0.002

    # --- foam, steel, door seal, a little light
    sf = ss(tb, T['foam'] - 0.1, T['foam'] + 0.5); st = ss(tb, T['foam'] + 0.2, T['seal'] + 0.4)
    for m in (M['box'], M['cut']): set_steel(m, st)
    for fo in foam: fo.hide_render = sf < 0.05; fo.scale = (1, 1, max(sf, 0.01))
    pset(P(M['tbackm']), color=mix((0.95, 0.95, 0.95), (0.16, 0.18, 0.22), st))
    hs = pop(tb, T['seal'], 0.35)
    for o in (handle, seal): o.scale = (max(hs, 0.001),) * 3; o.hide_render = hs < 0.01
    bl = ss(tb, T['light'] - 0.05, T['light'] + 0.25) * (1 - 0.9 * night)
    for o in (bulb, sock): o.hide_render = tb < T['light'] - 0.3
    pset(P(M['bulb']), estr=3.0 * bl)
    inside.data.energy = 7 + 5 * bl; inside.data.color = mix((0.6, 0.8, 1.0), (1.0, 0.9, 0.75), bl)

    # --- refrigerant dots
    ph = PHASE[min(f_idx, len(PHASE) - 1)]
    fill_ = ss(tb, T['filled'] - 0.1, T['filled'] + 1.0)
    leak = ss(tb, T['gas'], T['escape'] + 0.4) * (1 - ss(tb, T['trap'], T['trap'] + 0.5))
    dim = 1.0 if flow_speed(t) > 0.01 or tb < T['crush'] else 0.45
    w0 = T['drops'] + 0.3
    def wave(k): return 1.0 + 1.2 * win(tb, w0 + 0.25 * k, w0 + 0.25 * k + 0.7, 0.15, 0.4)
    tw = 1.0 + 0.5 * win(tb, T['never'], END + 2, 0.5, 0.5)
    flows['evap'].update(ph, g_evap * fill_, fill_ * (1 - 0.85 * leak), colf_evap(tb) if tb > T['boiling'] - 0.3 else (lambda f: COLD), dim * wave(0) * tw,
                        sizef=(lambda f: 0.8 + 0.6 * ss(f, 0.25, 0.9)) if tb > T['boiling'] - 0.3 else (lambda f: 0.8))
    flows['suct'].update(ph, g_suct, ss(tb, T['trap'] + 0.3, T['crush']), lambda f: GAS, dim * wave(1) * tw, sizef=lambda f: 1.4)
    flows['disch'].update(ph, g_disch, ss(tb, T['crush'] + 0.2, T['hot']), lambda f: HOT, dim * wave(2) * tw, sizef=lambda f: 1.3)
    flows['cond'].update(ph, g_cond, ss(tb, T['snake'] + 0.5, T['pours']), colf_cond, dim * wave(3) * tw, sizef=lambda f: 1.4 - 0.6 * ss(f, 0.45, 0.9))
    flows['capil'].update(ph, g_capil, ss(tb, T['cap'] - 0.6, T['cap']), colf_capil(tb), dim * wave(4) * tw)
    bv = win(tb, T['boiling'] - 0.2, T['gas'] + 0.3, 0.3, 0.3) + win(tb, T['drops'], T['round'] + 0.5, 0.3, 0.3)
    bubbles.update(ph * 1.6 + t * 0.05, g_evap, min(bv, 1.0), lambda f: (0.92, 0.97, 1.0), 1.0, jitter=0.006)

    # --- heat orbs (orange = heat)
    orbs.reset()
    HEAT = (1.0, 0.42, 0.05)
    food = [V((-0.12, -0.02, 1.02)), V((0.12, 0.0, 0.96)), V((0.14, 0.0, 0.2)), V((0.27, 0.0, 0.2)), V((-0.2, 0.0, 0.22))]
    if T['twod'] - 0.4 < tb < T['puddle'] + 0.6:     # melt water drips off the tray
        for k in range(10):
            t0 = T['twod'] - 0.4 + k * 0.25; u = (tb - t0) / 0.45
            if 0 <= u <= 1:
                x = (-0.2, 0.2, -0.12, 0.15, 0.0)[k % 5]
                orbs.put(V((x, -0.1, 1.21 - (1.21 - Z0 - TH - 0.02) * u * u)), 0.011, (0.25, 0.55, 1.0))
    if T['cant'] - 0.5 < tb < T['only'] + 0.2:     # heat seeps in from the kitchen, through the walls, into the food
        for k in range(16):
            t0 = T['cant'] - 0.5 + k * 0.1; u = (tb - t0) / 1.3
            if 0 <= u <= 1:
                rs = random.Random(300 + k); side = -1 if k % 2 else 1
                s0 = V((0.25 + side * rs.uniform(0.75, 1.0), -0.15, rs.uniform(0.4, 1.6))); e0 = food[k % 5]
                orbs.put(s0.lerp(e0, ss(u, 0, 1)), 0.03 * math.sin(u * math.pi) ** 0.4, HEAT)
    if T['only'] - 0.2 < tb < T['swap'] + 0.6:       # ...and the only way to cool is to carry it back out
        for k in range(16):
            t0 = T['only'] - 0.2 + k * 0.09; u = (tb - t0) / 1.2
            if 0 <= u <= 1:
                rs = random.Random(400 + k); s0 = food[k % 5]; e0 = V((rs.uniform(0.9, 1.3), -0.2, rs.uniform(1.5, 2.0)))
                mid = V((0.42, -0.05, 1.3))
                p = s0.lerp(mid, ss(u, 0, 0.5)) if u < 0.5 else mid.lerp(e0, ss(u, 0.5, 1))
                orbs.put(p, 0.03 * math.sin(u * math.pi) ** 0.4, HEAT)
    if T['boiling'] - 0.3 < tb < T['evap'] + 1.0:   # the pipe drinks the warmth out of the food
        for k in range(18):
            t0 = T['boiling'] - 0.3 + k * 0.25; u = (tb - t0) / 1.1
            if 0 <= u <= 1:
                tgt = evap_p.atf(0.15 + 0.8 * ((k * 0.37) % 1)); tgt = V((tgt.x, -0.01, tgt.z)); s0 = food[k % 5]
                p = s0.lerp(tgt, ss(u, 0, 1)) + V((0.03 * math.sin(k * 3 + u * 6), 0, 0.04 * math.sin(u * math.pi)))
                orbs.put(p, 0.025 * math.sin(u * math.pi) ** 0.5, HEAT)
    if T['pours'] - 0.4 < tb < T['cools'] + 0.4:     # heat pours off the condenser into the kitchen
        for k in range(18):
            t0 = T['pours'] - 0.4 + k * 0.28; u = (tb - t0) / 1.6
            if 0 <= u <= 1:
                s0 = cond_p.atf(0.08 + 0.8 * ((k * 0.41) % 1)); p = V((s0.x, -0.03, s0.z)) + V((0.5 * u, -0.1 * u, 0.25 * u))
                orbs.put(p, 0.017 * math.sin(u * math.pi) ** 0.5, HEAT)
    if tb > T['never'] - 0.3:                        # finished fridge: heat streams from the milk, round the loop, into the kitchen
        op = orb_path(); lead = 1.0 if OPEN else ss(tb, T['never'] - 0.3, T['never'] + 0.4)
        for k in range(9):
            u = (t * 0.42 + k / 9) % 1
            orbs.put(op.atf(u), (0.03 if k == 0 else 0.021) * lead * math.sin(u * math.pi) ** 0.3, HEAT)

    # --- wisps
    wisps.reset()
    def puff(t0, life, p0, vel, r0, r1, col, a=0.55, seed=0, spread=0.03, clock=None):
        u = ((tb if clock is None else clock) - t0) / life
        if 0 <= u <= 1:
            rs = random.Random(seed)
            off = V((rs.uniform(-spread, spread), rs.uniform(-0.02, 0.02), rs.uniform(-spread, spread)))
            wisps.put(V(p0) + off + V(vel) * u, r0 + (r1 - r0) * u, col, a * math.sin(u * math.pi))
    for j in range(5): puff(T['yog'] - 0.1 + j * 0.2, 1.3, (-0.12, -0.08, 1.2), (0.035 * (j - 2), -0.05, 0.3), 0.03, 0.11, (0.55, 0.8, 0.1), 0.9, j)
    for j in range(8): puff(T['gas'] + j * 0.3, 1.6, (0.42, 0.0, 1.30), (0.12, 0, 0.3), 0.02, 0.09, (0.8, 0.92, 1.0), 0.6, 10 + j)
    if T['hot'] - 0.2 < tb < T['cools'] + 1.5:      # heat shimmer off the red-hot pipe
        for j in range(int((min(tb, T['cools']) - T['hot']) / 0.25) + 2):
            t0 = T['hot'] + j * 0.25
            if t0 > tb or tb - t0 > 1.6: continue
            src = (0.755, -0.02, 0.22 + 0.12 * (j % 3)) if t0 < T['snake'] + 0.5 else (0.62 + 0.08 * math.sin(j), -0.02, 0.8 + 0.25 * (j % 4))
            puff(t0, 1.6, src, (0.05, 0, 0.35), 0.012, 0.035, (1.0, 0.5, 0.15), 0.25, 30 + j, 0.02)
    for j in range(10): puff(T['drops'] + j * 0.07, 0.8, (0.40, 0.0, 1.60), (-0.38, 0, -0.02), 0.008, 0.04, (0.55, 0.82, 1.0), 0.85, 90 + j, 0.006)
    if lg > 0.3:                                      # glints on the glass lettuce
        for j in range(6):
            puff(T['lettuce'] + 0.2 + j * 0.18, 0.5, (0.27 + 0.05 * math.cos(j * 2.1), -0.01, 0.19 + 0.05 * math.sin(j * 1.7)),
                 (0, 0, 0), 0.004, 0.012, (1.0, 1.0, 1.0), 1.0, 120 + j, 0.0)
    # hum rings while the pump runs at night, until it stops
    for i, rg in enumerate(rings):
        rg.hide_render = True
        if on and T['click'] - 0.6 < tb < T['stop']:
            u = ((t * 1.6) + i / 3) % 1
            rg.hide_render = False; rr = 0.12 + 0.18 * u; rg.scale = (rr, rr, rr); rg.color = (0.8, 0.9, 1.0, 0.5 * (1 - u))

# ---------------------------------------------------------------- anchors for the overlay (with on-screen flag)
ANCH = dict(evap=V((0.0, Y, 1.62)), comp=V((CX, Y, 0.30)), cond=V((0.62, Y, 1.10)), capil=V((0.475, Y, 1.05)),
            thermo=V((0.25, 0.27, 1.12)), pipe=V((-0.15, Y, 1.66)), lett=V((0.27, 0.06, 0.3)),
            heat=V((-0.55, -0.15, 1.3)), gas=V((0.45, 0.0, 1.42)), liq=V((0.6, Y, 0.56)), warmc=V((0.62, Y, 1.35)), spag=V((0.515, -0.02, 0.98)))
def anchors():
    out = []; W, H = sc.render.resolution_x, sc.render.resolution_y
    for f in range(NF):
        t = f / FPS; state(t); bpy.context.view_layer.update()
        row = {'t': round(t, 3), 'temp': round(temp(t), 1), 'on': int(comp_on(t, t)), 'flow': round(flow_speed(t), 3)}
        for k, v in ANCH.items():
            p = world_to_camera_view(sc, cam, v)
            row[k] = (round(p.x * W, 1), round((1 - p.y) * H, 1), int(0.03 < p.x < 0.97 and 0.03 < p.y < 0.97 and p.z > 0))
        out.append(row)
    json.dump(dict(fps=FPS, w=W, h=H, T=T, swap=SWAP, swap_d=SWAP_D, frames=out), open(os.path.join(OUT, 'anchors.json'), 'w'))

# ---------------------------------------------------------------- run
def render_frame(f, path):
    t = f / FPS; sc.frame_set(f); state(t); sc.cycles.seed = f
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
if '--anchors' in argv:
    anchors()
if '--stills' in argv:
    for s in arg('--stills').split(','):
        f = int(round(float(s) * FPS)); render_frame(f, os.path.join(OUT, f'still_{float(s):06.2f}{"o" if OPEN else ""}.png'))
if '--frames' in argv:
    a, b = arg('--frames').split(':'); a = int(a); b = min(int(b), NF)
    if OPEN: b = min(b, int(math.ceil((SWAP + SWAP_D) * FPS)) + 1)
    sub = 'open' if OPEN else 'frames'
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for f in range(a, b):
        p = os.path.join(OUT, sub, f'f_{f:05d}.png')
        if not os.path.exists(p): render_frame(f, p)
print('NF', NF, 'DONE')
