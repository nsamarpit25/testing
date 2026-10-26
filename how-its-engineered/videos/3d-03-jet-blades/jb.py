"""Jet engine blades that run hotter than their melting point: a procedural 3D product film for @how.its.engineered
(episode 3, no characters). Two studio sets far apart, each with its own floor and lights: a turbofan with a quarter
cutaway (E, engine axis along x, metres) and a macro studio with a high-pressure turbine disc on a stand and its hero
blade (D, disc axis along y, real scale: the blade is ~10 cm tall). Blade frame: z radial (span), x axial (gas flows
+x), y tangential; the origin sits on top of the platform. Every animated property is baked per frame from the shot
list; cuts get half-frame keys so motion blur never smears across a cut. Tracked labels are projected from 3D anchors
at bake time and written next to the .blend as labels.json.

blender -b --factory-startup -P jb.py -- build <out.blend>
blender -b jb.blend -P jb.py -- render <outdir> <height> <samples> [a-b | f,f,f] [--skip]
"""
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, Matrix, Quaternion

FPS = 30
T_END = 32.0
F_END = int(T_END * FPS) + 1
E0 = Vector((0, 0, 0))            # engine studio
D0 = Vector((100, 0, 0))          # disc / blade macro studio
ZE = 2.05                         # engine axis height
DC = D0 + Vector((0, 0, 0.62))    # disc centre
rad = math.radians

# blade (metres)
H_AF = 0.055                      # airfoil span
C_AX = 0.034                      # root chord
R_P = 0.300                       # platform radius on the disc
N_BL = 64
PITCH = 2 * math.pi * R_P / N_BL
Z_ROOT0, Z_ROOT1 = -0.016, -0.040  # fir-tree root top / bottom

PAL = dict(cyan="#2fd6ff", amber="#ff6a1a", gold="#ffc45a", ice="#bfe6ff")
THERMAL = [(0.0, "#05010f"), (0.22, "#2a0b5c"), (0.42, "#8e0f4a"), (0.58, "#d8242a"), (0.72, "#ff6a0e"),
           (0.85, "#ffb21c"), (0.94, "#ffe9a0"), (1.0, "#fffaf0")]
MELT = 0.84                       # melting point on the thermal scale (gas ~0.97, cooled metal ~0.6)
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



# ----------------------------------------------------------------------------------------------- 2-D helpers

def V2(x, y):
    return Vector((x, y))


def fillet(pts, r, n=6, closed=True):
    """Round every corner of a 2-D polyline (r: one radius or one per point). Corners closer than r get smaller arcs."""
    pts = [Vector(p) for p in pts]
    m = len(pts)
    out = []
    for i, P in enumerate(pts):
        if not closed and i in (0, m - 1):
            out.append(P)
            continue
        A, B = pts[i - 1], pts[(i + 1) % m]
        rr = r[i] if isinstance(r, (list, tuple)) else r
        u, w = (A - P), (B - P)
        la, lb = u.length, w.length
        if rr <= 0 or la < 1e-9 or lb < 1e-9:
            out.append(P)
            continue
        u, w = u / la, w / lb
        th = math.acos(clamp(u.dot(w), -1.0, 1.0))
        if th > math.pi - 1e-3:
            out.append(P)
            continue
        d = min(rr / math.tan(th / 2), 0.48 * la, 0.48 * lb)
        re = d * math.tan(th / 2)
        bis = (u + w).normalized()
        C = P + bis * (re / math.sin(th / 2))
        T1, T2 = P + u * d, P + w * d
        a1, a2 = math.atan2(T1.y - C.y, T1.x - C.x), math.atan2(T2.y - C.y, T2.x - C.x)
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            a = a1 + da * k / n
            out.append(C + V2(math.cos(a), math.sin(a)) * re)
    return out


def resample(pts, step, closed=True):
    """Even spacing along a polyline (keeps lathe rings smooth)."""
    P = [Vector(p) for p in pts] + ([Vector(pts[0])] if closed else [])
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(4, int(L[-1] / step))
    out, j = [], 0
    for k in range(n + (0 if closed else 1)):
        s = L[-1] * k / n
        while j < len(L) - 2 and L[j + 1] < s:
            j += 1
        u = (s - L[j]) / max(L[j + 1] - L[j], 1e-12)
        out.append(P[j].lerp(P[j + 1], u))
    return out


# ----------------------------------------------------------------------------------------------- lathe / extrude

def bm_lathe(bm, prof, a0=0.0, a1=2 * math.pi, n=128, caps=True, M=None):
    """Revolve a closed (x, r) profile around the x axis from angle a0 to a1 (angle 0 = +y, 90 = +z)."""
    M = M or Matrix()
    full = abs(a1 - a0) >= 2 * math.pi - 1e-6
    m = len(prof)
    nr = n if full else n + 1
    rings = []
    for k in range(nr):
        a = a0 + (a1 - a0) * k / n
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new(M @ Vector((p.x, max(p.y, 1e-5) * ca, max(p.y, 1e-5) * sa))) for p in prof])
    faces = []
    for k in range(n if full else n):
        r0, r1 = rings[k], rings[(k + 1) % nr]
        for i in range(m):
            try:
                f = bm.faces.new((r0[i], r0[(i + 1) % m], r1[(i + 1) % m], r1[i]))
                f.smooth = True
                faces.append(f)
            except ValueError:
                pass
    if not full and caps:
        for ring in (rings[0], rings[-1]):
            f = bm.faces.new(ring)
            f.smooth = False
            faces.append(f)
    return faces


def lathe(name, prof, mat, a0=0.0, a1=2 * math.pi, n=128, parent=None, loc=(0, 0, 0), caps=True, step=None):
    if step:
        prof = resample(prof, step)
    bm = bmesh.new()
    bm_lathe(bm, [Vector(p) for p in prof], a0, a1, n, caps)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return obj_from_bm(name, bm, mat, parent, loc)


def bm_extrude(bm, prof, x0, x1, ch=0.0, M=None, map2=None):
    """Extrude a closed 2-D profile (y, z) along x from x0 to x1 with a small chamfer ch at both ends.
    map2(x, p2) -> 3-D point overrides the default (x, p.x, p.y)."""
    M = M or Matrix()
    pv = [Vector(p) for p in prof]
    cen = sum(pv, Vector((0, 0))) / len(pv)
    mp = map2 or (lambda x, p: Vector((x, p.x, p.y)))
    stations = [(x0, ch), (x0 + ch, 0.0), (x1 - ch, 0.0), (x1, ch)] if ch else [(x0, 0.0), (x1, 0.0)]
    rings = []
    for x, inset in stations:
        ring = []
        for p in pv:
            d = (cen - p)
            q = p + (d.normalized() * inset if d.length > 1e-9 else Vector((0, 0)))
            ring.append(bm.verts.new(M @ mp(x, q)))
        rings.append(ring)
    m = len(pv)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(m):
            f = bm.faces.new((r0[i], r0[(i + 1) % m], r1[(i + 1) % m], r1[i]))
            f.smooth = True
    for ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring)
        f.smooth = False


def bm_rbox(bm, c, s, r=0.0006, segs=3, M=None):
    """Box with bevelled edges."""
    before = set(bm.verts)
    bm_box(bm, c, s)
    nv = [v for v in bm.verts if v not in before]
    ed = list({e for v in nv for e in v.link_edges})
    if r > 0:
        bmesh.ops.bevel(bm, geom=ed + nv, offset=r, segments=segs, profile=0.5, affect="EDGES", clamp_overlap=True)
    nv = [v for v in bm.verts if v not in before]
    if M is not None:
        for v in nv:
            v.co = M @ v.co
    for f in {f for v in nv for f in v.link_faces}:
        f.smooth = True


def weighted(ob):
    m = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
    try:
        m.keep_sharp = True
        m.mode = "FACE_AREA"
    except Exception:
        pass
    return ob


# ----------------------------------------------------------------------------------------------- the airfoil

def bez(P0, P1, P2, P3, t):
    a = 1 - t
    return P0 * a ** 3 + P1 * 3 * a * a * t + P2 * 3 * a * t * t + P3 * t ** 3


