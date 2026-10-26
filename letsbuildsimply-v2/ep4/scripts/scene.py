"""scene.py: "Can Square Wheels Give You a Smooth Ride?" (Blender 5.2, Cycles, 9:16 @ 30 fps).

A quiet miniature test gallery: dark green wall, walnut plinth, maple tracks. An amber inspection cart with four
square aluminium wheels (10 cm sides) carries a porcelain cup of tea. Lanes, all on one long plinth:
  M  matched road at x ~ 0   (inverted catenary arcs, sqgeom.py)        hook, contact close-up, wide, loop
  F  flat road    at x = XF                                             flat-road control + freeze detail
  R  reveal lane  at x = XR  (flat plank sinks, arcs rise, ghost wheel) orthographic profile
  G  two-shelf stand at x = XG (flat road on top, matched road below)   same motor input, side by side
Wheel pose comes from the exact contact solution (no physics sim): axle x/z and wheel angle are baked per frame,
the cart pose follows from the axles, the tea is a damped standing-wave + slosh model driven by the cart's motion.

  blender -b -P scene.py -- --words narration.words.json --out OUT [--res 480] [--samples 32]
          [--stills 1.0,20.5] [--frames A:B] [--save project.blend]
Writes OUT/labels.json (labels + per-frame overlay geometry) and OUT/events.json (sound cues + control curves).
"""
import bpy, bmesh, math, json, sys, os, random, time
from math import sin, cos, pi, atan2, sqrt, radians, sinh, cosh, atan, tan, asinh, floor, exp
from mathutils import Vector, Matrix, Euler, noise
from bpy_extras import anim_utils
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqgeom as G

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
OUT = os.path.abspath(arg('--out', 'out')); os.makedirs(OUT, exist_ok=True)
FPS = 30
RES = int(arg('--res', '480')); SAMPLES = int(arg('--samples', '32'))
random.seed(4)


# ================================================================== narration beats
WORDS = json.load(open(arg('--words')))
def _n(s): return ''.join(c for c in s.lower() if c.isalnum() or c == "'")
def W(word, n=1, end=False):
    k = 0
    for x in WORDS:
        if _n(x['w']) == _n(word):
            k += 1
            if k == n: return x['e'] if end else x['s']
    raise KeyError(word)
B = dict(bumpy_e=W('bumpy', end=True), on=W('on'), climbs=W('climbs'), as1=W('as'), now=W('now'), change=W('change'),
         these2=W('these', 2), shaped=W('shaped'), keeping=W('keeping'), same=W('same'), rolls_e=W('rolls', end=True),
         smoothing=W('smoothing'), real=W('real'), idea_e=W('idea', end=True), called=W('called'), catenary=W('catenary'),
         it2=W('it', 2), energy=W('energy'), wheel2=W('wheel', 2), road4_e=W('road', 4, end=True), surprise=W('surprise'),
         machine_e=W('machine', end=True))
T_RW0 = B['bumpy_e'] + 0.04                 # hook ends -> rewind
T_B = B['on'] - 0.06                        # flat-road control
T_C = B['as1'] - 0.10                       # 85 mm freeze detail
T_D = B['now'] - 0.04                       # orthographic reveal
T_E = B['keeping'] - 0.10                   # contact close-up
T_F1 = B['rolls_e'] + 0.22                  # clean wide release
T_F2 = B['real'] - 0.12                     # low 3/4 tracking on the tea
T_F3 = B['idea_e'] + 0.12                   # high front-right tracking: the road shape from above
T_G = B['it2'] - 0.25                       # two-shelf comparison
T_H = B['surprise'] - 0.42                  # loop shot
DUR = round(B['machine_e'] + 1.3, 2); NF = int(round(DUR * FPS)); DUR = NF / FPS
print('beats', {k: round(v, 2) for k, v in B.items()}, 'DUR', DUR)

# ------------------------------------------------------------------ small math
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def sm(x): x = clamp(x); return x * x * (3 - 2 * x)
def ss(t, a, b): return sm((t - a) / (b - a)) if b > a else float(t >= a)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def ei(x): x = clamp(x); return x ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, u): return a + (b - a) * u
def V(*a): return Vector(a if len(a) == 3 else a[0])
def lv(a, b, u): return Vector(a).lerp(Vector(b), u)
def nz(t, seed, f=1.0): return noise.noise(Vector((t * f, seed * 7.31, 0.37)))

# ------------------------------------------------------------------ geometry (metres)
A_ = 0.05                       # wheel apothem: 10 cm square wheels
PA = G.P * A_                   # one catenary arc (0.0881 m)
HB = 1.5 * PA                   # half wheelbase: axles 3 arcs apart, so both wheels are always in the same phase
GY = 0.082                      # wheel mid-plane |y|
WT = 0.014                      # wheel plate thickness
TWD = 0.012                     # rail width (narrower than the wheel, so the wheel overhangs it)
OM = (pi / 2) / 0.70            # motor: one quarter turn every 0.70 s
VM = PA / 0.70                  # mean speed on the matched road
XF, XR, XG = 6.0, 10.0, 14.0    # lanes: flat, reveal, shelf stand
ZS = 0.30                       # top-shelf track height
HUB_Y = -GY - WT / 2 - 0.006    # outer face of the near hub cap
def road_z(x, xo=0.0, z0=0.0): return z0 + A_ * (1 + G.road_y((x - xo) / A_))
def matched(phi, xo=0.0, z0=0.0):
    c, _, kx, ky = G.matched_from_phi(phi)
    return xo + A_ * c, z0 + A_, (xo + A_ * kx, z0 + A_ * (1 + ky))
def flat(phi, x0, z0=0.0):
    cx, cy, px, _ = G.flat_from_phi(phi)
    return x0 + A_ * cx, z0 + A_ * (1 + cy), (x0 + A_ * px, z0)
def ramp(s, tau=0.45):          # motor spin-up from rest: angle travelled / OM
    if s <= 0: return 0.0
    return s * s / (2 * tau) if s < tau else s - tau / 2

# ------------------------------------------------------------------ scene reset + Cycles
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.render.fps = FPS; sc.frame_start = 0; sc.frame_end = NF - 1
sc.render.resolution_x, sc.render.resolution_y = RES, int(round(RES * 16 / 9 / 2)) * 2
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
cy_ = sc.cycles
cy_.device = 'GPU'; cy_.samples = SAMPLES; cy_.use_adaptive_sampling = True; cy_.adaptive_threshold = 0.02
cy_.use_denoising = True
for k, v in dict(denoiser='OPENIMAGEDENOISE', denoising_use_gpu=True, max_bounces=8, diffuse_bounces=3, glossy_bounces=4,
                 transmission_bounces=6, transparent_max_bounces=8, caustics_reflective=False, caustics_refractive=False,
                 blur_glossy=1.0, sample_clamp_indirect=6.0, use_light_tree=True).items():
    try: setattr(cy_, k, v)
    except Exception as e: print('cycles', k, e)
try:
    pr = bpy.context.preferences.addons['cycles'].preferences
    for dt in ('OPTIX', 'CUDA', 'HIP'):
        try:
            pr.compute_device_type = dt; pr.get_devices(); devs = [d for d in pr.devices if d.type == dt]
            if devs:
                for d in pr.devices: d.use = d.type == dt
                print('GPU', dt, [d.name for d in devs]); break
        except Exception as e: print('gpu', dt, e)
except Exception as e: print('prefs', e); cy_.device = 'CPU'
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
try: sc.render.motion_blur_position = 'START'          # blur samples forward only: a cut's first frame never sees the old shot
except Exception as e: print('mb', e)
try: sc.view_settings.view_transform = 'AgX'
except Exception as e: print('view', e)
for lk in ('AgX - Medium High Contrast', 'Medium High Contrast', 'None'):
    try: sc.view_settings.look = lk; break
    except Exception: pass
sc.view_settings.exposure = 0.0
sc.render.film_transparent = False
COLL = sc.collection

# ------------------------------------------------------------------ node helpers
def new_mat(name):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    return m, nt, next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
def sock(x): return x.outputs[0] if hasattr(x, 'outputs') else x
def N(nt, kind, *pos, **kw):
    n = nt.nodes.new(kind)
    for i, v in enumerate(pos):
        if v is None: continue
        setin(nt, n.inputs[i], v)
    for k, v in kw.items():
        name = next((x for x in (k, k.title(), k.capitalize()) if x in n.inputs), None)
        if name: setin(nt, n.inputs[name], v)
        else: setattr(n, k, v)
    return n
def setin(nt, s, v):
    if isinstance(v, (bpy.types.NodeSocket, bpy.types.Node)): nt.links.new(sock(v), s)
    elif isinstance(v, (tuple, list)) and len(v) == 3 and s.type == 'RGBA': s.default_value = (*v, 1)
    else: s.default_value = v
def M_(nt, op, a, b=None, c=None, clamp_=False):
    n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp_
    for i, v in enumerate((a, b, c)):
        if v is not None: setin(nt, n.inputs[i], v)
    return n.outputs[0]
