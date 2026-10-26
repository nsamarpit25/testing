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
# ----------------------------------------------------------------------------------------------- storm barrier world
# The Maeslantkering on the Nieuwe Waterweg. Metres, z up, normal water level z = 0, the North Sea towards -x,
# Rotterdam towards +x. The channel is 360 m wide (banks at y = +-180, quays up to z = +5). Each gate is a hollow
# curved steel box (210 m long, 22 m high, 15 m deep) on an arc of radius R round a 10 m ball joint on its bank
# (JN north, JS south), held by a white tubular truss. Closed (swing 0) the gates meet mid-river, convex to the sea;
# parked (swing PARK) each sits in a curved dry dock cut into its bank. A gate's bottom is at zb: -16 resting in a
# dry dock, -7 floating, -17 sunk on the sill. The x-ray set shows the gate as glass with its chambers filling.
import mathutils.noise as mn

T_END = 30.5
F_END = int(T_END * FPS) + 1
CH = 180.0                           # half width of the channel
ZL = 5.0                             # quay / land height
R = 262.0                            # gate arc radius (gate centreline) round the joint
GD, GH = 15.0, 22.0                  # gate depth and height
PSI = math.degrees(210.0 / R) / 2    # half the gate's angular span (deg)
TH_C = 208.25                        # gate centre direction from the north joint when closed (deg, world)
JN = Vector((250.0, 205.0, 0.0))
JS = Vector((250.0, -205.0, 0.0))
ZJ = 4.0                             # ball centre height
PARK = -50.0                         # swing angle in the dock (deg; north gate, the south one mirrors)
ZB_FLOAT, ZB_DOCK, ZB_SUNK = -7.0, -16.0, -17.0
SILL = -17.0
GAUGE = Vector((-470.0, 160.0, 0.0))


def nz(x, y, s, seed=0.0):
    return mn.noise(V(x / s, y / s, seed), noise_basis='PERLIN_ORIGINAL')


def sstepv(nt, x, e0, e1):
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


def gpt(psi, r, z):
    """point in a gate's local frame (x = centre direction from the joint), psi in deg"""
    a = rad(psi)
    return V(r * math.cos(a), r * math.sin(a), z)


def world_pt(side, swing, zb, p):
    """local gate-frame point -> world, for the gate on side (+1 north, -1 south) at swing (deg) and bottom zb"""
    al = math.asin(clamp((ZB_FLOAT - zb) / R, -0.2, 0.2))
    q = Matrix.Rotation(al, 3, "Y") @ (Vector(p) - V(0, 0, ZJ)) + V(0, 0, ZJ)
    th = rad(TH_C + swing)
    q = Matrix.Rotation(th, 3, "Z") @ q
    if side < 0:
        q = V(q.x, -q.y, q.z)
    return (JN if side > 0 else JS) + q


# ----------------------------------------------------------------------------------------------- materials

