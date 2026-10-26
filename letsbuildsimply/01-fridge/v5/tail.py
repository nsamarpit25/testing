

# ================================================================ v5: cold open on the finished fridge, then the build, one readable cutaway
OPEN = '--open' in argv            # render the finished fridge for the hook (dissolved into the old icebox on "A hundred years ago")
SWAP = LS[1] - 0.1; SWAP_D = 0.5   # dissolve window [SWAP, SWAP + SWAP_D]
TB_FINAL = T['moves']              # build time the cold open shows
door.hide_render = False
for o in (panel, ice2, drop, frost_ring, spag, drain_o, dtray, dwater, heater_o, *extra_ice, *ice_shards, *glass_shards):
    o.hide_render = True
M['lett'] = mat('lett', (0.25, 0.6, 0.15), 0.5); lettuce.data.materials[0] = M['lett']
M['hotcu'] = mat('hotcu', (0.92, 0.5, 0.32), 0.28, metal=1.0); disch_o.data.materials[0] = M['hotcu']
M['bulb'] = mat('bulb', (1.0, 0.92, 0.75), 0.3, emit=(1.0, 0.85, 0.6), estr=0.0)
seal = box('seal', X0 + TH, X0 + TH + 0.016, Y0 + 0.004, Y1 - TH, Z0 + TH, Z1 - TH, M['rubber'], bev=0.004)
bulb = smooth(prim('uv_sphere', 'bulb', (0.05, 0.22, Z1 - TH - 0.035), M['bulb'], radius=0.022, segments=24, ring_count=12))
sock = smooth(prim('cylinder', 'socket', (0.05, 0.22, Z1 - TH - 0.008), M['steelm'], radius=0.014, depth=0.02, vertices=24))
gl = bpy.data.lights.new('backglow', 'POINT'); gl.color = (1.0, 0.45, 0.15); gl.shadow_soft_size = 0.3; gl.energy = 0
BACKGLOW = link(bpy.data.objects.new('backglow', gl)); BACKGLOW.location = (0.64, 0.4, 1.0)
CONDP = 0.28
for m_ in (M['box'], M['cut']): m_.node_tree.nodes[m_['mixnode']].inputs[7].default_value = (0.8, 0.81, 0.83, 1)   # soft grey enamel, not blown-out white
pset(P(M['spag']), color=(0.95, 0.66, 0.18))
# lettuce: crinkly core + leaves (was a plain ball)
lettuce.hide_render = True; LETT = []
LC = Vector((0.27, 0.06, Z0 + TH + 0.065))
core = smooth(prim('ico_sphere', 'lett_core', LC, M['lett'], radius=0.05, subdivisions=4))
dl = core.modifiers.new('crinkle', 'DISPLACE'); tx = bpy.data.textures.new('crinkle', 'VORONOI'); tx.noise_scale = 0.018; dl.texture = tx; dl.strength = 0.012
LETT.append(core)
for k in range(7):
    a = k * 2 * math.pi / 7
    lf = smooth(prim('uv_sphere', f'leaf{k}', LC + Vector((0.035 * math.cos(a), 0.035 * math.sin(a), -0.01)), M['lett'], radius=0.045, segments=20, ring_count=12))
    lf.scale = (1.0, 0.32, 1.15); lf.rotation_euler = (0, -0.5, a + math.pi / 2); lf.rotation_euler = (0.45 * math.cos(a + math.pi / 2), 0.45 * math.sin(a + math.pi / 2), a + math.pi / 2)
    d2 = lf.modifiers.new('crinkle', 'DISPLACE'); d2.texture = tx; d2.strength = 0.006; LETT.append(lf)
# melt water pools on the box floor (with drips) instead of a puddle under the box
pool = box('pool', X0 + TH + 0.004, X1 - TH - 0.004, Y0 + 0.004, Y1 - TH - 0.004, 0, 0.035, M['water'], bev=0)
pool.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.0175))); pool.location.z = Z0 + TH
puddle.hide_render = True
pset(P(M['water']), color=(0.3, 0.6, 1.0), emit=(0.3, 0.6, 1.0), estr=0.15)
_FU = Flow.update
def _upd(s, phase, grow, vis, colf, bright=1.0, jitter=0.0, sizef=None):
    _FU(s, phase, grow, vis, colf, bright, jitter)
    if sizef:
        for i, o in enumerate(s.dots):
            if not o.hide_render:
                d = (i * s.sp + phase) % (s.n * s.sp); o.scale = (o.scale[0] * sizef(d / s.path.L),) * 3