def af_ring(s, n=64):
    """Airfoil section at span fraction s in the blade x-y plane: points (counter-clockwise, starting at the TE on the
    suction side), outward normals, signed arc length from the leading edge (suction side positive), LE index."""
    c = C_AX * (1.0 - 0.12 * s)
    st = rad(-30 + 5 * s)
    b1, b2 = rad(46 - 10 * s), rad(-62 - 3 * s)
    P0, P3 = V2(0, 0), V2(math.cos(st), math.sin(st)) * c
    P1 = P0 + V2(math.cos(b1), math.sin(b1)) * 0.36 * c
    P2 = P3 - V2(math.cos(b2), math.sin(b2)) * 0.36 * c
    tau = 0.30 - 0.08 * s
    up, lo = [], []
    for k in range(n):
        t = 0.5 * (1 - math.cos(math.pi * k / (n - 1)))
        p = bez(P0, P1, P2, P3, t)
        dt = bez(P0, P1, P2, P3, min(t + 1e-4, 1)) - bez(P0, P1, P2, P3, max(t - 1e-4, 0))
        nn = V2(-dt.y, dt.x).normalized()
        yt = 5 * tau * (0.2969 * math.sqrt(t) - 0.1260 * t - 0.3516 * t * t + 0.2843 * t ** 3 - 0.1015 * t ** 4) * c
        up.append(p + nn * yt)
        lo.append(p - nn * yt)
    ring = up[::-1] + lo[1:]
    cen = sum(ring, V2(0, 0)) / len(ring)
    tw = rad(-7 * s)
    R = Matrix.Rotation(tw, 2)
    ring = [R @ (p - cen) for p in ring]
    m = len(ring)
    nrm = []
    for i in range(m):
        d = ring[(i + 1) % m] - ring[i - 1]
        nrm.append(V2(d.y, -d.x).normalized())
    arc = [0.0]
    for i in range(1, m):
        arc.append(arc[-1] + (ring[i] - ring[i - 1]).length)
    le = n - 1
    sa = [arc[le] - a for a in arc]
    return ring, nrm, sa, le


def af_point(sa, z, off=0.0):
    """Point, outward normal and downstream surface direction on the airfoil at signed arc sa and height z."""
    ring, nrm, sal, le = af_ring(clamp(z / H_AF))
    m = len(ring)
    for i in range(m - 1):
        a, b = sal[i], sal[i + 1]
        if (a - sa) * (b - sa) <= 0 and a != b:
            u = (sa - a) / (b - a)
            p = ring[i].lerp(ring[i + 1], u)
            nn = nrm[i].lerp(nrm[i + 1], u).normalized()
            down = (ring[i] - ring[i + 1]) if sa > 0 else (ring[i + 1] - ring[i])
            down = down.normalized()
            P = Vector((p.x + nn.x * off, p.y + nn.y * off, z))
            return P, Vector((nn.x, nn.y, 0)), Vector((down.x, down.y, 0))
    i = le
    return Vector((ring[i].x, ring[i].y, z)), Vector((nrm[i].x, nrm[i].y, 0)), Vector((1, 0, 0))


def af_stations():
    """(z, outward offset) rings: buried start, root fillet, span, rounded tip."""
    rf, rt = 0.0018, 0.0008
    st = [(-0.0016, rf)]
    for z in (0.0, 0.0002, 0.0005, 0.0009, 0.0013, 0.0018):
        st.append((z, rf - math.sqrt(max(rf * rf - (rf - z) ** 2, 0.0))))
    n = 40
    for k in range(n + 1):
        st.append((lerp(0.0026, H_AF - rt, k / n), 0.0))
    for k in range(1, 7):
        th = rad(90 * k / 6)
        st.append((H_AF - rt + rt * math.sin(th), -rt * (1 - math.cos(th))))
    return st


def bm_airfoil(bm, off=0.0, sa_keep=None, attrs=None, z_lo=None, squealer=False):
    """Loft the airfoil into bm (optionally offset outward by off, e.g. a coating). sa_keep=(lo, hi) keeps only faces
    whose arc range is inside (for split shells). Returns the rings. attrs collects per-vertex sa / sp / gt."""
    rings = []
    for z, o in af_stations():
        if z_lo is not None and z < z_lo:
            continue
        ring, nrm, sal, le = af_ring(clamp(z / H_AF))
        vs = []
        for p, nn, sa in zip(ring, nrm, sal):
            q = p + nn * (o + off)
            v = bm.verts.new((q.x, q.y, z))
            vs.append(v)
            if attrs is not None:
                attrs.setdefault("sa", {})[v] = sa
                attrs.setdefault("sp", {})[v] = z
                attrs.setdefault("te", {})[v] = (sal[0] - sa) if sa > 0 else (sa - sal[-1])
        rings.append((vs, sal))
    for (r0, sal), (r1, _) in zip(rings, rings[1:]):
        m = len(r0)
        for i in range(m):
            j = (i + 1) % m
            if sa_keep and not (sa_keep[0] <= min(sal[i], sal[j]) and max(sal[i], sal[j]) <= sa_keep[1]):
                continue
            if sa_keep and j == 0:
                continue
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.smooth = True
    if not sa_keep:
        top = rings[-1][0]
        cap = [bm.verts.new(v.co) for v in top]
        if attrs is not None:
            for v, w in zip(cap, top):
                attrs["sa"][v] = 99.0
                attrs["sp"][v] = H_AF
        f = bm.faces.new(cap)
        f.smooth = False
        if squealer:
            # squealer tip: a thin rim around a recessed tip floor
            r = bmesh.ops.inset_region(bm, faces=[f], thickness=0.0007, depth=-0.0014, use_even_offset=True)
            for g in r["faces"]:
                g.smooth = False
    return rings


def attrs_from(bm, attrs):
    """Turn {name: {vert: value}} into per-vertex lists in bm vertex order (missing -> default)."""
    bm.verts.index_update()
    out = {}
    for k, d in attrs.items():
        if k == "sp":
            out[k] = [d.get(v, v.co.z) for v in bm.verts]
            continue
        dflt = 99.0 if k in ("sa", "te") else 0.0
        out[k] = [d.get(v, dflt) for v in bm.verts]
    return out


# ----------------------------------------------------------------------------------------------- the blade

def root_hw(zd):
    """Fir-tree half width at depth zd below the root top (three lobes, tapering)."""
    return 0.0072 - 0.10 * zd + 0.0016 * math.cos(2 * math.pi * (zd - 0.0036) / 0.0072)


def root_profile():
    zs = [Z_ROOT0 - (Z_ROOT0 - Z_ROOT1) * k / 70 for k in range(71)]
    right = [V2(root_hw(Z_ROOT0 - z), z) for z in zs]
    wb = right[-1].x
    bottom = [V2(wb * math.cos(math.pi * k / 10), Z_ROOT1 - 0.0016 * math.sin(math.pi * k / 10)) for k in range(1, 10)]
    left = [V2(-p.x, p.y) for p in right[::-1]]
    return right + bottom + left


def blade_extent():
    ring, *_ = af_ring(0.0)
    xs = [p.x for p in ring]
    ys = [p.y for p in ring]
    return min(xs), max(xs), min(ys), max(ys)


def blade_mesh(name):
    """Hero blade mesh (shared by all blades): airfoil with fillet and rounded tip, bevelled platform, shank,
    fir-tree root. Attributes: sa (signed arc from LE, 99 off the airfoil), sp (height)."""
    bm = bmesh.new()
    at = {}
    bm_airfoil(bm, attrs=at, squealer=True)
    x0, x1, y0, y1 = blade_extent()
    cx = 0.5 * (x0 + x1)
    pl = x1 - x0 + 0.008
    # platform: a parallelogram sheared along the stagger so neighbouring platforms still tile the rim
    sh = Matrix.Translation((cx, 0, 0)) @ Matrix(((1, -0.42, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))) @ \
        Matrix.Translation((-cx, 0, 0))
    bm_rbox(bm, (cx, 0.0, -0.00175), (pl, PITCH - 0.0004, 0.0035), r=0.0006, M=sh)
    bm_rbox(bm, (cx, 0.0, -0.0098), (pl - 0.006, 0.009, 0.0128), r=0.0008)
    # angel-wing seals sticking out fore and aft of the shank
    for sx in (-1, 1):
        for zw in (-0.0058, -0.0128):
            bm_rbox(bm, (cx + sx * ((pl - 0.006) / 2 + 0.0018), 0.0, zw), (0.0042, 0.0082, 0.0011), r=0.00035)
    rx0, rx1 = cx - (pl - 0.006) / 2, cx + (pl - 0.006) / 2
    bm_extrude(bm, root_profile(), rx0, rx1, ch=0.0004)
    me_attrs = attrs_from(bm, at)
    sp = [v.co.z if v.co.z < 0 else s for v, s in zip(bm.verts, me_attrs["sp"])]
    me_attrs["sp"] = sp
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for k, vals in me_attrs.items():
        a = me.attributes.new(k, "FLOAT", "POINT")
        a.data.foreach_set("value", vals)
    return me, (rx0, rx1)


def mesh_obj(name, me, mat, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat and not me.materials:
        me.materials.append(mat)
    ob.parent = parent
    ob.location = loc
    return ob


def bm_tube(bm, pts, r, n=10, caps=True, attrs=None, phase=0.0, rfun=None):
    """Tube through 3-D points with parallel-transported rings; attrs gets gt (0..1 along) and gp (phase)."""
    rings = []
    prev_a = None
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_a is None:
            a = d.orthogonal().normalized()
        else:
            a = (prev_a - d * prev_a.dot(d)).normalized()
        prev_a = a
        b = d.cross(a)
        g = L[i] / max(L[-1], 1e-9)
        rr = r * (rfun(g) if rfun else 1.0)
        ring = [bm.verts.new(p + (a * math.cos(2 * math.pi * k / n) + b * math.sin(2 * math.pi * k / n)) * rr)
                for k in range(n)]
        if attrs is not None:
            for v in ring:
                attrs.setdefault("gt", {})[v] = g
                attrs.setdefault("gp", {})[v] = phase
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            f = bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
            f.smooth = True
    if caps:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])


