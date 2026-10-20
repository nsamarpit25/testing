# 20 Canary Releases: "The Hundred". A dark polished-stone stage under one soft overhead light. A hundred giant graphite
# phones stand in a staggered 10x10 field; each is one user. Their screens show the Shop app: blue v1, canary-yellow v2,
# or a red "App stopped" crash. A brushed-aluminium ROLLOUT dial (0 / 1 / 5 / 25 / 100) and a HEALTH pillar
# (CRASHES / ERRORS / SLOW) stand in front. A dark restaurant with silver cloches sits at X 60. Timed to voice/words.json.
# usage: blender -b -P videos/20-canary-releases/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 32] [--stills 3,20] [--range a,b] [--skip]
import bpy, bmesh, json, math, os, random, re, sys, wave
from mathutils import Vector, Matrix, Euler, Quaternion
from bpy_extras import anim_utils
import faulthandler, time; faulthandler.dump_traceback_later(45, repeat=True); T0 = time.time()
def tick(m): print(f'[t+{time.time() - T0:6.1f}s] {m}', flush=True)

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
RES, FPS, SAMPLES = int(opt('--res', 480)), int(opt('--fps', 24)), int(opt('--samples', 32))
STILLS = [float(x) for x in opt('--stills', '').split(',') if x]
D = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f'{D}/voice/timings.json'))
WORDS = json.load(open(f'{D}/voice/words.json'))
with wave.open(f'{D}/voice/voice.wav') as wv: VOICE = wv.getnframes() / wv.getframerate()
LS = {(x['li'], x['pi']): x['start'] for x in T}
L = lambda li, pi=0: LS[(li, pi)]
END = min(VOICE, T[-1]['end'] + 1.8)
F = lambda t: 1 + round(t * FPS)
NF = F(END)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
def W(tok, after=0.0):
    for w, s, e in WORDS:
        if s >= after - 1e-6 and norm(w) == tok: return s
    raise KeyError(tok)
PI = math.pi; rad = math.radians; FR = 1.0 / FPS

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection

