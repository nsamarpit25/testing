"""Claude mascot variants: soft clay terracotta characters built around the spark motif.

Desk scale (about 0.13 m tall), feet at z=0, face toward -Y.
"""
import bpy
import bmesh
from functools import partial
from math import sin, cos, pi, radians, sqrt, hypot, copysign
from mathutils import Vector, Quaternion, Euler, Matrix, noise
from kit import link, mk, empty, ellipsoid, bm_ico, bm_box, scale_bm, bm_tube, ring_pts, mat, emissive, jitter
from body import bm_sweep
from girls import surface_probe, facing, soften
from mathutils.bvhtree import BVHTree

CLAY = "#d4704c"
CRAIL = "#cc6544"  # Claude terracotta, set a little deeper so it still reads orange (not salmon) once lit and coated


def claude_materials(n):
    return {
        "clay": mat(f"{n}_Clay", CLAY, 0.52, spec=0.3, grain=0.12),
        "clay_light": mat(f"{n}_ClayLight", "#e88a64", 0.52, spec=0.3, grain=0.12),
        "dark": mat(f"{n}_Feet", "#b35a3e", 0.6, grain=0.1),
        "cream": mat(f"{n}_Cream", "#f6e8d6", 0.5, spec=0.35, sheen=0.2, grain=0.1),
        "eye": mat(f"{n}_Eye", "#1a1210", 0.12, spec=0.9),
        "glint": emissive(f"{n}_Glint", "#ffffff", 3.0),
        "blush": mat(f"{n}_Blush", "#f2877a", 0.8),
        "mouth": mat(f"{n}_Mouth", "#5b2a26", 0.6),
        "gloss": mat(f"{n}_Gloss", CLAY, 0.36, spec=0.45, coat=0.35, grain=0.05),
        "visor": mat(f"{n}_Visor", "#2b1e1c", 0.18, spec=0.6, coat=1.0),
        "glow": emissive(f"{n}_Glow", "#ffd3a1", 4.0),
        "pearl": mat(f"{n}_Pearl", "#f1ede8", 0.2, spec=0.55, coat=0.7),
        "copper": mat(f"{n}_Copper", "#c9653f", 0.3, metal=0.55, spec=0.5, coat=0.3),
        "glass": mat(f"{n}_Glass", "#06080e", 0.05, spec=0.8, coat=1.0),
        "seam": mat(f"{n}_Seam", "#2b2427", 0.5),
        "eyeglow": emissive(f"{n}_EyeGlow", "#eef4ff", 7.0),
        "thrust": emissive(f"{n}_Thrust", "#fff0d8", 9.0),
        "crail": mat(f"{n}_Crail", CRAIL, 0.3, spec=0.5, coat=0.6, grain=0.03),
        "crail_deep": mat(f"{n}_CrailDeep", "#b65a3c", 0.32, spec=0.5, coat=0.5),
        "clay_m": mat(f"{n}_ClayMatte", "#cf6a48", 0.5, spec=0.35, grain=0.06),
        "cream_m": mat(f"{n}_CreamMatte", "#efe4d3", 0.5, spec=0.35, grain=0.05),
        "stem": mat(f"{n}_Stem", "#7a4a3a", 0.45),
        "screen": mat(f"{n}_Screen", "#0d0a0a", 0.22, spec=0.4, coat=0.5),  # softer gloss so tilted screens stay dark
        "screenglow": emissive(f"{n}_ScreenGlow", "#ffcfa6", 5.0),
        "screenglow_o": emissive(f"{n}_ScreenGlowOrange", "#ff8f5a", 4.0),
        "core": emissive(f"{n}_Core", "#ff6a2a", 3.0),  # kept moderate so AgX leaves it orange, not white
        "shell": shell_mat(f"{n}_Shell"),
    }


def shell_mat(name):
    """Frosted peach shell you can see a glowing core through (alpha blended, faint self glow)."""
    m = mat(name, "#f3c4a6", 0.3, emit="#ffb184", strength=0.15, spec=0.6, coat=0.6)
    m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.3
    m.use_backface_culling = True
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        pass
    return m


# ----------------------------------------------------------------- geometry

def meta_bm(elems, res=0.005, threshold=0.6):
    """Smooth union of metaball elements -> bmesh. elems: (type, co, radius, size_x, rotation)."""
    mb = bpy.data.metaballs.new("tmp_meta")
    mb.resolution = mb.render_resolution = res
    mb.threshold = threshold
    for kind, co, r, sx, rot in elems:
        e = mb.elements.new(type=kind)
        e.co, e.radius = co, r
        if kind == "CAPSULE":
            e.size_x = sx
        elif kind in ("ELLIPSOID", "CUBE"):
            e.size_x, e.size_y, e.size_z = sx
        if rot is not None:
            e.rotation = rot
    ob = link(bpy.data.objects.new("tmp_meta", mb))
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm


def ray(theta, dist, length, r):
    """Capsule element pointing along angle theta (degrees) in the front (XZ) plane."""
    t = radians(theta)
    d = Vector((cos(t), 0, sin(t)))
    return ("CAPSULE", d * (dist + length / 2), r, length / 2, Quaternion((0, 1, 0), -t))


def fit(bm, height, yscale=1.0):
    """Flatten front-to-back, scale to a target height and drop the bottom to z=0."""
    for v in bm.verts:
        v.co.y *= yscale
    zs = [v.co.z for v in bm.verts]
    k = height / (max(zs) - min(zs))
    z0 = min(zs)
    for v in bm.verts:
        v.co = Vector((v.co.x * k, v.co.y * k, (v.co.z - z0) * k))
    return k


def pill_eyes(n, root, probe, M, x=0.016, z=0.07, size=(0.0058, 0.006, 0.0135), glint=True):
    for s in (-1, 1):
        c, nr = probe(s * x, z)
        e = ellipsoid(f"{n}_eye{s}", size, M["eye"], c - nr * 0.0022, facing(nr), root, sub=2)
        if glint:
            ellipsoid(f"{n}_glint{s}", (size[0] * 0.38, 0.0015, size[0] * 0.42), M["glint"],
                      (size[0] * 0.3, -size[1] * 0.9, size[2] * 0.42), parent=e, sub=1)


def blush(n, root, probe, M, x, z, r=0.0085):
    for s in (-1, 1):
        c, nr = probe(s * x, z)
        ellipsoid(f"{n}_blush{s}", (r, 0.0018, r * 0.55), M["blush"], c + nr * 0.0002, facing(nr), root, sub=2)


def smile(n, root, probe, M, z, w=0.007, depth=0.0025):
    pts = []
    for i in range(7):
        u = -1 + 2 * i / 6
        c, nr = probe(u * w, z - depth * (1 - u * u))
        pts.append(c - nr * 0.0004)
    mk(f"{n}_mouth", bm_tube(pts, 0.0013, 6), M["mouth"], parent=root)


def feet(n, root, M, xs, y=-0.004, r=(0.014, 0.017, 0.009)):
    for i, x in enumerate(xs):
        ellipsoid(f"{n}_foot{i}", r, M["dark"], (x, y, r[2] * 0.95), parent=root, sub=2)


# ----------------------------------------------------------------- variants

def spark(n, root, M):
    """Classic: a plump ten-ray starburst. The low rays are legs, the side rays are arms."""
    lens = [1.0, 0.86, 1.08, 0.92, 1.0, 1.0, 0.92, 1.08, 0.86, 1.0]
    elems = [("BALL", Vector((0, 0, 0)), 0.075, 0, None)]
    for i, L in enumerate(lens):
        elems.append(ray(108 + 36 * i, 0.03, 0.05 * L, 0.034))
    bm = meta_bm(elems)
    fit(bm, 0.128, 0.62)
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M["clay"], parent=root)
    pill_eyes(n, root, probe, M, 0.015, 0.068)
    smile(n, root, probe, M, 0.05)


def puff(n, root, M):
    """Puffy cloud-flower: a fat round core ringed with soft lobes, stubby arms and feet."""
    elems = [("BALL", Vector((0, 0, 0)), 0.08, 0, None), ("BALL", Vector((0, -0.012, -0.004)), 0.062, 0, None)]
    for i in range(8):
        t = radians(90 + 45 * i)
        elems.append(("BALL", Vector((cos(t), 0, sin(t))) * 0.05, 0.045, 0, None))
    bm = meta_bm(elems)
    fit(bm, 0.112, 0.8)
    for v in bm.verts:
        v.co.z += 0.014
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M["clay"], parent=root)
    pill_eyes(n, root, probe, M, 0.017, 0.074, size=(0.0068, 0.006, 0.0115))
    blush(n, root, probe, M, 0.033, 0.058)
    smile(n, root, probe, M, 0.058, w=0.006)
    for s in (-1, 1):
        ellipsoid(f"{n}_arm{s}", (0.014, 0.012, 0.018), M["clay"], (s * 0.066, -0.004, 0.05), (0, s * 0.5, 0), root, sub=2)
    feet(n, root, M, (-0.022, 0.022), y=-0.016, r=(0.016, 0.019, 0.01))


