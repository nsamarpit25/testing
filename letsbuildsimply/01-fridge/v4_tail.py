
# ================================================================ v4 additions: a real kitchen around the box + new props
M.update(
    cab=mat('cab', (0.9, 0.88, 0.82), 0.45), cabdoor=mat('cabdoor', (0.86, 0.84, 0.78), 0.35, coat=0.3),
    stone=mat('stone', (0.16, 0.17, 0.19), 0.25, coat=0.5), knob=mat('knob', (0.7, 0.7, 0.72), 0.2, metal=1.0),
    sky=mat('sky', (0.6, 0.8, 1.0), 0.5, emit=(0.6, 0.82, 1.0), estr=2.5), pot=mat('pot', (0.75, 0.42, 0.28), 0.6),
    plant=mat('plant', (0.18, 0.5, 0.2), 0.6), kettle=mat('kettle', (0.85, 0.2, 0.15), 0.2, coat=0.8),
    panelm=mat('panelm', (0.92, 0.93, 0.94), 0.3), piston=mat('piston', (0.6, 0.62, 0.65), 0.25, metal=1.0),
    dropm=mat('dropm', (0.7, 0.88, 1.0), 0.02, trans=1.0, ior=1.33),
)
box('ctr_l', -1.95, -0.62, 0.02, 0.6, 0.0, 0.86, M['cab'], bev=0.006)
box('ctop_l', -2.0, -0.58, -0.03, 0.62, 0.86, 0.9, M['stone'], bev=0.004)
for i, (a, b) in enumerate(((-1.92, -1.29), (-1.27, -0.65))):
    box(f'cdoor{i}', a, b, -0.005, 0.02, 0.06, 0.82, M['cabdoor'], bev=0.008)
    box(f'cknob{i}', b - 0.06, b - 0.04, -0.02, -0.005, 0.66, 0.74, M['knob'], bev=0.004)
box('ctr_r', 1.02, 2.4, 0.02, 0.6, 0.0, 0.86, M['cab'], bev=0.006)
box('ctop_r', 0.98, 2.45, -0.03, 0.62, 0.86, 0.9, M['stone'], bev=0.004)
box('cdoor_r', 1.05, 1.68, -0.005, 0.02, 0.06, 0.82, M['cabdoor'], bev=0.008)
box('up_l', -1.95, -0.7, 0.3, 0.6, 1.62, 2.3, M['cab'], bev=0.006)
box('up_r', 1.08, 2.4, 0.3, 0.6, 1.62, 2.3, M['cab'], bev=0.006)
box('win_frame', -1.62, -0.9, 0.585, 0.6, 1.0, 1.52, M['white'], bev=0.006)
box('win_sky', -1.58, -0.94, 0.6, 0.605, 1.04, 1.48, M['sky'], bev=0)
box('win_bar', -1.27, -1.25, 0.58, 0.585, 1.04, 1.48, M['white'], bev=0)
kettle = smooth(prim('cylinder', 'kettle', (-1.05, 0.3, 0.98), M['kettle'], radius=0.08, depth=0.16, vertices=40))
smooth(prim('uv_sphere', 'kettle_top', (-1.05, 0.3, 1.06), M['kettle'], radius=0.08, segments=32, ring_count=16)).scale.z = 0.45
smooth(prim('cylinder', 'pot', (1.35, 0.3, 0.97), M['pot'], radius=0.075, depth=0.14, vertices=32))
smooth(prim('ico_sphere', 'plant', (1.35, 0.3, 1.12), M['plant'], radius=0.12, subdivisions=3), 1)

drop = smooth(prim('uv_sphere', 'drop', (0.08, -0.12, 0.925), M['dropm'], radius=0.03, segments=32, ring_count=16))
DROP_C = Vector((0.08, -0.12, 0.925))
frost_ring = smooth(prim('torus', 'frostring', (0.08, -0.12, 0.914), M['frost'], major_radius=0.034, minor_radius=0.005))
ice_shards = [box(f'ishard{i}', -0.02, 0.02, -0.02, 0.02, -0.02, 0.02, M['ice'], bev=0.004) for i in range(9)]
glass_shards = [box(f'gshard{i}', -0.008, 0.008, -0.002, 0.002, -0.012, 0.012, M['glass'], bev=0) for i in range(7)]
piston = smooth(prim('cylinder', 'piston', (CX, Y, 0.16), M['piston'], radius=0.05, depth=0.05, vertices=32))
rod = prim('cylinder', 'rod', (CX, Y, 0.11), M['piston'], radius=0.012, depth=0.08, vertices=12)
panel = box('sidepanel', 0.505, 0.79, -0.035, -0.01, 0.0, 1.22, M['panelm'], bev=0.006)
panel.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.61)))
spagA = tube('spagA', [Vector((0, 0, 0)), Vector((0, 0, 0.2))], 0.0085, M['spag'], y=0.0)[0]
spagB = tube('spagB', [Vector((0, 0, 0)), Vector((0, 0, -0.2))], 0.0085, M['spag'], y=0.0)[0]
ice2 = box('ice2', -0.15, 0.15, -0.12, 0.2, 0, 0.3, M['ice'], bev=0.025)
ice2.data.transform(__import__('mathutils').Matrix.Translation((0, 0, 0.15)))
for o in (door, drain_o, dtray, dwater, heater_o, frost_o, spag): o.hide_render = True
cam_d.clip_start = 0.004

