"""How a block of ice becomes a refrigerator: procedural kitchen cutaway + Poly Haven CC0 props, keyed to audio/lines.json + words.json.
blender -b --factory-startup -P fr.py -- <outdir> [--res 1080] [--samples 16] [--range a,b] [--stills t,t,...] [--skip] [--save x.blend]"""
import bpy, bmesh, json, math, os, random, re, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["out"]
OUTDIR = os.path.abspath(argv[0])
opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
RES, SAMPLES = int(opt("--res", 1080)), int(opt("--samples", 16))
FPS = 30
random.seed(7)

LINES = json.load(open(os.path.join(HERE, "audio/lines.json")))
WORDS = json.load(open(os.path.join(HERE, "audio/words.json")))
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())


def T(li, word=None, k=0):
    """start time (s) of line li (1-based) or of the k-th word in it starting with `word`"""
    if word is None:
        return LINES[li - 1]["start"]
    ws = [w for w in WORDS if w[3] == li and norm(w[0]).startswith(word)]
    return ws[min(k, len(ws) - 1)][1]


F = lambda t: int(round(t * FPS)) + 1
END = LINES[-1]["end"] + 1.1
NF = F(END)

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, NF
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"


def link(o):
    sc.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- materials
def tex_img(nt, path, cs="sRGB"):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = cs
    n.projection, n.projection_blend = "BOX", 0.25
    return n