def cookie(n, root, M):
    """Logo cookie: a thick, pillowy eight-ray asterisk standing on two feet, terminal-style eyes."""
    N, R0, A, T, rr = 8, 0.04, 0.025, 0.032, 0.011
    th0 = pi / 2 + pi / N  # two rays straddle the bottom and become legs

    def outline(t):
        k = (0.5 + 0.5 * cos(N * (t - th0))) ** 1.1
        return R0 + A * k

    seg, prof = 128, 9
    bm = bmesh.new()
    rings = []
    for j in range(prof):
        ph = -pi / 2 + pi * j / (prof - 1)
        y = -T / 2 * sin(ph)
        shrink = rr * (1 - cos(ph))
        ring = []
        for i in range(seg):
            t = 2 * pi * i / seg
            r = outline(t) - shrink
            ring.append(bm.verts.new((r * cos(t), y, r * sin(t))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r0[(i + 1) % seg], r1[(i + 1) % seg], r1[i]))
    for ring, flip in ((rings[0], False), (rings[-1], True)):  # flat caps as concentric quad rings, not a fan
        prev = ring
        for f in (0.8, 0.6, 0.4, 0.22):
            cur = [bm.verts.new((v.co.x * f, v.co.y, v.co.z * f)) for v in ring]
            for i in range(seg):
                q = (prev[i], prev[(i + 1) % seg], cur[(i + 1) % seg], cur[i])
                bm.faces.new(q[::-1] if flip else q)
            prev = cur
        c = bm.verts.new((0, ring[0].co.y, 0))
        for i in range(seg):
            t = (c, prev[(i + 1) % seg], prev[i])
            bm.faces.new(t[::-1] if flip else t)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts:
        v.co.z += 0.074
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M["clay"], parent=root)
    for s in (-1, 1):
        c, nr = probe(s * 0.012, 0.076)
        mk(f"{n}_eye{s}", bm_box(0.0075, 0.005, 0.017, 0.0034, 3), M["eye"], c - nr * 0.0012, facing(nr), root)
    feet(n, root, M, (-0.0245, 0.0245), r=(0.014, 0.017, 0.009))
    smile(n, root, probe, M, 0.058, w=0.0055, depth=0.002)


def mochi(n, root, M):
    """Round mochi body with a little spark sprouting from the top of its head."""
    bm = bm_ico(1.0, 4)
    scale_bm(bm, (0.056, 0.05, 0.05))
    for v in bm.verts:
        if v.co.z < -0.026:
            v.co.z = -0.026 + (v.co.z + 0.026) * 0.4
        v.co.z += 0.036
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M["clay"], parent=root)
    top = Vector((0, 0.004, 0.084))
    for i, a in enumerate((-58, -29, 0, 29, 58)):
        t = radians(90 + a)
        d = Vector((cos(t), 0.12, sin(t)))
        L = 0.03 if a == 0 else 0.024
        mk(f"{n}_ray{i}", bm_sweep([(top, 0.0072), (top + d * L * 0.6, 0.0068), (top + d * L, 0.0046)], steps=3, seg=12),
           M["clay_light"], parent=root)
    pill_eyes(n, root, probe, M, 0.019, 0.042, size=(0.0078, 0.006, 0.0105))
    blush(n, root, probe, M, 0.034, 0.03, r=0.009)
    smile(n, root, probe, M, 0.026, w=0.0065)
    for s in (-1, 1):
        ellipsoid(f"{n}_arm{s}", (0.011, 0.01, 0.015), M["clay"], (s * 0.055, -0.008, 0.026), (0, s * 0.6, 0), root, sub=2)
    feet(n, root, M, (-0.022, 0.022), y=-0.02, r=(0.015, 0.017, 0.009))


def bloom(n, root, M):
    """Sunflower: a cream face disc ringed with ten terracotta petals."""
    cz = 0.074
    bm = bm_ico(1.0, 4)
    scale_bm(bm, (0.038, 0.022, 0.038))
    for v in bm.verts:
        v.co.z += cz
    probe = surface_probe(bm)
    mk(f"{n}_face", bm, M["cream"], parent=root)
    for i in range(10):
        t = radians(108 + 36 * i)  # two petals straddle the bottom and act as legs
        d = Vector((cos(t), 0, sin(t)))
        ellipsoid(f"{n}_petal{i}", (0.015, 0.011, 0.026), M["clay"], Vector((0, 0.008, cz)) + d * 0.047,
                  (-0.25, -t + pi / 2, 0), root, sub=3)
    pill_eyes(n, root, probe, M, 0.013, cz + 0.004, size=(0.0055, 0.006, 0.011))
    blush(n, root, probe, M, 0.024, cz - 0.01, r=0.0065)
    smile(n, root, probe, M, cz - 0.012, w=0.0055)
    feet(n, root, M, (-0.0226, 0.0226), r=(0.014, 0.016, 0.009))


VARIANTS = [("C1_Spark", spark), ("C2_Puff", puff), ("C3_Cookie", cookie), ("C4_Mochi", mochi), ("C5_Bloom", bloom)]


# ----------------------------------------------------------------- orbs

R_ORB = 0.046
HOVER = 0.1  # orb centre height: they float above the desk, no feet
HOVERING = {"shadow": 0.05}  # returned by orb builders: ask for a soft shadow on the desk below


