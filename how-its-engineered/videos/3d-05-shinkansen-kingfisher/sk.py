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
            L = min(rnd.uniform(0.007, 0.012), max(0.003, 0.029 - abs(sa0)))
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


# showerhead at the leading edge, then rows spread over both faces (staggered, stopping short of the TE slots)
HOLE_ROWS = [(0.0011, 0.0024, 0.0), (-0.0002, 0.0024, 0.0012), (-0.0015, 0.0024, 0.0),
             (0.0072, 0.0030, 0.0007), (0.0135, 0.0032, 0.0023), (0.0200, 0.0034, 0.0010),
             (-0.0062, 0.0028, 0.0004), (-0.0110, 0.0030, 0.0019), (-0.0160, 0.0032, 0.0006),
             (-0.0210, 0.0034, 0.0021), (-0.0255, 0.0036, 0.0009)]
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
        kinds = () if os.environ.get("CPU_ONLY") else ("OPTIX", "CUDA", "HIP", "METAL")   # CPU_ONLY: leave the GPU to another job
        for kind in kinds:
            try:
                pr.compute_device_type = kind
                pr.get_devices()
                gpus = [d for d in pr.devices if d.type == kind]
                if gpus:
                    for d in pr.devices:          # an AMD card renders faster with the CPU helping
                        d.use = d.type == kind or (kind == "HIP" and d.type == "CPU")
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
        optix = bpy.context.preferences.addons["cycles"].preferences.compute_device_type == "OPTIX"
        cy.denoiser = "OPTIX" if optix and scn.cycles.device == "GPU" else "OPENIMAGEDENOISE"
        cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        cy.denoising_use_gpu = scn.cycles.device == "GPU"     # OIDN on the GPU: ~20% faster per frame on the PC
    except Exception as e:
        print("skip denoise opt", e)
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 6
    cy.transmission_bounces, cy.transparent_max_bounces = 8, 32
    cy.sample_clamp_indirect = 8.0
    cy.volume_bounces = 0
    try:
        cy.volume_step_rate = globals().get("VOL_STEP_RATE", 1.0)
    except Exception as e:
        print("skip volume step", e)
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
# ----------------------------------------------------------------------------------------------- style frames
# blender -b --factory-startup -P sf.py -- <outdir> <height> <samples> [ids]
HS = Vector((0, 300, 300))         # hot section: a turbine disc in the flame, dark world (near the origin: float precision)
HB = HS + Vector((0, 3.0, 0))      # hero blade in the gas stream


def setv(m, name, v):
    m.node_tree.nodes[name].outputs[0].default_value = v


