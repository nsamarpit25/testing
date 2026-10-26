"""scene.py: "What If You Drilled Straight Through the Earth?" (Blender 5.2, Eevee, 9:16 @ 30 fps).

Two sets live in one scene: the EARTH set (R = 10 cutaway planet at the origin, vacuum tunnel, explorer) and the
DRILL set (a cut-away slice of ground at x = X0 that a tunnel-boring drill chews through, crust -> mantle -> liquid
outer core). Everything is procedural. state(t) poses the world for time t; the bake loop records every frame as
F-curves so the saved .blend plays on its own. Beat times come from the narration's word timestamps.

  blender -b -P scene.py -- --words narration.words.json --out OUT [--res 480] [--samples 16]
          [--stills 1.0,20.5] [--frames A:B] [--save project.blend]
Writes OUT/labels.json (label anchors + HUD values per frame) and OUT/events.json (sound cues + control curves).
"""
import bpy, bmesh, math, json, sys, os, random, time
from math import sin, cos, pi, atan2, sqrt, radians
from mathutils import Vector, Matrix, Euler, noise
from bpy_extras import anim_utils
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(k, d=None): return argv[argv.index(k) + 1] if k in argv else d
OUT = os.path.abspath(arg('--out', 'out')); os.makedirs(OUT, exist_ok=True)
FPS = 30
RES = int(arg('--res', '480')); SAMPLES = int(arg('--samples', '16'))
random.seed(11)

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
B = dict(jumped=W('jumped'), first=W('first'), rips=W('rips'), crust=W('crust'), nothing=W('nothing'),
         deeper=W('deeper'), hotter=W('hotter'), mantle=W('mantle'), lava=W('lava'), solid=W('solid'),
         glowing=W('glowing'), crushing=W('crushing'), your1=W('your'), fail=W('fail'), below=W('below'),
         sea=W('sea'), liquid=W('liquid'), around=W('around'), solid2=W('solid', 2), suns=W("sun's"),
         your2=W('your', 2), gone=W('gone'), but2=W('but', 2), suppose=W('suppose'), tunnel=W('tunnel'),
         air=W('air'), friction=W('friction'), jump=W('jump'), fall=W('fall'), faster2=W('faster', 2),
         center=W('center'), pull=W('pull'), top=W('top'), fly=W('fly'), past=W('past'), slowing=W('slowing'),
         other=W('other'), side=W('side'), back=W('back'), without=W('without'), forth=W('forth'),
         forever=W('forever'))
DUR = round(WORDS[-1]['e'] + 2.3, 2); NF = int(round(DUR * FPS))
# shot boundaries (seconds)
T_RW0 = B['first'] - 0.30; T_RW1 = B['first'] + 0.20          # rewind
T_SLAM = B['rips'] - 0.02
T_MANT = B['mantle'] - 0.32; T_CLOSE = B['glowing'] - 0.05; T_FAIL = B['your1'] - 0.1
T_BREAK = B['below'] + 0.22; T_CORE = B['around'] - 0.08; T_GONE0 = B['your2'] - 0.1
T_TWIST = B['but2'] - 0.06; T_JUMP0 = B['jump'] - 0.45; T_CEN0 = B['center'] - 0.15
T_PAST = B['fly'] - 0.5; T_SOUTH = B['other'] - 1.2; T_WIDE = B['back'] - 0.95; T_FLYIN = DUR - 1.55

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
def keys(t, ks, ease=sm):
    if t <= ks[0][0]: return ks[0][1]
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1
            return lerp(a, b, u) if isinstance(a, (int, float)) else tuple(lerp(x, y, u) for x, y in zip(a, b))
    return ks[-1][1]
def pchip(xs, ys):
    """monotone cubic through (xs, ys); returns f(x)."""
    n = len(xs); h = [xs[i + 1] - xs[i] for i in range(n - 1)]; d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else 3 * (h[i - 1] + h[i]) / ((2 * h[i] + h[i - 1]) / d[i - 1] + (h[i] + 2 * h[i - 1]) / d[i]) for i in range(1, n - 1)] + [d[-1]]
    def f(x):
        if x <= xs[0]: return ys[0] + m[0] * (x - xs[0]) if m[0] else ys[0]
        if x >= xs[-1]: return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x); u = (x - xs[i]) / h[i]
        return ((2 * u ** 3 - 3 * u ** 2 + 1) * ys[i] + (u ** 3 - 2 * u ** 2 + u) * h[i] * m[i]
                + (-2 * u ** 3 + 3 * u ** 2) * ys[i + 1] + (u ** 3 - u ** 2) * h[i] * m[i + 1])
    return f

# ------------------------------------------------------------------ scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.fps = FPS; sc.frame_start = 0; sc.frame_end = NF - 1
sc.render.resolution_x, sc.render.resolution_y = RES, int(round(RES * 16 / 9 / 2)) * 2
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
ee = sc.eevee; ee.taa_render_samples = SAMPLES
for k, v in dict(use_raytracing=True, use_fast_gi=True, use_shadows=True, shadow_ray_count=1, shadow_step_count=6,
                 fast_gi_distance=4.0, fast_gi_quality=0.5).items():
    try: setattr(ee, k, v)
    except Exception as e: print('eevee', k, e)
try: ee.ray_tracing_method = 'SCREEN'
except Exception as e: print('eevee rt', e)
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.45
try: sc.render.motion_blur_position = 'START'
except Exception as e: print('mb', e)
try: sc.view_settings.view_transform = 'Khronos PBR Neutral'
except Exception as e: print('view', e); sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'None'
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
def ico(name, r, m, loc=(0, 0, 0), sub=1, jitter=0.0, scale=(1, 1, 1), parent=None, smooth=False, seed=0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    rnd = random.Random(seed)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) * (1 + rnd.uniform(-jitter, jitter))
    return mesh_obj(name, bm, [m], loc, parent, smooth)
