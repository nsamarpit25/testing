"""Build the Claude Talk v2 look-dev scene.

Characters (all original, built procedurally from primitives):
  - Cleo   : the girl from girls.py (V3), seated at the desk holding a mug
  - Claude : terracotta "spark" (9 rounded rays), pill eyes, stubby feet
  - Codex  : blue->violet cloud with a glowing ">_" face
Set: cozy desk by a dusk window, city bokeh, fairy lights, desk lamp.

Usage: blender -b --factory-startup -P build_scene.py -- <out.blend>
"""
import bpy, bmesh, math, random, sys
from math import sin, cos, pi, sqrt, atan2, asin, exp, log, floor
from mathutils import Vector, Euler, noise
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from girls import VARIANTS, build_girl  # noqa: E402

FPS = 30
SEED = 7

# --------------------------------------------------------------------------- utils

def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = link(bpy.data.objects.new(name, None))
    e.empty_display_size = 0.05
    e.parent = parent
    e.location = loc
    return e


def mk(name, bm, material, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if material:
        me.materials.append(material)
    if smooth:
        me.shade_smooth()
    ob = link(bpy.data.objects.new(name, me))
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def bm_ico(r=1.0, sub=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    return bm


def bm_box(sx, sy, sz, bevel=0.0, seg=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=seg,
                        affect="EDGES", profile=0.5)
    return bm


def bm_cyl(r, depth, seg=12, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=depth)
    return bm


def scale_bm(bm, s):
    bmesh.ops.scale(bm, vec=s, verts=bm.verts)


def jitter(bm, amp, freq=40.0, seed=0.0):
    """Push verts along normals with smooth noise -> hand-made low-poly feel."""
    bm.normal_update()
    off = Vector((seed * 7.13, seed * 3.71, seed * 1.37))
    for v in bm.verts:
        v.co += v.normal * amp * noise.noise(v.co * freq + off)


def ellipsoid(name, radii, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, sub=2, jit=0.0, seed=0.0):
    bm = bm_ico(1.0, sub)
    scale_bm(bm, radii)
    if jit:
        jitter(bm, jit, 6.0 / max(radii), seed)
    return mk(name, bm, mat, loc, rot, parent)


def limb(name, p0, p1, r, mat, parent=None, sub=2, jit=0.0, seed=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bm_ico(1.0, sub)
    scale_bm(bm, (r, r, d.length / 2 + r * 0.55))
    if jit:
        jitter(bm, jit, 6.0 / r, seed)
    ob = mk(name, bm, mat, parent=parent)
    ob.location = (p0 + p1) / 2
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    return ob


def bm_tube(pts, r, seg=8, closed=False, plane_n=None):
    bm = bmesh.new()
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        if closed:
            t = pts[(i + 1) % n] - pts[i - 1]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        ref = Vector(plane_n) if plane_n is not None else (Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)))
        a = t.cross(ref).normalized()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + r * (cos(2 * pi * j / seg) * a + sin(2 * pi * j / seg) * b))
                      for j in range(seg)])
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(seg):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % seg], r0[(j + 1) % seg]))
    if not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def superellipse_xz(a, b, n=4.0, count=40):
    out = []
    for i in range(count):
        t = 2 * pi * i / count
        c, s = cos(t), sin(t)
        out.append((a * math.copysign(abs(c) ** (2 / n), c), 0.0, b * math.copysign(abs(s) ** (2 / n), s)))
    return out


def ring_pts(center, radius, normal, count=24):
    n = Vector(normal).normalized()
    a = n.orthogonal().normalized()
    b = n.cross(a)
    c = Vector(center)
    return [c + radius * (cos(2 * pi * i / count) * a + sin(2 * pi * i / count) * b) for i in range(count)]


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("-Z", "Y")


# --------------------------------------------------------------------------- materials

def mat(name, hexcol, rough=0.6, metal=0.0, emit=None, strength=0.0, spec=0.5, coat=0.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(hexcol), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.25
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit), 1)
        b.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*lin(hexcol), 1)
    return m


