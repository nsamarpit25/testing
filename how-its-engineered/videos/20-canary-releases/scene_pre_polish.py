# 20 Canary Releases: "Blue Screen". A night airport hall: a 10 x 10 wall of portrait departure screens (each one computer),
# kiosks and gate seats, a glass facade onto the apron. One update turns every screen blue (with an ATM and a ward monitor).
# Then a coal mine: a canary in a brass cage, gas creeping in. Back at the wall a brass cage covers one screen with a
# ceramic canary on top; the cage grows 1 -> 5 -> 25 -> 100. Timed to voice/words.json.
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

# ---------- word times ----------
tONE, tEIGHT = W('one'), W('eight')
tAIR, tBANKS, tHOSP, tBLUE = L(0, 1), W('banks'), W('hospitals'), L(0, 2)
tALL, tFLIGHTS, tHOSP2, tPAPER = L(1, 0), L(1, 1), W('hospitals', 11.5), W('paper')
tWHAT, tFEW = L(2, 0), W('few', 14)
tCOAL, tTOOK, tCANARY, tPOISON, tTINY, tSTOPS, tSING, tEVERYONE = L(3, 0), L(3, 1), W('canary'), L(3, 2), W('tiny'), W('stops'), W('singing'), W('everyone', 23)
tSOFT, tCAN2, tNEW, tONEP, tFIRST = L(4, 0), W('canary', 26), L(4, 1), W('one', 29), W('first', 30)
tWATCH, tCR, tER, tRB, tSPK, tSPIKE, tROLLS, tOTHER = L(5, 0), W('crashes', 32), W('errors'), W('reboots'), L(5, 1), W('spikes'), W('rolls'), L(5, 2)
tLOOKS, t5, t25, tALLX = L(6, 0), W('five', 40), W('twenty', 41), W('everyone', 42)
tAFTER, tSTAGES = L(7, 0), L(7, 1)
tSAME, tONE3, tMIN, tNOT = L(8, 0), W('one', 50.5), W('minutes'), W('not', 52.5)
tTHATS, tARGO, tAWS, tCTA = L(9, 0), W('argo'), W('aws'), L(10, 0)

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
def haze(name, c, size, dens, aniso, colr):
    hm_ = bpy.data.materials.new(name)
    try: hm_.use_nodes = True
    except Exception: pass
    nt = hm_.node_tree; nt.nodes.remove(principled(hm_)); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Density'].default_value = dens; pv.inputs['Anisotropy'].default_value = aniso; pv.inputs['Color'].default_value = hx(colr)
    nt.links.new(pv.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    return MB().box((0, 0, 0), size, hm_).ob(name, None, c, smooth=False, shadow=False)
M = {}
def tex_noise_color(m, lo, hi, scale):
    tc = nn(m, 'ShaderNodeTexCoord'); nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 6.0
    ln(m, tc.outputs['Object'], nz.inputs['Vector'])
    cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx(lo); cr.color_ramp.elements[1].color = hx(hi)
    ln(m, nz.outputs['Fac'], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
M['hfloor'] = mat('hfloor', '#121418', 0.12); tex_noise_color(M['hfloor'], '#0B0D10', '#1C1F24', 0.5); rough_noise(M['hfloor'], 0.08, 0.2, 0.3)
M['bezel'] = mat('bezel', '#0E0F11', 0.28, 0.5)
M['steel'] = mat('steel', '#2E3236', 0.4, 0.85)
M['chrome'] = mat('chrome', '#C8CCD2', 0.16, 1.0)
M['brass'] = mat('brass', '#C9A45C', 0.26, 1.0)
M['leather'] = mat('leather', '#141518', 0.5); bump(M['leather'], 60, 0.04)
M['concrete'] = concrete('concrete', '#77736D', 0.85)
M['ceil'] = mat('ceil', '#1A1C20', 0.8)
M['granite'] = mat('granite', '#1E2024', 0.25); tex_noise_color(M['granite'], '#16181B', '#2A2D32', 18.0)
M['paint'] = mat('paint', '#E6E9EE', 0.3)
M['tarmac'] = mat('tarmac', '#0C0D0F', 0.65)
M['label'] = mat('label', '#F1F3F6', 0.5, emit=1.4, eh='#F1F3F6')
M['walnut'] = wood('walnut', '#3A2618', '#5C3D27', 0.36, (12, 1, 1), 4.0)
M['timber'] = wood('timber', '#4A3524', '#6E5036', 0.85, (1, 1, 6), 7.0)
M['rock'] = mat('rock', '#3A332C', 0.9); tex_noise_color(M['rock'], '#221E1A', '#4A4038', 2.2); bump(M['rock'], 2.5, 0.7, voronoi=True)
M['dirt'] = mat('dirt', '#241F1A', 0.95); bump(M['dirt'], 9.0, 0.4)
M['rust'] = mat('rust', '#5A3E2C', 0.62, 0.5); rough_noise(M['rust'], 0.5, 0.8, 7.0)
M['coal'] = mat('coal', '#0B0B0C', 0.35)
M['canary'] = mat('canary', '#FFC21A', 0.3)
M['canary_w'] = mat('canary_w', '#E39C0C', 0.4)
M['beak'] = mat('beak', '#F0862A', 0.4)
M['eye'] = mat('eye', '#040404', 0.08)
M['note'] = mat('note', '#FFE9A8', 0.4, emit=3.5, eh='#FFE3A0')
M['sheet'] = mat('sheet', '#E9ECEE', 0.7)
M['vinyl'] = mat('vinyl', '#7E8885', 0.35)
M['wallpale'] = mat('wallpale', '#AEB9B6', 0.8)
M['board'] = wood('board', '#7A5231', '#94683F', 0.5, (1, 8, 1), 5.0)

IMG = {k: bpy.data.images.load(f'{D}/tex/{k}.png') for k in [f'fids{i}' for i in range(6)] + [f'fidsv{i}' for i in range(6)] +
       ['bsod', 'toast', 'bsod_l', 'kiosk', 'atm', 'ward', 'chart', 'wall_stages', 'wall_argo', 'wall_aws']}
def teximg(m, key, uvsock):
    n = nn(m, 'ShaderNodeTexImage'); n.image = IMG[key]; n.extension = 'CLIP'; n.interpolation = 'Linear'; ln(m, uvsock, n.inputs['Vector']); return n
def val(m, v):
    n = nn(m, 'ShaderNodeValue'); n.outputs[0].default_value = v; return n.outputs[0]
def obj_uv(m, w, h, ax='Z'):
    tc = nn(m, 'ShaderNodeTexCoord'); sp = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], sp.inputs[0])
    u = mth(m, 'MULTIPLY_ADD', sp.outputs['X'], 1 / w, 0.5); v = mth(m, 'MULTIPLY_ADD', sp.outputs[ax], 1 / h, 0.5)
    uv = nn(m, 'ShaderNodeCombineXYZ'); ln(m, u, uv.inputs[0]); ln(m, v, uv.inputs[1]); return sp, u, v, uv.outputs[0]

