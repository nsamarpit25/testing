# ----------------------------------------------------------------------------------------------- trains and the bird
# Two trains, lofted from superellipse sections along x (nose tip at x = 0, the train trails back along -x, rail top
# at z = 0): A, a 0-Series-like blunt nose; B, the 500 Series with a 15 m nearly round needle nose. B's lead car
# carries a shape key "beak" that turns its nose into a kingfisher's beak (and folds the body into the beak's base),
# used for the studio morph. The small Beak for the river shots is lofted from the same beak sections.
NB = 15.0                                   # 500 Series nose length
BODY_W, BODY_H, BODY_Z = 1.68, 1.68, 2.2    # body half-width, half-height, centre height above the rail


def sring(u, wx, hz, zc, n, zb=None, N=48):
    pts = []
    for i in range(N):
        a = 2 * math.pi * i / N
        c, s = math.cos(a), math.sin(a)
        y = wx * math.copysign(abs(c) ** (2 / n), c)
        z = zc + hz * math.copysign(abs(s) ** (2 / n), s)
        if zb is not None:
            z = max(z, zb)
        pts.append(V(u, y, z))
    return pts


def nose_a(u):
    """0 Series: a short rounded snub nose with a near-flat face"""
    s = clamp(-u / 5.5)
    k = math.sqrt(max(1 - (1 - s) ** 2, 0.0))
    return 1.75 * (0.42 + 0.58 * k), 1.8 * (0.36 + 0.64 * k), 2.25 - 0.75 * (1 - k), 2.9


def nose_b(u):
    """500 Series: a long, nearly round taper to a needle tip, set low"""
    s = clamp(-u / NB)
    p = s ** 0.62
    return BODY_W * (0.03 + 0.97 * p), BODY_H * (0.03 + 0.97 * p), 1.25 + (BODY_Z - 1.25) * s ** 0.8, 2.3


def beak_sec(u):
    """kingfisher beak at the same scale: a straight dagger, diamond-ish section, taller than wide"""
    s = clamp(-u / NB)
    p = s ** 0.95
    return 0.02 + 0.78 * p, 0.02 + 1.05 * p, 2.0 - 0.12 * (1 - s) ** 2, 1.7


def lead_stations(ln, body_end=-25.0):
    us = [-ln * (i / 36) ** 1.5 for i in range(37)]
    return us + [lerp(-ln, body_end, (i + 1) / 6) for i in range(6)]


def bm_car(bm, us, sec, zb=0.45):
    rings = [sring(u, *sec(u), zb=zb) for u in us]
    vs = bm_loft(bm, rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return rings


def livery_a():
    m, nt, out = new_mat("LiveryA")
    u, y, z = xyz(nt, obj_co(nt))
    band = mul(nt, sstep(nt, z, 2.42, 2.46), inv(nt, sstep(nt, z, 3.0, 3.04)), inv(nt, sstep(nt, u, -6.6, -6.3)))
    skirt = mul(nt, inv(nt, sstep(nt, z, 1.02, 1.06)), inv(nt, sstep(nt, u, -1.6, -1.2)))
    win = mul(nt, band, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.12, 0.16),
              inv(nt, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.7, 0.74)), inv(nt, sstep(nt, u, -9.0, -8.6)))
    shield = mul(nt, sstep(nt, u, -4.7, -4.6), inv(nt, sstep(nt, u, -2.5, -2.4)), sstep(nt, z, 2.75, 2.8))
    gap = sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", mth(nt, "ADD", u, 25.3), 25.6)), 0.985, 0.99)
    c = col_mix(nt, "#ece6d6", "#1d3f8f", mth(nt, "MAXIMUM", band, skirt))
    glass = mth(nt, "MAXIMUM", mth(nt, "MAXIMUM", win, shield), gap)
    c = col_mix(nt, c, "#07090c", glass)
    b = principled(nt, c, mth(nt, "MULTIPLY_ADD", glass, -0.25, 0.32), 0.0, coat=0.6)
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def irid(nt):
    """kingfisher sheen: dark gunmetal with a teal-to-orange thin-film shift at grazing angles"""
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    c = ramp3(nt, lw.outputs["Facing"], [(0.0, "#10262d"), (0.35, "#127f86"), (0.62, "#2ab7b0"), (0.82, "#e07a2a"),
                                          (1.0, "#3a1d0a")])
    _, _, z = xyz(nt, obj_co(nt))
    slit = inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", z, 1.98)), 0.02, 0.06))
    c = col_mix(nt, c, "#050506", mth(nt, "MULTIPLY", slit, 0.85))
    return principled(nt, c, 0.2, 0.85, coat=1.0, coat_r=0.03)


