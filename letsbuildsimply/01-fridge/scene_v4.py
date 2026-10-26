"""@letsbuildsimply ep: How a block of ice becomes a fridge (v4).  Cutaway kitchen, the box grows into a fridge, moving camera on every beat.

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
TIM = json.load(open(arg('--timings', 'voice4/timings_final.json')))
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

# ---------------------------------------------------------------- key times (v4 voice take, with the 1 s silence beat)
T = dict(
    lid=ws(0, 'box') - 0.05, congrats=ws(0, 'congratulations'),
    tomorrow=LS[1], puddle=ws(1, 'puddle'), sour=ws(1, 'sour'),
    need=LS[2], shower=ws(2, 'shower'), shiver=ws(2, 'shivered'),
    evapw=LS[3], steal=ws(3, 'stealing'),
    pipe0=ws(4, 'copper'), filled=ws(4, 'filled'),
    boils=LS[5], heat=ws(5, 'heat'), evap=ws(5, 'evaporator'),
    gas=ws(6, 'gas'), escapes=ws(6, 'escapes'),
    seal=ws(7, 'seal'), pump=ws(7, 'pump'), comp=ws(7, 'compressor'),
    hot=LS[8], scorch=ws(8, 'scorching'),
    snake=ws(9, 'snake'), escapes2=ws(9, 'escapes'), cond=ws(9, 'condenser'),
    sides=LS[10], hiding=ws(10, 'hiding'),
    leaves=LS[11], liquid=ws(11, 'liquid'), tight=ws(11, 'tight'),
    force=LS[12], spaghetti=ws(12, 'spaghetti'), cap=ws(12, 'capillary'),
    spray=LS[13], drops=ws(13, 'drops'), cold=ws(13, 'freezing'),
    never=LS[14], solid=ws(14, 'solid'), cracks=ws(14, 'cracks'),
    sensor=ws(15, 'sensor'), cuts=ws(15, 'cuts'), thermo=ws(15, 'thermostat'),
    hum=ws(16, 'hum'), stop=ws(16, 'stop'), night=ws(16, 'night'),
    twist=LS[17], made=ws(17, 'made'), pumps=ws(17, 'pumps'), kitchen=ws(17, 'kitchen'),
    wrap=LS[18], steel=ws(18, 'steel'), congrats2=ws(18, 'congratulations'), just=ws(18, 'just'),
)
END = LE[18]

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
# ================================================================ per-frame state
def flow_speed(t):
    if T['stop'] < t < T['twist'] - 0.2: return 0.0           # the hum stops at night
    boost = 1.0 + 1.3 * win(t, T['never'], T['cuts'], 0.4, 0.4)
    return 0.22 * boost
PHASE = [0.0]
for f in range(1, NF + 2): PHASE.append(PHASE[-1] + flow_speed(f / FPS) / FPS)
def comp_on(t): return t >= T['pump'] and flow_speed(t) > 0.05

def temp(t):
    return sched(t, [(0.0, 21), (0.6, 21), (3.0, 5), (T['tomorrow'], 5), (T['sour'], 24), (T['pipe0'], 24), (T['boils'], 22),
                     (T['evap'] + 0.3, 8), (T['gas'], 8), (T['escapes'] + 1.0, 15), (T['spray'], 15), (T['cold'] + 0.4, 4),
                     (T['never'] + 0.4, 4), (T['solid'] + 0.3, -12), (T['cuts'], -12), (T['thermo'] + 0.4, 3.5), (END + 2, 3.5)])

def ice_z(t):  # the opening plunge: block falls from high above into the box
    u = clamp(t / 0.6); return ICE_Z + 1.9 * (1 - u * u)
ORB_PIECES = None
def orb_path():
    global ORB_PIECES
    if ORB_PIECES is None:
        pts = [Vector((-0.12, -0.02, 1.02)), evap_p.atf(0.75), evap_p.atf(1.0)] + [suct_p.atf(k / 6) for k in range(7)] + \
              [disch_p.atf(k / 8) for k in range(9)] + [cond_p.atf(k / 12) for k in range(4)] + [Vector((0.95, -0.1, 1.45)), Vector((1.25, -0.3, 1.75))]
        ORB_PIECES = Path(fillet([(p.x, -0.02, p.z) for p in pts], r=0.04, seg=4))
    return ORB_PIECES

# ---------------------------------------------------------------- camera: shots blended in sequence
V = Vector
BASE = (V((-0.22, -3.0, 1.22)), V((0.2, 0.1, 0.93)), 46)
WIDE = (V((-0.35, -3.55, 1.25)), V((0.2, 0.1, 0.96)), 44)
def stat(p, tg, lens): return lambda t: (V(p), V(tg), lens)
def mv(p0, p1, g0, g1, l0, l1, a, b, ease=True):
    def f(t):
        k = ss(t, a, b) if ease else lin(t, a, b)
        return (V(p0).lerp(V(p1), k), V(g0).lerp(V(g1), k), l0 + (l1 - l0) * k)
    return f
def shot_plunge(t):
    z = max(ice_z(t) + 0.9, 2.78)
    return (V((0.0, -0.06, z)), V((0.0, 0.03, 0.0)), 24)
def shot_drop_orbit(t):
    a = math.radians(-28 + 60 * ss(t, T['evapw'], T['pipe0'] - 0.2)); r = 0.32
    return (DROP_C + V((r * math.sin(a), -r * math.cos(a), 0.07)), DROP_C, 58)
def shot_tip(t):
    g = max(ss(t, T['pipe0'] - 0.1, T['pipe0'] + 2.4), 0.04); tip = evap_p.atf(g)
    return (tip + V((0.06, -0.62, 0.12)), tip + V((0, 0, -0.03)), 36)
def shot_gas(t):
    k = lin(t, T['gas'], T['gas'] + 2.5)
    return (V((0.25, -1.25, 1.4 + 0.2 * k)), V((0.48, 0.0, 1.38 + 0.28 * k)), 40)
def shot_capride(t):
    a, b = T['cap'] - 0.5, T['spray'] + 0.9
    d = capil_p.L * (0.04 + 0.96 * ss(t, a, b) ** 0.9)
    p = capil_p.at(d); q = capil_p.at(min(d + 0.25, capil_p.L)) if d < capil_p.L - 0.02 else evap_p.atf(0.08)
    off = V((0.0, -0.47, 0.04))
    return (p + off, q + V((0.0, 0.0, 0.0)), 26)
def shot_orb(t):
    u = ss(t, T['twist'] + 0.1, T['kitchen'] + 0.7); p = orb_path().atf(u)
    return (p + V((-0.1, -0.48, 0.1)), p, 36)
def shot_hero(t):
    a = math.radians(-14 + 22 * lin(t, T['wrap'], T['just']))
    p, g, l = WIDE; r = (p - g).length
    return (g + V((r * math.sin(a), -r * math.cos(a), p.z - g.z)), g, l)
def shot_end(t):
    k = ss(t, T['just'] - 0.05, T['just'] + 0.5)
    return (V((0.0, -0.06, 2.95 + 0.2 * k)), V((0.0, 0.03, 0.0)), 24)
MILK_CU = stat((-0.02, -0.9, 1.14), (-0.1, 0.02, 1.04), 46)
SHOTS = [
    (0.0, 0.0, shot_plunge),
    (T['lid'] + 0.12, 0.65, stat(*BASE)),
    (T['tomorrow'], 1.2, mv((-0.45, -2.9, 1.3), (0.15, -2.2, 1.12), (0.2, 0.1, 0.93), (-0.05, 0.1, 1.0), 46, 46, T['tomorrow'], T['sour'] - 0.3)),
    (T['sour'] - 0.22, 0.2, MILK_CU),
    (T['need'], 0.3, stat(*BASE)),
    (T['shower'] - 0.15, 0.6, stat((0.08, -0.45, 1.06), DROP_C, 56)),
    (T['evapw'], 0.45, shot_drop_orbit),
    (T['pipe0'] - 0.25, 0.5, shot_tip),
    (T['boils'] - 0.1, 0.7, mv((0.0, -1.95, 1.22), (0.02, -1.3, 1.38), (-0.05, 0.1, 1.12), (0.0, 0.1, 1.36), 45, 45, T['boils'], T['evap'] + 0.5)),
    (T['gas'] - 0.15, 0.25, shot_gas),
    (T['seal'] - 0.1, 0.28, mv((0.55, -1.3, 0.45), (0.6, -0.68, 0.3), (0.58, 0.1, 0.22), (0.6, 0.1, 0.18), 42, 42, T['comp'] - 0.3, T['comp'] + 0.4)),
    (T['hot'] - 0.1, 0.35, stat((0.74, -0.52, 0.34), (0.7, 0.1, 0.27), 40)),
    (T['snake'] - 0.1, 0.8, mv((1.25, -1.45, 0.6), (1.12, -1.45, 1.5), (0.62, 0.1, 0.6), (0.62, 0.1, 1.38), 40, 40, T['snake'], T['cond'] + 0.4)),
    (T['sides'] - 0.1, 0.8, mv((1.02, -1.6, 1.15), (0.86, -1.15, 1.08), (0.64, 0.0, 1.05), (0.64, 0.0, 1.02), 42, 42, T['sides'], T['leaves'])),
    (T['leaves'] - 0.05, 0.6, mv((0.7, -0.64, 1.25), (0.6, -0.58, 0.56), (0.6, 0.1, 1.2), (0.5, 0.1, 0.48), 45, 45, T['leaves'], T['tight'] + 0.4)),
    (T['force'] - 0.1, 0.5, stat((0.42, -0.72, 0.95), (0.5, 0.05, 0.88), 44)),
    (T['cap'] - 0.55, 0.4, shot_capride),
    (T['drops'] + 0.35, 1.0, mv((0.15, -1.1, 1.5), WIDE[0], (0.25, 0.1, 1.45), WIDE[1], 30, 44, T['drops'] + 0.35, T['never'] - 0.1)),
    (T['solid'] - 0.45, 0.22, MILK_CU),
    (T['sensor'] - 0.1, 0.5, stat((0.18, -0.55, 1.12), (0.25, 0.27, 1.08), 44)),
    (T['hum'] - 0.25, 0.8, stat(*BASE)),
    (T['twist'] - 0.25, 0.5, shot_orb),
    (T['wrap'] - 0.1, 0.9, shot_hero),
    (T['just'] - 0.1, 0.45, shot_end),
]
IMPACTS = [(0.6, 0.012), (T['lid'], 0.02), (T['pump'], 0.018), (T['cracks'], 0.006), (T['steel'], 0.01), (T['twist'] - 0.2, 0.0)]
def cam_state(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    p, g, l = SHOTS[i][2](t)
    if i > 0 and SHOTS[i][1] > 0 and t < SHOTS[i][0] + SHOTS[i][1]:
        k = ss(t, SHOTS[i][0], SHOTS[i][0] + SHOTS[i][1]); p0, g0, l0 = SHOTS[i - 1][2](t)
        p, g, l = p0.lerp(p, k), g0.lerp(g, k), l0 + (l - l0) * k
    sh = V((0, 0, 0))
    for t0, a in IMPACTS:
        if t0 <= t < t0 + 0.6:
            e = a * math.exp(-(t - t0) * 9)
            sh += V((e * math.sin(t * 71), 0, e * math.sin(t * 53 + 1)))
    if T['stop'] - 0.05 < t < T['stop'] + 0.15: pass
    return p + sh, g + sh * 0.5, l
def apply_cam(t):
    p, g, l = cam_state(t)
    cam.location = p; d = g - p
    up = 'Y' if abs(d.normalized().z) > 0.97 else 'Y'
    cam.rotation_euler = d.to_track_quat('-Z', up).to_euler(); cam_d.lens = l

def state(t):
    f_idx = int(round(t * FPS))
    apply_cam(t)
    # --- lights: day/night cycle overnight, night for the hum beat
    night = win(t, T['night'] - 0.3, T['twist'] - 0.1, 0.4, 0.4)
    cyc = 0.5 + 0.5 * math.cos(2 * math.pi * 2 * ss(t, T['tomorrow'], T['puddle'] + 0.6)) if T['tomorrow'] < t < T['puddle'] + 0.6 else 1.0
    dimf = (0.35 + 0.65 * cyc) * (1 - 0.8 * night)
    blue = mix((1.0, 0.93, 0.84), (0.55, 0.65, 1.0), max(night, 1 - cyc))
    key.data.energy = KEYP * dimf; key.data.color = blue
    fill.data.energy = FILLP * (1 - 0.5 * night); top.data.energy = TOPP * dimf
    bg.inputs['Strength'].default_value = WORLDS * (1 - 0.6 * night) * (0.5 + 0.5 * cyc)
    sk = mix((0.6, 0.82, 1.0), (0.05, 0.08, 0.25), max(night, 1 - cyc))
    pset(P(M['sky']), color=sk, emit=sk, estr=2.5 * (1 - 0.6 * max(night, 1 - cyc)))
    pset(P(M['wall']), color=WALLC)
    if SUN: SUN.data.energy = SUNP * dimf

    # --- opening: ice plunge, shards, lid slam
    lid.rotation_euler.y = -math.radians(108) * (1 - ss(t, T['lid'] - 0.16, T['lid'] + 0.02))
    if t < T['tomorrow']:
        ice.location = (0, 0.04, ice_z(t)); ice.scale = (1, 1, 1); ice.hide_render = False
    else:
        m = ss(t, T['tomorrow'], T['puddle'] + 0.5)
        ice.location = (0, 0.04, ICE_Z); ice.scale = (1 - 0.75 * m, 1 - 0.75 * m, max(0.001, 1 - m)); ice.hide_render = m > 0.995
    for i, sh in enumerate(ice_shards):
        u = t - 0.6
        if 0 <= u <= 0.8:
            rs = random.Random(i); vx, vy, vz = rs.uniform(-0.7, 0.7), rs.uniform(-0.5, 0.2), rs.uniform(1.2, 2.2)
            sh.hide_render = False; sh.location = (vx * u, 0.04 + vy * u, ICE_Z + 0.3 + vz * u - 4.9 * u * u)
            sh.rotation_euler = (u * 9 * vx, u * 7, u * 5 * vy); sh.scale = (max(0.001, 1 - u / 0.8),) * 3
        else:
            sh.hide_render = True
    icetray.hide_render = t > T['pipe0'] - 0.1
    pud = ss(t, T['tomorrow'] + 0.4, T['puddle'] + 0.6) * (1 - ss(t, T['need'] - 0.2, T['need'] + 0.4))
    puddle.scale = (0.2 + 0.9 * pud, 0.5 + 0.5 * pud, 1); puddle.hide_render = pud < 0.02
    spin = ss(t, T['tomorrow'], T['puddle'] + 0.6)
    hands[0].rotation_euler.y = math.radians(60) + spin * 2 * math.pi * 2
    hands[1].rotation_euler.y = math.radians(-30) + spin * 2 * math.pi * 24
    for e in extra_ice: e.hide_render = True

    # --- milk: sours (cap pops at the lens), new bottle, freezes + cracks, thaws
    spoil = ss(t, T['sour'] - 0.5, T['sour'] + 0.15) * (1 - ss(t, T['need'] + 0.05, T['need'] + 0.3))
    froz = ss(t, T['solid'] - 0.35, T['solid'] + 0.2) * (1 - ss(t, T['thermo'], T['thermo'] + 1.0))
    mc = mix((0.97, 0.97, 0.95), (0.5, 0.58, 0.06), spoil); mc = mix(mc, (0.45, 0.75, 1.0), froz)
    pset(P(M['milk']), color=mc, rough=0.35 + 0.5 * froz)
    milk_o.modifiers['lumps'].strength = 0.03 * spoil; milk_o.scale.z = 1 + 0.3 * froz
    reset = pop(t, T['need'] + 0.2, 0.4) if t > T['need'] else 1.0
    for o in (bottle_o, milk_o): o.scale.x = o.scale.y = max(0.001, reset)
    bottle_o.scale.z = max(0.001, reset)
    cap_rest = V((-0.12, 0.02, 0.912 + 0.255))
    if T['sour'] - 0.05 < t < T['need'] + 0.2:   # flies at the camera
        u = clamp((t - T['sour'] + 0.05) / 0.45)
        cap_o.location = cap_rest.lerp(V((-0.05, -0.78, 1.14)), u * u) + V((0, 0, 0.06 * math.sin(u * math.pi)))
        cap_o.rotation_euler = (u * 7, u * 3, 0); cap_o.hide_render = u >= 1
    else:
        lift = 0.06 * froz
        cap_o.location = cap_rest + V((0, 0, lift)); cap_o.rotation_euler = (0.3 * froz, 0, 0); cap_o.hide_render = False
        cap_o.scale = (max(reset, 0.001),) * 3
    pset(P(M['glass']), rough=0.04 + 0.35 * froz, alpha=0.18 + 0.3 * froz, color=mix((0.95, 0.98, 1.0), (0.85, 0.93, 1.0), froz))
    for i, gs in enumerate(glass_shards):
        u = t - T['cracks']
        if 0 <= u <= 0.7:
            rs = random.Random(50 + i); a = rs.uniform(0, 2 * math.pi)
            gs.hide_render = False
            gs.location = (-0.12 + 0.05 * math.cos(a) + 0.25 * math.cos(a) * u, 0.02 + 0.05 * math.sin(a) - 0.25 * abs(math.sin(a)) * u,
                           1.0 + 0.6 * u - 3.0 * u * u)
            gs.rotation_euler = (u * 8, u * 6 * i, 0); gs.scale = (max(0.001, 1 - u / 0.7),) * 3
        else:
            gs.hide_render = True

    # --- thermometer
    tc = temp(t); tliq.scale.z = temp_h(tc)
    pset(P(M['red']), color=mix((0.85, 0.08, 0.06), (0.2, 0.45, 1.0), clamp((8 - tc) / 20)))

    # --- the shower droplet
    dp = pop(t, T['shower'] - 0.3, 0.35) if t < T['pipe0'] else 0.0
    ev = ss(t, T['evapw'] + 0.3, T['steal'] + 0.7)
    drop.scale = (max(0.001, dp * (1 - 0.95 * ev)),) * 2 + (max(0.001, 0.45 * dp * (1 - 0.95 * ev)),)
    drop.hide_render = dp * (1 - ev) < 0.03
    fr_ = ss(t, T['steal'], T['steal'] + 0.6) * (1 - ss(t, T['pipe0'] + 0.3, T['pipe0'] + 0.8))
    frost_ring.scale = (max(fr_, 0.001),) * 3; frost_ring.hide_render = fr_ < 0.02

    # --- pipes growing
    g_evap = ss(t, T['pipe0'] - 0.1, T['pipe0'] + 2.4)
    g_suct = ss(t, T['seal'] - 0.1, T['seal'] + 0.8)
    g_disch = 0.12 * ss(t, T['hot'] - 0.2, T['hot'] + 0.3) + 0.88 * ss(t, T['snake'] - 0.1, T['snake'] + 0.6)
    g_cond = ss(t, T['snake'] + 0.3, T['escapes2'] + 0.4)
    g_capil = ss(t, T['force'] + 0.1, T['spaghetti'] + 0.2)
    for o, g in ((evap_o, g_evap), (suct_o, g_suct), (disch_o, g_disch), (cond_o, g_cond), (capil_o, g_capil)):
        o.data.bevel_factor_end = max(g, 0.0005); o.hide_render = g < 0.002
    for i, fo in enumerate(fins):
        g = ss(t, T['snake'] + 0.3 + i * 0.08, T['escapes2'] + 0.4 + i * 0.08); fo.data.bevel_factor_end = max(g, 0.0005); fo.hide_render = g < 0.002
    stub_s = ss(t, T['liquid'] - 0.2, T['liquid'] + 0.2) * (1 - ss(t, T['force'] + 0.4, T['force'] + 0.7))
    bulge = 1 + 0.5 * win(t, T['tight'] - 0.5, T['force'] + 0.2, 0.3, 0.2) * (0.5 + 0.5 * math.sin(t * 22))
    stub.scale = (max(stub_s * bulge, 0.001),) * 3; stub.hide_render = stub_s < 0.01
    # spaghetti for scale: appears, then snaps
    sg = win(t, T['spaghetti'] - 0.15, T['cap'] - 0.2, 0.2, 0.25); snap = ss(t, T['spaghetti'] + 0.45, T['spaghetti'] + 0.7)
    for o, sgn in ((spagA, 1), (spagB, -1)):
        o.hide_render = sg < 0.02; o.data.bevel_factor_end = max(sg, 0.0005)
        o.location = (0.515 + 0.02 * sgn * snap, -0.02, 0.86 - 0.05 * snap); o.rotation_euler = (0, sgn * 0.5 * snap, 0)

    # --- side panel slides over the condenser ("hiding in the walls")
    pn = ss(t, T['sides'] + 0.4, T['hiding'] + 0.2) * (1 - ss(t, T['leaves'] - 0.3, T['leaves'] + 0.2))
    panel.hide_render = pn < 0.01; panel.location = (0.6475, -0.0225, 0.47 + 1.3 * (1 - pn))
    pset(P(M['panelm']), emit=(1.0, 0.42, 0.08), estr=0.9 * pn * (0.75 + 0.25 * math.sin(t * 5)))

    # --- compressor drop, x-ray piston, shudder
    cd = clamp((t - (T['pump'] - 0.45)) / 0.45)
    drop_ = 0.0 if t >= T['pump'] else (1.5 * (1 - cd * cd) if t > T['pump'] - 0.45 else 9)
    sq = 1 - 0.12 * math.sin(clamp((t - T['pump']) / 0.25) * math.pi) * (t > T['pump'])
    shake = 0.0025 * math.sin(t * 95) if comp_on(t) else 0.0
    for o in comp_parts:
        r = COMP_REST[o.name]; o.location = (r.x + shake, r.y, r.z + drop_ + (sq - 1) * 0.05); o.hide_render = drop_ > 5
    dome.scale = (1, 1, 0.62 * sq)
    xr = win(t, T['comp'] - 0.2, T['scorch'] + 0.6, 0.3, 0.4)
    pset(P(M['comp']), alpha=1 - 0.78 * xr)
    pz = 0.17 + 0.025 * math.sin(t * 2 * math.pi * 3) if comp_on(t) else 0.17
    piston.hide_render = rod.hide_render = xr < 0.02 or drop_ > 5
    piston.location = (CX + shake, Y, pz); rod.location = (CX + shake, Y, pz - 0.05)
    # glows
    hot = ss(t, T['hot'] - 0.1, T['scorch'] + 0.2)
    pset(P(M['piston']), emit=(1.0, 0.25, 0.04), estr=3.0 * hot * xr)
    pset(P(M['copper']), emit=(1.0, 0.3, 0.05), estr=0.0)
    pset(P(M['cond']), emit=(1.0, 0.35, 0.05), estr=0.28 * ss(t, T['snake'] + 0.5, T['escapes2']))
    def hl(m, at, base=0.0, col=(1.0, 0.85, 0.2)):
        k = win(t, at - 0.1, at + 0.9, 0.12, 0.4)
        if k > 0.001: pset(P(m), emit=col, estr=base + 2.5 * k)
    hl(M['copper'], T['evap']); hl(M['cond'], T['cond']); hl(M['capil'], T['cap']); hl(M['dialm'], T['thermo'])
    if not (T['thermo'] - 0.2 < t < T['thermo'] + 1.0): pset(P(M['dialm']), estr=0.0)
    if not (T['cap'] - 0.2 < t < T['cap'] + 1.0): pset(P(M['capil']), estr=0.0)

    # --- thermostat
    th = pop(t, T['sensor'], 0.35)
    for o in (dial, dptr): o.scale = (max(th, 0.001),) * 3; o.hide_render = th < 0.01
    dptr.rotation_euler.y = -math.radians(70) * ss(t, T['cuts'] - 0.2, T['cuts'] + 0.3)
    gw = ss(t, T['sensor'] + 0.1, T['cuts']); wire_o.data.bevel_factor_end = max(gw, 0.0005); wire_o.hide_render = gw < 0.002

    # --- wrap in foam and steel
    st = ss(t, T['wrap'] + 0.1, T['steel'] + 0.3)
    for m in (M['box'], M['cut']): set_steel(m, st)
    for fo in foam: fo.hide_render = st < 0.05; fo.scale = (1, 1, max(st, 0.01))
    pset(P(M['tbackm']), color=mix((0.95, 0.95, 0.95), (0.16, 0.18, 0.22), st))
    hs = pop(t, T['steel'], 0.35); handle.scale = (max(hs, 0.001),) * 3; handle.hide_render = hs < 0.01
    # the loop: a new block of ice drops onto the finished fridge
    u2 = clamp((t - T['just'] - 0.05) / 0.5)
    ice2.hide_render = t < T['just'] - 0.05; ice2.location = (0.0, 0.0, Z1 + 0.012 + 1.5 * (1 - u2 * u2))

    # --- refrigerant dots
    ph = PHASE[min(f_idx, len(PHASE) - 1)]
    fill_ = ss(t, T['filled'] - 0.1, T['filled'] + 1.0)
    leak = ss(t, T['gas'], T['escapes'] + 0.4) * (1 - ss(t, T['seal'], T['seal'] + 0.5))
    on_dim = 1.0 if flow_speed(t) > 0.01 or t < T['stop'] else 0.45
    wave0 = T['drops'] + 0.5
    def wave(k): return 1.0 + 1.2 * win(t, wave0 + 0.25 * k, wave0 + 0.25 * k + 0.7, 0.15, 0.4)
    tw = 1.0 + 0.6 * win(t, T['twist'], T['wrap'] + 0.4, 0.5, 0.5)
    flows['evap'].update(ph, g_evap * fill_, fill_ * (1 - 0.85 * leak), colf_evap(t) if t > T['boils'] - 0.3 else (lambda f: COLD), on_dim * wave(0) * tw)
    flows['suct'].update(ph, g_suct, ss(t, T['seal'] + 0.3, T['pump']), lambda f: GAS, on_dim * wave(1) * tw)
    flows['disch'].update(ph, g_disch, ss(t, T['pump'] + 0.2, T['hot']), lambda f: HOT, on_dim * wave(2) * tw)
    flows['cond'].update(ph, g_cond, ss(t, T['snake'] + 0.5, T['escapes2']), colf_cond, on_dim * wave(3) * tw)
    flows['capil'].update(ph, g_capil, ss(t, T['cap'] - 0.6, T['cap']), colf_capil(t), on_dim * wave(4) * tw)
    bv = win(t, T['boils'] - 0.2, T['gas'] + 0.3, 0.3, 0.3) + win(t, T['drops'], T['never'] + 0.5, 0.3, 0.3)
    bubbles.update(ph * 1.6 + t * 0.05, g_evap, min(bv, 1.0), lambda f: (0.92, 0.97, 1.0), 1.0, jitter=0.006)

    # --- heat orbs
    orbs.reset()
    milk_c = V((-0.12, -0.02, 1.02))
    if T['evapw'] - 0.1 < t < T['steal'] + 1.2:  # heat leaves the wood/skin through the evaporating drop
        for k in range(12):
            t0 = T['evapw'] - 0.1 + k * 0.25; u = (t - t0) / 1.0
            if 0 <= u <= 1:
                a = k * 2.4; s0 = DROP_C + V((0.09 * math.cos(a), 0.09 * math.sin(a) - 0.02, -0.012))
                p = s0.lerp(DROP_C, ss(u, 0, 0.5)) + V((0, 0, 0.18 * ss(u, 0.5, 1.0)))
                orbs.put(p, 0.008 * math.sin(u * math.pi) ** 0.5, (1.0, 0.42, 0.05))
    if T['heat'] - 0.4 < t < T['evap'] + 1.2:
        for k in range(14):
            t0 = T['heat'] - 0.4 + k * 0.17; u = (t - t0) / 1.1
            if 0 <= u <= 1:
                tgt = evap_p.atf(0.55 + 0.4 * ((k * 0.37) % 1)); tgt = V((tgt.x, -0.01, tgt.z))
                p = milk_c.lerp(tgt, ss(u, 0, 1)) + V((0.03 * math.sin(k * 3 + u * 6), 0, 0.04 * math.sin(u * math.pi)))
                orbs.put(p, 0.021 * math.sin(u * math.pi) ** 0.5, (1.0, 0.4, 0.04))
    if T['escapes2'] - 0.5 < t < T['sides'] + 1.0:  # heat radiates off the condenser into the room
        for k in range(16):
            t0 = T['escapes2'] - 0.5 + k * 0.28; u = (t - t0) / 1.6
            if 0 <= u <= 1:
                s0 = cond_p.atf(0.08 + 0.8 * ((k * 0.41) % 1)); p = V((s0.x, -0.03, s0.z)) + V((0.5 * u, -0.1 * u, 0.25 * u))
                orbs.put(p, 0.016 * math.sin(u * math.pi) ** 0.5, (1.0, 0.4, 0.04))
    if T['twist'] - 0.2 < t < T['wrap'] + 0.6:  # the twist: ONE big orb (camera rides it) + a few followers
        u = ss(t, T['twist'] + 0.1, T['kitchen'] + 0.7); op = orb_path()
        orbs.put(op.atf(u), 0.03, (1.0, 0.45, 0.05))
        for k in range(1, 6):
            uk = u - k * 0.06
            if 0 < uk < 1: orbs.put(op.atf(uk), 0.016, (1.0, 0.4, 0.04))
    if T['drips'] if False else False: pass

    # --- wisps
    wisps.reset()
    def puff(t0, life, p0, vel, r0, r1, col, a=0.55, seed=0, spread=0.03):
        u = (t - t0) / life
        if 0 <= u <= 1:
            rs = random.Random(seed)
            off = V((rs.uniform(-spread, spread), rs.uniform(-0.02, 0.02), rs.uniform(-spread, spread)))
            wisps.put(V(p0) + off + V(vel) * u, r0 + (r1 - r0) * u, col, a * math.sin(u * math.pi))
    for j in range(5): puff(T['sour'] - 0.1 + j * 0.2, 1.3, (-0.12, -0.08, 1.2), (0.035 * (j - 2), -0.05, 0.3), 0.03, 0.12, (0.35, 0.85, 0.05), 1.0, j)
    for j in range(6): puff(T['evapw'] + 0.4 + j * 0.35, 1.4, DROP_C, (0.0, 0.0, 0.16), 0.004, 0.016, (0.9, 0.95, 1.0), 0.5, 20 + j, 0.006)
    for j in range(8): puff(T['gas'] + j * 0.3, 1.6, (0.42, 0.0, 1.30), (0.12, 0, 0.3), 0.02, 0.09, (0.8, 0.92, 1.0), 0.6, 10 + j)
    if t > T['hot'] - 0.2:
        for j in range(int((min(t, END) - T['hot']) / 0.3) + 2):
            t0 = T['hot'] + j * 0.3
            if t0 > t or t - t0 > 1.8: continue
            src = (0.755, -0.02, 0.3 + 0.12 * (j % 3)) if t0 < T['snake'] + 0.5 else (0.62 + 0.08 * math.sin(j), -0.02, 0.8 + 0.25 * (j % 4))
            puff(t0, 1.8, src, (0.06, 0, 0.35), 0.015, 0.06, (1.0, 0.5, 0.15), 0.35, 30 + j, 0.02)
    for j in range(8): puff(T['drops'] + j * 0.08, 0.8, (0.32, 0.0, 1.60), (-0.35, 0, 0.0), 0.008, 0.035, (0.45, 0.78, 1.0), 0.85, 90 + j, 0.006)
    # hum rings, only until the hum stops
    for i, rg in enumerate(rings):
        rg.hide_render = True
        if comp_on(t) and T['hum'] - 0.6 < t < T['stop']:
            u = ((t * 1.6) + i / 3) % 1
            rg.hide_render = False; rr = 0.12 + 0.18 * u; rg.scale = (rr, rr, rr); rg.color = (0.8, 0.9, 1.0, 0.5 * (1 - u))

# ---------------------------------------------------------------- anchors for the overlay (with on-screen flag)
ANCH = dict(evap=V((0.0, Y, 1.62)), comp=V((CX, Y, 0.30)), cond=V((0.62, Y, 1.10)), capil=V((0.475, Y, 1.05)),
            thermo=V((0.25, 0.27, 1.12)), therm=V((TH_X, 0.27, TH_Z0 + TH_H + 0.03)), milk=V((-0.12, 0.02, 1.2)))
def anchors():
    out = []; W, H = sc.render.resolution_x, sc.render.resolution_y
    for f in range(NF):
        t = f / FPS; state(t); bpy.context.view_layer.update()
        row = {'t': round(t, 3), 'temp': round(temp(t), 1), 'on': int(comp_on(t)), 'flow': round(flow_speed(t), 3)}
        for k, v in ANCH.items():
            p = world_to_camera_view(sc, cam, v)
            row[k] = (round(p.x * W, 1), round((1 - p.y) * H, 1), int(0.03 < p.x < 0.97 and 0.03 < p.y < 0.97 and p.z > 0))
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