def paint_mat(name, col, rough=0.32, coat=0.6, grime=0.25, seams=0.0):
    """painted steel with soft streaky grime and optional plate seams (local coords)"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    g = noise(nt, P, 0.08, 6.0, 0.6, stretch=(1.0, 1.0, 0.18))
    dirt = mth(nt, "MULTIPLY", sstep(nt, g, 0.45, 0.75), grime)
    base = col_mix(nt, col, "#1a1714", dirt)
    rough_s = mth(nt, "ADD", rough, mth(nt, "MULTIPLY", dirt, 0.4))
    b = principled(nt, base, rough_s, 0.0, coat, 0.12)
    if seams:
        sz = mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "DIVIDE", z, 2.75)), 0.5))
        s1 = sstep(nt, sz, 0.47, 0.5)
        ang = mth(nt, "ARCTAN2", y, x)
        sa = mth(nt, "ABSOLUTE", mth(nt, "SUBTRACT", mth(nt, "FRACT", mth(nt, "MULTIPLY", ang, R / 12.0)), 0.5))
        s2 = sstep(nt, sa, 0.475, 0.5)
        h = mth(nt, "MAXIMUM", s1, s2)
        bump = node(nt, "ShaderNodeBump")
        bump.inputs["Distance"].default_value = 0.06
        bump.inputs["Strength"].default_value = seams
        link(nt, mth(nt, "SUBTRACT", 1.0, h), bump.inputs["Height"])
        link(nt, bump.outputs[0], b.inputs["Normal"])
    XA = val(nt, "XA", 0.0)
    gl = ghost(nt)
    link(nt, mix_sh(nt, XA, b.outputs[0], gl), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    m.diffuse_color = (*lin(col), 1)
    return m


def ghost(nt, col="#7fe0ff", edge=2.2, face=0.03):
    """x-ray glass: mostly transparent with a glowing fresnel edge"""
    lw = node(nt, "ShaderNodeLayerWeight")
    lw.inputs[0].default_value = 0.35
    fr = mth(nt, "POWER", lw.outputs["Facing"], 2.0)
    e = emission(nt, col, mth(nt, "MULTIPLY_ADD", fr, edge, face))
    tr = node(nt, "ShaderNodeBsdfTransparent")
    sh = node(nt, "ShaderNodeAddShader")
    link(nt, tr.outputs[0], sh.inputs[0])
    link(nt, e, sh.inputs[1])
    return sh.outputs[0]


def ghost_mat(name, col="#7fe0ff", edge=2.2, face=0.03):
    m, nt, out = new_mat(name)
    link(nt, ghost(nt, col, edge, face), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def fill_mat():
    """the water let into a gate's hollows: glowing blue below the fill height FH (local z), nothing above"""
    m, nt, out = new_mat("Fill")
    P = obj_co(nt)
    _, _, z = xyz(nt, P)
    FH = val(nt, "FH", -100.0)
    k = mth(nt, "LESS_THAN", z, FH)
    top = mul(nt, k, sstepv(nt, z, mth(nt, "SUBTRACT", FH, 0.6), FH))
    nzv = noise(nt, P, 0.15, 3.0, 0.5)
    e = emission(nt, col_mix(nt, "#0b5fd6", "#7fe6ff", mth(nt, "MULTIPLY_ADD", top, 0.8, mth(nt, "MULTIPLY", nzv, 0.25))),
                 mth(nt, "MULTIPLY_ADD", top, 5.0, 1.1))
    tr = node(nt, "ShaderNodeBsdfTransparent")
    link(nt, mix_sh(nt, mth(nt, "MULTIPLY", k, 0.82), tr.outputs[0], e), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def water_mat(name="Water", edge=0.3, face=0.004, gcol="#5fd0ff"):
    """dark North Sea water: glossy, foam from the ocean modifier, fine ripples; XA turns it into a glass sheet"""
    m, nt, out = new_mat(name)
    P = node(nt, "ShaderNodeTexCoord").outputs["Object"]
    foam = attr(nt, "foam")
    FO = val(nt, "FO", 1.0)
    f = mth(nt, "MULTIPLY", sstep(nt, foam, 0.25, 0.85), FO)
    fn = noise(nt, P, 0.35, 5.0, 0.6)
    f = mth(nt, "MULTIPLY", f, sstep(nt, fn, 0.35, 0.6))
    n4 = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")      # churning foam for water pouring in (FN, FW)
    n4.inputs["Scale"].default_value = 0.12
    n4.inputs["Detail"].default_value = 6.0
    n4.inputs["Roughness"].default_value = 0.6
    link(nt, P, n4.inputs["Vector"])
    link(nt, val(nt, "FW", 0.0), n4.inputs["W"])
    f = mth(nt, "MAXIMUM", f, mul(nt, val(nt, "FN", 0.0), sstep(nt, n4.outputs["Fac"], 0.42, 0.62)))
    base = col_mix(nt, "#0a1517", "#c9d2d6", f)
    b = principled(nt, base, mth(nt, "MULTIPLY_ADD", f, 0.5, 0.035), 0.0)
    b.inputs["IOR"].default_value = 1.33
    h = noise(nt, P, 0.6, 6.0, 0.62, stretch=(1.0, 2.2, 1.0))
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.08
    link(nt, val(nt, "RB", 0.5), bump.inputs["Strength"])
    link(nt, h, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    XA = val(nt, "XA", 0.0)
    link(nt, mix_sh(nt, XA, b.outputs[0], ghost(nt, gcol, edge, face)), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def land_mat():
    """quays: grass on top with a concrete apron along the water and round the docks; concrete walls, darker and
    slimy below the waterline"""
    m, nt, out = new_mat("Land")
    gc = node(nt, "ShaderNodeNewGeometry")
    P = gc.outputs["Position"]
    x, y, z = xyz(nt, P)
    _, _, nzz = xyz(nt, gc.outputs["Normal"])
    top = sstep(nt, nzz, 0.6, 0.8)
    ay = mth(nt, "ABSOLUTE", y)
    jy = mth(nt, "SUBTRACT", ay, JN.y)
    dj = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", mth(nt, "SUBTRACT", x, JN.x), mth(nt, "SUBTRACT", x, JN.x)),
                             mth(nt, "MULTIPLY", jy, jy)))
    apron = mth(nt, "MAXIMUM", inv(nt, sstep(nt, ay, CH + 22, CH + 26)),
                mul(nt, sstep(nt, dj, R - 30, R - 26), inv(nt, sstep(nt, dj, R + 26, R + 30))))
    apron = mth(nt, "MAXIMUM", apron, inv(nt, sstep(nt, dj, 34, 38)))
    n1 = noise(nt, P, 0.01, 6.0, 0.6)
    n2 = noise(nt, P, 0.3, 4.0, 0.6)
    grass = col_mix(nt, "#27301c", "#3b4526", n1)
    conc = col_mix(nt, "#8d8b85", "#6d6a64", n2)
    topc = col_mix(nt, grass, conc, apron)
    wet = inv(nt, sstep(nt, z, -0.5, 1.2))
    wall = col_mix(nt, col_mix(nt, "#7d7a73", "#5e5b55", n2), "#20241c", wet)
    c = col_mix(nt, wall, topc, top)
    rough = mth(nt, "SUBTRACT", 0.85, mth(nt, "MULTIPLY", mth(nt, "ADD", wet, mth(nt, "MULTIPLY", apron, 0.25)), 0.4))
    b = principled(nt, c, rough, 0.0)
    h = noise(nt, P, 0.8, 5.0, 0.6)
    bump = node(nt, "ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.05
    bump.inputs["Strength"].default_value = 0.3
    link(nt, h, bump.inputs["Height"])
    link(nt, bump.outputs[0], b.inputs["Normal"])
    XA = val(nt, "XA", 0.0)
    link(nt, mix_sh(nt, XA, b.outputs[0], ghost(nt, "#5fd0ff", 0.5, 0.01)), out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except Exception:
        pass
    return m


def storm_world():
    """an overcast sky built from the view direction: cloud bands, a bright gap at the horizon; STORM blends a dark
    stormy dusk (1) with a calm golden evening (0); FL is a lightning flash; XR fades to an x-ray void"""
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
    D = node(nt, "ShaderNodeTexCoord").outputs["Generated"]
    dx, dy, dz = xyz(nt, D)
    ST = val(nt, "STORM", 1.0)
    FL = val(nt, "FL", 0.0)
    XR = val(nt, "XR", 0.0)
    BGS = val(nt, "BGS", 1.0)
    e = mth(nt, "MAXIMUM", dz, -0.2)
    cz = mth(nt, "ADD", mth(nt, "MAXIMUM", dz, 0.0), 0.06)
    pxy = node(nt, "ShaderNodeCombineXYZ")
    link(nt, mth(nt, "DIVIDE", dx, cz), pxy.inputs[0])
    link(nt, mth(nt, "DIVIDE", dy, cz), pxy.inputs[1])
    link(nt, val(nt, "CW", 0.0), pxy.inputs[2])
    n1 = node(nt, "ShaderNodeTexNoise", noise_dimensions="3D")
    n1.inputs["Scale"].default_value = 0.55
    n1.inputs["Detail"].default_value = 9.0
    n1.inputs["Roughness"].default_value = 0.62
    link(nt, pxy.outputs[0], n1.inputs["Vector"])
    cl = n1.outputs["Fac"]
    dense = sstep(nt, cl, 0.38, 0.62)
    # stormy dusk
    sky_s = ramp3(nt, e, [(0.0, "#3a4550"), (0.03, "#8a96a2"), (0.1, "#4f5a65"), (0.3, "#323b44"), (1.0, "#1e252c")])
    cloud_s = ramp3(nt, e, [(0.0, "#323a42"), (0.05, "#4c555e"), (0.25, "#262d34"), (1.0, "#14191e")])
    storm = col_mix(nt, sky_s, cloud_s, mth(nt, "MULTIPLY", dense, 0.85))
    # calm golden evening
    sky_c = ramp3(nt, e, [(0.0, "#c08a5a"), (0.03, "#f2c08a"), (0.1, "#c9a888"), (0.35, "#7f8fa3"), (1.0, "#4e6178")])
    cloud_c = ramp3(nt, e, [(0.0, "#a87048"), (0.06, "#d8a074"), (0.3, "#8a7a78"), (1.0, "#56607a")])
    calm = col_mix(nt, sky_c, cloud_c, mth(nt, "MULTIPLY", dense, 0.65))
    col = col_mix(nt, calm, storm, ST)
    fl = col_mix(nt, col, "#c8d8ff", mth(nt, "MULTIPLY", FL, mth(nt, "MULTIPLY_ADD", dense, 0.6, 0.4)))
    below = sstep(nt, dz, -0.08, 0.0)
    fl = col_mix(nt, "#0d1316", fl, below)
    xc = col_mix(nt, fl, "#020406", XR)
    bg = node(nt, "ShaderNodeBackground")
    link(nt, xc, bg.inputs[0])
    link(nt, BGS, bg.inputs[1])
    link(nt, bg.outputs[0], out.inputs["Surface"])
    return w


# ----------------------------------------------------------------------------------------------- geometry

def bm_arcbox(bm, r0, r1, z0, z1, p0, p1, n=96, rr=0.6, M=None):
    """a curved box: radius r0..r1, height z0..z1, angle p0..p1 (deg), rounded section corners"""
    prof = fillet([(r0, z0), (r1, z0), (r1, z1), (r0, z1)], rr, 4)
    rings = []
    for k in range(n + 1):
        a = rad(lerp(p0, p1, k / n))
        rings.append([V(p.x * math.cos(a), p.x * math.sin(a), p.y) for p in prof])
    vs = bm_loft(bm, rings)
    fs = list({f for ring in vs for v in ring for f in v.link_faces})
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    if M is not None:
        for ring in vs:
            for v in ring:
                v.co = M @ v.co


def build_gate(name, M, parent):
    """one gate in its tilt frame: shell, inner ribs, top rail, chamber walls and the fill"""
    obs = {}
    z0, z1 = ZB_FLOAT, ZB_FLOAT + GH
    bm = bmesh.new()
    bm_arcbox(bm, R - GD / 2, R + GD / 2, z0, z1, -PSI, PSI, 220, 0.9)
    obs["shell"] = obj_from_bm(name + "Shell", bm, M["gate"], parent, smooth=True)
    weighted(obs["shell"])
    bm = bmesh.new()   # vertical ribs on the inner (truss) face
    for k in range(17):
        p = lerp(-PSI + 0.6, PSI - 0.6, k / 16)
        bm_arcbox(bm, R - GD / 2 - 1.1, R - GD / 2 + 0.2, z0 + 0.6, z1 - 0.6, p - 0.12, p + 0.12, 2, 0.25)
    for zz in (z0 + 4.0, z1 - 3.0):        # two horizontal walers
        bm_arcbox(bm, R - GD / 2 - 0.9, R - GD / 2 + 0.2, zz - 0.5, zz + 0.5, -PSI + 0.3, PSI - 0.3, 160, 0.25)
    obs["ribs"] = obj_from_bm(name + "Ribs", bm, M["gate"], parent, smooth=True)
    bm = bmesh.new()   # white top band
    bm_arcbox(bm, R - GD / 2 - 0.05, R + GD / 2 + 0.05, z1 - 1.4, z1 + 0.05, -PSI - 0.02, PSI + 0.02, 220, 0.3)
    obs["band"] = obj_from_bm(name + "Band", bm, M["truss"], parent, smooth=True)
    bm = bmesh.new()   # deck railing
    for rr in (R - GD / 2 + 0.6, R + GD / 2 - 0.6):
        pts = [gpt(lerp(-PSI + 0.3, PSI - 0.3, k / 120), rr, z1 + 1.1) for k in range(121)]
        bm_tube(bm, pts, 0.07, 6)
        for k in range(0, 121, 3):
            p = pts[k]
            bm_rod(bm, p - V(0, 0, 1.1), p, 0.05, 5)
    obs["rail"] = obj_from_bm(name + "Rail", bm, M["rail"], parent, smooth=True)
    bm = bmesh.new()   # lamps along the deck
    for k in range(9):
        p = gpt(lerp(-PSI + 1.0, PSI - 1.0, k / 8), R, z1 + 0.6)
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.35, matrix=Matrix.Translation(p))
    obs["lamps"] = obj_from_bm(name + "Lamps", bm, M["lamp"], parent, smooth=True)
    bm = bmesh.new()   # chambers (only seen in x-ray): radial bulkheads and a mid deck
    for k in range(1, 8):
        p = lerp(-PSI, PSI, k / 8)
        bm_arcbox(bm, R - GD / 2 + 0.3, R + GD / 2 - 0.3, z0 + 0.3, z1 - 0.3, p - 0.06, p + 0.06, 1, 0.05)
    bm_arcbox(bm, R - GD / 2 + 0.3, R + GD / 2 - 0.3, z0 + 9.5, z0 + 9.8, -PSI + 0.2, PSI - 0.2, 120, 0.05)
    obs["walls"] = obj_from_bm(name + "Walls", bm, M["xwall"], parent)
    bm = bmesh.new()
    bm_arcbox(bm, R - GD / 2 + 0.4, R + GD / 2 - 0.4, z0 + 0.4, z1 - 0.4, -PSI + 0.15, PSI - 0.15, 160, 0.3)
    obs["fill"] = obj_from_bm(name + "Fill", bm, M["fill"], parent)
    return obs


def build_truss(name, M, parent):
    """the white tubular truss from the knuckle at the ball to the gate's inner face"""
    bm = bmesh.new()
    rin = R - GD / 2 - 1.0
    ztop, zlow = ZB_FLOAT + GH - 2.5, ZB_FLOAT + GH - 11.0
    knuck = V(7.0, 0, ZJ)
    chords = []
    for ps in (-PSI + 2.5, PSI - 2.5):
        A = gpt(ps, rin, 0)
        d = (A - V(0, 0, 0)).normalized()
        s = V(-d.y, d.x, 0)
        cs = []
        for oz, os_ in ((ztop, -4.0), (ztop, 4.0), (zlow, -4.0), (zlow, 4.0)):
            p1 = V(A.x, A.y, 0) + s * os_ + V(0, 0, oz)
            p0 = knuck + s * (os_ * 0.25) + V(0, 0, (oz - ZJ) * 0.25) + d * 4.0
            cs.append((p0, p1))
            bm_rod(bm, p0, p1, 1.0, 16)
        chords.append(cs)
        n = 13
        for k in range(1, n + 1):
            u0, u1 = (k - 1) / n, k / n
            P = [[p0.lerp(p1, u) for p0, p1 in cs] for u in (u0, u1)]
            for a, b in ((0, 1), (2, 3), (0, 2), (1, 3)):          # diagonals on the four faces
                bm_rod(bm, P[0][a], P[1][b], 0.42, 10)
            for a, b in ((0, 1), (2, 3), (0, 2), (1, 3)):          # rings
                bm_rod(bm, P[1][a], P[1][b], 0.36, 10)
    # lattice between the two arms
    L, Rr = chords
    n = 9
    for k in range(1, n + 1):
        u0, u1 = (k - 0.5) / (n + 0.5), (k + 0.5) / (n + 0.5)
        for zi in (0, 2):
            a = L[zi][0].lerp(L[zi][1], u0)
            b = Rr[zi + 1][0].lerp(Rr[zi + 1][1], u1)
            bm_rod(bm, a, b, 0.5, 10)
            c = Rr[zi + 1][0].lerp(Rr[zi + 1][1], u0)
            d = L[zi][0].lerp(L[zi][1], u1)
            bm_rod(bm, c, d, 0.5, 10)
    ob = obj_from_bm(name, bm, M["truss"], parent, smooth=True)
    bm = bmesh.new()   # the yoke that grips the ball: a collar round its upper half and a block the chords meet
    bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=4.75)
    ring = [v for v in bm.verts]
    prof = fillet([(4.3, ZJ + 1.0), (6.2, ZJ + 1.0), (6.2, ZJ + 3.4), (3.4, ZJ + 3.4)], 0.4, 4)
    for v in ring:
        bm.verts.remove(v)
    rings = []
    for k in range(97):
        a = 2 * math.pi * k / 96
        rings.append([V(p.x * math.cos(a), p.x * math.sin(a), p.y) for p in prof])
    bm_loft(bm, rings)
    bm_rbox(bm, (9.5, 0, ZJ + 1.0), (9.0, 9.0, 7.0), r=1.2, segs=4)
    head = obj_from_bm(name + "Head", bm, M["truss"], parent, smooth=True)
    weighted(head)
    return ob, head


def build_joint(name, M, J, side):
    """the ball (on the moving frame) and its concrete foundation block (fixed)"""
    bm = bmesh.new()
    bm_rbox(bm, (0, 0, -4.0), (26.0, 30.0, 18.0), r=1.0, segs=4)
    base = obj_from_bm(name + "Base", bm, M["conc"], None, J + V(-4.0 * 0 - 6.0, 0, 0), smooth=True)
    bm = bmesh.new()
    bm_cyl(bm, 7.6, 6.6, 3.0, 96, Matrix.Translation(V(0, 0, 5.5)))
    seat = obj_from_bm(name + "Seat", bm, M["steel"], None, J, smooth=True)
    weighted(seat)
    return base, seat


XDOCK = []
DOCKX = []


def build_land(M):
    """both banks as slabs, with the curved dock slots cut out by booleans"""
    obs = []
    for side, J in ((1, JN), (-1, JS)):
        bm = bmesh.new()
        bm_box(bm, (0, side * (CH + 3000), (ZL - 30) / 2), (12000.0, 6000.0, ZL + 30))
        land = obj_from_bm("Land" + ("N" if side > 0 else "S"), bm, M["land"])
        bm = bmesh.new()
        r0, r1 = R - GD / 2 - 9.0, R + GD / 2 + 9.0
        th0, th1 = TH_C + PARK - PSI - 3.0, 190.0
        bm_arcbox(bm, r0, r1, ZB_DOCK, ZL + 20, th0, th1, 140, 0.0)
        if side < 0:
            for v in bm.verts:
                v.co.y = -v.co.y
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        cut = obj_from_bm("Cut", bm, None, None, J)
        bm = bmesh.new()
        bm_arcbox(bm, r0, r1, ZB_DOCK, ZL, th0, 185.0, 140, 0.3)
        if side < 0:
            for v in bm.verts:
                v.co.y = -v.co.y
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        gh = obj_from_bm("XDock" + ("N" if side > 0 else "S"), bm, M["xdock"], None, J)
        gh.hide_render = True
        XDOCK.append(gh)
        bm = bmesh.new()       # the joint pit
        bm_cyl(bm, 30.0, 30.0, 40.0, 96, Matrix.Translation(V(0, 0, 10.0)))
        pit = obj_from_bm("Pit", bm, None, None, J + V(-6, 0, -4.0))
        for c in (cut, pit):
            md = land.modifiers.new("B", "BOOLEAN")
            md.operation = "DIFFERENCE"
            md.solver = "EXACT"
            md.object = c
            bpy.context.view_layer.objects.active = land
            bpy.ops.object.modifier_apply(modifier="B")
            bpy.data.objects.remove(c)
        bv = land.modifiers.new("Bv", "BEVEL")
        bv.width, bv.segments, bv.limit_method = 0.4, 3, "ANGLE"
        weighted(land)
        obs.append(land)
    bm = bmesh.new()
    bm_box(bm, (0, 0, SILL - 1.0), (6000.0, 2 * CH + 40, 2.0))
    obs.append(obj_from_bm("Bed", bm, M["bed"]))
    bm = bmesh.new()
    for sgn in (1, -1):
        M_ = Matrix.Translation(JN if sgn > 0 else JS) @ (Matrix.Scale(-1, 4, V(0, 1, 0)) if sgn < 0 else Matrix())
        bm_arcbox(bm, R - GD / 2 - 6, R + GD / 2 + 6, SILL - 2.0, SILL, TH_C - PSI - 1.0, TH_C + PSI + 1.0, 120, 0.4,
                  M=M_)
    obs.append(obj_from_bm("Sill", bm, M["conc"], smooth=True))
    return obs


def build_sea(M):
    """the river surface: a 2.5 m grid between the quays, displaced by an ocean modifier (with foam)"""
    bm = bmesh.new()
    x0, x1, y0, y1, st = -1100.0, 1300.0, -CH - 2.0, CH + 2.0, 2.5
    nx, ny = int((x1 - x0) / st) + 1, int((y1 - y0) / st) + 1
    vs = [bm.verts.new((x0 + i * st, y0 + j * st, 0.0)) for j in range(ny) for i in range(nx)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 1], vs[a + nx]))
    sea = obj_from_bm("Sea", bm, M["water"], smooth=True)
    oc = sea.modifiers.new("Ocean", "OCEAN")
    oc.geometry_mode = "DISPLACE"
    oc.resolution = 9
    oc.spatial_size = 160
    oc.wave_scale = 1.6
    oc.choppiness = 1.3
    oc.wind_velocity = 22.0
    oc.wave_alignment = 0.6
    oc.wave_direction = 0.0
    oc.random_seed = 7
    oc.use_foam = True
    oc.foam_layer_name = "foam"
    oc.foam_coverage = 0.25
    oc.time = 0.0
    bm = bmesh.new()       # far water beyond the grid's ends, out to the horizon (bump only)
    bm_box(bm, (-1098.0 - 30000.0, 0, -0.5), (60000.0, 60000.0, 0.2))
    bm_box(bm, (1298.0 + 4000.0, 0, -0.5), (8000.0, 2 * CH + 4, 0.2))
    far = obj_from_bm("FarSea", bm, M["water"])
    bm = bmesh.new()       # the water inside each dock, raised as it floods
    docks = []
    for side, J in ((1, JN), (-1, JS)):
        bm = bmesh.new()
        bm_arcbox(bm, R - GD / 2 - 8.9, R + GD / 2 + 8.9, 0.0, -ZB_DOCK, TH_C + PARK - PSI - 2.9, 184.0, 120, 0.0)
        if side < 0:
            for v in bm.verts:
                v.co.y = -v.co.y
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        d = obj_from_bm("Dock" + ("N" if side > 0 else "S"), bm, M["dockwater"], None, J)
        docks.append(d)
        dx = bpy.data.objects.new(d.name + "X", d.data.copy())     # its x-ray twin: glowing blue water
        dx.data.materials.clear()
        dx.data.materials.append(M["dockfill"])
        bpy.context.scene.collection.objects.link(dx)
        dx.location = d.location
        dx.hide_render = True
        DOCKX.append(dx)
    return sea, far, docks


