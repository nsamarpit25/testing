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