# ================================================================ per-frame state
def flow_speed(t):
    if T['stop'] < t < T['twist'] - 0.2: return 0.0           # the hum stops at night
    boost = 1.0 + 1.3 * win(t, T['never'], T['cuts'], 0.4, 0.4)
    return 0.22 * boost
PHASE = [0.0]
for f in range(1, NF + 2): PHASE.append(PHASE[-1] + flow_speed(f / FPS) / FPS)
def comp_on(t): return t >= T['pump'] and flow_speed(t) > 0.05

def temp(t):
    return sched(t, [(0.0, 21), (0.6, 21), (3.0, 5), (T['tomorrow'], 5), (T['sour'], 24), (T['pipe0'], 24), (T['boils'], 22),
                     (T['evap'] + 0.3, 8), (T['gas'], 8), (T['escapes'] + 1.0, 15), (T['spray'], 15), (T['cold'] + 0.4, 4),
                     (T['never'] + 0.4, 4), (T['solid'] + 0.3, -12), (T['cuts'], -12), (T['thermo'] + 0.4, 3.5), (END + 2, 3.5)])

def ice_z(t):  # the opening plunge: block falls from high above into the box
    u = clamp(t / 0.6); return ICE_Z + 1.9 * (1 - u * u)
ORB_PIECES = None
def orb_path():
    global ORB_PIECES
    if ORB_PIECES is None:
        pts = [Vector((-0.12, -0.02, 1.02)), evap_p.atf(0.75), evap_p.atf(1.0)] + [suct_p.atf(k / 6) for k in range(7)] + \
              [disch_p.atf(k / 8) for k in range(9)] + [cond_p.atf(k / 12) for k in range(4)] + [Vector((0.95, -0.1, 1.45)), Vector((1.25, -0.3, 1.75))]
        ORB_PIECES = Path(fillet([(p.x, -0.02, p.z) for p in pts], r=0.04, seg=4))
    return ORB_PIECES

# ---------------------------------------------------------------- camera: shots blended in sequence
V = Vector
BASE = (V((-0.22, -3.0, 1.22)), V((0.2, 0.1, 0.93)), 46)
WIDE = (V((-0.35, -3.55, 1.25)), V((0.2, 0.1, 0.96)), 44)
def stat(p, tg, lens): return lambda t: (V(p), V(tg), lens)
def mv(p0, p1, g0, g1, l0, l1, a, b, ease=True):
    def f(t):
        k = ss(t, a, b) if ease else lin(t, a, b)
        return (V(p0).lerp(V(p1), k), V(g0).lerp(V(g1), k), l0 + (l1 - l0) * k)
    return f
def shot_plunge(t):
    z = max(ice_z(t) + 0.9, 2.78)
    return (V((0.0, -0.06, z)), V((0.0, 0.03, 0.0)), 24)
def shot_drop_orbit(t):
    a = math.radians(-28 + 60 * ss(t, T['evapw'], T['pipe0'] - 0.2)); r = 0.32
    return (DROP_C + V((r * math.sin(a), -r * math.cos(a), 0.07)), DROP_C, 58)
def shot_tip(t):
    g = max(ss(t, T['pipe0'] - 0.1, T['pipe0'] + 2.4), 0.04); tip = evap_p.atf(g)
    return (tip + V((0.06, -0.62, 0.12)), tip + V((0, 0, -0.03)), 36)
def shot_gas(t):
    k = lin(t, T['gas'], T['gas'] + 2.5)
    return (V((0.36, -1.3, 1.42 + 0.22 * k)), V((0.6, 0.0, 1.38 + 0.3 * k)), 42)
def shot_capride(t):
    a, b = T['cap'] - 0.5, T['spray'] + 0.9
    d = capil_p.L * (0.04 + 0.96 * ss(t, a, b) ** 0.9)
    p = capil_p.at(d); q = capil_p.at(min(d + 0.25, capil_p.L)) if d < capil_p.L - 0.02 else evap_p.atf(0.08)
    off = V((0.0, -0.05, 0.0))
    return (p + off, q + off * 0.6, 17)
