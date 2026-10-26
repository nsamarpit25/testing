# ----------------------------------------------------------------------------------------------- storm barrier world
# The Maeslantkering on the Nieuwe Waterweg. Metres, z up, normal water level z = 0, the North Sea towards -x,
# Rotterdam towards +x. The channel is 360 m wide (banks at y = +-180, quays up to z = +5). Each gate is a hollow
# curved steel box (210 m long, 22 m high, 15 m deep) on an arc of radius R round a 10 m ball joint on its bank
# (JN north, JS south), held by a white tubular truss. Closed (swing 0) the gates meet mid-river, convex to the sea;
# parked (swing PARK) each sits in a curved dry dock cut into its bank. A gate's bottom is at zb: -16 resting in a
# dry dock, -7 floating, -17 sunk on the sill. The x-ray set shows the gate as glass with its chambers filling.
import mathutils.noise as mn

T_END = 30.5
F_END = int(T_END * FPS) + 1
CH = 180.0                           # half width of the channel
ZL = 5.0                             # quay / land height
R = 262.0                            # gate arc radius (gate centreline) round the joint
GD, GH = 15.0, 22.0                  # gate depth and height
PSI = math.degrees(210.0 / R) / 2    # half the gate's angular span (deg)
TH_C = 208.25                        # gate centre direction from the north joint when closed (deg, world)
JN = Vector((250.0, 205.0, 0.0))
JS = Vector((250.0, -205.0, 0.0))
ZJ = 4.0                             # ball centre height
PARK = -50.0                         # swing angle in the dock (deg; north gate, the south one mirrors)
ZB_FLOAT, ZB_DOCK, ZB_SUNK = -7.0, -16.0, -17.0
SILL = -17.0
GAUGE = Vector((-470.0, 160.0, 0.0))


def nz(x, y, s, seed=0.0):
    return mn.noise(V(x / s, y / s, seed), noise_basis='PERLIN_ORIGINAL')


def sstepv(nt, x, e0, e1):
    m = node(nt, "ShaderNodeMapRange", data_type="FLOAT", interpolation_type="SMOOTHSTEP")
    link(nt, x, m.inputs[0])
    for k, e in ((1, e0), (2, e1)):
        if isinstance(e, (int, float)):
            m.inputs[k].default_value = e
        else:
            link(nt, e, m.inputs[k])
    m.inputs[3].default_value = 0.0
    m.inputs[4].default_value = 1.0
    return m.outputs[0]


def gpt(psi, r, z):
    """point in a gate's local frame (x = centre direction from the joint), psi in deg"""
    a = rad(psi)
    return V(r * math.cos(a), r * math.sin(a), z)


def world_pt(side, swing, zb, p):
    """local gate-frame point -> world, for the gate on side (+1 north, -1 south) at swing (deg) and bottom zb"""
    al = math.asin(clamp((ZB_FLOAT - zb) / R, -0.2, 0.2))
    q = Matrix.Rotation(al, 3, "Y") @ (Vector(p) - V(0, 0, ZJ)) + V(0, 0, ZJ)
    th = rad(TH_C + swing)
    q = Matrix.Rotation(th, 3, "Z") @ q
    if side < 0:
        q = V(q.x, -q.y, q.z)
    return (JN if side > 0 else JS) + q


# ----------------------------------------------------------------------------------------------- materials

