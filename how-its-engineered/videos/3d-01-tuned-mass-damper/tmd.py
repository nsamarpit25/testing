"""Taipei 101's tuned mass damper: a fully procedural 3D reel for @how.its.engineered (no characters).
Sets, far apart so each shot sees only its own: the city in a typhoon (origin, tower units: 1 u ~ 5 m), the damper
chamber (C, metres, floor 87 at z=0), an office near the top (O) and a ruler on a desk (R).
Every animated property is baked per frame from the shot list below; cuts get half-frame keys so motion blur never
smears across a cut.

blender -b --factory-startup -P tmd.py -- build <out.blend>
blender -b tmd.blend -P tmd.py -- render <outdir> <height> <samples> [a-b | f,f,f]
"""
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix, Quaternion

FPS = 30
T_END = 40.4
F_END = int(T_END * FPS) + 1
C = Vector((6000, 0, 0))
O = Vector((7000, 0, 0))
R = Vector((8000, 0, 0))
PEND = 14.4          # chamber pendulum length (m): pivot at z=21, ball centre at z=6.6
BALL_R = 2.75
BEND_SIGN = 1        # flips the tower bend direction if the modifier bends the other way
PAL = dict(deep="#0b1330", d="#16224a", m="#2a3d78", l="#4a64aa", xl="#8ea4dd", w="#dfe7ff",
           gold="#ffb21a", cyan="#3fe6ff", heat="#ff2a00", warm="#ffd9a0")
rad = math.radians


def floor_z(n):  # tower units, floor 27 starts the first flared segment at z=24
    return 24 + (n - 27) * 0.888


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


def facade(name, coord, glass, frame, lit_frac, lit_str, crown=False, xray=False):
    """Glass curtain wall: floor bands + mullions from rest/object coordinates, a few lit windows, optional gold
    crown glow (Value "G") and x-ray mode (Value "X": glass goes clear, frames glow cyan)."""
    m, nt, out = new_mat(name)
    if coord == "rest":
        P = node(nt, "ShaderNodeAttribute", attribute_name="rest").outputs["Vector"]
    else:
        P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    x, y, z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    band = mth(nt, "GREATER_THAN", mth(nt, "FRACT", mth(nt, "DIVIDE", z, 0.888)), 0.78)
    mx = mth(nt, "GREATER_THAN", mth(nt, "FRACT", mth(nt, "MULTIPLY", x, 1.15)), 0.85)
    my = mth(nt, "GREATER_THAN", mth(nt, "FRACT", mth(nt, "MULTIPLY", y, 1.15)), 0.85)
    fr = mth(nt, "MAXIMUM", band, mth(nt, "MAXIMUM", mx, my))
    gl = mth(nt, "SUBTRACT", 1.0, fr)
    vm = node(nt, "ShaderNodeVectorMath", operation="MULTIPLY")
    link(nt, P, vm.inputs[0])
    vm.inputs[1].default_value = (1.15, 1.15, 1 / 0.888)
    fl = node(nt, "ShaderNodeVectorMath", operation="FLOOR")
    link(nt, vm.outputs[0], fl.inputs[0])
    wn = node(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    link(nt, fl.outputs[0], wn.inputs["Vector"])
    lit = mth(nt, "MULTIPLY", mth(nt, "GREATER_THAN", wn.outputs["Value"], 1 - lit_frac), gl)
    b = node(nt, "ShaderNodeBsdfPrincipled")
    link(nt, ramp(nt, fr, glass, frame), b.inputs["Base Color"])
    link(nt, mth(nt, "MULTIPLY_ADD", fr, 0.4, 0.18), b.inputs["Roughness"])
    link(nt, mth(nt, "MULTIPLY", gl, 0.75), b.inputs["Metallic"])
    es = mth(nt, "MULTIPLY", lit, lit_str)
    if crown:
        cm = mth(nt, "MULTIPLY", mth(nt, "MULTIPLY", mth(nt, "GREATER_THAN", z, floor_z(86.5)),
                                         mth(nt, "LESS_THAN", z, floor_z(92.6))), gl)
        link(nt, ramp(nt, cm, PAL["warm"], PAL["gold"]), b.inputs["Emission Color"])
        es = mth(nt, "MULTIPLY_ADD", cm, val(nt, "G", 2.0), es)
    else:
        b.inputs["Emission Color"].default_value = (*lin(PAL["warm"]), 1)
    link(nt, es, b.inputs["Emission Strength"])
    shader = b.outputs[0]
    if xray:
        tr, em, add = node(nt, "ShaderNodeBsdfTransparent"), node(nt, "ShaderNodeEmission"), node(nt, "ShaderNodeMixShader")
        em.inputs[0].default_value = (*lin(PAL["cyan"]), 1)
        em.inputs[1].default_value = 1.8
        link(nt, mth(nt, "MULTIPLY", fr, 0.9), add.inputs[0])
        link(nt, tr.outputs[0], add.inputs[1])
        link(nt, em.outputs[0], add.inputs[2])
        mx_ = node(nt, "ShaderNodeMixShader")
        link(nt, val(nt, "X", 0.0), mx_.inputs[0])
        link(nt, shader, mx_.inputs[1])
        link(nt, add.outputs[0], mx_.inputs[2])
        shader = mx_.outputs[0]
    link(nt, shader, out.inputs[0])
    m.diffuse_color = (*lin(glass), 1)
    return m


def rain_mat(name, coord="object", period=5.0, dash=0.25, strength=1.6, alpha=0.55):
    """Falling dashes along tall thin quads; the fall is a shader offset (Value "T") so it never wraps."""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    seed = node(nt, "ShaderNodeAttribute", attribute_name="seed").outputs["Fac"]
    ph = mth(nt, "FRACT", mth(nt, "ADD", mth(nt, "DIVIDE", mth(nt, "ADD", sep.outputs[2], val(nt, "T", 0.0)), period), seed))
    a = mth(nt, "MULTIPLY", mth(nt, "LESS_THAN", ph, dash), mth(nt, "SUBTRACT", 1.0, mth(nt, "DIVIDE", ph, dash)))
    a = mth(nt, "MULTIPLY", a, val(nt, "A", alpha))
    tr, em, mx = node(nt, "ShaderNodeBsdfTransparent"), node(nt, "ShaderNodeEmission"), node(nt, "ShaderNodeMixShader")
    em.inputs[0].default_value = (*lin("#c9d7ff"), 1)
    em.inputs[1].default_value = strength
    link(nt, a, mx.inputs[0])
    link(nt, tr.outputs[0], mx.inputs[1])
    link(nt, em.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], out.inputs[0])
    return m