def emissive(name, hexcol, strength):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*lin(hexcol), 1)
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def gradient_mat(name, axis, lo, hi, stops, emit_strength=0.0, rough=0.5, coords="Object", pure_emission=False):
    """Colour ramp along one axis of the given texture-coordinate space."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = stops[0][0], (*lin(stops[0][1]), 1)
    els[1].position, els[1].color = stops[-1][0], (*lin(stops[-1][1]), 1)
    for pos, col in stops[1:-1]:
        e = els.new(pos)
        e.color = (*lin(col), 1)
    nt.links.new(tc.outputs[coords], sep.inputs[0])
    nt.links.new(sep.outputs["XYZ".index(axis)], mr.inputs["Value"])
    nt.links.new(mr.outputs[0], ramp.inputs["Fac"])
    if pure_emission:
        nt.nodes.remove(bsdf)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = emit_strength
        nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        if emit_strength:
            nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


# --------------------------------------------------------------------------- characters

def bm_spark(R, lobes=9, amp=0.30, sharp=1.6, depth=0.68, sub=3, seed=1, jit=0.035):
    """Claude: a plump starburst cookie. Lobes in the XZ (front) plane, thin along Y."""
    bm = bm_ico(1.0, sub)
    rnd = random.Random(seed)
    ph = pi / 2 - pi / lobes
    amps = [amp * (0.85 + 0.3 * rnd.random()) for _ in range(lobes)]
    for v in bm.verts:
        x, y, z = v.co
        u = (atan2(z, x) - ph) / (2 * pi) * lobes
        i = floor(u)
        k = 0.5 - 0.5 * cos(2 * pi * (u - i))
        bump = 1 + amps[int(i) % lobes] * (k ** sharp) * sqrt(x * x + z * z)
        v.co = Vector((x * bump, y * depth, z * bump))
    jitter(bm, jit, 2.5, seed)
    scale_bm(bm, (R, R, R))
    return bm


def bm_cloud(spheres, k=160.0, depth=0.8, sub=3, flat_z=None, jit=0.0015):
    """Codex: star-convex projection of an icosphere onto a smooth union of spheres."""
    bm = bm_ico(1.0, sub)
    for v in bm.verts:
        d = v.co.normalized()
        ts = []
        for cx, cz, r in spheres:
            c = Vector((cx, 0.0, cz))
            b = d.dot(c)
            disc = b * b - c.length_squared + r * r
            if disc > 0:
                ts.append(b + sqrt(disc))
        t = log(sum(exp(k * ti) for ti in ts)) / k if ts else 0.01
        p = d * t
        p.y *= depth
        if flat_z is not None and p.z < flat_z:
            p.z = flat_z + (p.z - flat_z) * 0.12
        v.co = p
    jitter(bm, jit, 60, 3.0)
    return bm


def build_mira(M, root_loc):
    root = empty("Mira", root_loc)
    body = empty("Mira_body", (0, 0, 0), root)
    head = empty("Mira_head", (0, 0, 1.15), body)

    # torso + hoodie
    torso = ellipsoid("Mira_torso", (0.19, 0.14, 0.17), M["hoodie"], (0, 0, 0.86), parent=body, sub=3, jit=0.006, seed=1)
    mk("Mira_collar", bm_tube([Vector((0, 0.02, 0.985)) + Vector(p).xzy for p in superellipse_xz(0.115, 0.1, 2.6, 28)],
                              0.038, 10, True, (0, 0, 1)), M["hoodie"], parent=body)
    ellipsoid("Mira_hood", (0.13, 0.07, 0.09), M["hoodie"], (0, 0.1, 1.0), parent=body, sub=2, jit=0.006, seed=2)
    for s in (-1, 1):
        mk(f"Mira_string{s}", bm_tube([(s * 0.035, -0.112, 0.965), (s * 0.038, -0.128, 0.92), (s * 0.042, -0.142, 0.865)],
                                      0.0042, 6), M["cream"], parent=body)
        mk(f"Mira_aglet{s}", bm_cyl(0.0055, 0.016, 6), M["metal"], (s * 0.042, -0.143, 0.855), parent=body)
        ellipsoid(f"Mira_shoulder{s}", (0.085, 0.085, 0.075), M["hoodie"], (s * 0.165, 0.0, 0.935), parent=body, jit=0.005, seed=3 + s)
        limb(f"Mira_upperarm{s}", (s * 0.2, 0.0, 0.92), (s * 0.235, -0.075, 0.81), 0.062, M["hoodie"], body, jit=0.004, seed=5 + s)
        limb(f"Mira_forearm{s}", (s * 0.232, -0.085, 0.805), (s * 0.088, -0.268, 0.812), 0.054, M["hoodie"], body, jit=0.004, seed=7 + s)
        fdir = Vector((s * 0.088, -0.268, 0.812)) - Vector((s * 0.232, -0.085, 0.805))
        mk(f"Mira_cuff{s}", bm_tube(ring_pts((s * 0.094, -0.26, 0.812), 0.043, fdir, 18), 0.011, 6, True, fdir),
           M["hoodie_dark"], parent=body)
        ellipsoid(f"Mira_hand{s}", (0.034, 0.031, 0.036), M["skin"], (s * 0.058, -0.3, 0.815), parent=body, sub=2, jit=0.002, seed=9 + s)
    # chest pin: tiny Claude spark
    pin = mk("Mira_pin", bm_spark(0.014, sub=2, jit=0.0), M["claude"], (0.085, -0.128, 0.925), (-0.35, 0, 0.2), body)
    pin.scale = (1, 0.5, 1)

    # mug held in both hands
    mug = empty("Mira_mug", (0, -0.31, 0.807), body)
    mk("Mira_mug_body", bm_cyl(0.042, 0.095, 12), M["mug"], parent=mug)
    mk("Mira_mug_band", bm_cyl(0.0428, 0.022, 12), M["claude"], (0, 0, 0.018), parent=mug)
    mk("Mira_coffee", bm_cyl(0.037, 0.004, 12), M["coffee"], (0, 0, 0.04), parent=mug)

    # head
    ellipsoid("Mira_face", (0.15, 0.1425, 0.1395), M["skin"], parent=head, sub=3, jit=0.0015, seed=11)
    for s in (-1, 1):
        ellipsoid(f"Mira_ear{s}", (0.02, 0.028, 0.034), M["skin"], (s * 0.147, 0.005, -0.012), parent=head, sub=1)
    eyes = empty("Mira_eyes", (0, 0, 0), head)
    for s in (-1, 1):
        eye = ellipsoid(f"Mira_eye{s}", (0.0125, 0.008, 0.0175), M["eye"], (s * 0.056, -0.128, -0.002), parent=eyes, sub=2)
        ellipsoid(f"Mira_glint{s}", (0.0036, 0.002, 0.0036), M["glint"], (0.004, -0.0075, 0.0065), parent=eye, sub=1)
        ellipsoid(f"Mira_brow{s}", (0.019, 0.005, 0.0045), M["hair"], (s * 0.06, -0.121, 0.05), (0, -s * 0.12, 0),
                  parent=head, sub=1)
        ellipsoid(f"Mira_blush{s}", (0.02, 0.003, 0.011), M["blush"], (s * 0.088, -0.111, -0.034), (0, 0, s * 0.62),
                  parent=head, sub=1)
    ellipsoid("Mira_nose", (0.0095, 0.007, 0.008), M["skin_dark"], (0, -0.142, -0.024), parent=head, sub=1)
    ellipsoid("Mira_mouth", (0.012, 0.004, 0.0032), M["mouth"], (0, -0.1285, -0.06), parent=head, sub=2)

    # glasses (rounded-square, tortoiseshell)
    for s in (-1, 1):
        mk(f"Mira_lens{s}", bm_tube(superellipse_xz(0.05, 0.042, 3.2, 36), 0.0055, 8, True, (0, 1, 0)),
           M["frames"], (s * 0.06, -0.156, 0.0), (0, 0, s * 0.3), head)
        mk(f"Mira_temple{s}", bm_tube([(s * 0.106, -0.142, 0.01), (s * 0.142, -0.095, 0.012), (s * 0.152, -0.02, 0.016)],
                                      0.0045, 6), M["frames"], parent=head)
    mk("Mira_bridge", bm_tube([(-0.012, -0.16, 0.012), (0, -0.164, 0.018), (0.012, -0.16, 0.012)], 0.0045, 6),
       M["frames"], parent=head)

    # hair: bob cap + bangs + side locks + bun with pencil
    cap = bm_ico(0.158, 3)
    scale_bm(cap, (1.05, 1.02, 1.0))
    kill = [v for v in cap.verts if not (v.co.z > 0.05 or (v.co.y > -0.075 and v.co.z > -0.10))]
    bmesh.ops.delete(cap, geom=kill, context="VERTS")
    for v in cap.verts:
        f = 1 + 0.32 * min(max((0.04 - v.co.z) / 0.14, 0), 1)
        v.co.x *= f
        v.co.y *= f if v.co.y > 0 else 1.0
    jitter(cap, 0.006, 30, 4)
    mk("Mira_haircap", cap, M["hair"], (0, 0.008, 0.012), parent=head)
    for i in range(6):
        x = -0.105 + i * 0.042
        ysurf = -0.1425 * sqrt(max(1 - (x / 0.15) ** 2 - (0.095 / 0.1395) ** 2, 0.02))
        ellipsoid(f"Mira_bang{i}", (0.031, 0.022, 0.056 - 0.008 * abs(x) / 0.1), M["hair"],
                  (x, ysurf - 0.004, 0.1 - 0.012 * abs(x) / 0.1), (-0.5, 0.15 * (i % 2 - 0.5), asin(x / 0.15)),
                  parent=head, sub=2, jit=0.003, seed=20 + i)
    for s in (-1, 1):
        ellipsoid(f"Mira_lock{s}", (0.03, 0.036, 0.088), M["hair"], (s * 0.13, -0.058, -0.04), (0.1, 0, s * 0.35),
                  parent=head, sub=2, jit=0.004, seed=30 + s)
    bun = ellipsoid("Mira_bun", (0.064, 0.06, 0.058), M["hair"], (0, 0.06, 0.178), parent=head, sub=2, jit=0.006, seed=40)
    bn = Vector((0, 0.35, 0.94))
    mk("Mira_scrunchie", bm_tube(ring_pts((0, 0.045, 0.138), 0.045, bn, 20), 0.012, 7, True, bn), M["scrunchie"], parent=head)
    pencil = empty("Mira_pencil", (0.0, 0.07, 0.185), head)
    pencil.rotation_euler = (0.5, 1.15, 0.25)
    mk("Mira_pencil_body", bm_cyl(0.0065, 0.15, 6), M["pencil"], parent=pencil)
    mk("Mira_pencil_wood", bm_cyl(0.0065, 0.022, 6, 0.0012), M["wood_light"], (0, 0, 0.086), parent=pencil)
    mk("Mira_pencil_ferrule", bm_cyl(0.0068, 0.012, 8), M["metal"], (0, 0, -0.081), parent=pencil)
    mk("Mira_pencil_eraser", bm_cyl(0.0064, 0.012, 8), M["eraser"], (0, 0, -0.093), parent=pencil)

    return dict(root=root, body=body, head=head, torso=torso, eyes=eyes,
                eye_l=bpy.data.objects["Mira_eye-1"], eye_r=bpy.data.objects["Mira_eye1"],
                mouth=bpy.data.objects["Mira_mouth"], brows=[bpy.data.objects["Mira_brow-1"], bpy.data.objects["Mira_brow1"]])


CLEO_Y = 0.64  # Cleo sits behind the desk, facing the camera (-Y)


def build_chair(M, y):
    """Drafting chair: padded seat and back, gas column, five-star base on casters, foot ring under her heels."""
    mk("Chair_seat", bm_box(0.44, 0.42, 0.06, 0.025, 3), M["chair"], (0, y, 0.52))
    mk("Chair_back", bm_box(0.42, 0.045, 0.32, 0.02, 3), M["chair"], (0, y + 0.2, 0.86), (-0.12, 0, 0))
    mk("Chair_post", bm_box(0.05, 0.03, 0.3, 0.008, 2), M["chair"], (0, y + 0.215, 0.64))
    mk("Chair_column", bm_cyl(0.024, 0.38, 12), M["metal"], (0, y, 0.3))
    for i in range(5):
        a = 2 * pi * i / 5 + pi / 2
        end = Vector((0.27 * cos(a), y + 0.27 * sin(a), 0.055))
        mk(f"Chair_spoke{i}", bm_tube([(0, y, 0.11), end + Vector((0, 0, 0.01))], 0.016, 8), M["chair"])
        ellipsoid(f"Chair_caster{i}", (0.022, 0.022, 0.022), M["chair"], end - Vector((0, 0, 0.032)), sub=2)
    mk("Chair_ring", bm_tube(ring_pts((0, y, 0.2), 0.24, (0, 0, 1), 32), 0.009, 8, True, (0, 0, 1)), M["metal"])
    for i in range(3):
        a = 2 * pi * i / 3 + pi / 2
        mk(f"Chair_ringarm{i}", bm_tube([(0, y, 0.2), (0.24 * cos(a), y + 0.24 * sin(a), 0.2)], 0.007, 6), M["metal"])


def build_cleo(M):
    cfg = dict(next(c for c in VARIANTS if c["name"] == "V3_Cleo"), pose="sit")
    g = build_girl(cfg, (0, CLEO_Y, 0), seed=cfg.get("seed", 3))
    n = cfg["name"]
    mug = empty(f"{n}_mug", (0, -0.29, 0.789), g["body"])  # a small cup on the desk, held snug between her hands
    mk(f"{n}_mug_body", bm_cyl(0.03, 0.058, 10), M["mug"], parent=mug)
    mk(f"{n}_mug_band", bm_cyl(0.0306, 0.013, 10), M["claude"], (0, 0, 0.011), parent=mug)
    mk(f"{n}_coffee", bm_cyl(0.026, 0.003, 10), M["coffee"], (0, 0, 0.0235), parent=mug)
    build_chair(M, CLEO_Y)
    return dict(root=g["root"], body=g["body"], head=g["head"], torso=None, eyes=g["eyes"],
                eye_l=g["eye"][0], eye_r=g["eye"][1], mouth=g["mouth"], brows=g["brows"])


def build_claude(M, loc):
    root = empty("Claude", loc)
    body = mk("Claude_body", bm_spark(0.058), M["claude"], (0, 0, 0.074), parent=root)
    for s in (-1, 1):
        ellipsoid(f"Claude_foot{s}", (0.017, 0.019, 0.012), M["claude_dark"], (s * 0.022, -0.004, 0.012), parent=root, sub=1)
    eyes = []
    for s in (-1, 1):
        e = ellipsoid(f"Claude_eye{s}", (0.0058, 0.006, 0.0135), M["eye"], (s * 0.016, -0.036, 0.006), parent=body, sub=2)
        ellipsoid(f"Claude_glint{s}", (0.0021, 0.0015, 0.0026), M["glint"], (0.0016, -0.0052, 0.006), parent=e, sub=1)
        eyes.append(e)
    return dict(root=root, body=body, eyes=eyes)


def build_codex(M, loc):
    root = empty("Codex", loc)
    spheres = [(0.0, 0.0, 0.045), (-0.042, -0.012, 0.03), (0.045, -0.008, 0.032), (0.014, 0.032, 0.033), (-0.022, 0.024, 0.028)]
    body = mk("Codex_body", bm_cloud(spheres, flat_z=-0.03), M["codex"], (0, 0, 0.049), parent=root)
    for s in (-1, 1):
        ellipsoid(f"Codex_foot{s}", (0.016, 0.018, 0.011), M["codex_feet"], (s * 0.026, 0.0, 0.011), parent=root, sub=1)
    face = empty("Codex_face", (0.002, -0.033, 0.002), body)
    L, T, D = 0.017, 0.0048, 0.009
    a = math.radians(38)
    tip = Vector((0.0, 0, 0.002))
    mk("Codex_chev_a", bm_box(L, D, T, 0.0012, 1), M["glyph"], tip + Vector((-cos(a) * L / 2, 0, sin(a) * L / 2)), (0, a, 0), face)
    mk("Codex_chev_b", bm_box(L, D, T, 0.0012, 1), M["glyph"], tip + Vector((-cos(a) * L / 2, 0, -sin(a) * L / 2)), (0, -a, 0), face)
    cursor = mk("Codex_cursor", bm_box(0.016, D, T, 0.0012, 1), M["glyph"], (0.016, 0, -0.011), parent=face)
    return dict(root=root, body=body, cursor=cursor, face=face)


# --------------------------------------------------------------------------- set

def build_set(M):
    rnd = random.Random(SEED)
    # floor, desk, chair
    mk("Floor", bm_box(8, 8, 0.02), M["floor"], (0, 1, -0.01))
    mk("Desk_top", bm_box(1.7, 0.7, 0.04, 0.008), M["desk"], (0, 0.15, 0.74))
    for sx in (-0.8, 0.8):
        for sy in (-0.15, 0.45):
            mk("Desk_leg", bm_box(0.045, 0.045, 0.72), M["desk_dark"], (sx, sy, 0.36))

    # back wall with window
    wy = 1.25
    for name, c, s in [("Wall_L", (-1.975, wy, 1.6), (2.05, 0.1, 3.2)), ("Wall_R", (1.975, wy, 1.6), (2.05, 0.1, 3.2)),
                       ("Wall_B", (0, wy, 0.475), (1.9, 0.1, 0.95)), ("Wall_T", (0, wy, 2.75), (1.9, 0.1, 0.9))]:
        mk(name, bm_box(*s), M["wall"], c)
    fr = 0.05
    for name, c, s in [("Frame_L", (-0.95 + fr / 2, wy - 0.02, 1.625), (fr, 0.08, 1.35)),
                       ("Frame_R", (0.95 - fr / 2, wy - 0.02, 1.625), (fr, 0.08, 1.35)),
                       ("Frame_T", (0, wy - 0.02, 2.3 - fr / 2), (1.9, 0.08, fr)),
                       ("Mullion_V", (0, wy - 0.01, 1.625), (0.035, 0.05, 1.35)),
                       ("Mullion_H", (0, wy - 0.01, 1.66), (1.9, 0.05, 0.035))]:
        mk(name, bm_box(*s), M["frame"], c)
    mk("Sill", bm_box(2.0, 0.24, 0.045, 0.006), M["sill"], (0, wy - 0.07, 0.95))
    # sill cactus
    mk("Cactus_pot", bm_cyl(0.045, 0.07, 8, 0.036), M["pot"], (0.6, wy - 0.08, 1.008))
    ellipsoid("Cactus", (0.03, 0.03, 0.06), M["plant"], (0.6, wy - 0.08, 1.08), sub=1, jit=0.003)
    ellipsoid("Cactus_arm", (0.016, 0.016, 0.03), M["plant"], (0.628, wy - 0.08, 1.1), (0, 0.5, 0), sub=1)

    # sky + city
    sky = bmesh.new()
    bmesh.ops.create_grid(sky, x_segments=1, y_segments=1, size=1.0)
    bmesh.ops.rotate(sky, verts=sky.verts, cent=(0, 0, 0), matrix=Euler((pi / 2, 0, 0)).to_matrix())
    scale_bm(sky, (24, 1, 9))
    mk("Sky", sky, M["sky"], (0, 18, 3.5))
    win_warm, win_cool = bmesh.new(), bmesh.new()
    for layer, (y0, y1, mat_key, count) in enumerate([(4.0, 7.5, "city_near", 26), (10.0, 14.0, "city_far", 30)]):
        for i in range(count):
            w, d, h = rnd.uniform(0.7, 1.8), rnd.uniform(0.7, 1.4), rnd.uniform(-1.0, 3.6) - layer * 0.4
            x, y = rnd.uniform(-7.5, 7.5) * (1 + layer), rnd.uniform(y0, y1)
            mk(f"Bldg{layer}_{i}", bm_box(w, d, h + 20), M[mat_key], (x, y, (h - 20) / 2))
            if layer == 0:
                for gx in range(int(w / 0.32)):
                    for gz in range(int((h + 1.5) / 0.42)):
                        if rnd.random() < 0.28:
                            tgt = win_warm if rnd.random() < 0.8 else win_cool
                            q = bm_box(0.13, 0.01, 0.17)
                            bmesh.ops.translate(q, vec=(x - w / 2 + 0.2 + gx * 0.32, y - d / 2 - 0.01, h - 0.3 - gz * 0.42), verts=q.verts)
                            me = bpy.data.meshes.new("tmp")
                            q.to_mesh(me)
                            q.free()
                            tgt.from_mesh(me)
                            bpy.data.meshes.remove(me)
    mk("City_windows_warm", win_warm, M["win_warm"])
    mk("City_windows_cool", win_cool, M["win_cool"])

    # fairy lights across the window top
    pts = [(-1.0 + 2.0 * i / 40, wy - 0.09, 2.27 - 0.16 * sin(pi * i / 40)) for i in range(41)]
    mk("Fairy_wire", bm_tube(pts, 0.002, 4), M["wire"])
    for i in range(1, 16):
        u = i / 16
        p = (-1.0 + 2.0 * u, wy - 0.095, 2.27 - 0.16 * sin(pi * u) - 0.018)
        ellipsoid(f"Fairy_{i}", (0.011, 0.011, 0.014), M["fairy"], p, sub=1)

    # monitor (faces camera-left), code on screen
    mon = empty("Monitor", (0.56, 0.32, 0.76))
    mon.rotation_euler = (0, 0, -0.42)
    mk("Mon_base", bm_box(0.2, 0.14, 0.012, 0.004), M["mon"], (0, 0.02, 0.006), parent=mon)
    mk("Mon_neck", bm_box(0.04, 0.025, 0.2, 0.006), M["mon"], (0, 0.05, 0.11), parent=mon)
    mk("Mon_bezel", bm_box(0.52, 0.028, 0.32, 0.01), M["mon"], (0, 0.03, 0.27), parent=mon)
    mk("Mon_screen", bm_box(0.49, 0.002, 0.29), M["screen"], (0, 0.015, 0.27), parent=mon)
    code = bmesh.new()
    colors = {}
    yv, indent = 0.39, 0
    for row in range(17):
        indent = max(0, min(3, indent + rnd.choice([-1, 0, 0, 1])))
        x = -0.225 + indent * 0.02
        for _ in range(rnd.randint(1, 3)):
            ln = rnd.uniform(0.025, 0.11)
            if x + ln > 0.22:
                break
            q = bm_box(ln, 0.002, 0.008)
            bmesh.ops.translate(q, vec=(x + ln / 2, 0.012, yv), verts=q.verts)
            key = rnd.choice(["code_blue", "code_green", "code_orange", "code_purple", "code_white"])
            colors.setdefault(key, bmesh.new())
            me = bpy.data.meshes.new("tmp")
            q.to_mesh(me)
            q.free()
            colors[key].from_mesh(me)
            bpy.data.meshes.remove(me)
            x += ln + 0.012
        yv -= 0.016
    for key, b in colors.items():
        mk(f"Code_{key}", b, M[key], parent=mon)
    mk("Mon_note", bm_box(0.05, 0.003, 0.05), M["note_yellow"], (0.235, 0.014, 0.4), (0, 0.18, 0), mon)

    # keyboard
    kb = empty("Keyboard", (0.02, 0.2, 0.76))
    kb.rotation_euler = (0, 0, 0.06)
    mk("KB_base", bm_box(0.36, 0.12, 0.016, 0.005), M["kb"], (0, 0, 0.008), parent=kb)
    keys = bmesh.new()
    for r in range(4):
        for c in range(13):
            q = bm_box(0.022, 0.022, 0.008, 0.002, 1)
            bmesh.ops.translate(q, vec=(-0.162 + c * 0.027, -0.04 + r * 0.027, 0.019), verts=q.verts)
            me = bpy.data.meshes.new("tmp")
            q.to_mesh(me)
            q.free()
            keys.from_mesh(me)
            bpy.data.meshes.remove(me)
    mk("KB_keys", keys, M["keys"], parent=kb)

    # desk lamp (back left)
    lamp = empty("Lamp", (-0.62, 0.34, 0.76))
    mk("Lamp_base", bm_cyl(0.07, 0.02, 14), M["lamp"], (0, 0, 0.01), parent=lamp)
    mk("Lamp_arm", bm_tube([(0, 0, 0.02), (0.02, -0.02, 0.32), (0.13, -0.12, 0.42)], 0.008, 6), M["lamp"], parent=lamp)
    shade = empty("Lamp_head", (0.15, -0.14, 0.4), lamp)
    shade.rotation_euler = (0.55, -0.45, 0)
    mk("Lamp_shade", bm_cyl(0.035, 0.11, 14, 0.085), M["lamp"], (0, 0, -0.02), (pi, 0, 0), shade)
    ellipsoid("Lamp_bulb", (0.025, 0.025, 0.025), M["bulb"], (0, 0, -0.06), parent=shade, sub=2)

    # books + plant + sticky notes
    for i, (h, col, rz) in enumerate([(0.03, "book_blue", 0.1), (0.025, "book_mustard", -0.12), (0.022, "book_red", 0.05)]):
        mk(f"Book{i}", bm_box(0.22, 0.16, h, 0.003), M[col], (-0.56, -0.03, 0.76 + 0.03 * i + h / 2), (0, 0, rz))
    mk("Plant_pot", bm_cyl(0.05, 0.085, 10, 0.04), M["pot"], (-0.36, 0.44, 0.8025))
    for i in range(8):
        a = 2 * pi * i / 8 + 0.3
        ellipsoid(f"Leaf{i}", (0.018, 0.008, 0.07 + 0.02 * (i % 3)), M["plant"],
                  (-0.36 + 0.025 * cos(a), 0.44 + 0.025 * sin(a), 0.89), (0.55 * sin(a), -0.55 * cos(a), 0), sub=1)
    mk("Note_a", bm_box(0.07, 0.07, 0.003), M["note_yellow"], (0.42, -0.07, 0.7615), (0, 0, 0.25))
    mk("Note_b", bm_box(0.07, 0.07, 0.003), M["note_pink"], (0.47, -0.02, 0.7645), (0, 0, -0.18))


def build_lights():
    def area(name, loc, target, hexcol, energy, size, size_y=None):
        ld = bpy.data.lights.new(name, "AREA")
        ld.color = lin(hexcol)
        ld.energy = energy
        if size_y:
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = size, size_y
        else:
            ld.shape = "DISK"
            ld.size = size
        ld.use_shadow_jitter = True
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc
        aim(ob, target)
        return ob

    area("Key_warm", (-0.75, -0.45, 1.6), (0, 0.6, 1.1), "#ffc49a", 42, 0.6)
    area("Rim_window", (0.35, 1.12, 1.75), (0, 0.66, 1.05), "#d59cff", 70, 1.0)
    area("Rim_window_L", (-0.45, 1.12, 1.55), (-0.1, 0.6, 1.0), "#ff9fb7", 30, 0.8)
    area("Monitor_glow", (0.45, 0.22, 1.03), (0.0, 0.6, 1.1), "#8fb2ff", 7, 0.45, 0.28)
    area("Front_fill", (0.0, -0.75, 0.98), (0.0, 0.08, 0.82), "#ffe0c4", 7, 0.7)
    sp = bpy.data.lights.new("Lamp_spot", "SPOT")
    sp.color, sp.energy, sp.spot_size, sp.spot_blend, sp.shadow_soft_size = lin("#ffb26b"), 22, math.radians(85), 0.6, 0.03
    sp.use_shadow_jitter = True
    ob = link(bpy.data.objects.new("Lamp_spot", sp))
    ob.location = (-0.47, 0.2, 1.1)
    aim(ob, (-0.3, 0.05, 0.76))
    pt = bpy.data.lights.new("Fairy_glow", "POINT")
    pt.color, pt.energy, pt.shadow_soft_size = lin("#ffb86b"), 6, 0.4
    ob = link(bpy.data.objects.new("Fairy_glow", pt))
    ob.location = (0, 1.05, 2.15)


def build_world():
    w = bpy.data.worlds.new("Dusk")
    bpy.context.scene.world = w
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*lin("#1f1d33"), 1)
    bg.inputs["Strength"].default_value = 0.7


def materials():
    M = {}
    M["skin"] = mat("Skin", "#e9a882", 0.55)
    M["skin_dark"] = mat("SkinShade", "#d98f6c", 0.6)
    M["blush"] = mat("Blush", "#f2877c", 0.8)
    M["hair"] = mat("Hair", "#2a1b18", 0.42, spec=0.6)
    M["hoodie"] = mat("Hoodie", "#86ad7f", 0.85)
    M["hoodie_dark"] = mat("HoodieCuff", "#6b9168", 0.85)
    M["cream"] = mat("Cream", "#f1e6d2", 0.7)
    M["metal"] = mat("Metal", "#c9c2b8", 0.3, metal=1.0)
    M["eye"] = mat("Eye", "#17110f", 0.15, spec=0.8)
    M["glint"] = emissive("Glint", "#ffffff", 4.0)
    M["mouth"] = mat("Mouth", "#5c2a2a", 0.6)
    M["frames"] = mat("Frames", "#5a2f22", 0.3, coat=0.6)
    M["scrunchie"] = mat("Scrunchie", "#e8735a", 0.8)
    M["pencil"] = mat("Pencil", "#f2c14e", 0.5)
    M["wood_light"] = mat("PencilWood", "#e8c9a0", 0.7)
    M["eraser"] = mat("Eraser", "#f08aa0", 0.8)
    M["mug"] = mat("Mug", "#f3ebe0", 0.35, coat=0.4)
    M["coffee"] = mat("Coffee", "#3b2418", 0.15)
    M["claude"] = mat("Claude", "#d97757", 0.55)
    M["claude_dark"] = mat("ClaudeFeet", "#b85d40", 0.6)
    M["codex"] = gradient_mat("Codex", "Z", -0.035, 0.06,
                              [(0.0, "#2f49e8"), (0.55, "#5b5cf0"), (1.0, "#9a5cf2")], emit_strength=0.12, rough=0.45)
    M["codex_feet"] = mat("CodexFeet", "#1f2a8c", 0.5)
    M["glyph"] = emissive("Glyph", "#eef3ff", 7.0)
    M["floor"] = mat("Floor", "#4a3226", 0.55)
    M["desk"] = mat("Desk", "#6e4a33", 0.45, coat=0.2)
    M["desk_dark"] = mat("DeskLeg", "#3a2a22", 0.6)
    M["chair"] = mat("Chair", "#2c2a38", 0.7)
    M["wall"] = mat("Wall", "#8b7a7c", 0.9)
    M["frame"] = mat("WinFrame", "#26232e", 0.6)
    M["sill"] = mat("Sill", "#d9cfc4", 0.6)
    M["sky"] = gradient_mat("Sky", "Z", 0.0, 1.0,
                            [(0.0, "#ffab7a"), (0.3, "#f07a8e"), (0.58, "#a35aa8"), (1.0, "#262350")],
                            emit_strength=1.6, coords="Generated", pure_emission=True)
    M["city_near"] = mat("CityNear", "#17162a", 0.9)
    M["city_far"] = mat("CityFar", "#4a3566", 0.9, emit="#5a3f78", strength=0.35)
    M["win_warm"] = emissive("WinWarm", "#ffcf8a", 9.0)
    M["win_cool"] = emissive("WinCool", "#9fd2ff", 7.0)
    M["wire"] = mat("Wire", "#2a2a2a", 0.6)
    M["fairy"] = emissive("Fairy", "#ffbd6e", 22.0)
    M["mon"] = mat("Monitor", "#22242e", 0.4)
    M["screen"] = emissive("Screen", "#141a33", 1.0)
    for k, c in [("code_blue", "#7aa2ff"), ("code_green", "#b6e388"), ("code_orange", "#f7a46c"),
                 ("code_purple", "#c79bf2"), ("code_white", "#dfe4f0")]:
        M[k] = emissive(k, c, 3.0)
    M["kb"] = mat("Keyboard", "#3a3d4f", 0.5)
    M["keys"] = mat("Keys", "#e9e4dc", 0.5)
    M["lamp"] = mat("Lamp", "#2f5d5a", 0.45)
    M["bulb"] = emissive("Bulb", "#fff0d6", 30.0)
    M["book_blue"] = mat("BookBlue", "#3d5a80", 0.7)
    M["book_mustard"] = mat("BookMustard", "#e0b04c", 0.7)
    M["book_red"] = mat("BookRed", "#9a4c4c", 0.7)
    M["pot"] = mat("Pot", "#c0694a", 0.8)
    M["plant"] = mat("Plant", "#4f8a5b", 0.6)
    M["note_yellow"] = mat("NoteYellow", "#f5d76e", 0.8)
    M["note_pink"] = mat("NotePink", "#f59bb0", 0.8)
    return M


# --------------------------------------------------------------------------- animation

def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def keyed(points, f, ease=8):
    """Piecewise-constant targets [(frame, value)...] with smoothstep transitions of `ease` frames."""
    v = points[0][1]
    for fr, val in points[1:]:
        v = v + (val - v) * ss((f - fr) / ease)
    return v


def key(ob, path, f, value):
    setattr(ob, path, value)
    ob.keyframe_insert(path, frame=f)


SHOTS = [
    # name, start, end, cam, target, lens, fstop, focus
    ("S1_wide", 1, 60, (0.08, -1.72, 1.16), (0.0, 0.4, 0.98), 30, 5.6, "V3_Cleo_head"),
    ("S2_cleo", 61, 135, (0.1, -0.85, 1.12), (0.0, 0.64, 1.02), 50, 2.8, "V3_Cleo_eye1"),
    ("S3_claude", 136, 225, (-0.115, -0.27, 0.84), (-0.17, 0.08, 0.872), 60, 1.6, "Claude_body"),
    ("S4_codex", 226, 285, (0.255, -0.26, 0.835), (0.21, 0.06, 0.858), 60, 1.6, "Codex_body"),
    ("S5_cleo_ecu", 286, 360, (-0.05, -0.2, 1.13), (0.0, 0.64, 1.12), 60, 2.8, "V3_Cleo_eye1"),
    ("S6_codex", 361, 420, (0.18, -0.25, 0.85), (0.21, 0.06, 0.855), 65, 1.6, "Codex_body"),
    ("S7_duo", 421, 480, (0.02, -0.42, 0.845), (0.02, 0.07, 0.86), 42, 2.0, "Claude_body"),
]
FRAME_END = SHOTS[-1][2]

LINES = [  # (start, end, speaker, text) -- frames
    (66, 128, "mira", "Okay, team. One tiny bug."),
    (140, 218, "claude", "Love that! A few quick\nquestions first. Which bug?"),
    (230, 280, "codex", "Fixed it."),
    (292, 352, "mira", "...I haven't told you\nwhat it is."),
    (366, 414, "codex", "Then it's a surprise."),
]


def cameras():
    scn = bpy.context.scene
    for name, f0, f1, loc, tgt, lens, fstop, focus in SHOTS:
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.sensor_fit = "AUTO"
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.aperture_blades = 0
        cd.dof.focus_object = bpy.data.objects[focus]
        cd.clip_start = 0.02
        cam = link(bpy.data.objects.new(name, cd))
        loc, tgt = Vector(loc), Vector(tgt)
        fwd = (tgt - loc).normalized()
        push = 0.06 if lens > 40 else 0.18
        for f in range(f0 - 1, f1 + 2, 3):
            u = (f - f0) / max(f1 - f0, 1)
            drift = Vector((noise.noise(Vector((f * 0.02, 1.3, 0))), 0, noise.noise(Vector((f * 0.02, 7.1, 0))))) * 0.0025
            cam.location = loc + fwd * push * ss(u) + drift
            aim(cam, tgt + drift * 0.5)
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_quaternion", frame=f)
        m = scn.timeline_markers.new(name, frame=f0)
        m.camera = cam
    scn.camera = bpy.data.objects[SHOTS[0][0]]


def talk_curve(f, f0, f1, seed):
    if not (f0 <= f <= f1):
        return 0.0
    rnd = random.Random(seed * 1000 + (f - f0) // 4)
    syll = 0.5 + 0.5 * sin(2 * pi * (f - f0) / 4.3)
    env = ss((f - f0) / 3) * ss((f1 - f) / 3)
    return env * syll * (0.55 + 0.45 * rnd.random())


def animate(mira, claude, codex):
    talk = {s: [(a, b) for a, b, sp, _ in LINES if sp == s] for s in ("mira", "claude", "codex")}

    def talking(who, f):
        seed = {"mira": 11, "claude": 23, "codex": 37}[who]
        return max([talk_curve(f, a, b, seed + i) for i, (a, b) in enumerate(talk[who])] + [0.0])

    # where Mira looks: yaw (+ = toward Codex / +X), pitch (+ = down)
    yaw_pts = [(1, 0.0), (61, 0.0), (140, -0.17), (228, 0.17), (290, 0.07), (362, 0.17), (430, 0.0)]
    pitch_pts = [(1, 0.1), (61, 0.14), (140, 0.2), (228, 0.2), (290, 0.12), (362, 0.2), (430, 0.16)]
    brow_pts = [(1, 0.0), (288, 0.006), (356, 0.0), (420, 0.004)]
    mira_blinks = [44, 118, 196, 262, 318, 341, 398, 458]
    claude_blinks = [28, 96, 168, 214, 250, 318, 392, 452]
    brow_base = [b.location.copy() for b in mira["brows"]]
    head_z0 = mira["head"].location.z
    for f in range(1, FRAME_END + 1):
        t = f / FPS
        breath = sin(2 * pi * t / 3.6)
        # Mira
        if f % 2 == 1 or f == FRAME_END:
            if mira["torso"] is not None:
                key(mira["torso"], "scale", f, (1 + 0.006 * breath, 1 + 0.006 * breath, 1 + 0.014 * breath))
            yaw, pitch = keyed(yaw_pts, f, 10), keyed(pitch_pts, f, 10)
            nod = 0.015 * talking("mira", f)
            key(mira["head"], "location", f, (0, 0, head_z0 + 0.003 * breath))
            # long hair hangs from the head: keep the head pitch small and let the eyes do the looking down
            key(mira["head"], "rotation_euler", f, (0.2 * pitch + nod, 0.025 * sin(t * 0.9), yaw))
            key(mira["eyes"], "location", f, (yaw * 0.03, 0, -pitch * 0.02))
            for b, b0 in zip(mira["brows"], brow_base):
                key(b, "location", f, (b0.x, b0.y, b0.z + keyed(brow_pts, f, 6)))
        m = talking("mira", f)
        key(mira["mouth"], "scale", f, (1 - 0.25 * m, 1, 1 + 2.6 * m))
        bl = max([1 - abs(f - b) / 2.5 for b in mira_blinks] + [0])
        for e in (mira["eye_l"], mira["eye_r"]):
            key(e, "scale", f, (1, 1, 1 - 0.9 * ss(bl * 1.6)))

        # Claude
        c = talking("claude", f)
        hop = abs(sin(2 * pi * t * 2.3)) * 0.007 * c
        turn = keyed([(1, 0.0), (228, 0.25), (286, 0.0), (362, 0.28), (420, 0.0), (436, 0.55)], f, 9)
        key(claude["root"], "rotation_euler", f, (0, 0, turn))
        key(claude["body"], "location", f, (0, 0, 0.074 + 0.0025 * sin(2 * pi * t / 1.7) + hop))
        key(claude["body"], "rotation_euler", f, (0, 0.07 * sin(2 * pi * t * 1.15) * c, 0))
        sq = 0.018 * sin(2 * pi * t / 1.7) + 0.05 * c * sin(2 * pi * t * 4.6)
        key(claude["body"], "scale", f, (1 - sq * 0.5, 1, 1 + sq))
        cb = max([1 - abs(f - b) / 2.5 for b in claude_blinks] + [0])
        if 446 <= f <= 462:  # slow deadpan blink at the end
            cb = max(cb, 1 - abs(f - 454) / 8)
        for e in claude["eyes"]:
            key(e, "scale", f, (1, 1, 1 - 0.85 * ss(cb * 1.6)))

        # Codex
        x = talking("codex", f)
        any_line = any(a <= f <= b for a, b in talk["codex"])
        key(codex["body"], "location", f, (0, 0, 0.049 + 0.0022 * sin(2 * pi * t / 1.9 + 1.3) + 0.004 * x))
        key(codex["body"], "scale", f, (1 + 0.012 * x, 1, 1 + 0.025 * sin(2 * pi * t / 1.9 + 1.3) * 0.4 + 0.03 * x))
        period = 8 if any_line else 30
        on = 1.0 if (f // (period // 2)) % 2 == 0 else 0.0
        key(codex["cursor"], "scale", f, (on, 1, 1))
        ctn = keyed([(1, 0.0), (140, -0.22), (226, 0.0), (436, -0.3)], f, 9)
        key(codex["root"], "rotation_euler", f, (0, 0, ctn))

    # constant interpolation for the cursor blink
    ad = codex["cursor"].animation_data
    if ad and ad.action:
        try:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
        except AttributeError:
            for layer in ad.action.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = "CONSTANT"


# --------------------------------------------------------------------------- main

def render_settings(scn):
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_x, scn.render.resolution_y = 1080, 1920
    ee = scn.eevee
    ee.taa_render_samples = 64
    ee.use_raytracing = True
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 8
    ee.use_bokeh_jittered = True
    ee.bokeh_max_size = 200
    ee.use_fast_gi = True
    scn.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scn.view_settings.look = look
            break
        except TypeError:
            pass
    scn.render.film_transparent = False


def main():
    out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/ctv2_scene.blend"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = FPS
    scn.frame_start, scn.frame_end = 1, FRAME_END
    M = materials()
    build_world()
    build_set(M)
    mira = build_cleo(M)
    claude = build_claude(M, (-0.17, 0.08, 0.76))
    codex = build_codex(M, (0.21, 0.06, 0.76))
    build_lights()
    cameras()
    animate(mira, claude, codex)

    render_settings(scn)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


if __name__ == "__main__":
    main()
