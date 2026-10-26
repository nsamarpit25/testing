# ----------------------------------------------------------------------------------------------- Hoover Dam world
# Black Canyon at golden hour: the arch-gravity dam, Lake Mead upstream (-y) with its white mineral "bathtub ring",
# the Colorado River downstream (+y), four intake towers and the powerhouse wings at the toe. Metres, base of the dam
# at z = 0, crest at z = 221. A separate cooling set (KS) far away holds the concrete-block cutaways.
import mathutils.noise as mn

T_END = 35.1
F_END = int(T_END * FPS) + 1
CREST = 221.0
LAKE = 168.0                         # today's low Lake Mead, ~53 m under the crest
RIVER = 3.0
R_ARCH = 260.0                       # upstream face radius; the arch centre is downstream at (0, R_ARCH)
KS = Vector((4000.0, 0.0, 0.0))      # cooling set


def bmh(bm, c, half):
    """box from its centre and half-sizes"""
    bm_box(bm, c, tuple(2 * h for h in half))


def dam_th(z):
    """dam thickness (m) at height z: 200 m at the base, 14 m at the crest, a concave downstream face"""
    u = clamp(1 - z / CREST)
    return 14.0 + 186.0 * u ** 2.2


def arch_pt(th, z, off=0.0):
    """point on the upstream face at arch angle th (rad), pushed off metres downstream along the radius"""
    r = R_ARCH - off
    return V(r * math.sin(th), R_ARCH - r * math.cos(th), z)


def arch_y(x):
    th = math.asin(clamp(x / R_ARCH, -0.99, 0.99))
    return R_ARCH - R_ARCH * math.cos(th)


def canyon_h(x, y):
    """terrain height: a narrow river bed, near-vertical dark walls, a broken plateau on top"""
    xc = 18.0 * math.sin(y / 260.0) + 10.0 * math.sin(y / 97.0 + 1.0)
    dx = abs(x - xc)
    w = 46.0 + 22.0 * (1 + math.sin(y / 330.0 + 2.0)) + 25.0 * max(0.0, -y / 900.0)   # wider upstream (the lake)
    u = clamp((dx - w) / 175.0)
    wall = 292.0 * (u * u * (3 - 2 * u)) ** 0.55
    n = mn.fractal(V(x / 140.0, y / 140.0, 0.3), 0.8, 2.1, 6, noise_basis='PERLIN_ORIGINAL')
    ridge = 1.0 - abs(mn.noise(V(x / 60.0, y / 60.0, 7.7), noise_basis='PERLIN_ORIGINAL'))
    z = wall + 26.0 * n * (0.3 + u) + 12.0 * ridge * u
    return max(z, -6.0)


def terrain(name, x0, x1, y0, y1, step, mat):
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    bm = bmesh.new()
    vs = []
    for j in range(ny):
        y = y0 + j * step
        for i in range(nx):
            x = x0 + i * step
            vs.append(bm.verts.new((x, y, canyon_h(x, y))))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    ob = obj_from_bm(name, bm, mat, smooth=True)
    return ob