Flow.update = _upd
pset(P(M['floor']), coat=0.0, rough=0.6)   # no sharp window glint on the floor
TMIN, TMAX = -20.0, 30.0
zero_mark.location.z = TH_Z0 + temp_h(0)

def flow_speed(t):
    if T['cuts'] < t < T['thermo'] + 0.6: return 0.0            # the thermostat cuts the pump
    if T['stop'] < t < LS[18]: return 0.0                        # and the hum stops at night
    return 0.22 * (1.0 + 1.4 * win(t, T['round'], T['glass'], 0.4, 0.5))
PHASE = [0.0]
for f in range(1, NF + 2): PHASE.append(PHASE[-1] + flow_speed(f / FPS) / FPS)
def comp_on(tb, t): return tb >= T['crush'] and flow_speed(t) > 0.05
def temp(tb):
    return sched(tb, [(0.0, 4), (SWAP, 4), (SWAP + 0.4, 21), (T['iceblk'], 21), (T['days'], 5), (T['then'], 5), (T['yog'], 22),
                      (T['boiling'], 22), (T['evap'] + 0.3, 5), (T['gas'], 5), (T['trap'], 14), (T['drops'], 14), (T['cap'], 4),
                      (T['forever'], 4), (T['glass'], -18), (T['cuts'], -18), (T['thermo'] + 0.5, 4), (END + 2, 4)])
def colf_capil(tb):
    return lambda f: mix(WARM, COLD, ss(f, 0.75, 1.0)) if tb > T['drops'] - 0.2 else WARM

# ---------------------------------------------------------------- camera: framings (target, distance, yaw°, pitch°, lens), eased in sequence + slow drift
V = Vector
def F(tg, d, yaw, pitch, lens=40): return (V(tg), d, yaw, pitch, lens)
def lerpF(a, b, k): return (a[0].lerp(b[0], k),) + tuple(x + (y - x) * k for x, y in zip(a[1:], b[1:]))
OPEN0 = F((-0.1, 0.02, 1.06), 1.15, -20, 6)   # hook: close on the milk, heat leaving it; dolly back to reveal the fridge
HERO = F((0.2, 0.1, 0.82), 3.25, -12, 7)
CAMK = [
    (0.0, 4.2, HERO),
    (SWAP + 0.3, 2.4, F((0.0, 0.05, 0.98), 2.5, -6, 8)),                 # the icebox
    (T['iceblk'] - 0.5, 0.8, F((0.0, 0.05, 1.1), 2.1, -4, 11)),           # ice lands
    (T['brill'], 2.4, F((0.05, 0.05, 0.92), 2.8, -16, 6)),                # two days pass
    (T['then'] - 0.1, 1.1, F((-0.12, 0.0, 0.62), 2.4, -20, 13)),          # puddle
    (T['yog'] - 0.45, 0.55, F((-0.12, 0.02, 1.04), 1.3, -14, 5)),         # yogurt
    (T['thing'] - 0.1, 1.4, F((0.2, 0.1, 1.0), 3.9, -4, 4)),              # heat only moves
    (T['swap'] - 0.2, 1.2, F((0.0, 0.1, 1.38), 1.8, -12, 9)),             # pipe replaces the ice
    (T['evap'] - 0.4, 0.8, F((0.02, 0.1, 1.42), 1.55, -6, 7)),
    (T['gas'] - 0.2, 0.9, F((0.4, 0.1, 1.25), 1.6, 16, 5)),               # gas escapes at the back
    (T['trap'], 1.2, F((0.55, 0.1, 0.45), 1.6, 22, 12)),                  # compressor
    (T['hot'] - 0.2, 0.8, F((0.62, 0.1, 0.3), 1.15, 28, 10)),             # hot
    (T['snake'] - 0.2, 1.6, F((0.6, 0.1, 1.05), 2.3, 30, 5)),             # condenser
    (T['warmline'] - 0.2, 1.0, F((0.66, 0.1, 1.0), 1.8, 50, 3)),          # warm back
    (T['cools'] - 0.1, 1.2, F((0.55, 0.1, 0.62), 1.6, 26, 6)),            # liquid again
    (T['push'] - 0.1, 1.4, F((0.47, 0.1, 1.0), 1.7, 16, 4)),              # capillary
    (T['pressure'] - 0.25, 0.8, F((0.36, 0.1, 1.42), 1.5, 8, 6)),         # spray into the evaporator
    (T['round'] - 0.2, 1.4, F((0.2, 0.1, 0.85), 3.4, -8, 6)),             # round and round
    (T['problem'] + 0.2, 1.0, F((0.2, 0.06, 0.36), 1.3, -10, 14)),        # lettuce
    (T['sensor'] - 0.2, 1.0, F((0.22, 0.2, 0.95), 1.6, -6, 6)),           # thermostat
    (T['click'] - 0.3, 1.0, HERO),
    (T['foam'] - 0.2, 2.0, F((0.2, 0.1, 0.85), 3.0, -18, 7)),
    (T['congrats'] - 0.1, 1.2, HERO),
    (T['never'], 1.6, F((0.45, 0.1, 1.1), 2.3, 10, 6)),                   # follow the heat out
    (T['milk'] - 0.2, END + 0.8 - T['milk'], OPEN0),                     # end where the hook starts (loops)
]
IMPACTS = [(T['iceblk'], 0.016), (T['slam'], 0.02), (T['crush'], 0.02), (T['spaghetti'] + 0.5, 0.004), (T['cuts'], 0.004)]
def cam_state(t):
    cur = OPEN0
    for t0, dur, fr in CAMK:
        if t < t0: break
        cur = lerpF(cur, fr, ss(t, t0, t0 + dur))
    tg, d, yaw, pitch, lens = cur
    dr = ss(t, 0.0, 1.5) * (1 - ss(t, END - 1.0, END + 0.6))   # drift fades out at both ends so the loop is seamless
    yaw += dr * 2.5 * math.sin(0.5 * t); pitch += dr * 1.0 * math.sin(0.37 * t + 1); d *= 1 + dr * 0.012 * math.sin(0.6 * t + 2)
    ya, pa = math.radians(yaw), math.radians(pitch)
    p = tg + d * V((math.sin(ya) * math.cos(pa), -math.cos(ya) * math.cos(pa), math.sin(pa)))
    sh = V((0, 0, 0))
    for t0, a in IMPACTS:
        if t0 <= t < t0 + 0.6:
            e = a * math.exp(-(t - t0) * 9); sh += V((e * math.sin(t * 71), 0, e * math.sin(t * 53 + 1)))
    return p + sh, tg + sh * 0.5, lens