# ---------- the wall: 10 x 10 portrait departure screens, each one computer ----------
MW, MHt, PXM, PZM, MZ0 = 0.60, 1.067, 0.65, 1.117, 1.95
def MXc(c): return (c - 4.5) * PXM
def MZc(r): return MZ0 + r * PZM
WW, WH = 9 * PXM + MW, 9 * PZM + MHt
WX0, WZ0 = MXc(0) - MW / 2, MZc(0) - MHt / 2
WCZ = WZ0 + WH / 2
def wall_mat(i, var, cx, cz):
    m = mat(f'mon{i}', '#000000', 0.12); b = principled(m)
    sp, u, v, uv = obj_uv(m, MW, MHt)
    pg = teximg(m, f'fids{var}', uv).outputs['Color']; p2 = teximg(m, f'fidsv{var}', uv).outputs['Color']; bs = teximg(m, 'bsod', uv).outputs['Color']
    to = teximg(m, 'toast', uv)
    V = {k: val(m, d) for k, d in (('ver', 0.0), ('crash', 0.0), ('dl', 0.0), ('tv', 0.0), ('s1', 0.0), ('s2', 0.0), ('s3', 0.0), ('lum', 1.6))}
    vv = mth(m, 'SUBTRACT', 1.0, v)   # 0 at the top: new versions wipe in from the header down
    g = mth(m, 'SUBTRACT', mth(m, 'MULTIPLY', V['ver'], 1.15), vv)
    f = mth(m, 'MULTIPLY', g, 12.0, clamp_=True)
    act = mth(m, 'MULTIPLY', mth(m, 'MULTIPLY', V['ver'], mth(m, 'SUBTRACT', 1.0, V['ver'])), 6.0, clamp_=True)
    band = mth(m, 'MULTIPLY', mth(m, 'SUBTRACT', 1.0, mth(m, 'MULTIPLY', mth(m, 'ABSOLUTE', mth(m, 'SUBTRACT', g, 0.03)), 45.0), clamp_=True), act)
    c = mixc(m, f, pg, p2); c = mixc(m, band, c, hx('#FFFFFF'))
    c = mixc(m, mth(m, 'MULTIPLY', to.outputs['Alpha'], V['tv']), c, to.outputs['Color'])
    inb = mth(m, 'MULTIPLY', mth(m, 'GREATER_THAN', u, 60 / 540), mth(m, 'LESS_THAN', u, mth(m, 'MULTIPLY_ADD', V['dl'], 420 / 540, 60 / 540)))
    inb = mth(m, 'MULTIPLY', inb, mth(m, 'MULTIPLY', mth(m, 'GREATER_THAN', v, 1 - 866 / 960), mth(m, 'LESS_THAN', v, 1 - 846 / 960)))
    c = mixc(m, mth(m, 'MULTIPLY', inb, V['tv']), c, hx('#FFC21A'))
    c = mixc(m, V['crash'], c, bs)
    us = mth(m, 'MULTIPLY_ADD', sp.outputs['X'], 1 / WW, (cx - WX0) / WW); vs_ = mth(m, 'MULTIPLY_ADD', sp.outputs['Z'], 1 / WH, (cz - WZ0) / WH)
    suv = nn(m, 'ShaderNodeCombineXYZ'); ln(m, us, suv.inputs[0]); ln(m, vs_, suv.inputs[1])
    for k, key in (('s1', 'wall_stages'), ('s2', 'wall_argo'), ('s3', 'wall_aws')):
        c = mixc(m, V[k], c, teximg(m, key, suv.outputs[0]).outputs['Color'])
    ln(m, c, b.inputs['Emission Color']); ln(m, V['lum'], b.inputs['Emission Strength'])
    return m, V
def shared_mesh(mb, name):
    me = bpy.data.meshes.new(name); mb.bm.to_mesh(me); mb.bm.free()
    for m_ in mb.mats: me.materials.append(m_)
    return me
SCR_ME = shared_mesh(MB().box((0, 0, 0), (MW, 0.004, MHt), mat('dummy', '#000000', 0.1)), 'scr')
BEZ_ME = shared_mesh(MB().box((0, 0.034, 0), (MW + 0.03, 0.06, MHt + 0.03), M['bezel']), 'bez')
class Mon:
    def __init__(s, i, c, r, var):
        s.i, s.c, s.r, s.x, s.z = i, c, r, MXc(c), MZc(r)
        s.m, s.V = wall_mat(i, var, s.x, s.z)
        o = bpy.data.objects.new(f'scr{i}', SCR_ME); col.objects.link(o); o.location = (s.x, -0.004, s.z)
        o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = s.m
        bz = bpy.data.objects.new(f'bez{i}', BEZ_ME); col.objects.link(bz); bz.location = (s.x, 0.0, s.z)
    def k(s, key, t, dur, v, ez='io'): tw(s.V[key], 'default_value', t, dur, v, ez)
    def set_(s, key, t, v): st(s.V[key], 'default_value', t, v)
    def install(s, t0, t1):
        s.k('tv', t0, 0.18, 1.0, 'out'); s.set_('dl', t0, 0.0); s.k('dl', t0 + 0.2, t1 - t0 - 0.2, 1.0, 'io')
    def crash_(s, t):
        s.k('tv', t, 0.05, 0.0, 'lin'); s.k('crash', t, 0.07, 1.0, 'lin')
        s.set_('lum', t, 3.4); s.k('lum', t + 2 * FR, 0.3, 1.7, 'out')
    def wipe(s, t, dur=0.6): s.k('tv', t, 0.12, 0.0, 'lin'); s.k('ver', t, dur, 1.0, 'io')
    def rollback(s, t, dur=0.6): s.k('crash', t, 0.3, 0.0, 'io'); s.k('ver', t, dur, 0.0, 'io'); s.k('tv', t, 0.1, 0.0, 'lin')
random.seed(7)
MONS = [Mon(r * 10 + c, c, r, random.randrange(6)) for r in range(10) for c in range(10)]
MG = {(m_.c, m_.r): m_ for m_ in MONS}
CAN = MG[(4, 3)]; CANX, CANZ = CAN.x, CAN.z
gd = lambda a, b: math.hypot(a.c - b.c, a.r - b.r)
wb = MB()
wb.box((0, 0.2, WCZ), (WW + 0.3, 0.26, WH + 0.3), M['steel'])
wb.box((0, 0.35, (WZ0 - 0.15) / 2), (WW + 0.9, 1.4, WZ0 - 0.15), M['granite'])
wb.box((0, -0.36, WZ0 - 0.17), (WW + 0.92, 0.02, 0.04), M['brass'])
for sx in (-1, 1): wb.box((sx * (WW / 2 + 0.32), 0.2, (WZ0 + WH + 0.6) / 2), (0.3, 0.4, WZ0 + WH + 0.6), M['steel'])
wb.box((0, 0.2, WZ0 + WH + 0.3), (WW + 0.94, 0.42, 0.14), M['steel'])
wb.ob('wallframe', None, bev=0.01)
face_txt('basetxt', 'DEPARTURES  ·  ALL GATES', 'inter_sb', 0.13, M['brass'], None, 0.0, -0.35, 0.72, space=1.25)
tick('wall built')