def livery_b():
    """500 Series: metallic blue-grey, dark blue window band, thin white pinstripe; BK crossfades to the beak"""
    m, nt, out = new_mat("LiveryB")
    u, y, z = xyz(nt, obj_co(nt))
    BK = val(nt, "BK", 0.0)
    band = mul(nt, sstep(nt, z, 2.5, 2.54), inv(nt, sstep(nt, z, 3.06, 3.1)), inv(nt, sstep(nt, u, -11.4, -11.0)))
    pin = mul(nt, sstep(nt, z, 2.38, 2.40), inv(nt, sstep(nt, z, 2.43, 2.45)), inv(nt, sstep(nt, u, -9.0, -8.6)))
    win = mul(nt, band, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.12, 0.16),
              inv(nt, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.7, 0.74)), inv(nt, sstep(nt, u, -18.5, -18.0)))
    skirt = inv(nt, sstep(nt, z, 0.9, 0.95))
    gap = sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", mth(nt, "ADD", u, 25.3), 25.6)), 0.985, 0.99)
    c = col_mix(nt, "#8796a8", "#1b2a4c", band)
    c = col_mix(nt, c, "#f2f2ee", pin)
    c = col_mix(nt, c, "#4b525c", skirt)
    glass = mth(nt, "MAXIMUM", win, gap)
    c = col_mix(nt, c, "#06080c", glass)
    b = principled(nt, c, 0.26, mth(nt, "MULTIPLY_ADD", glass, -0.6, 0.6), coat=1.0, coat_r=0.04)
    link(nt, mix_sh(nt, BK, b.outputs[0], irid(nt).outputs[0]), out.inputs["Surface"])
    return m


def beak_mat():
    m, nt, out = new_mat("Beak")
    link(nt, irid(nt).outputs[0], out.inputs["Surface"])
    return m


def under_parts(bm, x0, x1):
    """bogies and the dark underframe between the skirts"""
    bmh(bm, ((x0 + x1) / 2, 0, 0.55), ((x0 - x1) / 2 - 0.4, 1.35, 0.3))
    for xc in (x0 - 3.0, x1 + 3.0):
        bmh(bm, (xc, 0, 0.42), (1.6, 1.25, 0.32))
        for dx in (-1.2, 1.2):
            bm_rod(bm, (xc + dx, -0.82, 0.43), (xc + dx, 0.82, 0.43), 0.43, 16)