def fire_mat(name, axis_r=True, strength=26.0):
    """combustion gas as an emissive volume: streaks stretched along +x, white-hot upstream, orange downstream"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    W = val(nt, "W", 0.0)
    nz = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 7.0
    nz.inputs["Roughness"].default_value = 0.62
    sc = node(nt, "ShaderNodeVectorMath", operation="MULTIPLY")
    sc.inputs[1].default_value = (7.0, 70.0, 70.0)
    link(nt, P, sc.inputs[0])
    link(nt, sc.outputs[0], nz.inputs["Vector"])
    link(nt, W, nz.inputs["W"])
    n = nz.outputs[0]
    if axis_r:   # an annulus round the x axis, through the blade ring
        r = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", y, y), mth(nt, "MULTIPLY", z, z)))
        band = mul(nt, sstep(nt, r, 0.262, 0.29), inv(nt, sstep(nt, r, 0.36, 0.40)))
    else:        # a slab of gas around the hero blade
        band = mul(nt, sstep(nt, z, -0.012, 0.004), inv(nt, sstep(nt, z, 0.058, 0.075)))
    up = inv(nt, sstep(nt, x, -0.2, 0.12))                 # 1 upstream .. 0 downstream
    ends = mul(nt, sstep(nt, x, -0.34, -0.22), inv(nt, sstep(nt, x, -0.03, 0.10)))
    d = mul(nt, band, ends, mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", n, mth(nt, "MULTIPLY_ADD", up, -0.08, 0.56)), 0.0))
    T = mth(nt, "MULTIPLY_ADD", up, 0.32, mth(nt, "MULTIPLY", n, 0.5))
    col = ramp3(nt, T, [(0.15, "#a51a04"), (0.4, "#ff4d0a"), (0.62, "#ff9b2e"), (0.8, "#ffd88a"), (1.0, "#fff4de")])
    v = node(nt, "ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (*lin("#2a1a12"), 1)
    link(nt, mth(nt, "MULTIPLY", d, 6.0), v.inputs["Density"])
    link(nt, col, v.inputs["Emission Color"])
    link(nt, mth(nt, "MULTIPLY", d, strength), v.inputs["Emission Strength"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    return m


def haze_mat(name, density, col="#ffffff"):
    m, nt, out = new_mat(name)
    v = node(nt, "ShaderNodeVolumeScatter")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*lin(col), 1)
    v.inputs["Anisotropy"].default_value = 0.4
    link(nt, v.outputs[0], out.inputs["Volume"])
    return m


def vol_box(name, c, s, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = V(v.co.x * s[0], v.co.y * s[1], v.co.z * s[2])
    return obj_from_bm(name, bm, mat, None, c)


def embers(name, c, n, box, seed=5):
    random.seed(seed)
    m = emis("Ember", "#ffb35a", 18.0)
    bm = bmesh.new()
    for _ in range(n):
        p = V(random.uniform(-box[0], box[0]), random.uniform(-box[1], box[1]), random.uniform(-box[2], box[2]))
        r = random.uniform(0.00025, 0.0006)
        bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=r,
                                  matrix=Matrix.Translation(p) @ Matrix.Diagonal((6.0, 1.0, 1.0, 1.0)))
    return obj_from_bm(name, bm, m, None, c)


def sun_lamp(d, strength, col, angle=0.6):
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy = strength
    ld.color = lin(col)
    ld.angle = rad(angle)
    ob = bpy.data.objects.new("Sun", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (-Vector(d)).to_track_quat("-Z", "Y")
    return ob


def place_cam(camo, eye, tgt, lens, fstop=11.0, roll=0.0, focus=None):
    eye, tgt = Vector(eye), Vector(tgt)
    camo.location = eye
    camo.rotation_quaternion = (tgt - eye).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), rad(roll))
    camo.data.lens = lens
    camo.data.dof.aperture_fstop = fstop
    camo.data.dof.focus_distance = focus or (tgt - eye).length


def build_sf():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    M = materials()
    M["livery"] = livery_mat()
    M["wingpaint"] = pbr("WingPaint", "#c3c7cc", 0.34, 0.25)
    M["tailpaint"] = pbr("TailPaint", "#14254a", 0.3, 0.0)
    for k in ("wingpaint", "tailpaint"):
        b = M[k].node_tree.nodes["Principled BSDF"]
        b.inputs["Coat Weight"].default_value = 0.7
        b.inputs["Coat Roughness"].default_value = 0.08
    pb = M["paint"].node_tree.nodes["Principled BSDF"]       # nacelles in white paint
    pb.inputs["Base Color"].default_value = (*lin("#e6e8ea"), 1)
    pb.inputs["Metallic"].default_value = 0.0
    pb.inputs["Roughness"].default_value = 0.3
    world = sky_world(1.4, 96.5)
    me_blade, rxr = blade_mesh("Blade")
    me_blade.materials.append(M["bladeD"])
    A = build_airliner(M, me_blade, rxr)
    clouds = cloud_deck(-700.0, -1600.0, 40000.0)
    sun = sun_lamp((-0.97, -0.11, 0.07), 4.5, "#ffb070")
    # hot section: disc in the flame, haze, embers, fire lights
    disc, body, posts, blades = build_disc(M, "HotDisc", me_blade, rxr, loc=HS)
    fire = vol_box("Fire", HS + V(-0.02, 0, 0), (0.70, 0.84, 0.84), fire_mat("Fire", strength=420.0))
    haze = vol_box("Haze", HS, (2.0, 2.0, 2.0), haze_mat("Haze", 0.004, "#ffd2a8"))
    emb = embers("Embers", HS + V(0.05, 0, 0.33), 1, (0.25, 0.25, 0.05))
    hot = [disc, fire, haze, emb]
    for name, loc, tgt, sx, sy, col, e in (
            ("Hfire", HS + V(-0.35, 0.0, 0.33), HS + V(0, 0, 0.33), 0.3, 0.3, "#ff7a2a", 12),
            ("Hfire2", HS + V(-0.30, -0.25, 0.25), HS + V(0, 0, 0.33), 0.3, 0.3, "#ff5a10", 0),
            ("Hkey", HS + V(0.6, -0.45, 0.75), HS + V(0, 0, 0.33), 0.5, 0.25, "#cfd8e6", 8)):
        hot.append(area(name, loc, tgt, sx, sy, col, e))
    # hero blade in the gas slab, cooling air out of its holes
    hero = mesh_obj("Hero", me_blade, None)
    hero.location = HB
    hero.material_slots[0].link = "OBJECT"
    hero.material_slots[0].material = M["bladeH"]
    P = build_blade_parts(M, me_blade, hero)
    for k, ob in P.items():
        ob.hide_render = k not in ("film",)
    setv(M["bladeH"], "FC", 1.0)
    setv(M["bladeH"], "TB", 0.62)
    setv(M["film"], "S", 1.0)
    setv(M["film"], "FG", 1.0)
    gas = vol_box("GasB", HB + V(-0.02, 0.0, 0.025), (0.62, 0.20, 0.11), fire_mat("FireB", axis_r=False, strength=380.0))
    hazeb = vol_box("HazeB", HB, (1.2, 1.2, 1.2), haze_mat("HazeB", 0.004, "#ffd2a8"))
    embb = embers("EmbersB", HB + V(0, 0.03, 0.025), 1, (0.2, 0.06, 0.04), 9)
    herog = [hero, gas, hazeb, embb, *P.values()]
    for name, loc, tgt, sx, sy, col, e in (
            ("Bfire", HB + V(-0.25, 0.10, 0.03), HB + V(0, 0, 0.03), 0.2, 0.2, "#ff6a1a", 6),
            ("Bkey", HB + V(0.35, -0.45, 0.35), HB + V(0, 0, 0.03), 0.4, 0.18, "#d6e0ee", 2.5),
            ("Brim", HB + V(0.1, 0.35, 0.15), HB + V(0, 0, 0.03), 0.04, 0.5, "#ffb070", 4)):
        herog.append(area(name, loc, tgt, sx, sy, col, e))
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.01, 40000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    return dict(M=M, A=A, clouds=clouds, sun=sun, world=world, hot=hot, hero=herog, cam=camo)


def frames(W):
    bpy.context.view_layer.update()
    eng = W["A"]["engines"][0]["root"].matrix_world.translation.copy()
    fan = eng + V(-1.7, 0, 0)
    return {
        "wide": dict(sky=True, eye=(-70, 92, -16), tgt=(-1, 0, -2), lens=50, fstop=16),
        "engine": dict(sky=True, eye=tuple(fan + V(-9.5, 6.5, -2.4)), tgt=tuple(fan + V(1.2, -0.8, 0.6)), lens=30,
                       fstop=11),
        "fan": dict(sky=True, eye=tuple(fan + V(-4.2, 2.2, -0.8)), tgt=tuple(fan + V(0, -0.2, 0.05)), lens=24,
                    fstop=8),
        "hot": dict(hot=True, eye=tuple(HS + V(0.40, -0.26, 0.47)), tgt=tuple(HS + V(-0.02, 0.0, 0.31)), lens=45,
                    fstop=8),
        "hero": dict(hero=True, eye=tuple(HB + V(0.07, -0.23, 0.06)), tgt=tuple(HB + V(0.0, 0.0, 0.022)),
                     lens=70, fstop=8),
    }


def render_sf(W, outdir, h, samples, ids, setup=True):
    scn = bpy.context.scene
    if setup:
        render_settings(scn, h, samples)
    scn.render.use_motion_blur = False
    scn.cycles.volume_bounces = 1
    os.makedirs(outdir, exist_ok=True)
    bg = W["world"].node_tree.nodes["Background"]
    for k, F in frames(W).items():
        if ids and k not in ids:
            continue
        sky = F.get("sky", False)
        bg.inputs[1].default_value = 0.3 if sky else 0.0
        W["sun"].hide_render = not sky
        W["clouds"].hide_render = not sky
        for ob in W["hot"]:
            ob.hide_render = not F.get("hot", False)
        for ob in W["hero"]:
            if ob.name.startswith(("Channels", "Blanket", "Selector")):
                continue
            ob.hide_render = not F.get("hero", False)
        place_cam(W["cam"], F["eye"], F["tgt"], F["lens"], F["fstop"])
        scn.render.filepath = os.path.join(outdir, f"{k}.png")
        bpy.ops.render.render(write_still=True)
        print("DONE", k)


def bench(W, outdir, h, samples, ids):
    """time the same frames under several device setups"""
    import time
    scn = bpy.context.scene
    pr = bpy.context.preferences.addons["cycles"].preferences
    print("PROPS", [p.identifier for p in pr.bl_rna.properties if "hip" in p.identifier.lower() or "rt" == p.identifier[-2:]])
    for tag, kind, cpu, hiprt in (("hip", "HIP", False, False), ("hiprt", "HIP", False, True),
                                  ("hip+cpu", "HIP", True, False), ("cpu", "NONE", True, False)):
        pr.compute_device_type = kind if kind != "NONE" else "NONE"
        pr.get_devices()
        for d in pr.devices:
            d.use = (d.type == "CPU" and cpu) or (d.type == kind)
        if hasattr(pr, "use_hiprt"):
            pr.use_hiprt = hiprt
        elif hiprt:
            continue
        scn.render.engine = "CYCLES"
        scn.cycles.device = "GPU" if kind != "NONE" else "CPU"
        print("CFG", tag, [(d.name, d.use) for d in pr.devices], flush=True)
        for k in ids:
            t0 = time.time()
            render_sf(W, os.path.join(outdir, tag), h, samples, [k], setup=False)
            print("TIME", tag, k, round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = build_sf() if argv[0] not in ("film", "benchdev") else None
    if W is None:
        pass
    elif argv[0] == "bench":
        render_settings(bpy.context.scene, int(argv[2]), int(argv[3]))
        bench(W, argv[1], int(argv[2]), int(argv[3]), argv[4].split(","))
        sys.exit(0)
    else:
        render_sf(W, argv[0], int(argv[1]), int(argv[2]), argv[3].split(",") if len(argv) > 3 else None)
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
# ----------------------------------------------------------------------------------------------- trains and the bird
# Two trains, lofted from superellipse sections along x (nose tip at x = 0, the train trails back along -x, rail top
# at z = 0): A, a 0-Series-like blunt nose; B, the 500 Series with a 15 m nearly round needle nose. B's lead car
# carries a shape key "beak" that turns its nose into a kingfisher's beak (and folds the body into the beak's base),
# used for the studio morph. The small Beak for the river shots is lofted from the same beak sections.
NB = 15.0                                   # 500 Series nose length
BODY_W, BODY_H, BODY_Z = 1.68, 1.68, 2.2    # body half-width, half-height, centre height above the rail


def sring(u, wx, hz, zc, n, zb=None, N=48):
    pts = []
    for i in range(N):
        a = 2 * math.pi * i / N
        c, s = math.cos(a), math.sin(a)
        y = wx * math.copysign(abs(c) ** (2 / n), c)
        z = zc + hz * math.copysign(abs(s) ** (2 / n), s)
        if zb is not None:
            z = max(z, zb)
        pts.append(V(u, y, z))
    return pts


def nose_a(u):
    """0 Series: a short rounded snub nose with a near-flat face"""
    s = clamp(-u / 5.5)
    k = math.sqrt(max(1 - (1 - s) ** 2, 0.0))
    return 1.75 * (0.42 + 0.58 * k), 1.8 * (0.36 + 0.64 * k), 2.25 - 0.75 * (1 - k), 2.9


def nose_b(u):
    """500 Series: a long, nearly round taper to a needle tip, set low"""
    s = clamp(-u / NB)
    p = s ** 0.62
    return BODY_W * (0.03 + 0.97 * p), BODY_H * (0.03 + 0.97 * p), 1.25 + (BODY_Z - 1.25) * s ** 0.8, 2.3


def beak_sec(u):
    """kingfisher beak at the same scale: a straight dagger, diamond-ish section, taller than wide"""
    s = clamp(-u / NB)
    p = s ** 0.95
    return 0.02 + 0.78 * p, 0.02 + 1.05 * p, 2.0 - 0.12 * (1 - s) ** 2, 1.7


def lead_stations(ln, body_end=-25.0):
    us = [-ln * (i / 36) ** 1.5 for i in range(37)]
    return us + [lerp(-ln, body_end, (i + 1) / 6) for i in range(6)]


def bm_car(bm, us, sec, zb=0.45):
    rings = [sring(u, *sec(u), zb=zb) for u in us]
    vs = bm_loft(bm, rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return rings


def livery_a():
    m, nt, out = new_mat("LiveryA")
    u, y, z = xyz(nt, obj_co(nt))
    band = mul(nt, sstep(nt, z, 2.42, 2.46), inv(nt, sstep(nt, z, 3.0, 3.04)), inv(nt, sstep(nt, u, -6.6, -6.3)))
    skirt = mul(nt, inv(nt, sstep(nt, z, 1.02, 1.06)), inv(nt, sstep(nt, u, -1.6, -1.2)))
    win = mul(nt, band, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.12, 0.16),
              inv(nt, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.7, 0.74)), inv(nt, sstep(nt, u, -9.0, -8.6)))
    shield = mul(nt, sstep(nt, u, -4.7, -4.6), inv(nt, sstep(nt, u, -2.5, -2.4)), sstep(nt, z, 2.75, 2.8))
    gap = sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", mth(nt, "ADD", u, 25.3), 25.6)), 0.985, 0.99)
    c = col_mix(nt, "#ece6d6", "#1d3f8f", mth(nt, "MAXIMUM", band, skirt))
    glass = mth(nt, "MAXIMUM", mth(nt, "MAXIMUM", win, shield), gap)
    c = col_mix(nt, c, "#07090c", glass)
    b = principled(nt, c, mth(nt, "MULTIPLY_ADD", glass, -0.25, 0.32), 0.0, coat=0.6)
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def irid(nt):
    """kingfisher sheen: dark gunmetal with a teal-to-orange thin-film shift at grazing angles"""
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    c = ramp3(nt, lw.outputs["Facing"], [(0.0, "#10262d"), (0.35, "#127f86"), (0.62, "#2ab7b0"), (0.82, "#e07a2a"),
                                          (1.0, "#3a1d0a")])
    _, _, z = xyz(nt, obj_co(nt))
    slit = inv(nt, sstep(nt, mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", z, 1.98)), 0.02, 0.06))
    c = col_mix(nt, c, "#050506", mth(nt, "MULTIPLY", slit, 0.85))
    return principled(nt, c, 0.2, 0.85, coat=1.0, coat_r=0.03)


def livery_b():
    """500 Series: metallic blue-grey, dark blue window band, thin white pinstripe; BK crossfades to the beak"""
    m, nt, out = new_mat("LiveryB")
    u, y, z = xyz(nt, obj_co(nt))
    BK = val(nt, "BK", 0.0)
    band = mul(nt, sstep(nt, z, 2.5, 2.54), inv(nt, sstep(nt, z, 3.06, 3.1)), inv(nt, sstep(nt, u, -11.4, -11.0)))
    pin = mul(nt, sstep(nt, z, 2.38, 2.40), inv(nt, sstep(nt, z, 2.43, 2.45)), inv(nt, sstep(nt, u, -9.0, -8.6)))
    win = mul(nt, band, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.12, 0.16),
              inv(nt, sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", u, 1.4)), 0.7, 0.74)), inv(nt, sstep(nt, u, -18.5, -18.0)))
    skirt = inv(nt, sstep(nt, z, 0.9, 0.95))
    gap = sstep(nt, mth(nt, "FRACT", mth(nt, "DIVIDE", mth(nt, "ADD", u, 25.3), 25.6)), 0.985, 0.99)
    c = col_mix(nt, "#8796a8", "#1b2a4c", band)
    c = col_mix(nt, c, "#f2f2ee", pin)
    c = col_mix(nt, c, "#4b525c", skirt)
    glass = mth(nt, "MAXIMUM", win, gap)
    c = col_mix(nt, c, "#06080c", glass)
    b = principled(nt, c, 0.26, mth(nt, "MULTIPLY_ADD", glass, -0.6, 0.6), coat=1.0, coat_r=0.04)
    link(nt, mix_sh(nt, BK, b.outputs[0], irid(nt).outputs[0]), out.inputs["Surface"])
    return m


def beak_mat():
    m, nt, out = new_mat("Beak")
    link(nt, irid(nt).outputs[0], out.inputs["Surface"])
    return m


def under_parts(bm, x0, x1):
    """bogies and the dark underframe between the skirts"""
    bmh(bm, ((x0 + x1) / 2, 0, 0.55), ((x0 - x1) / 2 - 0.4, 1.35, 0.3))
    for xc in (x0 - 3.0, x1 + 3.0):
        bmh(bm, (xc, 0, 0.42), (1.6, 1.25, 0.32))
        for dx in (-1.2, 1.2):
            bm_rod(bm, (xc + dx, -0.82, 0.43), (xc + dx, 0.82, 0.43), 0.43, 16)


def build_train(key, M, mat):
    """root empty (move it along the track) with the lead car, three trailing cars and the underframe"""
    root = empty(f"Root{key}")
    us = lead_stations(5.5 if key == "A" else NB)
    sec = nose_a if key == "A" else nose_b
    bm = bmesh.new()
    rings = bm_car(bm, us, sec)
    lead = obj_from_bm(f"Lead{key}", bm, mat, parent=root, smooth=True)
    if key == "B":
        # the beak shape key: nose rings become the beak; body rings fold into a rounded base behind it
        brs = []
        nb = len([u for u in us if u >= -NB - 1e-6])
        for i, u in enumerate(us):
            if i < nb:
                brs.append(sring(u, *beak_sec(u)))
            else:
                k = (i - nb + 1) / (len(us) - nb)
                wx, hz, zc, n = beak_sec(-NB)
                f = math.sqrt(max(1 - k ** 2, 0.0))
                brs.append(sring(-NB - 0.9 * k, wx * f + 0.01, hz * f + 0.01, zc, n))
        co = [p for r in brs for p in r]
        co += [sum(brs[0], Vector()) / len(brs[0]), sum(brs[-1], Vector()) / len(brs[-1])]
        lead.shape_key_add(name="Basis")
        sk = lead.shape_key_add(name="beak")
        for v, p in zip(sk.data, co):
            v.co = p
    bm = bmesh.new()
    body = (BODY_W, BODY_H, BODY_Z, 2.3) if key == "B" else (1.75, 1.8, 2.25, 2.9)
    ul = [0.0, 0.12, 0.35] + [0.35 + 24.3 * (j + 1) / 6 for j in range(6)] + [24.88, 25.0]
    sc = [0.9, 0.97, 1.0] + [1.0] * 6 + [0.97, 0.9]
    for c in range(3):
        x = -25.6 * (c + 1)
        rings = [sring(x - u, body[0] * k, body[1] * k, body[2], body[3], zb=0.45) for u, k in zip(ul, sc)]
        bm_loft(bm, rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cars = obj_from_bm(f"Cars{key}", bm, mat, parent=root, smooth=True)
    bm = bmesh.new()
    for c in range(4):
        under_parts(bm, -25.6 * c - 0.5, -25.6 * c - 25.0)
    under = obj_from_bm(f"Under{key}", bm, M["under"], parent=root)
    parts = dict(root=root, lead=lead, cars=cars, under=under)
    if key == "B":
        parts["canopy"] = sphere("CanopyB", 1.0, (-10.6, 0, 3.15), M["glass"], parent=root, scale=(2.2, 0.62, 0.42))
        bm = bmesh.new()                                    # wing-shaped T pantograph on car 2
        px = -38.0
        bmh(bm, (px, 0, 3.98), (0.9, 0.5, 0.12))
        bm_rod(bm, (px, 0, 4.0), (px + 0.6, 0, 4.85), 0.07, 10)
        bmh(bm, (px + 0.6, 0, 4.95), (0.22, 1.0, 0.07))
        bmh(bm, (px + 0.6, 0, 5.06), (0.06, 0.95, 0.04))
        parts["panto"] = obj_from_bm("PantoB", bm, M["under"], parent=root)
        parts["spark"] = sphere("Spark", 0.05, (px + 0.6, 0.25, 5.1), M["spark"], parent=root)
    return parts


def build_beak(mat, scale=0.004):
    """the small beak for the river shots: tip at the origin pointing +x"""
    us = lead_stations(NB, -NB - 0.9)
    brs = []
    for u in us:
        if u >= -NB:
            brs.append(sring(u, *beak_sec(u)))
        else:
            k = (u + NB) / -0.9
            wx, hz, zc, n = beak_sec(-NB)
            f = math.sqrt(max(1 - k ** 2, 0.0))
            brs.append(sring(u, wx * f + 0.01, hz * f + 0.01, zc, n))
    bm = bmesh.new()
    bm_loft(bm, [[(p - V(0, 0, 2.0)) * scale for p in r] for r in brs])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    root = empty("BeakRoot")
    obj_from_bm("Beak", bm, mat, parent=root, smooth=True)
    return root


def bird_mats():
    """kingfisher plumage: electric blue-cyan above, orange below (split on the object-space normal)"""
    m, nt, out = new_mat("Plumage")
    _, _, nz = xyz(nt, node(nt, "ShaderNodeTexCoord").outputs["Normal"])
    back = col_mix(nt, "#0a4f9c", "#1fb8e0", sstep(nt, nz, 0.35, 0.95))
    c = col_mix(nt, back, "#e2671d", inv(nt, sstep(nt, nz, -0.45, -0.1)))
    fl = noise(nt, obj_co(nt), 900.0, 2.0)
    c = col_mix(nt, c, "#000000", mth(nt, "MULTIPLY", fl, 0.25))
    link(nt, principled(nt, c, 0.38, 0.0, coat=0.5, coat_r=0.18).outputs[0], out.inputs["Surface"])
    w, nt, out = new_mat("Wing")
    _, yy, _ = xyz(nt, obj_co(nt))
    fl = noise(nt, obj_co(nt), 500.0, 3.0)
    c = col_mix(nt, "#073f7a", "#16a6d4", mth(nt, "MULTIPLY", fl, 0.9))
    link(nt, principled(nt, c, 0.34, 0.0, coat=0.6, coat_r=0.15).outputs[0], out.inputs["Surface"])
    return m, w, pbr("Eye", "#030303", 0.06, 0.0), pbr("Cheek", "#f2f0ea", 0.5, 0.0)


def build_bird(root):
    """a stylised kingfisher behind the river beak (tip at the root origin, pointing +x)"""
    pl, wg, eye, wh = bird_mats()
    obs = [sphere("BirdHead", 1.0, (-0.074, 0, 0.004), pl, parent=root, scale=(0.017, 0.0135, 0.0145)),
           sphere("BirdBody", 1.0, (-0.118, 0, -0.003), pl, parent=root, scale=(0.042, 0.0185, 0.019)),
           sphere("BirdTail", 1.0, (-0.172, 0, 0.0), wg, parent=root, scale=(0.026, 0.0085, 0.0028))]
    for sy in (-1, 1):
        obs += [sphere(f"BirdWing{sy}", 1.0, (-0.124, sy * 0.016, 0.006), wg, parent=root,
                       scale=(0.033, 0.0036, 0.0115)),
                sphere(f"BirdEye{sy}", 1.0, (-0.068, sy * 0.0118, 0.0075), eye, parent=root,
                       scale=(0.0026, 0.0026, 0.0026), seg=16),
                sphere(f"BirdCheek{sy}", 1.0, (-0.083, sy * 0.0105, -0.004), wh, parent=root,
                       scale=(0.006, 0.0035, 0.0045), seg=16)]
    obs[2].rotation_euler = (0.0, rad(-8.0), 0.0)
    return obs


def water_mat():
    """still river water; a single radial ripple of radius RR (m), height RA, around the object origin"""
    m, nt, out = new_mat("Water")
    P = obj_co(nt)
    x, y, _ = xyz(nt, P)
    RR, RA = val(nt, "RR", 0.0), val(nt, "RA", 0.0)
    d = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", x, x), mth(nt, "MULTIPLY", y, y)))
    dr = mth(nt, "SUBTRACT", d, RR)
    rip = mul(nt, mth(nt, "SINE", mth(nt, "MULTIPLY", dr, 260.0)),
              mth(nt, "EXPONENT", mth(nt, "MULTIPLY", mth(nt, "POWER", mth(nt, "DIVIDE", dr, 0.012), 2.0), -1.0)), RA)
    h = mth(nt, "ADD", rip, mth(nt, "MULTIPLY", noise(nt, P, 0.9, 3.0, 0.5, stretch=(1.0, 3.0, 1.0)), 0.004))
    b = principled(nt, "#0a1a1c", 0.02, 0.0)
    b.inputs["IOR"].default_value = 1.33
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.004
    link(nt, h, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    link(nt, b.outputs[0], out.inputs["Surface"])
    return m


def build_river(M):
    """the river set at RV: still water, a reed bank behind, a bare branch, a dark treeline far away"""
    obs = []
    bm = bmesh.new()
    bmh(bm, (0, 0, -0.05), (40.0, 40.0, 0.05))
    obs.append(obj_from_bm("River", bm, M["water"], loc=RV))
    bm = bmesh.new()
    nx, ny, step = 61, 31, 1.0
    vs = []
    for j in range(ny):
        for i in range(nx):
            x, y = -30.0 + i * step, 7.0 + j * step
            vs.append(bm.verts.new((x, y, 0.18 * (y - 7.5) + 0.3 * nz(x, y, 4.0, 9.0))))
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    obs.append(obj_from_bm("Bank", bm, M["bank"], loc=RV, smooth=True))
    random.seed(4)
    bm = bmesh.new()
    for k in range(520):
        if k % 2:
            x, y = random.uniform(-12, 12), random.uniform(7.2, 10.0)
        else:
            x, y = random.choice((-1, 1)) * random.uniform(0.9, 5.0), random.uniform(-4.5, -2.6)
        h = random.uniform(0.6, 1.6)
        lean = V(random.uniform(-0.12, 0.12), random.uniform(-0.1, 0.1), 0)
        bm_rod(bm, V(x, y, -0.1), V(x, y, h) + lean, random.uniform(0.004, 0.008), 5)
    obs.append(obj_from_bm("Reeds", bm, M["reed"], loc=RV))
    bm = bmesh.new()
    pts = [V(-2.4, 2.6, 1.2), V(-1.5, 1.6, 0.95), V(-0.7, 0.9, 0.82), V(-0.15, 0.45, 0.78), V(0.25, 0.2, 0.8)]
    bm_tube(bm, pts, 0.018, 10, rfun=lambda u: 1.2 - 0.7 * u)
    obs.append(obj_from_bm("Branch", bm, M["bark"], loc=RV, smooth=True))
    bm = bmesh.new()
    random.seed(8)
    for _ in range(90):
        x, y = random.uniform(-60, 60), random.uniform(24, 40)
        h = random.uniform(8, 14)
        bm_cyl(bm, h * 0.24, 0.0, h, 14, Matrix.Translation(V(x, y, 0.18 * (y - 7.5) + h / 2)))
    obs.append(obj_from_bm("FarTrees", bm, M["tree"], loc=RV, smooth=True))
    return obs


def build_shock(M):
    """the pressure burst at the exit portal: an emissive torus that the shots scale up and fade"""
    bm = bmesh.new()
    bm_torus(bm, Matrix(), 1.0, 0.12, 64, 8)
    return obj_from_bm("Shock", bm, M["shock"], loc=(X1T + HOOD + 1.0, 0, ZT), smooth=True)


def studio_lights():
    """key and rim area lights round the studio set; their energy is keyed up only in the studio shots"""
    obs = []
    for name, off, size, col, e in (("Key", V(14, -16, 12), 10.0, "#fff3e2", 9000.0),
                                    ("Rim", V(-26, 14, 8), 6.0, "#d6e8ff", 14000.0),
                                    ("Top", V(-6, 0, 22), 14.0, "#ffffff", 5000.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "DISK"
        ld.size = size
        ld.color = lin(col)
        ld.energy = e
        ob = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = ST + off
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = (ST + V(-7, 0, 2) - ob.location).to_track_quat("-Z", "Y")
        obs.append(ob)
    return obs


def build_sk():
    scn = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    M = {}
    M["terrain"] = terrain_mat()
    M["conc"] = concrete("Concrete")
    M["rail"] = pbr("Steel", "#6c6e70", 0.35, 1.0)
    M["wire"] = pbr("Wire", "#3a3226", 0.4, 1.0)
    M["tree"] = tree_mat()
    M["wall"] = pbr("Wall", "#ddd6c8", 0.7)
    M["roof"] = pbr("Roof", "#3b3f45", 0.55, 0.2)
    M["win"] = emis("Win", "#ffbf70", 6.0)
    M["tunnel"] = tunnel_mats()
    M["rings"] = rings_mat()
    M["A"], M["B"] = livery_a(), livery_b()
    M["under"] = pbr("Under", "#1c1e21", 0.6, 0.3)
    M["glass"] = pbr("Glass", "#05070a", 0.04, 0.0)
    M["spark"] = emis("Spark", "#bfe3ff", 0.0)
    M["beak"] = beak_mat()
    M["water"] = water_mat()
    M["bank"] = pbr("Bank", "#4a4528", 0.9)
    M["reed"] = pbr("Reed", "#8d7a45", 0.8)
    M["bark"] = pbr("Bark", "#2e241c", 0.85)
    M["shock"] = emis("Shock", "#ffd9a0", 0.0, alpha=1.0)
    world = sky_studio_world(6.5, -58.0)
    ter = terrain(M["terrain"])
    tun = build_tunnel(M["tunnel"])
    rings = build_rings(M["rings"])
    track = build_track(M["conc"], M["rail"], M["wire"])
    trees = build_trees(M["tree"])
    houses = build_houses(M["wall"], M["roof"], M["win"])
    sd = V(-math.sin(rad(-58.0)), math.cos(rad(-58.0)), 0.0) * math.cos(rad(6.5)) + V(0, 0, math.sin(rad(6.5)))
    sun = sun_lamp(sd, 4.5, "#ffb072", angle=0.8)
    TA, TB = build_train("A", M, M["A"]), build_train("B", M, M["B"])
    beak = build_beak(M["beak"])
    build_bird(beak)
    river = build_river(M)
    shock = build_shock(M)
    lights = studio_lights()
    kd = bpy.data.lights.new("BeakKey", "AREA")
    kd.size = 0.6
    kd.color = lin("#ffe2bf")
    beakkey = bpy.data.objects.new("BeakKey", kd)
    bpy.context.scene.collection.objects.link(beakkey)
    beakkey.location = RV + V(0.5, -0.8, 0.9)
    beakkey.rotation_mode = "QUATERNION"
    beakkey.rotation_quaternion = (RV + V(0, 0, 0.45) - beakkey.location).to_track_quat("-Z", "Y")
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.05, 20000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    valley = [ter, *track, trees, *houses]
    return dict(M=M, world=world, valley=valley, tunnel=tun, rings=rings, sun=sun, A=TA, B=TB, beak=beak,
                river=river, shock=shock, lights=lights, beakkey=beakkey, cam=camo, hero=None)
# ----------------------------------------------------------------------------------------------- film
# blender -b --factory-startup -P sk.py -- film <outdir> <height> <samples> <a-b | f,f,f>
BG = 'nodes["BG"].inputs[1].default_value'
SUN = 4.5
VT = 70.0                              # train speed in the valley shots (m/s, ~250 km/h)


def sk_world():
    return build_sk()


def parts(W, key):
    return [o for k, o in W[key].items() if k != "root"]


def defaults(t, S, W):
    M = W["M"]
    put(S, W["world"].node_tree, BG, 0.35)
    mset(S, W["world"], STU=0.0)
    put(S, W["sun"].data, "energy", SUN)
    for ob in W["valley"] + [W["tunnel"]]:
        put(S, ob, "hide_render", 0, const=True)
    for ob in parts(W, "A") + parts(W, "B") + W["river"] + [W["rings"], W["shock"]] + list(W["beak"].children):
        put(S, ob, "hide_render", 1, const=True)
    for key in ("A", "B"):
        for i, v in enumerate((-3000.0, 0.0, ZR)):
            put(S, W[key]["root"], "location", v, i)
    for i, v in enumerate(RV + V(0, 0, 0.6)):
        put(S, W["beak"], "location", v, i)
    for i in range(3):
        put(S, W["beak"], "rotation_euler", 0.0, i)
        put(S, W["shock"], "scale", 0.0, i)
        put(S, W["B"]["root"], "rotation_euler", 0.0, i)
    mset(S, M["tunnel"], XA=0.0)
    mset(S, M["rings"], NX=-500.0, WX=-500.0, WW=4.0, AMP=0.0, NC=0.0)
    mset(S, M["B"], BK=0.0)
    mset(S, M["shock"], S=0.0)
    mset(S, M["spark"], S=0.0)
    mset(S, M["water"], RR=0.0, RA=0.0)
    put(S, W["B"]["lead"].data.shape_keys, 'key_blocks["beak"].value', 0.0)
    for lt in W["lights"]:
        put(S, lt.data, "energy", 0.0)
    put(S, W["beakkey"].data, "energy", 0.0)


def train(S, W, key, x):
    """train key's nose tip at x on the line"""
    put(S, W[key]["root"], "location", x, 0)
    for ob in parts(W, key):
        if ob.name != "Spark":
            put(S, ob, "hide_render", 0, const=True)


