"""Girl character generator.

Head-local space: origin = skull centre, +Z up, face looks toward -Y.
Hair is built from flat faceted strands that follow the skull, then hang and drape over
the body (simple ellipsoid colliders), giving the clean low-poly look.
"""
import random
import bpy, bmesh
from math import sin, cos, pi, sqrt, asin, atan2, radians, degrees, exp
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import bmesh
import body as body_mod
from kit import (lin, ss, empty, mk, bm_ico, bm_box, bm_cyl, scale_bm, jitter, ellipsoid, limb, bm_tube,
                 superellipse_xz, ring_pts, catmull, resample, collide, smooth, bm_ribbon, merge_into, mat, emissive)

SK = Vector((0.155, 0.145, 0.148))  # skull radii
HEAD_Z = 1.15                       # skull centre above the character root
TORSO_Z = 0.86
TR = Vector((0.158, 0.118, 0.16))  # torso radii


def dae(az, el):
    a, e = radians(az), radians(el)
    return Vector((cos(e) * cos(a), cos(e) * sin(a), sin(e)))


def on_shell(d, off):
    d = Vector(d).normalized()
    k = sqrt((d.x / SK.x) ** 2 + (d.y / SK.y) ** 2 + (d.z / SK.z) ** 2)
    return d / k + d * off


def surf_y(x, z):
    return -SK.y * sqrt(max(1 - (x / SK.x) ** 2 - (z / SK.z) ** 2, 0.0))


def hairline_el(az):
    f = (1 - sin(radians(az))) / 2  # 1 at the forehead, 0 at the nape
    return -38 + 74 * f ** 1.4 - 5 * exp(-((az - 90) / 28) ** 2)  # small dip at the nape


# ----------------------------------------------------------------- hair