def shot_orb(t):
    u = ss(t, T['twist'] + 0.1, T['kitchen'] + 0.7); p = orb_path().atf(u)
    return (p + V((-0.1, -0.48, 0.1)), p, 36)
def shot_hero(t):
    a = math.radians(-14 + 22 * lin(t, T['wrap'], T['just']))
    p, g, l = WIDE; r = (p - g).length
    return (g + V((r * math.sin(a), -r * math.cos(a), p.z - g.z)), g, l)
def shot_end(t):
    k = ss(t, T['just'] - 0.05, T['just'] + 0.5)
    return (V((0.0, -0.06, 2.95 + 0.2 * k)), V((0.0, 0.03, 0.0)), 24)
MILK_CU = stat((-0.05, -0.62, 1.12), (-0.12, 0.02, 1.06), 46)
SHOTS = [
    (0.0, 0.0, shot_plunge),
    (T['lid'] + 0.12, 0.65, stat(*BASE)),
    (T['tomorrow'], 1.2, mv((-0.45, -2.9, 1.3), (0.15, -2.2, 1.12), (0.2, 0.1, 0.93), (-0.05, 0.1, 1.0), 46, 46, T['tomorrow'], T['sour'] - 0.3)),
    (T['sour'] - 0.22, 0.2, MILK_CU),
    (T['need'], 0.3, stat(*BASE)),
    (T['shower'] - 0.15, 0.6, stat((0.08, -0.45, 1.06), DROP_C, 56)),
    (T['evapw'], 0.45, shot_drop_orbit),
    (T['pipe0'] - 0.25, 0.5, shot_tip),
    (T['boils'] - 0.1, 0.7, mv((0.0, -1.95, 1.22), (0.02, -1.3, 1.38), (-0.05, 0.1, 1.12), (0.0, 0.1, 1.36), 45, 45, T['boils'], T['evap'] + 0.5)),
    (T['gas'] - 0.15, 0.25, shot_gas),
    (T['seal'] - 0.1, 0.28, mv((0.55, -1.3, 0.45), (0.6, -0.68, 0.3), (0.58, 0.1, 0.22), (0.6, 0.1, 0.18), 42, 42, T['comp'] - 0.3, T['comp'] + 0.4)),
    (T['hot'] - 0.1, 0.35, stat((0.74, -0.52, 0.34), (0.7, 0.1, 0.27), 40)),
    (T['snake'] - 0.1, 0.8, mv((1.25, -1.45, 0.6), (1.12, -1.45, 1.5), (0.62, 0.1, 0.6), (0.62, 0.1, 1.38), 40, 40, T['snake'], T['cond'] + 0.4)),
    (T['sides'] - 0.1, 0.8, mv((1.02, -1.6, 1.15), (0.86, -1.15, 1.08), (0.64, 0.0, 1.05), (0.64, 0.0, 1.02), 42, 42, T['sides'], T['leaves'])),
    (T['leaves'] - 0.05, 0.6, mv((0.7, -0.64, 1.25), (0.6, -0.58, 0.56), (0.6, 0.1, 1.2), (0.5, 0.1, 0.48), 45, 45, T['leaves'], T['tight'] + 0.4)),
    (T['force'] - 0.1, 0.5, stat((0.3, -0.78, 0.94), (0.46, 0.05, 0.9), 44)),
    (T['cap'] - 0.55, 0.4, shot_capride),
    (T['drops'] + 0.35, 1.0, mv((0.15, -1.1, 1.5), WIDE[0], (0.25, 0.1, 1.45), WIDE[1], 30, 44, T['drops'] + 0.35, T['never'] - 0.1)),
    (T['solid'] - 0.45, 0.22, MILK_CU),
    (T['sensor'] - 0.1, 0.5, stat((0.18, -0.55, 1.12), (0.25, 0.27, 1.08), 44)),
    (T['hum'] - 0.25, 0.8, stat(*BASE)),
    (T['twist'] - 0.25, 0.5, shot_orb),
    (T['wrap'] - 0.1, 0.9, shot_hero),
    (T['just'] - 0.1, 0.45, shot_end),
]
IMPACTS = [(0.6, 0.012), (T['lid'], 0.02), (T['pump'], 0.018), (T['cracks'], 0.006), (T['steel'], 0.01), (T['twist'] - 0.2, 0.0)]
def cam_state(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    p, g, l = SHOTS[i][2](t)
    if i > 0 and SHOTS[i][1] > 0 and t < SHOTS[i][0] + SHOTS[i][1]:
        k = ss(t, SHOTS[i][0], SHOTS[i][0] + SHOTS[i][1]); p0, g0, l0 = SHOTS[i - 1][2](t)
        p, g, l = p0.lerp(p, k), g0.lerp(g, k), l0 + (l - l0) * k
    sh = V((0, 0, 0))
    for t0, a in IMPACTS:
        if t0 <= t < t0 + 0.6:
            e = a * math.exp(-(t - t0) * 9)
            sh += V((e * math.sin(t * 71), 0, e * math.sin(t * 53 + 1)))
    if T['stop'] - 0.05 < t < T['stop'] + 0.15: pass
    return p + sh, g + sh * 0.5, l
def apply_cam(t):
    p, g, l = cam_state(t)
    cam.location = p; d = g - p
    up = 'Y' if abs(d.normalized().z) > 0.97 else 'Y'
    cam.rotation_euler = d.to_track_quat('-Z', up).to_euler(); cam_d.lens = l

def state(t):
    f_idx = int(round(t * FPS))
    apply_cam(t)
    # --- lights: day/night cycle overnight, night for the hum beat
    night = win(t, T['night'] - 0.3, T['twist'] - 0.1, 0.4, 0.4)
    cyc = 0.5 + 0.5 * math.cos(2 * math.pi * 2 * ss(t, T['tomorrow'], T['puddle'] + 0.6)) if T['tomorrow'] < t < T['puddle'] + 0.6 else 1.0
    dimf = (0.35 + 0.65 * cyc) * (1 - 0.65 * night)
    blue = mix((1.0, 0.93, 0.84), (0.55, 0.65, 1.0), max(night, 1 - cyc))
    key.data.energy = KEYP * dimf; key.data.color = blue
    fill.data.energy = FILLP * (1 - 0.5 * night); top.data.energy = TOPP * dimf
    bg.inputs['Strength'].default_value = WORLDS * (1 - 0.6 * night) * (0.5 + 0.5 * cyc)
    sk = mix((0.6, 0.82, 1.0), (0.05, 0.08, 0.25), max(night, 1 - cyc))
    pset(P(M['sky']), color=sk, emit=sk, estr=2.5 * (1 - 0.6 * max(night, 1 - cyc)))
    pset(P(M['wall']), color=(0.22, 0.45, 0.47))

    # --- opening: ice plunge, shards, lid slam
    lid.rotation_euler.y = -math.radians(108) * (1 - ss(t, T['lid'] - 0.16, T['lid'] + 0.02))
    if t < T['tomorrow']:
        ice.location = (0, 0.04, ice_z(t)); ice.scale = (1, 1, 1); ice.hide_render = False
    else:
        m = ss(t, T['tomorrow'], T['puddle'] + 0.5)
        ice.location = (0, 0.04, ICE_Z); ice.scale = (1 - 0.75 * m, 1 - 0.75 * m, max(0.001, 1 - m)); ice.hide_render = m > 0.995
    for i, sh in enumerate(ice_shards):
        u = t - 0.6
        if 0 <= u <= 0.8:
            rs = random.Random(i); vx, vy, vz = rs.uniform(-0.7, 0.7), rs.uniform(-0.5, 0.2), rs.uniform(1.2, 2.2)
            sh.hide_render = False; sh.location = (vx * u, 0.04 + vy * u, ICE_Z + 0.3 + vz * u - 4.9 * u * u)
            sh.rotation_euler = (u * 9 * vx, u * 7, u * 5 * vy); sh.scale = (max(0.001, 1 - u / 0.8),) * 3
        else:
            sh.hide_render = True
    icetray.hide_render = t > T['pipe0'] - 0.1
    pud = ss(t, T['tomorrow'] + 0.4, T['puddle'] + 0.6) * (1 - ss(t, T['need'] - 0.2, T['need'] + 0.4))
    puddle.scale = (0.2 + 0.9 * pud, 0.5 + 0.5 * pud, 1); puddle.hide_render = pud < 0.02
    spin = ss(t, T['tomorrow'], T['puddle'] + 0.6)
    hands[0].rotation_euler.y = math.radians(60) + spin * 2 * math.pi * 2
    hands[1].rotation_euler.y = math.radians(-30) + spin * 2 * math.pi * 24
    for e in extra_ice: e.hide_render = True

    # --- milk: sours (cap pops at the lens), new bottle, freezes + cracks, thaws
    spoil = ss(t, T['sour'] - 0.5, T['sour'] + 0.15) * (1 - ss(t, T['need'] + 0.05, T['need'] + 0.3))
    froz = ss(t, T['solid'] - 0.35, T['solid'] + 0.2) * (1 - ss(t, T['thermo'], T['thermo'] + 1.0))
    mc = mix((0.97, 0.97, 0.95), (0.5, 0.58, 0.06), spoil); mc = mix(mc, (0.45, 0.75, 1.0), froz)
    pset(P(M['milk']), color=mc, rough=0.35 + 0.5 * froz)
    milk_o.modifiers['lumps'].strength = 0.03 * spoil; milk_o.scale.z = 1 + 0.3 * froz
    reset = pop(t, T['need'] + 0.2, 0.4) if t > T['need'] else 1.0
    for o in (bottle_o, milk_o): o.scale.x = o.scale.y = max(0.001, reset)
    bottle_o.scale.z = max(0.001, reset)
    cap_rest = V((-0.12, 0.02, 0.912 + 0.255))
    if T['sour'] - 0.05 < t < T['need'] + 0.2:   # flies at the camera
        u = clamp((t - T['sour'] + 0.05) / 0.45)
        cap_o.location = cap_rest.lerp(V((-0.07, -0.5, 1.13)), u * u) + V((0, 0, 0.06 * math.sin(u * math.pi)))
        cap_o.rotation_euler = (u * 7, u * 3, 0); cap_o.hide_render = u >= 1
    else:
        lift = 0.06 * froz
        cap_o.location = cap_rest + V((0, 0, lift)); cap_o.rotation_euler = (0.3 * froz, 0, 0); cap_o.hide_render = False
        cap_o.scale = (max(reset, 0.001),) * 3
    pset(P(M['glass']), rough=0.04 + 0.5 * froz, alpha=0.18 + 0.6 * froz, color=mix((0.95, 0.98, 1.0), (0.85, 0.93, 1.0), froz))
    for i, gs in enumerate(glass_shards):
        u = t - T['cracks']
        if 0 <= u <= 0.7:
            rs = random.Random(50 + i); a = rs.uniform(0, 2 * math.pi)
            gs.hide_render = False
            gs.location = (-0.12 + 0.05 * math.cos(a) + 0.25 * math.cos(a) * u, 0.02 + 0.05 * math.sin(a) - 0.25 * abs(math.sin(a)) * u,
                           1.0 + 0.6 * u - 3.0 * u * u)
            gs.rotation_euler = (u * 8, u * 6 * i, 0); gs.scale = (max(0.001, 1 - u / 0.7),) * 3
        else:
            gs.hide_render = True

    # --- thermometer
    tc = temp(t); tliq.scale.z = temp_h(tc)
    pset(P(M['red']), color=mix((0.85, 0.08, 0.06), (0.2, 0.45, 1.0), clamp((8 - tc) / 20)))

    # --- the shower droplet
    dp = pop(t, T['shower'] - 0.3, 0.35) if t < T['pipe0'] else 0.0
    ev = ss(t, T['evapw'] + 0.3, T['steal'] + 0.7)
    drop.scale = (max(0.001, dp * (1 - 0.95 * ev)),) * 2 + (max(0.001, 0.45 * dp * (1 - 0.95 * ev)),)
    drop.hide_render = dp * (1 - ev) < 0.03
    fr_ = ss(t, T['steal'], T['steal'] + 0.6) * (1 - ss(t, T['pipe0'] + 0.3, T['pipe0'] + 0.8))
    frost_ring.scale = (max(fr_, 0.001),) * 3; frost_ring.hide_render = fr_ < 0.02

    # --- pipes growing
    g_evap = ss(t, T['pipe0'] - 0.1, T['pipe0'] + 2.4)
    g_suct = ss(t, T['seal'] - 0.1, T['seal'] + 0.8)
    g_disch = 0.12 * ss(t, T['hot'] - 0.2, T['hot'] + 0.3) + 0.88 * ss(t, T['snake'] - 0.1, T['snake'] + 0.6)
    g_cond = ss(t, T['snake'] + 0.3, T['escapes2'] + 0.4)
    g_capil = ss(t, T['force'] + 0.1, T['spaghetti'] + 0.2)
    for o, g in ((evap_o, g_evap), (suct_o, g_suct), (disch_o, g_disch), (cond_o, g_cond), (capil_o, g_capil)):
        o.data.bevel_factor_end = max(g, 0.0005); o.hide_render = g < 0.002
    for i, fo in enumerate(fins):
        g = ss(t, T['snake'] + 0.3 + i * 0.08, T['escapes2'] + 0.4 + i * 0.08); fo.data.bevel_factor_end = max(g, 0.0005); fo.hide_render = g < 0.002
    stub_s = ss(t, T['liquid'] - 0.2, T['liquid'] + 0.2) * (1 - ss(t, T['force'] + 0.4, T['force'] + 0.7))
    bulge = 1 + 0.5 * win(t, T['tight'] - 0.5, T['force'] + 0.2, 0.3, 0.2) * (0.5 + 0.5 * math.sin(t * 22))
    stub.scale = (max(stub_s * bulge, 0.001),) * 3; stub.hide_render = stub_s < 0.01
    # spaghetti for scale: appears, then snaps
    sg = win(t, T['spaghetti'] - 0.15, T['cap'] - 0.2, 0.2, 0.25); snap = ss(t, T['spaghetti'] + 0.45, T['spaghetti'] + 0.7)
    for o, sgn in ((spagA, 1), (spagB, -1)):
        o.hide_render = sg < 0.02; o.data.bevel_factor_end = max(sg, 0.0005)
        o.location = (0.40 + 0.02 * sgn * snap, 0.0, 0.82 - 0.05 * snap); o.rotation_euler = (0, sgn * 0.5 * snap, 0)

    # --- side panel slides over the condenser ("hiding in the walls")
    pn = ss(t, T['sides'] + 0.4, T['hiding'] + 0.2) * (1 - ss(t, T['leaves'] - 0.3, T['leaves'] + 0.2))
    panel.hide_render = pn < 0.01; panel.location = (0, 0, 0.47 + 1.3 * (1 - pn))
    pset(P(M['panelm']), emit=(1.0, 0.42, 0.08), estr=0.9 * pn * (0.75 + 0.25 * math.sin(t * 5)))

    # --- compressor drop, x-ray piston, shudder
    cd = clamp((t - (T['pump'] - 0.45)) / 0.45)
    drop_ = 0.0 if t >= T['pump'] else (1.5 * (1 - cd * cd) if t > T['pump'] - 0.45 else 9)
    sq = 1 - 0.12 * math.sin(clamp((t - T['pump']) / 0.25) * math.pi) * (t > T['pump'])
    shake = 0.0025 * math.sin(t * 95) if comp_on(t) else 0.0
    for o in comp_parts:
        r = COMP_REST[o.name]; o.location = (r.x + shake, r.y, r.z + drop_ + (sq - 1) * 0.05); o.hide_render = drop_ > 5
    dome.scale = (1, 1, 0.62 * sq)
    xr = win(t, T['comp'] - 0.2, T['scorch'] + 0.6, 0.3, 0.4)
    pset(P(M['comp']), alpha=1 - 0.78 * xr)
    pz = 0.17 + 0.025 * math.sin(t * 2 * math.pi * 3) if comp_on(t) else 0.17
    piston.hide_render = rod.hide_render = xr < 0.02 or drop_ > 5
    piston.location = (CX + shake, Y, pz); rod.location = (CX + shake, Y, pz - 0.05)
    # glows
    hot = ss(t, T['hot'] - 0.1, T['scorch'] + 0.2)
    pset(P(M['piston']), emit=(1.0, 0.25, 0.04), estr=3.0 * hot * xr)
    pset(P(M['copper']), emit=(1.0, 0.3, 0.05), estr=0.0)
    pset(P(M['cond']), emit=(1.0, 0.35, 0.05), estr=0.6 * ss(t, T['snake'] + 0.5, T['escapes2']))
    def hl(m, at, base=0.0, col=(1.0, 0.85, 0.2)):
        k = win(t, at - 0.1, at + 0.9, 0.12, 0.4)
        if k > 0.001: pset(P(m), emit=col, estr=base + 2.5 * k)
    hl(M['copper'], T['evap']); hl(M['cond'], T['cond']); hl(M['capil'], T['cap']); hl(M['dialm'], T['thermo'])
    if not (T['thermo'] - 0.2 < t < T['thermo'] + 1.0): pset(P(M['dialm']), estr=0.0)
    if not (T['cap'] - 0.2 < t < T['cap'] + 1.0): pset(P(M['capil']), estr=0.0)

    # --- thermostat
    th = pop(t, T['sensor'], 0.35)
    for o in (dial, dptr): o.scale = (max(th, 0.001),) * 3; o.hide_render = th < 0.01
    dptr.rotation_euler.y = -math.radians(70) * ss(t, T['cuts'] - 0.2, T['cuts'] + 0.3)
    gw = ss(t, T['sensor'] + 0.1, T['cuts']); wire_o.data.bevel_factor_end = max(gw, 0.0005); wire_o.hide_render = gw < 0.002

    # --- wrap in foam and steel
    st = ss(t, T['wrap'] + 0.1, T['steel'] + 0.3)
    for m in (M['box'], M['cut']): set_steel(m, st)
    for fo in foam: fo.hide_render = st < 0.05; fo.scale = (1, 1, max(st, 0.01))
    pset(P(M['tbackm']), color=mix((0.95, 0.95, 0.95), (0.16, 0.18, 0.22), st))
    hs = pop(t, T['steel'], 0.35); handle.scale = (max(hs, 0.001),) * 3; handle.hide_render = hs < 0.01
    # the loop: a new block of ice drops onto the finished fridge
    u2 = clamp((t - T['just'] - 0.05) / 0.5)
    ice2.hide_render = t < T['just'] - 0.05; ice2.location = (0.0, 0.0, Z1 + 0.012 + 1.5 * (1 - u2 * u2))

    # --- refrigerant dots
    ph = PHASE[min(f_idx, len(PHASE) - 1)]
    fill_ = ss(t, T['filled'] - 0.1, T['filled'] + 1.0)
    leak = ss(t, T['gas'], T['escapes'] + 0.4) * (1 - ss(t, T['seal'], T['seal'] + 0.5))
    on_dim = 1.0 if flow_speed(t) > 0.01 or t < T['stop'] else 0.45
    wave0 = T['drops'] + 0.5
    def wave(k): return 1.0 + 1.2 * win(t, wave0 + 0.25 * k, wave0 + 0.25 * k + 0.7, 0.15, 0.4)
    tw = 1.0 + 0.6 * win(t, T['twist'], T['wrap'] + 0.4, 0.5, 0.5)
    flows['evap'].update(ph, g_evap * fill_, fill_ * (1 - 0.85 * leak), colf_evap(t) if t > T['boils'] - 0.3 else (lambda f: COLD), on_dim * wave(0) * tw)
    flows['suct'].update(ph, g_suct, ss(t, T['seal'] + 0.3, T['pump']), lambda f: GAS, on_dim * wave(1) * tw)
    flows['disch'].update(ph, g_disch, ss(t, T['pump'] + 0.2, T['hot']), lambda f: HOT, on_dim * wave(2) * tw)
    flows['cond'].update(ph, g_cond, ss(t, T['snake'] + 0.5, T['escapes2']), colf_cond, on_dim * wave(3) * tw)
    flows['capil'].update(ph, g_capil, ss(t, T['cap'] - 0.6, T['cap']), colf_capil(t), on_dim * wave(4) * tw)
    bv = win(t, T['boils'] - 0.2, T['gas'] + 0.3, 0.3, 0.3) + win(t, T['drops'], T['never'] + 0.5, 0.3, 0.3)
    bubbles.update(ph * 1.6 + t * 0.05, g_evap, min(bv, 1.0), lambda f: (0.92, 0.97, 1.0), 1.0, jitter=0.006)

    # --- heat orbs
    orbs.reset()
    milk_c = V((-0.12, -0.02, 1.02))
    if T['evapw'] - 0.1 < t < T['steal'] + 1.2:  # heat leaves the wood/skin through the evaporating drop
        for k in range(12):
            t0 = T['evapw'] - 0.1 + k * 0.25; u = (t - t0) / 1.0
            if 0 <= u <= 1:
                a = k * 2.4; s0 = DROP_C + V((0.09 * math.cos(a), 0.09 * math.sin(a) - 0.02, -0.012))
                p = s0.lerp(DROP_C, ss(u, 0, 0.5)) + V((0, 0, 0.18 * ss(u, 0.5, 1.0)))
                orbs.put(p, 0.008 * math.sin(u * math.pi) ** 0.5, (1.0, 0.42, 0.05))
    if T['heat'] - 0.4 < t < T['evap'] + 1.2:
        for k in range(14):
            t0 = T['heat'] - 0.4 + k * 0.17; u = (t - t0) / 1.1
            if 0 <= u <= 1:
                tgt = evap_p.atf(0.55 + 0.4 * ((k * 0.37) % 1)); tgt = V((tgt.x, -0.01, tgt.z))
                p = milk_c.lerp(tgt, ss(u, 0, 1)) + V((0.03 * math.sin(k * 3 + u * 6), 0, 0.04 * math.sin(u * math.pi)))
                orbs.put(p, 0.021 * math.sin(u * math.pi) ** 0.5, (1.0, 0.4, 0.04))
    if T['escapes2'] - 0.5 < t < T['sides'] + 1.0:  # heat radiates off the condenser into the room
        for k in range(16):
            t0 = T['escapes2'] - 0.5 + k * 0.28; u = (t - t0) / 1.6
            if 0 <= u <= 1:
                s0 = cond_p.atf(0.08 + 0.8 * ((k * 0.41) % 1)); p = V((s0.x, -0.03, s0.z)) + V((0.5 * u, -0.1 * u, 0.25 * u))
                orbs.put(p, 0.016 * math.sin(u * math.pi) ** 0.5, (1.0, 0.4, 0.04))
    if T['twist'] - 0.2 < t < T['wrap'] + 0.6:  # the twist: ONE big orb (camera rides it) + a few followers
        u = ss(t, T['twist'] + 0.1, T['kitchen'] + 0.7); op = orb_path()
        orbs.put(op.atf(u), 0.03, (1.0, 0.45, 0.05))
        for k in range(1, 6):
            uk = u - k * 0.06
            if 0 < uk < 1: orbs.put(op.atf(uk), 0.016, (1.0, 0.4, 0.04))
    if T['drips'] if False else False: pass

    # --- wisps
    wisps.reset()
    def puff(t0, life, p0, vel, r0, r1, col, a=0.55, seed=0, spread=0.03):
        u = (t - t0) / life
        if 0 <= u <= 1:
            rs = random.Random(seed)
            off = V((rs.uniform(-spread, spread), rs.uniform(-0.02, 0.02), rs.uniform(-spread, spread)))
            wisps.put(V(p0) + off + V(vel) * u, r0 + (r1 - r0) * u, col, a * math.sin(u * math.pi))
    for j in range(5): puff(T['sour'] - 0.1 + j * 0.2, 1.3, (-0.12, -0.08, 1.2), (0.035 * (j - 2), -0.05, 0.3), 0.03, 0.12, (0.35, 0.85, 0.05), 1.0, j)
    for j in range(6): puff(T['evapw'] + 0.4 + j * 0.35, 1.4, DROP_C, (0.0, 0.0, 0.22), 0.01, 0.05, (0.9, 0.95, 1.0), 0.6, 20 + j, 0.01)
    for j in range(8): puff(T['gas'] + j * 0.3, 1.6, (0.42, 0.0, 1.30), (0.12, 0, 0.3), 0.02, 0.09, (0.8, 0.92, 1.0), 0.6, 10 + j)
    if t > T['hot'] - 0.2:
        for j in range(int((min(t, END) - T['hot']) / 0.3) + 2):
            t0 = T['hot'] + j * 0.3
            if t0 > t or t - t0 > 1.8: continue
            src = (0.755, -0.02, 0.3 + 0.12 * (j % 3)) if t0 < T['snake'] + 0.5 else (0.62 + 0.08 * math.sin(j), -0.02, 0.8 + 0.25 * (j % 4))
            puff(t0, 1.8, src, (0.06, 0, 0.35), 0.015, 0.06, (1.0, 0.5, 0.15), 0.35, 30 + j, 0.02)
    for j in range(8): puff(T['drops'] + j * 0.08, 0.8, (0.32, 0.0, 1.60), (-0.35, 0, 0.0), 0.008, 0.035, (0.45, 0.78, 1.0), 0.85, 90 + j, 0.006)
    # hum rings, only until the hum stops
    for i, rg in enumerate(rings):
        rg.hide_render = True
        if comp_on(t) and T['hum'] - 0.6 < t < T['stop']:
            u = ((t * 1.6) + i / 3) % 1
            rg.hide_render = False; rr = 0.12 + 0.18 * u; rg.scale = (rr, rr, rr); rg.color = (0.8, 0.9, 1.0, 0.5 * (1 - u))

# ---------------------------------------------------------------- anchors for the overlay (with on-screen flag)
ANCH = dict(evap=V((0.0, Y, 1.62)), comp=V((CX, Y, 0.30)), cond=V((0.62, Y, 1.10)), capil=V((0.475, Y, 1.05)),
            thermo=V((0.25, 0.27, 1.12)), therm=V((TH_X, 0.27, TH_Z0 + TH_H + 0.03)), milk=V((-0.12, 0.02, 1.2)))
def anchors():
    out = []; W, H = sc.render.resolution_x, sc.render.resolution_y
    for f in range(NF):
        t = f / FPS; state(t); bpy.context.view_layer.update()
        row = {'t': round(t, 3), 'temp': round(temp(t), 1), 'on': int(comp_on(t)), 'flow': round(flow_speed(t), 3)}
        for k, v in ANCH.items():
            p = world_to_camera_view(sc, cam, v)
            row[k] = (round(p.x * W, 1), round((1 - p.y) * H, 1), int(0.03 < p.x < 0.97 and 0.03 < p.y < 0.97 and p.z > 0))
        out.append(row)
    json.dump(dict(fps=FPS, w=W, h=H, T=T, frames=out), open(os.path.join(OUT, 'anchors.json'), 'w'))

# ---------------------------------------------------------------- run
def render_frame(f, path):
    t = f / FPS; sc.frame_set(f); state(t); sc.cycles.seed = f
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
if '--anchors' in argv:
    anchors()
if '--stills' in argv:
    for s in arg('--stills').split(','):
        f = int(round(float(s) * FPS)); render_frame(f, os.path.join(OUT, f'still_{float(s):06.2f}.png'))
if '--frames' in argv:
    a, b = arg('--frames').split(':'); a = int(a); b = min(int(b), NF)
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    for f in range(a, b):
        p = os.path.join(OUT, 'frames', f'f_{f:05d}.png')
        if not os.path.exists(p): render_frame(f, p)
print('NF', NF, 'DONE')
