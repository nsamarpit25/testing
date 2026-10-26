

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


def blended(m):
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


# ----------------------------------------------------------------------------------------------- the track path
# A centre line in the x-z plane (y = 0). s is arc length. The train rides on the N side of the rails, N = T turned
# +90 degrees in x-z, B = +y.  Layout: launch track, pull-up, vertical climb, the top-hat crest, vertical drop,
# pull-out, brake run.

SEGS = [("line", V(-330, 0, 2), V(1, 0, 0), 310.0),
        ("arc", V(-20, 0, 22), 20.0, -90.0, 0.0),
        ("line", V(0, 0, 22), V(0, 0, 1), 102.0),
        ("arc", V(15, 0, 124), 15.0, 180.0, 0.0),
        ("line", V(30, 0, 124), V(0, 0, -1), 102.0),
        ("arc", V(50, 0, 22), 20.0, 180.0, 270.0),
        ("line", V(50, 0, 2), V(1, 0, 0), 380.0)]
SEG_LEN = [s[3] if s[0] == "line" else abs(s[4] - s[3]) * math.pi / 180 * s[2] for s in SEGS]
S_TOTAL = sum(SEG_LEN)
S_PULLUP = SEG_LEN[0]                          # 310
S_UP = S_PULLUP + SEG_LEN[1]                   # start of the vertical climb (z = 22)
S_CREST = S_UP + SEG_LEN[2]                    # start of the crest arc
S_TOP = S_CREST + SEG_LEN[3] / 2               # the very top (x = 15, z = 139)
S_DOWN = S_CREST + SEG_LEN[3]
S_BRAKE = sum(SEG_LEN[:6])                     # start of the brake run line (x = 50)
BR0, BR1 = S_BRAKE + 20, S_BRAKE + 280         # copper fins on the brake run: x = 70 .. 330
LF0, LF1 = 40.0, 300.0                         # retractable fins on the launch track: x = -290 .. -30
LFX0 = 160.0                                   # launch fins from here on are separate objects (they pop up on screen)
FIN_LEN, FIN_GAP, FIN_H, FIN_T = 2.4, 0.25, 0.36, 0.03
CAR_LEN, N_CARS = 3.4, 4
TRAIN_LEN = N_CARS * CAR_LEN + 1.3


def track_frame(s):
    s = clamp(s, 0.0, S_TOTAL)
    for sg, L in zip(SEGS, SEG_LEN):
        if s <= L or sg is SEGS[-1]:
            break
        s -= L
    if sg[0] == "line":
        P = sg[1] + sg[2] * s
        T = sg[2].copy()
    else:
        c, R, a0, a1 = sg[1], sg[2], sg[3], sg[4]
        d = 1 if a1 > a0 else -1
        a = rad(a0) + d * s / R
        P = c + V(R * math.cos(a), 0, R * math.sin(a))
        T = V(-math.sin(a), 0, math.cos(a)) * d
    N = V(-T.z, 0, T.x)
    return P, T, N


def frame_matrix(s, lift=0.0):
    P, T, N = track_frame(s)
    m = Matrix((T, V(0, 1, 0), N)).transposed().to_4x4()
    m.translation = P + N * lift
    return m


def s_of_x(x):  # on the launch track or the brake run
    return x + 330 if x < -20 else S_BRAKE + (x - 50)


# ----------------------------------------------------------------------------------------------- ride physics

class Run:
    """1-D run of the train's front along s: hydraulic launch to v_launch, gravity along the track, light drag,
    eddy-current braking (a = -k v) on the brake run (and on the launch-track fins when rolling back)."""

    def __init__(self, v_launch, rollback=False, dur=40.0, dt=1 / 400):
        s, v, t, launching = 30.0 + TRAIN_LEN, 0.0, 0.0, True
        self.t, self.s, self.v = [0.0], [s], [0.0]
        while t < dur:
            T = track_frame(s)[1]
            a = -9.81 * T.z - 0.00008 * v * abs(v)
            if launching:
                if v < v_launch:
                    a = 16.34
                else:
                    launching = False
            if BR0 - 6 < s < BR1 + 6 and v > 0:
                a -= 0.2 * v
            if s >= BR1 + 6 and v > 0:
                a = -2.2
            if rollback and v < 0 and s < LF1 + TRAIN_LEN:
                a -= 0.42 * v
                if abs(v) < 1.2:
                    a = -v / dt * 0.02
            v += a * dt
            if s >= BR1 + 6 and v < 0:
                v = 0.0
            s += v * dt
            t += dt
            self.t.append(t), self.s.append(s), self.v.append(v)

    def at(self, tau):
        tau = clamp(tau, 0.0, self.t[-1])
        i = min(int(tau / (self.t[1] - self.t[0])), len(self.t) - 2)
        u = (tau - self.t[i]) / (self.t[i + 1] - self.t[i])
        return lerp(self.s[i], self.s[i + 1], u), lerp(self.v[i], self.v[i + 1], u)

    def tau_s(self, s_target, falling=False):
        """First time the front reaches s_target (moving forward, or moving backward with falling=True)."""
        for i in range(1, len(self.t)):
            if (not falling and self.s[i - 1] < s_target <= self.s[i]) or \
                    (falling and self.v[i] < 0 and self.s[i - 1] > s_target >= self.s[i]):
                return self.t[i]
        return self.t[-1]

    def tau_apex(self):
        i = max(range(len(self.s)), key=lambda k: self.s[k])
        return self.t[i]