class Hair:
    def __init__(self, name, head, material, colliders, seed):
        self.name, self.head, self.mat, self.cols = name, head, material, colliders
        self.bm = bmesh.new()
        self.rnd = random.Random(seed)
        self.count = 0

    def strand(self, ctrl, off=0.008, hang=0.0, width=0.05, thick=0.015, wave=0.0, curl=0.0, flare=0.012,
               drift=(0, 0, 0), tip=0.2, root=0.5, tip_start=0.68, free=None, phase=None, tuck=False):
        """ctrl: unit directions on the skull. hang: length that falls straight down after the last ctrl point.
        free: extra absolute points (head-local) appended after the shell path (used for tails)."""
        dirs = catmull([Vector(d).normalized() for d in ctrl], 6)
        if tuck:  # root starts under the scalp and rises out of it: a soft hairline instead of a blunt edge
            pts = [on_shell(d, -0.007 + (off + 0.007) * ss(i / (len(dirs) * 0.3))) for i, d in enumerate(dirs)]
        else:
            pts = [on_shell(d, off) for d in dirs]
        hang_start = len(pts)
        if hang > 0:
            last = pts[-1]
            horiz = Vector((last.x, last.y, 0))
            horiz = horiz.normalized() if horiz.length > 1e-6 else Vector((0, 1, 0))
            ph = self.rnd.uniform(0, 6.28) if phase is None else phase
            n = max(4, int(hang / 0.018))
            for i in range(1, n + 1):
                u = i / n
                h = hang * u
                q = last + Vector((0, 0, -h)) + horiz * (flare * sin(u * pi / 2)) + Vector(drift) * u
                if wave:
                    q += horiz * wave * sin(h * 32 + ph) * ss(u * 4)
                if curl:
                    q -= horiz * curl * ss((u - 0.6) / 0.4)
                pts.append(q)
        if free:
            pts += [p.copy() for p in catmull([pts[-1]] + [Vector(p) for p in free], 6)[1:]]
        if len(pts) > hang_start:
            collide(pts, self.cols, 0.008, hang_start)
            smooth(pts, 2, hang_start)
            collide(pts, self.cols, 0.008, hang_start)
        pts = resample(pts, 0.022)
        merge_into(self.bm, bm_ribbon(pts, width, thick, tip=tip, root=root, tip_start=tip_start))
        self.count += 1

    def cap(self, hl_offset=0.0):
        bm = bm_ico(1.0, 3)
        scale_bm(bm, SK * 1.0 + Vector((0.004, 0.004, 0.004)))
        kill = []
        for v in bm.verts:
            d = Vector((v.co.x / SK.x, v.co.y / SK.y, v.co.z / SK.z)).normalized()
            if degrees(asin(max(-1, min(1, d.z)))) < hairline_el(degrees(atan2(d.y, d.x))) + hl_offset:
                kill.append(v)
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        merge_into(self.bm, bm)

    def finish(self):
        return mk(f"{self.name}_hair", self.bm, self.mat, parent=self.head)

    # -------- styles
    def part_start(self, az, part_x, side):
        ys = sin(radians(az)) * (0.75 if sin(radians(az)) < 0 else 0.55)  # behind: start high so roots don't kink
        x = part_x + side * 0.016
        return Vector((x, ys, sqrt(max(1 - x * x - ys * ys, 0.05))))

    def long_hair(self, length=0.3, part_x=0.0, count=32, wave=0.0, flare=0.016, width=0.078, front_len=None):
        """front_len: shorter strands toward the face (layered cut), blending to full length behind the ears."""
        r = self.rnd
        for i in range(count):
            az = -42 + i * 264 / (count - 1) + r.uniform(-3, 3)
            side = 1 if cos(radians(az)) > 0.02 else (-1 if cos(radians(az)) < -0.02 else (1 if i % 2 else -1))
            ctrl = [self.part_start(az, part_x, side), dae(az, 46), dae(az, 12), dae(az, -10)]
            back = max(0.0, sin(radians(az)))
            L = length
            if front_len is not None:
                t = min(1.0, max(0.0, (sin(radians(az)) + 0.3) / 0.7))
                L = front_len + (length - front_len) * t * t * (3 - 2 * t)
            self.strand(ctrl, off=0.006 + 0.004 * (i % 3), hang=L * (0.9 + 0.12 * back) * r.uniform(0.93, 1.05),
                        width=width, thick=0.02, wave=wave, flare=flare)

    def bob(self, length=0.1, count=30):
        r = self.rnd
        for i in range(count):
            az = -46 + i * 272 / (count - 1) + r.uniform(-3, 3)
            ctrl = [dae(az + 180 * 0, 82), dae(az, 50), dae(az, 14), dae(az, -12)]
            self.strand(ctrl, off=0.007 + 0.004 * (i % 3), hang=length * r.uniform(0.95, 1.04), width=0.078,
                        thick=0.02, flare=0.022, curl=0.022, tip=0.55, tip_start=0.8)

    def pulled_back(self, target, count=32):
        r = self.rnd
        T = dae(*target)
        for i in range(count):
            az = -100 + i * 360 / count + r.uniform(-3, 3)
            el0 = hairline_el(az) + 2
            if target[1] > 30:  # high tie: go straight over the head
                mid = (dae(az, el0) * 0.5 + T * 0.5 + Vector((0, 0, 0.25))).normalized()
            else:               # low side tie: travel around, rising over the top for front strands
                az_t = target[0]
                d_az = ((az_t - az + 180) % 360) - 180
                mid = dae(az + d_az * 0.5, max(el0, target[1]) + 35)
            self.strand([dae(az, el0 + 1), mid, T], off=0.004 + 0.003 * (i % 3), width=0.07, thick=0.014,
                        root=0.45, tip=0.35, tip_start=0.85, tuck=True)
        return on_shell(T, 0.018)

    def bun(self, c, up, R=0.058):
        bm = bm_ico(1.0, 2)
        scale_bm(bm, (R, R, R * 0.9))
        jitter(bm, 0.004, 40, 5)
        q = Vector((0, 0, 1)).rotation_difference(up)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=q.to_matrix())
        bmesh.ops.translate(bm, vec=c, verts=bm.verts)
        merge_into(self.bm, bm)
        a = up.orthogonal().normalized()
        b = up.cross(a)
        for k in range(3):
            pts = []
            for i in range(28):
                t = i / 27 * 1.7 * pi + k * 2.1
                h = (-0.55 + 1.1 * i / 27) * R * 0.7
                rr = R * 1.02 * sqrt(max(1 - (h / R) ** 2, 0.1))
                pts.append(c + rr * (cos(t) * a + sin(t) * b) + up * h)
            merge_into(self.bm, bm_ribbon(pts, 0.042, 0.018, root=0.4, tip=0.3, center=c))

    def tail(self, tie, path, count=12, width=0.05, spread=0.02):
        r = self.rnd
        for i in range(count):
            a = 2 * pi * i / count
            o = Vector((cos(a) * spread, 0, sin(a) * spread * 0.7))
            start = tie + o * 0.5
            pts = [start] + [tie + Vector(p) + o * (1 + 0.8 * k) + Vector((r.uniform(-.006, .006), r.uniform(-.006, .006), 0))
                             for k, p in enumerate(path)]
            pts = catmull(pts, 6)
            collide(pts, self.cols, 0.01, 1)
            smooth(pts, 2, 1)
            collide(pts, self.cols, 0.01, 1)
            merge_into(self.bm, bm_ribbon(resample(pts, 0.022), width, 0.022, root=0.7, tip=0.15, axis_z=10))

    def curtain_bangs(self, part_x=0.0, n=3, hang=0.05):
        for s in (-1, 1):
            for j in range(n):
                start = Vector((part_x + s * 0.012, -0.55, 0.83)).normalized()
                ctrl = [start, dae(-90 + s * (14 + 7 * j), 40), dae(-90 + s * (40 + 7 * j), 18), dae(-90 + s * (58 + 5 * j), -2)]
                self.strand(ctrl, off=0.013 + 0.003 * j, hang=hang + 0.03 * j, width=0.06, thick=0.016, flare=0.004)

    def face_frame(self, n=3, hang=0.17, inner=46):
        """Heavy curtain locks from the middle part: over the forehead corners, down the sides of the face
        (covering the outer cheeks and ears) and falling in front of the shoulders."""
        for s in (-1, 1):
            for j in range(n):
                a = inner + 6 * j
                start = Vector((s * (0.014 + 0.006 * j), -0.5, 0.86)).normalized()
                ctrl = [start, dae(-90 + s * (12 + 5 * j), 52 - 4 * j), dae(-90 + s * (a - 16), 26 - 3 * j),
                        dae(-90 + s * a, 0), dae(-90 + s * (a + 6), -16)]
                self.strand(ctrl, off=0.016 + 0.004 * j, hang=hang + 0.025 * j, width=0.076 - 0.005 * j, thick=0.018,
                            flare=0.006, tip=0.3, tip_start=0.75)

    def blunt_fringe(self, n=9):
        for j in range(n):
            az = -90 + (-56 + j * 112 / (n - 1))
            ctrl = [dae(-90 + (az + 90) * 0.3, 78), dae(az, 52), dae(az, 30), dae(az, 17)]
            self.strand(ctrl, off=0.013 + 0.002 * (j % 2), width=0.062, thick=0.017, tip=0.8, tip_start=0.88)

    def side_swept(self, to_left=True, n=3, hang=0.04, wave=0.0):
        s = -1 if to_left else 1
        for j in range(n):
            start = Vector((-s * 0.05, -0.5 + 0.04 * j, 0.86)).normalized()
            ctrl = [start, dae(-90 + s * (6 + 6 * j), 46 - 4 * j), dae(-90 + s * (38 + 6 * j), 30 - 3 * j),
                    dae(-90 + s * (60 + 4 * j), 6)]
            self.strand(ctrl, off=0.014 + 0.003 * j, hang=hang + 0.02 * j, width=0.065, thick=0.017, flare=0.005, wave=wave)

    def tendrils(self, length=0.1):
        for s in (-1, 1):
            self.strand([dae(-90 + s * 52, 26), dae(-90 + s * 60, 4)], off=0.012, hang=length, width=0.018,
                        thick=0.01, wave=0.006, flare=0.004, root=0.8)


