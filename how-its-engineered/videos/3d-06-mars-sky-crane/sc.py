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
# ----------------------------------------------------------------------------------------------- film
# blender -b --factory-startup -P sc.py -- film <outdir> <height> <samples> <a-b | f,f,f>
T_END = 32.2
F_END = int(T_END * FPS) + 1
BG = 'nodes["BG"].inputs[1].default_value'
SUNE = 3.6
STOW = 55.0                     # wheel fold angle while stowed


def sc_world():
    W = build_sc()
    for i, pl in enumerate(W["S"]["plumes"]):          # one engine per pod keeps running in the sky crane phase
        if i % 2:
            pl.data.materials[0] = W["M"]["plumeB"]
    return W


def defaults(t, S, W):
    M, R, St = W["M"], W["R"], W["S"]
    put(S, W["world"].node_tree, BG, 1.0)
    mset(S, W["world"], STU=0.0)
    put(S, W["sun"].data, "energy", SUNE)
    for ob in W["mars"]:
        put(S, ob, "hide_render", 0, const=True)
    for ob in [W["floorS"], W["bags"]["ball"], W["dust"], W["dustT"], W["dustC"], W["flash"]] + W["sparks"] + \
            W["fly"] + W["BR"] + St["parts"] + St["plumes"]:
        put(S, ob, "hide_render", 1, const=True)
    for ob in R["parts"]:
        put(S, ob, "hide_render", 0, const=True)
    for i in range(3):
        put(S, R["root"], "location", 0.0, i)
        put(S, R["root"], "rotation_euler", 0.0, i)
        put(S, St["root"], "location", (0.0, 0.0, -500.0)[i], i)
        put(S, St["root"], "rotation_euler", 0.0, i)
        put(S, W["bags"]["ball"], "scale", 1.0, i)
    put(S, W["bags"]["ball"], "location", 2.15, 2)
    for sd in R["sides"]:
        put(S, sd, "rotation_euler", 0.0, 0)
    put(S, R["mast"], "rotation_euler", rad(-90.0), 1)
    mset(S, M["plume"], S=0.0, W=t * 6.0)
    mset(S, M["plumeB"], S=0.0, W=t * 6.0 + 3.0)
    for k in ("dust", "dustT", "dustC"):
        mset(S, M[k], D=0.0, W=t * 0.35)
    mset(S, M["reg"], SC=0.0)
    mset(S, M["flash"], S=0.0)
    mset(S, M["spark"], S=0.0)
    put(S, St["glow"].data, "energy", 0.0)
    for lt in W["lights"]:
        put(S, lt.data, "energy", 0.0)


def fold(S, W, k):
    """k = 1 stowed (wheels folded up beside the body), 0 deployed"""
    for sd, s in zip(W["R"]["sides"], (1, -1)):
        put(S, sd, "rotation_euler", rad(STOW * s * k), 0)


def stage(S, W, p, pitch=0.0, yaw=0.0, burn=1.0, burnB=1.0):
    St = W["S"]
    for ob in St["parts"] + St["plumes"]:
        put(S, ob, "hide_render", 0, const=True)
    for i in range(3):
        put(S, St["root"], "location", p[i], i)
    put(S, St["root"], "rotation_euler", rad(pitch), 1)
    put(S, St["root"], "rotation_euler", rad(yaw), 2)
    mset(S, W["M"]["plume"], S=burn)
    mset(S, W["M"]["plumeB"], S=burnB)


def hang(S, W, belly, L, fold_k=0.0, burn=1.0, burnB=0.0, cables=True, glow=0.0):
    """the sky crane: the stage with its belly at `belly`, the rover L metres further down on the bridles"""
    belly = Vector(belly)
    stage(S, W, belly, burn=burn, burnB=burnB)
    rz = belly.z - (HANG + L)
    for i, v in enumerate((belly.x, belly.y, rz)):
        put(S, W["R"]["root"], "location", v, i)
    fold(S, W, fold_k)
    if cables:
        ln = belly.z - 0.15 - (rz + DECK + 0.06)
        for b in W["BR"]:
            a = Vector(b["att"])
            put(S, b, "hide_render", 0, const=True)
            for i, v in enumerate((belly.x + a.x, belly.y + a.y, belly.z - 0.15)):
                put(S, b, "location", v, i)
            put(S, b, "scale", max(ln, 0.01), 2)
    put(S, W["S"]["glow"].data, "energy", glow)
    return rz


