"""Kingda Ka's magnetic brakes: a fully procedural 3D reel for @how.its.engineered (episode 2, no characters).
Sets, far apart so each shot sees only its own: the ride at dusk (origin, metres: launch track along +x, the top hat
between x=0 and x=30, then the brake run), a friction-brake demo studio (FR) and a macro studio with one magnet
sweeping over one copper fin (MC). The train is placed from a 1-D physics run along the track (launch, gravity,
eddy-current braking), so every shot shows believable speeds. Every animated property is baked per frame from the
shot list; cuts get half-frame keys so motion blur never smears across a cut. Tracked on-screen labels are projected
from 3D anchors at bake time and written next to the .blend as labels.json.

blender -b --factory-startup -P kk.py -- build <out.blend>
blender -b kk.blend -P kk.py -- render <outdir> <height> <samples> [a-b | f,f,f] [--skip]
"""
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, Matrix, Quaternion

FPS = 30
T_END = 43.0
F_END = int(T_END * FPS) + 1
FR = Vector((5000, 0, 0))
MC = Vector((6000, 0, 0))
PAL = dict(sky0="#0d1015", sky1="#232b36", hz="#9a7458", track="#a7b0ba", lattice="#59626d", ground="#171b20",
           cyan="#19e3ff", amber="#ff6a1a", copper="#d0835a", nickel="#c9d2da", body="#1d232a", seat="#0e1115")
rad = math.radians
SUN_DIR = Vector((-0.6, -0.75, 0.13)).normalized()   # towards the low sun: front-left of the usual camera side (-y)


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, u):
    return a + (b - a) * u