def build_train(key, M, mat):
    """root empty (move it along the track) with the lead car, three trailing cars and the underframe"""
    root = empty(f"Root{key}")
    us = lead_stations(5.5 if key == "A" else NB)
    sec = nose_a if key == "A" else nose_b
    bm = bmesh.new()
    rings = bm_car(bm, us, sec)
    lead = obj_from_bm(f"Lead{key}", bm, mat, parent=root, smooth=True)
    if key == "B":
        # the beak shape key: nose rings become the beak; body rings fold into a rounded base behind it
        brs = []
        nb = len([u for u in us if u >= -NB - 1e-6])
        for i, u in enumerate(us):
            if i < nb:
                brs.append(sring(u, *beak_sec(u)))
            else:
                k = (i - nb + 1) / (len(us) - nb)
                wx, hz, zc, n = beak_sec(-NB)
                f = math.sqrt(max(1 - k ** 2, 0.0))
                brs.append(sring(-NB - 0.9 * k, wx * f + 0.01, hz * f + 0.01, zc, n))
        co = [p for r in brs for p in r]
        co += [sum(brs[0], Vector()) / len(brs[0]), sum(brs[-1], Vector()) / len(brs[-1])]
        lead.shape_key_add(name="Basis")
        sk = lead.shape_key_add(name="beak")
        for v, p in zip(sk.data, co):
            v.co = p
    bm = bmesh.new()
    body = (BODY_W, BODY_H, BODY_Z, 2.3) if key == "B" else (1.75, 1.8, 2.25, 2.9)
    ul = [0.0, 0.12, 0.35] + [0.35 + 24.3 * (j + 1) / 6 for j in range(6)] + [24.88, 25.0]
    sc = [0.9, 0.97, 1.0] + [1.0] * 6 + [0.97, 0.9]
    for c in range(3):
        x = -25.6 * (c + 1)
        rings = [sring(x - u, body[0] * k, body[1] * k, body[2], body[3], zb=0.45) for u, k in zip(ul, sc)]
        bm_loft(bm, rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cars = obj_from_bm(f"Cars{key}", bm, mat, parent=root, smooth=True)
    bm = bmesh.new()
    for c in range(4):
        under_parts(bm, -25.6 * c - 0.5, -25.6 * c - 25.0)
    under = obj_from_bm(f"Under{key}", bm, M["under"], parent=root)
    parts = dict(root=root, lead=lead, cars=cars, under=under)
    if key == "B":
        parts["canopy"] = sphere("CanopyB", 1.0, (-10.6, 0, 3.15), M["glass"], parent=root, scale=(2.2, 0.62, 0.42))
        bm = bmesh.new()                                    # wing-shaped T pantograph on car 2
        px = -38.0
        bmh(bm, (px, 0, 3.98), (0.9, 0.5, 0.12))
        bm_rod(bm, (px, 0, 4.0), (px + 0.6, 0, 4.85), 0.07, 10)
        bmh(bm, (px + 0.6, 0, 4.95), (0.22, 1.0, 0.07))
        bmh(bm, (px + 0.6, 0, 5.06), (0.06, 0.95, 0.04))
        parts["panto"] = obj_from_bm("PantoB", bm, M["under"], parent=root)
        parts["spark"] = sphere("Spark", 0.05, (px + 0.6, 0.25, 5.1), M["spark"], parent=root)
    return parts


def build_beak(mat, scale=0.004):
    """the small beak for the river shots: tip at the origin pointing +x"""
    us = lead_stations(NB, -NB - 0.9)
    brs = []
    for u in us:
        if u >= -NB:
            brs.append(sring(u, *beak_sec(u)))
        else:
            k = (u + NB) / -0.9
            wx, hz, zc, n = beak_sec(-NB)
            f = math.sqrt(max(1 - k ** 2, 0.0))
            brs.append(sring(u, wx * f + 0.01, hz * f + 0.01, zc, n))
    bm = bmesh.new()
    bm_loft(bm, [[(p - V(0, 0, 2.0)) * scale for p in r] for r in brs])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    root = empty("BeakRoot")
    obj_from_bm("Beak", bm, mat, parent=root, smooth=True)
    return root


def bird_mats():
    """kingfisher plumage: electric blue-cyan above, orange below (split on the object-space normal)"""
    m, nt, out = new_mat("Plumage")
    _, _, nz = xyz(nt, node(nt, "ShaderNodeTexCoord").outputs["Normal"])
    back = col_mix(nt, "#0a4f9c", "#1fb8e0", sstep(nt, nz, 0.35, 0.95))
    c = col_mix(nt, back, "#e2671d", inv(nt, sstep(nt, nz, -0.45, -0.1)))
    fl = noise(nt, obj_co(nt), 900.0, 2.0)
    c = col_mix(nt, c, "#000000", mth(nt, "MULTIPLY", fl, 0.25))
    link(nt, principled(nt, c, 0.38, 0.0, coat=0.5, coat_r=0.18).outputs[0], out.inputs["Surface"])
    w, nt, out = new_mat("Wing")
    _, yy, _ = xyz(nt, obj_co(nt))
    fl = noise(nt, obj_co(nt), 500.0, 3.0)
    c = col_mix(nt, "#073f7a", "#16a6d4", mth(nt, "MULTIPLY", fl, 0.9))
    link(nt, principled(nt, c, 0.34, 0.0, coat=0.6, coat_r=0.15).outputs[0], out.inputs["Surface"])
    return m, w, pbr("Eye", "#030303", 0.06, 0.0), pbr("Cheek", "#f2f0ea", 0.5, 0.0)


def build_bird(root):
    """a stylised kingfisher behind the river beak (tip at the root origin, pointing +x)"""
    pl, wg, eye, wh = bird_mats()
    obs = [sphere("BirdHead", 1.0, (-0.074, 0, 0.004), pl, parent=root, scale=(0.017, 0.0135, 0.0145)),
           sphere("BirdBody", 1.0, (-0.118, 0, -0.003), pl, parent=root, scale=(0.042, 0.0185, 0.019)),
           sphere("BirdTail", 1.0, (-0.172, 0, 0.0), wg, parent=root, scale=(0.026, 0.0085, 0.0028))]
    for sy in (-1, 1):
        obs += [sphere(f"BirdWing{sy}", 1.0, (-0.124, sy * 0.016, 0.006), wg, parent=root,
                       scale=(0.033, 0.0036, 0.0115)),
                sphere(f"BirdEye{sy}", 1.0, (-0.068, sy * 0.0118, 0.0075), eye, parent=root,
                       scale=(0.0026, 0.0026, 0.0026), seg=16),
                sphere(f"BirdCheek{sy}", 1.0, (-0.083, sy * 0.0105, -0.004), wh, parent=root,
                       scale=(0.006, 0.0035, 0.0045), seg=16)]
    obs[2].rotation_euler = (0.0, rad(-8.0), 0.0)
    return obs


def water_mat():
    """still river water; a single radial ripple of radius RR (m), height RA, around the object origin"""
    m, nt, out = new_mat("Water")
    P = obj_co(nt)
    x, y, _ = xyz(nt, P)
    RR, RA = val(nt, "RR", 0.0), val(nt, "RA", 0.0)
    d = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", x, x), mth(nt, "MULTIPLY", y, y)))
    dr = mth(nt, "SUBTRACT", d, RR)
    rip = mul(nt, mth(nt, "SINE", mth(nt, "MULTIPLY", dr, 260.0)),
              mth(nt, "EXPONENT", mth(nt, "MULTIPLY", mth(nt, "POWER", mth(nt, "DIVIDE", dr, 0.012), 2.0), -1.0)), RA)
    h = mth(nt, "ADD", rip, mth(nt, "MULTIPLY", noise(nt, P, 0.9, 3.0, 0.5, stretch=(1.0, 3.0, 1.0)), 0.004))
    b = principled(nt, "#0a1a1c", 0.02, 0.0)
    b.inputs["IOR"].default_value = 1.33
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.004
    link(nt, h, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def build_river(M):
    """the river set at RV: still water, a reed bank behind, a bare branch, a dark treeline far away"""
    obs = []
    bm = bmesh.new()
    bmh(bm, (0, 0, -0.05), (40.0, 40.0, 0.05))
    obs.append(obj_from_bm("River", bm, M["water"], loc=RV))
    bm = bmesh.new()
    nx, ny, step = 61, 31, 1.0
    vs = []
    for j in range(ny):
        for i in range(nx):
            x, y = -30.0 + i * step, 7.0 + j * step
            vs.append(bm.verts.new((x, y, 0.18 * (y - 7.5) + 0.3 * nz(x, y, 4.0, 9.0))))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    obs.append(obj_from_bm("Bank", bm, M["bank"], loc=RV, smooth=True))
    random.seed(4)
    bm = bmesh.new()
    for k in range(520):
        if k % 2:
            x, y = random.uniform(-12, 12), random.uniform(7.2, 10.0)
        else:
            x, y = random.choice((-1, 1)) * random.uniform(0.9, 5.0), random.uniform(-4.5, -2.6)
        h = random.uniform(0.6, 1.6)
        lean = V(random.uniform(-0.12, 0.12), random.uniform(-0.1, 0.1), 0)
        bm_rod(bm, V(x, y, -0.1), V(x, y, h) + lean, random.uniform(0.004, 0.008), 5)
    obs.append(obj_from_bm("Reeds", bm, M["reed"], loc=RV))
    bm = bmesh.new()
    pts = [V(-2.4, 2.6, 1.2), V(-1.5, 1.6, 0.95), V(-0.7, 0.9, 0.82), V(-0.15, 0.45, 0.78), V(0.25, 0.2, 0.8)]
    bm_tube(bm, pts, 0.018, 10, rfun=lambda u: 1.2 - 0.7 * u)
    obs.append(obj_from_bm("Branch", bm, M["bark"], loc=RV, smooth=True))
    bm = bmesh.new()
    random.seed(8)
    for _ in range(90):
        x, y = random.uniform(-60, 60), random.uniform(24, 40)
        h = random.uniform(8, 14)
        bm_cyl(bm, h * 0.24, 0.0, h, 14, Matrix.Translation(V(x, y, 0.18 * (y - 7.5) + h / 2)))
    obs.append(obj_from_bm("FarTrees", bm, M["tree"], loc=RV, smooth=True))
    return obs


def build_shock(M):
    """the pressure burst at the exit portal: an emissive torus that the shots scale up and fade"""
    bm = bmesh.new()
    bm_torus(bm, Matrix(), 1.0, 0.12, 64, 8)
    return obj_from_bm("Shock", bm, M["shock"], loc=(X1T + HOOD + 1.0, 0, ZT), smooth=True)


def studio_lights():
    """key and rim area lights round the studio set; their energy is keyed up only in the studio shots"""
    obs = []
    for name, off, size, col, e in (("Key", V(14, -16, 12), 10.0, "#fff3e2", 9000.0),
                                    ("Rim", V(-26, 14, 8), 6.0, "#d6e8ff", 14000.0),
                                    ("Top", V(-6, 0, 22), 14.0, "#ffffff", 5000.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "DISK"
        ld.size = size
        ld.color = lin(col)
        ld.energy = e
        ob = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = ST + off
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = (ST + V(-7, 0, 2) - ob.location).to_track_quat("-Z", "Y")
        obs.append(ob)
    return obs


def build_sk():
    scn = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    M = {}
    M["terrain"] = terrain_mat()
    M["conc"] = concrete("Concrete")
    M["rail"] = pbr("Steel", "#6c6e70", 0.35, 1.0)
    M["wire"] = pbr("Wire", "#3a3226", 0.4, 1.0)
    M["tree"] = tree_mat()
    M["wall"] = pbr("Wall", "#ddd6c8", 0.7)
    M["roof"] = pbr("Roof", "#3b3f45", 0.55, 0.2)
    M["win"] = emis("Win", "#ffbf70", 6.0)
    M["tunnel"] = tunnel_mats()
    M["rings"] = rings_mat()
    M["A"], M["B"] = livery_a(), livery_b()
    M["under"] = pbr("Under", "#1c1e21", 0.6, 0.3)
    M["glass"] = pbr("Glass", "#05070a", 0.04, 0.0)
    M["spark"] = emis("Spark", "#bfe3ff", 0.0)
    M["beak"] = beak_mat()
    M["water"] = water_mat()
    M["bank"] = pbr("Bank", "#4a4528", 0.9)
    M["reed"] = pbr("Reed", "#8d7a45", 0.8)
    M["bark"] = pbr("Bark", "#2e241c", 0.85)
    M["shock"] = emis("Shock", "#ffd9a0", 0.0, alpha=1.0)
    world = sky_studio_world(6.5, -58.0)
    ter = terrain(M["terrain"])
    tun = build_tunnel(M["tunnel"])
    rings = build_rings(M["rings"])
    track = build_track(M["conc"], M["rail"], M["wire"])
    trees = build_trees(M["tree"])
    houses = build_houses(M["wall"], M["roof"], M["win"])
    sd = V(-math.sin(rad(-58.0)), math.cos(rad(-58.0)), 0.0) * math.cos(rad(6.5)) + V(0, 0, math.sin(rad(6.5)))
    sun = sun_lamp(sd, 4.5, "#ffb072", angle=0.8)
    TA, TB = build_train("A", M, M["A"]), build_train("B", M, M["B"])
    beak = build_beak(M["beak"])
    build_bird(beak)
    river = build_river(M)
    shock = build_shock(M)
    lights = studio_lights()
    kd = bpy.data.lights.new("BeakKey", "AREA")
    kd.size = 0.6
    kd.color = lin("#ffe2bf")
    beakkey = bpy.data.objects.new("BeakKey", kd)
    bpy.context.scene.collection.objects.link(beakkey)
    beakkey.location = RV + V(0.5, -0.8, 0.9)
    beakkey.rotation_mode = "QUATERNION"
    beakkey.rotation_quaternion = (RV + V(0, 0, 0.45) - beakkey.location).to_track_quat("-Z", "Y")
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.05, 20000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    valley = [ter, *track, trees, *houses]
    return dict(M=M, world=world, valley=valley, tunnel=tun, rings=rings, sun=sun, A=TA, B=TB, beak=beak,
                river=river, shock=shock, lights=lights, beakkey=beakkey, cam=camo, hero=None)