def mat(name, col=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emit=None, es=0.0, alpha=1.0, trans=0.0, ior=1.45, tex=None, tscale=1.0, tint=None, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Alpha"].default_value = alpha
    b.inputs["Transmission Weight"].default_value = trans
    b.inputs["IOR"].default_value = ior
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = es
    if tex:
        d = os.path.join(A, "tex", tex)
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (tscale,) * 3
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        di = tex_img(nt, os.path.join(d, "Diffuse.jpg"))
        nt.links.new(mp.outputs[0], di.inputs[0])
        if tint:
            mx = nt.nodes.new("ShaderNodeMix")
            mx.data_type, mx.blend_type = "RGBA", "MULTIPLY"
            mx.inputs["Factor"].default_value = 1
            nt.links.new(di.outputs[0], mx.inputs[6])
            mx.inputs[7].default_value = (*tint, 1)
            nt.links.new(mx.outputs[2], b.inputs["Base Color"])
        else:
            nt.links.new(di.outputs[0], b.inputs["Base Color"])
        ro = tex_img(nt, os.path.join(d, "Rough.jpg"), "Non-Color")
        nt.links.new(mp.outputs[0], ro.inputs[0])
        nt.links.new(ro.outputs[0], b.inputs["Roughness"])
        no = tex_img(nt, os.path.join(d, "nor_gl.jpg"), "Non-Color")
        nt.links.new(mp.outputs[0], no.inputs[0])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.6
        nt.links.new(no.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return m


M = dict(
    white=mat("white", (0.48, 0.7, 0.85), 0.25, coat=0.5),
    foam=mat("foam", (0.95, 0.82, 0.45), 0.9),
    liner=mat("liner", (0.84, 0.86, 0.88), 0.35),
    wood=mat("wood", tex="oak_wood_planks", tscale=1.2),
    tin=mat("tin", (0.78, 0.8, 0.82), 0.3, 1.0),
    ice=mat("ice", (0.8, 0.93, 1.0), 0.06, trans=1.0, ior=1.31),
    water=mat("water", (0.75, 0.9, 1.0), 0.02, trans=1.0, ior=1.33),
    copper=mat("copper", (0.95, 0.55, 0.36), 0.3, 1.0),
    black=mat("black", (0.03, 0.03, 0.035), 0.35, coat=0.6),
    rubber=mat("rubber", (0.02, 0.02, 0.02), 0.7),
    glass=mat("glass", (0.85, 0.97, 0.95), 0.03, trans=1.0),
    floor=mat("floor", tex="laminate_floor_02", tscale=0.5),
    wall=mat("wall", tex="white_plaster_02", tscale=0.6, tint=(0.98, 0.88, 0.74)),
    tiles=mat("tiles", tex="long_white_tiles", tscale=1.0),
    cab=mat("cab", tex="kitchen_wood", tscale=1.0),
    grass=mat("grass", tex="grass_ground", tscale=0.4),
    top=mat("top", (0.12, 0.12, 0.13), 0.3),
    frame=mat("frame", (0.97, 0.97, 0.97), 0.4),
    knob=mat("knob", (0.95, 0.95, 0.95), 0.3),
    heat=mat("heat", (1, 0.35, 0.05), 0.5, emit=(1, 0.3, 0.02), es=3.5),
    cold=mat("cold", (0.6, 0.85, 1), 0.3, emit=(0.45, 0.8, 1), es=1.2, alpha=0.45),
    steam=mat("steam", (1, 1, 1), 0.5, emit=(1, 1, 1), es=0.6, alpha=0.35),
    crystal=mat("crystal", (0.95, 0.98, 1), 0.2, emit=(0.85, 0.95, 1), es=1.5),
    bulb=mat("bulb", (1, 0.95, 0.8), 0.3, emit=(1, 0.9, 0.7), es=0),
    blue=mat("blue", (0.3, 0.65, 1), 0.3, emit=(0.25, 0.6, 1), es=4),
)
M["water"].node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.8

# shared flow driver: time + power (power keyed so the thermostat can idle every pipe at once)
FG = bpy.data.node_groups.new("Flow", "ShaderNodeTree")
FG.interface.new_socket("time", in_out="OUTPUT", socket_type="NodeSocketFloat")
FG.interface.new_socket("power", in_out="OUTPUT", socket_type="NodeSocketFloat")
go = FG.nodes.new("NodeGroupOutput")
tv = FG.nodes.new("ShaderNodeValue"); tv.name = "time"
pv = FG.nodes.new("ShaderNodeValue"); pv.name = "power"
FG.links.new(tv.outputs[0], go.inputs[0]); FG.links.new(pv.outputs[0], go.inputs[1])
d = tv.outputs[0].driver_add("default_value").driver
d.type, d.expression = "SCRIPTED", "frame/30"


def key_power(t, v):
    pv.outputs[0].default_value = v
    pv.outputs[0].keyframe_insert("default_value", frame=F(t))


key_power(0, 1)


def pipe_mat(name, length, c1, c2=None, base="copper", speed=0.35, spacing=0.07, duty=0.45):
    """copper pipe with glowing dashes flowing along U (arc length, m) and a keyed 'reveal' length"""
    m = M[base].copy(); m.name = name
    nt = m.node_tree
    out = nt.nodes["Material Output"]
    bs = nt.nodes["Principled BSDF"]
    uv = nt.nodes.new("ShaderNodeUVMap")
    sx = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(uv.outputs[0], sx.inputs[0])
    g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = FG

    def op(o, a, b=None):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = o
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    ph = op("FRACT", op("DIVIDE", op("SUBTRACT", sx.outputs[0], op("MULTIPLY", g.outputs[0], speed)), spacing))
    dash = op("MULTIPLY", op("LESS_THAN", ph, duty), g.outputs[1])
    col = nt.nodes.new("ShaderNodeMix"); col.data_type = "RGBA"
    nt.links.new(op("DIVIDE", sx.outputs[0], length), col.inputs["Factor"])
    col.inputs[6].default_value = (*c1, 1); col.inputs[7].default_value = (*(c2 or c1), 1)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 2.6
    nt.links.new(col.outputs[2], em.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(dash, mix.inputs[0]); nt.links.new(bs.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    rv = nt.nodes.new("ShaderNodeValue"); rv.name = "reveal"; rv.outputs[0].default_value = 0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    hide = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(op("GREATER_THAN", sx.outputs[0], rv.outputs[0]), hide.inputs[0])
    nt.links.new(mix.outputs[0], hide.inputs[1]); nt.links.new(tr.outputs[0], hide.inputs[2])
    nt.links.new(hide.outputs[0], out.inputs["Surface"])
    rv.outputs[0].keyframe_insert("default_value", frame=1)
    return m


def reveal(m, t, length, dur=0.9):
    rv = m.node_tree.nodes["reveal"].outputs[0]
    rv.default_value = 0; rv.keyframe_insert("default_value", frame=F(t))
    rv.default_value = length + 0.05; rv.keyframe_insert("default_value", frame=F(t + dur))


def frost_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; out = nt.nodes["Material Output"]; bs = nt.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (0.94, 0.97, 1, 1); bs.inputs["Roughness"].default_value = 0.85
    bs.inputs["Emission Color"].default_value = (0.9, 0.95, 1, 1); bs.inputs["Emission Strength"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 45; nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8
    nt.links.new(nz.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs[0], bs.inputs["Normal"])
    th = nt.nodes.new("ShaderNodeValue"); th.name = "thr"; th.outputs[0].default_value = 1.0
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"
    nt.links.new(nz.outputs[0], gt.inputs[0]); nt.links.new(th.outputs[0], gt.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(gt.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(bs.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    th.outputs[0].keyframe_insert("default_value", frame=1)
    return m


def key_val(sock, t, v):
    sock.default_value = v
    sock.keyframe_insert("default_value", frame=F(t))


# ---------------------------------------------------------------- geometry helpers
def box(name, lo, hi, m, bevel=0.0, parent=None):
    lo, hi = Vector(lo), Vector(hi)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    c = (lo + hi) / 2
    for v in bm.verts:
        v.co = Vector((v.co.x * (hi.x - lo.x), v.co.y * (hi.y - lo.y), v.co.z * (hi.z - lo.z))) + (c if parent is None else c)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.data.materials.append(m)
    if bevel:
        bv = o.modifiers.new("bv", "BEVEL"); bv.width, bv.segments, bv.limit_method = bevel, 2, "ANGLE"
    if parent:
        o.parent = parent
    return o


def centered(o):
    """move origin to the bbox bottom-centre so scale pops grow from the floor"""
    me = o.data
    vs = [v.co for v in me.vertices]
    c = Vector(((min(v.x for v in vs) + max(v.x for v in vs)) / 2, (min(v.y for v in vs) + max(v.y for v in vs)) / 2, min(v.z for v in vs)))
    me.transform(Matrix.Translation(-c))
    o.location = c
    return o


def cyl(name, r, h, m, loc, axis="Z", seg=32, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    if axis == "X": bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    if axis == "Y": bmesh.ops.rotate(bm, verts=bm.verts, matrix=Matrix.Rotation(math.pi / 2, 3, "X"))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(m); o.location = loc
    if parent: o.parent = parent
    return o


def sphere(name, r, m, loc, sub=3, scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    for v in bm.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = sub > 1
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(m); o.location = loc
    return o


def fillet(pts, r=0.03, n=6):
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, p, b = pts[i - 1], pts[i], pts[i + 1]
        rr = min(r, (a - p).length / 2.01, (b - p).length / 2.01)
        p0, p1 = p + (a - p).normalized() * rr, p + (b - p).normalized() * rr
        for k in range(n + 1):
            u = k / n
            out.append((1 - u) ** 2 * p0 + 2 * (1 - u) * u * p + u * u * p1)
    out.append(pts[-1])
    return out


def serp(x0, x1, zs, y, r=None):
    """horizontal serpentine on plane y through rows zs with semicircular U-bends"""
    pts = []
    for i, z in enumerate(zs):
        xa, xb = (x0, x1) if i % 2 == 0 else (x1, x0)
        pts += [Vector((xa, y, z)), Vector((xb, y, z))]
        if i < len(zs) - 1:
            zn = zs[i + 1]; rr = abs(z - zn) / 2; cz = (z + zn) / 2; s = 1 if xb > xa else -1
            for k in range(1, 12):
                a = math.pi / 2 - math.pi * k / 12
                pts.append(Vector((xb + s * rr * math.cos(a), y, cz + rr * math.sin(a) * (1 if z > zn else -1))))
    return pts


def plength(pts):
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def along(pts, s):
    for i in range(len(pts) - 1):
        L = (pts[i + 1] - pts[i]).length
        if s <= L: return pts[i].lerp(pts[i + 1], s / max(L, 1e-9))
        s -= L
    return pts[-1].copy()


def tube(name, pts, r, m, seg=10):
    """swept tube with UV.x = arc length (m), parallel-transport frames"""
    pts = [Vector(p) for p in pts]
    pts = [p for i, p in enumerate(pts) if i == 0 or (p - pts[i - 1]).length > 1e-5]
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    tans = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    nrm = tans[0].orthogonal().normalized()
    rings, s, S = [], 0.0, []
    for i, p in enumerate(pts):
        if i:
            s += (p - pts[i - 1]).length
            ax = tans[i - 1].cross(tans[i])
            if ax.length > 1e-8:
                nrm = Matrix.Rotation(tans[i - 1].angle(tans[i]), 3, ax.normalized()) @ nrm
        bi = tans[i].cross(nrm).normalized(); nn = bi.cross(tans[i]).normalized()
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / seg) * nn + math.sin(2 * math.pi * k / seg) * bi)) for k in range(seg)])
        S.append(s)
    for i in range(len(rings) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            f.smooth = True
            for lp, (u, v) in zip(f.loops, ((S[i], k / seg), (S[i], (k + 1) / seg), (S[i + 1], (k + 1) / seg), (S[i + 1], k / seg))):
                lp[uvl].uv = (u, v)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(m)
    return o, S[-1]


def imp(name, loc=(0, 0, 0), rz=0.0, s=1.0):
    path = os.path.join(A, "models", name, f"{name}_1k.gltf")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    e = link(bpy.data.objects.new(name + "_rig", None))
    for o in new:
        if o.parent is None: o.parent = e
    e.location, e.rotation_euler.z, e.scale = loc, rz, (s, s, s)
    e["base_scale"] = s
    return e


# ---------------------------------------------------------------- animation helpers
def kscale(o, t, s):
    o.scale = (s, s, s) if isinstance(s, (int, float)) else s
    o.keyframe_insert("scale", frame=F(t) if isinstance(t, float) else t)


def hidden(o):
    o.scale = (0, 0, 0); o.keyframe_insert("scale", frame=1)


def pop(o, t, s=None, dur=0.28):
    if o.type == "MESH" and o.parent is None and o.location.length == 0:
        centered(o)
    s = o.get("base_scale", 1.0) if s is None else s
    f = F(t)
    for ff, v in ((f, 0.0), (f + round(dur * FPS * 0.6), s * 1.15), (f + round(dur * FPS), s)):
        o.scale = (v, v, v); o.keyframe_insert("scale", frame=ff)


def unpop(o, t, dur=0.22):
    s = o.get("base_scale", 1.0); f = F(t)
    for ff, v in ((f, s), (f + 2, s * 1.12), (f + round(dur * FPS), 0.0)):
        o.scale = (v, v, v); o.keyframe_insert("scale", frame=ff)


def kloc(o, t, loc):
    o.location = loc; o.keyframe_insert("location", frame=F(t))


def krot(o, t, rot):
    o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=F(t))


def popped(o, t, **k):
    hidden(o); pop(o, t, **k); return o


# ================================================================ WORLD + KITCHEN
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(A, "hdri", "kloofendal_48d_partly_cloudy_puresky.hdr"))
bg = w.node_tree.nodes["Background"]; bg.inputs["Strength"].default_value = 1.1
w.node_tree.links.new(env.outputs[0], bg.inputs[0])

sun = bpy.data.lights.new("sun", "SUN"); sun.energy, sun.angle = 3.6, math.radians(2.5); sun.color = (1, 0.96, 0.9)
so = link(bpy.data.objects.new("sun", sun))
so.rotation_euler = Vector((-0.55, 0.42, -0.72)).normalized().to_track_quat("-Z", "Y").to_euler()
fl = bpy.data.lights.new("fill", "AREA"); fl.energy, fl.size = 260, 2.5
fo = link(bpy.data.objects.new("fill", fl)); fo.location = (2.6, -1.6, 2.4)
fo.rotation_euler = (Vector((0, 0, 0.9)) - fo.location).to_track_quat("-Z", "Y").to_euler()

box("grass", (-60, -60, -0.32), (60, 60, -0.12), M["grass"])
box("slab", (-3.1, -2.0, -0.12), (1.9, 2.3, 0.0), M["floor"])
WY = 2.2
box("wall_b1", (-3.1, WY, 0), (-1.8, WY + 0.1, 2.7), M["wall"])
box("wall_b2", (-0.6, WY, 0), (1.9, WY + 0.1, 2.7), M["wall"])
box("wall_b3", (-1.8, WY, 0), (-0.6, WY + 0.1, 1.1), M["wall"])
box("wall_b4", (-1.8, WY, 2.1), (-0.6, WY + 0.1, 2.7), M["wall"])
for n, lo, hi in (("wf1", (-1.84, WY - 0.03, 1.06), (-0.56, WY + 0.13, 1.1)), ("wf2", (-1.84, WY - 0.03, 2.1), (-0.56, WY + 0.13, 2.14)),
                  ("wf3", (-1.84, WY - 0.03, 1.06), (-1.8, WY + 0.13, 2.14)), ("wf4", (-0.6, WY - 0.03, 1.06), (-0.56, WY + 0.13, 2.14)),
                  ("wf5", (-1.22, WY + 0.03, 1.1), (-1.18, WY + 0.07, 2.1))):
    box(n, lo, hi, M["frame"])
box("wall_l", (-3.1, -2.0, 0), (-3.0, WY + 0.1, 2.7), M["wall"])
box("splash", (-3.0, WY - 0.01, 0.9), (-0.9, WY, 1.06), M["tiles"])
box("cabinets", (-3.0, 1.6, 0.0), (-0.9, WY, 0.86), M["cab"], 0.006)
box("counter", (-3.02, 1.56, 0.86), (-0.88, WY, 0.9), M["top"], 0.004)
imp("electric_stove", (-0.55, 1.88, 0), 0)
imp("vintage_electric_kettle", (-1.35, 1.9, 0.9), 0.4)
imp("tea_set_01", (-2.3, 1.9, 0.9), 0.2, 0.8)
imp("potted_plant_01", (1.3, 1.85, 0), 0.6)
clock = imp("wall_clock", (0.7, WY, 1.9), 0)
hands = [o for o in clock.children_recursive if any(k in o.name.lower() for k in ("hand", "arrow", "minute", "hour"))]
print("CLOCK parts", [o.name for o in clock.children_recursive])

X0, X1, Y0, Y1, Z0, Z1, WT = -0.36, 0.36, -0.34, 0.34, 0.06, 1.78, 0.05
# gnome (faces -Y by default) beside the fridge, turned toward the main camera side
gn = imp("garden_gnome", (0.7, -0.5, 0), math.atan2(0.65, 1.05), 0.85)            # act 1: beside the ice
gn2 = imp("garden_gnome", (0.0, -0.08, Z1), math.atan2(1.9, 2.1), 0.75)             # act 2: standing on top of the fridge

# ================================================================ STAGE 1: ice block (L1-2)
ice = centered(box("ice", (-0.21, -0.18, 0.0), (0.21, 0.18, 0.34), M["ice"], 0.025))
for p in ice.data.polygons: p.use_smooth = False
board = imp("wooden_cutting_board", (0.42, -0.3, 0), 0.3)
f1 = [imp("food_apple_01", (0.36, -0.3, 0.041)), imp("lemon", (0.5, -0.27, 0.093)), imp("CheeseBox_01", (0.42, -0.36, 0.041), 0.3, 0.8)]
puddle = cyl("puddle", 0.4, 0.004, M["water"], (0.0, 0.0, 0.002))
hidden(puddle)
t2, t2e = T(2), T(3)
kscale(puddle, T(2, "melts"), 0.0); kscale(puddle, t2e, 1.5)
kscale(ice, T(2, "melts"), 1.0); kscale(ice, t2e, (0.95, 0.95, 0.82))

# ================================================================ STAGE 2: icebox (L3-5)
IB = link(bpy.data.objects.new("icebox", None))
iw = [  # wooden carcass: right side (+x) left open as the cutaway
    box("ib_back", (-0.36, 0.27, 0.12), (0.36, 0.31, 1.3), M["wood"], 0.004),
    box("ib_left", (-0.36, -0.31, 0.12), (-0.32, 0.31, 1.3), M["wood"], 0.004),
    box("ib_bot", (-0.36, -0.31, 0.12), (0.36, 0.31, 0.16), M["wood"], 0.004),
    box("ib_top", (-0.37, -0.32, 1.26), (0.37, 0.32, 1.31), M["wood"], 0.004),
    box("ib_mid", (-0.32, -0.27, 0.78), (0.36, 0.27, 0.81), M["wood"], 0.004),
]
for x in (-0.33, 0.33):
    for y in (-0.28, 0.28):
        iw.append(box(f"ib_leg{x}{y}", (x - 0.025, y - 0.025, 0), (x + 0.025, y + 0.025, 0.12), M["wood"], 0.004))
# doors on left hinges, swung open
for n, z0, z1 in (("ib_door_top", 0.82, 1.25), ("ib_door_bot", 0.17, 0.77)):
    hp = link(bpy.data.objects.new(n + "_hinge", None)); hp.location = (-0.36, -0.31, 0)
    dd = box(n, (0, -0.035, z0), (0.72, 0.0, z1), M["wood"], 0.004, parent=None)
    dd.parent = hp; dd.location = (0, 0, 0)
    knob = sphere(n + "_k", 0.018, M["tin"], (0.66, -0.05, (z0 + z1) / 2)); knob.parent = hp
    hp.rotation_euler.z = -math.radians(115)
    iw.append(hp)
tinl = [box("tin_back", (-0.32, 0.262, 0.16), (0.36, 0.27, 1.26), M["tin"]),
        box("tin_left", (-0.32, -0.31, 0.16), (-0.312, 0.27, 1.26), M["tin"]),
        box("tin_mid", (-0.312, -0.27, 0.81), (0.36, 0.262, 0.818), M["tin"]),
        box("tin_bot", (-0.312, -0.31, 0.16), (0.36, 0.262, 0.168), M["tin"])]
tray = box("ib_tray", (-0.25, -0.22, 0.004), (0.25, 0.22, 0.05), M["tin"], 0.006)
drain_ib, _ = tube("ib_drain", [(0.28, 0.2, 0.8), (0.28, 0.2, 0.3), (0.2, 0.15, 0.06)], 0.012, M["tin"])
f2 = [imp("food_apple_01", (0.12, -0.08, 0.168)), imp("CheeseBox_01", (-0.12, 0.02, 0.168), 0.4), imp("food_lime_01", (0.22, 0.08, 0.168)),
      imp("jug_01", (0.05, 0.12, 0.168), 0.2)]
ice_box_pos = (0.03, 0.0, 0.818)

t3 = T(3); tb = T(3, "wooden"); ttin = T(3, "tin"); ttray = T(3, "tray")
for o in [IB] + iw + tinl + [tray, drain_ib] + f2:
    hidden(o)
for o in (board, *f1):
    unpop(o, t3 + 0.1)
for k, o in enumerate(iw):
    pop(o, tb + 0.05 * k)
for k, o in enumerate(tinl + [drain_ib]):
    pop(o, ttin + 0.06 * k)
# ice hops into the top compartment as the box builds; the puddle dries
kloc(ice, tb - 0.05, (0, 0, 0)); kloc(ice, tb + 0.45, ice_box_pos)
kscale(ice, tb - 0.05, (0.95, 0.95, 0.82)); kscale(ice, tb + 0.45, (0.95, 0.95, 1.1))
kscale(puddle, tb, 1.5); kscale(puddle, tb + 0.5, 0.0)
# tray slides in from the right
tray.scale = (0, 0, 0); tray.keyframe_insert("scale", frame=F(ttray) - 1)
tray.scale = (1, 1, 1); tray.keyframe_insert("scale", frame=F(ttray))
kloc(tray, ttray, (1.4, 0, 0)); kloc(tray, ttray + 0.5, (0, 0, 0))
for k, o in enumerate(f2):
    pop(o, ttin + 0.5 + 0.08 * k)

# L5: ice melts away, clock spins, the iceman's crate slides in with a fresh block
t5 = T(5); tgone = T(5, "gone"); tice = T(5, "iceman")
kscale(ice, T(5, "every"), (0.95, 0.95, 1.1)); kscale(ice, tgone + 0.25, (0.5, 0.5, 0.25)); kscale(ice, tgone + 0.6, 0)
for h in hands:
    krot(h, t5, h.rotation_euler.copy())
    r = h.rotation_euler.copy(); r.y += math.tau * (6 if "min" in h.name.lower() else 1)
    krot(h, tgone + 0.4, r)
crate = imp("wooden_crate_01", (4.0, -0.85, 0), 0.0, 0.75)
cice = box("crate_ice", (-0.17, -0.12, 0.05), (0.17, 0.12, 0.3), M["ice"], 0.02); cice.parent = crate
kloc(crate, tice - 0.1, (4.0, -0.85, 0)); kloc(crate, tice + 0.55, (1.25, -0.85, 0))

# ================================================================ STAGE 3: the refrigerator (L6-19)
t6 = T(6); tswap = T(6, "swap")
hidden(gn2); pop(gn2, tswap + 0.3)
for o in [IB] + iw + tinl + [tray, drain_ib] + f2 + [crate, gn]:
    unpop(o, tswap - 0.05)
# move crate rig scale keys: unpop uses base_scale
SK = 0.006
FR = []


def panel(n, lo, hi, inner_axis, inner_sign):
    """white skin / yellow foam / white liner sandwich, so the cut edge reads as insulation"""
    lo, hi = Vector(lo), Vector(hi)
    out_lo, out_hi, in_lo, in_hi = lo.copy(), hi.copy(), lo.copy(), hi.copy()
    i = "xyz".index(inner_axis)
    if inner_sign > 0:  # inner face is at hi
        out_hi[i] = lo[i] + SK; in_lo[i] = hi[i] - SK
    else:
        out_lo[i] = hi[i] - SK; in_hi[i] = lo[i] + SK
    fo_lo, fo_hi = lo.copy(), hi.copy(); fo_lo[i] += SK; fo_hi[i] -= SK
    return [box(n + "_skin", out_lo, out_hi, M["white"]), box(n + "_foam", fo_lo, fo_hi, M["foam"]), box(n + "_liner", in_lo, in_hi, M["liner"])]


FR += panel("fr_left", (X0, Y0, Z0), (X0 + WT, Y1, Z1), "x", +1)
FR += panel("fr_top", (X0, Y0, Z1 - WT), (X1, Y1, Z1), "z", -1)
FR += panel("fr_bot", (X0, Y0, Z0), (X1, Y1, Z0 + WT), "z", +1)
FR += panel("fr_back", (X0, Y1 - WT, Z0), (X1, Y1, Z1), "y", -1)
for x in (-0.3, 0.3):
    for y in (-0.28, 0.28):
        FR.append(cyl(f"foot{x}{y}", 0.022, 0.06, M["black"], (x, y, 0.03)))
for k, o in enumerate(FR):
    hidden(o); pop(o, tswap + 0.03 * (k // 3), dur=0.3)

# --- circuit geometry
EY = Y1 - WT - 0.03                      # evaporator plane (inside, on the back liner)
EZ = [1.66, 1.575, 1.49, 1.405, 1.32]
evap_pts = serp(-0.26, 0.30, EZ, EY)
CY = Y1 + 0.06                           # condenser plane (outside the back)
CZ = [0.48 + 0.1 * k for k in range(12)]
cond_pts = serp(-0.28, 0.28, CZ, CY)     # starts bottom-left, ends top-left (even rows) -> fix end
COMP = Vector((0.0, Y1 + 0.13, 0.0))
suct_pts = fillet([evap_pts[-1], (0.30, Y1 + 0.02, 1.32), (0.32, Y1 + 0.02, 1.32), (0.32, Y1 + 0.02, 0.30), (0.09, COMP.y, 0.27)], 0.04)
dis_pts = fillet([(-0.1, COMP.y, 0.27), (-0.22, COMP.y, 0.3), (-0.3, CY, 0.4), cond_pts[0]], 0.04)
CAPX, CAPY = 0.33, Y1 + 0.17
liq_pts = fillet([cond_pts[-1], (cond_pts[-1].x - 0.03, CY, cond_pts[-1].z), (-0.33, CY, 1.66), (-0.33, CY, 1.72), (CAPX, CY, 1.72), (CAPX, CAPY, 1.72), (CAPX, CAPY, 1.42)], 0.04)
hel = [Vector((CAPX + 0.03 * math.cos(a), CAPY + 0.03 * math.sin(a), 1.4 - 0.32 * a / (math.tau * 9))) for a in [math.tau * 9 * k / 360 for k in range(361)]]
cap_pts = [liq_pts[-1]] + hel + fillet([hel[-1], (CAPX, CAPY, 0.98), (CAPX - 0.04, Y1 + 0.02, 0.98), (CAPX - 0.04, Y1 + 0.02, 1.71), (-0.26, EY, 1.71), evap_pts[0]], 0.03)

BLUE, LBLUE, WARM, RED, ORANGE = (0.02, 0.3, 1), (0.25, 0.55, 1), (1, 0.4, 0.08), (1, 0.03, 0.0), (1, 0.28, 0.0)
mE = pipe_mat("p_evap", plength(evap_pts), BLUE)
mS = pipe_mat("p_suct", plength(suct_pts), LBLUE, WARM)
mD = pipe_mat("p_dis", plength(dis_pts), RED)
mC = pipe_mat("p_cond", plength(cond_pts), RED, ORANGE)
mL = pipe_mat("p_liq", plength(liq_pts), ORANGE)
mK = pipe_mat("p_cap", plength(cap_pts), ORANGE, BLUE, spacing=0.05)
pE, LE = tube("evap", evap_pts, 0.012, mE)
pS, LS = tube("suct", suct_pts, 0.011, mS)
pD, LD = tube("dis", dis_pts, 0.011, mD)
pC, LC = tube("cond", cond_pts, 0.009, mC)
pL, LL = tube("liq", liq_pts, 0.007, mL)
pK, LK = tube("cap", cap_pts, 0.005, mK, seg=8)
# condenser wire grid
wires = []
for k in range(19):
    x = -0.27 + k * 0.03
    wires.append(box(f"wire{k}", (x - 0.002, CY + 0.008, 0.46), (x + 0.002, CY + 0.012, 1.6), M["black"]))
# compressor + mount
comp = link(bpy.data.objects.new("compressor", None)); comp.location = COMP
c_body = cyl("comp_body", 0.11, 0.2, M["black"], (0, 0, 0.17)); c_body.parent = comp
c_dome = sphere("comp_dome", 0.11, M["black"], (0, 0, 0.27), scale=(1, 1, 0.55)); c_dome.parent = comp
c_base = box("comp_base", (-0.16, -0.1, 0.04), (0.16, 0.1, 0.07), M["black"], 0.01); c_base.parent = comp
c_lbl = box("comp_lbl", (-0.05, -0.112, 0.13), (0.05, -0.108, 0.2), M["white"]); c_lbl.parent = comp
comp["base_scale"] = 1.0

t7 = T(7); tliq = T(6, "liquid"); tminus = T(6, "minus")
key_power(0, 1)
reveal(mE, tliq, LE, 1.1)
txt_c = bpy.data.curves.new("t26", "FONT"); txt_c.body = "-26°C"; txt_c.size = 0.17; txt_c.extrude = 0.012; txt_c.align_x = "CENTER"
txt = link(bpy.data.objects.new("t26", txt_c)); txt.data.materials.append(M["blue"]); txt.location = (0.05, -0.05, 1.12)
tc = txt.constraints.new("TRACK_TO"); tc.track_axis, tc.up_axis = "TRACK_Z", "UP_Y"
txt.hide_render = True

# food in the cabinet + heat rising from it into the coil (L7)
f3 = [imp("plastic_bottle_gallon", (0.17, 0.08, Z0 + WT), 0.3), imp("carrot_cake", (-0.12, -0.13, Z0 + WT)),
      imp("food_apple_01", (0.2, -0.2, Z0 + WT)), imp("CheeseBox_01", (-0.12, 0.12, Z0 + WT), 0.2)]
milk = f3[0]
for k, o in enumerate(f3):
    hidden(o); pop(o, t7 + 0.1 + 0.08 * k)
theat = T(7, "soaks")
for k in range(14):
    src = Vector(f3[k % 4].location) + Vector((random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), 0.12))
    dst = along(evap_pts, random.uniform(0.1, LE - 0.1))
    hb = sphere(f"heat{k}", 0.018, M["heat"], src, sub=2)
    t0 = theat - 0.6 + 0.16 * k
    hidden(hb); kscale(hb, t0, 0); kloc(hb, t0, src); kscale(hb, t0 + 0.15, 1)
    kloc(hb, t0 + 1.1, dst); kscale(hb, t0 + 1.0, 1); kscale(hb, t0 + 1.2, 0)

# L8-9: warm gas line to the compressor, compressor pops, squeezes (shakes), hot line out
t8, t9 = T(8), T(9)
reveal(mS, t8 + 0.2, LS, 1.2)
tcomp, tsq, thot = T(9, "compressor"), T(9, "squeezes"), T(9, "hotter")
hidden(comp); pop(comp, tcomp - 0.1, s=1.0)
reveal(mD, thot - 0.2, LD, 0.6)
# L10: condenser coils + wire grid, heat shimmering off the back
t10 = T(10); tcoils = T(10, "coils"); tdump = T(10, "dumps")
reveal(mC, tcoils - 0.2, LC, 1.6)
for k, o in enumerate(wires):
    hidden(o); pop(o, tcoils + 0.2 + 0.03 * k)
for k in range(16):
    p0 = Vector((random.uniform(-0.26, 0.26), CY + 0.03, random.uniform(0.5, 1.5)))
    hb = sphere(f"waste{k}", random.uniform(0.02, 0.035), M["heat"], p0, sub=2)
    t0 = tdump + 0.18 * (k % 8) + (1.6 if k >= 8 else 0)
    hidden(hb); kloc(hb, t0, p0); kscale(hb, t0, 0); kscale(hb, t0 + 0.2, 0.9)
    kloc(hb, t0 + 1.4, p0 + Vector((random.uniform(-0.1, 0.1), 0.45, 0.35))); kscale(hb, t0 + 1.2, 0.8); kscale(hb, t0 + 1.4, 0)
# L11: liquid line + capillary (orange -> blue)
t11 = T(11); ttube = T(11, "tube")
reveal(mL, t11 + 0.2, LL, 0.9)
reveal(mK, ttube - 0.2, LK, 1.6)

# compressor shake while running (L9 squeeze .. L13 off), plus again from L14
toff = T(13, "off")


def shake(o, t0, t1, amp=0.004):
    base = o.location.copy()
    for f in range(F(t0), F(t1)):
        o.location = base + Vector((random.uniform(-amp, amp), random.uniform(-amp, amp), random.uniform(0, amp)))
        o.keyframe_insert("location", frame=f)
    o.location = base; o.keyframe_insert("location", frame=F(t1))


shake(comp, tsq, toff)
shake(comp, T(14) + 0.3, END, 0.0025)

# L12: milk freezes (ice crystals); L13: thermostat dial, compressor + flow idle
t12 = T(12); tmilk = T(12, "ice"); t13 = T(13); tthermo = T(13, "thermostat"); tsw = T(13, "switches"); tenough = T(13, "enough")
mc = Vector(milk.location)
for k in range(22):
    a = random.uniform(0, math.tau); z = random.uniform(0.03, 0.27)
    p = mc + Vector((0.09 * math.cos(a), 0.07 * math.sin(a), z))
    cr = sphere(f"crys{k}", random.uniform(0.008, 0.016), M["crystal"], p, sub=1)
    cr.rotation_euler = (random.random() * 3, random.random() * 3, random.random() * 3)
    hidden(cr); pop(cr, tmilk - 0.3 + 0.03 * k); unpop(cr, tenough - 0.1 + 0.02 * k)
dial = link(bpy.data.objects.new("thermostat", None)); dial.location = (X0 + WT, -0.16, 1.5)
dh = box("dial_house", (0, -0.07, -0.05), (0.03, 0.07, 0.05), M["knob"], 0.006); dh.parent = dial
kn = cyl("dial_knob", 0.035, 0.025, M["knob"], (0.042, 0, 0), axis="X"); kn.parent = dial
mk = box("dial_mark", (0.054, -0.004, 0.0), (0.056, 0.004, 0.03), M["black"]); mk.parent = kn; mk.location = (-0.042, 0, 0)
for k in range(12):
    a = math.tau * k / 12
    tk = box(f"tick{k}", (0.031, -0.002, 0.04), (0.033, 0.002, 0.047), M["black"]); tk.parent = dial
    tk.rotation_euler.x = a
dial["base_scale"] = 1.0
hidden(dial); pop(dial, tthermo - 0.1)
krot(kn, tsw - 0.1, (0, 0, 0)); krot(kn, tsw + 0.4, (math.radians(-120), 0, 0))
key_power(toff - 0.1, 1); key_power(toff + 0.3, 0.12); key_power(T(14) + 0.2, 0.12); key_power(T(14) + 0.6, 1)

# L14-15: door (left hinge) ajar + cold air leaking; seal pops and the door snaps shut
t14, t15 = T(14), T(15); tmag = T(15, "magnet")
hinge = link(bpy.data.objects.new("door_hinge", None)); hinge.location = (X0, Y0, 0)
dbox = box("door", (0, -0.055, Z0), (X1 - X0, 0, Z1), M["white"], 0.012); dbox.parent = hinge
handle = box("handle", (X1 - X0 - 0.06, -0.085, 0.95), (X1 - X0 - 0.035, -0.055, 1.45), M["tin"], 0.008); handle.parent = hinge
dliner = box("door_liner", (0.04, -0.002, Z0 + 0.05), (X1 - X0 - 0.04, 0.012, Z1 - 0.05), M["liner"], 0.01); dliner.parent = hinge
for k, z in enumerate((0.5, 0.95, 1.35)):
    bn = box(f"door_bin{k}", (0.07, 0.012, z), (X1 - X0 - 0.07, 0.07, z + 0.07), M["glass"], 0.004); bn.parent = hinge
gk = []
G = 0.018
for n, lo, hi in (("g_l", (0.012, 0.0, Z0 + 0.012), (0.012 + G, G, Z1 - 0.012)), ("g_r", (X1 - X0 - 0.012 - G, 0.0, Z0 + 0.012), (X1 - X0 - 0.012, G, Z1 - 0.012)),
                  ("g_b", (0.012, 0.0, Z0 + 0.012), (X1 - X0 - 0.012, G, Z0 + 0.012 + G)), ("g_t", (0.012, 0.0, Z1 - 0.012 - G), (X1 - X0 - 0.012, G, Z1 - 0.012))):
    g_ = box(n, lo, hi, M["rubber"], 0.007); g_.parent = hinge; gk.append(g_)
hinge["base_scale"] = 1.0
hidden(hinge); pop(hinge, t14 - 0.05)
for g_ in gk:
    hidden(g_); pop(g_, T(15, "rubber") - 0.1)
krot(hinge, t14, (0, 0, -math.radians(35))); krot(hinge, t14 + 0.7, (0, 0, -math.radians(9)))
krot(hinge, tmag - 0.15, (0, 0, -math.radians(9))); krot(hinge, tmag + 0.12, (0, 0, 0))
for k in range(18):
    z = random.uniform(0.35, 1.6)
    p0 = Vector((X1 + 0.02, Y0 - 0.03, z))
    wi = sphere(f"wisp{k}", random.uniform(0.04, 0.07), M["cold"], p0, sub=2)
    t0 = t14 + 0.4 + 0.14 * k
    if t0 + 1.0 > tmag: t0 = tmag - 1.0 - 0.05 * (k % 4)
    hidden(wi); kloc(wi, t0, p0); kscale(wi, t0, 0.3); kscale(wi, t0 + 0.2, 1)
    kloc(wi, t0 + 1.2, p0 + Vector((random.uniform(0.25, 0.5), random.uniform(-0.4, -0.15), -random.uniform(0.15, 0.35))))
    kscale(wi, t0 + 1.0, 1.3); kscale(wi, min(t0 + 1.2, tmag + 0.1), 0)

# L16-17: frost grows on the evaporator, heater melts it, meltwater drips to a tray on the compressor and steams off
t16, t17 = T(16), T(17)
mF = frost_mat("frost")
pF, _ = tube("frost", evap_pts, 0.024, mF, seg=12)
thr = mF.node_tree.nodes["thr"].outputs[0]
key_val(thr, t16 + 0.2, 1.0); key_val(thr, t16 + 2.6, 0.38)
theater, tmelt, tdrip, ttray2, tdry = T(17, "heater"), T(17, "melts"), T(17, "drips"), T(17, "tray"), T(17, "dries")
key_val(thr, tmelt, 0.38); key_val(thr, tmelt + 1.3, 1.0)
heater_m = mat("heater", (0.15, 0.05, 0.03), 0.4, emit=(1, 0.25, 0.05), es=0)
hz = EZ[-1] - 0.04
heater, _ = tube("heater", [(-0.26, EY, hz), (0.30, EY, hz)], 0.006, heater_m)
hidden(heater); pop(heater, theater - 0.15)
es = heater_m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
key_val(es, theater, 0); key_val(es, theater + 0.4, 14); key_val(es, tmelt + 1.4, 14); key_val(es, tmelt + 1.8, 0)
drain_pts = fillet([(0.14, EY, hz - 0.02), (0.14, Y1 + 0.03, hz - 0.04), (0.14, Y1 + 0.03, 0.5), (0.05, COMP.y, 0.43)], 0.04)
dr, LDR = tube("drain", drain_pts, 0.008, mat("drainm", (0.95, 0.95, 0.95), 0.3, alpha=0.55))
hidden(dr); pop(dr, theater + 0.2)
ptray = box("drip_tray", (-0.12, COMP.y - 0.1, 0.375), (0.12, COMP.y + 0.1, 0.41), M["white"], 0.006)
pw = box("tray_water", (-0.11, COMP.y - 0.09, 0.38), (0.11, COMP.y + 0.09, 0.392), M["water"])
centered(pw)
hidden(ptray); pop(ptray, ttray2 - 0.5)
hidden(pw); kscale(pw, ttray2 + 0.3, (1, 1, 0)); kscale(pw, ttray2 + 0.9, 1); kscale(pw, tdry + 0.2, 1); kscale(pw, tdry + 1.6, (1, 1, 0.01))
for k in range(8):
    dp = sphere(f"drop{k}", 0.011, M["water"], drain_pts[0], sub=2, scale=(1, 1, 1.4))
    t0 = tdrip - 0.2 + 0.22 * k
    hidden(dp); kscale(dp, t0, 0); kscale(dp, t0 + 0.06, 1)
    for j in range(7):
        kloc(dp, t0 + 0.2 * j, along(drain_pts, LDR * j / 6))
    kscale(dp, t0 + 1.15, 1); kscale(dp, t0 + 1.25, 0)
for k in range(10):
    p0 = Vector((random.uniform(-0.08, 0.08), COMP.y + random.uniform(-0.06, 0.06), 0.41))
    st = sphere(f"steam{k}", random.uniform(0.03, 0.05), M["steam"], p0, sub=2)
    t0 = tdry - 0.3 + 0.17 * k
    hidden(st); kloc(st, t0, p0); kscale(st, t0, 0.2); kscale(st, t0 + 0.3, 1)
    kloc(st, t0 + 1.4, p0 + Vector((random.uniform(-0.1, 0.1), 0.15, 0.5))); kscale(st, t0 + 1.2, 1.4); kscale(st, t0 + 1.4, 0)

# L18: shelves + food, door opens and the light comes on
t18 = T(18); tsh = T(18, "shelves"); tlight = T(18, "light"); topen = T(18, "open")
SZ = [0.5, 0.86, 1.18]
shelves = [box(f"shelf{k}", (X0 + WT + 0.005, Y0 + 0.09, z), (X1 - 0.005, Y1 - WT - 0.06, z + 0.012), M["glass"], 0.003) for k, z in enumerate(SZ)]
for k, s_ in enumerate(shelves):
    centered(s_); hidden(s_); pop(s_, tsh - 0.15 + 0.12 * k)
f4 = [imp("strawberry_chocolate_cake", (-0.1, -0.06, SZ[0] + 0.012)), imp("food_pears_asian_01", (0.18, -0.12, SZ[0] + 0.044)),
      imp("hamburger_buns", (-0.02, 0.0, SZ[1] + 0.012), 0.1), imp("lemon", (0.22, -0.18, SZ[1] + 0.064)), imp("food_lime_01", (0.12, -0.2, SZ[1] + 0.012)),
      imp("jug_01", (-0.08, 0.05, SZ[2] + 0.012), -0.3), imp("food_avocado_01", (0.22, -0.12, SZ[2] + 0.012)), imp("yellow_onion", (0.14, 0.02, SZ[2] + 0.012))]
for k, o in enumerate(f4):
    hidden(o); pop(o, tsh + 0.25 + 0.09 * k)
krot(hinge, topen - 0.35, (0, 0, 0)); krot(hinge, topen + 0.4, (0, 0, -math.radians(112)))
bulb = sphere("bulb", 0.022, M["bulb"], (X0 + WT + 0.02, -0.16, 1.4), sub=2)
bes = M["bulb"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
key_val(bes, topen - 0.05, 0); key_val(bes, topen + 0.05, 25)
pl = bpy.data.lights.new("fridge_light", "POINT"); pl.energy, pl.shadow_soft_size, pl.color = 0, 0.05, (1, 0.93, 0.8)
plo = link(bpy.data.objects.new("fridge_light", pl)); plo.location = (X0 + WT + 0.06, -0.16, 1.4)
pl.keyframe_insert("energy", frame=F(topen - 0.05)); pl.energy = 35; pl.keyframe_insert("energy", frame=F(topen + 0.05))

# L19: gnome hops for "Congratulations"
t19 = T(19)
gl = gn2.location.copy()
kloc(gn2, t19, gl); kloc(gn2, t19 + 0.18, gl + Vector((0, 0, 0.14))); kloc(gn2, t19 + 0.36, gl)
kloc(gn2, t19 + 0.5, gl); kloc(gn2, t19 + 0.68, gl + Vector((0, 0, 0.1))); kloc(gn2, t19 + 0.84, gl)

# ================================================================ CAMERA (shot list, snappy 0.45 s eased moves + slow push)
SH = [  # (time, cam, target, lens)
    (0.0, (1.35, -1.55, 0.85), (0.0, -0.15, 0.25), 28),
    (T(2) - 0.1, (1.0, -1.2, 0.38), (0.05, -0.08, 0.06), 26),
    (tb - 0.25, (2.0, -1.8, 1.2), (0.0, 0.0, 0.62), 28),
    (ttray - 0.2, (1.25, -1.0, 0.4), (0.05, 0.0, 0.12), 28),
    (T(4) - 0.1, (1.6, -2.0, 1.0), (-0.05, 0.0, 0.62), 30),
    (t5 - 0.1, (2.5, -2.7, 1.5), (0.5, 0.1, 0.8), 26),
    (tswap - 0.25, (2.1, -1.9, 1.35), (0.0, 0.05, 0.9), 28),
    (tliq - 0.2, (1.55, -0.75, 1.75), (0.0, 0.15, 1.42), 28),
    (t7 + 0.4, (1.7, -1.0, 1.25), (0.0, 0.1, 0.85), 26),
    (t8 - 0.1, (1.7, 0.2, 1.15), (0.2, 0.35, 0.8), 28),
    (tcomp - 0.3, (1.3, 1.2, 0.75), (0.0, COMP.y, 0.35), 28),
    (t10 - 0.1, (1.5, 1.9, 1.3), (0.0, CY, 1.0), 26),
    (T(10, "thats") - 0.1, (2.1, 1.2, 1.1), (0.0, 0.3, 0.9), 28),
    (t11 - 0.1, (1.2, 1.05, 1.45), (CAPX, CAPY, 1.25), 32),
    (T(11, "freezing") - 0.15, (1.55, -0.75, 1.75), (0.0, 0.15, 1.42), 28),
    (t12 - 0.1, (1.5, -0.8, 0.9), (0.1, 0.05, 0.35), 28),
    (tthermo - 0.25, (1.1, -0.6, 1.6), (X0 + WT, -0.16, 1.5), 32),
    (t14 - 0.1, (1.8, -2.1, 1.25), (0.1, -0.3, 0.95), 28),
    (T(15, "rubber") - 0.2, (1.2, -1.3, 1.3), (0.36, -0.37, 1.1), 32),
    (t16 - 0.1, (1.55, -0.75, 1.75), (0.0, 0.15, 1.42), 28),
    (tdrip - 0.2, (1.8, 0.9, 1.0), (0.12, 0.4, 0.8), 26),
    (tdry - 0.4, (1.1, 1.0, 0.8), (0.03, COMP.y, 0.42), 30),
    (t18 - 0.1, (1.9, -2.1, 1.3), (0.0, 0.0, 0.9), 28),
    (t19 - 0.1, (2.4, -3.0, 1.5), (0.1, 0.0, 0.85), 26),
]
cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 24
cam = link(bpy.data.objects.new("cam", cam_d)); sc.camera = cam
aim = link(bpy.data.objects.new("aim", None))
tt = cam.constraints.new("TRACK_TO"); tt.target = aim; tt.track_axis, tt.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
TR = 0.45
ease = lambda x: x * x * x * (x * (6 * x - 15) + 10)


def pose(i, t):
    t0, c, g, L = SH[i]
    t1 = SH[i + 1][0] if i + 1 < len(SH) else END
    u = max(0.0, min(1.0, (t - t0) / max(t1 - t0, 0.1)))
    c, g = Vector(c), Vector(g)
    push = 0.09 if i < len(SH) - 1 else -0.18     # last shot pulls out
    return c + (g - c) * push * u, g, L


for f in range(1, NF + 1):
    t = (f - 1) / FPS
    i = max(k for k in range(len(SH)) if SH[k][0] <= t)
    c, g, L = pose(i, t)
    if i and t - SH[i][0] < TR:
        e = ease((t - SH[i][0]) / TR)
        c0, g0, L0 = pose(i - 1, SH[i][0])
        c, g, L = c0.lerp(c, e), g0.lerp(g, e), L0 + (L - L0) * e
    cam.location = c; cam.keyframe_insert("location", frame=f)
    aim.location = g; aim.keyframe_insert("location", frame=f)
    cam_d.lens = L; cam_d.keyframe_insert("lens", frame=f)

# ================================================================ RENDER
r = sc.render
r.engine = "CYCLES"
r.resolution_percentage = 100
if RES == 1080:
    r.resolution_x, r.resolution_y = 1080, 1920
else:
    r.resolution_y = RES; r.resolution_x = RES * 9 // 16 // 2 * 2
r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGB"; r.image_settings.compression = 15
r.use_persistent_data = True
try:
    sc.view_settings.view_transform = "AgX"; sc.view_settings.exposure = -0.25; sc.view_settings.look = "AgX - Medium High Contrast"
except Exception as ex:
    print("look", ex)
cy = sc.cycles
cy.samples, cy.use_adaptive_sampling, cy.adaptive_threshold = SAMPLES, True, 0.03
cy.use_denoising = True
cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces, cy.transmission_bounces, cy.transparent_max_bounces = 8, 3, 4, 8, 24
cy.caustics_reflective = cy.caustics_refractive = False
cy.blur_glossy = 1.0
dev = "CPU"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in (() if "--cpu" in argv else ("OPTIX", "CUDA", "HIP", "METAL")):
    try:
        prefs.compute_device_type = kind; prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices: d.use = d.type == kind
            dev = kind; break
    except Exception:
        pass
cy.device = "GPU" if dev != "CPU" else "CPU"
if dev == "CPU":
    r.threads_mode, r.threads = "FIXED", int(opt("--threads", 0)) or os.cpu_count()
if dev == "OPTIX":
    cy.denoiser = "OPTIX"
print("DEVICE", dev, "frames", NF, "res", r.resolution_x, r.resolution_y)

if opt("--save"):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opt("--save")))
os.makedirs(OUTDIR, exist_ok=True)
if opt("--stills"):
    for s in opt("--stills").split(","):
        f = F(float(s)); sc.frame_set(f)
        r.filepath = os.path.join(OUTDIR, f"still_{float(s):05.2f}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", s, flush=True)
elif "--dry" not in argv:
    a, b = map(int, opt("--range", f"1,{NF}").split(","))
    order = range(b, a - 1, -1) if "--reverse" in argv else range(a, b + 1)
    for f in order:
        p = os.path.join(OUTDIR, f"f_{f:04d}.png")
        if "--skip" in argv and os.path.exists(p) and os.path.getsize(p) > 0:
            continue
        sc.frame_set(f); r.filepath = p
        bpy.ops.render.render(write_still=True)
        print("FRAME", f, flush=True)