def paint_mat(name, col, rough=0.32, coat=0.6, grime=0.25, seams=0.0):
    """painted steel with soft streaky grime and optional plate seams (local coords)"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    g = noise(nt, P, 0.08, 6.0, 0.6, stretch=(1.0, 1.0, 0.18))
    dirt = mth(nt, "MULTIPLY", sstep(nt, g, 0.45, 0.75), grime)
    base = col_mix(nt, col, "#1a1714", dirt)
    rough_s = mth(nt, "ADD", rough, mth(nt, "MULTIPLY", dirt, 0.4))
    b = principled(nt, base, rough_s, 0.0, coat, 0.12)
    if seams:
        sz = mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "DIVIDE", z, 2.75)), 0.5))
        s1 = sstep(nt, sz, 0.47, 0.5)
        ang = mth(nt, "ARCTAN2", y, x)
        sa = mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "MULTIPLY", ang, R / 12.0)), 0.5))
        s2 = sstep(nt, sa, 0.475, 0.5)
        h = mth(nt, "MAXIMUM", s1, s2)
        bump = node(nt, "ShaderNodeBump")
        bump.inputs["Distance"].default_value = 0.06
        bump.inputs["Strength"].default_value = seams
        link(nt, mth(nt, "SUBTRACT", 1.0, h), bump.inputs["Height"])
        link(nt, bump.outputs[0], b.inputs["Normal"])
    XA = val(nt, "XA", 0.0)
    gl = ghost(nt)
    link(nt, mix_sh(nt, XA, b.outputs[0], gl), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    m.diffuse_color = (*lin(col), 1)
    return m


def ghost(nt, col="#7fe0ff", edge=2.2, face=0.03):
    """x-ray glass: mostly transparent with a glowing fresnel edge"""
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs[0].default_value = 0.35
    fr = mth(nt, "POWER", lw.outputs["Facing"], 2.0)
    e = emission(nt, col, mth(nt, "MULTIPLY_ADD", fr, edge, face))
    tr = node(nt, "ShaderNodeBsdfTransparent")
    sh = node(nt, "ShaderNodeAddShader")
    link(nt, tr.outputs[0], sh.inputs[0])
    link(nt, e, sh.inputs[1])
    return sh.outputs[0]


def ghost_mat(name, col="#7fe0ff", edge=2.2, face=0.03):
    m, nt, out = new_mat(name)
    link(nt, ghost(nt, col, edge, face), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def fill_mat():
    """the water let into a gate's hollows: glowing blue below the fill height FH (local z), nothing above"""
    m, nt, out = new_mat("Fill")
    P = obj_co(nt)
    _, _, z = xyz(nt, P)
    FH = val(nt, "FH", -100.0)
    k = mth(nt, "LESS_THAN", z, FH)
    top = mul(nt, k, sstepv(nt, z, mth(nt, "SUBTRACT", FH, 0.6), FH))
    nzv = noise(nt, P, 0.15, 3.0, 0.5)
    e = emission(nt, col_mix(nt, "#0b5fd6", "#7fe6ff", mth(nt, "MULTIPLY_ADD", top, 0.8, mth(nt, "MULTIPLY", nzv, 0.25))),
                 mth(nt, "MULTIPLY_ADD", top, 5.0, 1.1))
    tr = node(nt, "ShaderNodeBsdfTransparent")
    link(nt, mix_sh(nt, mth(nt, "MULTIPLY", k, 0.82), tr.outputs[0], e), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def water_mat(name="Water", edge=0.3, face=0.004, gcol="#5fd0ff"):
    """dark North Sea water: glossy, foam from the ocean modifier, fine ripples; XA turns it into a glass sheet"""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    foam = attr(nt, "foam")
    FO = val(nt, "FO", 1.0)
    f = mth(nt, "MULTIPLY", sstep(nt, foam, 0.25, 0.85), FO)
    fn = noise(nt, P, 0.35, 5.0, 0.6)
    f = mth(nt, "MULTIPLY", f, sstep(nt, fn, 0.35, 0.6))
    n4 = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")      # churning foam for water pouring in (FN, FW)
    n4.inputs["Scale"].default_value = 0.12
    n4.inputs["Detail"].default_value = 6.0
    n4.inputs["Roughness"].default_value = 0.6
    link(nt, P, n4.inputs["Vector"])
    link(nt, val(nt, "FW", 0.0), n4.inputs["W"])
    f = mth(nt, "MAXIMUM", f, mul(nt, val(nt, "FN", 0.0), sstep(nt, n4.outputs["Fac"], 0.42, 0.62)))
    base = col_mix(nt, "#0a1517", "#c9d2d6", f)
    b = principled(nt, base, mth(nt, "MULTIPLY_ADD", f, 0.5, 0.035), 0.0)
    b.inputs["IOR"].default_value = 1.33
    h = noise(nt, P, 0.6, 6.0, 0.62, stretch=(1.0, 2.2, 1.0))
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.08
    link(nt, val(nt, "RB", 0.5), bump.inputs["Strength"])
    link(nt, h, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    XA = val(nt, "XA", 0.0)
    link(nt, mix_sh(nt, XA, b.outputs[0], ghost(nt, gcol, edge, face)), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def land_mat():
    """quays: grass on top with a concrete apron along the water and round the docks; concrete walls, darker and
    slimy below the waterline"""
    m, nt, out = new_mat("Land")
    gc = node(nt, "ShaderNodeNewGeometry")
    P = gc.outputs["Position"]
    x, y, z = xyz(nt, P)
    _, _, nzz = xyz(nt, gc.outputs["Normal"])
    top = sstep(nt, nzz, 0.6, 0.8)
    ay = mth(nt, "ABSOLUTE", y)
    jy = mth(nt, "SUBTRACT", ay, JN.y)
    dj = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", x, JN.x), mth(nt, "SUBTRACT", x, JN.x)),
                             mth(nt, "MULTIPLY", jy, jy)))
    apron = mth(nt, "MAXIMUM", inv(nt, sstep(nt, ay, CH + 22, CH + 26)),
                mul(nt, sstep(nt, dj, R - 30, R - 26), inv(nt, sstep(nt, dj, R + 26, R + 30))))
    apron = mth(nt, "MAXIMUM", apron, inv(nt, sstep(nt, dj, 34, 38)))
    n1 = noise(nt, P, 0.01, 6.0, 0.6)
    n2 = noise(nt, P, 0.3, 4.0, 0.6)
    grass = col_mix(nt, "#27301c", "#3b4526", n1)
    conc = col_mix(nt, "#8d8b85", "#6d6a64", n2)
    topc = col_mix(nt, grass, conc, apron)
    wet = inv(nt, sstep(nt, z, -0.5, 1.2))
    wall = col_mix(nt, col_mix(nt, "#7d7a73", "#5e5b55", n2), "#20241c", wet)
    c = col_mix(nt, wall, topc, top)
    rough = mth(nt, "SUBTRACT", 0.85, mth(nt, "MULTIPLY", mth(nt, "ADD", wet, mth(nt, "MULTIPLY", apron, 0.25)), 0.4))
    b = principled(nt, c, rough, 0.0)
    h = noise(nt, P, 0.8, 5.0, 0.6)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.05
    bump.inputs["Strength"].default_value = 0.3
    link(nt, h, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    XA = val(nt, "XA", 0.0)
    link(nt, mix_sh(nt, XA, b.outputs[0], ghost(nt, "#5fd0ff", 0.5, 0.01)), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def storm_world():
    """an overcast sky built from the view direction: cloud bands, a bright gap at the horizon; STORM blends a dark
    stormy dusk (1) with a calm golden evening (0); FL is a lightning flash; XR fades to an x-ray void"""
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    D = node(nt, "ShaderNodeTexCoord").outputs["Generated"]
    dx, dy, dz = xyz(nt, D)
    ST = val(nt, "STORM", 1.0)
    FL = val(nt, "FL", 0.0)
    XR = val(nt, "XR", 0.0)
    BGS = val(nt, "BGS", 1.0)
    e = mth(nt, "MAXIMUM", dz, -0.2)
    cz = mth(nt, "ADD", mth(nt, "MAXIMUM", dz, 0.0), 0.06)
    pxy = node(nt, "ShaderNodeCombineXYZ")
    link(nt, mth(nt, "DIVIDE", dx, cz), pxy.inputs[0])
    link(nt, mth(nt, "DIVIDE", dy, cz), pxy.inputs[1])
    link(nt, val(nt, "CW", 0.0), pxy.inputs[2])
    n1 = node(nt, "ShaderNodeTexNoise", noise_dimensions="3D")
    n1.inputs["Scale"].default_value = 0.55
    n1.inputs["Detail"].default_value = 9.0
    n1.inputs["Roughness"].default_value = 0.62
    link(nt, pxy.outputs[0], n1.inputs["Vector"])
    cl = n1.outputs["Fac"]
    dense = sstep(nt, cl, 0.38, 0.62)
    # stormy dusk
    sky_s = ramp3(nt, e, [(0.0, "#3a4550"), (0.03, "#8a96a2"), (0.1, "#4f5a65"), (0.3, "#323b44"), (1.0, "#1e252c")])
    cloud_s = ramp3(nt, e, [(0.0, "#323a42"), (0.05, "#4c555e"), (0.25, "#262d34"), (1.0, "#14191e")])
    storm = col_mix(nt, sky_s, cloud_s, mth(nt, "MULTIPLY", dense, 0.85))
    # calm golden evening
    sky_c = ramp3(nt, e, [(0.0, "#c08a5a"), (0.03, "#f2c08a"), (0.1, "#c9a888"), (0.35, "#7f8fa3"), (1.0, "#4e6178")])
    cloud_c = ramp3(nt, e, [(0.0, "#a87048"), (0.06, "#d8a074"), (0.3, "#8a7a78"), (1.0, "#56607a")])
    calm = col_mix(nt, sky_c, cloud_c, mth(nt, "MULTIPLY", dense, 0.65))
    col = col_mix(nt, calm, storm, ST)
    fl = col_mix(nt, col, "#c8d8ff", mth(nt, "MULTIPLY", FL, mth(nt, "MULTIPLY_ADD", dense, 0.6, 0.4)))
    below = sstep(nt, dz, -0.08, 0.0)
    fl = col_mix(nt, "#0d1316", fl, below)
    xc = col_mix(nt, fl, "#020406", XR)
    bg = node(nt, "ShaderNodeBackground")
    link(nt, xc, bg.inputs[0])
    link(nt, BGS, bg.inputs[1])
    link(nt, bg.outputs[0], out.inputs["Surface"])
    return w


# ----------------------------------------------------------------------------------------------- geometry

def bm_arcbox(bm, r0, r1, z0, z1, p0, p1, n=96, rr=0.6, M=None):
    """a curved box: radius r0..r1, height z0..z1, angle p0..p1 (deg), rounded section corners"""
    prof = fillet([(r0, z0), (r1, z0), (r1, z1), (r0, z1)], rr, 4)
    rings = []
    for k in range(n + 1):
        a = rad(lerp(p0, p1, k / n))
        rings.append([V(p.x * math.cos(a), p.x * math.sin(a), p.y) for p in prof])
    vs = bm_loft(bm, rings)
    fs = list({f for ring in vs for v in ring for f in v.link_faces})
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    if M is not None:
        for ring in vs:
            for v in ring:
                v.co = M @ v.co


def build_gate(name, M, parent):
    """one gate in its tilt frame: shell, inner ribs, top rail, chamber walls and the fill"""
    obs = {}
    z0, z1 = ZB_FLOAT, ZB_FLOAT + GH
    bm = bmesh.new()
    bm_arcbox(bm, R - GD / 2, R + GD / 2, z0, z1, -PSI, PSI, 220, 0.9)
    obs["shell"] = obj_from_bm(name + "Shell", bm, M["gate"], parent, smooth=True)
    weighted(obs["shell"])
    bm = bmesh.new()   # vertical ribs on the inner (truss) face
    for k in range(17):
        p = lerp(-PSI + 0.6, PSI - 0.6, k / 16)
        bm_arcbox(bm, R - GD / 2 - 1.1, R - GD / 2 + 0.2, z0 + 0.6, z1 - 0.6, p - 0.12, p + 0.12, 2, 0.25)
    for zz in (z0 + 4.0, z1 - 3.0):        # two horizontal walers
        bm_arcbox(bm, R - GD / 2 - 0.9, R - GD / 2 + 0.2, zz - 0.5, zz + 0.5, -PSI + 0.3, PSI - 0.3, 160, 0.25)
    obs["ribs"] = obj_from_bm(name + "Ribs", bm, M["gate"], parent, smooth=True)
    bm = bmesh.new()   # white top band
    bm_arcbox(bm, R - GD / 2 - 0.05, R + GD / 2 + 0.05, z1 - 1.4, z1 + 0.05, -PSI - 0.02, PSI + 0.02, 220, 0.3)
    obs["band"] = obj_from_bm(name + "Band", bm, M["truss"], parent, smooth=True)
    bm = bmesh.new()   # deck railing
    for rr in (R - GD / 2 + 0.6, R + GD / 2 - 0.6):
        pts = [gpt(lerp(-PSI + 0.3, PSI - 0.3, k / 120), rr, z1 + 1.1) for k in range(121)]
        bm_tube(bm, pts, 0.07, 6)
        for k in range(0, 121, 3):
            p = pts[k]
            bm_rod(bm, p - V(0, 0, 1.1), p, 0.05, 5)
    obs["rail"] = obj_from_bm(name + "Rail", bm, M["rail"], parent, smooth=True)
    bm = bmesh.new()   # lamps along the deck
    for k in range(9):
        p = gpt(lerp(-PSI + 1.0, PSI - 1.0, k / 8), R, z1 + 0.6)
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.35, matrix=Matrix.Translation(p))
    obs["lamps"] = obj_from_bm(name + "Lamps", bm, M["lamp"], parent, smooth=True)
    bm = bmesh.new()   # chambers (only seen in x-ray): radial bulkheads and a mid deck
    for k in range(1, 8):
        p = lerp(-PSI, PSI, k / 8)
        bm_arcbox(bm, R - GD / 2 + 0.3, R + GD / 2 - 0.3, z0 + 0.3, z1 - 0.3, p - 0.06, p + 0.06, 1, 0.05)
    bm_arcbox(bm, R - GD / 2 + 0.3, R + GD / 2 - 0.3, z0 + 9.5, z0 + 9.8, -PSI + 0.2, PSI - 0.2, 120, 0.05)
    obs["walls"] = obj_from_bm(name + "Walls", bm, M["xwall"], parent)
    bm = bmesh.new()
    bm_arcbox(bm, R - GD / 2 + 0.4, R + GD / 2 - 0.4, z0 + 0.4, z1 - 0.4, -PSI + 0.15, PSI - 0.15, 160, 0.3)
    obs["fill"] = obj_from_bm(name + "Fill", bm, M["fill"], parent)
    return obs


def build_truss(name, M, parent):
    """the white tubular truss from the knuckle at the ball to the gate's inner face"""
    bm = bmesh.new()
    rin = R - GD / 2 - 1.0
    ztop, zlow = ZB_FLOAT + GH - 2.5, ZB_FLOAT + GH - 11.0
    knuck = V(7.0, 0, ZJ)
    chords = []
    for ps in (-PSI + 2.5, PSI - 2.5):
        A = gpt(ps, rin, 0)
        d = (A - V(0, 0, 0)).normalized()
        s = V(-d.y, d.x, 0)
        cs = []
        for oz, os_ in ((ztop, -4.0), (ztop, 4.0), (zlow, -4.0), (zlow, 4.0)):
            p1 = V(A.x, A.y, 0) + s * os_ + V(0, 0, oz)
            p0 = knuck + s * (os_ * 0.25) + V(0, 0, (oz - ZJ) * 0.25) + d * 4.0
            cs.append((p0, p1))
            bm_rod(bm, p0, p1, 1.0, 16)
        chords.append(cs)
        n = 13
        for k in range(1, n + 1):
            u0, u1 = (k - 1) / n, k / n
            P = [[p0.lerp(p1, u) for p0, p1 in cs] for u in (u0, u1)]
            for a, b in ((0, 1), (2, 3), (0, 2), (1, 3)):          # diagonals on the four faces
                bm_rod(bm, P[0][a], P[1][b], 0.42, 10)
            for a, b in ((0, 1), (2, 3), (0, 2), (1, 3)):          # rings
                bm_rod(bm, P[1][a], P[1][b], 0.36, 10)
    # lattice between the two arms
    L, Rr = chords
    n = 9
    for k in range(1, n + 1):
        u0, u1 = (k - 0.5) / (n + 0.5), (k + 0.5) / (n + 0.5)
        for zi in (0, 2):
            a = L[zi][0].lerp(L[zi][1], u0)
            b = Rr[zi + 1][0].lerp(Rr[zi + 1][1], u1)
            bm_rod(bm, a, b, 0.5, 10)
            c = Rr[zi + 1][0].lerp(Rr[zi + 1][1], u0)
            d = L[zi][0].lerp(L[zi][1], u1)
            bm_rod(bm, c, d, 0.5, 10)
    ob = obj_from_bm(name, bm, M["truss"], parent, smooth=True)
    bm = bmesh.new()   # the yoke that grips the ball: a collar round its upper half and a block the chords meet
    bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=4.75)
    ring = [v for v in bm.verts]
    prof = fillet([(4.3, ZJ + 1.0), (6.2, ZJ + 1.0), (6.2, ZJ + 3.4), (3.4, ZJ + 3.4)], 0.4, 4)
    for v in ring:
        bm.verts.remove(v)
    rings = []
    for k in range(97):
        a = 2 * math.pi * k / 96
        rings.append([V(p.x * math.cos(a), p.x * math.sin(a), p.y) for p in prof])
    bm_loft(bm, rings)
    bm_rbox(bm, (9.5, 0, ZJ + 1.0), (9.0, 9.0, 7.0), r=1.2, segs=4)
    head = obj_from_bm(name + "Head", bm, M["truss"], parent, smooth=True)
    weighted(head)
    return ob, head


def build_joint(name, M, J, side):
    """the ball (on the moving frame) and its concrete foundation block (fixed)"""
    bm = bmesh.new()
    bm_rbox(bm, (0, 0, -4.0), (26.0, 30.0, 18.0), r=1.0, segs=4)
    base = obj_from_bm(name + "Base", bm, M["conc"], None, J + V(-4.0 * 0 - 6.0, 0, 0), smooth=True)
    bm = bmesh.new()
    bm_cyl(bm, 7.6, 6.6, 3.0, 96, Matrix.Translation(V(0, 0, 5.5)))
    seat = obj_from_bm(name + "Seat", bm, M["steel"], None, J, smooth=True)
    weighted(seat)
    return base, seat


XDOCK = []
DOCKX = []


def build_land(M):
    """both banks as slabs, with the curved dock slots cut out by booleans"""
    obs = []
    for side, J in ((1, JN), (-1, JS)):
        bm = bmesh.new()
        bm_box(bm, (0, side * (CH + 3000), (ZL - 30) / 2), (12000.0, 6000.0, ZL + 30))
        land = obj_from_bm("Land" + ("N" if side > 0 else "S"), bm, M["land"])
        bm = bmesh.new()
        r0, r1 = R - GD / 2 - 9.0, R + GD / 2 + 9.0
        th0, th1 = TH_C + PARK - PSI - 3.0, 190.0
        bm_arcbox(bm, r0, r1, ZB_DOCK, ZL + 20, th0, th1, 140, 0.0)
        if side < 0:
            for v in bm.verts:
                v.co.y = -v.co.y
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        cut = obj_from_bm("Cut", bm, None, None, J)
        bm = bmesh.new()
        bm_arcbox(bm, r0, r1, ZB_DOCK, ZL, th0, 185.0, 140, 0.3)
        if side < 0:
            for v in bm.verts:
                v.co.y = -v.co.y
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        gh = obj_from_bm("XDock" + ("N" if side > 0 else "S"), bm, M["xdock"], None, J)
        gh.hide_render = True
        XDOCK.append(gh)
        bm = bmesh.new()       # the joint pit
        bm_cyl(bm, 30.0, 30.0, 40.0, 96, Matrix.Translation(V(0, 0, 10.0)))
        pit = obj_from_bm("Pit", bm, None, None, J + V(-6, 0, -4.0))
        for c in (cut, pit):
            md = land.modifiers.new("B", "BOOLEAN")
            md.operation = "DIFFERENCE"
            md.solver = "EXACT"
            md.object = c
            bpy.context.view_layer.objects.active = land
            bpy.ops.object.modifier_apply(modifier="B")
            bpy.data.objects.remove(c)
        bv = land.modifiers.new("Bv", "BEVEL")
        bv.width, bv.segments, bv.limit_method = 0.4, 3, "ANGLE"
        weighted(land)
        obs.append(land)
    bm = bmesh.new()
    bm_box(bm, (0, 0, SILL - 1.0), (6000.0, 2 * CH + 40, 2.0))
    obs.append(obj_from_bm("Bed", bm, M["bed"]))
    bm = bmesh.new()
    for sgn in (1, -1):
        M_ = Matrix.Translation(JN if sgn > 0 else JS) @ (Matrix.Scale(-1, 4, V(0, 1, 0)) if sgn < 0 else Matrix())
        bm_arcbox(bm, R - GD / 2 - 6, R + GD / 2 + 6, SILL - 2.0, SILL, TH_C - PSI - 1.0, TH_C + PSI + 1.0, 120, 0.4,
                  M=M_)
    obs.append(obj_from_bm("Sill", bm, M["conc"], smooth=True))
    return obs


def build_sea(M):
    """the river surface: a 2.5 m grid between the quays, displaced by an ocean modifier (with foam)"""
    bm = bmesh.new()
    x0, x1, y0, y1, st = -1100.0, 1300.0, -CH - 2.0, CH + 2.0, 2.5
    nx, ny = int((x1 - x0) / st) + 1, int((y1 - y0) / st) + 1
    vs = [bm.verts.new((x0 + i * st, y0 + j * st, 0.0)) for j in range(ny) for i in range(nx)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    sea = obj_from_bm("Sea", bm, M["water"], smooth=True)
    oc = sea.modifiers.new("Ocean", "OCEAN")
    oc.geometry_mode = "DISPLACE"
    oc.resolution = 9
    oc.spatial_size = 160
    oc.wave_scale = 1.6
    oc.choppiness = 1.3
    oc.wind_velocity = 22.0
    oc.wave_alignment = 0.6
    oc.wave_direction = 0.0
    oc.random_seed = 7
    oc.use_foam = True
    oc.foam_layer_name = "foam"
    oc.foam_coverage = 0.25
    oc.time = 0.0
    bm = bmesh.new()       # far water beyond the grid's ends, out to the horizon (bump only)
    bm_box(bm, (-1098.0 - 30000.0, 0, -0.5), (60000.0, 60000.0, 0.2))
    bm_box(bm, (1298.0 + 4000.0, 0, -0.5), (8000.0, 2 * CH + 4, 0.2))
    far = obj_from_bm("FarSea", bm, M["water"])
    bm = bmesh.new()       # the water inside each dock, raised as it floods
    docks = []
    for side, J in ((1, JN), (-1, JS)):
        bm = bmesh.new()
        bm_arcbox(bm, R - GD / 2 - 8.9, R + GD / 2 + 8.9, 0.0, -ZB_DOCK, TH_C + PARK - PSI - 2.9, 184.0, 120, 0.0)
        if side < 0:
            for v in bm.verts:
                v.co.y = -v.co.y
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        d = obj_from_bm("Dock" + ("N" if side > 0 else "S"), bm, M["dockwater"], None, J)
        docks.append(d)
        dx = bpy.data.objects.new(d.name + "X", d.data.copy())     # its x-ray twin: glowing blue water
        dx.data.materials.clear()
        dx.data.materials.append(M["dockfill"])
        bpy.context.scene.collection.objects.link(dx)
        dx.location = d.location
        dx.hide_render = True
        DOCKX.append(dx)
    return sea, far, docks


def build_gauge(M):
    """a tide staff by the north quay near the sea: a white post with metre marks and a red band at +3 m"""
    root = empty("Gauge", GAUGE)
    bm = bmesh.new()
    bm_rbox(bm, (0, 0, -3.0), (0.9, 0.5, 14.0), r=0.08, segs=3)
    obj_from_bm("GaugePost", bm, M["gaugepost"], root, smooth=True)
    bm = bmesh.new()
    for k in range(-2, 4):
        bm_rbox(bm, (0, -0.27, k), (1.0, 0.06, 0.1), r=0.02, segs=2)
        for j in range(1, 10):
            if j == 5:
                bm_rbox(bm, (0.18, -0.27, k + j / 10), (0.55, 0.05, 0.05), r=0.01, segs=1)
            else:
                bm_rbox(bm, (0.3, -0.27, k + j / 10), (0.3, 0.05, 0.035), r=0.01, segs=1)
    obj_from_bm("GaugeMarks", bm, M["ink"], root, smooth=True)
    bm = bmesh.new()
    bm_rbox(bm, (0, 0, 3.0), (0.96, 0.56, 0.35), r=0.05, segs=2)
    obj_from_bm("GaugeRed", bm, M["red"], root, smooth=True)
    for k in range(0, 4):
        t = text("GaugeN%d" % k, str(k), 0.55, V(-0.22, -0.31, k + 0.45), (rad(90), 0, 0), M["ink"], root, 0.02)
    bm = bmesh.new()       # a mooring dolphin it is bolted to
    bm_cyl(bm, 1.6, 1.6, 22.0, 48, Matrix.Translation(V(0.0, 1.4, -8.0)))
    obj_from_bm("GaugePile", bm, M["conc"], root, smooth=True)
    return root


def build_rain(M, n=4500, seed=3):
    """rain streaks in a box round the camera (parented to it in the shots)"""
    random.seed(seed)
    bm = bmesh.new()
    for _ in range(n):
        p = V(random.uniform(-14, 14), random.uniform(-25, 25), random.uniform(-60, -2))
        L = random.uniform(0.4, 0.9)
        w = random.uniform(0.004, 0.008)
        for ex, ey in ((w, 0), (0, w)):                  # crossed, so it reads from any side
            a = bm.verts.new(p + V(-ex, -ey, -L / 2))
            b = bm.verts.new(p + V(ex, ey, -L / 2))
            c = bm.verts.new(p + V(ex, ey, L / 2))
            d = bm.verts.new(p + V(-ex, -ey, L / 2))
            bm.faces.new((a, b, c, d))
    return obj_from_bm("Rain", bm, M["rain"])


def build_bolt(M, seed=11):
    """a lightning bolt: a jagged main channel from the cloud base to the sea with a few forks"""
    random.seed(seed)
    bm = bmesh.new()

    def channel(p, n, step, spread, r):
        pts = [p]
        for _ in range(n):
            p = p + V(random.gauss(0, spread), random.gauss(0, spread * 0.5), -step * random.uniform(0.6, 1.3))
            pts.append(p)
        bm_tube(bm, pts, r, 6)
        return pts

    main = channel(V(0, 0, 720), 40, 18.0, 9.0, 1.6)
    for k in (8, 15, 24):
        channel(main[k], 9, 14.0, 12.0, 0.8)
    return obj_from_bm("Bolt", bm, M["bolt"])


def sb_materials():
    M = {}
    M["gate"] = paint_mat("Gate", "#5d646c", 0.34, 0.5, 0.35, seams=0.6)
    M["truss"] = paint_mat("Truss", "#e9e8e2", 0.22, 0.8, 0.15)
    M["rail"] = paint_mat("RailM", "#d9d7cf", 0.4, 0.0, 0.1)
    M["lamp"] = emis("Lamp", "#ffcf8a", 30.0)
    M["xwall"] = ghost_mat("XWall", "#7fe0ff", 1.4, 0.05)
    M["xdock"] = ghost_mat("XDock", "#5fd0ff", 1.2, 0.03)
    M["fill"] = fill_mat()
    M["dockfill"] = fill_mat()
    M["dockfill"].name = "DockFill"
    M["dockfill"].node_tree.nodes["FH"].outputs[0].default_value = 100.0
    M["water"] = water_mat()
    M["dockwater"] = water_mat("DockWater", 1.0, 0.3, "#2f8fff")
    M["land"] = land_mat()
    M["conc"] = paint_mat("Concrete", "#8a8780", 0.8, 0.0, 0.45)
    M["bed"] = pbr("Bed", "#1d1a16", 0.95)
    M["steel"] = pbr("Steel", "#9aa0a6", 0.18, 1.0)
    M["ball"] = paint_mat("Ball", "#d5d9dc", 0.2, 0.6, 0.05)
    M["gaugepost"] = paint_mat("GaugePostM", "#f1efe8", 0.4, 0.3, 0.2)
    M["ink"] = pbr("Ink", "#101114", 0.5)
    M["red"] = pbr("RedBand", "#d92b1e", 0.35, 0.0, emit="#ff3020", estr=0.0)
    nt = M["red"].node_tree
    link(nt, val(nt, "S", 0.0), nt.nodes["Principled BSDF"].inputs["Emission Strength"])
    M["rain"] = emis("RainM", "#cfe0ee", 0.0, alpha=0.22)
    M["bolt"] = emis("BoltM", "#e4ecff", 0.0)
    return M


def haze_box(c, s):
    m, nt, out = new_mat("Haze")
    v = node(nt, "ShaderNodeVolumeScatter")
    v.inputs["Color"].default_value = (*lin("#c3ccd4"), 1)
    v.inputs["Anisotropy"].default_value = 0.35
    link(nt, val(nt, "HZ", 0.0006), v.inputs["Density"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    bm = bmesh.new()
    bm_box(bm, c, s)
    return obj_from_bm("HazeBox", bm, m)


def spot(name, loc, tgt, col, energy, size=1.0, angle=40.0):
    ld = bpy.data.lights.new(name, "SPOT")
    ld.color = lin(col)
    ld.energy = energy
    ld.shadow_soft_size = size
    ld.spot_size = rad(angle)
    ld.spot_blend = 0.6
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y")
    return ob


def build_sb():
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    M = sb_materials()
    world = storm_world()
    land = build_land(M)
    sea, far, docks = build_sea(M)
    G = {}
    for side, J in ((1, JN), (-1, JS)):
        k = "N" if side > 0 else "S"
        root = empty("Root" + k, J)
        root.scale = (1.0, float(side), 1.0)
        piv = empty("Piv" + k, (0, 0, 0), root)
        ori = empty("Ori" + k, (0, 0, 0), piv)
        ori.rotation_euler = (0, 0, rad(TH_C))
        tilt = empty("Tilt" + k, (0, 0, ZJ), ori)
        geo = empty("Geo" + k, (0, 0, -ZJ), tilt)
        g = build_gate("Gate" + k, M, geo)
        tr, head = build_truss("Truss" + k, M, geo)
        ball = sphere("Ball" + k, 5.0, (0, 0, ZJ), M["ball"], geo, seg=64)
        base, seat = build_joint("Joint" + k, M, J, side)
        G[k] = dict(root=root, piv=piv, tilt=tilt, geo=geo, truss=tr, head=head, ball=ball, base=base, seat=seat, **g)
    gauge = build_gauge(M)
    rain = build_rain(M)
    bolt = build_bolt(M)
    haze = haze_box((0, 0, 140), (9000.0, 9000.0, 300.0))
    sd = V(-0.94, 0.25, 0.22).normalized()
    sun = sun_lamp(V(-sd.x, -sd.y, -sd.z) * -1, 1.2, "#b9c6d4", angle=3.0)
    flash = sun_lamp(V(0.3, -0.5, 1.0), 0.0, "#cfe0ff", angle=8.0)
    flash.name = "Flash"
    floods = []
    for side, J in ((1, JN), (-1, JS)):
        for off, tg in ((V(-30, 30 * side, 18), V(-120, -60 * side, 8)), (V(40, -10 * side, 22), V(-60, -110 * side, 10)),
                        (V(-10, -25 * side, 16), V(0, 0, 6))):
            floods.append(spot("Flood", J + off, J + tg, "#ffc98a", 3e5, 2.0, 70.0))
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.05, 60000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    return dict(M=M, world=world, land=land, sea=sea, far=far, docks=docks, G=G, gauge=gauge, rain=rain, haze=haze, bolt=bolt,
                sun=sun, flash=flash, floods=floods, cam=camo, hero=None)