def seg(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def ss(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def ein(u):
    u = clamp(u)
    return u * u * u


def eout(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def V(*a):
    return Vector(a)


# ----------------------------------------------------------------------------------------------- materials

def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")


def node(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def link(nt, a, b):
    nt.links.new(a, b)


def mth(nt, op, *args, clamp_=False):
    n = node(nt, "ShaderNodeMath", operation=op, use_clamp=clamp_)
    for i, v in enumerate(args):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            link(nt, v, n.inputs[i])
    return n.outputs[0]


def val(nt, name, v):
    n = node(nt, "ShaderNodeValue")
    n.name = n.label = name
    n.outputs[0].default_value = v
    return n.outputs[0]


def ramp(nt, fac, c0, c1):
    r = node(nt, "ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*lin(c0), 1)
    r.color_ramp.elements[1].color = (*lin(c1), 1)
    link(nt, fac, r.inputs[0])
    return r.outputs[0]


def pbr(name, col, rough=0.5, metal=0.0, emit=None, estr=0.0, alpha=None):
    m, nt, out = new_mat(name)
    b = node(nt, "ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*lin(col), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit), 1)
        b.inputs["Emission Strength"].default_value = estr
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
    link(nt, b.outputs[0], out.inputs[0])
    m.diffuse_color = (*lin(col), 1)
    return m


def emis(name, col, strength, alpha=None):
    """Emission with an animatable strength (Value node "S"); with alpha, a see-through glow."""
    m, nt, out = new_mat(name)
    e = node(nt, "ShaderNodeEmission")
    e.inputs[0].default_value = (*lin(col), 1)
    link(nt, val(nt, "S", strength), e.inputs[1])
    if alpha is None:
        link(nt, e.outputs[0], out.inputs[0])
    else:
        tr, mx = node(nt, "ShaderNodeBsdfTransparent"), node(nt, "ShaderNodeMixShader")
        link(nt, val(nt, "A", alpha), mx.inputs[0])
        link(nt, tr.outputs[0], mx.inputs[1])
        link(nt, e.outputs[0], mx.inputs[2])
        link(nt, mx.outputs[0], out.inputs[0])
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    m.diffuse_color = (*lin(col), 1)
    return m


def obj_from_bm(name, bm, mat=None, parent=None, loc=(0, 0, 0), smooth=False, rest=False, attrs=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    if rest:
        a = me.attributes.new("rest", "FLOAT_VECTOR", "POINT")
        a.data.foreach_set("vector", [c for v in me.vertices for c in v.co])
    for an, vals in (attrs or {}).items():
        a = me.attributes.new(an, "FLOAT", "POINT")
        a.data.foreach_set("value", vals)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    ob.parent = parent
    ob.location = loc
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    e.empty_display_size = 0.5
    return e


def bm_box(bm, c, s):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r["verts"]:
        v.co = Vector((v.co.x * s[0] + c[0], v.co.y * s[1] + c[1], v.co.z * s[2] + c[2]))


def box(name, c, s, mat, parent=None):
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0), s)
    return obj_from_bm(name, bm, mat, parent, c)


def bm_cyl(bm, r1, r2, d, n=24, M=None):
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r1, radius2=r2, depth=d,
                          matrix=M if M is not None else Matrix())


def bm_rod(bm, p0, p1, r, n=12):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    M = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm_cyl(bm, r, r, d.length, n, M)


def cyl(name, r, d, c, mat, parent=None, n=32, r2=None, smooth=True):
    bm = bmesh.new()
    bm_cyl(bm, r, r if r2 is None else r2, d, n)
    return obj_from_bm(name, bm, mat, parent, c, smooth=smooth)


def sphere(name, r, c, mat, parent=None, scale=(1, 1, 1), seg=32):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r,
                              matrix=Matrix.Diagonal((*scale, 1)))
    return obj_from_bm(name, bm, mat, parent, c, smooth=True)


def text(name, s, size, loc, rot, mat, parent=None, extrude=0.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = s
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    return ob



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


# ----------------------------------------------------------------------------------------------- shots

def put(S, idb, path, v, idx=0, const=False):
    S[(idb, path, idx)] = (float(v), const)


def nv(m, name="S"):  # (node tree, path) of a material's Value node
    return m.node_tree, f'nodes["{name}"].outputs[0].default_value'


def cam(S, eye, tgt, lens=28, roll=0.0, fstop=8.0, focus=None, yaw=0.0, pitch=0.0, clip=0.1, shake=0.0, t=0.0):
    eye, tgt = Vector(eye), Vector(tgt)
    d = tgt - eye
    if shake:   # slow, smooth handheld drift (degrees)
        yaw += rad(shake) * (math.sin(t * 1.7) * 0.6 + math.sin(t * 3.1 + 1.0) * 0.4)
        pitch += rad(shake) * (math.sin(t * 2.3 + 2.0) * 0.6 + math.sin(t * 0.9) * 0.4)
    if yaw or pitch:
        d = Matrix.Rotation(yaw, 3, "Z") @ d
        side = d.cross(Vector((0, 0, 1)))
        if side.length > 1e-6:
            d = Matrix.Rotation(pitch, 3, side.normalized()) @ d
    q = d.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), roll)
    S["cam"] = (eye, q, lens, fstop, focus if focus is not None else (tgt - eye).length, clip)


def whip(t, t_end=None, t_start=None, amt=rad(60), dur=0.16):
    y = 0.0
    if t_end is not None:
        y += amt * ein(seg(t, t_end - dur, t_end))
    if t_start is not None:
        y -= amt * (1 - eout(seg(t, t_start, t_start + dur)))
    return y


def label(S, name, p):
    S.setdefault("labels", {})[name] = Vector(p)


def place_train(S, W, s_front):
    for i, car in enumerate(W["train"]):
        sc = s_front - 1.35 - CAR_LEN / 2 - i * CAR_LEN
        m = frame_matrix(sc)
        q = m.to_quaternion()
        prev = W["qprev"].get(i)
        if prev is not None and q.dot(prev) < 0:
            q = -q
        W["qprev"][i] = q
        for k in range(3):
            put(S, car, "location", m.translation[k], k)
        for k in range(4):
            put(S, car, "rotation_quaternion", q[k], k)


def train_x(s_front):
    return track_frame(s_front)[0]


def ride_light(S, W, sun=2.6, world=1.0):
    put(S, W["sun"], "energy", sun)
    put(S, *nv_world(W, "W"), world)


def nv_world(W, name):
    return W["world"].node_tree, f'nodes["{name}"].outputs[0].default_value'


def studio(S, W):
    put(S, W["sun"], "energy", 0.0)
    put(S, W["fill"], "energy", 0.0)
    put(S, *nv_world(W, "W"), 0.06)


def defaults(t, S, W):
    M, K, F, R = W["M"], W["K"], W["F"], W["R"]
    ride_light(S, W)
    put(S, *nv(M["haze"], "D"), 0.00035)
    for i in range(N_CARS):
        put(S, *nv(M[f"mag{i}"]), 0.0)
    put(S, *nv(M["magstudio"]), 0.0)
    put(S, *nv(M["fin_world"], "H"), 0.0)
    put(S, *nv(M["fin_world"], "MX"), -1e4)
    put(S, *nv(M["fin_macro"], "H"), 0.0)
    put(S, *nv(M["fin_macro"], "X"), 0.0)
    put(S, *nv(M["fin_macro"], "MX"), -10.0)
    for k in ("eddyA", "eddyB"):
        put(S, *nv(M[k]), 0.0)
        put(S, *nv(M[k], "P"), 0.0)
    for k in ("field", "arrow_c", "arrow_a"):
        put(S, *nv(M[k]), 0.0)
        put(S, *nv(M[k], "A"), 0.0)
    for a in ("arrow_move", "arrow_back"):
        put(S, K[a], "scale", 0.001, 0)
    put(S, K["rig"], "location", MC.x - 1.4, 0)
    put(S, K["light2"], "energy", 0.0)
    put(S, *nv(M["backpanel"]), 0.0)
    put(S, *nv(M["xmetal"], "X"), 0.0)
    put(S, *nv(M["xmag"], "X"), 0.0)
    put(S, *nv(M["xmag"]), 0.0)
    put(S, W["fill"], "energy", 0.6)
    put(S, *nv(M["pad"]), 0.0)
    for p in F["pads"]:
        put(S, p, "scale", 0.13, 1)
    put(S, F["plate"], "location", FR.x, 0)
    for sp, *_ in F["sparks"]:
        put(S, sp, "hide_render", 1, const=True)
    beacon = 6.0 * (0.25 + 0.75 * (math.sin(t * 2 * math.pi / 1.6) > 0.6))
    put(S, *nv(M["redlamp"]), beacon)
    for k, ob in enumerate(R["lfins"]):
        put(S, ob, "rotation_euler", rad(-90), 0)
    place_train(S, W, RUN.at(0.0)[0])


def shots(W):
    M, K, F, R = W["M"], W["K"], W["F"], W["R"]
    L = []

    # --- line 1: zero to 128 mph in 3.5 seconds ----------------------------------------------------------------
    def S1a(t, S):   # beside the lead car; the launch rips it out of frame
        tau = t - TAU_LAUNCH
        s = RUN.at(tau)[0]
        x0 = train_x(RUN.at(0)[0]).x
        u = seg(t, 0.0, 1.25)
        cam(S, V(x0 - 0.6 + 0.4 * u, -2.7 + 0.2 * u, 2.45), V(x0 - 2.6 + 0.4 * u, 0, 2.95), lens=30,
            fstop=2.8, roll=rad(-2), shake=0.25, t=t, yaw=whip(t, t_end=1.25, amt=rad(-55)))
        place_train(S, W, s)
    L.append((0.0, 1.25, S1a))

    def S1b(t, S):   # low and ahead: the nose comes at us and passes
        tau = t - TAU_LAUNCH
        s = RUN.at(tau)[0]
        x = train_x(s).x
        u = seg(t, 1.25, 2.8)
        cam(S, V(x + 6.5 - 9.0 * ein(u), -2.9, 2.05), V(x - 2.0, 0, 2.7), lens=21, fstop=4, roll=rad(lerp(4, -3, u)),
            yaw=whip(t, t_start=1.25, amt=rad(-55)))
        place_train(S, W, s)
    L.append((1.25, 2.8, S1b))

    def S1c(t, S):   # chase cam: the train pulls away towards the tower
        tau = t - TAU_LAUNCH + 1.7
        s = RUN.at(tau)[0]
        x = train_x(s).x
        u = seg(t, 2.8, 4.7)
        eye = V(x - TRAIN_LEN - 7.0 - 26 * ein(u), -3.6 - 1.5 * u, 4.2 + 1.5 * u)
        cam(S, eye, V(eye.x + 60, 0.0, eye.z + lerp(9, 20, ss(u))), lens=19, fstop=8, roll=rad(lerp(-5, 0, u)), clip=0.3)
        place_train(S, W, s)
    L.append((2.8, 4.7, S1c))

    # --- line 2: built for speed; stopping was the challenge ---------------------------------------------------
    T2A = RUN.tau_s(S_UP + 93)

    def S2a(t, S):   # from the top of the climb looking down: it rockets up at us
        tau = T2A + (t - 5.85)
        u = seg(t, 4.7, 6.4)
        cam(S, V(-8.8, -6.8, 122 + 1.2 * u), V(-0.8, 0, lerp(94, 104, ss(u))), lens=24, fstop=5.6, roll=rad(-6), clip=0.3)
        place_train(S, W, RUN.at(tau)[0])
    L.append((4.7, 6.4, S2a))

    T2B = RUN.tau_s(S_TOP)

    def S2b(t, S):   # the crest against the dusk sky
        tau = T2B + (t - 6.88)
        u = seg(t, 6.4, 7.25)
        cam(S, V(lerp(19, 16, u), lerp(-33, -30, u), lerp(140.5, 141.5, u)), V(15, 0, 134.5), lens=27, fstop=8, clip=0.5)
        place_train(S, W, RUN.at(tau)[0])
        label(S, "height", (15, 0, 139.8))
    L.append((6.4, 7.25, S2b))

    T2C = RUN.tau_s(s_of_x(150))

    def S2c(t, S):   # down on the brake run: it comes at us at full speed
        tau = T2C + (t - 8.95)
        u = seg(t, 7.25, 9.3)
        cam(S, V(152 + 2.0 * u, -2.4, 2.75), V(60, 0, lerp(10, 6, u)), lens=lerp(48, 40, u), fstop=4, clip=0.3,
            yaw=whip(t, t_end=9.3, amt=rad(65)), shake=0.15, t=t)
        s = RUN.at(tau)[0]
        place_train(S, W, s)
        put(S, *nv(M["fin_world"], "MX"), train_x(s).x - 1.4)
        put(S, *nv(M["fin_world"], "H"), 0.0)
    L.append((7.25, 9.3, S2c))

    # --- line 3: brake pads would wear out fast; magnets under every car ----------------------------------------
    def S3a(t, S):   # friction brake demo: pads clamp, glow, spark and wear
        studio(S, W)
        u = seg(t, 9.3, 11.3)
        cam(S, FR + V(-1.2, -1.35, 0.6).lerp(V(-0.95, -1.1, 0.45), ss(u)), FR + V(-0.2, 0, 0.02), lens=36, fstop=3.2,
            yaw=whip(t, t_start=9.3, amt=rad(-60)), shake=0.2, t=t)
        put(S, F["plate"], "location", FR.x + 14 - (t - 9.3) * 12.0, 0)
        heat = ss(seg(t, 9.45, 10.5))
        put(S, *nv(M["pad"]), 3.2 * heat)
        for p in F["pads"]:
            put(S, p, "scale", lerp(0.13, 0.035, ss(seg(t, 9.7, 11.1))), 1)
        for sp, ph, spd, vy, vz, life in F["sparks"]:
            if t < 9.42:
                continue
            c = ((t - 9.42) / life + ph) % 1.0
            a = c * life * min(1.0, (t - 9.42) / 0.25)
            vel = V(-spd, vy * spd * 0.18, vz - 9.8 * a)
            p = FR + V(-0.37, 0.025 * (1 if vy > 0 else -1), 0.0) + V(-spd * a, vy * spd * 0.18 * a, vz * a - 4.9 * a * a)
            put(S, sp, "hide_render", 0, const=True)
            for k in range(3):
                put(S, sp, "location", p[k], k)
            q = vel.normalized().to_track_quat("X", "Z")
            for k in range(4):
                put(S, sp, "rotation_quaternion", q[k], k)
        if 9.55 < t < 11.2:
            label(S, "pads", FR + V(0, -0.12, 0.19))
    L.append((9.3, 11.3, S3a))

    S3B_S = s_of_x(-155)

    def S3b(t, S):   # under the parked train: rows of magnets light up car by car
        u = seg(t, 11.3, 14.8)
        x0 = train_x(S3B_S).x
        cam(S, V(x0 - 0.8 - 7.0 * ss(u), -2.15, 1.82), V(x0 - 2.4 - 7.0 * ss(u), 0, 2.32), lens=28, fstop=2.8,
            roll=rad(-3), shake=0.15, t=t)
        place_train(S, W, S3B_S)
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 3.0 * ss(seg(t, 12.75 + 0.3 * i, 13.1 + 0.3 * i)))
        if 12.9 < t < 14.75:
            label(S, "magnets", (x0 - 2.6 - 7.0 * ss(u), -0.09, 2.2))
    L.append((11.3, 14.8, S3b))

    # --- line 4: on the track, thin copper fins ----------------------------------------------------------------
    def S4(t, S):    # three-quarter dolly along the fin row
        u = seg(t, 14.8, 17.4)
        x = lerp(101, 108, ss(u))
        cam(S, V(x, -1.75, 2.85), V(x + 3.2, 0, 2.2), lens=34, fstop=2.2, roll=rad(2), shake=0.12, t=t)
        place_train(S, W, s_of_x(372))
        if 15.6 < t < 17.35:
            label(S, "fins", (x + 3.2, 0, 2.42))
    L.append((14.8, 17.4, S4))

    # --- line 5: a magnet sweeps past a fin; swirling currents: eddy currents ----------------------------------
    def mx_at(t):   # macro magnet position along the fin (relative x)
        if t < 19.8:
            return lerp(-1.35, -0.02, eout(seg(t, 17.4, 19.6)))
        return -0.02 + 0.32 * seg(t, 19.8, 24.85) + 0.25 * seg(t, 24.85, 29.0) + 0.3 * seg(t, 29.95, 32.65)

    def macro_common(t, S, mx):
        studio(S, W)
        put(S, K["rig"], "location", MC.x + mx, 0)
        put(S, *nv(M["fin_macro"], "MX"), mx)
        put(S, *nv(M["magstudio"]), 0.35)
        put(S, *nv(M["xmag"]), 0.35)

    def eddy(S, t, s_amt, spin=1.0):
        for k, m in (("eddyA", 1), ("eddyB", -1)):
            put(S, *nv(M[k]), s_amt)
            put(S, *nv(M[k], "P"), m * spin * (t - 20.3) * 1.7)
        put(S, *nv(M["field"]), 2.2 * min(1, s_amt))
        put(S, *nv(M["field"], "A"), 0.85 * min(1, s_amt))

    def S5a(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        u = seg(t, 17.4, 19.8)
        cam(S, MC + V(mx * 0.4 + 0.95, -0.85, 0.78), MC + V(mx * 0.7, 0, 0.26), lens=36, fstop=2.8,
            yaw=whip(t, t_start=17.4, amt=rad(50)))
    L.append((17.4, 19.8, S5a))

    def S5b(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), ss(seg(t, 19.85, 20.5)))
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), 0.8 * ss(seg(t, 19.85, 20.5)))
        eddy(S, t, ss(seg(t, 20.35, 21.0)))
        u = ss(seg(t, 19.8, 23.8))
        a = rad(lerp(-90, -60, u))
        r = lerp(1.0, 0.86, u)
        cam(S, MC + V(mx + r * math.cos(a), r * math.sin(a), lerp(0.36, 0.56, u)), MC + V(mx, 0, 0.23), lens=38, fstop=3.2)
    L.append((19.8, 23.8, S5b))

    def S5c(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), 1.0)
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), 0.8)
        eddy(S, t, 1.0)
        u = ss(seg(t, 23.8, 24.85))
        ring = MC + V(mx + 0.27, 0, 0.21)
        cam(S, ring + V(0.22, -0.62, 0.3).lerp(V(0.08, -0.4, 0.14), u), ring, lens=40, fstop=2.8)
        if t > 23.85:
            label(S, "eddy", ring + V(0, 0, 0.11))
    L.append((23.8, 24.85, S5c))

    # --- line 6: their own field pushes back; speed becomes heat ------------------------------------------------
    def S6a(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), 1.0)
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), 0.8)
        eddy(S, t, 1.0 + 0.7 * ss(seg(t, 25.8, 26.4)), spin=1.0)
        put(S, K["arrow_move"], "scale", max(0.001, eout(seg(t, 25.0, 25.45))), 0)
        put(S, *nv(M["arrow_c"]), 2.5 * seg(t, 25.0, 25.2))
        put(S, *nv(M["arrow_c"], "A"), 0.95 * seg(t, 25.0, 25.2))
        put(S, K["arrow_back"], "scale", max(0.001, eout(seg(t, 27.9, 28.3))), 0)
        put(S, *nv(M["arrow_a"]), 3.0 * seg(t, 27.9, 28.05))
        put(S, *nv(M["arrow_a"], "A"), 0.95 * seg(t, 27.9, 28.05))
        u = ss(seg(t, 24.85, 28.75))
        cam(S, MC + V(mx - 0.5 + 0.15 * u, -1.25 + 0.1 * u, 0.9 - 0.1 * u), MC + V(mx + 0.06, -0.08, 0.36), lens=32, fstop=4,
            yaw=whip(t, t_end=28.75, amt=rad(-60)))
        if 25.35 < t < 27.85:
            label(S, "motion", MC + V(mx + 0.2, 0, 0.68))
        if 27.98 < t < 28.72:
            label(S, "drag", MC + V(mx + 0.16, -0.32, 0.3))
    L.append((24.85, 28.75, S6a))

    T6B = RUN.tau_s(BR0 + 62)

    def S6b(t, S):   # wide: the train slows along the brake run, a thermal trail behind it
        tau = T6B + (t - 28.75)
        s = RUN.at(tau)[0]
        x = train_x(s).x
        place_train(S, W, s)
        put(S, *nv(M["fin_world"], "MX"), x - 1.4)
        put(S, *nv(M["fin_world"], "H"), ss(seg(t, 28.85, 29.3)) * 1.3)
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 0.9)
        cam(S, V(x - 3, -24, 10.5), V(x - 12, 0, 2.2), lens=32, fstop=8, clip=0.5,
            yaw=whip(t, t_start=28.75, amt=rad(-60)))
    L.append((28.75, 29.95, S6b))

    def S6c(t, S):   # macro thermal: the fin glows where the magnet has just passed
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), lerp(1.0, 0.0, ss(seg(t, 29.95, 30.4))))
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), lerp(0.8, 0.0, ss(seg(t, 29.95, 30.4))))
        eddy(S, t, lerp(1.0, 0.25, seg(t, 29.95, 30.6)))
        put(S, *nv(M["fin_macro"], "H"), 1.4 * ss(seg(t, 30.1, 30.8)))
        u = ss(seg(t, 29.95, 31.3))
        cam(S, MC + V(mx - 0.55 + 0.1 * u, -0.95, 0.3), MC + V(mx - 0.32, 0, 0.21), lens=42, fstop=2.8)
    L.append((29.95, 31.3, S6c))

    # --- line 7: nothing touches, nothing wears out, no power ---------------------------------------------------
    def S7a(t, S):   # end-on: light through both air gaps
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "H"), lerp(1.4, 0.0, ss(seg(t, 31.3, 32.2))))
        put(S, K["light2"], "energy", 300.0)
        put(S, *nv(M["backpanel"]), 6.0)
        put(S, *nv(M["magstudio"]), 0.12)
        put(S, *nv(M["xmag"]), 0.12)
        u = ss(seg(t, 31.3, 32.65))
        cam(S, MC + V(mx + lerp(1.45, 1.05, u), 0.0, 0.3), MC + V(mx, 0, 0.3), lens=85, fstop=5.6)
    L.append((31.3, 32.65, S7a))

    T7B = RUN.tau_s(s_of_x(199))

    def S7b(t, S):   # low beside the fins as the cars glide over them
        tau = T7B + (t - 33.05)
        s = RUN.at(tau)[0]
        place_train(S, W, s)
        u = seg(t, 32.65, 33.85)
        cam(S, V(197.5 + 0.8 * u, -1.32, 2.2), V(214, 0.15, 2.45), lens=22, fstop=4, roll=rad(-2))
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 0.5)
    L.append((32.65, 33.85, S7b))

    T7C = RUN.tau_s(s_of_x(262))

    def S7c(t, S):   # straight down on the brake run: no cables, no power, it just glides to a stop
        tau = T7C + (t - 33.85)
        s = RUN.at(tau)[0]
        place_train(S, W, s)
        u = ss(seg(t, 33.85, 35.0))
        cam(S, V(276, 0.0, lerp(46, 38, u)), V(276, 0.001, 2), lens=40, roll=rad(90), fstop=11, clip=1.0)
    L.append((33.85, 35.0, S7c))

    # --- line 8: a launch falls short, rolls back, fins pop up and catch it ---------------------------------------
    T8A = ROLL.tau_apex()

    def S8a(t, S):
        tau = T8A + (t - 36.25)
        s = ROLL.at(tau)[0]
        place_train(S, W, s)
        z = train_x(s).z
        u = seg(t, 35.0, 36.7)
        cam(S, V(-45, -150, 66), V(-2, 0, lerp(z - 4, 104, 0.35)), lens=62, fstop=8, clip=1.0,
            yaw=whip(t, t_start=35.0, amt=rad(-45)))
    L.append((35.0, 36.7, S8a))

    def S8b(t, S):   # at the foot of the climb looking up: it comes back down, backwards
        tau = T8A + (t - 36.25)
        place_train(S, W, ROLL.at(tau)[0])
        u = seg(t, 36.7, 37.95)
        cam(S, V(-15.5, -9.5, 4.2), V(-1.5, 0, lerp(70, 40, ss(u))), lens=19, fstop=8, roll=rad(-8))
    L.append((36.7, 37.95, S8b))

    S8C_S = s_of_x(-110) + TRAIN_LEN
    T8C = ROLL.tau_s(S8C_S, falling=True)
    LFX = [ob.location.x for ob in R["lfins"]]

    def S8c(t, S):   # on the launch track: fins snap up in a wave, the train rolls back into them
        tau = T8C + (t - 39.4)
        s = ROLL.at(tau)[0]
        place_train(S, W, s)
        x_far, x_near = max(LFX), min(LFX)
        for ob, x in zip(R["lfins"], LFX):
            tp = 38.02 + 0.42 * (x_far - x) / (x_far - x_near)
            k = seg(t, tp, tp + 0.09)
            k = k + 0.12 * math.sin(math.pi * seg(t, tp + 0.09, tp + 0.2))
            put(S, ob, "rotation_euler", rad(-90) * (1 - k), 0)
        rear = train_x(s - TRAIN_LEN).x
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 1.4 * ss(seg(t, 38.75, 39.0)))
        u = seg(t, 37.95, 39.55)
        cam(S, V(-123.5 - 1.0 * u, -2.3, 2.5), V(-100, 0.2, 2.75), lens=30, fstop=4, roll=rad(2))
    L.append((37.95, 39.55, S8c))

    # --- line 9: follow ----------------------------------------------------------------------------------------
    def S9(t, S):
        u = ss(seg(t, 39.55, T_END))
        place_train(S, W, s_of_x(372) + TRAIN_LEN)
        cam(S, V(100, -205, 20).lerp(V(112, -250, 30), u), V(45, 0, 62).lerp(V(45, 0, 58), u), lens=28, fstop=11,
            clip=1.0)
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 0.6)
        put(S, *nv(M["fin_world"], "MX"), 340)
        put(S, *nv(M["fin_world"], "H"), 0.0)
        for ob in R["lfins"]:
            put(S, ob, "rotation_euler", 0.0, 0)
    L.append((39.55, T_END, S9))
    return L