def rock_mat():
    m, nt, out = new_mat("Rock")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    n1 = noise(nt, P, 0.012, 6.0, 0.6)
    n2 = noise(nt, P, 0.09, 8.0, 0.65)
    strata = noise(nt, P, 0.05, 3.0, 0.5, stretch=(0.15, 0.15, 3.0))
    base = ramp3(nt, mth(nt, "ADD", mth(nt, "MULTIPLY", n1, 0.7), mth(nt, "MULTIPLY", strata, 0.3)),
                 [(0.3, "#3b2a20"), (0.45, "#5e4231"), (0.58, "#8a6446"), (0.7, "#a9825c")])
    ring = mul(nt, sstep(nt, z, LAKE - 1.0, LAKE + 0.5), inv(nt, sstep(nt, z, LAKE + 34.0, LAKE + 40.0)))
    ring = mul(nt, ring, mth(nt, "MULTIPLY_ADD", n2, 0.5, 0.6), val(nt, "RING", 1.0))
    base = col_mix(nt, base, "#d8d0c2", ring)
    b = principled(nt, base, 0.9, 0.0)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 1.5
    link(nt, mth(nt, "ADD", n2, mth(nt, "MULTIPLY", strata, 0.5)), bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def concrete_mat(name="Concrete", col="#cdc3b2"):
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    streak = noise(nt, P, 0.35, 4.0, 0.6, stretch=(1.0, 1.0, 0.04))
    blot = noise(nt, P, 0.05, 5.0, 0.6)
    lift = mth(nt, "FRACT", mth(nt, "DIVIDE", z, 1.52))
    line = mul(nt, sstep(nt, lift, 0.0, 0.02), inv(nt, sstep(nt, lift, 0.04, 0.06)))
    base = col_mix(nt, col, "#8f8574", mth(nt, "MULTIPLY", mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", streak, 0.52), 0.0), 3.0))
    base = col_mix(nt, base, "#b5aa96", mth(nt, "MULTIPLY", blot, 0.5))
    base = col_mix(nt, base, "#9c927f", mth(nt, "MULTIPLY", line, 0.35))
    b = principled(nt, base, 0.78, 0.0)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    link(nt, mth(nt, "ADD", blot, mth(nt, "MULTIPLY", line, -0.4)), bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def water_mat():
    m, nt, out = new_mat("Water")
    P = node(nt, "ShaderNodeTexCoord").outputs["Generated"]
    w = noise(nt, obj_co(nt), 0.08, 6.0, 0.55, stretch=(1.0, 2.5, 1.0))
    b = principled(nt, "#0b2f37", 0.03, 0.0)
    b.inputs["IOR"].default_value = 1.33
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    link(nt, w, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def build_dam(mat):
    """arch-gravity dam: rings of (upstream, downstream) points over height, closed into a solid; the ends run
    deep into the canyon walls so the rock hides them"""
    bm = bmesh.new()
    na, nz = 96, 48
    th0 = rad(44)
    rows = []
    for k in range(nz + 1):
        z = -8.0 + (CREST + 8.0) * (k / nz) ** 0.8
        t = dam_th(z)
        up = [bm.verts.new(arch_pt(-th0 + 2 * th0 * i / na, z)) for i in range(na + 1)]
        dn = [bm.verts.new(arch_pt(-th0 + 2 * th0 * i / na, z, t)) for i in range(na + 1)]
        rows.append((up, dn))
    for k in range(nz):
        (u0, d0), (u1, d1) = rows[k], rows[k + 1]
        for i in range(na):
            bm.faces.new((u0[i], u0[i + 1], u1[i + 1], u1[i]))
            bm.faces.new((d0[i + 1], d0[i], d1[i], d1[i + 1]))
    u, d = rows[-1]
    for i in range(na):                          # the crest road
        bm.faces.new((u[i + 1], u[i], d[i], d[i + 1]))
    bm.normal_update()
    ob = obj_from_bm("Dam", bm, mat, smooth=True)
    # parapets along the crest
    bm = bmesh.new()
    for off in (0.6, dam_th(CREST) - 0.6):
        for i in range(na):
            a = -th0 + 2 * th0 * i / na
            p0, p1 = arch_pt(a, CREST, off), arch_pt(a + 2 * th0 / na, CREST, off)
            c = (p0 + p1) / 2 + V(0, 0, 0.6)
            bmh(bm, c, ((p1 - p0).length / 2 + 0.05, 0.3, 0.6))
    obj_from_bm("Parapet", bm, mat)
    return ob


def lake(mat):
    bm = bmesh.new()
    nx, ny = 120, 120
    x0, x1, y0 = -900.0, 900.0, -2600.0
    vs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            yd = arch_y(clamp(x, -R_ARCH * 0.69, R_ARCH * 0.69)) + 2.0
            y = y0 + (yd - y0) * j / ny
            vs.append(bm.verts.new((x, y, LAKE)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
    lk = obj_from_bm("Lake", bm, mat)
    bm = bmesh.new()
    bmh(bm, V(0, 1500.0, RIVER - 0.5), (900.0, 1400.0, 0.5))
    rv = obj_from_bm("River", bm, mat)
    return lk, rv


def towers(mat):
    obs = []
    for i, (x, y) in enumerate(((-118, -55), (118, -55), (-128, -175), (128, -175))):
        bm = bmesh.new()
        bm_cyl(bm, 14.0, 14.0, CREST + 12.0, 40, Matrix.Translation(V(x, y, (CREST + 12.0) / 2 - 6.0)))
        for k in range(12):                      # art-deco fins
            a = 2 * math.pi * k / 12
            bmh(bm, V(x + 14.4 * math.cos(a), y + 14.4 * math.sin(a), CREST - 30.0), (1.0, 1.0, 36.0))
        bm_cyl(bm, 15.5, 13.0, 5.0, 40, Matrix.Translation(V(x, y, CREST + 8.5)))
        bm_cyl(bm, 6.0, 4.5, 7.0, 24, Matrix.Translation(V(x, y, CREST + 14.0)))
        obs.append(obj_from_bm(f"Tower{i}", bm, mat, smooth=True))
    return obs


def powerhouse(mat, roof):
    bm = bmesh.new()
    y0 = arch_y(0.0) + dam_th(10.0) - 6.0
    for s in (-1, 1):
        for k in range(5):
            bmh(bm, V(s * 58.0, y0 + 30.0 + k * 34.0, 22.0), (14.0, 16.0, 22.0))
    bmh(bm, V(0, y0 + 12.0, 10.0), (50.0, 10.0, 10.0))
    obj_from_bm("Powerhouse", bm, mat)
    bm = bmesh.new()
    for s in (-1, 1):
        bmh(bm, V(s * 58.0, y0 + 98.0, 44.5), (14.5, 85.0, 0.6))
    return obj_from_bm("PowerRoof", bm, roof)


def build_hd():
    scn = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    M = {}
    M["rock"] = rock_mat()
    M["conc"] = concrete_mat()
    M["water"] = water_mat()
    M["roof"] = pbr("Roof", "#8c8a84", 0.6, 0.2)
    world = sky_world(7.0, 330.0, 0.32)
    sky = world.node_tree.nodes["Sky Texture"]
    sky.altitude = 600
    sky.aerosol_density = 2.0
    ter = terrain("Canyon", -900.0, 900.0, -2200.0, 2200.0, 5.0, M["rock"])
    dam = build_dam(M["conc"])
    lk, rv = lake(M["water"])
    tw = towers(M["conc"])
    ph = powerhouse(M["conc"], M["roof"])
    sun = sun_lamp((-math.sin(rad(330)), math.cos(rad(330)), 0.13), 5.0, "#ffb878", angle=0.8)
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.05, 20000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    ext = [ter, dam, lk, rv, ph, sun, *tw] + [bpy.data.objects[n] for n in ("Parapet", "Powerhouse")]
    return dict(M=M, world=world, ext=ext, sun=sun, cam=camo, hero=None)
