

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
            L = min(rnd.uniform(0.014, 0.022), max(0.005, 0.034 - abs(sa0)))
            for j in range(16):
                g = j / 15
                h = 0.00018 + 0.00045 * g ** 0.7
                p, nn, dn = af_point(sa + side * L * g, z + 0.0006 * g, off=h)
                pts.append(p)
            ph = rnd.random()
            bm_ribbon(bm, pts, lambda g: 0.0006 + 0.0018 * g ** 0.8, at, ph)
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
