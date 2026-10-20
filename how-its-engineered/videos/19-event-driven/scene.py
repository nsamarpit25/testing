# 19 Event-Driven Architecture: "The Event Yard". A bright 1960s Swiss-modernist rail depot: pale board-formed concrete,
# north-light roof, a steel window wall onto a cool morning sky. Events are signal-yellow ORDER PLACED tablets standing
# in a numbered row on the EVENT LOG platform; services are teal rail cars on stepped tracks below it (where a car
# stands is how far it has read); the ORDERS press at the left end never moves. Door-bell vignette at X 38..42, maker's
# pier with the Kafka / EventBridge plates. Spec: design.md. Timed to voice/words.json.
# usage: blender -b -P videos/19-event-driven/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 32] [--stills 3,20] [--range a,b] [--skip] [--cutfix]
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
random.seed(19)
PI = math.pi; rad = math.radians; FR = 1.0 / FPS

# ---------- word times ----------
tTAP, tONE, tLATER, tEMAIL, tTRACK, tREW, tALL, tNOBODY = W('tap'), L(0, 1), W('later'), W('email'), W('tracking'), W('rewards'), W('all'), L(0, 2)
tSLOW, tASKING, tANY1, tNEW1, tANY2, tALLDAY = L(1, 0), W('asking'), W('anything'), W('new'), L(1, 1), L(2, 0) - 1.12
tALLDAY = W('all', 12)
tSPOT, tALMOST, tNO, tTHOUS, tDROWNS, tCALLING, tTHEN, tKNOW, tEVERYONE = L(2, 0), L(3, 0), W('no', 15), L(3, 1), W('drowns'), L(3, 2), W('then'), W('know', 21), W('everyone')
tFIX, tEVENT, tDRIVEN, tORDER4, tJUST, tANNOUNCES, tFACT, tPLACED = L(4, 0), W('event', 23), W('driven'), L(4, 1), W('just'), W('announces'), W('fact'), W('placed', 27)
tTHATS, tLOG, tKEEPS, tINORDER = L(5, 0), W('log', 29), W('keeps'), W('order', 30.3)
tEMAIL2, tTRACK2, tREW2, tREACTS = L(5, 1), W('tracking', 31), W('rewards', 32), W('reacts')
tLIKE, tYOU, tCHECKING, tDOOR, tIT, tRINGS, tANSWER = L(6, 0), W('you', 35), W('checking'), W('door'), L(6, 1), W('rings'), W('answer')
tREWD, tREADS, tCATCHES, tUP, tNEWS, tREPLAYS, tEVENTS = L(7, 0), W('reads'), W('catches'), W('up', 41), L(7, 1), W('replays'), W('events')
tPROD, tDOESNT, tLISTEN, tSTOP, tSTART, tREACTING = L(8, 0), W('doesnt'), W('listening'), L(9, 0), W('start'), W('reacting')
tAPACHE0, tKAFKA, tAMAZON, tCTA = L(10, 0), W('kafka'), W('amazon'), L(11, 0)

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

