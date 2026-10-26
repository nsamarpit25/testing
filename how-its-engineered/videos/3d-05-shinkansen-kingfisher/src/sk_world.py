# ----------------------------------------------------------------------------------------------- Shinkansen world
# A terraced valley at golden hour: a slab track on a low viaduct runs along +x, through a mountain ridge in a
# 360 m tunnel (portals at x = 0 and x = 360, with slanted concrete hoods), past a few houses below the exit and on
# towards a second ridge. Metres; rail top at z = ZR. The river set (RV) and the studio set (ST) sit far away.
import mathutils.noise as mn

T_END = 33.0
F_END = int(T_END * FPS) + 1
ZR = 8.5                              # rail top
X0T, X1T = 0.0, 360.0                 # tunnel portals
HOOD = 12.0                           # hood length outside each portal
RT, ZT = 5.0, ZR + 1.2                # tunnel radius and centre height
RV = Vector((0.0, 4000.0, 0.0))       # river set
ST = Vector((0.0, -4000.0, 0.0))      # studio set
HOUSES = [(640, -118, 12), (668, -96, 40), (700, -132, 5), (722, -90, 30), (752, -120, 18), (690, -70, 55),
          (740, -60, 8), (780, -100, 60), (660, 92, 15), (700, 118, 48), (735, 86, 20), (770, 126, 5)]


def bmh(bm, c, half):
    """box from its centre and half-sizes"""
    bm_box(bm, c, tuple(2 * h for h in half))


def sstepv(nt, x, e0, e1):
    """smoothstep with edges that may be sockets"""
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


def bm_torus(bm, M, R, r, nu=40, nv=6):
    """torus in the local y-z plane (axis x) under matrix M"""
    vs = [[bm.verts.new(M @ V(r * math.sin(b), (R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a)))
           for b in (2 * math.pi * j / nv for j in range(nv))] for a in (2 * math.pi * i / nu for i in range(nu))]
    for i in range(nu):
        for j in range(nv):
            a, b = vs[i], vs[(i + 1) % nu]
            bm.faces.new((a[j], b[j], b[(j + 1) % nv], a[(j + 1) % nv]))


def nz(x, y, s, seed=0.0):
    return mn.noise(V(x / s, y / s, seed), noise_basis='PERLIN_ORIGINAL')


def mountain(x, y):
    """two ridges across the valley: the tunnel ridge and a taller one far down the line"""
    r1 = 150.0 * math.exp(-((x - 180.0) / 170.0) ** 2) * (0.8 + 0.2 * nz(x, y, 210.0, 1.0))
    r2 = 230.0 * math.exp(-((x - 1400.0) / 220.0) ** 2) * (0.8 + 0.2 * nz(x, y, 260.0, 2.0))
    return r1 + r2


def ground(x, y):
    base = 3.0 + 3.0 * mn.fractal(V(x / 300.0, y / 300.0, 0.4), 0.8, 2.0, 4, noise_basis='PERLIN_ORIGINAL')
    side = 70.0 * clamp((abs(y) - 230.0) / 420.0) ** 1.5 * (0.7 + 0.3 * nz(x, y, 180.0, 3.0))
    m = mountain(x, y)
    z = base + side + m + 12.0 * abs(nz(x, y, 55.0, 4.0)) * clamp(m / 60.0)
    # rice terraces on the low slopes: quantised height with a soft riser
    h = 0.9
    q = z / h
    zt = h * (math.floor(q) + clamp((q - math.floor(q) - 0.82) / 0.18))
    z = lerp(zt, z, clamp((z - 22.0) / 10.0))
    # the track corridor: open cuttings at the portals, low ground under the viaduct
    out = clamp((X0T + 2.0 - x) / 8.0) + clamp((x - X1T + 2.0) / 8.0)
    c = clamp((abs(y) - 8.0) / 24.0)
    c = c * c * (3 - 2 * c)
    z = lerp(min(z, ZR - 2.5), z, 1.0 - (1.0 - c) * clamp(out))
    return z