def uvsphere(name, r, m, loc=(0, 0, 0), seg=32, ring=16, parent=None, scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    return mesh_obj(name, bm, [m], loc, parent, smooth=True)
def capsule(bm, a, b, r, mi=0, seg=12):
    """rounded limb from point a to b (cylinder + end spheres), added into bm."""
    a, b = Vector(a), Vector(b); d = b - a; L_ = d.length
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    add_prim(bm, bmesh.ops.create_cone, Matrix.Translation((a + b) / 2) @ rot, mi, cap_ends=False, segments=seg, radius1=r, radius2=r, depth=L_)
    for p in (a, b): add_prim(bm, bmesh.ops.create_uvsphere, Matrix.Translation(p), mi, u_segments=seg, v_segments=seg // 2, radius=r)
def plane_xz(name, x0, x1, z0, z1, m, y=0.0, parent=None, nx=1, nz_=1):
    bm = bmesh.new(); vs = {}
    for i in range(nx + 1):
        for j in range(nz_ + 1):
            vs[i, j] = bm.verts.new((lerp(x0, x1, i / nx), y, lerp(z0, z1, j / nz_)))
    for i in range(nx):
        for j in range(nz_): bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.y > 0: f.normal_flip()
    return mesh_obj(name, bm, [m], (0, 0, 0), parent)
def halfpipe(name, r, z0, z1, m, parent=None, seg=40, origin_top=False):
    """half cylinder behind the y = 0 cut plane (y >= 0), normals facing the axis."""
    bm = bmesh.new(); top, bot = [], []
    zt, zb = (0.0, -(z1 - z0)) if origin_top else (z1, z0)
    for i in range(seg + 1):
        a = pi * i / seg; x, y = r * cos(a), r * sin(a)
        top.append(bm.verts.new((x, y, zt))); bot.append(bm.verts.new((x, y, zb)))
    for i in range(seg):
        f = bm.faces.new((bot[i], bot[i + 1], top[i + 1], top[i]))
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        if Vector((c.x, c.y, 0)).dot(f.normal) > 0: f.normal_flip()
    return mesh_obj(name, bm, [m], (0, 0, z0 if not origin_top else z1), parent, smooth=True) if False else mesh_obj(name, bm, [m], (0, 0, 0), parent, smooth=True)

# ================================================================== MATERIALS
R = 10.0; TW = 0.2                                  # earth radius, tunnel radius (scene units)
RB = dict(inner=1221 / 6371, outer=3480 / 6371, upper=(6371 - 660) / 6371, crust=0.975)
FLOW_TREES = []; HEAT_TREES = []
def mat_cut(name='earth_cut', emul=1.0):
    """the cut face of the planet: colour/emission by radius sqrt(x^2 + z^2) / R."""
    m, nt, o = new_mat(name); FLOW_TREES.append(nt)
    flow = VALUE(nt, 'FLOW')
    x, y, z = SEP(nt, POS(nt))
    r = M_(nt, 'DIVIDE', M_(nt, 'SQRT', M_(nt, 'ADD', M_(nt, 'MULTIPLY', x, x), M_(nt, 'MULTIPLY', z, z))), R)
    p = POS(nt)
    grain = NOISE(nt, p, 2.2, 8, 0.62)
    fine = NOISE(nt, p, 14.0, 4, 0.6)
    swirl = NOISE(nt, VSCALE(nt, p, 0.32), 1.3, 5, 0.6, w=M_(nt, 'MULTIPLY', flow, 0.22), dist=1.4)
    plume = NOISE(nt, VSCALE(nt, p, 0.5), 1.0, 4, 0.55, w=M_(nt, 'MULTIPLY', flow, 0.03), dist=0.6)
    I, O, U, C = RB['inner'], RB['outer'], RB['upper'], RB['crust']
    base = RAMP(nt, r, [(0.0, (1.0, 0.86, 0.5)), (I - 0.01, (1.0, 0.70, 0.22)), (I + 0.004, (1.0, 0.50, 0.07)),
                        (0.38, (1.0, 0.36, 0.035)), (O - 0.006, (0.92, 0.22, 0.02)), (O + 0.004, (0.48, 0.09, 0.03)),
                        (0.72, (0.30, 0.065, 0.03)), (U - 0.004, (0.17, 0.055, 0.035)), (U + 0.004, (0.14, 0.075, 0.05)),
                        (C - 0.003, (0.11, 0.075, 0.06)), (C + 0.002, (0.36, 0.31, 0.26)), (1.0, (0.44, 0.38, 0.31))])
    estr = RAMP(nt, r, [(0.0, 2.1), (I - 0.01, 1.7), (I + 0.004, 1.5), (O - 0.006, 1.0), (O + 0.004, 0.45),
                        (0.75, 0.22), (U - 0.004, 0.07), (U + 0.004, 0.035), (C - 0.003, 0.01), (C + 0.002, 0.0), (1.0, 0.0)])
    lines = RAMP(nt, r, [(0, 0), (I - 0.004, 0), (I, 1), (I + 0.004, 0), (O - 0.004, 0), (O, 1), (O + 0.004, 0),
                         (U - 0.003, 0), (U, 0.5), (U + 0.003, 0), (C - 0.003, 0), (C, 0.6), (C + 0.003, 0), (1, 0)])
    band_oc = RAMP(nt, r, [(0, 0), (I + 0.01, 0), (I + 0.03, 1), (O - 0.02, 1), (O, 0), (1, 0)])
    band_man = RAMP(nt, r, [(0, 0), (O, 0), (O + 0.01, 1), (C - 0.01, 1), (C, 0), (1, 0)])
    sw = RAMP(nt, swirl, [(0.3, 0.55), (0.5, 1.0), (0.62, 1.55), (0.75, 0.8)])
    pl = RAMP(nt, plume, [(0.35, 0.6), (0.55, 1.0), (0.7, 1.45)])
    band_ic = RAMP(nt, r, [(0, 1), (I - 0.005, 1), (I + 0.002, 0)])
    xtal = RAMP(nt, VORO(nt, p, 1.6, 'F1', 'Distance'), [(0.0, 1.25), (0.6, 0.8)])
    var = MIXC(nt, band_oc, (1, 1, 1), sw)
    var = MIXC(nt, band_ic, var, xtal)
    var = MIXC(nt, band_man, var, MIXC(nt, 0.5, pl, RAMP(nt, grain, [(0.3, 0.7), (0.7, 1.3)]), 'MULTIPLY'))
    col = MIXC(nt, 1.0, base, MIXC(nt, 0.35, var, RAMP(nt, fine, [(0.3, 0.85), (0.7, 1.15)]), 'MULTIPLY'), 'MULTIPLY')
    em = M_(nt, 'MULTIPLY', sock(estr), M_(nt, 'ADD', M_(nt, 'MULTIPLY', SEP(nt, var)[0], 1.0), 0.0))
    em = M_(nt, 'ADD', em, M_(nt, 'MULTIPLY', sock(lines), 0.9))
    ecol = MIXC(nt, sock(lines), col, (1.0, 0.85, 0.55))
    nrm = BUMP(nt, M_(nt, 'ADD', grain, M_(nt, 'MULTIPLY', fine, 0.3)), 0.25, 0.1)
    em = M_(nt, 'MULTIPLY', em, emul)
    dcol = MIXC(nt, 1.0, col, RAMP(nt, r, [(0.0, 0.12), (O, 0.2), (O + 0.01, 0.55), (C, 0.8), (C + 0.003, 1.0)]), 'MULTIPLY')
    OUTP(nt, o, BSDF(nt, dcol, 0.78, 0.0, emit_col=ecol, emit=em, normal=nrm))
    return m
def mat_surface():
    m, nt, o = new_mat('earth_surface'); blend_mode(m, 'DITHERED')
    p = OBJ(nt); x, y, z = SEP(nt, p)
    n1 = NOISE(nt, VSCALE(nt, p, 1 / R), 1.6, 9, 0.6, dist=0.2); n2 = NOISE(nt, p, 1.4, 6, 0.6)
    land = RAMP(nt, M_(nt, 'ADD', n1, RAMP(nt, M_(nt, 'DIVIDE', M_(nt, 'ABSOLUTE', z), R), [(0.9, 0.0), (0.97, 0.12)])), [(0.505, 0), (0.525, 1)])
    landcol = RAMP(nt, n2, [(0.3, (0.12, 0.26, 0.07)), (0.5, (0.32, 0.36, 0.12)), (0.62, (0.55, 0.45, 0.26)), (0.75, (0.42, 0.36, 0.28))])
    ocean = RAMP(nt, n1, [(0.35, (0.01, 0.04, 0.16)), (0.5, (0.03, 0.14, 0.32))])
    az = M_(nt, 'ABSOLUTE', z)
    ice = RAMP(nt, M_(nt, 'ADD', M_(nt, 'DIVIDE', az, R), M_(nt, 'MULTIPLY', n2, 0.12)), [(1.5, 0), (1.6, 1)])
    col = MIXC(nt, land, ocean, landcol); col = MIXC(nt, ice, col, (0.86, 0.9, 0.95))
    rough = RAMP(nt, land, [(0, 0.22), (1, 0.85)])
    # tunnel mouths: cut-out where x^2 + y^2 < TW^2, darkened rim around it
    rr = M_(nt, 'SQRT', M_(nt, 'ADD', M_(nt, 'MULTIPLY', x, x), M_(nt, 'MULTIPLY', y, y)))
    hole = M_(nt, 'LESS_THAN', rr, TW)
    rim = RAMP(nt, rr, [(TW, 0.0), (TW + 0.02, 0.3), (TW + 0.22, 1.0)])
    col = MIXC(nt, 1.0, col, rim, 'MULTIPLY')
    sh = BSDF(nt, col, rough, 0.0, normal=BUMP(nt, n2, 0.15, 0.2))
    mix = N(nt, 'ShaderNodeMixShader', hole, sh, N(nt, 'ShaderNodeBsdfTransparent'))
    OUTP(nt, o, mix); return m
def mat_clouds():
    m, nt, o = new_mat('clouds'); blend_mode(m)
    p = OBJ(nt); x, y, z = SEP(nt, p)
    n = NOISE(nt, VSCALE(nt, p, 1 / R), 3.0, 8, 0.6, dist=0.6)
    rr = M_(nt, 'SQRT', M_(nt, 'ADD', M_(nt, 'MULTIPLY', x, x), M_(nt, 'MULTIPLY', y, y)))
    a = M_(nt, 'MULTIPLY', RAMP(nt, n, [(0.5, 0), (0.64, 0.85)]), RAMP(nt, rr, [(1.8, 0), (3.0, 1)]))
    OUTP(nt, o, BSDF(nt, (1, 1, 1), 0.9, alpha=SEP(nt, a)[0])); return m
def mat_atmo():
    m, nt, o = new_mat('atmo'); blend_mode(m)
    lw = N(nt, 'ShaderNodeLayerWeight', blend=0.35)
    f = RAMP(nt, lw.outputs['Facing'], [(0.55, 0), (0.92, 1)])
    em = N(nt, 'ShaderNodeEmission', (0.25, 0.55, 1.0), 2.5)
    mix = N(nt, 'ShaderNodeMixShader', SEP(nt, f)[0], N(nt, 'ShaderNodeBsdfTransparent'), em)
    OUTP(nt, o, mix)
    try: m.use_transparency_overlap = False
    except Exception: pass
    return m
def mat_strata():
    """drill-set ground slice: layered by world depth; hotter (glowing cracks) with depth."""
    m, nt, o = new_mat('strata')
    p = POS(nt); x, y, z = SEP(nt, p)
    d = M_(nt, 'DIVIDE', z, -D_CORE)                 # 0 at surface, 1 at the core boundary
    warp = NOISE(nt, VSCALE(nt, p, 0.06), 1.0, 3, 0.5)
    bands = M_(nt, 'SINE', M_(nt, 'ADD', M_(nt, 'MULTIPLY', z, 2.6), M_(nt, 'MULTIPLY', warp, 9.0)))
    bandf = M_(nt, 'ADD', 0.86, M_(nt, 'MULTIPLY', bands, 0.14))
    base = RAMP(nt, d, [(0.0, (0.17, 0.11, 0.07)), (0.007, (0.40, 0.29, 0.19)), (0.02, (0.62, 0.49, 0.33)),
                        (0.035, (0.47, 0.43, 0.40)), (0.05, (0.60, 0.47, 0.35)), (0.065, (0.50, 0.47, 0.46)),
                        (0.18, (0.44, 0.40, 0.39)), (0.268, (0.33, 0.27, 0.24)), (0.276, (0.13, 0.135, 0.10)),
                        (0.6, (0.12, 0.07, 0.05)), (1.0, (0.16, 0.06, 0.03))])
    speck = NOISE(nt, p, 6.0, 6, 0.65)
    g = RAMP(nt, speck, [(0.3, 0.72), (0.7, 1.22)])
    col = MIXC(nt, 1.0, base, g, 'MULTIPLY')
    col = MIXC(nt, 1.0, col, (1, 1, 1), 'MULTIPLY')
    bandc = RAMP(nt, M_(nt, 'ADD', M_(nt, 'MULTIPLY', bands, 0.5), 0.5), [(0.0, (0.75, 0.62, 0.48)), (0.35, (1.05, 0.95, 0.85)), (0.6, (0.85, 0.66, 0.45)), (1.0, (1.1, 1.05, 1.0))])
    colb = MIXC(nt, RAMP(nt, d, [(0.0, 1.0), (0.27, 0.7), (0.3, 0.1)]), col, MIXC(nt, 1.0, MIXC(nt, 1.0, col, bandf, 'MULTIPLY'), bandc, 'MULTIPLY'))
    heat = RAMP(nt, d, [(0.24, 0.0), (0.3, 0.15), (0.6, 0.38), (0.85, 0.7), (1.0, 1.0)])
    dn = N(nt, 'ShaderNodeTexNoise', p, Scale=0.35, Detail=4.0)
    pw = VADD(nt, p, VSCALE(nt, dn.outputs['Color'], 3.0))
    cr = VORO(nt, pw, 0.5, 'DISTANCE_TO_EDGE')
    cr2 = VORO(nt, VSCALE(nt, pw, 2.7), 1.0, 'DISTANCE_TO_EDGE')
    crack = M_(nt, 'MAXIMUM', SEP(nt, RAMP(nt, cr, [(0.0, 1.0), (0.025, 0.25), (0.06, 0.0)]))[0], M_(nt, 'MULTIPLY', SEP(nt, RAMP(nt, cr2, [(0.0, 1.0), (0.025, 0.0)]))[0], 0.18))
    mott = RAMP(nt, NOISE(nt, VSCALE(nt, p, 0.25), 1.0, 5, 0.6), [(0.35, 0.1), (0.65, 1.0)])
    ecol = N(nt, 'ShaderNodeBlackbody', M_(nt, 'ADD', 850, M_(nt, 'MULTIPLY', SEP(nt, heat)[0], 1100))).outputs[0]
    em = M_(nt, 'MULTIPLY', M_(nt, 'POWER', SEP(nt, heat)[0], 1.5), M_(nt, 'ADD', M_(nt, 'MULTIPLY', SEP(nt, mott)[0], 0.22), M_(nt, 'MULTIPLY', crack, 2.2)))
    em = M_(nt, 'MULTIPLY', em, 1.3)
    nrm = BUMP(nt, M_(nt, 'ADD', speck, M_(nt, 'MULTIPLY', crack, -0.5)), 0.45, 0.3)
    OUTP(nt, o, BSDF(nt, colb, 0.85, 0.0, emit_col=ecol, emit=em, normal=nrm)); return m
def mat_liquid():
    m, nt, o = new_mat('liquid_iron'); FLOW_TREES.append(nt)
    flow = VALUE(nt, 'FLOW'); p = POS(nt)
    n = NOISE(nt, VSCALE(nt, p, 0.09), 1.0, 6, 0.6, w=M_(nt, 'MULTIPLY', flow, 0.35), dist=2.2)
    n2 = NOISE(nt, VSCALE(nt, p, 0.4), 1.0, 3, 0.5, w=M_(nt, 'MULTIPLY', flow, 0.7), dist=0.5)
    c = RAMP(nt, M_(nt, 'ADD', M_(nt, 'MULTIPLY', n, 0.8), M_(nt, 'MULTIPLY', n2, 0.2)),
             [(0.32, (0.30, 0.04, 0.01)), (0.45, (1.0, 0.28, 0.02)), (0.56, (1.0, 0.50, 0.08)), (0.68, (1.0, 0.75, 0.32)), (0.78, (1.0, 0.92, 0.7))])
    e = RAMP(nt, n, [(0.32, 0.5), (0.5, 1.6), (0.72, 3.2)])
    OUTP(nt, o, BSDF(nt, c, 0.25, 0.6, emit_col=c, emit=SEP(nt, e)[0])); return m
def heatable(name, col, rough=0.4, metal=0.0, kind='', zbias=0.0):
    """drill paint/steel; a HEAT value (0..1.3) drives blackbody glow, uneven via noise."""
    m, nt, o = new_mat(name); HEAT_TREES.append(nt)
    h = VALUE(nt, 'HEAT'); p = OBJ(nt)
    n = NOISE(nt, p, 1.6, 4, 0.55)
    zl = M_(nt, 'ADD', SEP(nt, p)[2], zbias)
    hh = M_(nt, 'ADD', M_(nt, 'SUBTRACT', M_(nt, 'MULTIPLY', h, 1.7), M_(nt, 'DIVIDE', zl, 7.0)), M_(nt, 'MULTIPLY', M_(nt, 'SUBTRACT', n, 0.5), 0.5), clamp_=True)
    temp = M_(nt, 'ADD', 700, M_(nt, 'MULTIPLY', hh, 3000))
    ecol = N(nt, 'ShaderNodeBlackbody', temp).outputs[0]
    em = M_(nt, 'MULTIPLY', M_(nt, 'POWER', M_(nt, 'MAXIMUM', M_(nt, 'SUBTRACT', hh, 0.25), 0.0), 2.0), 6.0)
    if kind == 'stripes':
        w = N(nt, 'ShaderNodeTexWave', p, wave_type='BANDS', bands_direction='DIAGONAL')
        w.inputs['Scale'].default_value = 1.6
        col_in = RAMP(nt, w.outputs['Fac'], [(0.45, (0.02, 0.02, 0.02)), (0.5, (0.95, 0.62, 0.04))], 'CONSTANT')
    else: col_in = col
    dark = MIXC(nt, RAMP(nt, hh, [(0.15, 0), (0.7, 0.92)]), col_in, (0.05, 0.03, 0.02))
    OUTP(nt, o, BSDF(nt, dark, rough, metal, emit_col=ecol, emit=em, normal=BUMP(nt, NOISE(nt, p, 22, 3), 0.08, 0.02))); return m
def mat_ground_top():
    m, nt, o = new_mat('ground_top'); blend_mode(m, 'DITHERED')
    p = OBJ(nt); x, y, z = SEP(nt, p)
    n = NOISE(nt, p, 0.25, 6, 0.6); n2 = NOISE(nt, p, 3.0, 5, 0.6)
    col = RAMP(nt, M_(nt, 'ADD', n, M_(nt, 'MULTIPLY', n2, 0.3)), [(0.35, (0.10, 0.17, 0.05)), (0.55, (0.20, 0.26, 0.08)), (0.68, (0.34, 0.27, 0.15)), (0.8, (0.40, 0.34, 0.24))])
    rr = M_(nt, 'SQRT', M_(nt, 'ADD', M_(nt, 'MULTIPLY', x, x), M_(nt, 'MULTIPLY', y, y)))
    hole = M_(nt, 'LESS_THAN', rr, SW)
    scorch = RAMP(nt, rr, [(SW, 0.15), (SW + 1.6, 1.0)])
    col = MIXC(nt, 1.0, col, scorch, 'MULTIPLY')
    sh = BSDF(nt, col, 0.92, normal=BUMP(nt, n2, 0.5, 0.2))
    OUTP(nt, o, N(nt, 'ShaderNodeMixShader', hole, sh, N(nt, 'ShaderNodeBsdfTransparent'))); return m
def mat_sky():
    m, nt, o = new_mat('sky_dome')
    p = OBJ(nt); x, y, z = SEP(nt, p)
    zz = M_(nt, 'DIVIDE', z, 150.0)
    c = RAMP(nt, zz, [(-0.05, (0.05, 0.03, 0.04)), (0.0, (0.95, 0.42, 0.16)), (0.05, (0.72, 0.36, 0.30)), (0.18, (0.16, 0.16, 0.34)), (0.5, (0.02, 0.03, 0.09))])
    OUTP(nt, o, N(nt, 'ShaderNodeEmission', c, 1.0)); return m
def mat_dust(name):
    m, nt, o = new_mat(name); blend_mode(m)
    f = VALUE(nt, 'FADE', 0.0); p = OBJ(nt)
    n = NOISE(nt, p, 1.4, 4, 0.6)
    lw = N(nt, 'ShaderNodeLayerWeight', blend=0.5)
    a = M_(nt, 'MULTIPLY', M_(nt, 'MULTIPLY', RAMP(nt, n, [(0.3, 0), (0.65, 1)]), RAMP(nt, lw.outputs['Facing'], [(0.2, 1), (0.9, 0)])), f)
    OUTP(nt, o, BSDF(nt, (0.42, 0.33, 0.24), 1.0, alpha=SEP(nt, a)[0])); return m
def mat_emit(name, col, s):
    m, nt, o = new_mat(name); OUTP(nt, o, N(nt, 'ShaderNodeEmission', col, s)); m.diffuse_color = (*col, 1); return m
def mat_visor():
    m, nt, o = new_mat('visor'); lw = N(nt, 'ShaderNodeLayerWeight', blend=0.3)
    e = RAMP(nt, lw.outputs['Facing'], [(0.4, 0.2), (0.95, 3.0)])
    OUTP(nt, o, BSDF(nt, (0.01, 0.03, 0.05), 0.08, 0.6, emit_col=(0.1, 0.85, 1.0), emit=SEP(nt, e)[0], coat=1.0)); return m

D_CORE = 110.0; SW = 1.65; X0 = 400.0           # drill set: depth of the core boundary, shaft radius, x offset
M = dict(cut=mat_cut(), tun=mat_cut('tunnel_wall', 0.45), surf=mat_surface(), cloud=mat_clouds(), atmo=mat_atmo(), strata=mat_strata(), liq=mat_liquid(),
         paint=heatable('drill_paint', (0.92, 0.58, 0.05), 0.42), steel=heatable('drill_steel', (0.42, 0.43, 0.45), 0.32, 1.0),
         dark=heatable('drill_dark', (0.06, 0.06, 0.07), 0.5, 0.4), stripes=heatable('drill_stripes', None, 0.45, kind='stripes'),
         carbide=heatable('drill_carbide', (0.62, 0.64, 0.66), 0.22, 1.0), panel=heatable('drill_panel', (0.42, 0.43, 0.45), 0.32, 1.0, zbias=4.2),
         lamp=mat_emit('drill_lamp', (1.0, 0.55, 0.12), 12.0), ground=mat_ground_top(), sky=mat_sky(),
         rock=flat_mat('rock_chunk', (0.36, 0.30, 0.25), 0.9), hotrock=heatable('hot_rock', (0.15, 0.12, 0.10), 0.8),
         spark=mat_emit('spark', (1.0, 0.62, 0.2), 40.0), ember=mat_emit('ember', (1.0, 0.42, 0.08), 18.0),
         blob=mat_emit('blob', (1.0, 0.75, 0.35), 14.0), ball=mat_emit('ball', (0.45, 0.95, 1.0), 22.0),
         suit=flat_mat('suit', (0.86, 0.87, 0.9), 0.55), orange=flat_mat('suit_orange', (1.0, 0.36, 0.06), 0.5),
         boot=flat_mat('boot', (0.08, 0.08, 0.09), 0.6), visor=mat_visor(),
         grav=mat_emit('arrow_gravity', (1.0, 0.18, 0.55), 9.0), vel=mat_emit('arrow_velocity', (0.2, 0.9, 1.0), 9.0),
         trail=mat_emit('trail', (0.45, 0.95, 1.0), 10.0), path=mat_emit('path', (0.45, 0.95, 1.0), 3.0),
         scan=mat_emit('scanline', (0.6, 1.0, 1.0), 30.0), bush=flat_mat('bush', (0.08, 0.16, 0.05), 0.9),
         stone=flat_mat('stone', (0.30, 0.29, 0.27), 0.85), metal=flat_mat('rig_metal', (0.55, 0.36, 0.08), 0.5, 0.7))
for k in ('path',): blend_mode(M[k])

# ------------------------------------------------------------------ world: deep space with stars
wd = bpy.data.worlds.new('space'); sc.world = wd
try: wd.use_nodes = True
except Exception: pass
wn = wd.node_tree; bg = next(n for n in wn.nodes if n.type == 'BACKGROUND')
tcw = wn.nodes.new('ShaderNodeTexCoord')
vor = wn.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 260
wn.links.new(tcw.outputs['Generated'], vor.inputs['Vector'])
st = wn.nodes.new('ShaderNodeValToRGB'); se = st.color_ramp.elements
se[0].position, se[0].color = 0.0, (1, 1, 1, 1); se[1].position, se[1].color = 0.035, (0, 0, 0, 1)
wn.links.new(vor.outputs['Distance'], st.inputs['Fac'])
nb = wn.nodes.new('ShaderNodeTexNoise'); nb.inputs['Scale'].default_value = 2.0
wn.links.new(tcw.outputs['Generated'], nb.inputs['Vector'])
neb = wn.nodes.new('ShaderNodeValToRGB'); ne = neb.color_ramp.elements
ne[0].position, ne[0].color = 0.35, (0.004, 0.006, 0.016, 1); ne[1].position, ne[1].color = 0.75, (0.02, 0.012, 0.04, 1)
wn.links.new(nb.outputs['Fac'], neb.inputs['Fac'])
add = wn.nodes.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'; add.inputs[0].default_value = 1.0
ins = [x for x in add.inputs if x.type == 'RGBA']
wn.links.new(neb.outputs['Color'], ins[0]); wn.links.new(st.outputs['Color'], ins[1])
wn.links.new([x for x in add.outputs if x.type == 'RGBA'][0], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 0.6

def sun(name, energy, col, rot, angle=2.0, shadow=True):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy; ld.color = col; ld.angle = radians(angle); ld.use_shadow = shadow
    o = bpy.data.objects.new(name, ld); o.rotation_euler = rot; return link(o)
def point(name, energy, col, loc=(0, 0, 0), size=0.1, shadow=False, parent=None):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = col; ld.shadow_soft_size = size; ld.use_shadow = shadow
    o = bpy.data.objects.new(name, ld); o.location = loc; return link(o, parent)
SUN = sun('sun', 3.2, (1.0, 0.93, 0.84), (radians(62), 0, radians(-28)))
RIM = sun('rim', 1.6, (0.55, 0.7, 1.0), (radians(-60), 0, radians(160)), 4.0, shadow=False)

# ================================================================== EARTH SET
EARTH = empty('EARTH')
def hemi(name, r, m, seg=192, ring=96):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, 'X'))   # poles on +-Y
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, -1, 0), clear_outer=True)
    return mesh_obj(name, bm, [m], (0, 0, 0), EARTH, smooth=True)
