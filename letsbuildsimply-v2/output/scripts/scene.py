"""scene.py: "How to Move a 100-Ton Rock Without a Crane" (Blender 5.2, Eevee, 1080x1920 @ 30 fps).

Everything (models, materials, lights, character, animation, cameras) is generated here. The animation is
procedural: state(t) poses the whole world for time t, the bake loop records it for every frame and writes the
F-curves, so the saved .blend plays on its own. Beat times come from the narration's word timestamps.

  blender -b -P scene.py -- --words narration.words.json --out OUT [--res 1080] [--samples 24]
          [--stills 1.0,20.5] [--frames A:B] [--save project.blend]
Writes OUT/labels.json (2D label anchors per frame) and OUT/events.json (sound cues) every run.
"""
import bpy, bmesh, math, json, sys, os, random, time
from math import sin, cos, pi, atan2, sqrt, radians
from mathutils import Vector, Matrix, Euler, Quaternion, noise
from mathutils.bvhtree import BVHTree
from bpy_extras import anim_utils
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(arg('--out', 'out')); os.makedirs(OUT, exist_ok=True)
FONT = arg('--font', os.path.join(HERE, 'fonts', 'Poppins-ExtraBold.ttf'))
FPS = 30; DUR = 56.5; NF = int(round(DUR * FPS))
RES = int(arg('--res', '1080')); SAMPLES = int(arg('--samples', '24'))
random.seed(7)

# ------------------------------------------------------------------ narration beats
WORDS = json.load(open(arg('--words')))
def _n(s): return ''.join(c for c in s.lower() if c.isalnum() or c == "'")
def W(word, n=1, end=False):
    k = 0
    for x in WORDS:
        if _n(x['w']) == _n(word):
            k += 1
            if k == n: return x['e'] if end else x['s']
    raise KeyError(word)
B = dict(this=W('this'), job=W('his'), crane=W('crane'), push=W('pushes'), notice=W('notice'),
         rope=W('ties'), rated=W('rated'), rockw=W('rock', 3), snap=W('snap'),
         lever=W('lever'), long=W('long'), short=W('short'), ratio=W('50', 2), light=W('light'), sand=W('sandbags'),
         lifts=W('lifts'), rollers=W('now') - 0.05, drag=W('dragging'), rolling=W('rolling'), twot=W('2', 2),
         pry=W('pry'), heave=W('heave'), week=W('week'), capstan=W('capstan'), arms=W('arms'), drum=W('drum'),
         twenty=W('20'), loop=W('loop'), pulley=W('pulley'), doubles=W('doubles'), forty=W('40'),
         half=W('half'), coming=W('coming'), dest=W('destination'), guy=W('guy'), zero=W('zero'),
         client=W('client'), texts=W('texts'))
T_SNAP = B['snap'] - 0.05
T_CAP_GO = B['doubles'] - 0.3          # engineer starts walking the capstan
T_ARRIVE = B['dest'] + 0.05            # rock stops

# ------------------------------------------------------------------ small math
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def sm(x): x = clamp(x); return x * x * (3 - 2 * x)
def ss(t, a, b): return sm((t - a) / (b - a)) if b > a else float(t >= a)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def ei(x): x = clamp(x); return x ** 3
def back(x, s=2.2): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, u): return a + (b - a) * u
def V(*a): return Vector(a if len(a) == 3 else a[0])
def lv(a, b, u): return Vector(a).lerp(Vector(b), u)
def nz(t, seed, f=1.0): return noise.noise(Vector((t * f, seed * 7.31, 0.37)))
def keys(t, ks, ease=sm):   # piecewise interpolation over [(t, value), ...]; value = float or tuple
    if t <= ks[0][0]: return ks[0][1]
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
            return lerp(a, b, u) if isinstance(a, (int, float)) else tuple(lerp(x, y, u) for x, y in zip(a, b))
    return ks[-1][1]

# ------------------------------------------------------------------ scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.fps = FPS; sc.frame_start = 0; sc.frame_end = NF - 1
sc.render.resolution_x, sc.render.resolution_y = RES, int(round(RES * 16 / 9 / 2)) * 2
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
ee = sc.eevee
ee.taa_render_samples = SAMPLES
for k, v in dict(use_raytracing=True, use_fast_gi=True, use_shadows=True, shadow_ray_count=2, shadow_step_count=8,
                 fast_gi_distance=6.0, fast_gi_quality=0.6, use_volumetric_shadows=False).items():
    try: setattr(ee, k, v)
    except Exception as e: print('eevee', k, e)
try: ee.ray_tracing_method = 'SCREEN'; ee.fast_gi_method = 'GLOBAL_ILLUMINATION'
except Exception as e: print('eevee gi', e)
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.35
try: sc.render.motion_blur_position = 'START'
except Exception as e: print('mb', e)
sc.view_settings.view_transform = 'AgX'
for look in ('AgX - Punchy', 'AgX - Medium High Contrast', 'Medium High Contrast'):
    try: sc.view_settings.look = look; break
    except Exception: pass
sc.view_settings.exposure = 0.0
sc.render.film_transparent = False

# ------------------------------------------------------------------ materials
def _bsdf(m):
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None:
        b = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        nt.links.new(b.outputs[0], o.inputs[0])
    return nt, b
def _in(b, *names):
    for n in names:
        if n in b.inputs: return b.inputs[n]
def mat(name, col, rough=0.5, metal=0.0, emit=0.0, coat=0.0, alpha=1.0, spec=0.5):
    m = bpy.data.materials.new(name); nt, b = _bsdf(m)
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        _in(b, 'Emission Color', 'Emission').default_value = (*col, 1); _in(b, 'Emission Strength').default_value = emit
    if coat: _in(b, 'Coat Weight', 'Clearcoat').default_value = coat
    _in(b, 'Specular IOR Level', 'Specular').default_value = spec
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        try: m.surface_render_method = 'BLENDED'
        except Exception: pass
    m.diffuse_color = (*col, 1)
    return m
def L(nt, a, b): nt.links.new(a, b)
def mixrgb(nt, blend, fac):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = blend; m.inputs[0].default_value = fac
    ins = [x for x in m.inputs if x.type == 'RGBA']; out = [x for x in m.outputs if x.type == 'RGBA'][0]
    return ins[0], ins[1], out
def ramp(nt, stops):
    r = nt.nodes.new('ShaderNodeValToRGB'); el = r.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = el.new(p); e.color = (*c, 1)
    return r
def tex(nt, kind, scale, coord, **kw):
    n = nt.nodes.new(kind); n.inputs['Scale'].default_value = scale
    for k, v in kw.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    L(nt, coord, n.inputs['Vector']); return n
def bump(nt, b, height, strength, dist=0.05):
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = dist; L(nt, height, bp.inputs['Height']); L(nt, bp.outputs['Normal'], b.inputs['Normal'])
def coords(nt, kind='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord'); return tc.outputs[kind]
def world_pos(nt):
    g = nt.nodes.new('ShaderNodeNewGeometry'); return g.outputs['Position']

def mat_rock():
    m = mat('rock', (0.5, 0.47, 0.43), 0.82); nt, b = _bsdf(m); c = coords(nt)
    n1 = tex(nt, 'ShaderNodeTexNoise', 0.45, c, Detail=5.0, Roughness=0.6)
    r1 = ramp(nt, [(0.3, (0.22, 0.20, 0.18)), (0.5, (0.42, 0.38, 0.34)), (0.72, (0.62, 0.57, 0.50))])
    L(nt, n1.outputs['Fac'], r1.inputs['Fac'])
    vo = tex(nt, 'ShaderNodeTexVoronoi', 18.0, c)
    ia, ib, io = mixrgb(nt, 'MULTIPLY', 1.0)
    sp = ramp(nt, [(0.0, (0.55, 0.55, 0.55)), (0.08, (1, 1, 1))]); L(nt, vo.outputs['Distance'], sp.inputs['Fac'])
    L(nt, r1.outputs['Color'], ia); L(nt, sp.outputs['Color'], ib); L(nt, io, b.inputs['Base Color'])
    n2 = tex(nt, 'ShaderNodeTexNoise', 3.5, c, Detail=8.0, Roughness=0.65); bump(nt, b, n2.outputs['Fac'], 0.45, 0.08)
    return m
def mat_ground():
    m = mat('ground', (0.62, 0.48, 0.33), 0.95); nt, b = _bsdf(m); c = world_pos(nt)
    n1 = tex(nt, 'ShaderNodeTexNoise', 0.06, c, Detail=3.0)
    r1 = ramp(nt, [(0.35, (0.42, 0.27, 0.14)), (0.55, (0.53, 0.36, 0.20)), (0.75, (0.60, 0.44, 0.27))])
    L(nt, n1.outputs['Fac'], r1.inputs['Fac'])
    n3 = tex(nt, 'ShaderNodeTexNoise', 1.2, c, Detail=6.0)
    ia, ib, io = mixrgb(nt, 'OVERLAY', 0.35)
    L(nt, r1.outputs['Color'], ia); L(nt, n3.outputs['Color'], ib); L(nt, io, b.inputs['Base Color'])
    vo = tex(nt, 'ShaderNodeTexVoronoi', 7.0, c); bump(nt, b, vo.outputs['Distance'], 0.25, 0.04)
    return m
def mat_wood(name, col=(0.55, 0.36, 0.2), axis='X'):
    m = mat(name, col, 0.7); nt, b = _bsdf(m); c = coords(nt)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = {'X': (0.4, 6, 6), 'Y': (6, 0.4, 6), 'Z': (6, 6, 0.4)}[axis]
    L(nt, c, mp.inputs['Vector'])
    n = tex(nt, 'ShaderNodeTexNoise', 2.0, mp.outputs['Vector'], Detail=4.0, Distortion=1.5)
    d = tuple(x * 0.62 for x in col); l = tuple(min(1, x * 1.22) for x in col)
    r = ramp(nt, [(0.35, d), (0.65, l)]); L(nt, n.outputs['Fac'], r.inputs['Fac']); L(nt, r.outputs['Color'], b.inputs['Base Color'])
    bump(nt, b, n.outputs['Fac'], 0.25, 0.02)
    return m
def mat_fabric(name, col, rough=0.9, scale=40.0):
    m = mat(name, col, rough); nt, b = _bsdf(m); c = coords(nt)
    w = tex(nt, 'ShaderNodeTexWave', scale, c, Distortion=2.0)
    bump(nt, b, w.outputs['Fac'], 0.15, 0.01)
    return m
def mat_stripes(name, a, b_, scale=3.0):
    m = mat(name, a, 0.5); nt, b = _bsdf(m); c = coords(nt)
    w = tex(nt, 'ShaderNodeTexWave', scale, c); w.wave_profile = 'SAW'
    r = ramp(nt, [(0.49, a), (0.51, b_)]); r.color_ramp.interpolation = 'CONSTANT'
    L(nt, w.outputs['Fac'], r.inputs['Fac']); L(nt, r.outputs['Color'], b.inputs['Base Color'])
    return m

M = dict(
    rock=mat_rock(), ground=mat_ground(), path=mat('path', (0.56, 0.45, 0.32), 0.95),
    wood=mat_wood('wood'), woodz=mat_wood('woodz', axis='Z'), woody=mat_wood('woody', axis='Y'),
    wood_dark=mat_wood('wood_dark', (0.36, 0.22, 0.12)), endgrain=mat('endgrain', (0.80, 0.62, 0.40), 0.75),
    rope=mat_fabric('rope', (0.80, 0.64, 0.40), 0.85, 60), burlap=mat_fabric('burlap', (0.66, 0.53, 0.34), 0.95, 25),
    steel=mat('steel', (0.40, 0.41, 0.43), 0.35, 1.0), dark=mat('dark', (0.08, 0.08, 0.09), 0.5),
    hat=mat('hat', (1.0, 0.40, 0.03), 0.32, coat=0.6), skin=mat('skin', (0.93, 0.64, 0.48), 0.55),
    overalls=mat_fabric('overalls', (0.10, 0.28, 0.62), 0.85, 30), vest=mat('vest', (0.80, 0.95, 0.10), 0.6),
    reflect=mat('reflect', (0.92, 0.92, 0.92), 0.2, 0.7), shirt=mat('shirt', (0.93, 0.90, 0.84), 0.8),
    glove=mat('glove', (0.83, 0.60, 0.28), 0.7), boot=mat('boot', (0.30, 0.18, 0.10), 0.6),
    eye=mat('eye', (0.97, 0.97, 0.97), 0.25), pupil=mat('pupil', (0.02, 0.02, 0.025), 0.15, coat=1.0),
    hair=mat('hair', (0.14, 0.08, 0.04), 0.7), mouth=mat('mouth', (0.30, 0.06, 0.06), 0.6),
    chalk=mat('chalk', (0.80, 0.80, 0.76), 0.95), orange=mat('orange', (1.0, 0.36, 0.05), 0.45),
    white=mat('white', (0.95, 0.95, 0.95), 0.5), yellow=mat('yellow', (1.0, 0.75, 0.05), 0.4, coat=0.3),
    cabin=mat('cabin', (0.88, 0.90, 0.92), 0.6), blue=mat('blue', (0.12, 0.33, 0.70), 0.5),
    glass=mat('glass', (0.15, 0.22, 0.30), 0.08, 0.5), tape=mat_stripes('tape', (1.0, 0.8, 0.05), (0.05, 0.05, 0.05), 6.0),
    leaf=mat('leaf', (0.30, 0.48, 0.18), 0.85), leaf2=mat('leaf2', (0.42, 0.55, 0.20), 0.85),
    hill=mat('hill', (0.55, 0.60, 0.32), 0.95), hill2=mat('hill2', (0.66, 0.62, 0.40), 0.95),
    gravel=mat('gravel', (0.55, 0.53, 0.50), 0.95), sign=mat('sign', (0.98, 0.96, 0.90), 0.6),
    redpaint=mat('redpaint', (0.80, 0.10, 0.06), 0.45), phone=mat('phone', (0.05, 0.05, 0.06), 0.25, coat=1.0),
    screen=mat('screen', (0.55, 0.80, 1.0), 0.2, emit=3.0), sweat=mat('sweat', (0.55, 0.80, 1.0), 0.05, emit=0.6),
    star=mat('star', (1.0, 0.85, 0.15), 0.3, emit=2.0), dust=mat('dust', (0.80, 0.70, 0.55), 0.95, alpha=0.55),
    flash=mat('flash', (1.0, 0.95, 0.8), 0.3, emit=12.0),
    g_blue=mat('g_blue', (0.15, 0.6, 1.0), 0.3, emit=1.5, alpha=0.75), g_orange=mat('g_orange', (1.0, 0.45, 0.05), 0.3, emit=1.5, alpha=0.75),
    g_yellow=mat('g_yellow', (1.0, 0.85, 0.1), 0.3, emit=1.5, alpha=0.8),
    a_red=mat('a_red', (1.0, 0.16, 0.08), 0.3, emit=1.6), a_blue=mat('a_blue', (0.15, 0.6, 1.0), 0.3, emit=1.6),
    a_yellow=mat('a_yellow', (1.0, 0.82, 0.1), 0.3, emit=1.6), a_green=mat('a_green', (0.2, 0.95, 0.35), 0.3, emit=1.6),
)
# pull rope gets its own material so its tension glow can be animated
M['rope_pull'] = mat_fabric('rope_pull', (0.80, 0.64, 0.40), 0.85, 60)
_nt, _b = _bsdf(M['rope_pull']); _in(_b, 'Emission Color', 'Emission').default_value = (1.0, 0.12, 0.05, 1)
ROPE_EMIT = _in(_b, 'Emission Strength'); ROPE_EMIT_PATH = f'nodes["{_b.name}"].inputs[{list(_b.inputs).index(ROPE_EMIT)}].default_value'

