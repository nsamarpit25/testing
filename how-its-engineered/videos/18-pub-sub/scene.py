# 18 Pub/Sub, v5: "The Dispatch Hall". A warm 1930s Art Deco hall of satin cobalt machines with cream enamel nameplates
# and thin brass trims: mechanical drum counters, printed message cards on roller conveyors, a topic drum that rises from
# a floor hatch, a FOLLOWERS scoreboard over a floor of ~7,300 bulbs, a queue vignette in the left aisle and a dusk
# rooftop radio set at x = 200. Spec: design_v5.md + HANDOFF_v5.md. Timed to voice/words.json.
# usage: blender -b -P videos/18-pub-sub/scene.py -- <out dir> [--res 480] [--fps 24] [--samples 32] [--stills 3,20] [--range a,b] [--skip] [--cutfix]
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
random.seed(18)
PI = math.pi; rad = math.radians; FR = 1.0 / FPS

# ---------- word times ----------
tPOST, tTWO, tAND, tKEEPS, tSPIN = W('post'), W('two'), L(0, 2), W('keeps'), W('spinning')
tWHY, tEVERY, tITSELF, tNOTIFY, tEMAILS, tFEEDS, tONE = L(1, 0), W('every'), W('itself'), W('notify'), W('emails'), W('feeds'), W('one', 12.5)
tSPOT, tIF, tSLOW, tWAITS, tAND2, tNEW, tREWRITE, tSERVICE, tAGAIN = L(2, 0), L(3, 0), W('slow'), W('waits'), L(3, 1), W('new'), W('rewriting'), W('service', 20), W('again')
tQ, tQUEUE, tIT, tONEW = L(4, 0), W('queue'), W('it', 23.5), W('one', 25)
tFIX, tPS, tPUB, tTOPIC, tDONE, tBUTTON, tSTOPS = L(5, 0), W('pubsub'), W('publishes'), W('topic'), W('done'), W('button', 31), W('stops')
tSUBS, tSUBSCRIBES, tEACH, tCOPY, tSAME = L(6, 0), W('subscribes'), W('each', 35), W('copy'), W('same')
tRADIO, tONCE, tTUNED = L(7, 0), W('once'), W('tuned')
tNF, tSUBIT, tNEVER = L(8, 0), W('subscribe'), W('never')
tSO, tONEPUB, tPUBLISH, tEVERYONE = L(9, 0), W('one', 49), W('publish'), W('everyone')
tTHATS, tGOOGLE, tAMAZON, tCTA = L(10, 0), W('google'), W('amazon'), L(11, 0)
CTA_LOOPS = (55.7, 58.5, 61.3)

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
        elif kind == 'set' or f1 == f0:
            cur = at(f0 - 1); drop(f0 - 1); keys[f0 - 1] = cur; keys[f0] = val
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