def xray(S, W, k=1.0):
    """the mountain goes away: the bore turns to glass in a dark void and the air rings show"""
    for ob in W["valley"]:
        put(S, ob, "hide_render", 1, const=True)
    put(S, W["rings"], "hide_render", 0, const=True)
    put(S, W["world"].node_tree, BG, lerp(0.35, 0.012, k))
    mset(S, W["M"]["tunnel"], XA=k)


def rings(S, W, nx, wx, ww, amp, nc=0.0):
    mset(S, W["M"]["rings"], NX=nx, WX=wx, WW=ww, AMP=amp, NC=nc)


def burst(S, W, t, t0, size, strength, dur=0.32, zmax=None):
    """the shock ring leaves the exit portal at t0"""
    if t < t0:
        return
    k = eout(clamp((t - t0) / dur))
    put(S, W["shock"], "hide_render", 0, const=True)
    for i in range(3):
        put(S, W["shock"], "scale", 0.3 + (min(size * k, zmax) if i == 2 and zmax else size * k), i)
    mset(S, W["M"]["shock"], S=strength * (1 - clamp((t - t0) / (dur * 1.6))) ** 1.5)


def river(S, W, beak=True):
    for ob in W["valley"] + [W["tunnel"]]:
        put(S, ob, "hide_render", 1, const=True)
    put(S, W["beakkey"].data, "energy", 25.0)
    for ob in W["river"]:
        put(S, ob, "hide_render", 0, const=True)
    if beak:
        for ob in W["beak"].children:
            put(S, ob, "hide_render", 0, const=True)