def bm_to_obj(name, bm, attrs, mat, parent=None, loc=(0, 0, 0)):
    vals = attrs_from(bm, attrs) if attrs else {}
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for k, v in vals.items():
        a = me.attributes.new(k, "FLOAT", "POINT")
        a.data.foreach_set("value", v)
    return mesh_obj(name, me, mat, parent, loc)


def camber_pt(c, z):
    """A point on the mean line at chord fraction c and height z (for internal passages)."""
    ring, nrm, sal, le = af_ring(clamp(z / H_AF))
    m = len(ring)
    k = int(round(c * (le)))
    up = ring[le - k]
    lo = ring[min(le + k, m - 1)]
    p = (up + lo) / 2
    th = (up - lo).length
    return Vector((p.x, p.y, z)), th


def serpentine():
    """Three-pass cooling passage: up the leading-edge side, down mid-chord, up the trailing side, fed from the root."""
    cs = (0.20, 0.44, 0.68)
    zl, zh = 0.004, H_AF - 0.0045
    pts = []
    for z in [Z_ROOT1 + 0.004 + k * 0.003 for k in range(int((0.004 - Z_ROOT1 - 0.004) / 0.003))]:
        pts.append(Vector((camber_pt(cs[0], 0.0)[0].x, 0.0, z)))
    for k, c in enumerate(cs):
        zz = [lerp(zl, zh, j / 24) for j in range(25)]
        if k % 2:
            zz = zz[::-1]
        for z in zz:
            pts.append(camber_pt(c, z)[0])
        if k < 2:   # U-turn
            z_end = zz[-1]
            p0 = camber_pt(c, z_end)[0]
            p1 = camber_pt(cs[k + 1], z_end)[0]
            mid = (p0 + p1) / 2
            dz = 0.0026 if k % 2 == 0 else -0.0026
            for j in range(1, 10):
                a = math.pi * j / 10
                w = (1 - math.cos(a)) / 2
                q = p0.lerp(p1, w)
                q.z = z_end + dz * math.sin(a)
                pts.append(q)
    return pts


def build_blade_parts(M, me, parent):
    """Children of the hero blade: cooling passage, film ribbons, film blanket, ceramic coat halves, gas ribbons,
    grain selector. All in the blade frame."""
    P = {}
    # serpentine passage
    bm, at = bmesh.new(), {}
    sp = serpentine()
    bm_tube(bm, sp, 0.0017, 14, attrs=at)
    P["chan"] = bm_to_obj("Channels", bm, at, M["chan"], parent)
    # film ribbons from each cooling hole
    bm, at = bmesh.new(), {}
    rnd = random.Random(7)
    for row, (sa0, pitch, ofs) in enumerate(HOLE_ROWS):
        z = 0.0035 + ofs
        while z < H_AF - 0.004:
            pts = []
            sa = sa0
            side = 1 if sa0 > 0.0004 else (-1 if sa0 < -0.0004 else (1 if row % 2 else -1))
            L = rnd.uniform(0.007, 0.012)
            for j in range(16):
                g = j / 15
                h = 0.00018 + 0.00045 * g ** 0.7
                p, nn, dn = af_point(sa + side * L * g, z + 0.0006 * g, off=h)
                pts.append(p)
            ph = rnd.random()
            bm_ribbon(bm, pts, lambda g: 0.0004 + 0.0011 * g ** 0.8, at, ph)
            z += pitch
    P["film"] = bm_to_obj("Film", bm, at, M["film"], parent)
    # film blanket: a thin shell just off the surface
    bm, at = bmesh.new(), {}
    bm_airfoil(bm, off=0.00045, attrs=at, z_lo=0.0026)
    P["blanket"] = bm_to_obj("Blanket", bm, at, M["blanket"], parent)
    # ceramic coat: suction and pressure halves (shells with thickness)
    for key, keep in (("tbcS", (-0.0002, 1.0)), ("tbcP", (-1.0, 0.0002))):
        bm, at = bmesh.new(), {}
        outer = bm_airfoil(bm, off=0.0007, sa_keep=keep, attrs=at, z_lo=0.0004)
        inner = bm_airfoil(bm, off=0.00012, sa_keep=keep, attrs=at, z_lo=0.0004)
        for v in [v for vs, _ in inner for v in vs]:
            at.setdefault("side", {})[v] = 1.0
        # close the shell edges (top, bottom and the split lines)
        rim_close(bm, outer, inner, keep)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        P[key] = bm_to_obj("TBC_" + key, bm, at, M["tbc"], parent)
    # hot gas ribbons around the airfoil (near: hugging the skin; far: further out)
    for key, offs in (("gasN", (0.0006, 0.0013)), ("gasF", (0.0028, 0.0045, 0.0068))):
        bm, at = bmesh.new(), {}
        for zf in (0.12, 0.27, 0.42, 0.57, 0.72, 0.87):
            z = zf * H_AF
            for o in offs:
                for side in (1, -1):
                    pts = gas_path(z, o, side)
                    bm_tube(bm, pts, 0.00028 if key == "gasN" else 0.00034, 6, attrs=at, phase=rnd.random())
        P[key] = bm_to_obj("Gas_" + key, bm, at, M["gas"], parent)
    # grain selector pigtail + starter block under the root
    bm = bmesh.new()
    x0, x1, *_ = blade_extent()
    cx = 0.5 * (x0 + x1)
    hel = [Vector((cx + 0.0036 * math.cos(a), 0.0036 * math.sin(a), Z_ROOT1 - 0.0035 - 0.022 * a / (5 * math.pi)))
           for a in [5 * math.pi * k / 80 for k in range(81)]]
    hel = [Vector((cx, 0, Z_ROOT1 + 0.0005)), Vector((cx, 0, Z_ROOT1 - 0.002))] + hel
    bm_tube(bm, hel, 0.0012, 12)
    bm_rbox(bm, (cx, 0, Z_ROOT1 - 0.031), (0.016, 0.016, 0.008), r=0.0008)
    P["selector"] = obj_from_bm("Selector", bm, M["bladeH"], parent)
    return P


def bm_ribbon(bm, pts, wfun, at, phase):
    """A flat strip along pts, lying on the surface (width across the flow, along the span)."""
    rows = []
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    for i, p in enumerate(pts):
        g = L[i] / max(L[-1], 1e-9)
        w = wfun(g)
        a = Vector((0, 0, 1))
        r = [bm.verts.new(p - a * w / 2), bm.verts.new(p + a * w / 2)]
        for v, x in zip(r, (0.0, 1.0)):
            at.setdefault("gt", {})[v] = g
            at.setdefault("gp", {})[v] = phase
            at.setdefault("gx", {})[v] = x
        rows.append(r)
    for r0, r1 in zip(rows, rows[1:]):
        f = bm.faces.new((r0[0], r1[0], r1[1], r0[1]))
        f.smooth = True


def rim_close(bm, outer, inner, keep):
    """Bridge the open edges of two parallel partial shells (same topology) into a closed solid."""
    bm.edges.ensure_lookup_table()
    def boundary(rings):
        vs = set(v for r, _ in rings for v in r)
        return [e for e in bm.edges if e.is_boundary and e.verts[0] in vs and e.verts[1] in vs]
    oi = {}
    for (ro, _), (ri, _) in zip(outer, inner):
        for a, b in zip(ro, ri):
            oi[a] = b
    for e in boundary(outer):
        a, b = e.verts
        if a in oi and b in oi:
            try:
                f = bm.faces.new((a, b, oi[b], oi[a]))
                f.smooth = False
            except ValueError:
                pass


def gas_path(z, o, side):
    """Streamline around the section at height z, offset o from the skin: upstream, around one side, downstream."""
    ring, nrm, sal, le = af_ring(clamp(z / H_AF))
    m = len(ring)
    idx = list(range(le, -1, -1)) if side > 0 else list(range(le, m))
    pts2 = [ring[i] + nrm[i] * o for i in idx]
    pts2 = pts2[::2] + [pts2[-1]]
    lead = pts2[0]
    inflow = V2(math.cos(rad(38)), math.sin(rad(38)))
    up = [lead - inflow * (0.004 + 0.032 * (1 - k / 10)) + V2(0, side * o * 0.6) * (1 - k / 10) for k in range(10)]
    tail = pts2[-1]
    outd = (pts2[-1] - pts2[-3]).normalized()
    dn = [tail + outd * 0.003 * k for k in range(1, 12)]
    return [Vector((p.x, p.y, z)) for p in up + pts2 + dn]


HOLE_ROWS = [(0.0011, 0.0024, 0.0), (-0.0002, 0.0024, 0.0012), (-0.0015, 0.0024, 0.0),
             (0.0072, 0.0028, 0.0007), (-0.0062, 0.0026, 0.0004), (-0.0135, 0.0026, 0.0017)]