# ----------------------------------------------------------------- body + outfits

def banded(bm, amp, period, z0=0.0):
    for v in bm.verts:
        b = 0.5 + 0.5 * cos(2 * pi * (v.co.z - z0) / period)
        v.co.x *= 1 + amp * b
        v.co.y *= 1 + amp * b


def build_body(n, cfg, body, M):
    o = cfg["outfit"]
    sc = 1.07 if o == "puffer" else 1.0
    main = M["top"]
    tr = TR * sc
    # torso
    bm = bm_ico(1.0, 4 if o == "puffer" else 3)
    scale_bm(bm, tr)
    shoulder_shape(bm)
    if o == "puffer":
        banded(bm, 0.05, 0.056, 0.01)
    if o == "cardigan":
        mk(f"{n}_tee", bm, M["second"], (0, 0, TORSO_Z), parent=body)
        bm = bm_ico(1.0, 3)
        scale_bm(bm, tr + Vector((0.006, 0.006, 0.004)))
        shoulder_shape(bm)
        cut_v(bm)
        for sd in (-1, 1):
            pts = [Vector((sd * vx(z), surf_t(z + TORSO_Z, vx(z), 1.05) + 0.001, z + TORSO_Z)) for z in
                   [-0.15 + 0.3 * i / 10 for i in range(11)]]
            mk(f"{n}_band{sd}", bm_tube(pts, 0.007, 5), M["trim"], parent=body)
    mk(f"{n}_torso", bm, main, (0, 0, TORSO_Z), parent=body)
    mk(f"{n}_neck", bm_cyl(0.04, 0.1, 10), M["skin"], (0, 0.005, 1.0), parent=body)

    for s in (-1, 1):
        for seg, (p0, p1, r0, r1) in enumerate([((s * 0.15, 0.005, 0.895), (s * 0.182, 0.012, 0.775), 0.042, 0.041),
                                                ((s * 0.182, 0.012, 0.78), (s * 0.162, -0.045, 0.645), 0.04, 0.037)]):
            ob = limb(f"{n}_arm{s}_{seg}", p0, p1, r0 * sc, main, body, sub=3, r_end=r1 * sc)
            if o == "puffer":
                me = ob.data
                bmx = bmesh.new()
                bmx.from_mesh(me)
                banded(bmx, 0.06, 0.05)
                bmx.to_mesh(me)
                bmx.free()
        cuff_dir = Vector((s * 0.162, -0.045, 0.645)) - Vector((s * 0.182, 0.012, 0.78))
        mk(f"{n}_cuff{s}", bm_tube(ring_pts((s * 0.171, -0.032, 0.663), 0.04 * sc, cuff_dir, 16), 0.011, 6, True, cuff_dir),
           M["trim"], parent=body)
        ellipsoid(f"{n}_hand{s}", (0.028, 0.026, 0.032), M["skin"], (s * 0.163, -0.058, 0.618), parent=body, sub=2)
    ellipsoid(f"{n}_hips", (0.15, 0.112, 0.1), M["pants"], (0, 0.005, 0.7), parent=body, sub=3)

    neck_ring = lambda r, tube, z, m, nm: mk(nm, bm_tube(ring_pts((0, 0.006, z), r, (0, 0, 1), 24), tube, 7, True, (0, 0, 1)), m, parent=body)
    if o == "sweater":
        neck_ring(0.063, 0.02, 0.99, M["trim"], f"{n}_collar")
    elif o == "overshirt":
        neck_ring(0.056, 0.011, 0.995, M["second"], f"{n}_teecollar")
        for s in (-1, 1):
            ellipsoid(f"{n}_collarpt{s}", (0.046, 0.006, 0.026), main, (s * 0.047, -0.078, 0.976), (-0.6, s * 0.3, s * 0.6),
                      parent=body, sub=2)
        mk(f"{n}_placket", bm_tube([(0, surf_t(z, 0.0) - 0.002, z) for z in (0.71, 0.78, 0.86, 0.95)], 0.0055, 4), M["trim"], parent=body)
        for z in (0.76, 0.83, 0.9):
            ellipsoid(f"{n}_btn", (0.0055, 0.003, 0.0055), M["second"], (0, surf_t(z, 0) - 0.0065, z), parent=body, sub=1)
        mk(f"{n}_pocket", bm_box(0.05, 0.005, 0.052, 0.004, 1), M["trim"], (0.07, surf_t(0.9, 0.07) - 0.0005, 0.9), (0.3, 0, 0.45), body)
    elif o == "hoodie":
        mk(f"{n}_hood", bm_tube([Vector((0, 0.028, 0.985)) + Vector(p).xzy for p in superellipse_xz(0.11, 0.098, 2.6, 28)],
                                0.033, 10, True, (0, 0, 1)), main, parent=body)
        ellipsoid(f"{n}_hoodback", (0.12, 0.065, 0.085), main, (0, 0.1, 0.995), parent=body, sub=2, jit=0.004)
        for s in (-1, 1):
            mk(f"{n}_string{s}", bm_tube([(s * 0.032, -0.1, 0.965), (s * 0.034, -0.115, 0.92), (s * 0.037, -0.124, 0.86)],
                                         0.0038, 6), M["second"], parent=body)
    elif o == "puffer":
        for k, z in enumerate((0.985, 1.02)):
            neck_ring(0.066, 0.023, z, main, f"{n}_stand{k}")
        mk(f"{n}_zip", bm_tube([(0, surf_t(z, 0.0, 1.11) - 0.001, z) for z in (0.71, 0.78, 0.86, 0.94, 1.0)], 0.0032, 4),
           M["second"], parent=body)
    elif o == "cardigan":
        neck_ring(0.056, 0.011, 0.995, M["second"], f"{n}_teecollar")
        for z in (0.74, 0.8):
            ellipsoid(f"{n}_btn", (0.006, 0.0035, 0.006), M["accent"], (-vx(z - TORSO_Z) - 0.012, surf_t(z, vx(z - TORSO_Z) + 0.012, 1.05) - 0.003, z),
                      parent=body, sub=1)

    cols = [(Vector((0, 0, TORSO_Z - HEAD_Z)), tr),
            (Vector((0.126, 0, 0.918 - HEAD_Z)), Vector((0.054, 0.058, 0.045)) * sc),
            (Vector((-0.126, 0, 0.918 - HEAD_Z)), Vector((0.054, 0.058, 0.045)) * sc),
            (Vector((0.168, 0.01, 0.84 - HEAD_Z)), Vector((0.046, 0.046, 0.1)) * sc),
            (Vector((-0.168, 0.01, 0.84 - HEAD_Z)), Vector((0.046, 0.046, 0.1)) * sc),
            (Vector((0, 0, 0)), SK + Vector((0.004, 0.004, 0.004)))]
    if o == "hoodie":
        cols.append((Vector((0, 0.1, 0.995 - HEAD_Z)), Vector((0.12, 0.065, 0.085))))
    return cols


