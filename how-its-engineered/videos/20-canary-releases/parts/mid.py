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

class Phone:
    def __init__(s, i, r, c, x, y):
        s.i, s.r, s.c, s.x, s.y = i, r, c, x, y
        s.root = empty(f'ph{i}', None, (x, y, 0))
        b = bpy.data.objects.new(f'body{i}', BODY_ME); col.objects.link(b); b.parent = s.root
        bv = b.modifiers.new('bv', 'BEVEL'); bv.width = 0.018; bv.segments = 3; bv.limit_method = 'ANGLE'; bv.angle_limit = rad(30); bv.harden_normals = True
        fo = bpy.data.objects.new(f'front{i}', FRONT_ME); col.objects.link(fo); fo.parent = s.root
        s.m, s.ver, s.crash, s.lum = screen_mat(i)
        fo.material_slots[0].link = 'OBJECT'; fo.material_slots[0].material = s.m
    def pos(s, z=0.0): return (s.x, s.y, z)
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

# ---------- floor, backdrop ----------
MB().box((30.0, 10.0, -0.1), (200.0, 160.0, 0.2), M['floor']).ob('floor', None, smooth=False)
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
MB().box((0.0, 0.0, 0.0), (90.0, 0.1, 30.0), grad_wall('cyc', '#1C2433', '#040507', 1.0, -15.0, 3.0)).ob('cyc', None, (0, 46.0, 15.0), smooth=False, shadow=False)

# ---------- ROLLOUT dial pedestal ----------
DX, DY = -6.0, -4.0
TA = math.atan2(0.35, 0.75)                     # top slope (front 0.85 m, back 1.20 m)
YZ = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))  # prism polygon in (y, z), extruded along x
MB().prism([(-0.375, 0.0), (0.375, 0.0), (0.375, 1.20), (-0.375, 0.85)], 1.0, M['ped'], rot=YZ).ob('pedestal', None, (DX, DY, 0), bev=0.008)
DTOP = empty('dtop', None, (DX, DY, 1.025 + 0.0015), (TA, 0, 0))
MB().ann((0, 0, 0), 0.215, 0.37, 0.004, M['ring'], seg=96).ob('dial_ring', DTOP, (0, 0, -0.001))
STEPS = [0, 1, 5, 25, 100]; ANG = {0: -135, 1: -67.5, 5: 0, 25: 67.5, 100: 135}
tk = MB()
for k in range(31):
    a = rad(-135 + 9 * k); major = (-135 + 9 * k) in [round(ANG[s]) for s in STEPS] or k in (0, 30)
    if (-135 + 9 * k) % 1: continue
    r0, r1 = (0.235, 0.285) if major else (0.24, 0.262)
    tk.box(((r0 + r1) / 2 * math.sin(a), (r0 + r1) / 2 * math.cos(a), 0.004), (0.005 if not major else 0.008, r1 - r0, 0.002), M['label'] if major else M['tick'], rot=(0, 0, -a))
for s_ in STEPS:
    a = rad(ANG[s_]); r0, r1 = 0.235, 0.29
    tk.box(((r0 + r1) / 2 * math.sin(a), (r0 + r1) / 2 * math.cos(a), 0.004), (0.008, r1 - r0, 0.002), M['label'], rot=(0, 0, -a))
tk.ob('dial_ticks', DTOP, shadow=False)
DLAMP = {}
for s_ in STEPS:
    a = rad(ANG[s_]); lm = mat(f'dlamp{s_}', '#2A2C30', 0.3, emit=0.0, eh='#FFC21A')
    MB().cyl((0, 0, 0), 0.014, 0.004, lm, seg=20).ob(f'dlamp{s_}', DTOP, (0.315 * math.sin(a), 0.315 * math.cos(a), 0.004))
    txt(f'dlab{s_}', str(s_), 'din', 0.042, M['label'], DTOP, (0.385 * math.sin(a), 0.385 * math.cos(a), 0.003), (0, 0, 0), 0.0006)
    DLAMP[s_] = sock(lm, 'Emission Strength')
txt('dial_title', 'ROLLOUT  %', 'inter_sb', 0.022, M['label_dim'], DTOP, (0, -0.33, 0.003), (0, 0, 0), 0.0004, space=1.25)
KNOB = empty('knob', DTOP, (0, 0, 0), (0, 0, rad(135)))
kb = MB().cyl((0, 0, 0.055), 0.19, 0.11, M['alu'], seg=96).cyl((0, 0, 0.112), 0.178, 0.006, M['alu_satin'], seg=96)
kb.tor((0, 0, 0.03), 0.191, 0.004, M['ti_dark'], seg=96, rs=8)
kb.box((0, 0.115, 0.1165), (0.016, 0.085, 0.004), M['yellow_e'])
kb.ob('knob_body', KNOB, bev=0.006)
DIALV = [0]
def dial(t, v, dur=0.38, ez='back2'):
    tw(KNOB, 'rotation_euler', t, dur, (0, 0, -rad(ANG[v])), ez)
    for s_ in STEPS: tw(DLAMP[s_], 'default_value', t + dur * 0.6, 0.08, 5.0 if (s_ <= v and s_ > 0) or (s_ == 0 and v == 0) else 0.0, 'lin')
def dial_set(t, v):
    st(KNOB, 'rotation_euler', t, (0, 0, -rad(ANG[v])))
    for s_ in STEPS: st(DLAMP[s_], 'default_value', t, 5.0 if (s_ <= v and s_ > 0) or (s_ == 0 and v == 0) else 0.0)