def project(eye, q, lens, p, w=1080, h=1920):
    pc = q.inverted() @ (Vector(p) - eye)
    if pc.z >= -0.01:
        return None
    k = lens / 36.0     # sensor fit AUTO: the 36 mm sensor spans the longer (vertical) side
    u = 0.5 + (pc.x / -pc.z) * k * (h / w)
    v = 0.5 + (pc.y / -pc.z) * k
    return round(u * w, 1), round((1 - v) * h, 1)


def bake(W, labels_out):
    tracks, camk, labels = {}, [], {}
    W["qprev"] = {}
    L = shots(W)
    for i, (t0, t1, fn) in enumerate(L):
        f0 = math.ceil(t0 * FPS - 1e-6) + 1
        f1 = math.ceil(t1 * FPS - 1e-6)
        fr = list(range(f0, f1 + 1))
        if i > 0:
            fr = [f0 - 0.49] + fr
        if i < len(L) - 1:
            fr = fr + [f1 + 0.49]
        for f in fr:
            t = (f - 1) / FPS
            S = {}
            defaults(t, S, W)
            fn(t, S)
            c = S.pop("cam")
            camk.append((f,) + c)
            lb = S.pop("labels", {})
            if f == int(f):
                for name, p in lb.items():
                    xy = project(c[0], c[1], c[2], p)
                    if xy:
                        labels.setdefault(name, []).append([int(f), *xy])
            for k, (v, const) in S.items():
                tracks.setdefault(k, []).append((f, v, const))
    hud = []
    for f in range(1, int(4.8 * FPS)):
        t = (f - 1) / FPS
        s, v = RUN.at(t - TAU_LAUNCH)
        hud.append([f, round(v * 2.23694, 1), round(clamp(t - TAU_LAUNCH, 0, 99), 2)])
    labels["hud"] = hud
    with open(labels_out, "w") as fh:
        json.dump(labels, fh)
    camo = W["cam"]
    prev = None
    for f, eye, q, lens, fstop, focus, clip in camk:
        if prev is not None and q.dot(prev) < 0:
            q = -q
        prev = q
        for i in range(3):
            tracks.setdefault((camo, "location", i), []).append((f, eye[i], False))
        for i in range(4):
            tracks.setdefault((camo, "rotation_quaternion", i), []).append((f, q[i], False))
        cd = camo.data
        tracks.setdefault((cd, "lens", 0), []).append((f, lens, False))
        tracks.setdefault((cd, "dof.aperture_fstop", 0), []).append((f, fstop, False))
        tracks.setdefault((cd, "dof.focus_distance", 0), []).append((f, focus, False))
        tracks.setdefault((cd, "clip_start", 0), []).append((f, clip, False))
    n = 0
    for (idb, path, idx), keys in tracks.items():
        keys.sort(key=lambda k: k[0])
        ad = idb.animation_data or idb.animation_data_create()
        if ad.action is None:
            ad.action = bpy.data.actions.new(f"{idb.name}_A")
        fc = ad.action.fcurve_ensure_for_datablock(idb, path, index=idx)
        fc.keyframe_points.add(len(keys))
        fc.keyframe_points.foreach_set("co", [c for f, v, _ in keys for c in (f, v)])
        const = keys[0][2]
        try:
            fc.keyframe_points.foreach_set("interpolation", [0 if const else 1] * len(keys))
        except Exception:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT" if const else "LINEAR"
        fc.update()
        n += len(keys)
    print("BAKED", len(tracks), "tracks", n, "keys")