def tw(z):
    """Torso x-widening at torso-local height z: squares the upper chest into shoulders."""
    return 1 + 0.17 * ss((z + 0.03) / 0.15)


def shoulder_shape(bm):
    for v in bm.verts:
        v.co.x *= tw(v.co.z)


def vx(z):
    """Half-width of the cardigan's V opening at torso-local height z."""
    return 0.008 + (z + 0.13) * (0.05 - 0.008) / 0.28


def cut_v(bm):
    planes = []
    for sd in (1, -1):
        d = Vector((sd * 0.042, 0, 0.28)).normalized()
        nrm = Vector((d.z, 0, -d.x)) * sd
        co = Vector((sd * 0.008, 0, -0.13))
        front = [f for f in bm.faces if f.calc_center_median().y < -0.015]
        geom = list({e for f in front for e in f.edges}) + list({v for f in front for v in f.verts}) + front
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=co, plane_no=nrm)
        planes.append((co, nrm))
    kill = [v for v in bm.verts if v.co.y < -0.015 and all((v.co - c).dot(nm) < -1e-4 for c, nm in planes)]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")


def surf_t(z, x, sc=1.0):
    """Front surface y of the torso at height z (character space)."""
    rx, ry, rz = TR * sc
    x = x / tw(z - TORSO_Z)
    return -ry * sqrt(max(1 - (x / rx) ** 2 - ((z - TORSO_Z) / rz) ** 2, 0.0))


