"""Shared helpers: mesh primitives (bmesh), materials, ribbons, colliders."""
import bpy, bmesh, math
from math import sin, cos, pi, sqrt
from mathutils import Vector, noise


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ----------------------------------------------------------------- objects

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


def aim(ob, target):
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (Vector(target) - ob.location).to_track_quat("-Z", "Y")


# ----------------------------------------------------------------- bmesh primitives

def bm_ico(r=1.0, sub=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    return bm


def bm_box(sx, sy, sz, bevel=0.0, seg=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=seg, affect="EDGES", profile=0.5)
    return bm


def bm_cyl(r, depth, seg=12, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=depth)
    return bm


def scale_bm(bm, s):
    bmesh.ops.scale(bm, vec=s, verts=bm.verts)


def jitter(bm, amp, freq=40.0, seed=0.0):
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


def limb(name, p0, p1, r, mat, parent=None, sub=2, jit=0.0, seed=0.0, r_end=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bm_ico(1.0, sub)
    scale_bm(bm, (r, r, d.length / 2 + r * 0.55))
    if r_end:  # taper toward p1
        for v in bm.verts:
            f = 1 + (r_end / r - 1) * (v.co.z / (d.length / 2 + r * 0.55) * 0.5 + 0.5)
            v.co.x *= f
            v.co.y *= f
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
        t = (pts[(i + 1) % n] - pts[i - 1]) if closed else (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        t.normalize()
        ref = Vector(plane_n) if plane_n is not None else (Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)))
        a = t.cross(ref).normalized()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + r * (cos(2 * pi * j / seg) * a + sin(2 * pi * j / seg) * b)) for j in range(seg)])
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


# ----------------------------------------------------------------- curves / hair

def catmull(pts, steps=6):
    pts = [Vector(p) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1].copy())
    return out


def resample(pts, step):
    """Even arc-length resampling."""
    out = [pts[0].copy()]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        while acc + seg >= step and seg > 1e-9:
            t = (step - acc) / seg
            a = a.lerp(b, t)
            out.append(a.copy())
            seg = (b - a).length
            acc = 0.0
        acc += seg
    if (out[-1] - pts[-1]).length > step * 0.3:
        out.append(pts[-1].copy())
    return out


def collide(pts, colliders, clearance=0.006, start=0):
    for p in pts[start:]:
        for c, r in colliders:
            q = p - c
            k = sqrt((q.x / (r[0] + clearance)) ** 2 + (q.y / (r[1] + clearance)) ** 2 + (q.z / (r[2] + clearance)) ** 2)
            if 1e-6 < k < 1.0:
                p[:] = c + q / k


def smooth(pts, iters=2, start=1):
    for _ in range(iters):
        new = [p.copy() for p in pts]
        for i in range(max(start, 1), len(pts) - 1):
            new[i] = pts[i] * 0.5 + (pts[i - 1] + pts[i + 1]) * 0.25
        pts[:] = new


def bm_ribbon(pts, width, thick, seg=6, root=0.5, tip=0.18, tip_start=0.68, axis_z=0.0, center=None):
    """Flat faceted hair strand along pts. Width lies tangent to the head, thickness along the outward normal."""
    bm = bmesh.new()
    n = len(pts)
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    total = max(L[-1], 1e-6)
    rings = []
    for i, p in enumerate(pts):
        s = L[i] / total
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        N = p - (Vector(center) if center is not None else Vector((0, 0, min(p.z, axis_z))))
        N = (N - T * N.dot(T))
        if N.length < 1e-6:
            N = T.orthogonal()
        N.normalize()
        B = T.cross(N).normalized()
        wf = root + (1 - root) * ss(s / 0.18)
        wf *= 1 - (1 - tip) * ss((s - tip_start) / (1 - tip_start))
        w, t = width * wf, thick * (0.6 + 0.4 * wf)
        rings.append([bm.verts.new(p + B * (w / 2) * cos(2 * pi * j / seg) + N * (t / 2) * sin(2 * pi * j / seg))
                      for j in range(seg)])
    for i in range(n - 1):
        r0, r1 = rings[i], rings[i + 1]
        for j in range(seg):
            bm.faces.new((r0[j], r1[j], r1[(j + 1) % seg], r0[(j + 1) % seg]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def merge_into(dst, src):
    me = bpy.data.meshes.new("tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


# ----------------------------------------------------------------- materials

def mat(name, hexcol, rough=0.6, metal=0.0, emit=None, strength=0.0, spec=0.5, coat=0.0, rib=0.0, rib_scale=90.0, sheen=0.0, grain=0.0, nubs=0.0, nub_scale=380.0):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(hexcol), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.25
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(emit), 1)
        b.inputs["Emission Strength"].default_value = strength
    if rib:  # knit / quilting ribs via bump
        tc = nt.nodes.new("ShaderNodeTexCoord")
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = rib_scale
        wave.inputs["Distortion"].default_value = 1.5
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = rib
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if nubs:  # small rounded knit nubs (voronoi domes), chained after any rib bump
        tc = nt.nodes.new("ShaderNodeTexCoord")
        vo = nt.nodes.new("ShaderNodeTexVoronoi")
        vo.inputs["Scale"].default_value = nub_scale
        dome, rnd = nt.nodes.new("ShaderNodeMath"), nt.nodes.new("ShaderNodeMath")
        dome.operation, rnd.operation = "SUBTRACT", "POWER"
        dome.inputs[0].default_value, rnd.inputs[1].default_value = 1.0, 0.6
        nb = nt.nodes.new("ShaderNodeBump")
        nb.inputs["Strength"].default_value = nubs
        nb.inputs["Distance"].default_value = 0.0006
        nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
        nt.links.new(vo.outputs["Distance"], dome.inputs[1])
        nt.links.new(dome.outputs[0], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], nb.inputs["Height"])
        if b.inputs["Normal"].links:
            nt.links.new(b.inputs["Normal"].links[0].from_socket, nb.inputs["Normal"])
        nt.links.new(nb.outputs["Normal"], b.inputs["Normal"])
    if grain:  # fine fabric / skin micro-texture, chained after any rib bump
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 420.0
        nz.inputs["Detail"].default_value = 4.0
        g = nt.nodes.new("ShaderNodeBump")
        g.inputs["Strength"].default_value = grain
        g.inputs["Distance"].default_value = 0.0004
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], g.inputs["Height"])
        if b.inputs["Normal"].links:
            nt.links.new(b.inputs["Normal"].links[0].from_socket, g.inputs["Normal"])
        nt.links.new(g.outputs["Normal"], b.inputs["Normal"])
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


def eevee_defaults(scn, samples=64):
    scn.render.engine = "BLENDER_EEVEE"
    ee = scn.eevee
    ee.taa_render_samples = samples
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