SURF = hemi('earth_surface', R, M['surf'])
CLOUD = hemi('clouds', R * 1.008, M['cloud'], 128, 64)
ATMO = hemi('atmosphere', R * 1.045, M['atmo'], 96, 48)
def disc_part(name, side):
    bm = bmesh.new(); n = 256; vs = []
    for i in range(n):
        a = 2 * pi * i / n; vs.append(bm.verts.new((R * cos(a), 0, R * sin(a))))
    bm.faces.new(vs)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    if side == 'R': bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(TW, 0, 0), plane_no=(-1, 0, 0), clear_outer=True)
    else: bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(-TW, 0, 0), plane_no=(1, 0, 0), clear_outer=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.y > 0: f.normal_flip()
    return mesh_obj(name, bm, [M['cut']], (0, 0, 0), EARTH)
DISC_R = disc_part('cut_right', 'R'); DISC_L = disc_part('cut_left', 'L')
ZT = sqrt(R * R - TW * TW)
FILL = plane_xz('slot_filler', -TW - 0.01, TW + 0.01, 0.0, 2 * ZT, M['cut'], y=0.0, parent=EARTH); FILL.location = (0, -0.002, -ZT)
TUN = halfpipe('tunnel', TW, -ZT, ZT, M['tun'], parent=EARTH)
SCAN = empty('scan_root', parent=EARTH)
bm = bmesh.new(); add_box(bm, (2 * TW + 0.08, 0.06, 0.035), (0, 0, 0)); SCANBAR = mesh_obj('scan_bar', bm, [M['scan']], (0, -0.03, 0), SCAN)
INNER = uvsphere('inner_core_ball', RB['inner'] * R * 0.995, M['cut'], (0, 0, 0), 64, 32, EARTH)
TRAIL_CU = bpy.data.curves.new('trail', 'CURVE'); TRAIL_CU.dimensions = '3D'; TRAIL_CU.bevel_depth = 0.035; TRAIL_CU.bevel_resolution = 3
sp = TRAIL_CU.splines.new('POLY'); sp.points.add(1); sp.points[0].co = (0, 0.06, -ZT, 1); sp.points[1].co = (0, 0.06, ZT, 1)
TRAIL_CU.bevel_factor_mapping_start = 'SPLINE'; TRAIL_CU.bevel_factor_mapping_end = 'SPLINE'
TRAIL = link(bpy.data.objects.new('trail', TRAIL_CU), EARTH); TRAIL_CU.materials.append(M['trail'])
PATH_CU = bpy.data.curves.new('path', 'CURVE'); PATH_CU.dimensions = '3D'; PATH_CU.bevel_depth = 0.02
sp = PATH_CU.splines.new('POLY'); sp.points.add(1); sp.points[0].co = (0, 0.06, -ZT, 1); sp.points[1].co = (0, 0.06, ZT, 1)
PATH_CU.bevel_factor_mapping_start = 'SPLINE'; PATH_CU.bevel_factor_mapping_end = 'SPLINE'
PATHO = link(bpy.data.objects.new('osc_path', PATH_CU), EARTH); PATH_CU.materials.append(M['path'])