# ---------- the hall: polished stone, concrete columns, a glass facade onto the apron at night ----------
HXW, HY0, HY1, HZ = 30.0, -32.0, 14.0, 18.0
MB().box((0, (HY0 + HY1) / 2, -0.1), (2 * HXW + 1, HY1 - HY0 + 1, 0.2), M['hfloor']).ob('floor', None, smooth=False)
hb = MB()
for sx in (-1, 1): hb.box((sx * (HXW + 0.2), (HY0 + HY1) / 2, HZ / 2), (0.4, HY1 - HY0, HZ), M['concrete'])
hb.box((0, HY0 - 0.2, HZ / 2), (2 * HXW, 0.4, HZ), M['concrete'])
hb.box((0, HY1 + 0.2, 0.3), (2 * HXW, 0.4, 0.6), M['concrete'])
hb.ob('walls', None, smooth=False)
MB().box((0, (HY0 + HY1) / 2, HZ + 0.2), (2 * HXW + 1, HY1 - HY0 + 1, 0.4), M['ceil']).ob('ceiling', None, smooth=False)
LSTRIP, _ = emat('lstrip', '#FFF0DC', 3.0)
ls = MB()
for y in range(-28, 13, 5): ls.box((0, y, HZ - 0.03), (2 * HXW - 2, 0.25, 0.04), LSTRIP)
ls.ob('lightstrips', None, smooth=False, shadow=False)
cb = MB()
for x in (-13.0, 13.0):
    for y in (-22.0, -8.0, 6.0): cb.cyl((x, y, HZ / 2), 0.5, HZ, M['concrete'], seg=32)
cb.ob('columns', None)
fb = MB()
for i in range(21): fb.box((-HXW + 3 * i, HY1 + 0.1, HZ / 2), (0.14, 0.3, HZ), M['steel'])
for z in (0.62, 4.5, 9.0, 13.5, HZ - 0.3): fb.box((0, HY1 + 0.1, z), (2 * HXW, 0.26, 0.12), M['steel'])
fb.ob('facade', None, bev=0.01)
# gate seating, facing the wall
sb = MB()
for y in (-8.5, -10.6, -12.7):
    for x0, x1 in ((-6.6, -1.0), (1.0, 6.6)):
        n = int((x1 - x0) / 0.58)
        sb.box(((x0 + x1) / 2, y, 0.36), (x1 - x0, 0.08, 0.07), M['chrome'])
        for xl in (x0 + 0.2, x1 - 0.2): sb.box((xl, y, 0.18), (0.05, 0.42, 0.36), M['chrome'])
        for k in range(n):
            x = x0 + 0.29 + k * 0.58
            sb.box((x, y + 0.02, 0.45), (0.5, 0.48, 0.08), M['leather'], rot=(rad(-3), 0, 0))
            sb.box((x, y - 0.25, 0.76), (0.5, 0.07, 0.5), M['leather'], rot=(rad(10), 0, 0))
sb.ob('seats', None, bev=0.012)
# check-in kiosks
def small_mat(name, key, w, h, ax='Z', lum=1.4):
    m = mat(name, '#000000', 0.12); b = principled(m); sp, u, v, uv = obj_uv(m, w, h, ax)
    a = teximg(m, key, uv).outputs['Color']; bs = teximg(m, 'bsod_l', uv).outputs['Color']
    cr = val(m, 0.0); lm = val(m, lum)
    ln(m, mixc(m, cr, a, bs), b.inputs['Emission Color']); ln(m, lm, b.inputs['Emission Strength'])
    return m, cr, lm
def screen_plane(name, parent, loc, rot, w, h, key, lum=1.4):
    m, cr, lm = small_mat(name, key, w, h, lum=lum)
    MB().box((0, 0, 0), (w, 0.003, h), m).ob(name, parent, loc, rot, smooth=False)
    return cr, lm
def crash_small(cr, lm, t, base=1.4):
    tw(cr, 'default_value', t, 0.07, 1.0, 'lin'); st(lm, 'default_value', t, base * 2.2); tw(lm, 'default_value', t + 2 * FR, 0.3, base, 'out')
KIOSK = []
for i, x in enumerate((-15.4, -14.0, -12.6, 12.6, 14.0, 15.4)):
    root = empty(f'kiosk{i}', None, (x, -3.2, 0))
    MB().box((0, 0, 0.55), (0.52, 0.42, 1.1), M['bezel']).box((0, -0.05, 1.32), (0.6, 0.16, 0.48), M['bezel'], rot=(rad(-18), 0, 0)) \
        .box((0, -0.215, 0.82), (0.36, 0.02, 0.05), M['brass']).ob(f'kbody{i}', root, bev=0.015)
    KIOSK.append(screen_plane(f'kscr{i}', root, (0, -0.13, 1.345), (rad(-18), 0, 0), 0.48, 0.36, 'kiosk'))
# ---------- outside: apron, runway lights, parked aircraft, a sky with a little city glow ----------
MB().box((0, 220, -0.12), (900, 410, 0.1), M['tarmac']).ob('apron', None, smooth=False)
SKYB = grad_wall('sky', '#2C2232', '#03050B', 1.0, -150.0, -70.0)
MB().box((0, 0, 0), (1500, 0.1, 300), SKYB).ob('sky', None, (0, 430, 140), smooth=False, shadow=False)
BLU, _ = emat('taxil', '#3D7BFF', 9.0); WHT, _ = emat('rwyl', '#FFF4E0', 9.0); AMB, _ = emat('ambl', '#FFB347', 7.0); CITY, _ = emat('city', '#FFD9A8', 3.0)
al = MB()
for x in range(-240, 241, 8):
    for y in (62.0, 84.0): al.box((x, y, 0.15), (0.35, 0.35, 0.3), BLU)
    for y in (138.0, 162.0): al.box((x + 4, y, 0.15), (0.4, 0.4, 0.3), WHT)
for x in range(-240, 241, 15): al.box((x, 150.0, 0.06), (1.2, 0.25, 0.08), AMB)
for _ in range(260): al.box((random.uniform(-500, 500), random.uniform(380, 420), random.uniform(0.5, 9)), (random.uniform(0.6, 2.2), 0.3, random.uniform(0.3, 1.0)), CITY)
al.ob('lights_out', None, smooth=False, shadow=False)
WIN, _ = emat('cabin', '#FFE2B0', 2.2); NAVR, _ = emat('navr', '#FF2A1A', 14.0); NAVG, _ = emat('navg', '#2AFF6A', 14.0); NAVW, _ = emat('navw', '#FFFFFF', 30.0)
def airliner(name, loc, yaw, land=False):
    root = empty(name, None, loc, (0, 0, yaw)); w_ = M['paint']; mb = MB()
    mb.cyl((0, 0, 0), 2.0, 34.0, w_, rot=(0, PI / 2, 0), seg=32)
    mb.sph((17.0, 0, -0.1), 2.0, w_, seg=24, ring=12, scale=(2.0, 1.0, 0.96))
    mb.cyl((-21.0, 0, 0.55), 0.45, 8.0, w_, rot=(0, PI / 2, 0), seg=24, r2=2.0)
    for sy in (-1, 1):
        mb.prism([(5.0, sy * 1.6), (-1.5, sy * 1.6), (-9.0, sy * 17.5), (-6.5, sy * 17.5)][::sy], 0.45, w_, c=(0, 0, -1.1))
        mb.prism([(-19.5, sy * 0.6), (-22.5, sy * 0.6), (-26.0, sy * 6.5), (-24.5, sy * 6.5)][::sy], 0.25, w_, c=(0, 0, 0.9))
        mb.cyl((3.0, sy * 6.2, -2.1), 1.15, 4.2, M['steel'], rot=(0, PI / 2, 0), seg=24)
        mb.box((0.5, sy * 2.005, 0.55), (27.0, 0.02, 0.24), WIN)
        mb.box((-1.0, sy * 1.0, -2.6), (0.4, 0.4, 1.2), M['bezel'])
        mb.sph((-8.8, sy * 17.6, -1.1), 0.18, NAVG if sy > 0 else NAVR, seg=8, ring=6)
    mb.box((13.0, 0, -2.6), (0.35, 0.35, 1.0), M['bezel'])
    mb.prism([(-17.0, 1.6), (-24.0, 1.6), (-26.4, 9.0), (-23.6, 9.0)], 0.35, w_, rot=(PI / 2, 0, 0))
    mb.sph((-26.5, 0, 9.0), 0.2, NAVW, seg=8, ring=6)
    if land: mb.sph((19.5, 0, -1.4), 0.45, NAVW, seg=10, ring=6)
    mb.ob(name + '_m', root, smooth=True)
    return root