HOLE_R = 0.00034


# ----------------------------------------------------------------------------------------------- the disc

def disc_profile():
    rb = R_P - 0.040
    pts = [V2(-0.017, rb + 0.0005), V2(-0.0175, rb - 0.010), V2(-0.007, rb - 0.030), V2(-0.0065, 0.150),
           V2(-0.030, 0.118), V2(-0.031, 0.072), V2(0.031, 0.072), V2(0.030, 0.118), V2(0.0065, 0.150),
           V2(0.007, rb - 0.030), V2(0.0175, rb - 0.010), V2(0.017, rb + 0.0005)]
    return fillet(pts, [0.001, 0.008, 0.02, 0.02, 0.006, 0.003, 0.003, 0.006, 0.02, 0.02, 0.008, 0.001], 8)


def build_disc(M, name, me_blade, rxr, skip_hero=False, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    """HP turbine disc in its own frame (axis x): web + hub lathe, fir-tree posts, bolt heads, 64 blades."""
    root = empty(name, loc, parent)
    root.rotation_mode = "XYZ"
    root.rotation_euler = rot
    body = lathe(name + "_body", disc_profile(), M["disc"], n=256, parent=root, step=0.0012)
    bm = bmesh.new()
    rx0, rx1 = rxr
    gap = 0.00025
    r_bot, r_top = R_P - 0.0410, R_P - 0.0038
    for i in range(N_BL):
        phc = 2 * math.pi * (i + 0.5) / N_BL
        prof = []
        rs = [lerp(r_bot, r_top, k / 60) for k in range(61)]
        for r in rs:
            zd = Z_ROOT0 - (r - R_P)
            w = 0.0045 if zd < 0 else root_hw(min(zd, Z_ROOT0 - Z_ROOT1))
            hw = math.pi * r / N_BL - w - gap
            prof.append(V2(hw, r))
        prof = prof + [V2(-p.x, p.y) for p in prof[::-1]]
        R = Matrix.Rotation(phc, 4, "X")
        bm_extrude(bm, prof, rx0 - 0.0006, rx1 + 0.0006, ch=0.0004, M=R,
                   map2=lambda x, p: Vector((x, p.y * math.sin(p.x / p.y), p.y * math.cos(p.x / p.y))))
    # bolt heads on the hub face, both sides
    for side in (-1, 1):
        for k in range(18):
            a = 2 * math.pi * k / 18
            Mb = Matrix.Rotation(a, 4, "X") @ Matrix.Translation((side * 0.0315, 0, 0.095)) @ \
                Matrix.Rotation(rad(90), 4, "Y")
            bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0052, radius2=0.0052, depth=0.006,
                                  matrix=Mb)
    posts = obj_from_bm(name + "_posts", bm, M["disc"], root)
    weighted(posts)
    blades = []
    for i in range(N_BL):
        if skip_hero and i == 0:
            continue
        b = mesh_obj(f"{name}_b{i:02d}", me_blade, None, root)
        b.matrix_basis = Matrix.Rotation(2 * math.pi * i / N_BL, 4, "X") @ Matrix.Translation((0, 0, R_P))
        blades.append(b)
    return root, body, posts, blades


def gas_disc(M, name, parent, n=110, seed=3):
    """Hot gas streaks through the blade row (disc frame, not spinning): short swirling arcs between the blades."""
    rnd = random.Random(seed)
    bm, at = bmesh.new(), {}
    for k in range(n):
        r = R_P + rnd.uniform(0.004, H_AF - 0.004)
        a0 = rnd.uniform(0, 2 * math.pi)
        pts = []
        for j in range(24):
            g = j / 23
            x = lerp(-0.07, 0.07, g)
            a = a0 + 0.55 * math.tanh((x) / 0.02)
            pts.append(Vector((x, r * math.cos(a), r * math.sin(a))))
        bm_tube(bm, pts, 0.00042, 6, attrs=at, phase=rnd.random())
    return bm_to_obj(name, bm, at, M["gasD"], parent)


# ----------------------------------------------------------------------------------------------- the engine

def bm_airfoil_blade(bm, x_c, r0, r1, chord, stagger, theta0, tau=0.07, camber=0.06, sweep=0.0, nsp=8, nch=10,
                     at=None, cf=False):
    """A thin cambered blade wrapped on cylinders between radii r0 and r1 (engine stages and the fan)."""
    rings = []
    for j in range(nsp + 1):
        s = j / nsp
        r = lerp(r0, r1, s)
        c = chord(s) if callable(chord) else chord
        st = stagger(s) if callable(stagger) else stagger
        sw = sweep * s * s
        pts = []
        for side in (1, -1):
            ks = range(nch) if side > 0 else range(nch - 1, 0, -1)
            for k in ks:
                t = 0.5 * (1 - math.cos(math.pi * k / (nch - 1)))
                yc = camber * c * 4 * t * (1 - t)
                yt = 5 * tau * (0.2969 * math.sqrt(t) - 0.1260 * t - 0.3516 * t * t + 0.2843 * t ** 3
                                - 0.1015 * t ** 4) * c
                pts.append((t, V2((t - 0.4) * c, yc + side * yt)))
        R = Matrix.Rotation(st, 2)
        ring = []
        for t, p in pts:
            q = R @ p
            a = theta0 + q.y / r
            v = bm.verts.new((x_c + q.x + sw, r * math.cos(a), r * math.sin(a)))
            if at is not None:
                at.setdefault("cf", {})[v] = t
                at.setdefault("sp", {})[v] = s
            ring.append(v)
        rings.append(ring)
    m = len(rings[0])
    for r0_, r1_ in zip(rings, rings[1:]):
        for i in range(m):
            f = bm.faces.new((r0_[i], r0_[(i + 1) % m], r1_[(i + 1) % m], r1_[i]))
            f.smooth = True
    f = bm.faces.new(rings[-1])
    f.smooth = False


def stage_rows(bm, stages, at=None):
    for x, r0, r1, n, c, st, cam in stages:
        for i in range(n):
            bm_airfoil_blade(bm, x, r0, r1, c, rad(st), 2 * math.pi * i / n, tau=0.09, camber=cam, nsp=4, nch=7,
                             at=at)


CUT = (rad(92), rad(212))         # the cutaway sector (angle 0 = +y, 90 = +z): faces the camera side (-y) and up