def hover_shadow(n, root, r):
    """Soft round shadow decal on the surface under a floating mascot (radial falloff, alpha-blended)."""
    m = bpy.data.materials.new(f"{n}_Shadow")
    nt = m.node_tree
    nt.nodes.clear()
    tc, g = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexGradient")
    g.gradient_type = "SPHERICAL"
    pw, mul = nt.nodes.new("ShaderNodeMath"), nt.nodes.new("ShaderNodeMath")
    pw.operation, mul.operation = "POWER", "MULTIPLY"
    pw.inputs[1].default_value, mul.inputs[1].default_value = 1.7, 0.5
    tr, df, mix = nt.nodes.new("ShaderNodeBsdfTransparent"), nt.nodes.new("ShaderNodeBsdfDiffuse"), nt.nodes.new("ShaderNodeMixShader")
    df.inputs["Color"].default_value = (0.05, 0.022, 0.018, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Object"], g.inputs["Vector"])
    nt.links.new(g.outputs["Fac"], pw.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(df.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        pass
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in ((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0))]
    bm.faces.new(vs)
    ob = mk(f"{n}_shadow", bm, m, (0, 0.004, 0.0008), parent=root)
    ob.scale = (r, r * 0.85, 1)
    return ob


def orb_body(n, root, M, cz, r=R_ORB, key="gloss"):
    bm = bm_ico(1.0, 4)
    scale_bm(bm, (r, r, r))
    for v in bm.verts:
        v.co.z += cz
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M[key], parent=root)
    return probe


def orb_face(n, root, probe, M, cz, dz=0.0):
    pill_eyes(n, root, probe, M, 0.016, cz + 0.012 + dz, size=(0.0068, 0.006, 0.0122))
    blush(n, root, probe, M, 0.031, cz - 0.003 + dz, r=0.0078)
    smile(n, root, probe, M, cz - 0.007 + dz, w=0.0062)


def bm_ring(r_in, r_out, ht, seg=128, step=0.0025):
    """Flat annulus with fully rounded edges, revolved around Z. Flat faces are sampled finely so bands can be painted."""
    rc0, rc1 = r_in + ht, r_out - ht
    k = max(2, int((rc1 - rc0) / step))
    prof = [(rc0 + (rc1 - rc0) * i / k, -ht) for i in range(k)]
    prof += [(rc1 + ht * sin(pi * i / 8), -ht * cos(pi * i / 8)) for i in range(8)]
    prof += [(rc1 - (rc1 - rc0) * i / k, ht) for i in range(k)]
    prof += [(rc0 - ht * sin(pi * i / 8), ht * cos(pi * i / 8)) for i in range(8)]
    bm = bmesh.new()
    rings = [[bm.verts.new((r * cos(2 * pi * i / seg), r * sin(2 * pi * i / seg), z)) for r, z in prof] for i in range(seg)]
    P = len(prof)
    for i in range(seg):
        a, b = rings[i], rings[(i + 1) % seg]
        for j in range(P):
            bm.faces.new((a[j], a[(j + 1) % P], b[(j + 1) % P], b[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def paint_bands(ob, mats, bands):
    """bands: [(r_lo, r_hi, material slot)] by distance from the ring's axis."""
    for m in mats:
        ob.data.materials.append(m)
    for p in ob.data.polygons:
        r = hypot(p.center.x, p.center.y)
        for lo, hi, slot in bands:
            if lo <= r < hi:
                p.material_index = slot


def saturn(n, root, M):
    """Saturn: a glossy terracotta planet wearing a wide, tilted cream ring with painted bands."""
    cz = HOVER
    probe = orb_body(n, root, M, cz)
    orb_face(n, root, probe, M, cz)
    ring = mk(f"{n}_ring", bm_ring(0.057, 0.086, 0.0024), M["cream"], (0, 0, cz), (0.36, 0.2, 0), root)
    paint_bands(ring, (M["clay_light"], M["dark"]), [(0, 0.065, 1), (0.0735, 0.0765, 2)])
    return HOVERING


def moonlet(n, root, M):
    """Orb with a tiny spark moon circling it, a tapering comet trail sweeping under its smile."""
    cz = HOVER
    probe = orb_body(n, root, M, cz)
    orb_face(n, root, probe, M, cz)
    rot = Euler((0.42, -0.3, 0)).to_matrix()
    c = Vector((0, 0, cz))

    def orbit(theta, R=0.074):
        t = radians(theta)
        return c + rot @ Vector((R * cos(t), R * sin(t), 0))

    elems = [("BALL", Vector((0, 0, 0)), 0.075, 0, None)]
    elems += [ray(90 + 45 * i, 0.03, 0.05, 0.034) for i in range(8)]
    bm = meta_bm(elems)
    fit(bm, 0.034, 0.62)
    p = orbit(15)
    for v in bm.verts:
        v.co += p - Vector((0, 0, 0.017))
    mk(f"{n}_moon", bm, M["clay_light"], parent=root)
    trail = [(orbit(10 - 8 * k), 0.0028 * (1 - k / 22) + 0.0005) for k in range(21)]  # comet tail tapering behind the moon
    mk(f"{n}_trail", bm_sweep(trail, steps=2, seg=10), M["cream"], parent=root)
    return HOVERING


def visor(n, root, M):
    """Assistant orb: a dark glossy face screen with glowing eyes and smile, little side pods."""
    cz = HOVER
    orb_body(n, root, M, cz)
    a, b, zc, Rv, e = 0.031, 0.022, cz + 0.004, R_ORB + 0.0016, 3.2
    seg = 96

    def onball(x, z):
        return Vector((x, -sqrt(max(Rv * Rv - x * x - (z - cz) ** 2, 1e-8)), z))

    bm = bmesh.new()
    rings = []
    for f in (1.0, 0.82, 0.62, 0.42, 0.22):
        ring = []
        for i in range(seg):
            t = 2 * pi * i / seg
            ct, st = cos(t), sin(t)
            ring.append(bm.verts.new(onball(f * a * copysign(abs(ct) ** (2 / e), ct), zc + f * b * copysign(abs(st) ** (2 / e), st))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r1[i], r1[(i + 1) % seg], r0[(i + 1) % seg]))
    mid = bm.verts.new(onball(0, zc))
    for i in range(seg):
        bm.faces.new((rings[-1][i], mid, rings[-1][(i + 1) % seg]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:  # outward = toward -Y
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    vprobe = surface_probe(bm)
    vis = mk(f"{n}_visor", bm, M["visor"], parent=root)
    sol = vis.modifiers.new("Shell", "SOLIDIFY")
    sol.thickness, sol.offset = 0.0026, -1.0
    for s in (-1, 1):
        c, nr = vprobe(s * 0.012, zc + 0.004)
        ellipsoid(f"{n}_eye{s}", (0.0056, 0.0026, 0.0098), M["glow"], c - nr * 0.0008, facing(nr), root, sub=2)
    smile(n, root, vprobe, dict(M, mouth=M["glow"]), zc - 0.011, w=0.0058, depth=0.0022)
    for s in (-1, 1):
        ellipsoid(f"{n}_pod{s}", (0.0075, 0.015, 0.015), M["clay_light"], (s * (R_ORB - 0.002), 0, cz + 0.004), parent=root, sub=3)
    return HOVERING


def sunorb(n, root, M):
    """Spark crown: the orb sits in the middle of the spark, its rays floating free around it like a sun."""
    cz = HOVER
    probe = orb_body(n, root, M, cz)
    orb_face(n, root, probe, M, cz)
    for i in range(10):
        t = radians(108 + 36 * i)
        d = Vector((cos(t), 0, sin(t)))
        L = 0.024 if i % 2 == 0 else 0.019
        p0 = Vector((0, 0.01, cz)) + d * (R_ORB + 0.007)
        mk(f"{n}_ray{i}", bm_sweep([(p0, 0.0062), (p0 + d * L * 0.55, 0.0068), (p0 + d * L, 0.0052)], steps=3, seg=14),
           M["clay_light"], parent=root)
    return HOVERING


def gyro(n, root, M):
    """Orb floating inside two crossed orbit rings, like a little gyroscope."""
    cz, R = HOVER, 0.044
    probe = orb_body(n, root, M, cz, r=R)
    orb_face(n, root, probe, M, cz)
    c = Vector((0, 0, cz))
    for k, (ax, az, bead) in enumerate(((0.3, 0.6, 14), (-0.3, -0.6, 40))):
        nrm = Euler((ax, 0, az)).to_matrix() @ Vector((0, -1, 0))
        pts = ring_pts(c, 0.062, nrm, 72)
        mk(f"{n}_orbit{k}", bm_tube(pts, 0.003, 12, closed=True), M["cream"], parent=root)
        ellipsoid(f"{n}_bead{k}", (0.0062,) * 3, M["clay_light"], pts[bead], parent=root, sub=2)
    return HOVERING


def sph(c, r, phi, th):
    """Point on a sphere: phi = azimuth from the front (+ toward +X), th = elevation."""
    return c + r * Vector((sin(phi) * cos(th), -cos(phi) * cos(th), sin(th)))


def pearl(n, root, M, ring=2, ears=2, seams=True, fin=True, cuffs=True, thrust_ring=True, hands=True):
    """Pearl-white robot orb: wraparound glass visor with glowing eyes, copper ear rings and a clipped copper orbit ring,
    a thruster glow underneath and two little floating hands.
    Simplify with: ring 2 clipped / 1 plain / 0 none, ears 2 ring+cap / 1 flat pod / 0 none, and the detail switches."""
    cz, R = 0.115, 0.05
    c = Vector((0, 0, cz))
    orb_body(n, root, M, cz, r=R, key="pearl")

    # visor: superellipse window in angle space so it wraps around the sphere
    pa, tb, t0, e, seg = radians(58), radians(30), radians(3), 4.0, 112

    def win(t, f, r):
        ct, st = cos(t), sin(t)
        return sph(c, r, f * pa * copysign(abs(ct) ** (2 / e), ct), t0 + f * tb * copysign(abs(st) ** (2 / e), st))

    Rv = R + 0.0014
    bm = bmesh.new()
    rings = [[bm.verts.new(win(2 * pi * i / seg, f, Rv)) for i in range(seg)] for f in (1.0, 0.86, 0.7, 0.53, 0.36, 0.19)]
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r1[i], r1[(i + 1) % seg], r0[(i + 1) % seg]))
    mid = bm.verts.new(sph(c, Rv, 0, t0))
    for i in range(seg):
        bm.faces.new((rings[-1][i], mid, rings[-1][(i + 1) % seg]))
    bm.normal_update()
    if sum(f.normal.dot(f.calc_center_median() - c) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    vis = mk(f"{n}_visor", bm, M["glass"], parent=root)
    sol = vis.modifiers.new("Shell", "SOLIDIFY")
    sol.thickness, sol.offset = 0.0034, -1.0
    if seams:
        groove = [win(2 * pi * i / seg, 1.05, R + 0.0002) for i in range(seg)]
        mk(f"{n}_seamvisor", bm_tube(groove, 0.0007, 6, closed=True), M["seam"], parent=root)

    # panel seams on the shell: a cap line over the visor and one under it
    for k, (th, tilt) in enumerate(((radians(47), 0.12), (radians(-40), -0.08)) if seams else ()):
        rot = Euler((tilt, 0, 0)).to_matrix()
        pts = [c + rot @ (sph(Vector(), R + 0.0002, 2 * pi * i / 96, th)) for i in range(96)]
        mk(f"{n}_seam{k}", bm_tube(pts, 0.0007, 6, closed=True), M["seam"], parent=root)

    # glowing eyes on the glass
    for s in (-1, 1):
        nrm = sph(Vector(), 1.0, s * radians(15), t0 + radians(5))
        ellipsoid(f"{n}_eye{s}", (0.0052, 0.0022, 0.0088), M["eyeglow"], c + nrm * (Rv + 0.0006), facing(nrm), root, sub=4)

    # ear pods: copper ring with a pearl cap, just behind the visor edge
    for s in (-1, 1) if ears else ():
        nrm = sph(Vector(), 1.0, s * radians(82), radians(4))
        pc = c + nrm * (R - 0.0012)
        if ears == 1:
            ellipsoid(f"{n}_ear{s}", (0.013, 0.0045, 0.013), M["copper"], pc + nrm * 0.0012, facing(nrm), root, sub=3)
            continue
        mk(f"{n}_ear{s}", bm_tube(ring_pts(pc, 0.0135, nrm, 48), 0.0046, 14, closed=True), M["copper"], parent=root)
        ellipsoid(f"{n}_earcap{s}", (0.0105, 0.0042, 0.0105), M["pearl"], pc + nrm * 0.0028, facing(nrm), root, sub=3)

    # little copper fin on the crown
    if fin:
        mk(f"{n}_fin", bm_sweep([(sph(c, R - 0.0008, 0, radians(68)), 0.0026), (sph(c, R + 0.0012, 0, radians(84)), 0.0031),
                                 (sph(c, R + 0.0012, 0, radians(100)), 0.0029), (sph(c, R - 0.0008, 0, radians(114)), 0.0024)],
                                steps=4, seg=12), M["copper"], parent=root)

    # thruster glow under the orb
    bot = Vector((0, 0, cz - R))
    if thrust_ring:
        mk(f"{n}_thrustring", bm_tube(ring_pts(bot + Vector((0, 0, 0.0028)), 0.0145, (0, 0, 1), 48), 0.0028, 12, closed=True),
           M["copper"], parent=root)
    ellipsoid(f"{n}_thrust", (0.0125, 0.0125, 0.0026), M["thrust"], bot + Vector((0, 0, 0.0012)), parent=root, sub=3)
    ld = bpy.data.lights.new(f"{n}_ThrustLight", "POINT")
    ld.energy, ld.shadow_soft_size, ld.color = 0.35, 0.006, (1.0, 0.86, 0.68)
    lo = link(bpy.data.objects.new(f"{n}_ThrustLight", ld))
    lo.parent, lo.location = root, bot - Vector((0, 0, 0.008))

    if ring:
        orbit_ring(n, root, c, 0.08, M["copper"], M["pearl"] if ring == 2 else None)

    # floating hands
    for s in (-1, 1) if hands else ():
        hc = Vector((s * 0.064, -0.018, cz - 0.05))
        ellipsoid(f"{n}_hand{s}", (0.0115,) * 3, M["pearl"], hc, parent=root, sub=3)
        if cuffs:
            ellipsoid(f"{n}_cuff{s}", (0.0098, 0.0098, 0.0042), M["copper"], hc + Vector((0, 0, 0.0085)), parent=root, sub=3)
    return {"shadow": 0.06}


def orbit_ring(n, root, c, r, ring_mat, clip_mat=None, tilt=(0.36, 0.2, 0), tube=0.0023, beads=True):
    """The Pearl's roundabout: a tilted tube ring, optionally with eight clips and two beads. Returns the ring points."""
    nrm = Euler(tilt).to_matrix() @ Vector((0, 0, 1))
    pts = ring_pts(c, r, nrm, 120)
    mk(f"{n}_orbit", bm_tube(pts, tube, 12, closed=True), ring_mat, parent=root)
    front = min(range(120), key=lambda i: pts[i].y)
    if clip_mat:
        for k in range(8):
            i = (front + 7 + 15 * k) % 120
            t = (pts[(i + 1) % 120] - pts[i - 1]).normalized()
            mk(f"{n}_clip{k}", bm_tube([pts[i] - t * 0.0036, pts[i] + t * 0.0036], tube + 0.0014, 12), clip_mat, parent=root)
        for k, off in enumerate((-16, 15) if beads else ()):
            ellipsoid(f"{n}_bead{k}", (tube * 2.5,) * 3, clip_mat, pts[(front + off) % 120], parent=root, sub=3)
    return pts


# ----------------------------------------------------------------- Claude-spark orbs (Pearl build quality, Claude identity)

# the spark: twelve rounded rays, uneven in length and spacing like a hand-drawn asterisk (angle in the XZ plane, length)
SPARK = [(90, 1.0), (119, 0.7), (147, 0.92), (178, 0.76), (207, 1.0), (237, 0.66), (268, 0.9), (297, 0.74),
         (325, 0.98), (355, 0.68), (25, 0.93), (57, 0.72)]


def spark_bm(reach, thick, core=0.07, ray_r=0.03, ray_len=0.085, rays=SPARK, res=0.004):
    """Inflated spark centred on the origin, facing -Y: ray tips reach `reach`, total depth about `thick`."""
    elems = [("BALL", Vector((0, 0, 0)), core, 0, None)] + [ray(th, 0.02, ray_len * L, ray_r) for th, L in rays]
    bm = meta_bm(elems, res=res)
    k = reach / max(hypot(v.co.x, v.co.z) for v in bm.verts)
    ky = thick / (max(v.co.y for v in bm.verts) - min(v.co.y for v in bm.verts))
    for v in bm.verts:
        v.co = Vector((v.co.x * k, v.co.y * ky, v.co.z * k))
    return bm


def screen(n, root, M, probe, zc, a, b, e=3.4, off=0.0016, thick=0.003):
    """Dark glass face screen laid over any front surface (via its probe). Returns a probe of the screen."""
    seg = 96

    def at(x, z):
        q, nr = probe(x, z)
        return q + nr * off

    bm = bmesh.new()
    rings = [[bm.verts.new(at(f * a * copysign(abs(cos(t)) ** (2 / e), cos(t)), zc + f * b * copysign(abs(sin(t)) ** (2 / e), sin(t))))
              for t in (2 * pi * i / seg for i in range(seg))] for f in (1.0, 0.82, 0.62, 0.42, 0.22)]
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r1[i], r1[(i + 1) % seg], r0[(i + 1) % seg]))
    mid = bm.verts.new(at(0, zc))
    for i in range(seg):
        bm.faces.new((rings[-1][i], mid, rings[-1][(i + 1) % seg]))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:  # outward = toward -Y
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    vprobe = surface_probe(bm)
    sol = mk(f"{n}_visor", bm, M["glass"], parent=root).modifiers.new("Shell", "SOLIDIFY")
    sol.thickness, sol.offset = thick, -1.0
    return vprobe


def glow_eyes(n, root, M, vprobe, zc, dx=0.0125, size=(0.0052, 0.0022, 0.0088)):
    for s in (-1, 1):
        q, nr = vprobe(s * dx, zc)
        ellipsoid(f"{n}_eye{s}", size, M["eyeglow"], q + nr * 0.0006, facing(nr), root, sub=4)


def spark_core(n, root, M):
    """The spark itself is the body: glossy terracotta asterisk with a glass screen face in its core,
    a cream roundabout with terracotta clips circling it."""
    cz = 0.115
    c = Vector((0, 0, cz))
    bm = spark_bm(0.088, 0.046, core=0.085, ray_r=0.031, ray_len=0.114)
    for v in bm.verts:
        v.co += c
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M["crail"], parent=root)
    vprobe = screen(n, root, M, probe, cz + 0.001, 0.022, 0.0145)
    glow_eyes(n, root, M, vprobe, cz + 0.003, dx=0.0092, size=(0.0041, 0.0019, 0.007))
    orbit_ring(n, root, c, 0.1, M["pearl"], M["crail_deep"])
    return {"shadow": 0.06}


def spark_pod(n, root, M):
    """The Pearl rebuilt in Claude colours: terracotta shell, cream trim and roundabout, a cream spark on the forehead."""
    info = pearl(n, root, dict(M, pearl=M["crail"], copper=M["pearl"]), seams=False, fin=False)
    c, R = Vector((0, 0, 0.115)), 0.05
    nrm = sph(Vector(), 1.0, 0, radians(50))
    mk(f"{n}_emblem", spark_bm(0.018, 0.0045, core=0.05, ray_r=0.028, ray_len=0.11, res=0.003), M["pearl"], c + nrm * (R - 0.0006), facing(nrm), root)
    return info


def spark_halo(n, root, M):
    """Cream Pearl head framed by a terracotta spark behind it, a slim terracotta roundabout carrying a little spark moon."""
    cz = 0.115
    c = Vector((0, 0, cz))
    info = pearl(n, root, M, ring=0, ears=0, seams=False, fin=False, hands=False)
    bm = spark_bm(0.118, 0.026, core=0.06, ray_r=0.03, ray_len=0.15)
    for v in bm.verts:
        v.co += c + Vector((0, 0.022, 0))
    mk(f"{n}_halo", bm, M["crail"], parent=root)
    pts = orbit_ring(n, root, c, 0.126, M["crail_deep"], tilt=(0.3, -0.18, 0), tube=0.0019)
    moon = min(pts, key=lambda q: q.y - 0.4 * q.x)  # front-right of the ring
    mk(f"{n}_moon", spark_bm(0.014, 0.006, core=0.05, ray_r=0.028, ray_len=0.11, res=0.003), M["crail"], moon, parent=root)
    root.scale = (0.8,) * 3
    return info


# ----------------------------------------------------------------- desk directions: simple shapes, calm faces, Cleo's facets

def facet(root, size=0.0032, lv=1, keep=("eye", "mouth", "glint", "visor", "stem", "core", "shadow")):
    """Cleo's low-poly look: one subdivision, then decimate to facets of roughly `size` metres, flat shaded."""
    for ob in root.children_recursive:
        if ob.type != "MESH" or "Subd" not in ob.modifiers or any(k in ob.name for k in keep):
            continue
        ob.modifiers["Subd"].levels = ob.modifiers["Subd"].render_levels = lv
        area = sum(p.area for p in ob.data.polygons)
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons) * 4 ** lv
        ratio = min(1.0, area / (size * size) / tris)
        if ratio < 1.0:
            ob.modifiers.new("Facets", "DECIMATE").ratio = ratio
        ob.data.shade_flat()


def calm_face(n, root, probe, M, z, dx=0.012, eye=(0.0036, 0.0035, 0.0072), mouth=-0.0105, w=0.005):
    """Small eyes and a thin smile: friendly, not cartoon-baby."""
    pill_eyes(n, root, probe, M, dx, z, size=eye)
    smile(n, root, probe, dict(M, mouth=M["eye"]), z + mouth, w=w, depth=0.0017)


def on(bm, dz):
    for v in bm.verts:
        v.co.z += dz
    return bm


def glow_orb(n, root, M):
    """Frosted peach orb floating over the desk, a glowing spark for a heart, a calm face on the shell."""
    cz, R = 0.1, 0.045
    bm = bm_ico(1.0, 3)
    scale_bm(bm, (R, R, R))
    probe = surface_probe(on(bm, cz))
    shell = mk(f"{n}_body", bm, M["shell"], parent=root)
    shell.visible_shadow = False  # let the heart light the desk
    mk(f"{n}_core", on(spark_bm(0.018, 0.01, core=0.06, ray_r=0.03, ray_len=0.1), cz - 0.017), M["core"], parent=root)
    ld = bpy.data.lights.new(f"{n}_HeartLight", "POINT")
    ld.energy, ld.shadow_soft_size, ld.color = 0.5, 0.01, (1.0, 0.62, 0.4)
    lo = link(bpy.data.objects.new(f"{n}_HeartLight", ld))
    lo.parent, lo.location = root, (0, 0, cz - 0.017)
    calm_face(n, root, probe, M, cz + 0.017, mouth=-0.0085)
    return {"shadow": 0.05, "facets": 0.0034}


def screen_bot(n, root, M):
    """Little desk robot: terracotta base, cream rounded head, dark screen with glowing eyes and smile, spark on its chest."""
    base = bm_ico(1.0, 3)
    scale_bm(base, (0.034, 0.03, 0.024))
    for v in base.verts:
        v.co.z = max(v.co.z, -0.016)
    bprobe = surface_probe(on(base, 0.016))
    mk(f"{n}_base", base, M["clay_m"], parent=root)
    mk(f"{n}_neck", bm_tube([(0, 0.002, 0.034), (0, 0.002, 0.056)], 0.007, 12), M["cream_m"], parent=root)
    hz = 0.086
    head = on(bm_box(0.09, 0.06, 0.066, 0.017, 3), hz)
    hprobe = surface_probe(head)
    mk(f"{n}_body", head, M["cream_m"], parent=root)
    vprobe = screen(n, root, dict(M, glass=M["screen"]), hprobe, hz + 0.001, 0.031, 0.021, e=4.0, off=0.0008, thick=0.0018)
    for s in (-1, 1):
        q, nr = vprobe(s * 0.011, hz + 0.005)
        ellipsoid(f"{n}_eye{s}", (0.0036, 0.0016, 0.0066), M["screenglow"], q + nr * 0.0005, facing(nr), root, sub=3)
    smile(n, root, vprobe, dict(M, mouth=M["screenglow"]), hz - 0.007, w=0.0052, depth=0.0018)
    q, nr = bprobe(0, 0.016)
    mk(f"{n}_spark", spark_bm(0.012, 0.0035, core=0.05, ray_r=0.028, ray_len=0.11, res=0.003), M["cream_m"], q + nr * 0.0004, facing(nr), root)
    return {"facets": 0.0034}


def flat_spark(n, root, M):
    """The Claude spark itself, thick and flat like a cut-out, floating, with a small face in its middle."""
    cz = 0.1
    bm = on(spark_bm(0.066, 0.024, core=0.075, ray_r=0.03, ray_len=0.1), cz)
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, M["clay_m"], parent=root)
    calm_face(n, root, probe, M, cz + 0.004, dx=0.0085, eye=(0.003, 0.003, 0.006), mouth=-0.0092, w=0.0042)
    return {"shadow": 0.05, "facets": 0.0055}  # bigger facets: small ones turn the dense spark mesh lumpy


