# ----------------------------------------------------------------------------------------------- Mars sky crane world
# A rolling Martian plain at a low sun (Gale-crater mood: butterscotch sky, a far mountain to the north), the landing
# spot at the origin. Two heroes built in their own frames: the rover (origin on the ground under its centre, +x
# forward, real Curiosity scale: ~3 m long, wheels 0.5 m) and the descent stage (origin at the centre of its belly).
# A dark product studio (ST) sits far away for the airbag comparison. Metres, Z up.
import mathutils.noise as mn

T_END = 32.2
F_END = int(T_END * FPS) + 1
ST = Vector((20000.0, 0.0, 0.0))      # studio set
CR = Vector((-180.0, 620.0, 0.0))      # where the descent stage crashes (seen from the landing spot)
SUN_EL, SUN_AZ = 16.0, -62.0           # low sun, from the south-west of the camera's usual view
RW, WW = 0.25, 0.40                    # wheel radius / width
WX = (1.02, 0.02, -1.02)               # wheel stations along the rover
WY = 1.12                              # wheel centre offset (y)
PIV = V(-0.12, 0.60, 0.82)             # rocker pivot on the +y side of the body
DECK = 1.20                            # deck top height
HANG = 1.50                            # rover origin sits HANG below the stage belly when the bridles are in
ATT = [V(0.55 * math.cos(a), 0.55 * math.sin(a), 0) for a in (rad(90), rad(210), rad(330))]   # bridle points (xy)


def sstep(nt, x, e0, e1):
    """smoothstep(e0, e1, x); the edges may be numbers or sockets"""
    m = node(nt, "ShaderNodeMapRange", data_type="FLOAT", interpolation_type="SMOOTHSTEP")
    link(nt, x, m.inputs[0])
    for i, e in ((1, e0), (2, e1)):
        if isinstance(e, (int, float)):
            m.inputs[i].default_value = e
        else:
            link(nt, e, m.inputs[i])
    m.inputs[3].default_value = 0.0
    m.inputs[4].default_value = 1.0
    return m.outputs[0]


def sun_dir():
    return V(math.cos(rad(SUN_AZ)) * math.cos(rad(SUN_EL)), math.sin(rad(SUN_AZ)) * math.cos(rad(SUN_EL)),
             math.sin(rad(SUN_EL)))