def build_gauge(M):
    """a tide staff by the north quay near the sea: a white post with metre marks and a red band at +3 m"""
    root = empty("Gauge", GAUGE)
    bm = bmesh.new()
    bm_rbox(bm, (0, 0, -3.0), (0.9, 0.5, 14.0), r=0.08, segs=3)
    obj_from_bm("GaugePost", bm, M["gaugepost"], root, smooth=True)
    bm = bmesh.new()
    for k in range(-2, 4):
        bm_rbox(bm, (0, -0.27, k), (1.0, 0.06, 0.1), r=0.02, segs=2)
        for j in range(1, 10):
            if j == 5:
                bm_rbox(bm, (0.18, -0.27, k + j / 10), (0.55, 0.05, 0.05), r=0.01, segs=1)
            else:
                bm_rbox(bm, (0.3, -0.27, k + j / 10), (0.3, 0.05, 0.035), r=0.01, segs=1)
    obj_from_bm("GaugeMarks", bm, M["ink"], root, smooth=True)
    bm = bmesh.new()
    bm_rbox(bm, (0, 0, 3.0), (0.96, 0.56, 0.35), r=0.05, segs=2)
    obj_from_bm("GaugeRed", bm, M["red"], root, smooth=True)
    for k in range(0, 4):
        t = text("GaugeN%d" % k, str(k), 0.55, V(-0.22, -0.31, k + 0.45), (rad(90), 0, 0), M["ink"], root, 0.02)
    bm = bmesh.new()       # a mooring dolphin it is bolted to
    bm_cyl(bm, 1.6, 1.6, 22.0, 48, Matrix.Translation(V(0.0, 1.4, -8.0)))
    obj_from_bm("GaugePile", bm, M["conc"], root, smooth=True)
    return root