def RAMP(nt, fac, stops, interp='LINEAR'):
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.interpolation = interp; el = r.color_ramp.elements
    def col(c): return (*c, 1) if isinstance(c, (tuple, list)) else (c, c, c, 1)
    el[0].position, el[0].color = stops[0][0], col(stops[0][1])
    el[1].position, el[1].color = stops[-1][0], col(stops[-1][1])
    for p, c in stops[1:-1]:
        e = el.new(p); e.color = col(c)
    setin(nt, r.inputs['Fac'], fac); return r.outputs['Color']
def MIXC(nt, fac, a, b, blend='MIX'):
    m = nt.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = blend
    setin(nt, m.inputs[0], fac); ins = [x for x in m.inputs if x.type == 'RGBA']
    setin(nt, ins[0], a); setin(nt, ins[1], b)
    return [x for x in m.outputs if x.type == 'RGBA'][0]
def SEP(nt, v):
    s = N(nt, 'ShaderNodeSeparateXYZ', v); return s.outputs[0], s.outputs[1], s.outputs[2]
def POS(nt): return nt.nodes.new('ShaderNodeNewGeometry').outputs['Position']
def OBJ(nt): return nt.nodes.new('ShaderNodeTexCoord').outputs['Object']
def NOISE(nt, vec, scale, detail=4.0, rough=0.55, w=None, dist=0.0):
    n = nt.nodes.new('ShaderNodeTexNoise')
    if w is not None: n.noise_dimensions = '4D'; setin(nt, n.inputs['W'], w)
    setin(nt, n.inputs['Vector'], vec); n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = dist
    return n.outputs['Fac']
def VORO(nt, vec, scale, feat='F1', out='Distance', rand=1.0):
    n = nt.nodes.new('ShaderNodeTexVoronoi'); n.feature = feat
    setin(nt, n.inputs['Vector'], vec); n.inputs['Scale'].default_value = scale
    try: n.inputs['Randomness'].default_value = rand
    except Exception: pass
    return n.outputs[out]
def VSCALE(nt, v, s): n = nt.nodes.new('ShaderNodeVectorMath'); n.operation = 'SCALE'; setin(nt, n.inputs[0], v); n.inputs['Scale'].default_value = s; return n.outputs[0]
def VADD(nt, v, w): n = nt.nodes.new('ShaderNodeVectorMath'); n.operation = 'ADD'; setin(nt, n.inputs[0], v); setin(nt, n.inputs[1], w); return n.outputs[0]
def BUMP(nt, h, strength, dist=0.05):
    b = N(nt, 'ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
    setin(nt, b.inputs['Height'], h); return b.outputs['Normal']
def BSDF(nt, col=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, emit_col=None, emit=None, normal=None, alpha=None, coat=0.0, spec=0.5):
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    setin(nt, b.inputs['Base Color'], col); setin(nt, b.inputs['Roughness'], rough); setin(nt, b.inputs['Metallic'], metal)
    if emit_col is not None: setin(nt, b.inputs['Emission Color'], emit_col)
    if emit is not None: setin(nt, b.inputs['Emission Strength'], emit)
    if normal is not None: setin(nt, b.inputs['Normal'], normal)
    if alpha is not None: setin(nt, b.inputs['Alpha'], alpha)
    if coat: b.inputs['Coat Weight'].default_value = coat
    b.inputs['Specular IOR Level'].default_value = spec
    return b
def OUTP(nt, o, shader): nt.links.new(sock(shader), o.inputs['Surface'])
def VALUE(nt, name, v=0.0):
    n = nt.nodes.new('ShaderNodeValue'); n.name = name; n.outputs[0].default_value = v; return n
def flat_mat(name, col, rough=0.5, metal=0.0, emit=0.0, ecol=None, coat=0.0):
    m, nt, o = new_mat(name)
    OUTP(nt, o, BSDF(nt, col, rough, metal, emit_col=ecol or col, emit=emit, coat=coat)); m.diffuse_color = (*col, 1); return m
def blend_mode(m, mode='BLENDED'):
    try: m.surface_render_method = mode
    except Exception as e: print('render method', e)

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
def NODEV(nt, name, v): PROP(nt, f'nodes["{name}"].outputs[0].default_value', v)

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

# ------------------------------------------------------------------ mesh helpers
def link(o, parent=None):
    if o.name not in COLL.objects: COLL.objects.link(o)
    if parent is not None: o.parent = parent
    return o
def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); o.empty_display_size = 0.2; o.location = loc; return link(o, parent)
def mesh_obj(name, bm, mats, loc=(0, 0, 0), parent=None, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for mm in mats: me.materials.append(mm)
    if smooth:
        try: me.shade_smooth()
        except Exception: me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me); o.location = loc; return link(o, parent)
def _new(bm, before):
    return [f for f in bm.faces if f.index == -2 or f not in before]
def add_prim(bm, fn, mtx, mi=0, **kw):
    before = set(bm.faces)
    r = fn(bm, matrix=mtx, **kw)
    for f in bm.faces:
        if f not in before: f.material_index = mi
    return r
def add_cyl(bm, r, z0, z1, mi=0, verts=32, r2=None, x=0.0, y=0.0, axis_mtx=None):
    m = Matrix.Translation((x, y, (z0 + z1) / 2))
    if axis_mtx: m = axis_mtx @ m
    add_prim(bm, bmesh.ops.create_cone, m, mi, cap_ends=True, segments=verts, radius1=r, radius2=r if r2 is None else r2, depth=z1 - z0)
def add_box(bm, size, loc, mi=0, rot=None):
    m = Matrix.Translation(loc) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*size, 1))
    add_prim(bm, bmesh.ops.create_cube, m, mi, size=1.0)
def add_torus(bm, R_, r, z, mi=0, seg=48, rs=8):
    before = set(bm.verts); ring = []
    for i in range(seg):
        a = 2 * pi * i / seg; row = []
        for j in range(rs):
            b = 2 * pi * j / rs
            row.append(bm.verts.new(((R_ + r * cos(b)) * cos(a), (R_ + r * cos(b)) * sin(a), z + r * sin(b))))
        ring.append(row)
    for i in range(seg):
        for j in range(rs):
            f = bm.faces.new((ring[i][j], ring[(i + 1) % seg][j], ring[(i + 1) % seg][(j + 1) % rs], ring[i][(j + 1) % rs]))
            f.material_index = mi

# ================================================================== MATERIALS
def VAL_MUL(nt, a, b): return M_(nt, 'MULTIPLY', a, b)
def mat_wall():
    m, nt, o = new_mat('wall_green'); co = OBJ(nt)
    n1 = NOISE(nt, VSCALE(nt, co, 1.0), 6.0, 6, 0.6); n2 = NOISE(nt, VSCALE(nt, co, 1.0), 60.0, 4, 0.5)
    col = MIXC(nt, M_(nt, 'MULTIPLY', n1, 0.6), (0.011, 0.034, 0.024), (0.018, 0.048, 0.034))
    OUTP(nt, o, BSDF(nt, col, M_(nt, 'ADD', 0.78, M_(nt, 'MULTIPLY', n2, 0.12)), normal=BUMP(nt, n2, 0.08, 0.002))); return m
def mat_wood(name, light=True, scale=1.0):
    """long-grain wood along x: stretched noise + wave rings, satin lacquer."""
    m, nt, o = new_mat(name); co = OBJ(nt); x, y, z = SEP(nt, co)
    v = N(nt, 'ShaderNodeCombineXYZ', M_(nt, 'MULTIPLY', x, 2.0 * scale), M_(nt, 'MULTIPLY', y, 60.0 * scale), M_(nt, 'MULTIPLY', z, 60.0 * scale)).outputs[0]
    wv = N(nt, 'ShaderNodeTexWave', v, scale=1.6, distortion=6.0, detail=3.0); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
    g = M_(nt, 'MULTIPLY', NOISE(nt, v, 3.0, 8, 0.6), 0.5)
    f = M_(nt, 'ADD', M_(nt, 'MULTIPLY', wv.outputs['Fac'], 0.55), g)
    if light: col = RAMP(nt, f, [(0.0, (0.50, 0.32, 0.17)), (0.6, (0.66, 0.46, 0.27)), (1.0, (0.74, 0.55, 0.34))])
    else: col = RAMP(nt, f, [(0.0, (0.035, 0.018, 0.010)), (0.6, (0.075, 0.040, 0.022)), (1.0, (0.11, 0.065, 0.035))])
    b = BSDF(nt, col, M_(nt, 'ADD', 0.30, M_(nt, 'MULTIPLY', g, 0.2)), normal=BUMP(nt, f, 0.05, 0.0005), coat=0.35)
    b.inputs['Coat Roughness'].default_value = 0.18
    OUTP(nt, o, b); return m