def spark_blob(n, root, M):
    """Soft cream gumdrop sitting on the desk, calm face, a thin antenna with a terracotta spark on top."""
    bm = bm_ico(1.0, 3)
    scale_bm(bm, (0.046, 0.04, 0.042))
    for v in bm.verts:
        if v.co.z < 0:
            v.co.x *= 1 + 0.1 * (-v.co.z / 0.042)
            v.co.y *= 1 + 0.1 * (-v.co.z / 0.042)
        v.co.z = max(v.co.z, -0.03)
    top = 0.042 + 0.03
    probe = surface_probe(on(bm, 0.03))
    mk(f"{n}_body", bm, M["cream_m"], parent=root)
    calm_face(n, root, probe, M, 0.044, dx=0.0125)
    tip = Vector((0.006, 0.004, top + 0.03))
    mk(f"{n}_stem", bm_sweep([((0, 0.003, top - 0.003), 0.0017), ((0.002, 0.004, top + 0.015), 0.0014), (tip, 0.0012)], steps=4, seg=8),
       M["stem"], parent=root)
    mk(f"{n}_spark", spark_bm(0.0115, 0.0045, core=0.05, ray_r=0.028, ray_len=0.11, res=0.003), M["clay_m"], tip + Vector((0, 0, 0.008)),
       parent=root)
    return {"facets": 0.0034}