# ------------------------------------------------------------------ explorer (1.8 m tall build, scaled to CH)
CH = 0.30
class Explorer:
    def __init__(s):
        s.root = empty('explorer'); s.root.parent = EARTH
        s.body = empty('ex_body', (0, 0, 0.98), s.root)                  # pelvis pivot
        bm = bmesh.new()
        capsule(bm, (0, 0, 0.05), (0, 0, 0.55), 0.19, 0)                 # torso
        add_box(bm, (0.36, 0.18, 0.44), (0, 0.17, 0.42), 1)              # backpack
        add_box(bm, (0.40, 0.03, 0.08), (0, -0.19, 0.3), 1)              # chest stripe
        capsule(bm, (-0.1, 0, -0.02), (0.1, 0, -0.02), 0.17, 0)          # hips
        s.torso = mesh_obj('ex_torso', bm, [M['suit'], M['orange']], (0, 0, 0), s.body, smooth=True)
        s.head = empty('ex_head', (0, 0, 0.66), s.body)
        bm = bmesh.new(); add_prim(bm, bmesh.ops.create_uvsphere, Matrix.Translation((0, 0, 0.14)), 0, u_segments=24, v_segments=12, radius=0.165)
        mesh_obj('ex_helmet', bm, [M['suit']], (0, 0, 0), s.head, smooth=True)
        bm = bmesh.new(); add_prim(bm, bmesh.ops.create_uvsphere, Matrix.Translation((0, -0.07, 0.13)) @ Matrix.Diagonal((1.0, 0.75, 0.75, 1)), 0, u_segments=20, v_segments=10, radius=0.13)
        mesh_obj('ex_visor', bm, [M['visor']], (0, 0, 0), s.head, smooth=True)
        s.arm = {}; s.fore = {}; s.leg = {}; s.shin = {}
        for side, sx in (('L', 1), ('R', -1)):
            sh = empty(f'ex_sh{side}', (0.24 * sx, 0, 0.5), s.body)
            bm = bmesh.new(); capsule(bm, (0, 0, 0), (0, 0, -0.3), 0.075, 0); mesh_obj(f'ex_ua{side}', bm, [M['suit']], (0, 0, 0), sh, smooth=True)
            el = empty(f'ex_el{side}', (0, 0, -0.3), sh)
            bm = bmesh.new(); capsule(bm, (0, 0, 0), (0, 0, -0.27), 0.065, 0); add_prim(bm, bmesh.ops.create_uvsphere, Matrix.Translation((0, 0, -0.32)), 1, u_segments=10, v_segments=6, radius=0.075)
            mesh_obj(f'ex_fa{side}', bm, [M['suit'], M['orange']], (0, 0, 0), el, smooth=True)
            hp = empty(f'ex_hip{side}', (0.1 * sx, 0, -0.04), s.body)
            bm = bmesh.new(); capsule(bm, (0, 0, 0), (0, 0, -0.42), 0.095, 0); mesh_obj(f'ex_th{side}', bm, [M['suit']], (0, 0, 0), hp, smooth=True)
            kn = empty(f'ex_kn{side}', (0, 0, -0.42), hp)
            bm = bmesh.new(); capsule(bm, (0, 0, 0), (0, 0, -0.38), 0.08, 0); add_box(bm, (0.16, 0.26, 0.12), (0, -0.05, -0.46), 1)
            mesh_obj(f'ex_sn{side}', bm, [M['suit'], M['boot']], (0, 0, 0), kn, smooth=True)
            s.arm[side], s.fore[side], s.leg[side], s.shin[side] = sh, el, hp, kn
        s.root.scale = (CH / 1.8,) * 3
        s.light = point('ex_light', 0.35, (0.5, 0.95, 1.0), (0, -0.6, 1.0), 0.2, parent=s.root)
    def pose(s, P):
        """P: dict of joint angles (radians): arm (x, y), elbow, leg (x, y), knee, head pitch."""
        for side, sx in (('L', 1), ('R', -1)):
            ROT(s.arm[side], (P.get('arm_x', 0), sx * P.get('arm_y', 0.15), 0))
            ROT(s.fore[side], (P.get('elbow', 0.1), 0, 0))
            ROT(s.leg[side], (P.get('leg_x', 0), sx * P.get('leg_y', 0.04), 0))
            ROT(s.shin[side], (P.get('knee', 0), 0, 0))
        ROT(s.head, (P.get('head', 0), 0, 0))
        ROT(s.body, (P.get('lean', 0), 0, 0))
POSES = dict(stand=dict(arm_x=0.05, arm_y=0.14, elbow=-0.25, leg_x=0, leg_y=0.03, knee=0.0, head=0.25),
             hold=dict(arm_x=-1.25, arm_y=0.2, elbow=-0.3, leg_x=0, leg_y=0.03, knee=0, head=0.45),
             crouch=dict(arm_x=0.6, arm_y=0.3, elbow=-0.5, leg_x=-0.9, leg_y=0.05, knee=1.4, head=0.3, lean=0.35),
             spread=dict(arm_x=0.1, arm_y=2.1, elbow=-0.3, leg_x=-0.15, leg_y=0.45, knee=0.35, head=-0.2),
             tuck=dict(arm_x=-1.4, arm_y=0.3, elbow=-1.6, leg_x=-1.6, leg_y=0.1, knee=2.1, head=0.4, lean=0.4),
             wave=dict(arm_x=0.0, arm_y=2.6, elbow=-0.6, leg_x=0, leg_y=0.05, knee=0.1, head=0.1))
def blendpose(a, b, u):
    ks = set(a) | set(b); return {k: lerp(a.get(k, 0), b.get(k, 0), u) for k in ks}
EX = Explorer()
BALL = uvsphere('glow_ball', 0.045, M['ball'], (0, 0, 0), 16, 8, EARTH)
BALL_L = point('ball_light', 0.6, (0.45, 0.95, 1.0), (0, 0, 0), 0.05, parent=BALL)
def arrow_obj(name, m):
    root = empty(name, parent=EARTH)
    bm = bmesh.new(); add_cyl(bm, 0.018, 0.0, 0.78, 0, 12); add_cyl(bm, 0.05, 0.78, 1.0, 0, 16, r2=0.0)
    mesh_obj(name + '_mesh', bm, [m], (0, 0, 0), root, smooth=True); return root
AG = arrow_obj('arrow_gravity', M['grav']); AV = arrow_obj('arrow_velocity', M['vel'])

# ================================================================== DRILL SET (at x = X0)
DS = empty('DRILLSET', (X0, 0, 0))
DOME = uvsphere('sky_dome', 150, M['sky'], (0, 0, 0), 48, 24, DS)
DOME.visible_shadow = False
for p in DOME.data.polygons: p.flip() if hasattr(p, 'flip') else None
bm = bmesh.new(); vs = {}
for i in range(41):
    for j in range(41): vs[i, j] = bm.verts.new((lerp(-70, 70, i / 40), lerp(0, 90, j / 40), 0))
for i in range(40):
    for j in range(40): bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
for (i, j), v in vs.items():
    if j > 6: v.co.z += 2.5 * noise.noise(Vector((v.co.x * 0.04, v.co.y * 0.04, 0.3))) * (j / 40) ** 1.5 + 6 * max(0, (j - 28) / 12) ** 2
GTOP = mesh_obj('ground_top', bm, [M['ground']], (0, 0, 0), DS, smooth=True)
FACE_L = plane_xz('face_left', -70, -SW, -D_CORE, 0.0, M['strata'], parent=DS)
FACE_R = plane_xz('face_right', SW, 70, -D_CORE, 0.0, M['strata'], parent=DS)
SHAFT = halfpipe('shaft', SW, -1.0, 0.0, M['strata'], parent=DS, seg=32)      # 1 unit tall, top at z=0 -> scaled in z
FILLD = plane_xz('shaft_filler', -SW - 0.02, SW + 0.02, -1.0, 0.0, M['strata'], parent=DS); FILLD.location.y = -0.003
LIQ = plane_xz('liquid_core', -70, 70, -D_CORE - 90, -D_CORE + 0.05, M['liq'], parent=DS); LIQ.location.y = 0.002
rnd = random.Random(5)
for i in range(26):   # surface stones and shrubs (behind the cut)
    x = rnd.uniform(-22, 22); y = rnd.uniform(2.5, 24)
    if abs(x) < 4 and y < 6: continue
    if rnd.random() < 0.5: ico(f'stone{i}', rnd.uniform(0.25, 0.8), M['stone'], (x, y, 0.1), 1, 0.3, (1, 1, 0.6), DS, seed=i)
    else: ico(f'bush{i}', rnd.uniform(0.4, 1.0), M['bush'], (x, y, 0.3), 2, 0.25, (1, 1, 0.7), DS, smooth=True, seed=i)
# A-frame gantry the drill hangs from
bm = bmesh.new()
for sx in (-1, 1):
    a = Vector((sx * 5.0, 4.5, 0)); b = Vector((sx * 1.3, 0.9, 13.0)); capsule(bm, a, b, 0.22, 0, 10)
    a2 = Vector((sx * 5.0, -0.0, 0)) if False else None
    for k in range(1, 5):
        u = k / 5; p1 = a.lerp(b, u); capsule(bm, p1, Vector((0, p1.y, p1.z)), 0.08, 0, 8)
add_box(bm, (3.6, 0.8, 0.6), (0, 0.9, 13.1), 0); add_box(bm, (1.2, 1.2, 1.0), (0, 0.6, 12.4), 1)
RIG = mesh_obj('gantry', bm, [M['metal'], M['dark']], (0, 0, 0), DS, smooth=False)
# the drill: tip at local z=0, axis +Z
DRILL = empty('drill', (0, 0, 2.0), DS)
bm = bmesh.new()
add_cyl(bm, 1.25, 1.75, 6.2, 0, 48)                                         # paint body
add_cyl(bm, 1.262, 2.0, 2.42, 3, 48)                                        # hazard band
for zr in (1.86, 3.35, 5.0, 6.1): add_torus(bm, 1.27, 0.075, zr, 2, 48, 8)
for k in range(8):
    a = 2 * pi * (k + 0.5) / 8
    add_box(bm, (0.13, 0.13, 4.1), (1.29 * cos(a), 1.29 * sin(a), 3.95), 1, Euler((0, 0, a)))
for k in range(4):
    a = 2 * pi * k / 4 + pi / 4
    capsule(bm, (1.48 * cos(a), 1.48 * sin(a), 2.0), (1.48 * cos(a), 1.48 * sin(a), 6.3), 0.07, 1, 8)
    capsule(bm, (1.48 * cos(a), 1.48 * sin(a), 4.3), (1.48 * cos(a), 1.48 * sin(a), 6.3), 0.1, 2, 8)
add_cyl(bm, 1.25, 6.2, 7.0, 0, 48, r2=0.5); add_cyl(bm, 0.5, 7.0, 7.6, 1, 24)
BODY = mesh_obj('drill_body', bm, [M['paint'], M['steel'], M['dark'], M['stripes']], (0, 0, 0), DRILL, smooth=False)
for k in range(4):
    a = 2 * pi * k / 4
    bm = bmesh.new(); add_box(bm, (0.14, 0.3, 0.14), (0, 0, 0)); mesh_obj(f'drill_lamp{k}', bm, [M['lamp']], (1.33 * cos(a), 1.33 * sin(a), 6.0), DRILL).rotation_euler = (0, 0, a)