def mat_track():
    """maple track pieces; a dark hairline seam where the segments meet (x = (k + 0.5) PA in lane coordinates)."""
    m, nt, o = new_mat('maple_track'); co = OBJ(nt); x, y, z = SEP(nt, co)
    v = N(nt, 'ShaderNodeCombineXYZ', M_(nt, 'MULTIPLY', x, 3.0), M_(nt, 'MULTIPLY', y, 90.0), M_(nt, 'MULTIPLY', z, 70.0)).outputs[0]
    wv = N(nt, 'ShaderNodeTexWave', v, scale=1.3, distortion=5.0, detail=3.0); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'
    g = M_(nt, 'MULTIPLY', NOISE(nt, v, 2.5, 8, 0.6), 0.5)
    f = M_(nt, 'ADD', M_(nt, 'MULTIPLY', wv.outputs['Fac'], 0.45), g)
    col = RAMP(nt, f, [(0.0, (0.58, 0.40, 0.22)), (0.6, (0.72, 0.53, 0.32)), (1.0, (0.80, 0.63, 0.42))])
    attr = N(nt, 'ShaderNodeAttribute'); attr.attribute_name = 'seam'
    col = MIXC(nt, attr.outputs['Fac'], col, (0.10, 0.06, 0.03))
    b = BSDF(nt, col, 0.34, normal=BUMP(nt, f, 0.04, 0.0004), coat=0.5); b.inputs['Coat Roughness'].default_value = 0.12
    OUTP(nt, o, b); return m
def mat_anod(name, col, rough=0.38, metal=0.85):
    m, nt, o = new_mat(name); n = NOISE(nt, VSCALE(nt, OBJ(nt), 1.0), 900.0, 2, 0.5)
    OUTP(nt, o, BSDF(nt, col, M_(nt, 'ADD', rough, M_(nt, 'MULTIPLY', n, 0.08)), metal)); return m
def mat_amber():
    m, nt, o = new_mat('amber_powder'); n = NOISE(nt, VSCALE(nt, OBJ(nt), 1.0), 1400.0, 2, 0.5)
    b = BSDF(nt, (0.80, 0.33, 0.025), 0.42, normal=BUMP(nt, n, 0.12, 0.0002), coat=0.25); b.inputs['Coat Roughness'].default_value = 0.3
    OUTP(nt, o, b); return m
def mat_wheel():
    """graphite anodised aluminium plate; engraved 12.5 mm grid, red painted spoke from the hub to one corner."""
    m, nt, o = new_mat('wheel_plate'); co = OBJ(nt); x, y, z = SEP(nt, co)
    def line(c, pitch=0.0125, w=0.00025):
        fr = M_(nt, 'SUBTRACT', M_(nt, 'FRACT', M_(nt, 'ADD', M_(nt, 'DIVIDE', c, pitch), 0.5)), 0.5)
        return M_(nt, 'LESS_THAN', M_(nt, 'ABSOLUTE', fr), w / pitch)
    grid = M_(nt, 'MAXIMUM', line(x), line(z))
    d = M_(nt, 'ABSOLUTE', M_(nt, 'SUBTRACT', x, z))                       # distance from the x = z diagonal * sqrt2
    stripe = M_(nt, 'MULTIPLY', M_(nt, 'MULTIPLY', M_(nt, 'LESS_THAN', d, 0.0075), M_(nt, 'GREATER_THAN', M_(nt, 'ADD', x, z), 0.026)), M_(nt, 'LESS_THAN', M_(nt, 'ADD', x, z), 0.080))
    face = M_(nt, 'GREATER_THAN', M_(nt, 'ABSOLUTE', y), WT / 2 - 0.0004)  # only on the flat faces
    stripe = M_(nt, 'MULTIPLY', stripe, face); grid = M_(nt, 'MULTIPLY', grid, face)
    n = NOISE(nt, VSCALE(nt, co, 1.0), 700.0, 2, 0.5)
    brushed = NOISE(nt, N(nt, 'ShaderNodeCombineXYZ', M_(nt, 'MULTIPLY', x, 30.0), M_(nt, 'MULTIPLY', y, 30.0), M_(nt, 'MULTIPLY', z, 3000.0)).outputs[0], 1.0, 2, 0.5)
    col = MIXC(nt, grid, (0.58, 0.59, 0.61), (0.30, 0.305, 0.315))
    col = MIXC(nt, stripe, col, (0.78, 0.09, 0.03))
    rough = M_(nt, 'ADD', 0.24, M_(nt, 'MULTIPLY', brushed, 0.16))
    metal = M_(nt, 'SUBTRACT', 1.0, stripe)
    rough = M_(nt, 'ADD', M_(nt, 'MULTIPLY', rough, metal), M_(nt, 'MULTIPLY', stripe, 0.45))
    b = BSDF(nt, col, rough, metal,
             normal=BUMP(nt, M_(nt, 'ADD', M_(nt, 'MULTIPLY', grid, -1.0), M_(nt, 'MULTIPLY', n, 0.15)), 0.35, 0.0003))
    OUTP(nt, o, b); return m
def mat_porcelain():
    m, nt, o = new_mat('porcelain')
    b = BSDF(nt, (0.86, 0.85, 0.81), 0.10, coat=0.6); b.inputs['Coat Roughness'].default_value = 0.04
    b.inputs['Subsurface Weight'].default_value = 0.15; b.inputs['Subsurface Radius'].default_value = (0.002, 0.0015, 0.001)
    OUTP(nt, o, b); return m
def mat_tea():
    """glossy tea surface; the standing ripple and the fine vibration are bump-only (driven by keyed value nodes)."""
    m, nt, o = new_mat('tea'); co = OBJ(nt); x, y, z = SEP(nt, co)
    r = M_(nt, 'SQRT', M_(nt, 'ADD', M_(nt, 'MULTIPLY', x, x), M_(nt, 'MULTIPLY', y, y)))
    rip = VALUE(nt, 'RIP', 0.0); vib = VALUE(nt, 'VIB', 0.0); tw = VALUE(nt, 'TW', 0.0)
    wave = M_(nt, 'COSINE', M_(nt, 'MULTIPLY', r, 2 * pi / 0.0105))
    edge = M_(nt, 'SUBTRACT', 1.0, M_(nt, 'POWER', M_(nt, 'DIVIDE', r, 0.034), 4.0))
    h1 = M_(nt, 'MULTIPLY', M_(nt, 'MULTIPLY', wave, rip), edge)
    fine = NOISE(nt, VSCALE(nt, co, 1.0), 260.0, 2.0, 0.5, w=tw)
    h2 = M_(nt, 'MULTIPLY', M_(nt, 'SUBTRACT', fine, 0.5), vib)
    h = M_(nt, 'ADD', h1, h2)
    b = BSDF(nt, (0.14, 0.050, 0.012), 0.025, normal=BUMP(nt, h, 1.0, 1.0)); b.inputs['IOR'].default_value = 1.33
    b.inputs['Specular IOR Level'].default_value = 0.5
    OUTP(nt, o, b); return m, nt
def mat_emit(name, col, s):
    m, nt, o = new_mat(name); em = N(nt, 'ShaderNodeEmission', col, s); OUTP(nt, o, em); return m
def mat_ghost():
    m, nt, o = new_mat('ghost'); co = OBJ(nt); x, y, z = SEP(nt, co)
    edge = M_(nt, 'GREATER_THAN', M_(nt, 'MAXIMUM', M_(nt, 'ABSOLUTE', x), M_(nt, 'ABSOLUTE', z)), A_ - 0.0022)
    fade = VALUE(nt, 'GA', 0.0)
    em = N(nt, 'ShaderNodeEmission', (0.55, 0.85, 1.0), M_(nt, 'ADD', 0.6, M_(nt, 'MULTIPLY', edge, 7.0)))
    tr = N(nt, 'ShaderNodeBsdfTransparent')
    mix = N(nt, 'ShaderNodeMixShader', M_(nt, 'MULTIPLY', fade, M_(nt, 'ADD', 0.22, M_(nt, 'MULTIPLY', edge, 0.7))), tr, em)
    OUTP(nt, o, mix); return m, nt
def mat_paper():
    """framed technical prints on the wall (they are far out of focus): cream paper + faint ruled curves."""
    m, nt, o = new_mat('paper'); co = OBJ(nt); x, y, z = SEP(nt, co)
    lines = M_(nt, 'LESS_THAN', M_(nt, 'ABSOLUTE', M_(nt, 'SUBTRACT', M_(nt, 'MULTIPLY', M_(nt, 'COSINE', M_(nt, 'MULTIPLY', x, 30.0)), 0.025), z)), 0.0015)
    col = MIXC(nt, lines, (0.30, 0.28, 0.24), (0.06, 0.065, 0.07))
    OUTP(nt, o, BSDF(nt, col, 0.8)); return m

MW = dict(wall=mat_wall(), walnut=mat_wood('walnut', False, 1.0), track=mat_track(), black=mat_anod('black_anod', (0.018, 0.018, 0.02), 0.42, 0.7),
          amber=mat_amber(), wheel=mat_wheel(), steel=mat_anod('steel', (0.62, 0.62, 0.64), 0.18, 1.0), brass=mat_anod('brass', (0.55, 0.40, 0.17), 0.3, 1.0),
          rubber=flat_mat('rubber', (0.012, 0.012, 0.013), 0.72), porcelain=mat_porcelain(), gray=mat_anod('battery', (0.06, 0.065, 0.07), 0.5, 0.2),
          white=flat_mat('marker_white', (0.8, 0.8, 0.78), 0.4), led_g=mat_emit('led_green', (0.2, 1.0, 0.35), 12.0),
          led_r=mat_emit('led_red', (1.0, 0.08, 0.04), 10.0), led_w=mat_emit('led_white', (1.0, 0.92, 0.8), 18.0),
          bead=mat_emit('contact_bead', (1.0, 0.42, 0.05), 12.0), lamp=mat_emit('picture_lamp', (1.0, 0.78, 0.52), 25.0),
          shelf_led=mat_emit('shelf_led', (1.0, 0.85, 0.66), 30.0), paper=mat_paper(), frame=mat_anod('frame', (0.03, 0.028, 0.025), 0.45, 0.3))
