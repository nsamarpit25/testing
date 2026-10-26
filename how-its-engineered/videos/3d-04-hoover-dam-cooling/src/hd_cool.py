# ----------------------------------------------------------------------------------------------- the cooling set
# The dam under construction in the dry canyon: a grid of concrete columns (16 m square, 1.52 m lifts) at the dam
# site, a one-pour monolith for the "what if" shots, steel cooling coils in the three hero columns facing
# downstream, and grout slabs for the joints. One column material does the concrete look, the thermal camera view
# (TH), the hot core / cooling skin (SK), cracks (CK), the cooling front spreading from the coils (CO) and an
# x-ray (XA, hero columns only).
CELL, LIFT, GAP0 = 16.0, 1.52, 0.10
COLS_X = [-80.0 + CELL * i for i in range(11)]
ROWS_Y = [8.0 + CELL * j for j in range(12)]
HERO_X = (-16.0, 0.0, 16.0)
BED = -7.0
MONO_X = (COLS_X[0] - CELL / 2, COLS_X[-1] + CELL / 2)
MONO_Y = (ROWS_Y[0] - CELL / 2, ROWS_Y[-1] + CELL / 2)
MONO_Z = (BED, 75.0)


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


def obj_attr(nt, name):
    a = node(nt, "ShaderNodeAttribute", attribute_type="OBJECT")
    a.attribute_name = name
    return a.outputs["Fac"]


