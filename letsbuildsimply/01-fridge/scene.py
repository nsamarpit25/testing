"""@letsbuildsimply ep: How a block of ice becomes a fridge.  Cutaway kitchen, one locked camera, the box grows into a fridge.

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

# ---------------------------------------------------------------- key times (from the voice take)
T = dict(
    ice_land=0.45, lid=ws(0, 'box') - 0.05,
    melt0=LS[1], melt1=ws(1, 'puddle') + 0.3, spoil=ws(1, 'milk'), cheese=ws(1, 'cheese'),
    need=LS[2], never=ws(2, 'never'),
    pipe0=ws(3, 'pipe'), filled=ws(3, 'filled'), boils=ws(4, 'boils'), heat=ws(4, 'heat'), evap=ws(4, 'evaporator'),
    gas=ws(5, 'gas'), floats=ws(5, 'floats'),
    catch=ws(6, 'catch'), pump=ws(6, 'pump'), comp=ws(6, 'compressor'),
    hot=ws(7, 'hot'), snake=ws(8, 'snake'), cools=ws(8, 'cools'), cond=ws(8, 'condenser'),
    why=LS[9], warmtxt=LE[9],
    stillwarm=LS[10], tight=ws(10, 'tight'),
    push=ws(11, 'push'), spaghetti=ws(11, 'spaghetti'), cap=ws(11, 'capillary'),
    spray=LS[12], drops=ws(12, 'drops'), cold=ws(12, 'freezing'),
    never2=ws(13, 'never'), solid=ws(13, 'solid'),
    sensor=ws(14, 'sensor'), off=ws(14, 'off'), thermo=ws(14, 'thermostat'),
    hum=ws(15, 'hum'), stops=ws(15, 'stops'), starts=ws(15, 'starts'),
    door=ws(16, 'door'), wet=ws(16, 'wet'), pipes=ws(16, 'pipes'), cstops=ws(16, 'stops'),
    heater=ws(17, 'heater'), melts=ws(17, 'melts'), drips=ws(17, 'drips'), dries=ws(17, 'dries'),
    twist=LS[18], moves=ws(18, 'moves'), kitchen=ws(18, 'kitchen'),
    wrap=LS[19], steel=ws(19, 'steel'), congrats=ws(19, 'congratulations'), could=ws(19, 'could'),
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
box('floor', -3, 3, -0.75, 1.2, -0.03, 0.0, M['floor'], bev=0)
box('slab', -3, 3, -0.75, 1.2, -0.45, -0.03, M['slab'], bev=0)
box('wall', -3, 3, 0.62, 0.7, 0.0, 3.2, M['wall'], bev=0)
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

# ---------------------------------------------------------------- per-frame state
def flow_speed(t):  # m/s of refrigerant dots
    on = 0.0
    if t < T['off']:
        on = 1.0
    else:  # thermostat cycling: off, on, off (stops), on (starts)
        on = 0.0
        if T['hum'] - 0.3 < t < T['stops']: on = 1.0
        if t > T['starts']: on = 1.0
        if T['pipes'] + 0.6 < t < T['heater']: on = 0.25  # frosted: barely cooling
    boost = 1.0 + 1.2 * win(t, T['never2'], T['off'], 0.4, 0.4)
    return 0.22 * on * boost
PHASE = [0.0]
for f in range(1, NF + 2): PHASE.append(PHASE[-1] + flow_speed(f / FPS) / FPS)
def comp_on(t): return flow_speed(t) > 0.05 and t >= T['pump']

def temp(t):
    return sched(t, [(0.0, 21), (0.6, 21), (3.5, 5), (T['melt0'], 5), (T['cheese'], 24), (T['pipe0'], 24), (T['boils'], 22),
                     (T['evap'] + 0.3, 8), (T['gas'], 8), (T['floats'] + 1.0, 16), (T['spray'], 16), (T['cold'] + 0.4, 4),
                     (T['never2'] + 0.5, 4), (T['solid'] + 0.3, -12), (T['off'], -12), (T['thermo'] + 0.4, 3.5),
                     (T['door'], 4), (T['cstops'], 13), (T['heater'] + 0.2, 13), (T['dries'], 4), (END + 2, 4)])

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

def state(t):
    f_idx = int(round(t * FPS))
    # --- camera
    c = C_BASE.copy()
    c = c.lerp(C_COND, ss(t, T['why'] - 0.2, T['why'] + 0.7) * (1 - ss(t, T['stillwarm'] - 0.1, T['stillwarm'] + 0.8)))
    c = c.lerp(C_CAP, ss(t, T['push'] - 0.1, T['push'] + 0.8) * (1 - ss(t, T['spray'] + 0.4, T['spray'] + 1.3)))
    c = c.lerp(C_COMP, ss(t, T['hum'] - 0.5, T['hum'] + 0.3) * (1 - ss(t, T['door'] - 0.9, T['door'] - 0.1)))
    c = c.lerp(C_WIDE, ss(t, T['congrats'] - 1.2, T['congrats'] + 0.6))
    c.x += 0.012 * math.sin(t * 0.37); c.z += 0.008 * math.sin(t * 0.29 + 1)
    cam.location = c

    # --- lights (x-ray dim during the twist)
    dim = 1 - 0.55 * win(t, T['twist'] + 0.2, T['wrap'] + 0.2, 0.5, 0.6)
    key.data.energy = KEYP * dim; fill.data.energy = FILLP * dim; top.data.energy = TOPP * dim
    bg.inputs['Strength'].default_value = WORLDS * dim
    pset(P(M['wall']), color=mix((0.22, 0.45, 0.47), (0.75, 0.33, 0.15), 0.45 * win(t, T['kitchen'] - 0.3, T['wrap'] + 0.6, 0.6, 0.6)))

    # --- lid slam + ice drop
    lid.rotation_euler.y = -math.radians(108) * max(1 - ss(t, T['lid'] - 0.18, T['lid'] + 0.02),
                                                   win(t, T['need'] - 0.2, T['pipe0'] - 0.1, 0.2, 0.3))
    if t < T['melt0']:
        u = clamp(t / T['ice_land'])
        z = ICE_Z + 0.55 * (1 - u * u)
        bounce = 0.02 * math.sin(clamp((t - T['ice_land']) / 0.25) * math.pi) * (t > T['ice_land'])
        ice.location = (0, 0.04, z + bounce); ice.scale = (1, 1, 1); ice.hide_render = False
    elif t < T['could']:
        m = ss(t, T['melt0'], T['melt1'])
        ice.location = (0, 0.04, ICE_Z); ice.scale = (1 - 0.75 * m, 1 - 0.75 * m, max(0.001, 1 - m)); ice.hide_render = m > 0.995
    else:  # "Or, you could just..." a block of ice lands on top of the finished fridge
        u = clamp((t - T['could'] - 0.1) / 0.45)
        ice.location = (0.0, 0.0, Z1 + 0.012 + 0.9 * (1 - u * u)); ice.scale = (1, 1, 1); ice.hide_render = u <= 0
    # the "ice runs out" montage: blocks drop in and melt fast
    for k, e in enumerate(extra_ice):
        t0 = T['need'] + 0.15 + k * 0.85
        if t0 - 0.05 < t < t0 + 0.85 and t < T['pipe0']:
            u = clamp((t - t0) / 0.3); mm = ss(t, t0 + 0.35, t0 + 0.8)
            e.hide_render = mm > 0.99; e.location = ((k - 1) * 0.07, 0.04, ICE_Z + 0.9 * (1 - u * u))
            e.scale = (1 - 0.7 * mm, 1 - 0.7 * mm, max(0.001, 1 - mm))
        else:
            e.hide_render = True
    tray_s = 1 - ss(t, T['pipe0'] - 0.4, T['pipe0'])
    icetray.scale = (max(tray_s, 0.001),) * 3; icetray.hide_render = tray_s < 0.01
    pud = ss(t, T['melt0'] + 0.6, T['melt1'] + 0.6) * (1 - ss(t, T['need'] - 0.3, T['need'] + 0.5))
    pud = max(pud, 0.6 * win(t, T['need'] + 0.4, T['pipe0'], 0.5, 0.4))
    puddle.scale = (0.2 + 0.9 * pud, 0.5 + 0.5 * pud, 1); puddle.hide_render = pud < 0.02
    # clock spins overnight
    spin = ss(t, T['melt0'], T['melt1'] + 0.4)
    hands[0].rotation_euler.y = math.radians(60) + spin * 2 * math.pi * 2
    hands[1].rotation_euler.y = math.radians(-30) + spin * 2 * math.pi * 24

    # --- milk: spoils, resets, freezes
    spoil = ss(t, T['spoil'] - 0.2, T['cheese'] + 0.2) * (1 - ss(t, T['need'] + 0.1, T['need'] + 0.4))
    froz = ss(t, T['solid'] - 0.4, T['solid'] + 0.2) * (1 - ss(t, T['thermo'], T['thermo'] + 1.0))
    mc = mix((0.97, 0.97, 0.95), (0.5, 0.58, 0.06), spoil); mc = mix(mc, (0.45, 0.75, 1.0), froz)
    pset(P(M['milk']), color=mc, rough=0.35 + 0.5 * froz)
    milk_o.modifiers['lumps'].strength = 0.03 * spoil
    milk_o.scale.z = 1 + 0.22 * froz  # frozen milk expands up the neck
    reset = pop(t, T['need'] + 0.25, 0.4) if t > T['need'] else 1.0
    for o in (bottle_o, milk_o, cap_o):
        o.scale = (max(0.001, reset),) * 3
    jump = 0.0; tilt = 0.0
    if T['cheese'] - 0.1 < t < T['need'] + 0.3:
        u = clamp((t - T['cheese'] + 0.1) / 0.7); jump = 0.28 * math.sin(min(u, 1) * math.pi) + 0.0 * u; tilt = 2.5 * u
    if T['solid'] - 0.1 < t < T['thermo'] + 0.6:
        u = clamp((t - T['solid'] + 0.1) / 0.35); jump = max(jump, 0.05 * ss(u, 0, 1)); tilt = 0.5 * u
    cap_o.location = (-0.12, 0.02, 0.912 + 0.255 + jump); cap_o.rotation_euler = (tilt, 0, 0)
    pset(P(M['glass']), rough=0.04 + 0.5 * froz, alpha=0.18 + 0.6 * froz, color=mix((0.95, 0.98, 1.0), (0.85, 0.93, 1.0), froz))

    # --- thermometer
    tc = temp(t); tliq.scale.z = temp_h(tc)
    pset(P(M['red']), color=mix((0.85, 0.08, 0.06), (0.2, 0.45, 1.0), clamp((8 - tc) / 20)))

    # --- pipes growing
    g_evap = ss(t, T['pipe0'] - 0.1, T['pipe0'] + 1.3)
    g_suct = ss(t, T['catch'] - 0.1, T['catch'] + 0.9)
    g_disch = 0.12 * ss(t, T['hot'] - 0.3, T['hot'] + 0.3) + 0.88 * ss(t, T['snake'] - 0.1, T['snake'] + 0.7)
    g_cond = ss(t, T['snake'] + 0.4, T['cools'])
    g_capil = ss(t, T['push'] - 0.1, T['push'] + 1.0)
    for o, g in ((evap_o, g_evap), (suct_o, g_suct), (disch_o, g_disch), (cond_o, g_cond), (capil_o, g_capil)):
        o.data.bevel_factor_end = max(g, 0.0005); o.hide_render = g < 0.002
    for i, fo in enumerate(fins):
        g = ss(t, T['snake'] + 0.4 + i * 0.08, T['cools'] + i * 0.08); fo.data.bevel_factor_end = max(g, 0.0005); fo.hide_render = g < 0.002
    stub_s = ss(t, T['cools'] - 0.2, T['cools'] + 0.2) * (1 - ss(t, T['push'] + 0.6, T['push'] + 0.9))
    bulge = 1 + 0.45 * win(t, T['stillwarm'], T['push'], 0.3, 0.2) * (0.5 + 0.5 * math.sin(t * 22))
    stub.scale = (max(stub_s * bulge, 0.001),) * 3; stub.hide_render = stub_s < 0.01
    stub.location.x = 0.49 + 0.004 * math.sin(t * 61) * win(t, T['stillwarm'], T['push'])
    # spaghetti for scale
    sg = win(t, T['spaghetti'] - 0.05, T['cap'] + 0.6, 0.25, 0.3)
    spag.data.bevel_factor_end = max(sg, 0.0005); spag.hide_render = sg < 0.01

    # --- compressor drop + shudder
    cd = clamp((t - (T['pump'] - 0.45)) / 0.45)
    drop = 0.0 if t >= T['pump'] else (1.5 * (1 - cd * cd) if t > T['pump'] - 0.45 else 9)
    sq = 1 - 0.12 * math.sin(clamp((t - T['pump']) / 0.25) * math.pi) * (t > T['pump'])
    shake = 0.0025 * math.sin(t * 95) if comp_on(t) else 0.0
    for o in comp_parts:
        r = COMP_REST[o.name]; o.location = (r.x + shake, r.y, r.z + drop + (sq - 1) * 0.05)
        o.hide_render = drop > 5
    dome.scale = (1, 1, 0.62 * sq)
    # discharge glow
    hot = ss(t, T['hot'] - 0.2, T['hot'] + 0.4)
    pset(P(M['copper']), emit=(1.0, 0.3, 0.05), estr=0.0)
    pset(P(M['cond']), emit=(1.0, 0.35, 0.05), estr=0.6 * ss(t, T['snake'] + 0.6, T['cools']) * (1 + 0.6 * win(t, T['why'], T['stillwarm'])))

    # --- highlight pulses when a term is named
    def hl(m, at, base_emit=0.0, col=(1.0, 0.85, 0.2)):
        k = win(t, at - 0.1, at + 0.9, 0.12, 0.4)
        if k > 0.001: pset(P(m), emit=col, estr=base_emit + 2.5 * k)
    hl(M['copper'], T['evap']); hl(M['comp'], T['comp']); hl(M['cond'], T['cond']); hl(M['capil'], T['cap']); hl(M['dialm'], T['thermo'])
    if t < T['thermo'] - 0.2 or t > T['thermo'] + 1.0: pset(P(M['dialm']), estr=0.0)
    if not (T['comp'] - 0.2 < t < T['comp'] + 1.0): pset(P(M['comp']), estr=0.0)
    if not (T['cap'] - 0.2 < t < T['cap'] + 1.0): pset(P(M['capil']), estr=0.0)

    # --- thermostat + wire
    th = pop(t, T['sensor'], 0.35)
    for o in (dial, dptr): o.scale = (max(th, 0.001),) * 3; o.hide_render = th < 0.01
    dial.rotation_euler = (math.radians(90), 0, 0)
    gw = ss(t, T['sensor'] + 0.1, T['off'] - 0.1); wire_o.data.bevel_factor_end = max(gw, 0.0005); wire_o.hide_render = gw < 0.002

    # --- frost + heater + door
    fr = ss(t, T['wet'] + 0.3, T['cstops']) * (1 - ss(t, T['melts'] - 0.1, T['drips']))
    frost_o.data.bevel_depth = 0.012 + 0.016 * fr; frost_o.hide_render = fr < 0.01
    hr = win(t, T['heater'] - 0.1, T['drips'] + 0.4, 0.25, 0.4)
    heater_o.hide_render = t < T['heater'] - 0.15
    pset(P(M['heater']), emit=(1.0, 0.2, 0.02), estr=14 * hr)
    door.rotation_euler.z = -math.radians(78) * win(t, T['door'] - 0.15, T['pipes'] - 0.2, 0.45, 0.5)
    dt = ss(t, T['drips'] - 0.3, T['drips'] + 0.2)
    drain_o.data.bevel_factor_end = max(dt, 0.0005); drain_o.hide_render = dt < 0.002
    tr = pop(t, T['drips'] - 0.2, 0.3)
    dtray.scale = (max(tr, 0.001),) * 3; dtray.hide_render = tr < 0.01
    wat = ss(t, T['drips'] + 0.5, T['dries'] - 0.2) * (1 - ss(t, T['dries'], T['dries'] + 0.6))
    dwater.scale = (max(tr, 0.001), max(tr, 0.001), max(wat, 0.001)); dwater.hide_render = wat < 0.02

    # --- wrap in foam and steel
    st = ss(t, T['wrap'] + 0.1, T['steel'] + 0.3)
    for m in (M['box'], M['cut']): set_steel(m, st)
    for fo in foam: fo.hide_render = st < 0.05; fo.scale = (1, 1, max(st, 0.01))
    pset(P(M['tbackm']), color=mix((0.95, 0.95, 0.95), (0.16, 0.18, 0.22), st))
    hs = pop(t, T['steel'], 0.35); handle.scale = (max(hs, 0.001),) * 3; handle.hide_render = hs < 0.01

    # --- refrigerant dots
    ph = PHASE[min(f_idx, len(PHASE) - 1)]
    fill_ = ss(t, T['filled'] - 0.1, T['filled'] + 1.0)
    leak = ss(t, T['gas'], T['floats'] + 0.4) * (1 - ss(t, T['catch'], T['catch'] + 0.5))
    evap_vis = fill_ * (1 - 0.85 * leak)
    bright = 1.0 + 0.8 * win(t, T['twist'], T['wrap'] + 0.4, 0.5, 0.5) - 0.6 * (flow_speed(t) < 0.01) * (t > T['off'])
    flows['evap'].update(ph, g_evap * fill_, evap_vis, colf_evap(t) if t > T['boils'] - 0.3 else (lambda f: COLD), bright)
    flows['suct'].update(ph, g_suct, ss(t, T['catch'] + 0.3, T['pump']), lambda f: GAS, bright)
    flows['disch'].update(ph, g_disch, ss(t, T['pump'] + 0.2, T['hot']), lambda f: HOT, bright)
    flows['cond'].update(ph, g_cond, ss(t, T['snake'] + 0.6, T['cools']), colf_cond, bright)
    flows['capil'].update(ph, g_capil, ss(t, T['push'] + 0.4, T['cap']), colf_capil(t), bright)
    bv = win(t, T['boils'] - 0.2, T['gas'] + 0.3, 0.3, 0.3) + win(t, T['drops'], T['never2'] + 0.5, 0.3, 0.3)
    bubbles.update(ph * 1.6 + t * 0.05, g_evap, min(bv, 1.0), lambda f: (0.92, 0.97, 1.0), 1.0, jitter=0.006)

    # --- orbs (heat) ---------------------------------------------------
    orbs.reset()
    milk_c = Vector((-0.12, -0.02, 1.02))
    if T['heat'] - 0.4 < t < T['evap'] + 1.2:  # heat leaves the milk into the coil
        for k in range(14):
            t0 = T['heat'] - 0.4 + k * 0.17; u = (t - t0) / 1.1
            if 0 <= u <= 1:
                tgt = evap_p.atf(0.55 + 0.4 * ((k * 0.37) % 1)); tgt = Vector((tgt.x, -0.01, tgt.z))
                p = milk_c.lerp(tgt, ss(u, 0, 1)) + Vector((0.03 * math.sin(k * 3 + u * 6), 0, 0.04 * math.sin(u * math.pi)))
                orbs.put(p, 0.021 * math.sin(u * math.pi) ** 0.5, (1.0, 0.4, 0.04))
    if T['moves'] - 0.6 < t < END + 0.2:  # the twist: heat rides the loop out into the kitchen
        loop = [milk_c, evap_p.atf(0.6), evap_p.atf(1.0)] + [suct_p.atf(k / 6) for k in range(7)] + \
               [disch_p.atf(k / 8) for k in range(9)] + [cond_p.atf(k / 10) for k in range(5)] + [Vector((0.85, 0.0, 1.25)), Vector((1.1, -0.2, 1.6))]
        lp = Path(fillet([(p.x, -0.02, p.z) for p in loop], r=0.03, seg=3))
        for k in range(22):
            t0 = T['moves'] - 0.6 + k * 0.22; u = (t - t0) / 3.2
            if 0 <= u <= 1:
                orbs.put(lp.atf(ss(u, 0, 1) * 0.6 + u * 0.4), 0.02, (1.0, 0.38, 0.04))

    if T['drips'] - 0.2 < t < T['dries']:  # meltwater drops run down the drain and fall into the tray
        for k in range(10):
            t0 = T['drips'] - 0.2 + k * 0.2; u = (t - t0) / 1.0
            if 0 <= u <= 1:
                p = drain_p.atf(min(u / 0.85, 1.0)); p = Vector((p.x, 0.17, p.z))
                if u > 0.85: p.z -= 0.06 * (u - 0.85) / 0.15
                orbs.put(p, 0.011, (0.25, 0.6, 1.0))
    # --- wisps -----------------------------------------------------------
    wisps.reset()
    def puff(t0, life, p0, vel, r0, r1, col, a=0.55, n=1, seed=0, spread=0.03):
        for j in range(n):
            tj = t0 + j * life / max(n, 1) * 0.5; u = (t - tj) / life
            if 0 <= u <= 1:
                rs = random.Random(seed * 100 + j)
                off = Vector((rs.uniform(-spread, spread), rs.uniform(-0.02, 0.02), rs.uniform(-spread, spread)))
                wisps.put(Vector(p0) + off + Vector(vel) * u, r0 + (r1 - r0) * u, col, a * math.sin(u * math.pi))
    # stink from spoiled milk
    for j in range(5): puff(T['cheese'] - 0.2 + j * 0.25, 1.4, (-0.12, -0.08, 1.2), (0.035 * (j - 2), 0, 0.3), 0.03, 0.12, (0.35, 0.85, 0.05), 1.0, 1, j)
    # gas escaping out of the open pipe end
    for j in range(8): puff(T['gas'] + j * 0.32, 1.6, (0.42, 0.0, 1.30), (0.12, 0, 0.3), 0.02, 0.09, (0.8, 0.92, 1.0), 0.6, 1, 10 + j)
    # heat shimmer off the hot discharge + condenser
    if t > T['hot'] - 0.2:
        for j in range(int((min(t, END) - T['hot']) / 0.3) + 2):
            t0 = T['hot'] + j * 0.3
            if t0 > t or t - t0 > 1.8: continue
            src = (0.755, -0.02, 0.35 + 0.15 * (j % 3)) if t0 < T['snake'] + 0.5 else (0.62 + 0.08 * math.sin(j), -0.02, 0.8 + 0.25 * (j % 4))
            mult = 1.6 if T['why'] - 0.3 < t0 < T['stillwarm'] else 1.0
            puff(t0, 1.8, src, (0.06, 0, 0.35), 0.015, 0.06 * mult, (1.0, 0.5, 0.15), 0.35 * mult, 1, 30 + j, 0.02)
    # warm wet air through the open door
    for j in range(10): puff(T['door'] + j * 0.12, 1.2, (-0.75, -0.05, 0.8 + 0.08 * (j % 5)), (0.55, 0.0, 0.25), 0.03, 0.08, (0.85, 0.9, 0.95), 0.5, 1, 60 + j)
    # steam off the drip tray
    for j in range(7): puff(T['drips'] + 0.6 + j * 0.22, 1.3, (0.625, 0.0, 0.32), (0.02, 0, 0.32), 0.015, 0.05, (0.95, 0.97, 1.0), 0.6, 1, 80 + j)
    # spray-can cold flash at the evaporator inlet
    for j in range(6): puff(T['drops'] + j * 0.1, 0.7, (0.30, 0.0, 1.60), (-0.3, 0, 0.0), 0.008, 0.03, (0.4, 0.75, 1.0), 0.8, 1, 90 + j, 0.006)
    # --- hum rings off the compressor
    for i, rg in enumerate(rings):
        rg.hide_render = True
        if comp_on(t) and T['hum'] - 0.4 < t < T['door'] - 0.3:
            u = ((t * 1.6) + i / 3) % 1
            rg.hide_render = False; rr = 0.12 + 0.18 * u; rg.scale = (rr, rr, rr); rg.color = (0.8, 0.9, 1.0, 0.5 * (1 - u))

# ---------------------------------------------------------------- anchors for the overlay
ANCH = dict(evap=Vector((0.0, Y, 1.62)), comp=Vector((CX, Y, 0.30)), cond=Vector((0.62, Y, 1.10)), capil=Vector((0.475, Y, 1.05)),
            thermo=Vector((0.25, 0.27, 1.12)), therm=Vector((TH_X, 0.27, TH_Z0 + TH_H + 0.03)), milk=Vector((-0.12, 0.02, 1.2)))
def anchors():
    out = []
    W, H = sc.render.resolution_x, sc.render.resolution_y
    for f in range(NF):
        t = f / FPS; state(t); bpy.context.view_layer.update()
        row = {'t': round(t, 3), 'temp': round(temp(t), 1), 'on': int(comp_on(t)), 'flow': round(flow_speed(t), 3)}
        for k, v in ANCH.items():
            p = world_to_camera_view(sc, cam, v); row[k] = (round(p.x * W, 1), round((1 - p.y) * H, 1))
        out.append(row)
    json.dump(dict(fps=FPS, w=W, h=H, T=T, frames=out), open(os.path.join(OUT, 'anchors.json'), 'w'))

# ---------------------------------------------------------------- run
def render_frame(f, path):
    t = f / FPS; sc.frame_set(f); state(t); sc.cycles.seed = f
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
if '--anchors' in argv:
    anchors()
if '--stills' in argv:
    for s in arg('--stills').split(','):
        f = int(round(float(s) * FPS)); render_frame(f, os.path.join(OUT, f'still_{float(s):06.2f}.png'))
if '--frames' in argv:
    a, b = arg('--frames').split(':'); a = int(a); b = min(int(b), NF)
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    for f in range(a, b):
        p = os.path.join(OUT, 'frames', f'f_{f:05d}.png')
        if not os.path.exists(p): render_frame(f, p)
print('NF', NF, 'DONE')