MW['ghost'], GHOST_NT = mat_ghost()

# ================================================================== WORLD + LIGHTS
wd = bpy.data.worlds.new('gallery'); sc.world = wd
try: wd.use_nodes = True
except Exception: pass
bgn = next(n for n in wd.node_tree.nodes if n.type == 'BACKGROUND'); bgn.inputs['Color'].default_value = (0.012, 0.018, 0.015, 1); bgn.inputs['Strength'].default_value = 0.5

RIG = empty('light_rig')
def area(name, energy, col, loc, tgt, size, size_y=None, spread=None, parent=RIG):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = col
    ld.shape = 'RECTANGLE' if size_y else 'SQUARE'; ld.size = size
    if size_y: ld.size_y = size_y
    if spread: ld.spread = radians(spread)
    o = bpy.data.objects.new(name, ld); o.location = loc; o.rotation_euler = aim(loc, tgt); return link(o, parent)
def spot(name, energy, col, loc, tgt, angle=40, blend=0.6, size=0.05, parent=RIG):
    ld = bpy.data.lights.new(name, 'SPOT'); ld.energy = energy; ld.color = col; ld.spot_size = radians(angle); ld.spot_blend = blend
    ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld); o.location = loc; o.rotation_euler = aim(loc, tgt); return link(o, parent)
def aim(pos, tgt, roll=0.0):
    d = Vector(tgt) - Vector(pos); q = d.to_track_quat('-Z', 'Y')
    return (q @ Matrix.Rotation(roll, 3, 'Z').to_quaternion()).to_euler() if roll else q.to_euler()
WARM = (1.0, 0.80, 0.60); NEUT = (1.0, 0.93, 0.86)
KEY = area('key', 70.0, WARM, (-0.75, -0.95, 1.05), (0.05, 0, 0.06), 0.55)
FILL = area('fill', 9.0, NEUT, (1.3, -1.1, 0.45), (0, 0, 0.08), 1.2)
RIMR = area('rim', 26.0, (1.0, 0.86, 0.68), (0.35, 0.75, 0.75), (0, 0, 0.06), 0.35, 1.0)
WASH = spot('wall_wash', 30.0, (1.0, 0.76, 0.50), (-0.2, -0.3, 1.4), (0.1, 0.42, 0.35), 60, 1.0, 0.2)
TOPF = area('top_soft', 6.0, NEUT, (0.0, -0.15, 1.4), (0, 0, 0), 0.9)

# ================================================================== SET: wall, plinth, frames
def box_obj(name, size, loc, m, parent=None, bevel=0.0):
    bm = bmesh.new(); add_box(bm, size, (0, 0, 0)); o = mesh_obj(name, bm, [m], loc, parent)
    if bevel:
        bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'
    return o
X0S, X1S = -3.0, 16.0
box_obj('wall', (X1S - X0S, 0.02, 1.9), ((X0S + X1S) / 2, 0.43, 0.65), MW['wall'])
box_obj('dado_rail', (X1S - X0S, 0.012, 0.016), ((X0S + X1S) / 2, 0.414, 0.33), MW['wall'], bevel=0.003)
for pa, pb, py0 in ((X0S, XR - 1.0, -1.32), (XR - 1.0, XR + 1.0, -0.56), (XR + 1.0, X1S, -1.32)):
    box_obj(f'plinth{pa:.0f}', (pb - pa, 0.43 - py0, 0.36), ((pa + pb) / 2, (0.43 + py0) / 2, -0.22), MW['walnut'], bevel=0.004)
for i, fx in enumerate([x * 0.92 - 2.6 for x in range(22)]):
    if 15.5 < fx or abs(fx - XG) < 0.5: continue
    fz = 0.86 + 0.04 * ((i * 7) % 3 - 1)
    box_obj(f'frame{i}', (0.24, 0.016, 0.30), (fx, 0.41, fz), MW['frame'], bevel=0.002)
    box_obj(f'print{i}', (0.19, 0.004, 0.25), (fx, 0.400, fz), MW['paper'])
    box_obj(f'lampbar{i}', (0.16, 0.012, 0.010), (fx, 0.37, fz + 0.20), MW['brass'], bevel=0.002)
    box_obj(f'lamp{i}', (0.15, 0.004, 0.003), (fx, 0.37, fz + 0.194), MW['lamp'])

# ================================================================== TRACKS
def strip_bm(bm, xa, xb, y0, y1, zf, zbot, n, xo=0.0, seam=False):
    """one solid track piece from xa to xb, top following zf(x); the top/side edges are sharp (bevelled by modifier)."""
    xs = [xa + (xb - xa) * i / n for i in range(n + 1)]
    T0 = [bm.verts.new((x, y0, zf(x))) for x in xs]; T1 = [bm.verts.new((x, y1, zf(x))) for x in xs]
    B0 = [bm.verts.new((x, y0, zbot)) for x in xs]; B1 = [bm.verts.new((x, y1, zbot)) for x in xs]
    top = []
    for i in range(n):
        top.append(bm.faces.new((T0[i], T0[i + 1], T1[i + 1], T1[i])))
        bm.faces.new((B0[i], B0[i + 1], T0[i + 1], T0[i])); bm.faces.new((T1[i], T1[i + 1], B1[i + 1], B1[i]))
        bm.faces.new((B1[i], B1[i + 1], B0[i + 1], B0[i]))
    bm.faces.new((B0[0], T0[0], T1[0], B1[0])); bm.faces.new((B1[-1], T1[-1], T0[-1], B0[-1]))
    for f in top: f.smooth = True
    return top
def finish_track(name, bm, loc=(0, 0, 0), parent=None, seam_fn=None):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        fs = e.link_faces
        e.smooth = not (len(fs) == 2 and fs[0].smooth != fs[1].smooth) and all(f.smooth for f in fs)
    o = mesh_obj(name, bm, [MW['track']], loc, parent)
    me = o.data
    at = me.attributes.new('seam', 'FLOAT', 'POINT')
    at.data.foreach_set('value', [seam_fn(v.co.x + o.location.x) if seam_fn else 0.0 for v in me.vertices])
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0008; bv.segments = 2; bv.limit_method = 'ANGLE'; bv.angle_limit = radians(50)
    bv.harden_normals = False
    return o
def matched_track(name, xo, z0, xa, xb, y_c=0.0, per_arc=False):
    """both strips of a matched catenary road (arc crests at xo + k PA, height z0). Separate solid piece per arc."""
    objs = []; ks = range(int(math.floor((xa - xo) / PA)), int(math.ceil((xb - xo) / PA)) + 1)
    bm = bmesh.new() if not per_arc else None
    for k in ks:
        a, b = xo + (k - 0.5) * PA, xo + (k + 0.5) * PA
        if b < xa or a > xb: continue
        if per_arc: bm = bmesh.new()
        for sgn in (-1, 1):
            yc = y_c + sgn * GY
            strip_bm(bm, a + 0.00015, b - 0.00015, yc - TWD / 2, yc + TWD / 2, lambda x: road_z(x, xo, z0), z0 - 0.030, 40)
        if per_arc: objs.append((k, finish_track(f'{name}_k{k}', bm)))
    if not per_arc:
        objs = finish_track(name, bm, seam_fn=lambda x: 0.0)
    return objs
def flat_track(name, xa, xb, z0, y_c=0.0):
    bm = bmesh.new()
    for sgn in (-1, 1):
        yc = y_c + sgn * GY
        strip_bm(bm, xa, xb, yc - TWD / 2, yc + TWD / 2, lambda x: z0, z0 - 0.030, 4)
    return finish_track(name, bm)
def base_plate(name, xa, xb, z0, y_c=0.0):
    return box_obj(name, (xb - xa, 0.23, 0.010), ((xa + xb) / 2, y_c, z0 - 0.035), MW['black'], bevel=0.0015)