def dust(S, W, key, c, R, H, D, t=None):
    ob = W[key]
    put(S, ob, "hide_render", 0, const=True)
    for i in range(3):
        put(S, ob, "location", c[i], i)
    put(S, ob, "scale", R, 0)
    put(S, ob, "scale", R, 1)
    put(S, ob, "scale", H, 2)
    mset(S, W["M"][key], D=D)


def studio(S, W):
    for ob in W["mars"]:
        put(S, ob, "hide_render", 1, const=True)
    put(S, W["floorS"], "hide_render", 0, const=True)
    mset(S, W["world"], STU=1.0)
    put(S, W["sun"].data, "energy", 0.0)
    for lt in W["lights"]:
        put(S, lt.data, "energy", {"Key": 2600.0, "Rim": 4200.0, "Top": 1400.0}[lt.name])


def gz(x, y):
    return ground(x, y)


def shots(W):
    M = W["M"]
    L = []
    O = V(0, 0, 0)

    def A(t, S):     # "To land a one-tonne rover on Mars": from the ground, the sky crane coming down out of the sky
        u = ss(seg(t, 0.0, 2.1))
        belly = V(2.0, 1.0, lerp(17.5, 15.5, u))
        hang(S, W, belly, 6.0, burn=1.0, glow=0.0)
        cam(S, V(lerp(-15, -13, u), lerp(-18, -16, u), 1.1), belly + V(0, 0, -4.4), lens=34, fstop=11, clip=0.1)
    L.append((0.0, 2.1, A))

    def B(t, S):     # "NASA hung it": close under the stage, looking up past the cables
        u = ss(seg(t, 2.1, 3.55))
        belly = V(0, 0, 15.0 - 0.6 * u)
        hang(S, W, belly, 6.0)
        a = rad(lerp(-150, -110, u))
        c = belly + V(0, 0, -4.2)
        cam(S, c + V(5.2 * math.cos(a), 5.2 * math.sin(a), -2.6), belly + V(0, 0, -0.2), lens=24, fstop=8, clip=0.05)
    L.append((2.1, 3.55, B))

    def B2(t, S):    # "from a flying rocket": side on, the whole rig against the sky, slow push
        u = ss(seg(t, 3.55, 4.95))
        belly = V(0, 0, 14.0 - 0.6 * u)
        hang(S, W, belly, 6.0)
        cam(S, belly + V(lerp(3, 2, u), lerp(-24, -20, u), -3.2), belly + V(0, 0, -3.6), lens=40, fstop=11, clip=0.1)
    L.append((3.55, 4.95, B2))

    def C(t, S):     # "too heavy for airbags": in the studio the rover drops onto an airbag ball and flattens it
        studio(S, W)
        put(S, W["bags"]["ball"], "hide_render", 0, const=True)
        k = ss(seg(t, 5.55, 5.95))
        sz, sxy = lerp(1.0, 0.58, k), lerp(1.0, 1.22, k)
        for i, v in enumerate((sxy, sxy, sz)):
            put(S, W["bags"]["ball"], "scale", v, i)
        put(S, W["bags"]["ball"], "location", 2.17 * sz, 2)
        top = 4.32 * sz
        z = max(lerp(9.5, top - 0.05, ein(seg(t, 4.95, 5.55))), top - 0.05)
        for i, v in enumerate((ST.x, ST.y, z)):
            put(S, W["R"]["root"], "location", v, i)
        u = ss(seg(t, 4.95, 6.45))
        cam(S, ST + V(lerp(9.5, 8.5, u), -11.0, 3.4), ST + V(0, 0, 3.3), lens=40, fstop=11, clip=0.1)
        label(S, "rover", ST + V(0.0, 0, z + 1.4))
        label(S, "bag", ST + V(-1.6, -1.2, 2.2 * sz))
    L.append((4.95, 6.45, C))

    def blast(S, t, t0=6.45):
        k = seg(t, t0, t0 + 3.4)
        dust(S, W, "dust", V(0, 0, -0.2), lerp(1.5, 9.0, eout(k)), lerp(0.6, 4.0, eout(k)), lerp(0.3, 0.9, ss(k * 3)))
        mset(S, M["reg"], SC=ss(seg(t, t0, t0 + 1.2)))
        for ob in W["fly"]:
            tf = t - (t0 + 0.35 + ob["dt"])
            if tf < 0:
                continue
            p0, v0 = Vector(ob["p0"]), Vector(ob["v0"])
            p = p0 + v0 * tf + V(0, 0, -0.5 * 3.71 * tf * tf)
            if p.z < -0.5:
                continue
            put(S, ob, "hide_render", 0, const=True)
            for i in range(3):
                put(S, ob, "location", p[i], i)
                put(S, ob, "rotation_euler", ob["spin"] * tf * (1, 0.7, 0.4)[i], i)

    def D(t, S):     # "and rockets firing near the ground": a lander with its engines close to the ground
        hang(S, W, V(0, 0, 3.4), 0.0, fold_k=1.0, burn=1.3, burnB=1.3, cables=False, glow=2500.0)
        blast(S, t)
        u = ss(seg(t, 6.45, 8.5))
        sh = 0.5 * seg(t, 6.8, 7.2)
        cam(S, V(lerp(-15, -13, u), lerp(-13, -11, u), 1.6), V(0, 0, 2.2), lens=28, fstop=11, clip=0.1, shake=sh,
            t=t * 4)
    L.append((6.45, 8.5, D))

    def E(t, S):     # "would blast dust and rocks everywhere": low by the ground, stones flying at the lens
        hang(S, W, V(0, 0, 3.4), 0.0, fold_k=1.0, burn=1.3, burnB=1.3, cables=False, glow=2500.0)
        blast(S, t)
        u = ss(seg(t, 8.5, 10.6))
        cam(S, V(lerp(-12.5, -11.5, u), lerp(-8.0, -7.4, u), 0.5), V(0, 0, 1.6), lens=30, fstop=8, clip=0.05,
            shake=0.8, t=t * 5)
    L.append((8.5, 10.6, E))

    def F(t, S):     # "So twenty metres up": side on, a long way down to the ground
        u = ss(seg(t, 10.6, 12.5))
        belly = V(0, 0, 20.5 - 0.4 * u)
        hang(S, W, belly, 0.0, fold_k=1.0, burn=1.0, burnB=lerp(1.0, 0.0, seg(t, 11.9, 12.3)), cables=False,
             glow=800.0)
        dust(S, W, "dustT", V(0, 0, -0.1), 9.0, 1.2, 0.25)
        cam(S, V(lerp(5, 3, u), -31.0, 7.0), V(0, 0, 10.5), lens=40, fstop=16, clip=0.2)
        label(S, "belly", belly)
        label(S, "gnd", V(0, 0, gz(0, 0)))
    L.append((10.6, 12.5, F))

    def G(t, S):     # "the descent stage slows to a crawl": close on the engines, four throttle down, four keep firing
        u = ss(seg(t, 12.5, 14.55))
        belly = V(0, 0, 19.8 - 0.75 * (t - 12.5))
        hang(S, W, belly, 0.0, fold_k=1.0, burn=1.0, burnB=lerp(0.6, 0.0, seg(t, 12.5, 13.1)), cables=False)
        dust(S, W, "dustT", V(0, 0, -0.1), 9.0, 1.2, 0.25)
        a = rad(lerp(-60, -35, u))
        cam(S, belly + V(5.0 * math.cos(a), 5.0 * math.sin(a), lerp(-1.2, -0.8, u)), belly + V(0.9, -0.9, -0.1),
            lens=35, fstop=5.6, clip=0.05)
    L.append((12.5, 14.55, G))

    def H(t, S):     # "and lowers the rover on three nylon cables": from below and to the side, the rover drops away
        u = ss(seg(t, 14.55, 16.97))
        belly = V(0, 0, 18.3 - 0.75 * (t - 14.55))
        Lp = 6.0 * ss(seg(t, 14.6, 16.1))
        rz = hang(S, W, belly, Lp, fold_k=1.0)
        dust(S, W, "dustT", V(0, 0, -0.1), 9.0, 1.2, 0.3)
        cam(S, belly + V(lerp(9.0, 8.0, u), lerp(-13.0, -12.0, u), -5.5), belly + V(0, 0, -4.6), lens=28, fstop=11,
            clip=0.1)
        label(S, "belly", belly + V(0, 0, -0.2))
        label(S, "wheels", V(0, 0, rz))
    L.append((14.55, 16.97, H))

    def I(t, S):     # "Its wheels drop down to become the landing gear": close on one side as the wheels swing down
        belly = V(0, 0, 15.0 - 0.75 * (t - 16.97))
        k = 1.0 - ss(seg(t, 17.35, 18.4))
        rz = hang(S, W, belly, 6.0, fold_k=k)
        u = ss(seg(t, 16.97, 19.36))
        c = V(0.0, 0, rz + 0.7)
        cam(S, c + V(lerp(4.0, 3.4, u), lerp(-4.4, -3.8, u), lerp(-0.2, 0.1, u)), c + V(0, -0.6, -0.1), lens=32,
            fstop=5.6, clip=0.05)
    L.append((16.97, 19.36, I))

    def J(t, S):     # "Once its wheels touch down": low on the ground as the wheels settle in a puff of dust
        td = 20.05
        rz = 0.75 * max(0.0, td - t)
        belly = V(0, 0, rz + HANG + 6.0)
        hang(S, W, belly, 6.0)
        k = seg(t, td - 0.1, td + 1.0)
        dust(S, W, "dustT", V(0, 0, -0.1), lerp(2.0, 6.0, eout(k)), lerp(0.4, 1.0, eout(k)), 0.25 + 0.6 * ss(k))
        u = ss(seg(t, 19.36, 20.92))
        cam(S, V(lerp(5.5, 5.0, u), lerp(-5.0, -4.6, u), 0.35), V(0.0, -0.4, 0.9), lens=26, fstop=5.6, clip=0.05)
    L.append((19.36, 20.92, J))

    def K(t, S):     # "blades slice the cables": on the deck, a flash at each bridle, the cables whip away upwards
        tc = 21.15
        belly = V(0, 0, HANG + 6.0 + 0.5 * ein(seg(t, tc, 22.2)))
        hang(S, W, belly, 6.0, cables=t < tc + 0.05)
        if t >= tc + 0.05:     # the cut ends ride back up into the stage
            g = ss(seg(t, tc, tc + 0.7))
            for b in W["BR"]:
                a = Vector(b["att"])
                put(S, b, "hide_render", 0, const=True)
                for i, v in enumerate((a.x, a.y, belly.z - 0.15)):
                    put(S, b, "location", v, i)
                put(S, b, "scale", max(lerp(belly.z - 0.15 - DECK - 0.06, 0.2, g), 0.05), 2)
        f = seg(t, tc, tc + 0.05) * (1 - seg(t, tc + 0.12, tc + 0.6))
        for sp, b in zip(W["sparks"], W["BR"]):
            a = Vector(b["att"])
            put(S, sp, "hide_render", 0 if f > 0 else 1, const=True)
            for i, v in enumerate((a.x, a.y, DECK + 0.1)):
                put(S, sp, "location", v, i)
        mset(S, M["spark"], S=40.0 * f)
        dust(S, W, "dustT", V(0, 0, -0.1), 6.0, 1.0, 0.7)
        u = ss(seg(t, 20.92, 22.19))
        cam(S, V(lerp(2.6, 2.3, u), lerp(-2.9, -2.6, u), DECK + 2.0), V(-0.1, 0.05, DECK + 0.6), lens=28, fstop=4,
            clip=0.05)
    L.append((20.92, 22.19, K))

    def flight(t):
        """the stage after the cut: climbs, tips over and heads for CR, then dives in"""
        t0 = 21.25
        k = clamp((t - t0) / 3.5)
        kh = ss(seg(k, 0.1, 0.75))
        d = V(CR.x, CR.y, 0).normalized()
        cz = gz(CR.x, CR.y)
        h = lerp(HANG + 6.5, 40.0, kh)
        h = lerp(h, cz + 1.0, ein(seg(k, 0.72, 1.0)))
        p = d * (V(CR.x, CR.y, 0).length * k ** 3.2) + V(0, 0, h)
        yaw = math.degrees(math.atan2(d.y, d.x))
        pitch = 48.0 * ss(seg(k, 0.12, 0.5))
        return p, pitch, yaw, k

    def Lf(t, S):    # "The stage flies away": throttles up, tips and heads off; from beside the rover
        p, pitch, yaw, k = flight(t)
        stage(S, W, p, pitch, yaw, burn=1.3, burnB=1.3)
        put(S, W["R"]["mast"], "rotation_euler", rad(-90.0), 1)
        dust(S, W, "dustT", V(0, 0, -0.1), 8.0, 1.6, 0.9 * (1 - seg(t, 22.2, 24.2)))
        u = ss(seg(t, 22.19, 24.2))
        cam(S, V(lerp(8.0, 8.6, u), lerp(-12.0, -12.8, u), 1.4), p.lerp(V(0, 0, 1.0), lerp(0.45, 0.0, u)),
            lens=lerp(28, 70, ss(u)), fstop=11, clip=0.05)
    L.append((22.19, 24.2, Lf))

    def Mc(t, S):    # "and crashes a safe distance off": wide, the rover in front, the impact far away
        p, pitch, yaw, k = flight(t + 0.6)
        if k < 1.0:
            stage(S, W, p, pitch, yaw, burn=1.3, burnB=1.3)
        ti = 24.75
        g = seg(t, ti, ti + 1.5)
        if t >= ti:
            put(S, W["flash"], "hide_render", 0, const=True)
            for i in range(3):
                put(S, W["flash"], "scale", lerp(2.0, 7.0, eout(seg(t, ti, ti + 0.3))), i)
            mset(S, M["flash"], S=50.0 * (1 - seg(t, ti, ti + 0.45)) ** 2)
            cz = gz(CR.x, CR.y)
            dust(S, W, "dustC", V(CR.x, CR.y, cz - 2.0), lerp(6.0, 20.0, eout(g)), lerp(5.0, 48.0, eout(g)),
                 lerp(0.16, 0.07, g))
        u = ss(seg(t, 24.2, 26.28))
        cam(S, V(lerp(2.2, 2.1, u), lerp(-4.6, -5.1, u), 2.5), V(CR.x, CR.y, gz(CR.x, CR.y) + 12.0), lens=lerp(50, 56, u),
            fstop=16, clip=0.05)
        label(S, "crash", V(CR.x, CR.y, gz(CR.x, CR.y) + 25.0))
    L.append((24.2, 26.28, Mc))

    def N(t, S):     # "Curiosity and Perseverance both landed this way": the rover alone, its mast rising, the sun low
        put(S, W["R"]["mast"], "rotation_euler", rad(lerp(-90, 0, ss(seg(t, 26.5, 27.7)))), 1)
        cz = gz(CR.x, CR.y)
        dust(S, W, "dustC", V(CR.x, CR.y, cz - 2.0), 22.0, 52.0, 0.06)
        u = ss(seg(t, 26.28, 29.27))
        a = rad(lerp(-25, 5, u))
        cam(S, V(6.2 * math.cos(a), 6.2 * math.sin(a), 1.1), V(0, 0, 1.15), lens=35, fstop=5.6, clip=0.05)
        label(S, "roverN", V(0, 0, 2.6))
    L.append((26.28, 29.27, N))

    def P(t, S):     # "Follow for how the world is really engineered": crane up and away over the plain
        put(S, W["R"]["mast"], "rotation_euler", 0.0, 1)
        cz = gz(CR.x, CR.y)
        dust(S, W, "dustC", V(CR.x, CR.y, cz - 2.0), 24.0, 56.0, 0.05)
        u = ss(seg(t, 29.27, T_END))
        cam(S, V(lerp(4.0, 14.0, u), lerp(-6.0, -26.0, u), lerp(1.4, 16.0, u)), V(lerp(0, -40, u), lerp(0, 160, u),
            lerp(1.0, 6.0, u)), lens=lerp(30, 26, u), fstop=16, clip=0.05)
    L.append((29.27, T_END + 0.1, P))
    return L


def camcheck(W):
    L = shots(W)
    for f in range(1, F_END + 1, 6):
        t = (f - 1) / FPS
        fn = next(fn for t0, t1, fn in L if t0 <= t < t1)
        S = {}
        defaults(t, S, W)
        fn(t, S)
        eye = S["cam"][0]
        if abs(eye.x) < 15000:
            clr = eye.z - ground(eye.x, eye.y)
            print("CC %4d %5.2f %-3s clr %7.2f %s" % (f, t, fn.__name__, clr, "UNDERGROUND" if clr < 0.1 else ""))


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = sc_world()
    if os.environ.get("CAMCHECK"):
        camcheck(W)
        sys.exit(0)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_sc.json"))
    if os.environ.get("BAKEONLY"):
        sys.exit(0)
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