DESK = [("G1_GlowOrb", glow_orb), ("S2_ScreenBot", screen_bot), ("F3_FlatSpark", flat_spark), ("B4_SparkBlob", spark_blob)]


# ----------------------------------------------------------------- one-piece screen buddies: a single body, a screen for a face

def screen_face(n, root, M, vprobe, zc, glow, dx=0.011, eye=(0.0036, 0.0016, 0.0066), mouth=-0.012, w=0.0052):
    for s in (-1, 1):
        q, nr = vprobe(s * dx, zc + 0.004)
        ellipsoid(f"{n}_eye{s}", eye, M[glow], q + nr * 0.0005, facing(nr), root, sub=3)
    smile(n, root, vprobe, dict(M, mouth=M[glow]), zc + 0.004 + mouth, w=w, depth=0.0018)


def spark_rings(insets, rays=SPARK, w0=0.05, w1=0.11, blend=0.02, seg=540):
    """The Claude spark as clean 2D outlines (reach 1): rounded strokes from the centre, a touch thinner at the root,
    softly filleted where they meet. One outline per inset (reach units), each sampled at the same `seg` angles."""
    strokes = [(cos(radians(th)), sin(radians(th)), L) for th, L in rays]

    def sdf(x, y):
        d = 1e9
        for cx, cy, L in strokes:
            h = max(0.0, min(1.0, (x * cx + y * cy) / L))
            e = hypot(x - cx * L * h, y - cy * L * h) - (w0 + (w1 - w0) * h)
            k = max(0.0, min(1.0, 0.5 + 0.5 * (d - e) / blend))  # smooth union
            d = d + (e - d) * k - blend * k * (1 - k)
        return d

    def edge(c, s, inset):  # the outline is star-shaped about the centre: bisect along each angle
        lo, hi = 0.0, 1.4
        for _ in range(24):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if sdf(mid * c, mid * s) < -inset else (lo, mid)
        return lo
    angs = [(cos(2 * pi * i / seg), sin(2 * pi * i / seg)) for i in range(seg)]
    scale = max(edge(c, s, 0.0) for c, s in angs[::6])
    return [[(c * r, s * r) for c, s in angs for r in [edge(c, s, k * scale) / scale]] for k in insets]


def emblem(n, root, M, probe, x, z, key, reach=0.0105, tag="logo", h=0.0012):
    """The Claude spark as a raised decal wrapped onto the surface through its probe: crisp outline, rounded edge, smooth."""
    b = 0.03 * reach  # edge rounding
    prof = [(0.0, -0.0008)] + [(b * (1 - cos(a)), h - b + b * sin(a)) for a in (pi / 2 * i / 4 for i in range(5))]
    bm = bmesh.new()
    loops = []
    for (k, ht), ring in zip(prof, spark_rings([k / reach for k, _ in prof])):
        loops.append([bm.verts.new(q + nr * ht) for q, nr in (probe(x + u * reach, z + v * reach) for u, v in ring)])
    N = len(loops[0])
    for lo, up in zip(loops, loops[1:]):
        for i in range(N):
            j = (i + 1) % N
            bm.faces.new((up[j], up[i], lo[i], lo[j]))
    q, nr = probe(x, z)
    c = bm.verts.new(q + nr * h)
    for i in range(N):
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % N], c))
        bm.edges.get((loops[-1][i], loops[-1][(i + 1) % N])).smooth = False  # flat-faced top, no creases into the centre
    return mk(f"{n}_{tag}", bm, M[key], parent=root)


def face_screen(n, root, M, probe, zc, a, b, e=4.0):
    return screen(n, root, dict(M, glass=M["screen"]), probe, zc, a, b, e=e, off=0.0008, thick=0.0018)


def pebble(n, root, M):
    """Cream pebble, screen on the upper half, terracotta spark on its tummy."""
    bm = bm_ico(1.0, 3)
    scale_bm(bm, (0.042, 0.036, 0.05))
    for v in bm.verts:
        if v.co.z < 0:
            k = 1 + 0.12 * (-v.co.z / 0.05)
            v.co.x, v.co.y = v.co.x * k, v.co.y * k
        v.co.z = max(v.co.z, -0.04)
    probe = surface_probe(on(bm, 0.04))
    mk(f"{n}_body", bm, M["cream_m"], parent=root)
    vprobe = face_screen(n, root, M, probe, 0.062, 0.027, 0.0175, e=3.6)
    screen_face(n, root, M, vprobe, 0.062, "screenglow")
    emblem(n, root, M, probe, 0, 0.026, "clay_m")
    return {"facets": 0.0034}


def squircle(n, root, M, body="cream_m", mark="clay_m", glow="screenglow_o"):
    """Soft rounded cube, a touch narrower at the top, screen across the front, spark under it."""
    bm = bm_box(0.08, 0.066, 0.08, 0.024, 4)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= 1 - 0.08 * v.co.z / 0.04
            v.co.y *= 1 - 0.05 * v.co.z / 0.04
    probe = surface_probe(on(bm, 0.04))
    mk(f"{n}_body", bm, M[body], parent=root)
    vprobe = face_screen(n, root, M, probe, 0.053, 0.029, 0.017)
    screen_face(n, root, M, vprobe, 0.053, glow)
    emblem(n, root, M, probe, 0, 0.0205, mark, reach=0.012)
    return {"facets": 0.0034}


def screen_orb(n, root, M):
    """Cream ball floating over the desk, a wide screen for a face, a small spark on the forehead."""
    cz, R = 0.1, 0.042
    bm = bm_ico(1.0, 3)
    scale_bm(bm, (R, R, R))
    probe = surface_probe(on(bm, cz))
    mk(f"{n}_body", bm, M["cream_m"], parent=root)
    vprobe = face_screen(n, root, M, probe, cz - 0.007, 0.03, 0.016)
    screen_face(n, root, M, vprobe, cz - 0.007, "screenglow_o")
    emblem(n, root, M, probe, 0, cz + 0.0235, "clay_m", reach=0.011)
    return {"shadow": 0.045, "facets": 0.0034}


def tablet(n, root, M):
    """A tiny terracotta tablet standing on the desk, leaning back a little; the whole front is screen, a glowing spark under the smile."""
    bm = bm_box(0.072, 0.028, 0.1, 0.012, 4)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, -0.05), matrix=Matrix.Rotation(radians(-8), 3, "X"))
    probe = surface_probe(on(bm, 0.05))
    mk(f"{n}_body", bm, M["clay_m"], parent=root)
    zc = 0.055
    vprobe = face_screen(n, root, M, probe, zc, 0.028, 0.037, e=4.5)
    screen_face(n, root, M, vprobe, zc + 0.008, "screenglow")
    emblem(n, root, M, vprobe, 0, zc - 0.021, "screenglow_o", reach=0.0075, tag="glowlogo")
    return {"facets": 0.0034}


def dome(n, root, M):
    """Low terracotta dome, a wide screen band for a face, cream spark on top."""
    bm = bm_ico(1.0, 3)
    scale_bm(bm, (0.05, 0.044, 0.052))
    for v in bm.verts:
        v.co.z = max(v.co.z, -0.004)
    probe = surface_probe(on(bm, 0.004))
    mk(f"{n}_body", bm, M["clay_m"], parent=root)
    vprobe = face_screen(n, root, M, probe, 0.026, 0.032, 0.0135)
    screen_face(n, root, M, vprobe, 0.024, "screenglow", mouth=-0.0095)
    emblem(n, root, M, probe, 0, 0.047, "cream_m", reach=0.009)
    return {"facets": 0.0034}


# ----------------------------------------------------------------- puffy star: chunky low-poly orange star, bar eyes, round feet