matched_track('track_M', 0.0, 0.0, -1.95, 1.95); base_plate('plate_M', -2.0, 2.0, 0.0)
flat_track('track_F', XF - 1.0, XF + 1.0, 0.0); base_plate('plate_F', XF - 1.05, XF + 1.05, 0.0)
R_ARCS = matched_track('track_R', XR, 0.0, XR - 0.40, XR + 0.40, per_arc=True); base_plate('plate_R', XR - 0.6, XR + 0.6, 0.0)
R_PLANK = flat_track('plank_R', XR - 0.44, XR + 0.44, 0.0)
matched_track('track_Gb', XG, 0.0, XG - 0.9, XG + 0.9); base_plate('plate_Gb', XG - 0.95, XG + 0.95, 0.0)
# two-tier display stand: walnut shelf board on two posts, a warm LED strip under its front lip
box_obj('shelf_board', (1.55, 0.36, 0.026), (XG, 0.03, ZS - 0.04 - 0.013), MW['walnut'], bevel=0.003)
for sx in (-0.76, 0.76): box_obj(f'shelf_post{sx}', (0.04, 0.30, ZS + 0.02), (XG + sx, 0.06, ZS / 2 - 0.05), MW['walnut'], bevel=0.003)
box_obj('shelf_led', (1.45, 0.010, 0.004), (XG, -0.135, ZS - 0.068), MW['shelf_led'])
SHELF_L = area('shelf_light', 7.0, (1.0, 0.86, 0.68), (XG, -0.08, ZS - 0.075), (XG, -0.02, 0.0), 1.3, 0.12, parent=None)
flat_track('track_Gt', XG - 0.75, XG + 0.75, ZS); base_plate('plate_Gt', XG - 0.76, XG + 0.76, ZS)

# ================================================================== CART
def lathe(name, prof, m, parent=None, seg=72):
    bm = bmesh.new(); vs = [bm.verts.new((r, 0, z)) for r, z in prof]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), steps=seg, angle=2 * pi)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm, [m], (0, 0, 0), parent, smooth=True)
def handle_curve(name, pts, r, m, parent):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 6
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.materials.append(m); o = bpy.data.objects.new(name, cu); return link(o, parent)
CUP_IN = [(0.0, 0.006), (0.020, 0.006), (0.027, 0.012), (0.032, 0.028), (0.0337, 0.042), (0.0345, 0.050)]
def cup_r_at(z):
    for (r0, z0), (r1, z1) in zip(CUP_IN, CUP_IN[1:]):
        if z0 <= z <= z1 and z1 > z0: return lerp(r0, r1, (z - z0) / (z1 - z0))
    return CUP_IN[-1][0]
def wheel(name, parent, loc, side):
    bm = bmesh.new(); add_box(bm, (2 * A_, WT, 2 * A_), (0, 0, 0)); o = mesh_obj(name, bm, [MW['wheel']], loc, parent)
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0007; bv.segments = 3; bv.limit_method = 'ANGLE'
    hb = bmesh.new(); ax = Matrix.Rotation(pi / 2, 4, 'X')
    yo = side * (WT / 2)                                    # outer face
    add_cyl(hb, 0.0125, 0, 0.0045, 0, 48, axis_mtx=Matrix.Translation((0, yo + side * 0.00225, 0)) @ ax @ Matrix.Translation((0, 0, -0.00225)))
    for i in range(4):
        a = pi / 4 + i * pi / 2
        add_cyl(hb, 0.0018, 0, 0.0022, 0, 16, axis_mtx=Matrix.Translation((0.0175 * cos(a), yo + side * 0.0011, 0.0175 * sin(a))) @ ax @ Matrix.Translation((0, 0, -0.0011)))
    add_cyl(hb, 0.0042, 0, 0.007, 0, 6, axis_mtx=Matrix.Translation((0, yo + side * (0.0045 + 0.0035), 0)) @ ax @ Matrix.Translation((0, 0, -0.0035)))
    h = mesh_obj(name + '_hub', hb, [MW['steel']], (0, 0, 0), o, smooth=False)
    db = bmesh.new(); add_cyl(db, 0.0022, 0, 0.0004, 0, 24, axis_mtx=Matrix.Translation((0, yo + side * 0.0117, 0)) @ ax @ Matrix.Translation((0, 0, -0.0002)))
    mesh_obj(name + '_dot', db, [MW['white']], (0, 0, 0), o)
    return o
def build_cart(name, teamat):
    root = empty(name)
    parts = {}
    # chassis: two amber side rails, cross members, deck plate
    bm = bmesh.new()
    for sy in (-1, 1): add_box(bm, (0.38, 0.010, 0.036), (0, sy * 0.053, 0.006))
    for cx in (-0.17, 0.0, 0.17): add_box(bm, (0.014, 0.096, 0.014), (cx, 0, 0.016))
    add_box(bm, (0.40, 0.124, 0.008), (0, 0, 0.028))
    o = mesh_obj(name + '_chassis', bm, [MW['amber']], (0, 0, 0), root); bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0012; bv.segments = 3; bv.limit_method = 'ANGLE'
    # axles, bearing blocks, screws
    bm = bmesh.new(); ax = Matrix.Rotation(pi / 2, 4, 'X')
    for x in (-HB, HB):
        add_cyl(bm, 0.0042, -0.090, 0.090, 0, 20, axis_mtx=Matrix.Translation((x, 0, 0)) @ ax)
    o = mesh_obj(name + '_axles', bm, [MW['steel']], (0, 0, 0), root, smooth=True)
    bm = bmesh.new()
    for x in (-HB, HB):
        for sy in (-1, 1): add_box(bm, (0.026, 0.012, 0.026), (x, sy * 0.064, 0.0))
    add_box(bm, (0.012, 0.130, 0.010), (0.205, 0, 0.012))                      # front bumper
    add_box(bm, (0.012, 0.130, 0.010), (-0.205, 0, 0.012))
    o = mesh_obj(name + '_blocks', bm, [MW['black']], (0, 0, 0), root); bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.001; bv.segments = 2; bv.limit_method = 'ANGLE'
    bm = bmesh.new()
    for x in (-0.15, -0.075, 0.075, 0.15):
        for sy in (-1, 1): add_cyl(bm, 0.0022, 0, 0.0016, 0, 12, axis_mtx=Matrix.Translation((x, sy * 0.0585, 0.014)) @ ax @ Matrix.Translation((0, 0, -0.0008)))
    for x in (-HB, HB):
        for sy in (-1, 1):
            for dz in (-0.008, 0.008): add_cyl(bm, 0.0016, 0, 0.0014, 0, 10, axis_mtx=Matrix.Translation((x + 0.008, sy * 0.0705, dz)) @ ax @ Matrix.Translation((0, 0, -0.0007)))
    mesh_obj(name + '_screws', bm, [MW['steel']], (0, 0, 0), root, smooth=True)
    # motor + gearbox at the rear (drives the rear axle), battery + controller at the front
    bm = bmesh.new()
    add_cyl(bm, 0.0135, -0.034, 0.030, 0, 32, axis_mtx=Matrix.Translation((-0.150, 0, 0.0455)) @ ax)
    for i in range(7): add_cyl(bm, 0.0152, -0.026 + i * 0.0065, -0.026 + i * 0.0065 + 0.0022, 0, 32, axis_mtx=Matrix.Translation((-0.150, 0, 0.0455)) @ ax)
    add_box(bm, (0.040, 0.026, 0.018), (-0.150, 0.034, 0.041))
    o = mesh_obj(name + '_motor', bm, [MW['black']], (0, 0, 0), root, smooth=False)
    bm = bmesh.new(); add_box(bm, (0.062, 0.084, 0.022), (0.140, 0, 0.043))
    o = mesh_obj(name + '_battery', bm, [MW['gray']], (0, 0, 0), root); bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = 0.002; bv.segments = 3; bv.limit_method = 'ANGLE'
    bm = bmesh.new(); add_cyl(bm, 0.0018, 0, 0.002, 0, 12, axis_mtx=Matrix.Translation((0.120, -0.0425, 0.048)) @ ax @ Matrix.Translation((0, 0, -0.001)))
    mesh_obj(name + '_led', bm, [MW['led_g']], (0, 0, 0), root)
    bm = bmesh.new(); add_box(bm, (0.003, 0.016, 0.005), (-0.2125, 0, 0.012)); mesh_obj(name + '_tail', bm, [MW['led_r']], (0, 0, 0), root)
    bm = bmesh.new()
    for sy in (-1, 1): add_box(bm, (0.003, 0.010, 0.006), (0.2125, sy * 0.04, 0.012))
    mesh_obj(name + '_head', bm, [MW['led_w']], (0, 0, 0), root)
    bm = bmesh.new(); add_box(bm, (0.120, 0.100, 0.002), (0, 0, 0.033)); mesh_obj(name + '_mat', bm, [MW['rubber']], (0, 0, 0), root)
    # saucer + cup + tea (cup rattles on the saucer; tea surface tilts on its own)
    cupr = empty(name + '_cuproot', (0, 0, 0.034), root)
    lathe(name + '_saucer', [(0.0, 0.0), (0.030, 0.0), (0.032, 0.0018), (0.031, 0.0032), (0.044, 0.0058), (0.0515, 0.0105), (0.053, 0.0118),
                             (0.0518, 0.0124), (0.043, 0.0082), (0.030, 0.0062), (0.0, 0.0062)][::-1], MW['porcelain'], cupr)
    cup = empty(name + '_cup', (0, 0, 0.0062), cupr)
    lathe(name + '_cupmesh', [(0.0, 0.0), (0.020, 0.0), (0.0215, 0.0012), (0.027, 0.006), (0.0335, 0.024), (0.0365, 0.042), (0.0378, 0.0505),
                              (0.0372, 0.0512), (0.0362, 0.0508)] + [(r, z) for r, z in CUP_IN[::-1]][1:-1] + [(0.0, 0.006)], MW['porcelain'], cup)
    handle_curve(name + '_handle', [(0.0360, 0, 0.041), (0.0525, 0, 0.040), (0.0545, 0, 0.026), (0.0325, 0, 0.017)], 0.0028, MW['porcelain'], cup)
    TZ = 0.047; tr_ = cup_r_at(TZ) - 0.0002
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=96, radius=tr_)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    tea = mesh_obj(name + '_tea', bm, [teamat], (0, 0, TZ), cup)
    parts.update(root=root, cuproot=cupr, cup=cup, tea=tea)
    # wheels (rear/front x near/far), parented to the root at axle height
    for key, x in (('r', -HB), ('f', HB)):
        for sk, sy in (('n', -1), ('o', 1)):
            parts['w' + key + sk] = wheel(f'{name}_w{key}{sk}', root, (x, sy * GY, 0), sy)
    return parts