# ----------------------------------------------------------------------------------------------- main

def render_settings(scn, h=1920, samples=32):
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_y = h
    scn.render.resolution_x = round(h * 9 / 16 / 2) * 2
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    ee = scn.eevee
    ee.taa_render_samples = samples
    for k, v in (("use_raytracing", True), ("use_shadows", True), ("use_fast_gi", True), ("volumetric_start", 0.5),
                 ("volumetric_end", 1500.0), ("volumetric_tile_size", "8"), ("volumetric_samples", 48),
                 ("use_volumetric_shadows", True), ("motion_blur_steps", 1), ("use_bokeh_jittered", False),
                 ("shadow_ray_count", 2), ("shadow_step_count", 8)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print("skip", k, e)
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.5
    scn.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scn.view_settings.look = look
            break
        except TypeError:
            pass
    scn.view_settings.exposure = 0.25
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.compression = 15


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    M = materials()
    world = sky_world()
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "AUTO"
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.clip_end = 6000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 2.6
    sd.color = lin("#ffcfa8")
    sd.angle = rad(3)
    so = bpy.data.objects.new("Sun", sd)
    scn.collection.objects.link(so)
    so.rotation_mode = "QUATERNION"
    so.rotation_quaternion = SUN_DIR.to_track_quat("Z", "Y")
    fd = bpy.data.lights.new("Fill", "SUN")   # soft cool fill from the camera side
    fd.energy, fd.color, fd.angle = 0.6, lin("#a9bde0"), rad(25)
    try:
        fd.use_shadow = False
    except Exception:
        pass
    fo = bpy.data.objects.new("Fill", fd)
    scn.collection.objects.link(fo)
    fo.rotation_mode = "QUATERNION"
    fo.rotation_quaternion = Vector((0.45, 0.6, 0.65)).normalized().to_track_quat("Z", "Y")
    W = dict(M=M, cam=camo, sun=sd, world=world, fill=fd)
    W["R"] = build_ride(M)
    W["train"] = build_train(M)
    W["F"] = build_friction(M)
    W["K"] = build_macro(M)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(out)), "labels.json"))
    render_settings(scn)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)
    print("RUN: launch end s=%.1f, top v=%.1f m/s, brake entry v=%.1f, stop t=%.1f" % (
        RUN.at(3.5)[0], RUN.at(RUN.tau_s(S_TOP))[1], RUN.at(RUN.tau_s(BR0))[1], RUN.tau_s(BR1)))
    print("ROLL apex z=%.1f at tau=%.2f" % (track_frame(max(ROLL.s))[0].z, ROLL.tau_apex()))


def render(outdir, h, samples, which):
    scn = bpy.context.scene
    render_settings(scn, h, samples)
    if which and "-" in which:
        a, b = (int(x) for x in which.split("-"))
        frames = range(a, b + 1)
    elif which:
        frames = [int(x) for x in which.split(",")]
    else:
        frames = range(scn.frame_start, scn.frame_end + 1)
    os.makedirs(outdir, exist_ok=True)
    for f in frames:
        p = os.path.join(outdir, f"f_{f:04d}.png")
        if os.path.exists(p) and "--skip" in sys.argv:
            continue
        scn.frame_set(f)
        scn.render.filepath = p
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv and argv[0] == "build":
        build(argv[1])
    elif argv and argv[0] == "render":
        render(argv[1], int(argv[2]), int(argv[3]), argv[4] if len(argv) > 4 and not argv[4].startswith("--") else None)