def build_rain(M, n=4500, seed=3):
    """rain streaks in a box round the camera (parented to it in the shots)"""
    random.seed(seed)
    bm = bmesh.new()
    for _ in range(n):
        p = V(random.uniform(-14, 14), random.uniform(-25, 25), random.uniform(-60, -2))
        L = random.uniform(0.4, 0.9)
        w = random.uniform(0.004, 0.008)
        for ex, ey in ((w, 0), (0, w)):                  # crossed, so it reads from any side
            a = bm.verts.new(p + V(-ex, -ey, -L / 2))
            b = bm.verts.new(p + V(ex, ey, -L / 2))
            c = bm.verts.new(p + V(ex, ey, L / 2))
            d = bm.verts.new(p + V(-ex, -ey, L / 2))
            bm.faces.new((a, b, c, d))
    return obj_from_bm("Rain", bm, M["rain"])


def build_bolt(M, seed=11):
    """a lightning bolt: a jagged main channel from the cloud base to the sea with a few forks"""
    random.seed(seed)
    bm = bmesh.new()

    def channel(p, n, step, spread, r):
        pts = [p]
        for _ in range(n):
            p = p + V(random.gauss(0, spread), random.gauss(0, spread * 0.5), -step * random.uniform(0.6, 1.3))
            pts.append(p)
        bm_tube(bm, pts, r, 6)
        return pts

    main = channel(V(0, 0, 720), 40, 18.0, 9.0, 1.6)
    for k in (8, 15, 24):
        channel(main[k], 9, 14.0, 12.0, 0.8)
    return obj_from_bm("Bolt", bm, M["bolt"])