TEA1, TEA1_NT = mat_tea(); TEA2, TEA2_NT = mat_tea()
CART = build_cart('cart', TEA1); CART['tea_nt'] = TEA1_NT
CART2 = build_cart('cart2', TEA2); CART2['tea_nt'] = TEA2_NT
# ghost wheel for the reveal and the contact bead for the close-up
gb = bmesh.new(); add_box(gb, (2 * A_, WT * 0.6, 2 * A_), (0, 0, 0)); GHOST = mesh_obj('ghost', gb, [MW['ghost']], (XR, -GY, A_))
gb = bmesh.new(); bmesh.ops.create_uvsphere(gb, u_segments=24, v_segments=12, radius=0.0017); BEAD = mesh_obj('bead', gb, [MW['bead']], (0, 0, 0), smooth=True)

# ================================================================== CAMERAS
def make_cam(name, ortho=False):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'AUTO'; cd.sensor_width = 36.0; cd.clip_start = 0.02; cd.clip_end = 30
    if ortho: cd.type = 'ORTHO'
    else: cd.dof.use_dof = True
    o = bpy.data.objects.new(name, cd); return link(o)
CAM = make_cam('cam'); CAMO = make_cam('cam_ortho', True); sc.camera = CAM

# ================================================================== SHOTS
# Each shot maps screen time t -> simulation time s, and s -> cart kinematics from the exact contact solution.
PHI_A0 = 0.0                                      # hook starts with the rear wheel face-down on crest 0 of lane M
def kin_M(phi_fn, xo=0.0, z0=0.0):
    def k(s):
        ph = phi_fn(s); x, z, c = matched(ph, xo, z0); return dict(x=x, z=z, phi=ph, contact=c)
    return k
def kin_F(phi_fn, x0, z0=0.0):
    def k(s):
        ph = phi_fn(s); x, z, p = flat(ph, x0, z0); return dict(x=x, z=z, phi=ph, pivot=p)
    return k
# hook / loop: one continuous motion; the loop shot ends exactly where the hook begins
KIN_A = kin_M(lambda s: PHI_A0 - OM * s)
# flat control: landings timed so the 4th one lands 0.08 s before the freeze shot
S_C0 = T_C - T_B
PHI_B0 = -2 * pi - OM * 0.08 + OM * S_C0
X0_B = XF - 0.26 - HB
KIN_B = kin_F(lambda s: PHI_B0 - OM * s, X0_B)
S_C1 = (2 * pi + pi / 4 + PHI_B0) / OM          # tipping point (corner straight below the axle)
T_C_HOLD = T_D - 0.12
def s_C(t):                                       # ultra slow motion that keeps creeping to the tipping point
    u = clamp((t - T_C) / (T_C_HOLD - T_C)); return S_C0 + (S_C1 - S_C0) * (1 - (1 - u) ** 1.6)
# reveal: ghost wheel on lane R
T_P0 = B['change'] + 0.02                       # plank starts sinking
T_A0 = B['change'] + 0.45                       # first arc rises
T_LN0, T_LN1 = B['change'] + 0.25, B['change'] + 1.25   # profile line draws left -> right
T_G0 = B['these2'] + 0.05                       # ghost appears
K_GH = -2
KIN_GH = kin_M(lambda s: -K_GH * pi / 2 - OM * 0.8 * s, XR)
# contact close-up: 0.3x slow motion, face rolls over crest K_E then the corner lands in the join
K_E = round(1.0 / PA); U0 = -0.55 * G.L
PL0 = -atan(sinh(U0)); SLOW_E = 0.30
KIN_E = kin_M(lambda s: -K_E * pi / 2 + PL0 - OM * s)
# clean wide release from rest
XF1 = -1.25; K_F1 = round((XF1 - 0.30 - HB) / PA)
KIN_F1 = kin_M(lambda s: -K_F1 * pi / 2 - OM * ramp(s))
# low 3/4 tracking
K_F2 = 3
KIN_F2 = kin_M(lambda s: -K_F2 * pi / 2 - OM * s)
# shelves: same motor input on both carts, both from rest
K_G = round(-0.44 / PA); X0_G = XG + K_G * PA
KIN_GB = kin_M(lambda s: -K_G * pi / 2 - OM * ramp(s), XG)
KIN_GT = kin_F(lambda s: -OM * ramp(s), X0_G, ZS)

def shot(t):
    if t < T_RW0: return 'A'
    if t < T_B: return 'RW'
    if t < T_C: return 'B'
    if t < T_D: return 'C'
    if t < T_E: return 'D'
    if t < T_F1: return 'E'
    if t < T_F2: return 'F1'
    if t < T_F3: return 'F2'
    if t < T_G: return 'F3'
    if t < T_H: return 'G'
    return 'H'
def sim(t):
    """shot, sim time s, kinematics fn (for cart 1)."""
    S = shot(t)
    if S == 'A': return S, t, KIN_A
    if S == 'RW': return S, T_RW0 - (t - T_RW0) * 5.5, KIN_A
    if S == 'H': return S, t - DUR, KIN_A
    if S == 'B': return S, t - T_B, KIN_B
    if S == 'C': return S, s_C(t), KIN_B
    if S == 'D': return S, t - T_G0, KIN_GH
    if S == 'E': return S, (t - T_E) * SLOW_E, KIN_E
    if S == 'F1': return S, t - T_F1, KIN_F1
    if S in ('F2', 'F3'): return S, t - T_F2, KIN_F2
    return S, t - T_G, KIN_GB

# ------------------------------------------------------------------ crossings -> impulses (tea, sound)
def crossings(kin, s0, s1, step=1 / 600):
    """s where a corner lands (flat: phi crosses k pi/2) or passes a join (matched: phi crosses (k + 1/2) pi/2)."""
    out = []; prev = None; s = s0
    while s <= s1:
        ph = kin(s)['phi']; q = (-ph) / (pi / 2) + (0.5 if 'contact' in kin(s) else 0.0)
        if prev is not None and floor(q) > floor(prev): out.append(s)
        prev = q; s += step
    return out
IMP = {}
def impulses(key, kin, s0, s1):
    if key not in IMP:
        IMP[key] = crossings(kin, s0, s1)
    return IMP[key]
S_RING = -0.9                                     # the tea ring that the loop hands from the last shot to the first

def tea_model(kin, s, imps, flat_road, slow=1.0, extra=()):
    rip = 0.0; tilt = 0.0; rat = 0.0
    for si in imps:
        d = s - si
        if d < 0 or d > 3.0: continue
        if flat_road:
            rip += 0.0011 * exp(-d / 0.55) * cos(2 * pi * 3.6 * d)
            tilt += 0.032 * exp(-d / 0.5) * sin(2 * pi * 2.3 * d)
            rat += 0.0045 * exp(-d / 0.07) * sin(2 * pi * 19 * d)
        else:
            rip += 0.00011 * exp(-d / 0.5) * cos(2 * pi * 3.6 * d)
    for si, amp in extra:
        d = s - si
        if 0 <= d < 3.0: rip += amp * exp(-d / 0.6) * cos(2 * pi * 3.6 * d)
    h = 1 / 240
    ax = (kin(s + h)['x'] - 2 * kin(s)['x'] + kin(s - h)['x']) / (h * h)
    tilt += clamp(0.6 * ax / 9.81, -0.05, 0.05)
    vib = 0.00007 if flat_road else 0.00005
    return rip, vib, tilt, rat

# ------------------------------------------------------------------ recorders for one cart
def set_cart(P, k, y=0.0, tea=None, t=0.0, bob=0.0):
    LOC(P['root'], (k['x'] + HB, y, k['z'] + bob))
    for w in ('wrn', 'wro', 'wfn', 'wfo'): ROT(P[w], (0, -k['phi'], 0))
    rip, vib, tilt, rat = tea or (0, 0.00002, 0, 0)
    ROT(P['tea'], (0, tilt, 0))
    ROT(P['cup'], (rat * 0.4, rat * 0.25, rat))
    NODEV(P['tea_nt'], 'RIP', rip); NODEV(P['tea_nt'], 'VIB', vib); NODEV(P['tea_nt'], 'TW', t * 6.0)

