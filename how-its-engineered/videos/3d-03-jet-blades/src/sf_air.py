# ----------------------------------------------------------------------------------------------- airliner + sky
# A twin-engine wide-body (nose at -x, z up, metres) cruising above a cloud deck at golden hour. The two engines are
# the real-scale turbofans from build_engine, hung under the wings on pylons.

def naca(t, n=48, camber=0.02, p=0.4):
    """closed NACA 4-digit loop (chord 0..1), upper surface LE->TE then lower TE->LE"""
    up, lo = [], []
    for k in range(n + 1):
        x = (1 - math.cos(math.pi * k / n)) / 2
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4)
        yc = camber / p ** 2 * (2 * p * x - x * x) if x < p else camber / (1 - p) ** 2 * (1 - 2 * p + 2 * p * x - x * x)
        up.append((x, yc + yt))
        lo.append((x, yc - yt))
    return up[::-1] + lo[1:-1]   # TE(upper) -> LE -> TE(lower), no duplicate LE/TE


def bm_loft(bm, rings, cap0=True, cap1=True):
    """rings: list of equal-length vertex position lists; quads between, fan caps at the ends"""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    for cap, ring in ((cap0, vs[0]), (cap1, vs[-1])):
        if cap:
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / n)
            for i in range(n):
                bm.faces.new((ring[i], ring[(i + 1) % n], c) if ring is vs[-1] else (ring[(i + 1) % n], ring[i], c))
    return vs


def bm_wing(bm, sections, t_of, camber=0.02, mirror_y=False, vertical=False):
    """sections: [(le Vector, chord, twist_deg, s)]; airfoil in the x-z plane (or x-y for a fin)"""
    rings = []
    for le, ch, tw, s in sections:
        af = naca(t_of(s), camber=camber)
        ring = []
        for x, z in af:
            xr, zr = x * ch, z * ch
            a = rad(tw)
            xr, zr = xr * math.cos(a) + zr * math.sin(a), -xr * math.sin(a) + zr * math.cos(a)
            p = le + (V(xr, zr, 0) if vertical else V(xr, 0, zr))
            if mirror_y:
                p = V(p.x, -p.y, p.z)
            ring.append(p)
        rings.append(ring if not mirror_y else ring[::-1])
    bm_loft(bm, rings)


def fuse_section(x):
    """(top z, bottom z, half width) of the fuselage at station x"""
    R = 2.95
    if x < -22.0:                                  # nose: blunt ogive, slightly drooped
        u = (x + 30.0) / 8.0
        k = math.sqrt(max(1 - (1 - u) ** 2, 0.0)) ** 0.9
        top = -0.65 + (R + 0.65) * math.sqrt(max(1 - (1 - u) ** 2.2, 0))
        bot = -0.65 - (R - 0.65) * k
        return top, bot, R * k
    if x < 12.0:
        return R, -R, R
    u = (x - 12.0) / 18.0                          # tail: belly sweeps up, top stays nearly flat
    top = R - 0.9 * u ** 1.6
    bot = -R + (R + 1.55) * (1 - (1 - u) ** 1.7)
    w = R * (1 - 0.88 * u ** 1.25)
    return top, max(bot, top - 0.02), w