def apply_cam(t):
    p, g, l = cam_state(t)
    cam.location = p; cam.rotation_euler = (g - p).to_track_quat('-Z', 'Y').to_euler(); cam_d.lens = l

# ---------------------------------------------------------------- per-frame state.  tb = build time (what exists), t = real time (camera, motion)
def state(t):
    f_idx = int(round(t * FPS))
    tb = TB_FINAL if OPEN else t
    apply_cam(t)
    # --- light: two quick days, night for the hum
    night = win(tb, T['night'] - 0.3, LS[18] + 0.1, 0.4, 0.4)
    cyc = 0.5 + 0.5 * math.cos(2 * math.pi * 2 * ss(tb, T['twod'] - 0.3, T['days'] + 0.5)) if T['twod'] - 0.3 < tb < T['days'] + 0.5 else 1.0
    dimf = (0.35 + 0.65 * cyc) * (1 - 0.8 * night)
    blue = mix((1.0, 0.93, 0.84), (0.55, 0.65, 1.0), max(night, 1 - cyc))
    key.data.energy = KEYP * dimf; key.data.color = blue
    fill.data.energy = FILLP * (1 - 0.5 * night); top.data.energy = TOPP * dimf
    bg.inputs['Strength'].default_value = WORLDS * (1 - 0.6 * night) * (0.5 + 0.5 * cyc)
    sk = mix((0.6, 0.82, 1.0), (0.05, 0.08, 0.25), max(night, 1 - cyc))
    pset(P(M['sky']), color=sk, emit=sk, estr=2.5 * (1 - 0.6 * max(night, 1 - cyc)))
    pset(P(M['wall']), color=WALLC)
    if SUN: SUN.data.energy = SUNP * dimf
    spin = ss(tb, T['twod'] - 0.3, T['days'] + 0.5)
    hands[0].rotation_euler.y = math.radians(60) + spin * 2 * math.pi * 2
    hands[1].rotation_euler.y = math.radians(-30) + spin * 2 * math.pi * 24

    # --- the icebox: lid open, ice block drops in, lid slams; melts over two days; restocked; swapped for a pipe
    lid.rotation_euler.y = -math.radians(108) * win(tb, T['iceblk'] - 0.75, T['slam'] + 0.02, 0.25, 0.18)
    melt = ss(tb, T['twod'] - 0.6, T['puddle'] + 0.3)
    restock = pop(tb, T['thing'] + 0.5, 0.4) if tb > T['thing'] + 0.5 else 0.0
    out_ = ss(tb, T['swap'], T['pipe'] + 0.2)
    if tb < T['thing'] + 0.5:
        u = clamp((tb - (T['iceblk'] - 0.4)) / 0.4)
        ice.location = (0, 0.04, ICE_Z + 1.6 * (1 - u * u)); s = 1 - 0.75 * melt
        ice.scale = (s, s, max(0.001, 1 - melt)); ice.hide_render = tb < T['iceblk'] - 0.4 or melt > 0.995
    else:
        s = max(0.001, restock * (1 - out_)); ice.location = (0, 0.04, ICE_Z + 0.25 * out_)
        ice.scale = (s, s, s); ice.hide_render = s < 0.01
    icetray.hide_render = not (SWAP - 0.2 < tb < T['pipe'] + 0.3); icetray.scale = (max(0.001, 1 - out_),) * 3
    pud = ss(tb, T['twod'], T['puddle'] + 0.5) * (1 - ss(tb, T['thing'] - 0.1, T['thing'] + 0.5))
    pool.scale = (1, 1, max(0.35 * pud, 0.001)); pool.hide_render = pud < 0.02

    # --- milk: yogurt (cap pops off), fresh bottle, freezes with the lettuce, thaws
    spoil = ss(tb, T['yog'] - 0.4, T['yog'] + 0.2) * (1 - ss(tb, T['thing'] + 0.1, T['thing'] + 0.35))
    froz = ss(tb, T['lettuce'] - 0.4, T['glass']) * (1 - ss(tb, T['cuts'], T['thermo'] + 1.0))
    mc = mix((0.97, 0.97, 0.95), (0.93, 0.86, 0.55), spoil); mc = mix(mc, (0.75, 0.88, 1.0), froz)
    pset(P(M['milk']), color=mc, rough=0.35 + 0.4 * froz)
    milk_o.modifiers['lumps'].strength = 0.035 * spoil
    reset = (1 - ss(tb, T['thing'] - 0.2, T['thing'] + 0.05)) if tb < T['thing'] + 0.1 else (pop(tb, T['thing'] + 0.1, 0.4) if tb < T['thing'] + 0.6 else 1.0)
    for o in (bottle_o, milk_o): o.scale = (max(0.001, reset),) * 3
    cap_rest = V((-0.12, 0.02, 0.912 + 0.255))
    if T['yog'] - 0.1 < tb < T['thing'] + 0.1:
        u = clamp((tb - T['yog'] + 0.1) / 0.45)
        cap_o.location = cap_rest.lerp(V((0.06, -0.24, 0.925)), u) + V((0, 0, 0.03 * math.sin(u * math.pi)))
        cap_o.rotation_euler = (u * 7.5, u * 2, 0); cap_o.scale = (max(reset, 0.001),) * 3; cap_o.hide_render = False
    else:
        cap_o.location = cap_rest; cap_o.rotation_euler = (0, 0, 0); cap_o.scale = (max(reset, 0.001),) * 3; cap_o.hide_render = False
    pset(P(M['glass']), rough=0.04 + 0.3 * froz, alpha=0.18 + 0.25 * froz)
    # lettuce turns into a glass sculpture, then thaws
    for o in LETT: o.hide_render = False
    lg = ss(tb, T['lettuce'] - 0.1, T['lettuce'] + 0.5) * (1 - ss(tb, T['cuts'] + 0.2, T['thermo'] + 1.2))
    pset(P(M['lett']), color=mix((0.25, 0.6, 0.15), (0.3, 0.62, 1.0), lg), rough=0.5 - 0.47 * lg, coat=lg, alpha=1 - 0.45 * lg,
         emit=(0.5, 0.8, 1.0), estr=1.1 * lg)

    # --- thermometer
    tc = temp(tb); tliq.scale.z = temp_h(tc)
    pset(P(M['red']), color=mix((0.85, 0.08, 0.06), (0.2, 0.45, 1.0), clamp((8 - tc) / 20)))

    # --- the loop grows
    g_evap = ss(tb, T['pipe'] - 0.1, T['pipe'] + 1.6)
    g_suct = ss(tb, T['trap'] - 0.1, T['trap'] + 0.7)
    g_disch = 0.12 * ss(tb, T['crush'], T['crush'] + 0.3) + 0.88 * ss(tb, T['snake'] - 0.1, T['snake'] + 0.6)
    g_cond = ss(tb, T['snake'] + 0.3, T['pours'] + 0.3)
    g_capil = ss(tb, T['push'] + 0.1, T['spaghetti'] + 0.3)
    for o, g in ((evap_o, g_evap), (suct_o, g_suct), (disch_o, g_disch), (cond_o, g_cond), (capil_o, g_capil)):
        o.data.bevel_factor_end = max(g, 0.0005); o.hide_render = g < 0.002
    for i, fo in enumerate(fins):
        g = ss(tb, T['snake'] + 0.3 + i * 0.08, T['pours'] + 0.3 + i * 0.08); fo.data.bevel_factor_end = max(g, 0.0005); fo.hide_render = g < 0.002
    fr = clamp((2 - tc) / 14) * g_evap
    frost_o.hide_render = fr < 0.05; frost_o.data.bevel_depth = 0.012 + 0.009 * fr; frost_o.data.bevel_factor_end = max(g_evap, 0.0005)
    stub_s = ss(tb, T['liquid'] - 0.2, T['liquid'] + 0.2) * (1 - ss(tb, T['push'] + 0.4, T['push'] + 0.7))
    bulge = 1 + 0.5 * win(tb, T['tight'] - 0.5, T['push'] + 0.2, 0.3, 0.2) * (0.5 + 0.5 * math.sin(t * 22))
    stub.scale = (max(stub_s * bulge, 0.001),) * 3; stub.hide_render = stub_s < 0.01
    sg = win(tb, T['spaghetti'] - 0.15, T['pressure'] - 0.1, 0.2, 0.25); snap = ss(tb, T['spaghetti'] + 0.5, T['spaghetti'] + 0.75)
    for o, sgn in ((spagA, 1), (spagB, -1)):
        o.hide_render = sg < 0.02; o.data.bevel_factor_end = max(sg, 0.0005)
        o.location = (0.515 + 0.02 * sgn * snap, -0.02, 0.86 - 0.05 * snap); o.rotation_euler = (0, sgn * 0.5 * snap, 0)

    # --- compressor: drops in on "crush", x-ray piston, shudders while running
    cd = clamp((tb - (T['crush'] - 0.3)) / 0.3)
    drop_ = 0.0 if tb >= T['crush'] else (0.3 * (1 - cd * cd) if tb > T['crush'] - 0.3 else 9)
    cgrow = 0.55 + 0.45 * cd
    sq = 1 - 0.12 * math.sin(clamp((tb - T['crush']) / 0.25) * math.pi) * (tb > T['crush'])
    on = comp_on(tb, t)
    shake = 0.0025 * math.sin(t * 95) if on else 0.0
    for o in comp_parts:
        r = COMP_REST[o.name]; o.location = (r.x + shake, r.y, r.z + drop_ + (sq - 1) * 0.05); o.hide_render = drop_ > 5
        o.scale = (cgrow,) * 3 if o is not dome else (cgrow, cgrow, 0.62 * sq * cgrow)
    xr = win(tb, T['crush'] + 0.1, T['fingers'] + 0.4, 0.3, 0.4)
    pset(P(M['comp']), alpha=1 - 0.78 * xr)
    pz = 0.17 + 0.025 * math.sin(t * 2 * math.pi * 3) if on else 0.17
    piston.hide_render = rod.hide_render = xr < 0.02 or drop_ > 5
    piston.location = (CX + shake, Y, pz); rod.location = (CX + shake, Y, pz - 0.05)
    hot = ss(tb, T['hot'] - 0.1, T['burn']) * (1 - 0.85 * ss(tb, T['perfect'], T['cools']))
    pset(P(M['piston']), emit=(1.0, 0.25, 0.04), estr=3.0 * hot * xr)
    pset(P(M['hotcu']), emit=(1.0, 0.22, 0.03), estr=4.0 * hot, color=mix((0.92, 0.5, 0.32), (1.0, 0.3, 0.1), hot))
    pset(P(M['copper']), emit=(1.0, 0.3, 0.05), estr=0.0)
    pset(P(M['cond']), emit=(1.0, 0.35, 0.05), estr=CONDP * ss(tb, T['snake'] + 0.5, T['pours']))
    def hl(m, at, col=(1.0, 0.85, 0.2)):
        k = win(tb, at - 0.1, at + 0.9, 0.12, 0.4)
        if k > 0.001: pset(P(m), emit=col, estr=2.5 * k)
    hl(M['copper'], T['evap']); hl(M['cond'], T['cond']); hl(M['capil'], T['cap']); hl(M['dialm'], T['thermo'])
    if not (T['thermo'] - 0.2 < tb < T['thermo'] + 1.0): pset(P(M['dialm']), estr=0.0)
    if not (T['cap'] - 0.2 < tb < T['cap'] + 1.0): pset(P(M['capil']), estr=0.0)
    BACKGLOW.data.energy = 9 * ss(tb, T['pours'] - 0.3, T['pours'] + 0.6) + 45 * win(tb, T['warmline'] - 0.2, T['cools'] + 0.1, 0.4, 0.5) * (0.85 + 0.15 * math.sin(t * 6))

    # --- thermostat: dial pops in, wire runs to the pump; clicks the pump off
    th = pop(tb, T['sensor'], 0.35)
    for o in (dial, dptr): o.scale = (max(th, 0.001),) * 3; o.hide_render = th < 0.01
    dptr.rotation_euler.y = -math.radians(70) * ss(tb, T['cuts'] - 0.2, T['cuts'] + 0.15) + math.radians(25) * win(tb, T['click'] - 0.1, T['click'] + 0.5, 0.08, 0.2)
    gw = ss(tb, T['sensor'] + 0.1, T['cuts']); wire_o.data.bevel_factor_end = max(gw, 0.0005); wire_o.hide_render = gw < 0.002

    # --- foam, steel, door seal, a little light
    sf = ss(tb, T['foam'] - 0.1, T['foam'] + 0.5); st = ss(tb, T['foam'] + 0.2, T['seal'] + 0.4)
    for m in (M['box'], M['cut']): set_steel(m, st)
    for fo in foam: fo.hide_render = sf < 0.05; fo.scale = (1, 1, max(sf, 0.01))
    pset(P(M['tbackm']), color=mix((0.95, 0.95, 0.95), (0.16, 0.18, 0.22), st))
    hs = pop(tb, T['seal'], 0.35)
    for o in (handle, seal): o.scale = (max(hs, 0.001),) * 3; o.hide_render = hs < 0.01
    bl = ss(tb, T['light'] - 0.05, T['light'] + 0.25) * (1 - 0.9 * night)
    for o in (bulb, sock): o.hide_render = tb < T['light'] - 0.3
    pset(P(M['bulb']), estr=3.0 * bl)
    inside.data.energy = 7 + 5 * bl; inside.data.color = mix((0.6, 0.8, 1.0), (1.0, 0.9, 0.75), bl)

    # --- refrigerant dots
    ph = PHASE[min(f_idx, len(PHASE) - 1)]
    fill_ = ss(tb, T['filled'] - 0.1, T['filled'] + 1.0)
    leak = ss(tb, T['gas'], T['escape'] + 0.4) * (1 - ss(tb, T['trap'], T['trap'] + 0.5))
    dim = 1.0 if flow_speed(t) > 0.01 or tb < T['crush'] else 0.45
    w0 = T['drops'] + 0.3
    def wave(k): return 1.0 + 1.2 * win(tb, w0 + 0.25 * k, w0 + 0.25 * k + 0.7, 0.15, 0.4)
    tw = 1.0 + 0.5 * win(tb, T['never'], END + 2, 0.5, 0.5)
    flows['evap'].update(ph, g_evap * fill_, fill_ * (1 - 0.85 * leak), colf_evap(tb) if tb > T['boiling'] - 0.3 else (lambda f: COLD), dim * wave(0) * tw,
                        sizef=(lambda f: 0.8 + 0.6 * ss(f, 0.25, 0.9)) if tb > T['boiling'] - 0.3 else (lambda f: 0.8))
    flows['suct'].update(ph, g_suct, ss(tb, T['trap'] + 0.3, T['crush']), lambda f: GAS, dim * wave(1) * tw, sizef=lambda f: 1.4)
    flows['disch'].update(ph, g_disch, ss(tb, T['crush'] + 0.2, T['hot']), lambda f: HOT, dim * wave(2) * tw, sizef=lambda f: 1.3)
    flows['cond'].update(ph, g_cond, ss(tb, T['snake'] + 0.5, T['pours']), colf_cond, dim * wave(3) * tw, sizef=lambda f: 1.4 - 0.6 * ss(f, 0.45, 0.9))
    flows['capil'].update(ph, g_capil, ss(tb, T['cap'] - 0.6, T['cap']), colf_capil(tb), dim * wave(4) * tw)
    bv = win(tb, T['boiling'] - 0.2, T['gas'] + 0.3, 0.3, 0.3) + win(tb, T['drops'], T['round'] + 0.5, 0.3, 0.3)
    bubbles.update(ph * 1.6 + t * 0.05, g_evap, min(bv, 1.0), lambda f: (0.92, 0.97, 1.0), 1.0, jitter=0.006)

    # --- heat orbs (orange = heat)
    orbs.reset()
    HEAT = (1.0, 0.42, 0.05)
    food = [V((-0.12, -0.02, 1.02)), V((0.12, 0.0, 0.96)), V((0.14, 0.0, 0.2)), V((0.27, 0.0, 0.2)), V((-0.2, 0.0, 0.22))]
    if T['twod'] - 0.4 < tb < T['puddle'] + 0.6:     # melt water drips off the tray
        for k in range(10):
            t0 = T['twod'] - 0.4 + k * 0.25; u = (tb - t0) / 0.45
            if 0 <= u <= 1:
                x = (-0.2, 0.2, -0.12, 0.15, 0.0)[k % 5]
                orbs.put(V((x, -0.1, 1.21 - (1.21 - Z0 - TH - 0.02) * u * u)), 0.011, (0.25, 0.55, 1.0))
    if T['cant'] - 0.5 < tb < T['only'] + 0.2:     # heat seeps in from the kitchen, through the walls, into the food
        for k in range(16):
            t0 = T['cant'] - 0.5 + k * 0.1; u = (tb - t0) / 1.3
            if 0 <= u <= 1:
                rs = random.Random(300 + k); side = -1 if k % 2 else 1
                s0 = V((0.25 + side * rs.uniform(0.75, 1.0), -0.15, rs.uniform(0.4, 1.6))); e0 = food[k % 5]
                orbs.put(s0.lerp(e0, ss(u, 0, 1)), 0.03 * math.sin(u * math.pi) ** 0.4, HEAT)
    if T['only'] - 0.2 < tb < T['swap'] + 0.6:       # ...and the only way to cool is to carry it back out
        for k in range(16):
            t0 = T['only'] - 0.2 + k * 0.09; u = (tb - t0) / 1.2
            if 0 <= u <= 1:
                rs = random.Random(400 + k); s0 = food[k % 5]; e0 = V((rs.uniform(0.9, 1.3), -0.2, rs.uniform(1.5, 2.0)))
                mid = V((0.42, -0.05, 1.3))
                p = s0.lerp(mid, ss(u, 0, 0.5)) if u < 0.5 else mid.lerp(e0, ss(u, 0.5, 1))
                orbs.put(p, 0.03 * math.sin(u * math.pi) ** 0.4, HEAT)
    if T['boiling'] - 0.3 < tb < T['evap'] + 1.0:   # the pipe drinks the warmth out of the food
        for k in range(18):
            t0 = T['boiling'] - 0.3 + k * 0.25; u = (tb - t0) / 1.1
            if 0 <= u <= 1:
                tgt = evap_p.atf(0.15 + 0.8 * ((k * 0.37) % 1)); tgt = V((tgt.x, -0.01, tgt.z)); s0 = food[k % 5]
                p = s0.lerp(tgt, ss(u, 0, 1)) + V((0.03 * math.sin(k * 3 + u * 6), 0, 0.04 * math.sin(u * math.pi)))
                orbs.put(p, 0.025 * math.sin(u * math.pi) ** 0.5, HEAT)
    if T['pours'] - 0.4 < tb < T['cools'] + 0.4:     # heat pours off the condenser into the kitchen
        for k in range(18):
            t0 = T['pours'] - 0.4 + k * 0.28; u = (tb - t0) / 1.6
            if 0 <= u <= 1:
                s0 = cond_p.atf(0.08 + 0.8 * ((k * 0.41) % 1)); p = V((s0.x, -0.03, s0.z)) + V((0.5 * u, -0.1 * u, 0.25 * u))
                orbs.put(p, 0.017 * math.sin(u * math.pi) ** 0.5, HEAT)
    if tb > T['never'] - 0.3:                        # finished fridge: heat streams from the milk, round the loop, into the kitchen
        op = orb_path(); lead = 1.0 if OPEN else ss(tb, T['never'] - 0.3, T['never'] + 0.4)
        for k in range(9):
            u = (t * 0.42 + k / 9) % 1
            orbs.put(op.atf(u), (0.03 if k == 0 else 0.021) * lead * math.sin(u * math.pi) ** 0.3, HEAT)

    # --- wisps
    wisps.reset()
    def puff(t0, life, p0, vel, r0, r1, col, a=0.55, seed=0, spread=0.03, clock=None):
        u = ((tb if clock is None else clock) - t0) / life
        if 0 <= u <= 1:
            rs = random.Random(seed)
            off = V((rs.uniform(-spread, spread), rs.uniform(-0.02, 0.02), rs.uniform(-spread, spread)))
            wisps.put(V(p0) + off + V(vel) * u, r0 + (r1 - r0) * u, col, a * math.sin(u * math.pi))
    for j in range(5): puff(T['yog'] - 0.1 + j * 0.2, 1.3, (-0.12, -0.08, 1.2), (0.035 * (j - 2), -0.05, 0.3), 0.03, 0.11, (0.55, 0.8, 0.1), 0.9, j)
    for j in range(8): puff(T['gas'] + j * 0.3, 1.6, (0.42, 0.0, 1.30), (0.12, 0, 0.3), 0.02, 0.09, (0.8, 0.92, 1.0), 0.6, 10 + j)
    if T['hot'] - 0.2 < tb < T['cools'] + 1.5:      # heat shimmer off the red-hot pipe
        for j in range(int((min(tb, T['cools']) - T['hot']) / 0.25) + 2):
            t0 = T['hot'] + j * 0.25
            if t0 > tb or tb - t0 > 1.6: continue
            src = (0.755, -0.02, 0.22 + 0.12 * (j % 3)) if t0 < T['snake'] + 0.5 else (0.62 + 0.08 * math.sin(j), -0.02, 0.8 + 0.25 * (j % 4))
            puff(t0, 1.6, src, (0.05, 0, 0.35), 0.012, 0.035, (1.0, 0.5, 0.15), 0.25, 30 + j, 0.02)
    for j in range(10): puff(T['drops'] + j * 0.07, 0.8, (0.40, 0.0, 1.60), (-0.38, 0, -0.02), 0.008, 0.04, (0.55, 0.82, 1.0), 0.85, 90 + j, 0.006)
    if lg > 0.3:                                      # glints on the glass lettuce
        for j in range(6):
            puff(T['lettuce'] + 0.2 + j * 0.18, 0.5, (0.27 + 0.05 * math.cos(j * 2.1), -0.01, 0.19 + 0.05 * math.sin(j * 1.7)),
                 (0, 0, 0), 0.004, 0.012, (1.0, 1.0, 1.0), 1.0, 120 + j, 0.0)
    # hum rings while the pump runs at night, until it stops
    for i, rg in enumerate(rings):
        rg.hide_render = True
        if on and T['click'] - 0.6 < tb < T['stop']:
            u = ((t * 1.6) + i / 3) % 1
            rg.hide_render = False; rr = 0.12 + 0.18 * u; rg.scale = (rr, rr, rr); rg.color = (0.8, 0.9, 1.0, 0.5 * (1 - u))