bend = BODY.modifiers.new('Bend', 'SIMPLE_DEFORM'); bend.deform_method = 'BEND'; bend.deform_axis = 'X'; bend.angle = 0.0
try: bend.origin = DRILL
except Exception: pass
CUTTER = empty('cutter', (0, 0, 0), DRILL)
bm = bmesh.new(); add_cyl(bm, 0.12, 0.0, 1.5, 0, 40, r2=1.28) if False else None
add_prim(bm, bmesh.ops.create_cone, Matrix.Translation((0, 0, 0.75)), 0, cap_ends=True, segments=40, radius1=0.14, radius2=1.28, depth=1.5)
add_cyl(bm, 1.31, 1.5, 1.76, 1, 40)
for k in range(2):
    pts = []
    for i in range(60):
        s_ = i / 59; a = 2 * pi * 2.2 * s_ + k * pi; zz = 0.08 + 1.38 * s_; rr = 0.16 + 1.1 * s_ + 0.03
        pts.append(Vector((rr * cos(a), rr * sin(a), zz)))
    for p0, p1 in zip(pts, pts[1:]): capsule(bm, p0, p1, 0.055, 1, 6)
CUTM = mesh_obj('cutterhead', bm, [M['carbide'], M['steel']], (0, 0, 0), CUTTER, smooth=True)
TEETH = []
for k in range(14):
    a = 2 * pi * k / 14
    bm = bmesh.new(); add_prim(bm, bmesh.ops.create_cone, Matrix.Translation((0, 0, -0.14)), 0, cap_ends=True, segments=8, radius1=0.0, radius2=0.12, depth=0.28)
    TEETH.append((mesh_obj(f'tooth{k}', bm, [M['carbide']], (0, 0, 0), DS, smooth=False), a))
PANELS = []
for k in range(6):
    a0 = 2 * pi * k / 6 + 0.12; bm = bmesh.new(); vt = []
    for i in range(7):
        a = a0 + 0.8 * i / 6
        vt.append((bm.verts.new((1.33 * cos(a), 1.33 * sin(a), -0.6)), bm.verts.new((1.33 * cos(a), 1.33 * sin(a), 0.6)),
                   bm.verts.new((1.41 * cos(a), 1.41 * sin(a), -0.6)), bm.verts.new((1.41 * cos(a), 1.41 * sin(a), 0.6))))
    for i in range(6):
        for q in ((0, 1), (2, 3)):
            pass
        bm.faces.new((vt[i][2], vt[i + 1][2], vt[i + 1][3], vt[i][3])); bm.faces.new((vt[i][1], vt[i + 1][1], vt[i + 1][0], vt[i][0]))
        bm.faces.new((vt[i][3], vt[i + 1][3], vt[i + 1][1], vt[i][1])); bm.faces.new((vt[i][0], vt[i + 1][0], vt[i + 1][2], vt[i][2]))
    bm.normal_update()
    cen = Vector((1.37 * cos(a0 + 0.4), 1.37 * sin(a0 + 0.4), 0.0))
    for v in bm.verts: v.co -= cen
    PANELS.append((mesh_obj(f'panel{k}', bm, [M['panel']], (0, 0, 0), DS), cen))
STRING = empty('string_root', (0, 0, 0), DS)
bm = bmesh.new(); add_cyl(bm, 0.3, 0.0, 1.0, 0, 16); mesh_obj('drill_string', bm, [M['steel']], (0, 0, 0), STRING)
BITLIGHT = point('bit_light', 0.0, (1.0, 0.45, 0.12), (0, -1.8, 1.0), 1.0, parent=DS)
CAMFILL = point('cam_fill', 900.0, (1.0, 0.95, 0.9), (0, -10, 0), 3.0, parent=DS)
LIQLIGHT = bpy.data.lights.new('liq_light', 'AREA'); LIQLIGHT.energy = 0.0; LIQLIGHT.size = 30; LIQLIGHT.color = (1.0, 0.5, 0.15)
LIQL = link(bpy.data.objects.new('liq_light', LIQLIGHT), DS); LIQL.location = (0, -6, -D_CORE - 1.0); LIQL.rotation_euler = (radians(-100), 0, 0)

# particle pools (drill set)
class Pool:
    def __init__(s, name, n, make):
        s.objs = [make(f'{name}{i}', i) for i in range(n)]; s.spawns = []    # (t0, life, p0, v0, spin, size, kind)
    def emit(s, t0, life, p0, v0, size=1.0, spin=None, grav=-9.0):
        s.spawns.append(dict(t0=t0, life=life, p0=Vector(p0), v0=Vector(v0), size=size, grav=grav,
                             spin=spin or Vector((random.uniform(-9, 9), random.uniform(-9, 9), random.uniform(-9, 9)))))
    def assign(s):
        """greedy: each spawn gets the object that is free earliest."""
        free = [0.0] * len(s.objs); s.slots = [[] for _ in s.objs]
        for sp_ in sorted(s.spawns, key=lambda d: d['t0']):
            k = min(range(len(free)), key=lambda i: free[i])
            if free[k] > sp_['t0']: continue
            s.slots[k].append(sp_); free[k] = sp_['t0'] + sp_['life'] + 0.05
    def apply(s, t, stretch=False):
        for o, sl in zip(s.objs, s.slots):
            cur = next((d for d in sl if d['t0'] <= t < d['t0'] + d['life']), None)
            if cur is None:
                VIS(o, False); continue
            VIS(o, True); u = t - cur['t0']
            p = cur['p0'] + cur['v0'] * u + Vector((0, 0, 0.5 * cur['grav'] * u * u))
            LOC(o, DS.location + p)
            fade = 1 - ss(u, cur['life'] * 0.6, cur['life'])
            if stretch:
                v = cur['v0'] + Vector((0, 0, cur['grav'] * u))
                q = v.to_track_quat('Z', 'Y'); ROT(o, q.to_euler())
                SCL(o, (cur['size'] * fade, cur['size'] * fade, cur['size'] * (1 + v.length * 0.06) * fade))
            else:
                ROT(o, tuple(cur['spin'] * u)); SCL(o, cur['size'] * (0.3 + 0.7 * fade) if cur.get('shrink', True) else cur['size'])
ROCKS = Pool('rock', 46, lambda n, i: ico(n, 0.22, M['rock'], (0, 0, 0), 1, 0.35, (1, 0.8, 0.7), seed=i))
HOT = Pool('hot', 34, lambda n, i: ico(n, 0.2, M['hotrock'], (0, 0, 0), 1, 0.35, (1, 0.8, 0.7), seed=100 + i))
SPARKS = Pool('spark', 60, lambda n, i: uvsphere(n, 0.03, M['spark'], (0, 0, 0), 6, 4))
BLOBS = Pool('blob', 30, lambda n, i: uvsphere(n, 0.18, M['blob'], (0, 0, 0), 12, 6))
DUSTS = [uvsphere(f'dust{i}', 1.0, mat_dust(f'dust_m{i}'), (0, 0, 0), 20, 10) for i in range(6)]
EMBERS = [uvsphere(f'ember{i}', 0.035, M['ember'], (0, 0, 0), 6, 4) for i in range(36)]
for o in ROCKS.objs + HOT.objs + SPARKS.objs + BLOBS.objs + DUSTS + EMBERS: o.parent = None
DUST_EV = []   # (t0, pos, size)

# ================================================================== CAMERA
camd = bpy.data.cameras.new('cam'); camd.lens = 24; camd.sensor_fit = 'AUTO'; camd.sensor_width = 36
camd.clip_start = 0.02; camd.clip_end = 600
CAM = link(bpy.data.objects.new('cam', camd)); sc.camera = CAM
def aim(pos, tgt, roll=0.0):
    d = Vector(tgt) - Vector(pos); q = d.to_track_quat('-Z', 'Y')
    e = (q @ Matrix.Rotation(roll, 3, 'Z').to_quaternion()).to_euler() if roll else q.to_euler()
    return e

# ================================================================== TIMELINE
LABELS = []; EVENTS = []; HUD = {}; CURVES = {k: [] for k in ('drill', 'rumble', 'heat', 'wind', 'liquid', 'music')}
def label(text, t0, t1, anchor=None, xy=None, style='tag', color='o'):
    LABELS.append(dict(text=text, t0=t0, t1=t1, anchor=anchor, xy=xy, style=style, color=color, pts={}))
def ev(t, name, gain=1.0, rate=1.0): EVENTS.append(dict(t=round(t, 3), name=name, gain=gain, rate=rate))

def shot(t):
    if t < T_RW1: return 'hook'
    if t < T_MANT: return 'dig'
    if t < T_BREAK - 0.05: return 'mantle'
    if t < T_CORE: return 'liquid'
    if t < T_GONE0: return 'core'
    if t < T_TWIST: return 'gone'
    return 'earth'

# ---------------- hook: ball drop + camera dive, then rewind
T_DROP = 0.42
def ball_z(th):            # hook time th -> ball height
    u = max(0.0, th - T_DROP); return 10.0 + CH * 0.62 - 1.05 * u * u - 0.3 * u
def hook_time(t):
    if t <= T_RW0: return t
    u = (t - T_RW0) / (T_RW1 - T_RW0); return lerp(T_RW0, 0.25, eio(u))
HOOK_CAM0 = (Vector((0.85, -2.35, 11.15)), Vector((0.02, 0.05, 8.7)))
def hook_cam(th):
    z = ball_z(th); p0, t0 = HOOK_CAM0
    u = ss(th, 0.55, 1.45)
    pf = Vector((0.42 + 0.1 * sin(th * 2), -1.25, z + 1.15)); tf = Vector((0.0, 0.07, z - 1.6))
    return p0.lerp(pf, u), t0.lerp(tf, u)

# ---------------- drill depth (bit z, drill set units) and spin
def bit_z(t):
    if t < T_SLAM: return keys(t, [(T_RW1, 3.4), (B['first'] + 0.9, 1.9), (T_SLAM - 0.12, 1.2), (T_SLAM, 0.6)])
    if t < T_MANT: return keys(t, [(T_SLAM, 0.6), (T_SLAM + 0.15, -1.6), (B['nothing'] + 0.4, -11.5), (B['hotter'], -21.0), (T_MANT, -27.5)], lambda x: x)
    if t < T_CLOSE: return lerp(-60.0, -66.0, (t - T_MANT) / (T_CLOSE - T_MANT))
    if t < T_FAIL: return lerp(-84.0, -86.5, ss(t, T_CLOSE, B['crushing'] + 0.2))
    if t < T_BREAK: return keys(t, [(T_FAIL, -96.0), (T_BREAK - 0.5, -101.0), (T_BREAK, -D_CORE + 1.5)], ei)
    if t < T_CORE: return -D_CORE + 1.5 - 7.5 * eo((t - T_BREAK) / (T_CORE - T_BREAK))
    return -D_CORE - 9.0 - 1.2 * eo((t - T_GONE0) / 1.6)
def spin_speed(t):         # cutter rev/s
    return (keys(t, [(T_RW1, 0.0), (B['first'] + 0.6, 2.5), (T_SLAM, 3.2), (T_MANT, 3.0), (T_CLOSE, 1.8), (B['crushing'], 0.9), (T_FAIL + 0.4, 0.15), (T_BREAK, 0.05)]))
SPIN = {}
_acc = 0.0
for f in range(NF):
    SPIN[f] = _acc; _acc += 2 * pi * spin_speed(f / FPS) / FPS
def heat(t): return keys(t, [(B['deeper'], 0.0), (T_MANT, 0.1), (T_CLOSE, 0.3), (B['crushing'], 0.45), (T_FAIL, 0.58), (T_BREAK, 0.75), (T_CORE, 0.95), (B['gone'], 1.15)])
def squeeze(t): return ss(t, B['crushing'] - 0.1, B['crushing'] + 0.7) if T_CLOSE <= t < T_BREAK else 0.0

# ---------------- debris schedule
def burst(pool, t0, n, p0, spread, up, toward, life=1.6, size=(0.6, 1.4), grav=-9.0, side=1.0):
    for i in range(n):
        ang = random.uniform(-pi, pi)
        v = Vector((cos(ang) * random.uniform(0.3, 1) * spread * side, -random.uniform(0.4, 1.0) * toward, random.uniform(0.3, 1.0) * up))
        pool.emit(t0 + random.uniform(0, 0.05), life * random.uniform(0.7, 1.2), Vector(p0) + Vector((random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.2), random.uniform(-0.2, 0.3))), v, random.uniform(*size), grav=grav)