def build_airliner(M, me_blade, rxr):
    A = {}
    root = empty("Plane", (0, 0, 0))
    A["root"] = root
    bm = bmesh.new()
    rings = []
    xs = [-30 + 8 * (1 - math.cos(math.pi / 2 * k / 24)) for k in range(1, 25)] + \
         [-22 + 34 * k / 30 for k in range(1, 31)] + [12 + 17.6 * k / 30 for k in range(1, 31)]
    for x in xs:
        top, bot, w = fuse_section(x)
        zc, hz = (top + bot) / 2, (top - bot) / 2
        ring = []
        for i in range(72):
            a = 2 * math.pi * i / 72
            c, s = math.cos(a), math.sin(a)
            sq = 2.2                                 # superellipse: a slightly squarer cross-section
            cy = math.copysign(abs(c) ** (2 / sq), c)
            sz = math.copysign(abs(s) ** (2 / sq), s)
            ring.append(V(x, w * cy, zc + hz * sz))
        rings.append(ring)
    bm_loft(bm, rings)
    fus = obj_from_bm("Fuselage", bm, M["livery"], root, smooth=True)
    A["fus"] = fus
    # wings: low-mounted, 32 deg sweep, 6 deg dihedral, raked tips
    bm = bmesh.new()
    for side in (1, -1):
        secs = []
        for k in range(26):
            s = k / 25
            y = 2.6 + 27.4 * s
            rake = max(0.0, (s - 0.86) / 0.14)
            xle = -6.0 + (y - 2.6) * math.tan(rad(32)) + 2.2 * rake ** 1.5
            ch = lerp(11.2, 2.0, s) - 1.6 * rake ** 1.2 if s > 0.28 else lerp(11.2, 7.6, s / 0.28)
            ch = max(ch, 0.6)
            secs.append((V(xle, y, -1.75 + (y - 2.6) * math.tan(rad(6))), ch, lerp(2.5, -1.5, s), s))
        bm_wing(bm, secs, lambda s: lerp(0.14, 0.095, s), 0.025, mirror_y=side < 0)
    A["wing"] = obj_from_bm("Wing", bm, M["wingpaint"], root, smooth=True)
    # tailplane
    bm = bmesh.new()
    for side in (1, -1):
        secs = []
        for k in range(12):
            s = k / 11
            y = 1.2 + 9.4 * s
            secs.append((V(20.5 + (y - 1.2) * math.tan(rad(36)), y, 0.6 + (y - 1.2) * math.tan(rad(7))),
                         lerp(5.6, 1.9, s), 0.0, s))
        bm_wing(bm, secs, lambda s: 0.10, 0.0, mirror_y=side < 0)
    A["htail"] = obj_from_bm("HTail", bm, M["wingpaint"], root, smooth=True)
    # fin
    bm = bmesh.new()
    secs = []
    for k in range(14):
        s = k / 13
        zz = 2.2 + 9.6 * s
        secs.append((V(17.8 + (zz - 2.2) * math.tan(rad(40)), 0, zz), lerp(8.4, 2.9, s), 0.0, s))
    bm_wing(bm, secs, lambda s: 0.10, 0.0, vertical=True)
    A["fin"] = obj_from_bm("Fin", bm, M["tailpaint"], root, smooth=True)
    # engines + pylons
    A["engines"] = []
    for side in (1, -1):
        y = 9.8 * side
        xle = -6.0 + (abs(y) - 2.6) * math.tan(rad(32))
        zw = -1.75 + (abs(y) - 2.6) * math.tan(rad(6))
        G = build_engine(M, me_blade, rxr)
        G["root"].parent = root
        G["root"].location = (xle - 1.0, y, zw - 2.35)
        A["engines"].append(G)
        bm = bmesh.new()
        secs = []
        for k in range(6):
            s = k / 5
            zz = lerp(zw - 2.35 + 1.3, zw + 0.2, s)
            secs.append((V(xle - 1.6 + 1.2 * s, y, zz), lerp(4.6, 6.5, s), 0.0, s))
        bm_wing(bm, secs, lambda s: 0.16, 0.0, vertical=True)
        obj_from_bm(f"Pylon{side}", bm, M["wingpaint"], root, smooth=True)
    return A