def puff_mats(n):
    return {"puff": mat(f"{n}_Puff", "#ee4a06", 0.55, spec=0.35, grain=0.06),
            "puff_feet": mat(f"{n}_PuffFeet", "#bb3504", 0.6, grain=0.06),
            "bar": mat(f"{n}_Bar", "#0a0807", 0.4, spec=0.3)}


FEET4 = [(-0.0085, -0.011, 0.0118), (0.0085, -0.011, 0.0118), (-0.0235, 0.003, 0.0108), (0.0235, 0.003, 0.0108)]


def round_feet(n, root, m, spots=FEET4):
    """Little round feet tucked under the body."""
    for i, (x, y, r) in enumerate(spots):
        ellipsoid(f"{n}_foot{i}", (r, r, r * 0.8), m, (x, y, r * 0.8), (0, 0, 0), root, sub=2)


def bar_eyes(n, root, m, probe, z, dx=0.0108, size=(0.0068, 0.004, 0.0172), out=-0.0007, bevel=0.001):
    """Two tall bars for eyes; `out` sets how far they stand off the surface (negative = sunk in)."""
    for s in (-1, 1):
        q, nr = probe(s * dx, z)
        mk(f"{n}_eye{s}", bm_box(*size, bevel, 2), m, q + nr * out, facing(nr), root)


def puff_body(n, root, m, elems, w, depth, lift, height=None, jit=0.0007):
    """Metaballs -> faceted-ready body scaled to w x depth (x height), bottom at `lift`. Returns (probe, centre z)."""
    bm = meta_bm(elems, res=0.05)
    xs, ys, zs = ([getattr(v.co, a) for v in bm.verts] for a in "xyz")
    k, ky = w / (max(xs) - min(xs)), depth / (max(ys) - min(ys))
    kz = height / (max(zs) - min(zs)) if height else k
    for v in bm.verts:
        v.co = Vector((v.co.x * k, v.co.y * ky, v.co.z * kz))
    jitter(bm, jit, freq=60.0, seed=2.0)
    cz = lift + (max(zs) - min(zs)) * kz / 2
    probe = surface_probe(on(bm, cz))
    mk(f"{n}_body", bm, m, parent=root)
    return probe, cz


def star_elems(lobes=7):
    elems = [("BALL", Vector((0, 0, 0)), 1.45, 0, None)]
    for i in range(lobes):  # rounded lobes round the rim, a little uneven so it reads hand-made
        t = radians(90 + 360 * i / lobes + (4 if i % 2 else -3))
        elems.append(("BALL", Vector((cos(t), 0, sin(t))) * (0.9 + 0.04 * (i % 3 == 1)), 0.55, 0, None))
    return elems


def puff_star(n, root, M, lobes=7, w=0.086, depth=0.054, lift=0.0075):
    """A puffy, rounded orange star standing on little round feet: low-poly facets, two tall black bar eyes, no mouth."""
    P = puff_mats(n)
    probe, cz = puff_body(n, root, P["puff"], star_elems(lobes), w, depth, lift)
    bar_eyes(n, root, P["bar"], probe, cz + 0.003)
    round_feet(n, root, P["puff_feet"])
    root.scale = (1.12, 1.12, 1.12)  # a touch bigger beside Cleo
    return {"facets": 0.0047}


# ----------------------------------------------------------------- mixes: the puffy star x the screen cube

def star_screen(n, root, M):
    """Mix 1: the puffy star, with the cube's dark screen for a face (glowing bar eyes and a small smile)."""
    P = puff_mats(n)
    probe, cz = puff_body(n, root, P["puff"], star_elems(), 0.088, 0.056, 0.0075)
    vprobe = face_screen(n, root, M, probe, cz + 0.001, 0.025, 0.0145)
    bar_eyes(n, root, M["screenglow"], vprobe, cz + 0.004, dx=0.0095, size=(0.0052, 0.002, 0.0128), out=0.0004, bevel=0.0009)
    smile(n, root, vprobe, dict(M, mouth=M["screenglow"]), cz - 0.0065, w=0.0045, depth=0.0016)
    round_feet(n, root, P["puff_feet"])
    root.scale = (1.12, 1.12, 1.12)
    return {"facets": 0.0047}


def puff_cube(n, root, M):
    """Mix 2: the cube's shape built puffy like the star (soft bulging corners), low-poly orange, black bar eyes,
    the cream spark on its tummy, round feet."""
    P = puff_mats(n)
    elems = [("BALL", Vector((0, 0, 0)), 1.2, 0, None)]
    elems += [("BALL", Vector((x, 0, z)) * 0.42, 0.85, 0, None) for x in (-1, 1) for z in (-1, 1)]  # fill out a square
    ring = [(0.74, 0.74), (0.82, 0.0), (0.0, 0.8)]  # bumps round a square outline: corners and edge middles
    elems += [("BALL", Vector((sx * x, 0, sz * z)), 0.5, 0, None) for x, z in ring for sx in (-1, 1) for sz in (-1, 1)
              if not ((x == 0 and sx < 0) or (z == 0 and sz < 0))]
    probe, cz = puff_body(n, root, P["puff"], elems, 0.082, 0.066, 0.0085, height=0.08)
    bar_eyes(n, root, P["bar"], probe, cz + 0.008, dx=0.0112)
    emblem(n, root, M, probe, 0, cz - 0.017, "cream_m", reach=0.0105)
    round_feet(n, root, P["puff_feet"])
    root.scale = (1.12, 1.12, 1.12)
    return {"facets": 0.0047}


def screen_cube_feet(n, root, M):
    """Mix 3: the soft cube with its screen face and cream spark, made in the star's orange and low-poly facets,
    glowing bar eyes on the screen, standing on the star's round feet."""
    P = puff_mats(n)
    lift = 0.009
    bm = bm_box(0.08, 0.066, 0.08, 0.024, 4)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.x *= 1 - 0.08 * v.co.z / 0.04
            v.co.y *= 1 - 0.05 * v.co.z / 0.04
    probe = surface_probe(on(bm, lift + 0.04))
    mk(f"{n}_body", bm, P["puff"], parent=root)
    zc = lift + 0.053
    vprobe = face_screen(n, root, M, probe, zc, 0.029, 0.017)
    bar_eyes(n, root, M["screenglow"], vprobe, zc + 0.004, dx=0.011, size=(0.0056, 0.002, 0.0135), out=0.0004, bevel=0.0009)
    smile(n, root, vprobe, dict(M, mouth=M["screenglow"]), zc - 0.0075, w=0.005, depth=0.0017)
    emblem(n, root, M, probe, 0, lift + 0.0205, "cream_m", reach=0.012)
    round_feet(n, root, P["puff_feet"])
    root.scale = (1.12, 1.12, 1.12)
    return {"facets": 0.0047}


MIX = [("M1_StarScreen", star_screen), ("M2_PuffCube", puff_cube), ("M3_CubeFeet", screen_cube_feet)]

# ----------------------------------------------------------------- pixel critter: the little terminal sprite, built from voxels

PIXEL = [" ######### ",
         " #o#####o# ",
         "###########",
         " ######### ",
         " # #   # # ",
         " # #   # # "]
CUBE_FACES = [((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))), ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
              ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))), ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
              ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))), ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)))]


def pixel_critter(n, root, M, v=0.0095, depth=5, art=PIXEL, facet=0.0068):
    """The sprite as a chunky voxel toy: body `depth` voxels deep, arms a little shallower, thin legs, eyes as dark pixels."""
    rows, cols = len(art), len(art[0])
    vox, eyes = set(), set()
    for r, line in enumerate(art):
        z = rows - 1 - r
        for c, ch in enumerate(line):
            if ch == " ":
                continue
            ds = [depth // 2] if r >= 4 else range(1, depth - 1) if c in (0, cols - 1) else range(depth)
            vox.update((c, d, z) for d in ds)
            if ch == "o":
                eyes.add((c, z))
    bm, vid = bmesh.new(), {}

    def vert(i, j, k):
        if (i, j, k) not in vid:
            vid[i, j, k] = bm.verts.new(((i - cols / 2) * v, (j - depth / 2) * v, k * v))
        return vid[i, j, k]
    front = {(c, z): min(d for cc, d, zz in vox if (cc, zz) == (c, z)) for c, _, z in vox}
    for c, d, z in vox:
        for (dx, dy, dz), corners in CUBE_FACES:
            if (c + dx, d + dy, z + dz) in vox:
                continue
            f = bm.faces.new([vert(c + a, d + b, z + e) for a, b, e in corners])
    bmesh.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts[:], edges=bm.edges[:])
    ob = mk(f"{n}_body", bm, mat(f"{n}_Pix", "#e05a22", 0.55, spec=0.3, grain=0.04), parent=root)
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments, bev.limit_method = 0.0042, 4, "ANGLE"  # softly rounded voxel edges
    ob.modifiers.new("Dense", "SUBSURF").subdivision_type = "SIMPLE"
    ob.modifiers["Dense"].levels = ob.modifiers["Dense"].render_levels = 3
    lump = bpy.data.textures.new(f"{n}_Lumps", "CLOUDS")
    lump.noise_scale, lump.noise_depth = 0.022, 1
    big = ob.modifiers.new("Lumps", "DISPLACE")  # broad dents so edges and silhouettes wander instead of running straight
    big.texture, big.strength, big.mid_level, big.texture_coords = lump, 0.0075, 0.5, "LOCAL"
    even = ob.modifiers.new("Even", "REMESH")  # even density everywhere so legs facet as coarsely as the body
    even.mode, even.voxel_size, even.adaptivity = "VOXEL", 0.0018, 0.0
    bpy.context.view_layer.update()
    me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    area, tris = sum(p.area for p in me.polygons), sum(len(p.vertices) - 2 for p in me.polygons)
    ob.to_mesh_clear()
    ob.modifiers.new("Facets", "DECIMATE").ratio = min(1.0, 2.0 * area / (facet * facet) / tris)  # big flat triangles
    bpy.context.view_layer.update()
    flat = bmesh.new()  # bake the stack, then even out the decimated slivers into chunky triangles
    flat.from_mesh(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh())
    ob.to_mesh_clear()
    ob.modifiers.clear()
    bmesh.ops.triangulate(flat, faces=flat.faces[:])
    bmesh.ops.beautify_fill(flat, faces=flat.faces[:], edges=flat.edges[:])
    off = Vector((3.1, 7.7, 1.9))
    for vt in flat.verts:  # knock every corner a little off: uneven edges, facets tilted to catch light differently
        vt.co += noise.noise_vector(vt.co * (0.6 / facet) + off) * facet * 0.22
    flat.to_mesh(ob.data)
    flat.free()
    ob.data.shade_flat()
    eye_m = mat(f"{n}_PixEye", "#0d0a09", 0.45)
    for i, (c, z) in enumerate(sorted(eyes)):  # square pixel eyes kept as their own crisp pieces
        loc = ((c - cols / 2 + 0.5) * v, (front[c, z] - depth / 2) * v - 0.0006, (z + 0.5) * v)
        mk(f"{n}_eye{2 * i - 1}", bm_box(v * 0.92, 0.003, v * 0.92, 0.0005, 2), eye_m, loc, (0, 0, 0.04 * (i - 0.5)), root)
    root.scale = (1.25, 1.25, 1.25)  # reads at desk-toy size beside Cleo
    return {"crisp": True, "facets": None}