RUN = Run(57.2)
ROLL = Run(46.0, rollback=True, dur=30.0)
TAU_LAUNCH = 0.55            # the main run's launch starts at t = 0.55


# ----------------------------------------------------------------------------------------------- geometry helpers

def bm_boxM(bm, M, c, s):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r["verts"]:
        v.co = M @ Vector((v.co.x * s[0] + c[0], v.co.y * s[1] + c[1], v.co.z * s[2] + c[2]))


def bm_tube(bm, pts, r, n=12):
    """Tube through 3D points (each ring perpendicular to the local direction)."""
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = d.orthogonal().normalized()
        b = d.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / n) + b * math.sin(2 * math.pi * k / n)) * r)
                      for k in range(n)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])


def path_samples(s0, s1, step_line=12.0, step_arc=0.8):
    out, s = [s0], s0
    while s < s1:
        P, T, N = track_frame(s)
        s = min(s1, s + (step_line if abs(T.x) > 0.999 or abs(T.z) > 0.999 else step_arc))
        out.append(s)
    # straight lines need extra samples next to arcs so rings don't skew
    return sorted(set(out + [x for x in (S_PULLUP, S_UP, S_CREST, S_DOWN, S_BRAKE - SEG_LEN[5], S_BRAKE) if s0 < x < s1]))


def bevel(ob, w=0.04, segs=3):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = w
    m.segments = segs
    m.limit_method = "ANGLE"
    return ob


# ----------------------------------------------------------------------------------------------- materials

