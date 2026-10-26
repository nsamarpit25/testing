"""Zack D. Films-style look test over an epx.py build: the whole room in one teal (Cleo, her keyboard, the screens and the
view outside keep their own colours, so the story reads), Claude hidden, four seasons outside the window, and the
cameras for the cut. Rendered as overlapping clips (one season state each) that zdf_cut.sh dissolves together.

blender -b base.blend -P zdf.py -- look <out.blend> <screens dir>
blender -b zdf.blend  -P zdf.py -- clips <outdir> <height> <samples> [clip,clip...]
"""
import bpy, colorsys, os, sys
from math import radians
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_scene as bs  # noqa: E402
from lineup import camera  # noqa: E402

KEEP = ("V3_Cleo", "D2_", "MorningSky", "SeasonSky", "FarHouse", "NearHouse", "Tree", "Win_", "Screen", "Phone",
        "Bulb", "SolLed", "Keyboard", "Keys", "Succulent", "Soil", "Sticky")
TEAL_H = 0.505
SCREENS = ("d1", "d92", "d183", "d274", "ship")
# per state: tree, tree glow, sky stops, roofs, Cleo's hoodie, monitor picture
SEASONS = [
    dict(tree="#f4a3c4", glow=0.85, roof=None, top="#f2c230", mon="d1",
         sky=[(0.0, "#f6e7d8"), (0.35, "#f3dfe6"), (0.45, "#cfe3f2"), (0.7, "#8fc0ea"), (1.0, "#6aa4dc")]),
    dict(tree="#4cae4f", glow=0.8, roof=None, top="#e8544a", mon="d92",
         sky=[(0.0, "#fff3cf"), (0.35, "#e9f2f6"), (0.45, "#b5dcf5"), (0.7, "#6fb4ee"), (1.0, "#3f8fdc")]),
    dict(tree="#e8742a", glow=0.85, roof=None, top="#7e57c2", mon="d183",
         sky=[(0.0, "#ffd9a8"), (0.35, "#f6c99a"), (0.45, "#e9b8a0"), (0.7, "#a9a4c8"), (1.0, "#7a86b8")]),
    dict(tree="#eef3f7", glow=0.9, roof="#f2f6fa", top="#f08a2c", mon="d274",
         sky=[(0.0, "#c9d6e3"), (0.35, "#b7c7d8"), (0.45, "#9fb3ca"), (0.7, "#8299b5"), (1.0, "#6d86a6")]),
]
SEASONS.append(dict(SEASONS[0], mon="ship"))  # a year on: blossom again, and the app is out

# name, camera, state, first, last  (overlaps are the dissolve handles)
CLIPS = [("A", "WIDE", 0, 1, 64), ("B", "HANDS", 0, 62, 118),
         ("L0", "LAPSE", 0, 116, 149), ("L1", "LAPSE", 1, 141, 174), ("L2", "LAPSE", 2, 166, 199), ("L3", "LAPSE", 3, 191, 218),
         ("C", "MON", 4, 215, 246), ("D", "CU", 4, 244, 300)]


def set_col(m, hexcol, strength=None):
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            inp = n.inputs["Base Color"]
            for lk in list(inp.links):
                m.node_tree.links.remove(lk)
            inp.default_value = (*bs.lin(hexcol), 1)
        elif n.type == "EMISSION":
            n.inputs["Color"].default_value = (*bs.lin(hexcol), 1)
            if strength is not None:
                n.inputs["Strength"].default_value = strength
    m.diffuse_color = (*bs.lin(hexcol), 1)


def teal(m):
    """Same lightness as the material had (so shapes still separate), in one teal hue."""
    r, g, b = (c ** (1 / 2.2) for c in m.diffuse_color[:3])
    v = 0.299 * r + 0.587 * g + 0.114 * b
    rr, gg, bb = colorsys.hsv_to_rgb(TEAL_H, 0.62 - 0.22 * v, 0.30 + 0.62 * v)
    set_col(m, "#%02x%02x%02x" % tuple(int(255 * x) for x in (rr, gg, bb)))


def darker(hexcol, k=0.85):
    h = hexcol.lstrip("#")
    return "#" + "".join("%02x" % int(int(h[i:i + 2], 16) * k) for i in (0, 2, 4))