# ----------------------------------------------------------------- face

def head_sculpt(cfg):
    """Maps the SK ellipsoid onto the face shape (identity with the defaults).
    face_sq: exponent of the lower outline seen from the front (>2 = fuller cheeks and a broad, rounded chin).
    face_fill: same for the lower face in profile.  face_flat: squares the front plane so the face reads flatter.
    face_chin: vertical scale of everything below the eye line.  face_cheek: soft fullness just under the eyes."""
    sq, fill, flat = (cfg.get(k, 2.0) for k in ("face_sq", "face_fill", "face_flat"))
    chin, cheek = cfg.get("face_chin", 1.0), cfg.get("face_cheek", 0.0)

    def sculpt(p):
        p = Vector(p)
        u = Vector((p.x / SK.x, p.y / SK.y, p.z / SK.z))
        if u.length < 1e-6:
            return p
        d = u.normalized()
        q = 2 + (flat - 2) * ss(-d.y / 0.6)
        if q != 2:
            fxy = (abs(d.x) ** q + abs(d.y) ** q) ** (1 / q)
            p *= (fxy * fxy + d.z * d.z) ** -0.5
        if d.z < 0:
            rho = sqrt(max(1 - d.z * d.z, 1e-9))
            kx = (1 - (-d.z) ** sq) ** (1 / sq) / rho
            ky = (1 - (-d.z) ** fill) ** (1 / fill) / rho
            p.x *= (1 + (kx - 1) * ss((0.6 - d.y) / 0.6)) * (1 + cheek * exp(-((d.z + 0.3) / 0.25) ** 2) * ss(-d.y / 0.4 + 0.5))
            if p.y < 0:
                p.y *= 1 + (ky - 1) * ss(-d.y / 0.5)
            p.z *= chin
        return p
    return sculpt


def surface_probe(bm):
    """Front-surface lookup on the sculpted skull: (x, z) -> (point, outward normal)."""
    tree = BVHTree.FromBMesh(bm)

    def hit(x, z):
        loc = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))[0]
        return loc if loc is not None else Vector((x, 0, z))

    def probe(x, z, e=0.006):
        tx = hit(x + e, z) - hit(x - e, z)
        tz = hit(x, z + e) - hit(x, z - e)
        return hit(x, z), tx.cross(tz).normalized()
    return probe


def facing(nrm, roll=0.0):
    """Euler that turns a feature's local -Y onto the surface normal."""
    return (asin(max(-1, min(1, -nrm.z))), roll, atan2(nrm.x, -nrm.y))


