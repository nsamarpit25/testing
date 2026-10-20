
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
# ---------- surface detail: small procedural building blocks (object space, metres) ----------
def OC(m, s_=(1, 1, 1), loc=(0, 0, 0)):
    tc = nn(m, 'ShaderNodeTexCoord'); mp = nn(m, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = s_; mp.inputs['Location'].default_value = loc
    ln(m, tc.outputs['Object'], mp.inputs['Vector']); return mp.outputs[0]
def NZ(m, v, scale, detail=6.0, rough=0.55, dist=0.0):
    n = nn(m, 'ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = dist; ln(m, v, n.inputs['Vector']); return n.outputs['Fac']
def VO(m, v, scale, feature='F1', out='Distance', rnd=1.0):
    n = nn(m, 'ShaderNodeTexVoronoi', feature=feature); n.inputs['Scale'].default_value = scale; n.inputs['Randomness'].default_value = rnd
    ln(m, v, n.inputs['Vector']); return n.outputs[out]
def WV(m, v, scale, dist=4.0, axis='Z', detail=3.0):
    n = nn(m, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction=axis); n.inputs['Scale'].default_value = scale
    n.inputs['Distortion'].default_value = dist; n.inputs['Detail'].default_value = detail; ln(m, v, n.inputs['Vector']); return n.outputs['Fac']
def RAMP(m, fac, stops):
    cr = nn(m, 'ShaderNodeValToRGB'); el = cr.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], hx(stops[0][1]); el[1].position, el[1].color = stops[-1][0], hx(stops[-1][1])
    for p, h in stops[1:-1]: el.new(p).color = hx(h)
    ln(m, fac, cr.inputs['Fac']); return cr.outputs['Color']
def MR(m, x, a, b, lo, hi):
    n = nn(m, 'ShaderNodeMapRange', clamp=True)
    for k, d in (('From Min', a), ('From Max', b), ('To Min', lo), ('To Max', hi)): n.inputs[k].default_value = d
    ln(m, x, n.inputs['Value']); return n.outputs['Result']
def MIXB(m, fac, a, b, blend='MIX'):
    mx = nn(m, 'ShaderNodeMix', data_type='RGBA', blend_type=blend)
    for i, x in ((0, fac), (6, a), (7, b)):
        if isinstance(x, (int, float, tuple)): mx.inputs[i].default_value = x
        else: ln(m, x, mx.inputs[i])
    return mx.outputs[2]
def BMP(m, h, strength, dist, normal=None):
    bp = nn(m, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = strength; bp.inputs['Distance'].default_value = dist
    ln(m, h, bp.inputs['Height'])
    if normal is not None: ln(m, normal, bp.inputs['Normal'])
    return bp.outputs['Normal']
def AOF(m, dist=0.25):
    a = nn(m, 'ShaderNodeAmbientOcclusion', samples=8); a.inputs['Distance'].default_value = dist; return a.outputs['AO']
def SET(m, name, x):
    s_ = sock(m, name)
    if isinstance(x, (int, float, tuple)): s_.default_value = x
    else: ln(m, x, s_)
def grime(m, col, dist=0.25, k=0.55):  # darken crevices and corners
    return MIXB(m, k, col, MIXB(m, 1.0, col, AOF(m, dist), 'MULTIPLY'))

def floor_mat():  # dark polished terrazzo in 1.2 m tiles, with smudges
    m = mat('hfloor', '#121418', 0.1); v = OC(m)
    br = nn(m, 'ShaderNodeTexBrick', offset=0.0, squash=1.0); ln(m, v, br.inputs['Vector'])
    for k, d in (('Scale', 1.0), ('Mortar Size', 0.005), ('Mortar Smooth', 0.3), ('Brick Width', 1.2), ('Row Height', 1.2), ('Bias', 0.0)): br.inputs[k].default_value = d
    br.inputs['Color1'].default_value = hx('#131518'); br.inputs['Color2'].default_value = hx('#181A1E'); br.inputs['Mortar'].default_value = hx('#08090A')
    base = MIXB(m, 0.5, br.outputs['Color'], RAMP(m, NZ(m, v, 2.2, 6), [(0.35, '#0E1013'), (0.65, '#1D2025')]), 'MULTIPLY')
    base = MIXB(m, 0.45, br.outputs['Color'], base)
    c1 = MR(m, VO(m, v, 70.0), 0.12, 0.2, 0.75, 0.0); c2 = MR(m, VO(m, v, 28.0, rnd=0.9), 0.08, 0.13, 0.6, 0.0)
    col = MIXB(m, c1, base, hx('#474A52')); col = MIXB(m, c2, col, hx('#5C5448'))
    col = MIXB(m, br.outputs['Fac'], col, hx('#060607'))
    SET(m, 'Base Color', col)
    sm_ = MR(m, NZ(m, v, 0.7, 4), 0.35, 0.75, 0.035, 0.24)
    SET(m, 'Roughness', mth(m, 'MAXIMUM', sm_, mth(m, 'MULTIPLY', br.outputs['Fac'], 0.75)))
    SET(m, 'Normal', BMP(m, mth(m, 'SUBTRACT', 1.0, br.outputs['Fac']), 0.6, 0.002)); return m
def concrete2(name, h, rough):
    m = mat(name, h, rough); v = OC(m)
    mid = NZ(m, v, 3.5, 8); big = NZ(m, v, 0.5, 3); streak = NZ(m, OC(m, (2.2, 2.2, 0.1)), 4.0, 6)
    board = WV(m, v, 0.9, 0.0, 'Z')
    col = RAMP(m, mid, [(0.3, '#5B5751'), (0.55, '#77736C'), (0.75, '#8E8981')])
    col = MIXB(m, MR(m, streak, 0.45, 0.75, 0.0, 0.45), col, hx('#3D3A36'))
    col = MIXB(m, MR(m, big, 0.3, 0.7, 0.0, 0.3), col, hx('#4A4743')); col = MIXB(m, 0.12, col, board, 'MULTIPLY')
    SET(m, 'Base Color', grime(m, col, 0.6, 0.6)); SET(m, 'Roughness', MR(m, mid, 0.2, 0.8, rough - 0.12, rough + 0.08))
    SET(m, 'Normal', BMP(m, VO(m, v, 55.0), 0.35, 0.002, BMP(m, mid, 0.35, 0.01))); return m
def metal(name, cols, rough, scale=6.0, tarnish=None, smudge=0.12, bump_=0.0):
    m = mat(name, cols[0][1], rough[0], 1.0); v = OC(m); t = NZ(m, v, scale, 6); s_ = NZ(m, v, scale * 5, 4)
    col = RAMP(m, t, cols)
    if tarnish: col = MIXB(m, MR(m, AOF(m, 0.08), 0.25, 0.9, 0.85, 0.0), col, hx(tarnish))
    SET(m, 'Base Color', col)
    SET(m, 'Roughness', mth(m, 'ADD', MR(m, t, 0.3, 0.75, rough[0], rough[1]), MR(m, s_, 0.45, 0.8, 0.0, smudge)))
    if bump_: SET(m, 'Normal', BMP(m, NZ(m, v, 500.0, 2), bump_, 0.0005))
    return m
def plastic(name, h, rough, metal_=0.0):
    m = mat(name, h, rough, metal_); v = OC(m)
    SET(m, 'Roughness', MR(m, NZ(m, v, 9.0, 5), 0.3, 0.75, rough - 0.08, rough + 0.12))
    SET(m, 'Normal', BMP(m, NZ(m, v, 700.0, 2), 0.12, 0.0004)); return m
def wood2(name, cols, rough, axis='X', scale=7.0, coat=0.0, cracks=0.0, soot=0.0):
    st_ = {'X': (0.05, 1, 1), 'Y': (1, 0.05, 1), 'Z': (1, 1, 0.05)}[axis]
    m = mat(name, cols[0][1], rough); v = OC(m, st_); g = NZ(m, v, scale, 10, 0.62, 1.5)
    lines = MR(m, mth(m, 'SINE', mth(m, 'MULTIPLY', g, 90.0)), 0.75, 1.0, 0.0, 1.0)
    col = RAMP(m, g, cols); col = MIXB(m, mth(m, 'MULTIPLY', lines, 0.35), col, hx('#140B05'))
    h = mth(m, 'ADD', mth(m, 'MULTIPLY', lines, 0.4), g)
    if cracks:
        ck = MR(m, VO(m, OC(m, tuple(x * 1.0 for x in st_)), 9.0, 'DISTANCE_TO_EDGE'), 0.0, 0.03, 1.0, 0.0)
        col = MIXB(m, mth(m, 'MULTIPLY', ck, cracks), col, hx('#0A0604')); h = mth(m, 'SUBTRACT', h, mth(m, 'MULTIPLY', ck, cracks))
    if soot: col = MIXB(m, MR(m, NZ(m, OC(m), 1.4, 5), 0.4, 0.75, 0.0, soot), col, hx('#0D0A08'))
    SET(m, 'Base Color', grime(m, col, 0.12, 0.5)); SET(m, 'Roughness', MR(m, g, 0.2, 0.8, rough - 0.08, rough + 0.06))
    SET(m, 'Normal', BMP(m, h, 0.3, 0.0015))
    if coat: SET(m, 'Coat Weight', coat); SET(m, 'Coat Roughness', MR(m, NZ(m, OC(m), 14.0, 3), 0.4, 0.7, 0.04, 0.14))
    return m
def rock_mat():
    m = mat('rock', '#3A332C', 0.9); v = OC(m)
    n1 = NZ(m, v, 1.6, 8, 0.6); n2 = NZ(m, v, 11.0, 6); vo = VO(m, v, 3.2)
    col = RAMP(m, n1, [(0.3, '#1A1714'), (0.5, '#35302A'), (0.68, '#4E453B'), (0.8, '#615548')])
    seam = MR(m, WV(m, v, 0.7, 6.0, 'Z'), 0.78, 0.92, 0.0, 1.0)
    col = MIXB(m, seam, col, hx('#0B0B0C')); col = MIXB(m, MR(m, n2, 0.55, 0.8, 0.0, 0.5), col, hx('#6E6152'))
    SET(m, 'Base Color', grime(m, col, 0.5, 0.7))
    wet = MR(m, NZ(m, v, 2.2, 4), 0.48, 0.62, 0.92, 0.32); SET(m, 'Roughness', mth(m, 'MINIMUM', wet, MR(m, seam, 0, 1, 1.0, 0.4)))
    SET(m, 'Normal', BMP(m, n2, 0.35, 0.01, BMP(m, vo, 0.7, 0.06))); return m
def dirt_mat():
    m = mat('dirt', '#241F1A', 0.95); v = OC(m); n = NZ(m, v, 4.0, 8); p = VO(m, v, 26.0)
    col = RAMP(m, n, [(0.35, '#16130F'), (0.65, '#2E2720')]); col = MIXB(m, MR(m, p, 0.0, 0.25, 0.5, 0.0), col, hx('#4A4036'))
    SET(m, 'Base Color', col); SET(m, 'Roughness', MR(m, NZ(m, v, 0.9, 3), 0.5, 0.62, 0.95, 0.25))
    SET(m, 'Normal', BMP(m, mth(m, 'SUBTRACT', 1.0, p), 0.5, 0.012, BMP(m, n, 0.3, 0.01))); return m
def rust_mat():
    m = mat('rust', '#5A3E2C', 0.62, 0.5); v = OC(m); n = NZ(m, v, 5.0, 8); r = MR(m, NZ(m, v, 2.0, 6), 0.42, 0.55, 0.0, 1.0)
    rc = RAMP(m, n, [(0.3, '#3A1E10'), (0.6, '#7A3E1C'), (0.8, '#A4602C')])
    SET(m, 'Base Color', grime(m, MIXB(m, r, hx('#2C302D'), rc), 0.2, 0.6)); SET(m, 'Metallic', MR(m, r, 0, 1, 0.6, 0.0))
    SET(m, 'Roughness', MR(m, r, 0, 1, 0.45, 0.92)); SET(m, 'Normal', BMP(m, mth(m, 'MULTIPLY', n, r), 0.6, 0.006)); return m
def leather_mat():
    m = mat('leather', '#141518', 0.5); v = OC(m)
    SET(m, 'Base Color', RAMP(m, NZ(m, v, 3.0, 4), [(0.4, '#101113'), (0.6, '#1A1B1F')]))
    SET(m, 'Roughness', MR(m, NZ(m, v, 2.0, 4), 0.35, 0.7, 0.32, 0.55)); SET(m, 'Sheen Weight', 0.25)
    SET(m, 'Normal', BMP(m, VO(m, v, 320.0), 0.35, 0.0008)); return m
def granite_mat():
    m = mat('granite', '#1E2024', 0.2); v = OC(m)
    col = RAMP(m, NZ(m, v, 14.0, 6), [(0.35, '#121316'), (0.65, '#24272C')])
    col = MIXB(m, MR(m, VO(m, v, 120.0), 0.1, 0.2, 0.7, 0.0), col, hx('#5A5D66'))
    SET(m, 'Base Color', col); SET(m, 'Roughness', MR(m, NZ(m, v, 1.0, 3), 0.35, 0.7, 0.08, 0.26)); return m

M['hfloor'] = floor_mat()
M['bezel'] = plastic('bezel', '#0D0E10', 0.34, 0.3)
M['steel'] = metal('steel', [(0.3, '#272A2E'), (0.7, '#3A3E43')], (0.42, 0.28), 4.0, None, 0.1, 0.12)
M['chrome'] = metal('chrome', [(0.3, '#B9BDC3'), (0.7, '#D2D5DA')], (0.16, 0.06), 5.0, None, 0.1)
M['brass'] = metal('brass', [(0.3, '#7A5C2C'), (0.55, '#BE9550'), (0.8, '#D9B46C')], (0.42, 0.2), 7.0, '#3A2A12', 0.14, 0.15)
M['leather'] = leather_mat()
M['concrete'] = concrete2('concrete', '#77736D', 0.85)
M['ceil'] = plastic('ceil', '#17191D', 0.8)
M['granite'] = granite_mat()
M['paint'] = plastic('paint', '#E6E9EE', 0.3)
M['tarmac'] = mat('tarmac', '#0C0D0F', 0.65)
M['label'] = mat('label', '#F1F3F6', 0.5, emit=1.4, eh='#F1F3F6')
M['walnut'] = wood2('walnut', [(0.25, '#24150B'), (0.55, '#4E3220'), (0.8, '#6A4630')], 0.4, 'X', 6.0, coat=0.8)
M['timber'] = wood2('timber', [(0.25, '#2E2116'), (0.55, '#4F3A27'), (0.8, '#6B5237')], 0.9, 'Z', 5.0, cracks=0.8, soot=0.7)
M['timber_h'] = wood2('timber_h', [(0.25, '#2E2116'), (0.55, '#4F3A27'), (0.8, '#6B5237')], 0.9, 'X', 5.0, cracks=0.8, soot=0.7)
M['rock'] = rock_mat()
M['dirt'] = dirt_mat()
M['rust'] = rust_mat()
M['iron'] = metal('iron', [(0.3, '#1E1C1A'), (0.6, '#3A2A1E'), (0.8, '#4A3220')], (0.75, 0.45), 6.0, '#2A170C', 0.1, 0.2)
M['coal'] = mat('coal', '#0B0B0C', 0.3); rough_noise(M['coal'], 0.18, 0.45, 30.0)
M['eye'] = mat('eye', '#030303', 0.05); SET(M['eye'], 'Coat Weight', 1.0); SET(M['eye'], 'Coat Roughness', 0.02)
M['note'] = mat('note', '#FFE9A8', 0.4, emit=3.5, eh='#FFE3A0')
M['sheet'] = plastic('sheet', '#E9ECEE', 0.75)
M['vinyl'] = plastic('vinyl', '#7E8885', 0.35)
M['wallpale'] = plastic('wallpale', '#AEB9B6', 0.8)
M['board'] = wood2('board', [(0.3, '#6A4428'), (0.6, '#8C6038'), (0.85, '#A0744A')], 0.5, 'Y', 6.0)
M['signbox'] = plastic('signbox', '#0B0C0E', 0.4, 0.4)

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
def screen_glass(m, u, v):
    b = principled(m); b.inputs['Roughness'].default_value = 0.35; b.inputs['Coat Weight'].default_value = 1.0
    sm_ = NZ(m, OC(m, loc=(random.uniform(0, 50), 0, 0)), 9.0, 5); ln(m, MR(m, sm_, 0.45, 0.8, 0.015, 0.16), b.inputs['Coat Roughness'])
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
    screen_glass(m, u, v)
    vig = mth(m, 'MULTIPLY_ADD', mth(m, 'ADD', mth(m, 'POWER', mth(m, 'SUBTRACT', u, 0.5), 2.0), mth(m, 'POWER', mth(m, 'SUBTRACT', v, 0.5), 2.0)), -0.55, 1.0)
    ln(m, c, b.inputs['Emission Color']); ln(m, mth(m, 'MULTIPLY', mth(m, 'MULTIPLY', V['lum'], vig), random.uniform(0.9, 1.05)), b.inputs['Emission Strength'])
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
# hanging gate signs (black lightboxes, yellow type), queue posts with belts at the kiosks, a few bins
SIGNY = mat('signy', '#FFC21A', 0.4, emit=5.0, eh='#FFC21A'); SIGNW = mat('signw', '#F4F6F8', 0.4, emit=4.0, eh='#F4F6F8')
gs = MB()
for k, (x, y, g) in enumerate(((-9.6, -10.6, 'B12'), (9.6, -10.6, 'B14'), (-9.6, -22.0, 'B10'), (9.6, -22.0, 'B16'))):
    gs.box((x, y, 5.4), (2.6, 0.22, 0.62), M['signbox'])
    for sx in (-1, 1): gs.cyl((x + sx * 1.0, y, 5.7 + (HZ - 5.7) / 2), 0.012, HZ - 5.7, M['steel'], seg=8)
    face_txt(f'gate{k}', g, 'inter_b', 0.3, SIGNY, None, x - 0.55, y - 0.11, 5.4, space=1.05)
    face_txt(f'gatew{k}', 'GATE', 'inter_sb', 0.14, SIGNW, None, x + 0.62, y - 0.11, 5.4, space=1.3)
gs.ob('gatesigns', None, bev=0.01)
qp = MB(); BELT = plastic('belt', '#101218', 0.5)
for sx in (-1, 1):
    for k in range(4):
        x = sx * (11.6 - 0.0) ; y = -4.6 - 1.2 * k
        qp.cyl((x, y, 0.5), 0.03, 1.0, M['chrome'], seg=16).cyl((x, y, 0.02), 0.17, 0.04, M['chrome'], seg=32).cyl((x, y, 1.01), 0.045, 0.03, M['chrome'], seg=16)
        if k < 3: qp.box((x, y - 0.6, 0.93), (0.006, 1.14, 0.05), BELT)
    qp.cyl((sx * 16.8, -6.0, 0.45), 0.24, 0.9, M['steel'], seg=32).cyl((sx * 16.8, -6.0, 0.92), 0.25, 0.05, M['chrome'], seg=32)
qp.ob('queue', None)
# check-in kiosks
def small_mat(name, key, w, h, ax='Z', lum=1.4):
    m = mat(name, '#000000', 0.12); b = principled(m); sp, u, v, uv = obj_uv(m, w, h, ax)
    a = teximg(m, key, uv).outputs['Color']; bs = teximg(m, 'bsod_l', uv).outputs['Color']
    cr = val(m, 0.0); lm = val(m, lum)
    screen_glass(m, u, v)
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
from mathutils import noise as mnz
def blob(mb, c, size, m, amp=0.28, freq=1.4, sub=3):
    r = bmesh.ops.create_icosphere(mb.bm, subdivisions=sub, radius=1.0); off = Vector((random.uniform(0, 99), random.uniform(0, 99), random.uniform(0, 99)))
    rot = Euler((random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(-PI, PI))).to_matrix()
    for vv in r['verts']:
        p = vv.co.copy(); n_ = mnz.fractal(p * freq + off, 0.55, 2.2, 4) + 0.35 * mnz.noise(p * freq * 4 + off)
        p = p * (1 + amp * n_); vv.co = Vector(c) + rot @ Vector((p.x * size[0] / 2, p.y * size[1] / 2, p.z * size[2] / 2))
    return mb._fin(r['verts'], m)
rk = MB()
rk.box((MX0 - 2.35, (MY0 + MY1) / 2, THm / 2), (0.4, MY1 - MY0, THm + 1.4), M['rock']).box((MX0 + 2.35, (MY0 + MY1) / 2, THm / 2), (0.4, MY1 - MY0, THm + 1.4), M['rock'])
rk.box((MX0, (MY0 + MY1) / 2, THm + 0.75), (TWm + 2.6, MY1 - MY0, 0.4), M['rock'])
y = MY0
while y < MY1:
    for sx in (-1, 1):
        for zc, zh in ((0.55, 1.6), (1.75, 1.7), (2.75, 1.2)):
            blob(rk, (MX0 + sx * (TWm / 2 + 0.42 + random.uniform(-0.1, 0.1)), y + random.uniform(-0.2, 0.2), zc), (1.0, random.uniform(1.1, 1.6), zh), M['rock'])
    blob(rk, (MX0 + random.uniform(-0.4, 0.4), y + random.uniform(-0.2, 0.2), THm + 0.32), (TWm * 0.7, random.uniform(1.1, 1.5), 0.75), M['rock'])
    y += 0.8
rk.box((MX0, (MY0 + MY1) / 2, -0.1), (TWm + 1.0, MY1 - MY0, 0.2), M['dirt'])
for _ in range(90): blob(rk, (MX0 + random.choice((-1, 1)) * random.uniform(0.75, 1.35), random.uniform(MY0, MY1), 0.0), (random.uniform(0.08, 0.3),) * 2 + (random.uniform(0.06, 0.16),), M['rock'], 0.35, 2.0, 2)
rk.box((MX0, MY1 + 0.5, THm / 2), (TWm + 2, 1.0, THm + 1), M['rock'])
rk.ob('rock', None, smooth=True)
tb = MB()
for k in range(34):
    y = MY0 + 2.0 + 1.6 * k
    for sx in (-1, 1): tb.box((MX0 + sx * (TWm / 2 - 0.12), y, (THm - 0.1) / 2), (0.2, 0.2, THm - 0.1), M['timber'], rot=(0, sx * 0.04, 0))
    tb.box((MX0, y, THm - 0.12), (TWm + 0.1, 0.22, 0.22), M['timber_h'])
for k in range(int((MY1 - MY0) / 0.6)): tb.box((MX0, MY0 + 0.3 + 0.6 * k, 0.04), (1.25, 0.16, 0.08), M['timber_h'])
tb.ob('timber', None, bev=0.01)
rl = MB()
for sx in (-1, 1): rl.box((MX0 + sx * 0.42, (MY0 + MY1) / 2, 0.12), (0.06, MY1 - MY0, 0.08), M['iron'])
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
light('CAGEL', 'SPOT', (MX0 + 0.25, 2.2, 2.5), (MX0 - 0.35, 3.2, 1.75), 45, '#FFEBD2', spot=28, blend=0.7, size=0.1, cutoff=4)
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
GEM = val(gm, 0.7)
pv.inputs['Emission Color'].default_value = hx('#A6C94E'); ln(gm, mth(gm, 'MULTIPLY', mth(gm, 'MULTIPLY', front, low), mth(gm, 'MULTIPLY', wisp, GEM)), pv.inputs['Emission Strength'])
MB().box((0, 0, 0), (TWm + 0.4, MY1 - MY0, THm), gm).ob('gas', None, (MX0, GY0, THm / 2), smooth=False, shadow=False)
tw(GW, 'default_value', 0.0, END, END * 0.35, 'lin')

# ---------- the canary: a real-looking bird. Metaball body (one smooth skin), layered wing and tail feathers, a horn beak ----------
def feather_mat(name, lo, hi, tip, fluff=True):
    m = mat(name, hi, 0.6); v = OC(m)
    g = NZ(m, v, 30.0, 4)
    sc_ = VO(m, OC(m, (0.5, 1.0, 1.0)), 230.0, 'SMOOTH_F1')   # overlapping feather tips
    col = RAMP(m, g, [(0.3, lo), (0.7, hi)])
    col = MIXB(m, MR(m, sc_, 0.1, 0.7, 0.0, 0.18), col, hx(tip or lo))   # darker at each feather's edge
    SET(m, 'Base Color', grime(m, col, 0.015, 0.8))
    if fluff: SET(m, 'Sheen Weight', 0.3); SET(m, 'Sheen Roughness', 0.4); SET(m, 'Sheen Tint', hx('#FFE9A0')); SET(m, 'Subsurface Weight', 0.15); SET(m, 'Subsurface Scale', 0.004)
    fine = WV(m, OC(m, (1.0, 1.0, 1.0)), 900.0, 2.0, 'Y')    # barbs
    SET(m, 'Normal', BMP(m, NZ(m, v, 700.0, 3), 0.25, 0.0002, BMP(m, fine, 0.12, 0.00005, BMP(m, sc_, 0.35, 0.0012))))
    SET(m, 'Roughness', MR(m, g, 0.3, 0.7, 0.45, 0.65)); return m
M['canary'] = feather_mat('canary', '#F2A900', '#FFD21A', '#D98E00')
M['canary_w'] = feather_mat('canary_w', '#D29A00', '#F7C51A', '#7A6410')
M['canary_t'] = feather_mat('canary_t', '#9A7A10', '#E0B21C', '#4A4214', fluff=False)
M['beak'] = mat('beak', '#E7C39A', 0.35); SET(M['beak'], 'Subsurface Weight', 0.5); SET(M['beak'], 'Subsurface Scale', 0.003)
M['leg'] = mat('leg', '#D9A28A', 0.45); SET(M['leg'], 'Subsurface Weight', 0.4); SET(M['leg'], 'Subsurface Scale', 0.002)
SET(M['leg'], 'Normal', BMP(M['leg'], VO(M['leg'], OC(M['leg']), 900.0), 0.4, 0.0002))

def meta_mesh(name, elems, m, res=0.0035, thresh=0.25):
    md = bpy.data.metaballs.new(name + '_md'); md.resolution = md.render_resolution = res; md.threshold = thresh
    for kind, co, r, sz, rot in elems:
        e = md.elements.new(type=kind); e.co = co; e.radius = r
        if sz: e.size_x, e.size_y, e.size_z = sz
        if rot: e.rotation = Euler(rot).to_quaternion()
    mo = bpy.data.objects.new(name + '_mo', md); col.objects.link(mo); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(mo); bpy.data.metaballs.remove(md)
    me.materials.clear(); me.materials.append(m); me.shade_smooth(); return me
def feather(mb, root_, tip, w, th, m, flat=False):  # a long leaf-shaped feather from root to tip, thin across the flank (or flat for the tail)
    a, b = Vector(root_), Vector(tip); d = b - a; L_ = d.length
    R = d.to_track_quat('X', 'Z').to_matrix().to_4x4()
    mx = Matrix.Translation((a + b) / 2) @ R @ Matrix.Diagonal((L_ / 2, w, th, 1.0) if flat else (L_ / 2, th, w, 1.0))
    res = bmesh.ops.create_uvsphere(mb.bm, u_segments=16, v_segments=8, radius=1.0, matrix=mx); return mb._fin(res['verts'], m)
BIRD_ME = None
def bird_mesh():
    E = 'ELLIPSOID'
    body = [('BALL', (0.03, 0, 0.062), 0.050, None, None),                       # breast
            (E, (-0.005, 0, 0.064), 0.058, (1.25, 0.82, 0.8), (0, rad(-28), 0)),   # body, tilted head-up
            (E, (-0.05, 0, 0.042), 0.04, (1.4, 0.7, 0.55), (0, rad(-30), 0)),      # rump
            ('BALL', (0.045, 0, 0.095), 0.034, None, None),                       # neck
            (E, (0.06, 0, 0.113), 0.034, (1.12, 0.95, 0.98), None),               # head
            (E, (0.078, 0, 0.107), 0.016, (1.2, 1.0, 0.9), None)]                 # cheek / face
    me_b = meta_mesh('canary_body', body, M['canary'])
    mb = MB()
    for sy in (-1, 1):  # folded wing: coverts then primaries, lying along the flank
        for k in range(5):
            r0 = Vector((0.03 - 0.008 * k, sy * (0.036 - 0.001 * k), 0.083 - 0.004 * k)); t0 = Vector((-0.06 - 0.008 * k, sy * (0.029 - 0.002 * k), 0.034 + 0.002 * k))
            feather(mb, r0, t0, 0.017 - 0.0015 * k, 0.0026, M['canary_w'] if k < 3 else M['canary_t'])
        feather(mb, (0.035, sy * 0.037, 0.08), (-0.015, sy * 0.039, 0.058), 0.02, 0.003, M['canary_w'])
    for k in range(5):  # tail fan
        sy = (k - 2) * 0.0045
        feather(mb, (-0.055, sy, 0.04), (-0.125, sy * 2.4, 0.012), 0.0085, 0.0018, M['canary_t'], flat=True)
    mb.cyl((0.094, 0, 0.112), 0.0085, 0.017, M['beak'], rot=(0, PI / 2 + rad(6), 0), seg=16, r2=0.0012)
    for sy in (-1, 1):
        mb.sph((0.071, sy * 0.0215, 0.119), 0.0046, M['eye'], seg=14, ring=8)
        mb.cyl((0.004, sy * 0.012, 0.016), 0.0026, 0.032, M['leg'], rot=(rad(-sy * 6), rad(10), 0), seg=8)
        for a in (-0.5, 0.0, 0.5):  # three toes forward, one back, curled on the perch
            mb.cyl((0.006 + 0.008 * math.cos(a), sy * 0.012 + 0.008 * math.sin(a), 0.001), 0.0017, 0.017, M['leg'], rot=(0, PI / 2, a), seg=6)
        mb.cyl((-0.004, sy * 0.012, 0.001), 0.0017, 0.012, M['leg'], rot=(0, PI / 2, 0), seg=6)
    me_d = bpy.data.meshes.new('canary_detail'); mb.bm.to_mesh(me_d); mb.bm.free()
    for m_ in mb.mats: me_d.materials.append(m_)
    me_d.shade_smooth()
    jb = MB(); jb.cyl((0.008, 0, -0.002), 0.0062, 0.015, M['beak'], rot=(0, PI / 2 + rad(14), 0), seg=12, r2=0.001)
    me_j = bpy.data.meshes.new('canary_jaw'); jb.bm.to_mesh(me_j); jb.bm.free(); me_j.materials.append(M['beak']); me_j.shade_smooth()
    return me_b, me_d, me_j
def note(name, parent): return None
def bird(name, parent, loc, s, yaw):
    global BIRD_ME
    if BIRD_ME is None: BIRD_ME = bird_mesh()
    root = empty(name, parent, loc, (0, 0, yaw)); root.scale = (s, s, s); body = empty(name + '_b', root)
    for k, me in enumerate(BIRD_ME[:2]):
        o = bpy.data.objects.new(f'{name}_m{k}', me); col.objects.link(o); o.parent = body
    jaw = empty(name + '_jaw', body, (0.084, 0, 0.106))
    o = bpy.data.objects.new(name + '_jm', BIRD_ME[2]); col.objects.link(o); o.parent = jaw
    body['jaw'] = jaw.name
    return root, body, []
def sing(body, notes, ivals, droops):
    on = lambda t: any(a <= t < b for a, b in ivals)
    def dr(t):
        v = 0.0
        for a, b in droops:
            if a <= t: v = max(v, sm((t - a) / 0.45) * (1 - sm((t - b) / 0.35)))
        return v
    def song(t):  # phrases of quick trills: the beak opens and closes, the throat shivers
        if not on(t): return 0.0
        ph = 0.5 + 0.5 * math.sin(2 * PI * 0.55 * t)
        return clamp(ph * 1.3 - 0.25) * (0.55 + 0.45 * math.sin(2 * PI * 7.5 * t)) * (0.7 + 0.3 * math.sin(2 * PI * 2.1 * t + 1))
    look = lambda t: rad(10) * math.sin(0.9 * t) * math.sin(0.37 * t + 1.3) + rad(6) * math.sin(2.3 * t) * (1 - dr(t))
    fn(body, 'rotation_euler', 0.0, END, lambda t: (rad(1.2) * math.sin(2 * PI * 13 * t) * song(t), rad(-6) * song(t) + rad(42) * dr(t), look(t) * (1 - dr(t))))
    fn(body, 'scale', 0.0, END, lambda t: (1.0, 1.0 + 0.06 * dr(t), 1.0 + 0.03 * dr(t)))  # fluffed up when sick
    jaw = bpy.data.objects[body['jaw']]
    fn(jaw, 'rotation_euler', 0.0, END, lambda t: (0.0, rad(24) * song(t), 0.0))
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
_pl = light('PLQL', 'SPOT', (0.7, -1.5, 1.2), (0.05, 0.0, 0.42), float(opt('--plql', 60)), '#FFE2B8', spot=32, blend=0.7, size=0.15, cutoff=5); _pl.parent = PLQ; _pl.data.specular_factor = 0.0
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
light('ATMF', 'AREA', (AX + 1.2, -1.6, 1.6), (AX, 0.2, 1.2), 60, '#DCE6FF', size=1.2, cutoff=6); light('ATMS', 'SPOT', (AX + 0.5, -1.9, 3.1), (AX, 0.3, 1.2), 1100, '#E6EEFF', spot=48, blend=0.8, size=0.2, cutoff=10)
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
st(GEM, 'default_value', CT(tEVERYONE), 0.12)
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