def build_engine(M, me_blade, rxr):
    G = {}
    root = empty("Engine", (0, 0, ZE))
    G["root"] = root
    # nacelle (outer skin + intake lip + inner fan-case wall), one closed profile
    nac = [V2(-2.30, 1.36), V2(-2.34, 1.42), V2(-2.20, 1.53), V2(-1.70, 1.585), V2(-0.9, 1.57), V2(0.0, 1.47),
           V2(0.62, 1.31), V2(0.60, 1.285), V2(-0.2, 1.30), V2(-1.2, 1.33), V2(-1.95, 1.33), V2(-2.22, 1.33)]
    nac = fillet(nac, [0.04, 0.05, 0.3, 0.6, 0.6, 0.5, 0.012, 0.012, 0.3, 0.3, 0.2, 0.05], 10)
    a0, a1 = CUT
    G["nac"] = lathe("Nacelle", nac, M["paint"], a1, a0 + 2 * math.pi, 200, root, step=0.03)
    G["nacCut"] = lathe("NacelleCut", nac, M["paint"], a0, a1, 70, root, step=0.03)
    # core cowl: splitter lip, outer cowl, core nozzle; inner wall = the core case
    cow = [V2(-1.30, 0.70), V2(-1.18, 0.74), V2(-0.5, 0.82), V2(0.5, 0.86), V2(1.25, 0.76), V2(1.85, 0.60),
           V2(1.84, 0.575), V2(1.2, 0.66), V2(0.9, 0.63), V2(0.1, 0.62), V2(-0.4, 0.62), V2(-1.1, 0.66),
           V2(-1.26, 0.68)]
    cow = fillet(cow, [0.02, 0.1, 0.5, 0.5, 0.5, 0.01, 0.01, 0.1, 0.1, 0.1, 0.1, 0.06, 0.02], 10)
    G["cowl"] = lathe("Cowl", cow, M["cowl"], a1, a0 + 2 * math.pi, 200, root, step=0.03)
    G["cowlCut"] = lathe("CowlCut", cow, M["cowl"], a0, a1, 70, root, step=0.03)
    # cut faces show as polished metal: caps get their own material slot
    for k in ("nac", "cowl"):
        ob = G[k]
        ob.data.materials.append(M["cutface"])
        for p in ob.data.polygons:
            if not p.use_smooth:
                p.material_index = 1
    # spinner with a painted spiral, fan hub
    spn = [V2(-2.05, 0.0), V2(-1.98, 0.12), V2(-1.80, 0.30), V2(-1.55, 0.43), V2(-1.35, 0.45), V2(-1.35, 0.0)]
    spn = fillet(spn, [0.0, 0.1, 0.25, 0.15, 0.02, 0.0], 10)
    G["spinner"] = lathe("Spinner", spn, M["spinner"], n=160, parent=root, step=0.015)
    # fan: 20 wide-chord swept blades (carbon with a titanium leading edge)
    fan = empty("Fan", (0, 0, 0), root)
    fan.rotation_mode = "XYZ"
    bm, at = bmesh.new(), {}
    for i in range(20):
        bm_airfoil_blade(bm, -1.62, 0.43, 1.315, lambda s: lerp(0.34, 0.56, s), lambda s: rad(lerp(28, 64, s)),
                         2 * math.pi * i / 20, tau=0.05, camber=0.05, sweep=0.10, nsp=16, nch=14, at=at)
    G["fanblades"] = bm_to_obj("FanBlades", bm, at, M["fan"], fan)
    G["fan"] = fan
    # spool: compressor + turbine rows on one shaft (rotates together)
    spool = empty("Spool", (0, 0, 0), root)
    spool.rotation_mode = "XYZ"
    G["spool"] = spool
    comp = []
    for k in range(10):
        x = lerp(-1.05, -0.05, k / 9)
        r0 = lerp(0.36, 0.44, k / 9)
        r1 = lerp(0.60, 0.50, k / 9)
        comp.append((x, r0, r1, int(lerp(44, 70, k / 9)), lerp(0.075, 0.045, k / 9), lerp(48, 40, k / 9), 0.08))
    bm, at = bmesh.new(), {}
    stage_rows(bm, comp, at)
    G["comp"] = bm_to_obj("Compressor", bm, at, M["ti"], spool)
    drum = [V2(-1.12, 0.30), V2(-1.10, 0.36), V2(0.0, 0.44), V2(0.05, 0.30)]
    lathe("Drum", fillet(drum, 0.01, 4), M["steel"], n=160, parent=spool, step=0.02)
    lpt = []
    for k in range(6):
        x = lerp(0.82, 1.55, k / 5)
        lpt.append((x, lerp(0.34, 0.36, k / 5), lerp(0.44, 0.60, k / 5), int(lerp(80, 110, k / 5)), 0.06, -50, -0.10))
    bm, at = bmesh.new(), {}
    stage_rows(bm, lpt, at)
    G["lpt"] = bm_to_obj("LPT", bm, at, M["nickel_dark"], spool)
    shaft = [V2(-1.3, 0.0), V2(-1.3, 0.12), V2(1.9, 0.12), V2(1.9, 0.0)]
    lathe("Shaft", shaft, M["steel"], n=64, parent=spool)
    hp, body, posts, blades = build_disc(M, "EngDisc", me_blade, rxr, parent=spool, loc=(0.58, 0, 0))
    G["hpdisc"] = hp
    # combustor: annular flame tube cut open on the same sector, with a glowing liner
    cmb = [V2(0.04, 0.42), V2(0.09, 0.51), V2(0.45, 0.49), V2(0.51, 0.41), V2(0.47, 0.33), V2(0.12, 0.35)]
    G["comb"] = lathe("Combustor", fillet(cmb, 0.03, 6), M["comb"], a1, a0 + 2 * math.pi, 160, root, step=0.01)
    lin_ = [V2(0.11, 0.425), V2(0.14, 0.475), V2(0.43, 0.465), V2(0.47, 0.41), V2(0.44, 0.355), V2(0.15, 0.37)]
    G["flame"] = lathe("Flame", fillet(lin_, 0.02, 6), M["flame"], a1, a0 + 2 * math.pi, 160, root, step=0.01)
    G["gas"] = gas_disc(M, "EngGas", root, 120, 9)
    G["gas"].location = (0.58, 0, 0)
    # exhaust plug
    plug = [V2(1.55, 0.0), V2(1.55, 0.36), V2(1.9, 0.355), V2(2.55, 0.12), V2(2.75, 0.0)]
    lathe("Plug", fillet(plug, [0, 0.03, 0.2, 0.3, 0], 8), M["plug"], n=160, parent=root, step=0.02)
    return G


# ----------------------------------------------------------------------------------------------- studios

def floor(name, c, r, mat):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=96, radius=r)
    ob = obj_from_bm(name, bm, mat, None, c)
    return ob


def area(name, loc, target, size, size_y, col, energy, shape="RECTANGLE", spread=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size = size
    ld.size_y = size_y
    ld.color = lin(col)
    ld.energy = energy
    if spread is not None:
        try:
            ld.spread = spread
        except Exception:
            pass
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    return ob


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


# ----------------------------------------------------------------------------------------------- shot helpers

def put(S, idb, path, v, idx=0, const=False):
    S[(idb, path, idx)] = (float(v), const)


def nv(m, name="S"):
    return m.node_tree, f'nodes["{name}"].outputs[0].default_value'


def mset(_S, _m, **kw):
    for k, v in kw.items():
        put(_S, *nv(_m, k), v)


def cam(S, eye, tgt, lens=50, roll=0.0, fstop=8.0, focus=None, clip=0.01, shake=0.0, t=0.0):
    eye, tgt = Vector(eye), Vector(tgt)
    d = tgt - eye
    yaw = pitch = 0.0
    if shake:
        yaw += rad(shake) * (math.sin(t * 1.7) * 0.6 + math.sin(t * 3.1 + 1.0) * 0.4)
        pitch += rad(shake) * (math.sin(t * 2.3 + 2.0) * 0.6 + math.sin(t * 0.9) * 0.4)
    if yaw or pitch:
        d = Matrix.Rotation(yaw, 3, "Z") @ d
        side = d.cross(Vector((0, 0, 1)))
        if side.length > 1e-6:
            d = Matrix.Rotation(pitch, 3, side.normalized()) @ d
    q = d.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), roll)
    S["cam"] = (eye, q, lens, fstop, focus if focus is not None else (tgt - eye).length, clip)


def label(S, name, p):
    S.setdefault("labels", {})[name] = Vector(p)


def hide(S, ob, h=True):
    put(S, ob, "hide_render", 1 if h else 0, const=True)


def disc_matrix(spin):
    return Matrix.Translation(DC) @ Matrix.Rotation(rad(90), 4, "Z") @ Matrix.Rotation(spin, 4, "X")


def hero_pose(S, W, Mh):
    loc, q, sc = Mh.decompose()
    S["hero"] = Mh
    for k in range(3):
        put(S, W["hero"], "location", loc[k], k)
    for k in range(4):
        put(S, W["hero"], "rotation_quaternion", q[k], k)


def hero_slot(S, W, spin=0.0, lift=0.0):
    hero_pose(S, W, Matrix.Translation((0, 0, lift)) @ disc_matrix(spin) @ Matrix.Translation((0, 0, R_P)))


B0 = Vector((200, 0, 0))                # blade studio: the hero alone in a pool of light, no floor, no neighbours
HOVER = B0 + Vector((0, 0, 0.70))


