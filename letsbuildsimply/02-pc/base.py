"""@letsbuildsimply ep 02: How a calculator becomes a gaming PC.  A golden-hour desk; the PC builds itself part by part, multi-angle edit.

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
def area(name, loc, rot, size, power, color):
    li = bpy.data.lights.new(name, 'AREA'); li.size = size; li.energy = power; li.color = color
    o = link(bpy.data.objects.new(name, li)); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; return o
