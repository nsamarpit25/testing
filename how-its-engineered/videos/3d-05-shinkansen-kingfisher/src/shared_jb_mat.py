

# ----------------------------------------------------------------------------------------------- shader helpers

def ramp3(nt, fac, stops):
    r = node(nt, "ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for e, (p, c) in zip(els, stops):
        e.position = p
        e.color = (*lin(c), 1)
    link(nt, fac, r.inputs[0])
    return r.outputs[0]


def attr(nt, name):
    return node(nt, "ShaderNodeAttribute", attribute_name=name).outputs["Fac"]


def sstep(nt, x, e0, e1):
    """smoothstep(e0, e1, x) with e0 < e1."""
    m = node(nt, "ShaderNodeMapRange", data_type="FLOAT", interpolation_type="SMOOTHSTEP")
    link(nt, x, m.inputs[0])
    m.inputs[1].default_value = e0
    m.inputs[2].default_value = e1
    m.inputs[3].default_value = 0.0
    m.inputs[4].default_value = 1.0
    return m.outputs[0]


def inv(nt, x):
    return mth(nt, "SUBTRACT", 1.0, x)


def mul(nt, *xs):
    out = xs[0]
    for x in xs[1:]:
        out = mth(nt, "MULTIPLY", out, x)
    return out


def xyz(nt, vec):
    s = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, vec, s.inputs[0])
    return s.outputs[0], s.outputs[1], s.outputs[2]


def col_mix(nt, a, b, fac, mode="MIX"):
    """RGBA mix: a + (b - a) * fac (MIX) or a + b * fac (ADD); a/b are sockets or hex strings."""
    m = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type=mode)
    m.clamp_result = False
    m.clamp_factor = False
    if isinstance(fac, (int, float)):
        m.inputs["Factor"].default_value = fac
    else:
        link(nt, fac, m.inputs["Factor"])
    for k, c in ((6, a), (7, b)):
        if isinstance(c, str):
            m.inputs[k].default_value = (*lin(c), 1)
        else:
            link(nt, c, m.inputs[k])
    return m.outputs[2]


def mix_sh(nt, fac, a, b):
    m = node(nt, "ShaderNodeMixShader")
    if isinstance(fac, (int, float)):
        m.inputs[0].default_value = fac
    else:
        link(nt, fac, m.inputs[0])
    link(nt, a, m.inputs[1])
    link(nt, b, m.inputs[2])
    return m.outputs[0]


def emission(nt, col, strength):
    e = node(nt, "ShaderNodeEmission")
    if isinstance(col, str):
        e.inputs[0].default_value = (*lin(col), 1)
    else:
        link(nt, col, e.inputs[0])
    if isinstance(strength, (int, float)):
        e.inputs[1].default_value = strength
    else:
        link(nt, strength, e.inputs[1])
    return e.outputs[0]


def principled(nt, base, rough, metal, coat=0.0, coat_r=0.05):
    b = node(nt, "ShaderNodeBsdfPrincipled")
    for k, v in (("Base Color", base), ("Roughness", rough), ("Metallic", metal)):
        if isinstance(v, str):
            b.inputs[k].default_value = (*lin(v), 1)
        elif isinstance(v, (int, float)):
            b.inputs[k].default_value = v
        else:
            link(nt, v, b.inputs[k])
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_r
    return b


