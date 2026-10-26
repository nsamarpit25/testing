"""Stylised body: lofted torso with real shoulders, swept arms and legs, mitten hands, sneakers,
and outfit pieces (hoodie / sweater) layered on top.

Character space: feet at z=0, face looks toward -Y, skull centre at HEAD_Z.
"""
import bmesh
from math import sin, cos, pi, copysign, atan2
from mathutils import Vector
from kit import mk, bm_tube, ring_pts, catmull, ellipsoid, mat, bm_ico, scale_bm

HEAD_Z = 1.15

# torso cross-sections: (z, half-width, half-depth, y offset, superellipse exponent)
TORSO = [
    (0.645, 0.122, 0.092, 0.004, 2.5),
    (0.69, 0.12, 0.09, 0.002, 2.5),
    (0.75, 0.123, 0.092, 0.0, 2.6),
    (0.80, 0.13, 0.096, -0.004, 2.7),
    (0.85, 0.138, 0.097, -0.004, 3.0),
    (0.89, 0.144, 0.092, -0.002, 3.4),
    (0.918, 0.14, 0.085, 0.0, 3.4),
    (0.94, 0.12, 0.075, 0.002, 2.8),
    (0.958, 0.085, 0.064, 0.004, 2.3),
    (0.972, 0.056, 0.052, 0.006, 2.0),
    (0.978, 0.044, 0.044, 0.006, 2.0),
]
HIPS = [  # ends above the crotch so the thighs, not a rounded seat, form the silhouette between the legs
    (0.588, 0.05, 0.05, 0.006, 2.0),
    (0.602, 0.1, 0.078, 0.005, 2.4),
    (0.625, 0.118, 0.088, 0.004, 2.5),
    (0.665, 0.118, 0.088, 0.004, 2.5),
]
ARM = [((0.118, 0.002, 0.912), 0.042), ((0.146, 0.004, 0.872), 0.04), ((0.163, 0.012, 0.765), 0.035),
       ((0.162, -0.005, 0.69), 0.036), ((0.155, -0.03, 0.628), 0.031)]
# straight-leg jeans: full thigh, soft knee, slight forward shin, hem just above the ankle
LEG = [((0.058, 0.006, 0.625), 0.063), ((0.066, 0.0, 0.47), 0.056), ((0.072, -0.007, 0.34), 0.048),
       ((0.077, 0.003, 0.235), 0.046), ((0.081, 0.003, 0.15), 0.045), ((0.082, 0.004, 0.122), 0.046)]
FOOT_X = 0.083
# seated at a desk: forearms resting forward with the hands round a mug, thighs level, shins hanging
ARM_SIT = [((0.118, 0.002, 0.912), 0.042), ((0.148, 0.0, 0.87), 0.04), ((0.172, -0.035, 0.8), 0.036),
           ((0.124, -0.15, 0.795), 0.034), ((0.054, -0.269, 0.795), 0.031)]  # wrists in close round the small cup
LEG_SIT = [((0.058, 0.006, 0.625), 0.063), ((0.064, -0.12, 0.61), 0.058), ((0.069, -0.24, 0.6), 0.053),
           ((0.074, -0.3, 0.565), 0.05), ((0.078, -0.31, 0.47), 0.047), ((0.081, -0.307, 0.37), 0.045),
           ((0.082, -0.306, 0.332), 0.046)]
FOOT_SIT = Vector((0, -0.31, 0.21))  # shift of the ankle/foot relative to standing
# sneaker sections along the foot, heel (+y) to toe: (y, half-width, bottom z, top z, exponent)
SHOE = [(0.052, 0.018, 0.016, 0.046, 2.4), (0.046, 0.031, 0.012, 0.066, 2.8), (0.024, 0.039, 0.012, 0.078, 3.0),
        (-0.008, 0.042, 0.012, 0.074, 3.0), (-0.04, 0.044, 0.012, 0.06, 3.0), (-0.07, 0.044, 0.012, 0.047, 2.9),
        (-0.096, 0.039, 0.012, 0.037, 2.7), (-0.114, 0.028, 0.013, 0.03, 2.4), (-0.124, 0.012, 0.016, 0.026, 2.2)]