def bob_flat(s, imps):
    z = 0.0
    for si in imps:
        d = s - si
        if 0 <= d < 0.4: z += 0.0006 * exp(-d / 0.06) * sin(2 * pi * 13 * d)
    return z

# ------------------------------------------------------------------ cameras
VB = 2 * A_ / 0.70                                 # mean speed on the flat road
def cam_track_A(s):
    xl = HB + VM * s                               # constant-speed dolly following the mean cart position
    return (xl + 0.015, -1.36, 0.375), (xl + 0.015, 0.0, 0.126), 55.0, 4.0
def cam(t):
    S, s, kin = sim(t)
    if S in ('A', 'RW'): return ('P',) + cam_track_A(s)
    if S == 'H':
        p, q, lens, fs = cam_track_A(s); u = eio(clamp((t - T_H) / 3.2))
        p0 = (p[0] - 0.04, -1.72, 0.40); q0 = (q[0], 0.0, 0.14)
        return 'P', tuple(lv(p0, p, u)), tuple(lv(q0, q, u)), lerp(50.0, lens, u), fs
    if S == 'B':                                   # same camera as the hook: same lens, height, tracking dolly
        xl = X0_B + HB + VB * s
        return 'P', (xl + 0.015, -1.36, 0.375), (xl + 0.015, 0.0, 0.126), 55.0, 4.0
    if S == 'C':
        xh = KIN_B(S_C1)['x']
        return 'P', (xh + 0.012, -GY - 0.70, 0.071), (xh + 0.012, -GY, 0.053), 85.0, 4.0
    if S == 'D': return 'O', (XR, -2.0, 0.12), (XR, 0.0, 0.12), 0.62, 0
    if S == 'E':
        x0 = KIN_E(0)['x']; xc = x0 + SLOW_E * VM * (t - T_E) + 0.006
        return 'P', (xc, -GY - 0.75, 0.062), (xc, -GY, 0.050), 70.0, 4.5
    if S == 'F1':
        u = eio(clamp((t - T_F1) / (T_F2 - T_F1)))
        return 'P', (XF1 + 0.03 * u, -1.52 + 0.24 * u, 0.33 - 0.03 * u), (XF1 + 0.03 * u, 0.0, 0.12), 40.0, 5.0
    if S == 'F2':
        xl = K_F2 * PA + HB + VM * s; u = eio(clamp((t - T_F2) / (T_F3 - T_F2)))
        return 'P', (xl - 0.34 + 0.07 * u, -0.52, 0.255 - 0.015 * u), (xl + 0.02, -0.005, 0.110), 50.0, 4.0
    if S == 'F3':
        xl = K_F2 * PA + HB + VM * s; u = eio(clamp((t - T_F3) / (T_G - T_F3)))
        return 'P', (xl + 0.36 - 0.05 * u, -0.46, 0.40 - 0.03 * u), (xl - 0.03, 0.0, 0.035), 45.0, 5.6
    return 'P', (XG, -1.95, 0.30), (XG, 0.0, 0.24), 60.0, 6.3

# ------------------------------------------------------------------ labels + sound cues
LABELS = []; EVENTS = []; HUD = {}; CURVES = {k: [] for k in ('hum', 'rate', 'roll', 'music', 'room')}
def label(text, t0, t1, anchor=None, xy=None, style='tag', color='o'):
    LABELS.append(dict(text=text, t0=t0, t1=t1, anchor=anchor, xy=xy, style=style, color=color, pts={}))
def ev(t, name, gain=1.0, rate=1.0, pan=0.0):
    if 0 <= t < DUR: EVENTS.append(dict(t=round(t, 3), name=name, gain=round(gain, 3), rate=round(rate, 3), pan=pan))

label('SQUARE WHEELS', 0.30, T_RW0 - 0.05, anchor=lambda t: V(KIN_A(t)['x'] + HB, -0.10, 0.265), color='o')
label('FLAT ROAD', T_B + 0.20, T_C - 0.02, anchor=lambda t: V(X0_B + HB + VB * (t - T_B), -0.10, 0.255), color='r')
label('AXLE HEIGHT', T_C + 0.55, T_D - 0.05, anchor=lambda t: V(KIN_B(s_C(t))['x'] + 0.050, -GY, A_ + 0.034), color='y')
label('MATCHED CATENARY ROAD', T_A0 + 1.3, T_E - 0.08, xy=(0.5, 0.36), color='g')
label('AXLE HEIGHT', T_E + 0.45, B['rolls_e'] + 0.15, anchor=lambda t: V(cam(t)[1][0] + 0.072, HUB_Y, A_ + 0.007), color='y', style='note')
label('MATCHED CATENARY ROAD', B['called'] - 0.25, T_G - 0.08, anchor=lambda t: V(K_F2 * PA + HB - 0.24 + VM * (t - T_F2), -0.13, 0.0), color='g')
label('DRIVEN, NOT FREE ENERGY', T_G + 0.45, B['wheel2'] - 0.25, xy=(0.5, 0.505), color='y')
label('IDEALIZED GEOMETRY', B['wheel2'] - 0.15, T_H - 0.08, xy=(0.5, 0.505), color='b')

# ------------------------------------------------------------------ per-frame state
TRAIL = {}
def proj(p):
    q = world_to_camera_view(sc, sc.camera, Vector(p)); return [round(q.x, 4), round(1 - q.y, 4)]
def trail(key, t, p, span=2.6):
    tr = TRAIL.setdefault(key, []); tr.append((t, Vector(p)))
    while tr and t - tr[0][0] > span: tr.pop(0)
    return [proj(q) for _, q in tr]
def hub(k, y=0.0): return (k['x'], y + HUB_Y, k['z'])

PREV = {'shot': None}
def state(t):
    S, s, kin = sim(t); k = kin(s); h = {}
    if S != PREV['shot']: TRAIL.clear(); PREV['shot'] = S
    # camera
    kind, p, q, lens, fs = cam(t)
    cobj = CAMO if kind == 'O' else CAM; sc.camera = cobj
    LOC(cobj, p); ROT(cobj, aim(p, q))
    if kind == 'O': PROP(cobj.data, 'ortho_scale', lens)
    else:
        PROP(cobj.data, 'lens', lens); PROP(cobj.data, 'dof.aperture_fstop', fs)
        PROP(cobj.data, 'dof.focus_distance', (Vector(q) - Vector(p)).length)
    focus_x = q[0]
    LOC(RIG, (focus_x, 0, ZS * 0.5 if S == 'G' else 0.0))
    # default placements (parked carts, hidden helpers)
    VIS(GHOST, S == 'D'); VIS(BEAD, S == 'E')
    VIS(CART['root'], S != 'D'); VIS(CART2['root'], S == 'G')
    for kk, o in R_ARCS:
        a = T_A0 + (kk + 4) * 0.11; u = clamp((t - a) / 0.32)
        z = -0.075 * (1 - eo(u))
        LOC(o, (0, 0, z if t >= T_D else -0.075))
    pz = -0.07 * eio(clamp((t - T_P0) / 0.62)) if t >= T_D else 0.0
    LOC(R_PLANK, (0, 0, pz))
    NODEV(GHOST_NT, 'GA', ss(t, T_G0, T_G0 + 0.3) * (1 - ss(t, T_E - 0.25, T_E - 0.02)))

    if S in ('A', 'RW', 'H'):
        imps = impulses('M', KIN_A, -9.5, T_RW0 + 0.5)
        tea = tea_model(KIN_A, s, imps, False, extra=[(S_RING, 0.00016)])
        set_cart(CART, k, 0.0, tea, t)
        if S == 'RW': h['rewind'] = round((t - T_RW0) / (T_B - T_RW0), 3)
    elif S in ('B', 'C'):
        imps = impulses('B', KIN_B, -1.0, S_C1 + 0.1)
        tea = tea_model(KIN_B, s, imps, True)
        set_cart(CART, k, 0.0, tea, s, bob=bob_flat(s, imps))
        y0 = HUB_Y
        h['ref'] = [proj((XF - 1.5, y0, A_)), proj((XF + 1.5, y0, A_))]
        if S == 'B': h['trail'] = trail('B', t, hub(k))
        else:
            hb_ = hub(k); h['bracket'] = [proj(hb_), proj((hb_[0], y0, A_))]
            h['pivot'] = proj((k['pivot'][0], -GY - WT / 2 - 0.002, k['pivot'][1]))
            h['hgt'] = round((k['z'] - A_) / A_, 4)
            if t < T_C + 0.5: h['freeze'] = round((t - T_C) / 0.5, 3)
    elif S == 'D':
        LOC(GHOST, (k['x'], -GY - 0.004, k['z'])); ROT(GHOST, (0, -k['phi'], 0))
        prof = [proj((x, -GY - TWD / 2, road_z(x, XR))) for x in [XR - 0.24 + i * 0.48 / 160 for i in range(161)]]
        h['prof'] = prof; h['prof_u'] = round(clamp((t - T_LN0) / (T_LN1 - T_LN0)), 4)
        h['prof_a'] = round(1 - ss(t, T_A0 + 1.3, T_A0 + 1.8) * 0.85, 3)
        if t >= T_G0:
            h['ref'] = [proj((XR - 1, -GY - 0.006, A_)), proj((XR + 1, -GY - 0.006, A_))]
            h['trail'] = trail('D', t, (k['x'], -GY - 0.006, k['z']))
            h['ref_a'] = round(ss(t, T_G0, T_G0 + 0.4), 3)
    elif S == 'E':
        imps = impulses('E', KIN_E, -3.0, 1.5)
        set_cart(CART, k, 0.0, tea_model(KIN_E, s, imps, False), s)
        c = k['contact']; cp = (c[0], -GY - WT / 2 - 0.0009, c[1])
        LOC(BEAD, cp)
        h['ref'] = [proj((k['x'] - 1, HUB_Y, A_)), proj((k['x'] + 1, HUB_Y, A_))]
        h['ctrail'] = trail('E', t, cp, 2.2)
        h['hubp'] = proj(hub(k))
    elif S in ('F1', 'F2', 'F3'):
        kinf = KIN_F1 if S == 'F1' else KIN_F2
        imps = impulses('F1' if S == 'F1' else 'F2', kinf, -3.0, 9.0)
        set_cart(CART, k, 0.0, tea_model(kinf, s, imps, False), t)
        if S == 'F1':
            h['ref'] = [proj((XF1 - 1.5, HUB_Y, A_)), proj((XF1 + 1.5, HUB_Y, A_))]
            h['trail'] = trail('F1', t, hub(k), 3.5)
    elif S == 'G':
        kt = KIN_GT(s); imt = impulses('GT', KIN_GT, -1.0, 6.0); imb = impulses('GB', KIN_GB, -1.0, 6.0)
        set_cart(CART, kt, 0.0, tea_model(KIN_GT, s, imt, True), s, bob=bob_flat(s, imt))
        set_cart(CART2, k, 0.0, tea_model(KIN_GB, s, imb, False), s)
        h['ref'] = [proj((XG - 1, HUB_Y, ZS + A_)), proj((XG + 1, HUB_Y, ZS + A_))]
        h['ref2'] = [proj((XG - 1, HUB_Y, A_)), proj((XG + 1, HUB_Y, A_))]
        h['trail'] = trail('GT', t, hub(kt)); h['trail2'] = trail('GB', t, hub(k))
        if T_G + 0.45 <= t < T_H - 0.08:
            h['motor'] = [proj(hub(kt)) + [round(-kt['phi'], 3)], proj(hub(k)) + [round(-k['phi'], 3)]]
    if S != 'G':                                    # park cart 2 on its shelf
        set_cart(CART2, KIN_GB(0.0), 0.0, None, t)
    if S != 'E': LOC(BEAD, (XR, 0, -1))
    return S, s, k, h