def thermal(nt, T, strength=1.0):
    """Thermal-camera emission for a temperature value on the 0..1 scale (melting point at MELT)."""
    col = ramp3(nt, T, THERMAL)
    hot = mth(nt, "MULTIPLY", mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", T, 0.7), 0.0), 5.0)
    return emission(nt, col, mth(nt, "ADD", hot, strength))


def obj_co(nt):
    return node(nt, "ShaderNodeTexCoord").outputs["Object"]


def noise(nt, vec, scale, detail=4.0, rough=0.55, stretch=None):
    if stretch:
        mp = node(nt, "ShaderNodeVectorMath", operation="MULTIPLY")
        link(nt, vec, mp.inputs[0])
        mp.inputs[1].default_value = stretch
        vec = mp.outputs[0]
    n = node(nt, "ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    link(nt, vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def hole_field(nt):
    """Distance (m) to the nearest film-cooling hole centre from the surface attributes sa / sp, and a validity mask."""
    sa, sp = attr(nt, "sa"), attr(nt, "sp")
    dmin = None
    for sa0, pitch, ofs in HOLE_ROWS:
        du = mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", sa, sa0), 0.8)
        f = mth(nt, "FRACT", mth(nt, "DIVIDE", mth(nt, "SUBTRACT", sp, ofs), pitch))
        dv = mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", f, 0.5), pitch)
        c = node(nt, "ShaderNodeCombineXYZ")
        link(nt, du, c.inputs[0])
        link(nt, dv, c.inputs[1])
        ln = node(nt, "ShaderNodeVectorMath", operation="LENGTH")
        link(nt, c.outputs[0], ln.inputs[0])
        d = ln.outputs["Value"]
        dmin = d if dmin is None else mth(nt, "MINIMUM", dmin, d)
    valid = mul(nt, mth(nt, "GREATER_THAN", sp, 0.0032), mth(nt, "LESS_THAN", sp, H_AF - 0.0035),
                mth(nt, "LESS_THAN", sa, 50.0))
    return dmin, valid, sa, sp


# ----------------------------------------------------------------------------------------------- materials

def blade_mat(name):
    """Nickel superalloy blade. Values: G grains, GB grain-boundary glow, CK crack front (0..1 along the chord),
    SM/SF single-crystal growth (front height SF), TH/TB thermal view and blade temperature, XA/XZ x-ray wipe,
    FC hole glow (cooling air), HT heat-tint strength."""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    dmin, valid, sa, sp = hole_field(nt)
    hole = mul(nt, inv(nt, sstep(nt, dmin, HOLE_R * 0.82, HOLE_R * 1.02)), valid)
    hh = mth(nt, "ADD", inv(nt, valid), mul(nt, valid, sstep(nt, dmin, HOLE_R * 0.8, HOLE_R * 1.5)))
    # trailing-edge cut-back: cooling slots between thin lands on the pressure side near the trailing edge
    te = attr(nt, "te")
    stripe = sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "DIVIDE", sp, 0.0027)), 0.5)),
                   0.17, 0.24)
    slot = mul(nt, mth(nt, "LESS_THAN", sa, 0.0), inv(nt, sstep(nt, te, 0.0042, 0.0050)),
               mth(nt, "GREATER_THAN", sp, 0.004), mth(nt, "LESS_THAN", sp, H_AF - 0.004), inv(nt, stripe))
    hh = mth(nt, "SUBTRACT", hh, mth(nt, "MULTIPLY", slot, 0.8))
    # grains (Voronoi cells ~4 mm) and their boundaries
    G, GB, CK = val(nt, "G", 0.0), val(nt, "GB", 0.0), val(nt, "CK", 0.0)
    vo = node(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="F1")
    vo.inputs["Scale"].default_value = 250.0
    link(nt, P, vo.inputs["Vector"])
    gv = node(nt, "ShaderNodeRGBToBW")
    link(nt, vo.outputs["Color"], gv.inputs[0])
    gv = gv.outputs[0]
    ve = node(nt, "ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="DISTANCE_TO_EDGE")
    ve.inputs["Scale"].default_value = 250.0
    link(nt, P, ve.inputs["Vector"])
    e = ve.outputs["Distance"]
    bmask = inv(nt, sstep(nt, e, 0.0, 0.025))
    thin = inv(nt, sstep(nt, e, 0.0, 0.02))
    zc = mth(nt, "ADD", 0.030, mth(nt, "MULTIPLY", mth(nt, "SINE", mth(nt, "MULTIPLY_ADD", x, 420.0, 1.0)), 0.0035))
    band = inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", z, zc)), 0.0008, 0.0032))
    xc = mth(nt, "MULTIPLY_ADD", CK, 0.044, -0.022)
    front = inv(nt, sstep(nt, mth(nt, "SUBTRACT", x, xc), -0.001, 0.001))
    crack = mul(nt, thin, band, front, mth(nt, "GREATER_THAN", CK, 0.001))
    # single-crystal growth: molten above the front, a gold line at the front
    SM, SF = val(nt, "SM", 0.0), val(nt, "SF", -0.07)
    dz = mth(nt, "SUBTRACT", z, SF)
    molten = mul(nt, sstep(nt, dz, -0.0006, 0.0006), SM)
    fline = mul(nt, inv(nt, sstep(nt, mth(nt, "ABSOLUTE", dz), 0.0, 0.0012)), SM)
    mcol = ramp3(nt, mth(nt, "DIVIDE", mth(nt, "MAXIMUM", dz, 0.0), 0.03),
                 [(0.0, "#ffe2a0"), (0.25, "#ff9a2a"), (1.0, "#d2380c")])
    # metal colour: warm grey with a heat tint near the tip; brushed roughness along the span
    HT = val(nt, "HT", 1.0)
    tint = ramp3(nt, mth(nt, "DIVIDE", sp, H_AF), [(0.0, "#b4b6b9"), (0.55, "#b9b5ae"), (0.8, "#c3ad8c"),
                                                   (0.93, "#9b8fa6"), (1.0, "#7f8db0")])
    base = col_mix(nt, "#aba79f", tint, mth(nt, "MULTIPLY", HT, 0.5))
    nz = noise(nt, P, 1.0, 6.0, 0.6, stretch=(1400.0, 1400.0, 60.0))
    rough = mth(nt, "MULTIPLY_ADD", nz, 0.08, 0.21)
    gm = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    link(nt, G, gm.inputs["Factor"])
    link(nt, base, gm.inputs[6])
    gcol = node(nt, "ShaderNodeCombineColor")
    gval = mth(nt, "MULTIPLY_ADD", gv, 0.30, 0.82)
    for k in range(3):
        link(nt, gval, gcol.inputs[k])
    link(nt, gcol.outputs[0], gm.inputs[7])
    base = gm.outputs[2]
    base = col_mix(nt, base, "#141210", mul(nt, bmask, G, 0.8))
    base = col_mix(nt, base, "#050505", mth(nt, "MAXIMUM", mth(nt, "MAXIMUM", hole, crack), mth(nt, "MULTIPLY", slot, 0.85)))
    base = col_mix(nt, base, mcol, molten)
    rough = mth(nt, "ADD", mth(nt, "MULTIPLY", inv(nt, G), rough),
                mul(nt, G, mth(nt, "MULTIPLY_ADD", gv, 0.16, 0.16)))
    rough = mth(nt, "ADD", mth(nt, "MULTIPLY", rough, inv(nt, hole)), mth(nt, "MULTIPLY", hole, 0.65))
    rough = mth(nt, "ADD", mth(nt, "MULTIPLY", rough, inv(nt, molten)), mth(nt, "MULTIPLY", molten, 0.06))
    metal = mth(nt, "SUBTRACT", 1.0, mth(nt, "MAXIMUM", mth(nt, "MULTIPLY", hole, 0.9), mth(nt, "MULTIPLY", molten,
                                                                                         0.7)))
    b = principled(nt, base, rough, metal)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.00025
    link(nt, hh, bump.inputs["Height"])
    link(nt, bump.outputs["Normal"], b.inputs["Normal"])
    # emission: boundary glow, crack, molten metal, crystal front, cooling air in the holes, x-ray wipe line
    FC = val(nt, "FC", 0.0)
    XA, XZ = val(nt, "XA", 0.0), val(nt, "XZ", 0.07)
    wl = mul(nt, inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", z, XZ)), 0.0, 0.0009)), XA)
    ec = col_mix(nt, "#000000", PAL["amber"], mul(nt, bmask, GB, mth(nt, "GREATER_THAN", z, 0.0008), 0.9), "ADD")
    ec = col_mix(nt, ec, "#ffd9a8", mth(nt, "MULTIPLY", crack, 22.0), "ADD")
    ec = col_mix(nt, ec, mcol, mth(nt, "MULTIPLY", molten, 1.3), "ADD")
    ec = col_mix(nt, ec, PAL["gold"], mth(nt, "MULTIPLY", fline, 7.0), "ADD")
    ec = col_mix(nt, ec, PAL["cyan"], mul(nt, hole, FC, 4.0), "ADD")
    ec = col_mix(nt, ec, PAL["cyan"], mth(nt, "MULTIPLY", wl, 10.0), "ADD")
    link(nt, ec, b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.0
    sh = b.outputs[0]
    # thermal camera
    TH, TB = val(nt, "TH", 0.0), val(nt, "TB", 0.62)
    le = mul(nt, inv(nt, sstep(nt, mth(nt, "ABSOLUTE", sa), 0.0, 0.006)), mth(nt, "LESS_THAN", sa, 50.0))
    cool = mul(nt, inv(nt, sstep(nt, dmin, 0.0, 0.003)), valid, FC)
    T = mth(nt, "ADD", TB, mth(nt, "SUBTRACT", mth(nt, "MULTIPLY", le, 0.07), mth(nt, "MULTIPLY", cool, 0.12)))
    T = mth(nt, "ADD", T, mth(nt, "MULTIPLY", mth(nt, "DIVIDE", sp, H_AF), 0.05), clamp_=True)
    T = mth(nt, "ADD", T, mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", nz, 0.5), 0.04), clamp_=True)
    sh = mix_sh(nt, TH, sh, thermal(nt, T, 1.0))
    # x-ray: everything above the wipe line turns to glass with a fresnel rim
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    rim = mth(nt, "POWER", lw.outputs["Fresnel"], 3.0)
    # dithered transparency drops fully transparent fragments (and their emission), so the ghost keeps some opacity
    op = mth(nt, "MULTIPLY_ADD", rim, 0.6, 0.1, clamp_=True)
    glass = node(nt, "ShaderNodeMixShader")
    link(nt, op, glass.inputs[0])
    link(nt, node(nt, "ShaderNodeBsdfTransparent").outputs[0], glass.inputs[1])
    link(nt, emission(nt, PAL["ice"], mth(nt, "DIVIDE", mth(nt, "MULTIPLY_ADD", rim, 1.6, 0.004), op)),
         glass.inputs[2])
    xm = mul(nt, sstep(nt, mth(nt, "SUBTRACT", z, XZ), -0.0004, 0.0004), XA)
    sh = mix_sh(nt, mth(nt, "MULTIPLY", xm, mth(nt, "SUBTRACT", 1.0, wl)), sh, glass.outputs[0])
    link(nt, sh, out.inputs[0])
    m.diffuse_color = (*lin("#b5b7ba"), 1)
    return m


def disc_mat(name):
    """Anodised titanium with fine lathe rings; TH/TB thermal."""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    r = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", y, y), mth(nt, "MULTIPLY", z, z)))
    rings = mth(nt, "MULTIPLY_ADD", mth(nt, "SINE", mth(nt, "MULTIPLY", r, 9000.0)), 0.5, 0.5)
    nz = noise(nt, P, 80.0, 3.0)
    rough = mth(nt, "ADD", mth(nt, "MULTIPLY", rings, 0.07), mth(nt, "MULTIPLY_ADD", nz, 0.06, 0.17))
    base = ramp3(nt, nz, [(0.3, "#3a4252"), (0.7, "#455066")])
    b = principled(nt, base, rough, 1.0)
    TH, TB = val(nt, "TH", 0.0), val(nt, "TB", 0.35)
    T = mth(nt, "ADD", TB, mth(nt, "MULTIPLY", mth(nt, "DIVIDE", mth(nt, "SUBTRACT", r, 0.2), 0.1), 0.12),
            clamp_=True)
    link(nt, mix_sh(nt, TH, b.outputs[0], thermal(nt, T, 0.8)), out.inputs[0])
    m.diffuse_color = (*lin("#3e4656"), 1)
    return m


def tbc_mat(name):
    """Ceramic thermal barrier coating: matte off-white, sprayed micro texture, the same cooling holes. side=1 on the
    inner face. HF glows the outer face hot (the heat it holds back); TH thermal."""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    dmin, valid, sa, sp = hole_field(nt)
    hole = mul(nt, inv(nt, sstep(nt, dmin, HOLE_R * 0.95, HOLE_R * 1.15)), valid)
    side = attr(nt, "side")
    nz = noise(nt, P, 9000.0, 3.0, 0.7)
    base = col_mix(nt, "#c9c3b8", "#a89c86", side)
    base = col_mix(nt, base, "#0a0908", hole)
    b = principled(nt, base, mth(nt, "MULTIPLY_ADD", nz, 0.15, 0.5), 0.0)
    try:
        b.inputs["Subsurface Weight"].default_value = 0.08
        b.inputs["Subsurface Radius"].default_value = (0.0004, 0.0003, 0.0002)
    except Exception:
        pass
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.0001
    link(nt, mth(nt, "ADD", nz, mth(nt, "MULTIPLY", inv(nt, hole), 1.0)), bump.inputs["Height"])
    link(nt, bump.outputs["Normal"], b.inputs["Normal"])
    HF = val(nt, "HF", 0.0)
    outer = inv(nt, side)
    glow = mul(nt, HF, outer)
    T = mth(nt, "ADD", 0.9, mth(nt, "MULTIPLY", nz, 0.08))
    hot = ramp3(nt, T, THERMAL)
    link(nt, hot, b.inputs["Emission Color"])
    link(nt, mth(nt, "MULTIPLY", glow, 2.2), b.inputs["Emission Strength"])
    TH = val(nt, "TH", 0.0)
    Tt = mth(nt, "ADD", mth(nt, "MULTIPLY", outer, 0.92), mth(nt, "MULTIPLY", side, 0.6))
    link(nt, mix_sh(nt, TH, b.outputs[0], thermal(nt, Tt, 1.0)), out.inputs[0])
    m.diffuse_color = (*lin("#ebe6dc"), 1)
    return m


def flow_mat(name, kind):
    """Glowing flow lines with comet streaks moving along gt (P = phase, animate it). kind: gas (thermal white-hot),
    film (cyan ribbons, FG grows them out of the holes), chan (cyan, CF switches the flow on)."""
    m, nt, out = new_mat(name)
    gt, gp = attr(nt, "gt"), attr(nt, "gp")
    S, Pp = val(nt, "S", 0.0), val(nt, "P", 0.0)
    rep = {"gas": 3.0, "film": 2.0, "chan": 9.0}[kind]
    f = mth(nt, "FRACT", mth(nt, "ADD", mth(nt, "SUBTRACT", mth(nt, "MULTIPLY", gt, rep), Pp), gp))
    streak = mul(nt, sstep(nt, f, 0.0, 0.08), inv(nt, sstep(nt, f, 0.2, 0.75)))
    ends = mul(nt, sstep(nt, gt, 0.0, 0.08), inv(nt, sstep(nt, gt, 0.86, 1.0)))
    tr = node(nt, "ShaderNodeBsdfTransparent").outputs[0]
    if kind == "gas":
        T = mth(nt, "ADD", 0.86, mth(nt, "MULTIPLY", streak, 0.14))
        col = ramp3(nt, T, THERMAL)
        a = mth(nt, "MINIMUM", mul(nt, S, ends, mth(nt, "MULTIPLY_ADD", streak, 0.85, 0.15)), 1.0)
        em = emission(nt, col, mth(nt, "MULTIPLY_ADD", streak, 7.0, 1.2))
    elif kind == "film":
        FG = val(nt, "FG", 0.0)
        gx = attr(nt, "gx")
        edge = mth(nt, "SINE", mth(nt, "MULTIPLY", gx, math.pi))
        grow = inv(nt, sstep(nt, mth(nt, "SUBTRACT", gt, FG), -0.08, 0.0))
        fade = mth(nt, "POWER", inv(nt, gt), 0.7)
        a = mth(nt, "MINIMUM", mul(nt, S, edge, grow, fade, mth(nt, "MULTIPLY_ADD", streak, 0.7, 0.3)), 1.0)
        col = col_mix(nt, PAL["cyan"], PAL["ice"], streak)
        em = emission(nt, col, mth(nt, "MULTIPLY_ADD", streak, 5.0, 2.0))
    else:
        CF = val(nt, "CF", 0.0)
        a = mth(nt, "MINIMUM", S, 1.0)
        em = emission(nt, col_mix(nt, "#0f5a73", PAL["cyan"], mul(nt, streak, CF)),
                      mth(nt, "MULTIPLY_ADD", mul(nt, streak, CF), 9.0, 0.6))
    link(nt, mix_sh(nt, a, tr, em), out.inputs[0])
    return m


def blanket_mat(name):
    m, nt, out = new_mat(name)
    S = val(nt, "S", 0.0)
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.4
    fr = lw.outputs["Fresnel"]
    sp = attr(nt, "sp")
    n = noise(nt, obj_co(nt), 1.0, 3.0, 0.5, stretch=(300.0, 300.0, 40.0))
    a = mth(nt, "MINIMUM", mul(nt, S, mth(nt, "MULTIPLY_ADD", fr, 0.55, 0.1), mth(nt, "MULTIPLY_ADD", n, 0.8, 0.6)),
            1.0)
    em = emission(nt, col_mix(nt, PAL["cyan"], PAL["ice"], fr), mth(nt, "MULTIPLY_ADD", fr, 3.0, 1.0))
    link(nt, mix_sh(nt, a, node(nt, "ShaderNodeBsdfTransparent").outputs[0], em), out.inputs[0])
    return m


def floor_mat(name, R):
    """Glossy black studio floor that fades to nothing towards radius R (dithered alpha)."""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    r = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", x, x), mth(nt, "MULTIPLY", y, y)))
    u = mth(nt, "DIVIDE", r, R)
    nz = noise(nt, P, 40.0 / R, 4.0)
    b = principled(nt, "#030304", mth(nt, "ADD", mth(nt, "MULTIPLY_ADD", nz, 0.05, 0.15), mth(nt, "MULTIPLY", u, 0.3)),
                   0.0)
    b.inputs["Specular IOR Level"].default_value = 0.35
    link(nt, inv(nt, sstep(nt, u, 0.55, 1.0)), b.inputs["Alpha"])
    link(nt, b.outputs[0], out.inputs[0])
    return m


def studio_world():
    w = bpy.data.worlds.new("Studio")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    # a seamless studio backdrop: a soft pool of light behind the subject (screen space), falling off to the edges
    win = node(nt, "ShaderNodeTexCoord").outputs["Window"]
    wx, wy, _ = xyz(nt, win)
    dx = mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", wx, 0.5), 0.5625)
    dy = mth(nt, "SUBTRACT", wy, 0.56)
    d = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", dx, dx), mth(nt, "MULTIPLY", dy, dy)))
    grad = ramp3(nt, d, [(0.0, "#2c2e33"), (0.14, "#222428"), (0.30, "#121316"), (0.48, "#070809"),
                         (0.7, "#020203")])
    bgc = node(nt, "ShaderNodeBackground")
    link(nt, grad, bgc.inputs[0])
    link(nt, val(nt, "W", 1.0), bgc.inputs[1])
    amb = node(nt, "ShaderNodeBackground")
    amb.inputs[0].default_value = (*lin("#1d1e21"), 1)
    link(nt, val(nt, "A", 0.18), amb.inputs[1])
    lp = node(nt, "ShaderNodeLightPath")
    link(nt, mix_sh(nt, lp.outputs["Is Camera Ray"], amb.outputs[0], bgc.outputs[0]), out.inputs[0])
    return w


def spinner_mat():
    m, nt, out = new_mat("Spinner")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    ang = mth(nt, "DIVIDE", mth(nt, "ARCTAN2", z, y), 2 * math.pi)
    f = mth(nt, "FRACT", mth(nt, "ADD", ang, mth(nt, "MULTIPLY", mth(nt, "ADD", x, 2.05), 1.25)))
    stripe = mul(nt, sstep(nt, f, 0.0, 0.004), inv(nt, sstep(nt, f, 0.075, 0.08)))
    b = principled(nt, col_mix(nt, "#0d0f12", "#e9ecef", stripe), 0.25, 0.0, coat=1.0)
    link(nt, b.outputs[0], out.inputs[0])
    return m


def fan_mat():
    """Carbon-composite fan blade with a titanium leading edge (cf = chord fraction)."""
    m, nt, out = new_mat("Fan")
    cf = attr(nt, "cf")
    le = inv(nt, sstep(nt, cf, 0.05, 0.08))
    P = obj_co(nt)
    nz = noise(nt, P, 60.0, 3.0)
    b = principled(nt, col_mix(nt, "#0e1013", "#b9bec5", le), mth(nt, "MULTIPLY_ADD", nz, 0.08, 0.26),
                   mth(nt, "MULTIPLY_ADD", le, 0.85, 0.15), coat=1.0, coat_r=0.06)
    link(nt, b.outputs[0], out.inputs[0])
    return m


def flame_mat():
    m, nt, out = new_mat("Flame")
    P = obj_co(nt)
    S = val(nt, "S", 0.0)
    nz = noise(nt, P, 18.0, 5.0, 0.6)
    col = ramp3(nt, nz, [(0.3, "#ff4a0a"), (0.6, "#ff9a2a"), (0.8, "#ffd38a")])
    link(nt, emission(nt, col, mth(nt, "MULTIPLY", S, mth(nt, "MULTIPLY_ADD", nz, 2.0, 0.5))), out.inputs[0])
    return m


def brushed(name, col, rough, metal=1.0, scale=200.0):
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    nz = noise(nt, P, 1.0, 5.0, 0.6, stretch=(scale * 0.1, scale, scale))
    b = principled(nt, col, mth(nt, "MULTIPLY_ADD", nz, 0.1, rough - 0.05), metal)
    link(nt, b.outputs[0], out.inputs[0])
    m.diffuse_color = (*lin(col), 1)
    return m


def card_mat(name, col, strength):
    m, nt, out = new_mat(name)
    link(nt, emission(nt, col, val(nt, "S", strength)), out.inputs[0])
    return m


def materials():
    M = {}
    M["bladeD"] = blade_mat("BladeDisc")
    M["bladeH"] = blade_mat("BladeHero")
    M["disc"] = disc_mat("Disc")
    M["tbc"] = tbc_mat("TBC")
    M["gas"] = flow_mat("Gas", "gas")
    M["gasD"] = flow_mat("GasDisc", "gas")
    M["film"] = flow_mat("Film", "film")
    M["chan"] = flow_mat("Chan", "chan")
    M["blanket"] = blanket_mat("Blanket")
    M["floorE"] = floor_mat("FloorE", 9.0)
    M["floorD"] = floor_mat("FloorD", 2.2)
    M["floorB"] = floor_mat("FloorB", 1.2)
    M["paint"] = pbr("Paint", "#1d2026", 0.36, 0.55)
    M["paint"].node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 1.0
    M["paint"].node_tree.nodes["Principled BSDF"].inputs["Coat Roughness"].default_value = 0.04
    M["cowl"] = brushed("Cowl", "#aeb4bb", 0.3)
    M["cutface"] = pbr("CutFace", "#d5d9de", 0.16, 1.0)
    M["spinner"] = spinner_mat()
    M["fan"] = fan_mat()
    M["ti"] = brushed("Ti", "#babfc6", 0.24)
    M["nickel_dark"] = brushed("NiDark", "#938b82", 0.3)
    M["steel"] = brushed("Steel", "#9aa0a7", 0.3)
    M["plug"] = brushed("Plug", "#6e6a66", 0.42)
    M["comb"] = brushed("Comb", "#5e6268", 0.34)
    M["flame"] = flame_mat()
    M["card"] = card_mat("Card", "#ffffff", 4.0)
    return M