airliner('park1', (-17.0, 42.0, 3.1), -0.8); airliner('park2', (22.0, 45.0, 3.1), PI)
TP = airliner('takeoff', (-400.0, 150.0, 3.1), 0.0, land=True)
tick('hall built')

# ---------- ATM (x -80) and a hospital ward (x -110) ----------
AX = -80.0
ab = MB()
ab.box((AX, 0.7, 2.5), (7.0, 0.6, 5.0), M['granite'])
ab.box((AX, 0.32, 0.9), (0.9, 0.5, 1.8), M['steel']).box((AX, 0.09, 1.38), (0.5, 0.04, 0.4), M['bezel'])
ab.box((AX, -0.02, 1.02), (0.56, 0.3, 0.05), M['steel'], rot=(rad(18), 0, 0))
for i in range(4):
    for j in range(3): ab.box((AX - 0.12 + 0.12 * j, -0.06 + 0.06 * i, 1.06 + 0.02 * i), (0.08, 0.045, 0.02), M['chrome'], rot=(rad(18), 0, 0))
ab.box((AX + 0.3, 0.07, 1.2), (0.12, 0.02, 0.025), NAVG)
ab.box((AX, -2.0, -0.1), (10, 6, 0.2), M['hfloor'])
ab.ob('atm', None, bev=0.006)
ATM = screen_plane('atmscr', None, (AX, 0.066, 1.38), (rad(-8), 0, 0), 0.40, 0.30, 'atm')
face_txt('atmsign', 'ATM', 'inter_b', 0.14, M['label'], None, AX, 0.4, 2.15, space=1.2)
HXs = -110.0
hb2 = MB()
hb2.box((HXs, 1.4, 2.0), (6.0, 0.3, 4.0), M['wallpale']).box((HXs, -1.0, -0.1), (6.0, 6.0, 0.2), M['vinyl'])
hb2.box((HXs - 0.6, -0.4, 0.62), (1.0, 2.1, 0.12), M['steel']).box((HXs - 0.6, -0.4, 0.75), (0.95, 2.0, 0.16), M['sheet'])
hb2.box((HXs - 0.6, 0.66, 0.95), (1.0, 0.06, 0.65), M['steel'])
for sx in (-1, 1): hb2.box((HXs - 0.6 + sx * 0.52, -0.6, 0.98), (0.03, 1.1, 0.03), M['chrome'])
hb2.cyl((HXs + 0.45, 0.45, 0.78), 0.025, 1.56, M['chrome'], seg=12).cyl((HXs + 0.45, 0.45, 0.02), 0.25, 0.04, M['steel'], seg=24)
hb2.box((HXs + 0.45, 0.36, 1.58), (0.48, 0.14, 0.38), M['bezel'])
hb2.box((HXs - 0.45, -0.62, 0.837), (0.25, 0.34, 0.008), M['board']).box((HXs - 0.45, -0.47, 0.845), (0.09, 0.03, 0.012), M['chrome'])
hb2.cyl((HXs - 0.28, -0.66, 0.842), 0.005, 0.14, M['bezel'], rot=(rad(90), 0, rad(15)), seg=8)
hb2.ob('ward', None, bev=0.008)
WARD = screen_plane('wardscr', None, (HXs + 0.45, 0.288, 1.58), (0, 0, 0), 0.42, 0.31, 'ward')
pm = mat('chartm', '#FFFFFF', 0.8); _, _, _, cuv = obj_uv(pm, 0.215, 0.28, 'Y'); ln(pm, teximg(pm, 'chart', cuv).outputs['Color'], sock(pm, 'Base Color'))
MB().box((0, 0, 0), (0.215, 0.28, 0.002), pm).ob('chart', None, (HXs - 0.45, -0.635, 0.842), smooth=False)

# ---------- the mine (x 60): timber sets, rails, a cart, hanging lanterns, the canary's cage, gas ----------
MX0, TWm, THm, MY0, MY1 = 60.0, 3.0, 2.7, -12.0, 42.0
rk = MB()
y = MY0
while y < MY1:
    for sx in (-1, 1):
        rk.box((MX0 + sx * (TWm / 2 + 0.25 + random.uniform(-0.12, 0.12)), y, THm / 2), (0.6, random.uniform(0.7, 1.1), THm + 0.6), M['rock'],
               rot=(random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), random.uniform(-0.2, 0.2)))
    rk.box((MX0 + random.uniform(-0.2, 0.2), y, THm + 0.25 + random.uniform(-0.08, 0.08)), (TWm + 1.2, random.uniform(0.7, 1.1), 0.5), M['rock'],
           rot=(random.uniform(-0.1, 0.1), random.uniform(-0.08, 0.08), random.uniform(-0.1, 0.1)))
    y += 0.75
rk.box((MX0, (MY0 + MY1) / 2, -0.1), (TWm + 1.0, MY1 - MY0, 0.2), M['dirt'])
rk.box((MX0, MY1 + 0.5, THm / 2), (TWm + 2, 1.0, THm + 1), M['rock'])
rk.ob('rock', None, smooth=False)
tb = MB()
for k in range(34):
    y = MY0 + 2.0 + 1.6 * k
    for sx in (-1, 1): tb.box((MX0 + sx * (TWm / 2 - 0.12), y, (THm - 0.1) / 2), (0.2, 0.2, THm - 0.1), M['timber'], rot=(0, sx * 0.04, 0))
    tb.box((MX0, y, THm - 0.12), (TWm + 0.1, 0.22, 0.22), M['timber'])
for k in range(int((MY1 - MY0) / 0.6)): tb.box((MX0, MY0 + 0.3 + 0.6 * k, 0.04), (1.25, 0.16, 0.08), M['timber'])
tb.ob('timber', None, bev=0.01)
rl = MB()
for sx in (-1, 1): rl.box((MX0 + sx * 0.42, (MY0 + MY1) / 2, 0.12), (0.06, MY1 - MY0, 0.08), M['steel'])
rl.ob('rails', None)
CART = empty('cart', None, (MX0, 1.0, 0))
cm = MB().box((0, 0, 0.68), (1.0, 1.4, 0.7), M['rust']).box((0, 0, 0.36), (0.8, 1.2, 0.08), M['steel'])
for sx in (-1, 1):
    for sy in (-1, 1): cm.cyl((sx * 0.42, sy * 0.45, 0.2), 0.17, 0.08, M['steel'], rot=(0, PI / 2, 0), seg=20)