KNOB.rotation_euler = (0, 0, -rad(ANG[0])); DLAMP[0].default_value = 5.0
# plaques on the front face
PF = DY - 0.375
face_txt('ped_title', 'CANARY', 'inter_sb', 0.026, M['label_dim'], None, DX, PF, 0.76, space=1.6)
for nm, z in (('ARGO ROLLOUTS', 0.60), ('AWS CODEDEPLOY', 0.42)):
    MB().box((0, 0, 0), (0.80, 0.012, 0.13), M['alu_satin']).ob('plq_' + nm, None, (DX, PF - 0.006, z), bev=0.004)
    face_txt('plqt_' + nm, nm, 'din', 0.046, M['engrave'], None, DX, PF - 0.012, z, space=1.12, fit=0.70)

# ---------- HEALTH pillar ----------
MX, MY = -3.55, -4.7
MB().box((0, 0, 0.8), (0.62, 0.30, 1.60), M['ped']).ob('pillar', None, (MX, MY, 0), bev=0.01)
MFY = MY - 0.15
face_txt('health', 'HEALTH', 'inter_sb', 0.026, M['label_dim'], None, MX, MFY, 1.52, space=1.6)
BARS = []
for k, (nm, bx) in enumerate((('CRASHES', -0.17), ('ERRORS', 0.0), ('SLOW', 0.17))):
    MB().box((0, 0, 0), (0.105, 0.01, 1.02), M['ring']).ob('slot_' + nm, None, (MX + bx, MFY - 0.004, 0.96))
    bm_ = mat('bar_' + nm, '#EAF1FF', 0.4, emit=2.2, eh='#EAF1FF')
    o = MB().box((0, 0, 0.5), (0.07, 0.012, 1.0), bm_).ob('bar_' + nm, None, (MX + bx, MFY - 0.01, 0.47), shadow=False)
    face_txt('bl_' + nm, nm, 'inter_sb', 0.017, M['label'], None, MX + bx, MFY, 0.38, space=1.1, fit=0.155)
    BARS.append((o, bm_))
LIMIT = mat('limit', '#FF453A', 0.4, emit=2.5, eh='#FF453A')
MB().box((0, 0, 0), (0.50, 0.006, 0.006), LIMIT).ob('limit', None, (MX, MFY - 0.018, 0.47 + 0.62), shadow=False)
face_txt('limit_t', 'LIMIT', 'inter_sb', 0.012, M['red_e'], None, MX + 0.28, MFY - 0.012, 0.47 + 0.62, ax='LEFT')
def meter_level(k, t):
    base = (0.12, 0.19, 0.25)[k]
    w = 0.022 * math.sin(t * 2.3 + k * 1.7) + 0.012 * math.sin(t * 5.9 + k * 0.6)
    if k == 0: w += 0.74 * sm((t - (tSPIKE - 0.04)) / 0.22) * (1 - sm((t - (tROLLS + 0.4)) / 0.6))
    return clamp(base + w, 0.02, 0.97)
for k, (o, bm_) in enumerate(BARS):
    fn(o, 'scale', 0.0, END, lambda t, k=k: (1.0, 1.0, meter_level(k, t)))
    es = sock(bm_, 'Emission Strength')
    for tp in ((tCRW, tERR, tSLOW)[k],):
        tw(es, 'default_value', tp - 0.05, 0.12, 5.5, 'out'); tw(es, 'default_value', tp + 0.35, 0.5, 2.2, 'io')
bc = sock(BARS[0][1], 'Emission Color'); bb_ = sock(BARS[0][1], 'Base Color')
for sk_ in (bc, bb_): st(sk_, 'default_value', tSPIKE + 0.06, hx('#FF453A')); st(sk_, 'default_value', tROLLS + 0.85, hx('#EAF1FF'))
le = sock(LIMIT, 'Emission Strength')
for k in range(4): st(le, 'default_value', tSPIKE + 0.1 + 0.16 * k, 7.0 if k % 2 == 0 else 2.5)

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
WBG = WORLD.node_tree.nodes['Background']; WBG.inputs['Color'].default_value = hx('#0A0C10'); WBG.inputs['Strength'].default_value = 1.0
KEYE = float(opt('--key', 2600)); RIME = float(opt('--rim', 5000)); FILLE = float(opt('--fill', 500))
light('KEY', 'AREA', (0.0, 8.0, 13.0), (0.0, 8.0, 0.0), KEYE, '#F3F1EC', size=26.0, size_y=24.0, cutoff=45)
light('RIM', 'AREA', (0.0, 30.0, 5.5), (0.0, 6.0, 0.8), RIME, '#FFD7A8', size=34.0, size_y=3.0, cutoff=48)
light('FILL', 'AREA', (0.0, -16.0, 5.0), (0.0, 4.0, 0.8), FILLE, '#BFD3F2', size=24.0, size_y=4.0, shadow=False, cutoff=45)
light('DKEY', 'AREA', (-4.6, -7.4, 2.8), (-4.8, -4.4, 1.0), 140, '#FFF1E0', size=2.5, size_y=2.5, shadow=False, cutoff=12)
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
dial(tROLLS + 0.02, 0, 0.32, 'back')
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
dial(tTWO + 0.25, 0, 0.32, 'back'); CAN.restore(tTWO + 0.5, 0.5)
# L9: a few, then everyone
dial(tFEW0 + 0.2, 5)
for k, p in enumerate(FIVE): p.update(tFEW0 + 0.35 + 0.07 * k, 0.55)
dial(tALL3 - 0.08, 100)
for p in PH:
    if p not in FIVE: p.update(tALL3 + 0.02 + 0.022 * dist(p, CAN) + random.uniform(0, 0.05), 0.4)
JOLTS = []