M = {}
M['teal'] = mat('teal', '#1F5F66', 0.40); rough_noise(M['teal'], 0.36, 0.46, 8.0)
M['teal_deep'] = mat('teal_deep', '#143F45', 0.50)
M['yellow'] = mat('yellow', '#F0B429', 0.45)
M['yellow_btn'] = mat('yellow_btn', '#F0B429', 0.35)
M['cream'] = mat('cream', '#EEE6D6', 0.50)
M['paper'] = mat('paper', '#F5F0E6', 0.75); bump(M['paper'], 260, 0.03)
M['ink'] = mat('ink', '#1B2A2F', 0.60)
M['ink_red'] = mat('ink_red', '#C8432C', 0.60)
M['vermilion'] = mat('vermilion', '#D2452E', 0.45)
M['brass'] = mat('brass', '#C6A15B', 0.32, 1.0)
M['brass_satin'] = mat('brass_satin', '#B8955A', 0.48, 1.0)
M['riser'] = mat('riser', '#A9A398', 0.85)
M['oak'] = mat('oak', '#A47A52', 0.55)
m = M['oak']; tc = nn(m, 'ShaderNodeTexCoord'); mp = nn(m, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, 8, 1)
ln(m, tc.outputs['Object'], mp.inputs['Vector']); nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6.0; ln(m, mp.outputs[0], nz.inputs['Vector'])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx('#8E6744'); cr.color_ramp.elements[1].color = hx('#B48A60')
ln(m, nz.outputs['Fac'], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
M['steel'] = mat('steel', '#55595B', 0.40, 0.85)
M['rail'] = mat('rail', '#55595B', 0.30, 0.85)
M['charcoal'] = mat('charcoal', '#262829', 0.65)
M['silh'] = mat('silh', '#6F7C86', 0.9)
def concrete(name, h, rough, wave_=True):
    m = mat(name, h, rough); tc = nn(m, 'ShaderNodeTexCoord')
    nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; ln(m, tc.outputs['Object'], nz.inputs['Vector'])
    f = mth(m, 'MULTIPLY_ADD', nz.outputs['Fac'], 0.06, 0.97)
    if wave_:
        wv = nn(m, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z', wave_profile='SAW'); wv.inputs['Scale'].default_value = 0.9
        wv.inputs['Distortion'].default_value = 0.0; ln(m, tc.outputs['Object'], wv.inputs['Vector'])
        f = mth(m, 'MULTIPLY', f, mth(m, 'MULTIPLY_ADD', wv.outputs['Fac'], 0.08, 0.96))
    mu = nn(m, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mu.inputs['Factor'].default_value = 1.0; mu.inputs[6].default_value = hx(h)
    cc = nn(m, 'ShaderNodeCombineXYZ'); [ln(m, f, cc.inputs[i]) for i in range(3)]
    ln(m, cc.outputs[0], mu.inputs[7]); ln(m, mu.outputs[2], sock(m, 'Base Color')); return m
def mth(m, op, a, b=None, c=None, clamp_=False):
    n = nn(m, 'ShaderNodeMath', operation=op, use_clamp=clamp_)
    for i, x in enumerate((a, b, c)):
        if x is None: continue
        if isinstance(x, (int, float)): n.inputs[i].default_value = x
        else: ln(m, x, n.inputs[i])
    return n.outputs[0]
M['concrete'] = concrete('concrete', '#BEB8AD', 0.88)
M['tierc'] = concrete('tierc', '#BEB8AD', 0.88, False)
M['screed'] = mat('screed', '#B3ACA0', 0.70)
m = M['screed']; tc = nn(m, 'ShaderNodeTexCoord'); vo = nn(m, 'ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 140
ln(m, tc.outputs['Object'], vo.inputs['Vector']); sp = nn(m, 'ShaderNodeSeparateColor'); ln(m, vo.outputs['Color'], sp.inputs[0])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#8E887E'); el[1].position = 0.10; el[1].color = hx('#B3ACA0')
ln(m, sp.outputs[0], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
bp = nn(m, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.015; ln(m, vo.outputs['Distance'], bp.inputs['Height']); ln(m, bp.outputs['Normal'], sock(m, 'Normal'))
M['cobalt'] = M['teal']; M['brick'] = M['vermilion']   # names the ported drum code uses

# ---------- status lamps (half-sphere domes) ----------
LAMPC = dict(amber='#FFB547', cream='#FFF1D6', red='#FF5A3C')
def lamp(name, parent, c, r=0.03, state='cream', level=4.0):
    m = mat(name, '#E2DCCF', 0.30, emit=level if state != 'off' else 0.0, eh=LAMPC.get(state, LAMPC['cream']))
    mb = MB().sph((0, 0, 0), r, m, seg=20, ring=10, scale=(1, 1, 0.8)).tor((0, 0, 0.002), r * 1.08, r * 0.16, M['brass'], seg=24, rs=6)
    mb.ob(name, parent, c); return m
def flick(es, t, level):
    st(es, 'default_value', t, level); st(es, 'default_value', t + FR, level * 0.4); st(es, 'default_value', t + 2 * FR, level)
def lamp_to(m, t, state, level=4.0):
    es = sock(m, 'Emission Strength')
    if state == 'off': tw(es, 'default_value', t, 0.1, 0.0, 'lin'); return
    st(sock(m, 'Emission Color'), 'default_value', t, hx(LAMPC[state])); flick(es, t, level)
def hide(o, t): st(o, 'scale', t, (0.001,) * 3)
def show(o, t, s=(1, 1, 1)): st(o, 'scale', t, s)

# ---------- component kit ----------
def plate(name, parent, c, w, h, cap, text, desc=None, font='din', space=1.15):
    """cream enamel plate on a brass rim with two screws, facing -Y. c = centre of its back on the face."""
    root = empty(name, parent, c)
    mb = MB().box((0, -0.003, 0), (w + 0.024, 0.006, h + 0.024), M['brass']).box((0, -0.010, 0), (w, 0.012, h), M['cream'])
    for sx in (-1, 1): mb.cyl((sx * (w / 2 - 0.022), -0.017, 0), 0.010, 0.004, M['brass'], rot=(PI / 2, 0, 0), seg=12)
    mb.ob(name + '_p', root, bev=0.004)
    fw = w - 0.08
    if desc:
        face_txt(name + '_n', text, font, cap, M['ink'], root, 0, -0.016, h * 0.14, space=space, fit=fw)
        face_txt(name + '_d', desc, 'serif_i', cap * 0.42, M['ink'], root, 0, -0.016, -h * 0.30, fit=fw)
    else: face_txt(name + '_n', text, font, cap, M['ink'], root, 0, -0.016, 0, space=space, fit=fw)
    return root
def label(name, parent, c, text, cap=0.03, m=None, space=1.35, font='inter_sb'):
    return face_txt(name, text, font, cap, m or M['ink'], parent, c[0], c[1], c[2], space=space)

def tag(name, parent, c, text, w, h, cap, red=True):
    """enamel tag hung from a brass hook by two short steel rods; root at the hook (top). drops in with a damped swing."""
    root = empty(name, parent, c)
    mb = MB().box((0, 0, -0.035 - h / 2), (w, 0.012, h), M['vermilion'] if red else M['cream'])
    for sx in (-1, 1): mb.cyl((sx * w * 0.3, 0, -0.018), 0.003, 0.036, M['steel'], seg=6)
    mb.box((0, 0, 0.0), (w * 0.7, 0.008, 0.006), M['steel']).tor((0, 0, 0.012), 0.012, 0.003, M['brass'], rot=(PI / 2, 0, 0), seg=16, rs=6)
    mb.ob(name + '_m', root, bev=0.003)
    face_txt(name + '_t', text, 'dinc', cap, M['cream'] if red else M['ink'], root, 0, -0.006, -0.035 - h / 2, space=1.08, fit=w - 0.03)
    return root
def tag_drop(o, t, z_from=0.35, dur=1.0):
    """hidden until t, then drops in and swings +-5 deg about X, decaying over dur."""
    c = Vector(o.location); hide(o, -1); show(o, t)
    fn(o, 'location', t, t + 0.18, lambda tt, c=c: (c.x, c.y, c.z + z_from * (1 - EZ['in2'](clamp((tt - t) / 0.18)))))
    fn(o, 'rotation_euler', t, t + dur, lambda tt: (rad(5) * math.sin(2 * PI * 2.2 * (tt - t)) * math.exp(-4 * (tt - t)) * (tt > t + 0.18), 0, 0))
def tag_lift(o, t, z_to=0.5):
    c = Vector(o.location); tw(o, 'location', t, 0.25, (c.x, c.y, c.z + z_to), 'in2'); hide(o, t + 0.26)

# ---------- event tablet ----------
TABW, TABD, TABH = 0.50, 0.07, 0.80
def tablet(n, parent=None, blank=False):
    root = empty(f'tab{n:02d}', parent)
    mb = MB().box((0, 0, 0), (TABW, TABD, TABH), M['yellow'])
    fy = -TABD / 2
    if not blank: mb.box((0, fy - 0.0004, -0.12), (0.40, 0.0008, 0.004), M['ink'])
    mb.ob(root.name + '_m', root, bev=0.02)
    if blank: return root
    face_txt(root.name + '_e', 'EVENT', 'inter_sb', 0.032, M['ink'], root, 0, fy, 0.33, space=1.35)
    face_txt(root.name + '_o', 'ORDER', 'dinc', 0.14, M['ink'], root, 0, fy, 0.17, space=1.04, fit=0.44)
    face_txt(root.name + '_p', 'PLACED', 'dinc', 0.13, M['ink'], root, 0, fy, -0.01, space=1.04, fit=0.44)
    face_txt(root.name + '_n', f'#{n:04d}', 'mono', 0.055, M['ink'], root, 0, fy, -0.21)
    face_txt(root.name + '_f', 'from orders', 'serif_i', 0.03, M['ink'], root, 0, fy, -0.31)
    return root

# ---------- service car ----------
LANE = dict(A=(-2.65, 0.0), B=(-2.05, 0.34), C=(-1.45, 0.68), D=(-0.85, 1.02))
XS = lambda n: -5.10 if n == 0 else -4.70 + 0.62 * (n - 1)
DEPOT = 0.6
class Car:
    def __init__(s, name, lane, desc):
        ly, tz = LANE[lane]; s.name, s.ly, s.tz = name, ly, tz; s.moves = []; s.zf = None
        s.ob = empty('car_' + name, None, (DEPOT, ly, tz))
        mb = MB().box((0, 0, 0.18), (0.70, 0.40, 0.08), M['charcoal']).box((0, 0, 0.37), (0.66, 0.44, 0.30), M['teal'])
        mb.box((0, 0, 0.245), (0.668, 0.448, 0.012), M['brass'])
        for sx in (-1, 1): mb.cyl((sx * 0.355, 0, 0.18), 0.04, 0.016, M['brass'], rot=(0, PI / 2, 0), seg=20).cyl((sx * 0.34, 0, 0.18), 0.012, 0.03, M['steel'], rot=(0, PI / 2, 0), seg=8)
        mb.ob('car_' + name + '_body', s.ob, bev=0.025)
        s.axles = []
        for ax in (-0.22, 0.22):
            w = MB()
            for sy in (-1, 1):
                w.cyl((0, sy * 0.18, 0), 0.07, 0.035, M['charcoal'], rot=(PI / 2, 0, 0), seg=24).cyl((0, sy * 0.2, 0), 0.045, 0.012, M['brass'], rot=(PI / 2, 0, 0), seg=16)
                w.box((0, sy * 0.207, 0), (0.08, 0.004, 0.012), M['charcoal'])
            w.cyl((0, 0, 0), 0.012, 0.36, M['steel'], rot=(PI / 2, 0, 0), seg=8)
            s.axles.append(w.ob(f'car_{name}_ax{ax:+.2f}', s.ob, (ax, 0, 0.12)))
        plate('pl_' + name, s.ob, (0, -0.22, 0.37), 0.58, 0.17, 0.085, name, space=1.15 if len(name) < 8 else 1.05)
        s.lamp = lamp('lp_' + name, s.ob, (0.25, -0.15, 0.52), 0.03, 'cream')
    def x_at(s, t):
        x = DEPOT
        for sg in sorted(s.moves, key=lambda g: g[1]):
            k, t0 = sg[0], sg[1]
            if t < t0: return x
            if k == 'to':
                _, _, dur, x1, ez = sg
                if t < t0 + dur: return x + (x1 - x) * EZ[ez]((t - t0) / dur)
                x = x1
            else:
                _, _, t1, f = sg
                if t < t1: return f(t)
                x = f(t1)
        return x
    def to(s, t, x1, dur=0.22, ez='io'): s.moves.append(('to', t, dur, x1, ez))
    def put(s, t, x1): s.moves.append(('to', t, 0.0001, x1, 'lin'))
    def path(s, t0, t1, f): s.moves.append(('fn', t0, t1, f))
    def fin(s):
        zf = s.zf or (lambda t: 0.0)
        fn(s.ob, 'location', 0.0, END, lambda t: (s.x_at(t), s.ly, s.tz + zf(t)))
        for a in s.axles: fn(a, 'rotation_euler', 0.0, END, lambda t: (0, s.x_at(t) / 0.07, 0))
CARS = {}

def read_fx(car, t, slot):
    """lamp amber -> device fires -> lamp cream 0.3 s later."""
    lamp_to(car.lamp, t, 'amber'); lamp_to(car.lamp, t + 0.32, 'cream'); car.fire(t + 0.02, slot)
def hop(car, t, slot, dur=0.22, fx=True):
    car.to(t, XS(slot), dur, 'io')
    if fx: read_fx(car, t + dur, slot)
class Drum:
    """mechanical drum (decagon of digits / octagon of words) behind a window housing that stands proud of the face."""
    def __init__(s, name, parent, c, width, face_h, labels, kind='word', red=(), protrude=0.04, cap=None, ext=0.0006, housing=None):
        N = 10 if kind == 'digit' else 8; s.N = N; s.th = 2 * PI / N; s.ev = []; s.idx = {l: i for i, l in enumerate(labels) if l}
        R = face_h / (2 * math.sin(PI / N)); a = R * math.cos(PI / N)
        fx, fy, fz = c; yc = fy - protrude + a + 0.008
        s.ob = empty(name, parent, (fx, yc, fz)); mb = MB()
        for i in range(N):
            an = i * s.th; n = Vector((0, -math.cos(an), math.sin(an)))
            fm = M['cream'] if kind == 'digit' else (M['brick'] if i in red else M['charcoal'])
            mb.box(n * (a - 0.003), (width, 0.006, face_h * 1.004), fm, rot=(-an, 0, 0))
        mb.ob(name + '_m', s.ob)
        font = 'din' if kind == 'digit' else 'dinc'; cap = cap or face_h * (0.62 if kind == 'digit' else 0.48)
        tm = M['ink'] if kind == 'digit' else M['cream']
        for i, lab in enumerate(labels):
            if not lab: continue
            an = i * s.th; n = Vector((0, -math.cos(an), math.sin(an)))
            txt(f'{name}_t{i}', lab, font, cap, tm, s.ob, n * (a + 0.0008 + ext), (PI / 2 - an, 0, 0), ext, space=1.0 if kind == 'digit' else 1.08, fit=width * 0.88)
        hh = math.sqrt(max(R * R - (a + 0.008 - protrude) ** 2, 0.0)) + 0.012; bh = max(hh - face_h / 2, 0.014)
        hw = width / 2 + 0.03; y = fy - protrude / 2; hm = housing or M['cobalt']
        hb = MB()
        for sz in (-1, 1): hb.box((fx, y, fz + sz * (face_h / 2 + bh / 2)), (2 * hw, protrude, bh), hm)
        for sx in (-1, 1): hb.box((fx + sx * (width / 2 + 0.015), y, fz), (0.03, protrude, face_h), hm)
        hb.ob(name + '_h', parent, bev=0.005)
        bz = MB(); yb = fy - protrude - 0.002
        for sz in (-1, 1): bz.box((fx, yb, fz + sz * (face_h / 2 + 0.006)), (width + 0.024, 0.006, 0.012), M['brass'])
        for sx in (-1, 1): bz.box((fx + sx * (width / 2 + 0.006), yb, fz), (0.012, 0.006, face_h), M['brass'])
        bz.ob(name + '_bz', parent, bev=0.002)
        DRUMS.append(s)
    def say(s, t, word, dur=0.24, ez='back'): s.ev.append((t, 'to', s.idx[word], dur, ez))
    def by(s, t, steps, dur, ez='out'): s.ev.append((t, 'by', steps, dur, ez))
    def nudge(s, t, amt=0.35, dur=0.22): s.ev.append((t, 'nudge', amt, dur, None))
    def reset(s, t, i): s.ev.append((t, 'reset', i, 0, None))
    def fin(s):
        pos = 0
        for t, k, v, dur, ez in sorted(s.ev, key=lambda e: e[0]):
            if k == 'to':
                d = (v - pos) % s.N
                if d == 0: continue
                pos += d; tw(s.ob, 'rotation_euler', t, dur, (pos * s.th, 0, 0), ez)
            elif k == 'by': pos += v; tw(s.ob, 'rotation_euler', t, dur, (pos * s.th, 0, 0), ez)
            elif k == 'nudge':
                tw(s.ob, 'rotation_euler', t, dur * 0.35, ((pos + v) * s.th, 0, 0), 'out2'); tw(s.ob, 'rotation_euler', t + dur * 0.35, dur * 0.65, (pos * s.th, 0, 0), 'back')
            elif k == 'reset': pos = v; st(s.ob, 'rotation_euler', t, (pos * s.th, 0, 0))
DRUMS = []

class Odo:
    """odometer: n digit drums with brass comma plates; rolls odometer-style (lower digits spin whole turns)."""
    def __init__(s, name, parent, c, n, ww, wh, commas=(), gap=0.008, cw=0.022, cap=None, protrude=0.04):
        fx, fy, fz = c; seq = []
        for j in range(n):
            seq.append(('d', ww))
            if j in commas: seq.append(('c', cw))
        total = sum(w for _, w in seq) + gap * (len(seq) - 1)
        x = fx - total / 2; s.d = []; s.n = n; s.v = 0; cm = MB(); cx_ = []
        for kind, w in seq:
            cx = x + w / 2
            if kind == 'd': s.d.append(Drum(f'{name}{len(s.d)}', parent, (cx, fy, fz), w, wh, [str(i) for i in range(10)], 'digit', protrude=protrude, cap=cap))
            else: cm.box((cx, fy - protrude / 2 - 0.003, fz), (w + 0.02, protrude + 0.006, wh + 0.03), M['brass']); cx_.append(cx)
            x += w + gap
        if cx_:
            cm.ob(name + '_cm', parent, bev=0.003)
            for i, cx in enumerate(cx_): face_txt(f'{name}_c{i}', ',', 'din', wh * 0.45, M['ink'], parent, cx, fy - protrude - 0.006, fz - wh * 0.28)
    def digits(s, v): return [int(ch) for ch in str(int(v)).zfill(s.n)[-s.n:]]
    def roll(s, t, dur, new, lead_dur=None, lead_ez='back'):
        a, b = s.digits(s.v), s.digits(new); s.v = new
        ch = [j for j in range(s.n) if a[j] != b[j]]
        if not ch: return
        for j in range(ch[0], s.n):
            if j == ch[0]: s.d[j].by(t, (b[j] - a[j]) % 10, lead_dur or dur, lead_ez)
            else:
                k = s.n - 1 - j; revs = [4, 3, 3, 2, 2, 1][k] if k < 6 else 1
                s.d[j].by(t, revs * 10 + (b[j] - a[j]) % 10, dur, 'out')
    def reset(s, t, new):
        s.v = new
        for d, x in zip(s.d, s.digits(new)): d.reset(t, x)

def snap(o, t, loc=None, rot=None, scale=(1, 1, 1)):
    """hide, move, show over two frames (an instant reset that never smears)."""
    hide(o, t)
    if loc is not None: st(o, 'location', t + FR, loc)
    if rot is not None: st(o, 'rotation_euler', t + FR, rot)
    show(o, t + 2 * FR, scale)

# ---------- car devices (roof at local z 0.52; at rest <= 0.14 m tall) ----------
def dev_email(car):
    o = car.ob; n = car.name
    MB().box((0.04, 0.02, 0.56), (0.30, 0.18, 0.08), M['teal']).box((0.04, -0.075, 0.603), (0.26, 0.012, 0.008), M['brass']) \
        .box((0.04, 0.115, 0.603), (0.26, 0.012, 0.008), M['brass']).box((0.04, 0.02, 0.6005), (0.25, 0.03, 0.002), M['charcoal']).ob(n + '_slot', o, bev=0.008)
    tr = MB().box((-0.20, 0.02, 0.523), (0.15, 0.27, 0.006), M['brass'])
    for sx in (-1, 1): tr.box((-0.20 + sx * 0.075, 0.02, 0.545), (0.006, 0.27, 0.04), M['brass'])
    for sy in (-1, 1): tr.box((-0.20, 0.02 + sy * 0.135, 0.545), (0.15, 0.006, 0.04), M['brass'])
    tr.ob(n + '_tray', o)
    stk = MB().box((0, 0, 0.0005), (0.13, 0.23, 0.001), M['paper']).ob(n + '_stack', o, (-0.20, 0.02, 0.526)); stk.scale = (1, 1, 6)
    env = empty(n + '_env', o, (0.04, 0.02, 0.52))
    em = MB().box((0, 0, 0), (0.24, 0.004, 0.14), M['paper'])
    for sx in (-1, 1): em.box((sx * 0.06, -0.0025, 0.03), (0.135, 0.0008, 0.004), M['ink'], rot=(0, sx * rad(30), 0))
    em.ob(n + '_env_m', env)
    car.env, car.stk, car.nstk = env, stk, 6
    def fire(t, slot):
        st(env, 'location', t, (0.04, 0.02, 0.52)); tw(env, 'location', t, 4 * FR, (0.04, 0.02, 0.69), 'back2')
        t2 = t + 7 * FR
        tw(env, 'location', t2, 0.22, (-0.20, 0.02, 0.56 + 0.003 * car.nstk / 3), 'io'); tw(env, 'rotation_euler', t2, 0.22, (-PI / 2, 0, 0), 'io')
        car.nstk = min(car.nstk + 3, 45); st(stk, 'scale', t2 + 0.22, (1, 1, car.nstk))
        snap(env, t2 + 0.22, (0.04, 0.02, 0.52), (0, 0, 0))
    car.fire = fire
def dev_track(car):
    o = car.ob; n = car.name
    MB().box((-0.02, 0.05, 0.56), (0.42, 0.10, 0.08), M['teal']).ob(n + '_stand', o, bev=0.01)
    pan = empty(n + '_pan', o, (-0.02, 0.0, 0.59), (rad(36), 0, 0))
    MB().box((0, 0, -0.012), (0.48, 0.24, 0.008), M['teal_deep']).box((0, 0, -0.005), (0.46, 0.22, 0.010), M['cream']) \
        .box((0, 0.005, 0.0005), (0.30, 0.006, 0.002), M['teal']).ob(n + '_pan_m', pan, bev=0.003)
    dm = mat(n + '_ring', '#E2DCCF', 0.3, emit=0.0, eh=LAMPC['amber']); car.ring = dm
    dt = MB()
    for i, (x, lab) in enumerate(((-0.15, 'PLACED'), (0.0, 'PACKED'), (0.15, 'SHIPPED'))):
        dt.cyl((x, 0.005, 0.002), 0.018, 0.004, M['teal'], seg=20)
        if i == 0: dt.ann((x, 0.005, 0.001), 0.020, 0.028, 0.004, dm, seg=24)
        txt(f'{n}_l{i}', lab, 'inter_sb', 0.022, M['ink'], pan, (x, -0.06, 0.0012), (0, 0, 0), space=1.25)
    dt.ob(n + '_dots', pan)
    txt(n + '_mt', 'ORDER', 'inter_sb', 0.018, M['ink'], pan, (0, 0.075, 0.0012), (0, 0, 0), space=1.35)
    pin = empty(n + '_pin', pan, (-0.15, 0.005, 0.0))
    MB().cyl((0, 0, 0.025), 0.003, 0.05, M['brass'], seg=8).sph((0, 0, 0.06), 0.025, M['yellow'], seg=16, ring=8).ob(n + '_pin_m', pin)
    car.pin = pin
    def fire(t, slot):
        tw(pin, 'location', t, 0.12, (-0.15, 0.005, 0.07), 'out'); tw(pin, 'location', t + 0.14, 3 * FR, (-0.15, 0.005, 0.0), 'in2')
        es = sock(dm, 'Emission Strength'); tc = t + 0.14 + 3 * FR
        flick(es, tc, 5.0); tw(es, 'default_value', tc + 3 * FR, 0.45, 0.0, 'out')
    car.fire = fire
def coin(mb, c, m):
    mb.cyl((c[0], c[1], c[2] + 0.006), 0.045, 0.012, m, seg=28)
    pts = [((0.032 if i % 2 == 0 else 0.013) * math.cos(PI / 2 + i * PI / 5), (0.032 if i % 2 == 0 else 0.013) * math.sin(PI / 2 + i * PI / 5)) for i in range(10)]
    return mb.prism(pts, 0.003, m, c=(c[0], c[1], c[2] + 0.0135))
def dev_rewards(car):
    o = car.ob; n = car.name
    MB().box((-0.11, -0.02, 0.59), (0.24, 0.16, 0.14), M['teal']).ob(n + '_lect', o, bev=0.01)
    car.odo = Odo(n + '_pts', o, (-0.11, -0.10, 0.585), 4, 0.040, 0.05, gap=0.006, protrude=0.012, cap=0.032)
    face_txt(n + '_ptl', 'POINTS', 'inter_sb', 0.012, M['cream'], o, -0.11, -0.10, 0.643, space=1.4)
    MB().cyl((0.17, 0.03, 0.524), 0.05, 0.008, M['brass'], seg=24).ob(n + '_base', o)
    car.tok = []
    for k in range(11):
        tk = coin(MB(), (0, 0, 0), M['brass_satin']).ob(f'{n}_tok{k}', o, (0.17, 0.03, 0.528 + 0.012 * k)); car.tok.append(tk)
    car.ntok = 2
    for k in range(2, 11): tk = car.tok[k]; tk.scale = (0.001,) * 3
    fly = coin(MB(), (0, 0, 0), M['brass_satin']).ob(n + '_fly', o, (0.02, 0.03, 0.50)); fly.scale = (0.001,) * 3
    def fire(t, slot):
        car.odo.roll(t, 0.35, car.odo.v + 50, lead_dur=0.25)
        k = car.ntok
        show(fly, t); st(fly, 'location', t, (0.02, 0.03, 0.50))
        z1 = 0.528 + 0.012 * min(k, 10)
        fn(fly, 'location', t, t + 0.25, lambda tt, z1=z1: (0.02 + 0.15 * clamp((tt - t) / 0.25), 0.03, 0.50 + (z1 - 0.50) * clamp((tt - t) / 0.25) + 0.12 * math.sin(PI * clamp((tt - t) / 0.25))))
        hide(fly, t + 0.25 + FR)
        if k < 11: show(car.tok[k], t + 0.25 + FR); car.ntok = k + 1
    car.fire = fire
def tok_reset(car, t, k):
    for i in range(11): (show if i < k else hide)(car.tok[i], t)
    car.ntok = k
BARINC = [0.010, 0.012, 0.011, 0.013, 0.012, 0.014]
def dev_analytics(car):
    o = car.ob; n = car.name
    MB().box((0.0, 0.03, 0.545), (0.46, 0.14, 0.05), M['teal']).ob(n + '_stand', o, bev=0.01)
    pan = empty(n + '_pan', o, (0.0, 0.0, 0.57), (rad(20), 0, 0))
    pm = MB().box((0, 0, -0.012), (0.48, 0.24, 0.008), M['teal_deep']).box((0, 0, -0.005), (0.46, 0.22, 0.010), M['cream'])
    for y in (-0.07, 0.0, 0.07): pm.box((0, y, 0.0005), (0.42, 0.003, 0.002), M['ink'])
    pm.ob(n + '_pan_m', pan, bev=0.003)
    car.bars, car.bh = [], [0.010, 0.016, 0.022, 0.028, 0.034, 0.040]
    for i in range(6):
        b = MB().box((0, 0, 0.005), (0.045, 0.03, 0.01), M['brass_satin']).ob(f'{n}_bar{i}', o, (-0.15 + 0.06 * i, -0.02, 0.565))
        b.scale = (1, 1, car.bh[i] / 0.01); car.bars.append(b)
    MB().tor((0, 0, 0), 0.03, 0.007, M['brass'], rot=(PI / 2, 0, 0), seg=20, rs=6).ob(n + '_eye', o, (-0.27, 0.12, 0.555))
    def fire(t, slot):
        i = slot % 6; car.bh[i] = min(car.bh[i] + BARINC[i], 0.085)
        tw(car.bars[i], 'scale', t, 0.18, (1, 1, car.bh[i] / 0.01), 'back')
    car.fire = fire

# ---------- hall shell ----------
HALL = []        # (light data, base energy) dimmed for the freeze
HALLEM = []      # (emission socket, base strength)

def light(name, kind, loc, aim=None, energy=100.0, color='#FFFFFF', size=None, size_y=None, spot=None, blend=0.6, vf=1.0, shadow=True, cutoff=30.0, hall=True):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = hx(color)[:3]
    if kind == 'AREA':
        ld.shape = 'RECTANGLE' if size_y else 'DISK'; ld.size = size
        if size_y: ld.size_y = size_y
    elif kind == 'SPOT': ld.spot_size = rad(spot); ld.spot_blend = blend; ld.shadow_soft_size = size or 0.1
    elif kind == 'POINT': ld.shadow_soft_size = size or 0.05
    ld.volume_factor = vf; ld.use_shadow = shadow
    if cutoff: ld.use_custom_distance = True; ld.cutoff_distance = cutoff
    o = bpy.data.objects.new(name, ld); col.objects.link(o); o.location = loc
    if aim: o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if hall: HALL.append((ld, energy))
    return o
def haze(name, c, size, dens, aniso, colr):
    hm_ = bpy.data.materials.new(name)
    try: hm_.use_nodes = True
    except Exception: pass
    nt = hm_.node_tree; nt.nodes.remove(principled(hm_)); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Density'].default_value = dens; pv.inputs['Anisotropy'].default_value = aniso; pv.inputs['Color'].default_value = hx(colr)
    nt.links.new(pv.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    o = MB().box((0, 0, 0), size, hm_).ob(name, None, c, smooth=False, shadow=False); return o, pv.inputs['Density']
def grad_sky(name, lo, hi, strength, z0, z1):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; nt.nodes.remove(principled(m)); out = nt.nodes['Material Output']
    tc = nn(m, 'ShaderNodeTexCoord'); sp = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], sp.inputs[0])
    mr = nn(m, 'ShaderNodeMapRange'); mr.inputs['From Min'].default_value = z0; mr.inputs['From Max'].default_value = z1; ln(m, sp.outputs['Z'], mr.inputs['Value'])
    cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = hx(lo); cr.color_ramp.elements[1].color = hx(hi); ln(m, mr.outputs['Result'], cr.inputs['Fac'])
    e = nn(m, 'ShaderNodeEmission'); e.inputs['Strength'].default_value = strength; ln(m, cr.outputs['Color'], e.inputs['Color']); ln(m, e.outputs[0], out.inputs['Surface'])
    return m, e.inputs['Strength']

# floor, walls, ceiling
MB().box((1.0, -1.5, -0.1), (24.0, 17.0, 0.2), M['screed']).ob('floor', None, smooth=False)
wm = MB()
wm.box((-11.15, -1.5, 3.5), (0.3, 17.0, 7.0), M['concrete']).box((13.15, -1.5, 3.5), (0.3, 17.0, 7.0), M['concrete']).box((1.0, -10.15, 3.5), (24.6, 0.3, 7.0), M['concrete'])
wm.box((1.0, 7.0, 0.45), (24.6, 0.5, 0.9), M['concrete']).box((1.0, 7.0, 6.1), (24.6, 0.5, 1.8), M['concrete'])
PIERX = (-10.0, -6.0, -2.0, 2.0, 6.0, 10.0)
for x in PIERX: wm.box((x, 7.0, 3.05), (0.5, 0.5, 4.3), M['concrete'])
wm.box((1.0, -1.5, 7.1), (24.6, 17.6, 0.2), M['concrete'])
wm.ob('walls', None, smooth=False)
mu_ = MB()
for x in [x0 + 1.2 * i for x0 in (-11.0,) for i in range(21)]: mu_.box((x, 6.9, 3.05), (0.08, 0.08, 4.3), M['teal_deep'])
for z in (0.92, 2.35, 3.78, 5.18): mu_.box((1.0, 6.9, z), (24.0, 0.08, 0.08), M['teal_deep'])
mu_.ob('mullions', None, bev=0.01)
# north-light roof: three sawtooth ridges with skylight strips
SKYM, SKYS = emat('skylight', '#E6F0F8', 3.0); HALLEM.append((SKYS, 3.0))
rf, sk = MB(), MB()
for y in (-4.0, 0.0, 4.0):
    rf.box((1.0, y - 0.6, 6.55), (24.0, 0.25, 1.0), M['concrete']).box((1.0, y + 0.75, 6.6), (24.0, 0.25, 0.8), M['concrete'])
    sk.box((1.0, y + 0.08, 6.97), (12.0, 1.2, 0.02), SKYM)
rf.ob('roof', None, smooth=False); sk.ob('skylights', None, smooth=False, shadow=False)
# window backdrop + silhouettes
SKYB, SKYBS = grad_sky('sky', '#F4E6CF', '#CFE0EE', 1.3, 0.0, 9.0)
MB().box((2.0, 16.0, 6.0), (64.0, 0.1, 20.0), SKYB).ob('backdrop', None, smooth=False, shadow=False)
SILM, _ = emat('silh', '#6F7C86', 0.55)
si = MB()
for x in (-7.0, 0.5, 7.5):
    for sx in (-1, 1): si.box((x + sx * 1.6, 14.0, 3.0), (0.18, 0.18, 6.0), SILM)
    si.box((x, 14.0, 5.8), (3.6, 0.2, 0.35), SILM)
    for k in range(3): si.box((x - 0.9 + 0.9 * k, 14.0, 5.35), (0.25, 0.2, 0.5), SILM)
si.cyl((10.5, 14.5, 6.6), 1.3, 2.2, SILM, seg=24).cyl((10.5, 14.5, 7.8), 0.4, 0.4, SILM, seg=12, r2=0.0)
for sx in (-1, 1):
    for sy in (-1, 1): si.box((10.5 + sx * 0.9, 14.5 + sy * 0.9, 2.75), (0.14, 0.14, 5.5), SILM)
si.box((-4.0, 13.5, 1.0), (7.0, 3.0, 2.0), SILM).box((5.0, 13.0, 0.8), (5.0, 3.0, 1.6), SILM)
si.ob('silhouettes', None, smooth=False, shadow=False)

# ---------- stepped tiers, tracks, slot ticks, riser lettering ----------
TIERS = dict(B=-2.35, C=-1.75, D=-1.15)
tm, nos = MB(), MB()
for k, yf in TIERS.items():
    ly, tz = LANE[k]; ya = -0.55
    tm.box((0.9, (yf + ya) / 2, tz / 2), (13.4, ya - yf, tz), M['tierc'])
    tm.box((0.9, yf - 0.002, tz / 2), (13.4, 0.004, tz - 0.004), M['riser'])
    nos.box((0.9, yf + 0.019, tz - 0.019), (13.42, 0.042, 0.042), M['brass'])
for k, (ly, tz) in LANE.items():
    yf = ly - 0.30
    for n in range(1, 21): nos.box((XS(n), yf + 0.07, tz + 0.0012), (0.012, 0.10, 0.002), M['brass'])
tm.ob('tiers', None, smooth=False); nos.ob('nosings', None, smooth=False)
trk = MB(); STEMP = tpl_ = None
for k, (ly, tz) in LANE.items():
    trk.box((1.075, ly, tz + 0.0025), (13.05, 0.56, 0.005), M['charcoal'])
    x = -5.40
    while x < 7.6: trk.box((x, ly, tz + 0.015), (0.08, 0.50, 0.02), M['oak']); x += 0.31
    for sy in (-1, 1): trk.box((1.075, ly + sy * 0.18, tz + 0.04), (13.05, 0.025, 0.03), M['rail'])
trk.ob('tracks', None, smooth=False)
for k, word in (('B', 'REWARDS'), ('C', 'TRACKING'), ('D', 'EMAIL')):
    ly, tz = LANE[k]; prev = {'B': 0.0, 'C': 0.34, 'D': 0.68}[k]
    for i, x in enumerate((-4.15, -1.05, 2.05, 5.15)):
        face_txt(f'riser_{k}{i}', word, 'din', 0.16, M['cream'], None, x, TIERS[k] - 0.004, (prev + tz) / 2, ext=0.001, space=1.15)

# ---------- EVENT LOG platform ----------
pf = MB().box((1.15, 0.2, 0.87), (12.7, 1.5, 1.74), M['concrete']).box((1.15, 0.2, 1.77), (12.74, 1.54, 0.06), M['oak'])
pf.box((1.15, -0.556, 1.55), (12.7, 0.012, 0.20), M['cream'])
for n in range(1, 21):
    pf.box((XS(n), -0.565, 1.625), (0.006, 0.004, 0.03), M['brass'])
    pf.box((XS(n), -0.30, 1.81), (0.56, 0.10, 0.02), M['brass_satin']).box((XS(n), -0.30, 1.8205), (0.50, 0.072, 0.002), M['charcoal'])
pf.box((1.15, 0.45, 2.085), (12.7, 0.03, 0.03), M['brass'])
for x in [-5.0 + 1.24 * i for i in range(11)]: pf.box((x, 0.45, 1.935), (0.025, 0.025, 0.27), M['steel'])
pf.box((-5.40, 0.45, 2.10), (0.42, 0.14, 0.02), M['brass'])
pf.ob('platform', None, bev=0.004)
for n in range(1, 21): face_txt(f'ruler{n}', f'{n:04d}', 'din', 0.07, M['ink'], None, XS(n), -0.562, 1.535, space=1.05)
CARRIER = MB().box((0, 0, 0), (0.50, 0.10, 0.04), M['brass_satin']).box((0, 0, 0.026), (0.52, 0.02, 0.012), M['brass']).ob('carrier', None, (-5.20, 0.45, 2.13), bev=0.006)
# blade sign
SIGN = empty('sign', None, (1.0, -0.40, 3.85))
MB().box((0, 0, 0), (2.2, 0.05, 0.50), M['teal']).box((0, -0.0255, 0), (2.08, 0.001, 0.40), M['cream']).box((0, -0.0262, 0), (2.06, 0.001, 0.38), M['teal']) \
    .ob('sign_m', SIGN, bev=0.012)
face_txt('sign_t', 'EVENT LOG', 'dinc', 0.28, M['cream'], SIGN, 0, -0.027, 0, ext=0.012, space=1.12)
MB().cyl((-0.8, 0, 1.75), 0.008, 3.0, M['steel'], seg=8).cyl((0.8, 0, 1.75), 0.008, 3.0, M['steel'], seg=8).ob('sign_rods', SIGN)
# platform lamps
SHADE_IN = mat('shade_in', '#EEE6D6', 0.5, emit=0.3, eh='#FFE3B3'); PBULB = mat('pbulb', '#E2DCCF', 0.25, emit=10.0, eh='#FFE3B3')
LAMPX = [-4.39 + 1.24 * k for k in range(10)]; LAMPS = []
ps, pb_ = MB(), MB()
for i, x in enumerate(LAMPX):
    tube(f'neck{i}', [(x, 0.90, 1.80), (x, 0.90, 3.30), (x, 0.70, 3.52), (x, 0.20, 3.52), (x, -0.05, 3.44)], 0.012, M['brass'])
    ps.cyl((x, -0.05, 3.32), 0.16, 0.20, M['teal_deep'], seg=32, r2=0.05, caps=False).cyl((x, -0.05, 3.32), 0.155, 0.195, SHADE_IN, seg=32, r2=0.047, caps=False)
    ps.cyl((x, -0.05, 3.43), 0.035, 0.03, M['brass'], seg=12)
    pb_.sph((x, -0.05, 3.28), 0.035, PBULB, seg=16, ring=8)
    LAMPS.append(light(f'LAMP{i}', 'POINT', (x, -0.05, 3.25), None, 55, '#FFE3B3', size=0.04, vf=0.25, hall=False))
ps.ob('lamp_shades'); pb_.ob('lamp_bulbs', shadow=False)
# station clock on the pier at x -2
CLK = (-2.0, 6.72, 4.3)
ck = MB().cyl(CLK, 0.45, 0.04, M['cream'], rot=(PI / 2, 0, 0), seg=64).tor((CLK[0], CLK[1] - 0.01, CLK[2]), 0.46, 0.03, M['teal'], rot=(PI / 2, 0, 0), seg=64, rs=10)
for i in range(12):
    a = i * PI / 6; L_ = 0.09 if i % 3 == 0 else 0.06
    ck.box((CLK[0] + 0.37 * math.sin(a), CLK[1] - 0.022, CLK[2] + 0.37 * math.cos(a)), (0.022, 0.004, L_), M['ink'], rot=(0, a, 0))
ck.cyl((CLK[0], CLK[1] - 0.04, CLK[2]), 0.025, 0.02, M['brass'], rot=(PI / 2, 0, 0), seg=16)
ck.ob('clock', None)
HOUR = empty('hour', None, (CLK[0], CLK[1] - 0.024, CLK[2]), (0, rad(231), 0)); MIN = empty('minute', None, (CLK[0], CLK[1] - 0.030, CLK[2]), (0, rad(252), 0))
MB().box((0, 0, 0.09), (0.032, 0.005, 0.24), M['ink']).ob('hour_m', HOUR); MB().box((0, 0, 0.14), (0.02, 0.005, 0.36), M['ink']).ob('minute_m', MIN)

# ---------- ORDERS press (never moves) ----------
ORD = empty('orders', None, (-6.35, 0.35, 0.0))
MB().box((0, 0, 0.06), (1.54, 1.24, 0.12), M['charcoal']).box((0, 0, 1.37), (1.50, 1.20, 2.50), M['teal']).box((0, 0, 2.69), (1.30, 1.00, 0.14), M['teal']) \
    .ob('ord_body', ORD, bev=0.025)
otr = MB()
for z in (0.126, 2.614): otr.box((0, 0, z), (1.508, 1.208, 0.012), M['brass'])
otr.box((0.751, 0.10, 2.37), (0.012, 0.18, 0.56), M['brass']).box((0.752, 0.10, 2.37), (0.012, 0.11, 0.50), M['charcoal'])
otr.cyl((0, -0.40, 2.78), 0.135, 0.04, M['brass'], seg=32).tor((0, -0.40, 2.80), 0.13, 0.018, M['brass'], seg=40, rs=8)
otr.ob('ord_trim', ORD, bev=0.002)
BTN = empty('button', ORD, (0, -0.40, 2.80))
MB().cyl((0, 0, 0.025), 0.10, 0.05, M['yellow_btn'], seg=32).sph((0, 0, 0.05), 0.10, M['yellow_btn'], seg=32, ring=12, scale=(1, 1, 0.42)).ob('button_m', BTN)
plate('ord_tab', ORD, (0, -0.50, 2.69), 0.34, 0.075, 0.032, 'PLACE ORDER', font='inter_sb', space=1.3)
OF = -0.60  # front face (local y)
plate('ord_plate', ORD, (-0.08, OF, 2.30), 1.00, 0.30, 0.14, 'ORDERS', desc='order service')
ORDLAMP = lamp('ord_lamp', ORD, (0.56, OF - 0.01, 2.30), 0.045, 'cream')
ASKED = Odo('asked', ORD, (0.08, OF, 1.85), 4, 0.075, 0.09, commas=(0,), gap=0.008, protrude=0.03)
face_txt('asked_l', 'ASKED', 'inter_sb', 0.032, M['ink'], ORD, -0.38, OF - 0.002, 1.85, space=1.35)
MB().box((-0.38, OF - 0.004, 1.85), (0.22, 0.006, 0.07), M['cream']).ob('asked_lp', ORD)
cb = MB().box((-0.20, OF - 0.006, 0.975), (0.82, 0.012, 0.57), M['brass']).box((-0.20, OF - 0.012, 0.975), (0.80, 0.012, 0.55), M['teal_deep'])
cb.box((-0.20, OF - 0.020, 1.20), (0.76, 0.006, 0.08), M['cream'])
HOOKS = [(-0.40, 1.08), (0.0, 1.08), (-0.40, 0.88), (0.0, 0.88)]
for hx_, hz in HOOKS: cb.cyl((hx_, OF - 0.03, hz), 0.006, 0.04, M['brass'], rot=(PI / 2, 0, 0), seg=8)
cb.ob('calllist', ORD, bev=0.003)
face_txt('calllist_t', 'CALL LIST', 'inter_sb', 0.034, M['ink'], ORD, -0.20, OF - 0.023, 1.20, space=1.35)
CTAGS = {nm: tag('ct_' + nm, ORD, (hx_, OF - 0.05, hz), nm, 0.32, 0.09, 0.05, red=False) for nm, (hx_, hz) in zip(('EMAIL', 'TRACKING', 'REWARDS', 'ANALYTICS'), HOOKS)}
for o in CTAGS.values(): o.scale = (0.001,) * 3
hm = MB().box((0.42, OF - 0.002, 0.95), (0.42, 0.006, 0.32), M['brass']).box((0.42, OF - 0.004, 0.95), (0.38, 0.006, 0.28), M['charcoal'])
for i in range(4): hm.tor((0.34 + 0.05 * i, OF - 0.01, 0.92 + 0.03 * (i % 2)), 0.06, 0.011, M['charcoal'], rot=(PI / 2 + 0.3 * i, 0.2, 0), seg=20, rs=6)
hm.ob('hatch_in', ORD)
LID = empty('hatch_lid', ORD, (0.42, OF - 0.012, 1.10))
MB().box((0, -0.008, -0.15), (0.40, 0.016, 0.30), M['teal']).box((0, -0.018, -0.24), (0.10, 0.012, 0.02), M['brass']).ob('hatch_lid_m', LID, bev=0.004)
SWAMP = tag('swamped', ORD, (-0.08, OF - 0.04, 2.37), 'SWAMPED', 0.70, 0.16, 0.10); SWAMP.scale = (0.001,) * 3
# spare tablet crate
cr_ = MB().box((-7.7, -1.5, 0.08), (0.9, 0.5, 0.16), M['teal']).box((-7.7, -1.5, 0.45), (0.92, 0.04, 0.04), M['teal'])
for sx in (-1, 1): cr_.box((-7.7 + sx * 0.44, -1.5, 0.30), (0.04, 0.5, 0.6), M['teal'])
cr_.ob('crate', None, bev=0.01)
for i in range(6): tablet(100 + i, blank=True).location = (-8.05 + 0.14 * i, -1.5, 0.52); bpy.data.objects[f'tab{100 + i:02d}'].rotation_euler = (0, rad(-12), 0)

# ---------- ENQUIRY buffer beam ----------
BEAM = empty('beam', None, (0, 0, 0))
bb = MB(); HEADS, FLAPS = {}, {}
for k, (ly, tz) in LANE.items():
    bb.box((-5.675, ly, tz + 0.21), (0.25, 0.60, 0.42), M['teal']).box((-5.675, ly - 0.30, tz + 0.40), (0.252, 0.012, 0.012), M['brass'])
    bb.cyl((-5.50, ly, tz + 0.30), 0.02, 0.10, M['steel'], rot=(0, PI / 2, 0), seg=10)
    HEADS[k] = MB().cyl((0, 0, 0), 0.08, 0.02, M['brass'], rot=(0, PI / 2, 0), seg=28).cyl((-0.012, 0, 0), 0.05, 0.01, M['charcoal'], rot=(0, PI / 2, 0), seg=20) \
        .ob('head_' + k, BEAM, (-5.44, ly, tz + 0.30))
    fl = empty('flap_' + k, BEAM, (-5.675, ly - 0.05, tz + 0.425), (PI / 2, 0, 0))
    MB().box((0, 0, 0.06), (0.22, 0.01, 0.12), M['cream']).box((0, 0.004, 0.06), (0.226, 0.006, 0.126), M['brass']).ob('flap_m_' + k, fl, bev=0.002)
    face_txt('flap_t_' + k, 'NO', 'dinc', 0.08, M['vermilion'], fl, 0, -0.005, 0.06, space=1.1)
    FLAPS[k] = fl
bb.ob('beam_m', BEAM, bev=0.012)
for k, (ly, tz) in LANE.items(): face_txt('beam_l' + k, 'ENQUIRY', 'inter_sb', 0.022, M['cream'], BEAM, -5.675, ly - 0.30, tz + 0.21, space=1.3) if k == 'B' else None

# ---------- maker's pier ----------
PIER = (8.40, -1.40)
MB().box((PIER[0], PIER[1], 0.85), (0.70, 0.40, 1.70), M['concrete']).box((PIER[0], PIER[1], 1.725), (0.76, 0.46, 0.05), M['concrete']).ob('pier', None, bev=0.01)
def ell(a, b, n=48): return [(a * math.cos(2 * PI * i / n), b * math.sin(2 * PI * i / n)) for i in range(n)]
for nm, z, top, big, bc in (('kafka', 1.38, 'APACHE', 'Kafka', 0.09), ('eb', 0.95, 'AMAZON', 'EventBridge', 0.072)):
    fy = PIER[1] - 0.20
    MB().prism(ell(0.33, 0.17), 0.02, M['brass_satin'], c=(PIER[0], fy - 0.01, z), rot=(PI / 2, 0, 0)).prism(ell(0.31, 0.15), 0.026, M['ink'], c=(PIER[0], fy - 0.013, z), rot=(PI / 2, 0, 0)) \
        .cyl((PIER[0] - 0.27, fy - 0.027, z), 0.012, 0.006, M['brass_satin'], rot=(PI / 2, 0, 0), seg=10).cyl((PIER[0] + 0.27, fy - 0.027, z), 0.012, 0.006, M['brass_satin'], rot=(PI / 2, 0, 0), seg=10) \
        .ob('plate_' + nm, None, bev=0.003)
    face_txt(nm + '_a', top, 'inter_sb', 0.03, M['cream'], None, PIER[0], fy - 0.026, z + 0.075, ext=0.002, space=1.4)
    face_txt(nm + '_b', big, 'serif', bc, M['cream'], None, PIER[0], fy - 0.026, z - 0.03, ext=0.002, fit=0.5)

# ---------- door island (x 38..42): the doorbell ----------
DI = 40.0
dm_ = MB().box((DI, -1.5, -0.05), (4.4, 3.2, 0.1), M['oak']).box((DI, 3.0, -0.05), (4.4, 6.0, 0.1), M['screed'])
dm_.box(((38.0 + 39.6) / 2, 0, 1.5), (1.6, 0.2, 3.0), M['concrete']).box(((40.6 + 42.0) / 2, 0, 1.5), (1.4, 0.2, 3.0), M['concrete']).box((40.1, 0, 2.575), (1.0, 0.2, 0.85), M['concrete'])
dm_.box((37.9, -1.5, 1.5), (0.2, 3.2, 3.0), M['concrete']).box((42.1, -1.5, 1.5), (0.2, 3.2, 3.0), M['concrete']).box((DI, -1.5, 3.05), (4.4, 3.2, 0.1), M['concrete'])
for x in (39.55, 40.65): dm_.box((x, 0, 1.1), (0.1, 0.24, 2.2), M['cream'])
dm_.box((40.1, 0, 2.2), (1.2, 0.24, 0.1), M['cream']).box((40.1, 0.35, 0.04), (1.3, 0.5, 0.08), M['oak'])
dm_.box((40.1, 3.2, 0.35), (4.0, 0.25, 0.7), M['concrete']).box((38.6, -1.2, 0.22), (0.9, 0.35, 0.06), M['teal'])
for sx in (-1, 1): dm_.box((38.6 + sx * 0.4, -1.2, 0.1), (0.05, 0.3, 0.2), M['teal'])
dm_.ob('island', None, smooth=False)
SKYD, _ = grad_sky('sky_d', '#F4E6CF', '#CFE0EE', 1.5, 0.0, 5.0)
MB().box((DI, 6.0, 2.0), (10.0, 0.1, 8.0), SKYD).ob('island_sky', None, smooth=False, shadow=False)
DOOR = empty('door', None, (39.62, 0.0, 0.0))
MB().box((0.48, 0, 1.06), (0.96, 0.05, 2.12), M['teal']).box((0.48, -0.027, 1.06), (0.80, 0.004, 1.9), M['teal_deep']).box((0.48, -0.03, 1.06), (0.76, 0.004, 1.86), M['teal']) \
    .ob('door_m', DOOR, bev=0.006)
MB().cyl((0.86, -0.05, 1.0), 0.012, 0.05, M['brass'], rot=(PI / 2, 0, 0), seg=10).box((0.80, -0.075, 1.0), (0.13, 0.016, 0.016), M['brass']).ob('door_h', DOOR)
BELL = (41.05, -0.12, 1.95)
MB().box((BELL[0], BELL[1] + 0.01, BELL[2]), (0.22, 0.02, 0.30), M['teal']).ob('bell_bp', None, bev=0.004)
GONG = MB().sph((0, 0, 0), 0.10, M['brass'], seg=32, ring=16, scale=(1, 0.45, 1)).ob('gong', None, (BELL[0], BELL[1] - 0.04, BELL[2] + 0.03))
HAM = empty('hammer', None, (BELL[0] + 0.09, BELL[1] - 0.06, BELL[2] - 0.13), (0, rad(-25), 0))
MB().cyl((0, 0, 0.07), 0.006, 0.14, M['brass'], seg=8).sph((0, 0, 0.15), 0.022, M['brass'], seg=12, ring=6).ob('hammer_m', HAM)
plate('bell_pl', None, (BELL[0], BELL[1], BELL[2] - 0.205), 0.12, 0.05, 0.03, 'BELL', font='inter_sb', space=1.3)
ANSM = lamp('answer', None, (40.1, -0.12, 2.45), 0.06, 'off', 0.0)
pc = MB().box((40.1, 0.45, 0.20), (0.36, 0.28, 0.24), M['yellow']).box((40.1, 0.45, 0.20), (0.37, 0.02, 0.245), M['cream']).box((40.1, 0.45, 0.20), (0.02, 0.29, 0.245), M['cream'])
pc.box((40.1, 0.304, 0.17), (0.16, 0.004, 0.07), M['cream']).ob('parcel', None, bev=0.01)
face_txt('parcel_t', 'ORDER PLACED', 'dinc', 0.03, M['ink'], None, 40.1, 0.302, 0.17, space=1.06)

# ---------- lights, haze, world ----------
HAZE, HAZED = haze('haze_hall', (1.0, -1.5, 3.5), (24.0, 17.0, 7.0), 0.007, 0.5, '#DDE4E8')
haze('haze_island', (DI, -1.5, 1.5), (4.0, 3.0, 3.0), 0.004, 0.5, '#DDE4E8')
WORLD = bpy.data.worlds.new('w'); sc.world = WORLD
try: WORLD.use_nodes = True
except Exception: pass
WBG = WORLD.node_tree.nodes['Background']; WBG.inputs['Color'].default_value = hx('#2B2F33'); WBG.inputs['Strength'].default_value = 0.3
light('KEY', 'AREA', (-3.5, -6.5, 4.2), (0, -1.0, 1.2), 700, '#FFDDB8', size=3.0)
for y in (-4.0, 0.0, 4.0): light('SKY%g' % y, 'AREA', (1.0, y + 0.08, 6.8), (1.0, y + 0.08, 0.0), 350, '#D9E7F4', size=12.0, size_y=1.2)
BACK = light('BACK', 'AREA', (1.0, 7.6, 3.0), (1.0, -3.0, 2.0), 3000, '#CFE0F2', size=20.0, size_y=4.0, vf=1.0, hall=False)
RIM = light('RIM', 'SPOT', (5.0, 4.0, 4.5), (0, -1.6, 0.8), 450, '#C4D8EE', spot=50, blend=0.7, hall=False)
light('FILL', 'AREA', (4.5, -6.0, 1.2), (0, -1.5, 0.6), 80, '#FFF1E0', size=4.0, size_y=4.0, shadow=False)
light('ORDKEY', 'AREA', (-5.0, -2.8, 3.0), (-6.35, -0.25, 1.6), 160, '#FFE6C8', size=1.2, size_y=1.2)
light('PIERKEY', 'AREA', (7.2, -3.6, 2.6), (8.4, -1.6, 1.2), 90, '#FFE6C8', size=1.0, size_y=1.0)
light('SUN_D', 'AREA', (40.1, 3.0, 2.8), (40.1, -1.0, 0.8), 400, '#E3EEF8', size=3.0, size_y=3.0, cutoff=12, hall=False)
light('KEY_D', 'AREA', (39.0, -2.2, 2.6), (40.6, -0.1, 1.6), 120, '#FFDDB8', size=1.0, size_y=1.0, cutoff=12, hall=False)
light('FILL_D', 'AREA', (41.3, -2.4, 1.4), (40.6, 0.0, 1.4), 40, '#FFF1E0', size=1.5, size_y=1.5, shadow=False, cutoff=12, hall=False)
DUSTM = mat('dust', '#EEE6D6', 0.6, emit=0.4, eh='#FFF1D6'); DUST = []
for nm, c, s_, n in (('dust1', (-3.0, -1.2, 2.0), (6, 4, 3), 350), ('dust2', (3.0, -0.8, 2.4), (8, 4, 3), 300)):
    dmb = MB()
    for _ in range(n): dmb.tet((random.uniform(-s_[0] / 2, s_[0] / 2), random.uniform(-s_[1] / 2, s_[1] / 2), random.uniform(-s_[2] / 2, s_[2] / 2)), 0.004, DUSTM)
    DUST.append(dmb.ob(nm, None, c, smooth=False, shadow=False))
tick('set built')

# ---------- cars ----------
CARS['EMAIL'] = Car('EMAIL', 'D', None); dev_email(CARS['EMAIL'])
CARS['TRACKING'] = Car('TRACKING', 'C', None); dev_track(CARS['TRACKING'])
CARS['REWARDS'] = Car('REWARDS', 'B', None); dev_rewards(CARS['REWARDS'])
CARS['ANALYTICS'] = Car('ANALYTICS', 'A', None); dev_analytics(CARS['ANALYTICS'])
E_, T_, R_, A_ = CARS['EMAIL'], CARS['TRACKING'], CARS['REWARDS'], CARS['ANALYTICS']
OFFTAG = tag('offline', R_.ob, (0.14, -0.245, 0.55), 'OFFLINE', 0.30, 0.09, 0.06); OFFTAG.scale = (0.001,) * 3
MB().tor((0, 0, 0), 0.012, 0.003, M['brass'], rot=(PI / 2, 0, 0), seg=12, rs=6).ob('offhook', R_.ob, (0.14, -0.23, 0.53))
# hoist (ANALYTICS)
CHAIN = MB().cyl((0, 0, 0.5), 0.012, 1.0, M['steel'], seg=8).ob('chain', None, (-5.10 - 0.27, LANE['A'][0] + 0.12, 6.8))
HOOK = empty('hook', None, (0, 0, 0))
MB().tor((0, 0, -0.03), 0.035, 0.008, M['brass_satin'], rot=(PI / 2, 0, 0), seg=20, rs=6, arc=1.5 * PI).cyl((0, 0, 0.03), 0.01, 0.06, M['brass_satin'], seg=8).ob('hook_m', HOOK)

# ---------- tablets ----------
TABS = {n: tablet(n) for n in range(1, 14)}
TSTAND = lambda n: (XS(n), -0.30, 1.80 + TABH / 2 + 0.01)
TCARRY = lambda x: (x, 0.45, 2.15 + TABH / 2)
for n, o in TABS.items():
    if n <= 8: o.location = TSTAND(n)
    else: o.location = TCARRY(-5.20); o.scale = (0.001,) * 3
TOUT = -5.20
JOLTS = []
def press(t):
    tw(BTN, 'location', t - 2 * FR, 2 * FR, (0, -0.40, 2.803), 'out'); tw(BTN, 'location', t, 2 * FR, (0, -0.40, 2.78), 'in2')
    tw(BTN, 'location', t + 2 * FR, 6 * FR, (0, -0.40, 2.80), 'out')
CARRIER_X = []   # (t0, t1, f) pieces of the carrier's x for camera follow
def deliver(n, t_out, t_land, travel=None, ret=0.6, jolt=False):
    """tablet n pops out of the ORDERS outlet onto the carrier at t_out, rides to slot n, arcs down and lands at t_land."""
    o = TABS[n]; x1 = XS(n); ta = t_land - 0.30; tt0 = travel if travel is not None else t_out + 0.18
    st(o, 'location', t_out, TCARRY(TOUT - 0.25)); st(o, 'scale', t_out, (0.001,) * 3)
    tw(o, 'scale', t_out, 4 * FR, (1, 1, 1), 'out'); tw(o, 'location', t_out, 0.16, TCARRY(TOUT), 'out')
    def cx(t): return TOUT + (x1 - TOUT) * EZ['io'](clamp((t - tt0) / max(ta - tt0, 1e-3)))
    fn(o, 'location', tt0, ta, lambda t: TCARRY(cx(t)))
    def arc(t):
        u = clamp((t - ta) / 0.30); a, b = Vector(TCARRY(x1)), Vector(TSTAND(n)); e = EZ['in2'](u)
        p = a.lerp(b, e); p.z += 0.10 * math.sin(PI * u) - (0.004 * math.sin(PI * clamp((t - t_land) / (3 * FR))) if t > t_land else 0)
        return tuple(p)
    fn(o, 'location', ta, t_land + 3 * FR, arc)
    fn(CARRIER, 'location', tt0, ta, lambda t: (cx(t), 0.45, 2.13))
    tw(CARRIER, 'location', t_land, ret, (TOUT, 0.45, 2.13), 'io')
    CARRIER_X.append((tt0, ta, cx, x1))
    if jolt: JOLTS.append((t_land, 0.003))
def hide_all_tabs(t):
    for o in TABS.values(): hide(o, t)

# ---------- timeline ----------
# hook: flash-forward. #0001-#0008 stand, #0009 lands on "later"; E/T/R read slot 8 -> 9 one after another
for c in (E_, T_, R_): c.put(0.0, XS(8))
hide(A_.ob, 0.0)
R_.odo.reset(0.0, 400); tok_reset(R_, 0.0, 9); E_.nstk = 24; st(E_.stk, 'scale', 0.0, (1, 1, 24))
press(tTAP); deliver(9, tTAP + 0.22, tLATER + 0.02, travel=1.18, jolt=True)
JOLTS.append((tTAP + 2 * FR, 0.004))
hop(E_, tEMAIL - 0.04, 9); hop(T_, tTRACK + 0.02, 9); hop(R_, tREW + 0.02, 9)
# whip to polling (7.66): log empty, lamps off, sign edge-on, cars at the depot, counters zeroed
hide_all_tabs(tSLOW); st(SIGN, 'rotation_euler', tSLOW, (0, 0, PI / 2))
for c in (E_, T_, R_): snap(c.ob, tSLOW); c.put(tSLOW + FR, DEPOT)
R_.odo.reset(tSLOW + FR, 0); tok_reset(R_, tSLOW + FR, 2); E_.nstk = 3; st(E_.stk, 'scale', tSLOW + FR, (1, 1, 3))
for l_ in LAMPS: st(l_.data, 'energy', tSLOW, 0.0)
st(sock(PBULB, 'Emission Strength'), 'default_value', tSLOW, 0.0); st(sock(SHADE_IN, 'Emission Strength'), 'default_value', tSLOW, 0.0)
# polling: virtual time without the freeze (13.34 -> 14.58 holds)
FZ0, FZ1 = tSPOT, tALMOST; FZD = FZ1 - FZ0
def vt(t): return t if t < FZ0 else (FZ0 if t < FZ1 else t - FZD)
def rt(v): return v if v < FZ0 else v + FZD
XC = -5.09
BUMPS = dict(REWARDS=[10.40, 11.62, 12.75, 15.62, 17.30], TRACKING=[10.66, 11.90, 13.00, 15.22, 16.60], EMAIL=[10.95, 12.20, 13.29, 15.42, 17.00])
LAUNCH = dict(REWARDS=8.15, TRACKING=8.45, EMAIL=8.75)
def shuttle_x(b, launch, v):
    """car x in virtual time v: depot -> buffer (bump), then out-and-back between bumps, then home."""
    if v <= launch: return DEPOT
    if v <= b[0]:
        u = (v - launch) / (b[0] - launch); return DEPOT + (XC - DEPOT) * (0.55 * EZ['io'](u) + 0.45 * u * u)
    for b0, b1 in zip(b, b[1:]):
        if v <= b1:
            u = (v - b0) / (b1 - b0); reach = min(DEPOT - XC, 2.6 * (b1 - b0)); return XC + reach * math.sin(PI * u)
    u = clamp((v - b[-1]) / 1.5); return XC + (DEPOT - XC) * EZ['out2'](u)
asked = [0]
for nm in ('REWARDS', 'TRACKING', 'EMAIL'):
    c = CARS[nm]; b = [vt(x) for x in BUMPS[nm]]; la = LAUNCH[nm]
    c.path(la, 19.4, lambda t, b=b, la=la: shuttle_x(b, la, vt(t)))
    k = {'REWARDS': 'B', 'TRACKING': 'C', 'EMAIL': 'D'}[nm]; ly, tz = LANE[k]
    for tb in BUMPS[nm]:
        tw(HEADS[k], 'location', tb - FR, FR, (-5.47, ly, tz + 0.30), 'lin'); tw(HEADS[k], 'location', FZ1 if FZ0 - 0.2 < tb < FZ0 else tb, 0.15, (-5.44, ly, tz + 0.30), 'out')
        if tb < FZ0 - 0.1 or tb > FZ1:
            hold = 0.5 if 15.0 < tb < 15.7 else 0.4
            tw(FLAPS[k], 'rotation_euler', tb, 3 * FR, (0, 0, 0), 'out'); tw(FLAPS[k], 'rotation_euler', rt(vt(tb) + hold), 0.15, (PI / 2, 0, 0), 'in2')
        if tb < tTHOUS: lamp_to(ORDLAMP, tb, 'amber'); lamp_to(ORDLAMP, tb + 0.25, 'cream')
BUMPALL = sorted(tb for nm in BUMPS for tb in BUMPS[nm] if tb < tTHOUS)
for tb in BUMPALL: asked[0] += 1; ASKED.roll(FZ1 if FZ0 - 0.2 < tb < FZ0 else tb, 0.2, asked[0], lead_ez='back')
# the EMAIL flap is half up when everything freezes at "Spot": its flip spans the freeze
tw(FLAPS['D'], 'rotation_euler', 13.29, 0.05, (PI / 4, 0, 0), 'lin'); tw(FLAPS['D'], 'rotation_euler', FZ1, 2 * FR, (0, 0, 0), 'out')
tw(FLAPS['D'], 'rotation_euler', FZ1 + 0.35, 0.15, (PI / 2, 0, 0), 'in2')
# freeze lighting: hall to 35 % within 3 frames, restore at "Almost"
for ld, e in HALL: tw(ld, 'energy', FZ0, 3 * FR, e * 0.35, 'lin'); tw(ld, 'energy', FZ1, 4 * FR, e, 'lin')
for es, e in HALLEM: tw(es, 'default_value', FZ0, 3 * FR, e * 0.35, 'lin'); tw(es, 'default_value', FZ1, 4 * FR, e, 'lin')
tw(WBG.inputs['Strength'], 'default_value', FZ0, 3 * FR, 0.15, 'lin'); tw(WBG.inputs['Strength'], 'default_value', FZ1, 4 * FR, 0.3, 'lin')
# clock: all day
tw(HOUR, 'rotation_euler', tALLDAY + 0.08, 1.0, (0, rad(231 + 300), 0), 'io'); tw(MIN, 'rotation_euler', tALLDAY + 0.08, 1.0, (0, rad(252 + 3600), 0), 'io')
# thousands of wasted calls: ASKED spins, ORDERS drowns
ASKED.roll(tTHOUS + 0.05, 1.25, 4812)
tag_drop(SWAMP, tDROWNS - 0.06); lamp_to(ORDLAMP, tDROWNS, 'red')
fn(ORD, 'location', tDROWNS, tFIX, lambda t: (-6.35 + 0.004 * math.sin(2 * PI * 9 * (t - tDROWNS)) * min(1.0, 0.4 + 0.6 * math.exp(-(t - tDROWNS))), 0.35, 0.0))
st(ORD, 'location', tFIX, (-6.35, 0.35, 0.0))
# direct calls: cables unreel from the hatch to each parked car, CALL LIST fills, ANALYTICS tag lowers, hatch pops
CABLES = []
for i, (nm, k) in enumerate((('EMAIL', 'D'), ('TRACKING', 'C'), ('REWARDS', 'B'))):
    ly, tz = LANE[k]; yc = ly - 0.25
    pts = [(-5.93, -0.27, 0.92), (-6.0, -0.55, 0.30), (-6.05, -0.9, 0.03), (-6.1, yc, 0.03), (-6.0, yc, tz + 0.50), (-5.45, yc, tz + 0.06),
           (-4.0, yc, tz + 0.06), (-1.5, yc, tz + 0.06), (DEPOT - 0.55, yc, tz + 0.06), (DEPOT - 0.39, ly, tz + 0.18)]
    cb_ = tube(f'cable{i}', pts, 0.022, M['charcoal']); cb_.data.bevel_factor_end = 0.0; CABLES.append(cb_)
    t0 = tCALLING + 0.05 + 0.08 * i
    tw(cb_.data, 'bevel_factor_end', t0, 0.4, 1.0, 'out'); tw(cb_.data, 'bevel_factor_end', tFIX, 0.2, 0.0, 'in2')
    show(CTAGS[nm], t0 + 0.35); lamp_to(CARS[nm].lamp, t0 + 0.4, 'amber'); lamp_to(CARS[nm].lamp, t0 + 0.7, 'cream')
tag_drop(CTAGS['ANALYTICS'], tEVERYONE, z_from=0.3)
tw(LID, 'rotation_euler', tEVERYONE + 0.32, 4 * FR, (rad(-105), 0, 0), 'back')
# the fix (whip at 22.58): everything resets in the whip, then the log switches on
for o in CTAGS.values(): hide(o, tFIX)
hide(SWAMP, tFIX); st(LID, 'rotation_euler', tFIX, (0, 0, 0)); lamp_to(ORDLAMP, tFIX, 'cream')
ASKED.reset(tFIX, 0)
for c in (E_, T_, R_): snap(c.ob, tFIX); c.put(tFIX + FR, XS(0))
for i, l_ in enumerate(LAMPS):
    tl = tEVENT + 0.07 * i; st(l_.data, 'energy', tl, 55.0); st(l_.data, 'energy', tl + FR, 22.0); st(l_.data, 'energy', tl + 2 * FR, 55.0)
flick(sock(PBULB, 'Emission Strength'), tEVENT, 10.0); tw(sock(SHADE_IN, 'Emission Strength'), 'default_value', tEVENT, 0.7, 0.3, 'lin')
tw(SIGN, 'rotation_euler', tEVENT + 0.05, 0.32, (0, 0, -rad(3)), 'out'); tw(SIGN, 'rotation_euler', tEVENT + 0.37, 0.25, (0, 0, 0), 'io')
# the order service just announces a fact
press(tJUST); deliver(1, tANNOUNCES, tPLACED, travel=tFACT + 0.05, jolt=True)
deliver(2, tLOG - 0.55, tKEEPS + 0.06, ret=0.2); deliver(3, tKEEPS + 0.14, tINORDER, travel=tKEEPS + 0.28, ret=0.4, jolt=True)
# each reacts on its own rhythm
for c, ts in ((E_, (tEMAIL2 - 0.10, tEMAIL2 + 0.37, tEMAIL2 + 0.72)), (T_, (tTRACK2 - 0.12, tTRACK2 + 0.40, tTRACK2 + 0.80)), (R_, (tREW2 - 0.12, tREW2 + 0.38, tREW2 + 0.76))):
    for s_, t_ in enumerate(ts, 1): hop(c, t_, s_, 0.40 if s_ == 1 else 0.22)
# off-camera at the door: #0004-#0008 land, EMAIL / TRACKING read to 8, REWARDS goes offline at 3
for i, n in enumerate(range(4, 9)):
    tl = tLIKE + 0.75 + 0.72 * i; deliver(n, tl - 0.62, tl, ret=0.12)
    hop(E_, tl + 0.08, n); hop(T_, tl + 0.20, n)
lamp_to(R_.lamp, tLIKE + 0.1, 'red'); show(OFFTAG, tLIKE + 0.1)
# door island
DOORT = [(tCHECKING, rad(-20)), (tCHECKING + 0.32, 0.0), (tDOOR, rad(-20)), (tDOOR + 0.34, 0.0)]
for t_, a_ in DOORT: tw(DOOR, 'rotation_euler', t_, 0.16 if a_ else 0.2, (0, 0, a_), 'out' if a_ else 'in2')
for k in range(3):
    th = tRINGS + 0.1 * k; tw(HAM, 'rotation_euler', th - 0.05, 0.05, (0, rad(-6), 0), 'in2'); tw(HAM, 'rotation_euler', th, 0.05, (0, rad(-25), 0), 'out')
fn(GONG, 'scale', tRINGS, tRINGS + 1.0, lambda t: tuple(1 + 0.015 * math.sin(2 * PI * 22 * (t - tRINGS)) * math.exp(-4 * (t - tRINGS)) * s_ for s_ in (1, -1, 1)))
lamp_to(ANSM, tRINGS + 0.02, 'cream', 5.0)
tw(DOOR, 'rotation_euler', tANSWER, 0.42, (0, 0, rad(-95)), 'out')
# rewards was down: it reads the log and catches up
tag_lift(OFFTAG, tREADS); lamp_to(R_.lamp, tREADS + 0.02, 'amber')
for i, n in enumerate(range(4, 9)): hop(R_, tREADS + 0.15 + 0.23 * i, n)
# new service: lowered on the hoist, then replays history
AL0, AL1 = tNEWS - 0.05, tNEWS + 0.62
A_.put(0.0, XS(0)); show(A_.ob, AL0)
A_.zf = lambda t: (2.6 * (1 - EZ['out'](clamp((t - AL0) / (AL1 - AL0)))) + 0.015 * math.sin(PI * clamp((t - AL1) / 0.16))) if t < AL1 + 0.16 else 0.0
HK1 = AL1 + 0.15
def hook_z(t):
    z = LANE['A'][1] + A_.zf(t) + 0.59 if t >= AL0 else 6.0
    if t > HK1: z = LANE['A'][1] + 0.59 + 4.5 * EZ['in2'](clamp((t - HK1) / 0.8))
    return min(z, 6.8)
fn(HOOK, 'location', 0.0, END, lambda t: (XS(0) - 0.27, LANE['A'][0] + 0.12, hook_z(t)))
fn(CHAIN, 'location', 0.0, END, lambda t: (XS(0) - 0.27, LANE['A'][0] + 0.12, hook_z(t) + 0.06))
fn(CHAIN, 'scale', 0.0, END, lambda t: (1, 1, max(0.001, 6.8 - hook_z(t) - 0.06)))
lamp_to(A_.lamp, AL1 + 0.05, 'cream')
for i, n in enumerate(range(1, 9)): hop(A_, tREPLAYS + 0.04 + 0.13 * i, n, 0.13)
# the producer never changes; doesn't know who's listening
press(tDOESNT - 0.22); deliver(9, tDOESNT - 0.08, tLISTEN + 0.02, ret=0.5)
for c, t_ in ((E_, tLISTEN + 0.15), (A_, tLISTEN + 0.30), (T_, tLISTEN + 0.50), (R_, tLISTEN + 0.70)): hop(c, t_, 9)
# stop asking: the beam sinks
for k in FLAPS: st(FLAPS[k], 'rotation_euler', tSTOP, (PI / 2, 0, 0))
tw(BEAM, 'location', tSTOP + 0.10, 0.4, (0, 0, -0.9), 'in2'); hide(BEAM, tSTOP + 0.6)
# start reacting
press(tSTART - 0.85); deliver(10, tSTART - 0.65, tREACTING + 0.02, travel=tSTART - 0.50, ret=0.5)
for c, t_ in ((T_, tREACTING + 0.18), (E_, tREACTING + 0.30), (R_, tREACTING + 0.45), (A_, tREACTING + 0.60)): hop(c, t_, 10)
# CTA: one event every 3 s, gentle staggered reads
for i, n in enumerate((11, 12, 13)):
    tl = tCTA + 1.05 + 3.0 * i
    if tl > END - 0.8: break
    press(tl - 1.6); deliver(n, tl - 1.45, tl, travel=tl - 1.25, ret=0.6)
    for c, d in ((E_, 0.20), (A_, 0.38), (T_, 0.55), (R_, 0.80)): hop(c, tl + d, n)
tw(sc.view_settings, 'exposure', tCTA, 0.7, -0.3, 'io')
for c in CARS.values(): c.fin()
for d_ in DUST:
    c0 = Vector(d_.location)
    fn(d_, 'location', 0.0, END, lambda t, c0=c0: (c0.x + 0.05 * math.sin(0.3 * t), c0.y, c0.z + 0.03 * t))
tick('timeline built')
# ---------- resolve text, drums and the keyframe registry ----------
fit_texts()
for d_ in DRUMS: d_.fin()

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
S9 = CARRIER_X[0]
def _s02(t, u, e, s):
    tt0, ta, cx, x1 = S9; x = cx(t); k = clamp((t - tt0) / (ta - tt0))
    return V3(x - 0.05, -2.4, 2.5), V3(x + 0.35 * (1 - EZ['io'](k)), -0.3, 2.3)
shot(0.0, (-5.95, -1.45, 3.40), (-6.35, -0.05, 2.86), toward((-5.95, -1.45, 3.40), V3(-6.35, -0.05, 2.86), 0.96), None, 85, 2.0)
shot(tONE, (0, 0, 0), (0, 0, 1), None, None, 40, 2.4, fnP=_s02,
     foc=lambda t, P, G: V3(S9[2](t), 0.45 - 0.75 * EZ['in2'](clamp((t - S9[1]) / 0.3)), 2.4))
def push(t0, P, G, k, lens, fs, **kw): P, G = V3(*P), V3(*G); shot(t0, P, G, toward(P, G, k), None, lens, fs, **kw)
push(tEMAIL - 0.06, (0.55, -2.05, 1.95), (0.26, -0.85, 1.62), 0.95, 50, 2.0)
push(tTRACK - 0.02, (0.60, -2.60, 1.60), (0.26, -1.45, 1.30), 0.95, 50, 2.0)
push(tREW - 0.02, (0.60, -3.25, 1.25), (0.26, -2.05, 0.95), 0.95, 50, 2.0)
P6, G6 = V3(1.5, -6.4, 2.6), V3(0.1, -1.2, 1.6)
shot(tALL - 0.02, P6, G6, P6 + (P6 - G6).normalized() * 0.6, None, 35, 3.5)
shot(tNOBODY - 0.02, (-4.4, -5.6, 2.9), (-2.6, -0.6, 1.6), (-4.4, -5.6, 3.2), None, 32, 3.2)
push(tSLOW, (2.6, -3.6, 1.35), (-5.6, -1.5, 1.1), 0.96, 35, 2.8, whip='L')
push(tASKING, (-4.70, -3.50, 1.40), (-5.60, -1.60, 1.00), 0.97, 50, 2.2)
shot(tANY2, (1.4, -7.8, 4.8), (-2.3, -1.0, 1.1), (1.4, -7.8, 5.2), None, 28, 4.0)
push(tALLDAY, (-2.0, 4.6, 4.3), (-2.0, 6.85, 4.3), 0.95, 50, 2.8)
G12 = V3(-5.20, -0.85, 1.35)
shot(tSPOT, (-4.4, -2.3, 1.75), G12, None, None, 35, 2.8, roll=2.0,
     fnP=lambda t, u, e, s: (G12 + Matrix.Rotation(rad(-25) * EZ['io'](u), 3, 'Z') @ (V3(-4.4, -2.3, 1.75) - G12), G12))
push(tALMOST, (-5.20, -3.10, 1.55), (-5.62, -1.45, 1.18), 0.97, 65, 2.2)
def _s14(t, u, e, s):
    k = EZ['io'](clamp((t - 17.7) / 0.8)); P0 = V3(-6.19, -1.45, 1.92).lerp(V3(-6.16, -1.35, 1.90), e)
    return P0.lerp(V3(-5.0, -2.9, 2.1), k), V3(-6.27, -0.25, 1.85).lerp(V3(-6.35, -0.25, 2.05), k)
shot(tTHOUS, (-6.19, -1.45, 1.92), (-6.27, -0.25, 1.85), None, None, 65, 2.0, fnP=_s14)
shot(tCALLING, (-6.9, -3.9, 2.9), (-1.8, -1.4, 0.9), (-6.5, -3.9, 2.9), (-1.4, -1.4, 0.9), 32, 3.2, ez='io')
push(tTHEN, (-6.48, -2.85, 1.25), (-6.44, -0.26, 0.97), 0.95, 50, 2.2)
shot(tFIX, (1.0, -8.4, 3.4), (0.6, -0.4, 2.0), (1.0, -8.4, 3.1), None, 30, 4.0, whip='R')
def _s16(t, u, e, s):
    k = EZ['io'](clamp((t - (tJUST + 0.12)) / (tFACT - tJUST - 0.1)))
    P = V3(-5.75, -1.95, 3.10).lerp(V3(-5.45, -1.80, 3.15), k); G = V3(-6.32, -0.20, 2.70).lerp(V3(-5.35, 0.35, 2.45), k)
    return P + (G - P) * 0.04 * (1 - k) * e, G
shot(tORDER4, (-5.75, -1.95, 3.10), (-6.32, -0.20, 2.70), None, None, 50, 2.4, fnP=_s16)
shot(tFACT, (-4.30, -2.45, 2.40), (-4.70, -0.30, 2.25), (-4.32, -2.35, 2.38), None, 50, 2.0, foc=lambda t, P, G: V3(-4.70, -0.34, 2.25))
shot(tTHATS, (-4.25, -1.05, 1.80), (-4.70, -0.30, 2.30), (-4.25, -1.05, 1.95), None, 35, 2.0, foc=lambda t, P, G: V3(-4.70, -0.34, 2.3))
shot(tLOG - 0.15, (-4.9, -2.6, 2.55), (-4.6, -0.3, 2.15), (-3.0, -2.6, 2.55), (-2.7, -0.3, 2.15), 40, 2.8, ez='io')
push(tEMAIL2, (-4.0, -6.4, 2.2), (-4.0, -1.2, 1.45), 0.97, 50, 4.0)
push(tLIKE, (40.92, -1.6, 1.98), (41.02, -0.1, 1.86), 0.95, 65, 2.2, whip='R')
push(tYOU, (39.7, -3.0, 1.35), (40.0, 0.0, 1.15), 0.93, 35, 2.8)
push(tIT, (40.75, -1.6, 2.0), (41.0, -0.06, 1.95), 0.96, 50, 2.4)
push(tANSWER - 0.2, (39.95, -2.7, 1.35), (40.1, 0.6, 0.9), 0.95, 35, 2.8, whip='L')
push(tREWD, (-3.10, -3.95, 1.30), (-3.46, -2.05, 0.95), 0.96, 50, 2.0, whip='L')
def _s27(t, u, e, s):
    x = R_.x_at(t); return V3(x - 0.3, -4.4, 1.55), V3(x + 0.6, -1.6, 1.25)
shot(tREADS - 0.05, (0, 0, 0), (0, 0, 1), None, None, 40, 2.8, fnP=_s27, foc=lambda t, P, G: V3(R_.x_at(t), -2.27, 0.75))
def _s28(t, u, e, s):
    k = EZ['io'](clamp((t - AL0) / (AL1 - AL0 + 0.2))); P = V3(-4.55, -4.70, 1.35).lerp(V3(-4.6, -4.6, 1.15), e)
    return P, V3(-5.10, -2.65, 1.7).lerp(V3(-5.10, -2.65, 0.55), k)
shot(tNEWS, (0, 0, 0), (0, 0, 1), None, None, 40, 2.4, fnP=_s28, foc=lambda t, P, G: V3(-5.10, -2.87, 0.4 + A_.zf(t)))
def _s29(t, u, e, s):
    x = A_.x_at(t); return V3(x - 0.2, -5.6, 1.10), V3(x + 0.3, -1.5, 1.35)
shot(tREPLAYS - 0.06, (0, 0, 0), (0, 0, 1), None, None, 35, 2.8, fnP=_s29, foc=lambda t, P, G: V3(A_.x_at(t), -2.87, 0.4))
push(tPROD, (-5.55, -2.35, 1.95), (-6.35, -0.25, 1.70), 0.98, 50, 2.4)
shot(45.90, (-7.35, -2.45, 2.85), (-0.6, -1.6, 1.50), (-7.25, -2.55, 2.85), None, 32, 3.2, foc=lambda t, P, G: V3(0.0, -1.2, 1.6))
push(tSTOP, (-3.55, -4.70, 1.95), (-5.50, -1.70, 0.75), 0.96, 35, 2.8)
shot(tSTART - 0.05, (2.6, -8.4, 5.0), (-0.2, -0.8, 1.6), (2.6, -8.4, 4.7), None, 28, 4.0)
def _s34(t, u, e, s):
    k = EZ['io'](clamp((t - (tAMAZON - 0.25)) / 0.5)); P = V3(8.05, -2.95, 1.50).lerp(V3(8.10, -2.88, 1.30), k)
    return P, V3(8.40, -1.62, 1.38).lerp(V3(8.40, -1.62, 0.95), k)
shot(tAPACHE0, (8.05, -2.95, 1.50), (8.40, -1.62, 1.38), None, None, 65, 2.0, whip='R', fnP=_s34)
G35 = V3(0.4, -0.8, 1.7)
shot(tCTA, (-2.6, -8.6, 4.8), G35, (-1.4, -8.9, 5.1), None, 32, 3.5, ez='io')
# heavier blur through the polling shuttles and the replay
st(sc.render, 'motion_blur_shutter', 8.2, 0.8); st(sc.render, 'motion_blur_shutter', tSPOT - 0.1, 0.5)
st(sc.render, 'motion_blur_shutter', tREPLAYS - 0.06, 0.9); st(sc.render, 'motion_blur_shutter', tPROD - 0.3, 0.5)
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
ee.shadow_resolution_scale = 0.75
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
ee.volumetric_tile_size = opt('--vtile', '4'); ee.volumetric_samples = 64; ee.volumetric_start = 0.1; ee.volumetric_end = 220.0
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
if '--blend' in argv: bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/scene_v5.blend')
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