# ---------------------------------------------------------------- anchors for the overlay (with on-screen flag)
ANCH = dict(evap=V((0.0, Y, 1.62)), comp=V((CX, Y, 0.30)), cond=V((0.62, Y, 1.10)), capil=V((0.475, Y, 1.05)),
            thermo=V((0.25, 0.27, 1.12)), pipe=V((-0.15, Y, 1.66)), lett=V((0.27, 0.06, 0.3)),
            heat=V((-0.55, -0.15, 1.3)), gas=V((0.45, 0.0, 1.42)), liq=V((0.6, Y, 0.56)), warmc=V((0.62, Y, 1.35)), spag=V((0.515, -0.02, 0.98)))
def anchors():
    out = []; W, H = sc.render.resolution_x, sc.render.resolution_y
    for f in range(NF):
        t = f / FPS; state(t); bpy.context.view_layer.update()
        row = {'t': round(t, 3), 'temp': round(temp(t), 1), 'on': int(comp_on(t, t)), 'flow': round(flow_speed(t), 3)}
        for k, v in ANCH.items():
            p = world_to_camera_view(sc, cam, v)
            row[k] = (round(p.x * W, 1), round((1 - p.y) * H, 1), int(0.03 < p.x < 0.97 and 0.03 < p.y < 0.97 and p.z > 0))
        out.append(row)
    json.dump(dict(fps=FPS, w=W, h=H, T=T, swap=SWAP, swap_d=SWAP_D, frames=out), open(os.path.join(OUT, 'anchors.json'), 'w'))

# ---------------------------------------------------------------- run
def render_frame(f, path):
    t = f / FPS; sc.frame_set(f); state(t); sc.cycles.seed = f
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
if '--anchors' in argv:
    anchors()
if '--stills' in argv:
    for s in arg('--stills').split(','):
        f = int(round(float(s) * FPS)); render_frame(f, os.path.join(OUT, f'still_{float(s):06.2f}{"o" if OPEN else ""}.png'))
if '--frames' in argv:
    a, b = arg('--frames').split(':'); a = int(a); b = min(int(b), NF)
    if OPEN: b = min(b, int(math.ceil((SWAP + SWAP_D) * FPS)) + 1)
    sub = 'open' if OPEN else 'frames'
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for f in range(a, b):
        p = os.path.join(OUT, sub, f'f_{f:05d}.png')
        if not os.path.exists(p): render_frame(f, p)
print('NF', NF, 'DONE')