def column_mat():
    m, nt, out = new_mat("Column")
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    g = node(nt, "ShaderNodeTexCoord").outputs["Generated"]
    gx, gy, gz = xyz(nt, g)
    TH, TT, SK, CK, CO, XA = (val(nt, k, v) for k, v in (("TH", 0.0), ("TT", 0.9), ("SK", 0.0), ("CK", 0.0),
                                                         ("CO", 0.0), ("XA", 0.0)))
    hero = obj_attr(nt, "hero")
    mono = obj_attr(nt, "mono")
    # concrete
    base = principled(nt, "#c9bfae", 0.8, 0.0)
    streak = noise(nt, P, 0.35, 4.0, 0.6, stretch=(1.0, 1.0, 0.05))
    lz = mth(nt, "FRACT", mth(nt, "DIVIDE", z, LIFT))
    line = mul(nt, sstep(nt, lz, 0.0, 0.015), inv(nt, sstep(nt, lz, 0.03, 0.05)))
    c = col_mix(nt, "#cbc1b0", "#958a77", mth(nt, "MULTIPLY", mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", streak, 0.5), 0.0), 3.0))
    c = col_mix(nt, c, "#8d8370", mth(nt, "MULTIPLY", line, 0.6))
    core = mth(nt, "MINIMUM", mth(nt, "MINIMUM", mth(nt, "MINIMUM", gx, inv(nt, gx)), mth(nt, "MINIMUM", gy, inv(nt, gy))),
               inv(nt, gz))
    # the monolith (and its cutaway half) measure depth in metres from the full block's outer faces
    dm = mth(nt, "MINIMUM", mth(nt, "MINIMUM", mth(nt, "SUBTRACT", x, MONO_X[0]), mth(nt, "SUBTRACT", MONO_X[1], x)),
             mth(nt, "MINIMUM", mth(nt, "MINIMUM", mth(nt, "SUBTRACT", y, MONO_Y[0]), mth(nt, "SUBTRACT", MONO_Y[1], y)),
                 mth(nt, "SUBTRACT", MONO_Z[1], z)))
    dm = mth(nt, "MINIMUM", mth(nt, "DIVIDE", dm, 36.0), 1.0)
    core = mth(nt, "ADD", mth(nt, "MULTIPLY", core, inv(nt, mono)), mth(nt, "MULTIPLY", dm, mono))
    skin = inv(nt, sstep(nt, core, 0.0, 0.5))
    # cracks: Voronoi cell edges, grown in by CK where a slow noise is below the front
    vor = node(nt, "ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    vor.inputs["Scale"].default_value = 0.09
    warp = noise(nt, P, 0.4, 3.0)
    pw = node(nt, "ShaderNodeVectorMath", operation="ADD")
    link(nt, P, pw.inputs[0])
    link(nt, mth(nt, "MULTIPLY", warp, 3.0), pw.inputs[1])
    link(nt, pw.outputs[0], vor.inputs["Vector"])
    grow = sstepv(nt, noise(nt, P, 0.03, 2.0), mth(nt, "MULTIPLY_ADD", CK, 0.8, -0.05),
                 mth(nt, "MULTIPLY_ADD", CK, 0.8, 0.0))
    grow = inv(nt, grow)
    crack = mul(nt, inv(nt, sstep(nt, vor.outputs["Distance"], 0.0, 0.055)), grow, CK, skin)
    c = col_mix(nt, c, "#1a1410", crack)
    link(nt, c, base.inputs["Base Color"])
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    link(nt, mth(nt, "ADD", streak, mth(nt, "MULTIPLY", crack, -2.0)), bump.inputs["Height"])
    link(nt, bump.outputs[0], base.inputs["Normal"])
    # temperature: hot everywhere (TT), the skin cools first in the monolith (SK), the coils pull heat out (CO)
    d = mth(nt, "MULTIPLY", mth(nt, "MINIMUM", lz, inv(nt, lz)), LIFT)          # 0 .. 0.76 m from a coil plane
    cool = inv(nt, sstepv(nt, d, mth(nt, "MULTIPLY_ADD", CO, 1.0, -0.25), mth(nt, "MULTIPLY", CO, 1.0)))
    cool = mth(nt, "MAXIMUM", cool, sstep(nt, CO, 0.75, 1.0))
    T = mth(nt, "MULTIPLY", TT, mth(nt, "SUBTRACT", 1.0, mth(nt, "MULTIPLY", mul(nt, SK, skin, mono), 0.5)))
    T = mth(nt, "MULTIPLY", T, mth(nt, "SUBTRACT", 1.0, mth(nt, "MULTIPLY", cool, 0.62)))
    T = mth(nt, "ADD", T, mth(nt, "MULTIPLY", crack, 0.62))
    T = mth(nt, "ADD", T, mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", streak, 0.5), 0.08))
    th = thermal(nt, mth(nt, "MINIMUM", T, 1.0), 0.75)
    sh = mix_sh(nt, TH, base.outputs[0], th)
    # x-ray on the hero columns: see-through with glowing edges
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    edge = emission(nt, "#7fd6ff", mth(nt, "MULTIPLY", lw.outputs["Facing"], 1.6))
    tr = node(nt, "ShaderNodeBsdfTransparent")
    xr = node(nt, "ShaderNodeAddShader")
    link(nt, tr.outputs[0], xr.inputs[0])
    link(nt, edge, xr.inputs[1])
    sh = mix_sh(nt, mul(nt, XA, hero), sh, xr.outputs[0])
    link(nt, sh, out.inputs["Surface"])
    return m


def pipe_mat():
    m, nt, out = new_mat("Pipe")
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    WF, IC, PH = val(nt, "WF", 0.0), val(nt, "IC", 0.0), val(nt, "P", 0.0)
    off = node(nt, "ShaderNodeVectorMath", operation="ADD")
    link(nt, P, off.inputs[0])
    cmb = node(nt, "ShaderNodeCombineXYZ")
    link(nt, PH, cmb.inputs[1])
    link(nt, cmb.outputs[0], off.inputs[1])
    streak = noise(nt, off.outputs[0], 0.6, 3.0, 0.5, stretch=(0.3, 1.0, 0.3))
    col = col_mix(nt, "#1aa39a", "#38d2ff", IC)
    stg = mul(nt, WF, mth(nt, "ADD", 1.0, mth(nt, "MULTIPLY", IC, 0.6)), mth(nt, "MULTIPLY_ADD", streak, 1.2, 0.3))
    steel = principled(nt, "#6b6f73", 0.35, 1.0)
    sh = node(nt, "ShaderNodeAddShader")
    link(nt, steel.outputs[0], sh.inputs[0])
    link(nt, emission(nt, col, stg), sh.inputs[1])
    link(nt, sh.outputs[0], out.inputs["Surface"])
    return m


def grout_mat():
    m, nt, out = new_mat("Grout")
    x, y, z = xyz(nt, node(nt, "ShaderNodeTexCoord").outputs["Generated"])
    F = val(nt, "F", 0.0)
    b = principled(nt, "#e6dfcf", 0.45, 0.0)
    front = mul(nt, sstepv(nt, z, mth(nt, "SUBTRACT", F, 0.06), F), inv(nt, sstep(nt, F, 0.97, 1.0)))
    wet = node(nt, "ShaderNodeAddShader")
    link(nt, b.outputs[0], wet.inputs[0])
    link(nt, emission(nt, "#fff1c8", mth(nt, "MULTIPLY", front, 6.0)), wet.inputs[1])
    tr = node(nt, "ShaderNodeBsdfTransparent")
    link(nt, mix_sh(nt, sstepv(nt, z, F, mth(nt, "ADD", F, 0.01)), wet.outputs[0], tr.outputs[0]), out.inputs["Surface"])
    return m


def col_height(x, y):
    """final column height (m) at a grid cell: tall upstream, stepped down towards the toe, staggered like a site"""
    u = (y - ROWS_Y[0]) / (ROWS_Y[-1] - ROWS_Y[0])
    base = 82.0 - 52.0 * u
    jit = (mn.noise(V(x * 0.11, y * 0.11, 3.3), noise_basis='PERLIN_ORIGINAL')) * 12.0
    return max(10.0, round((base + jit) / LIFT) * LIFT)


def coil(bm, h, r=0.12):
    """one cooling coil per lift: serpentine passes along y, 1.75 m apart, U-bends at the ends (column frame)"""
    n = 8
    xs = [-7.0 + 14.0 * k / n for k in range(n + 1)]
    z = LIFT - 0.05
    while z < h:
        for k, x in enumerate(xs):
            bm_rod(bm, (x, -7.0, z), (x, 7.0, z), r, 8)
            if k < n:
                yb = 7.0 if k % 2 == 0 else -7.0
                bm_rod(bm, (x, yb, z), (xs[k + 1], yb, z), r, 8)
        z += LIFT


def build_cool(M):
    cm, pm, gm = column_mat(), pipe_mat(), grout_mat()
    M.update(column=cm, pipe=pm, grout=gm)
    cols, pipes, hero = [], [], []
    for x in COLS_X:
        for y in ROWS_Y:
            h = col_height(x, y) - BED
            bm = bmesh.new()
            bmh(bm, (0, 0, h / 2), ((CELL - GAP0) / 2, (CELL - GAP0) / 2, h / 2))
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.18, segments=2, affect="EDGES")
            ob = obj_from_bm(f"Col_{int(x)}_{int(y)}", bm, cm, loc=(x, y, BED))
            ob["hero"] = 1.0 if (x in HERO_X and y == ROWS_Y[-1]) else 0.0
            ob["mono"] = 0.0
            ob["h"] = h
            cols.append(ob)
            if ob["hero"]:
                hero.append(ob)
                bm = bmesh.new()
                coil(bm, h)
                pipes.append(obj_from_bm(f"Coil_{int(x)}", bm, pm, parent=ob))
    # the one-pour monolith
    (x0, x1), (y0, y1), (z0, z1) = MONO_X, MONO_Y, MONO_Z
    monos = []
    for name, xa in (("Mono", x1), ("MonoCut", 0.0)):          # the whole block, and its half cut open at x = 0
        bm = bmesh.new()
        bmh(bm, ((x0 + xa) / 2, (y0 + y1) / 2, (z0 + z1) / 2), ((xa - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2))
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.4, segments=2, affect="EDGES")
        ob = obj_from_bm(name, bm, cm)
        ob["hero"], ob["mono"] = 0.0, 1.0
        monos.append(ob)
    mono, monocut = monos
    # grout slabs in the joints round the hero columns (the only joints the camera sees close up)
    bm = bmesh.new()
    yh = ROWS_Y[-1]
    hh = max(o["h"] for o in hero)
    for xb in (-24.0, -8.0, 8.0, 24.0):
        bmh(bm, (xb, yh, BED + hh / 2), (0.32, CELL / 2, hh / 2))
    bmh(bm, (0.0, yh - CELL / 2, BED + hh / 2), (3 * CELL / 2, 0.32, hh / 2))
    grout = obj_from_bm("Grout", bm, gm)
    return dict(cols=cols, herocols=hero, pipes=pipes, mono=mono, monocut=monocut, grout=grout)