# ------------------------------------------------------------------ sound cues (screen time)
def cues():
    # flat control: four muted corner knocks + cup clinks
    for si in impulses('B', KIN_B, -1.0, S_C1 + 0.1):
        t = T_B + si
        if T_B <= t < T_C: ev(t, 'knock', 1.5); ev(t + 0.035, 'clink', 0.7)
    # matched road: soft rhythmic click as each corner settles into a join
    for si in impulses('M', KIN_A, -9.5, T_RW0 + 0.5):
        for t in (si, si + DUR):
            if (0 <= t < T_RW0) or (T_H <= t < DUR): ev(t, 'click', 0.55)
    for si in impulses('E', KIN_E, -3.0, 1.5):
        t = T_E + si / SLOW_E
        if T_E <= t < T_F1: ev(t, 'click', 0.8, 0.55)
    for key, kin, t0, t1 in (('F1', KIN_F1, T_F1, T_F2), ('F2', KIN_F2, T_F2, T_G)):
        for si in impulses(key, kin, -3.0, 9.0):
            if t0 <= t0 + si < t1: ev(t0 + si, 'click', 0.5)
    for si in impulses('GT', KIN_GT, -1.0, 6.0):
        if T_G <= T_G + si < T_H: ev(T_G + si, 'knock', 0.65, 1.0, -0.2); ev(T_G + si + 0.035, 'clink', 0.35)
    for si in impulses('GB', KIN_GB, -1.0, 6.0):
        if T_G <= T_G + si < T_H: ev(T_G + si, 'click', 0.45, 1.0, 0.2)
    ev(DUR + S_RING, 'tick', 0.9)
    ev(T_RW0, 'rewind', 0.55); ev(T_C, 'freeze', 0.8)
    ev(T_P0, 'slide', 0.7)
    for kk, _ in R_ARCS: ev(T_A0 + (kk + 4) * 0.11 + 0.30, 'clack', 0.5 + 0.05 * (kk % 2))
    ev(T_G0, 'shimmer', 0.5)
    ev(T_F1, 'motor_start', 0.8); ev(T_G, 'motor_start', 0.9)
    ev(T_D, 'swish', 0.4); ev(T_G - 0.05, 'swish', 0.35)
def curves(t, S, s):
    c = {}
    c['hum'] = {'A': 1.0, 'RW': 0.6, 'H': 1.0, 'B': 1.0, 'C': 0.7, 'D': 0.0, 'E': 0.75, 'F1': min(1.0, (t - T_F1) / 0.45),
                'F2': 1.0, 'F3': 1.0, 'G': 1.3 * min(1.0, (t - T_G) / 0.45)}[S]
    c['rate'] = {'C': clamp(1 - (t - T_C) / 0.4, 0.25, 1), 'E': 0.62, 'RW': 1.8}.get(S, 1.0)
    c['roll'] = {'A': 1.0, 'H': 1.0, 'E': 0.95, 'F1': min(1.0, (t - T_F1) / 0.45), 'F2': 1.0, 'F3': 1.0, 'G': 0.8, 'B': 0.6, 'C': 0.2}.get(S, 0.0)
    c['music'] = 0.45 if T_E <= t < B['smoothing'] else (0.75 if S == 'C' else 1.0)
    c['room'] = 1.0
    return c

# ================================================================== bake
CUTS = []
for f in range(1, NF):
    if shot(f / FPS) != shot((f - 1) / FPS): CUTS.append(f)
def bake():
    t0 = time.time()
    for f in range(NF):
        FR[0] = f; t = f / FPS
        S, s, k, h = state(t)
        bpy.context.view_layer.update()
        for lb in LABELS:
            if lb['t0'] <= t < lb['t1']:
                if lb['anchor']:
                    p = world_to_camera_view(sc, sc.camera, lb['anchor'](t))
                    if p.z > 0: lb['pts'][f] = (round(p.x, 4), round(1 - p.y, 4))
                else: lb['pts'][f] = lb['xy']
        HUD[f] = h
        for kk, v in curves(t, S, s).items(): CURVES[kk].append(round(v, 4))
    print(f'state loop {time.time() - t0:.1f}s')
    write_fcurves()
bake()
# camera switches (perspective <-> orthographic) as timeline markers
cur = None
for f in range(NF):
    want = CAMO if shot(f / FPS) == 'D' else CAM
    if want is not cur:
        mk = sc.timeline_markers.new(f'cam{f}', frame=f); mk.camera = want; cur = want
sc.camera = CAM
cues()
json.dump(dict(fps=FPS, nf=NF, w=sc.render.resolution_x, h=sc.render.resolution_y, cuts=CUTS, hud={str(k): v for k, v in HUD.items() if v},
               labels=[dict(text=l['text'], style=l['style'], color=l['color'], t0=l['t0'], t1=l['t1'], pts=l['pts']) for l in LABELS]),
          open(os.path.join(OUT, 'labels.json'), 'w'))
json.dump(dict(events=sorted(EVENTS, key=lambda e: e['t']), beats=B, dur=DUR, fps=FPS, curves=CURVES, cuts=[c / FPS for c in CUTS],
               shots=dict(A=0, RW=T_RW0, B=T_B, C=T_C, D=T_D, E=T_E, F1=T_F1, F2=T_F2, F3=T_F3, G=T_G, H=T_H)),
          open(os.path.join(OUT, 'events.json'), 'w'), indent=1)
print('cuts at', [round(c / FPS, 2) for c in CUTS])

if arg('--save'):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg('--save')), compress=True)
    print('saved', arg('--save'))
if arg('--stills'):
    for ts in arg('--stills').split(','):
        f = int(round(float(ts) * FPS)); sc.frame_set(f)
        c = sc.camera; print('STILL', ts, c.name, c.data.type, tuple(round(v, 3) for v in c.matrix_world.translation),
                             tuple(round(v, 3) for v in c.matrix_world.to_euler()), round(c.data.ortho_scale, 3), round(c.data.lens, 1))
        sc.render.filepath = os.path.join(OUT, f'still_{float(ts):06.2f}.png')
        bpy.ops.render.render(write_still=True)
    print('STILLS_DONE')
if arg('--frames'):
    a, b = (int(x) for x in arg('--frames').split(':'))
    sc.frame_start, sc.frame_end = a, b
    sc.render.filepath = os.path.join(OUT, 'frames', 'f_#####')
    t0 = time.time(); bpy.ops.render.render(animation=True)
    print(f'FRAMES_DONE {a}:{b} in {time.time() - t0:.0f}s')