M = {}
M['cobalt'] = mat('cobalt', '#2547B5', 0.42); rough_noise(M['cobalt'], 0.38, 0.48)
M['cobalt_deep'] = mat('cobalt_deep', '#172F7E', 0.55)
M['deck'] = mat('deck', '#182A6E', 0.55)
M['cream'] = mat('cream', '#E8DCC2', 0.50)
M['paper'] = mat('paper', '#F2E9D6', 0.75); bump(M['paper'], 260, 0.03)
M['ink'] = mat('ink', '#1C2A6B', 0.60)
M['ink_red'] = mat('ink_red', '#A8302B', 0.60)
M['brick'] = mat('brick', '#B0302A', 0.50)
M['brick_btn'] = mat('brick_btn', '#B0302A', 0.35)
M['brass'] = mat('brass', '#C99A48', 0.33, 1.0)
M['brass_satin'] = mat('brass_satin', '#B8904A', 0.48, 1.0)
M['charcoal'] = mat('charcoal', '#26221E', 0.65)
M['steel'] = mat('steel', '#3A3835', 0.45, 0.8)
M['wood'] = mat('wood', '#3E2E22', 0.60)
M['walnut'] = mat('walnut', '#5B3A22', 0.42)
M['grille'] = mat('grille', '#D8C7A3', 0.90)
M['colbase'] = mat('colbase', '#8E7354', 0.85)
M['roof'] = mat('roof', '#8C7A66', 0.90)
M['sandstone'] = mat('sandstone', '#C8B49A', 0.85)
m = M['sandstone']; nz = nn(m, 'ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.5
mr = nn(m, 'ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.95; mr.inputs['To Max'].default_value = 1.05
mu = nn(m, 'ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mu.inputs['Factor'].default_value = 1.0
mu.inputs[6].default_value = hx('#C8B49A'); ln(m, nz.outputs['Fac'], mr.inputs['Value'])
cc = nn(m, 'ShaderNodeCombineXYZ'); [ln(m, mr.outputs['Result'], cc.inputs[i]) for i in range(3)]
ln(m, cc.outputs[0], mu.inputs[7]); ln(m, mu.outputs[2], sock(m, 'Base Color'))
M['terrazzo'] = mat('terrazzo', '#CDB995', 0.62)
m = M['terrazzo']; tc = nn(m, 'ShaderNodeTexCoord'); vo = nn(m, 'ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 180
ln(m, tc.outputs['Object'], vo.inputs['Vector']); sp = nn(m, 'ShaderNodeSeparateColor'); ln(m, vo.outputs['Color'], sp.inputs[0])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#7A6650'); el[1].position = 0.075; el[1].color = hx('#CDB995')
e3 = el.new(0.925); e3.color = hx('#EFE5D0'); ln(m, sp.outputs[0], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))
bp = nn(m, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.02; ln(m, vo.outputs['Distance'], bp.inputs['Height']); ln(m, bp.outputs['Normal'], sock(m, 'Normal'))
TILE = [mat(f'tile{i}', h, 0.6) for i, h in enumerate(('#B0302A', '#F4EEE2', '#2547B5', '#7FA0E6', '#E9A48E'))]
M['belt'] = mat('belt', '#26221E', 0.7)
m = M['belt']; gp = nn(m, 'ShaderNodeNewGeometry'); vs = nn(m, 'ShaderNodeVectorMath', operation='SUBTRACT')
vs.inputs[1].default_value = (0, 2.2, 0); ln(m, gp.outputs['Position'], vs.inputs[0])
wv = nn(m, 'ShaderNodeTexWave', wave_type='RINGS', rings_direction='Z', wave_profile='SAW'); wv.inputs['Scale'].default_value = 1.4
ln(m, vs.outputs[0], wv.inputs['Vector'])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#26221E'); el[1].position = 0.86; el[1].color = hx('#3A332C')
ln(m, wv.outputs['Fac'], cr.inputs['Fac']); ln(m, cr.outputs['Color'], sock(m, 'Base Color'))

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

# ---------- shared bulb shaders: one material drives a whole group of bulbs ----------
BULB_OFF, BULB_ON = '#D9CBB0', '#FFD7A0'
def gmat(name, ref, eh=BULB_ON):
    m = mat(name, BULB_OFF, 0.25, eh=eh)
    tc = nn(m, 'ShaderNodeTexCoord', object=ref); sp = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], sp.inputs[0])
    return m, sp
def mth(m, op, a, b=None, c=None, clamp_=False):
    n = nn(m, 'ShaderNodeMath', operation=op, use_clamp=clamp_)
    for i, x in enumerate((a, b, c)):
        if x is None: continue
        if isinstance(x, (int, float)): n.inputs[i].default_value = x
        else: ln(m, x, n.inputs[i])
    return n.outputs[0]
def val(m, v=0.0): n = nn(m, 'ShaderNodeValue'); n.outputs[0].default_value = v; return n.outputs[0]
def spin_mat(name, ref, base=8.0):
    """comet chase around a ring: phase (revs), comet level, all-on level."""
    m, sp = gmat(name, ref); ph, cm, al = val(m), val(m), val(m)
    a = mth(m, 'MULTIPLY', mth(m, 'ARCTAN2', sp.outputs['Y'], sp.outputs['X']), 1 / (2 * PI))
    fr = mth(m, 'FRACT', mth(m, 'SUBTRACT', ph, a))
    c = mth(m, 'POWER', mth(m, 'MULTIPLY_ADD', fr, -1 / 0.3125, 1.0, clamp_=True), 1.6)
    out = mth(m, 'MULTIPLY', mth(m, 'MAXIMUM', mth(m, 'MULTIPLY', c, cm), al), base)
    ln(m, out, sock(m, 'Emission Strength')); return m, dict(phase=ph, comet=cm, all=al)
def sweep_mat(name, ref, base=8.0, eh=BULB_ON):
    """bulbs fill left -> right as xs passes them; bp is a travelling brighter bump."""
    m, sp = gmat(name, ref, eh); xs, bp, lv = val(m, -99), val(m, -99), val(m, 1.0)
    fill = mth(m, 'MULTIPLY', mth(m, 'SUBTRACT', xs, sp.outputs['X']), 6.0, clamp_=True)
    bmp = mth(m, 'MULTIPLY_ADD', mth(m, 'ABSOLUTE', mth(m, 'SUBTRACT', sp.outputs['X'], bp)), -1 / 0.35, 1.0, clamp_=True)
    out = mth(m, 'MULTIPLY', mth(m, 'MULTIPLY', fill, mth(m, 'MULTIPLY_ADD', bmp, 0.6, 0.7)), mth(m, 'MULTIPLY', lv, base))
    ln(m, out, sock(m, 'Emission Strength')); return m, dict(xs=xs, bp=bp, lvl=lv)
def field_mat(name, ref):
    m, sp = gmat(name, ref, '#FFC27A'); sock(m, 'Roughness').default_value = 0.3
    wr, lv = val(m, -3.0), val(m, 1.0)
    cxy = nn(m, 'ShaderNodeCombineXYZ'); ln(m, sp.outputs['X'], cxy.inputs[0]); ln(m, sp.outputs['Y'], cxy.inputs[1])
    ln_ = nn(m, 'ShaderNodeVectorMath', operation='LENGTH'); ln(m, cxy.outputs[0], ln_.inputs[0])
    sc_ = nn(m, 'ShaderNodeVectorMath', operation='SCALE'); sc_.inputs['Scale'].default_value = 5.0; ln(m, cxy.outputs[0], sc_.inputs[0])
    fl = nn(m, 'ShaderNodeVectorMath', operation='FLOOR'); ln(m, sc_.outputs[0], fl.inputs[0])
    wn = nn(m, 'ShaderNodeTexWhiteNoise', noise_dimensions='3D'); ln(m, fl.outputs[0], wn.inputs['Vector'])
    d = mth(m, 'ADD', ln_.outputs['Value'], mth(m, 'MULTIPLY_ADD', wn.outputs['Value'], 0.8, -0.4))
    on = mth(m, 'MULTIPLY_ADD', mth(m, 'SUBTRACT', wr, d), 1 / 0.8, 0.5, clamp_=True)
    ln(m, mth(m, 'MULTIPLY', mth(m, 'MULTIPLY', on, lv), 4.0), sock(m, 'Emission Strength')); return m, dict(wave=wr, lvl=lv)
def bulb_flick(es, t, level):
    """lamp ignition: on -> 40 % -> on over three frames."""
    st(es, 'default_value', t, level); st(es, 'default_value', t + FR, level * 0.4); st(es, 'default_value', t + 2 * FR, level)
def bulbs_on(m, t, level=6.0): bulb_flick(sock(m, 'Emission Strength'), t, level)
def bulbs_off(m, t): tw(sock(m, 'Emission Strength'), 'default_value', t, 0.15, 0.0, 'lin')

# ---------- status lamps ----------
LAMPC = dict(amber='#FFB04A', cream='#FFE6C0', red='#FF4A35')
def lamp(name, parent, c):
    m = mat(name, BULB_OFF, 0.30, eh=LAMPC['amber'])
    MB().sph((0, 0, 0), 0.022, m, scale=(1, 0.7, 1)).tor((0, -0.004, 0), 0.025, 0.0045, M['brass'], rot=(PI / 2, 0, 0)).ob(name, parent, c)
    return m
def lamp_to(m, t, state, level=4.5):
    es = sock(m, 'Emission Strength')
    if state == 'off': tw(es, 'default_value', t, 0.1, 0.0, 'lin'); return
    st(sock(m, 'Emission Color'), 'default_value', t, hx(LAMPC[state])); bulb_flick(es, t, level)

# ---------- component kit ----------
def cab(name, parent, w, d, h, loc=(0, 0, 0), casters=False, rot=(0, 0, 0)):
    """bevelled cobalt cabinet on a charcoal plinth with brass trims and Deco speed lines. body runs Z 0.12 -> h + 0.10."""
    root = empty(name, parent, loc, rot); top = h + 0.10; hh = top - 0.12
    body = MB().box((0, 0, 0.06), (w + 0.04, d + 0.04, 0.12), M['charcoal']).box((0, 0, (0.12 + top) / 2), (w, d, hh), M['cobalt']).ob(name + '_body', root, bev=0.028)
    tr = MB()
    for z in (0.126, top - 0.012): tr.box((0, 0, z), (w + 0.008, d + 0.008, 0.012), M['brass'])
    for sx in (-1, 1):
        for k in range(3): tr.box((sx * (w / 2 + 0.002), -d / 2 + 0.07 + k * 0.025, 0.12 + hh * 0.5), (0.004, 0.008, hh * 0.62), M['brass'])
    tr.ob(name + '_trim', root, bev=0.002)
    wheels = []
    if casters:
        for sx in (-1, 1):
            for sy in (-1, 1):
                wheels.append(MB().cyl((0, 0, 0), 0.035, 0.025, M['charcoal'], rot=(PI / 2, 0, 0)).cyl((0, 0, 0), 0.02, 0.03, M['brass'], rot=(PI / 2, 0, 0))
                              .box((0, 0, 0.0), (0.012, 0.034, 0.012), M['brass']).ob(f'{name}_w{sx}{sy}', root, (sx * (w / 2 - 0.08), sy * (d / 2 + 0.02), 0.035)))
    return root, top, body, wheels

def plate(name, parent, c, w, h, caps, cap, italic=None, bulbs=True, space=1.3, font='serif'):
    """cream enamel nameplate on a brass rim with a bulb at each end. c = centre on the machine face (faces -Y)."""
    root = empty(name, parent, c)
    MB().box((0, -0.002, 0), (w + 0.024, 0.008, h + 0.024), M['brass']).box((0, -0.010, 0), (w, 0.012, h), M['cream']).ob(name + '_p', root, bev=0.004)
    fy = -0.016; bw = w - (0.10 if bulbs else 0.04)
    if italic:
        face_txt(name + '_c', caps, font, cap, M['ink'], root, 0, fy, h * 0.17, space=space, fit=bw)
        face_txt(name + '_i', italic, 'serif_i', cap * 0.62, M['ink_red'], root, 0, fy, -h * 0.25, fit=bw)
    else: face_txt(name + '_c', caps, font, cap, M['ink'], root, 0, fy, 0, space=space, fit=bw)
    bm = None
    if bulbs:
        bm = mat(name + '_b', BULB_OFF, 0.25, eh=BULB_ON); r = min(0.012 * max(1.0, h / 0.12), 0.05)
        mb = MB()
        for sx in (-1, 1):
            x = sx * (w / 2 - r * 2.6)
            mb.sph((x, fy - r * 0.4, 0), r, bm).tor((x, fy - r * 0.2, 0), r * 1.15, r * 0.25, M['brass'], rot=(PI / 2, 0, 0), seg=20, rs=6)
        mb.ob(name + '_bl', root)
    return root, bm

def label(name, parent, c, text, cap=0.017, w=None, h=None):
    """small cream label plate with tracked Inter SemiBold caps."""
    w = w or cap * 0.95 * len(text) * 1.35 + 0.04; h = h or cap * 2.1
    MB().box((0, -0.001, 0), (w + 0.012, 0.006, h + 0.012), M['brass']).box((0, -0.006, 0), (w, 0.008, h), M['cream']).ob(name, parent, c, bev=0.002)
    face_txt(name + '_t', text, 'inter_sb', cap, M['ink'], parent, c[0], c[1] - 0.010, c[2], space=1.35, fit=w - 0.02)

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

def card(name, serial='No. 0001'):
    """the message: a printed paper card standing on a brass carrier sled. origin = carrier bottom centre, face -Y."""
    root = empty(name, None, (0, 0.18, 0.70))
    mb = MB().box((0, 0, 0.01), (0.30, 0.05, 0.02), M['brass_satin'])
    for sx in (-1, 1): mb.box((sx * 0.115, -0.006, 0.026), (0.022, 0.008, 0.014), M['brass_satin'])
    mb.box((0, 0, 0.115), (0.30, 0.004, 0.19), M['paper'])
    fy = -0.002
    mb.box((0, fy - 0.0003, 0.10), (0.26, 0.0006, 0.0015), M['ink'])
    for i in range(10): mb.box((-0.1235 + 0.011 + i * 0.025, fy - 0.0003, 0.07), (0.022, 0.0006, 0.03), TILE[i % 5])
    mb.ob(name + '_m', root, bev=0.0015)
    face_txt(name + '_tp', 'TOPIC', 'inter_sb', 0.010, M['ink_red'], root, -0.135, fy, 0.19, space=1.35, ax='LEFT')
    face_txt(name + '_id', 'new-post', 'mono', 0.011, M['ink'], root, 0.135, fy, 0.19, ax='RIGHT')
    face_txt(name + '_ti', 'new post', 'inter_b', 0.036, M['ink'], root, 0, fy, 0.135, space=0.98)
    face_txt(name + '_no', serial, 'mono', 0.008, M['ink'], root, 0.135, fy, 0.045, ax='RIGHT')
    return root

def mini(name, parent, loc, w, h, k, cap, serial=None):
    """small printed card (feed column / queue column)."""
    root = empty(name, parent, loc)
    mb = MB().box((0, 0, 0), (w, 0.004, h), M['paper']); tw_ = w * 0.07
    for i in range(6): mb.box((w * 0.05 + i * (tw_ + 0.003), -0.0023, -h * 0.22), (tw_, 0.0006, h * 0.26), TILE[(i + k) % 5])
    mb.ob(name + '_m', root, bev=0.001)
    face_txt(name + '_t', 'new post', 'inter_b', cap, M['ink'], root, -w * 0.44, -0.002, h * 0.16, ax='LEFT')
    if serial: face_txt(name + '_s', serial, 'mono', cap * 0.5, M['ink'], root, -w * 0.44, -0.002, -h * 0.24, ax='LEFT')
    return root

def rollers(mb, pts, width=0.36, pitch=0.06, frame=True):
    """roller conveyor whose roller tops follow the polyline pts."""
    for a, b in zip(pts, pts[1:]):
        a, b = Vector(a), Vector(b); d = b - a; Lg = d.length; R = frame_along(d)
        up, side = R.col[2], R.col[1]; rr = R @ Matrix.Rotation(-PI / 2, 3, 'X')
        n = max(1, int(Lg / pitch))
        for k in range(n + 1):
            p = a + d * (k / n) - up * 0.018
            mb.cyl(p, 0.018, width - 0.05, M['charcoal'], rot=rr, seg=12)
            for sx in (-1, 1): mb.cyl(p + side * sx * (width / 2 - 0.022), 0.02, 0.008, M['brass'], rot=rr, seg=12)
        mid = (a + b) / 2
        for sx in (-1, 1): mb.box(mid + side * sx * (width / 2) + up * 0.004, (Lg, 0.015, 0.03), M['brass'], rot=R)
        if frame: mb.box(mid - up * 0.06, (Lg, width + 0.01, 0.035), M['cobalt_deep'], rot=R)
    return mb

def coin(name, parent, loc):
    mb = MB().cyl((0, 0, 0.004), 0.05, 0.008, M['brass'], seg=32)
    pts = [((0.034 if i % 2 == 0 else 0.014) * math.cos(PI / 2 + i * PI / 5), (0.034 if i % 2 == 0 else 0.014) * math.sin(PI / 2 + i * PI / 5)) for i in range(10)]
    mb.prism(pts, 0.002, M['brass'], c=(0, 0, 0.009))
    return mb.ob(name, parent, loc)

# ---------- subscriber bays ----------
FACE = -0.375
BAYWORDS = {k: ['IDLE', w, 'SLOW', 'SUBSCRIBED', 'RECEIVED', 'GOT IT', '', ''] for k, w in (('notify', 'DONE'), ('email', 'SENT'), ('feed', 'UPDATED'), ('badges', 'ISSUED'))}
BAYNAME = dict(notify=('NOTIFY', 'followers'), email=('EMAIL', 'inbox'), feed=('FEED', 'timeline'), badges=('BADGES', 'new feature'))
class Bay: pass
def gauge_angle(v): return (v / 10 - 0.5) * rad(270)
AIR = mat('airmail', '#F2E9D6', 0.75)
m = AIR; tc = nn(m, 'ShaderNodeTexCoord'); sp = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], sp.inputs[0])
wv = nn(m, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL', wave_profile='SAW'); wv.inputs['Scale'].default_value = 11.0
ln(m, tc.outputs['Object'], wv.inputs['Vector'])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#B0302A'); el[1].position = 0.333; el[1].color = hx('#F2E9D6'); el.new(0.666).color = hx('#2547B5')
ln(m, wv.outputs['Fac'], cr.inputs['Fac'])
bx = mth(m, 'GREATER_THAN', mth(m, 'ABSOLUTE', sp.outputs['X']), 0.098); bz = mth(m, 'GREATER_THAN', mth(m, 'ABSOLUTE', mth(m, 'SUBTRACT', sp.outputs['Z'], 0.06)), 0.048)
mx = nn(m, 'ShaderNodeMix', data_type='RGBA'); ln(m, mth(m, 'MAXIMUM', bx, bz), mx.inputs['Factor']); mx.inputs[6].default_value = hx('#F2E9D6')
ln(m, cr.outputs['Color'], mx.inputs[7]); ln(m, mx.outputs[2], sock(m, 'Base Color'))

def bay(kind, name, loc, yaw=0.0):
    B = Bay(); B.kind = kind; B.name = name; B.ev = []
    B.root, top, B.body, B.wheels = cab(name, None, 0.90, 0.75, 1.18, (loc[0], loc[1], 0), casters=True, rot=(0, 0, yaw))
    cp, it = BAYNAME[kind]
    _, B.pb = plate(name + '_np', B.root, (0, FACE, 1.205), 0.62, 0.11, cp, 0.040, it)
    B.st = Drum(name + '_st', B.root, (0.04, FACE, 1.035), 0.40, 0.09, BAYWORDS[kind], red=(2,), cap=0.040)
    B.lamp = lamp(name + '_lamp', B.root, (-0.27, FACE - 0.004, 1.035))
    # gate: brass stamp arm cantilevered from the face; the head is its own object
    MB().box((0, FACE - 0.02, 0.59), (0.07, 0.04, 0.06), M['brass_satin']).box((0, -0.52, 0.605), (0.03, 0.29, 0.02), M['brass_satin']).ob(name + '_arm', B.root, bev=0.004)
    B.stamp = MB().box((0, 0, 0), (0.08, 0.05, 0.04), M['brass_satin']).box((0, 0, 0.03), (0.014, 0.014, 0.03), M['steel']).ob(name + '_stamp', B.root, (0, -0.625, 0.548), bev=0.004)
    if kind == 'notify':
        label(name + '_lb', B.root, (0, FACE, 0.905), 'NOTIFIED')
        B.odo = Odo(name + '_od', B.root, (0, FACE, 0.745), 7, 0.07, 0.10, commas=(0, 3), cap=0.066)
    elif kind == 'badges':
        label(name + '_lb', B.root, (0, FACE, 0.905), 'ISSUED')
        B.odo = Odo(name + '_od', B.root, (0, FACE, 0.745), 4, 0.07, 0.10, cap=0.066)
        pr = MB()
        for sx in (-1, 1): pr.cyl((sx * 0.13, 0.05, top + 0.18), 0.018, 0.36, M['brass_satin'])
        pr.box((0, 0.05, top + 0.37), (0.32, 0.06, 0.04), M['brass_satin']).cyl((0, 0.05, top + 0.01), 0.07, 0.02, M['brass_satin'], seg=32).cyl((0, 0.05, top + 0.004), 0.1, 0.008, M['charcoal'], seg=32)
        pr.ob(name + '_press', B.root, bev=0.004)
        B.head = MB().cyl((0, 0, 0.035), 0.09, 0.07, M['brass_satin'], seg=32).cyl((0, 0, 0.13), 0.02, 0.12, M['steel']).ob(name + '_head', B.root, (0, 0.05, top + 0.15), bev=0.004)
        B.top = top; B.coins = []
        for k in range(6): coin(f'{name}_stk{k}', B.root, (0.30, 0.05, top + k * 0.008))
        for k in range(7):
            c = coin(f'{name}_coin{k}', B.root, (0, 0.05, top + 0.02)); c.scale = (0.001,) * 3; B.coins.append(c)
    elif kind == 'email':
        gx, gz = -0.20, 0.77; gy = FACE - 0.02
        g = MB().cyl((gx, gy, gz), 0.13, 0.012, M['cream'], rot=(PI / 2, 0, 0), seg=48).tor((gx, gy - 0.006, gz), 0.13, 0.012, M['brass'], rot=(PI / 2, 0, 0))
        for i in range(11):
            a = gauge_angle(i); g.box((gx + 0.105 * math.sin(a), gy - 0.0065, gz + 0.105 * math.cos(a)), (0.004, 0.0008, 0.02), M['ink'], rot=(0, a, 0))
        for i in range(11):
            a = gauge_angle(7.5 + i * 0.25); g.box((gx + 0.085 * math.sin(a), gy - 0.0065, gz + 0.085 * math.cos(a)), (0.012, 0.0008, 0.01), M['brick'], rot=(0, a, 0))
        g.ob(name + '_gauge', B.root)
        face_txt(name + '_load', 'LOAD', 'inter_sb', 0.014, M['ink'], B.root, gx, gy - 0.006, gz - 0.06, space=1.35)
        B.needle = MB().box((0, -0.002, 0.045), (0.006, 0.003, 0.11), M['brick']).cyl((0, -0.004, 0), 0.012, 0.008, M['brass'], rot=(PI / 2, 0, 0)).ob(name + '_needle', B.root, (gx, gy - 0.009, gz), (0, gauge_angle(0), 0))
        ex, ez_ = 0.20, 0.77; fr = MB(); pz = 0.035
        fr.box((ex, FACE - pz / 2, 0.6025), (0.31, pz, 0.135), M['cobalt']).box((ex, FACE - pz / 2, 0.8825), (0.31, pz, 0.025), M['cobalt'])
        for sx in (-1, 1): fr.box((ex + sx * 0.1475, FACE - pz / 2, 0.77), (0.015, pz, 0.20), M['cobalt'])
        fr.box((ex, FACE - 0.003, 0.715), (0.28, 0.006, 0.36), M['charcoal'])
        for sz in (-1, 1): fr.box((ex, FACE - pz - 0.002, 0.77 + sz * 0.103), (0.30, 0.005, 0.008), M['brass'])
        for sx in (-1, 1): fr.box((ex + sx * 0.143, FACE - pz - 0.002, 0.77), (0.008, 0.005, 0.21), M['brass'])
        fr.ob(name + '_ewin', B.root, bev=0.004)
        B.env = MB().box((0, 0, 0.06), (0.22, 0.003, 0.12), AIR).tor((-0.03, -0.0022, 0.065), 0.022, 0.0016, M['ink'], rot=(PI / 2, 0, 0), seg=32, rs=6) \
            .box((0.075, -0.0019, 0.085), (0.026, 0.0008, 0.03), M['brick']).ob(name + '_env', B.root, (ex, FACE - 0.016, 0.535))
    elif kind == 'feed':
        fx, fz = 0.03, 0.775; pz = 0.035; fr = MB()
        fr.box((fx, FACE - pz / 2, 0.935), (0.30, pz, 0.03), M['cobalt']).box((fx, FACE - pz / 2, 0.615), (0.30, pz, 0.03), M['cobalt'])
        for sx in (-1, 1): fr.box((fx + sx * 0.14, FACE - pz / 2, fz), (0.02, pz, 0.29), M['cobalt'])
        fr.box((fx, FACE - 0.003, fz), (0.28, 0.006, 0.34), M['charcoal'])
        for sz in (-1, 1): fr.box((fx, FACE - pz - 0.002, fz + sz * 0.146), (0.27, 0.005, 0.008), M['brass'])
        for sx in (-1, 1): fr.box((fx + sx * 0.131, FACE - pz - 0.002, fz), (0.008, 0.005, 0.30), M['brass'])
        fr.ob(name + '_fwin', B.root, bev=0.004)
        label(name + '_lb', B.root, (-0.30, FACE, 0.88), 'LATEST', cap=0.015)
        B.slots = [0.885 - i * 0.07 for i in range(4)]; B.cards = []; B.nfeed = 0; B.fx = fx
        for j in range(11):
            s_ = 3 - j
            mc = mini(f'{name}_mc{j}', B.root, (fx, FACE - 0.016, B.slots[clamp(s_, 0, 3) if s_ >= 0 else 0]), 0.22, 0.06, j, 0.016)
            if s_ < 0: mc.scale = (1, 1, 0.001)
            B.cards.append(mc)
    return B

def stamp(B, t):
    """stamp head: 2 frames down, 5 frames up."""
    tw(B.stamp, 'location', t - 2 * FR, 2 * FR, (0, -0.625, 0.527), 'in2'); tw(B.stamp, 'location', t, 5 * FR, (0, -0.625, 0.548), 'out')
def feed_shift(B, t):
    """the column slides down one pitch (ease-out-back); bottom card hides, a new one appears at the top."""
    n = B.nfeed; B.nfeed += 1
    for j, mc in enumerate(B.cards):
        s0 = 3 - j + n; s1 = s0 + 1
        if s1 < 0 or s0 > 3: continue
        if s0 < 0:   # incoming at the top
            st(mc, 'location', t - FR, (B.fx, FACE - 0.016, B.slots[0])); tw(mc, 'scale', t, 0.22, (1, 1, 1), 'out')
        elif s1 > 3:  # leaving at the bottom
            tw(mc, 'location', t, 0.22, (B.fx, FACE - 0.016, B.slots[3] - 0.03), 'out'); tw(mc, 'scale', t, 0.18, (1, 1, 0.001), 'in2')
        else: tw(mc, 'location', t, 0.22, (B.fx, FACE - 0.016, B.slots[s1]), 'back')
def env_rise(B, t, level=1.0, dur=0.3):
    z = 0.535 + 0.145 * level; tw(B.env, 'location', t, dur, (0.20, FACE - 0.016, z), 'back' if level >= 1 else 'out')
def env_down(B, t, dur=0.15): tw(B.env, 'location', t, dur, (0.20, FACE - 0.016, 0.535), 'in2')
def needle(B, t, v, dur=0.25, ez='back'): tw(B.needle, 'rotation_euler', t, dur, (0, gauge_angle(v), 0), ez)
def coin_press(B, t):
    """the press slams in 2 frames, the coin pops 0.12 m, flips 360 deg in X and lands on the stack."""
    k = len([1 for _ in B.ev if _ == 'coin']); B.ev.append('coin'); c = B.coins[k]; top = B.top
    st(c, 'location', t - 0.35, (0, 0.05, top + 0.02)); tw(c, 'scale', t - 0.35, 0.15, (1, 1, 1), 'back')
    tw(B.head, 'location', t - 2 * FR, 2 * FR, (0, 0.05, top + 0.03), 'in2'); tw(B.head, 'location', t + 0.05, 5 * FR, (0, 0.05, top + 0.15), 'out')
    tw(c, 'location', t + 0.12, 0.16, (0.12, 0.05, top + 0.16), 'out2'); tw(c, 'rotation_euler', t + 0.12, 0.36, (2 * PI, 0, 0), 'out2')
    tw(c, 'location', t + 0.28, 0.2, (0.30, 0.05, top + 0.048 + k * 0.008), 'in2')

# ---------- helpers for sets ----------
def hide(o, t): st(o, 'scale', t, (0.001,) * 3)
def show(o, t, s=(1, 1, 1)): st(o, 'scale', t, s)
def seg(mb, a, b, r, m, n=8):
    a, b = Vector(a), Vector(b); d = b - a
    rm = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix()
    return mb.cyl((a + b) / 2, r, d.length, m, rot=rm, seg=n)
def border_pts(w, h, step):
    """points around a w x h rectangle (x, z) at ~step spacing."""
    pts = []; per = 2 * (w + h); n = max(4, int(per / step))
    for i in range(n):
        s = per * i / n
        if s < w: pts.append((-w / 2 + s, h / 2))
        elif s < w + h: pts.append((w / 2, h / 2 - (s - w)))
        elif s < 2 * w + h: pts.append((w / 2 - (s - w - h), -h / 2))
        else: pts.append((-w / 2, -h / 2 + (s - 2 * w - h)))
    return pts
TV = Vector((0, 2.2, 0))

# ---------- POST SERVICE module (0, 0), faces -Y; never translates ----------
post = empty('post')
cab('postc', post, 0.90, 0.80, 1.00)
MB().box((0, 0, 1.18), (0.80, 0.70, 0.16), M['cobalt']).ob('post_crown', post, bev=0.025)
MB().box((0, 0, 1.106), (0.808, 0.708, 0.012), M['brass']).ob('post_crown_trim', post, bev=0.002)
sl = MB().box((0, 0.18, 1.2615), (0.34, 0.03, 0.004), M['charcoal'])
for sy in (-1, 1): sl.box((0, 0.18 + sy * 0.021, 1.266), (0.36, 0.008, 0.012), M['brass'])
sl.ob('post_slot', post, bev=0.002)
vb = MB()
for k in range(6): vb.box((0, 0.402, 0.40 + k * 0.09), (0.60, 0.012, 0.03), M['charcoal'])
vb.ob('post_vents', post, bev=0.004)
btn = empty('btn', post, (0, -0.10, 1.26))
MB().tor((0, 0, 0.012), 0.11, 0.018, M['brass'], seg=64, rs=12).ob('btn_bezel', btn)
dome = MB().cyl((0, 0, 0.0175), 0.075, 0.035, M['brick_btn'], seg=48).sph((0, 0, 0.035), 0.075, M['brick_btn'], seg=32, ring=12, scale=(1, 1, 0.4)).ob('btn_dome', btn, (0, 0, 0))
SPIN, SPN = spin_mat('spin', btn)
sb = MB()
for i in range(16):
    a = 2 * PI * i / 16; x, y = 0.11 * math.cos(a), 0.11 * math.sin(a)
    sb.sph((x, y, 0.038), 0.011, SPIN, seg=12, ring=6)
sb.ob('btn_bulbs', btn, shadow=False)
MB().box((0, -0.142, 0.016), (0.075, 0.006, 0.028), M['cream']).ob('btn_tab', btn, bev=0.002)
face_txt('btn_post', 'POST', 'inter_sb', 0.011, M['ink'], btn, 0, -0.145, 0.016, space=1.35)
_, POSTPB = plate('post_np', post, (0, -0.40, 1.02), 0.70, 0.13, 'POST SERVICE', 0.042, 'publisher')
POST_ST = Drum('post_st', post, (0.03, -0.40, 0.84), 0.50, 0.10, ['READY', 'SENDING...', 'WAITING...', 'REWRITING', 'PUBLISHED', '', '', ''], red=(3,), cap=0.044)
POSTLAMP = lamp('post_lamp', post, (-0.32, -0.404, 0.84))
label('post_rwl', post, (0, -0.40, 0.68), 'REWRITES')
POST_RW = Odo('post_rw', post, (0, -0.40, 0.50), 2, 0.085, 0.12, cap=0.082)

# ---------- monolith: side chute, ledge, cap, wires, crane, crate ----------
mchute = empty('mchute')
rollers(MB(), [(0.16, 0.15, 1.27), (0.70, 0.05, 1.10), (0.70, -0.625, 0.31)], width=0.36).ob('mchute_r', mchute, bev=0.0)
mledge = empty('mledge')
lm = rollers(MB(), [(0.55, -0.625, 0.30), (3.90, -0.625, 0.30)])
for x in (0.9, 1.9, 2.9, 3.8): lm.box((x, -0.625, 0.11), (0.06, 0.24, 0.22), M['cobalt_deep'])
lm.ob('mledge_r', mledge)
CAP = empty('cap', None, (2.35, 0, 1.28))
cm_ = MB().box((0, 0, 0.07), (2.90, 0.80, 0.14), M['cobalt'])
cm_.ob('cap_body', CAP, bev=0.02)
ct = MB()
for sy in (-1, 1): ct.box((0, sy * 0.402, 0.134), (2.904, 0.006, 0.012), M['brass']); ct.box((0, sy * 0.402, 0.006), (2.904, 0.006, 0.012), M['brass'])
for x in (-1.2, -0.4, 0.4, 1.2): ct.cyl((x, 0, 0.145), 0.02, 0.012, M['brass'])
for sx in (-1, 1): ct.tor((sx * 1.30, 0, 0.17), 0.035, 0.008, M['steel'], rot=(PI / 2, 0, 0), seg=24, rs=6)
ct.ob('cap_trim', CAP, bev=0.002)
_, CAPPB = plate('cap_np', CAP, (0, -0.40, 0.07), 2.2, 0.11, 'POST SERVICE', 0.06, space=1.4)
WIRES = []
random.seed(7)
for k, m_ in enumerate([M['brick'], M['cobalt'], M['cream'], M['brick'], M['cobalt_deep'], M['cream']]):
    pts = [(1.0 + i * 0.45, random.uniform(-0.3, 0.3), 1.30 + random.uniform(0, 0.09)) for i in range(7)]
    WIRES.append(tube(f'wire{k}', pts, 0.012, m_))
HOOKS = []
for sx in (-1, 1):
    h = empty(f'hook{sx}', None, (2.35 + sx * 1.30, 0, 7.5))
    MB().tor((0, 0, 0.05), 0.05, 0.01, M['steel'], rot=(PI / 2, 0, 0), seg=24, rs=6, arc=1.5 * PI).cyl((0, 0, 0.13), 0.012, 0.06, M['steel']).ob(f'hookm{sx}', h)
    MB().cyl((0, 0, 4.16), 0.008, 8.0, M['steel'], seg=8).ob(f'cable{sx}', h)
    HOOKS.append(h)
CRATE = empty('crate', None, (6.4, 0, 6.0))
cr_ = MB(); W_, D_, H_ = 0.9, 0.75, 1.2; zc = -0.10 - H_ / 2
for sx in (-1, 1):
    for sy in (-1, 1): cr_.box((sx * W_ / 2, sy * D_ / 2, zc), (0.025, 0.025, H_), M['brass_satin'])
for sz in (-1, 1):
    for sy in (-1, 1): cr_.box((0, sy * D_ / 2, zc + sz * H_ / 2), (W_, 0.025, 0.025), M['brass_satin'])
    for sx in (-1, 1): cr_.box((sx * W_ / 2, 0, zc + sz * H_ / 2), (0.025, D_, 0.025), M['brass_satin'])
for sx in (-1, 1): seg(cr_, (sx * W_ / 2, 0, -0.10), (0, 0, 0), 0.006, M['steel'])
cr_.cyl((0, 0, 4.0), 0.008, 8.0, M['steel'], seg=8)
cr_.cyl((0.0, -D_ / 2 - 0.01, -0.22), 0.002, 0.12, M['brick'], seg=6)
cr_.ob('crate_m', CRATE, bev=0.004)
TAG = empty('tag', CRATE, (0, -D_ / 2 - 0.012, -0.28))
MB().box((0, 0, -0.06), (0.34, 0.004, 0.12), M['paper']).ob('tag_m', TAG, bev=0.0015)
face_txt('tag_t', 'NEW FEATURE', 'dinc', 0.045, M['ink'], TAG, 0, -0.002, -0.06, space=1.08, fit=0.30)

# ---------- bays ----------
MONO_X = dict(notify=1.40, email=2.35, feed=3.30)
BAYS = {k: bay(k, 'b' + k, (MONO_X[k], 0)) for k in ('notify', 'email', 'feed')}
BAYS['badges'] = bay('badges', 'bbadges', (5.2, 3.6), 0.0)
ARC = dict(notify=(-1.89, 3.12), email=(-0.75, 4.16), feed=(0.75, 4.16), badges=(1.89, 3.12))
ARCYAW, GATE, UDIR = {}, {}, {}
for k, (x, y) in ARC.items():
    d = TV - Vector((x, y, 0)); yw = 0.75 * math.atan2(d.x, -d.y); ARCYAW[k] = yw
    g = Vector((x + 0.625 * math.sin(yw), y - 0.625 * math.cos(yw), 0.30)); GATE[k] = g
    u = Vector((g.x - TV.x, g.y - TV.y, 0)).normalized(); UDIR[k] = u
NCABLE = tube('ncable', [(-1.89, 3.55, 0.35), (-1.6, 4.4, 0.03), (-1.0, 5.6, 0.03), (-0.6, 6.5, 0.13)], 0.03, M['charcoal'])
NCABLE.scale = (0.001,) * 3

# ---------- topic hub ----------
HUB = empty('hub', None, (0, 2.2, -0.95))
PORTANG = {k: math.atan2(u.y, u.x) for k, u in UDIR.items()}
hm = MB().cyl((0, 0, 0.47), 0.70, 0.86, M['cobalt'], seg=96)
for i in range(24):
    a = 2 * PI * i / 24
    if min(abs((a - pa + PI) % (2 * PI) - PI) for pa in PORTANG.values()) < rad(11): continue
    hm.box((0.704 * math.cos(a), 0.704 * math.sin(a), 0.47), (0.012, 0.012, 0.80), M['brass'], rot=(0, 0, a))
hm.tor((0, 0, 0.06), 0.705, 0.014, M['brass'], seg=96, rs=8)
hm.cyl((0, 0, 0.900), 0.62, 0.010, M['cream'], seg=96)
for i in range(60):
    a = 2 * PI * i / 60; hm.box((0.455 * math.cos(a), 0.455 * math.sin(a), 0.9055), (0.03, 0.004 if i % 5 else 0.007, 0.0012), M['ink'], rot=(0, 0, a))
hm.box((0, -0.32, 0.9055), (0.34, 0.03, 0.002), M['charcoal'])
for sy in (-1, 1): hm.box((0, -0.32 + sy * 0.021, 0.908), (0.36, 0.008, 0.008), M['brass'])
PORTLAMP = {}
for k, u in UDIR.items():
    pa = PORTANG[k]; rz = yaw_to(u.x, u.y); c = u * 0.700
    hm.box((c.x, c.y, 0.42), (0.40, 0.03, 0.30), M['brass'], rot=(0, 0, rz))
    hm.box((c.x + u.x * 0.003, c.y + u.y * 0.003, 0.415), (0.36, 0.03, 0.25), M['charcoal'], rot=(0, 0, rz))
hm.ob('hub_drum', HUB, bev=0.004)
for k, u in UDIR.items():
    c = u * 0.712; PORTLAMP[k] = lamp('plamp_' + k, HUB, (c.x, c.y, 0.63)); bpy.data.objects['plamp_' + k].rotation_euler = (0, 0, yaw_to(u.x, u.y))
HRING = empty('hub_ring', HUB, (0, 0, 0.905))
rg = MB().tor((0, 0, 0), 0.66, 0.022, M['brass'], seg=96, rs=10)
for i in range(12): a = 2 * PI * i / 12; rg.box((0.66 * math.cos(a), 0.66 * math.sin(a), 0.02), (0.02, 0.035, 0.012), M['brass'], rot=(0, 0, a))
rg.ob('hub_ring_m', HRING)
RING = 'TOPIC · NEW-POST · ' * 3; n_ = len(RING)
for i, ch in enumerate(RING):
    if ch == ' ': continue
    th = -PI / 2 - 0.35 + 2 * PI * i / n_
    txt(f'ring{i}', ch, 'inter_sb', 0.040, M['ink'], HUB, (0.53 * math.cos(th), 0.53 * math.sin(th), 0.9064), (0, 0, th + PI / 2), 0.0006)
txt('hub_word', 'new-post', 'serif_i', 0.10, M['ink'], HUB, (0, -0.02, 0.9064), (0, 0, 0), 0.0006, fit=0.60)
txt('hub_topic', 'TOPIC', 'inter_sb', 0.022, M['ink_red'], HUB, (0, 0.13, 0.9064), (0, 0, 0), 0.0006, space=1.35)
DOORS = []
for sx in (-1, 1):
    hp = [(sx * 0.719 * math.cos(-PI / 2 + PI * i / 24), 0.719 * math.sin(-PI / 2 + PI * i / 24)) for i in range(25)]
    if sx < 0: hp = hp[::-1]
    DOORS.append(MB().prism(hp, 0.02, M['cobalt_deep'], c=(0, 0, -0.012)).ob(f'door{sx}', None, (0, 2.2, 0)))
# lanes (from the port, scaling out along u) and collars at each gate
LANE, COLLAR = {}, {}
for k, u in UDIR.items():
    s0 = TV + u * 0.70; g = GATE[k]; Lg = (Vector((g.x, g.y, 0)) - Vector((s0.x, s0.y, 0))).length + 0.06
    lr = empty('lane_' + k, None, (s0.x, s0.y, 0), (0, 0, math.atan2(u.y, u.x)))
    lb = MB().box((Lg / 2, 0, 0.29), (Lg, 0.34, 0.02), M['belt']).box((Lg / 2, 0, 0.245), (Lg, 0.36, 0.07), M['cobalt_deep'])
    for sy in (-1, 1): lb.box((Lg / 2, sy * 0.18, 0.305), (Lg, 0.015, 0.03), M['brass'])
    lb.box((Lg * 0.55, 0, 0.105), (0.05, 0.28, 0.21), M['cobalt_deep'])
    lb.ob('lane_m_' + k, lr, bev=0.003)
    lr.scale = (0.001, 1, 1); LANE[k] = lr
    cl = MB()
    for sy in (-1, 1): cl.box((0, sy * 0.195, 0.31), (0.06, 0.02, 0.07), M['brass'])
    cl.box((0, 0, 0.235), (0.06, 0.41, 0.03), M['brass'])
    COLLAR[k] = cl.ob('collar_' + k, None, (g.x - u.x * 0.06, g.y - u.y * 0.06, 0), (0, 0, math.atan2(u.y, u.x)), bev=0.003)
    COLLAR[k].scale = (0.001,) * 3
# post -> topic chute
PCH = empty('pchute', None, (0, 0.40, 1.24))
rollers(MB(), [(0, 0, 0), (0, 1.22, -0.31)], width=0.38).ob('pchute_r', PCH)
PCH.scale = (1, 0.001, 1)
PSTAND = MB().box((0, 0, 0.49), (0.05, 0.05, 0.98), M['cobalt_deep']).box((0, 0, 0.01), (0.22, 0.22, 0.02), M['cobalt_deep']).ob('pstand', None, (0, 1.20, 0), bev=0.004)
PSTAND.scale = (1, 1, 0.001)

# ---------- PUB/SUB sign ----------
SIGN = empty('sign', None, (0, 2.2, 6.5), (rad(12), 0, 0))
sm_ = MB().box((0, 0, 0), (1.90, 0.06, 0.56), M['brick'])
sm_.ob('sign_m', SIGN, bev=0.01)
bl_ = MB()
for (x0, z0), (x1, z1) in (((-0.91, 0.24), (0.91, 0.24)), ((-0.91, -0.24), (0.91, -0.24)), ((-0.91, -0.24), (-0.91, 0.24)), ((0.91, -0.24), (0.91, 0.24))):
    bl_.box(((x0 + x1) / 2, -0.031, (z0 + z1) / 2), (abs(x1 - x0) + 0.012, 0.002, abs(z1 - z0) + 0.012), M['cream'])
for sx in (-1, 1): bl_.cyl((sx * 0.85, 0, 3.5), 0.012, 6.4, M['steel'], seg=8)
bl_.ob('sign_trim', SIGN)
txt('sign_t', 'PUB/SUB', 'dinc', 0.30, M['cream'], SIGN, (0, -0.030 - 0.012, -0.005), (PI / 2, 0, 0), 0.012, space=1.08)
SIGNB, SGN = sweep_mat('signb', SIGN)
sbm = MB()
for x, z in border_pts(1.80, 0.46, 0.10): sbm.sph((x, -0.034, z), 0.016, SIGNB, seg=12, ring=6).tor((x, -0.031, z), 0.019, 0.004, M['brass'], rot=(PI / 2, 0, 0), seg=16, rs=6)
sbm.ob('sign_b', SIGN, shadow=False)

# ---------- vendor plaque ----------
MB().cyl((0, 0, 0.015), 0.16, 0.03, M['brass_satin'], seg=48).cyl((0, 0, 0.505), 0.04, 0.95, M['brass_satin'], seg=24).ob('ped', None, (-1.1, 1.1, 0), bev=0.003)
PLQ = empty('plaque', None, (-1.1, 1.1, 1.15), (0, 0, rad(90)))
pq = MB().box((0, 0, 0), (0.644, 0.017, 0.324), M['brass']).box((0, 0, 0), (0.62, 0.025, 0.30), M['cream'])
for sx in (-1, 1):
    for sz in (-1, 1):
        for sy in (-1, 1): pq.cyl((sx * 0.28, sy * 0.0135, sz * 0.12), 0.008, 0.004, M['brass'], rot=(PI / 2, 0, 0), seg=12)
for sy in (-1, 1): pq.box((0, sy * 0.0128, 0.04), (0.20, 0.001, 0.004), M['brick'])
pq.cyl((0, 0.0, -0.17), 0.02, 0.05, M['brass_satin'])
pq.ob('plaque_m', PLQ, bev=0.004)
face_txt('pq_f1', 'GOOGLE CLOUD', 'inter_sb', 0.036, M['ink'], PLQ, 0, -0.0125, 0.085, space=1.3, fit=0.54)
face_txt('pq_f2', 'Pub/Sub', 'serif', 0.085, M['ink'], PLQ, 0, -0.0125, -0.045, fit=0.54)
txt('pq_b1', 'AMAZON', 'inter_sb', 0.036, M['ink'], PLQ, (0, 0.0133 + 0.0006, 0.085), (PI / 2, 0, PI), 0.0006, space=1.3, fit=0.54)
txt('pq_b2', 'SNS', 'serif', 0.085, M['ink'], PLQ, (0, 0.0133 + 0.0006, -0.045), (PI / 2, 0, PI), 0.0006, fit=0.54)

# ---------- FOLLOWERS scoreboard ----------
SB = empty('board', None, (0, 29.55, 0))
MB().box((0, 0, 5.2), (9.0, 0.30, 3.4), M['cobalt']).ob('board_f', SB, bev=0.05)
bt = MB()
for sz in (-1, 1): bt.box((0, -0.152, 5.2 + sz * 1.69), (9.0, 0.006, 0.02), M['brass'])
for sx in (-1, 1): bt.box((sx * 4.49, -0.152, 5.2), (0.02, 0.006, 3.4), M['brass'])
bt.ob('board_t', SB)
_, BOARDPB = plate('board_np', SB, (0, -0.15, 6.35), 4.2, 0.75, 'FOLLOWERS', 0.42, space=1.3)
BOARD = Odo('board_od', SB, (0, -0.15, 4.75), 7, 0.95, 1.45, commas=(0, 3), gap=0.05, cw=0.35, cap=1.05)
ap_ = MB().box((0, -0.11, 2.95), (8.9, 0.08, 1.42), M['cobalt_deep']).box((0, -0.16, 3.62), (8.9, 0.02, 0.05), M['brass'])
ap_.box((0, -0.11, 7.25), (8.9, 0.08, 1.0), M['cobalt_deep']).box((0, -0.16, 6.78), (8.9, 0.02, 0.05), M['brass']).ob('board_apron', SB, bev=0.01)
BOARDB, BDB = sweep_mat('boardb', SB)
bb_ = MB()
for x, z in border_pts(8.7, 3.1, 0.30): bb_.sph((x, -0.17, 5.2 + z), 0.035, BOARDB, seg=12, ring=6).tor((x, -0.155, 5.2 + z), 0.04, 0.008, M['brass'], rot=(PI / 2, 0, 0), seg=16, rs=6)
bb_.ob('board_b', SB, shadow=False)

# ---------- follower field ----------
FREF = empty('fref', None, (0, 6.5, 0))
FIELDM, FLD = field_mat('field', FREF)
pf = MB().box((0, 17.0, 0.06), (14.0, 21.0, 0.12), M['deck'])
pf.box((0, 17.0, 0.04), (14.08, 21.08, 0.08), M['cobalt'])
for sy in (-1, 1): pf.box((0, 17.0 + sy * 10.54, 0.121), (14.1, 0.012, 0.004), M['brass'])
for sx in (-1, 1): pf.box((sx * 7.04, 17.0, 0.121), (0.012, 21.1, 0.004), M['brass'])
pf.ob('platform', None, bev=0.01)
random.seed(18)
stems, heads = MB(), MB()
def tpl(fn, *a, **k):
    t = MB(); getattr(t, fn)((0, 0, 0), *a, **k); t.bm.verts.index_update()
    return [tuple(v.co) for v in t.bm.verts], [[v.index for v in f.verts] for f in t.bm.faces]
TSTEM = tpl('cyl', 0.006, 1.0, M['brass_satin'], seg=5, caps=False); THEAD = tpl('sph', 0.016, FIELDM, seg=8, ring=4)
NP = 0
for i in range(70):
    for j in range(105):
        x = -6.9 + i * 0.2 + random.uniform(-0.03, 0.03); y = 6.6 + j * 0.2 + random.uniform(-0.03, 0.03); h = random.uniform(0.07, 0.12)
        stems.stamp(TSTEM, (x, y, 0.12 + h / 2), M['brass_satin'], (1, 1, h))
        heads.stamp(THEAD, (x, y, 0.12 + h + 0.012), FIELDM)
        NP += 1
stems.ob('pins_stems', None, smooth=False); heads.ob('pins_heads', None, shadow=False)

# ---------- hall shell ----------
HALL = []        # (light data, base energy) dimmed for "spot the problem"
HALLEM = []      # (emission socket, base strength)
def light(name, kind, loc, aim=None, energy=100.0, color='#FFFFFF', size=None, size_y=None, spot=None, blend=0.6, vf=1.0, shadow=True, cutoff=45.0, hall=True):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = hx(color)[:3]
    if kind == 'AREA':
        ld.shape = 'RECTANGLE' if size_y else 'DISK'; ld.size = size
        if size_y: ld.size_y = size_y
    elif kind == 'SPOT': ld.spot_size = rad(spot); ld.spot_blend = blend; ld.shadow_soft_size = size or 0.1
    elif kind == 'POINT': ld.shadow_soft_size = size or 0.05
    elif kind == 'SUN': ld.angle = rad(size or 2)
    ld.volume_factor = vf; ld.use_shadow = shadow
    if cutoff and kind != 'SUN': ld.use_custom_distance = True; ld.cutoff_distance = cutoff
    o = bpy.data.objects.new(name, ld); col.objects.link(o); o.location = loc
    if aim: o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if hall: HALL.append((ld, energy))
    return o
FLOOR = MB().box((0, 7.0, -0.1), (34.0, 46.0, 0.2), M['terrazzo']).ob('floor', None, smooth=False)
cut = MB().cyl((0, 2.2, -0.1), 0.72, 0.6, M['charcoal'], seg=96).ob('floor_cut'); cut.hide_render = True; cut.display_type = 'WIRE'
bo = FLOOR.modifiers.new('hole', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'
inl = MB().ann((0, 2.2, 0), 1.02, 1.08, 0.002, M['cobalt'], seg=96).ann((0, 2.2, 0), 0.72, 0.76, 0.002, M['brass'], seg=96)
for sy in (-1, 1): inl.box((0, 17.0 + sy * 10.75, 0.001), (14.6, 0.12, 0.002), M['cobalt'])
for sx in (-1, 1): inl.box((sx * 7.25, 17.0, 0.001), (0.12, 21.6, 0.002), M['cobalt'])
for x in (-11.5, 11.5):
    for y in range(-15, 30, 5): inl.box((x, y, 0.001), (0.25, 0.25, 0.002), M['brick'], rot=(0, 0, PI / 4))
inl.ob('inlays', None, smooth=False)
def wall_x(mb, y, th, holes, m, x0=-17.0, x1=17.0, z1=9.0):
    """wall along X at y with rectangular holes (xc, w, z0, z1)."""
    xs = sorted(holes); cur = x0
    for xc, w, a, b in xs:
        mb.box(((cur + xc - w / 2) / 2, y, z1 / 2), (xc - w / 2 - cur, th, z1), m)
        mb.box((xc, y, a / 2), (w, th, a), m); mb.box((xc, y, (b + z1) / 2), (w, th, z1 - b), m); cur = xc + w / 2
    mb.box(((cur + x1) / 2, y, z1 / 2), (x1 - cur, th, z1), m)
def wall_y(mb, x, th, holes, m, y0=-16.0, y1=30.4, z1=9.0):
    cur = y0
    for yc, w, a, b in sorted(holes):
        mb.box((x, (cur + yc - w / 2) / 2, z1 / 2), (th, yc - w / 2 - cur, z1), m)
        mb.box((x, yc, a / 2), (th, w, a), m); mb.box((x, yc, (b + z1) / 2), (th, w, z1 - b), m); cur = yc + w / 2
    mb.box((x, (cur + y1) / 2, z1 / 2), (th, y1 - cur, z1), m)
BW = [(-12.0, 2.2, 1.0, 7.5), (-6.2, 2.2, 1.0, 7.5), (6.2, 2.2, 1.0, 7.5), (12.0, 2.2, 1.0, 7.5)]
SW = [(y, 2.0, 3.0, 7.0) for y in (1.5, 11.5, 16.5, 21.5)]
wm = MB(); wall_x(wm, 30.2, 0.4, BW, M['sandstone']); wall_x(wm, -16.2, 0.4, [], M['sandstone'])
for sx in (-1, 1): wall_y(wm, sx * 17.2, 0.4, SW, M['sandstone'])
wm.box((0, 7.0, 9.15), (34.8, 46.8, 0.3), M['sandstone'])
wm.ob('walls', None, smooth=False)
bm_ = MB()
for x in range(-15, 16, 5): bm_.box((x, 7.0, 8.7), (0.4, 46.0, 0.6), M['wood'])
for y in range(-15, 31, 5): bm_.box((0, y, 8.7), (34.0, 0.4, 0.6), M['wood'])
bm_.ob('beams', None, bev=0.02)
# mullions + glow planes + window lights
GLOWB, GLOWBS = emat('winglow', '#FFDDB0', 4.0); GLOWS, GLOWSS = emat('winglow_s', '#FFDDB0', 2.0)
HALLEM += [(GLOWBS, 4.0), (GLOWSS, 2.0)]
mu_, gl_ = MB(), MB()
for xc, w, a, b in BW:
    for i in range(4): mu_.box((xc - w / 2 + i * w / 3, 30.2, (a + b) / 2), (0.06, 0.08, b - a), M['cobalt'])
    for j in range(7): mu_.box((xc, 30.2, a + j * (b - a) / 6), (w, 0.08, 0.06), M['cobalt'])
    gl_.box((xc, 30.55, (a + b) / 2), (w + 0.4, 0.02, b - a + 0.4), GLOWB)
    light('win%g' % xc, 'AREA', (xc, 30.7, (a + b) / 2), (xc, 0, (a + b) / 2), 4200, '#FFC48E', size=w, size_y=b - a, vf=1.0, cutoff=45)
for sx in (-1, 1):
    for yc, w, a, b in SW:
        for i in range(3): mu_.box((sx * 17.2, yc - w / 2 + i * w / 2, (a + b) / 2), (0.08, 0.06, b - a), M['cobalt'])
        for j in range(5): mu_.box((sx * 17.2, yc, a + j * (b - a) / 4), (0.08, w, 0.06), M['cobalt'])
        gl_.box((sx * 17.55, yc, (a + b) / 2), (0.02, w + 0.4, b - a + 0.4), GLOWS)
        light('swin%d_%g' % (sx, yc), 'AREA', (sx * 17.7, yc, (a + b) / 2), (0, yc, (a + b) / 2 - 1.0), 1100, '#FFCB98', size=w, size_y=b - a, cutoff=45)
mu_.ob('mullions', None, bev=0.006); gl_.ob('glowplanes', None, smooth=False, shadow=False)
# columns
cm2 = MB()
for sx in (-1, 1):
    for y in (-6, -1, 4, 9, 14, 19, 24, 29):
        x = sx * 8.8
        cm2.box((x, y, 0.25), (1.1, 1.1, 0.5), M['colbase']).box((x, y, 4.525), (0.8, 0.8, 8.05), M['sandstone'])
        cm2.box((x, y, 8.675), (1.0, 1.0, 0.25), M['sandstone']).box((x, y, 8.9), (1.15, 1.15, 0.2), M['sandstone'])
        for z in (6.6, 6.9): cm2.box((x, y, z), (0.81, 0.81, 0.06), M['cobalt'])
        cm2.box((x, y, 0.52), (0.81, 0.81, 0.03), M['brass'])
cm2.ob('columns', None, bev=0.015)
# pendant lamps
SHADE_IN = mat('shade_in', '#E8DCC2', 0.5, emit=0.3, eh='#FFE6C0'); PBULB = mat('pbulb', BULB_OFF, 0.25, emit=10.0, eh='#FFD7A0')
HALLEM += [(sock(SHADE_IN, 'Emission Strength'), 0.3), (sock(PBULB, 'Emission Strength'), 10.0)]
PEND = [((x, y, 4.6), 110) for x in (-4.5, 4.5) for y in (8, 12.5, 17, 21.5, 26)] + [((x, y, 4.8), 180) for x in (-3.2, 3.2) for y in (-0.6,)] \
     + [((x, 3.8, 4.8), 180) for x in (-3.0, 3.0)] + [((x, -0.9, 3.8), 160) for x in (-13.0, -15.0)]
ps, pb_ = MB(), MB()
for (x, y, z), e in PEND:
    ps.cyl((x, y, z + 0.14), 0.34, 0.28, M['cobalt'], seg=32, r2=0.07, caps=False).cyl((x, y, z + 0.14), 0.33, 0.27, SHADE_IN, seg=32, r2=0.065, caps=False)
    ps.cyl((x, y, (z + 0.28 + 9.0) / 2), 0.006, 9.0 - z - 0.28, M['charcoal'], seg=6).cyl((x, y, z + 0.30), 0.04, 0.05, M['brass'], seg=16)
    pb_.sph((x, y, z + 0.06), 0.05, PBULB, seg=16, ring=8)
    light('pend_%g_%g' % (x, y), 'POINT', (x, y, z + 0.05), None, e, '#FFC792', size=0.05, vf=0.3)
ps.ob('pend_shades'); pb_.ob('pend_bulbs', shadow=False)
# sorting cabinets along the side walls
sc_ = MB()
for sx in (-1, 1):
    for y in (-11.0, -7.5, -4.0, 7.0, 10.5, 14.0):
        x = sx * 16.75; ff = -sx
        sc_.box((x, y, 1.1), (0.5, 2.4, 2.2), M['cobalt'])
        sc_.box((x + ff * 0.24, y, 1.15), (0.03, 2.2, 1.9), M['cream'])
        for i in range(9): sc_.box((x + ff * 0.255, y - 1.1 + i * 2.2 / 8, 1.15), (0.02, 0.025, 1.9), M['cobalt'])
        for j in range(7): sc_.box((x + ff * 0.255, y, 0.2 + j * 1.9 / 6), (0.02, 2.2, 0.025), M['cobalt'])
        for i in range(8):
            for j in range(6):
                if random.random() < 0.5: sc_.box((x + ff * 0.235, y - 1.1 + (i + 0.5) * 2.2 / 8, 0.2 + j * 1.9 / 6 + 0.07), (0.004, 0.25, 0.08), M['paper'])
sc_.ob('sorters', None, bev=0.006)
# carts and card bundles
def cart(name, loc, yaw):
    r = empty(name, None, loc, (0, 0, yaw)); m_ = MB()
    for sx in (-1, 1):
        for sy in (-1, 1): m_.cyl((sx * 0.43, sy * 0.23, 0.45), 0.012, 0.76, M['brass_satin'], seg=10); m_.cyl((sx * 0.43, sy * 0.23, 0.04), 0.035, 0.025, M['charcoal'], rot=(PI / 2, 0, 0), seg=16)
    for z in (0.25, 0.65): m_.box((0, 0, z), (0.9, 0.5, 0.03), M['wood'])
    for k in range(3):
        cx = -0.28 + k * 0.28
        for zz, n in ((0.265, 20), (0.665, 14 + k * 3)):
            m_.box((cx, 0, zz + n * 0.002), (0.22, 0.30, n * 0.004), M['paper'])
            m_.box((cx, 0, zz + n * 0.002), (0.225, 0.008, n * 0.004 + 0.004), M['brick'])
    m_.ob(name + '_m', r, bev=0.004)
for nm, lc, yw in (('cart1', (-3.6, 1.0, 0), 0.3), ('cart2', (-3.4, 5.4, 0), -0.2), ('cart3', (4.2, 6.0, 0), 0.5)): cart(nm, lc, yw)
bd = MB()
for x, y, n in ((-3.0, 0.3, 12), (-2.9, 1.8, 8), (-4.2, 4.6, 16), (3.7, 5.2, 10), (4.8, 5.5, 6), (-4.0, 1.6, 9)):
    bd.box((x, y, n * 0.002), (0.30, 0.22, n * 0.004), M['paper'], rot=(0, 0, random.uniform(-0.5, 0.5)))
bd.ob('bundles', None, bev=0.002)
# haze + dust
def haze(name, c, size, dens, aniso, colr):
    hm_ = bpy.data.materials.new(name)
    try: hm_.use_nodes = True
    except Exception: pass
    nt = hm_.node_tree; nt.nodes.remove(principled(hm_)); pv = nt.nodes.new('ShaderNodeVolumePrincipled')
    pv.inputs['Density'].default_value = dens; pv.inputs['Anisotropy'].default_value = aniso; pv.inputs['Color'].default_value = hx(colr)
    nt.links.new(pv.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    o = MB().box((0, 0, 0), size, hm_).ob(name, None, c, smooth=False, shadow=False); return o, pv.inputs['Density']
HAZE, HAZED = haze('haze_hall', (0, 7.0, 4.5), (34.0, 46.0, 9.0), 0.007, 0.55, '#E8E0D2')
DUSTM = mat('dust', '#E8DCC2', 0.6, emit=0.6, eh='#FFE9C4')
DUST = []
for nm, c, s, n in (('dust1', (0.8, -0.4, 1.6), (6, 6, 3), 400), ('dust2', (0, 8.0, 1.6), (12, 4, 3), 300)):
    dm = MB()
    for _ in range(n): dm.tet((random.uniform(-s[0] / 2, s[0] / 2), random.uniform(-s[1] / 2, s[1] / 2), random.uniform(-s[2] / 2, s[2] / 2)), 0.004, DUSTM)
    DUST.append(dm.ob(nm, None, c, smooth=False, shadow=False))
# world
WORLD = bpy.data.worlds.new('w'); sc.world = WORLD
try: WORLD.use_nodes = True
except Exception: pass
WBG = WORLD.node_tree.nodes['Background']; WBG.inputs['Color'].default_value = hx('#2A2622'); WBG.inputs['Strength'].default_value = 0.35
# hall lights
light('KEY', 'AREA', (-3.6, -3.2, 5.0), (0.4, 1.6, 0.7), 900, '#FFD9B0', size=2.5)
light('RIM', 'SPOT', (0.5, 8.5, 4.6), (0, 2.0, 0.8), 700, '#FFB57A', spot=45, blend=0.6, vf=0.4)
for sx in (-1, 1): light('BOARD%d' % sx, 'SPOT', (sx * 3.0, 26.5, 0.4), (0, 29.5, 5.2), 2500, '#FFCB98', spot=35, blend=0.5)
light('FILL', 'AREA', (4.0, -3.0, 2.0), (0, 1.5, 0.7), 140, '#B4C2FF', size=3.0, size_y=3.0, shadow=False)
FIELDL = [light('FIELD%d' % y, 'AREA', (0, y, 3.2), (0, y, 0), 0.0, '#FFB868', size=5.0, size_y=5.0) for y in (9, 14, 19, 24)]
HALL[:] = [(ld, e) for ld, e in HALL if not ld.name.startswith('FIELD')]
SPOTP = light('SPOT_PROBLEM', 'SPOT', (0, -0.5, 6.2), (0, -0.1, 1.2), 0.0, '#FFE2C0', spot=16, blend=0.2, size=0.05, hall=False)
light('KEY_Q', 'AREA', (-10.6, -3.4, 4.2), (-13.8, -0.3, 0.8), 600, '#FFC690', size=1.5)

# ---------- queue set (left aisle) ----------
QT, qtop, _, _ = cab('qtower', None, 0.70, 0.70, 2.30, (-12.0, -0.6, 0))
qb = MB()
for z in (0.5, 1.4, 2.2): qb.box((0, 0, z), (0.708, 0.708, 0.012), M['brass'])
qb.box((0, -0.352, 1.20), (0.36, 0.006, 1.5), M['charcoal'])
for sz in (-1, 1): qb.box((0, -0.36, 1.20 + sz * 0.756), (0.38, 0.012, 0.012), M['brass'])
for sx in (-1, 1): qb.box((sx * 0.186, -0.36, 1.20), (0.012, 0.012, 1.524), M['brass'])
qb.box((-0.36, -0.025, 0.40), (0.02, 0.38, 0.26), M['charcoal'])
qb.ob('qtower_t', QT, bev=0.002)
QPUSH = MB().box((0, 0, 0), (0.10, 0.05, 0.05), M['brass_satin']).cyl((0.08, 0, 0), 0.012, 0.12, M['brass_satin'], rot=(0, PI / 2, 0)).ob('qpush', QT, (0.24, -0.38, 0.42), bev=0.003)
QMINI = [mini(f'qmc{k}', QT, (0, -0.36, 0.51 + k * 0.12), 0.30, 0.10, k, 0.024, 'No. %04d' % (k + 1)) for k in range(12)]
QS = empty('qsign', QT, (0, -0.37, 2.50))
MB().box((0, 0, 0), (0.68, 0.04, 0.18), M['brick']).ob('qsign_m', QS, bev=0.006)
txt('qsign_t', 'MESSAGE QUEUE', 'dinc', 0.08, M['cream'], QS, (0, -0.02 - 0.008, -0.004), (PI / 2, 0, 0), 0.008, space=1.08, fit=0.56)
QSB = mat('qsignb', BULB_OFF, 0.25, emit=6.0, eh=BULB_ON)
qsb = MB()
for x, z in border_pts(0.64, 0.14, 0.075): qsb.sph((x, -0.024, z), 0.009, QSB, seg=10, ring=5)
qsb.ob('qsign_b', QS, shadow=False)
ql = rollers(MB(), [(-12.4, -0.625, 0.30), (-16.0, -0.625, 0.30)])
for x in (-12.8, -13.9, -14.9, -15.8): ql.box((x, -0.625, 0.11), (0.06, 0.24, 0.22), M['cobalt_deep'])
ql.ob('qledge')
QB = {k: bay(k, 'q' + k, (x, 0)) for k, x in (('notify', -13.4), ('email', -14.4), ('feed', -15.4))}

# ---------- radio set (X = 200): dusk rooftop ----------
RX = 200.0
MB().box((RX, 8.0, -0.1), (30.0, 30.0, 0.2), M['roof']).ob('rdeck', None, smooth=False)
MB().box((RX, 0.8, 0.475), (6.0, 0.45, 0.95), M['sandstone']).box((RX, 0.8, 0.97), (6.1, 0.55, 0.06), M['sandstone']).ob('parapet', None, bev=0.01)
et = MB()
for z in (0.71, 1.11, 0.30): et.box((RX, 0, z), (0.95, 0.40, 0.02), M['walnut'])
for sx in (-1, 1):
    for sy in (-1, 1): et.cyl((RX + sx * 0.465, sy * 0.19, 0.75), 0.012, 1.5, M['brass'], seg=12)
et.ob('etagere', None, bev=0.003)
RADIOS = []
def radio(name, loc, tuned):
    r = empty(name, None, loc); m_ = MB()
    m_.box((0, 0, 0.10), (0.30, 0.18, 0.20), M['walnut']).cyl((0, 0, 0.20), 0.15, 0.18, M['walnut'], rot=(PI / 2, 0, 0), seg=48)
    for sx in (-1, 1): m_.cyl((sx * 0.11, -0.10, 0.05), 0.018, 0.02, M['brass'], rot=(PI / 2, 0, 0), seg=16)
    m_.ob(name + '_b', r, bev=0.006)
    gr = MB().box((0, 0, -0.035), (0.20, 0.004, 0.14), M['grille']).cyl((0, 0, 0.035), 0.10, 0.004, M['grille'], rot=(PI / 2, 0, 0), seg=40)
    for i in range(5): gr.box((-0.08 + i * 0.04, -0.003, -0.01), (0.006, 0.003, 0.19), M['brass'])
    G = gr.ob(name + '_g', r, (0, -0.091, 0.205))
    dm = mat(name + '_dial', '#E8DCC2', 0.5, eh='#FFC67A')
    MB().cyl((0, 0, 0), 0.04, 0.004, dm, rot=(PI / 2, 0, 0), seg=32).tor((0, -0.002, 0), 0.042, 0.004, M['brass'], rot=(PI / 2, 0, 0), seg=32, rs=6).ob(name + '_d', r, (0, -0.092, 0.055))
    for i, nmb in enumerate(('88', '92', '96', '100', '104', '108')):
        a = rad(-60 + i * 24); face_txt(f'{name}_n{i}', nmb, 'din', 0.006, M['ink'], r, 0.028 * math.sin(a), -0.0945, 0.055 + 0.028 * math.cos(a))
    nd = MB().box((0, -0.001, 0.016), (0.003, 0.002, 0.034), M['brick']).ob(name + '_ndl', r, (0, -0.096, 0.055), (0, rad(18.6) if tuned else rad(-60), 0))
    face_txt(name + '_f', '101.1', 'mono', 0.008, M['cream'], r, 0.105, -0.0905, 0.10)
    RADIOS.append((r, G, dm, tuned)); return r
for i, (x, z) in enumerate(((199.76, 0.72), (200.24, 0.72), (199.76, 1.12), (200.24, 1.12))): radio('radio%d' % i, (x, 0, z), i != 3)
TWR = MB(); tw_m = mat('tower', '#C9A983', 0.85)
m = tw_m; tc = nn(m, 'ShaderNodeTexCoord'); spx = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Object'], spx.inputs[0])
cx_ = nn(m, 'ShaderNodeCombineXYZ'); ln(m, mth(m, 'ADD', spx.outputs['X'], spx.outputs['Y']), cx_.inputs[0]); ln(m, spx.outputs['Z'], cx_.inputs[1])
bk = nn(m, 'ShaderNodeTexBrick'); bk.inputs['Scale'].default_value = 0.35; bk.inputs['Mortar Size'].default_value = 0.6; bk.inputs['Bias'].default_value = 0.1
bk.inputs['Color1'].default_value = (1, 1, 1, 1); bk.inputs['Color2'].default_value = (0, 0, 0, 1); bk.inputs['Mortar'].default_value = (0, 0, 0, 1)
ln(m, cx_.outputs[0], bk.inputs['Vector']); sock(m, 'Emission Color').default_value = hx('#FFCE8A')
bw = nn(m, 'ShaderNodeRGBToBW'); ln(m, bk.outputs['Color'], bw.inputs[0]); ln(m, mth(m, 'MULTIPLY', bw.outputs[0], 4.0), sock(m, 'Emission Strength'))
RT = Vector((210.0, 70.0, 0))
for (w, h, z0) in ((8, 12, 0), (6, 10, 12), (4, 8, 22), (2.4, 5, 30)): TWR.box(RT + Vector((0, 0, z0 + h / 2)), (w, w, h), tw_m)
TWR.ob('rtower', None, bev=0.05)
mst = MB()
for sx in (-1, 1):
    for sy in (-1, 1): seg(mst, RT + Vector((sx * 1.0, sy * 1.0, 35)), RT + Vector((sx * 0.1, sy * 0.1, 49)), 0.06, M['cobalt_deep'])
for k in range(8):
    z = 35.5 + k * 1.7; hw = 1.0 - 0.9 * (z - 35) / 14
    mst.tor(RT + Vector((0, 0, z)), hw * 1.414, 0.04, M['cobalt_deep'], seg=4, rs=6, rot=(0, 0, PI / 4))
mst.ob('mast')
BEAC = mat('beacon', '#B0302A', 0.4, eh='#FF4A35')
MB().sph(RT + Vector((0, 0, 49.5)), 0.5, BEAC, seg=16, ring=8).ob('beacon', shadow=False)
RS = empty('rsign', None, (210.0, 67.55, 29.0))
MB().box((0, 0, 0), (6.0, 0.2, 1.6), M['brick']).ob('rsign_m', RS, bev=0.04)
txt('rsign_t', 'NEW-POST', 'dinc', 0.9, M['cream'], RS, (0, -0.1 - 0.05, 0.18), (PI / 2, 0, 0), 0.05, space=1.08, fit=5.2)
txt('rsign_f', '101.1', 'mono', 0.25, M['cream'], RS, (0, -0.1 - 0.02, -0.58), (PI / 2, 0, 0), 0.02)
RSB, RSN = sweep_mat('rsignb', RS)
rsb = MB()
for x, z in border_pts(5.8, 1.4, 0.3): rsb.sph((x, -0.12, z), 0.06, RSB, seg=10, ring=5)
rsb.ob('rsign_b', RS, shadow=False)
city_m = mat('city', '#C9A983', 0.85); m = city_m
tc = nn(m, 'ShaderNodeNewGeometry'); spx = nn(m, 'ShaderNodeSeparateXYZ'); ln(m, tc.outputs['Position'], spx.inputs[0])
cx_ = nn(m, 'ShaderNodeCombineXYZ'); ln(m, mth(m, 'ADD', spx.outputs['X'], spx.outputs['Y']), cx_.inputs[0]); ln(m, spx.outputs['Z'], cx_.inputs[1])
bk = nn(m, 'ShaderNodeTexBrick'); bk.inputs['Scale'].default_value = 0.3; bk.inputs['Mortar Size'].default_value = 0.7; bk.inputs['Bias'].default_value = 0.3
bk.inputs['Color1'].default_value = (1, 1, 1, 1); bk.inputs['Color2'].default_value = (0, 0, 0, 1); bk.inputs['Mortar'].default_value = (0, 0, 0, 1)
ln(m, cx_.outputs[0], bk.inputs['Vector']); bw = nn(m, 'ShaderNodeRGBToBW'); ln(m, bk.outputs['Color'], bw.inputs[0])
sock(m, 'Emission Color').default_value = hx('#FFCE8A'); ln(m, mth(m, 'MULTIPLY', bw.outputs[0], 3.0), sock(m, 'Emission Strength'))
random.seed(5); cty = MB(); placed = 0
while placed < 40:
    x, y = random.uniform(110, 300), random.uniform(110, 230)
    if abs(x - RX) < 0.25 * (y + 2.5) + 6: continue
    w, h = random.uniform(6, 14), random.uniform(8, 26); cty.box((x, y, h / 2), (w, w * random.uniform(0.7, 1.2), h), city_m)
    if random.random() < 0.4: cty.box((x, y, h + 4), (w * 0.6, w * 0.6, 8), city_m)
    placed += 1
cty.ob('city', None, smooth=False)
sky_m = bpy.data.materials.new('sky')
try: sky_m.use_nodes = True
except Exception: pass
nt = sky_m.node_tree; nt.nodes.remove(principled(sky_m)); e_ = nt.nodes.new('ShaderNodeEmission'); e_.inputs['Strength'].default_value = 1.2
tc = nt.nodes.new('ShaderNodeTexCoord'); sp_ = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sp_.inputs[0])
mr_ = nt.nodes.new('ShaderNodeMapRange'); mr_.inputs['From Min'].default_value = 0; mr_.inputs['From Max'].default_value = 160
nt.links.new(sp_.outputs['Z'], mr_.inputs['Value']); cr = nt.nodes.new('ShaderNodeValToRGB'); el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#F3B88A'); el[1].position = 1.0; el[1].color = hx('#4E4A7E'); el.new(0.35).color = hx('#B98AA0')
nt.links.new(mr_.outputs['Result'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], e_.inputs['Color']); nt.links.new(e_.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
MB().cyl((0, 0, 120), 260, 260, sky_m, seg=96, caps=False).ob('sky', None, (RX, 60, -10), shadow=False)
RHAZE, RHAZED = haze('haze_radio', (220, 95, 40), (200, 210, 80), 0.004, 0.4, '#CDA9A8')
# broadcast ring with a shape key: basis R 0.3 / r 0.08 at the mast top, key R 120 / r 0.6 dropped 0.66 R
RINGM = bpy.data.materials.new('bring')
try: RINGM.use_nodes = True
except Exception: pass
nt = RINGM.node_tree; nt.nodes.remove(principled(RINGM)); e_ = nt.nodes.new('ShaderNodeEmission'); e_.inputs['Color'].default_value = hx('#FFE3B5'); e_.inputs['Strength'].default_value = 2.5
tr_ = nt.nodes.new('ShaderNodeBsdfTransparent'); mx_ = nt.nodes.new('ShaderNodeMixShader'); RFADE = mx_.inputs['Fac']; RFADE.default_value = 0.0
nt.links.new(tr_.outputs[0], mx_.inputs[1]); nt.links.new(e_.outputs[0], mx_.inputs[2]); nt.links.new(mx_.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
RSEG, RRS = 160, 8
BR = MB().tor((0, 0, 0), 0.3, 0.08, RINGM, seg=RSEG, rs=RRS).ob('bring', None, (210.0, 70.0, 48.0), shadow=False)
BR.shape_key_add(name='Basis'); BIG = BR.shape_key_add(name='big', from_mix=False)
for idx, v in enumerate(BIG.data):
    i, j = divmod(idx, RRS); a = 2 * PI * i / RSEG; b = 2 * PI * j / RRS; Rr, rr = 120.0, 0.6
    v.co = Vector(((Rr + rr * math.cos(b)) * math.cos(a), (Rr + rr * math.cos(b)) * math.sin(a), rr * math.sin(b) - 0.66 * Rr))
SUN = light('SUN', 'SUN', (RX, 20, 30), None, 0.0, '#FF9F66', size=2, cutoff=None, hall=False); SUN.rotation_euler = (rad(-82), 0, 0)
light('FILL_R', 'AREA', (199.4, -3.4, 2.2), (200, 0, 1.0), 120, '#9C94D6', size=2.0, size_y=2.0, cutoff=250, hall=False)
light('KEY_R', 'AREA', (201.6, -1.9, 2.4), (200, 0, 1.0), 160, '#FFC690', size=1.0, size_y=1.0, cutoff=250, hall=False)

# ---------- timeline (design_v5 §7.1) ----------
def newcard(name, loc, rz=0.0):
    c = card(name); c.location = loc; c.rotation_euler = (0, 0, rz); c.scale = (0.001,) * 3; return c
def pop(c, t, dur=0.25, z=1.27, ez='back'):
    st(c, 'location', t - FR, (0, 0.18, 1.02)); show(c, t - FR); tw(c, 'location', t, dur, (0, 0.18, z), ez)
CHUTE_TILT = -0.249
def to_topic(c, t, slide, ring_t=None):
    """slot -> post/topic chute -> intake slot; returns the time the card is inside the topic."""
    tw(c, 'location', t, 0.12, (0, 0.40, 1.245), 'io'); tw(c, 'rotation_euler', t, 0.12, (CHUTE_TILT, 0, 0), 'io')
    t2 = t + 0.12; tw(c, 'location', t2, slide, (0, 1.62, 0.935), 'in2')
    t3 = t2 + slide; tw(c, 'location', t3, 0.06, (0, 1.88, 0.912), 'out2'); tw(c, 'rotation_euler', t3, 0.06, (0, 0, 0), 'out2')
    t4 = t3 + 0.07; tw(c, 'location', t4, 0.14, (0, 1.88, 0.70), 'in2'); hide(c, t4 + 0.15)
    ring_turn(t4 + 0.02, 30)
    return t4 + 0.15
HRING_ROT = [0.0]
def ring_turn(t, deg):
    HRING_ROT[0] += rad(deg); tw(HRING, 'rotation_euler', t, 0.45, (0, 0, HRING_ROT[0]), 'back')
def press(t, up_t):
    tw(dome, 'location', t - 2 * FR, 2 * FR, (0, 0, 0.002), 'out'); tw(dome, 'location', t, 2 * FR, (0, 0, -0.018), 'in2')
    if up_t: tw(dome, 'location', up_t, 0.15, (0, 0, 0), 'back')
def react(B, t, word='RECEIVED', roll_to=None, rdur=0.6, lead=0.5):
    stamp(B, t); lamp_to(B.lamp, t + FR, 'amber'); B.st.say(t + 0.05, word); lamp_to(B.lamp, t + 0.42, 'cream')
    if B.kind == 'notify' and roll_to is not None: B.odo.roll(t + 0.02, rdur, roll_to, lead)
    elif B.kind == 'email': env_rise(B, t + 0.03); needle(B, t + 0.03, 3.0, 0.12, 'out2'); needle(B, t + 0.2, 0.6, 0.35, 'back')
    elif B.kind == 'feed': feed_shift(B, t + 0.02)
    elif B.kind == 'badges': coin_press(B, t); B.odo.roll(t + 0.45, 0.3, B.odo.v + 1)
def bay_root_at(k): return Vector((ARC[k][0], ARC[k][1], 0))
def fan_out(t_out, t_gate, kinds, tag, ts=None):
    """copies slide out of the ports in sync, stamp on one frame, then slide into the bay faces."""
    for k in kinds:
        u = UDIR[k]; g = GATE[k]; s0 = TV + u * 0.42
        c = newcard(f'copy_{tag}_{k}', (s0.x, s0.y, 0.30), ARCYAW[k]); show(c, t_out - FR)
        tw(c, 'location', t_out, t_gate - t_out, (g.x, g.y, 0.30), 'io')
        ts_ = ts or t_gate; yw = ARCYAW[k]; tw(c, 'location', ts_, 2 * FR, (g.x, g.y, 0.29), 'out2'); tw(c, 'location', ts_ + 2 * FR, 3 * FR, (g.x, g.y, 0.30), 'out')
        tw(c, 'location', ts_ + 0.22, 0.2, (g.x - 0.24 * math.sin(yw), g.y + 0.24 * math.cos(yw), 0.30), 'in2'); hide(c, ts_ + 0.44)

# lamps / plates at rest
for m_ in (POSTPB, CAPPB, BOARDPB): sock(m_, 'Emission Strength').default_value = 6.0
for B in QB.values(): sock(B.pb, 'Emission Strength').default_value = 6.0
BB = BAYS['badges']; BB.root.scale = (0.001,) * 3

# hook (0-6.7 s): post press, spinner, scoreboard
tw(dome, 'location', 0.40, 0.04, (0, 0, 0.002), 'out'); tw(dome, 'location', tPOST, 2 * FR, (0, 0, -0.018), 'in2')
st(SPN['comet'], 'default_value', 0.50, 1.0)
def spin_phase(t): return (t - 0.5) / 0.9 if t < tSPIN else (tSPIN - 0.5) / 0.9 + (t - tSPIN) / 0.7
fn(SPN['phase'], 'default_value', 0.50, tSTOPS, spin_phase)
POST_ST.say(0.50, 'SENDING...'); lamp_to(POSTLAMP, 0.50, 'amber')
BOARD.roll(tTWO, 0.71, 2000000, lead_dur=0.60)
st(BDB['xs'], 'default_value', 2.0, 99.0); bulb_flick(BDB['lvl'], 2.0, 1.0)
for tt in (tKEEPS, tKEEPS + 0.36): POST_ST.nudge(tt, 0.35, 0.24)

# why (6.66-14.44): monolith runs the jobs in order
BN, BE, BF = BAYS['notify'], BAYS['email'], BAYS['feed']
for B, tt in ((BN, tEVERY), (BE, tEVERY + 0.36), (BF, tITSELF)): bulbs_on(B.pb, tt)
cM = newcard('cardM', (0, 0.18, 1.02)); pop(cM, 8.40)
tw(cM, 'location', 8.70, 0.12, (0.16, 0.15, 1.27), 'in2'); tw(cM, 'location', 8.82, 0.20, (0.70, 0.05, 1.10), 'lin')
tw(cM, 'rotation_euler', 9.00, 0.06, (0.86, 0, 0), 'io'); tw(cM, 'location', 9.02, 0.33, (0.70, -0.625, 0.31), 'in2')
tw(cM, 'rotation_euler', 9.33, 0.06, (0, 0, 0), 'io'); tw(cM, 'location', 9.35, 0.06, (0.70, -0.625, 0.30), 'out')
for B, x, ta, ts, word in ((BN, 1.40, tNOTIFY, 10.50, 'DONE'), (BE, 2.35, 11.15, tEMAILS, 'SENT'), (BF, 3.30, 12.10, tFEEDS, 'UPDATED')):
    tw(cM, 'location', ta, 0.32, (x, -0.625, 0.30), 'io')
    stamp(B, ts); lamp_to(B.lamp, ts + FR, 'amber'); lamp_to(B.lamp, ts + 0.42, 'cream'); B.st.say(ts + 0.40, word)
    if B.kind == 'notify': B.odo.roll(ts + 0.02, 0.58, 2000000, 0.5)
    elif B.kind == 'email': env_rise(B, ts + 0.03); needle(B, ts + 0.03, 3.0, 0.12, 'out2'); needle(B, ts + 0.2, 0.6, 0.35, 'back')
    else: feed_shift(B, ts + 0.02)
tw(cM, 'location', 12.92, 0.18, (3.30, -0.40, 0.30), 'in2'); hide(cM, 13.12)
for B, tt in ((BN, 13.50), (BE, 13.70), (BF, 13.90)): lamp_to(B.lamp, tt, 'amber'); lamp_to(B.lamp, tt + 0.14, 'cream')

# spot the problem: every hall light to 6 %, a theatrical spot
for ld, e in HALL: tw(ld, 'energy', tSPOT, 3 * FR, e * 0.06, 'lin'); tw(ld, 'energy', tIF, 4 * FR, e, 'lin')
for s_, e in HALLEM: tw(s_, 'default_value', tSPOT, 3 * FR, e * 0.06, 'lin'); tw(s_, 'default_value', tIF, 4 * FR, e, 'lin')
tw(WBG.inputs['Strength'], 'default_value', tSPOT, 3 * FR, 0.05, 'lin'); tw(WBG.inputs['Strength'], 'default_value', tIF, 4 * FR, 0.35, 'lin')
tw(SPOTP.data, 'energy', 14.50, 2 * FR, 2500.0, 'lin'); tw(SPOTP.data, 'energy', 15.70, 3 * FR, 0.0, 'lin')

# problem: EMAIL is slow, the post waits, features mean rewriting
cM2 = newcard('cardM2', (2.35, -0.625, 0.30)); show(cM2, 15.0)
env_down(BE, 15.80, 0.12); tw(BE.env, 'location', 16.0, 0.9, (0.20, FACE - 0.016, 0.535 + 0.0725), 'out')
needle(BE, 15.88, 9.3, 0.3, 'back')
fn(BE.needle, 'rotation_euler', 16.20, 26.30, lambda t: (0, gauge_angle(9.3) + rad(3) * math.sin(2 * PI * 7 * t), 0))
BE.st.say(tSLOW, 'SLOW'); lamp_to(BE.lamp, tSLOW, 'red')
fn(cM2, 'location', 15.90, 17.74, lambda t: (2.35 + 0.002 * math.sin(2 * PI * 11 * t), -0.625, 0.30 + 0.0015 * abs(math.sin(2 * PI * 9 * t))))
POST_ST.say(tWAITS, 'WAITING...')
for h in HOOKS: tw(h, 'location', 17.80, 0.35, (h.location.x, 0, 1.43), 'out')
st(CRATE, 'rotation_euler', 18.50, (0, -0.25, 0))
tw(CRATE, 'location', tNEW, 0.54, (4.30, 0, 2.30), 'out'); tw(CRATE, 'rotation_euler', tNEW, 0.54, (0, rad(6), 0), 'out')
fn(CRATE, 'rotation_euler', tNEW + 0.54, 22.0, lambda t: (0, rad(6) * math.exp(-(t - tNEW - 0.54) / 0.8) * math.cos(2 * PI * (t - tNEW - 0.54) / 1.5), 0))
tw(CAP, 'location', tREWRITE, 0.6, (2.35, 0, 1.28 + 0.9), 'io'); tw(CAP, 'rotation_euler', tREWRITE, 0.6, (0, rad(2), 0), 'io')
for h in HOOKS: tw(h, 'location', tREWRITE, 0.6, (h.location.x, 0, 1.43 + 0.9 + (0.045 if h.location.x > 2.35 else -0.045)), 'io')
POST_ST.say(tREWRITE, 'REWRITING'); lamp_to(POSTLAMP, tREWRITE, 'red')
POST_RW.roll(tSERVICE, 0.30, 1)
POST_RW.roll(tAGAIN, 0.22, 2, lead_ez='back3')
tw(post, 'location', tAGAIN, 2 * FR, (0, 0, -0.006), 'in2'); tw(post, 'location', tAGAIN + 2 * FR, 5 * FR, (0, 0, 0), 'back')
for h in HOOKS:
    fn(h, 'rotation_euler', tAGAIN, tAGAIN + 0.8, lambda t: (0, rad(2.5) * math.exp(-(t - tAGAIN) / 0.25) * math.sin(2 * PI * 4 * (t - tAGAIN)), 0))

# queue (22.04-26.36)
QC = newcard('cardQ', (-12.2, -0.625, 0.30))
tw(QPUSH, 'location', tQUEUE - 0.08, 0.08, (0.12, -0.38, 0.42), 'in2'); tw(QPUSH, 'location', tQUEUE + 0.1, 0.25, (0.24, -0.38, 0.42), 'out')
tw(QMINI[0], 'location', tQUEUE, 0.18, (-0.25, -0.36, 0.51), 'in2'); hide(QMINI[0], tQUEUE + 0.2)
for k, mc in enumerate(QMINI[1:], 1): tw(mc, 'location', tQUEUE + 0.04, 0.24, (0, -0.36, 0.51 + (k - 1) * 0.12), 'back2')
show(QC, tQUEUE - FR); tw(QC, 'location', tQUEUE, 0.4, (-12.80, -0.625, 0.30), 'out')
tw(QC, 'location', 23.60, 1.40, (-13.40, -0.625, 0.30), 'io')
QN = QB['notify']; stamp(QN, tONEW); lamp_to(QN.lamp, tONEW + FR, 'amber'); QN.odo.roll(tONEW + 0.02, 0.4, 1, 0.4)
QN.st.say(tONEW + 0.16, 'GOT IT'); lamp_to(QN.lamp, tONEW + 0.42, 'cream')
tw(QC, 'location', tONEW + 0.16, 0.2, (-13.40, -0.40, 0.30), 'in2'); hide(QC, tONEW + 0.38)

# the fix (26.36-27.30): the jobs leave, the topic rises
tw(CAP, 'location', 26.40, 0.3, (2.35, 0, 1.28 + 0.9 + 7.0), 'in2')
for h in HOOKS: tw(h, 'location', 26.40, 0.3, (h.location.x, 0, 1.43 + 0.9 + 7.0), 'in2')
tw(CRATE, 'location', 26.40, 0.3, (4.30, 0, 2.30 + 7.0), 'in2')
for w_ in WIRES: tw(w_, 'location', 26.40, 0.3, (0, 0, 7.0), 'in2')
POST_ST.say(26.40, 'WAITING...'); lamp_to(POSTLAMP, 26.40, 'amber')
for i, k in enumerate(('notify', 'email', 'feed')):
    B = BAYS[k]; t0 = tFIX + 0.08 * i; lamp_to(B.lamp, 26.40, 'off')
    tw(B.root, 'location', t0, 0.6, (MONO_X[k] + 4.2, 0, 0), 'io')
    for wh in B.wheels: tw(wh, 'rotation_euler', t0, 0.6, (0, 4.2 / 0.035, 0), 'io')
    if k == 'email': tw(cM2, 'location', t0, 0.6, (2.35 + 4.2, -0.625, 0.30), 'io'); hide(cM2, 27.2)
tw(mledge, 'location', tFIX, 0.4, (0, 0, -1.6), 'in2'); tw(mchute, 'location', tFIX, 0.4, (0, 0, -1.6), 'in2')
for B in (BN, BE, BF):
    B.st.reset(27.10, 0)
    for wh in B.wheels: st(wh, 'rotation_euler', 27.10, (0, 0, 0))
BN.odo.reset(27.10, 0); st(BE.env, 'location', 27.10, (0.20, FACE - 0.016, 0.535)); st(BE.needle, 'rotation_euler', 27.10, (0, gauge_angle(0), 0))
for d_, sx in zip(DOORS, (-1, 1)):
    tw(d_, 'location', 26.66, 0.08, (0, 2.2, -0.25), 'in2'); tw(d_, 'location', 26.74, 0.15, (sx * 0.75, 2.2, -0.25), 'out')
tw(HUB, 'location', 26.80, 0.45, (0, 2.2, 0), 'back2')
tw(PCH, 'scale', 27.00, 0.25, (1, 1, 1), 'out'); tw(PSTAND, 'scale', 27.00, 0.2, (1, 1, 1), 'out')
tw(SIGN, 'location', 27.05, 0.25, (0, 2.2, 2.95), 'in2')
fn(SIGN, 'rotation_euler', tPS, tPS + 0.7, lambda t: (rad(12) + rad(2) * math.exp(-(t - tPS) / 0.22) * math.sin(2 * PI * (t - tPS) / 0.5), 0, 0))
st(SGN['xs'], 'default_value', tPS - FR, -1.2); tw(SGN['xs'], 'default_value', tPS, 0.30, 1.2, 'lin')
st(SGN['bp'], 'default_value', tPS - FR, -1.4); tw(SGN['bp'], 'default_value', tPS, 0.40, 1.6, 'lin')
for k in ('notify', 'email', 'feed'):
    st(BAYS[k].root, 'location', tPS, tuple(bay_root_at(k))); st(BAYS[k].root, 'rotation_euler', tPS, (0, 0, ARCYAW[k]))
show(NCABLE, tPS)

# publish (28.68-33.14)
cP = newcard('cardP', (0, 0.18, 1.02)); pop(cP, tPUB)
to_topic(cP, 29.25, 0.80)
POST_ST.say(tDONE, 'PUBLISHED'); lamp_to(POSTLAMP, tDONE, 'cream')
st(SPN['comet'], 'default_value', tSTOPS, 0.0); st(SPN['all'], 'default_value', tSTOPS, 1.0)
tw(dome, 'location', 32.10, 0.15, (0, 0, 0), 'back')
tw(SPN['all'], 'default_value', 32.40, 0.4, 0.0, 'io')
POST_ST.say(32.80, 'READY'); lamp_to(POSTLAMP, 32.80, 'off')

# subscribe (33.80-34.20) and fan-out (36.00-38.24)
def subscribe(k, t):
    B = BAYS[k]; tw(LANE[k], 'scale', t, 0.32, (1, 1, 1), 'back2')
    tw(COLLAR[k], 'scale', t + 0.30, 0.06, (1.15, 1.15, 1.15), 'out2'); tw(COLLAR[k], 'scale', t + 0.36, 0.12, (1, 1, 1), 'out')
    lamp_to(PORTLAMP[k], t + 0.33, 'cream'); lamp_to(B.lamp, t + 0.34, 'cream'); B.st.say(t + 0.34, 'SUBSCRIBED')
for k, tt in (('notify', tSUBSCRIBES), ('email', tSUBSCRIBES + 0.2), ('feed', tSUBSCRIBES + 0.4)): subscribe(k, tt)
ring_turn(34.70, 15)
tw(HUB, 'location', tEACH + 0.46, 2 * FR, (0, 2.2, -0.01), 'in2'); tw(HUB, 'location', tEACH + 0.46 + 2 * FR, 5 * FR, (0, 2.2, 0), 'out'); ring_turn(tEACH + 0.46, 15)
fan_out(tCOPY, tSAME - 0.12, ('notify', 'email', 'feed'), 'a', tSAME)
for k in ('notify', 'email', 'feed'): react(BAYS[k], tSAME, roll_to=2000000 if k == 'notify' else None, rdur=0.66, lead=0.55)

# radio (38.24-43.14)
st(SUN.data, 'energy', 38.0, 2.2); st(SUN.data, 'energy', 43.1, 0.0)
st(RSN['xs'], 'default_value', 38.54, 99.0); bulb_flick(RSN['lvl'], 38.54, 1.0)
for tt in (38.70, tONCE - 0.42, 41.0, 42.2): bulb_flick(sock(BEAC, 'Emission Strength'), tt, 14.0); st(sock(BEAC, 'Emission Strength'), 'default_value', tt + 0.25, 0.6)
st(RFADE, 'default_value', tONCE, 1.0); tw(RFADE, 'default_value', 41.9, 0.7, 0.0, 'lin')
tw(BIG, 'value', tONCE, 2.56, 1.0, 'lin')
for r, G, dm, tuned in RADIOS:
    if not tuned: continue
    bulb_flick(sock(dm, 'Emission Strength'), tTUNED, 2.5)
    fn(G, 'scale', tTUNED, 43.1, lambda t: (1 + 0.01 * (1 - math.cos(2 * PI * 5 * (t - tTUNED))),) * 3)

# new feature (43.14-47.04): BADGES rolls in and subscribes
show(BB.root, 43.0)
tw(BB.root, 'location', tNF, 0.76, tuple(bay_root_at('badges')), 'back2'); tw(BB.root, 'rotation_euler', tNF, 0.76, (0, 0, ARCYAW['badges']), 'out')
for wh in BB.wheels: tw(wh, 'rotation_euler', tNF, 0.76, (0, 3.35 / 0.035, 0), 'out')
bulbs_on(BB.pb, 43.96)
subscribe('badges', tSUBIT)
react(BB, 44.70); react(BB, 45.40)
BN.odo.reset(48.0, 0); st(BE.env, 'location', 48.0, (0.20, FACE - 0.016, 0.535))

# payoff (49.30-51.76)
press(tONEPUB, 49.62)
st(SPN['all'], 'default_value', tONEPUB, 1.0); st(SPN['all'], 'default_value', tONEPUB + 0.26, 0.0)
POST_ST.say(49.40, 'PUBLISHED'); lamp_to(POSTLAMP, 49.40, 'cream')
cY = newcard('cardPay', (0, 0.18, 1.02)); pop(cY, tPUBLISH, 0.08, 1.45, 'out2')
to_topic(cY, tPUBLISH + 0.08, 0.18)
fan_out(50.12, 50.30, ('notify', 'email', 'feed', 'badges'), 'b')
for k in ('notify', 'email', 'feed', 'badges'): react(BAYS[k], 50.30, roll_to=2000000 if k == 'notify' else None, rdur=0.70, lead=0.64)
POST_ST.say(50.20, 'READY'); lamp_to(POSTLAMP, 50.20, 'off')
tw(FLD['wave'], 'default_value', 50.40, 0.90, 24.0, 'out')
for i, L_ in enumerate(FIELDL): tw(L_.data, 'energy', 50.40 + 0.18 * i, 0.45, 350.0, 'out')
st(BDB['bp'], 'default_value', 50.40, -5.0); tw(BDB['bp'], 'default_value', 50.40, 0.9, 5.0, 'lin')

# products (51.76-55.40)
tw(PLQ, 'rotation_euler', 51.90, 0.30, (0, 0, 0), 'out'); tw(PLQ, 'rotation_euler', 53.30, 0.35, (0, 0, PI), 'io')

# CTA (55.40-END): calm loops
tw(sc.view_settings, 'exposure', 55.40, 0.6, -0.35, 'io')
tw(FLD['lvl'], 'default_value', 55.40, 0.6, 0.7, 'io')
for L_ in FIELDL: tw(L_.data, 'energy', 55.40, 0.6, 245.0, 'io')
for i, t0 in enumerate(CTA_LOOPS):
    press(t0, t0 + 0.25)
    st(SPN['all'], 'default_value', t0, 0.6); st(SPN['all'], 'default_value', t0 + 0.25, 0.0)
    c = newcard(f'cardC{i}', (0, 0.18, 1.02)); pop(c, t0 + 0.05, 0.2)
    tin = to_topic(c, t0 + 0.30, 0.35)
    st(SGN['bp'], 'default_value', t0 - 0.3, -1.4); tw(SGN['bp'], 'default_value', t0 - 0.3, 0.6, 1.6, 'lin')
    for k in ('email',): env_down(BAYS[k], tin + 0.1)
    fan_out(tin + 0.02, tin + 0.5, ('notify', 'email', 'feed', 'badges'), f'c{i}')
    for k in ('notify', 'email', 'feed', 'badges'): react(BAYS[k], tin + 0.5)

# dust drifts
for d_ in DUST:
    c0 = Vector(d_.location)
    fn(d_, 'location', 0.0, END, lambda t, c0=c0: (c0.x + 0.05 * math.sin(0.3 * t), c0.y, c0.z + 0.03 * t))

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
S01P, S01G = V3(0.30, -1.75, 1.72), V3(0, -0.12, 1.33)
S09P, S09G = V3(0.45, -1.35, 1.65), V3(0, -0.3, 1.0)
shot(0.0, S01P, S01G, toward(S01P, S01G, 0.89), None, 85, 2.0)
shot(1.30, (0.4, 5.4, 0.6), (0, 29.6, 4.6), (0.4, 6.4, 0.6), None, 50, 2.8,
     fnP=lambda t, u, e, s: (s['P0'].lerp(s['P1'], e), s['G0'] - Vector((0, 0, 1.7 * EZ['io'](clamp((t - 2.48) / 0.6))))),
     foc=lambda t, P, G: V3(0, 29.4, 4.75).lerp(V3(0.4, 14.4, 0.25), EZ['io'](clamp((t - 2.48) / 0.42))))
S03P, S03G = V3(0.65, -1.75, 1.75), V3(0, -0.3, 1.05)
def _orb03(t, u, e, s):
    a = rad(14) * e; d = s['P0'] - S03G; R = Matrix.Rotation(a, 3, 'Z'); return S03G + R @ d, S03G
shot(tAND, S03P, S03G, None, None, 50, 2.2, fnP=_orb03)
def _s04(t, u, e, s):
    k = EZ['out'](clamp((t - tWHY) / (8.6 - tWHY))); P = s['P0'].lerp(s['P1'], k) + Vector((0.18 * max(0.0, t - 8.6), 0, 0)); G = s['G0'].lerp(s['G1'], k) + Vector((0.12 * max(0.0, t - 8.6), 0, 0))
    return P, G
shot(tWHY, (0.4, -1.2, 1.7), (0, -0.1, 1.2), (-2.2, -4.6, 2.5), (1.75, 0, 0.75), 35, 3.2, fnP=_s04)
CX5 = [(tNOTIFY, 0.95), (10.45, 1.40), (11.15, 1.40), (11.50, 2.35), (12.10, 2.35), (12.48, 3.30), (12.94, 3.40)]
shot(tNOTIFY, (0.8, -2.68, 0.9), (0.95, -0.375, 0.73), None, None, 50, 2.2,
     fnP=lambda t, u, e, s: (Vector((pw(t, [(a, (b, 0, 0)) for a, b in CX5]).x - 0.15, -2.68, 0.9)), Vector((pw(t, [(a, (b, 0, 0)) for a, b in CX5]).x, -0.375, 0.73))))
shot(tONE, (-1.2, -3.4, 1.6), (1.75, 0, 0.75), (-2.2, -4.6, 2.5), None, 35, 3.5)
S07P, S07G = V3(0.35, -2.1, 0.55), V3(0, -0.2, 1.05)
shot(tSPOT, S07P, S07G, toward(S07P, S07G, 0.97), None, 35, 2.8, roll=2.0)
S08P, S08G = V3(2.55, -1.85, 1.05), V3(2.25, -0.375, 0.84)
shot(tIF, S08P, S08G, toward(S08P, S08G, 0.94), None, 65, 2.0)
shot(16.90, S09P, S09G, toward(S09P, S09G, 0.97), None, 50, 2.0)
shot(tAND2, (-1.4, -4.9, 3.0), (2.2, 0.1, 1.2), (-1.4, -4.9, 3.4), None, 28, 3.5)
S11P, S11G = V3(-0.35, -1.6, 0.75), V3(0, -0.4, 0.58)
shot(20.40, S11P, S11G, toward(S11P, S11G, 0.96), None, 65, 2.2)
shot(tQ, (-12.9, -2.9, 0.75), (-12.1, -0.6, 1.45), (-12.75, -2.6, 0.8), (-12.1, -0.6, 1.75), 32, 2.8, whip='L')
S13P, S13G = V3(-10.2, -2.6, 2.2), V3(-13.9, -0.3, 0.8)
shot(23.50, S13P, S13G, toward(S13P, S13G, 0.95), (-14.1, -0.3, 0.8), 32, 4.0)
S14P, S14G = V3(-0.9, -3.8, 1.6), V3(0.9, 1.0, 0.8)
shot(tFIX, S14P, S14G, toward(S14P, S14G, 0.93), None, 35, 3.2, whip='R')
shot(tPS, (0, -4.2, 6.6), (0, 2.0, 0.6), (0, -4.2, 6.3), None, 30, 4.0)
def _s16(t, u, e, s):
    k = EZ['io'](clamp((t - 29.25) / 1.15)); return V3(0.75, -1.35, 1.85).lerp(V3(0.9, 0.4, 1.9), k), V3(0, 0.2, 1.2).lerp(V3(0, 2.0, 0.9), k)
shot(28.30, (0.75, -1.35, 1.85), (0, 0.2, 1.2), None, None, 50, 2.4, fnP=_s16)
shot(30.95, S09P, S09G, toward(S09P, S09G, 0.97), None, 50, 2.0)
shot(31.60, S01P, S01G, toward(S01P, S01G, 0.92), None, 85, 2.0)
G19 = V3(0, 2.4, 0.6)
shot(tSUBS, orbit(G19, -14, 6.6, 5.0), G19, None, None, 30, 3.5, fnP=lambda t, u, e, s: (orbit(G19, -14 + 10 * EZ['io'](u), 6.6, 5.0), G19))
P20 = orbit(G19, -4, 6.6, 5.0)
shot(35.50, P20, G19, P20 + (G19 - P20).normalized() * 0.8, None, 30, 4.0)
shot(tRADIO, (200, -2, 1.6), (210, 70, 33), (200, -2, 2.1), (210, 70, 29), 50, 2.8, whip='UR')
S22P, S22G = V3(200.0, -2.45, 1.25), V3(200.0, 0, 1.18)
shot(40.50, S22P, S22G, toward(S22P, S22G, 0.95), None, 50, 2.8)
G23 = [(tNF, (4.6, 3.5, 0.8)), (43.90, (1.75, 3.0, 0.8)), (44.95, (1.6, 2.9, 0.8))]
shot(tNF, (0.9, -0.4, 1.8), (4.6, 3.5, 0.8), (0.8, -0.2, 1.75), None, 35, 2.8, whip='D',
     fnP=lambda t, u, e, s: (s['P0'].lerp(s['P1'], e), pw(t, G23, 'out')))
S24P, S24G = V3(-0.8, -2.45, 1.15), V3(0.1, -0.4, 0.85)
shot(44.95, S24P, S24G, toward(S24P, S24G, 0.98), None, 50, 2.4)
shot(tSO, (0.4, 6.4, 0.6), (0, 29.6, 4.6), (0.4, 5.4, 0.6), None, 50, 2.8, whip='R', foc=lambda t, P, G: V3(0, 29.4, 4.75))
shot(49.30, S01P, S01G, toward(S01P, S01G, 0.92), None, 85, 2.0)
shot(50.30, (-1.0, -2.2, 2.4), (0, 12, 0.6), (-1.0, -2.2, 3.6), None, 24, 4.0, foc=lambda t, P, G: V3(0, 2.6, 0.6))
S28P, S28G = V3(-1.0, -1.5, 1.45), V3(-1.1, 1.1, 1.15)
shot(tTHATS, S28P, S28G, toward(S28P, S28G, 0.84), None, 65, 2.0, whip='R')
shot(55.40, (-3.2, -4.4, 5.6), (0, 2.4, 0.7), (-1.6, -5.0, 6.0), None, 32, 3.2, ez='io')
JOLTS = [(tPOST, 0.004)]
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
CUTFIX = [tPS]
write_tracks()

# ---------- render ----------
sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = SAMPLES
ee.use_shadows = True; ee.shadow_pool_size = '1024'; ee.use_raytracing = True; ee.ray_tracing_method = 'SCREEN'; ee.use_fast_gi = True
# stay inside EEVEE's 4096-tile shadow buffer: when it overflows, shadows drop out at random per frame and the haze flickers.
ee.shadow_resolution_scale = 0.75
for o in sc.objects:  # the big window lights were the overflow: no shadows, no haze (this is the look the approved frames had)
    if o.type == 'LIGHT' and o.name.startswith('win'): o.data.use_shadow = False; o.data.volume_factor = 0.0
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