def chord_normal_angle():
    """blade-frame angle of the normal to the mid-span chord, on the concave (pressure) side"""
    ring, nrm, sal, le = af_ring(0.5)
    cv = ring[0] - ring[le]
    mid = ring[le // 2]                  # a point on the suction surface
    n = Vector((-cv.y, cv.x, 0)).normalized()
    if (Vector((mid.x, mid.y, 0)) - Vector((ring[le].x, ring[le].y, 0))).dot(n) > 0:
        n = -n                           # point away from the convex side
    return math.atan2(n.y, n.x)


PHI = chord_normal_angle()


def hero_float(S, W, yaw=0.0, tilt=0.0, t=0.0, bob=True):
    z = 0.0012 * math.sin(t * 1.3) if bob else 0.0
    Mh = Matrix.Translation(HOVER + Vector((0, 0, z))) @ Matrix.Rotation(rad(90) + yaw, 4, "Z") @ \
        Matrix.Rotation(tilt, 4, "X")
    hero_pose(S, W, Mh)


def face(az, off=0.0, side=1):
    """hero yaw that turns the blade's pressure side (side=1) or suction side (-1) to a camera at azimuth az, plus
    off degrees"""
    base = PHI if side > 0 else PHI + math.pi
    return rad(az) - rad(90) - base - rad(90) + rad(off)


def bcam(S, az, el, dist, lens=85, tz=-0.004, fstop=9.0, focus=None, shake=0.0, t=0.0, c=None):
    """camera on the hero at the blade studio: azimuth az (deg, 0 = from -y), elevation el, distance dist"""
    c = (HOVER + Vector((0, 0, tz))) if c is None else c
    eye = c + Matrix.Rotation(rad(az), 3, "Z") @ Vector((0, -dist * math.cos(rad(el)), dist * math.sin(rad(el))))
    cam(S, eye, c, lens=lens, fstop=fstop, focus=focus, shake=shake, t=t)


def bw(S, p):
    """blade-frame point -> world (current hero pose)"""
    return S["hero"] @ Vector(p)


def spin_disc(S, W, a):
    put(S, W["disc"], "rotation_euler", a, 0)


def lights(S, W, which, k=1.0):
    for name, ob, e in W["lights"]:
        on = name.startswith(which)
        put(S, ob.data, "energy", e * k if on else 0.0)
    for name, m, s in W["cards"]:
        put(S, *nv(m), s * k if name == which else 0.0)


def thermal_on(S, W, tb_hero=0.74, tb_disc=0.74, disc=0.4, k=1.0):
    M = W["M"]
    mset(S, M["bladeH"], TH=k, TB=tb_hero)
    mset(S, M["bladeD"], TH=k, TB=tb_disc)
    mset(S, M["disc"], TH=k, TB=disc)
    put(S, *nv_world(W, "W"), lerp(1.0, 0.2, k))


def nv_world(W, name):
    return W["world"].node_tree, f'nodes["{name}"].outputs[0].default_value'


def defaults(t, S, W):
    M, G, P = W["M"], W["G"], W["P"]
    lights(S, W, "none")
    put(S, *nv_world(W, "W"), 1.0)
    put(S, *nv_world(W, "A"), 0.18)
    put(S, G["fan"], "rotation_euler", t * 1.9, 0)
    put(S, G["spool"], "rotation_euler", t * 3.2, 0)
    for k in ("nacCut", "cowlCut"):
        for i in range(3):
            put(S, G[k], "location", 0.0, i)
        hide(S, G[k], False)
    spin_disc(S, W, 0.0)
    mset(S, M["bladeH"], G=0.0, GB=0.0, CK=0.0, SM=0.0, SF=-0.07, TH=0.0, TB=0.62, XA=0.0, XZ=0.07, FC=0.0, HT=1.0)
    mset(S, M["bladeD"], TH=0.0, TB=0.62, FC=0.0)
    mset(S, M["disc"], TH=0.0, TB=0.35)
    mset(S, M["tbc"], HF=0.0, TH=0.0)
    mset(S, M["gas"], S=0.0, P=t * 1.1)
    mset(S, M["gasD"], S=0.0, P=t * 1.6)
    mset(S, M["film"], S=0.0, FG=0.0, P=t * 1.2)
    mset(S, M["chan"], S=0.0, CF=0.0, P=t * 1.4)
    mset(S, M["blanket"], S=0.0)
    mset(S, M["flame"], S=3.0)
    for k in ("chan", "film", "blanket", "tbcS", "tbcP", "gasN", "gasF", "selector"):
        hide(S, P[k])
    for k in ("tbcS", "tbcP"):
        for i in range(3):
            put(S, P[k], "location", 0.0, i)
            put(S, P[k], "rotation_euler", 0.0, i)
    put(S, W["hero"], "scale", 1.0, 2)
    hide(S, W["discgas"])
    hide(S, G["gas"])
    hero_slot(S, W)


def shots(W):
    M, G, P = W["M"], W["G"], W["P"]
    L = []
    EC = Vector((0, 0, ZE))
    AZ = -24                              # the standard hero azimuth: every blade beat starts from this framing

    def opened(S, k):
        d = Vector((0, -0.35, 1.0)).normalized()
        for key in ("nacCut", "cowlCut"):
            for i in range(3):
                put(S, G[key], "location", d[i] * 4.5 * k, i)
            hide(S, G[key], k > 0.98)

    def disc_cam(S, t, t0, t1, a0, a1, d0, d1):
        """the whole disc, three-quarter front, with room around it"""
        u = ss(seg(t, t0, t1))
        a = rad(lerp(a0, a1, u))
        d = lerp(d0, d1, u)
        c = DC + V(0, 0, -0.07)
        eye = c + Matrix.Rotation(a, 3, "Z") @ V(0, -d, d * 0.24)
        cam(S, eye, c, lens=42, fstop=8)

    # --- 1: jet engine blades spin in gas up to 200 C above their melting point ------------------------------------
    def S1a(t, S):   # the whole engine, front three-quarter, fan turning
        lights(S, W, "E")
        u = seg(t, 0.0, 1.25)
        a = rad(lerp(-6, 0, u))
        eye = EC + Matrix.Rotation(a, 3, "Z") @ Vector((-9.4, -5.6, 0.9 + 0.2 * u))
        cam(S, eye, EC + V(-1.25, 0, -0.5), lens=42, fstop=8, clip=0.05)
    L.append((0.0, 1.25, S1a))

    def S1b(t, S):   # the cutaway lifts away: the core inside, the turbine glowing at the back
        lights(S, W, "E")
        u = seg(t, 1.25, 2.35)
        opened(S, ein(seg(t, 1.3, 2.1)))
        hide(S, G["gas"], False)
        mset(S, M["gasD"], S=1.0)
        eye = EC + V(lerp(-0.4, 0.0, u), lerp(-10.6, -10.0, u), lerp(1.6, 1.7, u))
        cam(S, eye, EC + V(-0.45, 0, -0.45), lens=32, fstop=8, clip=0.05)
    L.append((1.25, 2.35, S1b))

    def S1c(t, S):   # the turbine disc on its own, the whole ring of blades turning
        lights(S, W, "D")
        a = t * 0.5
        spin_disc(S, W, a)
        hero_slot(S, W, a)
        disc_cam(S, t, 2.35, 3.5, -34, -28, 1.75, 1.6)
    L.append((2.35, 3.5, S1c))

    def S1d(t, S):   # same disc in thermal view: white-hot gas streaming through, blades glowing orange
        lights(S, W, "D", 0.12)
        a = t * 0.5
        spin_disc(S, W, a)
        hero_slot(S, W, a)
        hide(S, W["discgas"], True)
        thermal_on(S, W, 0.76, 0.76, 0.22)
        disc_cam(S, t, 3.5, 4.85, -28, -22, 1.6, 1.5)
    L.append((3.5, 4.85, S1d))

    # --- 2: each palm-sized blade makes the power of a Formula One car --------------------------------------------
    def S2a(t, S):   # one blade slides up out of its slot
        lights(S, W, "D")
        lift = 0.10 * ss(seg(t, 4.95, 6.2))
        hero_slot(S, W, 0.0, lift)
        u = seg(t, 4.85, 6.35)
        c = DC + V(0, 0, R_P + 0.012 + lift * 0.55)
        eye = c + Matrix.Rotation(rad(lerp(-34, -26, u)), 3, "Z") @ V(0, -0.40, 0.12)
        cam(S, eye, c, lens=70, fstop=10)
    L.append((4.85, 6.35, S2a))

    def S2b(t, S):   # the blade alone in the light, turning
        lights(S, W, "B")
        u = seg(t, 6.35, 8.15)
        hero_float(S, W, yaw=face(AZ, lerp(-60, -35, u)), t=t)
        bcam(S, AZ, 16, lerp(0.40, 0.37, u))
        label(S, "blade", bw(S, V(0.0, 0.0, H_AF - 0.004)))
    L.append((6.35, 8.15, S2b))

    # --- 3: normal metal is a patchwork of tiny crystals; heat and pull crack it along the seams -------------------
    def S3a(t, S):   # same framing: the blade turns into a patchwork of crystal grains
        lights(S, W, "B")
        u = seg(t, 8.15, 9.65)
        hero_float(S, W, yaw=face(AZ, lerp(-35, -28, u)), t=t)
        mset(S, M["bladeH"], G=ss(seg(t, 8.25, 9.0)), HT=0.4)
        bcam(S, AZ, 16, lerp(0.37, 0.32, ss(u)))
        label(S, "grains", bw(S, V(0.0, 0.0, 0.03)) + (S["hero"].to_3x3() @ Vector((0, 0, 0))))
    L.append((8.15, 9.65, S3a))

    def S3b(t, S):   # closer on the airfoil: the grain boundaries heat up and glow
        lights(S, W, "B", lerp(1.0, 0.55, seg(t, 9.9, 10.9)))
        u = seg(t, 9.65, 11.1)
        hero_float(S, W, yaw=face(AZ, -28), t=t, bob=False)
        mset(S, M["bladeH"], G=1.0, GB=ss(seg(t, 9.8, 10.8)), HT=0.4)
        bcam(S, AZ, 10, lerp(0.24, 0.22, u), tz=0.024)
    L.append((9.65, 11.1, S3b))

    def S3c(t, S):   # heat and pull: the blade strains, a crack runs along the boundaries
        lights(S, W, "B", 0.55)
        hero_float(S, W, yaw=face(AZ, -28), t=t, bob=False)
        jit = 0.0025 * math.sin(t * 61) * seg(t, 11.3, 11.6)
        put(S, W["hero"], "scale", 1.0 + 0.02 * ss(seg(t, 11.2, 12.0)) + jit, 2)
        mset(S, M["bladeH"], G=1.0, GB=0.7, CK=ss(seg(t, 11.55, 12.9)), HT=0.4)
        put(S, *nv_world(W, "W"), 0.8)
        bcam(S, AZ, 10, 0.22, tz=0.024, shake=0.35 * seg(t, 11.3, 11.7), t=t)
        label(S, "crack", bw(S, af_point(0.0, 0.0302)[0]))
    L.append((11.1, 13.4, S3c))

    # --- 4: so each blade is grown as one single crystal. No seams. -----------------------------------------------
    def S4a(t, S):   # the whole blade with its spiral grain selector: one crystal grows up from the bottom
        lights(S, W, "B", 0.6)
        hero_float(S, W, yaw=face(AZ, -30), t=t, bob=False)
        hide(S, P["selector"], False)
        sf = lerp(Z_ROOT1 - 0.036, H_AF + 0.003, ss(seg(t, 13.45, 15.35)))
        mset(S, M["bladeH"], SM=1.0, SF=sf, HT=0.0)
        bcam(S, AZ, 10, 0.50, tz=-0.012)
        label(S, "crystal", bw(S, V(0, 0, clamp(sf, Z_ROOT1, H_AF))))
    L.append((13.4, 15.5, S4a))

    def S4b(t, S):   # the finished blade: one flawless surface, a highlight sweeps across it
        lights(S, W, "B")
        u = seg(t, 15.5, 17.55)
        hero_float(S, W, yaw=face(AZ, lerp(-70, -20, u)), t=t)
        mset(S, M["bladeH"], HT=0.6)
        bcam(S, AZ, 16, lerp(0.39, 0.36, u))
    L.append((15.5, 17.55, S4b))

    # --- 5: inside, cool air snakes through hidden channels --------------------------------------------------------
    def S5a(t, S):   # x-ray wipe from the tip down reveals the hidden passage
        lights(S, W, "B", 0.4)
        put(S, *nv_world(W, "W"), 0.6)
        hero_float(S, W, yaw=face(AZ, -20), t=t)
        hide(S, P["chan"], False)
        mset(S, M["chan"], S=1.0, CF=0.35)
        mset(S, M["bladeH"], XA=1.0, XZ=lerp(H_AF + 0.003, Z_ROOT1 - 0.004, ss(seg(t, 17.6, 18.6))))
        bcam(S, AZ, 12, 0.40)
    L.append((17.55, 18.75, S5a))

    def S5b(t, S):   # cool air races up and down the passage
        lights(S, W, "B", 0.4)
        put(S, *nv_world(W, "W"), 0.6)
        u = seg(t, 18.75, 19.95)
        hero_float(S, W, yaw=face(AZ, lerp(-20, -8, u)), t=t)
        hide(S, P["chan"], False)
        mset(S, M["chan"], S=1.0, CF=1.0)
        mset(S, M["bladeH"], XA=1.0, XZ=Z_ROOT1 - 0.006)
        bcam(S, AZ, 12, lerp(0.40, 0.34, ss(u)))
        label(S, "chan", bw(S, camber_pt(0.20, 0.036)[0]))
    L.append((18.75, 19.95, S5b))

    # --- 6: then streams from tiny holes to blanket the surface --------------------------------------------------
    def S6a(t, S):   # closer on the leading edge: cool air streams out of every hole
        lights(S, W, "B", 0.8)
        hero_float(S, W, yaw=face(AZ, -35), t=t, bob=False)
        hide(S, P["film"], False)
        mset(S, M["bladeH"], FC=ss(seg(t, 20.0, 20.4)), HT=0.6)
        mset(S, M["film"], S=1.0, FG=ss(seg(t, 20.1, 21.1)))
        bcam(S, AZ, 14, lerp(0.30, 0.27, seg(t, 19.95, 21.45)), tz=0.024)
        label(S, "holes", bw(S, af_point(0.0011, 0.040)[0]))
    L.append((19.95, 21.45, S6a))

    def S6b(t, S):   # the whole blade wrapped in a film of cool air; hot gas streams past outside it
        lights(S, W, "B", 0.55)
        put(S, *nv_world(W, "W"), 0.7)
        u = seg(t, 21.45, 23.1)
        hero_float(S, W, yaw=face(AZ, lerp(-30, -15, u)), t=t)
        for k in ("film", "blanket", "gasF"):
            hide(S, P[k], False)
        mset(S, M["bladeH"], FC=1.0, HT=0.6)
        mset(S, M["film"], S=1.0, FG=1.0)
        mset(S, M["blanket"], S=ss(seg(t, 21.5, 22.3)))
        mset(S, M["gas"], S=0.8)
        bcam(S, AZ, 14, lerp(0.40, 0.37, u), tz=0.0)
        label(S, "film", bw(S, af_point(0.010, 0.046, off=0.0006)[0]))
    L.append((21.45, 23.1, S6b))

    # --- 7: on top, a ceramic coat holds back more heat ------------------------------------------------------------
    def shells(S, k_open):
        for key, sgn in (("tbcS", 1), ("tbcP", -1)):
            hide(S, P[key], False)
            put(S, P[key], "location", sgn * 0.016 * k_open, 1)
            put(S, P[key], "location", 0.006 * k_open, 2)
            put(S, P[key], "rotation_euler", sgn * rad(-10) * k_open, 0)

    def S7a(t, S):   # the coated blade; the ceramic coat lifts away from the metal
        lights(S, W, "B")
        u = seg(t, 23.1, 24.55)
        hero_float(S, W, yaw=face(AZ, lerp(60, 75, u)), t=t)
        shells(S, ss(seg(t, 23.5, 24.4)))
        bcam(S, AZ, 14, 0.42, tz=0.0)
        label(S, "tbc", bw(S, af_point(0.009, 0.044, off=0.0008)[0]))
    L.append((23.1, 24.55, S7a))

    def S7b(t, S):   # the outer face of the coat takes the heat, the metal inside stays cool
        lights(S, W, "B", 0.6)
        u = seg(t, 24.55, 26.0)
        hero_float(S, W, yaw=face(AZ, lerp(75, 95, u)), t=t)
        shells(S, 1.0)
        mset(S, M["tbc"], HF=ss(seg(t, 24.6, 25.3)))
        bcam(S, AZ, 16, lerp(0.40, 0.36, u), tz=0.0)
    L.append((24.55, 26.0, S7b))

    # --- 8: so the metal never reaches its melting point -----------------------------------------------------------
    def S8a(t, S):   # coat on, the blade drops home into the disc
        lights(S, W, "D")
        lift = 0.10 * (1 - ss(seg(t, 26.1, 27.0)))
        hero_slot(S, W, 0.0, lift)
        c = DC + V(0, 0, R_P + 0.012 + lift * 0.55)
        eye = c + Matrix.Rotation(rad(-26), 3, "Z") @ V(0, -0.40, 0.12)
        cam(S, eye, c, lens=70, fstop=10)
    L.append((26.0, 27.3, S8a))

    def S8b(t, S):   # thermal payoff: the same disc, white-hot gas, the blades now well below the melting point
        lights(S, W, "D", 0.12)
        a = (t - 27.3) * 0.5
        spin_disc(S, W, a)
        hero_slot(S, W, a)
        hide(S, W["discgas"], True)
        mset(S, M["bladeH"], FC=1.0)
        mset(S, M["bladeD"], FC=1.0)
        thermal_on(S, W, 0.58, 0.58, 0.2)
        disc_cam(S, t, 27.3, 28.6, -22, -28, 1.5, 1.6)
    L.append((27.3, 28.6, S8b))

    # --- 9: follow for how the world is really engineered ----------------------------------------------------------
    def S9a(t, S):   # the open engine in profile, the core glowing
        lights(S, W, "E")
        opened(S, 1.0)
        hide(S, G["gas"], False)
        mset(S, M["gasD"], S=1.0)
        u = seg(t, 28.6, 30.3)
        eye = EC + V(lerp(0.0, 0.4, u), -10.0, lerp(1.7, 1.5, u))
        cam(S, eye, EC + V(0.0, 0, -0.45), lens=32, fstop=8, clip=0.05)
    L.append((28.6, 30.3, S9a))

    def S9b(t, S):   # the cowl closes, slow pull-back on the whole engine
        lights(S, W, "E")
        opened(S, 1.0 - ss(seg(t, 30.4, 31.2)))
        u = seg(t, 30.3, 32.0)
        a = rad(lerp(-30, -24, u))
        eye = EC + Matrix.Rotation(a, 3, "Z") @ V(-8.6 - 1.4 * eout(u), -2.8, 1.0 + 0.4 * eout(u))
        cam(S, eye, EC + V(0.4, 0, -0.55), lens=40, fstop=8, clip=0.05)
    L.append((30.3, T_END + 0.1, S9b))
    return L


# ----------------------------------------------------------------------------------------------- bake

def project(eye, q, lens, p, w=1080, h=1920):
    pc = q.inverted() @ (Vector(p) - eye)
    if pc.z >= -0.001:
        return None
    k = lens / 36.0
    u = 0.5 + (pc.x / -pc.z) * k * (h / w)
    v = 0.5 + (pc.y / -pc.z) * k
    return round(u * w, 1), round((1 - v) * h, 1)


def bake(W, labels_out):
    tracks, camk, labels = {}, [], {}
    L = shots(W)
    qprev = {}
    for i, (t0, t1, fn) in enumerate(L):
        f0 = math.ceil(t0 * FPS - 1e-6) + 1
        f1 = min(math.ceil(t1 * FPS - 1e-6), F_END)
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
            S.pop("hero", None)
            c = S.pop("cam")
            camk.append((f,) + c)
            lb = S.pop("labels", {})
            if f == int(f):
                for name, p in lb.items():
                    xy = project(c[0], c[1], c[2], p)
                    if xy:
                        labels.setdefault(name, []).append([int(f), *xy])
            hq = [S.get((W["hero"], "rotation_quaternion", k)) for k in range(4)]
            if all(hq):
                q = Quaternion([v for v, _ in hq])
                pq = qprev.get("hero")
                if pq is not None and q.dot(pq) < 0:
                    for k in range(4):
                        S[(W["hero"], "rotation_quaternion", k)] = (-q[k], False)
                    q = -q
                qprev["hero"] = q
            for k, (v, const) in S.items():
                tracks.setdefault(k, []).append((f, v, const))
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

def cycles_settings(scn, samples):
    scn.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA", "HIP"):
            try:
                pr.compute_device_type = kind
                pr.get_devices()
                gpus = [d for d in pr.devices if d.type == kind]
                if gpus:
                    for d in pr.devices:
                        d.use = d.type == kind
                    scn.cycles.device = "GPU"
                    print("GPU", kind, [d.name for d in gpus])
                    break
            except TypeError:
                pass
    except Exception as e:
        print("no gpu", e)
    cy = scn.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.015
    cy.use_denoising = True
    try:
        cy.denoiser = "OPTIX" if scn.cycles.device == "GPU" else "OPENIMAGEDENOISE"
        cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    except Exception as e:
        print("skip denoise opt", e)
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 6
    cy.transmission_bounces, cy.transparent_max_bounces = 8, 32
    cy.sample_clamp_indirect = 8.0
    cy.caustics_reflective = cy.caustics_refractive = False
    scn.render.use_persistent_data = True
    for ob in bpy.data.objects:            # Cycles area lights reflect on their own: the Eevee reflection cards go
        if ob.name.startswith("Card"):
            ob.hide_render = True
            ob.animation_data_clear()


def render_settings(scn, h=1920, samples=64):
    if "--eevee" not in sys.argv:
        cycles_settings(scn, samples)
    else:
        scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_y = h
    scn.render.resolution_x = round(h * 9 / 16 / 2) * 2
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    ee = scn.eevee
    ee.taa_render_samples = samples
    for k, v in (("use_raytracing", True), ("use_shadows", True), ("use_fast_gi", True), ("motion_blur_steps", 1),
                 ("shadow_ray_count", 2), ("shadow_step_count", 10), ("use_shadow_jitter_viewport", True),
                 ("fast_gi_distance", 0.5), ("use_bokeh_jittered", True), ("bokeh_overblur", 3.0)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print("skip", k, e)
    try:
        ee.ray_tracing_options.resolution_scale = "1"
        ee.ray_tracing_options.trace_max_roughness = 0.6
    except Exception as e:
        print("skip rt", e)
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.5
    scn.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scn.view_settings.look = look
            break
        except TypeError:
            pass
    scn.view_settings.exposure = 0.0
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.compression = 15


def card(name, light_ob, mat, sx, sy):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
    ob = obj_from_bm(name, bm, mat)
    ob.location = light_ob.location + (light_ob.rotation_quaternion @ Vector((0, 0, 1))) * 0.02
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = light_ob.rotation_quaternion
    for k in ("visible_camera", "visible_shadow"):
        try:
            setattr(ob, k, False)
        except Exception:
            pass
    return ob


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    M = materials()
    world = studio_world()
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "AUTO"
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_end = 400
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    me_blade, rxr = blade_mesh("Blade")
    me_blade.materials.append(M["bladeD"])
    G = build_engine(M, me_blade, rxr)
    floor("FloorE", E0, 9.0, M["floorE"])
    # disc studio: disc on an axle, a slim column behind, the hero blade
    disc, body, posts, blades = build_disc(M, "Disc", me_blade, rxr, skip_hero=True, loc=DC, rot=(0, 0, rad(90)))
    ax = cyl("Axle", 0.06, 0.34, DC + V(0, 0.12, 0), M["steel"], n=96)
    ax.rotation_euler = (rad(90), 0, 0)
    col = cyl("Column", 0.045, DC.z - 0.03, D0 + V(0, 0.27, (DC.z - 0.03) / 2), M["paint"], n=96)
    bevel_mod = col.modifiers.new("B", "BEVEL")
    bevel_mod.width, bevel_mod.segments = 0.006, 4
    weighted(col)
    floor("FloorD", D0, 2.2, M["floorD"])
    gr = empty("DiscGasRoot", DC)
    gr.rotation_euler = (0, 0, rad(90))
    dg = gas_disc(M, "DiscGas", gr)
    floor("FloorB", HOVER - V(0, 0, 0.10), 1.2, M["floorB"])
    hero = mesh_obj("Hero", me_blade, None)
    hero.rotation_mode = "QUATERNION"
    hero.material_slots[0].link = "OBJECT"
    hero.material_slots[0].material = M["bladeH"]
    P = build_blade_parts(M, me_blade, hero)
    for k in ("tbcS", "tbcP"):
        P[k].rotation_mode = "XYZ"
    # lights: (name, object, energy); names start with the set letter
    LT = []
    hc = DC + V(0, 0, R_P + 0.08)
    for name, loc, tgt, sx, sy, colr, e, shape in (
            ("Ekey", (-3.2, -6.2, 7.2), (0, 0, ZE), 6.0, 2.6, "#fff3e6", 5200, "RECTANGLE"),
            ("Efill", (6.5, -7.0, 2.2), (0, 0, ZE), 6.0, 6.0, "#9aa0a8", 650, "RECTANGLE"),
            ("ErimA", (6.5, 6.0, 3.6), (0, 0, ZE), 0.5, 7.0, "#fff1e2", 3400, "RECTANGLE"),
            ("ErimC", (-6.5, 6.0, 3.6), (0, 0, ZE), 0.5, 7.0, "#e6eeff", 3400, "RECTANGLE"),
            ("Etop", (0.5, 0.0, 9.5), (0, 0, ZE), 5.0, 5.0, "#ffffff", 2200, "DISK"),
            ("Dkey", tuple(D0 + V(-0.75, -1.05, 1.95)), tuple(hc), 1.2, 0.5, "#fff3e6", 170, "RECTANGLE"),
            ("Dfill", tuple(D0 + V(1.4, -1.2, 0.75)), tuple(hc), 1.5, 1.5, "#9aa0a8", 30, "RECTANGLE"),
            ("DrimA", tuple(D0 + V(0.95, 0.95, 1.15)), tuple(hc), 0.08, 1.4, "#fff1e2", 95, "RECTANGLE"),
            ("DrimC", tuple(D0 + V(-0.95, 0.95, 1.05)), tuple(hc), 0.08, 1.4, "#e6eeff", 95, "RECTANGLE"),
            ("Dtop", tuple(D0 + V(0.05, 0.25, 2.25)), tuple(hc), 0.6, 0.6, "#ffffff", 60, "DISK"),
            ("Bkey", tuple(HOVER + V(-0.9, -1.2, 1.3)), tuple(HOVER), 1.2, 0.55, "#fff3e6", 150, "RECTANGLE"),
            ("Bfill", tuple(HOVER + V(1.3, -1.1, 0.2)), tuple(HOVER), 1.2, 1.2, "#9aa0a8", 30, "RECTANGLE"),
            ("BrimA", tuple(HOVER + V(0.9, 0.9, 0.5)), tuple(HOVER), 0.06, 1.4, "#fff1e2", 150, "RECTANGLE"),
            ("BrimC", tuple(HOVER + V(-0.9, 0.9, 0.45)), tuple(HOVER), 0.06, 1.4, "#e6eeff", 150, "RECTANGLE"),
            ("Btop", tuple(HOVER + V(0.05, 0.2, 1.6)), tuple(HOVER), 0.5, 0.5, "#ffffff", 50, "DISK")):
        ob = area(name, loc, tgt, sx, sy, colr, e, shape)
        LT.append((name, ob, e))
    cards = []
    for setname, keyname, sx, sy, s in (("E", "Ekey", 6.0, 2.6, 5.0), ("D", "Dkey", 1.0, 0.45, 6.0),
                                        ("B", "Bkey", 1.0, 0.45, 6.0)):
        m = card_mat("Card" + setname, "#ffffff", s)
        lo = [o for n, o, _ in LT if n == keyname][0]
        card("Card" + setname, lo, m, sx, sy)
        cards.append((setname, m, s))
    W = dict(M=M, cam=camo, world=world, G=G, P=P, hero=hero, disc=disc, discgas=dg, lights=LT, cards=cards)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(out)), "labels.json"))
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