def build_face(n, cfg, head, M):
    sculpt = head_sculpt(cfg)
    bm = bm_ico(1.0, 4)
    scale_bm(bm, SK)
    for v in bm.verts:
        v.co = sculpt(v.co)
    probe = surface_probe(bm)
    mk(f"{n}_skull", bm, M["skin"], parent=head)
    for s in (-1, 1):
        ellipsoid(f"{n}_ear{s}", (0.018, 0.026, 0.032), M["skin"], sculpt((s * 0.15, 0.006, -0.022)), parent=head, sub=2)
    eyes = empty(f"{n}_eyes", (0, 0, 0), head)
    es = cfg.get("eye_scale", 1.0)
    ex, ez = cfg.get("eye_x", 0.054), cfg.get("eye_z", -0.022)
    R, lx = cfg.get("lens", 0.036), cfg.get("lens_x", 0.055)
    out = {"eyes": eyes, "eye": [], "brows": [], "sculpt": sculpt}
    for s in (-1, 1):
        c, nr = probe(s * ex, ez)
        e = ellipsoid(f"{n}_eye{s}", (0.0102 * es, 0.007, 0.0142 * es), M["eye"], c - nr * 0.0028, facing(nr), eyes, sub=2)
        ellipsoid(f"{n}_glint{s}", (0.003, 0.0015, 0.003), M["glint"], (0.0032, -0.0066, 0.0048), parent=e, sub=1)
        ellipsoid(f"{n}_lash{s}", (0.0062, 0.002, 0.0022), M["eye"], (s * 0.0095, -0.001, 0.0112),
                  (0, -s * 0.55, 0), parent=e, sub=1).scale = (0.8, 1, 0.8)
        out["eye"].append(e)
        c, nr = probe(s * (lx + 0.001), max(0.034, ez + R + 0.012) if cfg.get("glasses") else 0.034)
        out["brows"].append(ellipsoid(f"{n}_brow{s}", (0.0155, 0.0036, 0.003), M["brow"], c - nr * 0.0015,
                                      facing(nr, -s * 0.09), head, sub=1))
    c, nr = probe(0, cfg.get("nose_z", -0.046))
    ellipsoid(f"{n}_nose", (0.0078, 0.0058, 0.0068), M["skin_shade"], c + nr * 0.0005, facing(nr), parent=head, sub=2)
    c, nr = probe(0, cfg.get("mouth_z", -0.074))
    out["mouth"] = ellipsoid(f"{n}_mouth", (0.0105 * cfg.get("mouth_w", 1.0), 0.004, 0.0027), M["mouth"],
                             c - nr * 0.0016, facing(nr), head, sub=2)

    g = cfg.get("glasses")
    if g:
        shape = {"round": (R, R, 2.0), "oval": (R * 1.11, R * 0.86, 2.2), "rect": (R * 1.14, R * 0.8, 5.0)}[g]
        tube = 0.0026
        cz = ez + 0.001
        c, nr = probe(lx, cz)
        yaw = 0.82 * atan2(nr.x, -nr.y)
        ring = [Vector((x * cos(yaw), x * sin(yaw), z)) for x, _, z in superellipse_xz(*shape, count=40)]
        cy = c.y - 0.018
        for p in ring[::2]:  # keep every point of the rim clear of the cheeks
            sy = probe(lx + p.x, cz + p.z)[0].y
            cy = min(cy, sy - 0.006 - p.y)
        for s in (-1, 1):
            mk(f"{n}_rim{s}", bm_tube(superellipse_xz(*shape, count=40), tube, 6, True, (0, 1, 0)),
               M["frames"], (s * lx, cy, cz), (0, 0, s * yaw), head)
        bz = cz + 0.22 * shape[1]
        hx = shape[0] * sqrt(1 - 0.22 ** 2)
        ix, iy = lx - hx * cos(yaw), cy - hx * sin(yaw)
        mk(f"{n}_bridge", bm_tube([(-ix, iy, bz), (0, iy - 0.003, bz + 0.007), (ix, iy, bz)], tube, 6), M["frames"], parent=head)
        ox, oy = lx + hx * cos(yaw), cy + hx * sin(yaw)
        for s in (-1, 1):
            mk(f"{n}_temple{s}", bm_tube([(s * ox, oy, bz - 0.001), (s * 0.148, -0.085, -0.01), (s * 0.158, -0.01, -0.008)],
                                         tube, 6), M["frames"], parent=head)
    return out


# ----------------------------------------------------------------- assemble

def girl_materials(n, cfg):
    o = cfg["outfit_colors"]
    knit = cfg["outfit"] in ("sweater", "cardigan")
    M = {
        "skin": mat(f"{n}_Skin", cfg["skin"], 0.5, spec=0.4),
        "skin_shade": mat(f"{n}_SkinShade", cfg.get("skin_shade", cfg["skin"]), 0.55, spec=0.4),
        "hair": mat(f"{n}_Hair", cfg["hair"], 0.62, spec=0.3),
        "brow": mat(f"{n}_Brow", cfg["hair"], 0.6),
        "eye": mat(f"{n}_Eye", "#120d0c", 0.12, spec=0.9),
        "glint": emissive(f"{n}_Glint", "#ffffff", 3.0),
        "mouth": mat(f"{n}_Mouth", cfg.get("mouth", "#5b2b29"), 0.6),
        "frames": mat(f"{n}_Frames", cfg.get("frames", "#1a1819"), 0.45, metal=cfg.get("frames_metal", 0.0), spec=0.25),
        "top": mat(f"{n}_Top", o[0], 0.85 if knit else 0.78, rib=0.25 if knit else 0.0, sheen=0.3, grain=0.25,
                   nubs=cfg.get("sweater_nubs", 0.0)),
        "second": mat(f"{n}_Second", o[1], 0.75),
        "trim": mat(f"{n}_Trim", o[2], 0.8, rib=0.35 if knit or cfg["outfit"] == "hoodie" else 0.0, rib_scale=160, sheen=0.3),
        "pants": mat(f"{n}_Pants", cfg.get("pants", "#2b2c38"), 0.82, grain=0.18),
        "accent": mat(f"{n}_Accent", cfg.get("accent", "#d97757"), 0.7),
    }
    return M