def densify(S, k=3):
    """Catmull-Rom between section tuples so lofts stay smooth without subdivision."""
    P = [S[0]] + S + [S[-1]]
    out = []
    for i in range(1, len(P) - 2):
        for st in range(k):
            t = st / k
            out.append(tuple(0.5 * (2 * P[i][j] + (-P[i - 1][j] + P[i + 1][j]) * t +
                                    (2 * P[i - 1][j] - 5 * P[i][j] + 4 * P[i + 1][j] - P[i + 2][j]) * t * t +
                                    (-P[i - 1][j] + 3 * P[i][j] - 3 * P[i + 1][j] + P[i + 2][j]) * t ** 3)
                             for j in range(len(S[0]))))
    out.append(S[-1])
    return out


# ----------------------------------------------------------------- geometry helpers

def _lerp(a, b, t):
    return a + (b - a) * t


def section_at(S, z):
    if z <= S[0][0]:
        return S[0][1:]
    for a, b in zip(S, S[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(_lerp(a[i], b[i], t) for i in range(1, 5))
    return S[-1][1:]


def _se(c, e):
    return copysign(abs(c) ** (2 / e), c)


def bm_loft(S, n=32, grow=0.0, caps=(True, True)):
    bm = bmesh.new()
    rings = []
    for z, hw, hd, yo, e in S:
        rings.append([bm.verts.new((_se(cos(2 * pi * j / n), e) * (hw + grow),
                                    yo + _se(sin(2 * pi * j / n), e) * (hd + grow), z)) for j in range(n)])
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(n):
            bm.faces.new((r0[j], r0[(j + 1) % n], r1[(j + 1) % n], r1[j]))
    if caps[0]:
        bm.faces.new(list(reversed(rings[0])))
    if caps[1]:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def front_y(S, x, z, grow=0.0):
    hw, hd, yo, e = section_at(S, z)
    u = min(abs(x) / (hw + grow), 0.999)
    return yo - (hd + grow) * (1 - u ** e) ** (1 / e)


def bm_sweep(ctrl, steps=5, seg=16, caps=(True, True), squash=1.0):
    """Tube through catmull-smoothed control points [(pos, radius)], parallel-transport frames, rounded ends."""
    P = catmull([Vector(p) for p, _ in ctrl], steps)
    R = []
    for k in range(len(P)):
        i, t = min(k // steps, len(ctrl) - 2), (k - min(k // steps, len(ctrl) - 2) * steps) / steps
        R.append(_lerp(ctrl[i][1], ctrl[i + 1][1], min(t, 1.0)))
    n = len(P)
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    a = T[0].orthogonal().normalized()
    A = []
    for i in range(n):
        if i:
            a = T[i - 1].rotation_difference(T[i]) @ a
            a = (a - T[i] * a.dot(T[i])).normalized()
        A.append(a.copy())
    bm = bmesh.new()

    def ring(c, t, a, r):
        b = t.cross(a).normalized()
        return [bm.verts.new(c + r * (cos(2 * pi * j / seg) * a + squash * sin(2 * pi * j / seg) * b)) for j in range(seg)]

    rings = []
    if caps[0]:
        for k in (2, 1):
            ph = k / 3 * pi / 2
            rings.append(ring(P[0] - T[0] * R[0] * sin(ph) * 0.85, T[0], A[0], R[0] * cos(ph)))
    rings += [ring(P[i], T[i], A[i], R[i]) for i in range(n)]
    if caps[1]:
        for k in (1, 2):
            ph = k / 3 * pi / 2
            rings.append(ring(P[-1] + T[-1] * R[-1] * sin(ph) * 0.85, T[-1], A[-1], R[-1] * cos(ph)))
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(seg):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % seg], r0[(j + 1) % seg]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def bm_patch(fn, nu, nv, thick):
    """Thin shell from a parametric front surface fn(u, v) -> Vector, extruded +Y (into the body)."""
    bm = bmesh.new()
    F = [[bm.verts.new(fn(i / (nu - 1), j / (nv - 1))) for i in range(nu)] for j in range(nv)]
    B = [[bm.verts.new(v.co + Vector((0, thick, 0))) for v in row] for row in F]
    for j in range(nv - 1):
        for i in range(nu - 1):
            bm.faces.new((F[j][i], F[j + 1][i], F[j + 1][i + 1], F[j][i + 1]))
            bm.faces.new((B[j][i], B[j][i + 1], B[j + 1][i + 1], B[j + 1][i]))
    border = [(0, i) for i in range(nu)] + [(j, nu - 1) for j in range(1, nv)] + \
             [(nv - 1, i) for i in range(nu - 2, -1, -1)] + [(j, 0) for j in range(nv - 2, 0, -1)]
    for (j0, i0), (j1, i1) in zip(border, border[1:] + border[:1]):
        bm.faces.new((F[j0][i0], F[j1][i1], B[j1][i1], B[j0][i0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def mirror(ctrl, s):
    return [((s * p[0], p[1], p[2]), r) for p, r in ctrl]


# ----------------------------------------------------------------- body

def build_body(n, cfg, body, M):
    o = cfg["outfit"]
    main, trim = M["top"], M["trim"]
    shoe = mat(f"{n}_Shoe", cfg.get("shoe", "#f4f1ec"), 0.5, grain=0.15)
    sole = mat(f"{n}_Sole", cfg.get("sole", "#e6dccb"), 0.7)
    sock = mat(f"{n}_Sock", cfg.get("sock", "#f1ede6"), 0.85, rib=0.3, rib_scale=160)
    cuff = mat(f"{n}_PantsCuff", cfg.get("pants_cuff", cfg.get("pants", "#2b2c38")), 0.82, grain=0.18)

    mk(f"{n}_torso", bm_loft(TORSO), main, parent=body)
    drop = cfg.get("neck_drop", 0.0)
    mk(f"{n}_neck", bm_sweep([((0, 0.0098, 0.95), 0.058), ((0, 0.0098, 0.99), 0.0515), ((0, 0.0098, 1.07 - drop), 0.0485)],
                             seg=20), M["skin"], parent=body)
    mk(f"{n}_hem", bm_loft([(0.632, *section_at(TORSO, 0.645)), (0.672, *section_at(TORSO, 0.68))], grow=0.005),
       trim, parent=body)
    mk(f"{n}_hips", bm_loft(HIPS), M["pants"], parent=body)

    sit = cfg.get("pose") == "sit"
    F = FOOT_SIT if sit else Vector((0, 0, 0))
    for s in (-1, 1):
        arm = mirror(ARM_SIT if sit else ARM, s)
        mk(f"{n}_arm{s}", bm_sweep(arm), main, parent=body)
        wrist, prev = Vector(arm[-1][0]), Vector(arm[-2][0])
        d = (wrist - prev).normalized()
        mk(f"{n}_cuff{s}", bm_sweep([(wrist - d * 0.006, 0.03), (wrist + d * 0.016, 0.029)], steps=1, seg=18), trim,
           parent=body)
        build_hand(n, s, wrist, d, body, M["skin"])
        leg = mirror(LEG_SIT if sit else LEG, s)
        mk(f"{n}_leg{s}", bm_sweep(leg, caps=(True, False)), M["pants"], parent=body)
        hem = Vector(leg[-1][0])
        mk(f"{n}_cuffroll{s}", bm_sweep([(hem + Vector((0, 0, -0.01)), 0.0472), (hem + Vector((0, 0, 0.0)), 0.0476),
                                        (hem + Vector((0, 0, 0.012)), 0.0474)], steps=2, seg=24), cuff, parent=body)
        mk(f"{n}_sock{s}", bm_sweep([(hem + Vector((0, 0, 0.01)), 0.03), (Vector((s * FOOT_X, 0.006, 0.05)) + F, 0.031)],
                                   steps=1, seg=16), sock, parent=body)
        build_sneaker(n, s, body, shoe, sole, M["accent"], F)

    if o == "hoodie":
        hoodie(n, body, M)
    else:
        ring = ring_pts((0, 0.008, 0.968), 0.05, (0, -0.25, 1), 28)
        mk(f"{n}_collar", bm_tube(ring, 0.011, 8, True, (0, -0.25, 1)), trim, parent=body)

    hz = drop - HEAD_Z  # colliders live in head space
    cols = [(Vector((0, 0, 0.84 + hz)), Vector((0.14, 0.1, 0.14))),
            (Vector((0, 0, 0.915 + hz)), Vector((0.148, 0.09, 0.06))),
            (Vector((0.152, 0.006, 0.8 + hz)), Vector((0.045, 0.045, 0.13))),
            (Vector((-0.152, 0.006, 0.8 + hz)), Vector((0.045, 0.045, 0.13))),
            (Vector((0, 0, 0)), Vector((0.159, 0.149, 0.152)))]
    if o == "hoodie":
        cols.append((Vector((0, 0.07, 0.96 + hz)), Vector((0.1, 0.06, 0.05))))
    return cols


def build_hand(n, s, wrist, d, body, skin):
    """Mitten-ish hand: four slightly curled fingers and a thumb. Hanging, the palm faces the thigh;
    held forward, the palm faces inward (round a mug) with the thumb on top."""
    inward = Vector((-s, 0, 0))
    sp = d.cross(Vector((-1, 0, 0))).normalized()  # finger spread axis: +Y when hanging, -Z when forward
    palm = wrist + d * 0.024
    rot = (d.y * 1.2, 0, 0) if abs(d.z) > 0.7 else (0, 0, atan2(-d.x, d.y))
    ellipsoid(f"{n}_palm{s}", (0.011, 0.02, 0.022), skin, palm, rot, body, sub=3)
    for k, (yo, ln) in enumerate([(-0.0125, 0.9), (-0.0042, 1.0), (0.0042, 0.95), (0.0122, 0.78)]):
        p0 = palm + d * 0.014 + sp * yo
        p1 = p0 + d * 0.015 * ln + inward * 0.002
        p2 = p1 + d * 0.012 * ln + inward * 0.006
        r = 0.0052 if k < 3 else 0.0046
        mk(f"{n}_finger{s}_{k}", bm_sweep([(p0, r), (p1, r * 0.95), (p2, r * 0.85)], steps=3, seg=10), skin, parent=body)
    t0 = palm - sp * 0.016 - d * 0.004 + inward * 0.004
    t1 = t0 - sp * 0.007 + d * 0.012 + inward * 0.006
    t2 = t1 - sp * 0.002 + d * 0.011 + inward * 0.004
    mk(f"{n}_thumb{s}", bm_sweep([(t0, 0.0064), (t1, 0.0058), (t2, 0.005)], steps=3, seg=10), skin, parent=body)


def build_sneaker(n, s, body, shoe, sole, accent, offset=Vector((0, 0, 0))):
    """Low-top sneaker lofted heel-to-toe, with sole, padded collar, tongue, laces, heel tab and side stripe."""
    def loft_y(S, grow=0.0):
        bm = bm_loft([(y, hw + grow, (top - bot) / 2 + grow * 0.5, (top + bot) / 2, e) for y, hw, bot, top, e in densify(S)],
                     n=36)
        for v in bm.verts:
            v.co.y, v.co.z = v.co.z, v.co.y
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm

    loc, rot = Vector((s * FOOT_X, 0.004, 0)) + offset, (0, 0, s * 0.12)
    foot = mk(f"{n}_shoe{s}", loft_y(SHOE), shoe, loc, rot, body)
    mk(f"{n}_sole{s}", loft_y([(y, hw, 0.0 if y > -0.1 else 0.006, 0.017 if y > -0.1 else 0.022, 4.0)
                               for y, hw, *_ in SHOE], 0.004), sole, parent=foot)
    mk(f"{n}_collarpad{s}", bm_tube(ring_pts((0, 0.014, 0.073), 0.032, (0, 0.3, 1), 20), 0.0075, 8, True, (0, 0.3, 1)),
       shoe, parent=foot)
    ellipsoid(f"{n}_tongue{s}", (0.019, 0.03, 0.006), shoe, (0, -0.012, 0.081), (0.35, 0, 0), foot, sub=2)
    for k, (y, z) in enumerate([(-0.014, 0.077), (-0.031, 0.071), (-0.048, 0.064)]):
        mk(f"{n}_lace{s}_{k}", bm_tube([(-0.016, y, z - 0.002), (0, y, z + 0.0015), (0.016, y, z - 0.002)], 0.0032, 6),
           sole, parent=foot)
    ellipsoid(f"{n}_heeltab{s}", (0.012, 0.007, 0.017), accent, (0, 0.052, 0.062), (-0.2, 0, 0), foot, sub=2)
    for side in (-1, 1):
        pts = [(side * (section_at_y(y) + 0.0012), y, z) for y, z in [(0.034, 0.034), (0.005, 0.04), (-0.03, 0.034), (-0.055, 0.03)]]
        mk(f"{n}_stripe{s}_{side}", bm_tube(pts, 0.0042, 6), accent, parent=foot)


def section_at_y(y):
    for a, b in zip(SHOE, SHOE[1:]):
        if b[0] <= y <= a[0]:
            t = (a[0] - y) / (a[0] - b[0])
            return _lerp(a[1], b[1], t)
    return SHOE[-1][1]


def hoodie(n, body, M):
    main, trim = M["top"], M["trim"]
    # hood: a soft roll around the back of the neck, thick at the back, tapering to the front V
    ctrl = [((-0.022, -0.09, 0.936), 0.012)]
    for deg in range(-150, 151, 25):
        t = deg * pi / 180
        k = (cos(t) + 1) / 2
        ctrl.append(((0.074 * sin(t), 0.008 + 0.064 * cos(t), 0.958 + 0.026 * k), 0.014 + 0.024 * k ** 1.3))
    ctrl.append(((0.022, -0.09, 0.936), 0.012))
    mk(f"{n}_hood", bm_sweep(ctrl, steps=4, seg=14), main, parent=body)
    bm = bm_ico(1.0, 3)
    for v in bm.verts:  # teardrop: the hood narrows to a soft point as it lies down the back
        v.co.x *= 1 - 0.45 * max(-v.co.z, 0.0) ** 1.3
    scale_bm(bm, (0.09, 0.03, 0.075))
    mk(f"{n}_hoodback", bm, main, (0, 0.084, 0.915), (-0.22, 0, 0), body)
    # drawstrings with tips
    for s in (-1, 1):
        top = Vector((s * 0.025, -0.097, 0.938))
        bot = Vector((s * 0.028, front_y(TORSO, 0.028, 0.84) - 0.006, 0.84))
        mid = (top + bot) / 2 + Vector((0, -0.012, 0))
        mk(f"{n}_string{s}", bm_sweep([(top, 0.0032), (mid, 0.0032), (bot, 0.0032)], seg=8), M["second"], parent=body)
        mk(f"{n}_aglet{s}", bm_sweep([(bot, 0.0042), (bot + Vector((0, 0.001, -0.014)), 0.0042)], steps=1, seg=8),
           M["second"], parent=body)
    # kangaroo pocket, slanted openings
    z0, z1 = 0.685, 0.785

    def pocket(u, v):
        z = _lerp(z0, z1, v)
        hw = _lerp(0.088, 0.066, v)
        x = _lerp(-hw, hw, u)
        return Vector((x, front_y(TORSO, x, z) - 0.0035, z))

    mk(f"{n}_pocket", bm_patch(pocket, 12, 6, 0.008), main, parent=body)
    for s in (-1, 1):
        pts = [Vector((s * _lerp(0.088, 0.066, v), 0, _lerp(z0, z1, v))) for v in (0.05, 0.5, 0.95)]
        pts = [Vector((p.x, front_y(TORSO, p.x, p.z) - 0.0065, p.z)) for p in pts]
        mk(f"{n}_pocketedge{s}", bm_tube(pts, 0.0028, 6), trim, parent=body)