def mars_world():
    """Mars sky: butterscotch at the horizon, darker rust overhead, a cold blue halo round the sun; STU crossfades to a
    dark studio backdrop with a soft pool of light; BG scales the sky"""
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
    gen = node(nt, "ShaderNodeTexCoord").outputs["Generated"]
    nrm = node(nt, "ShaderNodeVectorMath", operation="NORMALIZE")
    link(nt, gen, nrm.inputs[0])
    _, _, dz = xyz(nt, nrm.outputs[0])
    sky = ramp3(nt, mth(nt, "MULTIPLY_ADD", dz, 0.5, 0.5), [(0.0, "#2a1a12"), (0.47, "#6b4a36"), (0.5, "#d6a57c"),
                                                              (0.56, "#c08a62"), (0.72, "#8c5c40"), (1.0, "#4d3024")])
    dt = node(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
    link(nt, nrm.outputs[0], dt.inputs[0])
    dt.inputs[1].default_value = tuple(sun_dir())
    cosd = mth(nt, "MAXIMUM", dt.outputs["Value"], 0.0)
    halo = mth(nt, "POWER", cosd, 40.0)
    glow = mth(nt, "POWER", cosd, 6.0)
    disc = mth(nt, "MULTIPLY", sstep(nt, cosd, 0.99985, 0.99995), 60.0)
    c = col_mix(nt, sky, "#e9c39c", mth(nt, "MULTIPLY", glow, 0.45))
    c = col_mix(nt, c, "#b8d2f0", mth(nt, "MULTIPLY", halo, 0.85))
    c = col_mix(nt, c, "#ffffff", disc, mode="ADD")
    bg = node(nt, "ShaderNodeBackground")
    bg.name = "BG"
    link(nt, c, bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    win = node(nt, "ShaderNodeTexCoord").outputs["Window"]
    wx, wy, _ = xyz(nt, win)
    dx = mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", wx, 0.5), 0.5625)
    dy = mth(nt, "SUBTRACT", wy, 0.56)
    d = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", dx, dx), mth(nt, "MULTIPLY", dy, dy)))
    grad = ramp3(nt, d, [(0.0, "#2e2a28"), (0.14, "#232120"), (0.30, "#131212"), (0.48, "#070707"), (0.7, "#020202")])
    st = node(nt, "ShaderNodeBackground")
    link(nt, grad, st.inputs[0])
    amb = node(nt, "ShaderNodeBackground")
    amb.inputs[0].default_value = (*lin("#1f1d1c"), 1)
    amb.inputs[1].default_value = 0.18
    lp = node(nt, "ShaderNodeLightPath")
    studio = mix_sh(nt, lp.outputs["Is Camera Ray"], amb.outputs[0], st.outputs[0])
    link(nt, mix_sh(nt, val(nt, "STU", 0.0), bg.outputs[0], studio), out.inputs[0])
    return w


# ----------------------------------------------------------------------------------------------- terrain

def nz2(x, y, s, seed=0.0):
    return mn.noise(V(x / s, y / s, seed), noise_basis='PERLIN_ORIGINAL')


def ground(x, y):
    """rolling plain, soft dune swells and ripples near the landing spot, a mountain far to the north (+y)"""
    z = 4.0 * mn.fractal(V(x / 420.0, y / 420.0, 0.3), 0.8, 2.0, 4, noise_basis='PERLIN_ORIGINAL')
    z += 1.2 * mn.fractal(V(x / 70.0, y / 70.0, 1.7), 0.7, 2.0, 3, noise_basis='PERLIN_ORIGINAL')
    z += 0.28 * mn.fractal(V(x / 11.0, y / 11.0, 2.9), 0.6, 2.0, 3, noise_basis='PERLIN_ORIGINAL')
    rip = 0.035 * math.sin((x * 0.86 + y * 0.5) * 2 * math.pi / 1.4) * clamp(0.5 + nz2(x, y, 9.0, 4.0))
    z += rip
    d = (y - 5200.0) / 1700.0
    z += 1500.0 * math.exp(-(d * d) - ((x + 600.0) / 3800.0) ** 2) * (0.75 + 0.25 * nz2(x, y, 900.0, 5.0))
    z += 260.0 * clamp((abs(x) - 2600.0) / 2500.0) ** 1.6 * (0.6 + 0.4 * nz2(x, y, 700.0, 6.0))
    z -= ground0()
    return z


_G0 = []


def ground0():
    if not _G0:
        _G0.append(0.0)
        _G0[0] = ground(0.0, 0.0)
    return _G0[0]


def grid_obj(name, x0, x1, y0, y1, step, mat, sink=None):
    import numpy as np
    nx, ny = int(round((x1 - x0) / step)) + 1, int(round((y1 - y0) / step)) + 1
    xs = [x0 + i * step for i in range(nx)]
    ys = [y0 + j * step for j in range(ny)]
    co = []
    for y in ys:
        for x in xs:
            z = ground(x, y)
            if sink and abs(x) < sink and abs(y) < sink:
                z -= 0.6
            co += (x, y, z)
    idx = np.arange(nx * ny).reshape(ny, nx)
    q = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(nx * ny)
    me.vertices.foreach_set("co", co)
    nf = (nx - 1) * (ny - 1)
    me.loops.add(nf * 4)
    me.loops.foreach_set("vertex_index", q.tolist())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", list(range(0, nf * 4, 4)))
    me.polygons.foreach_set("loop_total", [4] * nf)
    me.update(calc_edges=True)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


def regolith_mat():
    m, nt, out = new_mat("Regolith")
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    x, y, z = xyz(nt, P)
    n0 = noise(nt, P, 0.004, 4.0, 0.6)
    n1 = noise(nt, P, 0.08, 5.0, 0.6)
    n2 = noise(nt, P, 1.6, 5.0, 0.65)
    vo = node(nt, "ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 9.0
    link(nt, P, vo.inputs["Vector"])
    peb = inv(nt, sstep(nt, vo.outputs["Distance"], 0.0, 0.32))
    c = col_mix(nt, "#7a3f22", "#a8623a", n0)
    c = col_mix(nt, c, "#c98a5c", mth(nt, "MULTIPLY", sstep(nt, n1, 0.45, 0.75), 0.6))
    c = col_mix(nt, c, "#4a2818", mth(nt, "MULTIPLY", sstep(nt, n2, 0.55, 0.8), 0.55))
    c = col_mix(nt, c, "#3b2116", mth(nt, "MULTIPLY", peb, 0.35))
    SC = val(nt, "SC", 0.0)                                    # scorch under the engines (L3)
    r = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", x, x), mth(nt, "MULTIPLY", y, y)))
    sc = mul(nt, inv(nt, sstep(nt, r, 0.6, 3.4)), SC)
    c = col_mix(nt, c, "#24140d", sc)
    b = principled(nt, c, 0.92, 0.0)
    b.inputs["Specular IOR Level"].default_value = 0.3
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.02
    link(nt, mth(nt, "ADD", mth(nt, "MULTIPLY", n2, 0.6), mth(nt, "MULTIPLY", peb, 0.5)), bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def rock_mat():
    m, nt, out = new_mat("Rock")
    P = obj_co(nt)
    n = noise(nt, P, 6.0, 5.0, 0.6)
    c = col_mix(nt, "#3d2419", "#6e3f27", n)
    c = col_mix(nt, c, "#a0663e", mth(nt, "MULTIPLY", sstep(nt, noise(nt, P, 1.5, 3.0), 0.55, 0.8), 0.7))
    b = principled(nt, c, 0.85, 0.0)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    link(nt, noise(nt, P, 20.0, 6.0, 0.6), bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def bm_rock(bm, c, r, seed, flat=0.6):
    before = set(bm.verts)
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    nv = [v for v in bm.verts if v not in before]
    s = V(random.uniform(0.8, 1.3), random.uniform(0.8, 1.2), flat * random.uniform(0.7, 1.1))
    a = random.uniform(0, 6.28)
    Rz = Matrix.Rotation(a, 3, "Z")
    for v in nv:
        p = v.co.copy()
        k = 1.0 + 0.22 * mn.noise(p * 1.4 + V(seed, 0, 0)) + 0.08 * mn.noise(p * 3.5 + V(0, seed, 0))
        p = V(p.x * s.x, p.y * s.y, p.z * s.z) * k * r
        v.co = c + Rz @ p
    for f in {f for v in nv for f in v.link_faces}:
        f.smooth = True


def build_rocks(mat, n=900, R=55.0, seed=21):
    random.seed(seed)
    bm = bmesh.new()
    for _ in range(n):
        x, y = random.uniform(-R, R), random.uniform(-R, R)
        if abs(x) < 2.6 and abs(y) < 2.2:
            continue
        r = 0.02 + 0.32 * random.random() ** 6
        bm_rock(bm, V(x, y, ground(x, y) + r * 0.15), r, random.uniform(0, 50))
    for _ in range(1400):
        a, d = random.uniform(0, 2 * math.pi), 2.4 + 22.0 * random.random() ** 1.6
        x, y = d * math.cos(a), d * math.sin(a)
        r = 0.015 + 0.09 * random.random() ** 3
        bm_rock(bm, V(x, y, ground(x, y) + r * 0.1), r, random.uniform(0, 50))
    return obj_from_bm("Rocks", bm, mat, smooth=True)


def build_flyrocks(mat, n=26, seed=4):
    """loose stones the engine blast throws (L3), each its own object so it can fly"""
    random.seed(seed)
    out = []
    for i in range(n):
        bm = bmesh.new()
        r = random.uniform(0.04, 0.13)
        bm_rock(bm, V(0, 0, 0), r, random.uniform(0, 50), flat=0.8)
        ob = obj_from_bm(f"Fly{i:02d}", bm, mat, smooth=True)
        a = random.uniform(0, 2 * math.pi) if i % 2 else rad(-147) + random.uniform(-0.45, 0.45)
        d = random.uniform(0.8, 3.0)
        ob["p0"] = (d * math.cos(a), d * math.sin(a), r)
        sp = random.uniform(5.0, 13.0)
        ob["v0"] = (sp * math.cos(a), sp * math.sin(a), random.uniform(3.0, 8.0))
        ob["spin"] = random.uniform(4, 14)
        ob["dt"] = random.uniform(0.0, 0.35)
        out.append(ob)
    return out


# ----------------------------------------------------------------------------------------------- materials

def gold_foil(name="Foil"):
    """crinkled gold multi-layer insulation"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    vo = node(nt, "ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 7.0
    link(nt, P, vo.inputs["Vector"])
    n = noise(nt, P, 3.0, 6.0, 0.6)
    c = col_mix(nt, "#b4791f", "#e7b65a", n)
    b = principled(nt, c, mth(nt, "MULTIPLY_ADD", n, 0.18, 0.16), 1.0)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.01
    link(nt, mth(nt, "ADD", vo.outputs["Distance"], mth(nt, "MULTIPLY", n, 0.5)), bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs[0])
    return m


def paint(name, col, rough=0.45, coat=0.4):
    m = pbr(name, col, rough, 0.0)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.12
    return m


def wheel_mat():
    """machined aluminium wheel with chevron grousers (darker raised strips) round the tread"""
    m, nt, out = new_mat("Wheel")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    ang = mth(nt, "DIVIDE", mth(nt, "ARCTAN2", z, x), 2 * math.pi / 24)
    chev = mth(nt, "ADD", ang, mth(nt, "MULTIPLY", mth(nt, "ABSOLUTE", y), 4.0))
    f = mth(nt, "FRACT", chev)
    g = mul(nt, sstep(nt, f, 0.0, 0.05), inv(nt, sstep(nt, f, 0.16, 0.21)))
    nzv = noise(nt, P, 30.0, 4.0)
    c = col_mix(nt, "#b9bcbf", "#8d9094", g)
    b = principled(nt, c, mth(nt, "MULTIPLY_ADD", nzv, 0.1, mth(nt, "MULTIPLY_ADD", g, 0.15, 0.24)), 1.0)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.01
    link(nt, g, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs[0])
    return m


def plume_mat(name="Plume"):
    """rocket exhaust: hot, nearly clear; bright at the nozzle, fading along the jet (local -z); S = throttle"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    S, Wt = val(nt, "S", 0.0), val(nt, "W", 0.0)
    u = mth(nt, "DIVIDE", mth(nt, "MULTIPLY", z, -1.0), 1.1)
    n4 = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")
    n4.inputs["Scale"].default_value = 3.0
    n4.inputs["Detail"].default_value = 4.0
    link(nt, P, n4.inputs["Vector"])
    link(nt, Wt, n4.inputs["W"])
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    core = mth(nt, "POWER", inv(nt, lw.outputs["Facing"]), 3.0)
    fade = mth(nt, "POWER", inv(nt, sstep(nt, u, 0.0, 1.0)), 2.4)
    a = mul(nt, fade, core, mth(nt, "MULTIPLY_ADD", n4.outputs["Fac"], 0.9, 0.55), S)
    col = ramp3(nt, u, [(0.0, "#fff3e2"), (0.15, "#ffc98a"), (0.5, "#ff8a48"), (1.0, "#d8603a")])
    e = emission(nt, col, mth(nt, "MULTIPLY", a, 2.0))
    add = node(nt, "ShaderNodeAddShader")
    link(nt, node(nt, "ShaderNodeBsdfTransparent").outputs[0], add.inputs[0])
    link(nt, e, add.inputs[1])
    link(nt, add.outputs[0], out.inputs[0])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def dust_mat(name, col="#b5805a"):
    """a dust cloud in a unit cylinder (object space: r 0..1, z 0..1); D = density, Wt evolves the noise"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    D, Wt = val(nt, "D", 0.0), val(nt, "W", 0.0)
    r = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", x, x), mth(nt, "MULTIPLY", y, y)))
    n4 = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")
    n4.inputs["Scale"].default_value = 2.6
    n4.inputs["Detail"].default_value = 6.0
    n4.inputs["Roughness"].default_value = 0.6
    link(nt, P, n4.inputs["Vector"])
    link(nt, Wt, n4.inputs["W"])
    shape = mul(nt, inv(nt, sstep(nt, r, 0.45, 1.0)), inv(nt, sstep(nt, z, mth(nt, "MULTIPLY_ADD", r, 0.55, 0.25), 1.0)),
                sstep(nt, z, -0.02, 0.06))
    d = mul(nt, mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", n4.outputs["Fac"], 0.42), 0.0), shape, D, 7.0)
    v = node(nt, "ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (*lin(col), 1)
    v.inputs["Absorption Color"].default_value = (*lin("#5a3420"), 1)
    v.inputs["Anisotropy"].default_value = 0.35
    link(nt, d, v.inputs["Density"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    return m


def haze_mat2(name, density, col):
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    _, _, z = xyz(nt, P)
    v = node(nt, "ShaderNodeVolumeScatter")
    v.inputs["Color"].default_value = (*lin(col), 1)
    v.inputs["Anisotropy"].default_value = 0.55
    link(nt, mth(nt, "MULTIPLY", inv(nt, sstep(nt, z, -0.5, 0.5)), val(nt, "H", density)), v.inputs["Density"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    return m


def fabric_mat():
    m, nt, out = new_mat("Airbag")
    P = obj_co(nt)
    n = noise(nt, P, 18.0, 4.0)
    b = principled(nt, col_mix(nt, "#d8c49b", "#c2ab7f", n), 0.62, 0.0)
    b.inputs["Sheen Weight"].default_value = 0.6
    b.inputs["Subsurface Weight"].default_value = 0.1
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    link(nt, n, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs[0])
    return m


def sc_mats():
    M = {}
    M["reg"] = regolith_mat()
    M["rock"] = rock_mat()
    M["foil"] = gold_foil()
    M["white"] = paint("WhitePaint", "#dcd8d0", 0.5, 0.3)
    M["grey"] = paint("GreyPaint", "#6d6f72", 0.45, 0.3)
    M["black"] = paint("BlackPaint", "#141516", 0.35, 0.6)
    M["alu"] = brushed("Alu", "#c4c7ca", 0.28)
    M["ti"] = brushed("Ti", "#a7abb0", 0.3)
    M["tank"] = brushed("Tank", "#cfd2d6", 0.18)
    M["nozzle"] = brushed("Nozzle", "#4c4844", 0.34)
    M["wheel"] = wheel_mat()
    M["glass"] = pbr("Lens", "#05070a", 0.04, 0.0)
    M["rtg"] = paint("RTG", "#1c1d1e", 0.5, 0.2)
    M["cable"] = pbr("Cable", "#e9e4d8", 0.6, 0.0)
    M["plume"] = plume_mat()
    M["plumeB"] = plume_mat("PlumeB")
    M["dust"] = dust_mat("Dust")
    M["dustT"] = dust_mat("DustTouch")
    M["dustC"] = dust_mat("DustCrash", "#d6a27a")
    M["haze"] = haze_mat2("Haze", 0.00035, "#e0b08a")
    M["flash"] = emis("Flash", "#ffb46a", 0.0, alpha=1.0)
    M["spark"] = emis("Spark", "#fff1d6", 0.0)
    M["bag"] = fabric_mat()
    M["floorS"] = floor_mat("FloorS", 14.0)
    return M


# ----------------------------------------------------------------------------------------------- the rover

def rbox(bm, c, s, r=0.03, segs=3, M=None):
    bm_rbox(bm, c, s, r, segs, M)


def bm_wheel(bm, c, side):
    """a wheel round the y axis at c: tread drum, a slightly domed outer face and six curved spokes to a hub"""
    Rm = Matrix.Translation(c) @ Matrix.Rotation(rad(90), 4, "Z")    # lathe axis x -> world y
    h = WW / 2
    prof = [V2(-h, 0.0), V2(-h, RW - 0.012), V2(-h + 0.01, RW), V2(h - 0.01, RW), V2(h, RW - 0.012), V2(h, 0.0)]
    f = bm_lathe(bm, prof, n=64, caps=False, M=Rm)
    # spokes and hub on the outer side
    so = side * (h - 0.02)
    for k in range(6):
        a = 2 * math.pi * k / 6
        pts = []
        for j in range(7):
            q = j / 6
            rr = lerp(0.05, RW - 0.02, q)
            aa = a + 0.45 * q * q
            pts.append(c + V(rr * math.cos(aa), so * (1 - 0.3 * q), rr * math.sin(aa)))
        bm_tube(bm, pts, 0.012, 6)
    bm_cyl(bm, 0.06, 0.06, 0.1, 24, Matrix.Translation(c + V(0, so, 0)) @ Matrix.Rotation(rad(90), 4, "X"))


def build_rover(M):
    root = empty("Rover")
    root.rotation_mode = "XYZ"
    # body: the warm electronics box under a white deck, gold and black detail
    bm = bmesh.new()
    rbox(bm, V(-0.08, 0, 0.93), (1.95, 1.12, 0.5), 0.05)
    body = obj_from_bm("RBody", bm, M["white"], root)
    bm = bmesh.new()
    rbox(bm, V(-0.05, 0, DECK - 0.03), (2.12, 1.30, 0.06), 0.02)
    rbox(bm, V(0.55, 0.0, DECK + 0.06), (0.6, 0.7, 0.12), 0.03)               # instrument box on the deck
    rbox(bm, V(-0.45, -0.32, DECK + 0.05), (0.5, 0.4, 0.1), 0.03)
    deck = obj_from_bm("RDeck", bm, M["grey"], root)
    bm = bmesh.new()
    rbox(bm, V(-0.08, 0.0, 0.66), (1.7, 0.95, 0.04), 0.01)                      # belly foil
    rbox(bm, V(0.9, 0.0, 0.92), (0.03, 0.9, 0.36), 0.01)                        # front face foil
    foil = obj_from_bm("RFoil", bm, M["foil"], root)
    # high-gain antenna (hexagonal dish) and a low-gain mast at the rear left
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=6, radius=0.22,
                            matrix=Matrix.Translation(V(-0.55, 0.42, DECK + 0.16)) @ Matrix.Rotation(rad(-20), 4, "X"))
    bm_cyl(bm, 0.03, 0.03, 0.16, 12, Matrix.Translation(V(-0.55, 0.42, DECK + 0.08)))
    bm_cyl(bm, 0.02, 0.02, 0.38, 12, Matrix.Translation(V(-0.8, -0.45, DECK + 0.19)))
    ant = obj_from_bm("RAnt", bm, M["white"], root, smooth=True)
    # RTG at the rear: a finned black cylinder, tilted up
    rt = empty("RTGRoot", V(-1.08, 0, 1.02), root)
    rt.rotation_euler = (0, rad(-28), 0)
    bm = bmesh.new()
    bm_cyl(bm, 0.2, 0.2, 0.66, 40, Matrix.Rotation(rad(90), 4, "Y"))
    for k in range(8):
        a = 2 * math.pi * k / 8
        bm_rbox(bm, V(0, 0, 0), (0.62, 0.15, 0.012), 0.004, 1,
                M=Matrix.Rotation(a, 4, "X") @ Matrix.Translation(V(0, 0.27, 0)))
    rtg = obj_from_bm("RTG", bm, M["rtg"], rt, smooth=True)
    # robotic arm folded across the front
    bm = bmesh.new()
    pts = [V(0.98, -0.42, 0.98), V(1.18, -0.38, 1.0), V(1.22, 0.2, 1.02), V(1.12, 0.42, 1.02)]
    bm_tube(bm, pts, 0.045, 12)
    rbox(bm, V(1.12, 0.45, 0.94), (0.26, 0.22, 0.22), 0.03)                      # turret
    arm = obj_from_bm("RArm", bm, M["ti"], root, smooth=True)
    # remote-sensing mast: pivot at the front left of the deck, stowed flat (rotation_y = 90 deg) until it stands up
    mp = empty("MastPivot", V(0.72, 0.42, DECK), root)
    mp.rotation_euler = (0, 0, 0)
    bm = bmesh.new()
    bm_cyl(bm, 0.05, 0.045, 0.95, 24, Matrix.Translation(V(0, 0, 0.48)))
    rbox(bm, V(0.0, 0.0, 1.02), (0.22, 0.42, 0.2), 0.03)                        # head
    mast = obj_from_bm("Mast", bm, M["white"], mp, smooth=True)
    bm = bmesh.new()
    for yy in (-0.12, 0.12):
        bm_cyl(bm, 0.045, 0.045, 0.04, 20, Matrix.Translation(V(0.115, yy, 1.03)) @ Matrix.Rotation(rad(90), 4, "Y"))
    rbox(bm, V(0.115, 0.0, 1.08), (0.03, 0.12, 0.05), 0.01)
    lens = obj_from_bm("MastEyes", bm, M["glass"], mp, smooth=True)
    # rocker-bogie sides: each side under a pivot empty that folds the wheels up beside the body when stowed
    sides = []
    for s in (1, -1):
        pv = empty(f"Side{'L' if s > 0 else 'R'}", V(PIV.x, s * PIV.y, PIV.z), root)
        pv.rotation_euler = (0, 0, 0)
        o = V(PIV.x, s * PIV.y, PIV.z)
        L = lambda p: p - o
        bm = bmesh.new()
        knee_f = V(1.0, s * WY, 0.62)
        bog = V(-0.46, s * 0.98, 0.58)
        top_m, top_r = V(WX[1], s * WY, 0.55), V(WX[2], s * WY, 0.55)
        bm_tube(bm, [L(o), L(V(0.45, s * 0.92, 0.80)), L(knee_f)], 0.036, 10)
        bm_tube(bm, [L(o), L(bog)], 0.036, 10)
        bm_tube(bm, [L(top_m), L(bog), L(top_r)], 0.032, 10)
        for wx, tp in zip(WX, (knee_f, top_m, top_r)):
            bm_tube(bm, [L(tp), L(V(wx, s * WY, RW + 0.02))], 0.03, 10)
            rbox(bm, L(V(wx, s * (WY - 0.17), RW)), (0.12, 0.08, 0.12), 0.015)     # motor hub
        sus = obj_from_bm(f"Susp{s}", bm, M["ti"], pv, smooth=True)
        bm = bmesh.new()
        for wx in WX:
            bm_wheel(bm, L(V(wx, s * WY, RW)), s)
        wh = obj_from_bm(f"Wheels{s}", bm, M["wheel"], pv, smooth=True)
        sides.append(pv)
    parts = [body, deck, foil, ant, rtg, arm, mast, lens] + [c for p in sides for c in p.children]
    return dict(root=root, sides=sides, mast=mp, parts=parts)


# ----------------------------------------------------------------------------------------------- the descent stage

def bm_bell(bm, M, r0=0.05, r1=0.13, L=0.32):
    prof = [V2(0.0, r0 + 0.02), V2(0.0, r0), V2(-L * 0.35, r0 * 1.15), V2(-L, r1), V2(-L, r1 - 0.01),
            V2(-L * 0.35 + 0.01, r0 * 1.15 - 0.01), V2(0.01, r0 + 0.01)]
    bm_lathe(bm, prof, n=40, caps=False, M=M @ Matrix.Rotation(rad(-90), 4, "Y"))   # lathe x -> world -z


def build_stage(M):
    root = empty("Stage")
    root.rotation_mode = "XYZ"
    parts = []
    # central octagonal frame, gold foil sides, dark top deck
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=8, radius=1.25,
                            matrix=Matrix.Rotation(rad(22.5), 4, "Z"))
    f = [f for f in bm.faces][0]
    ex = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in ex["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z += 0.42
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    oct_ = obj_from_bm("SFrame", bm, M["foil"], root)
    bv = oct_.modifiers.new("B", "BEVEL")
    bv.width, bv.segments = 0.03, 3
    weighted(oct_)
    parts.append(oct_)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=8, radius=1.18, matrix=Matrix.Translation(V(0, 0, 0.44))
                            @ Matrix.Rotation(rad(22.5), 4, "Z"))
    for v in bm.verts:
        pass
    rbox(bm, V(0, 0, 0.0), (0.6, 0.6, 0.06), 0.02)
    topd = obj_from_bm("STop", bm, M["black"], root)
    parts.append(topd)
    # propellant tanks on top, a pressurant sphere in the middle
    bm = bmesh.new()
    for k in range(3):
        a = rad(30 + 120 * k)
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=0.42,
                                  matrix=Matrix.Translation(V(0.68 * math.cos(a), 0.68 * math.sin(a), 0.86)))
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=0.3, matrix=Matrix.Translation(V(0, 0, 0.78)))
    tanks = obj_from_bm("STanks", bm, M["tank"], root, smooth=True)
    parts.append(tanks)
    bm = bmesh.new()
    for k in range(3):
        a = rad(30 + 120 * k)
        c = V(0.68 * math.cos(a), 0.68 * math.sin(a), 0.86)
        for d in (V(0.3, 0.3, -0.42), V(-0.3, 0.3, -0.42), V(0, -0.38, -0.42)):
            bm_tube(bm, [c + d * 0.62, c + d], 0.018, 6)
    struts = obj_from_bm("SStruts", bm, M["black"], root, smooth=True)
    parts.append(struts)
    # four engine pods on outrigger arms at the corners, two nozzles each = eight engines
    bm, bn, bk = bmesh.new(), bmesh.new(), bmesh.new()
    plumes, nozzles = [], []
    for k in range(4):
        a = rad(45 + 90 * k)
        u = V(math.cos(a), math.sin(a), 0)
        t = V(-u.y, u.x, 0)
        pc = u * 1.62 + V(0, 0, 0.18)
        R = Matrix.Translation(pc) @ Matrix.Rotation(a, 4, "Z")
        rbox(bm, V(0, 0, 0), (0.42, 0.56, 0.34), 0.04, 3, M=R)
        bm_tube(bk, [u * 1.1 + V(0, 0, 0.36), pc + V(0, 0, 0.12)], 0.035, 10)
        bm_tube(bk, [u * 1.1 + V(0, 0, 0.04), pc - V(0, 0, 0.08)], 0.035, 10)
        for j in (-1, 1):
            nc = pc + t * (0.15 * j) + V(0, 0, -0.17)
            cant = Matrix.Rotation(rad(14), 4, t.normalized())          # tip the bell outwards a little
            Mn = Matrix.Translation(nc) @ cant
            bm_bell(bn, Mn)
            nozzles.append((nc, (cant.to_3x3() @ V(0, 0, -1)).normalized()))
    pods = obj_from_bm("SPods", bm, M["foil"], root)
    parts.append(pods)
    arms = obj_from_bm("SArms", bk, M["black"], root, smooth=True)
    parts.append(arms)
    bells = obj_from_bm("SBells", bn, M["nozzle"], root, smooth=True)
    parts.append(bells)
    for i, (nc, d) in enumerate(nozzles):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.11, radius2=0.3, depth=1.8,
                              matrix=Matrix.Translation(V(0, 0, -0.9)))
        pl = obj_from_bm(f"Plume{i}", bm, M["plume"], root, nc + d * 0.33, smooth=True)
        pl.rotation_mode = "QUATERNION"
        pl.rotation_quaternion = (-d).to_track_quat("Z", "Y")
        pl.visible_shadow = False
        plumes.append(pl)
    # bridle and umbilical device under the belly
    bm = bmesh.new()
    bm_cyl(bm, 0.24, 0.24, 0.22, 40, Matrix.Translation(V(0, 0, -0.08)))
    rbox(bm, V(0, 0, -0.02), (0.9, 0.16, 0.08), 0.02)
    bud = obj_from_bm("SBUD", bm, M["grey"], root, smooth=True)
    parts.append(bud)
    glow = bpy.data.lights.new("EngGlow", "POINT")
    glow.color = lin("#ffb27a")
    glow.energy = 0.0
    glow.shadow_soft_size = 1.2
    gl = bpy.data.objects.new("EngGlow", glow)
    bpy.context.scene.collection.objects.link(gl)
    gl.parent = root
    gl.location = (0, 0, -1.4)
    return dict(root=root, parts=parts, plumes=plumes, glow=gl)


def build_bridles(M):
    """three cables and the umbilical: unit-length rods along -z, scaled in z to the paid-out length"""
    out = []
    for i, p in enumerate(ATT + [V(0.15, 0.0, 0)]):
        bm = bmesh.new()
        r = 0.012 if i < 3 else 0.015
        bm_cyl(bm, r, r, 1.0, 10, Matrix.Translation(V(0, 0, -0.5)))
        ob = obj_from_bm(f"Bridle{i}", bm, M["cable"] if i < 3 else M["grey"], None, smooth=True)
        ob["att"] = tuple(p)
        out.append(ob)
    return out


def build_airbags(M):
    """an airbag ball like the ones that bounced Pathfinder and Spirit/Opportunity: 24 lobes round a core"""
    root = empty("Bags", ST)
    bm = bmesh.new()
    phi = (1 + 5 ** 0.5) / 2
    dirs = []
    for a, b in ((0, 1), (0, -1)):
        pass
    pts = [(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0), (0, -1, phi), (0, 1, phi), (0, -1, -phi),
           (0, 1, -phi), (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)]
    for p in pts:
        d = V(*p).normalized()
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=0.92,
                                  matrix=Matrix.Translation(d * 1.25))
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.25)
    ob = obj_from_bm("Airbag", bm, M["bag"], root, (0, 0, 2.15), smooth=True)
    return dict(root=root, ball=ob)


def build_sc():
    scn = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    M = sc_mats()
    world = mars_world()
    near = grid_obj("Near", -60.0, 60.0, -60.0, 60.0, 0.2, M["reg"])
    far = grid_obj("Far", -9000.0, 9000.0, -6000.0, 9000.0, 30.0, M["reg"], sink=58.0)
    rocks = build_rocks(M["rock"])
    fly = build_flyrocks(M["rock"])
    haze = vol_box("Haze", V(0, 1500, 300), (20000.0, 16000.0, 1400.0), M["haze"])
    sun = sun_lamp(sun_dir(), 3.6, "#ffe2c4", angle=0.5)
    R = build_rover(M)
    S = build_stage(M)
    BR = build_bridles(M)
    bags = build_airbags(M)
    bm = bmesh.new()
    bm_cyl(bm, 1.0, 1.0, 1.0, 48, Matrix.Translation(V(0, 0, 0.5)))
    dust = obj_from_bm("DustCloud", bm, M["dust"], None)
    bm = bmesh.new()
    bm_cyl(bm, 1.0, 1.0, 1.0, 48, Matrix.Translation(V(0, 0, 0.5)))
    dustT = obj_from_bm("DustTouch", bm, M["dustT"], None)
    bm = bmesh.new()
    bm_cyl(bm, 1.0, 1.0, 1.0, 48, Matrix.Translation(V(0, 0, 0.5)))
    dustC = obj_from_bm("DustCrash", bm, M["dustC"], None, CR + V(0, 0, ground(CR.x, CR.y) - 2.0))
    flash = sphere("CrashFlash", 1.0, CR + V(0, 0, ground(CR.x, CR.y) + 4.0), M["flash"])
    flash.visible_shadow = False
    sparks = [sphere(f"Spark{i}", 0.035, (0, 0, 0), M["spark"]) for i in range(3)]
    for sp in sparks:
        sp.visible_shadow = False
    floorS = floor("FloorS", ST, 14.0, M["floorS"])
    cl = bpy.data.lights.new("CrashGlow", "POINT")
    cl.color = lin("#ffa860")
    cl.energy = 0.0
    cl.shadow_soft_size = 4.0
    crashL = bpy.data.objects.new("CrashGlow", cl)
    scn.collection.objects.link(crashL)
    crashL.location = CR + V(0, 0, ground(CR.x, CR.y) + 9.0)
    lights = []
    for name, loc, tgt, sx, sy, col in (("Key", ST + V(-5, -7, 7), ST + V(0, 0, 1.5), 4.0, 2.0, "#fff0e0"),
                                        ("Rim", ST + V(4, 6, 4), ST + V(0, 0, 1.5), 0.6, 6.0, "#ffd9b0"),
                                        ("Top", ST + V(0, 0, 9), ST + V(0, 0, 1.0), 4.0, 4.0, "#ffffff")):
        lights.append(area(name, loc, tgt, sx, sy, col, 0.0))
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.05, 30000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    mars = [near, far, rocks, haze]
    return dict(M=M, world=world, mars=mars, fly=fly, sun=sun, R=R, S=S, BR=BR, bags=bags, dust=dust, dustT=dustT,
                dustC=dustC, flash=flash, crashL=crashL, sparks=sparks, floorS=floorS, lights=lights, cam=camo, hero=None)