def sb_materials():
    M = {}
    M["gate"] = paint_mat("Gate", "#5d646c", 0.34, 0.5, 0.35, seams=0.6)
    M["truss"] = paint_mat("Truss", "#e9e8e2", 0.22, 0.8, 0.15)
    M["rail"] = paint_mat("RailM", "#d9d7cf", 0.4, 0.0, 0.1)
    M["lamp"] = emis("Lamp", "#ffcf8a", 30.0)
    M["xwall"] = ghost_mat("XWall", "#7fe0ff", 1.4, 0.05)
    M["xdock"] = ghost_mat("XDock", "#5fd0ff", 1.2, 0.03)
    M["fill"] = fill_mat()
    M["dockfill"] = fill_mat()
    M["dockfill"].name = "DockFill"
    M["dockfill"].node_tree.nodes["FH"].outputs[0].default_value = 100.0
    M["water"] = water_mat()
    M["dockwater"] = water_mat("DockWater", 1.0, 0.3, "#2f8fff")
    M["land"] = land_mat()
    M["conc"] = paint_mat("Concrete", "#8a8780", 0.8, 0.0, 0.45)
    M["bed"] = pbr("Bed", "#1d1a16", 0.95)
    M["steel"] = pbr("Steel", "#9aa0a6", 0.18, 1.0)
    M["ball"] = paint_mat("Ball", "#d5d9dc", 0.2, 0.6, 0.05)
    M["gaugepost"] = paint_mat("GaugePostM", "#f1efe8", 0.4, 0.3, 0.2)
    M["ink"] = pbr("Ink", "#101114", 0.5)
    M["red"] = pbr("RedBand", "#d92b1e", 0.35, 0.0, emit="#ff3020", estr=0.0)
    nt = M["red"].node_tree
    link(nt, val(nt, "S", 0.0), nt.nodes["Principled BSDF"].inputs["Emission Strength"])
    M["rain"] = emis("RainM", "#cfe0ee", 0.0, alpha=0.22)
    M["bolt"] = emis("BoltM", "#e4ecff", 0.0)
    return M