def build_girl(cfg, loc, seed=1):
    n = cfg["name"]
    M = girl_materials(n, cfg)
    root = empty(n, loc)
    body = empty(f"{n}_body", (0, 0, 0), root)
    head = empty(f"{n}_head", (0, 0, HEAD_Z - cfg.get("neck_drop", 0.0)), body)  # neck_drop: shorter neck, head sits lower
    cols = body_mod.build_body(n, cfg, body, M)
    if cfg.get("fuse_sleeves"):  # one knit skin: sleeves welded into the torso, remeshed and relaxed so no seam shows
        torso = bpy.data.objects[f"{n}_torso"]
        torso.data.copy().name = f"{n}_torso_core"  # the torso alone, kept so a rig can tell body from sleeve
        bm = bmesh.new()
        bm.from_mesh(torso.data)
        for s in (-1, 1):
            arm = bpy.data.objects[f"{n}_arm{s}"]
            bm.from_mesh(arm.data)
            bpy.data.objects.remove(arm)
        bm.to_mesh(torso.data)
        bm.free()
        rm = torso.modifiers.new("Fuse", "REMESH")
        rm.mode, rm.voxel_size, rm.adaptivity = "VOXEL", 0.0045, 0.0
        sm = torso.modifiers.new("Relax", "SMOOTH")
        sm.factor, sm.iterations = 0.6, 10
        torso["fused"] = True
    if cfg.get("sweater_lumps"):  # soft, irregular puffy lumps on the sweater (not on cuffs/hem)
        tex = bpy.data.textures.new(f"{n}_Lumps", "CLOUDS")
        tex.noise_basis, tex.noise_scale, tex.noise_depth = "IMPROVED_PERLIN", cfg.get("lump_size", 0.035), 1
        for ob in body.children:
            if ob.type == "MESH" and ob.data.materials and ob.data.materials[0] == M["top"]:
                if not ob.get("fused"):  # the remeshed torso is already dense
                    pre = ob.modifiers.new("PreSubd", "SUBSURF")
                    pre.levels = pre.render_levels = 1
                d = ob.modifiers.new("Lumps", "DISPLACE")
                d.texture, d.texture_coords, d.strength, d.mid_level = tex, "LOCAL", cfg["sweater_lumps"], 0.5
                ob["sweater"] = True
    face = build_face(n, cfg, head, M)

    hair = Hair(n, head, M["hair"], cols, seed)
    st = cfg["hair_style"]
    if st == "long":
        hair.cap()
        hair.long_hair(length=0.3, part_x=0.0)
        hair.curtain_bangs()
    elif st == "long_front":
        hair.cap()
        hair.long_hair(length=cfg.get("hair_len", 0.26), part_x=0.0, width=0.07, count=cfg.get("hair_count", 32),
                       front_len=cfg.get("hair_front"))
        hair.face_frame(n=cfg.get("frame_n", 3), hang=cfg.get("frame_hang", 0.2))
    elif st == "bob":
        hair.cap()
        hair.bob()
        hair.blunt_fringe()
    elif st == "top_bun":
        hair.cap(-1)
        tie = hair.pulled_back((90, 68))
        up = dae(90, 68)
        hair.bun(tie + up * 0.045, up)
        mk(f"{n}_scrunchie", bm_tube(ring_pts(tie + up * 0.006, 0.033, up, 20), 0.011, 7, True, up), M["accent"], parent=head)
        if cfg.get("front_hair"):
            hair.face_frame()
        else:
            hair.curtain_bangs(n=2, hang=0.03)
            hair.tendrils(0.11)
    elif st == "wavy":
        hair.cap()
        hair.long_hair(length=0.19, part_x=0.05, wave=0.012, flare=0.022, width=0.058)
        hair.side_swept(to_left=True, n=3, hang=0.07, wave=0.008)
    elif st == "low_pony":
        hair.cap(-1)
        tie = hair.pulled_back((152, -24))
        hair.tail(tie, [(-0.02, -0.02, -0.06), (-0.035, -0.07, -0.13), (-0.01, -0.13, -0.22), (0.02, -0.15, -0.33)],
                  count=11, width=0.05, spread=0.018)
        tdir = (dae(152, -24) + Vector((0, -0.3, -0.6))).normalized()
        mk(f"{n}_scrunchie", bm_tube(ring_pts(tie + tdir * 0.01, 0.023, tdir, 18), 0.011, 7, True, tdir), M["accent"], parent=head)
        hair.curtain_bangs(n=2, hang=0.035)
    hair_ob = hair.finish()
    for v in hair_ob.data.vertices:  # hair follows the sculpted skull
        v.co = face["sculpt"](v.co)
    soften(root)
    if cfg.get("sweater_facets"):  # crumpled low-poly look: decimate the lumpy sweater and flat-shade it
        for ob in body.children:
            if ob.get("sweater"):
                ob.modifiers.remove(ob.modifiers["Subd"])
                dec = ob.modifiers.new("Facets", "DECIMATE")
                dec.ratio = cfg["sweater_facets"]
                ob.data.shade_flat()
    # low-poly look like the sweater: flat-shaded, decimated facets on skin (skull, ears, neck) and hair
    # value: ratio, or (ratio, subdivision levels kept before decimating) for finer facets
    for key, names in (("skin_facets", ("_skull", "_ear", "_neck")), ("hair_facets", ("_hair",))):
        v = cfg.get(key)
        if not v:
            continue
        ratio, lv = v if isinstance(v, tuple) else (v, 0)
        for ob in root.children_recursive:
            if ob.type == "MESH" and any(k in ob.name for k in names) and "Subd" in ob.modifiers:
                if lv:
                    ob.modifiers["Subd"].levels = ob.modifiers["Subd"].render_levels = lv
                else:
                    ob.modifiers.remove(ob.modifiers["Subd"])
                if ratio < 1.0:
                    ob.modifiers.new("Facets", "DECIMATE").ratio = ratio
                ob.data.shade_flat()
    return dict(root=root, body=body, head=head, **face)