def hx(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sm(u): u = clamp(u); return u * u * (3 - 2 * u)
def back(s): return lambda u: 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2
EZ = dict(lin=lambda u: u, in2=lambda u: u * u, in3=lambda u: u ** 3, out=lambda u: 1 - (1 - u) ** 3, out2=lambda u: 1 - (1 - u) ** 2,
          io=sm, back=back(1.2), back2=back(0.6), back3=back(2.0))

# ---------- keyframe registry: segments per (owner, path), resolved and written once at the end ----------
SEG = {}; _ORD = [0]
def _v(v): return tuple(float(x) for x in v) if hasattr(v, '__len__') else float(v)
def _tr(owner, path):
    k = (owner.as_pointer(), path)
    if k not in SEG: SEG[k] = [owner, path, _v(getattr(owner, path)), []]
    return SEG[k][3]
def _add(owner, path, seg): _ORD[0] += 1; _tr(owner, path).append(seg + (_ORD[0],))
def tw(owner, path, t, dur, val, ez='out'):
    """tween from whatever the value is at t to val over dur seconds."""
    f0 = F(t); f1 = max(f0, F(t + dur)); _add(owner, path, ('tw', f0, f1, _v(val), ez))
def st(owner, path, t, val): _add(owner, path, ('set', F(t), F(t), _v(val), None))
def fn(owner, path, t0, t1, f): _add(owner, path, ('fn', F(t0), F(t1), f, None))
def lerpv(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * u
def _resolve(v0, segs):
    keys = {}
    def at(f):
        if not keys: return v0
        lo = [x for x in keys if x <= f]
        if not lo: return v0
        a = max(lo); hi = [x for x in keys if x > f]
        if not hi: return keys[a]
        b = min(hi); return lerpv(keys[a], keys[b], (f - a) / (b - a))
    def drop(f0):
        for x in [x for x in keys if x >= f0]: del keys[x]
    for kind, f0, f1, val, ez, _ in sorted(segs, key=lambda s: (s[1], s[5])):
        if kind == 'fn':
            cur = at(f0 - 1); drop(f0 - 1); keys[f0 - 1] = cur
            for f in range(f0, f1 + 1): keys[f] = _v(val((f - 1) / FPS))
        elif kind == 'set' or f1 == f0:  # jump between sub-frames f0-0.52 / f0-0.48 so motion blur never smears it
            cur = at(f0 - 1); drop(f0 - 1); keys[f0 - 1] = cur; keys[f0 - 0.52] = cur; keys[f0 - 0.48] = val; keys[f0] = val
        else:
            cur = at(f0); drop(f0); keys[f0] = cur
            e = EZ[ez] if isinstance(ez, str) else ez
            for f in range(f0 + 1, f1 + 1): keys[f] = lerpv(cur, val, e((f - f0) / (f1 - f0)))
    fs = sorted(keys); out = [fs[0]] if fs else []
    for i in range(1, len(fs) - 1):  # drop keys in the middle of a constant run
        if not (keys[fs[i - 1]] == keys[fs[i]] == keys[fs[i + 1]]): out.append(fs[i])
    if len(fs) > 1: out.append(fs[-1])
    return [(f, keys[f]) for f in out]
def write_tracks():
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for owner, path, v0, segs in SEG.values():
        ks = _resolve(v0, segs)
        if not ks: continue
        setattr(owner, path, ks[0][1])
        if len(ks) == 1 or all(v == ks[0][1] for _, v in ks): continue
        owner.keyframe_insert(path, frame=ks[0][0])
        idd = owner.id_data
        dp = path if isinstance(owner, bpy.types.ID) else owner.path_from_id(path)
        ad = idd.animation_data
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        vec = isinstance(ks[0][1], tuple)
        for fc in cb.fcurves:
            if fc.data_path != dp: continue
            i = fc.array_index
            co = [c for f, v in ks for c in (float(f), v[i] if vec else v)]
            kp = fc.keyframe_points; kp.clear(); kp.add(len(ks)); kp.foreach_set('co', co)
            for p in kp: p.interpolation = 'LINEAR'
            fc.update()

# ---------- materials ----------
def principled(m): return m.node_tree.nodes.get('Principled BSDF')
def sock(m, name): return principled(m).inputs[name]
def mat(name, h, rough=0.5, metal=0.0, emit=0.0, eh=None):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = principled(m)
    b.inputs['Base Color'].default_value = hx(h); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['Emission Color'].default_value = hx(eh or h); b.inputs['Emission Strength'].default_value = emit
    return m
def nn(m, kind, **kw):
    n = m.node_tree.nodes.new(kind)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def ln(m, a, b): m.node_tree.links.new(a, b)
def emat(name, h, strength):  # pure emission (glow planes, sky)
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; nt.nodes.remove(principled(m)); out = nt.nodes['Material Output']
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = hx(h); e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs[0], out.inputs['Surface']); return m, e.inputs['Strength']
def rough_noise(m, lo, hi, scale=6.0):
    nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale
    mr = nn(m, 'ShaderNodeMapRange'); mr.inputs['To Min'].default_value = lo; mr.inputs['To Max'].default_value = hi
    ln(m, nz.outputs['Fac'], mr.inputs['Value']); ln(m, mr.outputs['Result'], sock(m, 'Roughness'))
def bump(m, scale, strength, voronoi=False):
    if voronoi: tx = nn(m, 'ShaderNodeTexVoronoi'); tx.inputs['Scale'].default_value = scale; o = tx.outputs['Distance']
    else: tx = nn(m, 'ShaderNodeTexNoise'); tx.inputs['Scale'].default_value = scale; o = tx.outputs['Fac']
    bp = nn(m, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = strength
    ln(m, o, bp.inputs['Height']); ln(m, bp.outputs['Normal'], sock(m, 'Normal'))

# ---------- mesh builder: boxes / cylinders / spheres / tori merged into one mesh per object ----------
def _rm(rot):
    if isinstance(rot, Matrix): return rot.to_4x4() if len(rot) == 3 else rot
    return Euler(rot).to_matrix().to_4x4()
class MB:
    def __init__(s): s.bm = bmesh.new(); s.mats = []
    def _fin(s, verts, m):
        if m not in s.mats: s.mats.append(m)
        i = s.mats.index(m)
        for f in {f for v in verts for f in v.link_faces}: f.material_index = i
        return s
    def box(s, c, size, m, rot=(0, 0, 0)):
        r = bmesh.ops.create_cube(s.bm, size=1.0)
        mx = Matrix.Translation(Vector(c)) @ _rm(rot) @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
        bmesh.ops.transform(s.bm, matrix=mx, verts=r['verts']); return s._fin(r['verts'], m)
    def cyl(s, c, r, h, m, rot=(0, 0, 0), seg=24, r2=None, caps=True):
        mx = Matrix.Translation(Vector(c)) @ _rm(rot)
        res = bmesh.ops.create_cone(s.bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=mx)
        return s._fin(res['verts'], m)
    def stamp(s, tp, c, m, scale=(1, 1, 1)):  # copy a template without bmesh.ops (each op touches the whole mesh)
        bm = s.bm; vs = [bm.verts.new((c[0] + x * scale[0], c[1] + y * scale[1], c[2] + z * scale[2])) for x, y, z in tp[0]]
        if m not in s.mats: s.mats.append(m)
        i = s.mats.index(m)
        for f in tp[1]: bm.faces.new([vs[k] for k in f]).material_index = i
        return s
    def sph(s, c, r, m, seg=16, ring=8, scale=(1, 1, 1)):
        mx = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
        res = bmesh.ops.create_uvsphere(s.bm, u_segments=seg, v_segments=ring, radius=r, matrix=mx); return s._fin(res['verts'], m)
    def tor(s, c, R, r, m, rot=(0, 0, 0), seg=48, rs=10, arc=2 * PI):
        mx = Matrix.Translation(Vector(c)) @ _rm(rot); bm = s.bm; closed = arc >= 2 * PI - 1e-6
        n = seg if closed else seg + 1; rings = []
        for i in range(n):
            a = arc * i / seg
            rings.append([bm.verts.new(mx @ Vector(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
                          for b in (2 * PI * j / rs for j in range(rs))])
        for i in range(seg):
            A, B = rings[i], rings[(i + 1) % n]
            for j in range(rs): bm.faces.new((A[j], B[j], B[(j + 1) % rs], A[(j + 1) % rs]))
        return s._fin([v for rg in rings for v in rg], m)
    def ann(s, c, r0, r1, h, m, seg=64):  # flat ring (annulus) lying in XY
        bm = s.bm; c = Vector(c); vs = []
        for z in (0, h):
            vs.append([bm.verts.new(c + Vector((r * math.cos(2 * PI * i / seg), r * math.sin(2 * PI * i / seg), z))) for r in (r0, r1) for i in range(seg)])
        for i in range(seg):
            j = (i + 1) % seg
            bi, bo, ti, to = vs[0][i], vs[0][seg + i], vs[1][i], vs[1][seg + i]
            bj, bo2, tj, to2 = vs[0][j], vs[0][seg + j], vs[1][j], vs[1][seg + j]
            bm.faces.new((ti, to, to2, tj)); bm.faces.new((bi, bj, bo2, bo)); bm.faces.new((bo, bo2, to2, to)); bm.faces.new((bi, ti, tj, bj))
        return s._fin(vs[0] + vs[1], m)
    def prism(s, pts, depth, m, c=(0, 0, 0), rot=(0, 0, 0)):  # CCW polygon in local XY, extruded along local Z
        mx = Matrix.Translation(Vector(c)) @ _rm(rot); bm = s.bm; n = len(pts)
        bot = [bm.verts.new(mx @ Vector((x, y, -depth / 2))) for x, y in pts]; top = [bm.verts.new(mx @ Vector((x, y, depth / 2))) for x, y in pts]
        bm.faces.new(bot[::-1]); bm.faces.new(top)
        for i in range(n): bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
        return s._fin(bot + top, m)
    def tet(s, c, r, m):
        bm = s.bm; c = Vector(c)
        vs = [bm.verts.new(c + Vector(p) * r) for p in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]
        for a, b, d in ((0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)): bm.faces.new((vs[a], vs[b], vs[d]))
        return s._fin(vs, m)
    def ob(s, name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), bev=0.0, smooth=True, shadow=True):
        me = bpy.data.meshes.new(name); s.bm.to_mesh(me); s.bm.free()
        for m in s.mats: me.materials.append(m)
        o = bpy.data.objects.new(name, me); col.objects.link(o)
        if parent: o.parent = parent
        o.location = loc; o.rotation_euler = rot
        if smooth: me.shade_smooth()
        if bev:
            bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bev; bv.segments = 3; bv.limit_method = 'ANGLE'; bv.angle_limit = rad(30); bv.harden_normals = True
        elif smooth:
            try: me.set_sharp_from_angle(angle=rad(35))
            except Exception: pass
        if not shadow: o.visible_shadow = False
        return o
def empty(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); col.objects.link(o)
    if parent: o.parent = parent
    o.location = loc; o.rotation_euler = rot; return o
def box(name, parent, loc, size, m, bev=0.0, rot=(0, 0, 0)): return MB().box((0, 0, 0), size, m).ob(name, parent, loc, rot, bev)
def tube(name, pts, r, m, parent=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp_, p in zip(sp.bezier_points, pts): bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu); col.objects.link(o); cu.materials.append(m)
    if parent: o.parent = parent
    return o
def yaw_to(dx, dy): return math.atan2(dx, -dy)  # yaw that turns local -Y toward (dx, dy)
def frame_along(d):
    """rotation whose X axis runs along d and whose Z axis is as close to world up as possible."""
    X = Vector(d).normalized(); Z = Vector((0, 0, 1)) - X * X.z; Z.normalize(); Y = Z.cross(X)
    return Matrix((X, Y, Z)).transposed()

# ---------- text ----------
FD = f'{D}/fonts'
FONTS = dict(serif='InstrumentSerif-Regular.woff2', serif_i='InstrumentSerif-Italic.woff2', din='DINAlternate-Bold.ttf', dinc='DINCondensed-Bold.ttf',
             mono='JetBrainsMono-Medium.ttf', inter_b='Inter-Bold.ttf', inter_sb='Inter-SemiBold.ttf')
FONTS = {k: bpy.data.fonts.load(f'{FD}/{v}') for k, v in FONTS.items()}
CAPR = dict(serif=0.66, serif_i=0.66, din=0.71, dinc=0.71, mono=0.73, inter_b=0.73, inter_sb=0.73)
TXT = []  # (object, max width) fitted + vertically centred after one depsgraph update
def txt(name, body, font, cap, m, parent=None, loc=(0, 0, 0), rot=(PI / 2, 0, 0), ext=0.0006, space=1.0, ax='CENTER', fit=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONTS[font]; cu.size = cap / CAPR[font]
    cu.space_character = space; cu.align_x = ax; cu.align_y = 'CENTER'; cu.extrude = ext
    o = bpy.data.objects.new(name, cu); col.objects.link(o); cu.materials.append(m)
    if parent: o.parent = parent
    o.location = loc; o.rotation_euler = rot; TXT.append((o, fit)); return o
def fit_texts():
    bpy.context.view_layer.update()
    for o, fit in TXT:
        bb = [Vector(c) for c in o.bound_box]
        if not bb: continue
        w = max(v.x for v in bb) - min(v.x for v in bb); cy = (max(v.y for v in bb) + min(v.y for v in bb)) / 2
        s = min(1.0, fit / w) if fit and w > 1e-6 else 1.0
        o.scale = (s, s, s)
        o.location = Vector(o.location) + o.rotation_euler.to_matrix() @ Vector((0, -cy * s, 0))
def face_txt(name, body, font, cap, m, parent, x, fy, z, ext=0.0006, **kw):
    """printed text on a -Y facing surface at y = fy."""
    return txt(name, body, font, cap, m, parent, (x, fy - 0.0008 - ext, z), (PI / 2, 0, 0), ext, **kw)

random.seed(20)
def cut_frame(t0): return 1 + math.ceil(t0 * FPS - 1e-9)
CT = lambda t: (cut_frame(t) - 1) / FPS   # a time whose frame is exactly the cut frame of a shot starting at t

# ---------- word times ----------
tSHIP, tCRASH0, t99 = W('ship'), W('crashes'), L(0, 2)
tUSUAL, tPUSH, tEVERY = L(1, 0), W('push'), L(1, 1)
tSPOT, tONEBUG, tBUG, tEVERY2, tCRASHES = L(2, 0), L(3, 0), W('bug'), W('every', 10), W('crashes', 10)
tTESTER, tBYTIME, tUNDO = L(3, 1), L(3, 2), W('undo')
tFIX, tSEND, t1, tUSERS = L(4, 0), L(4, 1), W('1'), W('users', 19)
tWATCH, tCRW, tERR, tSLOW, tIF, tSPIKE, tROLLS = L(5, 0), W('crashes', 21), W('errors'), W('slow'), L(5, 1), W('spike'), W('rolls')
tGOOD, t5, t25, tALL = L(6, 0), W('5', 27), W('25', 28), W('everyone', 29)
tLIKE, tDISH, tSERVE, tONE_T, tFIRST, tIF2, tCOMES, tREST = L(7, 0), W('dish'), L(7, 1), W('one', 31.5), W('first', 32), W('if', 32.5), W('comes'), W('the', 33.5)
tBUG2, tSHIP2, tHITS, tTWO = L(8, 0), W('ship', 36), W('hits'), W('two', 38)
tFEW0, tFEW, tALL3 = L(9, 0), W('few'), W('everyone', 40.5)
tTHATS, tARGO, tAWS, tCTA = L(10, 0), W('argo'), W('aws'), L(11, 0)

M = {}
M['floor'] = mat('floor', '#0B0D10', 0.16); rough_noise(M['floor'], 0.10, 0.24, 0.35)
m = M['floor']; tc = nn(m, 'ShaderNodeTexCoord'); nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.08; nz.inputs['Detail'].default_value = 6.0
ln(m, tc.outputs['Object'], nz.inputs['Vector'])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx('#08090C'); cr.color_ramp.elements[1].color = hx('#13161B')
ln(m, nz.outputs['Fac'], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
M['ti'] = mat('ti', '#6A6D73', 0.30, 1.0); rough_noise(M['ti'], 0.26, 0.34, 40.0)
M['ti_dark'] = mat('ti_dark', '#3A3C41', 0.35, 1.0)
M['glass'] = mat('glass', '#030405', 0.05)
M['alu'] = mat('alu', '#CDD0D5', 0.26, 1.0); bump(M['alu'], 900, 0.015)
M['alu_satin'] = mat('alu_satin', '#B9BCC2', 0.38, 1.0); bump(M['alu_satin'], 700, 0.02)
M['ped'] = mat('ped', '#15171B', 0.42); rough_noise(M['ped'], 0.36, 0.48, 9.0)
M['ring'] = mat('ring', '#0D0E11', 0.30)
M['label'] = mat('label', '#F1F3F6', 0.5, emit=0.9, eh='#F1F3F6')
M['label_dim'] = mat('label_dim', '#8B9099', 0.5, emit=0.35, eh='#9AA0AA')
M['engrave'] = mat('engrave', '#1A1C20', 0.55)
M['tick'] = mat('tick', '#5C6068', 0.4, emit=0.25, eh='#8A9099')
M['yellow_e'] = mat('yellow_e', '#FFC21A', 0.4, emit=4.0, eh='#FFC21A')
M['red_e'] = mat('red_e', '#FF453A', 0.4, emit=3.0, eh='#FF453A')

def mth(m, op, a, b=None, c=None, clamp_=False):
    n = nn(m, 'ShaderNodeMath', operation=op, use_clamp=clamp_)
    for i, x in enumerate((a, b, c)):
        if x is None: continue
        if isinstance(x, (int, float)): n.inputs[i].default_value = x
        else: ln(m, x, n.inputs[i])
    return n.outputs[0]
def mixc(m, fac, a, b):
    mx = nn(m, 'ShaderNodeMix', data_type='RGBA')
    for i, x in ((0, fac), (6, a), (7, b)):
        if isinstance(x, (int, float)): mx.inputs[i].default_value = x
        elif isinstance(x, tuple): mx.inputs[i].default_value = x
        else: ln(m, x, mx.inputs[i])
    return mx.outputs[2]

# ---------- phone screen: v1 -> v2 wipe from the bottom with a bright install line, crash overlay ----------
SW, SH_, SZ = 0.72, 1.54, 0.80
IMG = {k: bpy.data.images.load(f'{D}/tex/{k}.png') for k in ('v1', 'v2', 'crash')}
def screen_mat(i):
    m = mat(f'scr{i}', '#000000', 0.07); b = principled(m)
    tc = nn(m, 'ShaderNodeTexCoord'); sp = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], sp.inputs[0])
    u = mth(m, 'MULTIPLY_ADD', sp.outputs['X'], 1 / SW, 0.5); v = mth(m, 'MULTIPLY_ADD', sp.outputs['Z'], 1 / SH_, 0.5 - SZ / SH_)
    uv = nn(m, 'ShaderNodeCombineXYZ'); ln(m, u, uv.inputs[0]); ln(m, v, uv.inputs[1])
    tx = {}
    for k, im in IMG.items():
        n = nn(m, 'ShaderNodeTexImage'); n.image = im; n.extension = 'CLIP'; n.interpolation = 'Linear'; ln(m, uv.outputs[0], n.inputs['Vector']); tx[k] = n.outputs['Color']
    ver = nn(m, 'ShaderNodeValue'); ver.outputs[0].default_value = 0.0
    crash = nn(m, 'ShaderNodeValue'); crash.outputs[0].default_value = 0.0
    lum = nn(m, 'ShaderNodeValue'); lum.outputs[0].default_value = 1.5
    g = mth(m, 'SUBTRACT', mth(m, 'MULTIPLY', ver.outputs[0], 1.15), v)
    f = mth(m, 'MULTIPLY', g, 12.0, clamp_=True)
    act = mth(m, 'MULTIPLY', mth(m, 'MULTIPLY', ver.outputs[0], mth(m, 'SUBTRACT', 1.0, ver.outputs[0])), 6.0, clamp_=True)
    band = mth(m, 'MULTIPLY', mth(m, 'SUBTRACT', 1.0, mth(m, 'MULTIPLY', mth(m, 'ABSOLUTE', mth(m, 'SUBTRACT', g, 0.03)), 45.0), clamp_=True), act)
    c = mixc(m, f, tx['v1'], tx['v2']); c = mixc(m, band, c, hx('#FFFFFF')); c = mixc(m, crash.outputs[0], c, tx['crash'])
    ln(m, c, b.inputs['Emission Color']); ln(m, lum.outputs[0], b.inputs['Emission Strength'])
    return m, ver.outputs[0], crash.outputs[0], lum.outputs[0]

def rrect(w, h, r, n=8):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = rad(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
UPR = (PI / 2, 0, 0)  # polygon y -> world z, extrusion -> -y
def _mesh(mb, name):
    me = bpy.data.meshes.new(name); mb.bm.to_mesh(me); mb.bm.free()
    for m_ in mb.mats: me.materials.append(m_)
    me.shade_smooth()
    try: me.set_sharp_from_angle(angle=rad(35))
    except Exception: pass
    return me
BODY_ME = _mesh(MB().prism(rrect(0.78, 1.60, 0.12), 0.075, M['ti'], c=(0, 0, 0.80), rot=UPR), 'body')
FRONT_ME = _mesh(MB().prism(rrect(0.716, 1.536, 0.086), 0.004, M['glass'], c=(0, -0.0395, SZ), rot=UPR)  # placeholder slot 0 = screen
                 .prism(rrect(0.15, 0.044, 0.022, 6), 0.002, M['glass'], c=(0, -0.0425, SZ + 0.705), rot=UPR)
                 .box((0.392, 0, 1.18), (0.012, 0.03, 0.17), M['ti_dark']).box((-0.392, 0, 1.25), (0.012, 0.03, 0.09), M['ti_dark'])
                 .box((-0.392, 0, 1.12), (0.012, 0.03, 0.09), M['ti_dark']), 'front')
# slot 0 of FRONT_ME is the glass of the pill too, so give the screen its own first slot
FRONT_ME.materials.clear()
_scr_dummy = mat('scr_dummy', '#000000', 0.07)
FRONT_ME.materials.append(_scr_dummy); FRONT_ME.materials.append(M['glass']); FRONT_ME.materials.append(M['ti_dark'])
# rebuild with explicit slot indices: screen faces 0, pill 1, buttons 2
bm = bmesh.new(); bm.from_mesh(FRONT_ME)
bm.faces.ensure_lookup_table()
for fc_ in bm.faces:
    cz = fc_.calc_center_median()
    if abs(cz.x) > 0.385: fc_.material_index = 2
    elif cz.z > SZ + 0.68 and cz.y < -0.0412 and abs(cz.x) < 0.08: fc_.material_index = 1
    else: fc_.material_index = 0
bm.to_mesh(FRONT_ME); bm.free()

PZ = 0.30   # plinth height
class Phone:
    def __init__(s, i, r, c, x, y):
        s.i, s.r, s.c, s.x, s.y = i, r, c, x, y
        s.root = empty(f'ph{i}', None, (x, y, PZ))
        b = bpy.data.objects.new(f'body{i}', BODY_ME); col.objects.link(b); b.parent = s.root
        bv = b.modifiers.new('bv', 'BEVEL'); bv.width = 0.018; bv.segments = 3; bv.limit_method = 'ANGLE'; bv.angle_limit = rad(30); bv.harden_normals = True
        fo = bpy.data.objects.new(f'front{i}', FRONT_ME); col.objects.link(fo); fo.parent = s.root
        s.m, s.ver, s.crash, s.lum = screen_mat(i)
        fo.material_slots[0].link = 'OBJECT'; fo.material_slots[0].material = s.m
    def pos(s, z=0.0): return (s.x, s.y, PZ + z)
    def update(s, t, dur=0.7):
        tw(s.ver, 'default_value', t, dur, 1.0, 'io')
        tw(s.root, 'location', t, 0.22, s.pos(0.06), 'out'); tw(s.root, 'location', t + 0.22, 0.5, s.pos(0.0), 'io')
    def setv(s, t, v): st(s.ver, 'default_value', t, v)
    def crash_(s, t):
        tw(s.crash, 'default_value', t, 0.06, 1.0, 'lin')
        def shake(tt, t0=t):
            u = clamp((tt - t0) / 0.5); a = 0.045 * (1 - u) ** 2
            return (0.0, a * math.sin(2 * PI * 13 * (tt - t0)), 0.4 * a * math.sin(2 * PI * 9 * (tt - t0) + 1.0))
        fn(s.root, 'rotation_euler', t, t + 0.5, shake); st(s.root, 'rotation_euler', t + 0.5 + FR, (0, 0, 0))
    def glitch(s, t):
        st(s.crash, 'default_value', t, 0.55); st(s.crash, 'default_value', t + 2 * FR, 0.0)
    def restore(s, t, dur=0.5):
        st(s.ver, 'default_value', t, 0.0); tw(s.crash, 'default_value', t, dur, 0.0, 'io')

PH = []
for r in range(10):
    for c in range(10):
        PH.append(Phone(len(PH), r, c, -9.9 + 2.2 * c + (0.55 if r % 2 else -0.55), 2.2 * r))
CAN = PH[4]                                    # front row, left of centre
ORIGIN = min(PH, key=lambda p: (p.x - 0.55) ** 2 + (p.y - 4.4) ** 2)
dist = lambda p, q: math.hypot(p.x - q.x, p.y - q.y)
others = [p for p in PH if p is not CAN]; random.shuffle(others)
FIVE = [CAN]
for p in others:
    if len(FIVE) == 5: break
    if p.r <= 6 and all(dist(p, q) > 5.0 for q in FIVE): FIVE.append(p)
T25 = list(FIVE)
for p in others:
    if len(T25) == 25: break
    if p not in T25 and all(dist(p, q) > 2.3 for q in T25): T25.append(p)
for p in others:
    if len(T25) == 25: break
    if p not in T25: T25.append(p)
tick('phones built')

def grad_wall(name, lo, hi, strength, z0, z1):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; nt.nodes.remove(principled(m)); out = nt.nodes['Material Output']
    tc = nn(m, 'ShaderNodeTexCoord'); sp = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], sp.inputs[0])
    mr = nn(m, 'ShaderNodeMapRange'); mr.inputs['From Min'].default_value = z0; mr.inputs['From Max'].default_value = z1; ln(m, sp.outputs['Z'], mr.inputs['Value'])
    cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx(lo); cr.color_ramp.elements[1].color = hx(hi); ln(m, mr.outputs['Result'], cr.inputs['Fac'])
    e = nn(m, 'ShaderNodeEmission'); e.inputs['Strength'].default_value = strength; ln(m, cr.outputs['Color'], e.inputs['Color']); ln(m, e.outputs[0], out.inputs['Surface'])
    return m

# ---------- the hall: terrazzo floor, board-formed concrete, oak-slat ceiling, a window wall at golden hour ----------
def concrete(name, h, rough):
    m = mat(name, h, rough); tc = nn(m, 'ShaderNodeTexCoord')
    nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; ln(m, tc.outputs['Object'], nz.inputs['Vector'])
    f = mth(m, 'MULTIPLY_ADD', nz.outputs['Fac'], 0.07, 0.96)
    wv = nn(m, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z', wave_profile='SAW'); wv.inputs['Scale'].default_value = 0.9
    wv.inputs['Distortion'].default_value = 0.0; ln(m, tc.outputs['Object'], wv.inputs['Vector'])
    f = mth(m, 'MULTIPLY', f, mth(m, 'MULTIPLY_ADD', wv.outputs['Fac'], 0.08, 0.96))
    mu = nn(m, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mu.inputs['Factor'].default_value = 1.0; mu.inputs[6].default_value = hx(h)
    cc = nn(m, 'ShaderNodeCombineXYZ'); [ln(m, f, cc.inputs[i]) for i in range(3)]
    ln(m, cc.outputs[0], mu.inputs[7]); ln(m, mu.outputs[2], sock(m, 'Base Color')); return m
def wood(name, lo, hi, rough, stretch=(1, 10, 1), scale=5.0):
    m = mat(name, lo, rough); tc = nn(m, 'ShaderNodeTexCoord'); mp = nn(m, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
    ln(m, tc.outputs['Object'], mp.inputs['Vector']); nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 8.0
    ln(m, mp.outputs[0], nz.inputs['Vector'])
    cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx(lo); cr.color_ramp.elements[1].color = hx(hi)
    ln(m, nz.outputs['Fac'], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
    bp = nn(m, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.04; ln(m, nz.outputs['Fac'], bp.inputs['Height']); ln(m, bp.outputs['Normal'], sock(m, 'Normal'))
    return m
M['concrete'] = concrete('concrete', '#B9B2A6', 0.88)
M['oak'] = wood('oak', '#8E6744', '#B88D62', 0.5)
M['oak_x'] = wood('oak_x', '#8E6744', '#B88D62', 0.5, (10, 1, 1))
M['walnut2'] = wood('walnut2', '#3A2618', '#5C3D27', 0.38, (12, 1, 1), 4.0)
M['steel'] = mat('steel', '#3E4246', 0.42, 0.85)
M['brass'] = mat('brass', '#C6A15B', 0.30, 1.0)
M['brass_satin'] = mat('brass_satin', '#B8955A', 0.46, 1.0)
M['enamel'] = mat('enamel', '#F2ECDD', 0.35, emit=0.0, eh='#FFF3DC')
M['ink'] = mat('ink', '#1B1D20', 0.6)
M['ink_red'] = mat('ink_red', '#C8432C', 0.5)
M['terrazzo'] = mat('terrazzo', '#5B554D', 0.26)
m = M['terrazzo']; tc = nn(m, 'ShaderNodeTexCoord'); vo = nn(m, 'ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 70
ln(m, tc.outputs['Object'], vo.inputs['Vector']); sp = nn(m, 'ShaderNodeSeparateColor'); ln(m, vo.outputs['Color'], sp.inputs[0])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#8C8377'); el[1].position = 0.10; el[1].color = hx('#58524A')
e2 = el.new(0.05); e2.color = hx('#3E3A35')
ln(m, sp.outputs[0], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color')); rough_noise(m, 0.18, 0.34, 0.6)
HX0, HX1, HY0, HY1, HZ = -14.0, 14.0, -18.0, 26.0, 12.0
MB().box(((HX0 + HX1) / 2, (HY0 + HY1) / 2, -0.1), (HX1 - HX0 + 1, HY1 - HY0 + 1, 0.2), M['terrazzo']).ob('floor', None, smooth=False)
MB().box((60.0, 1.0, -0.1), (22.0, 22.0, 0.2), M['floor']).ob('rfloor', None, smooth=False)
wm = MB()
wm.box((HX0 - 0.15, 4.0, HZ / 2), (0.3, HY1 - HY0, HZ), M['concrete']).box((HX1 + 0.15, 4.0, HZ / 2), (0.3, HY1 - HY0, HZ), M['concrete'])
wm.box((0.0, HY0 - 0.15, HZ / 2), (HX1 - HX0 + 0.6, 0.3, HZ), M['concrete']).box((0.0, 4.0, HZ + 0.15), (HX1 - HX0 + 0.6, HY1 - HY0 + 0.6, 0.3), M['concrete'])
wm.box((0.0, HY1 + 0.25, 0.45), (HX1 - HX0 + 0.6, 0.5, 0.9), M['concrete']).box((0.0, HY1 + 0.25, HZ - 0.8), (HX1 - HX0 + 0.6, 0.5, 1.6), M['concrete'])
for y in range(-16, 26, 4):
    for x in (HX0 + 0.25, HX1 - 0.25): wm.box((x, y, HZ / 2), (0.5, 0.7, HZ), M['concrete'])
wm.ob('walls', None, smooth=False)
mu_ = MB()
for x in [HX0 + 1.4 * i for i in range(21)]: mu_.box((x, HY1 + 0.1, HZ / 2), (0.1, 0.12, HZ), M['steel'])
for z in (0.9, 3.4, 5.9, 8.4, HZ - 1.6): mu_.box((0.0, HY1 + 0.1, z), (HX1 - HX0, 0.12, 0.1), M['steel'])
mu_.ob('mullions', None, bev=0.01)
SKYM, _ = emat('skylight', '#EAF1F8', 2.5)
cs, sk = MB(), MB()
for k in range(70):
    y = HY0 + 0.3 + 0.62 * k
    if any(abs(y - y0) < 0.8 for y0 in (-6.0, 4.0, 14.0)): continue
    cs.box((0.0, y, HZ - 0.18), (HX1 - HX0, 0.09, 0.32), M['oak_x'])
for y0 in (-6.0, 4.0, 14.0): sk.box((0.0, y0, HZ - 0.01), (HX1 - HX0, 1.5, 0.02), SKYM)
cs.ob('slats', None); sk.ob('skylights', None, smooth=False, shadow=False)
SKYB = grad_wall('sky', '#FFB067', '#5E7FB0', float(opt('--skys', 0.9)), 0.0, 30.0)
MB().box((0.0, 0.0, 0.0), (140.0, 0.1, 60.0), SKYB).ob('sky', None, (0, 70.0, 24.0), smooth=False, shadow=False)
SILM, _ = emat('silh', '#A07A64', 0.7)
sl = MB()
for i in range(26):
    x = -60 + 4.8 * i + random.uniform(-1, 1); h = random.uniform(2.5, 8.0); w = random.uniform(3.0, 6.5)
    sl.box((x, 66.0, h / 2), (w, 0.1, h), SILM)
sl.ob('skyline', None, smooth=False, shadow=False)
# oak plinths under the phones
pl = MB()
for p in PH:
    pl.box((p.x, p.y, PZ / 2), (0.98, 0.56, PZ), M['oak']).box((p.x, p.y, PZ + 0.003), (0.86, 0.12, 0.006), M['brass_satin'])
pl.ob('plinths', None, bev=0.01)

# ---------- RELEASE console: walnut desk, brass trim, the ROLLOUT dial and a ROLLBACK lever ----------
DX, DY = -6.0, -4.0
PX = DX + 0.28                                  # desk centre (the dial sits left of it, the lever right)
TA = math.atan2(0.35, 0.75)                     # top slope (front 0.85 m, back 1.20 m)
YZ = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))  # prism polygon in (y, z), extruded along x
MB().prism([(-0.375, 0.0), (0.375, 0.0), (0.375, 1.20), (-0.375, 0.85)], 1.56, M['walnut2'], rot=YZ).ob('pedestal', None, (PX, DY, 0), bev=0.01)
tr = MB().box((PX, DY - 0.378, 0.85), (1.58, 0.02, 0.02), M['brass']).box((PX, DY + 0.378, 1.20), (1.58, 0.02, 0.02), M['brass'])
tr.box((PX, DY - 0.36, 0.04), (1.6, 0.06, 0.08), M['brass_satin'])
tr.ob('trim', None, bev=0.004)
DTOP = empty('dtop', None, (DX, DY, 1.025 + 0.0015), (TA, 0, 0))
MB().cyl((0, 0, 0), 0.385, 0.006, M['ink'], seg=96).tor((0, 0, 0.003), 0.385, 0.006, M['brass'], seg=96, rs=8).ob('dial_ring', DTOP, (0, 0, -0.001))
STEPS = [0, 1, 5, 25, 100]; ANG = {0: -135, 1: -67.5, 5: 0, 25: 67.5, 100: 135}
tk = MB()
for k in range(31):
    a = rad(-135 + 9 * k); major = (-135 + 9 * k) in [round(ANG[s]) for s in STEPS]
    r0, r1 = (0.235, 0.29) if major else (0.24, 0.262)
    tk.box(((r0 + r1) / 2 * math.sin(a), (r0 + r1) / 2 * math.cos(a), 0.005), (0.008 if major else 0.005, r1 - r0, 0.002), M['enamel'] if major else M['brass_satin'], rot=(0, 0, -a))
tk.ob('dial_ticks', DTOP, shadow=False)
DLAMP = {}
for s_ in STEPS:
    a = rad(ANG[s_]); lm = mat(f'dlamp{s_}', '#3A2E1A', 0.25, emit=0.0, eh='#FFC21A')
    MB().sph((0, 0, 0), 0.017, lm, seg=20, ring=10, scale=(1, 1, 0.7)).tor((0, 0, 0.001), 0.019, 0.004, M['brass'], seg=24, rs=6).ob(f'dlamp{s_}', DTOP, (0.318 * math.sin(a), 0.318 * math.cos(a), 0.004))
    txt(f'dlab{s_}', str(s_), 'din', 0.042, M['enamel'], DTOP, (0.37 * math.sin(a) * 1.0, 0.37 * math.cos(a), 0.004), (0, 0, 0), 0.0006)
    DLAMP[s_] = sock(lm, 'Emission Strength')
txt('dial_title', 'ROLLOUT  %', 'inter_sb', 0.022, M['brass_satin'], DTOP, (0, -0.30, 0.004), (0, 0, 0), 0.0004, space=1.25)
KNOB = empty('knob', DTOP, (0, 0, 0), (0, 0, rad(135)))
kb = MB().cyl((0, 0, 0.055), 0.19, 0.11, M['alu'], seg=96).cyl((0, 0, 0.112), 0.178, 0.006, M['alu_satin'], seg=96)
kb.tor((0, 0, 0.03), 0.191, 0.004, M['brass'], seg=96, rs=8)
kb.box((0, 0.115, 0.1165), (0.016, 0.085, 0.004), M['yellow_e'])
kb.ob('knob_body', KNOB, bev=0.006)
def dial(t, v, dur=0.38, ez='back2'):
    tw(KNOB, 'rotation_euler', t, dur, (0, 0, -rad(ANG[v])), ez)
    for s_ in STEPS: tw(DLAMP[s_], 'default_value', t + dur * 0.6, 0.08, 6.0 if (s_ <= v and s_ > 0) or (s_ == 0 and v == 0) else 0.0, 'lin')
def dial_set(t, v):
    st(KNOB, 'rotation_euler', t, (0, 0, -rad(ANG[v])))
    for s_ in STEPS: st(DLAMP[s_], 'default_value', t, 6.0 if (s_ <= v and s_ > 0) or (s_ == 0 and v == 0) else 0.0)
KNOB.rotation_euler = (0, 0, -rad(ANG[0])); DLAMP[0].default_value = 6.0
# the ROLLBACK lever: brass quadrant, steel arm, red ball; it pulls itself when the numbers spike
LX = 0.66
MB().box((0, 0, 0.012), (0.10, 0.20, 0.024), M['brass']).box((0, -0.12, 0.004), (0.02, 0.02, 0.006), M['ink_red']).ob('lever_base', DTOP, (LX, 0.02, 0), bev=0.004)
LEV = empty('lever', DTOP, (LX, 0.02, 0.03), (rad(-28), 0, 0))
MB().cyl((0, 0, 0.12), 0.009, 0.24, M['alu'], seg=12).sph((0, 0, 0.255), 0.032, M['ink_red'], seg=24, ring=12).cyl((0, 0, 0), 0.02, 0.06, M['brass'], rot=(0, PI / 2, 0), seg=20).ob('lever_arm', LEV)
txt('lever_t', 'ROLLBACK', 'inter_sb', 0.018, M['brass_satin'], DTOP, (LX, -0.17, 0.004), (0, 0, 0), 0.0004, space=1.2)
def pull(t):
    tw(LEV, 'rotation_euler', t, 0.16, (rad(34), 0, 0), 'out'); tw(LEV, 'rotation_euler', t + 1.1, 0.5, (rad(-28), 0, 0), 'io')
# plaques on the front face
PF = DY - 0.375
face_txt('ped_title', 'CANARY  RELEASE', 'inter_sb', 0.024, M['brass_satin'], None, PX, PF, 0.74, space=1.5)
for nm, z in (('ARGO ROLLOUTS', 0.58), ('AWS CODEDEPLOY', 0.40)):
    MB().box((0, 0, 0), (0.86, 0.012, 0.13), M['brass']).ob('plq_' + nm, None, (PX, PF - 0.006, z), bev=0.004)
    face_txt('plqt_' + nm, nm, 'din', 0.046, M['ink'], None, PX, PF - 0.012, z, space=1.12, fit=0.76)

# ---------- HEALTH cabinet: three analog gauges (CRASHES / ERRORS / SLOW) with red zones, a warning lamp on top ----------
MX, MY = -3.55, -4.7
MB().box((0, 0, 0.8), (0.62, 0.32, 1.60), M['walnut2']).box((0, 0, 1.605), (0.66, 0.36, 0.02), M['brass']).box((0, 0, 0.03), (0.66, 0.36, 0.06), M['brass_satin']).ob('pillar', None, (MX, MY, 0), bev=0.008)
MFY = MY - 0.16
face_txt('health', 'HEALTH', 'inter_sb', 0.026, M['brass_satin'], None, MX, MFY, 1.50, space=1.6)
GR = 0.135; GZ = (1.25, 0.88, 0.51)
NEED, GFACE = [], []
GA = lambda L: -120 + 240 * L
for k, (nm, gz) in enumerate(zip(('CRASHES', 'ERRORS', 'SLOW'), GZ)):
    fm = mat('gface_' + nm, '#F2ECDD', 0.35, emit=0.15, eh='#FFF3DC'); GFACE.append(sock(fm, 'Emission Strength'))
    g = MB().cyl((0, 0, 0), GR, 0.01, fm, rot=(PI / 2, 0, 0), seg=64).tor((0, -0.006, 0), GR + 0.008, 0.011, M['brass'], rot=(PI / 2, 0, 0), seg=64, rs=10)
    for j in range(25):
        a = rad(GA(j / 24)); r0, r1 = (GR - 0.03, GR - 0.008) if j % 6 == 0 else (GR - 0.02, GR - 0.008)
        red = j / 24 >= 0.62
        g.box(((r0 + r1) / 2 * math.sin(a), -0.0055, (r0 + r1) / 2 * math.cos(a)), (0.004 if j % 6 else 0.006, 0.002, r1 - r0), M['ink_red'] if red else M['ink'], rot=(0, a, 0))
    for j in range(16):  # red zone band
        a0 = rad(GA(0.62 + 0.38 * j / 16)); r_ = GR - 0.04
        g.box((r_ * math.sin(a0), -0.0055, r_ * math.cos(a0)), (0.018, 0.002, 0.012), M['ink_red'], rot=(0, a0, 0))
    g.cyl((0, -0.012, 0), 0.012, 0.01, M['brass'], rot=(PI / 2, 0, 0), seg=20)
    g.ob('gauge_' + nm, None, (MX, MFY - 0.006, gz))
    nd = empty('needle_' + nm, None, (MX, MFY - 0.016, gz), (0, rad(GA(0.1)), 0))
    MB().box((0, 0, GR * 0.38), (0.006, 0.003, GR * 0.95), M['ink']).box((0, 0, GR * 0.82), (0.004, 0.0032, GR * 0.2), M['ink_red']).ob('nd_' + nm, nd)
    NEED.append(nd)
    face_txt('gl_' + nm, nm, 'inter_sb', 0.019, M['enamel'], None, MX, MFY, gz - GR - 0.04, space=1.2)
WARN = mat('warn', '#5A1A14', 0.3, emit=0.0, eh='#FF3B2F')
MB().sph((0, 0, 0), 0.05, WARN, seg=24, ring=12, scale=(1, 1, 0.8)).tor((0, 0, 0.0), 0.054, 0.008, M['brass'], seg=32, rs=8).ob('warn', None, (MX, MY, 1.62))
WS = sock(WARN, 'Emission Strength')
def meter_level(k, t):
    base = (0.12, 0.2, 0.26)[k]
    w = 0.022 * math.sin(t * 2.3 + k * 1.7) + 0.012 * math.sin(t * 5.9 + k * 0.6)
    if k == 0:
        w += 0.76 * sm((t - (tSPIKE - 0.04)) / 0.22) * (1 - sm((t - (tROLLS + 0.4)) / 0.6))
        w += 0.70 * sm((t - (tHITS + 0.1)) / 0.22) * (1 - sm((t - (tTWO + 0.5)) / 0.6))
    return clamp(base + w, 0.02, 0.98)
for k, nd in enumerate(NEED):
    fn(nd, 'rotation_euler', 0.0, END, lambda t, k=k: (0.0, rad(GA(meter_level(k, t))), 0.0))
    tp = (tCRW, tERR, tSLOW)[k]
    tw(GFACE[k], 'default_value', tp - 0.05, 0.12, 1.4, 'out'); tw(GFACE[k], 'default_value', tp + 0.35, 0.5, 0.15, 'io')
for t0, t1 in ((tSPIKE + 0.12, tROLLS + 0.5), (tHITS + 0.25, tTWO + 0.6)):
    k = 0; t = t0
    while t < t1: st(WS, 'default_value', t, 9.0); st(WS, 'default_value', t + 0.18, 0.4); t += 0.34
    st(WS, 'default_value', t1 + 0.05, 0.0)

# ---------- restaurant (x 60) ----------
RX = 60.0
M['marble'] = mat('marble', '#1C1E22', 0.22); rough_noise(M['marble'], 0.16, 0.30, 5.0)
m = M['marble']; tc = nn(m, 'ShaderNodeTexCoord'); wv = nn(m, 'ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 2.2; wv.inputs['Distortion'].default_value = 9.0
wv.inputs['Detail'].default_value = 4.0; ln(m, tc.outputs['Object'], wv.inputs['Vector'])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx('#15171A'); cr.color_ramp.elements[1].color = hx('#3A3D43'); cr.color_ramp.elements[1].position = 0.95
ln(m, wv.outputs['Fac'], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
M['brass'] = mat('brass', '#C6A15B', 0.30, 1.0)
M['silver'] = mat('silver', '#D9DBDE', 0.12, 1.0)
M['porcelain'] = mat('porcelain', '#F2F1EC', 0.18)
M['dish'] = mat('dish', '#FFC21A', 0.30)
M['leaf'] = mat('leaf', '#3F7A3A', 0.5)
M['walnut'] = mat('walnut', '#2A1D15', 0.55)
m = M['walnut']; tc = nn(m, 'ShaderNodeTexCoord'); wv = nn(m, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
wv.inputs['Scale'].default_value = 6.0; ln(m, tc.outputs['Object'], wv.inputs['Vector']); bp = nn(m, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35
ln(m, wv.outputs['Fac'], bp.inputs['Height']); ln(m, bp.outputs['Normal'], sock(m, 'Normal'))
M['leather'] = mat('leather', '#3B2A20', 0.55)
WARM, _ = emat('warm', '#FFD9A6', 6.0)
KITCH, _ = emat('kitchen', '#FFB46B', 1.6)
TABLES = [(RX - 3.3 + 2.2 * i, 2.4 * j) for j in range(3) for i in range(4)]
HT = TABLES[1]                                    # the canary table: front row
tb, ch = MB(), MB()
for (x, y) in TABLES:
    tb.cyl((x, y, 0.735), 0.48, 0.03, M['marble'], seg=64).cyl((x, y, 0.37), 0.03, 0.70, M['brass'], seg=16).cyl((x, y, 0.012), 0.22, 0.024, M['brass'], seg=48)
    for sx in (-1, 1):
        cx = x + sx * 0.70
        ch.box((cx, y, 0.46), (0.42, 0.42, 0.05), M['leather']).box((cx + sx * 0.2, y, 0.78), (0.04, 0.40, 0.55), M['leather'])
        for lx in (-0.17, 0.17):
            for ly in (-0.17, 0.17): ch.cyl((cx + lx, y + ly, 0.22), 0.012, 0.44, M['brass'], seg=8)
    if (x, y) == HT: continue
    tb.cyl((x, y, 0.756), 0.15, 0.012, M['porcelain'], seg=48)
tb.ob('tables', None, bev=0.004); ch.ob('chairs', None, bev=0.01)
pd, pe = MB(), MB()
for (x, y) in TABLES:
    pd.cyl((x, y, 2.07), 0.14, 0.16, M['brass'], seg=40, r2=0.035).cyl((x, y, 3.3), 0.004, 2.3, M['ti_dark'], seg=6)
    pe.cyl((x, y, 1.985), 0.125, 0.004, WARM, seg=40)
pd.ob('pendants', None); pe.ob('pendant_glow', None, shadow=False)
def hemi(mb, c, r, m, scale=(1, 1, 1), seg=48, ring=24):
    mx = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
    res = bmesh.ops.create_uvsphere(mb.bm, u_segments=seg, v_segments=ring, radius=r, matrix=mx)
    below = [v for v in res['verts'] if v.co.z < c[2] - 1e-5]; bmesh.ops.delete(mb.bm, geom=below, context='VERTS')
    keep = [v for v in res['verts'] if v.is_valid]; return mb._fin(keep, m)
oc = MB()
for (x, y) in TABLES:
    if (x, y) == HT: continue
    hemi(oc, (x, y, 0.762), 0.135, M['silver'], (1, 1, 0.85)); oc.sph((x, y, 0.762 + 0.118), 0.016, M['silver'], seg=16, ring=8)
oc.ob('cloches', None)
PLT = empty('plate', None, (HT[0], HT[1], 0.75))
MB().cyl((0, 0, 0.006), 0.15, 0.012, M['porcelain'], seg=48).ob('plate_m', PLT)
MB().sph((0, 0, 0.012), 0.072, M['dish'], seg=32, ring=16, scale=(1, 1, 0.62)).box((0.012, 0.0, 0.058), (0.035, 0.012, 0.004), M['leaf'], rot=(0, 0, 0.6)).ob('dish', PLT)
CL = empty('cloche', PLT, (0, 0, 0.012))
ccm = MB(); hemi(ccm, (0, 0, 0), 0.135, M['silver'], (1, 1, 0.85)); ccm.sph((0, 0, 0.118), 0.016, M['silver'], seg=16, ring=8).ob('cloche_m', CL)
# back wall with the kitchen pass
wl = MB()
for (x0, x1, z0, z1) in ((RX - 9, RX - 3.2, 0, 4.6), (RX + 3.2, RX + 9, 0, 4.6), (RX - 3.2, RX + 3.2, 0, 1.0), (RX - 3.2, RX + 3.2, 2.3, 4.6)):
    wl.box(((x0 + x1) / 2, 8.6, (z0 + z1) / 2), (x1 - x0, 0.3, z1 - z0), M['walnut'])
wl.box((RX - 9.0, 3.0, 2.3), (0.3, 12.0, 4.6), M['walnut']).box((RX + 9.0, 3.0, 2.3), (0.3, 12.0, 4.6), M['walnut'])
wl.box((RX, 3.0, 4.75), (18.3, 12.0, 0.3), M['walnut'])
wl.ob('rwalls', None, smooth=False)
MB().box((RX, 7.75, 0.5), (6.4, 0.7, 1.0), M['marble']).box((RX, 7.4, 1.0), (6.4, 0.02, 0.02), M['brass']).ob('pass', None, bev=0.006)
MB().box((RX, 10.2, 1.65), (7.0, 0.1, 2.6), KITCH).ob('kitchen', None, smooth=False, shadow=False)
hl = MB()
for k in range(4): hl.cyl((RX - 2.4 + 1.6 * k, 7.75, 1.95), 0.12, 0.12, M['brass'], seg=32, r2=0.04).cyl((RX - 2.4 + 1.6 * k, 7.75, 3.2), 0.004, 2.4, M['ti_dark'], seg=6)
hl.ob('heatlamps', None)
hg = MB()
for k in range(4): hg.cyl((RX - 2.4 + 1.6 * k, 7.75, 1.888), 0.11, 0.004, WARM, seg=32)
hg.ob('heat_glow', None, shadow=False)
PASS_Z = 1.0
tick('set built')

# ---------- lights, world ----------
def light(name, kind, loc, aim=None, energy=100.0, color='#FFFFFF', size=None, size_y=None, spot=None, blend=0.6, shadow=True, cutoff=40.0):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = hx(color)[:3]
    if kind == 'AREA':
        ld.shape = 'RECTANGLE' if size_y else 'DISK'; ld.size = size
        if size_y: ld.size_y = size_y
    elif kind == 'SPOT': ld.spot_size = rad(spot); ld.spot_blend = blend; ld.shadow_soft_size = size or 0.1
    ld.use_shadow = shadow
    if cutoff: ld.use_custom_distance = True; ld.cutoff_distance = cutoff
    o = bpy.data.objects.new(name, ld); col.objects.link(o); o.location = loc
    if aim: o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
WORLD = bpy.data.worlds.new('w'); sc.world = WORLD
try: WORLD.use_nodes = True
except Exception: pass
WBG = WORLD.node_tree.nodes['Background']; WBG.inputs['Color'].default_value = hx('#2B2F33'); WBG.inputs['Strength'].default_value = 0.25
SUNE = float(opt('--sun', 10)); KEYE = float(opt('--key', 1200))
sd = bpy.data.lights.new('SUN', 'SUN'); sd.energy = SUNE; sd.color = hx('#FFC48A')[:3]; sd.angle = rad(1.2); sd.use_shadow = True
SUN = bpy.data.objects.new('SUN', sd); col.objects.link(SUN); SUN.rotation_euler = Vector((0.30, -0.93, -0.21)).to_track_quat('-Z', 'Y').to_euler()
for y0 in (-6.0, 4.0, 14.0): light('SKY%g' % y0, 'AREA', (0.0, y0, HZ - 0.2), (0.0, y0, 0.0), float(opt('--skyl', 300)), '#D9E7F4', size=26.0, size_y=1.5, shadow=False, cutoff=30)
light('KEY', 'AREA', (-2.0, -14.0, 8.0), (0.0, 4.0, 1.0), KEYE, '#FFE4C4', size=6.0, size_y=4.0, cutoff=40)
light('FILL', 'AREA', (6.0, -15.0, 3.0), (0.0, 4.0, 1.0), 400, '#E6EEF8', size=10.0, size_y=4.0, shadow=False, cutoff=40)
light('DKEY', 'AREA', (-4.4, -7.6, 2.8), (-4.8, -4.4, 1.0), 120, '#FFE8CC', size=2.5, size_y=2.5, shadow=False, cutoff=12)
def haze(name, c, size, dens, aniso, colr):
    hm_ = bpy.data.materials.new(name)
    try: hm_.use_nodes = True
    except Exception: pass
    nt = hm_.node_tree; nt.nodes.remove(principled(hm_)); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Density'].default_value = dens; pv.inputs['Anisotropy'].default_value = aniso; pv.inputs['Color'].default_value = hx(colr)
    nt.links.new(pv.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    return MB().box((0, 0, 0), size, hm_).ob(name, None, c, smooth=False, shadow=False)
haze('haze', (0.0, 4.0, HZ / 2), (HX1 - HX0, HY1 - HY0, HZ), float(opt('--haze', 0.007)), 0.55, '#EDE3D3')
DUSTM = mat('dust', '#EEE6D6', 0.6, emit=0.5, eh='#FFF1D6')
for nm, c, s_, n in (('dust1', (-4.0, -4.0, 1.8), (8, 6, 3), 450), ('dust2', (0.0, 2.0, 2.0), (12, 6, 3.5), 400)):
    dmb = MB()
    for _ in range(n): dmb.tet((random.uniform(-s_[0] / 2, s_[0] / 2), random.uniform(-s_[1] / 2, s_[1] / 2), random.uniform(-s_[2] / 2, s_[2] / 2)), 0.004, DUSTM)
    o = dmb.ob(nm, None, c, smooth=False, shadow=False); fn(o, 'location', 0.0, END, lambda t, c=c: (c[0] + 0.04 * t, c[1] + 0.02 * math.sin(t * 0.3), c[2] + 0.01 * t))
light('ROOM', 'AREA', (RX, 3.0, 4.4), (RX, 3.0, 0.0), 700, '#FFE2C2', size=14.0, size_y=10.0, cutoff=16)
light('HERO', 'SPOT', (HT[0] + 0.3, HT[1] - 0.8, 3.0), (HT[0], HT[1], 0.8), 260, '#FFE6C8', spot=34, blend=0.8, size=0.15, cutoff=8)
light('PASSL', 'AREA', (RX, 7.2, 1.85), (RX, 7.7, 1.0), 120, '#FFC890', size=6.0, size_y=0.5, shadow=False, cutoff=8)

# ---------- timeline ----------
# L0: one phone updates, then crashes; the 99 around it never notice
CAN.update(tSHIP + 0.05, 0.6); CAN.crash_(tCRASH0)
CAN.restore(CT(tUSUAL), 0.0)
# L1: everyone at once
for p in PH: p.update(tPUSH + 0.1 + 0.13 * p.r + random.uniform(0, 0.12), 0.6)
# L2: a glitch hiding in the yellow
ORIGIN.glitch(tSPOT + 0.38); ORIGIN.glitch(tSPOT + 0.55)
# L3: one bug, every phone; the undo crawls
ORIGIN.crash_(tBUG)
for p in PH:
    if p is ORIGIN: continue
    p.crash_(tEVERY2 + 0.05 + 0.045 * dist(p, ORIGIN) + random.uniform(0, 0.06))
for p in PH: p.restore(tUNDO + 0.1 + 0.16 * p.r + random.uniform(0, 0.15), 0.6)
# L4: canary: the dial goes to 1, one phone gets it
dial(t1 - 0.05, 1); CAN.update(t1 + 0.22, 0.7)
# L5: watch -> spike -> automatic rollback
CAN.crash_(tSPIKE - 0.02)
dial(tROLLS + 0.02, 0, 0.32, 'back'); pull(tROLLS - 0.12)
CAN.restore(tROLLS + 0.3, 0.5)
# L6: fixed build: 1 -> 5 -> 25 -> everyone
CAN.setv(CT(tGOOD), 1.0); dial_set(CT(tGOOD), 1)
dial(t5 - 0.06, 5)
for k, p in enumerate(FIVE[1:]): p.update(t5 + 0.15 + 0.07 * k, 0.6)
dial(t25 - 0.06, 25)
for p in T25[5:]: p.update(t25 + 0.15 + random.uniform(0, 0.35), 0.6)
dial(tALL - 0.08, 100)
for p in PH:
    if p not in T25: p.update(tALL + 0.02 + 0.022 * dist(p, CAN) + random.uniform(0, 0.05), 0.35)
# L7: restaurant: one cloche lifts, it goes back to the kitchen
tw(CL, 'location', tONE_T, 0.55, (0.0, 0.05, 0.36), 'out'); tw(CL, 'rotation_euler', tONE_T, 0.55, (rad(-28), 0, 0), 'out')
tw(CL, 'location', tIF2 + 0.02, 0.3, (0, 0, 0.012), 'io'); tw(CL, 'rotation_euler', tIF2 + 0.02, 0.3, (0, 0, 0), 'io')
G0, G1 = tIF2 + 0.32, tIF2 + 1.75
def glide(t):
    e = sm((t - G0) / (G1 - G0)); return (HT[0], HT[1] + (7.75 - HT[1]) * e, 0.75 + (PASS_Z - 0.75) * e + 0.62 * math.sin(PI * e))
fn(PLT, 'location', G0, G1 + FR, glide)
# L8: the next bug: one phone in a hundred, for two minutes
for p in PH: p.setv(CT(tBUG2), 0.0)
dial_set(CT(tBUG2), 0)
dial(tSHIP2 - 0.05, 1); CAN.update(tSHIP2 + 0.15, 0.6)
CAN.crash_(tHITS + 0.1)
dial(tTWO + 0.25, 0, 0.32, 'back'); pull(tTWO + 0.1); CAN.restore(tTWO + 0.5, 0.5)
# L9: a few, then everyone
dial(tFEW0 + 0.2, 5)
for k, p in enumerate(FIVE): p.update(tFEW0 + 0.35 + 0.07 * k, 0.55)
dial(tALL3 - 0.08, 100)
for p in PH:
    if p not in FIVE: p.update(tALL3 + 0.02 + 0.022 * dist(p, CAN) + random.uniform(0, 0.05), 0.4)
JOLTS = []

fit_texts()

# ---------- camera: per-frame bake (look-at + dutch), sub-frame jumps at cuts so motion blur never smears across a cut ----------
camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); col.objects.link(cam); sc.camera = cam
cam.rotation_mode = 'QUATERNION'; camd.clip_start = 0.05; camd.clip_end = 700.0; camd.sensor_fit = 'AUTO'; camd.sensor_width = 36.0
FOC = empty('foc'); camd.dof.use_dof = True; camd.dof.focus_object = FOC; camd.dof.aperture_blades = 7; camd.dof.aperture_rotation = rad(15)
V3 = lambda *a: Vector(a)
def landf(u): return 0.7 * EZ['out'](min(u / 0.45, 1.0)) + 0.3 * u
def toward(P, G, k): return G + (Vector(P) - G) * k
def pw(t, pts, ez='io'):
    if t <= pts[0][0]: return Vector(pts[0][1])
    for (ta, a), (tb, b) in zip(pts, pts[1:]):
        if t <= tb: return Vector(a).lerp(Vector(b), EZ[ez]((t - ta) / (tb - ta)))
    return Vector(pts[-1][1])
SH = []
def shot(t0, P0, G0, P1=None, G1=None, lens=50, fs=2.8, roll=0.0, whip=None, foc=None, fnP=None, ez='land'):
    P0, G0 = Vector(P0), Vector(G0)
    SH.append(dict(t0=t0, P0=P0, G0=G0, P1=Vector(P1) if P1 is not None else P0, G1=Vector(G1) if G1 is not None else G0, lens=lens, fs=fs, roll=roll, whip=whip, foc=foc, fnP=fnP, ez=ez))
def orbit(G, az, R, h): a = rad(az); return Vector(G) + Vector((R * math.sin(a), -R * math.cos(a), h))
def push(t0, P, G, k, lens, fs, **kw): P, G = V3(*P), V3(*G); shot(t0, P, G, toward(P, G, k), None, lens, fs, **kw)
CX = CAN.x
KN = V3(DX, DY, 1.03); CANS = V3(CX, 0.0, 0.85 + PZ); MET = V3(MX, MFY, 1.0)
# L0 the one phone, then crane back over the hundred
push(0.0, (CX + 0.35, -2.55, 1.32), (CX, 0.0, 1.14), 0.9, 50, 2.0)
def _s1(t, u, e, s):
    k = EZ['io'](u); kz = EZ['out'](u)
    P0, P1 = V3(CX + 0.4, -2.7, 1.35), V3(CX + 5.0, -15.5, 9.8)
    P = P0.lerp(P1, k); P.z = P0.z + (P1.z - P0.z) * kz
    return P, CANS.lerp(V3(0.0, 8.0, 0.2), k)
shot(t99 - 0.1, (0, 0, 0), (0, 0, 1), None, None, 35, 3.5, fnP=_s1, ez='io', foc=lambda t, P, G: CANS.lerp(V3(0, 6, 0.4), EZ['io'](clamp((t - t99) / 2.2))))
# L1 everyone at once
shot(tUSUAL, (13.0, -6.5, 1.8), (1.0, 7.0, 0.9), (11.5, -5.5, 2.4), (0.0, 7.0, 0.9), 32, 4.0)
shot(tEVERY, (-3.0, -13.0, 10.0), (0.5, 9.0, 0.0), (-2.0, -12.5, 11.0), None, 30, 6.0)
# L2 spot the problem
push(tSPOT, (5.2, -2.6, 1.35), (-2.0, 12.0, 1.25), 0.9, 40, 2.2, foc=lambda t, P, G: V3(ORIGIN.x, ORIGIN.y, 1.15))
# L3 one bug -> every phone
OG = V3(ORIGIN.x, ORIGIN.y, 1.15)
def _s5(t, u, e, s):
    k = EZ['io'](clamp((t - (tEVERY2 - 0.1)) / 1.5)); kz = EZ['out'](k)
    P0, P1 = V3(ORIGIN.x, ORIGIN.y - 3.4, 1.5), V3(ORIGIN.x + 2.0, ORIGIN.y - 13.5, 6.5)
    P = P0.lerp(P1, k); P.z = P0.z + (P1.z - P0.z) * kz
    P = P + (OG - P) * 0.05 * e * (1 - k)
    return P, OG.lerp(V3(0.5, 7.0, 0.5), k)
shot(tONEBUG, (0, 0, 0), (0, 0, 1), None, None, 40, 2.8, fnP=_s5, foc=lambda t, P, G: OG.lerp(V3(0.5, 6, 0.5), EZ['io'](clamp((t - tEVERY2) / 1.4))))
shot(tTESTER, (0, 0, 1), (0, 0, 0), None, None, 30, 8.0, fnP=lambda t, u, e, s: (V3(0, 9.0, 0) + Matrix.Rotation(rad(-9 + 14 * EZ['io'](u)), 3, 'Z') @ V3(0, -14.0, 10.5), V3(0, 9.0, 0)), ez='io')
shot(tBYTIME, (-7.0, -6.5, 1.5), (2.0, 8.0, 1.0), (-6.0, -6.8, 1.75), None, 30, 4.0)
# L4 the dial
GD = KN + V3(0, 0.02, 0)
shot(tFIX, (0, 0, 0), (0, 0, 1), None, None, 50, 2.0, fnP=lambda t, u, e, s: (GD + Matrix.Rotation(rad(14 - 20 * EZ['io'](u)), 3, 'Z') @ V3(0.2, -1.25, 0.5), GD), ez='io')
_dv = V3(DX - CX, DY, 0).normalized(); _sd = V3(-_dv.y, _dv.x, 0)
POV = KN + _dv * 1.35 + _sd * 0.12 + V3(0, 0, 0.52)
def overdial(k_canary):
    return lambda t, P, G: KN.lerp(CANS, EZ['io'](clamp((t - k_canary) / 0.4)))
shot(tSEND, POV, KN.lerp(CANS, 0.3), POV - _dv * 0.12, None, 35, 2.4, foc=overdial(t1 + 0.15))
shot(tUSERS, (CX + 2.0, -9.0, 5.5), (CX + 0.5, 5.0, 0.3), (CX + 2.4, -9.4, 5.8), None, 35, 5.0)
# L5 watch the numbers
push(tWATCH, (MX + 0.3, MY - 2.35, 1.15), (MX, MFY, 0.98), 0.95, 50, 2.6)
PM = V3(MX + 0.75, MY - 2.6, 1.3)
shot(tIF, PM, MET.lerp(CANS, 0.3), PM + V3(0.05, 0.12, 0), None, 28, 4.5, foc=lambda t, P, G: MET.lerp(CANS, 0.75))
shot(tROLLS - 0.02, POV - _dv * 0.1, KN.lerp(CANS, 0.32), POV - _dv * 0.22, None, 35, 2.4, foc=overdial(tROLLS + 0.3))
# L6 1 -> 5 -> 25 -> 100, craning up off the dial
def _s14(t, u, e, s):
    k = EZ['io'](clamp((t - (t5 + 0.3)) / 1.7)); kz = EZ['out'](k)
    P0, P1 = V3(DX + 0.55, DY - 1.25, 1.55), V3(-1.5, -14.5, 11.0)
    P = P0.lerp(P1, k); P.z = P0.z + (P1.z - P0.z) * kz
    return P, KN.lerp(V3(0.0, 8.0, 0.0), k)
shot(tGOOD, (0, 0, 0), (0, 0, 1), None, None, 35, 3.0, fnP=_s14, foc=lambda t, P, G: KN.lerp(V3(0, 6, 0.4), EZ['io'](clamp((t - (t5 + 0.3)) / 1.7))))
# L7 the restaurant
HP = V3(HT[0], HT[1], 0.82)
shot(tDISH - 0.02, (RX + 2.6, -5.6, 2.4), (RX, 3.0, 0.9), (RX + 2.1, -5.1, 2.25), None, 30, 4.0, whip='R')
push(tSERVE, (HT[0] + 0.55, HT[1] - 1.2, 1.25), HP, 0.92, 50, 2.0)
def _s17(t, u, e, s):
    pp = V3(*glide(clamp(t, G0, G1))) + V3(0, 0, 0.1); return V3(HT[0] + 2.4, HT[1] + 0.8 + 0.5 * e, 1.75), pp
shot(tIF2, (0, 0, 0), (0, 0, 1), None, None, 35, 2.8, fnP=_s17, foc=lambda t, P, G: G)
shot(tREST, (RX - 4.6, -4.4, 5.0), (RX, 3.4, 0.5), (RX - 4.1, -4.8, 5.3), None, 28, 5.0)
# L8 a bug can still ship
shot(tBUG2, (4.0, -11.0, 4.2), (0.0, 6.0, 0.6), (3.5, -10.5, 4.0), None, 32, 5.0, whip='L')
shot(tHITS - 0.2, (CX + 1.0, -4.2, 1.9), (CX, 1.5, 1.15), (CX + 0.8, -4.0, 1.8), None, 32, 3.5, foc=lambda t, P, G: CANS)
# L9 a few, then everyone
shot(tFEW0, (-4.0, -12.0, 9.0), (0.0, 8.0, 0.0), (-3.0, -12.5, 9.5), None, 30, 6.0)
# L10 the plaques
shot(tARGO - 0.12, (PX - 0.22, PF - 1.3, 0.62), (PX - 0.06, PF, 0.58), (PX + 0.12, PF - 1.25, 0.46), (PX + 0.04, PF, 0.41), 50, 2.8, ez='io')
# L11 wide orbit
G23 = V3(0.0, 8.0, 0.4)
shot(tCTA, orbit(G23, -24, 22.0, 9.0), G23, None, None, 28, 6.0, fnP=lambda t, u, e, s: (orbit(G23, -24 + 18 * EZ['io'](u), 22.0, 9.0 - 1.0 * u), G23), ez='io')
CUTFIX = []
WHIPDIR = dict(L=(-1, 0), R=(1, 0), U=(0, 1), D=(0, -1), UR=(0.707, 0.707))
def cut_frame(t0): return 1 + math.ceil(t0 * FPS - 1e-9)
def cam_eval(i, t):
    s = SH[i]; t0 = s['t0']; t1 = SH[i + 1]['t0'] if i + 1 < len(SH) else END
    u = clamp((t - t0) / (t1 - t0)); e = landf(u) if s['ez'] == 'land' else EZ[s['ez']](u)
    P, G = s['fnP'](t, u, e, s) if s['fnP'] else (s['P0'].lerp(s['P1'], e), s['G0'].lerp(s['G1'], e))
    P, G = Vector(P), Vector(G)
    fwd = (G - P); dist = fwd.length; fwd.normalize(); rt = fwd.cross(Vector((0, 0, 1))).normalized(); up = rt.cross(fwd)
    if i + 1 < len(SH) and SH[i + 1]['whip']:
        k = clamp((t - (t1 - 4 * FR)) / (4 * FR))
        if k > 0: a, b = WHIPDIR[SH[i + 1]['whip']]; G = G + (rt * a + up * b) * dist * math.tan(rad(18) * k * k)
    if s['whip']:
        k = clamp((t - t0) / (4 * FR))
        if k < 1: a, b = WHIPDIR[s['whip']]; G = G - (rt * a + up * b) * dist * math.tan(rad(18) * (1 - EZ['out'](k)))
    for tj, amp in JOLTS:
        x = (t - tj) / FR
        if 0 <= x <= 2: P = P - Vector((0, 0, amp * (x if x <= 1 else 2 - x)))
    fo = s['foc'](t, P, G) if s['foc'] else (s['G0'].lerp(s['G1'], e) if not s['fnP'] else G)
    q = (G - P).to_track_quat('-Z', 'Y') @ Quaternion((0, 0, 1), rad(s['roll']))
    return P, q, s['lens'], s['fs'], fo
def shot_at(t):
    i = 0
    while i + 1 < len(SH) and t >= SH[i + 1]['t0'] - 1e-9: i += 1
    return i
CK = []
for f in range(1, NF + 1): t = (f - 1) / FPS; CK.append((float(f), cam_eval(shot_at(t), t)))
for i in range(1, len(SH)):
    fc = cut_frame(SH[i]['t0'])
    CK.append((fc - 0.52, cam_eval(i - 1, (fc - 1.52) / FPS))); CK.append((fc - 0.48, cam_eval(i, (fc - 1.48) / FPS)))
CK.sort(key=lambda x: x[0])
prev = None; QK = []
for f, (P, q, lens, fs, fo) in CK:
    if prev is not None and q.dot(prev) < 0: q = -q
    prev = q; QK.append((f, P, q, lens, fs, fo))
def write_raw(owner, path, keys):
    owner.keyframe_insert(path, frame=1)
    ad = owner.id_data.animation_data; cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    dp = path if isinstance(owner, bpy.types.ID) else owner.path_from_id(path)
    vec = hasattr(keys[0][1], '__len__')
    for fc in cb.fcurves:
        if fc.data_path != dp: continue
        i = fc.array_index; co = [c for f, v in keys for c in (float(f), float(v[i] if vec else v))]
        kp = fc.keyframe_points; kp.clear(); kp.add(len(keys)); kp.foreach_set('co', co)
        for p in kp: p.interpolation = 'LINEAR'
        fc.update()
write_raw(cam, 'location', [(f, tuple(P)) for f, P, q, l, s_, fo in QK])
write_raw(cam, 'rotation_quaternion', [(f, tuple(q)) for f, P, q, l, s_, fo in QK])
write_raw(camd, 'lens', [(f, l) for f, P, q, l, s_, fo in QK])
write_raw(camd.dof, 'aperture_fstop', [(f, s_) for f, P, q, l, s_, fo in QK])
write_raw(FOC, 'location', [(f, tuple(fo)) for f, P, q, l, s_, fo in QK])
# whip frames get a longer shutter
for s in SH:
    if not s['whip']: continue
    fc = cut_frame(s['t0']); st(sc.render, 'motion_blur_shutter', (fc - 5) / FPS, 0.9); st(sc.render, 'motion_blur_shutter', (fc + 3) / FPS, 0.5)
write_tracks()

# ---------- render ----------
sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = SAMPLES
ee.use_shadows = True; ee.shadow_pool_size = '1024'; ee.use_raytracing = True; ee.ray_tracing_method = 'SCREEN'; ee.use_fast_gi = True
# stay inside EEVEE's 4096-tile shadow buffer: when it overflows, shadows drop out at random per frame and the haze flickers.
ee.shadow_resolution_scale = float(opt("--shres", 0.5))
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
ee.volumetric_tile_size = opt('--vtile', '4'); ee.volumetric_samples = 64; ee.volumetric_start = 0.1; ee.volumetric_end = 90.0
ee.volumetric_sample_distribution = 0.85; ee.use_volumetric_shadows = True
sc.render.resolution_x, sc.render.resolution_y = RES, int(RES * 16 / 9) // 2 * 2
sc.render.resolution_percentage = 100; sc.render.fps = FPS
a, b = [int(x) for x in opt('--range', f'1,{NF}').split(',')]
sc.frame_start, sc.frame_end = a, b
sc.render.image_settings.file_format = 'PNG'
if '--skip' in argv: sc.render.use_overwrite = False; sc.render.use_placeholder = True
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new('CompositorNodeRLayers'); go = ng.nodes.new('NodeGroupOutput')
ng.links.new(rl.outputs['Image'], go.inputs[0])  # no bloom
if '--blend' in argv: bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/scene20.blend')
if '--cutfix' in argv:
    sc.render.use_motion_blur = False
    for t in CUTFIX:
        for fr in (cut_frame(t) - 1, cut_frame(t)):
            sc.frame_set(fr); sc.render.filepath = f'{OUT}/f_{fr:04d}.png'; bpy.ops.render.render(write_still=True)
elif STILLS:
    for s in STILLS:
        sc.frame_set(F(s)); sc.render.filepath = f'{OUT}/still_{s:05.2f}.png'; bpy.ops.render.render(write_still=True)
elif '--dry' not in argv:
    sc.render.filepath = f'{OUT}/f_'; bpy.ops.render.render(animation=True)