# ----------------------------------------------------------------- reference stars: the film's chubby low-poly star on a plinth

def star_mats(n, body="#e5531d"):
    return {"star": mat(f"{n}_Star", body, 0.62, spec=0.28),
            "star_feet": mat(f"{n}_StarFeet", "#c9441a", 0.66, spec=0.25),
            "bar": mat(f"{n}_StarEye", "#0b0807", 0.7, spec=0.15),
            "plinth": mat(f"{n}_Plinth", "#b8422a", 0.55, spec=0.3),
            "book": mat(f"{n}_Book", "#21434a", 0.6, spec=0.25),
            "pages": mat(f"{n}_Pages", "#efe4d0", 0.7, spec=0.2)}


def lobe_ring(lobes, centre, r, dist, tilt=0.0):
    """A fat middle ball with rounded lobes round the rim, a little uneven so it reads hand-made."""
    elems = [("BALL", Vector((0, 0, 0)), centre, 0, None)]
    for i in range(lobes):
        t = radians(90 + tilt + 360 * i / lobes + (3 if i % 2 else -2))
        elems.append(("BALL", Vector((cos(t), 0, sin(t))) * dist * (1 + 0.03 * (i % 3 == 1)), r, 0, None))
    elems.append(("BALL", Vector((0, 0, -0.5)), centre * 0.62, 0, None))  # a full round tummy, not a point, over the feet
    return elems


def relax_wrap(bm, tree, it):
    """Even the triangles out: pull each vertex to its neighbours' average, then back onto the shape along its ray."""
    for _ in range(it):
        avg = {v: sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) for v in bm.verts}
        for v, a in avg.items():
            hit = tree.ray_cast(Vector(), (v.co * 0.4 + a * 0.6).normalized())[0]
            if hit is not None:
                v.co = hit


def wrapped(elems, size, sub=3, relax=4, jit=0.2, seed=1.0, res=0.03):
    """An icosphere shrunk onto the metaball shape from its centre: even, chunky triangles like the film's star,
    each corner knocked a little off so the facets catch the light unevenly. size = (width, depth, height)."""
    src = meta_bm(elems, res=res)
    tree = BVHTree.FromBMesh(src)
    bm = bm_ico(1.0, sub)
    for v in bm.verts:
        hit = tree.ray_cast(Vector(), v.co.normalized())[0]
        v.co = hit if hit is not None else v.co
    relax_wrap(bm, tree, relax)
    src.free()
    lo = [min(v.co[a] for v in bm.verts) for a in range(3)]
    hi = [max(v.co[a] for v in bm.verts) for a in range(3)]
    k = [size[a] / (hi[a] - lo[a]) for a in range(3)]
    for v in bm.verts:
        v.co = Vector(((v.co.x - (lo[0] + hi[0]) / 2) * k[0], (v.co.y - (lo[1] + hi[1]) / 2) * k[1], (v.co.z - lo[2]) * k[2]))
    edge = sum(e.calc_length() for e in bm.edges) / len(bm.edges)
    off = Vector((seed * 5.3, seed * 1.7, seed * 3.1))
    for v in bm.verts:
        v.co += noise.noise_vector(v.co * (1.3 / edge) + off) * edge * jit
    return bm


def rock(radii, sub=2, jit=0.22, seed=0.0):
    """Faceted pebble for feet: a coarse icosphere with its corners knocked about."""
    bm = bm_ico(1.0, sub)
    scale_bm(bm, radii)
    edge = sum(e.calc_length() for e in bm.edges) / len(bm.edges)
    off = Vector((seed * 2.9, seed * 4.1, seed * 0.7))
    for v in bm.verts:
        v.co += noise.noise_vector(v.co * (1.3 / edge) + off) * edge * jit
    return bm


def flat_bars(n, root, m, probe, z, dx, w, h, tilt=0.0, nx=6, nz=16, lift=0.00055, thick=0.0012):
    """Tall black bar eyes painted onto the facets: a fine grid dropped onto the face along the view axis,
    lifted a hair off it and given a thin back, so they hug every facet with no slab edge from the side."""
    for s in (-1, 1):
        bm = bmesh.new()
        grid = [[None] * (nz + 1) for _ in range(nx + 1)]
        for i in range(nx + 1):
            for j in range(nz + 1):
                u, t = (i / nx - 0.5) * w, (j / nz - 0.5) * h
                x, zz = s * dx + u * cos(tilt) - t * sin(s * tilt), z + t * cos(tilt) + u * sin(s * tilt)
                grid[i][j] = bm.verts.new(probe(x, zz)[0] + Vector((0, -lift, 0)))
        for i in range(nx):
            for j in range(nz):
                bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        bm.normal_update()
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
        mk(f"{n}_eye{s}", bm, m, parent=root)


def plinth(n, root, P, w=0.074, d=0.058, h=0.017, book=True):
    """The little terracotta block it stands on, on a closed teal book. Returns the height of the top."""
    z = 0.0
    if book:
        bh = 0.014
        mk(f"{n}_book", bm_box(w + 0.03, d + 0.026, bh, 0.0012, 2), P["book"], (0.004, 0.002, bh / 2), (0, 0, 0.05), root)
        mk(f"{n}_pages", bm_box(w + 0.024, d + 0.022, bh * 0.72, 0.0004, 1), P["pages"], (0.0055, -0.0005, bh / 2), (0, 0, 0.05), root)
        z = bh
    mk(f"{n}_plinth", bm_box(w, d, h, 0.0012, 2), P["plinth"], (0, 0, z + h / 2), (0, 0, -0.03), root)
    return z + h


def ref_star(n, root, M, lobes=7, centre=1.6, lobe_r=0.62, dist=0.92, W=0.09, depth=0.058, H=0.075, sub=3, jit=0.2,
             eye=(0.0062, 0.02), eye_dx=0.0121, eye_z=0.5, feet="four", stand=True, body="#e5531d", tilt=0.0, seed=1.0):
    """The film's Claude: a chubby rounded star made of big flat facets, two tall flat black bar eyes,
    round faceted feet tucked under, standing on a little block."""
    P = star_mats(n, body)
    base = plinth(n, root, P) if stand else 0.0
    fr = 0.0102 * W / 0.09
    lift = base + fr * 0.95  # body sits down onto its feet
    bm = wrapped(lobe_ring(lobes, centre, lobe_r, dist, tilt), (W, depth, H), sub=sub, jit=jit, seed=seed)
    probe = surface_probe(on(bm, lift))
    mk(f"{n}_body", bm, P["star"], parent=root)
    flat_bars(n, root, P["bar"], probe, lift + H * eye_z, eye_dx * W / 0.09, *eye)
    spots = [(-0.0155, -0.013, fr * 1.05), (0.0155, -0.013, fr * 1.05)]
    if feet == "four":
        spots += [(-0.022, 0.009, fr * 0.95), (0.022, 0.009, fr * 0.95)]
    for i, (x, y, r) in enumerate(spots):
        k = W / 0.09
        mk(f"{n}_foot{i}", rock((r * 1.15, r * 1.1, r * 0.78), 2, 0.2, seed + i), P["star_feet"], (x * k, y * k, base + r * 0.78), (0, 0, 0.4 * i), root)
    return {"crisp": True}


STARS = [("S1_Star", ref_star),
         ("S2_StarClay", partial(ref_star, body="#d97757", jit=0.24, seed=3.0)),
         ("S3_StarRound", partial(ref_star, lobes=6, centre=1.8, lobe_r=0.62, dist=0.9, H=0.08, eye=(0.0068, 0.0215), eye_z=0.53,
                                  stand=False, feet="two", seed=5.0)),
         ("S4_StarSquat", partial(ref_star, lobes=6, centre=1.62, lobe_r=0.6, dist=0.95, W=0.096, H=0.07, tilt=30, eye=(0.0062, 0.0185),
                                  eye_z=0.47, body="#e65a22", seed=7.0))]


# ----------------------------------------------------------------- our Claude: the spark itself as a chubby low-poly critter on a keycap

def decal(name, root, m, probe, at, nu=6, nv=16, lift=0.00055, thick=0.0012):
    """A flat black shape painted onto the facets: at(u, v) maps the unit square onto the face (x, z);
    a fine grid is dropped onto the surface along the view axis, lifted a hair and given a thin back."""
    bm = bmesh.new()
    grid = [[bm.verts.new(probe(*at(i / nu, j / nv))[0] + Vector((0, -lift, 0))) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bm.normal_update()
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thick)
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)  # origin at its middle, so cameras can focus on it
    for v in bm.verts:
        v.co -= c
    return mk(name, bm, m, c, parent=root)