FINE = ("eye", "glint", "lash", "brow", "btn", "nose", "mouth", "rim", "bridge", "temple", "logo")


def soften(root):
    """Smooth shading everywhere; one subdivision level on the larger forms so nothing reads as blocks."""
    for ob in root.children_recursive:
        if ob.type != "MESH":
            continue
        ob.data.shade_smooth()
        if "_shoe" in ob.name or "_sole" in ob.name:  # dense lofts: keep crisp sole edges instead of subdividing
            ob.data.set_sharp_from_angle(angle=0.75)
            continue
        if not any(k in ob.name for k in FINE):
            md = ob.modifiers.new("Subd", "SUBSURF")
            md.levels = md.render_levels = 1


VARIANTS = [
    dict(name="V1_Aanya", skin="#e6ae88", skin_shade="#d99872", hair="#1d1513", hair_style="long", glasses="round",
         frames="#1b1718", outfit="sweater", outfit_colors=("#ece2d0", "#ece2d0", "#e3d6c0"), pants="#3b3a48"),
    dict(name="V2_Bea", skin="#c4845e", skin_shade="#b27049", hair="#231814", hair_style="bob", glasses=None,
         outfit="overshirt", outfit_colors=("#4a6a96", "#f3efe8", "#3d5a82"), pants="#2c2b33"),
    dict(name="V3_Cleo", skin="#eebb96", skin_shade="#dfa27c", hair="#5b3322", hair_style="long_front", glasses="round",
         face_sq=2.25, face_fill=2.2, face_flat=2.25, face_chin=0.95, face_cheek=0.035, seed=3, neck_drop=0.03, sweater_lumps=0.008, lump_size=0.07, sweater_facets=0.4, fuse_sleeves=True, skin_facets=(0.5, 1), hair_facets=(0.6, 1), hair_front=0.17, frame_hang=0.13,
         eye_x=0.062, lens=0.045, lens_x=0.064, mouth_z=-0.096, nose_z=-0.056, mouth_w=1.15,
         frames="#c8a065", frames_metal=0.9, outfit="hoodie", outfit_colors=("#b9a8de", "#f4efe6", "#a996d1"),
         accent="#f0b44c", pants="#55688f", pants_cuff="#677aa0"),
    dict(name="V4_Dani", skin="#8f5b3d", skin_shade="#7c4b30", hair="#141010", hair_style="wavy", glasses="oval",
         frames="#3a2219", frames_metal=0.2, outfit="puffer", outfit_colors=("#3f6f57", "#c9c7c1", "#365f4b"),
         mouth="#4a2420", pants="#2a2a30"),
    dict(name="V5_Esha", skin="#dda07a", skin_shade="#cb8c66", hair="#2e1d16", hair_style="low_pony", glasses="rect",
         frames="#1b1718", outfit="cardigan", outfit_colors=("#4c4b57", "#efe6d6", "#4c4b57"), accent="#d97757",
         pants="#2a2a33"),
]