def haze_box(c, s):
    m, nt, out = new_mat("Haze")
    v = node(nt, "ShaderNodeVolumeScatter")
    v.inputs["Color"].default_value = (*lin("#c3ccd4"), 1)
    v.inputs["Anisotropy"].default_value = 0.35
    link(nt, val(nt, "HZ", 0.0006), v.inputs["Density"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    bm = bmesh.new()
    bm_box(bm, c, s)
    return obj_from_bm("HazeBox", bm, m)


def spot(name, loc, tgt, col, energy, size=1.0, angle=40.0):
    ld = bpy.data.lights.new(name, "SPOT")
    ld.color = lin(col)
    ld.energy = energy
    ld.shadow_soft_size = size
    ld.spot_size = rad(angle)
    ld.spot_blend = 0.6
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y")
    return ob


def build_sb():
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    M = sb_materials()
    world = storm_world()
    land = build_land(M)
    sea, far, docks = build_sea(M)
    G = {}
    for side, J in ((1, JN), (-1, JS)):
        k = "N" if side > 0 else "S"
        root = empty("Root" + k, J)
        root.scale = (1.0, float(side), 1.0)
        piv = empty("Piv" + k, (0, 0, 0), root)
        ori = empty("Ori" + k, (0, 0, 0), piv)
        ori.rotation_euler = (0, 0, rad(TH_C))
        tilt = empty("Tilt" + k, (0, 0, ZJ), ori)
        geo = empty("Geo" + k, (0, 0, -ZJ), tilt)
        g = build_gate("Gate" + k, M, geo)
        tr, head = build_truss("Truss" + k, M, geo)
        ball = sphere("Ball" + k, 5.0, (0, 0, ZJ), M["ball"], geo, seg=64)
        base, seat = build_joint("Joint" + k, M, J, side)
        G[k] = dict(root=root, piv=piv, tilt=tilt, geo=geo, truss=tr, head=head, ball=ball, base=base, seat=seat, **g)
    gauge = build_gauge(M)
    rain = build_rain(M)
    bolt = build_bolt(M)
    haze = haze_box((0, 0, 140), (9000.0, 9000.0, 300.0))
    sd = V(-0.94, 0.25, 0.22).normalized()
    sun = sun_lamp(V(-sd.x, -sd.y, -sd.z) * -1, 1.2, "#b9c6d4", angle=3.0)
    flash = sun_lamp(V(0.3, -0.5, 1.0), 0.0, "#cfe0ff", angle=8.0)
    flash.name = "Flash"
    floods = []
    for side, J in ((1, JN), (-1, JS)):
        for off, tg in ((V(-30, 30 * side, 18), V(-120, -60 * side, 8)), (V(40, -10 * side, 22), V(-60, -110 * side, 10)),
                        (V(-10, -25 * side, 16), V(0, 0, 6))):
            floods.append(spot("Flood", J + off, J + tg, "#ffc98a", 3e5, 2.0, 70.0))
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.05, 60000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    return dict(M=M, world=world, land=land, sea=sea, far=far, docks=docks, G=G, gauge=gauge, rain=rain, haze=haze, bolt=bolt,
                sun=sun, flash=flash, floods=floods, cam=camo, hero=None)
# ----------------------------------------------------------------------------------------------- film
# blender -b --factory-startup -P sb.py -- film <outdir> <height> <samples> <a-b | f,f,f>
OCEAN_T = 'modifiers["Ocean"].time'
OCEAN_W = 'modifiers["Ocean"].wave_scale'


def wnode(W, name):
    return W["world"].node_tree, f'nodes["{name}"].outputs[0].default_value'


def wset(S, W, **kw):
    for k, v in kw.items():
        put(S, *wnode(W, k), v)


def gate_parts(W, k):
    return [o for n, o in W["G"][k].items() if n not in ("root", "piv", "tilt", "geo")]


def defaults(t, S, W):
    M = W["M"]
    wset(S, W, STORM=1.0, FL=0.0, XR=0.0, BGS=1.3, CW=t * 0.004)
    put(S, W["sun"].data, "energy", 3.0)
    put(S, W["sun"].data, "color", 0.73, 0)
    put(S, W["sun"].data, "color", 0.78, 1)
    put(S, W["sun"].data, "color", 0.83, 2)
    put(S, W["flash"].data, "energy", 0.0)
    for f in W["floods"]:
        put(S, f.data, "energy", 3e5)
    put(S, W["sea"], OCEAN_T, 20.0 + t * 1.0)
    put(S, W["sea"], OCEAN_W, 1.6)
    put(S, W["sea"], "location", 0.0, 2)
    mset(S, M["water"], XA=0.0, RB=0.5, FO=1.0)
    mset(S, M["dockwater"], XA=0.0, RB=0.15, FO=0.0, FN=0.0, FW=t * 0.6)
    for m in ("gate", "truss", "rail", "land", "conc", "ball"):
        mset(S, M[m], XA=0.0)
    mset(S, M["fill"], FH=-100.0)
    mset(S, M["lamp"], S=30.0)
    mset(S, M["red"], S=0.0)
    mset(S, M["rain"], S=0.0)
    put(S, W["haze"].data.materials[0].node_tree, 'nodes["HZ"].outputs[0].default_value', 0.0006)
    for ob in (W["haze"], W["sea"], W["far"], *W["docks"], *W["land"]):
        hide(S, ob, False)
    for ob in XDOCK:
        hide(S, ob, True)
    hide(S, W["rain"], True)
    hide(S, W["bolt"], True)
    mset(S, M["bolt"], S=0.0)
    for k in ("N", "S"):
        for ob in gate_parts(W, k):
            hide(S, ob, ob.name.startswith(("GateNWalls", "GateSWalls", "GateNFill", "GateSFill")))
    dock_level(S, W, ZB_DOCK - 1.0)
    gates(S, W, PARK, ZB_DOCK)


def gates(S, W, swing, zb, swing_s=None):
    """both gates at swing (deg, 0 = closed) with their bottoms at zb"""
    al = math.asin(clamp((ZB_FLOAT - zb) / R, -0.2, 0.2))
    for k, sw in (("N", swing), ("S", swing if swing_s is None else swing_s)):
        put(S, W["G"][k]["piv"], "rotation_euler", rad(sw), 2)
        put(S, W["G"][k]["tilt"], "rotation_euler", al, 1)


def dock_level(S, W, z, xr=False):
    """the dock water is a box from the dock floor up to z"""
    for d in W["docks"]:
        put(S, d, "location", ZB_DOCK, 2)
        put(S, d, "scale", max(z - ZB_DOCK, 0.01) / -ZB_DOCK, 2)
        hide(S, d, z < ZB_DOCK + 0.05 or xr)
    for d in DOCKX:
        put(S, d, "location", ZB_DOCK, 2)
        put(S, d, "scale", max(z - ZB_DOCK, 0.01) / -ZB_DOCK, 2)
        hide(S, d, not xr or z < ZB_DOCK + 0.05)


def storm(S, W, k=1.0):
    """k = 1 stormy dusk, 0 calm golden evening"""
    wset(S, W, STORM=k)
    put(S, W["sea"], OCEAN_W, lerp(0.35, 1.6, k))
    mset(S, W["M"]["water"], FO=k, RB=lerp(0.2, 0.5, k))
    put(S, W["sun"].data, "energy", lerp(4.2, 3.0, k))
    for i, (a, b) in enumerate(zip((1.0, 0.70, 0.42), (0.73, 0.78, 0.83))):
        put(S, W["sun"].data, "color", lerp(a, b, k), i)
    for f in W["floods"]:
        put(S, f.data, "energy", lerp(1e5, 3e5, k))
    put(S, W["haze"].data.materials[0].node_tree, 'nodes["HZ"].outputs[0].default_value', lerp(0.00025, 0.0006, k))


def flash(S, W, t, t0, k=1.0, lat=-260.0):
    """lightning: two quick pulses from t0"""
    a = max(0.0, 1 - abs(t - t0) / 0.07) + 0.6 * max(0.0, 1 - abs(t - t0 - 0.2) / 0.06)
    if a > 0:
        wset(S, W, FL=a * k)
        put(S, W["flash"].data, "energy", 14.0 * a * k)
        eye, q = S["cam"][0], S["cam"][1]
        fw = q @ V(0, 0, -1)
        fw.z = 0
        fw.normalize()
        rt = V(fw.y, -fw.x, 0)
        p = eye + fw * 1700 + rt * lat
        hide(S, W["bolt"], False)
        mset(S, W["M"]["bolt"], S=60.0 * a * k)
        for i in range(3):
            put(S, W["bolt"], "location", (p.x, p.y, -5.0)[i], i)


def rain(S, W, eye, t, t0, k=1.0):
    hide(S, W["rain"], False)
    mset(S, W["M"]["rain"], S=2.2 * k)
    for i, v in enumerate(eye + V(0, 0, 32.0 - 11.0 * (t - t0))):
        put(S, W["rain"], "location", v, i)


def xray(S, W, k=1.0, land=True):
    """the river turns to glass in a dark void; the gates' shells go clear and their chambers show"""
    M = W["M"]
    wset(S, W, XR=k, BGS=lerp(1.3, 0.25, k))
    mset(S, M["water"], XA=k)
    mset(S, M["dockwater"], XA=k)
    for m in ("gate", "truss", "rail", "conc", "ball"):
        mset(S, M[m], XA=k)
    mset(S, M["land"], XA=k if land else 0.0)
    put(S, W["haze"].data.materials[0].node_tree, 'nodes["HZ"].outputs[0].default_value', 0.0)
    if k > 0.5:
        hide(S, W["far"], True)
        hide(S, W["haze"], True)
    put(S, W["sun"].data, "energy", lerp(3.0, 0.0, k))
    for f in W["floods"]:
        put(S, f.data, "energy", lerp(3e5, 0.0, k))
    mset(S, M["lamp"], S=lerp(30.0, 4.0, k))
    for kk in ("N", "S"):
        for ob in gate_parts(W, kk):
            if ob.name.startswith(("Gate" + kk + "Walls", "Gate" + kk + "Fill")):
                hide(S, ob, False)


def gpos(side, swing, zb, psi, r, z):
    return world_pt(side, swing, zb, gpt(psi, r, z))


def shots(W):
    M = W["M"]
    L = []
    CN = gpos(1, 0, ZB_FLOAT, 0, R, 0)          # north gate centre, closed

    def A(t, S):     # "When a storm could push the sea": low over the storm waves at the mouth, lightning
        u = ss(seg(t, 0.0, 1.85))
        eye = V(lerp(-640, -610, u), lerp(40, 46, u), lerp(5.5, 4.6, u))
        cam(S, eye, V(-420, 175, 3.0), lens=24, fstop=11, clip=0.2)
        flash(S, W, t, 0.55)
        rain(S, W, eye, t, 0.0)
    L.append((0.0, 1.85, A))

    def B(t, S):     # "three metres higher": the tide staff, the water climbing to the red +3 m band
        k = ss(seg(t, 1.95, 3.0))
        put(S, W["sea"], "location", 3.05 * k, 2)
        mset(S, M["red"], S=6.0 * seg(t, 2.85, 3.05))
        u = ss(seg(t, 1.85, 3.4))
        g = GAUGE
        eye = g + V(lerp(-7.0, -6.0, u), lerp(-15.0, -13.0, u), lerp(2.4, 3.6, u))
        cam(S, eye, g + V(0.0, 0, lerp(1.7, 2.6, u)), lens=45, fstop=4.0, clip=0.1)
        rain(S, W, eye, t, 1.85, 0.7)
        label(S, "plus3", g + V(0.55, -0.3, 3.0))
    L.append((1.85, 3.4, B))

    def C(t, S):     # "Rotterdam shuts its river": high over the sea, the two doors swinging across
        u = seg(t, 3.4, 4.9)
        gates(S, W, lerp(-42, -14, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(-640, -600, u), lerp(-260, -240, u), lerp(260, 240, u)), V(lerp(60, 70, u), 0, 0), lens=30,
            fstop=16, clip=1.0)
        flash(S, W, t, 4.3, 0.6)
    L.append((3.4, 4.9, C))

    def D(t, S):     # "with two floating doors": at the waterline mid-river, the two ends closing on each other
        u = seg(t, 4.9, 6.27)
        gates(S, W, lerp(-14, -3, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        eye = V(lerp(-150, -138, u), lerp(-14, -10, u), 4.2)
        cam(S, eye, V(70, 6, 6.0), lens=32, fstop=11, clip=0.2)
        rain(S, W, eye, t, 4.9, 0.8)
    L.append((4.9, 6.27, D))

    def E(t, S):     # "Each one is two hundred": skimming along the north door's sea face
        u = seg(t, 6.27, 7.7)
        gates(S, W, 0.0, ZB_FLOAT)
        dock_level(S, W, 0.0)
        p = lerp(-PSI + 4, PSI - 10, ss(u))
        eye = gpos(1, 0, ZB_FLOAT, p, R + GD / 2 + 26.0, 9.0)
        tg = gpos(1, 0, ZB_FLOAT, p + 9.0, R + GD / 2, 6.0)
        cam(S, eye, tg, lens=28, fstop=8, clip=0.2)
    L.append((6.27, 7.7, E))

    def F(t, S):     # "...and ten metres long": the whole north door square on from the sea, 210 m drawn on
        u = seg(t, 7.7, 9.6)
        gates(S, W, 0.0, ZB_FLOAT)
        dock_level(S, W, 0.0)
        n = (CN - JN).normalized()
        n.z = 0
        eye = CN + n * lerp(345, 330, u) + V(0, -30, lerp(195, 185, u))
        cam(S, eye, CN + V(0, -20, 0.0), lens=30, fstop=16, clip=1.0)
        label(S, "g0", gpos(1, 0, ZB_FLOAT, -PSI, R + GD / 2, ZB_FLOAT + GH + 1.0))
        label(S, "g1", gpos(1, 0, ZB_FLOAT, PSI, R + GD / 2, ZB_FLOAT + GH + 1.0))
    L.append((7.7, 9.6, F))

    def G(t, S):     # "Most days, they hide in dry docks": a calm golden evening, the door resting in its dry dock
        storm(S, W, 0.0)
        u = ss(seg(t, 9.6, 11.6))
        c = gpos(1, PARK, ZB_FLOAT, 0, R, 0)
        cam(S, c + V(lerp(-150, -135, u), lerp(-210, -190, u), lerp(120, 105, u)), c + V(0, 0, -6), lens=30, fstop=16,
            clip=1.0)
        label(S, "dock", gpos(1, PARK, ZB_FLOAT, 6, R + GD / 2 + 3, ZB_DOCK + 2.0))
    L.append((9.6, 11.6, G))

    def H(t, S):     # "When a surge is coming": the storm rolls in off the sea, lightning
        u = seg(t, 11.6, 12.75)
        put(S, W["sea"], OCEAN_W, 2.2)
        eye = V(lerp(-300, -320, u), -60, 6.0)
        cam(S, eye, V(-900, -10, 8.0), lens=26, fstop=11, clip=0.2)
        flash(S, W, t, 11.95)
        rain(S, W, eye, t, 11.6)
    L.append((11.6, 12.75, H))

    def xdock(S, t, t0):
        """the real dock under the storm; only the door and the water inside the dock turn to x-ray"""
        k = ss(seg(t, t0, t0 + 0.12))
        for m in ("gate", "truss", "rail", "ball"):
            mset(S, M[m], XA=k)
        mset(S, M["dockwater"], XA=k, RB=0.6, FO=0.0, FN=0.0)
        mset(S, M["lamp"], S=lerp(30.0, 4.0, k))
        for kk in ("N", "S"):
            for ob in gate_parts(W, kk):
                if ob.name.startswith(("Gate" + kk + "Walls", "Gate" + kk + "Fill")):
                    hide(S, ob, False)
        hide(S, W["haze"], True)
        lv = lerp(ZB_DOCK, 0.0, ss(seg(t, 12.85, 14.75)))
        dock_level(S, W, lv, xr=k > 0.5)
        gates(S, W, PARK, max(ZB_DOCK, lv - 7.0))

    def I(t, S):     # "the docks flood": the door turns to glass, its dry dock filling round it
        xdock(S, t, 12.75)
        u = seg(t, 12.75, 13.85)
        eye = gpos(1, PARK, ZB_FLOAT, lerp(14, 11, u), R + 85, 72.0)
        cam(S, eye, gpos(1, PARK, ZB_FLOAT, 5, R, -6.0), lens=26, fstop=16, clip=0.5)
    L.append((12.75, 13.85, I))

    def Jx(t, S):    # "and the hollow doors float": closer, the hollow door lifting off the dock floor
        xdock(S, t, 12.75)
        u = seg(t, 13.85, 14.94)
        eye = gpos(1, PARK, ZB_FLOAT, lerp(-2, -4, u), R + 48, lerp(40, 36, u))
        cam(S, eye, gpos(1, PARK, ZB_FLOAT, -9, R, -4.0), lens=28, fstop=11, clip=0.5)
    L.append((13.85, 14.94, Jx))

    def K(t, S):     # "Motors swing them out": high above, both doors swinging out of their docks
        u = seg(t, 14.94, 16.25)
        gates(S, W, lerp(PARK, -26, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(330, 300, u), lerp(-120, -90, u), lerp(470, 430, u)), V(lerp(110, 100, u), 0, 0), lens=24,
            fstop=16, clip=1.0)
    L.append((14.94, 16.25, K))

    def Lb(t, S):    # "on ball joints ten metres wide": close on the north ball turning in its seat
        u = seg(t, 16.25, 18.25)
        gates(S, W, lerp(-26, -7, u), ZB_FLOAT)
        dock_level(S, W, 0.0)
        j = JN + V(0, 0, ZJ)
        a = rad(lerp(-35, -20, ss(u)))
        eye = j + V(34 * math.cos(a) + 8, 34 * math.sin(a), lerp(17, 15, ss(u)))
        cam(S, eye, j + V(-7, 0, 1.0), lens=40, fstop=5.6, clip=0.2)
        for f in W["floods"]:
            put(S, f.data, "energy", 6e4)
        side = (eye - j).cross(V(0, 0, 1)).normalized()
        label(S, "b0", j - side * 5.0 + V(0, 0, 6.5))
        label(S, "b1", j + side * 5.0 + V(0, 0, 6.5))
    L.append((16.25, 18.25, Lb))

    def Mm(t, S):    # "In the middle": low on the river side, the two ends meeting mid-channel
        u = seg(t, 18.25, 19.35)
        gates(S, W, lerp(-7, 0, eout(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        mid = gpos(1, 0, ZB_FLOAT, PSI, R, 0)
        eye = mid + V(lerp(-150, -140, u), -12, lerp(48, 44, u))
        cam(S, eye, mid + V(15, 0, 2.0), lens=30, fstop=11, clip=0.5)
        rain(S, W, eye, t, 18.25, 0.7)
    L.append((18.25, 19.35, Mm))

    def N(t, S):     # "they fill with water and sink to the riverbed": x-ray, chambers flood blue, the doors go down
        xray(S, W, ss(seg(t, 19.35, 19.55)), land=False)
        hide(S, W["land"][0], True)
        hide(S, W["land"][1], True)
        fh = lerp(ZB_FLOAT, ZB_FLOAT + GH, ss(seg(t, 19.45, 20.5)))
        mset(S, M["fill"], FH=fh)
        zb = lerp(ZB_FLOAT, ZB_SUNK, ss(seg(t, 19.95, 21.0)))
        gates(S, W, 0.0, zb)
        mid = gpos(1, 0, ZB_FLOAT, PSI, R, 0)
        cam(S, gpos(1, 0, ZB_FLOAT, PSI - 9, R + GD / 2 + 105, -3.0), gpos(1, 0, ZB_FLOAT, PSI - 10, R, -5.0), lens=36,
            fstop=16, clip=0.5)
        label(S, "bed", gpos(1, 0, ZB_FLOAT, PSI - 13, R + GD / 2 + 14, SILL))
    L.append((19.35, 21.1, N))

    def O(t, S):     # "Now a steel wall holds back the North Sea": low on the sea side, the storm against the wall
        u = seg(t, 21.1, 23.5)
        gates(S, W, 0.0, ZB_SUNK)
        dock_level(S, W, 0.0)
        put(S, W["sea"], OCEAN_W, 2.2)
        put(S, W["sea"], "location", 1.5, 2)
        n = (CN - JN).normalized()
        n.z = 0
        eye = gpos(1, 0, ZB_FLOAT, lerp(PSI - 12, PSI - 15, ss(u)), R + GD / 2 + lerp(36, 28, ss(u)), 8.0)
        cam(S, eye, gpos(1, 0, ZB_FLOAT, PSI - 30, R + GD / 2, 3.0), lens=24, fstop=11, clip=0.2)
        flash(S, W, t, 22.45)
        rain(S, W, eye, t, 21.1)
        label(S, "sea", gpos(1, 0, ZB_FLOAT, PSI - 18, R + GD / 2 + 14, 2.5))
    L.append((21.1, 23.5, O))

    def P(t, S):     # "When the storm passes": the sky breaks to gold over the closed barrier
        u = seg(t, 23.5, 24.75)
        storm(S, W, 1 - ss(seg(t, 23.6, 24.6)))
        gates(S, W, 0.0, ZB_SUNK)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(-420, -400, u), lerp(-330, -310, u), lerp(120, 115, u)), V(60, 20, 0), lens=30, fstop=16,
            clip=1.0)
    L.append((23.5, 24.75, P))

    def Q(t, S):     # "they're pumped empty": x-ray again, the chambers drain and the doors rise
        storm(S, W, 0.0)
        xray(S, W, ss(seg(t, 24.75, 24.95)), land=False)
        hide(S, W["land"][0], True)
        hide(S, W["land"][1], True)
        fh = lerp(ZB_FLOAT + GH, ZB_FLOAT - 0.5, ss(seg(t, 24.8, 25.6)))
        mset(S, M["fill"], FH=fh)
        zb = lerp(ZB_SUNK, ZB_FLOAT, ss(seg(t, 24.95, 25.8)))
        gates(S, W, 0.0, zb)
        mid = gpos(1, 0, ZB_FLOAT, PSI, R, 0)
        cam(S, gpos(1, 0, ZB_FLOAT, PSI - 9, R + GD / 2 + 105, -3.0), gpos(1, 0, ZB_FLOAT, PSI - 10, R, -5.0), lens=36,
            fstop=16, clip=0.5)
    L.append((24.75, 25.8, Q))

    def Rr(t, S):    # "and float home": golden light, the doors swing back into their docks
        storm(S, W, 0.0)
        u = seg(t, 25.8, 27.4)
        gates(S, W, lerp(0, PARK, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(520, 500, u), lerp(-230, -215, u), lerp(260, 250, u)), V(60, 20, 0), lens=26, fstop=16, clip=1.0)
    L.append((25.8, 27.4, Rr))

    def U(t, S):     # "Follow for how the world is really engineered": crane up and out over the open barrier
        storm(S, W, 0.0)
        u = ss(seg(t, 27.4, T_END))
        gates(S, W, PARK, ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(-160, -700, u), lerp(-120, -420, u), lerp(40, 420, u)), V(lerp(60, 120, u), 0, lerp(5, 0, u)),
            lens=28, fstop=16, clip=1.0)
    L.append((27.4, T_END + 0.1, U))
    return L


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = build_sb()
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_sb.json"))
    if os.environ.get("BAKEONLY"):
        sys.exit(0)
    if os.environ.get("SAVEBLEND"):
        bpy.ops.wm.save_as_mainfile(filepath=os.environ["SAVEBLEND"])
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