def window_glow_mat(name, base, period_z, lo, hi, n_side):
    """Octagon chamber wall: steel with tall window panes that glow storm-blue (Value "F" = lightning flash)."""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    x, y, z = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    fz = mth(nt, "FRACT", mth(nt, "DIVIDE", z, period_z))
    vz = mth(nt, "MULTIPLY", mth(nt, "GREATER_THAN", fz, lo), mth(nt, "LESS_THAN", fz, hi))
    ang = mth(nt, "ARCTAN2", y, x)
    fa = mth(nt, "FRACT", mth(nt, "MULTIPLY", ang, n_side / (2 * math.pi)))
    va = mth(nt, "MULTIPLY", mth(nt, "GREATER_THAN", fa, 0.12), mth(nt, "LESS_THAN", fa, 0.88))
    win = mth(nt, "MULTIPLY", vz, va)
    b = node(nt, "ShaderNodeBsdfPrincipled")
    link(nt, ramp(nt, win, base, "#0d1838"), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    link(nt, ramp(nt, val(nt, "F", 0.0), "#2b45a0", "#e8f0ff"), b.inputs["Emission Color"])
    link(nt, mth(nt, "MULTIPLY", win, mth(nt, "MULTIPLY_ADD", val(nt, "F2", 0.0), 10.0, 1.2)), b.inputs["Emission Strength"])
    link(nt, b.outputs[0], out.inputs[0])
    nt.nodes["F2"].outputs[0].default_value = 0.0
    m.diffuse_color = (*lin(base), 1)
    return m


# ----------------------------------------------------------------------------------------------- geometry

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


def oct_pts(hw, ch, rot=0.0):
    pts = [(hw, -hw + ch), (hw, hw - ch), (hw - ch, hw), (-hw + ch, hw), (-hw, hw - ch), (-hw, -hw + ch),
           (-hw + ch, -hw), (hw - ch, -hw)]
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        pts = [(x * c - y * s, x * s + y * c) for x, y in pts]
    return pts


def reg_oct(r, rot=math.pi / 8):
    return [(r * math.cos(rot + k * math.pi / 4), r * math.sin(rot + k * math.pi / 4)) for k in range(8)]


def loft(bm, rings, cap=True):
    """rings: list of point lists (same count) -> side quads (+ caps)."""
    vs = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap:
        bm.faces.new(list(reversed(vs[0])))
        bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def oct_slab(bm, ri, ro, z0, z1):
    """Annular regular-octagon slab (a balcony ring)."""
    pi, po = reg_oct(ri), reg_oct(ro)
    v = {}
    for nm, pts, z in (("ib", pi, z0), ("ob", po, z0), ("it", pi, z1), ("ot", po, z1)):
        v[nm] = [bm.verts.new((x, y, z)) for x, y in pts]
    for i in range(8):
        j = (i + 1) % 8
        bm.faces.new((v["it"][i], v["ot"][i], v["ot"][j], v["it"][j]))
        bm.faces.new((v["ib"][j], v["ob"][j], v["ob"][i], v["ib"][i]))
        bm.faces.new((v["ob"][i], v["ot"][i], v["ot"][j], v["ob"][j]))
        bm.faces.new((v["ib"][j], v["it"][j], v["it"][i], v["ib"][i]))


# ----------------------------------------------------------------------------------------------- the city

def tower_profile():
    P = [(24 * i / 40, lerp(5.6, 4.9, i / 40)) for i in range(41)]
    for k in range(8):
        z0 = 24 + 7 * k
        P += [(z0 + 7 * i / 14, lerp(4.3, 5.3, (i / 14) ** 1.3)) for i in range(15)]
    P += [(80 + 5 * i / 8, lerp(4.5, 3.4, i / 8)) for i in range(9)]
    P += [(85, 2.6), (87.5, 2.6), (87.5, 1.7), (89.5, 1.7), (89.5, 0.7), (90.2, 0.5)]
    P += [(90.2 + 10.8 * i / 11, lerp(0.42, 0.07, i / 11)) for i in range(12)]
    return P


def hw_at(z):
    P = tower_profile()
    for (z0, w0), (z1, w1) in zip(P, P[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return lerp(w0, w1, (z - z0) / (z1 - z0))
    return 1.0


def tower_mesh(name, mat, parent):
    bm = bmesh.new()
    loft(bm, [[(x, y, z) for x, y in oct_pts(hw, hw * 0.24)] for z, hw in tower_profile()])
    return obj_from_bm(name, bm, mat, parent, rest=True)


def build_city(M):
    root = empty("TowerRoot")
    shell = tower_mesh("Tower", M["facade"], root)
    ghost = obj_from_bm("Ghost", bmesh.new(), None, root)
    ghost.data = shell.data.copy()
    ghost.data.materials.clear()
    ghost.data.materials.append(M["ghost"])
    bo = empty("BendOrigin", parent=root)
    bo.rotation_euler = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_euler()
    for ob in (shell, ghost):
        md = ob.modifiers.new("Bend", "SIMPLE_DEFORM")
        md.deform_method = "BEND"
        md.origin = bo
        md.deform_axis = "Z"
        md.angle = 0.0
    # inside the crown, only seen in x-ray: floor slabs, the chamber block, the ball on its cables, a pull arrow
    bm = bmesh.new()
    for n in range(60, 96):
        z = floor_z(n)
        if z > 84:
            break
        hw = hw_at(z) - 0.25
        loft(bm, [[(x, y, z) for x, y in oct_pts(hw, hw * 0.24)], [(x, y, z + 0.07) for x, y in oct_pts(hw, hw * 0.24)]])
    floors = obj_from_bm("DiagFloors", bm, M["diagline"], root)
    bm = bmesh.new()
    bm_box(bm, (0, 0, (floor_z(87) + floor_z(92)) / 2), (8.4, 8.4, floor_z(92) - floor_z(87)))
    chamber = obj_from_bm("DiagChamber", bm, M["diagzone"], root)
    piv = empty("DiagPivot", (0, 0, floor_z(92) - 0.1), root)
    ball = sphere("DiagBall", 1.05, (0, 0, -(floor_z(92) - 0.1 - 78.65)), M["diagball"], piv)
    bm = bmesh.new()
    zc = -(floor_z(92) - 0.1 - 78.65)
    for k in range(4):
        a = rad(45 + 90 * k)
        bm_rod(bm, (0.95 * math.cos(a), 0.95 * math.sin(a), 0), (0.75 * math.cos(a), 0.75 * math.sin(a), zc + 0.4), 0.04, 8)
    cables = obj_from_bm("DiagCables", bm, M["cable"], piv)
    bm = bmesh.new()
    bm_cyl(bm, 0.22, 0.22, 3.2, 16, Matrix.Translation((-1.6, 0, 0)) @ Matrix.Rotation(rad(90), 4, "Y"))
    bm_cyl(bm, 0.6, 0.0, 1.2, 24, Matrix.Translation((-3.8, 0, 0)) @ Matrix.Rotation(rad(-90), 4, "Y"))
    arrow = obj_from_bm("PullArrow", bm, M["goldglow"], empty("ArrowPivot", (-5.6, -2.0, 79.0), root))
    labels = []
    for n in range(87, 93):
        lb = text(f"Lbl{n}", str(n), 0.85, (7.2, -1.4, floor_z(n) + 0.45), (rad(90), 0, 0), M[f"lbl{n}"], extrude=0.02)
        labels.append(lb)
    # the city around it
    rnd = random.Random(3)
    bm = bmesh.new()
    for gx in range(-14, 15):
        for gy in range(-14, 15):
            cx, cy = gx * 40, gy * 40
            d = math.hypot(cx, cy)
            if d < 30 or d > 560:
                continue
            for _ in range(rnd.randint(1, 3)):
                w, dd = rnd.uniform(7, 15), rnd.uniform(7, 15)
                h = rnd.uniform(5, 20) * (1.5 if d < 160 else 1.0) * (1.3 if rnd.random() < 0.12 else 1.0)
                bm_box(bm, (cx + rnd.uniform(-16 + w / 2, 16 - w / 2), cy + rnd.uniform(-16 + dd / 2, 16 - dd / 2), h / 2), (w, dd, h))
    obj_from_bm("City", bm, M["city"])
    box("Ground", (0, 0, -0.5), (4000, 4000, 1), M["ground"])
    bm = bmesh.new()
    for k in range(18):
        a = k * 2 * math.pi / 18 + rnd.uniform(-0.1, 0.1)
        r = rnd.uniform(850, 1100)
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0,
                                  matrix=Matrix.Translation((r * math.cos(a), r * math.sin(a), -20)) @
                                  Matrix.Diagonal((rnd.uniform(160, 260), rnd.uniform(160, 260), rnd.uniform(70, 150), 1)))
    obj_from_bm("Hills", bm, M["hills"], smooth=True)
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0), (2600, 2600, 34))
    obj_from_bm("Clouds", bm, M["cloud"], loc=(0, 0, 150))
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0), (3000, 3000, 132))
    obj_from_bm("Fog", bm, M["fog"], loc=(0, 0, 66))
    # wind: glowing streams that sweep past the tower toward +X
    winds = []
    for i in range(14):
        z = rnd.uniform(18, 98)
        y = rnd.choice([-1, 1]) * rnd.uniform(8, 34)
        pts = []
        for k in range(11):
            x = -170 + 340 * k / 10
            pts.append((x, y + math.copysign(9, y) * math.exp(-(x / 26) ** 2), z + 2.5 * math.sin(k * 1.4 + i)))
        cu = bpy.data.curves.new(f"Wind{i}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = rnd.uniform(0.12, 0.32)
        cu.bevel_resolution = 2
        cu.resolution_u = 18
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        for p, c in zip(sp.points, pts):
            p.co = (*c, 1)
        sp.use_endpoint_u = True
        sp.order_u = 4
        cu.materials.append(M["wind"])
        ob = bpy.data.objects.new(f"Wind{i}", cu)
        bpy.context.scene.collection.objects.link(ob)
        winds.append((cu, rnd.random(), rnd.uniform(0.9, 1.5)))
    # lightning
    bolts = []
    for bi, (top, bot) in enumerate((((-140, 260, 165), (-120, 250, 0)), ((14, 10, 168), (0, 0, 101)))):
        pts, p0, p1 = [], Vector(top), Vector(bot)
        for k in range(14):
            u = k / 13
            q = p0.lerp(p1, u)
            if 0 < k < 13:
                q += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * (6 if bi == 0 else 3.5)
            pts.append(q)
        cu = bpy.data.curves.new(f"Bolt{bi}", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.5 if bi == 0 else 0.3
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, c in zip(sp.points, pts):
            p.co = (*c, 1)
        cu.materials.append(M["bolt"])
        ob = bpy.data.objects.new(f"Bolt{bi}", cu)
        bpy.context.scene.collection.objects.link(ob)
        bolts.append(ob)
    return dict(root=root, shell=shell, ghost=ghost, floors=floors, chamber=chamber, piv=piv, ball=ball,
                cables=cables, arrow=arrow, labels=labels, winds=winds, bolts=bolts)


def build_rain(M, cam):
    rnd = random.Random(5)
    bm = bmesh.new()
    seed = []
    for i in range(5200):
        p = Vector((rnd.uniform(-30, 30), rnd.uniform(-30, 30), rnd.uniform(-26, 26)))
        a = rnd.uniform(0, math.pi)
        for aa in (a, a + math.pi / 2):
            dx, dy = math.cos(aa) * 0.035, math.sin(aa) * 0.035
            vs = [bm.verts.new(p + Vector(o)) for o in ((-dx, -dy, 0), (dx, dy, 0), (dx, dy, 5), (-dx, -dy, 5))]
            bm.faces.new(vs)
        seed += [rnd.random()] * 8
    ob = obj_from_bm("Rain", bm, M["rain"], attrs={"seed": seed})
    ob.rotation_euler = (0, rad(16), 0)
    c = ob.constraints.new("COPY_LOCATION")
    c.target = cam
    return ob


# ----------------------------------------------------------------------------------------------- the chamber

def build_chamber(M):
    root = empty("ChamberRoot", C)
    box("ChFloor", (0, 0, -0.4), (27, 27, 0.8), M["chfloor"], root)
    bm = bmesh.new()
    loft(bm, [[(x, y, z) for x, y in reg_oct(12.9)] for z in (-0.5, 22.6)], cap=False)
    obj_from_bm("ChWalls", bm, M["chwall"], root)
    bm = bmesh.new()
    for k in range(1, 5):
        oct_slab(bm, 7.4, 12.9, 4.2 * k - 0.45, 4.2 * k)
    obj_from_bm("Balconies", bm, M["concrete"], root)
    bm = bmesh.new()
    for k in range(1, 5):
        z = 4.2 * k
        pts = reg_oct(7.55)
        for i in range(8):
            a, b = pts[i], pts[(i + 1) % 8]
            for h in (1.05, 0.55):
                bm_rod(bm, (*a, z + h), (*b, z + h), 0.04, 8)
            for u in (0.0, 0.25, 0.5, 0.75):
                q = (lerp(a[0], b[0], u), lerp(a[1], b[1], u))
                bm_rod(bm, (*q, z), (*q, z + 1.05), 0.035, 6)
    obj_from_bm("Railings", bm, M["rail"], root)
    box("ChCeiling", (0, 0, 21.8), (27, 27, 1.6), M["concrete"], root)
    bm = bmesh.new()
    for i in range(-4, 5):
        bm_box(bm, (i * 3.0, 0, 20.65), (0.5, 26, 0.7))
        bm_box(bm, (0, i * 3.0, 20.3), (26, 0.5, 0.6))
    bm_box(bm, (0, 0, 19.9), (8.5, 1.2, 0.9))
    bm_box(bm, (0, 0, 19.9), (1.2, 8.5, 0.9))
    obj_from_bm("Beams", bm, M["steel"], root)
    # floor labels on the far balconies
    for k, n in enumerate(range(87, 93)):
        z = 4.2 * k
        if n == 87:
            text("ChL87", "87F", 0.9, (0, 12.75, 1.6), (rad(90), 0, 0), M["chlabel"], root)
        elif n == 92:
            text("ChL92", "92F", 0.9, (0, 7.6, 19.3), (rad(90), 0, 0), M["chlabel"], root)
        else:
            text(f"ChL{n}", f"{n}F", 0.6, (0, 7.42, z - 0.24), (rad(90), 0, 0), M["chlabel"], root)
            text(f"ChLx{n}", f"{n}F", 0.6, (7.42, 0, z - 0.24), (rad(90), 0, rad(-90)), M["chlabel"], root)
    # the pendulum: pivot at the ceiling, everything that swings hangs from it
    piv = empty("Pivot", (0, 0, 21), root)
    zc = -PEND
    bm = bmesh.new()
    n_pl = 41
    th = 2 * BALL_R / n_pl
    for i in range(n_pl):
        zm = -BALL_R + th * (i + 0.5)
        r = math.sqrt(max(BALL_R ** 2 - zm ** 2, 0.04))
        bm_cyl(bm, r, r, th * 0.86, 64, Matrix.Translation((0, 0, zc + zm)))
    ball = obj_from_bm("Ball", bm, M["gold"], piv, smooth=False)
    bm = bmesh.new()
    bm_cyl(bm, 3.12, 3.12, 0.55, 64, Matrix.Translation((0, 0, zc + 0.2)))
    for k in range(8):
        a = rad(22.5 + 45 * k)
        bm_rod(bm, (2.6 * math.cos(a), 2.6 * math.sin(a), zc + 0.2), (3.1 * math.cos(a), 3.1 * math.sin(a), zc + 0.2), 0.18, 10)
    bm_cyl(bm, 1.9, 1.9, 0.35, 8, Matrix.Translation((0, 0, zc - BALL_R - 0.05)))
    obj_from_bm("Cradle", bm, M["darksteel"], piv)
    bm = bmesh.new()
    for k in range(4):
        a0 = rad(45 + 90 * k)
        for off in (-0.13, 0.13):
            a = a0 + off
            bm_rod(bm, (3.5 * math.cos(a), 3.5 * math.sin(a), -0.8), (3.12 * math.cos(a), 3.12 * math.sin(a), zc + 0.45), 0.1, 10)
    obj_from_bm("Cables", bm, M["cable"], piv)
    laser = cyl("Laser", 0.035, 3.75, (0, 0, zc - BALL_R - 0.25 - 1.87), M["laser"], piv, n=10)
    brackets, anchors, barrels = [], [], []
    bm = bmesh.new()
    for k in range(8):
        a = rad(45 * k)
        brackets.append(empty(f"Brk{k}", (1.7 * math.cos(a), 1.7 * math.sin(a), zc - BALL_R - 0.05), piv))
        anchors.append(empty(f"Anc{k}", (7.2 * math.cos(a), 7.2 * math.sin(a), 1.25), root))
        bm_box(bm, (7.4 * math.cos(a), 7.4 * math.sin(a), 0.55), (1.3, 1.3, 1.1))
    obj_from_bm("Pedestals", bm, M["darksteel"], root)
    for k in range(8):
        bm = bmesh.new()
        bm_cyl(bm, 0.36, 0.36, 3.3, 24, Matrix.Translation((0, 0, 1.65)))
        bm_cyl(bm, 0.44, 0.44, 0.3, 24, Matrix.Translation((0, 0, 0.15)))
        bm_cyl(bm, 0.4, 0.4, 0.2, 24, Matrix.Translation((0, 0, 3.2)))
        b = obj_from_bm(f"Barrel{k}", bm, M["piston"], root, anchors[k].location, smooth=True)
        c = b.constraints.new("DAMPED_TRACK")
        c.target = brackets[k]
        c.track_axis = "TRACK_Z"
        barrels.append(b)
        bm = bmesh.new()
        bm_cyl(bm, 0.15, 0.15, 3.7, 16, Matrix.Translation((0, 0, 1.85)))
        bm_cyl(bm, 0.3, 0.3, 0.3, 16, Matrix.Translation((0, 0, 0.1)))
        rd = obj_from_bm(f"Rod{k}", bm, M["chrome"], brackets[k], smooth=True)
        c = rd.constraints.new("DAMPED_TRACK")
        c.target = anchors[k]
        c.track_axis = "TRACK_Z"
    # one-metre marker on the floor
    bm = bmesh.new()
    bm_box(bm, (0.5, 0, 0.02), (1.0, 0.07, 0.04))
    bm_box(bm, (0, 0, 0.03), (0.06, 0.6, 0.06))
    mk = obj_from_bm("Marker", bm, M["marker"], root)
    bm = bmesh.new()
    bm_box(bm, (1.0, 0, 0.03), (0.08, 0.7, 0.06))
    tick = obj_from_bm("MarkerTick", bm, M["tick"], root)
    mtxt = text("MarkerTxt", "1 m", 0.42, (0.5, -0.55, 0.03), (0, 0, 0), M["marker"], root)
    # light
    spots = []
    for g in range(3):
        ld = bpy.data.lights.new(f"Spot{g}", "SPOT")
        ld.energy = 0
        ld.spot_size = rad(34)
        ld.spot_blend = 0.4
        ld.color = lin("#ffe2b0")
        ld.shadow_soft_size = 0.3
        spots.append(ld)
        for j in range(2):
            a = rad(-90 + (g - 1) * 50 + j * 180)
            lo = bpy.data.objects.new(f"SpotO{g}{j}", ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.parent = root
            lo.location = (10.5 * math.cos(a), 10.5 * math.sin(a), 4.2 * (1 + (g % 2)) + 1.2)
            c = lo.constraints.new("DAMPED_TRACK")
            c.target = ball
            c.track_axis = "TRACK_NEGATIVE_Z"
    amb = bpy.data.lights.new("ChAmb", "AREA")
    amb.shape = "DISK"
    amb.size = 18
    amb.energy = 900
    amb.color = lin("#9db4ff")
    lo = bpy.data.objects.new("ChAmbO", amb)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = root
    lo.location = (0, 0, 19.4)
    rim = bpy.data.lights.new("ChRim", "AREA")
    rim.size = 6
    rim.energy = 0
    rim.color = lin("#c8d8ff")
    lo = bpy.data.objects.new("ChRimO", rim)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = root
    lo.location = (-9.5, 6.5, 9)
    c = lo.constraints.new("DAMPED_TRACK")
    c.target = ball
    c.track_axis = "TRACK_NEGATIVE_Z"
    return dict(root=root, piv=piv, ball=ball, laser=laser, barrels=barrels, marker=(mk, tick, mtxt),
                spots=spots, amb=amb, rim=rim)


def ball_world(phi):
    return C + Vector((0, 0, 21)) + Matrix.Rotation(phi, 3, "Y") @ Vector((0, 0, -PEND))


def phi_for(m):  # pivot angle that puts the ball m metres along +X
    return -math.asin(m / PEND)


# ----------------------------------------------------------------------------------------------- the office

def build_office(M):
    root = empty("OfficeRoot", O)
    box("OfFloor", (0, 0, -0.1), (10.4, 8.4, 0.2), M["offloor"], root)
    box("OfCeil", (0, 0, 3.3), (10.4, 8.4, 0.2), M["ofceil"], root)
    box("OfBack", (0, -4.1, 1.6), (10.4, 0.2, 3.4), M["ofwall"], root)
    box("OfLeft", (-5.1, 0, 1.6), (0.2, 8.4, 3.4), M["ofwall"], root)
    box("OfRight", (5.1, 0, 1.6), (0.2, 8.4, 3.4), M["ofwall"], root)
    bm = bmesh.new()
    for x in (-5, -3.3, -1.65, 0, 1.65, 3.3, 5):
        bm_box(bm, (x, 4.05, 1.6), (0.09, 0.14, 3.4))
    bm_box(bm, (0, 4.05, 0.08), (10.2, 0.16, 0.16))
    bm_box(bm, (0, 4.05, 3.15), (10.2, 0.16, 0.2))
    obj_from_bm("OfMullions", bm, M["steel"], root)
    box("OfGlass", (0, 4.1, 1.6), (10.2, 0.02, 3.2), M["glass"], root)
    bm = bmesh.new()
    rnd = random.Random(11)
    seed = []
    for i in range(1400):
        p = Vector((rnd.uniform(-7, 7), rnd.uniform(4.4, 9), rnd.uniform(-2.5, 3.5)))
        vs = [bm.verts.new(p + Vector(o)) for o in ((-0.008, 0, 0), (0.008, 0, 0), (0.008, 0, 2.2), (-0.008, 0, 2.2))]
        bm.faces.new(vs)
        seed += [rnd.random()] * 4
    rc = obj_from_bm("OfRain", bm, M["rain2"], root, attrs={"seed": seed})
    rc.rotation_euler = (0, rad(12), 0)
    bm = bmesh.new()
    bm_box(bm, (0, 0, 0), (300, 1, 170))
    obj_from_bm("OfBackdrop", bm, M["backdrop"], root, (0, 80, -40))
    # furniture
    box("Desk", (0, 1.55, 0.74), (2.3, 0.95, 0.05), M["desk"], root)
    for x in (-1.08, 1.08):
        box(f"DeskLeg{x}", (x, 1.55, 0.36), (0.06, 0.85, 0.72), M["steel"], root)
    box("Monitor", (-0.35, 1.85, 1.1), (0.95, 0.04, 0.56), M["darksteel"], root)
    box("Screen", (-0.35, 1.825, 1.1), (0.88, 0.01, 0.49), M["screen"], root)
    box("MonStand", (-0.35, 1.88, 0.86), (0.06, 0.06, 0.22), M["steel"], root)
    box("Keyboard", (-0.3, 1.4, 0.775), (0.5, 0.16, 0.02), M["light"], root)
    cyl("Mug", 0.045, 0.1, (-0.85, 1.35, 0.815), M["light"], root)
    glass = cyl("Glass", 0.05, 0.15, (0.45, 1.33, 0.84), M["glasscup"], root)
    wpiv = empty("WaterPivot", (0.45, 1.33, 0.86), root)
    wpiv.location.z = 0.855
    cyl("Water", 0.046, 0.09, (0.45, 1.33, 0.81), M["water"], root)
    cyl("WaterTop", 0.0465, 0.006, (0, 0, 0), M["water"], wpiv)
    pen = cyl("Pen", 0.006, 0.15, (0.15, 1.2, 0.772), M["gold"], root, n=8)
    pen.rotation_euler = (rad(90), 0, rad(10))
    lamp = empty("LampPivot", (0.3, 1.25, 3.2), root)
    bm = bmesh.new()
    bm_rod(bm, (0, 0, 0), (0, 0, -0.95), 0.008, 6)
    bm_cyl(bm, 0.05, 0.3, 0.32, 32, Matrix.Translation((0, 0, -1.1)))
    obj_from_bm("Lamp", bm, M["lampshade"], lamp)
    sphere("Bulb", 0.06, (0, 0, -1.2), M["bulb"], lamp)
    ld = bpy.data.lights.new("LampL", "POINT")
    ld.energy = 30
    ld.color = lin("#ffd9a0")
    ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new("LampLO", ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = lamp
    lo.location = (0, 0, -1.25)
    chair = empty("Chair", (0.1, 0.55, 0), root)
    box("Seat", (0, 0, 0.48), (0.55, 0.5, 0.08), M["chair"], chair)
    box("Back", (0, -0.24, 0.85), (0.5, 0.06, 0.6), M["chair"], chair)
    cyl("Pole", 0.03, 0.4, (0, 0, 0.26), M["steel"], chair)
    bm = bmesh.new()
    for k in range(5):
        a = rad(72 * k)
        bm_rod(bm, (0, 0, 0.06), (0.32 * math.cos(a), 0.32 * math.sin(a), 0.04), 0.025, 8)
    obj_from_bm("ChairBase", bm, M["steel"], chair)
    plant = empty("Plant", (-1.8, 2.6, 0), root)
    cyl("Pot", 0.2, 0.4, (0, 0, 0.2), M["light"], plant, r2=0.24)
    leaves = empty("Leaves", (0, 0, 0.4), plant)
    for k in range(7):
        a = rad(51 * k)
        lf = sphere(f"Leaf{k}", 0.1, (0.13 * math.cos(a), 0.13 * math.sin(a), 0.35 + 0.05 * k), M["leaf"], leaves, (1, 0.35, 3.0))
        lf.rotation_euler = (rad(25) * math.cos(a), rad(25) * math.sin(a), a)
    frm = empty("Frame", (-5.0, 0.6, 2.35), root)
    box("FrameBox", (0.03, 0, -0.35), (0.04, 0.9, 0.65), M["darksteel"], frm)
    box("FramePic", (0.055, 0, -0.35), (0.01, 0.78, 0.53), M["pic"], frm)
    for i in range(4):
        box(f"Shelf{i}", (-4.75, -1.9, 0.4 + 0.55 * i), (0.4, 1.6, 0.04), M["desk"], root)
        rb = random.Random(i)
        y = -2.6
        while y < -1.25:
            w = rb.uniform(0.04, 0.09)
            h = rb.uniform(0.28, 0.42)
            box(f"Book{i}_{y:.2f}", (-4.75, y + w / 2, 0.42 + 0.55 * i + h / 2), (0.3, w, h),
                M[rb.choice(["light", "chair", "desk"])], root)
            y += w + 0.01
    pnl = bpy.data.lights.new("OfPanel", "AREA")
    pnl.shape = "RECTANGLE"
    pnl.size, pnl.size_y = 3.0, 1.2
    pnl.energy = 260
    pnl.color = lin("#dfe6ff")
    lo = bpy.data.objects.new("OfPanelO", pnl)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = root
    lo.location = (0.2, 0.2, 3.15)
    box("PanelGlow", (0.2, 0.2, 3.19), (3.0, 1.2, 0.02), M["panel"], root)
    return dict(root=root, lamp=lamp, wpiv=wpiv, chair=chair, leaves=leaves, frame=frm, pen=pen, glass=glass)


# ----------------------------------------------------------------------------------------------- the ruler

def build_ruler(M):
    root = empty("RulerRoot", R)
    box("RDesk", (-3.5, 0, -0.25), (7, 7, 0.5), M["desk"], root)
    box("RWall", (0, 4, 2), (20, 0.2, 12), M["ofwall"], root)
    box("RFloor", (0, 0, -8), (30, 30, 0.2), M["offloor"], root)
    box("RulerIn", (-0.85, 0, 0.012), (1.7, 0.34, 0.024), M["ruler"], root)
    bm = bmesh.new()
    n = 60
    for i in range(n):
        bm_box(bm, (2.0 * (i + 0.5) / n, 0, 0), (2.0 / n * 1.001, 0.34, 0.024))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0005)
    ov = obj_from_bm("RulerOut", bm, M["ruler"], root, (0, 0, 0.012), rest=True)
    md = ov.modifiers.new("Bend", "SIMPLE_DEFORM")
    md.deform_method = "BEND"
    md.deform_axis = "Y"
    md.angle = 0
    box("Book", (-0.95, 0.05, 0.19), (1.45, 1.1, 0.33), M["book"], root)
    box("BookPages", (-0.95, 0.05, 0.19), (1.38, 1.04, 0.29), M["light"], root)
    cyl("Pencil", 0.035, 1.6, (-2.4, -1.2, 0.035), M["gold"], root, n=6).rotation_euler = (rad(90), 0, rad(70))
    ld = bpy.data.lights.new("RKey", "AREA")
    ld.size = 4
    ld.energy = 600
    ld.color = lin("#e3e9ff")
    lo = bpy.data.objects.new("RKeyO", ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.parent = root
    lo.location = (1.5, -3, 4)
    c = lo.constraints.new("DAMPED_TRACK")
    c.target = ov
    c.track_axis = "TRACK_NEGATIVE_Z"
    return dict(root=root, out=ov)


# ----------------------------------------------------------------------------------------------- world + materials

def build_world():
    w = bpy.data.worlds.new("Storm")
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
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    link(nt, tc.outputs["Generated"], sep.inputs[0])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*lin("#3a4e92"), 1)
    r.color_ramp.elements[1].position = 0.55
    r.color_ramp.elements[1].color = (*lin("#0c1434"), 1)
    link(nt, sep.outputs[2], r.inputs[0])
    link(nt, r.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.9
    link(nt, bg.outputs[0], out.inputs[0])


def volume_mats():
    m, nt, out = new_mat("Cloud")
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    nz = node(nt, "ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.0045
    nz.inputs["Detail"].default_value = 6
    nz.inputs["Roughness"].default_value = 0.6
    link(nt, P, nz.inputs["Vector"])
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    shape = mth(nt, "SUBTRACT", 1.0, mth(nt, "POWER", mth(nt, "ABSOLUTE", mth(nt, "DIVIDE", sep.outputs[2], 17.0)), 2.0), clamp_=True)
    dens = mth(nt, "MULTIPLY", mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", nz.outputs["Fac"], 0.4), 3.0, clamp_=True), shape)
    pv = node(nt, "ShaderNodeVolumeScatter")
    pv.inputs["Color"].default_value = (*lin("#6c7bb0"), 1)
    link(nt, mth(nt, "MULTIPLY", dens, 0.09), pv.inputs["Density"])
    link(nt, pv.outputs[0], out.inputs["Volume"])
    cloud = m
    m, nt, out = new_mat("Fog")
    sc = node(nt, "ShaderNodeVolumeScatter")
    sc.inputs["Color"].default_value = (*lin("#8fa3e0"), 1)
    sc.inputs["Density"].default_value = 0.0022
    link(nt, sc.outputs[0], out.inputs["Volume"])
    return cloud, m


def materials():
    M = {}
    M["facade"] = facade("Facade", "rest", "#1b2a5c", "#6f88cc", 0.10, 1.2, crown=True, xray=True)
    M["city"] = facade("CityFacade", "object", "#121c40", "#33498a", 0.09, 1.4)
    M["ground"] = pbr("Ground", "#141d3d", 0.18, 0.0)
    M["hills"] = pbr("Hills", "#1a2550", 0.9)
    M["cloud"], M["fog"] = volume_mats()
    M["ghost"] = emis("Ghost", PAL["cyan"], 0.0, alpha=0.0)
    M["diagline"] = emis("DiagLine", PAL["cyan"], 0.7, alpha=0.28)
    M["diagball"] = emis("DiagBall", PAL["gold"], 3.5)
    M["diagzone"] = emis("DiagZone", PAL["gold"], 0.0, alpha=0.0)
    M["goldglow"] = emis("GoldGlow", PAL["gold"], 6.0)
    for n in range(87, 93):
        M[f"lbl{n}"] = emis(f"Lbl{n}", PAL["gold"], 0.0, alpha=0.0)
    M["wind"] = emis("Wind", PAL["cyan"], 0.0, alpha=0.0)
    M["bolt"] = emis("Bolt", "#e6eeff", 0.0)
    M["rain"] = rain_mat("RainM")
    M["rain2"] = rain_mat("RainOffice", period=2.4, dash=0.3, strength=1.2, alpha=0.5)
    M["gold"] = pbr("Gold", PAL["gold"], 0.22, 1.0, emit=PAL["gold"], estr=0.08)
    M["cable"] = pbr("Cable", "#a9bbef", 0.3, 1.0)
    M["steel"] = pbr("Steel", "#3d5398", 0.38, 0.7)
    M["darksteel"] = pbr("DarkSteel", "#1c2958", 0.42, 0.6)
    M["chrome"] = pbr("Chrome", "#dfe7ff", 0.12, 1.0)
    M["rail"] = pbr("Rail", "#90a6e2", 0.3, 0.9)
    M["concrete"] = pbr("Concrete", "#2c3f7c", 0.75)
    M["chfloor"] = pbr("ChFloor", "#22336a", 0.3)
    M["chwall"] = window_glow_mat("ChWall", "#304788", 4.2, 0.18, 0.92, 8)
    M["chlabel"] = emis("ChLabel", "#bcd0ff", 1.5)
    M["laser"] = emis("Laser", PAL["gold"], 0.0, alpha=0.0)
    M["marker"] = emis("Marker", PAL["cyan"], 0.0, alpha=0.0)
    M["tick"] = emis("Tick", PAL["gold"], 0.0, alpha=0.0)
    m, nt, out = new_mat("Piston")
    b = node(nt, "ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*lin("#7f8fc4"), 1)
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Metallic"].default_value = 0.4
    b.inputs["Emission Color"].default_value = (*lin(PAL["heat"]), 1)
    link(nt, val(nt, "Heat", 0.0), b.inputs["Emission Strength"])
    link(nt, b.outputs[0], out.inputs[0])
    M["piston"] = m
    M["offloor"] = pbr("OfFloor", "#22346c", 0.45)
    M["ofceil"] = pbr("OfCeil", "#5269ad", 0.8)
    M["ofwall"] = pbr("OfWall", "#3c5499", 0.85)
    M["glass"] = pbr("Glass", "#9fb4ff", 0.05, 0.0, alpha=0.08)
    M["glasscup"] = pbr("GlassCup", "#cfdcff", 0.05, 0.0, alpha=0.25)
    M["water"] = pbr("Water", "#2fb4ff", 0.05, 0.0, emit="#2fb4ff", estr=1.2, alpha=0.88)
    for k in ("water", "glasscup", "glass"):
        try:
            M[k].surface_render_method = "BLENDED"
        except Exception:
            pass
    m, nt, out = new_mat("Backdrop")
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    vz = mth(nt, "ADD", mth(nt, "DIVIDE", sep.outputs[2], 170.0), 0.5)
    vo = node(nt, "ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 0.6
    link(nt, P, vo.inputs["Vector"])
    dots = mth(nt, "MULTIPLY", mth(nt, "LESS_THAN", vo.outputs["Distance"], 0.08), mth(nt, "LESS_THAN", vz, 0.42))
    sky = ramp(nt, vz, "#2a3f86", "#0a1230")
    em = node(nt, "ShaderNodeEmission")
    mix = node(nt, "ShaderNodeMixShader")
    em2 = node(nt, "ShaderNodeEmission")
    em2.inputs[0].default_value = (*lin("#ffe2b8"), 1)
    em2.inputs[1].default_value = 3.0
    link(nt, sky, em.inputs[0])
    link(nt, mth(nt, "MULTIPLY_ADD", val(nt, "F", 0.0), 6.0, 1.0), em.inputs[1])
    link(nt, dots, mix.inputs[0])
    link(nt, em.outputs[0], mix.inputs[1])
    link(nt, em2.outputs[0], mix.inputs[2])
    link(nt, mix.outputs[0], out.inputs[0])
    M["backdrop"] = m
    M["desk"] = pbr("Desk", "#5a74bd", 0.5)
    M["light"] = pbr("Light", "#c4d1f5", 0.6)
    M["screen"] = emis("Screen", "#7fa2ff", 2.2)
    M["chair"] = pbr("Chair", "#24357a", 0.7)
    M["lampshade"] = pbr("LampShade", "#e2e9ff", 0.5)
    M["bulb"] = emis("Bulb", "#ffe0b0", 12)
    M["leaf"] = pbr("Leaf", "#4f74c9", 0.6)
    M["pic"] = pbr("Pic", "#7d95d6", 0.6)
    M["panel"] = emis("Panel", "#e8eeff", 4)
    M["book"] = pbr("Book", "#283c84", 0.6)
    m, nt, out = new_mat("Ruler")
    P = node(nt, "ShaderNodeAttribute", attribute_name="rest").outputs["Vector"]
    sep = node(nt, "ShaderNodeSeparateXYZ")
    link(nt, P, sep.inputs[0])
    tk = mth(nt, "LESS_THAN", mth(nt, "FRACT", mth(nt, "MULTIPLY", sep.outputs[0], 10.0)), 0.07)
    tk = mth(nt, "MULTIPLY", tk, mth(nt, "GREATER_THAN", sep.outputs[1], 0.05))
    b = node(nt, "ShaderNodeBsdfPrincipled")
    link(nt, ramp(nt, tk, "#e3eaff", "#1c2a60"), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    link(nt, b.outputs[0], out.inputs[0])
    M["ruler"] = m
    return M


def ruler_rest_fix():
    """RulerIn has no rest attribute; give it a plain material look by reusing Light."""
    ob = bpy.data.objects["RulerIn"]
    ob.data.materials[0] = bpy.data.materials["Light"]


# ----------------------------------------------------------------------------------------------- shots

TRACKS = {}


def put(S, idb, path, v, idx=0, const=False):
    S[(idb, path, idx)] = (float(v), const)


def nv(m, name="S"):  # (node tree, path) of a material's Value node
    return m.node_tree, f'nodes["{name}"].outputs[0].default_value'


def cam(S, eye, tgt, lens=28, roll=0.0, fstop=8.0, focus=None, yaw=0.0, pitch=0.0, clip=0.1):
    eye, tgt = Vector(eye), Vector(tgt)
    d = tgt - eye
    if yaw or pitch:
        d = Matrix.Rotation(yaw, 3, "Z") @ d
        side = d.cross(Vector((0, 0, 1))).normalized()
        d = Matrix.Rotation(pitch, 3, side) @ d
    q = d.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), roll)
    S["cam"] = (eye, q, lens, fstop, focus if focus is not None else (tgt - eye).length, clip)


def whip(t, t_end=None, t_start=None, amt=rad(70), dur=0.18):
    """Yaw offset for a whip pan out of a shot (t_end) or into one (t_start)."""
    y = 0.0
    if t_end is not None:
        y += amt * ein(seg(t, t_end - dur, t_end))
    if t_start is not None:
        y -= amt * (1 - eout(seg(t, t_start, t_start + dur)))
    return y


FLASHES = [(1.75, 1.3), (1.92, 0.7), (5.86, 1.5), (16.12, 1.0), (30.8, 1.6), (30.98, 0.6)]


def defaults(t, S, W):
    cty, ch, of, ru, M = W["city"], W["ch"], W["of"], W["ru"], W["M"]
    scn = bpy.context.scene
    e = 0.0
    for tf, a in FLASHES:
        if t >= tf - 1 / FPS:
            e += a * math.exp(-max(t - tf, 0) / 0.11)
    put(S, scn, "view_settings.exposure", e)
    put(S, W["sun"], "energy", 2.2)
    for b in cty["bolts"]:
        put(S, b, "hide_render", 1, const=True)
    put(S, *nv(M["bolt"]), 0.0)
    put(S, cty["shell"], "modifiers[\"Bend\"].angle", 0.0)
    put(S, cty["ghost"], "modifiers[\"Bend\"].angle", 0.0)
    put(S, *nv(M["ghost"]), 0.0)
    put(S, *nv(M["ghost"], "A"), 0.0)
    put(S, *nv(M["facade"], "X"), 0.0)
    put(S, *nv(M["facade"], "G"), 3.0)
    put(S, cty["root"], "rotation_euler", 0.0, 1)
    put(S, cty["piv"], "rotation_euler", 0.0, 1)
    for k in ("floors", "chamber", "ball", "cables", "arrow", "ghost"):
        put(S, cty[k], "hide_render", 1, const=True)
    put(S, cty["arrow"].parent, "scale", 0.001, 0)
    put(S, cty["arrow"].parent, "scale", 0.001, 1)
    put(S, cty["arrow"].parent, "scale", 0.001, 2)
    put(S, *nv(M["diagzone"]), 0.0)
    put(S, *nv(M["diagzone"], "A"), 0.0)
    for n in range(87, 93):
        put(S, *nv(M[f"lbl{n}"]), 0.0)
        put(S, *nv(M[f"lbl{n}"], "A"), 0.0)
    put(S, *nv(M["wind"]), 0.0)
    put(S, *nv(M["wind"], "A"), 0.0)
    for i, (cu, ph, per) in enumerate(cty["winds"]):
        head = ((t / per + ph) % 1.0) * 1.6 - 0.3
        put(S, cu, "bevel_factor_start", clamp(head - 0.32))
        put(S, cu, "bevel_factor_end", clamp(head))
    put(S, W["rain"], "hide_render", 1, const=True)
    for i in range(len(cty["winds"])):
        put(S, bpy.data.objects[f"Wind{i}"], "hide_render", 0, const=True)
    put(S, *nv(M["rain"], "T"), t * 42.0)
    put(S, *nv(M["rain2"], "T"), t * 22.0)
    # chamber
    put(S, ch["piv"], "rotation_euler", 0.0, 1)
    for ld in ch["spots"]:
        put(S, ld, "energy", 0.0)
    put(S, ch["amb"], "energy", 900)
    put(S, ch["rim"], "energy", 0.0)
    put(S, *nv(M["piston"], "Heat"), 0.0)
    put(S, *nv(M["laser"]), 0.0)
    put(S, *nv(M["laser"], "A"), 0.0)
    put(S, *nv(M["marker"]), 0.0)
    put(S, *nv(M["marker"], "A"), 0.0)
    put(S, *nv(M["tick"]), 0.0)
    put(S, *nv(M["tick"], "A"), 0.0)
    put(S, *nv(M["chwall"], "F"), 0.0)
    put(S, *nv(M["chwall"], "F2"), 0.0)
    # office
    put(S, of["root"], "rotation_euler", 0.0, 0)
    put(S, of["root"], "rotation_euler", 0.0, 1)
    put(S, of["lamp"], "rotation_euler", 0.0, 0)
    put(S, of["lamp"], "rotation_euler", 0.0, 1)
    put(S, of["wpiv"], "rotation_euler", 0.0, 1)
    put(S, of["chair"], "location", 0.1, 0)
    put(S, of["chair"], "rotation_euler", 0.0, 2)
    put(S, of["leaves"], "rotation_euler", 0.0, 1)
    put(S, of["frame"], "rotation_euler", 0.0, 0)
    put(S, of["pen"], "location", 0.15, 0)
    put(S, *nv(M["backdrop"], "F"), 0.0)
    # ruler
    put(S, ru["out"], "modifiers[\"Bend\"].angle", 0.0)


def lightning(S, W, t, t0, which=1):
    on = t0 - 1 / FPS <= t < t0 + 0.16 or t0 + 0.2 <= t < t0 + 0.27
    put(S, W["city"]["bolts"][which], "hide_render", 0 if on else 1, const=True)
    put(S, *nv(W["M"]["bolt"]), 40.0 if on else 0.0)
    if on:
        put(S, W["sun"], "energy", 9.0)


def storm(S, W, wind=1.0, rain=True):
    put(S, *nv(W["M"]["wind"]), 3.5 * wind)
    put(S, *nv(W["M"]["wind"], "A"), 0.85 * clamp(wind))
    if rain:
        put(S, W["rain"], "hide_render", 0, const=True)


def near_winds(S, W, ymax=26):
    """close-up city shots: hide the wind ribbons that would pass right in front of the lens"""
    for i, (cu, _, _) in enumerate(W["city"]["winds"]):
        if abs(cu.splines[0].points[0].co.y) > ymax:
            put(S, bpy.data.objects[f"Wind{i}"], "hide_render", 1, const=True)


def bend(S, W, deg, ghost=None):
    put(S, W["city"]["shell"], "modifiers[\"Bend\"].angle", BEND_SIGN * rad(deg))
    if ghost is not None:
        put(S, W["city"]["ghost"], "modifiers[\"Bend\"].angle", BEND_SIGN * rad(ghost))
        put(S, W["city"]["ghost"], "hide_render", 0, const=True)


def xray(S, W, x, diag=True):
    put(S, *nv(W["M"]["facade"], "X"), x)
    if diag and x > 0.01:
        for k in ("ball", "cables"):
            put(S, W["city"][k], "hide_render", 0, const=True)


def chamber_phi(S, W, phi):
    put(S, W["ch"]["piv"], "rotation_euler", phi, 1)


def sway_office(S, W, t, amt):
    of = W["of"]
    w = 2 * math.pi / 2.3
    put(S, of["root"], "rotation_euler", amt * rad(1.5) * math.sin(w * t), 1)
    put(S, of["root"], "rotation_euler", amt * rad(0.6) * math.sin(w * t + 1.1), 0)
    put(S, of["lamp"], "rotation_euler", amt * rad(13) * math.sin(w * t - 0.9), 1)
    put(S, of["lamp"], "rotation_euler", amt * rad(4) * math.sin(w * t + 0.4), 0)
    put(S, of["wpiv"], "rotation_euler", -amt * rad(9) * math.sin(w * t - 0.5), 1)
    put(S, of["chair"], "location", 0.1 + amt * 0.16 * math.sin(w * t - 1.2), 0)
    put(S, of["chair"], "rotation_euler", amt * rad(14) * math.sin(w * t * 0.5), 2)
    put(S, of["leaves"], "rotation_euler", amt * rad(6) * math.sin(w * t - 0.7), 1)
    put(S, of["frame"], "rotation_euler", amt * rad(5) * math.sin(w * t - 1.0), 0)
    put(S, of["pen"], "location", 0.15 + amt * 0.12 * math.sin(w * t - 1.4), 0)


def shots(W):
    cty, ch, of, M = W["city"], W["ch"], W["of"], W["M"]
    L = []

    def S1a(t, S):  # above the storm, diving into the clouds
        u = seg(t, 0.0, 1.45)
        cam(S, V(62, -185, 56).lerp(V(36, -112, 66), ein(u) * 0.6 + u * 0.4), V(0, 0, 70).lerp(V(0, 0, 82), u),
            lens=34, roll=rad(lerp(-9, -4, u)), clip=0.5)
        storm(S, W, 0.7)
    L.append((0.0, 1.45, S1a))

    def S1b(t, S):  # under the clouds, lightning hits the spire
        u = seg(t, 1.45, 2.65)
        a = rad(lerp(-62, -78, u))
        r = lerp(80, 52, eout(u))
        cam(S, V(r * math.cos(a), r * math.sin(a), lerp(122, 104, u)), V(0, 0, lerp(99, 92, u)), lens=24,
            roll=rad(lerp(5, 1, u)), clip=0.5, pitch=rad(-60) * ein(seg(t, 2.47, 2.65)))
        storm(S, W, 0.9)
        lightning(S, W, t, 1.75, 1)
    L.append((1.45, 2.65, S1b))

    def S2a(t, S):  # street level, looking up the tower
        u = seg(t, 2.65, 3.92)
        cam(S, V(15, -32, 1.8).lerp(V(11, -25, 2.4), u), V(0, 0, 40).lerp(V(0, 0, 62), ss(u)), lens=19,
            roll=rad(lerp(-6, -2, u)), clip=0.2, pitch=rad(45) * ein(seg(t, 3.75, 3.92)))
        storm(S, W, 1.0)
    L.append((2.65, 3.92, S2a))

    def S2b(t, S):  # rocket up the facade and through a crown window
        u = seg(t, 3.92, 5.95)
        zz = lerp(16, 79.2, ein(u) * 0.55 + ss(u) * 0.45)
        k = ein(seg(t, 5.45, 5.95))
        y = lerp(-17, -10.5, ss(u))
        y = lerp(y, -5.9, k)
        eye = V(lerp(3.0, 0.5, u), y, zz)
        tgt = V(0, 0, zz + lerp(16, 0.4, ss(seg(t, 4.6, 5.6))))
        cam(S, eye, tgt.lerp(V(0, 6, 79.4), k), lens=22, roll=rad(lerp(-4, 0, u)), clip=0.1,
            pitch=-rad(40) * (1 - eout(seg(t, 3.92, 4.12))))
        storm(S, W, 1.0)
        put(S, *nv(M["facade"], "G"), lerp(3, 7, seg(t, 4.6, 5.9)))
    L.append((3.92, 5.95, S2b))

    def S3(t, S):  # in the dark, the ball swings past: a full metre
        u = seg(t, 5.95, 7.5)
        phi = phi_for(-1.0 + 2.0 * ss(seg(t, 5.95, 7.3)))
        chamber_phi(S, W, phi)
        bc = ball_world(phi)
        eye = C + V(5.2, -6.8, 5.6).lerp(V(4.4, -6.0, 6.0), u)
        k = ein(seg(t, 7.18, 7.5))
        eye = eye.lerp(bc + V(0.6, -3.2, 0.3), k)
        cam(S, eye, (C + V(0, 0, 6.8)).lerp(bc, 0.4 + 0.6 * k), lens=30, roll=rad(lerp(4, -2, u)), clip=0.05, fstop=4)
        put(S, ch["rim"], "energy", 2500)
        put(S, ch["amb"], "energy", 140)
        f = 1.0 if 6.35 <= t < 6.45 or 6.52 <= t < 6.58 else 0.0
        put(S, *nv(M["chwall"], "F"), f)
        put(S, *nv(M["chwall"], "F2"), f)
    L.append((5.95, 7.5, S3))

    def S4(t, S):  # wind makes the tower sway
        u = seg(t, 7.5, 9.45)
        per = 1.3
        ph = math.pi / 2 - 2 * math.pi * (9.45 - 7.5) / per
        amp = 20 * eout(seg(t, 7.5, 8.2))
        bend(S, W, amp * math.sin(2 * math.pi * (t - 7.5) / per + ph))
        cam(S, V(0, -152, 50).lerp(V(0, -140, 50), u), V(0, 0, 49), lens=35, clip=0.5)
        storm(S, W, 1.0)
    L.append((7.5, 9.45, S4))

    def S5(t, S):  # match cut: a ruler flicked on a desk
        u = seg(t, 9.45, 11.3)
        tt = t - 9.45
        put(S, W["ru"]["out"], "modifiers[\"Bend\"].angle", rad(42) * math.exp(-tt / 1.1) * math.cos(2 * math.pi * 2.6 * tt))
        r = ss(seg(t, 9.62, 10.35))
        eye = (R + V(1.2, -2.7, 0.45)).lerp(R + V(0.7, -3.6, 0.75), r)
        tgt = (R + V(0.9, 0, 0.05)).lerp(R + V(0.6, 0, 0.15), r)
        cam(S, eye, tgt, lens=35, roll=rad(-90) * (1 - r), clip=0.02, fstop=5.6, yaw=whip(t, t_end=11.3))
    L.append((9.45, 11.3, S5))

    def S6a(t, S):  # up top: the office sways
        u = seg(t, 11.3, 12.35)
        sway_office(S, W, t, 1.0)
        cam(S, O + V(2.1, -2.6, 1.55).lerp(V(1.8, -2.2, 1.5), u), O + V(-0.1, 1.6, 1.15), lens=24,
            roll=rad(3.5) * math.sin(2 * math.pi * t / 2.3), clip=0.02, fstop=4, yaw=whip(t, t_start=11.3))
        f = 1.0 if 11.95 <= t < 12.05 or 12.1 <= t < 12.16 else 0.0
        put(S, *nv(M["backdrop"], "F"), f)
    L.append((11.3, 12.35, S6a))

    def S6b(t, S):  # the water glass sloshes
        u = seg(t, 12.35, 13.4)
        sway_office(S, W, t, 1.0)
        cam(S, O + V(0.86, 0.85, 0.98).lerp(V(0.8, 0.92, 0.95), u), O + V(0.42, 1.36, 0.86), lens=50,
            roll=rad(2.5) * math.sin(2 * math.pi * t / 2.3), clip=0.01, fstop=5.6)
    L.append((12.35, 13.4, S6b))

    def S7(t, S):  # x-ray: floors 87 to 92
        u = seg(t, 13.4, 16.2)
        k = ein(seg(t, 15.75, 16.2))
        eye = V(17, -31, 73.5).lerp(V(9.5, -19, 79), ss(u))
        eye = eye.lerp(V(1.5, -5.5, 79.6), k)
        cam(S, eye, V(lerp(1.0, 2.0, u), 0, lerp(78, 79.5, u)), lens=30, clip=0.2)
        xray(S, W, ss(seg(t, 13.55, 14.2)))
        storm(S, W, 0.35)
        for n, tl in zip(range(87, 93), (14.44, 14.62, 14.8, 14.98, 15.16, 15.3)):
            a = eout(seg(t, tl, tl + 0.15))
            put(S, *nv(M[f"lbl{n}"]), 5.0 * a)
            put(S, *nv(M[f"lbl{n}"], "A"), a)
        z = eout(seg(t, 15.3, 15.6))
        put(S, cty["chamber"], "hide_render", 0, const=True)
        put(S, *nv(M["diagzone"]), 2.0 * z)
        put(S, *nv(M["diagzone"], "A"), 0.22 * z)
        put(S, cty["piv"], "rotation_euler", rad(3) * math.sin(2 * math.pi * t / 2.0), 1)
    L.append((13.4, 16.2, S7))

    def S8(t, S):  # crane down the cables in the dark
        u = seg(t, 16.2, 17.15)
        chamber_phi(S, W, rad(0.6) * math.sin(t))
        cam(S, C + V(3.2, -4.6, 19.2).lerp(V(3.7, -5.6, 11.8), ss(u)), C + V(1.4, -1.2, 17).lerp(V(0.6, 0, 9.2), ss(u)),
            lens=26, roll=rad(lerp(-6, 0, u)), clip=0.05, fstop=4)
        put(S, ch["rim"], "energy", 2500)
        put(S, ch["amb"], "energy", 160)
    L.append((16.2, 17.15, S8))

    def spots_on(S, t):
        for g, tg in enumerate((17.18, 17.33, 17.48)):
            put(S, ch["spots"][g], "energy", 4200 * (1 if t >= tg else 0) * (1 + 0.6 * math.exp(-max(t - tg, 0) / 0.08)))
        put(S, ch["amb"], "energy", lerp(160, 900, seg(t, 17.2, 17.7)))
        put(S, ch["rim"], "energy", 1500)

    def S9a(t, S):  # the reveal: 660 tonnes of steel
        u = seg(t, 17.15, 18.4)
        chamber_phi(S, W, rad(0.6) * math.sin(t))
        cam(S, C + V(0, -6.9, 3.6).lerp(V(0, -6.3, 4.4), eout(u)), C + V(0, 0, 7.2), lens=18, clip=0.05, fstop=5.6)
        spots_on(S, t)
    L.append((17.15, 18.4, S9a))

    def S9b(t, S):  # slide over the stacked steel plates
        u = seg(t, 18.4, 19.5)
        chamber_phi(S, W, rad(0.6) * math.sin(t))
        a = rad(lerp(-72, -106, u))
        cam(S, C + V(5.0 * math.cos(a), 5.0 * math.sin(a), lerp(8.4, 7.6, u)), C + V(0, 0, lerp(7.2, 6.8, u)), lens=35,
            clip=0.05, fstop=4, yaw=whip(t, t_end=19.5, amt=rad(-60)))
        spots_on(S, t)
    L.append((18.4, 19.5, S9b))

    def S10(t, S):  # the whole damper
        u = seg(t, 19.5, 21.75)
        chamber_phi(S, W, rad(1.6) * math.sin(2 * math.pi * (t - 19.5) / 3.4))
        a = rad(lerp(-112, -72, u))
        cam(S, C + V(6.6 * math.cos(a), 6.6 * math.sin(a), lerp(13.6, 12.4, u)), C + V(0, 0, 7.0), lens=17, clip=0.05,
            yaw=whip(t, t_start=19.5, amt=rad(-60)) + whip(t, t_end=21.75))
        spots_on(S, t)
    L.append((19.5, 21.75, S10))

    def diag(t, S, th_deg, phi_deg):
        put(S, cty["root"], "rotation_euler", rad(th_deg), 1)
        put(S, cty["piv"], "rotation_euler", rad(phi_deg), 1)
        xray(S, W, 1.0)
        put(S, cty["chamber"], "hide_render", 0, const=True)
        put(S, *nv(M["diagzone"]), 1.2)
        put(S, *nv(M["diagzone"], "A"), 0.12)

    def S11(t, S):  # same rhythm, opposite swing
        u = seg(t, 21.75, 23.75)
        w = 2 * math.pi * (t - 21.75) / 1.9
        diag(t, S, 1.5 * math.sin(w), 6.0 * math.sin(w))
        cam(S, V(2, -64, 70).lerp(V(1.5, -56, 71), u), V(0, 0, 71), lens=45, clip=0.5, yaw=whip(t, t_start=21.75))
        storm(S, W, 0.3, rain=True)
        near_winds(S, W)
    L.append((21.75, 23.75, S11))

    def S12(t, S):  # wind shoves the tower one way
        u = seg(t, 23.75, 25.4)
        th = 3.2 * eout(seg(t, 24.0, 24.7))
        diag(t, S, th, 2.8 * th)
        cam(S, V(-4, -50, 73).lerp(V(-2.5, -45, 74), u), V(0, 0, 74), lens=42, clip=0.5)
        storm(S, W, 1.3)
        near_winds(S, W)
    L.append((23.75, 25.4, S12))

    def S13(t, S):  # the ball lags behind and pulls it back
        u = seg(t, 25.4, 27.5)
        r = ss(seg(t, 26.7, 27.35))
        th = 3.2 * (1 - r)
        diag(t, S, th, 2.8 * 3.2 * (1 - ss(seg(t, 26.9, 27.45))))
        a = eout(seg(t, 26.75, 26.95)) * (1 - seg(t, 27.3, 27.5))
        for i in range(3):
            put(S, cty["arrow"].parent, "scale", max(a, 0.001), i)
        put(S, cty["arrow"], "hide_render", 0 if a > 0.01 else 1, const=True)
        cam(S, V(-3, -27, 79).lerp(V(-2.2, -23.5, 79.3), u), V(-0.8, 0, 79), lens=38, clip=0.3)
        storm(S, W, 0.4)
        near_winds(S, W)
    L.append((25.4, 27.5, S13))

    def piston_phi(t):
        return rad(3.4) * math.sin(2 * math.pi * (t - 27.5) / 2.1)

    def S14a(t, S):  # drop under the ball: eight pistons
        u = seg(t, 27.5, 29.0)
        chamber_phi(S, W, piston_phi(t))
        k = ss(seg(t, 27.5, 28.1))
        eye = (C + V(2.6, -6.2, 9.5)).lerp(C + V(2.6, -6.0, 2.5), k).lerp(C + V(2.4, -5.6, 2.3), seg(t, 28.1, 29.0))
        cam(S, eye, (C + V(0, 0, 6.6)).lerp(C + V(0, 0, 3.0), k), lens=18, clip=0.05)
        spots_on(S, 30)
    L.append((27.5, 29.0, S14a))

    def S14b(t, S):  # a piston heats up
        u = seg(t, 29.0, 30.8)
        phi = piston_phi(t)
        chamber_phi(S, W, phi)
        a = rad(-45)
        A = C + V(7.2 * math.cos(a), 7.2 * math.sin(a), 1.25)
        B = ball_world(phi) + V(1.7 * math.cos(a), 1.7 * math.sin(a), -BALL_R - 0.05 - 0) - V(0, 0, 0)
        Mid = (A + B) / 2
        d = (B - A).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized()
        eye = Mid - side * lerp(2.6, 2.1, u) + V(0, 0, 0.7) + d * lerp(-0.6, 0.4, u)
        cam(S, eye, Mid + V(0, 0, 0.1), lens=32, clip=0.03, fstop=2.8)
        put(S, *nv(M["piston"], "Heat"), 1.1 * ss(seg(t, 29.25, 30.3)))
        spots_on(S, 30)
    L.append((29.0, 30.8, S14b))

    def S15(t, S):  # with vs without: up to 40% less sway
        u = seg(t, 30.8, 33.0)
        w = 2 * math.pi * (t - 30.8) / 1.6
        g = 22 * math.sin(w) * eout(seg(t, 30.8, 31.2))
        bend(S, W, 0.6 * g, ghost=g)
        put(S, *nv(M["ghost"]), 2.5)
        put(S, *nv(M["ghost"], "A"), 0.55)
        put(S, *nv(M["facade"], "G"), 9.0)
        cam(S, V(-22, -168, 52).lerp(V(-15, -156, 53), u), V(0, 0, 53), lens=35, clip=0.5, yaw=whip(t, t_end=33.0))
        storm(S, W, 0.8)
        lightning(S, W, t, 30.8, 0)
    L.append((30.8, 33.0, S15))

    def S16a(t, S):  # in that typhoon the ball moved a metre
        u = seg(t, 33.0, 34.4)
        chamber_phi(S, W, phi_for(1.0 * eout(seg(t, 33.25, 35.1))))
        cam(S, C + V(3.0, -6.0, 5.2).lerp(V(2.6, -5.4, 4.6), u), C + V(0.6, 0, 1.8), lens=22, clip=0.05,
            yaw=whip(t, t_start=33.0))
        spots_on(S, 30)
        on = eout(seg(t, 33.1, 33.4))
        for nm in ("marker", "laser"):
            put(S, *nv(M[nm]), 4.0 * on)
            put(S, *nv(M[nm], "A"), on)
    L.append((33.0, 34.4, S16a))

    def S16b(t, S):
        u = seg(t, 34.4, 35.35)
        chamber_phi(S, W, phi_for(1.0 * eout(seg(t, 33.25, 35.1))))
        cam(S, C + V(2.7, -3.5, 0.55).lerp(V(2.3, -3.0, 0.5), u), C + V(0.9, 0, 1.4), lens=24, clip=0.02, fstop=4,
            yaw=whip(t, t_end=35.35, amt=rad(-60)))
        spots_on(S, 30)
        for nm in ("marker", "laser"):
            put(S, *nv(M[nm]), 4.0)
            put(S, *nv(M[nm], "A"), 1.0)
        hit = eout(seg(t, 35.0, 35.15))
        put(S, *nv(M["tick"]), 12.0 * hit)
        put(S, *nv(M["tick"], "A"), hit)
    L.append((34.4, 35.35, S16b))

    def S17(t, S):  # so the people inside didn't have to: calm office
        u = seg(t, 35.35, 37.5)
        sway_office(S, W, t, 0.0)
        b = ss(seg(t, 37.05, 37.5))
        cam(S, O + V(1.25, 0.5, 1.06).lerp(V(1.0, 0.72, 0.99), u), O + V(0.43, 1.35, 0.85), lens=45, clip=0.01,
            fstop=lerp(5.6, 0.5, b), focus=lerp(1.0, 0.12, b), yaw=whip(t, t_start=35.35, amt=rad(-60)))
    L.append((35.35, 37.5, S17))

    def S18(t, S):  # pull out: the tower stands still
        u = seg(t, 37.5, T_END)
        b = 1 - ss(seg(t, 37.5, 38.1))
        e = ss(u)
        eye = V(6, -22, 80.5).lerp(V(46, -250, 66), e)
        tgt = V(0, 0, 80).lerp(V(0, 0, 64), e)
        cam(S, eye, tgt, lens=28, clip=0.3, fstop=lerp(8, 0.4, b), focus=lerp((tgt - eye).length, 3.0, b))
        put(S, *nv(M["facade"], "G"), 9.0)
        storm(S, W, 0.0, rain=True)
        put(S, *nv(M["rain"], "A"), lerp(0.3, 0.0, ss(seg(t, 38.0, 39.6))))
    L.append((37.5, T_END, S18))
    return L


def bake(W):
    tracks, camk = {}, []
    L = shots(W)
    for i, (t0, t1, fn) in enumerate(L):
        f0 = math.ceil(t0 * FPS - 1e-6) + 1
        f1 = math.ceil(t1 * FPS - 1e-6)  # last frame of this shot
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
            camk.append((f,) + S.pop("cam"))
            for k, (v, const) in S.items():
                tracks.setdefault(k, []).append((f, v, const))
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
                 ("volumetric_end", 1400.0), ("volumetric_tile_size", "8"), ("volumetric_samples", 48),
                 ("use_volumetric_shadows", False), ("motion_blur_steps", 1), ("use_bokeh_jittered", False)):
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
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.compression = 15


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    M = materials()
    build_world()
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "AUTO"
    cd.dof.use_dof = True
    cd.clip_end = 4000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 2.2
    sd.color = lin("#b8c8ff")
    sd.angle = rad(8)
    so = bpy.data.objects.new("Sun", sd)
    scn.collection.objects.link(so)
    so.rotation_euler = (rad(52), rad(-18), rad(-35))
    W = dict(M=M, cam=camo, sun=sd)
    W["city"] = build_city(M)
    W["rain"] = build_rain(M, camo)
    W["ch"] = build_chamber(M)
    W["of"] = build_office(M)
    W["ru"] = build_ruler(M)
    ruler_rest_fix()
    bake(W)
    render_settings(scn)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


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
    import os
    os.makedirs(outdir, exist_ok=True)
    for f in frames:
        p = os.path.join(outdir, f"f_{f:04d}.png")
        if os.path.exists(p) and "--skip" in sys.argv:
            continue
        scn.frame_set(f)
        scn.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print("FRAME", f, flush=True)


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    if a[0] == "build":
        build(a[1])
    elif a[0] == "render":
        render(a[1], int(a[2]), int(a[3]), a[4] if len(a) > 4 and not a[4].startswith("--") else "")