def sky_world():
    w = bpy.data.worlds.new("Dusk")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    D = node(nt, "ShaderNodeTexCoord").outputs["Generated"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, D, sep.inputs[0])
    z = sep.outputs[2]
    col = ramp3(nt, mth(nt, "MULTIPLY_ADD", z, 0.5, 0.5),
                [(0.0, "#07090c"), (0.49, "#0e1116"), (0.5, "#7d6250"), (0.52, "#4a5160"), (0.6, "#2b3445"),
                 (1.0, "#0b0e14")])
    dp = node(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
    link(nt, D, dp.inputs[0])
    dp.inputs[1].default_value = SUN_DIR
    glow = mth(nt, "POWER", mth(nt, "MAXIMUM", dp.outputs["Value"], 0.0), 40.0)
    halo = mth(nt, "MULTIPLY", mth(nt, "POWER", mth(nt, "MAXIMUM", dp.outputs["Value"], 0.0), 5.0), 0.12)
    g = mth(nt, "ADD", glow, halo)
    mix = node(nt, "ShaderNodeMix", data_type="RGBA", blend_type="ADD")
    link(nt, g, mix.inputs["Factor"])
    link(nt, col, mix.inputs[6])
    mix.inputs[7].default_value = (*lin("#ffb27a"), 1)
    link(nt, mix.outputs[2], bg.inputs[0])
    link(nt, val(nt, "W", 1.0), bg.inputs[1])
    link(nt, bg.outputs[0], out.inputs[0])
    return w


def fin_mat(name, world):
    """Copper fin. Heat (Value H) glows behind the magnets: d = MX - x (world x on the brake run, object x in the
    macro studio), thermal ramp. Value X turns the copper see-through (x-ray)."""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"] if not world else \
        node(nt, "ShaderNodeNewGeometry").outputs["Position"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    d = mth(nt, "SUBTRACT", val(nt, "MX", -1e4), sep.outputs[0])
    L = 14.0 if world else 0.45
    heat = mth(nt, "MULTIPLY", mth(nt, "GREATER_THAN", d, -0.02 if not world else -0.5),
               mth(nt, "POWER", 2.718, mth(nt, "DIVIDE", mth(nt, "MAXIMUM", d, 0.0), -L)))
    heat = mth(nt, "MULTIPLY", heat, val(nt, "H", 0.0))
    b = node(nt, "ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*lin(PAL["copper"]), 1)
    b.inputs["Metallic"].default_value = 0.8
    b.inputs["Roughness"].default_value = 0.3
    link(nt, ramp3(nt, mth(nt, "MINIMUM", heat, 1.0), [(0.0, "#2a0400"), (0.5, "#d62a00"), (0.85, "#ff7a12"),
                                                       (1.0, "#ffb347")]), b.inputs["Emission Color"])
    link(nt, mth(nt, "MULTIPLY", heat, 4.0 if world else 2.0), b.inputs["Emission Strength"])
    shader = b.outputs[0]
    if not world:
        tr, mx, em, ad = (node(nt, "ShaderNodeBsdfTransparent"), node(nt, "ShaderNodeMixShader"),
                          node(nt, "ShaderNodeEmission"), node(nt, "ShaderNodeAddShader"))
        em.inputs[0].default_value = (*lin(PAL["copper"]), 1)
        em.inputs[1].default_value = 0.35
        link(nt, tr.outputs[0], ad.inputs[0])
        link(nt, em.outputs[0], ad.inputs[1])
        link(nt, mth(nt, "MULTIPLY", val(nt, "X", 0.0), 0.8), mx.inputs[0])
        link(nt, shader, mx.inputs[1])
        link(nt, ad.outputs[0], mx.inputs[2])
        shader = mx.outputs[0]
        blended(m)
    link(nt, shader, out.inputs[0])
    m.diffuse_color = (*lin(PAL["copper"]), 1)
    return m


def eddy_mat(name):
    """Dashed glowing ring in the object's x-z plane; Value P spins the dashes, S fades it in."""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    ang = mth(nt, "ARCTAN2", sep.outputs[2], sep.outputs[0])
    ph = mth(nt, "FRACT", mth(nt, "ADD", mth(nt, "MULTIPLY", ang, 9 / (2 * math.pi)), val(nt, "P", 0.0)))
    dash = mth(nt, "MULTIPLY", mth(nt, "LESS_THAN", ph, 0.62), mth(nt, "SUBTRACT", 1.0, mth(nt, "MULTIPLY", ph, 0.9)))
    S = val(nt, "S", 0.0)
    fac = mth(nt, "MULTIPLY", dash, mth(nt, "MINIMUM", S, 1.0))
    tr, em, mx = node(nt, "ShaderNodeBsdfTransparent"), node(nt, "ShaderNodeEmission"), node(nt, "ShaderNodeMixShader")
    em.inputs[0].default_value = (*lin(PAL["cyan"]), 1)
    link(nt, mth(nt, "MULTIPLY", S, 4.0), em.inputs[1])
    link(nt, fac, mx.inputs[0])
    link(nt, tr.outputs[0], mx.inputs[1])
    link(nt, em.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], out.inputs[0])
    return blended(m)


def glow_pbr(name, col, rough, metal, ecol, coat=0.0):
    """Principled with an animatable emission strength (Value "S")."""
    m, nt, out = new_mat(name)
    b = node(nt, "ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*lin(col), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat:
        for k in ("Coat Weight", "Coat"):
            try:
                b.inputs[k].default_value = coat
                break
            except KeyError:
                pass
    b.inputs["Emission Color"].default_value = (*lin(ecol), 1)
    link(nt, val(nt, "S", 0.0), b.inputs["Emission Strength"])
    link(nt, b.outputs[0], out.inputs[0])
    m.diffuse_color = (*lin(col), 1)
    return m


def xray_metal(name, col, glow=False):
    """Metal that turns see-through (Value X) for cutaways; with glow, an emission Value S like the magnets."""
    m, nt, out = new_mat(name)
    b = node(nt, "ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*lin(col), 1)
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Emission Color"].default_value = (*lin(PAL["cyan"]), 1)
    link(nt, val(nt, "S", 0.0), b.inputs["Emission Strength"])
    tr, mx = node(nt, "ShaderNodeBsdfTransparent"), node(nt, "ShaderNodeMixShader")
    link(nt, val(nt, "X", 0.0), mx.inputs[0])
    link(nt, b.outputs[0], mx.inputs[1])
    link(nt, tr.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], out.inputs[0])
    m.diffuse_color = (*lin(col), 1)
    return blended(m)


def ground_mat():
    m, nt, out = new_mat("Ground")
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    nz = node(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.08
    nz.inputs["Detail"].default_value = 8
    link(nt, P, nz.inputs["Vector"])
    b = node(nt, "ShaderNodeBsdfPrincipled")
    link(nt, ramp3(nt, nz.outputs["Fac"], [(0.3, "#121519"), (0.7, "#20252b")]), b.inputs["Base Color"])
    link(nt, ramp3(nt, nz.outputs["Fac"], [(0.35, "#9a9a9a"), (0.65, "#d0d0d0")]), b.inputs["Roughness"])
    link(nt, b.outputs[0], out.inputs[0])
    return m


def studio_mat(name, c0, c1):
    """Cyc backdrop: dark slate with a soft vertical gradient (object z)."""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    b = node(nt, "ShaderNodeBsdfPrincipled")
    link(nt, ramp3(nt, mth(nt, "DIVIDE", sep.outputs[2], 4.0), [(0.0, c0), (1.0, c1)]), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.42
    link(nt, b.outputs[0], out.inputs[0])
    return m


def materials():
    M = {}
    M["track"] = pbr("Track", PAL["track"], 0.32, 0.75)
    M["spine"] = pbr("Spine", "#8c96a1", 0.36, 0.7)
    M["lattice"] = pbr("Lattice", PAL["lattice"], 0.45, 0.6)
    M["concrete"] = pbr("Concrete", "#3a3f46", 0.8)
    M["ground"] = ground_mat()
    M["tree"] = pbr("Tree", "#0c0f12", 0.9)
    M["bldg"] = pbr("Bldg", "#15191e", 0.7, emit="#ffc48a", estr=0.0)
    M["lamp"] = emis("Lamp", "#ffcf9a", 9.0)
    M["redlamp"] = emis("RedLamp", "#ff3020", 6.0)
    M["body"] = pbr("Body", "#d6dade", 0.24, 0.15)
    for k in ("Coat Weight", "Coat"):
        try:
            M["body"].node_tree.nodes["Principled BSDF"].inputs[k].default_value = 1.0
            break
        except KeyError:
            pass
    M["seat"] = pbr("Seat", "#15191e", 0.55)
    M["stripe"] = emis("Stripe", PAL["cyan"], 2.2)
    M["chassis"] = pbr("Chassis", "#2b3138", 0.4, 0.8)
    M["wheel"] = pbr("Wheel", "#1a1d21", 0.55, 0.2)
    for i in range(N_CARS):
        M[f"mag{i}"] = glow_pbr(f"Magnet{i}", PAL["nickel"], 0.22, 1.0, PAL["cyan"])
    M["magstudio"] = glow_pbr("MagnetStudio", PAL["nickel"], 0.22, 1.0, PAL["cyan"])
    M["yoke"] = pbr("Yoke", "#6f7882", 0.3, 0.9)
    M["fin_world"] = fin_mat("FinBrake", True)
    M["fin_launch"] = pbr("FinLaunch", PAL["copper"], 0.32, 0.8)
    M["fin_macro"] = fin_mat("FinMacro", False)
    M["bracket"] = pbr("Bracket", "#6c7580", 0.4, 0.8)
    M["eddyA"] = eddy_mat("EddyA")
    M["eddyB"] = eddy_mat("EddyB")
    M["field"] = emis("Field", PAL["cyan"], 0.0, alpha=0.0)
    M["arrow_c"] = emis("ArrowC", PAL["cyan"], 0.0, alpha=0.0)
    M["arrow_a"] = emis("ArrowA", PAL["amber"], 0.0, alpha=0.0)
    M["cyc"] = studio_mat("Cyc", "#161a20", "#2a313b")
    M["plate"] = pbr("Plate", "#9aa3ad", 0.3, 1.0)
    M["caliper"] = blended(pbr("Caliper", "#7d8792", 0.3, 0.8, alpha=0.32))
    M["slots"] = pbr("Slots", "#2a2f36", 0.4, 0.6)
    M["xmetal"] = xray_metal("XMetal", "#8a929c")
    M["xmag"] = xray_metal("XMag", PAL["nickel"], glow=True)
    M["backpanel"] = emis("BackPanel", "#dfeaff", 0.0)
    m = glow_pbr("Pad", "#3b3430", 0.8, 0.0, PAL["amber"])
    M["pad"] = m
    M["spark"] = emis("Spark", "#ffb050", 18.0)
    M["haze"] = None
    m, nt, out = new_mat("Haze")
    sc = node(nt, "ShaderNodeVolumeScatter")
    sc.inputs["Color"].default_value = (*lin("#9aa4b2"), 1)
    link(nt, val(nt, "D", 0.00035), sc.inputs["Density"])
    link(nt, sc.outputs[0], out.inputs["Volume"])
    M["haze"] = m
    return M


# ----------------------------------------------------------------------------------------------- the ride

def build_ride(M):
    R = {}
    # rails, spine, ties
    ss_ = path_samples(0.0, S_TOTAL)
    bm = bmesh.new()
    for y in (-0.6, 0.6):
        bm_tube(bm, [frame_matrix(s) @ V(0, y, 0) for s in ss_], 0.1, 10)
    obj_from_bm("Rails", bm, M["track"], smooth=True)
    bm = bmesh.new()
    bm_tube(bm, [frame_matrix(s) @ V(0, 0, -0.95) for s in ss_], 0.42, 18)
    obj_from_bm("Spine", bm, M["spine"], smooth=True)
    bm = bmesh.new()
    s = 1.0
    while s < S_TOTAL - 1:
        F = frame_matrix(s)
        bm_boxM(bm, F, (0, 0, -0.16), (0.14, 1.3, 0.09))
        for y in (-0.45, 0.45):
            bm_rod(bm, F @ V(0, y, -0.16), F @ V(0, y * 0.35, -0.75), 0.045, 6)
        s += 1.6
    obj_from_bm("Ties", bm, M["track"])
    # ground supports on the flat parts
    bm = bmesh.new()
    for x in list(range(-326, -24, 10)) + list(range(56, 428, 10)):
        bm_cyl(bm, 0.28, 0.32, 0.9, 12, Matrix.Translation((x, 0, 0.45)))
        bm_boxM(bm, Matrix(), (x, 0, 0.04), (1.2, 2.2, 0.08))
    obj_from_bm("Footings", bm, M["concrete"])
    # the top-hat tower: lattice between the climb (x=0) and the drop (x=30)
    bm = bmesh.new()
    cols = [(x, y) for x in (3.0, 15.0, 27.0) for y in (-7.0, 7.0)]
    for x, y in cols:
        bm_rod(bm, V(x, y, 0), V(x, y * 0.65, 128), 0.55, 14)
    zs = list(range(10, 128, 12))
    for z in zs:
        f = z / 128
        pts = [V(x, y * (1 - 0.35 * f), z) for x, y in cols]
        for a, b in ((0, 2), (2, 4), (1, 3), (3, 5), (0, 1), (4, 5), (2, 3)):
            bm_rod(bm, pts[a], pts[b], 0.22, 8)
    for z0, z1 in zip(zs, zs[1:]):
        for a, b in ((0, 2), (2, 4), (1, 3), (3, 5)):
            f0, f1 = z0 / 128, z1 / 128
            p0 = V(cols[a][0], cols[a][1] * (1 - 0.35 * f0), z0)
            p1 = V(cols[b][0], cols[b][1] * (1 - 0.35 * f1), z1)
            bm_rod(bm, p0, p1, 0.14, 6)
    for s in range(int(S_UP) + 6, int(S_CREST), 12):     # arms from the lattice to the spines
        F = frame_matrix(s)
        bm_rod(bm, F @ V(0, 0, -0.95), V(3.0, 0, F.translation.z), 0.25, 8)
    for s in range(int(S_DOWN) + 6, int(S_DOWN + SEG_LEN[4]), 12):
        F = frame_matrix(s)
        bm_rod(bm, F @ V(0, 0, -0.95), V(27.0, 0, F.translation.z), 0.25, 8)
    for s in (S_CREST + 6, S_TOP, S_DOWN - 6):
        F = frame_matrix(s)
        bm_rod(bm, F @ V(0, 0, -0.95), V(15, 0, 120), 0.3, 8)
    for x, y in cols:
        bm_boxM(bm, Matrix(), (x, y, 0.3), (3.2, 3.2, 0.6))
    obj_from_bm("Tower", bm, M["lattice"], smooth=False)
    # aircraft warning lamps on top
    for k, (x, y) in enumerate(((12, -2), (18, 2))):
        sphere(f"Beacon{k}", 0.35, (x, y, 140.4), M["redlamp"], seg=12)
    # copper fins on the brake run (one mesh) + their brackets
    bm, bb = bmesh.new(), bmesh.new()
    s = BR0
    while s + FIN_LEN <= BR1:
        F = frame_matrix(s + FIN_LEN / 2)
        bm_boxM(bm, F, (0, 0, FIN_H / 2 + 0.02), (FIN_LEN, FIN_T, FIN_H))
        bm_boxM(bb, F, (0, 0, -0.12), (FIN_LEN * 0.9, 0.14, 0.22))
        s += FIN_LEN + FIN_GAP
    R["brakefins"] = obj_from_bm("BrakeFins", bm, M["fin_world"])
    obj_from_bm("BrakeBrackets", bb, M["bracket"])
    # retractable launch-track fins: a static (flat) mesh up to LFX0, then separate hinged objects
    bm, bb = bmesh.new(), bmesh.new()
    R["lfins"] = []
    s = LF0
    while s + FIN_LEN <= LF1:
        F = frame_matrix(s + FIN_LEN / 2)
        bm_boxM(bb, F, (0, 0, -0.12), (FIN_LEN * 0.9, 0.14, 0.22))
        if s < LFX0:
            bm_boxM(bm, F @ Matrix.Rotation(rad(-90), 4, "X"), (0, 0, FIN_H / 2 + 0.02), (FIN_LEN, FIN_T, FIN_H))
        else:
            b1 = bmesh.new()
            bm_box(b1, (0, 0, FIN_H / 2 + 0.02), (FIN_LEN, FIN_T, FIN_H))
            ob = obj_from_bm(f"LFin{len(R['lfins'])}", b1, M["fin_launch"], loc=F.translation)
            ob.rotation_euler = (rad(-90), 0, 0)
            R["lfins"].append(ob)
        s += FIN_LEN + FIN_GAP
    obj_from_bm("LaunchFinsFlat", bm, M["fin_launch"])
    obj_from_bm("LaunchBrackets", bb, M["bracket"])
    # station canopy at the end of the brake run, launch-track light poles
    bm = bmesh.new()
    for x in range(352, 424, 8):
        for y in (-4.5, 4.5):
            bm_cyl(bm, 0.18, 0.18, 5.6, 10, Matrix.Translation((x, y, 2.8)))
    bm_boxM(bm, Matrix(), (388, 0, 5.8), (78, 11, 0.4))
    bm_boxM(bm, Matrix(), (388, 3.4, 1.3), (70, 3.0, 1.0))
    obj_from_bm("Station", bm, M["lattice"])
    box("StationRoofGlow", (388, 0, 5.56), (74, 9, 0.06), M["lamp"])
    bm, bl = bmesh.new(), bmesh.new()
    for x in list(range(-320, -30, 24)) + list(range(70, 340, 24)):
        y = -9.0
        bm_cyl(bm, 0.12, 0.16, 9.0, 8, Matrix.Translation((x, y, 4.5)))
        bm_rod(bm, V(x, y, 9.0), V(x, y + 1.6, 9.3), 0.07, 6)
        bm_boxM(bl, Matrix(), (x, y + 1.7, 9.2), (0.6, 0.35, 0.12))
    obj_from_bm("Poles", bm, M["lattice"])
    obj_from_bm("PoleLamps", bl, M["lamp"])
    # ground, distant tree line, a few park buildings, haze
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=2500)
    obj_from_bm("Ground", bm, M["ground"])
    rnd = random.Random(7)
    bm = bmesh.new()
    for k in range(900):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(420, 900)
        h = rnd.uniform(9, 22)
        bm_cyl(bm, rnd.uniform(3, 6), 0.3, h, 7, Matrix.Translation((r * math.cos(a) + 40, r * math.sin(a), h / 2)))
    obj_from_bm("Trees", bm, M["tree"])
    bm = bmesh.new()
    for k in range(14):
        a = rnd.uniform(0.2, 2.9)
        r = rnd.uniform(240, 380)
        bm_boxM(bm, Matrix(), (r * math.cos(a) + 40, r * math.sin(a), 6), (rnd.uniform(20, 50), rnd.uniform(15, 30), 12))
    obj_from_bm("Buildings", bm, M["bldg"])
    bm = bmesh.new()
    bm_box(bm, (40, 0, 120), (2200, 2200, 240))
    R["haze"] = obj_from_bm("Haze", bm, M["haze"])
    R["haze"].visible_shadow = False
    return R


def build_car(M, i, parent=None):
    """One car in its own frame: x forward, z up from the rail plane. Origin on the track centre line."""
    root = empty(f"Car{i}")
    root.rotation_mode = "QUATERNION"
    h = CAR_LEN / 2 - 0.12
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0.56), (2 * h, 1.5, 0.12))
    obj_from_bm(f"Chassis{i}", bm, M["chassis"], root)
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0.94), (2 * h - 0.1, 1.7, 0.66))
    bevel(obj_from_bm(f"Body{i}", bm, M["body"], root), 0.14, 4)
    bm = bmesh.new()
    for x in (-0.75, 0.65):
        bm_box(bm, (x, 0, 1.38), (0.32, 1.42, 0.62))
    bm_box(bm, (0, 0, 1.24), (2 * h - 0.4, 1.36, 0.06))
    bevel(obj_from_bm(f"Seats{i}", bm, M["seat"], root), 0.08, 3)
    bm = bmesh.new()
    for y in (-0.862, 0.862):
        bm_box(bm, (0, y, 1.02), (2 * h - 0.5, 0.012, 0.045))
    obj_from_bm(f"Stripe{i}", bm, M["stripe"], root)
    if i == 0:   # nose
        bm = bmesh.new()
        r0 = [V(h - 0.05, y, z) for y, z in ((-0.85, 0.62), (0.85, 0.62), (0.85, 1.26), (-0.85, 1.26))]
        r1 = [V(h + 1.35, y, z) for y, z in ((-0.32, 0.62), (0.32, 0.62), (0.3, 0.86), (-0.3, 0.86))]
        vs0, vs1 = [bm.verts.new(p) for p in r0], [bm.verts.new(p) for p in r1]
        for k in range(4):
            bm.faces.new((vs0[k], vs0[(k + 1) % 4], vs1[(k + 1) % 4], vs1[k]))
        bm.faces.new(vs1)
        bevel(obj_from_bm("Nose", bm, M["body"], root), 0.1, 3)
        bm = bmesh.new()
        for y in (-0.6, 0.6):
            bm_box(bm, (h + 0.55, y * 0.9, 1.0), (0.5, 0.012, 0.04))
        obj_from_bm("NoseStripe", bm, M["stripe"], root)
    bm = bmesh.new()   # wheel bogies on both rails
    for x in (-h + 0.35, h - 0.35):
        for y in (-0.6, 0.6):
            bm_boxM(bm, Matrix(), (x, y, 0.42), (0.55, 0.22, 0.2))
            for z in (0.24, -0.24):
                bm_cyl(bm, 0.13, 0.13, 0.12, 14, Matrix.Translation((x, y, z)) @ Matrix.Rotation(rad(90), 4, "X"))
            bm_cyl(bm, 0.1, 0.1, 0.1, 12, Matrix.Translation((x, y * 1.3, 0.0)))
    obj_from_bm(f"Bogies{i}", bm, M["wheel"], root)
    # magnets: two rows straddling the fin line, on a yoke under the chassis
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0.475), (2 * h - 0.5, 0.36, 0.05))
    obj_from_bm(f"Yoke{i}", bm, M["yoke"], root)
    bm = bmesh.new()
    n = 9
    for k in range(n):
        x = (k - (n - 1) / 2) * (2 * h - 0.6) / n
        for y in (-0.085, 0.085):
            bm_box(bm, (x, y, 0.3), (0.24, 0.09, 0.3))
    bevel(obj_from_bm(f"Magnets{i}", bm, M[f"mag{i}"], root), 0.012, 2)
    return root