def terrain_mat():
    m, nt, out = new_mat("Terrain")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    geo = node(nt, "ShaderNodeNewGeometry")
    _, _, nzc = xyz(nt, geo.outputs["Normal"])
    n1 = noise(nt, P, 0.02, 5.0, 0.6)
    n2 = noise(nt, P, 0.25, 4.0, 0.6)
    rice = col_mix(nt, "#8f8a3a", "#b49a45", n1)                          # ripening paddies, gold-green
    forest = col_mix(nt, "#1d2a17", "#34401f", n2)
    rock = col_mix(nt, "#5b5248", "#7d7062", n2)
    lo = sstep(nt, z, 18.0, 34.0)
    c = col_mix(nt, rice, forest, lo)
    c = col_mix(nt, c, rock, inv(nt, sstep(nt, nzc, 0.55, 0.75)))
    edge = mul(nt, inv(nt, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", z, 0.9)), 0.0, 0.12)), inv(nt, lo))
    c = col_mix(nt, c, "#4a4626", mth(nt, "MULTIPLY", edge, 0.35))
    b = principled(nt, c, 0.85, 0.0)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    link(nt, n2, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def terrain(mat, x0=-1300.0, x1=1700.0, y0=-800.0, y1=800.0, step=4.0):
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    bm = bmesh.new()
    vs = [bm.verts.new((x0 + i * step, y0 + j * step, ground(x0 + i * step, y0 + j * step)))
          for j in range(ny) for i in range(nx)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    return obj_from_bm("Terrain", bm, mat, smooth=True)


def concrete(name, col="#b9b4aa"):
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    n = noise(nt, P, 0.3, 5.0, 0.6)
    st = noise(nt, P, 0.6, 3.0, 0.5, stretch=(1.0, 1.0, 0.1))
    c = col_mix(nt, col, "#8a857b", mth(nt, "MULTIPLY", mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", st, 0.5), 0.0), 2.5))
    c = col_mix(nt, c, "#a39e93", mth(nt, "MULTIPLY", n, 0.4))
    b = principled(nt, c, 0.8, 0.0)
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def tube_ring(x, r, n=48, slant=0.0):
    """tunnel cross-section: a circle with a flat floor, the end sheared back with height for the hood face"""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        y, z = r * math.cos(a), ZT + r * math.sin(a)
        z = max(z, ZR - 0.6)
        pts.append(V(x + slant * (z - ZR), y, z))
    return pts


def tunnel_mats():
    """inside: dark concrete with a strip of lamps; XA turns the shell to x-ray glass with cyan edges"""
    m, nt, out = new_mat("Tunnel")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    XA = val(nt, "XA", 0.0)
    b = principled(nt, col_mix(nt, "#5c5953", "#77736a", noise(nt, P, 0.4, 4.0)), 0.85, 0.0)
    lamp = mul(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", y, 3.7)), 0.0, 0.14),
               inv(nt, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", x, 9.0)), 0.25, 0.3)),
               sstep(nt, z, ZT + 2.3, ZT + 2.4), inv(nt, sstep(nt, z, ZT + 2.7, ZT + 2.8)))
    sh = node(nt, "ShaderNodeAddShader")
    link(nt, b.outputs[0], sh.inputs[0])
    link(nt, emission(nt, "#ffd7a0", mth(nt, "MULTIPLY", lamp, 6.0)), sh.inputs[1])
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.25
    edge = emission(nt, "#4fd8ff", mth(nt, "MULTIPLY", mth(nt, "POWER", lw.outputs["Facing"], 3.0), 0.8))
    tr = node(nt, "ShaderNodeBsdfTransparent")
    xr = node(nt, "ShaderNodeAddShader")
    link(nt, tr.outputs[0], xr.inputs[0])
    link(nt, edge, xr.inputs[1])
    link(nt, mix_sh(nt, XA, sh.outputs[0], xr.outputs[0]), out.inputs["Surface"])
    return m


def build_tunnel(mt):
    """the bore (x = -HOOD .. X1T + HOOD) as one thick shell; the hood ends are cut on a slant"""
    bm = bmesh.new()
    xs = [X0T - HOOD] + [X0T + 4.0 * i for i in range(int((X1T - X0T) / 4.0) + 1)] + [X1T + HOOD]
    inner, outer = [], []
    for k, x in enumerate(xs):
        sl = -0.9 if k == 0 else (0.9 if k == len(xs) - 1 else 0.0)
        inner.append([bm.verts.new(p) for p in tube_ring(x, RT, slant=sl)])
        outer.append([bm.verts.new(p) for p in tube_ring(x + (0.0 if sl == 0 else 0.0), RT + 0.6, slant=sl)])
    n = len(inner[0])
    for a, b in zip(inner, inner[1:]):
        for i in range(n):
            bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))
    for a, b in zip(outer, outer[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    for r_in, r_out in ((inner[0], outer[0]), (inner[-1], outer[-1])):
        for i in range(n):
            bm.faces.new((r_in[i], r_in[(i + 1) % n], r_out[(i + 1) % n], r_out[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm("Tunnel", bm, mt, smooth=True)


def rings_mat():
    """air rings in the bore, lit by the pressure: calm air faint cyan, squeezed air amber to red, the wavefront a
    bright band at WX (width WW, height AMP); NC adds the pile-up against the nose at NX"""
    m, nt, out = new_mat("Rings")
    x, _, _ = xyz(nt, obj_co(nt))
    NX, WX, WW, AMP, NC = (val(nt, k, v) for k, v in (("NX", -500.0), ("WX", -500.0), ("WW", 4.0), ("AMP", 0.0),
                                                      ("NC", 0.0)))
    ahead = mth(nt, "SUBTRACT", x, NX)
    front = mth(nt, "SUBTRACT", x, WX)
    plateau = mul(nt, sstepv(nt, ahead, -0.5, 0.5), inv(nt, sstepv(nt, front, mth(nt, "MULTIPLY", WW, -1.0), 0.0)),
                  AMP, 0.5)
    sig = mth(nt, "ADD", mth(nt, "MULTIPLY", WW, 0.3), 0.5)
    band = mth(nt, "EXPONENT", mth(nt, "MULTIPLY", mth(nt, "POWER", mth(nt, "DIVIDE", front, sig), 2.0), -1.0))
    band = mul(nt, band, AMP)
    pile = mul(nt, mth(nt, "EXPONENT", mth(nt, "MULTIPLY", mth(nt, "POWER", mth(nt, "DIVIDE", ahead, 4.0), 2.0), -1.0)),
               sstepv(nt, ahead, -0.5, 0.3), NC)
    p = mth(nt, "MINIMUM", mth(nt, "MAXIMUM", mth(nt, "MAXIMUM", plateau, band), pile), 1.2)
    col = ramp3(nt, p, [(0.0, "#2fd6ff"), (0.3, "#7fc6c0"), (0.5, "#ffa12a"), (0.8, "#ff3a12"), (1.0, "#ff8a5a")])
    link(nt, emission(nt, col, mth(nt, "ADD", 0.3, mth(nt, "MULTIPLY", p, 3.2))), out.inputs["Surface"])
    return m


def build_rings(mat):
    bm = bmesh.new()
    x = X0T - HOOD + 0.5
    while x < X1T + HOOD:
        bm_torus(bm, Matrix.Translation(V(x, 0, ZT)), RT - 0.55, 0.035, 40, 5)
        x += 1.0
    return obj_from_bm("Rings", bm, mat, smooth=True)


def build_track(mc, mrail, mwire):
    """viaduct deck and piers, slab track, rails, catenary masts and the contact wire"""
    bm = bmesh.new()
    spans = [(-1300.0, X0T - HOOD), (X1T + HOOD, 1700.0)]
    for a, b in spans:
        bmh(bm, ((a + b) / 2, 0, ZR - 1.1), ((b - a) / 2, 6.0, 0.7))           # deck
        bmh(bm, ((a + b) / 2, 0, ZR - 0.3), ((b - a) / 2, 1.5, 0.12))          # slab
        for s in (-1, 1):
            bmh(bm, ((a + b) / 2, s * 5.9, ZR - 0.1), ((b - a) / 2, 0.12, 0.55))  # parapets
        x = a + 15.0
        while x < b:
            g = ground(x, 0.0)
            if g < ZR - 2.2:
                bmh(bm, (x, 0, (g + ZR - 1.8) / 2 - 1.0), (1.2, 3.2, (ZR - 1.8 - g) / 2 + 1.0))
            x += 30.0
    deck = obj_from_bm("Deck", bm, mc)
    bm = bmesh.new()
    bmh(bm, (200.0, 0.7175, ZR - 0.08), (1500.0, 0.035, 0.08))
    bmh(bm, (200.0, -0.7175, ZR - 0.08), (1500.0, 0.035, 0.08))
    rails = obj_from_bm("Rails", bm, mrail)
    bm = bmesh.new()
    x = -1290.0
    while x < 1700.0:
        if not (X0T - HOOD - 5 < x < X1T + HOOD + 5):
            bm_rod(bm, (x, 5.4, ZR - 0.4), (x, 5.4, ZR + 6.4), 0.14, 10)
            bm_rod(bm, (x, 5.4, ZR + 6.0), (x, -0.4, ZR + 6.0), 0.06, 8)
            bm_rod(bm, (x, 0.0, ZR + 6.0), (x, 0.0, ZR + 5.15), 0.03, 6)
        x += 50.0
    masts = obj_from_bm("Masts", bm, mrail)
    bm = bmesh.new()
    bm_rod(bm, (-1300.0, 0.0, ZR + 5.1), (1700.0, 0.0, ZR + 5.1), 0.012, 6)
    bm_rod(bm, (-1300.0, 0.0, ZR + 6.0), (1700.0, 0.0, ZR + 6.0), 0.01, 6)
    wire = obj_from_bm("Wire", bm, mwire)
    return [deck, rails, masts, wire]


def build_trees(mat, n=4200, seed=11):
    random.seed(seed)
    bm = bmesh.new()
    k = 0
    while k < n:
        x, y = random.uniform(-1250, 1650), random.uniform(-760, 760)
        if abs(y) < 26 or (600 < x < 800 and abs(y) < 160):
            continue
        z = ground(x, y)
        if z < 20.0 and random.random() < 0.8:                     # mostly on the slopes, a few by the paddies
            continue
        h = random.uniform(9.0, 16.0)
        r = h * random.uniform(0.2, 0.26)
        for j, (f0, f1, rr) in enumerate(((0.0, 0.42, 1.0), (0.2, 0.6, 0.84), (0.4, 0.76, 0.66), (0.58, 0.9, 0.48),
                                          (0.74, 1.0, 0.3))):
            rr *= random.uniform(0.85, 1.1)
            bm_cyl(bm, r * rr, 0.0, h * (f1 - f0), 14,
                   Matrix.Translation(V(x, y, z - 0.5 + h * (f0 + f1) / 2 + 1.2)))
        k += 1
    return obj_from_bm("Trees", bm, mat, smooth=True)


def tree_mat():
    m, nt, out = new_mat("Tree")
    P = obj_co(nt)
    c = col_mix(nt, "#14200f", "#2b3a1a", noise(nt, P, 0.6, 4.0))
    b = principled(nt, c, 0.9, 0.0)
    b.inputs["Subsurface Weight"].default_value = 0.08
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def build_houses(mw, mr, mwin):
    bm, br, bw = bmesh.new(), bmesh.new(), bmesh.new()
    for x, y, rot in HOUSES:
        z = ground(x, y)
        R = Matrix.Translation(V(x, y, z)) @ Matrix.Rotation(rad(rot), 4, "Z")
        w, d, h = 9.0, 7.0, 5.2
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=R @ Matrix.Translation(V(0, 0, h / 2 - 0.5))
                                  @ Matrix.Diagonal((w, d, h + 1.0, 1)))
        # gable roof: a ridge prism
        v = [br.verts.new(R @ V(sx * (w / 2 + 0.5), sy * (d / 2 + 0.6), h)) for sx, sy in
             ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        r0, r1 = br.verts.new(R @ V(-w / 2 - 0.5, 0, h + 2.6)), br.verts.new(R @ V(w / 2 + 0.5, 0, h + 2.6))
        br.faces.new((v[0], v[1], r1, r0))
        br.faces.new((v[2], v[3], r0, r1))
        br.faces.new((v[1], v[2], r1))
        br.faces.new((v[3], v[0], r0))
        for sx in (-2.2, 2.2):
            bmesh.ops.create_cube(bw, size=1.0, matrix=R @ Matrix.Translation(V(sx, -d / 2 - 0.02, 2.4))
                                  @ Matrix.Diagonal((1.5, 0.08, 1.2, 1)))
    return [obj_from_bm("Houses", bm, mw), obj_from_bm("Roofs", br, mr), obj_from_bm("Windows", bw, mwin)]


def sky_studio_world(sun_el, sun_rot):
    """golden-hour sky, crossfaded (STU) to a dark studio backdrop with a soft pool of light; BG scales the sky"""
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
    sky = node(nt, "ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = rad(sun_el)
    sky.sun_rotation = rad(sun_rot)
    sky.altitude = 300
    sky.aerosol_density = 3.0
    bg = node(nt, "ShaderNodeBackground")
    bg.name = "BG"
    bg.inputs[1].default_value = 0.35
    link(nt, sky.outputs[0], bg.inputs[0])
    win = node(nt, "ShaderNodeTexCoord").outputs["Window"]
    wx, wy, _ = xyz(nt, win)
    dx = mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", wx, 0.5), 0.5625)
    dy = mth(nt, "SUBTRACT", wy, 0.56)
    d = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", dx, dx), mth(nt, "MULTIPLY", dy, dy)))
    grad = ramp3(nt, d, [(0.0, "#2c2e33"), (0.14, "#222428"), (0.30, "#121316"), (0.48, "#070809"), (0.7, "#020203")])
    st = node(nt, "ShaderNodeBackground")
    link(nt, grad, st.inputs[0])
    amb = node(nt, "ShaderNodeBackground")
    amb.inputs[0].default_value = (*lin("#1d1e21"), 1)
    amb.inputs[1].default_value = 0.18
    lp = node(nt, "ShaderNodeLightPath")
    studio = mix_sh(nt, lp.outputs["Is Camera Ray"], amb.outputs[0], st.outputs[0])
    link(nt, mix_sh(nt, val(nt, "STU", 0.0), bg.outputs[0], studio), out.inputs[0])
    return w
