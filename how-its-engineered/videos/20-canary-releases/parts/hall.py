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
m = M['terrazzo']; tc = nn(m, 'ShaderNodeTexCoord'); vo = nn(m, 'ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 28
ln(m, tc.outputs['Object'], vo.inputs['Vector']); sp = nn(m, 'ShaderNodeSeparateColor'); ln(m, vo.outputs['Color'], sp.inputs[0])
cr = nn(m, 'ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; el = cr.color_ramp.elements
el[0].position = 0.0; el[0].color = hx('#C9BFAE'); el[1].position = 0.14; el[1].color = hx('#5B554D')
e2 = el.new(0.07); e2.color = hx('#2F2B27')
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
SKYB = grad_wall('sky', '#FFD39C', '#8FA9CC', 2.2, 0.0, 26.0)
MB().box((0.0, 0.0, 0.0), (140.0, 0.1, 60.0), SKYB).ob('sky', None, (0, 70.0, 24.0), smooth=False, shadow=False)
SILM, _ = emat('silh', '#B79A80', 1.4)
sl = MB()
for i in range(26):
    x = -60 + 4.8 * i + random.uniform(-1, 1); h = random.uniform(4, 16); w = random.uniform(2.5, 5.0)
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
MB().cyl((0, 0, 0), 0.40, 0.006, M['ink'], seg=96).tor((0, 0, 0.003), 0.40, 0.006, M['brass'], seg=96, rs=8).ob('dial_ring', DTOP, (0, 0, -0.001))
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