for _ in range(40): cm.sph((random.uniform(-0.4, 0.4), random.uniform(-0.6, 0.6), 1.0 + random.uniform(0, 0.08)), random.uniform(0.06, 0.12), M['coal'], seg=6, ring=4)
cm.ob('cartm', CART, bev=0.01)
LANT = []
GLASS, _ = emat('lglass', '#FFB866', 7.0)
for k, y in enumerate((-6.4, -1.6, 4.8, 11.2, 17.6, 24.0)):
    x = MX0 + (0.6 if k % 2 else -0.6)
    root = empty(f'lant{k}', None, (x, y, THm - 0.22))
    MB().cyl((0, 0, -0.04), 0.07, 0.03, M['brass'], seg=16).cyl((0, 0, -0.14), 0.055, 0.16, GLASS, seg=16).cyl((0, 0, -0.24), 0.075, 0.03, M['brass'], seg=16) \
        .tor((0, 0, 0.01), 0.04, 0.005, M['brass'], rot=(PI / 2, 0, 0), seg=16, rs=6).ob(f'lantm{k}', root, shadow=False)
    lo = light(f'LL{k}', 'POINT', (0, 0, -0.14), None, 55, '#FFAE5C', size=None, cutoff=14); lo.parent = root; lo.data.shadow_soft_size = 0.04
    ph = random.uniform(0, 6.28)
    fn(lo.data, 'energy', 0.0, END, lambda t, ph=ph: 55 * (0.86 + 0.08 * math.sin(t * 13 + ph) + 0.06 * math.sin(t * 29 + 2 * ph)))
    fn(root, 'rotation_euler', 0.0, END, lambda t, ph=ph: (0.05 * math.sin(t * 1.7 + ph), 0.04 * math.sin(t * 1.3 + ph), 0))
    LANT.append(root)