def rect(cx, cz, w, h, turn=0.0):
    return lambda u, v: (cx + (u - 0.5) * w * cos(turn) - (v - 0.5) * h * sin(turn), cz + (v - 0.5) * h * cos(turn) + (u - 0.5) * w * sin(turn))


def arc(cx, cz, R, span, th):
    """A smile: a thick arc hanging under (cx, cz + R)."""
    return lambda u, v: (cx + (R + (v - 0.5) * th) * cos(-pi / 2 + (u - 0.5) * span),
                         cz + R + (R + (v - 0.5) * th) * sin(-pi / 2 + (u - 0.5) * span))


def spark_body(rays=8, core=1.0, ray_r=0.5, ray_len=0.74, short=0.52, skip_down=True, wobble=(0, 4, -3, 5, -4, 2, -5, 3)):
    """Claude's spark, inflated: a round core and rounded rays that alternate long and short, a little uneven,
    the downward ray left out so the feet can sit there."""
    elems = [("BALL", Vector((0, 0, 0)), core, 0, None)]
    for i in range(rays):
        th = 90 + 360 * i / rays + wobble[i % len(wobble)]
        if skip_down and abs(((th - 270 + 180) % 360) - 180) < 25:
            continue
        elems.append(ray(th, 0.22, ray_len * (1.0 if i % 2 == 0 else short), ray_r * (1.0 if i % 2 == 0 else 0.92)))
    elems.append(("BALL", Vector((0, 0, -0.35)), core * 0.85, 0, None))  # full round tummy over the feet
    return elems


def keycap(n, root, P, w=0.07, d=0.062, h=0.024, top=0.82):
    """A big cream keycap for a stand (it lives on a keyboard): tapered sides, soft edges, a shallow dish on top."""
    bm = bm_box(w, d, h, 0.0028, 3)
    for v in bm.verts:
        f = (v.co.z + h / 2) / h
        k = 1 - (1 - top) * f
        v.co.x, v.co.y = v.co.x * k, v.co.y * k
        v.co.z += h / 2
        if v.co.z > h - 0.0015 and abs(v.co.x) < w * top / 2 - 0.004 and abs(v.co.y) < d * top / 2 - 0.004:
            v.co.z -= 0.0012 * (1 - (2 * v.co.x / (w * top)) ** 2)
    mk(f"{n}_keycap", bm, P["cap"], (0, 0, 0), (0, 0, -0.06), root)
    mk(f"{n}_keyshadow", bm_box(w * 1.02, d * 1.02, 0.002, 0.0008, 1), P["capdark"], (0, 0, 0.001), (0, 0, -0.06), root)
    return h - 0.0006


def our_mats(n, body):
    return {"star": mat(f"{n}_Spark", body, 0.6, spec=0.3),
            "star_feet": mat(f"{n}_SparkFeet", "#c24a20", 0.66, spec=0.25),
            "bar": mat(f"{n}_SparkEye", "#0b0807", 0.7, spec=0.15),
            "blush": mat(f"{n}_SparkBlush", "#ff7f6a", 0.7, spec=0.2),
            "cap": mat(f"{n}_Keycap", "#efe6d6", 0.42, spec=0.4),
            "capdark": mat(f"{n}_KeycapFoot", "#bfb3a2", 0.6)}


def our_claude(n, root, M, rays=8, short=0.52, ray_r=0.5, W=0.094, depth=0.058, H=0.084, sub=3, jit=0.2, seed=2.0,
               eyes="bars", smile=True, blush=False, cock=0.0, look=0.0, stand=True, body="#de5f2e", size=1.0, elems=None, eye_z=0.5):
    """Our Claude: the spark as a chubby faceted critter, two stubby feet, flat painted-on eyes, standing on a keycap."""
    P = our_mats(n, body)
    base = keycap(n, root, P) if stand else 0.0
    fr = 0.0108
    lift = base + fr * 0.9
    pivot = empty(f"{n}_pivot", (0, 0, lift), root)
    pivot.rotation_euler = (0, radians(cock), 0)
    bm = wrapped(elems or spark_body(rays, ray_r=ray_r, short=short), (W, depth, H), sub=sub, jit=jit, seed=seed, res=0.025)
    probe = surface_probe(bm)
    mk(f"{n}_body", bm, P["star"], parent=pivot)
    ez = H * eye_z
    if eyes == "bars":
        for s in (-1, 1):
            decal(f"{n}_eye{s}", pivot, P["bar"], probe, rect(s * 0.0118 + look, ez, 0.0064, 0.0165))
    else:  # square pixel eyes, a nod to the terminal sprite
        for s in (-1, 1):
            decal(f"{n}_eye{s}", pivot, P["bar"], probe, rect(s * 0.0115 + look, ez + 0.001, 0.0086, 0.0086), nu=10, nv=10)
    if smile:
        decal(f"{n}_mouth", pivot, P["bar"], probe, arc(look, ez - 0.0175, 0.0042, 2.0, 0.0017), nu=14, nv=3)
    if blush:
        for s in (-1, 1):
            decal(f"{n}_blush{s}", pivot, P["blush"], probe, rect(s * 0.0215 + look, ez - 0.0105, 0.0085, 0.0045), nu=8, nv=4, lift=0.0004)
    for i, s in enumerate((-1, 1)):
        mk(f"{n}_foot{i}", rock((fr * 1.2, fr * 1.15, fr * 0.8), 2, 0.2, seed + i), P["star_feet"],
           (s * 0.0145, -0.006, base + fr * 0.8), (0, 0, 0.3 * s), root)
    root.scale = (size,) * 3
    return {"crisp": True}


OURS = [("C1_Spark", our_claude),
        ("C2_SparkPixel", partial(our_claude, eyes="pixel", smile=False, blush=True, seed=4.0)),
        ("C3_SparkCurious", partial(our_claude, rays=10, short=0.55, ray_r=0.44, cock=-9, look=0.0035, H=0.088, seed=6.0, stand=False, size=1.7))]


# ----------------------------------------------------------------- shape options for the curious one: same face, feet and tilt

def tuft(z0=0.78, r=0.27):
    """A little three-nub spark sprouting from the top of the head: short and fat so the facets keep them round."""
    return [ray(90, z0, 0.3, r), ray(58, z0 - 0.1, 0.18, r * 0.85), ray(122, z0 - 0.1, 0.18, r * 0.85)]


def tummy(z=-0.35, k=0.85):
    return [("BALL", Vector((0, 0, z)), k, 0, None)]


SHAPES = {
    "sparkle": [("BALL", Vector(), 1.0, 0, None)] + [ray(t, 0.2, 0.78, 0.5) for t in (90, 0, 180)] + tummy(-0.3, 0.95),
    "bubble": [("CUBE", Vector(), 0.6, (0.78, 0.6, 0.56), None), ray(238, 0.75, 0.62, 0.27)],  # a speech bubble, tail low left
    "gumdrop": [("BALL", Vector((0, 0, 0.05)), 1.0, 0, None), ("BALL", Vector((0, 0, -0.4)), 1.08, 0, None)] + tuft(0.8),
    "cube": [("CUBE", Vector(), 0.62, (0.62, 0.62, 0.66), None)] + tuft(0.92, 0.24),
    "bean": [("CAPSULE", Vector(), 0.95, 0.42, None), ray(64, 0.75, 0.2, 0.38), ray(116, 0.75, 0.2, 0.38)],
}

CURIOUS = dict(cock=-9, look=0.0035, stand=False, size=1.7, seed=6.0)
SHAPE_OPTS = [("D1_Sparkle", partial(our_claude, elems=SHAPES["sparkle"], H=0.094, W=0.1, **CURIOUS)),
              ("D2_Bubble", partial(our_claude, elems=SHAPES["bubble"], H=0.074, W=0.098, eye_z=0.56, **dict(CURIOUS, size=1.3))),
              ("D3_Gumdrop", partial(our_claude, elems=SHAPES["gumdrop"], H=0.098, W=0.084, eye_z=0.42, **CURIOUS)),
              ("D4_Cube", partial(our_claude, elems=SHAPES["cube"], H=0.098, W=0.082, eye_z=0.42, **CURIOUS)),
              ("D5_Bean", partial(our_claude, elems=SHAPES["bean"], H=0.078, W=0.104, eye_z=0.45, **CURIOUS))]


REF = [("R1_PuffStar", puff_star), ("P1_Pixel", pixel_critter)]

ONE_PIECE = [("E1_Pebble", pebble), ("E2_Squircle", squircle),
             ("E3_SquircleClay", partial(squircle, body="clay_m", mark="cream_m", glow="screenglow")),
             ("E4_ScreenOrb", screen_orb), ("E5_Tablet", tablet), ("E6_Dome", dome)]


HERO = [("K1_SparkCore", spark_core), ("K2_SparkPod", spark_pod), ("K3_SparkHalo", spark_halo)]

ORBS = [("O1_Saturn", saturn), ("O2_Moonlet", moonlet), ("O3_Visor", visor), ("O4_SunOrb", sunorb), ("O5_Gyro", gyro)]


def build_claude(name, fn, loc):
    root = empty(name, loc)
    info = fn(name, root, claude_materials(name))
    soften(root)
    if info and info.get("crisp"):  # blocky builds: keep hard voxel edges
        for ob in root.children_recursive:
            if ob.type == "MESH" and "Subd" in ob.modifiers:
                ob.modifiers.remove(ob.modifiers["Subd"])
                ob.data.shade_flat()
    if info and info.get("facets"):
        facet(root, info["facets"])
    if info and info.get("shadow"):
        hover_shadow(name, root, info["shadow"])
    return root