burst(ROCKS, T_SLAM + 0.08, 30, (0, -0.2, 0.3), 7.0, 9.0, 4.0, 1.7, (0.8, 2.2))
DUST_EV += [(T_SLAM + 0.05, Vector((0.0, 0.3, 0.6)), 3.2), (T_SLAM + 0.15, Vector((-2.2, 0.8, 0.5)), 2.4), (T_SLAM + 0.2, Vector((2.4, 0.6, 0.5)), 2.6)]
t = T_SLAM + 0.3
while t < T_MANT - 0.2:
    burst(ROCKS, t, 1, (random.choice((-0.9, 0.9)), -0.5, bit_z(t) + 0.3), 4.5, 3.5, 3.0, 1.1, (0.5, 1.2)); t += 0.12
t = T_MANT
while t < T_BREAK - 0.1:
    if t < T_CLOSE or t > T_FAIL - 0.2: burst(HOT, t, 1, (random.choice((-1.0, 1.0)), -0.6, bit_z(t) + 0.4), 3.5, 2.8, 2.5, 1.0, (0.5, 1.3))
    t += 0.2
for f in range(int(B['crushing'] * FPS), int(T_BREAK * FPS)):      # sparks where the walls grind the body
    tt = f / FPS
    rate = 0.55 if tt < T_FAIL else 1.0
    if random.random() < rate:
        for _ in range(2):
            sx = random.choice((-1, 1)); z = bit_z(tt) + random.uniform(1.8, 6.0)
            SPARKS.emit(tt, random.uniform(0.25, 0.5), (sx * 1.3, -random.uniform(0.1, 0.9), z), (sx * random.uniform(2, 6), -random.uniform(2, 7), random.uniform(-1, 4)), random.uniform(0.7, 1.4), grav=-12)
for k in range(5):
    tt = T_FAIL + 0.15 + 0.22 * k
    for _ in range(10):
        a = random.uniform(-pi, pi); SPARKS.emit(tt, random.uniform(0.3, 0.6), (1.2 * cos(a), -0.6, bit_z(tt) + random.uniform(0.2, 1.4)), (cos(a) * 7, -random.uniform(3, 8), random.uniform(0, 6)), random.uniform(0.9, 1.6), grav=-12)
for i in range(30):
    a = random.uniform(-pi, pi); BLOBS.emit(T_BREAK + random.uniform(0.0, 0.3), random.uniform(0.8, 1.4), (random.uniform(-1.5, 1.5), -random.uniform(0.2, 1.0), -D_CORE + 0.3),
                                           (cos(a) * random.uniform(1, 5), -random.uniform(0.5, 3.5), random.uniform(5, 10)), random.uniform(0.6, 1.6), grav=-14)
for i in range(16):
    a = random.uniform(-pi, pi); BLOBS.emit(B['gone'] + random.uniform(0.0, 0.15), random.uniform(0.6, 1.0), (random.uniform(-1, 1), -0.5, bit_z(B['gone']) + 1.0),
                                           (cos(a) * random.uniform(1, 4), -random.uniform(0.5, 3), random.uniform(2, 6)), random.uniform(0.4, 1.1), grav=-10)
for pool in (ROCKS, HOT, SPARKS, BLOBS): pool.assign()
TOOTH_T = [T_FAIL + 0.1 + 0.11 * k + random.uniform(0, 0.05) for k in range(14)]
PANEL_T = [T_FAIL + 0.55 + 0.2 * k for k in range(6)]
TOOTH_V = [Vector((cos(a) * random.uniform(2, 4), -random.uniform(1.5, 4), random.uniform(1, 4))) for _, a in TEETH]
PANEL_V = [Vector((c.x * 3.0, -random.uniform(3, 6), random.uniform(2, 5))) for _, c in PANELS]
EMBER_P = [Vector((random.uniform(-7, 7), random.uniform(-6, -1.5), random.uniform(-6, 9))) for _ in EMBERS]

# ---------------- fall: phase of the oscillation (z = A cos(phi)); time is compressed for the screen
A = R + CH * 0.5
T_J = B['jump'] + 0.18                         # leaves the rim
T_ARRIVE = T_FLYIN + 0.95
PH = pchip([T_J, B['center'] - 0.05, B['top'] + 0.35, T_SOUTH + 1.05, T_SOUTH + 1.55, T_WIDE + 1.85, B['forever'] + 0.55, T_ARRIVE],
           [0.0, 1.32, 1.86, pi, pi, 2 * pi, 3 * pi, 4 * pi])
def phase(t): return PH(t) if t >= T_J else 0.0
VMAX_KMH = 28400
def hop_height(t):         # little jump off the rim before the fall
    u = (t - (B['jump'] - 0.05)) / (T_J - B['jump'] + 0.05 + 0.25)
    return 0.12 * sin(pi * clamp(u)) if 0 < u < 1 else 0.0

# ================================================================== state(t)
def state(t):
    s = shot(t); F = FR[0]
    earth_on = s in ('hook', 'core', 'earth')
    VIS(EARTH, earth_on); VIS(DS, not earth_on)
    for o in ROCKS.objs + HOT.objs + SPARKS.objs + BLOBS.objs + DUSTS + EMBERS: VIS(o, False)
    for o, _ in TEETH: VIS(o, not earth_on)
    for o, _ in PANELS: VIS(o, not earth_on)
    # flowing interiors (frozen during the twist, reversed in the rewind)
    if t < T_RW0: flow = t
    elif t < T_RW1: flow = hook_time(t)
    elif t < T_TWIST: flow = t
    else: flow = T_TWIST + max(0.0, t - (B['friction'] + 0.4)) * 0.6
    for nt in FLOW_TREES: NODEV(nt, 'FLOW', flow)
    if earth_on: state_earth(t, s)
    else: state_drill(t, s)
def state_earth(t, s):
    PROP(SUN.data, 'energy', 1.6); PROP(RIM.data, 'energy', 1.6)
    tunnel = s != 'core'
    reveal = keys(t, [(T_TWIST + 0.7, 0.0), (B['tunnel'] + 0.55, 1.0)], eio) if s == 'earth' else 1.0
    if s == 'core': reveal = 0.0
    VIS(TUN, tunnel); VIS(FILL, reveal < 0.999)
    zedge = lerp(ZT, -ZT, reveal)
    SCL(FILL, (1, 1, max(0.0005, (zedge + ZT) / (2 * ZT))))
    VIS(SCAN, s == 'earth' and 0.0 < reveal < 0.999); LOC(SCAN, (0, 0, zedge))
    VIS(INNER, s == 'core')
    VIS(ATMO, s == 'earth' and (t < T_JUMP0 or t >= T_WIDE)); VIS(CLOUD, True)
    VIS(BALL, s == 'hook'); VIS(AG, False); VIS(AV, False); VIS(TRAIL, False); VIS(PATHO, False)
    # explorer
    if s == 'hook':
        th = hook_time(t)
        LOC(EX.root, (0.36, 0.05, R)); ROT(EX.root, (0, 0, radians(-80)))
        EX.pose(blendpose(POSES['hold'], POSES['stand'], ss(th, T_DROP - 0.05, T_DROP + 0.5)))
        LOC(BALL, (lerp(0.2, 0.0, ss(th, T_DROP, T_DROP + 0.5)), lerp(-0.02, 0.06, ss(th, T_DROP, T_DROP + 0.4)), ball_z(th)))
        p, tg = hook_cam(th); LOC(CAM, p); ROT(CAM, aim(p, tg, 0.05 * sin(th * 1.3))); camd.lens = 24
        return
    if s == 'core':
        LOC(EX.root, (0.36, 0.05, R)); EX.pose(POSES['stand'])
        u = (t - T_CORE) / (T_GONE0 - T_CORE)
        p = lv((1.7, -5.0, 1.1), (2.6, -9.0, 2.0), eo(u)); LOC(CAM, p); ROT(CAM, aim(p, (0.1, 0, -0.1), -0.06)); camd.lens = 26
        return
    # ------- twist / fall / payoff
    ph = phase(t); z = A * cos(ph) - CH * 0.5 if t >= T_J else R      # feet height when upright
    vz = 0.0
    if t >= T_J:
        dph = (phase(t + 0.01) - phase(t - 0.01)) / 0.02
        vz = -A * sin(ph) * dph
    spd = abs(sin(ph)) if t >= T_J else 0.0
    # explorer pose and orientation
    if t < B['jump'] - 0.05:
        LOC(EX.root, (0.36, 0.05, R)); ROT(EX.root, (0, 0, radians(-80)))
        EX.pose(blendpose(POSES['stand'], POSES['crouch'], ss(t, B['jump'] - 0.4, B['jump'] - 0.05)))
    elif t < T_J + 0.25:
        u = ss(t, B['jump'] - 0.05, T_J + 0.25)
        LOC(EX.root, (lerp(0.36, 0.0, u), 0.07, R + hop_height(t) + (z - R) * ss(t, T_J, T_J + 0.25)))
        ROT(EX.root, (0, 0, radians(-80) * (1 - u)))
        EX.pose(blendpose(POSES['crouch'], POSES['spread'], u))
    else:
        flip1 = ss(t, B['center'] + 0.25, B['pull'] + 0.4)                  # head-first after the centre
        tumble = 0.25 * sin(t * 1.7) * (1 - ss(t, T_SOUTH + 0.4, T_SOUTH + 0.9))
        rx = pi * flip1 + tumble
        if t >= T_WIDE: rx = pi * (1 - ss(phase(t), 3.5 * pi, 3.5 * pi + 0.5))   # upright for the last arrival
        P = POSES['spread']
        if B['center'] + 0.1 < t < B['pull'] + 0.6: P = blendpose(POSES['spread'], POSES['tuck'], sin(pi * ss(t, B['center'] + 0.1, B['pull'] + 0.6)))
        if T_SOUTH + 0.7 < t < T_SOUTH + 1.6: P = blendpose(POSES['spread'], POSES['wave'], sin(pi * ss(t, T_SOUTH + 0.7, T_SOUTH + 1.6)))
        com = A * cos(ph); x_hop = 0.0; yaw = 0.3 * sin(t * 0.9)
        root_z = com - CH * 0.5 * cos(rx)
        if t >= T_ARRIVE:                                                   # climbs out onto the rim (loops to frame 0)
            u = ss(t, T_ARRIVE, DUR - 0.25)
            x_hop = 0.36 * u; root_z = lerp(root_z, R, u) + 0.1 * sin(pi * u)
            P = blendpose(P, POSES['stand'], u); rx = 0.0; yaw = lerp(yaw, radians(-80), u)
        LOC(EX.root, (x_hop, 0.07, root_z)); ROT(EX.root, (rx, 0, yaw))
        EX.pose(P)
    PROP(EX.light.data, 'energy', 1.2 + 1.5 * spd)
    # arrows (close shots only)
    arrows = T_J + 0.3 < t < T_SOUTH + 0.6
    VIS(AG, arrows); VIS(AV, arrows)
    if arrows:
        zz = A * cos(ph)
        g = -zz / R
        LOC(AG, (-0.11, -0.1, zz)); ROT(AG, (0 if g > 0 else pi, 0, 0)); SCL(AG, (0.7, 0.7, max(0.001, abs(g) * 0.32)))
        LOC(AV, (0.11, -0.1, zz)); ROT(AV, (0 if vz > 0 else pi, 0, 0)); SCL(AV, (0.7, 0.7, max(0.001, spd * 0.32)))
    # trail
    trail_on = t > T_WIDE and t < T_ARRIVE - 0.05
    VIS(TRAIL, trail_on)
    if trail_on:
        PROP(TRAIL_CU, 'bevel_depth', 0.012 if t < T_WIDE else 0.07)
        lag = 0.55 if t < T_WIDE else 0.45
        zs = [A * cos(phase(max(T_J, t - lag * k / 6))) for k in range(7)]
        lo, hi = (min(zs) + ZT) / (2 * ZT), (max(zs) + ZT) / (2 * ZT)
        PROP(TRAIL_CU, 'bevel_factor_start', clamp(lo)); PROP(TRAIL_CU, 'bevel_factor_end', clamp(max(hi, lo + 0.002)))
    path_on = t > T_WIDE + 0.2 and t < T_ARRIVE - 0.2
    VIS(PATHO, path_on)
    if path_on:
        PROP(PATH_CU, 'bevel_factor_start', 0.0); PROP(PATH_CU, 'bevel_factor_end', ss(t, T_WIDE + 0.2, T_WIDE + 1.0))
    # camera
    zf = A * cos(ph) if t >= T_J else R + CH * 0.5
    if t < T_JUMP0:                                  # twist: freeze at the core, pull back to the whole planet
        u = (t - T_TWIST) / (T_JUMP0 - T_TWIST)
        k = eio(ss(t, T_TWIST + 0.35, B['tunnel'] + 0.2))
        dist = lerp(9.0, 31.0, k)
        p = Vector((lerp(2.6, 0.0, k), -dist, lerp(2.0, 0.6, k))); tg = Vector((0, 0, lerp(-0.1, 0.0, k)))
        p += Vector((0.0, 1.5 * ss(t, B['tunnel'] + 0.2, T_JUMP0), 0.0))
        orb = 0.42 * sm((t - B['tunnel']) / (T_JUMP0 - B['tunnel'])) * k        # slow orbit shows the 3D planet
        p = Matrix.Rotation(orb, 3, 'Z') @ p
        LOC(CAM, p); ROT(CAM, aim(p, tg)); camd.lens = lerp(26, 30, k)
    elif t < T_CEN0:                                 # jump + accelerating fall, tracked from beside
        u = ss(t, T_J - 0.1, T_J + 0.9)
        p0 = Vector((0.95, -1.35, R + 0.55)); t0 = Vector((0.1, 0.05, R + 0.12))
        lagz = 0.55 + 0.25 * spd
        lagz = 0.3 + 0.15 * spd
        pf = Vector((0.36, -0.7, zf + lagz)); tf = Vector((0.0, 0.07, zf - 0.2))
        p = p0.lerp(pf, u); tg = t0.lerp(tf, u)
        p += Vector((nz(t, 3, 9) * 0.02, nz(t, 4, 9) * 0.02, 0)) * spd
        LOC(CAM, p); ROT(CAM, aim(p, tg, 0.12 * sin(t * 0.8))); camd.lens = lerp(24, 17, spd)
    elif t < T_PAST:                                 # through the centre, slow-mo, side view
        p = Vector((0.62, -1.1, lerp(0.45, -0.35, ss(t, T_CEN0, T_PAST)))); tg = Vector((0.0, 0.05, zf * 0.75))
        LOC(CAM, p); ROT(CAM, aim(p, tg)); camd.lens = 24
    elif t < T_SOUTH:                                # decelerating toward the far side, camera below looking up
        p = Vector((0.32, -0.62, zf - 0.75 - 0.2 * spd)); tg = Vector((0.0, 0.07, zf + 0.1))
        LOC(CAM, p); ROT(CAM, aim(p, tg, pi + 0.15)); camd.lens = 22
    elif t < T_WIDE:                                 # south rim: pops out, hangs, waves
        p = Vector((0.85, -1.45, -R - 0.55)); tg = Vector((0.0, 0.05, -R - 0.05))
        LOC(CAM, p); ROT(CAM, aim(p, tg, pi)); camd.lens = 26
    elif t < T_FLYIN:                                # the whole planet: back and forth
        u = (t - T_WIDE) / (T_FLYIN - T_WIDE)
        p = Vector((lerp(0.6, 0.0, u), lerp(-30.5, -28.5, u), lerp(-1.0, 0.6, u))); tg = Vector((0, 0, 0.2))
        LOC(CAM, p); ROT(CAM, aim(p, tg)); camd.lens = 30
    else:                                            # fly into the opening framing (loops into frame 0)
        u = eio((t - T_FLYIN) / (DUR - 1 / FPS - T_FLYIN))
        pA = Vector((0.0, -28.5, 0.6)); tA = Vector((0, 0, 0.2)); pB, tB = HOOK_CAM0
        w_ = 1 - (1 - u) ** 2
        p = pA.lerp(pB, w_); p.y = pA.y * (pB.y / pA.y) ** u if u < 1 else pB.y
        p.y = min(p.y, -2.35) if u > 0.98 else p.y
        tg = tA.lerp(tB, u)
        LOC(CAM, p); ROT(CAM, aim(p, tg)); camd.lens = lerp(30, 24, u)