# ------------------------------------------------------------------ geometry helpers
COLL = sc.collection
def link(o, parent=None):
    if o.name not in COLL.objects: COLL.objects.link(o)
    if parent is not None: o.parent = parent
    return o
def empty(name, loc=(0, 0, 0), parent=None, size=0.1):
    o = bpy.data.objects.new(name, None); o.empty_display_size = size; o.location = loc; return link(o, parent)
def mesh_obj(name, bm, m=None, loc=(0, 0, 0), parent=None, smooth=False, mats=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mm in (mats or ([m] if m else [])): me.materials.append(mm)
    if smooth:
        try: me.shade_smooth()
        except Exception: me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me); o.location = loc; return link(o, parent)
def _xf(bm, mtx): bmesh.ops.transform(bm, matrix=mtx, verts=bm.verts)
def box(name, size, loc=(0, 0, 0), m=None, parent=None, rot=None, bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    _xf(bm, Matrix.Diagonal((*size, 1)))
    if rot: _xf(bm, Euler(rot).to_matrix().to_4x4())
    o = mesh_obj(name, bm, m, loc, parent)
    if bevel:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'
    return o
AX = {'X': Euler((0, pi / 2, 0)).to_matrix().to_4x4(), 'Y': Euler((pi / 2, 0, 0)).to_matrix().to_4x4(), 'Z': Matrix.Identity(4)}
def cyl(name, r, depth, loc=(0, 0, 0), m=None, parent=None, axis='Z', verts=20, base=None, r2=None, smooth=True, caps_m=None):
    """cylinder (or cone with r2) along axis. base='+'/'-': origin at that end instead of the centre."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    if base == '-': _xf(bm, Matrix.Translation((0, 0, depth / 2)))
    if base == '+': _xf(bm, Matrix.Translation((0, 0, -depth / 2)))
    _xf(bm, AX[axis])
    mats = [m] if caps_m is None else [m, caps_m]
    if caps_m is not None:
        ax = Vector({'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[axis])
        for f in bm.faces:
            if abs(f.normal.dot(ax)) > 0.9: f.material_index = 1
    o = mesh_obj(name, bm, None, loc, parent, smooth, mats)
    if smooth:  # keep cap edges crisp
        o.data.polygons.foreach_set('use_smooth', [abs(p.normal[{'X': 0, 'Y': 1, 'Z': 2}[axis]]) < 0.9 for p in o.data.polygons])
    return o
def sph(name, r, loc=(0, 0, 0), m=None, parent=None, scale=(1, 1, 1), seg=20, ring=12, smooth=True, half=False):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    if half:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context='VERTS')
    _xf(bm, Matrix.Diagonal((*scale, 1)))
    return mesh_obj(name, bm, m, loc, parent, smooth)
def ico(name, r, loc=(0, 0, 0), m=None, parent=None, scale=(1, 1, 1), sub=1, jitter=0.0, smooth=False):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    for v in bm.verts:
        v.co += v.co.normalized() * jitter * r * noise.noise(v.co * 3.1 + Vector((random.random() * 50, 0, 0)))
    _xf(bm, Matrix.Diagonal((*scale, 1)))
    return mesh_obj(name, bm, m, loc, parent, smooth)
def rod(name, a, b, r, m=None, parent=None, verts=10):
    a, b = Vector(a), Vector(b); d = b - a
    o = cyl(name, r, d.length, (a + b) / 2, m, parent, verts=verts)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); return o
def text3d(name, body, size, loc, rot, m, parent=None, extrude=0.01, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = 'CENTER'
    try: cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    except Exception as e: print('font', e)
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = rot; o.data.materials.append(m)
    return link(o, parent)
def star_mesh(name, r, m, parent=None):
    bm = bmesh.new(); pts = []
    for i in range(10):
        a = pi / 2 + i * pi / 5; rr = r if i % 2 == 0 else r * 0.45
        pts.append(bm.verts.new((rr * cos(a), 0, rr * sin(a))))
    f = bm.faces.new(pts); bmesh.ops.solidify(bm, geom=[f], thickness=0.02)
    return mesh_obj(name, bm, m, parent=parent)
def arrow(name, length, r, m, axis='X'):
    """emissive force/velocity arrow along +axis, origin at its tail."""
    root = empty(name)
    hl = min(length * 0.4, r * 5)
    sh = cyl(name + '_s', r, length - hl, (0, 0, 0), m, root, axis='Z', base='-', verts=12)
    hd = cyl(name + '_h', r * 2.6, hl, (0, 0, length - hl), m, root, axis='Z', base='-', r2=0.0, verts=16)
    root.rotation_euler = {'X': (0, pi / 2, 0), '-X': (0, -pi / 2, 0), 'Z': (0, 0, 0), '-Z': (pi, 0, 0), 'Y': (-pi / 2, 0, 0)}[axis]
    return root

# ------------------------------------------------------------------ record / bake
REC, CONST, FR = {}, set(), [0]
def put(idb, path, idx, v, const=False):
    REC.setdefault((idb, path, idx), {})[FR[0]] = float(v)
    if const: CONST.add((idb, path, idx))
def LOC(o, v, const=False):
    o.location = v
    for i in range(3): put(o, 'location', i, v[i], const)
def ROT(o, v, const=False):
    o.rotation_euler = v
    for i in range(3): put(o, 'rotation_euler', i, v[i], const)
def SCL(o, s):
    s = (s, s, s) if isinstance(s, (int, float)) else s
    o.scale = s
    for i in range(3): put(o, 'scale', i, s[i])
def VIS(o, on):
    for ob in [o] + list(o.children_recursive):
        ob.hide_render = not on; put(ob, 'hide_render', -1, not on, True)
def PROP(idb, path, v, const=False):
    obj, attr = (idb.path_resolve(path.rsplit('.', 1)[0]), path.rsplit('.', 1)[1]) if '.' in path else (idb, path)
    setattr(obj, attr, v); put(idb, path, -1, v, const)
def CO(cu, i, p):
    cu.splines[0].points[i].co = (p[0], p[1], p[2], 1)
    for k in range(3): put(cu, f'splines[0].points[{i}].co', k, p[k])

CUTS = []
def write_fcurves():
    t0 = time.time(); groups = {}
    for (idb, path, idx), d in REC.items(): groups.setdefault(idb, []).append((path, idx, d))
    cutprev = set(c - 1 for c in CUTS); nkeys = 0
    for idb, chans in groups.items():
        for path, idx, d in chans:
            idb.keyframe_insert(data_path=path, index=idx, frame=min(d))
        ad = idb.animation_data
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        for path, idx, d in chans:
            fc = cb.fcurves.find(path, index=max(idx, 0))
            fr = sorted(d); vals = [d[f] for f in fr]; const = (idb, path, idx) in CONST
            keep = []
            for i, f in enumerate(fr):
                if i == 0 or i == len(fr) - 1 or abs(vals[i] - vals[i - 1]) > 1e-7 or (not const and abs(vals[i] - vals[i + 1]) > 1e-7):
                    keep.append(i)
            kp = fc.keyframe_points
            while len(kp): kp.remove(kp[0], fast=True)
            kp.add(len(keep))
            kp.foreach_set('co', [x for i in keep for x in (fr[i], vals[i])])
            kp.foreach_set('interpolation', [0 if (const or fr[i] in cutprev) else 1 for i in keep])
            fc.update(); nkeys += len(keep)
    print(f'baked {len(REC)} channels, {nkeys} keys in {time.time() - t0:.1f}s')

# ------------------------------------------------------------------ world + lights
wd = bpy.data.worlds.new('sky'); sc.world = wd
try: wd.use_nodes = True
except Exception: pass
wn = wd.node_tree; bg = next(n for n in wn.nodes if n.type == 'BACKGROUND')
tc = wn.nodes.new('ShaderNodeTexCoord'); sep = wn.nodes.new('ShaderNodeSeparateXYZ')
wn.links.new(tc.outputs['Generated'], sep.inputs[0])
sky = wn.nodes.new('ShaderNodeValToRGB'); se = sky.color_ramp.elements
se[0].position, se[0].color = 0.0, (0.98, 0.80, 0.62, 1)
se[1].position, se[1].color = 0.6, (0.42, 0.64, 0.95, 1)
e = se.new(0.12); e.color = (0.82, 0.86, 0.92, 1)
wn.links.new(sep.outputs['Z'], sky.inputs['Fac']); wn.links.new(sky.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.45

def sun(name, energy, col, rot, angle, shadow=True):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy; ld.color = col; ld.angle = radians(angle)
    ld.use_shadow = shadow
    o = bpy.data.objects.new(name, ld); o.rotation_euler = rot; return link(o)
SUN = sun('sun', 4.6, (1.0, 0.86, 0.68), (radians(58), 0, radians(-100)), 1.5)
sun('fill', 0.5, (0.70, 0.80, 1.0), (radians(50), 0, radians(-10)), 10.0, shadow=False)
sun('rim', 1.2, (1.0, 0.85, 0.7), (radians(70), 0, radians(150)), 8.0, shadow=False)

# ------------------------------------------------------------------ environment
ground = box('ground', (400, 400, 0.2), (0, 0, -0.1), M['ground'])
box('path_strip', (34, 5.0, 0.01), (2.5, 0, 0.004), M['path'])

def cone_prop(name, loc):
    c = cyl(name, 0.17, 0.62, (loc[0], loc[1], 0.31), M['orange'], r2=0.03, verts=16)
    cyl(name + '_band', 0.115, 0.1, (0, 0, 0.06), M['white'], c, r2=0.09, verts=16)
    box(name + '_base', (0.42, 0.42, 0.04), (0, 0, -0.29), M['orange'], c)
    return c
def barrier(name, x, y, rotz=0.0):
    e = empty(name, (x, y, 0)); e.rotation_euler = (0, 0, rotz)
    box(name + '_p', (2.0, 0.08, 0.6), (0, 0, 0.62), M['orange'], e, bevel=0.02)
    box(name + '_s', (2.0, 0.085, 0.12), (0, 0, 0.62), M['white'], e)
    for sx in (-0.95, 0.95):
        box(name + f'_f{sx}', (0.1, 0.5, 0.06), (sx, 0, 0.03), M['dark'], e)
        box(name + f'_l{sx}', (0.06, 0.06, 0.95), (sx, 0, 0.48), M['steel'], e)
    return e
def timber_stack(name, x, y, rotz=0.0, rows=3, n=4, L_=3.2):
    e = empty(name, (x, y, 0)); e.rotation_euler = (0, 0, rotz)
    for r in range(rows):
        for i in range(n - r % 2):
            box(f'{name}_{r}_{i}', (L_, 0.22, 0.2), (0, (i - (n - 1) / 2) * 0.24 + (0.12 if r % 2 else 0), 0.1 + r * 0.2), M['wood'], e, bevel=0.01)
    return e
def tree(name, x, y, s=1.0):
    e = empty(name, (x, y, 0))
    cyl(name + '_t', 0.18 * s, 1.6 * s, (0, 0, 0.8 * s), M['wood_dark'], e, verts=8)
    ico(name + '_c1', 1.4 * s, (0, 0, 2.4 * s), M['leaf' if random.random() < 0.5 else 'leaf2'], e, (1, 1, 1.15), 1, 0.25)
    ico(name + '_c2', 1.0 * s, (0.3 * s, 0.2 * s, 3.3 * s), M['leaf2'], e, (1, 1, 1.1), 1, 0.25)
    return e
def gravel_pile(name, x, y, r=2.0, h=1.0, m=None):
    return ico(name, r, (x, y, 0), m or M['gravel'], scale=(1, 1, h / r), sub=2, jitter=0.25)
def cabin(name, x, y, rotz):
    e = empty(name, (x, y, 0)); e.rotation_euler = (0, 0, rotz)
    box(name + '_b', (6.0, 2.5, 2.6), (0, 0, 1.45), M['cabin'], e, bevel=0.03)
    box(name + '_base', (6.2, 2.6, 0.18), (0, 0, 0.09), M['dark'], e)
    box(name + '_roof', (6.2, 2.7, 0.12), (0, 0, 2.8), M['blue'], e)
    for wx in (-1.8, 0.0):
        box(name + f'_w{wx}', (1.3, 0.05, 0.9), (wx, -1.26, 1.75), M['glass'], e)
    box(name + '_door', (0.95, 0.05, 2.0), (2.0, -1.26, 1.2), M['blue'], e)
    text3d(name + '_txt', 'SITE OFFICE', 0.32, (-0.9, -1.29, 2.45), (pi / 2, 0, 0), M['blue'], e)
    return e
def sign(name, txt, x, y, rotz, size=0.26, w=1.9, h=0.75, post=1.6, m_txt=None):
    e = empty(name, (x, y, 0)); e.rotation_euler = (0, 0, rotz)
    for px in (-w / 2 + 0.1, w / 2 - 0.1):
        box(name + f'_p{px}', (0.08, 0.08, post), (px, 0.03, post / 2), M['wood'], e)
    box(name + '_board', (w, 0.05, h), (0, 0, post - h / 2 + 0.1), M['sign'], e, bevel=0.01)
    text3d(name + '_t', txt, size, (0, -0.035, post - h / 2 + 0.1), (pi / 2, 0, 0), m_txt or M['redpaint'], e)
    return e
def wheelbarrow(name, x, y, rotz):
    e = empty(name, (x, y, 0)); e.rotation_euler = (0, 0, rotz)
    box(name + '_tray', (0.9, 0.6, 0.3), (0, 0, 0.55), M['redpaint'], e, bevel=0.05)
    cyl(name + '_w', 0.2, 0.08, (0.55, 0, 0.2), M['dark'], e, axis='Y')
    for s in (-0.25, 0.25):
        rod(name + f'_h{s}', (0.4, s, 0.4), (-0.95, s * 1.1, 0.62), 0.025, M['steel'], e)
        rod(name + f'_l{s}', (-0.35, s, 0.4), (-0.35, s, 0.0), 0.02, M['steel'], e)
    return e

def lattice(name, p0, p1, w, m, parent=None, n=10):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    e = empty(name, p0, parent); e.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    Ln = d.length; off = [(-w / 2, -w / 2), (w / 2, -w / 2), (w / 2, w / 2), (-w / 2, w / 2)]
    for i, (a, b) in enumerate(off):
        rod(f'{name}_c{i}', (a, b, 0), (a, b, Ln), 0.045, m, e, 8)
    for k in range(n):
        z0, z1 = Ln * k / n, Ln * (k + 1) / n
        for i in range(4):
            a, b = off[i], off[(i + 1) % 4]
            rod(f'{name}_d{k}_{i}', (a[0], a[1], z0), (b[0], b[1], z1), 0.025, m, e, 6)
    return e
def broken_crane(x, y, rotz):
    e = empty('crane', (x, y, 0)); e.rotation_euler = (0, 0, rotz)
    for s in (-1.3, 1.3):
        box(f'crane_track{s}', (5.0, 0.8, 0.9), (0, s, 0.45), M['dark'], e, bevel=0.12)
    box('crane_body', (3.6, 2.6, 1.5), (-0.3, 0, 1.65), M['yellow'], e, bevel=0.06)
    box('crane_cw', (1.0, 2.4, 1.1), (-2.3, 0, 1.6), M['dark'], e, bevel=0.05)
    box('crane_cab', (1.3, 1.1, 1.4), (1.0, 0.75, 2.9), M['yellow'], e, bevel=0.05)
    box('crane_win', (0.05, 0.9, 0.8), (1.66, 0.75, 3.0), M['glass'], e)
    lattice('crane_boom1', (1.2, -0.3, 2.4), (6.6, -0.3, 6.4), 0.8, M['yellow'], e, 8)
    lattice('crane_boom2', (6.6, -0.3, 6.4), (12.0, -0.3, 0.3), 0.8, M['yellow'], e, 9)   # snapped and drooping
    rod('crane_cable', (6.6, -0.3, 6.4), (8.2, -0.3, 0.6), 0.02, M['dark'], e)
    box('crane_hook', (0.3, 0.12, 0.4), (8.2, -0.3, 0.45), M['redpaint'], e)
    sign('crane_sign', 'OUT OF ORDER', 3.2, -2.4, 0.0, 0.3, 2.6, 0.9, 1.3).parent = e
    for i, (a, b) in enumerate([((-3, -3.2), (5.5, -3.2)), ((5.5, -3.2), (5.5, 3.0))]):
        p0, p1 = Vector((*a, 0.9)), Vector((*b, 0.9))
        t = box(f'crane_tape{i}', ((p1 - p0).length, 0.02, 0.12), (p0 + p1) / 2, M['tape'], e)
        t.rotation_euler = (0, 0, atan2(p1.y - p0.y, p1.x - p0.x))
        for p in (p0, p1): cyl(f'crane_tp{i}{p.x}', 0.04, 1.0, (p.x, p.y, 0.5), M['orange'], e, verts=8)
    return e

broken_crane(-9.0, 15.0, radians(-15))
cabin('cabin', 7.5, 13.5, radians(-6))
timber_stack('timber1', -4.5, 6.5, radians(80))
timber_stack('timber2', 17.5, 6.0, radians(10), rows=2)
gravel_pile('gravel1', 20.0, 12.0, 3.0, 1.6); gravel_pile('gravel2', -18.0, 9.0, 3.4, 1.8, M['hill2'])
wheelbarrow('barrow', 2.0, 5.2, radians(200))
for i, (x, y) in enumerate([(-6.5, -3.5), (-1.0, -5.5), (4.5, -5.0), (8.5, -9.5), (17.5, -5.5), (-12.5, -4.0),
                            (12.0, 4.6), (1.0, 4.4), (-7.5, 3.6), (19.0, -1.5)]):
    cone_prop(f'cone{i}', (x, y))
for i in range(22):
    barrier(f'bar{i}', -24 + i * 2.15, 21.0)
for i in range(10):
    barrier(f'barL{i}', -25.0, 20.0 - i * 2.15, pi / 2)
for i in range(46):
    a = random.uniform(0, 2 * pi); r = random.uniform(32, 70)
    x, y = r * cos(a), r * sin(a) * 0.9 + 8
    tree(f'tree{i}', x, y, random.uniform(1.4, 2.6))
for i in range(16):
    a = i / 16 * 2 * pi; r = 150
    ico(f'hill{i}', 55, (r * cos(a), r * sin(a), -14), M['hill' if i % 2 else 'hill2'], scale=(1.4, 1.0, 0.45), sub=2, jitter=0.15)

# destination: chalk outline + X + flags + sign
X_DEST = 6.15
for i, (cx, cy, sx, sy) in enumerate([(X_DEST, 1.8, 5.4, 0.05), (X_DEST, -1.8, 5.4, 0.05), (X_DEST - 2.7, 0, 0.05, 3.6), (X_DEST + 2.7, 0, 0.05, 3.6)]):
    box(f'chalk{i}', (sx, sy, 0.01), (cx, cy, 0.008), M['chalk'])
for i, a in enumerate((0.55, -0.55)):
    c = box(f'chalkx{i}', (6.2, 0.06, 0.01), (X_DEST, 0, 0.009), M['chalk']); c.rotation_euler = (0, 0, a)
for i, (fx, fy) in enumerate([(X_DEST - 2.7, -1.8), (X_DEST + 2.7, -1.8), (X_DEST + 2.7, 1.8)]):
    f = empty(f'flag{i}', (fx, fy, 0))
    cyl(f'flag{i}_p', 0.02, 1.2, (0, 0, 0.6), M['white'], f, verts=8)
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in ((0, 0, 1.18), (0.42, 0, 1.06), (0, 0, 0.94))]; bm.faces.new(vs)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.01); mesh_obj(f'flag{i}_c', bm, M['orange'], parent=f)
sign('destsign', 'ROCK GOES HERE', X_DEST + 3.4, 2.6, radians(-8), 0.22, 2.1, 0.62, 1.25)

# ------------------------------------------------------------------ the rock (100 t: ~35 m^3 of granite)
RX, RY, RZ = 2.4, 1.6, 1.6
def make_rock():
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=8, use_grid_fill=True)
    for v in bm.verts:
        p = v.co.copy(); n = (abs(p.x) ** 4 + abs(p.y) ** 4 + abs(p.z) ** 4) ** 0.25
        q = Vector((p.x / n * RX, p.y / n * RY, p.z / n * RZ)); dn = q.normalized()
        q += dn * (0.26 * noise.noise(q * 0.42 + Vector((3.1, 1.7, 0.4))) + 0.09 * noise.noise(q * 1.3 + Vector((9, 2, 5))))
        v.co = q
    zb = -RZ * 0.8
    for v in bm.verts:
        v.co.z = max(v.co.z, zb) - zb
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    tree_ = BVHTree.FromBMesh(bm)
    me = bpy.data.meshes.new('rock'); bm.to_mesh(me); bm.free(); me.materials.append(M['rock'])
    o = bpy.data.objects.new('rock', me); link(o)
    return o, tree_
ROCK, RBVH = make_rock()
def rock_surface(zl, ang, out=0.035):
    d = Vector((cos(ang), sin(ang), 0)); o = Vector((0, 0, zl)) + d * 8
    hit = RBVH.ray_cast(o, -d)
    return (hit[0] + d * out) if hit[0] else Vector((0, 0, zl)) + d * 2.5
def ring_curve(name, zl, m, parent, r=0.035, n=56):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3
    sp = cu.splines.new('NURBS'); sp.points.add(n - 1); sp.use_cyclic_u = True; sp.order_u = 3
    for i in range(n):
        p = rock_surface(zl, 2 * pi * i / n, r + 0.01); sp.points[i].co = (p.x, p.y, p.z, 1)
    o = bpy.data.objects.new(name, cu); cu.materials.append(m); return link(o, parent)
REAR_X = lambda zl: rock_surface(zl, pi, 0).x
FRONT_X = lambda zl: rock_surface(zl, 0.0, 0).x
BELT = ring_curve('belt', 1.1, M['rope'], ROCK)            # rope stage
SLING = ring_curve('sling', 0.62, M['rope'], ROCK)         # capstan stage
ROCK_FRONT_11 = FRONT_X(1.1); ROCK_FRONT_06 = FRONT_X(0.62); ROCK_REAR_09 = REAR_X(0.9)

# weight arrow + pulley block (parented to rock)
W_ARROW = arrow('w_arrow', 1.6, 0.09, M['a_red'], '-Z'); W_ARROW.parent = ROCK; W_ARROW.location = (0, 0, 4.9)
PULLEY = empty('pulley', (ROCK_FRONT_06 + 0.32, 0, 0.62), ROCK)
box('pulley_block', (0.34, 0.5, 0.22), (0, 0, 0.0), M['wood_dark'], PULLEY, bevel=0.03)
SHEAVE = cyl('sheave', 0.19, 0.08, (0, 0, 0.0), M['steel'], PULLEY, verts=24)
box('sheave_mark', (0.06, 0.2, 0.09), (0.09, 0, 0), M['redpaint'], SHEAVE)
rod('pulley_strap', (-0.32, 0, 0), (-0.05, 0, 0), 0.04, M['rope'], PULLEY)
PULLEY_HL = sph('pulley_hl', 0.36, (0, 0, 0), M['g_yellow'], PULLEY, (1, 1, 0.6))
V_ARROW = arrow('v_arrow', 1.3, 0.06, M['a_yellow'], 'X'); V_ARROW.parent = ROCK; V_ARROW.location = (-0.6, -RY - 0.25, 1.2)

# ------------------------------------------------------------------ rollers (Ø 0.30 m logs) + cribbing
R_ROLL = 0.15; ROCK_Z_ROLL = 2 * R_ROLL
UNDER = [-1.8, -0.9, 0.0, 0.9, 1.8]; AHEAD = [2.7 + 0.9 * i for i in range(7)]
ROLLERS = []
for i, p in enumerate(UNDER + AHEAD):
    o = cyl(f'roller{i}', R_ROLL, 3.6, (p, 0, R_ROLL), M['woody'], axis='Y', verts=18, caps_m=M['endgrain'])
    box(f'roller{i}_mark', (0.05, 3.62, 0.05), (0, 0, R_ROLL - 0.02), M['wood_dark'], o)
    ROLLERS.append((o, p, i < len(UNDER)))
CRIBS = []
for i, cx in enumerate((-1.35, 1.35)):
    e = empty(f'crib{i}', (cx, 0, 0))
    for k in range(3):
        box(f'crib{i}_{k}', (0.3, 2.2, 0.1), (0, 0, 0.05 + 0.1 * k), M['wood'], e, bevel=0.01)
    CRIBS.append(e)

# ------------------------------------------------------------------ lever (8.16 m beam, 50:1)
PIV = Vector((-2.36, 0, 0.20)); LONG, SHORT = 8.0, 0.16; TH0 = radians(15.0); TH1 = radians(5.6)
LEVER = empty('lever', PIV)
box('lever_beam', (LONG + SHORT, 0.16, 0.16), (-(LONG - SHORT) / 2, 0, 0), M['wood'], LEVER, bevel=0.015)
box('lever_band', (0.08, 0.18, 0.18), (SHORT - 0.04, 0, 0), M['steel'], LEVER)
HL_LONG = box('hl_long', (LONG, 0.24, 0.24), (-LONG / 2, 0, 0), M['g_blue'], LEVER)
HL_SHORT = box('hl_short', (SHORT + 0.06, 0.26, 0.26), (SHORT / 2, 0, 0), M['g_orange'], LEVER)
FULC = cyl('fulcrum', 0.06, 0.9, (PIV.x, 0, 0.06), M['wood_dark'], axis='Y', verts=14, caps_m=M['endgrain'])
BASKET = empty('basket')
box('basket_floor', (0.95, 0.95, 0.06), (0, 0, 0.03), M['wood'], BASKET)
for i, (bx, by, sx, sy) in enumerate([(0.45, 0, 0.05, 0.95), (-0.45, 0, 0.05, 0.95), (0, 0.45, 0.95, 0.05), (0, -0.45, 0.95, 0.05)]):
    box(f'basket_w{i}', (sx, sy, 0.3), (bx, by, 0.18), M['wood'], BASKET)
B_ROPES = []
for i, s in enumerate((-0.4, 0.4)):
    cu = bpy.data.curves.new(f'bas_rope{i}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.018
    sp = cu.splines.new('POLY'); sp.points.add(1); o = bpy.data.objects.new(f'bas_rope{i}', cu); cu.materials.append(M['rope']); link(o)
    B_ROPES.append((cu, s))
BAGS = []
for i in range(5):
    BAGS.append(ico(f'bag{i}', 0.3, (0, 0, 0), M['burlap'], scale=(1.15, 0.8, 0.5), sub=2, jitter=0.12, smooth=True))
for i, (x, y, z) in enumerate([(-11.6, 2.4, 0.15), (-12.2, 2.2, 0.15), (-11.9, 2.9, 0.15), (-11.9, 2.5, 0.42)]):
    ico(f'pilebag{i}', 0.3, (x, y, z), M['burlap'], scale=(1.15, 0.8, 0.5), sub=2, jitter=0.12, smooth=True).rotation_euler = (0, 0, random.uniform(0, 3))
PRY = empty('prybar')
cyl('pry_bar', 0.03, 1.7, (0, 0, 0), M['steel'], PRY, axis='X', base='-', verts=10)
rod('pry_tip', (0, 0, 0), (-0.12, 0, -0.06), 0.03, M['steel'], PRY)

# ------------------------------------------------------------------ capstan (arms 3 m, drum r 0.15 m: 20:1)
CAP = Vector((14.0, 0, 0)); R_DRUM = 0.15; R_ARM = 3.0; R_PUSH = 2.55; DRUM_Z = 0.5; ANCHOR = Vector((12.75, -0.18, 0.5))
CAP_PARTS = []
cap_base = empty('cap_base', CAP)
for i, a in enumerate((0, pi / 2)):
    b_ = box(f'cap_sill{i}', (2.6, 0.24, 0.2), (0, 0, 0.1), M['wood_dark'], cap_base, bevel=0.02); b_.rotation_euler = (0, 0, a); CAP_PARTS.append(b_)
for i in range(4):
    a = i * pi / 2 + pi / 4
    s = cyl(f'cap_stake{i}', 0.07, 0.7, (1.0 * cos(a), 1.0 * sin(a), 0.2), M['wood'], cap_base, verts=8); CAP_PARTS.append(s)
    br = rod(f'cap_brace{i}', (1.15 * cos(a), 1.15 * sin(a), 0.2), (0.24 * cos(a), 0.24 * sin(a), 0.92), 0.06, M['wood'], cap_base); CAP_PARTS.append(br)
collar = cyl('cap_collar', 0.3, 0.1, (0, 0, 0.92), M['steel'], cap_base, verts=24); CAP_PARTS.append(collar)
CAP_ROT = empty('cap_rot', CAP)
drum = cyl('cap_drum', R_DRUM, 0.75, (0, 0, 0.55), M['woodz'], CAP_ROT, verts=24); CAP_PARTS.append(drum)
for k in range(3): box(f'cap_drumrib{k}', (0.06, 0.06, 0.7), (R_DRUM * cos(k * 2.1), R_DRUM * sin(k * 2.1), 0.55), M['steel'], drum)
head = cyl('cap_head', 0.32, 0.26, (0, 0, 1.08), M['wood_dark'], CAP_ROT, verts=24); CAP_PARTS.append(head)
for k in range(4): box(f'cap_headbolt{k}', (0.06, 0.06, 0.28), (0.3 * cos(k * pi / 2 + pi / 4), 0.3 * sin(k * pi / 2 + pi / 4), 0), M['steel'], head)
ARMS = []
for i in range(4):
    a = i * pi / 2
    ar = box(f'cap_arm{i}', (R_ARM, 0.13, 0.13), (R_ARM / 2 * cos(a), R_ARM / 2 * sin(a), 1.08), M['wood'], CAP_ROT, bevel=0.015)
    ar.rotation_euler = (0, 0, a); CAP_PARTS.append(ar); ARMS.append(ar)
COIL = cyl('cap_coil', R_DRUM + 0.025, 1.0, (0, 0, DRUM_Z), M['rope'], CAP_ROT, verts=24)
HL_ARMS = [box(f'hl_arm{i}', (R_ARM - 0.3, 0.2, 0.2), ((R_ARM + 0.3) / 2 * cos(i * pi / 2), (R_ARM + 0.3) / 2 * sin(i * pi / 2), 1.08), M['g_blue'], CAP_ROT,
               rot=(0, 0, i * pi / 2)) for i in range(4)]
HL_DRUM = cyl('hl_drum', R_DRUM + 0.08, 0.8, (0, 0, 0.55), M['g_orange'], CAP_ROT, verts=24)
anc = cyl('cap_anchor', 0.09, 1.1, (ANCHOR.x, ANCHOR.y, 0.35), M['wood_dark'], verts=10); CAP_PARTS.append(anc)
def rope_line(name, m, n=2, r=0.03):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 2
    sp = cu.splines.new('POLY'); sp.points.add(n - 1); o = bpy.data.objects.new(name, cu); cu.materials.append(m); link(o); return o, cu
LINE_A, CU_A = rope_line('cap_line_a', M['rope'])
LINE_B, CU_B = rope_line('cap_line_b', M['rope'])
PULL1, CU_P1 = rope_line('pull_rope1', M['rope_pull'], 10, 0.035)
PULL2, CU_P2 = rope_line('pull_rope2', M['rope_pull'], 10, 0.035)
COILPILE = ico('rope_coil', 0.32, (4.0, -1.1, 0.08), M['rope'], scale=(1, 1, 0.3), sub=2, jitter=0.1, smooth=True)
T_ARROWS = [arrow(f't_arrow{i}', 1.1, 0.05, M['a_red'], 'X') for i in range(2)]
PUSH_ARROW = arrow('push_arrow', 0.55, 0.04, M['a_blue'], 'X')
LIFT_ARROW = arrow('lift_arrow', 0.3, 0.025, M['a_red'], 'Z')
LOAD_ARROW = arrow('load_arrow', 0.9, 0.06, M['a_blue'], '-Z')
HALF_ARROW = arrow('half_arrow', 0.65, 0.06, M['a_green'], 'X')
FLASH = ico('snap_flash', 0.25, (0, 0, 0), M['flash'], sub=1)
DUSTS = [ico(f'dust{i}', 0.25, (0, 0, 0), M['dust'], sub=1, jitter=0.3, smooth=True) for i in range(18)]

# ------------------------------------------------------------------ the engineer (procedural rig)
class Engineer:
    HIP = 0.58
    def __init__(s):
        j = s.j = {}
        j['root'] = empty('eng_root')
        j['pelvis'] = empty('eng_pelvis', (0, 0, s.HIP), j['root'])
        sph('eng_hips', 0.2, (0, 0, 0.02), M['overalls'], j['pelvis'], (0.95, 1.18, 0.7))
        j['torso'] = empty('eng_torso', (0, 0, 0), j['pelvis'])
        sph('eng_belly', 0.2, (0.01, 0, 0.2), M['overalls'], j['torso'], (1.0, 1.25, 1.25))
        sph('eng_vest', 0.205, (0.0, 0, 0.33), M['vest'], j['torso'], (1.0, 1.28, 0.95))
        cyl('eng_band', 0.215, 0.05, (0, 0, 0.28), M['reflect'], j['torso'], verts=24).scale = (1.0, 1.27, 1)
        box('eng_bib', (0.04, 0.2, 0.14), (0.2, 0, 0.18), M['overalls'], j['torso'])
        j['head'] = empty('eng_head', (0, 0, 0.5), j['torso'])
        sph('eng_neck', 0.08, (0, 0, 0.02), M['skin'], j['head'])
        sph('eng_skull', 0.23, (0, 0, 0.21), M['skin'], j['head'], (1.0, 1.0, 0.98))
        sph('eng_nose', 0.06, (0.225, 0, 0.18), M['skin'], j['head'], (1, 0.9, 0.85))
        sph('eng_must', 0.06, (0.205, 0, 0.115), M['hair'], j['head'], (0.7, 2.2, 0.55))
        s.mouth = sph('eng_mouth', 0.05, (0.195, 0, 0.06), M['mouth'], j['head'], (0.5, 1.0, 0.25))
        s.eyes, s.pupils, s.brows = [], [], []
        for k, y in enumerate((0.085, -0.085)):
            e = sph(f'eng_eye{k}', 0.062, (0.185, y, 0.27), M['eye'], j['head'], (0.6, 1, 1.15)); s.eyes.append(e)
            s.pupils.append(sph(f'eng_pupil{k}', 0.032, (0.03, 0, 0.0), M['pupil'], e, (0.9, 1.0, 1.0)))
            s.brows.append(box(f'eng_brow{k}', (0.03, 0.08, 0.022), (0.205, y, 0.36), M['hair'], j['head']))
        sph('eng_ear0', 0.05, (0.0, 0.225, 0.2), M['skin'], j['head'], (0.6, 0.5, 1)); sph('eng_ear1', 0.05, (0.0, -0.225, 0.2), M['skin'], j['head'], (0.6, 0.5, 1))
        sph('eng_hat', 0.255, (0, 0, 0.29), M['hat'], j['head'], (1.04, 1.0, 0.86), half=True)
        cyl('eng_brim', 0.29, 0.03, (0.05, 0, 0.3), M['hat'], j['head'], verts=28).scale = (1.12, 0.95, 1)
        box('eng_ridge', (0.40, 0.07, 0.035), (0, 0, 0.485), M['hat'], j['head'], bevel=0.02)
        for side, y in (('L', 0.27), ('R', -0.27)):
            sh = j['sh' + side] = empty('eng_sh' + side, (0, y, 0.43), j['torso'])
            sph('eng_shoulder' + side, 0.075, (0, 0, 0), M['vest'], sh)
            cyl('eng_uarm' + side, 0.058, 0.27, (0, 0, 0), M['shirt'], sh, base='+', verts=12)
            el = j['el' + side] = empty('eng_el' + side, (0, 0, -0.27), sh)
            cyl('eng_farm' + side, 0.05, 0.25, (0, 0, 0), M['skin'], el, base='+', verts=12)
            j['hand' + side] = empty('eng_hand' + side, (0, 0, -0.29), el)
            sph('eng_glove' + side, 0.075, (0, 0, 0), M['glove'], j['hand' + side], (1, 0.85, 1.05))
            hp = j['hip' + side] = empty('eng_hip' + side, (0, y * 0.42, 0), j['pelvis'])
            cyl('eng_thigh' + side, 0.078, 0.29, (0, 0, 0), M['overalls'], hp, base='+', verts=12)
            kn = j['kn' + side] = empty('eng_kn' + side, (0, 0, -0.29), hp)
            cyl('eng_shin' + side, 0.068, 0.24, (0, 0, 0), M['overalls'], kn, base='+', verts=12)
            box('eng_boot' + side, (0.24, 0.13, 0.1), (0.045, 0, -0.24), M['boot'], kn, bevel=0.03)
        s.phone = box('eng_phone', (0.025, 0.08, 0.15), (0.06, 0, 0.02), M['phone'], j['handR'], bevel=0.008)
        box('eng_screen', (0.004, 0.068, 0.13), (0.014, 0, 0), M['screen'], s.phone)
        s.stars = [star_mesh(f'eng_star{k}', 0.06, M['star'], j['head']) for k in range(3)]
        s.drops = [sph(f'eng_drop{k}', 0.03, (0, 0, 0), M['sweat'], j['head'], (1, 1, 1.5)) for k in range(2)]

    def apply(s, t, x, y, yaw, P, grounded=True, rz=0.0, pitch=0.0):
        g = lambda k, d=0.0: P.get(k, d)
        pp, lean = g('pp'), g('lean')
        legs = {}
        for side in 'LR':
            a, k = g('hip' + side), g('kn' + side)
            th1 = a - pp; th2 = th1 - k
            legs[side] = -cos(th1) * 0.29 - cos(th2) * 0.24
        pel_z = (0.05 - min(legs.values())) if grounded else s.HIP
        pel_z += g('bob')
        ROT(s.j['root'], (0, pitch, yaw)); LOC(s.j['root'], (x, y, rz))
        LOC(s.j['pelvis'], (g('px'), 0, pel_z)); ROT(s.j['pelvis'], (0, pp, 0))
        ROT(s.j['torso'], (g('roll'), lean, g('twist')))
        ROT(s.j['head'], (g('head_r'), g('head_p'), g('head_y')))
        for side, sg in (('L', 1), ('R', -1)):
            ROT(s.j['sh' + side], (sg * g('ab' + side), -g('sh' + side), 0))
            ROT(s.j['el' + side], (0, -g('el' + side), 0))
            ROT(s.j['hip' + side], (sg * g('hab' + side), -g('hip' + side), 0))
            ROT(s.j['kn' + side], (0, g('kn' + side), 0))
        bl = g('blink'); sq = g('squint'); wide = g('wide')
        for e in s.eyes: SCL(e, (1.0, 1.0 + 0.15 * wide, max(0.08, (1 - bl) * (1 - 0.6 * sq) * (1 + 0.35 * wide))))
        for k, b in enumerate(s.brows):
            ROT(b, (g('brow') * (1 if k == 0 else -1), 0, 0)); LOC(b, (0.205, (0.085, -0.085)[k], 0.36 + 0.03 * wide - 0.02 * sq))
        mo = g('mouth')
        SCL(s.mouth, (1.0, 1.0 - 0.35 * mo, 1.0 + 4.4 * mo))
ENG = Engineer()

def walk(phase, amt=1.0, arms=1.0):
    sp = sin(phase); cp = cos(phase)
    return dict(hipL=0.48 * sp * amt, hipR=-0.48 * sp * amt,
                knL=(0.12 + 0.75 * max(0.0, cp)) * amt, knR=(0.12 + 0.75 * max(0.0, -cp)) * amt,
                shL=-0.4 * sp * amt * arms, shR=0.4 * sp * amt * arms, elL=0.35, elR=0.35,
                bob=0.025 * abs(cp) * amt, lean=0.08 * amt, abL=0.08, abR=0.08)
def blend(a, b, u):
    out = dict(a)
    for k in set(a) | set(b): out[k] = lerp(a.get(k, 0.0), b.get(k, 0.0), u)
    return out
IDLE = dict(abL=0.1, abR=0.1, elL=0.25, elR=0.25, shL=0.05, shR=0.05, knL=0.05, knR=0.05, hipL=0.03, hipR=0.03)
def idle(t):
    P = dict(IDLE); br = sin(t * 2.2) * 0.02
    P['lean'] = br; P['shL'] += br; P['shR'] += br
    return P
def blink(t, P):
    ph = (t * 0.37 + 0.3) % 1.0
    P['blink'] = max(P.get('blink', 0.0), 1.0 - min(1.0, abs(ph - 0.5) * 30)); return P

# ------------------------------------------------------------------ timeline: rock
def rock_x(t):
    """rock centre x (m). Pry heaves then the capstan pull (real speed, then time-lapse)."""
    x = 0.0
    for k, th in enumerate(PRY_T): x += 0.05 * ss(t, th + 0.12, th + 0.42)
    x += cap_dist(t)
    return x
PRY_T = [B['pry'] + 0.55, B['pry'] + 1.45, B['pry'] + 2.35]
X_PRY = 0.15
D_CAP = X_DEST - X_PRY
def _cap_v(t):   # unnormalised speed profile
    if t < T_CAP_GO + 0.25: return 0.0
    real = 0.035
    if t < B['forty'] + 0.6: return real * ss(t, T_CAP_GO + 0.25, T_CAP_GO + 0.8)
    fast = ss(t, B['forty'] + 0.6, B['forty'] + 1.4)
    return (real + fast) * (1 - ss(t, T_ARRIVE - 1.0, T_ARRIVE))
_CAPTAB = []
def _build_cap():
    acc = 0.0; tab = []; dt = 1 / (FPS * 4); t = 0.0
    while t <= DUR + 0.5: tab.append(acc); acc += _cap_v(t) * dt; t += dt
    real_d = 0.0; t = 0.0
    while t < B['forty'] + 0.6: real_d += 0.035 * ss(t, T_CAP_GO + 0.25, T_CAP_GO + 0.8) * dt * (t >= T_CAP_GO + 0.25); t += dt
    # scale only the time-lapse part so the total is exactly D_CAP
    return tab, dt, real_d
_tab, _dt, _real = _build_cap()
_fast_total = _tab[-1] - _real
def cap_dist(t):
    i = int(clamp(t / _dt, 0, len(_tab) - 1)); raw = _tab[i]
    if raw <= _real: return raw
    return _real + (raw - _real) * (D_CAP - _real) / _fast_total
def rock_pose(t):
    """(location, rot_y) of the rock object (origin = bottom centre)."""
    if t < B['rollers']:
        lift = lever_tip_rise(t)
        a = math.asin(lift / (2 * RX * 0.95))
        piv = Vector((RX * 0.95, 0, 0))
        p = piv - Matrix.Rotation(a, 3, 'Y') @ piv
        return Vector((p.x, 0, p.z)), a
    z = lerp(ROCK_Z_ROLL + 0.012, ROCK_Z_ROLL, ss(t, B['rolling'] - 1.0, B['rolling'] - 0.6))
    return Vector((rock_x(t), 0, z)), 0.0

# ------------------------------------------------------------------ timeline: lever + bags
BAG_T = [B['sand'] - 1.1 + 0.28 * i for i in range(5)]       # release times
BAG_FALL = 0.36
T_LEVER = BAG_T[-1] + BAG_FALL + 0.15
def lever_theta(t):
    return lerp(TH0, TH1, sm((t - T_LEVER) / 0.75) ** 1.3)
def lever_tip_rise(t):
    if t < B['lever'] - 0.1: return 0.0
    return SHORT * (sin(TH0) - sin(lever_theta(t)))
def lever_point(t, d):   # point on beam centreline at distance d along the long side (d<0 = short side)
    th = lever_theta(t)
    return PIV + Vector((-d * cos(th), 0, d * sin(th)))

# ------------------------------------------------------------------ timeline: capstan
CAP_POP0 = B['capstan'] + 0.05
def cap_pop(i, n):   # pop time of part i of n
    return CAP_POP0 + 1.2 * i / n
def drum_angle(t):   # clockwise to wind the rope in; rope speed = 2 x rock speed (pulley)
    return -2.0 * cap_dist(t) / (R_DRUM + 0.025)
PSI0 = -pi / 2 + 0.25

# ------------------------------------------------------------------ the engineer's acting
EVENTS = []
def ev(t, name, gain=1.0, rate=1.0): EVENTS.append(dict(t=round(t, 3), s=name, g=gain, r=rate))
_walk = dict(phase=0.0, last=None)
def eng_state(t):
    """returns (x, y, yaw, pose, grounded, rz, pitch)"""
    g_ = True; rz = 0.0; pitch = 0.0
    if t < B['push'] - 0.45:                                    # A: sizing up the rock
        x, y, yaw = -0.6, -2.95, pi / 2 + 0.25
        P = idle(t)
        P['head_p'] = -0.55 * ss(t, B['job'] - 0.4, B['job'] + 0.2)
        P['head_y'] = -0.25 * ss(t, B['job'], B['job'] + 0.6)
        if t > B['crane'] - 0.2:
            P.update(abL=0.5, abR=0.5, elL=1.2, elR=1.2, shL=0.3, shR=0.3)
    elif t < B['rope']:                                          # B/C: run in and push
        hx = ROCK_REAR_09 - 0.95
        x0 = hx - 1.7
        u = ss(t, B['push'] - 0.45, B['push'] - 0.05)
        x, y, yaw = lerp(x0, hx, u), -0.3, 0.0
        ph = (t - (B['push'] - 0.45)) * 2 * pi * 2.6
        if u < 1:
            P = walk(ph, 1.0); P['lean'] = 0.3
        else:
            P = walk(ph * 1.15, 0.8, 0.0)
            P.update(lean=0.78, pp=0.25, shL=pi / 2 + 1.03 - 0.05, shR=pi / 2 + 1.03 + 0.05, elL=0.1, elR=0.1, abL=0.05, abR=0.05,
                     squint=0.85, mouth=0.25, head_p=-0.6, brow=0.35)
            P['hipL'] -= 0.35; P['hipR'] -= 0.35
            P['head_r'] = 0.04 * nz(t, 1, 9)
    elif t < T_SNAP:                                             # D/E: rope pull
        u = ss(t, B['rope'] + 0.1, B['rope'] + 1.4)
        x, y, yaw = lerp(4.3, 7.0, u), lerp(-0.9, 0.0, u), pi
        if u < 1:
            P = walk(-(t - B['rope']) * 2 * pi * 1.8, 0.9); P['lean'] = -0.1
            P.update(shL=0.9, shR=0.9, elL=0.6, elR=0.6)
        else:
            tr = ss(t, B['rope'] + 1.4, T_SNAP) * 0.06
            P = dict(lean=-0.42, pp=-0.12, shL=pi / 2 - 0.42 - 0.12 - 0.25, shR=pi / 2 - 0.54 - 0.15, elL=0.35, elR=0.35, abL=0.1, abR=0.1,
                     hipL=0.55, knL=0.75, hipR=-0.25, knR=0.1, squint=0.8, mouth=0.35, brow=0.3, head_p=0.1)
            P['lean'] += tr * nz(t, 3, 14); P['head_r'] = tr * nz(t, 4, 17)
    elif t < B['lever'] - 0.02:                                  # F: snap, fly back, sit dazed
        u = clamp((t - T_SNAP) / 0.36)
        x = lerp(7.0, 8.75, eo(u)); y = 0.0; yaw = pi
        rz = 0.55 * sin(pi * u) if u < 1 else 0.0
        fall = dict(lean=-0.5, pp=-0.6, shL=1.6, shR=1.9, elL=0.3, elR=0.2, abL=0.6, abR=0.6, hipL=1.5, knL=0.4, hipR=1.2, knR=0.6, wide=1.0, mouth=0.9)
        sit = dict(lean=-0.15, pp=-0.35, shL=-0.4, shR=-0.4, elL=0.2, elR=0.2, abL=0.3, abR=0.3, hipL=1.45, knL=0.5, hipR=1.3, knR=0.7,
                   squint=0.3, mouth=0.3, head_r=0.15 * sin(t * 6), head_y=0.2 * sin(t * 4))
        P = blend(fall, sit, ss(t, T_SNAP + 0.3, T_SNAP + 0.5))
        g_ = False
        P['bob'] = lerp(0.0, -0.47, ss(t, T_SNAP + 0.2, T_SNAP + 0.36))
    elif t < B['light'] - 0.6:                                   # G: walk to the long end of the lever
        u = ss(t, B['lever'] + 0.0, B['lever'] + 1.3)
        x, y = lerp(-7.3, -9.15, u), lerp(-1.6, -0.75, u)
        yaw = lerp(2.71, 0.25, ss(t, B['lever'] + 1.2, B['lever'] + 1.7))
        P = walk((t - B['lever']) * 2 * pi * 1.7, 1.0 - ss(t, B['lever'] + 1.1, B['lever'] + 1.4)) if u < 1 else idle(t)
        if t > B['long'] - 0.2:
            P.update(shR=1.4 * ss(t, B['long'] - 0.2, B['long'] + 0.2), elR=0.1, abR=0.2)
    elif t < BAG_T[0] - 0.1:                                     # H: jump and hang from the lever
        hang = lever_point(t, LONG - 1.0)
        u = ss(t, B['light'] - 0.6, B['light'] - 0.25)
        x, y = lerp(-9.15, hang.x, u), lerp(-0.75, 0.0, u)
        yaw = 0.0
        rz_h = hang.z - 1.02 - Engineer.HIP
        rz = rz_h * eo(clamp((t - (B['light'] - 0.45)) / 0.25)) + 0.15 * sin(pi * clamp((t - (B['light'] - 0.45)) / 0.25))
        sw = sin((t - B['light']) * 5.0) * 0.25
        hangp = dict(shL=pi - 0.05, shR=pi - 0.05, elL=0.1, elR=0.1, abL=0.12, abR=0.12, hipL=0.2 + sw, hipR=0.2 - sw, knL=0.5 + sw, knR=0.5 - sw,
                     head_p=-0.3, mouth=0.15, brow=0.25)
        P = blend(idle(t), hangp, ss(t, B['light'] - 0.6, B['light'] - 0.4))
        g_ = rz < 0.02
    else:                                                        # I: drop, step aside, watch the bags
        hang = lever_point(t, LONG - 1.0)
        u = clamp((t - (BAG_T[0] - 0.1)) / 0.25)
        rz_h = hang.z - 1.02 - Engineer.HIP
        rz = rz_h * (1 - u * u)
        w = ss(t, BAG_T[0] + 0.2, BAG_T[0] + 0.9)
        x, y = lerp(hang.x, -9.0, w), lerp(0.0, -1.45, w)
        yaw = lerp(0.0, pi / 2 + 0.6, ss(t, BAG_T[0] + 0.6, BAG_T[0] + 1.1))
        P = walk((t - BAG_T[0]) * 2 * pi * 1.8, 1.0) if 0 < w < 1 else idle(t)
        if u < 1: P = blend(dict(shL=pi - 0.05, shR=pi - 0.05, hipL=0.2, hipR=0.2, knL=0.5, knR=0.5), P, u)
        if t > T_LEVER + 0.3:
            c = ss(t, T_LEVER + 0.3, T_LEVER + 0.6)
            P.update(shL=lerp(P['shL'], 2.7, c), shR=lerp(P['shR'], 2.7, c), elL=0.3, elR=0.3, abL=0.4, abR=0.4, wide=c, mouth=0.6 * c)
        g_ = rz < 0.02
    if t >= B['rollers']:                                        # J: push rollers in under the cribbed rock
        k = clamp(int((t - (B['rollers'] + 0.08)) / 0.5), 0, 4); lt = (t - (B['rollers'] + 0.08)) - 0.5 * k
        rx_ = UNDER[k]
        if t < B['rollers'] + 2.6:
            if lt < 0.36:
                u = clamp(lt / 0.36); x, y = rx_ - 0.25, lerp(-5.85, -2.25, u); yaw = pi / 2
                P = walk(t * 2 * pi * 2.6, 0.9); P.update(lean=0.55, shL=pi / 2 + 0.5, shR=pi / 2 + 0.5, elL=0.2, elR=0.2, squint=0.5)
            else:
                u = clamp((lt - 0.36) / 0.14); nx = UNDER[min(k + 1, 4)]
                x, y = lerp(rx_ - 0.25, nx - 0.25, u), lerp(-2.25, -5.85, u); yaw = pi / 2
                P = walk(t * 2 * pi * 3, 0.9)
        elif t < B['drag'] + 2.0:
            u = ss(t, B['rollers'] + 2.6, B['rollers'] + 3.3)
            x, y = lerp(UNDER[4] - 0.25, 3.3, u), lerp(-2.25, -2.6, u)
            yaw = lerp(pi / 2, pi / 2 + 0.4, u)
            P = walk(t * 2 * pi * 1.8, 1.0) if 0 < u < 1 else idle(t)
            if t > B['drag'] - 0.3:
                P.update(shR=2.2 * ss(t, B['drag'] - 0.3, B['drag']), elR=1.2, abR=0.2)   # points at the rollers
        elif t < B['pry'] - 0.05:                                # K: walk round to the back
            u = ss(t, B['drag'] + 2.0, B['pry'] - 0.4)
            pts = [(3.3, -2.6), (-0.5, -2.1), (-3.4, -1.6), (-3.85, -0.1)]
            seg = u * 3; i = min(int(seg), 2); f = seg - i
            x, y = lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)
            dx, dy = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
            yaw = atan2(dy, dx) if u < 1 else 0.0
            P = walk(t * 2 * pi * 1.7, 1.0) if 0 < u < 1 else idle(t)
        elif t < B['capstan'] - 0.02:                            # L: pry-bar heaves, then the deadpan look
            x, y, yaw = -3.85 + rock_x(t) - 0.0, -0.1, 0.0
            hv = sum(sin(pi * clamp((t - th) / 0.5)) for th in PRY_T)
            P = dict(IDLE); P.update(lean=0.35 + 0.35 * hv, pp=0.1, shL=1.05 + 0.25 * hv, shR=1.05 + 0.25 * hv, elL=0.5 - 0.3 * hv, elR=0.5 - 0.3 * hv,
                                     hipL=0.3, knL=0.4 + 0.2 * hv, hipR=-0.15, knR=0.15, squint=0.6 * hv, mouth=0.3 * hv)
            look = ss(t, B['week'] - 1.3, B['week'] - 0.9)
            P['head_y'] = -1.15 * look; P['head_p'] = -0.1 * look; P['brow'] = -0.25 * look
            P['blink'] = 0.45 * look
        elif t < T_ARRIVE:                                       # M/N: the capstan
            ang = drum_angle(t)
            psi = PSI0 + ang + 0.13
            x, y = CAP.x + R_PUSH * cos(psi), CAP.y + R_PUSH * sin(psi)
            yaw = atan2(-cos(psi), sin(psi))
            v = 2 * (cap_dist(t + 1 / FPS) - cap_dist(t)) * FPS * R_PUSH / (R_DRUM + 0.025)
            last = _walk['last']; dtt = (t - last) if last is not None and t > last else 0.0
            _walk['phase'] += min(v, 3.2) / 0.85 * 2 * pi * dtt; _walk['last'] = t
            amt = clamp(v / 0.6)
            P = walk(_walk['phase'], amt, 0.0)
            P.update(lean=0.15 + 0.45 * ss(t, B['arms'] - 0.6, B['arms'] - 0.1), shL=pi / 2 + 0.45, shR=pi / 2 + 0.6, elL=0.25, elR=0.25,
                     abL=0.05, abR=0.25, squint=0.4 * amt)
            P['lean'] = 0.15 + 0.45 * ss(t, B['arms'] - 0.6, B['arms'] - 0.1)
            P['shL'] = pi / 2 + P['lean'] + 0.0; P['shR'] = pi / 2 + P['lean'] + 0.1
            dr = (psi - pi) % (2 * pi)
            dr = min(dr, 2 * pi - dr)
            if dr < 0.32 and amt > 0.05:
                h = 1 - (dr / 0.32) ** 2; rz = 0.42 * h; P['knL'] += 0.9 * h; P['knR'] += 0.9 * h; P['hipL'] += 0.5 * h; P['hipR'] += 0.5 * h
                g_ = False
            P = blink(t, P)
        elif t < B['client'] - 0.6:                              # O: arrival, fist pump
            ang = drum_angle(T_ARRIVE); psi = PSI0 + ang + 0.13
            x, y = CAP.x + R_PUSH * cos(psi), CAP.y + R_PUSH * sin(psi)
            yaw = lerp(atan2(-cos(psi), sin(psi)), atan2(0 - y, X_DEST - x), ss(t, B['dest'] + 0.2, B['dest'] + 0.7))
            P = idle(t)
            c = ss(t, B['dest'] + 0.7, B['dest'] + 1.0) * (1 - ss(t, B['zero'] + 0.6, B['zero'] + 1.0))
            P.update(shR=lerp(P['shR'], 2.9, c), elR=0.3 * c + 0.25 * (1 - c), abR=0.15, mouth=0.5 * c, squint=0.3 * c)
            rz = 0.12 * c * abs(sin((t - B['dest']) * 7))
            P = blink(t, P)
        else:                                                    # P: the client's text, faint
            x, y = 10.6, -1.8; yaw = atan2(-5.6 - y, 13.4 - x)
            P = idle(t)
            ph = ss(t, B['client'] - 0.5, B['client'] + 0.1)
            P.update(shR=lerp(0.05, 0.75, ph), elR=lerp(0.25, 1.95, ph), abR=0.1, head_p=0.32 * ph)
            shock = ss(t, B['texts'] + 0.75, B['texts'] + 0.95)
            P['wide'] = shock; P['mouth'] = 0.8 * shock; P['brow'] = -0.4 * shock
            T_F = B['texts'] + 1.55
            fu = clamp((t - T_F) / 0.42)
            pitch = -(pi / 2) * fu ** 2.2
            if fu >= 1: pitch = -(pi / 2) + 0.06 * sin(pi * clamp((t - T_F - 0.42) / 0.22)) * (1 - clamp((t - T_F - 0.42) / 0.5))
            if fu > 0:
                P.update(shR=lerp(P['shR'], 0.3, fu), elR=lerp(P['elR'], 0.1, fu), abL=0.35 * fu, abR=0.35 * fu, blink=fu, head_p=lerp(P['head_p'], -0.2, fu))
            rz = 0.0
            P = blink(t, P) if fu == 0 else P
    if t < B['rollers']: P = blink(t, P)
    return x, y, yaw, P, g_, rz, pitch

# ------------------------------------------------------------------ cameras
CAM = bpy.data.objects.new('camera', bpy.data.cameras.new('camera')); link(CAM); sc.camera = CAM
CAM.data.sensor_fit = 'HORIZONTAL'; CAM.data.sensor_width = 36; CAM.data.dof.use_dof = True
CAM.data.clip_start = 0.05; CAM.data.clip_end = 600
def head_pos(): return ENG.j['head'].matrix_world @ Vector((0.05, 0, 0.2))
def eng_pos(): return ENG.j['pelvis'].matrix_world.translation.copy()
SHOTS = []   # (t0, fn(t,u) -> (loc, target, lens, fstop))
def shot(t0):
    def deco(fn): SHOTS.append((t0, fn)); return fn
    return deco
@shot(0.0)
def s_open(t, u):
    return lv((2.3, -6.0, 0.45), (1.7, -5.2, 0.5), eo(u)), lv((-0.3, -0.6, 1.9), (-0.45, -0.6, 1.95), u), 24, 8
@shot(B['crane'] - 0.25)
def s_crane(t, u):
    return lv((-2.6, -4.4, 1.55), (-2.9, -3.8, 1.65), u), lv((-6.3, 13.0, 3.0), (-6.5, 13.4, 3.1), u), 50, 11
@shot(B['push'] - 0.5)
def s_push(t, u):
    return lv((-2.3, -4.3, 1.0), (-2.5, -4.0, 1.0), u), V(-3.2, -0.3, 0.95), 28, 7
@shot(B['push'] + 0.42)
def s_zoom(t, u):
    h = head_pos(); z = eo(clamp((t - (B['push'] + 0.48)) / 0.32))
    return V(h.x - 0.4, -4.6, 1.35), lv(V(-2.5, 0, 1.1), h, z), lerp(26, 105, z), lerp(8, 3.5, z)
@shot(B['rope'] - 0.02)
def s_rope_wide(t, u):
    return lv((9.8, -6.8, 4.0), (9.3, -6.3, 3.7), u), V(4.9, -0.3, 0.7), 34, 9
@shot(B['rated'] - 0.85)
def s_ots(t, u):
    return lv((8.7, -1.05, 1.42), (8.3, -0.95, 1.4), u), V(2.4, 0, 1.4), 32, 6
@shot(B['rockw'] + 0.95)
def s_snap(t, u):
    return lv((7.6, -6.6, 3.0), (7.8, -6.3, 2.9), u), V(6.3, 0, 0.7), 30, 9
@shot(B['lever'] - 0.02)
def s_lever(t, u):
    return lv((-6.6, -9.8, 3.6), (-6.2, -9.2, 3.3), u), V(-6.3, 0, 0.7), 24, 10
@shot(B['short'] - 0.15)
def s_fulcrum(t, u):
    return lv((-3.25, -1.95, 0.6), (-3.05, -1.75, 0.55), u), V(-2.33, 0, 0.2), 40, 4
@shot(B['light'] - 0.75)
def s_hang(t, u):
    return lv((-9.0, -5.0, 1.6), (-9.1, -4.6, 1.6), u), V(-9.6, 0, 1.25), 32, 7
@shot(T_LEVER + 0.1)
def s_gap(t, u):
    return lv((-2.95, -1.35, 0.17), (-2.88, -1.25, 0.17), u), V(-2.3, 0, 0.1), 55, 4
@shot(B['rollers'] - 0.02)
def s_rollers(t, u):
    return lv((3.0, -8.6, 3.6), (2.7, -8.2, 3.4), u), V(-0.4, -2.3, 0.4), 30, 9
@shot(B['drag'] + 1.95)
def s_rollers_low(t, u):
    return lv((-4.2, -3.4, 0.36), (1.4, -3.4, 0.36), sm(u)), lv((-2.2, 0, 0.32), (3.0, 0, 0.32), sm(u)), 26, 9
@shot(B['pry'] - 0.05)
def s_pry(t, u):
    z = ss(t, B['week'] - 1.35, B['week'] - 1.0)
    h = head_pos()
    return lv((-5.5, -3.0, 1.3), (-5.3, -2.8, 1.25), u), lv(V(-3.2, -0.1, 0.8), h, z), lerp(30, 55, z), lerp(7, 4, z)
@shot(B['capstan'] - 0.02)
def s_build(t, u):
    return lv((11.6, -7.2, 3.9), (12.0, -6.6, 3.5), u), V(13.2, 0, 0.5), 34, 10
@shot(B['loop'] - 0.08)
def s_pulley(t, u):
    rx = rock_x(t); fx = rx + ROCK_FRONT_06 + 0.3
    return lv((fx + 2.7, -2.6, 1.55), (fx + 2.4, -2.3, 1.45), u), V(fx + 0.1, 0, 0.75), 32, 5
@shot(B['forty'] - 0.95)
def s_track(t, u):
    rx = rock_x(t); mid = (rx + CAP.x) / 2
    return V(mid - 0.5, -11.0, 5.5), V(mid, 0, 0.4), 22, 10
@shot(B['half'] - 1.0)
def s_rollers_track(t, u):
    rx = rock_x(t)
    return V(rx + 0.9, -3.45, 0.5), V(rx + 0.15, 0, 0.36), 30, 5
@shot(T_ARRIVE - 0.15)
def s_reveal(t, u):
    e = sm(u)
    p = Vector((X_DEST + 3.2, -4.6, 1.0)).lerp(Vector((X_DEST + 7.0, -12.5, 6.5)), e)
    p += Vector((0, 0, 4.5 * sin(pi * e) * 0.3))
    tg = Vector((X_DEST, 0, 1.4)).lerp(Vector((4.5, 0, 0.3)), e)
    return p, tg, lerp(30, 24, e), 12
@shot(B['client'] - 0.6)
def s_phone(t, u):
    return lv((12.7, -4.7, 1.4), (12.4, -4.3, 1.3), sm(u)), lv((10.55, -1.75, 1.15), (10.3, -1.5, 0.75), ss(t, B['texts'] + 1.5, B['texts'] + 2.2)), 38, 6
SHOTS.sort(key=lambda s: s[0])
CUTS[:] = [math.ceil(s[0] * FPS - 1e-6) for s in SHOTS[1:]]   # first frame that uses the new shot
CAM_PREV = [None]
def camera(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t + 1e-6)
    t0 = SHOTS[i][0]; t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else DUR
    loc, tgt, lens, fs = SHOTS[i][1](t, clamp((t - t0) / (t1 - t0)))
    loc = Vector(loc); tgt = Vector(tgt)
    sh = 0.0
    for ts, amp, d in ((T_SNAP, 0.12, 0.5), (T_LEVER + 0.75, 0.03, 0.4), (B['rolling'] - 0.6, 0.03, 0.3), (T_ARRIVE, 0.05, 0.5),
                       (B['texts'] + 2.0, 0.04, 0.35)):
        if ts <= t < ts + d: sh += amp * (1 - (t - ts) / d)
    loc += Vector((nz(t, 11, 31), nz(t, 12, 29), nz(t, 13, 33))) * sh
    loc += Vector((nz(t, 21, 0.6), 0, nz(t, 22, 0.5))) * 0.025       # handheld breathing
    q = (tgt - loc).to_track_quat('-Z', 'Y')
    e = q.to_euler()
    if CAM_PREV[0] is not None: e.make_compatible(CAM_PREV[0])
    CAM_PREV[0] = e.copy()
    LOC(CAM, loc); ROT(CAM, e)
    PROP(CAM.data, 'lens', lens); PROP(CAM.data, 'dof.focus_distance', (tgt - loc).length)
    PROP(CAM.data, 'dof.aperture_fstop', fs)

# ------------------------------------------------------------------ labels (projected later by overlay.py)
LABELS = []
def label(text, style, t0, t1, anchor=None, xy=None, color='y'):
    LABELS.append(dict(text=text, style=style, t0=t0, t1=t1, anchor=anchor, xy=xy, color=color, pts={}))
rock_top = lambda t: ROCK.matrix_world @ Vector((0, 0, 4.9 + 1.75 * 0 + 0.0))
label('100 t', 'tag', B['this'] + 0.6, B['crane'] - 0.25, lambda t: ROCK.matrix_world @ Vector((0, 0, 5.0)), color='r')
label('≈ 50 kg push', 'tag', B['push'] + 0.15, B['push'] + 0.42, lambda t: ENG.j['handL'].matrix_world.translation + Vector((0, 0, 0.45)), color='b')
label('≈ 50 kg push', 'tag', B['notice'] - 0.3, B['rope'] - 0.05, lambda t: ENG.j['handL'].matrix_world.translation + Vector((0, 0, 0.35)), color='b')
label('ROPE MAX 2 t', 'tag', B['rated'] - 0.1, B['rockw'] - 0.1, lambda t: Vector(CU_P1.splines[0].points[5].co[:3]) + Vector((0, 0, 0.35)), color='y')
label('ROCK 100 t', 'tag', B['rockw'] - 0.1, B['rockw'] + 0.95, lambda t: ROCK.matrix_world @ Vector((0, 0, 3.3)), color='r')
label('50×', 'big', B['rockw'] + 0.35, B['rockw'] + 0.95, xy=(0.5, 0.56))
label('LONG 8 m', 'tag', B['long'] - 0.05, B['short'] - 0.15, lambda t: lever_point(t, 4.2) + Vector((0, 0, 0.55)), color='b')
label('SHORT 16 cm', 'tag', B['short'], B['light'] - 0.75, lambda t: lever_point(t, -0.08) + Vector((0, 0, 0.32)), color='o')
label('50 : 1', 'big', B['ratio'], B['light'] - 0.75, xy=(0.5, 0.62))
label('80 kg', 'tag', B['light'] - 0.3, BAG_T[0] - 0.15, lambda t: ENG.j['pelvis'].matrix_world.translation + Vector((0.6, 0, 0.0)), color='b')
for i, bt in enumerate(BAG_T):
    label(f'+{(i + 1) * 200} kg', 'tag', bt + BAG_FALL, (BAG_T[i + 1] + BAG_FALL) if i < 4 else T_LEVER + 0.1,
          lambda t: BASKET.matrix_world.translation + Vector((0, 0, 1.25)), color='b')
label('+2.6 cm', 'tag', T_LEVER + 0.45, B['rollers'] - 0.05, lambda t: ROCK.matrix_world @ Vector((-RX * 0.93, 0, 0.05)) + Vector((0, 0, 0.22)), color='r')
label('LIFT · WEDGE · REPEAT', 'tag', B['rollers'] + 0.05, B['rollers'] + 1.4, xy=(0.5, 0.68), color='y')
label('DRAG  ≈ 60 t', 'strike', B['drag'] - 0.05, B['drag'] + 1.95, xy=(0.5, 0.60), color='r')
label('ROLL  ≈ 2 t', 'tag', B['rolling'] - 0.05, B['pry'] - 0.1, xy=(0.5, 0.66), color='g')
for i, th in enumerate(PRY_T):
    label('+5 cm', 'tag', th + 0.3, th + 0.95, lambda t: ROCK.matrix_world @ Vector((-RX, 0, 2.3)), color='g')
label('ETA: 1 WEEK', 'big', B['week'] - 0.1, B['capstan'] - 0.05, xy=(0.5, 0.64))
label('ARMS 3 m', 'tag', B['arms'] - 0.05, B['twenty'] + 0.9, lambda t: CAP_ROT.matrix_world @ Vector((R_ARM * 0.7, 0, 1.45)), color='b')
label('DRUM 15 cm', 'tag', B['drum'] - 0.05, B['twenty'] + 0.9, lambda t: CAP + Vector((0, 0, 1.75)), color='o')
label('20 : 1', 'big', B['twenty'], B['loop'] - 0.1, xy=(0.5, 0.60))
label('PULLEY', 'tag', B['pulley'] - 0.05, B['forty'] - 0.95, lambda t: PULLEY.matrix_world.translation + Vector((0, 0, 0.55)), color='y')
label('×2', 'big', B['doubles'], B['forty'] - 0.95, xy=(0.5, 0.62))
label('20 × 2 = 40×', 'big', B['forty'] - 0.4, B['half'] - 1.05, xy=(0.5, 0.60))
label('REAL SPEED: 3.5 cm/s', 'tag', B['forty'] - 0.85, B['forty'] + 0.7, xy=(0.5, 0.70), color='g')
label('TIME-LAPSE', 'badge', B['forty'] + 0.75, T_ARRIVE - 0.3, xy=(0.12, 0.2))
label('ROCK  v', 'tag', B['half'] - 0.8, T_ARRIVE - 0.2, lambda t: V_ARROW.matrix_world.translation + Vector((0.7, -0.05, 0.35)), color='y')
label('ROLLERS  ½ v', 'tag', B['half'] - 0.1, T_ARRIVE - 0.2, lambda t: HALF_ARROW.matrix_world.translation + Vector((0.35, 0, -0.3)), color='g')
label('LEVER 50:1', 'tag', B['dest'] + 0.5, B['client'] - 0.65, lambda t: lever_point(t, 5.0) + Vector((0, 0, 0.6)), color='b')
label('ROLLERS', 'tag', B['dest'] + 0.8, B['client'] - 0.65, lambda t: Vector((0.9, 0, 0.6)), color='g')
label('PULLEY ×2', 'tag', B['dest'] + 1.1, B['client'] - 0.65, lambda t: PULLEY.matrix_world.translation + Vector((0, 0, 1.7)), color='y')
label('CAPSTAN 20:1', 'tag', B['dest'] + 1.4, B['client'] - 0.65, lambda t: CAP + Vector((0, 0, 3.0)), color='o')
label('1 guy · 1 rock · 0 cranes', 'tag', B['guy'] - 0.1, B['client'] - 0.65, xy=(0.5, 0.74), color='y')
label('TEXT', 'text', B['texts'] - 0.05, DUR, xy=(0.5, 0.355))

# ------------------------------------------------------------------ dust puffs
PUFFS = []  # (t0, pos, size)
def puff(t0, pos, size=1.0): PUFFS.append((t0, Vector(pos), size))
def dust_state(t):
    k = 0
    for t0, pos, size in PUFFS:
        u = (t - t0) / 0.9
        for j in range(6):
            o = DUSTS[(k + j) % len(DUSTS)]
            if 0 <= u <= 1 and k + j < len(DUSTS):
                a = j / 6 * 2 * pi + t0
                LOC(o, pos + Vector((cos(a), sin(a), 0.2 + 0.4 * u)) * size * (0.3 + 0.9 * eo(u)))
                SCL(o, size * (0.4 + 0.9 * eo(u)) * (1 - u) ** 0.7); VIS(o, True)
        k += 6
    # hide unused
_dust_used = {}
def dust_all(t):
    active = []
    for t0, pos, size in PUFFS:
        if t0 <= t <= t0 + 0.9: active.append((t0, pos, size))
    for i, o in enumerate(DUSTS):
        slot = i // 6; j = i % 6
        if slot < len(active):
            t0, pos, size = active[slot]; u = (t - t0) / 0.9; a = j / 6 * 2 * pi + t0 * 3
            LOC(o, pos + Vector((cos(a) * (0.3 + 0.9 * eo(u)) * size, sin(a) * (0.3 + 0.9 * eo(u)) * size * 0.6, 0.12 + 0.35 * u * size)))
            SCL(o, max(0.001, size * (0.5 + 0.8 * eo(u)) * (1 - u) ** 0.8)); VIS(o, True)
        else:
            SCL(o, 0.001); VIS(o, False)

# ------------------------------------------------------------------ world state for time t
def state(t):
    # rock
    rp, ra = rock_pose(t)
    LOC(ROCK, rp); ROT(ROCK, (0, ra, 0))
    VIS(W_ARROW, B['this'] + 0.5 <= t < B['crane'] - 0.25); SCL(W_ARROW, back((t - B['this'] - 0.5) / 0.35))
    VIS(BELT, B['rope'] + 0.05 <= t < B['lever'] - 0.02); SCL(BELT, (1, 1, 1) if t > B['rope'] + 0.4 else (1 + 2 * (1 - eo((t - B['rope']) / 0.35)),) * 3)
    VIS(SLING, t >= cap_pop(9, 12))
    VIS(PULLEY, t >= cap_pop(10, 12)); SCL(PULLEY, back((t - cap_pop(10, 12)) / 0.3))
    VIS(PULLEY_HL, B['pulley'] - 0.05 <= t < B['forty'] - 0.95); SCL(PULLEY_HL, 1 + 0.08 * sin(t * 12))
    ROT(SHEAVE, (0, 0, -cap_dist(t) / 0.19))
    VIS(V_ARROW, B['half'] - 0.8 <= t < T_ARRIVE - 0.15)
    # rollers + cribs
    on_rollers = t >= B['rollers']
    xr = rock_x(t) if on_rollers else 0.0
    for i, (o, p, under) in enumerate(ROLLERS):
        if under:
            k = i; t_in = B['rollers'] + 0.08 + 0.5 * k
            y = lerp(-3.6, 0.0, clamp((t - t_in) / 0.36))
            xi = 0.0
        else:
            k = i - len(UNDER); t_in = cap_pop(k * 0.5 + 0.2, 12)
            y = 0.0; xi = p - RX
        x_exit = 2 * p + 2 * RX - xi
        q = p + (clamp(xr, xi, max(xi, x_exit)) - xi) / 2
        z = R_ROLL + (max(0.0, 2.0 * (1 - eo((t - t_in) / 0.35))) if not under else 0.0)
        LOC(o, (q, y, z)); ROT(o, (0, (q - p) / R_ROLL, 0))
        VIS(o, t >= t_in)
    for i, c in enumerate(CRIBS):
        out = ss(t, B['rolling'] - 0.6, B['rolling'] - 0.15)
        LOC(c, (c.location.x, lerp(0, -2.9, out), lerp(0.30 - 0.3, 0.0, 0) + 0.0)); VIS(c, B['rollers'] <= t < B['rolling'] + 0.5)
        SCL(c, (1, 1, 1.03))
    # lever, basket, bags
    th = lever_theta(t)
    LOC(LEVER, PIV); ROT(LEVER, (0, th, 0)); VIS(LEVER, t >= B['lever'] - 0.02); VIS(FULC, t >= B['lever'] - 0.02)
    VIS(HL_LONG, B['long'] - 0.05 <= t < B['short'] + 0.3); VIS(HL_SHORT, B['short'] - 0.05 <= t < B['light'] - 0.75)
    SCL(HL_LONG, (1, 1 + 0.1 * sin(t * 14), 1 + 0.1 * sin(t * 14))); SCL(HL_SHORT, (1, 1 + 0.1 * sin(t * 14), 1 + 0.1 * sin(t * 14)))
    end = lever_point(t, LONG); bpos = end - Vector((0, 0, 0.95))
    bpos.z = max(bpos.z, 0.0)
    LOC(BASKET, bpos); VIS(BASKET, t >= B['lever'] - 0.02)
    for cu, s in B_ROPES:
        CO(cu, 0, end + Vector((s * 0.4, 0, 0.0))); CO(cu, 1, bpos + Vector((s * 0.45, 0, 0.3)))
    stack = [(0.0, 0.0, 0.15), (0.05, 0.18, 0.15), (-0.05, -0.2, 0.15), (0.0, 0.05, 0.4), (0.03, -0.1, 0.62)]
    for i, (o, bt) in enumerate(zip(BAGS, BAG_T)):
        tgt = bpos + Vector(stack[i])
        u = clamp((t - bt) / BAG_FALL)
        start = tgt + Vector((-0.6, -0.4, 3.2))
        p = start.lerp(tgt, u) if u < 1 else tgt
        if u < 1: p.z = start.z + (tgt.z - start.z) * u * u
        sq = 1 + 0.35 * sin(pi * clamp((t - bt - BAG_FALL) / 0.18)) if t > bt + BAG_FALL else 1
        LOC(o, p); SCL(o, (sq, sq, 1 / sq)); ROT(o, (0, 0, i * 1.3 + 2.0 * (1 - u)))
        VIS(o, t >= bt)
    pt = PRY_T
    VIS(PRY, t >= B['rollers'])
    if t < B['pry'] - 0.05:
        LOC(PRY, (-3.4, -1.3, 0.04)); ROT(PRY, (0, 0, 0.4))
    else:
        rx = rock_x(t); hv = sum(sin(pi * clamp((t - th_) / 0.5)) for th_ in pt)
        tip = Vector((-RX * 0.98 + rx, 0.0, 0.34)); hand = Vector((-3.2 + rx - 0.0, -0.05, 1.05 - 0.3 * hv))
        d = hand - tip; d.normalize()
        LOC(PRY, tip); ROT(PRY, Vector((1, 0, 0)).rotation_difference(d).to_euler())
    # capstan
    nparts = len(CAP_PARTS)
    for i, o in enumerate(CAP_PARTS):
        tp = cap_pop(i * 9 / nparts, 12)
        VIS(o, t >= tp); SCL(o, back((t - tp) / 0.28))
    ROT(CAP_ROT, (0, 0, PSI0 + drum_angle(t)))
    wound = 2 * cap_dist(t)
    SCL(COIL, (1, 1, 0.06 + 0.5 * clamp(wound / 12.0))); VIS(COIL, t >= cap_pop(9, 12))
    for h in HL_ARMS: VIS(h, B['arms'] - 0.05 <= t < B['drum'] + 0.1); SCL(h, (1, 1 + 0.12 * sin(t * 14), 1 + 0.12 * sin(t * 14)))
    VIS(HL_DRUM, B['drum'] - 0.05 <= t < B['loop'] - 0.1); SCL(HL_DRUM, 1 + 0.06 * sin(t * 14))
    # capstan rope lines: drum -> pulley -> anchor
    tl = cap_pop(10.5, 12); draw = eo((t - tl) / 0.5)
    pw = PULLEY.matrix_world.translation if t >= cap_pop(10, 12) else Vector((rock_x(t) + ROCK_FRONT_06 + 0.32, 0, 0.92))
    a0 = Vector((CAP.x, 0.17, DRUM_Z)); a1 = pw + Vector((0, 0.19, 0)); b1 = pw + Vector((0, -0.19, 0))
    CO(CU_A, 0, a0); CO(CU_A, 1, a0.lerp(a1, max(draw, 0.001)))
    CO(CU_B, 0, ANCHOR); CO(CU_B, 1, ANCHOR.lerp(b1, max(draw, 0.001)))
    VIS(LINE_A, t >= tl); VIS(LINE_B, t >= tl)
    for i, ar in enumerate(T_ARROWS):
        VIS(ar, B['loop'] + 0.2 <= t < B['forty'] - 0.95)
        base = (a1 if i == 0 else b1)
        sl = (t * 0.8 + i * 0.5) % 1.0
        LOC(ar, base + Vector((0.7 + 1.6 * sl, 0, 0.25)))
    # arrows
    VIS(PUSH_ARROW, B['push'] + 0.15 <= t < B['rope'] - 0.05)
    hp = ENG.j['handL'].matrix_world.translation
    LOC(PUSH_ARROW, (hp.x - 0.95, -0.55, hp.z + 0.1))
    VIS(LIFT_ARROW, T_LEVER + 0.3 <= t < B['rollers'] - 0.05)
    LOC(LIFT_ARROW, ROCK.matrix_world @ Vector((-RX - 0.15, -0.35, 0.05))); SCL(LIFT_ARROW, back((t - T_LEVER - 0.3) / 0.3))
    VIS(LOAD_ARROW, BAG_T[-1] + BAG_FALL <= t < T_LEVER + 0.1)
    LOC(LOAD_ARROW, end + Vector((0, -0.45, 1.6)))
    VIS(HALF_ARROW, B['half'] - 0.1 <= t < T_ARRIVE - 0.15)
    xh = rock_x(B['half'] - 0.1)
    LOC(HALF_ARROW, (xh + 0.9 + (rock_x(t) - xh) / 2, -1.85, 0.18))
    # snap flash
    fu = (t - T_SNAP) / 0.18
    VIS(FLASH, 0 <= fu <= 1); SCL(FLASH, 0.3 + 1.6 * eo(fu)); LOC(FLASH, Vector(CU_P1.splines[0].points[9].co[:3]))
    VIS(COILPILE, B['rope'] - 0.02 <= t < B['lever'] - 0.02)
    dust_all(t)
    # engineer
    x, y, yaw, P, g_, rz, pitch = eng_state(t)
    ENG.apply(t, x, y, yaw, P, g_, rz, pitch)
    VIS(ENG.phone, t >= B['client'] - 0.6)
    for k, s in enumerate(ENG.stars):
        on = T_SNAP + 0.4 <= t < B['lever'] - 0.02
        a = t * 7 + k * 2 * pi / 3
        LOC(s, (0.32 * cos(a), 0.32 * sin(a), 0.55 + 0.04 * sin(t * 9 + k))); ROT(s, (0, 0, a + pi / 2)); VIS(s, on)
    for k, d in enumerate(ENG.drops):
        ph = ((t - B['notice']) * 1.4 + k * 0.5) % 1.0
        on = B['notice'] - 0.5 <= t < B['rope'] - 0.05
        LOC(d, (0.0 - 0.25 * ph, (0.24 if k == 0 else -0.24) * (1 + ph), 0.38 + 0.25 * sin(pi * ph) - 0.3 * ph * ph)); VIS(d, on)

def rope_state(t):
    """pull rope: from the belt to the engineer's hands; it parts at T_SNAP."""
    a = ROCK.matrix_world @ Vector((ROCK_FRONT_11 + 0.03, 0, 1.1))
    hL = ENG.j['handL'].matrix_world.translation; hR = ENG.j['handR'].matrix_world.translation
    h = (hL + hR) / 2
    on = B['rope'] + 0.05 <= t < B['lever'] - 0.02
    VIS(PULL1, on); VIS(PULL2, on)
    taut = ss(t, B['rope'] + 1.2, B['rope'] + 1.6)
    PROP(M['rope_pull'].node_tree, ROPE_EMIT_PATH, 2.5 * ss(t, B['rated'], T_SNAP) ** 1.5 if t < T_SNAP else 0.0)
    if t < T_SNAP:
        m = (a + h) / 2
        sag = 0.45 * (1 - taut) + 0.03
        pts = []
        for i in range(19):
            s = i / 18; p = a.lerp(h, s); p.z -= sag * 4 * s * (1 - s)
            if t > B['rated']: p += Vector((0, 0, 0.006 * sin(t * 60 + s * 9))) * ss(t, B['rated'], T_SNAP)
            pts.append(p)
        for i in range(10): CO(CU_P1, i, pts[i]); CO(CU_P2, i, pts[9 + i])
    else:
        u = clamp((t - T_SNAP) / 0.5)
        m0 = (a + Vector((4.6, 0, 1.0))) / 2 if False else None
        for i in range(10):
            s = i / 9
            reach = 1.0 - 0.5 * eo(u)
            p = a + (Vector((ROCK_FRONT_11 + 2.3, 0, 1.0)) + ROCK.matrix_world.translation - a) * s * reach
            p.z = lerp(p.z, 0.05 + 1.05 * (1 - s) ** 2, eo(clamp((t - T_SNAP - 0.1) / 0.5))) + 0.15 * sin(s * 7 + t * 20) * (1 - u) * s
            CO(CU_P1, i, p)
            q = h + (Vector((4.7, 0, 1.0)) - h) * (1 - s) * (1 - 0.65 * eo(u))
            q.z = lerp(q.z, 0.05 + max(0.0, h.z - 0.05) * s ** 2, eo(clamp((t - T_SNAP - 0.15) / 0.5))) + 0.12 * sin(s * 6 - t * 22) * (1 - u) * (1 - s)
            CO(CU_P2, i, q)

# ------------------------------------------------------------------ sound cues + dust from the timeline
ev(B['this'] + 0.5, 'whoosh_low', 0.5)
ev(B['crane'] - 0.25, 'whoosh', 0.5); ev(B['crane'] + 0.1, 'sad_horn', 0.5)
ev(B['push'] - 0.5, 'whoosh', 0.4); ev(B['push'] - 0.05, 'impactSoft_heavy_000', 0.7)
ev(B['push'] + 0.1, 'scrape_loop:2.6', 0.45)
ev(B['push'] + 0.45, 'zoom', 0.8)
ev(B['rope'] - 0.02, 'whoosh', 0.4); ev(B['rope'] + 0.1, 'rope_tie', 0.6)
ev(B['rope'] + 1.5, 'creak_loop:' + str(round(T_SNAP - B['rope'] - 1.5, 2)), 0.65)
ev(T_SNAP, 'snap', 1.0); ev(T_SNAP + 0.38, 'impactSoft_heavy_002', 0.9); ev(T_SNAP + 0.45, 'tweety', 0.45)
puff(T_SNAP + 0.38, (8.75, 0, 0.0), 0.6)
ev(B['lever'] - 0.02, 'whoosh', 0.4); ev(B['lever'] + 0.15, 'impactWood_heavy_001', 0.5)
ev(B['long'], 'ding_low', 0.35); ev(B['short'], 'ding_high', 0.35); ev(B['ratio'], 'pop', 0.6)
ev(B['light'] - 0.45, 'impactWood_medium_002', 0.7); ev(B['light'] - 0.2, 'creak_short', 0.5)
for i, bt in enumerate(BAG_T):
    ev(bt + BAG_FALL, f'impactSoft_heavy_00{i % 5}', 0.85); puff(bt + BAG_FALL, (lever_point(bt + BAG_FALL, LONG).x, 0, 0.3), 0.35)
ev(T_LEVER, 'creak_short', 0.8); ev(T_LEVER + 0.1, 'rumble:1.0', 0.8); ev(T_LEVER + 0.7, 'impactMining_001', 0.5)
puff(T_LEVER + 0.72, (lever_point(T_LEVER + 1, LONG).x, 0, 0.0), 0.5)
ev(B['rollers'] - 0.02, 'whoosh', 0.45)
for k in range(5): ev(B['rollers'] + 0.08 + 0.5 * k + 0.05, 'roll_in', 0.55); ev(B['rollers'] + 0.08 + 0.5 * k + 0.36, f'impactWood_medium_00{k % 5}', 0.55)
ev(B['rolling'] - 0.6, 'impactMining_000', 0.75); puff(B['rolling'] - 0.6, (0, -1.7, 0), 0.8)
ev(B['rolling'] - 0.4, 'scrape_loop:0.5', 0.4)
ev(B['drag'], 'buzzer', 0.4); ev(B['rolling'], 'ding_high', 0.4)
ev(B['drag'] + 1.95, 'whoosh', 0.35); ev(B['pry'] - 0.05, 'whoosh', 0.35)
for th in PRY_T: ev(th + 0.05, f'impactMetal_medium_00{int(th) % 5}', 0.6); ev(th + 0.15, 'rumble:0.35', 0.5)
ev(B['week'] - 1.3, 'record_scratch', 0.35)
ev(B['capstan'] - 0.02, 'whoosh', 0.45)
for i in range(12): ev(cap_pop(i, 12) + 0.05, f'impactPlank_medium_00{i % 5}', 0.5, 0.9 + 0.03 * i)
ev(B['arms'], 'ding_low', 0.35); ev(B['drum'], 'ding_high', 0.35); ev(B['twenty'], 'pop', 0.6)
ev(B['loop'] - 0.08, 'whoosh', 0.4); ev(B['doubles'], 'pop', 0.6); ev(B['forty'] - 0.95, 'whoosh', 0.4); ev(B['forty'] - 0.4, 'pop', 0.7)
ev(T_CAP_GO + 0.25, 'capstan:' + str(round(T_ARRIVE - T_CAP_GO - 0.25, 2)), 0.7)
ev(B['forty'] + 0.75, 'speedup', 0.6)
ev(B['half'] - 1.0, 'whoosh', 0.35)
ev(T_ARRIVE - 0.15, 'whoosh_low', 0.5); ev(T_ARRIVE, 'impactMining_002', 0.9); ev(T_ARRIVE + 0.3, 'confirmation_002', 0.6)
puff(T_ARRIVE, (X_DEST + RX, 0, 0), 0.9); puff(T_ARRIVE + 0.05, (X_DEST - RX, -1.2, 0), 0.7)
for k in range(4): ev(B['dest'] + 0.5 + 0.3 * k, 'pop', 0.35)
ev(B['client'] - 0.6, 'whoosh', 0.35); ev(B['client'] - 0.2, 'buzz', 0.8); ev(B['texts'] - 0.05, 'msg', 0.8)
ev(B['texts'] + 1.55 + 0.42, 'impactSoft_heavy_004', 1.0); ev(B['texts'] + 1.62, 'whomp', 0.6)
puff(B['texts'] + 1.97, (10.0, -1.4, 0), 0.8)

# ------------------------------------------------------------------ bake
def bake():
    t0 = time.time()
    lab_cam = []
    for f in range(NF):
        FR[0] = f; t = f / FPS
        state(t)
        bpy.context.view_layer.update()
        rope_state(t)
        camera(t)
        bpy.context.view_layer.update()
        for lb in LABELS:
            if lb['t0'] <= t < lb['t1']:
                if lb['anchor']:
                    p = world_to_camera_view(sc, CAM, lb['anchor'](t))
                    if p.z > 0: lb['pts'][f] = (round(p.x, 4), round(1 - p.y, 4))
                else:
                    lb['pts'][f] = lb['xy']
    print(f'state loop {time.time() - t0:.1f}s')
    write_fcurves()
bake()
json.dump(dict(fps=FPS, nf=NF, w=sc.render.resolution_x, h=sc.render.resolution_y, cuts=CUTS,
               labels=[dict(text=l['text'], style=l['style'], color=l['color'], t0=l['t0'], t1=l['t1'], pts=l['pts']) for l in LABELS]),
          open(os.path.join(OUT, 'labels.json'), 'w'))
json.dump(dict(events=sorted(EVENTS, key=lambda e: e['t']), beats=B, dur=DUR), open(os.path.join(OUT, 'events.json'), 'w'), indent=1)

if arg('--save'):
    try: bpy.ops.file.pack_all()
    except Exception as e: print('pack', e)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg('--save')), compress=True)
    print('saved', arg('--save'))

if arg('--stills'):
    for ts in arg('--stills').split(','):
        f = int(round(float(ts) * FPS)); sc.frame_set(f)
        sc.render.filepath = os.path.join(OUT, f'still_{float(ts):06.2f}.png')
        bpy.ops.render.render(write_still=True)
    print('STILLS_DONE')
if arg('--framelist'):
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    for f in sorted(set(int(x) for x in arg('--framelist').split(','))):
        sc.frame_set(f); sc.render.filepath = os.path.join(OUT, 'frames', f'f_{f:05d}.png')
        bpy.ops.render.render(write_still=True)
    print('FRAMELIST_DONE')
if arg('--frames'):
    a, b = (int(x) for x in arg('--frames').split(':'))
    sc.frame_start, sc.frame_end = a, b
    sc.render.filepath = os.path.join(OUT, 'frames', 'f_#####')
    t0 = time.time(); bpy.ops.render.render(animation=True)
    print(f'FRAMES_DONE {a}:{b} in {time.time() - t0:.0f}s')