def livery_mat():
    """white fuselage, grey belly, a row of cabin windows, cockpit glass, faint panel seams"""
    m, nt, out = new_mat("Livery")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    belly = sstep(nt, z, -1.9, -1.6)
    base = col_mix(nt, "#7d8389", "#f1f2f3", belly)
    # cabin windows: rounded slots, 0.53 m pitch, on the sides only
    fx = mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "DIVIDE", x, 0.53)), 0.5)
    wx = mth(nt, "MULTIPLY", fx, 0.53)
    wz = mth(nt, "SUBTRACT", z, 0.75)
    d = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", mth(nt, "DIVIDE", wx, 0.12), mth(nt, "DIVIDE", wx, 0.12)),
                         mth(nt, "MULTIPLY", mth(nt, "DIVIDE", wz, 0.19), mth(nt, "DIVIDE", wz, 0.19))))
    side = sstep(nt, mth(nt, "ABSOLUTE", y), 2.2, 2.5)
    span = mul(nt, mth(nt, "GREATER_THAN", x, -20.5), mth(nt, "LESS_THAN", x, 11.0))
    win = mul(nt, inv(nt, sstep(nt, d, 0.85, 1.0)), side, span)
    # cockpit glass: a dark band wrapping the nose
    cz = mth(nt, "SUBTRACT", z, mth(nt, "MULTIPLY_ADD", x, -0.10, -1.55))
    cock = mul(nt, mth(nt, "GREATER_THAN", x, -28.6), mth(nt, "LESS_THAN", x, -26.6),
               inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", cz, 0.2)), 0.18, 0.24)))
    dark = mth(nt, "MAXIMUM", win, cock)
    base = col_mix(nt, base, "#0b0e12", dark)
    # cheatline: a thin navy stripe under the windows
    line = inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", z, 0.18)), 0.05, 0.07))
    base = col_mix(nt, base, "#18284a", mul(nt, line, side, mth(nt, "GREATER_THAN", x, -24.0)))
    seams = inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "DIVIDE", x, 2.6)), 0.5)),
                          0.0, 0.003))
    base = col_mix(nt, base, "#9a9fa5", mth(nt, "MULTIPLY", seams, 0.25))
    b = principled(nt, base, mth(nt, "MULTIPLY_ADD", dark, -0.2, 0.28), 0.0, coat=0.6, coat_r=0.08)
    link(nt, b.outputs[0], out.inputs[0])
    return m


def sky_world(sun_el, sun_rot, strength=0.3):
    w = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sky = node(nt, "ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = rad(sun_el)
    sky.sun_rotation = rad(sun_rot)
    sky.altitude = 9000
    sky.aerosol_density = 4.0
    bg = node(nt, "ShaderNodeBackground")
    bg.inputs[1].default_value = strength
    link(nt, sky.outputs[0], bg.inputs[0])
    o = node(nt, "ShaderNodeOutputWorld")
    link(nt, bg.outputs[0], o.inputs[0])
    return w


def cloud_deck(z_top, z_bot, size):
    """a slab of cumulus: fbm density with cauliflower tops, denser towards the base"""
    m, nt, out = new_mat("Clouds")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    h = mth(nt, "DIVIDE", mth(nt, "SUBTRACT", z, z_bot), z_top - z_bot)      # 0 base .. 1 top
    n1 = noise(nt, P, 1 / 2600.0, 6.0, 0.55)
    n2 = noise(nt, P, 1 / 420.0, 4.0, 0.5)
    cov = mth(nt, "SUBTRACT", mth(nt, "MULTIPLY_ADD", n1, 1.0, mth(nt, "MULTIPLY", n2, 0.25)), 0.52)
    prof = mth(nt, "SUBTRACT", cov, mth(nt, "MULTIPLY", mth(nt, "POWER", h, 1.6), 0.28))
    dens = mth(nt, "MULTIPLY", mth(nt, "MAXIMUM", prof, 0.0), 0.12)
    v = node(nt, "ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (1, 1, 1, 1)
    v.inputs["Anisotropy"].default_value = 0.55
    link(nt, dens, v.inputs["Density"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    for l in list(out.inputs[0].links):
        nt.links.remove(l)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for vv in bm.verts:
        vv.co = V(vv.co.x * size, vv.co.y * size, z_bot + (vv.co.z + 0.5) * (z_top - z_bot))
    return obj_from_bm("Clouds", bm, m)