def state_drill(t, s):
    zb = bit_z(t); hz = heat(t); sq = squeeze(t)
    PROP(SUN.data, 'energy', {'dig': lerp(3.2, 2.0, ss(t, T_SLAM + 0.5, T_MANT)), 'mantle': 0.55}.get(s, 0.3)); PROP(RIM.data, 'energy', 0.0)
    LOC(DRILL, DS.location + Vector((0, 0, zb))) if False else LOC(DRILL, (0, 0, zb))
    wob = (0.012 * nz(t, 1, 3) + 0.03 * sq * nz(t, 2, 4)) if s != 'liquid' else 0.0
    sink = s in ('liquid', 'gone')
    tilt = 0.0
    if s == 'mantle' and t > T_FAIL: tilt = 0.12 * ss(t, T_FAIL + 0.3, T_BREAK)
    if sink: tilt = 0.22 + 0.25 * ss(t, T_BREAK, T_CORE) + 0.2 * ss(t, T_GONE0, B['gone'])
    ROT(DRILL, (wob, tilt + wob * 0.5, 0))
    squash = 1 - 0.08 * sq
    gone = ss(t, B['gone'] - 0.05, B['gone'] + 0.35) if s == 'gone' else 0.0
    SCL(DRILL, (squash * (1 - gone) + 1e-3, squash * (1 - gone) + 1e-3, (1 + 0.04 * sq) * (1 - gone) + 1e-3))
    VIS(DRILL, gone < 0.999)
    PROP(BODY, 'modifiers["Bend"].angle', -0.35 * ss(t, T_FAIL + 0.35, T_BREAK) - 0.3 * ss(t, T_BREAK, T_CORE) if t > T_FAIL else 0.0)
    ROT(CUTTER, (0, 0, -SPIN[FR[0]]))
    for nt in HEAT_TREES:
        if nt.nodes.get('HEAT'): NODEV(nt, 'HEAT', hz if nt != M['hotrock'].node_tree else 0.75)
    # drill string from the gantry block to the coupling
    top = zb + 7.6
    if top < 12.0:
        LOC(STRING, (0, 0, top)); SCL(STRING, (1, 1, max(0.01, 12.4 - top))); VIS(STRING, True)
    else: VIS(STRING, False)
    VIS(RIG, t < T_MANT)
    # shaft groove down to the bit; filler below it; walls close in under pressure
    depth = max(0.01, -zb + 0.2)
    VIS(SHAFT, True); SCL(SHAFT, (1 - 0.18 * sq, 1 - 0.18 * sq, min(depth, D_CORE)))
    for fo, sx in ((FACE_L, -1), (FACE_R, 1)): LOC(fo, (-sx * SW * 0.18 * sq, 0, 0))
    VIS(FILLD, zb > -D_CORE + 0.3)
    LOC(FILLD, (0, -0.003, min(0.0, zb + 0.2))); SCL(FILLD, (1 - 0.18 * sq, 1, max(0.001, D_CORE + min(0.0, zb + 0.2))))
    # teeth: on the cutter until they snap
    spin = SPIN[FR[0]]
    for i, (o, a) in enumerate(TEETH):
        aa = a - spin
        p_att = Vector((1.18 * cos(aa) * squash, 1.18 * sin(aa) * squash, zb + 0.05))
        if t < TOOTH_T[i] or s != 'mantle' and t < T_FAIL:
            LOC(o, (p_att.x, p_att.y, p_att.z)); ROT(o, (0.5 * cos(aa) * 0 + 0.0, 0.0, 0.0)); SCL(o, 1.0); VIS(o, s != 'gone' or gone < 0.5)
        else:
            u = t - TOOTH_T[i]; v = TOOTH_V[i]
            p = p_att + v * u + Vector((0, 0, -6 * u * u))
            LOC(o, p); ROT(o, (u * 9, u * 7, 0)); SCL(o, max(0.0, 1 - u / 1.4)); VIS(o, u < 1.4)
    for i, (o, c) in enumerate(PANELS):
        cw = Vector((c.x * squash, c.y * squash, zb + 4.2))
        if t < PANEL_T[i]:
            LOC(o, cw); ROT(o, (0, 0, 0)); SCL(o, (squash, squash, 1.0)); VIS(o, s not in ('liquid', 'gone'))
        else:
            u = t - PANEL_T[i]; v = PANEL_V[i]
            LOC(o, cw + v * u + Vector((0, 0, -7 * u * u))); ROT(o, (u * 4 * (1 if i % 2 else -1), u * 3, u * 2)); SCL(o, 1.0); VIS(o, u < 1.5 and s == 'mantle')
    # lights
    PROP(BITLIGHT.data, 'energy', 450 * hz * hz); LOC(BITLIGHT, (2.6, -2.4, zb - 0.6))
    PROP(LIQLIGHT, 'energy', 0.0 if s in ('dig', 'mantle') and zb > -D_CORE + 12 else 6000.0 * (0.4 + 0.6 * ss(zb, -D_CORE + 10, -D_CORE)))
    # pools
    ROCKS.apply(t); HOT.apply(t); SPARKS.apply(t, stretch=True); BLOBS.apply(t)
    for d, o in zip(DUST_EV, DUSTS):
        t0, p, sz = d; u = t - t0
        on = 0 <= u < 2.2 and s == 'dig'
        VIS(o, on)
        if on:
            LOC(o, DS.location + p + Vector((0, -0.6 * u, 0.9 * u))); SCL(o, sz * (0.4 + 0.9 * eo(u / 1.4)))
            NODEV(o.active_material.node_tree, 'FADE', 0.9 * ss(u, 0, 0.12) * (1 - ss(u, 0.6, 2.2)))
    for o in DUSTS[len(DUST_EV):]: VIS(o, False)
    emb = s in ('mantle', 'liquid', 'gone')
    for i, (o, p) in enumerate(zip(EMBERS, EMBER_P)):
        VIS(o, emb)
        if emb:
            q = Vector((p.x + 0.4 * sin(t * 0.7 + i), p.y, ((p.z + t * (0.8 + 0.05 * i)) % 15.0) - 6.0))
            LOC(o, DS.location + Vector((0, 0, zb)) + q); SCL(o, 0.6 + 0.6 * abs(sin(t * 3 + i)))
    # camera
    if s == 'dig':
        if t < T_SLAM + 0.55:
            u = ss(t, T_RW1, T_SLAM + 0.5)
            p = Vector((lerp(7.5, 6.2, u), lerp(-13.5, -11.0, u), lerp(2.6, 1.6, u))); tg = Vector((0.0, 0.0, lerp(2.8, 0.2, u)))
            shake = 0.18 * max(0.0, 1 - (t - T_SLAM) / 0.5) if t > T_SLAM else 0.0
        else:
            u = ss(t, T_SLAM + 0.55, T_MANT)
            p = Vector((lerp(5.5, 3.2, u), lerp(-10.5, -8.0, u), zb + lerp(3.5, 2.2, u))); tg = Vector((0.0, 0.0, zb + 1.2))
            shake = 0.03 + 0.04 * u
        p += Vector((nz(t, 5, 4.5), nz(t, 6, 4.5), nz(t, 7, 4.5))) * shake
        LOC(CAM, DS.location + p); ROT(CAM, aim(DS.location + p, DS.location + tg, 0.05 * sin(t))); camd.lens = 24
    elif s == 'mantle':
        if t < T_CLOSE:
            u = ss(t, T_MANT, T_CLOSE)
            p = Vector((lerp(-6.5, -4.2, u), lerp(-13.0, -10.5, u), zb + lerp(5.0, 3.0, u))); tg = Vector((0.0, 0, zb + 2.2))
            shake = 0.04
        elif t < T_FAIL:
            u = ss(t, T_CLOSE, T_FAIL)
            p = Vector((lerp(2.6, 3.4, u), lerp(-4.6, -5.6, u), zb + lerp(3.8, 4.2, u))); tg = Vector((0.0, 0, zb + 3.4))
            shake = 0.04 + 0.08 * sq
        else:
            u = ss(t, T_FAIL, T_BREAK)
            p = Vector((lerp(-3.6, -4.4, u), lerp(-7.8, -9.4, u), zb + lerp(1.8, 3.0, u))); tg = Vector((0.0, 0, zb + 1.6))
            shake = 0.14
        p += Vector((nz(t, 5, 4.5), nz(t, 6, 4.5), nz(t, 7, 4.5))) * shake
        LOC(CAM, DS.location + p); ROT(CAM, aim(DS.location + p, DS.location + tg, -0.06)); camd.lens = 24
    elif s == 'liquid':
        u = ss(t, T_BREAK, T_CORE)
        p = Vector((lerp(4.5, 3.4, u), lerp(-12.0, -10.5, u), lerp(-D_CORE + 3.5, -D_CORE - 1.5, u))); tg = Vector((0.0, 0, lerp(-D_CORE + 0.5, -D_CORE - 3.5, u)))
        shake = 0.25 * max(0.0, 1 - (t - T_BREAK) / 0.6) + 0.03
        p += Vector((nz(t, 5, 4.5), nz(t, 6, 4.5), nz(t, 7, 4.5))) * shake
        LOC(CAM, DS.location + p); ROT(CAM, aim(DS.location + p, DS.location + tg, 0.05)); camd.lens = 24
    else:  # gone
        u = ss(t, T_GONE0, T_TWIST)
        p = Vector((lerp(2.2, 2.6, u), lerp(-6.8, -7.6, u), zb + 3.0)); tg = Vector((0.0, 0, zb + 2.4))
        LOC(CAM, DS.location + p); ROT(CAM, aim(DS.location + p, DS.location + tg, 0.04)); camd.lens = 26
    LOC(CAMFILL, CAM.location - DS.location + Vector((0, 2.0, 1.5)))
    PROP(CAMFILL.data, 'energy', keys(t, [(T_RW1, 1200.0), (T_MANT - 0.5, 700.0), (T_MANT, 160.0), (T_BREAK, 90.0)]))