light('CAGEL', 'SPOT', (MX0 + 0.25, 2.2, 2.5), (MX0 - 0.35, 3.2, 1.75), 30, '#FFC88A', spot=28, blend=0.7, size=0.1, cutoff=4)
DAY, _ = emat('daylight', '#EAF2FF', 5.0)
MB().box((0, 0, 0), (TWm + 2, 0.1, THm + 1), DAY).ob('exit', None, (MX0, MY0 - 0.6, THm / 2), smooth=False, shadow=False)
light('EXITL', 'AREA', (MX0, MY0 + 0.3, 1.5), (MX0, 6.0, 0.8), 260, '#DCE8FF', size=2.8, size_y=2.4, cutoff=30)
CGM = V3_ = Vector((MX0 - 0.35, 3.2, 1.62))
MCAGE = empty('mcage', None, tuple(CGM))
mc = MB().cyl((0, 0, 0), 0.16, 0.03, M['brass'], seg=32).tor((0, 0, 0.275), 0.15, 0.004, M['brass'], seg=48, rs=6)
for k in range(18): a = 2 * PI * k / 18; mc.cyl((0.15 * math.cos(a), 0.15 * math.sin(a), 0.145), 0.003, 0.26, M['brass'], seg=6)
for k in range(6): mc.tor((0, 0, 0.275), 0.15, 0.0035, M['brass'], rot=(PI / 2, 0, PI * k / 6), seg=24, rs=6, arc=PI)
mc.tor((0, 0, 0.455), 0.03, 0.005, M['brass'], rot=(PI / 2, 0, 0), seg=16, rs=6).cyl((0, 0, 0.09), 0.005, 0.29, M['timber'], rot=(0, PI / 2, 0), seg=8)
mc.cyl((0, 0, 0.47 + (THm - 0.24 - 1.62 - 0.47) / 2), 0.004, THm - 0.24 - 1.62 - 0.47, M['steel'], seg=6)
mc.ob('mcagem', MCAGE)
fn(MCAGE, 'rotation_euler', 0.0, END, lambda t: (0.02 * math.sin(t * 1.1), 0.015 * math.sin(t * 0.8 + 1), 0.06 * math.sin(t * 0.5)))
# gas: a volume whose front creeps toward the camera, denser near the floor, swirling noise; a little dust always
gm = bpy.data.materials.new('gas')
try: gm.use_nodes = True
except Exception: pass
nt = gm.node_tree; nt.nodes.remove(principled(gm)); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
pv.inputs['Color'].default_value = hx('#B9CB6E'); pv.inputs['Anisotropy'].default_value = 0.35
nt.links.new(pv.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
GY0 = (MY0 + MY1) / 2
tc = nn(gm, 'ShaderNodeTexCoord'); sp = nn(gm, 'ShaderNodeSeparateXYZ'); ln(gm, tc.outputs['Object'], sp.inputs[0])
GFRONT = val(gm, 60.0)
front = mth(gm, 'MULTIPLY', mth(gm, 'SUBTRACT', mth(gm, 'ADD', sp.outputs['Y'], GY0), GFRONT), 0.6, clamp_=True)
low = mth(gm, 'SUBTRACT', 1.15, mth(gm, 'MULTIPLY', mth(gm, 'ADD', sp.outputs['Z'], THm / 2), 0.42), clamp_=True)
nz = nn(gm, 'ShaderNodeTexNoise', noise_dimensions='4D'); nz.inputs['Scale'].default_value = 0.9; nz.inputs['Detail'].default_value = 3.0
ln(gm, tc.outputs['Object'], nz.inputs['Vector']); GW = nz.inputs['W']
wisp = mth(gm, 'MULTIPLY_ADD', nz.outputs['Fac'], 1.8, -0.55, clamp_=True)
dens = mth(gm, 'MULTIPLY_ADD', mth(gm, 'MULTIPLY', mth(gm, 'MULTIPLY', front, low), wisp), 0.55, 0.012)
ln(gm, dens, pv.inputs['Density'])
pv.inputs['Emission Color'].default_value = hx('#A6C94E'); ln(gm, mth(gm, 'MULTIPLY', mth(gm, 'MULTIPLY', front, low), mth(gm, 'MULTIPLY', wisp, 0.7)), pv.inputs['Emission Strength'])
MB().box((0, 0, 0), (TWm + 0.4, MY1 - MY0, THm), gm).ob('gas', None, (MX0, GY0, THm / 2), smooth=False, shadow=False)
tw(GW, 'default_value', 0.0, END, END * 0.35, 'lin')

# ---------- the canary (a glazed ceramic bird) with little notes when it sings ----------
def note(name, parent):
    mb = MB(); mb.sph((0, 0, 0), 0.013, M['note'], seg=12, ring=8, scale=(1.35, 0.55, 1.0))
    mb.box((0.0155, 0, 0.032), (0.004, 0.004, 0.064), M['note']); mb.box((0.024, 0, 0.058), (0.018, 0.004, 0.01), M['note'], rot=(0, rad(-30), 0))
    o = mb.ob(name, parent, (0.1, 0, 0.12), smooth=False, shadow=False); o.scale = (0, 0, 0); return o
def bird(name, parent, loc, s, yaw):
    root = empty(name, parent, loc, (0, 0, yaw)); root.scale = (s, s, s); body = empty(name + '_b', root)
    mb = MB()
    mb.sph((0.0, 0, 0.055), 0.05, M['canary'], seg=24, ring=14, scale=(1.3, 0.85, 0.9))
    mb.sph((0.055, 0, 0.105), 0.034, M['canary'], seg=20, ring=12)
    mb.cyl((0.094, 0, 0.1), 0.011, 0.026, M['beak'], rot=(0, PI / 2, 0), seg=12, r2=0.001)
    for sy in (-1, 1):
        mb.sph((0.074, sy * 0.026, 0.114), 0.0058, M['eye'], seg=10, ring=6)
        mb.sph((-0.008, sy * 0.037, 0.06), 0.04, M['canary_w'], seg=16, ring=10, scale=(1.25, 0.3, 0.6))
        mb.cyl((0.005, sy * 0.014, 0.0), 0.0035, 0.03, M['beak'], seg=8)
    mb.box((-0.088, 0, 0.045), (0.07, 0.04, 0.01), M['canary_w'], rot=(0, rad(-20), 0))
    mb.ob(name + '_m', body)
    return root, body, [note(f'{name}_n{k}', root) for k in range(3)]
def sing(body, notes, ivals, droops):
    on = lambda t: any(a <= t < b for a, b in ivals)
    def dr(t):
        v = 0.0
        for a, b in droops:
            if a <= t: v = max(v, sm((t - a) / 0.35) * (1 - sm((t - b) / 0.3)))
        return v
    fn(body, 'rotation_euler', 0.0, END, lambda t: (0.0, (rad(-7) * math.sin(2 * PI * 2.3 * t) if on(t) else 0.0) + rad(40) * dr(t), 0.0))
    P = 1.1
    for k, n in enumerate(notes):
        def cyc(t, k=k):
            off = k * P / 3; tc_ = math.floor((t - off) / P) * P + off; return tc_, t - tc_
        def loc(t, k=k):
            tc_, age = cyc(t); u = age / P
            return (0.11 + 0.07 * u, 0.012 * math.sin(age * 6 + k), 0.13 + 0.17 * u)
        def scl(t, k=k):
            tc_, age = cyc(t)
            if not on(tc_): return (0.0, 0.0, 0.0)
            v = sm(age / (0.15 * P)) * (1 - sm((age - 0.62 * P) / (0.38 * P))); return (v, v, v)
        fn(n, 'location', 0.0, END, loc); fn(n, 'scale', 0.0, END, scl)
MB_R, MB_B, MB_N = bird('mbird', MCAGE, (0, 0, 0.096), 0.9, PI * 0.88)
# ---------- the wall cage: brass bars in front of the canary group, a plaque with three lamps, the bird on top ----------
CY_ = -0.17
def region(c0, c1, r0, r1): return MXc(c0) - MW / 2 - 0.07, MXc(c1) + MW / 2 + 0.07, MZc(r0) - MHt / 2 - 0.07, MZc(r1) + MHt / 2 + 0.07
def cage(name, c0, c1, r0, r1):
    x0, x1, z0, z1 = region(c0, c1, r0, r1); ox, oz = CANX, CANZ; mb = MB()
    for z in (z0, z1): mb.box(((x0 + x1) / 2 - ox, 0, z - oz), (x1 - x0 + 0.05, 0.05, 0.05), M['brass'])
    for x in (x0, x1): mb.box((x - ox, 0, (z0 + z1) / 2 - oz), (0.05, 0.05, z1 - z0 + 0.05), M['brass'])
    n = max(2, round((x1 - x0) / 0.15))
    for k in range(1, n): mb.cyl((x0 + (x1 - x0) * k / n - ox, 0, (z0 + z1) / 2 - oz), 0.009, z1 - z0, M['brass'], seg=8)
    nz_ = max(1, round((z1 - z0) / 1.12))
    for k in range(1, nz_): mb.box(((x0 + x1) / 2 - ox, 0, z0 + (z1 - z0) * k / nz_ - oz), (x1 - x0, 0.025, 0.025), M['brass'])
    o = mb.ob(name, None, (CANX, CY_, CANZ)); o.scale = (0, 0, 0)
    return dict(o=o, w=x1 - x0, h=z1 - z0, top=((x0 + x1) / 2, z1))
CAGES = [cage('cage1', 4, 4, 3, 3), cage('cage5', 2, 6, 3, 3), cage('cage25', 2, 6, 1, 5), cage('cage100', 0, 9, 0, 9)]
PLQ = empty('plaque', None, (CANX, CY_, 80.0))
PH_ = 0.30
pq = MB().box((0, 0, PH_ / 2), (0.92, 0.16, PH_), M['walnut']).box((0, -0.081, 0.012), (0.93, 0.01, 0.02), M['brass']).box((0, -0.081, PH_ - 0.012), (0.93, 0.01, 0.02), M['brass'])
LAMPS = []
for k, (x, lab) in enumerate(((-0.29, 'CRASHES'), (0.0, 'ERRORS'), (0.29, 'REBOOTS'))):
    lm_ = mat(f'lamp{k}', '#262626', 0.25, emit=0.0, eh='#000000')
    pq.sph((x, -0.08, 0.19), 0.04, lm_, seg=16, ring=8, scale=(1, 0.55, 1)).cyl((x, -0.08, 0.19), 0.05, 0.012, M['brass'], rot=(PI / 2, 0, 0), seg=24)
    LAMPS.append((sock(lm_, 'Emission Color'), sock(lm_, 'Emission Strength')))
    face_txt(f'lab{k}', lab, 'inter_b', 0.03, M['label'], PLQ, x, -0.081, 0.075, space=1.1)
pq.ob('plaquem', PLQ, bev=0.008)
WB_R, WB_B, WB_N = bird('wbird', PLQ, (0.05, 0.0, PH_), 2.6, 0.0)
_pl = light('PLQL', 'SPOT', (0.7, -1.5, 1.2), (0.05, 0.0, 0.42), float(opt('--plql', 60)), '#FFE2B8', spot=32, blend=0.7, size=0.15, cutoff=5); _pl.parent = PLQ
def plq_at(cg): return (cg['top'][0], CY_, cg['top'][1] + 0.025)
def lamps(t, colr, stren, stagger=0.0):
    for k, (cs, ss) in enumerate(LAMPS):
        tw(cs, 'default_value', t + k * stagger, 0.12, hx(colr), 'lin'); tw(ss, 'default_value', t + k * stagger, 0.12, stren, 'lin')
# highlight frames ("a few computers")
HLM, HLS = emat('hl', '#FFC21A', 0.0)
hm = MB()
for (c, r) in ((4, 3), (1, 7), (7, 6)):
    x0, x1, z0, z1 = region(c, c, r, r)
    for z in (z0 + 0.03, z1 - 0.03): hm.box(((x0 + x1) / 2, -0.03, z), (x1 - x0, 0.01, 0.03), HLM)
    for x in (x0 + 0.03, x1 - 0.03): hm.box((x, -0.03, (z0 + z1) / 2), (0.03, 0.01, z1 - z0), HLM)
hm.ob('hlframes', None, smooth=False, shadow=False)
tick('sets built')

# ---------- lights, world ----------
WORLD = bpy.data.worlds.new('w'); sc.world = WORLD
try: WORLD.use_nodes = True
except Exception: pass
WBG = WORLD.node_tree.nodes['Background']; WBG.inputs['Color'].default_value = hx('#0A0E18'); WBG.inputs['Strength'].default_value = 0.5
WALLE = float(opt('--walle', 700))
WL = light('WALLL', 'AREA', (0, -0.5, WCZ), (0, -10, WCZ), WALLE, '#93A9FF', size=WW, size_y=WH, cutoff=70)
for y in (-24.0, -12.0, 0.0): light('CEIL%g' % y, 'AREA', (0, y, HZ - 0.3), (0, y, 0), float(opt('--ceil', 220)), '#FFE7CF', size=44.0, size_y=2.0, shadow=False, cutoff=30)
sd = bpy.data.lights.new('MOON', 'SUN'); sd.energy = float(opt('--moon', 0.35)); sd.color = hx('#9DB2FF')[:3]; sd.angle = rad(1.5)
MOON = bpy.data.objects.new('MOON', sd); col.objects.link(MOON); MOON.rotation_euler = Vector((0.25, -0.8, -0.55)).to_track_quat('-Z', 'Y').to_euler()
for x in (-14.0, 14.0): light('KSPOT%g' % x, 'SPOT', (x, -5.0, 5.0), (x, -3.2, 1.0), 700, '#FFE2C2', spot=40, blend=0.7, size=0.2, cutoff=12)
for x, y in ((-17.0, 42.0), (22.0, 45.0)): light('MAST%g' % x, 'SPOT', (x + 8, y - 14, 18), (x, y, 3), float(opt('--mast', 20000)), '#FFB46A', spot=50, blend=0.6, size=0.5, cutoff=60)
light('ATMS', 'SPOT', (AX + 0.5, -1.9, 3.1), (AX, 0.3, 1.2), 450, '#E6EEFF', spot=48, blend=0.8, size=0.2, cutoff=10)
light('WARDL', 'AREA', (HXs - 0.2, -0.4, 3.0), (HXs - 0.2, -0.4, 0.0), 150, '#E6F2FF', size=2.5, size_y=1.5, cutoff=10)
haze('haze', (0.0, (HY0 + HY1) / 2, HZ / 2), (2 * HXW, HY1 - HY0, HZ), float(opt('--haze', 0.004)), 0.5, '#D6DEF0')

# ---------- timeline ----------
random.seed(3)
WBLUE, WNORM = hx('#3D86FF')[:3], hx('#93A9FF')[:3]
# L0: one update to every screen, then blue screens in a wave out from one of them; an ATM, a ward monitor, the kiosks
for mo in MONS: mo.install(tONE + 0.08 + random.uniform(0, 0.45), tAIR - 0.25 + random.uniform(-0.6, 0.2))
for mo in MONS: mo.crash_(tAIR + 0.04 + 0.055 * gd(mo, CAN) + random.uniform(0, 0.06))
tw(WL.data, 'color', tAIR + 0.1, 0.45, WBLUE, 'out'); tw(WL.data, 'energy', tAIR + 0.1, 0.45, WALLE * 1.6, 'out')
for i, (cr, lm) in enumerate(KIOSK): crash_small(cr, lm, tAIR + 0.2 + 0.06 * i)
crash_small(*ATM, tBANKS + 0.22); crash_small(*WARD, tHOSP + 0.22)
# L2: rewind: the screens come back, converging on three; they light up yellow on "a few"
for mo in MONS: mo.k('crash', tWHAT + 0.12 + 0.05 * (8.0 - gd(mo, CAN)), 0.14, 0.0, 'lin'); mo.set_('dl', tWHAT + 0.1, 0.0)
tw(WL.data, 'color', tWHAT + 0.2, 0.6, WNORM, 'io'); tw(WL.data, 'energy', tWHAT + 0.2, 0.6, WALLE, 'io')
for cr, lm in KIOSK: st(cr, 'default_value', CT(tWHAT), 0.0)
tw(HLS, 'default_value', tFEW - 0.05, 0.25, 5.0, 'out'); st(HLS, 'default_value', CT(tCOAL), 0.0)
# L3: the mine: gas creeps toward the cage, the canary stops singing, the cart rolls out
st(GFRONT, 'default_value', 0.0, 60.0); st(GFRONT, 'default_value', tPOISON - 0.4, 34.0)
tw(GFRONT, 'default_value', tPOISON - 0.4, tTINY + 0.7 - tPOISON, 2.6, 'lin'); tw(GFRONT, 'default_value', tTINY + 0.3, 3.0, -6.0, 'lin')
sing(MB_B, MB_N, [(0.0, tSING + 0.05)], [(tSING + 0.12, END)])
tw(CART, 'location', tEVERYONE + 0.05, 1.5, (MX0, -10.0, 0), 'in2')
# L4: the cage comes down over one screen; the canary lands on top
C1, C5, C25, C100 = CAGES
st(C1['o'], 'scale', CT(tSOFT), (1, 1, 1)); st(C1['o'], 'location', CT(tSOFT), (CANX, CY_, CANZ + 3.5))
tw(C1['o'], 'location', tSOFT + 0.3, 0.9, (CANX, CY_, CANZ), 'back2')
st(PLQ, 'location', CT(tSOFT), (plq_at(C1)[0], CY_, plq_at(C1)[2] + 3.5))
tw(PLQ, 'location', tSOFT + 0.3, 0.9, plq_at(C1), 'back2')
sing(WB_B, WB_N, [(tSOFT + 1.3, tSPIKE + 0.05), (tROLLS + 0.6, tONE3 + 0.05), (tMIN + 0.45, END)], [(tSPIKE + 0.12, tROLLS + 0.5), (tONE3 + 0.12, tMIN + 0.4)])
CAN.install(tNEW + 0.3, tFIRST - 0.55); CAN.wipe(tFIRST - 0.52)
# L5: watch -> spike -> automatic rollback
for k, tt in enumerate((tCR, tER, tRB)): tw(LAMPS[k][0], 'default_value', tt, 0.1, hx('#33E07A'), 'lin'); tw(LAMPS[k][1], 'default_value', tt, 0.1, 7.0, 'lin')
CAN.crash_(tSPIKE + 0.02); lamps(tSPIKE + 0.08, '#FF3B30', 9.0, 0.05)
CAN.rollback(tROLLS + 0.12); lamps(tROLLS + 0.55, '#33E07A', 7.0, 0.06)
# L6: healthy: 1 -> 5 -> 25 -> everyone, the cage grows each time
CAN.set_('ver', CT(tLOOKS), 1.0)
def grow(t, a, b):
    st(a['o'], 'scale', t - 0.02, (0, 0, 0)); st(b['o'], 'scale', t - 0.02, (a['w'] / b['w'], 1, a['h'] / b['h'])); tw(b['o'], 'scale', t, 0.42, (1, 1, 1), 'back2')
    tw(PLQ, 'location', t, 0.42, plq_at(b), 'back2')
grow(t5, C1, C5)
for k, c in enumerate((3, 5, 2, 6)): MG[(c, 3)].wipe(t5 + 0.15 + 0.07 * k)
grow(t25, C5, C25)
for c in range(2, 7):
    for r in range(1, 6):
        if r != 3: MG[(c, r)].wipe(t25 + 0.12 + random.uniform(0, 0.35))
grow(tALLX, C25, C100)
for mo in MONS:
    if not (2 <= mo.c <= 6 and 1 <= mo.r <= 5): mo.wipe(tALLX + 0.05 + 0.045 * gd(mo, CAN) + random.uniform(0, 0.05))
# L7: the wall shows the plan
for mo in MONS: mo.k('s1', tSTAGES + 0.05 + 0.03 * mo.c, 0.35, 1.0, 'io')
# L8: replay the same bad file with a canary
for mo in MONS: mo.set_('s1', CT(tSAME), 0.0); mo.set_('ver', CT(tSAME), 0.0)
st(C100['o'], 'scale', CT(tSAME), (0, 0, 0)); st(C1['o'], 'scale', CT(tSAME), (1, 1, 1)); st(C1['o'], 'location', CT(tSAME), (CANX, CY_, CANZ)); st(PLQ, 'location', CT(tSAME), plq_at(C1))
CAN.install(tSAME + 0.12, tONE3 - 0.03); CAN.crash_(tONE3); lamps(tONE3 + 0.06, '#FF3B30', 9.0, 0.05)
CAN.rollback(tMIN); lamps(tMIN + 0.4, '#33E07A', 7.0, 0.06)
def takeoff(t):
    x = -60.0 + 85.0 * (t - tNOT); k = sm((t - (tNOT + 0.25)) / 0.9)
    return (x, 150.0, 3.1 + 14.0 * max(0.0, t - (tNOT + 0.35)) ** 2)
fn(TP, 'location', tNOT - 1.0, END, takeoff)
fn(TP, 'rotation_euler', tNOT - 1.0, END, lambda t: (0.0, -rad(9) * sm((t - (tNOT + 0.2)) / 0.8), 0.0))
# L9: the wall says the names; the canary sits on top of it all
st(C1['o'], 'scale', CT(tTHATS), (0, 0, 0)); st(PLQ, 'location', CT(tTHATS), plq_at(C100))
for mo in MONS:
    mo.set_('ver', CT(tTHATS), 1.0)
    mo.k('s2', tARGO - 0.15 + 0.025 * mo.c, 0.3, 1.0, 'io'); mo.k('s3', tAWS - 0.15 + 0.025 * mo.c, 0.3, 1.0, 'io')
    mo.k('s2', tCTA - 0.3, 0.4, 0.0, 'io'); mo.k('s3', tCTA - 0.3, 0.4, 0.0, 'io')
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
CANP = V3(CANX, -0.03, CANZ); WC = V3(0.0, 0.0, WCZ)
PLZ = plq_at(C1)[2]
# L0 one screen, then the whole wall, all installing
def _s0(t, u, e, s):
    k = EZ['io'](clamp((t - 2.75) / 2.7))
    P0 = V3(CANX + 0.16, -1.5 + 0.16 * EZ['out'](clamp(t / 2.75)), CANZ + 0.04)
    return P0.lerp(V3(1.4, -13.6, WCZ - 0.2), k), CANP.lerp(WC, k)
shot(0.0, (0, 0, 0), (0, 0, 1), None, None, 40, 2.8, fnP=_s0)
shot(tAIR, (-5.2, -6.2, 1.6), (0.6, 0.0, 6.4), (-4.7, -5.7, 1.7), None, 22, 4.0)
shot(tBANKS, (AX + 0.3, -0.95, 1.5), (AX, 0.07, 1.33), (AX + 0.24, -0.8, 1.47), None, 32, 2.8)
shot(tHOSP, (HXs + 0.12, -0.5, 1.64), (HXs + 0.45, 0.29, 1.56), (HXs + 0.16, -0.36, 1.62), None, 35, 2.8)
shot(tBLUE, (0.6, -17.5, 0.95), (0.0, 0.0, 6.3), (0.4, -15.6, 1.05), None, 24, 5.0)
shot(tALL, (-15.9, -5.6, 1.45), (-13.0, -3.1, 1.25), (-14.6, -5.7, 1.5), (-12.4, -3.0, 1.3), 32, 3.5)
# L1 grounded / paper
shot(tFLIGHTS, (-9.5, -13.5, 0.9), (0.0, 0.0, 5.6), (-8.4, -12.6, 1.0), None, 24, 4.0)
shot(tHOSP2, (HXs - 0.4, -1.0, 1.28), (HXs - 0.45, -0.62, 0.84), (HXs - 0.42, -0.9, 1.15), None, 40, 2.8)
# L2 what if
shot(tWHAT, (0.4, -12.5, 6.2), WC, (0.0, -9.2, 6.8), V3(0.0, 0.0, 7.0), 30, 5.0, ez='io')
# L3 the mine
shot(tCOAL, (MX0 + 0.75, -4.6, 1.25), (MX0 - 0.1, 14.0, 1.35), (MX0 + 0.7, -3.3, 1.3), None, 26, 4.0)
CGC = CGM + V3(0, 0, 0.15)
shot(tTOOK, CGC + V3(0.42, -0.72, 0.08), CGC, CGC + V3(0.36, -0.6, 0.1), None, 50, 2.2)
shot(tPOISON, (MX0 + 1.0, -0.9, 0.8), (MX0 - 0.3, 16.0, 0.95), (MX0 + 0.95, -0.4, 0.82), None, 26, 5.0)
BM = CGM + V3(0, 0, 0.18)
shot(tSTOPS - 0.12, BM + V3(0.06, -0.45, 0.05), BM, BM + V3(0.05, -0.38, 0.04), None, 55, 4.5)
shot(tEVERYONE, (MX0 - 0.5, 7.6, 1.5), (MX0, -9.0, 1.1), (MX0 - 0.45, 6.6, 1.45), None, 28, 6.0)
# L4 the cage over one screen, then 1%
shot(tSOFT, (CANX + 1.3, -3.4, CANZ + 0.2), CANP + V3(0, 0, 0.45), (CANX + 1.1, -3.05, CANZ + 0.25), None, 30, 3.5)
def _s15(t, u, e, s):
    k = EZ['io'](clamp((t - (tONEP - 0.55)) / 1.9))
    return V3(CANX + 0.35, -2.4, CANZ + 0.3).lerp(V3(1.2, -13.4, WCZ - 0.3), k), (CANP + V3(0, 0, 0.2)).lerp(WC, k)
shot(tNEW, (0, 0, 0), (0, 0, 1), None, None, 30, 3.5, fnP=_s15)
# L5 watch / spike / roll back
shot(tWATCH, (CANX + 0.45, -2.4, PLZ + 0.4), (CANX, CY_, PLZ + 0.22), (CANX + 0.38, -2.15, PLZ + 0.36), None, 40, 3.2)
shot(tSPK, (CANX - 1.0, -2.9, CANZ + 0.5), (CANX, 0.0, CANZ + 0.4), (CANX - 0.85, -2.6, CANZ + 0.5), None, 32, 3.5)
shot(tOTHER, (-1.8, -15.5, 4.2), WC, (-0.8, -15.0, 4.5), None, 26, 6.0)
# L6 crane out as the cage grows
def _s19(t, u, e, s):
    k = EZ['io'](clamp((t - (t5 - 0.3)) / (tALLX + 0.6 - (t5 - 0.3))))
    return V3(CANX + 0.6, -3.0, CANZ + 0.6).lerp(V3(0.3, -15.4, WCZ), k), (CANP + V3(0, 0, 0.45)).lerp(WC + V3(0, 0, 0.3), k)
shot(tLOOKS, (0, 0, 0), (0, 0, 1), None, None, 30, 4.0, fnP=_s19)
# L7 the plan
shot(tAFTER, (6.5, -10.5, 1.8), (0.0, 0.0, 7.0), (5.0, -9.6, 2.2), None, 24, 6.0)
shot(tSTAGES, (0.0, -12.9, WCZ + 0.2), WC + V3(0, 0, 0.2), (0.0, -11.8, WCZ + 0.2), None, 30, 6.0)
# L8 the replay, then the world carries on
shot(tSAME, (CANX + 1.1, -3.0, CANZ + 0.3), (CANX, 0.0, CANZ + 0.45), (CANX + 0.9, -2.7, CANZ + 0.32), None, 32, 3.5)
shot(tNOT, (-9.0, -26.0, 2.6), (3.0, 14.0, 6.0), (-8.6, -25.0, 2.7), None, 24, 8.0)
# L9 the names
shot(tTHATS, (0.0, -12.6, WCZ + 0.2), WC + V3(0, 0, 0.2), (0.0, -11.4, WCZ + 0.2), None, 30, 6.0)
# L10 orbit
G23 = WC + V3(0, 0, -0.3)
shot(tCTA, orbit(G23, -28, 17.0, -2.4), G23, None, None, 26, 6.0, fnP=lambda t, u, e, s: (orbit(G23, -28 + 16 * EZ['io'](u), 17.0, -2.4 + 0.6 * u), G23), ez='io')
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