def apply_state(k):
    s = SEASONS[k]
    set_col(bpy.data.materials["Tree"], s["tree"], s["glow"])
    for nm in ("FarHouse_roof", "NearHouse_roof"):
        m = bpy.data.materials[nm]
        set_col(m, s["roof"] or m["roof0"], 0.9 if s["roof"] else m["roof_glow"])
    bpy.data.objects["Night_sky"].data.materials[0] = bpy.data.materials[f"SeasonSky{SEASONS.index(s) if k < 4 else 0}"]
    set_col(bpy.data.materials["V3_Cleo_Top"], s["top"])
    set_col(bpy.data.materials["V3_Cleo_Trim"], darker(s["top"]))
    tex = next(n for n in bpy.data.objects["Mon_screen"].data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE")
    tex.image = bpy.data.images[s["mon"] + ".png"]


def look(out, screens):
    # Claude off the desk: this one is only about her
    root = bpy.data.objects["D2_Bubble"]
    for ob in [root] + list(root.children_recursive):
        ob.hide_render = ob.hide_viewport = True
    for m in bpy.data.materials:
        if m.node_tree and not m.name.startswith(KEEP):
            teal(m)
    for ob in bpy.data.objects:  # bigger trees, crowns over the near roofs, so the seasons read through the window
        if ob.name.startswith("Tree"):
            ob.scale *= 1.7
            ob.location.z *= 1.7
    # the room light a touch cooler and brighter, as in the reference's flat daylight
    bpy.data.objects["Room_fill"].data.energy *= 1.25
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (*bs.lin("#3e6f74"), 1)
    for nm in ("FarHouse_roof", "NearHouse_roof"):  # remember the daylight roofs for the non-winter states
        m = bpy.data.materials[nm]
        em = next(n for n in m.node_tree.nodes if n.type == "EMISSION")
        c = em.inputs["Color"].default_value
        m["roof0"] = "#%02x%02x%02x" % tuple(int(255 * min(1, x ** (1 / 2.2))) for x in c[:3])
        m["roof_glow"] = em.inputs["Strength"].default_value
    for i, s in enumerate(SEASONS[:4]):
        sky = bs.gradient_mat(f"SeasonSky{i}", "Z", 0.0, 1.0, s["sky"], emit_strength=1.0, coords="Generated", pure_emission=True)
        sky.use_fake_user = True
    for nm in SCREENS:
        im = bpy.data.images.get(nm + ".png") or bpy.data.images.load(os.path.join(screens, nm + ".png"))
        im.pack()
        im.use_fake_user = True

    # cameras
    kb = bpy.data.objects["KB_base"].matrix_world.translation.copy()
    eyes = next(o for o in bpy.data.objects if o.name == "V3_Cleo_eye1")
    scr = bpy.data.objects["Mon_screen"]
    sc = scr.matrix_world.translation.copy()
    sn = (scr.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    head = bpy.data.objects["V3_Cleo_hair"]
    cams = {
        "WIDE": camera("CAM_Z_WIDE", (0.10, -1.25, 1.36), Vector((0.0, 0.42, 0.98)), 27, 5.6, head),
        "HANDS": camera("CAM_Z_HANDS", tuple(kb + Vector((0.26, -0.30, 0.20))), kb + Vector((0.0, 0.03, 0.03)), 42, 2.2,
                        bpy.data.objects["KB_base"]),
        "LAPSE": camera("CAM_Z_LAPSE", (-0.40, -1.30, 1.42), Vector((-0.10, 0.60, 1.08)), 23, 8.0, head),
        "MON": camera("CAM_Z_MON", tuple(sc + sn * 1.05 + Vector((0, 0, 0.03))), sc, 35, 4.0, scr),
        "CU": camera("CAM_Z_CU", (-0.10, -0.34, 1.05), Vector((0.0, 0.55, 1.00)), 40, 2.0, eyes),
    }
    cams["MON"].data.shift_y = -0.06
    push = {"WIDE": (1, 64, 0.16), "HANDS": (62, 118, 0.12), "MON": (215, 246, 0.10), "CU": (244, 300, 0.10)}
    for k, (f0, f1, amt) in push.items():  # the slow push-in on every moving shot (straight down the lens axis)
        c = cams[k]
        fwd = c.matrix_world.to_3x3() @ Vector((0, 0, -1))
        p0 = c.location.copy()
        dist = (Vector(c.data.dof.focus_object.matrix_world.translation) - p0).length if c.data.dof.focus_object else 1.0
        c.location = p0
        c.keyframe_insert("location", frame=f0)
        c.location = p0 + fwd * dist * amt
        c.keyframe_insert("location", frame=f1)
        for fc in c.animation_data.action.fcurves if hasattr(c.animation_data.action, "fcurves") else []:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    scn = bpy.context.scene
    scn.timeline_markers.clear()
    apply_state(0)
    scn.camera = cams["WIDE"]
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


def clips(outdir, height, samples, only):
    scn = bpy.context.scene
    scn.render.resolution_y = height
    scn.render.resolution_x = round(height * 9 / 16 / 2) * 2
    scn.render.resolution_percentage = 100
    scn.eevee.taa_render_samples = samples
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    ee = scn.eevee
    ee.use_raytracing, ee.use_fast_gi = True, True
    for name, cam, state, f0, f1 in CLIPS:
        if only and name not in only:
            continue
        apply_state(state)
        scn.camera = bpy.data.objects[f"CAM_Z_{cam}"]
        scn.frame_start, scn.frame_end = f0, f1
        if only and only.get(name):  # a single still at that frame
            scn.frame_set(only[name])
            scn.render.filepath = os.path.join(outdir, f"{name}_{only[name]:04d}.png")
            bpy.ops.render.render(write_still=True)
        else:
            scn.render.filepath = os.path.join(outdir, name, "f_")
            bpy.ops.render.render(animation=True)
        print("CLIP", name, flush=True)


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:]
    if a[0] == "look":
        look(a[1], a[2])
    else:  # clips <outdir> <height> <samples> [A,B or A:30,L2:180 for stills]
        sel = {}
        for x in (a[4].split(",") if len(a) > 4 else []):
            n, _, f = x.partition(":")
            sel[n] = int(f) if f else 0
        clips(a[1], int(a[2]), int(a[3]), sel)