# ================================================================== labels, HUD, sound
label('IMAGINARY DRILL', B['first'] + 0.25, B['nothing'] + 0.35, xy=(0.5, 0.33), style='note', color='o')
label('Deepest real hole: 12 km', B['deeper'] - 0.35, B['hotter'] + 0.65, xy=(0.5, 0.33), style='tag', color='b')
label('MANTLE: solid rock', B['lava'] - 0.25, B['crushing'] + 0.2, xy=(0.5, 0.33), style='tag', color='r')
label('OUTER CORE: liquid iron', B['liquid'] - 0.15, T_CORE + 0.05, xy=(0.5, 0.33), style='tag', color='o')
label('INNER CORE: solid', B['solid2'] - 0.1, B['suns'] - 0.1, anchor=lambda t: Vector((0.0, -0.4, 1.4)), style='tag', color='y')
label('about 5,200 °C, like the Sun\'s surface', B['suns'] - 0.1, T_GONE0 - 0.02, xy=(0.5, 0.33), style='tag', color='y')
label('IDEALISED: no air, no friction', B['air'] - 0.2, DUR, xy=(0.5, 0.25), style='note', color='b')
label('net pull = 0', B['pull'] - 0.6, B['top'] - 0.05, xy=(0.5, 0.36), style='tag', color='m')
label('top speed', B['top'] - 0.05, T_PAST + 0.2, xy=(0.5, 0.36), style='tag', color='b')
label('gravity', T_J + 0.45, B['center'] - 0.4, xy=(0.27, 0.42), style='tag', color='m')
label('speed', T_J + 0.45, B['center'] - 0.4, xy=(0.73, 0.42), style='tag', color='b')
label('one trip: about 42 min', B['without'] - 0.2, T_FLYIN + 0.1, xy=(0.5, 0.33), style='tag', color='b')

KM = [(0, 0), (30, 35), (D_CORE, 2890), (D_CORE + 20, 3500)]
TEMP = [(0, 15), (12, 190), (35, 600), (660, 1900), (2890, 3700), (3500, 4300)]
def interp(ks, x):
    for (x0, y0), (x1, y1) in zip(ks, ks[1:]):
        if x <= x1: return y0 + (y1 - y0) * clamp((x - x0) / (x1 - x0))
    return ks[-1][1]
def hud(t):
    s = shot(t); h = {}
    if s in ('dig', 'mantle', 'liquid') and t > T_SLAM:
        u = max(0.0, -bit_z(t)); km = interp(KM, u)
        h['depth'] = round(km, 1); h['temp'] = round(interp(TEMP, km))
    if s == 'earth' and T_J <= t < T_WIDE:
        h['speed'] = round(VMAX_KMH * abs(sin(phase(t))))
    if s == 'earth' and t >= T_WIDE - 0.2:
        h['osc'] = round(cos(phase(t)), 4)
    if T_RW0 <= t < T_RW1: h['rewind'] = round((t - T_RW0) / (T_RW1 - T_RW0), 3)
    if T_TWIST <= t < T_TWIST + 0.9: h['freeze'] = round((t - T_TWIST) / 0.9, 3)
    if B['gone'] - 0.05 <= t < B['gone'] + 0.3: h['flash'] = round((t - B['gone'] + 0.05) / 0.35, 3)
    if T_BREAK - 0.02 <= t < T_BREAK + 0.3: h['flash'] = round((t - T_BREAK + 0.02) / 0.32, 3)
    return h

# sound cues
ev(0.0, 'drone_hook', 0.8); ev(T_DROP, 'ball_drop', 0.7); ev(T_DROP + 0.25, 'fall_whoosh:2.8', 0.9)
ev(T_RW0, 'rewind', 0.9)
ev(T_RW1, 'impact_low', 0.5)
ev(B['first'] + 0.45, 'motor_start', 0.7)
ev(T_SLAM, 'impact_big', 1.0); ev(T_SLAM + 0.05, 'debris:1.4', 0.9); ev(T_SLAM - 0.25, 'whoosh', 0.6)
ev(T_SLAM + 0.55, 'whoosh', 0.45)
ev(B['hotter'] - 0.2, 'riser:1.4', 0.4)
ev(T_MANT, 'whoosh_low', 0.6); ev(T_MANT, 'impact_low', 0.7)
ev(T_CLOSE, 'whoosh', 0.45)
ev(B['crushing'], 'metal_groan:1.6', 0.9); ev(B['crushing'] + 0.1, 'crunch', 0.7)
for k, tt in enumerate(TOOTH_T[::2]): ev(tt, f'impactMetal_heavy_00{k % 5}', 0.5)
for k, tt in enumerate(PANEL_T): ev(tt, f'impactMetal_medium_00{k % 5}', 0.7); ev(tt + 0.05, 'metal_snap', 0.6)
ev(T_FAIL, 'alarm:1.8', 0.35)
ev(T_BREAK - 0.35, 'whoosh_low', 0.6); ev(T_BREAK, 'core_boom', 1.0); ev(T_BREAK + 0.05, 'splash', 0.9)
ev(T_CORE - 0.25, 'whoosh', 0.6); ev(T_CORE, 'shimmer:3.0', 0.6)
ev(T_GONE0 - 0.15, 'whoosh', 0.45); ev(B['gone'], 'fizzle', 1.0); ev(B['gone'], 'impact_low', 0.7)
ev(T_TWIST, 'freeze_drop', 1.0); ev(T_TWIST + 0.85, 'whoosh_big', 1.0); ev(B['tunnel'] + 0.1, 'scan:0.9', 0.5)
ev(B['jump'] - 0.1, 'jump', 0.7); ev(B['center'] - 0.05, 'pass_whoosh', 0.9); ev(B['center'] + 0.2, 'slowmo', 0.6)
ev(T_SOUTH + 1.05, 'pop_out', 0.6); ev(T_SOUTH + 1.4, 'chime', 0.4)
ev(T_WIDE - 0.1, 'whoosh_big', 0.6); ev(B['forever'], 'resolve', 0.7); ev(T_FLYIN, 'whoosh_big', 0.7)
ev(T_ARRIVE, 'pop_out', 0.4)

def curves(t):
    s = shot(t); c = {}
    c['drill'] = (clamp(spin_speed(t) / 3.2) if s in ('dig', 'mantle') else 0.0)
    c['rumble'] = ({'dig': 0.25 + 0.4 * ss(t, B['deeper'], T_MANT), 'mantle': 0.75 + 0.25 * ss(t, T_CLOSE, T_BREAK), 'liquid': 1.0, 'gone': 0.7}.get(s, 0.0))
    c['heat'] = ({'mantle': 0.55 + 0.45 * ss(t, T_CLOSE, T_BREAK), 'liquid': 1.0, 'gone': 0.9, 'dig': 0.3 * ss(t, B['hotter'] - 0.5, T_MANT)}.get(s, 0.0))
    c['liquid'] = 1.0 if s in ('liquid', 'gone', 'core') else 0.0
    c['wind'] = (abs(sin(phase(t))) * (1.0 if t < T_WIDE else 0.35) if s == 'earth' and t >= T_J else 0.0)
    if s == 'hook': c['wind'] = 0.4 * ss(t, 0.8, 2.5) if t < T_RW0 else 0.0
    c['music'] = 0.0 if T_TWIST <= t < T_TWIST + 0.8 else 1.0
    return c

# ================================================================== bake
def bake():
    t0 = time.time()
    for f in range(NF):
        FR[0] = f; t = f / FPS
        prev = shot((f - 1) / FPS) if f else None
        state(t)
        bpy.context.view_layer.update()
        for lb in LABELS:
            if lb['t0'] <= t < lb['t1']:
                if lb['anchor']:
                    p = world_to_camera_view(sc, CAM, lb['anchor'](t))
                    if p.z > 0: lb['pts'][f] = (round(p.x, 4), round(1 - p.y, 4))
                else: lb['pts'][f] = lb['xy']
        HUD[f] = hud(t)
        for k, v in curves(t).items(): CURVES[k].append(round(v, 4))
    print(f'state loop {time.time() - t0:.1f}s')
    write_fcurves()
for f in range(1, NF):
    t, tp = f / FPS, (f - 1) / FPS
    if shot(t) != shot(tp) or any(tp < c <= t for c in (T_RW1, T_SLAM + 0.55, T_CLOSE, T_FAIL, T_JUMP0, T_CEN0, T_PAST, T_SOUTH, T_WIDE, T_FLYIN)):
        CUTS.append(f)
bake()
json.dump(dict(fps=FPS, nf=NF, w=sc.render.resolution_x, h=sc.render.resolution_y, cuts=CUTS, hud={str(k): v for k, v in HUD.items() if v},
               labels=[dict(text=l['text'], style=l['style'], color=l['color'], t0=l['t0'], t1=l['t1'], pts=l['pts']) for l in LABELS]),
          open(os.path.join(OUT, 'labels.json'), 'w'))
json.dump(dict(events=sorted(EVENTS, key=lambda e: e['t']), beats=B, dur=DUR, fps=FPS, curves=CURVES, cuts=[c / FPS for c in CUTS]),
          open(os.path.join(OUT, 'events.json'), 'w'), indent=1)
print('cuts at', [round(c / FPS, 2) for c in CUTS])

if arg('--save'):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(arg('--save')), compress=True)
    print('saved', arg('--save'))
if arg('--stills'):
    os.makedirs(OUT, exist_ok=True)
    for ts in arg('--stills').split(','):
        f = int(round(float(ts) * FPS)); sc.frame_set(f)
        sc.render.filepath = os.path.join(OUT, f'still_{float(ts):06.2f}.png')
        bpy.ops.render.render(write_still=True)
    print('STILLS_DONE')
if arg('--frames'):
    a, b = (int(x) for x in arg('--frames').split(':'))
    sc.frame_start, sc.frame_end = a, b
    sc.render.filepath = os.path.join(OUT, 'frames', 'f_#####')
    t0 = time.time(); bpy.ops.render.render(animation=True)
    print(f'FRAMES_DONE {a}:{b} in {time.time() - t0:.0f}s')