def beak_at(S, W, p, tilt):
    for i in range(3):
        put(S, W["beak"], "location", p[i], i)
    put(S, W["beak"], "rotation_euler", rad(tilt), 1)


def studio(S, W):
    for ob in W["valley"] + [W["tunnel"]]:
        put(S, ob, "hide_render", 1, const=True)
    mset(S, W["world"], STU=1.0)
    put(S, W["sun"].data, "energy", 0.0)
    for lt in W["lights"]:
        put(S, lt.data, "energy", {"Key": 9000.0, "Rim": 14000.0, "Top": 5000.0}[lt.name])
    for i, v in enumerate(ST):
        put(S, W["B"]["root"], "location", v, i)


def shots(W):
    M = W["M"]
    L = []
    PORT = V(X1T + HOOD, 0, ZT - 1.0)

    def A(t, S):     # "Four hundred metres from a tunnel": high over the houses, looking back up the line to the exit
        u = ss(seg(t, 0.0, 1.8))
        train(S, W, "A", -760.0)
        cam(S, V(lerp(1010, 975, u), lerp(-300, -285, u), lerp(105, 96, u)), V(lerp(560, 540, u), -20, 12), lens=30,
            fstop=16, clip=1.0)
        label(S, "home", V(752, -120, ground(752, -120) + 5.0))
        label(S, "portal", V(X1T + HOOD, 0, ZT))
    L.append((0.0, 1.8, A))

    def B(t, S):     # "homes heard": low by the track as it blasts past, whipping round to the portal
        nx = -230 + VT * (t - 1.8)
        train(S, W, "A", nx)
        w = ss(seg(t, 2.55, 3.3))
        tg = V(nx + 6, 0, ZR + 1.8).lerp(V(X0T - HOOD, 0, ZT), w)
        cam(S, V(lerp(-152, -146, seg(t, 1.8, 3.3)), -15.0, ZR + 0.9), tg, lens=30, fstop=11, clip=0.3)
    L.append((1.8, 3.3, B))

    def C(t, S):     # "Japan's bullet train boom": the far portal from the houses, a burst on "boom"
        burst(S, W, t, 4.0, 7.0, 40.0)
        sh = 1.6 * seg(t, 4.0, 4.12) * (1 - seg(t, 4.12, 4.6))
        cam(S, PORT + V(lerp(150, 142, seg(t, 3.3, 4.62)), -22.0, 26.0), PORT + V(0, 0, 3.0), lens=50, fstop=32,
            clip=1.0, shake=sh, t=t * 3)
    L.append((3.3, 4.62, C))

    def D(t, S):     # "Its blunt nose squeezed the air": x-ray, side on, the rings bunch ahead of the nose
        xray(S, W, ss(seg(t, 4.62, 5.0)))
        u = seg(t, 4.62, 6.25)
        nx = lerp(-6, 40, u)
        train(S, W, "A", nx)
        rings(S, W, nx, nx + lerp(6, 34, u), 5.0, lerp(0.3, 0.85, u), lerp(0.3, 0.8, u))
        cam(S, V(nx - 1, -11.5, ZT + 0.8), V(nx + 6, 0, ZT), lens=20, fstop=16, clip=0.5)
    L.append((4.62, 6.25, D))

    def E(t, S):     # "...inside the tunnel": close on the blunt face, the air piling up red against it
        xray(S, W)
        u = seg(t, 6.25, 7.85)
        nx = lerp(36, 44, u)
        train(S, W, "A", nx)
        rings(S, W, nx, nx + lerp(36, 50, u), 4.0, 1.0, lerp(0.8, 1.1, u))
        cam(S, V(nx + lerp(13, 10, ss(u)), -6.5, ZR + 2.2), V(nx - 1.5, 0, ZR + 1.9), lens=35, fstop=4, clip=0.1)
    L.append((6.25, 7.85, E))

    def F(t, S):     # "That squeeze raced ahead at the speed of sound": the front breaks away, whip with it
        xray(S, W)
        u = seg(t, 7.85, 9.1)
        nx = lerp(46, 52, u)
        wx = nx + lerp(52, 190, ein(u))
        train(S, W, "A", nx)
        rings(S, W, nx, wx, 3.0, 1.0, 0.9)
        cam(S, V(lerp(70, 215, ss(u)), -38.0, ZT + 2.0), V(wx, 0, ZT), lens=28, fstop=16, clip=0.5)
    L.append((7.85, 9.1, F))

    def G(t, S):     # ...riding ahead of the front, looking back as it steepens
        xray(S, W)
        u = seg(t, 9.1, 10.3)
        wx = lerp(250, 335, u)
        rings(S, W, 56.0, wx, lerp(3.0, 1.2, u), lerp(1.0, 1.25, u))
        cam(S, V(wx + 16, 1.2, ZT + 0.6), V(wx - 30, 0, ZT - 0.5), lens=24, fstop=16, clip=0.1)
    L.append((9.1, 10.3, G))

    def H(t, S):     # "and burst from the exit": inside the bore, the front racing for the daylight
        put(S, W["rings"], "hide_render", 0, const=True)
        u = seg(t, 10.3, 11.1)
        wx = lerp(318, 375, u)
        rings(S, W, 56.0, wx, 1.5, 1.1)
        cam(S, V(lerp(298, 330, ss(u)), 0.8, ZT + 0.3), V(X1T + 40, 0, ZT + 1.2), lens=30, fstop=16, clip=0.1)
    L.append((10.3, 11.1, H))

    def I(t, S):     # "...exit. Boom.": outside, from behind the houses: the pulse leaves the portal and sweeps over them
        burst(S, W, t, 11.2, 360.0, 60.0, dur=1.1, zmax=40.0)
        sh = 2.2 * seg(t, 11.93, 11.99) * (1 - seg(t, 11.99, 12.42))
        u = ss(seg(t, 11.1, 12.42))
        cam(S, V(lerp(830, 812, u), lerp(-190, -182, u), lerp(38, 34, u)), V(lerp(480, 490, u), -45, 12), lens=30,
            fstop=16, clip=0.5, shake=sh, t=t * 4)
        label(S, "homes", V(700, -132, ground(700, -132) + 5.0))
    L.append((11.1, 12.42, I))

    def J(t, S):     # "Engineer Eiji Nakatsu, a birdwatcher": a still river at golden hour
        river(S, W, beak=False)
        u = ss(seg(t, 12.42, 14.0))
        cam(S, RV + V(lerp(-3.2, -2.0, u), -2.2, 0.16), RV + V(0.6, 3.0, 0.75), lens=30, fstop=5.6, clip=0.02)
    L.append((12.42, 14.0, J))

    def K(t, S):     # "thought of the kingfisher": the beak, high over the water, catching the sun
        river(S, W)
        beak_at(S, W, RV + V(0, 0, 0.6), 14.0)
        u = ss(seg(t, 14.0, 16.0))
        a = rad(lerp(-118, -72, u))
        c = RV + V(lerp(-0.1, -0.035, u), 0, lerp(0.598, 0.604, u))
        d = lerp(0.62, 0.27, u)
        cam(S, c + V(d * math.cos(a), d * math.sin(a), lerp(0.07, 0.03, u)), c, lens=85, fstop=lerp(5.6, 2.8, u),
            clip=0.005)
    L.append((14.0, 16.0, K))

    def Lb(t, S):    # "which dives from air into water": tip first
        river(S, W)
        u = seg(t, 16.0, 17.3)
        z = lerp(0.6, 0.06, ein(u))
        beak_at(S, W, RV + V(0, 0, z), lerp(14, 88, ss(u)))
        cam(S, RV + V(0.06, -0.42, lerp(0.56, 0.1, ss(u))), RV + V(0, 0, z - 0.02), lens=60, fstop=4, clip=0.005)
    L.append((16.0, 17.3, Lb))

    def Mw(t, S):    # "with barely a splash": slow motion at the waterline, one clean ripple
        river(S, W)
        u = seg(t, 17.3, 19.05)
        z = lerp(0.03, -0.035, u)
        beak_at(S, W, RV + V(0, 0, z), 88.0)
        k = seg(t, 17.55, 19.05)
        mset(S, M["water"], RR=0.14 * eout(k), RA=0.006 * (1 - k) * (k > 0))
        cam(S, RV + V(0.03, -0.42, 0.12), RV + V(0, 0, 0.035), lens=50, fstop=5.6, clip=0.005)
    L.append((17.3, 19.05, Mw))

    def N(t, S):     # "So the five hundred Series": in the studio the beak turns and grows into the nose
        studio(S, W)
        put(S, W["B"]["lead"], "hide_render", 0, const=True)
        m = ss(seg(t, 19.55, 20.9))
        put(S, W["B"]["lead"].data.shape_keys, 'key_blocks["beak"].value', 1 - m)
        mset(S, M["B"], BK=1 - ss(seg(t, 20.1, 21.0)))
        put(S, W["B"]["root"], "rotation_euler", rad(lerp(24, 0, m)), 2)
        put(S, W["B"]["root"], "rotation_euler", rad(lerp(-10, 0, m)), 1)
        u = ss(seg(t, 19.05, 21.0))
        cam(S, ST + V(lerp(13, 8, u), lerp(-21, -24, u), lerp(4.5, 3.4, u)), ST + V(lerp(-7, -8, u), 0, 2.0), lens=40,
            fstop=8, clip=0.1)
    L.append((19.05, 21.0, N))

    def O(t, S):     # "got a fifteen-metre beak for a nose": side on, the whole nose and the cars behind it
        studio(S, W)
        train(S, W, "B", ST.x)
        u = ss(seg(t, 21.0, 22.1))
        cam(S, ST + V(lerp(-6.5, -8.5, u), -24.0, 2.6), ST + V(lerp(-7.2, -7.8, u), 0, 2.2), lens=24, fstop=11, clip=0.1)
        label(S, "tip", ST + V(0.0, 0, 1.25))
        label(S, "base", ST + V(-NB, 0, BODY_Z))
    L.append((21.0, 22.1, O))

    def P(t, S):     # back in the valley: the 500 Series rockets at the camera
        nx = -205 + VT * (t - 22.1)
        train(S, W, "B", nx)
        cam(S, V(-150, -3.9, ZR + 1.1), V(nx - 4, 0, ZR + 1.6), lens=28, fstop=11, clip=0.2)
    L.append((22.1, 22.8, P))

    def Q0(t, S):    # "Now the air...": outside, the pointed nose slides into the portal
        nx = -VT * (23.5 - t)
        train(S, W, "B", nx)
        u = seg(t, 22.8, 23.75)
        cam(S, V(lerp(-44, -36, u), -6.5, ZR + 14.0), V(lerp(-14, -8, u), 0, ZT - 1.5), lens=24, fstop=16, clip=0.3)
    L.append((22.8, 23.75, Q0))

    def Q(t, S):     # "...is squeezed gently": the same x-ray, a soft wide gradient building slowly, no sharp front
        xray(S, W, 0.8 * ss(seg(t, 23.75, 24.05)))
        u = seg(t, 23.75, 25.1)
        nx = lerp(4, 36, u)
        train(S, W, "B", nx)
        rings(S, W, nx, nx + lerp(15, 90, u), 45.0, lerp(0.1, 0.3, ss(u)), 0.12)
        cam(S, V(nx - 3, -13.5, ZT + 1.5), V(nx + 3, 0, ZT), lens=22, fstop=16, clip=0.5)
    L.append((23.75, 25.1, Q))

    def R(t, S):     # "The boom fades": the same exit, only a faint soft ring, no shake
        burst(S, W, t, 25.35, 4.0, 3.0, dur=0.6)
        cam(S, PORT + V(lerp(58, 54, seg(t, 25.1, 26.34)), -6.0, 6.0), PORT + V(0, 0, 1.5), lens=35, fstop=16, clip=0.5)
    L.append((25.1, 26.34, R))

    def Sp(t, S):    # "Ten percent faster": out of the portal into the light, whip-follow along the viaduct
        nx = 372 + VT * (t - 26.34)
        train(S, W, "B", nx)
        u = ss(seg(t, 26.34, 28.0))
        cam(S, V(max(X1T + 16, nx - lerp(34, 14, u)), -9.5, ZR + 3.5), V(nx - 4, 0, ZR + 2.0), lens=28, fstop=16, clip=0.3)
        label(S, "speed", V(nx - 6, 0, ZR + 4.2))
    L.append((26.34, 28.0, Sp))

    def T(t, S):     # "on fifteen percent less power": the pantograph on the wire, a spark
        x = 520 + VT * (t - 28.0)
        train(S, W, "B", x)
        put(S, W["B"]["spark"], "hide_render", 0, const=True)
        mset(S, M["spark"], S=30.0 * max(0.0, math.sin(t * 41.0)) ** 8)
        r = V(x, 0, ZR)
        cam(S, r + V(lerp(-33.0, -35.0, seg(t, 28.0, 29.7)), -5.2, 6.6), r + V(-37.4, 0, 4.9), lens=40, fstop=5.6,
            clip=0.1)
        label(S, "panto", r + V(-37.4, 0, 5.0))
    L.append((28.0, 29.7, T))

    def U(t, S):     # "Follow for how the world is really engineered": crane up and away down the valley
        u = seg(t, 29.7, T_END)
        x = 690 + VT * (t - 29.7)
        train(S, W, "B", x)
        cam(S, V(lerp(740, 520, ss(u)), lerp(-60, -430, ss(u)), lerp(24, 250, ss(u))), V(lerp(760, 1050, ss(u)), 0,
            lerp(14, 70, ss(u))), lens=30, fstop=16, clip=1.0)
    L.append((29.7, T_END + 0.1, U))
    return L


def camcheck(W):
    """camera clearance over the valley terrain, per sampled frame (valley shots only)"""
    L = shots(W)
    for f in range(1, F_END + 1, 6):
        t = (f - 1) / FPS
        fn = next(fn for t0, t1, fn in L if t0 <= t < t1)
        S = {}
        defaults(t, S, W)
        fn(t, S)
        eye = S["cam"][0]
        if abs(eye.y) < 1500:
            clr = eye.z - ground(eye.x, eye.y)
            print("CC %4d %5.2f %-3s clr %7.1f %s" % (f, t, fn.__name__, clr, "UNDERGROUND" if clr < 0 else ""))


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = sk_world()
    if os.environ.get("CAMCHECK"):
        camcheck(W)
        sys.exit(0)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_sk.json"))
    if os.environ.get("BAKEONLY"):
        sys.exit(0)
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