def build_train(M):
    return [build_car(M, i) for i in range(N_CARS)]


# ----------------------------------------------------------------------------------------------- friction studio

def build_friction(M):
    F = {}
    bm = bmesh.new()
    bm_box(bm, (0, 14, 6), (60, 1, 12))
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30)
    obj_from_bm("FrCyc", bm, M["cyc"], loc=FR + V(0, 0, -0.4))
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0), (40, 0.04, 0.4))
    F["plate"] = obj_from_bm("FrPlate", bm, M["plate"], loc=FR)
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0.3), (0.5, 0.42, 0.14))
    for y in (-0.19, 0.19):
        bm_box(bm, (0, y, 0.08), (0.5, 0.06, 0.5))
    bevel(obj_from_bm("Caliper", bm, M["caliper"], loc=FR), 0.03, 3)
    F["pads"] = []
    for k, sg in enumerate((-1, 1)):
        bm = bmesh.new()
        bm_box(bm, (0, sg * 0.5, 0), (0.7, 1.0, 0.3))
        pad = obj_from_bm(f"Pad{k}", bm, M["pad"], loc=FR + V(0, sg * 0.021, 0.02))
        pad.scale = (1, 0.13, 1)
        F["pads"].append(pad)
    bm = bmesh.new()
    for k in range(-34, 35):
        for sg in (-1, 1):
            bm_box(bm, (k * 0.6, sg * 0.021, 0.15), (0.14, 0.004, 0.05))
            bm_box(bm, (k * 0.6 + 0.3, sg * 0.021, -0.15), (0.14, 0.004, 0.05))
    obj_from_bm("FrSlots", bm, M["slots"], F["plate"])
    rnd = random.Random(3)
    F["sparks"] = []
    for k in range(46):
        bm = bmesh.new()
        bm_box(bm, (0, 0, 0), (0.09, 0.008, 0.008))
        sp = obj_from_bm(f"Spark{k}", bm, M["spark"], loc=FR)
        sp.rotation_mode = "QUATERNION"
        F["sparks"].append((sp, rnd.uniform(0, 1), rnd.uniform(2.5, 6.0), rnd.uniform(-0.6, 0.6), rnd.uniform(0.6, 2.6),
                            rnd.uniform(0.25, 0.55)))
    for k, (loc, energy, size, col) in enumerate((((-1.2, -2.0, 2.2), 900, 2.5, "#fff1e2"), ((1.5, 3.0, 1.2), 700, 3.0, "#a8c8ff"))):
        ld = bpy.data.lights.new(f"FrLight{k}", "AREA")
        ld.energy, ld.size, ld.color = energy, size, lin(col)
        lo = bpy.data.objects.new(f"FrLight{k}", ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = FR + V(*loc)
        lo.rotation_euler = (V(0, 0, 0) - V(*loc)).to_track_quat("-Z", "Y").to_euler()
    return F


# ----------------------------------------------------------------------------------------------- macro studio

def arrow(name, length, r, mat, parent=None):
    bm = bmesh.new()
    bm_cyl(bm, r, r, length - r * 3, 16, Matrix.Translation(((length - r * 3) / 2, 0, 0)) @ Matrix.Rotation(rad(90), 4, "Y"))
    bm_cyl(bm, r * 2.4, 0.0, r * 3, 20, Matrix.Translation((length - r * 1.5, 0, 0)) @ Matrix.Rotation(rad(90), 4, "Y"))
    ob = obj_from_bm(name, bm, mat, parent)
    return ob


def build_macro(M):
    K = {}
    bm = bmesh.new()
    bm_box(bm, (0, 9, 4), (40, 1, 10))
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=20)
    obj_from_bm("McCyc", bm, M["cyc"], loc=MC + V(0, 0, -0.6))
    # one fin on its bracket, with rail stubs for context
    bm = bmesh.new()
    bm_box(bm, (0, 0, FIN_H / 2 + 0.02), (3.4, FIN_T, FIN_H))
    K["fin"] = obj_from_bm("McFin", bm, M["fin_macro"], loc=MC)
    bm = bmesh.new()
    bm_box(bm, (0, 0, -0.12), (3.2, 0.14, 0.22))
    obj_from_bm("McBracket", bm, M["bracket"], loc=MC)
    bm = bmesh.new()
    for y in (-0.6, 0.6):
        bm_tube(bm, [V(x, y, 0) for x in (-4, 4)], 0.1, 16)
    bm_tube(bm, [V(x, 0, -0.95) for x in (-4, 4)], 0.42, 24)
    obj_from_bm("McTrack", bm, M["track"], loc=MC, smooth=True)
    # the moving magnet: two blocks on a U-yoke, a slice of chassis above
    rig = empty("MagRig", MC)
    K["rig"] = rig
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0.5), (0.3, 0.42, 0.06))
    bm_box(bm, (0, 0.165, 0.3), (0.3, 0.07, 0.38))
    bevel(obj_from_bm("McYoke", bm, M["yoke"], rig), 0.01, 2)
    bm = bmesh.new()
    bm_box(bm, (0, -0.165, 0.3), (0.3, 0.07, 0.38))
    bevel(obj_from_bm("McYokeNear", bm, M["xmetal"], rig), 0.01, 2)
    bm = bmesh.new()
    bm_box(bm, (0, 0.085, 0.3), (0.26, 0.09, 0.3))
    bevel(obj_from_bm("McMagnets", bm, M["magstudio"], rig), 0.012, 2)
    bm = bmesh.new()
    bm_box(bm, (0, -0.085, 0.3), (0.26, 0.09, 0.3))
    bevel(obj_from_bm("McMagNear", bm, M["xmag"], rig), 0.012, 2)
    bm = bmesh.new()   # field lines across the gap, through the fin
    for x in (-0.09, -0.03, 0.03, 0.09):
        for z in (0.2, 0.28, 0.36, 0.42):
            bm_rod(bm, V(x, -0.04, z), V(x, 0.04, z), 0.0035, 6)
    K["field"] = obj_from_bm("McField", bm, M["field"], rig)
    # eddy rings ahead of and behind the magnet (they ride with the rig but sit on the fin plane)
    K["rings"] = []
    for k, (dx, mat) in enumerate(((0.27, M["eddyA"]), (-0.27, M["eddyB"]))):
        bm = bmesh.new()
        for y in (-0.019, 0.019):
            pts = [V(0.105 * math.cos(a), y, 0.105 * math.sin(a))
                   for a in [2 * math.pi * j / 64 for j in range(65)]]
            bm_tube(bm, pts, 0.0065, 8)
            pts = [V(0.06 * math.cos(a), y, 0.06 * math.sin(a)) for a in [2 * math.pi * j / 48 for j in range(49)]]
            bm_tube(bm, pts, 0.005, 8)
        ring = obj_from_bm(f"Eddy{k}", bm, mat, rig, loc=(dx, 0, 0.21))
        K["rings"].append(ring)
    K["arrow_move"] = arrow("ArrowMove", 0.55, 0.018, M["arrow_c"], rig)
    K["arrow_move"].location = (-0.1, 0, 0.68)
    K["arrow_back"] = arrow("ArrowBack", 0.5, 0.02, M["arrow_a"], rig)
    K["arrow_back"].location = (0.36, -0.32, 0.3)
    K["arrow_back"].rotation_euler = (0, 0, math.pi)
    for k, (loc, energy, size, col) in enumerate((((-0.8, -1.6, 1.6), 520, 1.6, "#fff4e8"),
                                                  ((1.4, 1.6, 0.9), 420, 1.4, "#a9c9ff"),
                                                  ((-2.4, 0.0, 0.32), 0, 0.6, "#cfe6ff"))):
        ld = bpy.data.lights.new(f"McLight{k}", "AREA")
        ld.energy, ld.size, ld.color = energy, size, lin(col)
        lo = bpy.data.objects.new(f"McLight{k}", ld)
        bpy.context.scene.collection.objects.link(lo)
        lo.location = MC + V(*loc)
        lo.rotation_euler = (V(0, 0, 0.25) - V(*loc)).to_track_quat("-Z", "Y").to_euler()
        K[f"light{k}"] = ld
    box("BackPanel", MC + V(-2.6, 0, 0.3), (0.05, 1.6, 1.2), M["backpanel"])
    return K
