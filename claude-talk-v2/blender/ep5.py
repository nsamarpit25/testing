"""Episode 5 "Three dev servers": she has made the button green eleven times and it is still blue, because she edits
~/my-app-final while her browser shows ~/my-app on localhost:5173 (three dev servers running; Vite took 5174 and 5175).
Same room, rig, look (Ep 4's sunset restyle, the rebuilt phone), staging and acting tools as ep4.py.

blender -b --factory-startup -P ep5.py -- <out.blend> <timeline.json>
timeline.json (scripts/ep5_timeline.py): lines with mouth envelopes, story events (ev), the monitor and phone image
changes (mon, phone), the phone's screen glow (pglow) and the monitor glow (frame, colour, energy).
"""
import bpy, bmesh, json, os, sys
from math import sin, cos, pi, atan2, radians, sqrt
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_scene as bs  # noqa: E402
from build_scene import ss  # noqa: E402
from lineup import camera  # noqa: E402
from rooms import build_room  # noqa: E402
from body import ARM_SIT, mirror  # noqa: E402

N = "V3_Cleo"
HIDE = ("PaperStar", "Orb", "Headphone", "TaskCard", "TaskLine", "Fairy", "Cork", "Pin",
        "NoteLine", "Book0", "Book1", "Book2", "Note_")
HOME = Vector((-0.36, 0.23))   # Claude's spot on the desk, a little way off her right hand
NEAR = Vector((-0.30, 0.25))   # a hop closer on line 16, still with room between them
TOP = 0.76                     # desk top
WRIST_SIGN = 1                 # which way round the hands roll palm-down (checked in renders)
CK = 0.82                      # Claude's acting scale: leans, tilts, hops, squash and puff at 82%

# camera per line (inserts between lines are placed in main())
SHOT = {1: "CLEO", 2: "CLAUDE", 3: "CLEOCU", 4: "CLAUDE", 5: "CLEO", 6: "MON", 7: "CLEO", 8: "CLAUDE", 9: "CLEOCU",
        10: "MON", 11: "CLEOCU", 12: "CLAUDE", 13: "MON", 14: "CLEOCU", 15: "CLAUDE", 16: "CLEOCU", 17: "CLAUDE", 18: "CLEOCU",
        19: "TWO", 20: "CLEO", 21: "CLAUDE", 22: "CLEOCU"}
MON_RZ = -1.0                  # monitor turned well toward the cameras
PHONE_AT = (-0.14, 0.03)


def tidy():
    for ob in list(bpy.data.objects):
        if ob.name.startswith(HIDE):
            if ob.type == "LIGHT":
                ob.data.energy = 0
            else:
                ob.hide_render = True
    stage_monitor()
    face_light()
    desk_props()
    outside()
    restyle()
    restyle5()


def stage_monitor():
    """Turn the monitor a little toward the cameras (she still sees it), switch its screen on and light it."""
    mon = bpy.data.objects["Monitor"]
    mon.rotation_euler.z = MON_RZ
    for ob in bpy.data.objects:  # the modelled code strips and sticky note would sit over the screen images
        if ob.name.startswith(("Code_", "Mon_note")):
            ob.hide_render = True
    bpy.context.view_layer.update()
    scr = bpy.data.objects["Mon_screen"]
    scr.data.materials[0] = scr.data.materials[0].copy()  # its own material: the screen images go in later
    nt = scr.data.materials[0].node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    em.inputs["Strength"].default_value = 1.5
    # screen glow: a soft blue area light just in front of the screen, facing out of it
    c = scr.matrix_world.translation
    n = (scr.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    glow = bpy.data.objects["Monitor_glow"]
    glow.location = c + n * 0.10
    glow.rotation_euler = n.to_track_quat("-Z", "Y").to_euler()
    glow.data.energy, glow.data.color, glow.data.size = 0.9, (0.55, 0.68, 1.0), 0.40
    # a little light on the monitor itself, from the camera side, so its shape reads
    ld = bpy.data.lights.new("Mon_fill", "AREA")
    ld.energy, ld.size, ld.color = 4.0, 0.35, (1.0, 0.88, 0.75)
    f = bs.link(bpy.data.objects.new("Mon_fill", ld))
    f.location = (0.75, -0.05, 1.35)
    f.rotation_euler = (Vector((0.45, 0.39, 1.0)) - f.location).to_track_quat("-Z", "Y").to_euler()


def face_light():
    """A small, hard-ish key on her face from camera right, so the glasses rims and her fringe cast real shadows."""
    ld = bpy.data.lights.new("Face_key", "SPOT")
    ld.energy, ld.color = 40.0, (1.0, 0.86, 0.72)
    ld.spot_size, ld.spot_blend = radians(20), 0.6   # her head and shoulders, not the desk
    ld.shadow_soft_size = 0.015
    k = bs.link(bpy.data.objects.new("Face_key", ld))
    k.location = (0.25, -0.15, 1.65)   # high and to camera right: rims and fringe throw shadows down onto her cheeks
    k.rotation_euler = (Vector((0.0, 0.50, 1.07)) - k.location).to_track_quat("-Z", "Y").to_euler()
    for n, f in (("Front_fill", 0.6), ("Key_warm", 0.8), ("Lamp_spot", 0.9)):  # some fill back, the face key still makes the shadows
        bpy.data.objects[n].data.energy *= f
    bpy.data.objects["Rim_window"].data.specular_factor = 0.15  # keep its rim on her, lose its glare across the desk top
    # a soft low fill from the front lifts the lower face (it sat in shadow), so her mouth shows; the rims still shade
    ld = bpy.data.lights.new("Chin_fill", "AREA")
    ld.energy, ld.size, ld.color = 2.0, 0.35, (1.0, 0.90, 0.82)
    c = bs.link(bpy.data.objects.new("Chin_fill", ld))
    c.location = (-0.08, -0.10, 0.96)
    c.rotation_euler = (Vector((0.0, 0.50, 1.02)) - c.location).to_track_quat("-Z", "Y").to_euler()
    for n in bpy.data.materials["V3_Cleo_Mouth"].node_tree.nodes:  # redder lips
        if n.type == "BSDF_PRINCIPLED":
            n.inputs["Base Color"].default_value = (0.30, 0.05, 0.06, 1.0)
    room_light()


def room_light():
    """Brighter room: a big soft ceiling fill over the desk and more ambient; the window's rim light turned down."""
    ld = bpy.data.lights.new("Room_fill", "AREA")
    ld.energy, ld.size, ld.color = 60.0, 2.2, (1.0, 0.90, 0.80)
    r = bs.link(bpy.data.objects.new("Room_fill", ld))
    r.location = (0.25, -0.70, 2.35)
    r.rotation_euler = (Vector((0.0, 0.40, 0.95)) - r.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    bpy.data.objects["Rim_window"].data.energy *= 0.55


def outside():
    """The night outside the window, replacing the room's flat backdrop: a deep sky that warms toward the horizon, stars,
    a soft full moon with a halo, two rows of houses (the far row paler, as in haze) with a few lit windows, and dark
    trees between them. All emissive and dim, so it reads as quiet night behind her and never competes with the room."""
    import random
    rnd = random.Random(11)
    for ob in bpy.data.objects:
        if ob.name in ("Sky", "Moon", "MoonBite") or ob.name.startswith(("Roof", "RoofCap", "RoofWin")):
            ob.hide_render = True

    def emit_mat(name, hexcol, strength):
        m = bpy.data.materials.new(name)
        nt = m.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*bs.lin(hexcol), 1)
        em.inputs["Strength"].default_value = strength
        nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        return m

    def plane(name, w, h, m, loc):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, "X"))
        bs.scale_bm(bm, (w, 1, h))
        return bs.mk(name, bm, m, loc)

    # sky: 9 m wide, z -1..5; the warm band sits just above the rooftops (ramp 0.33..0.42 = z 1.0..1.5)
    sky = bs.gradient_mat("NightSky", "Z", 0.0, 1.0, [(0.0, "#2a2350"), (0.33, "#c48ea0"), (0.42, "#7a68a6"), (0.52, "#323e7c"),
                                                      (0.68, "#171e4e"), (1.0, "#0a0d26")],
                          emit_strength=0.8, coords="Generated", pure_emission=True)
    plane("Night_sky", 9.0, 6.0, sky, (-1.5, 7.0, 2.0))
    # stars, sparser and smaller toward the horizon glow
    star_cols = ("#ffffff", "#dfe8ff", "#fff1d0")
    for i in range(140):
        x, z = rnd.uniform(-5.5, 2.5), rnd.uniform(2.0, 4.9)
        if rnd.random() > (z - 1.6) / 2.2:
            continue
        r = rnd.uniform(0.006, 0.013) * (1.6 if rnd.random() < 0.08 else 1.0)
        bs.mk(f"Star{i}", bs.bm_ico(r, 1), emit_mat(f"Star{i}", rnd.choice(star_cols), rnd.uniform(3.0, 9.0)), (x, 6.9, z))
    # moon: a soft full moon with faint markings, and a halo that fades out over 0.9 m
    mm = bpy.data.materials.new("NightMoon")
    nt = mm.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc, nz, ramp, em = (nt.nodes.new(t) for t in ("ShaderNodeTexCoord", "ShaderNodeTexNoise", "ShaderNodeValToRGB", "ShaderNodeEmission"))
    nz.inputs["Scale"].default_value, nz.inputs["Detail"].default_value = 9.0, 3.0
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.42, (*bs.lin("#cfc6b6"), 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.58, (*bs.lin("#fff6e4"), 1)
    em.inputs["Strength"].default_value = 3.2
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    mb = bmesh.new()
    bmesh.ops.create_circle(mb, cap_ends=True, segments=48, radius=0.24)
    bmesh.ops.rotate(mb, verts=mb.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, "X"))
    bs.mk("Night_moon", mb, mm, (-1.62, 6.8, 3.35))
    hm = bpy.data.materials.new("NightHalo")
    hm.surface_render_method = "BLENDED"
    nt = hm.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    tc, mp, gr, pw, tr, em, mix = (nt.nodes.new(t) for t in ("ShaderNodeTexCoord", "ShaderNodeMapping", "ShaderNodeTexGradient",
                                                             "ShaderNodeMath", "ShaderNodeBsdfTransparent", "ShaderNodeEmission", "ShaderNodeMixShader"))
    mp.inputs["Scale"].default_value = (1 / 0.9, 1 / 0.9, 1 / 0.9)
    gr.gradient_type = "SPHERICAL"
    pw.operation, pw.inputs[1].default_value = "POWER", 2.2
    em.inputs["Color"].default_value, em.inputs["Strength"].default_value = (*bs.lin("#c8c4f0"), 1), 0.55
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], gr.inputs["Vector"])
    nt.links.new(gr.outputs["Fac"], pw.inputs[0])
    nt.links.new(pw.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    plane("Night_halo", 1.8, 1.8, hm, (-1.62, 6.85, 3.35))

    def houses(tag, y, xs, base, roof_col, glow, win_lit, win_off, scale):
        wall, roof = emit_mat(f"{tag}_wall", base, glow), emit_mat(f"{tag}_roof", roof_col, glow * 0.8)
        for i, x in enumerate(xs):
            w, h = rnd.uniform(0.55, 0.9) * scale, rnd.uniform(1.0, 1.55) * scale
            d = 0.5 * scale
            bs.mk(f"{tag}{i}", bs.bm_box(w, d, h), wall, (x, y, h / 2))
            pr = bmesh.new()  # gable roof
            rh = rnd.uniform(0.22, 0.34) * scale
            V = [pr.verts.new(q) for q in [(-w / 2 - 0.03, -d / 2 - 0.03, 0), (w / 2 + 0.03, -d / 2 - 0.03, 0), (w / 2 + 0.03, d / 2, 0),
                                           (-w / 2 - 0.03, d / 2, 0), (0, -d / 2 - 0.03, rh), (0, d / 2, rh)]]
            for f in [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4), (0, 3, 2, 1)]:
                pr.faces.new([V[j] for j in f])
            bmesh.ops.recalc_face_normals(pr, faces=pr.faces)
            bs.mk(f"{tag}{i}_roof", pr, roof, (x, y, h))
            if rnd.random() < 0.6:
                bs.mk(f"{tag}{i}_chim", bs.bm_box(0.07 * scale, 0.07 * scale, 0.22 * scale), roof,
                      (x + rnd.choice((-1, 1)) * w * 0.25, y, h + rh * 0.55))
            for r_ in range(2):  # two rows of windows, about half of them lit
                zz = h - (0.28 + 0.38 * r_) * scale
                for c_ in (-1, 1):
                    lit = rnd.random() < 0.5
                    m = win_lit[rnd.randrange(len(win_lit))] if lit else win_off
                    bs.mk(f"{tag}{i}_w{r_}{c_}", bs.bm_box(0.12 * scale, 0.01, 0.15 * scale), m, (x + c_ * w * 0.24, y - d / 2 - 0.006, zz))

    lit = [emit_mat("Win_amber", "#ffbf6e", 6.0), emit_mat("Win_warm", "#ffd59a", 4.5), emit_mat("Win_soft", "#ffb48a", 3.5)]
    off = emit_mat("Win_off", "#1b2148", 0.35)
    houses("FarHouse", 5.3, [-4.6, -3.8, -3.0, -2.3, -1.5, -0.8, -0.1, 0.6], "#323a72", "#2a3066", 0.6, lit, off, 0.9)
    houses("NearHouse", 3.1, [-2.9, -2.05, -1.2, -0.35, 0.45], "#1f2552", "#161a3c", 0.45, lit, off, 1.0)
    tree = emit_mat("Tree", "#141a3a", 0.3)
    for i, (x, z, r) in enumerate([(-2.5, 1.25, 0.32), (-1.62, 1.1, 0.26), (-0.78, 1.3, 0.34), (0.05, 1.15, 0.28)]):
        bm = bs.bm_ico(1.0, 2)
        bs.scale_bm(bm, (r, r * 0.8, r * 1.15))
        bs.mk(f"Tree{i}", bm, tree, (x, 4.2, z), smooth=True)
        bs.mk(f"Tree{i}_trunk", bs.bm_box(0.05, 0.05, z), tree, (x, 4.2, z / 2))


def restyle():
    """Ep 4's own look, so it doesn't feel like a rerun of Ep 3: sunset instead of night, sage-teal walls with cream linen
    curtains and a navy rug, greyer walnut furniture, and Cleo in a mustard hoodie, charcoal jeans and navy sneakers."""
    def col(name, hexcol):
        m = bpy.data.materials.get(name)
        if m is None:
            return
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED" and not n.inputs["Base Color"].is_linked:
                n.inputs["Base Color"].default_value = (*bs.lin(hexcol), 1)
            elif n.type == "EMISSION":
                n.inputs["Color"].default_value = (*bs.lin(hexcol), 1)
        m.diffuse_color = (*bs.lin(hexcol), 1)

    for name, h in {
        # room
        "Sol_6e5266": "#4d6766", "Sol_7a5c6c": "#5b7473",            # walls: plum -> sage teal
        "Sol_c98b93": "#ece2cf",                                     # curtains: dusty rose -> cream linen
        "Sol_b5654a": "#34466e", "Sol_c97a5a": "#45598a",            # rug: rust -> navy
        "Sol_6b4429": "#5e4636", "Desk": "#5e4636",                  # walnut -> cooler, greyer walnut
        "Sol_8fa58a": "#3f4550",                                     # desk mat: sage -> charcoal
        "Lamp": "#e9e2d4", "Sol_a996d1": "#e8c9a0", "Sol_b9a8de": "#efe4d2",  # lamp, blanket, mouse
        "Keyboard": "#2f3440", "PhoneCase": "#7fc4b4", "Sticky": "#f4a6b8", "Sol_d9a441": "#3f8f86",
        # Cleo
        "V3_Cleo_Top": "#e3ad3f", "V3_Cleo_Trim": "#c9952f", "V3_Cleo_Accent": "#4d8f8a",
        "V3_Cleo_Pants": "#2c2f38", "V3_Cleo_PantsCuff": "#3b3f4b",
        "V3_Cleo_Shoe": "#2b3550", "V3_Cleo_Sole": "#f2efe8", "V3_Cleo_Sock": "#e8b64c",
        # outside at sunset: purple silhouettes, the trees darker
        "FarHouse_wall": "#5a3f6e", "FarHouse_roof": "#4a3460", "NearHouse_wall": "#3a2a52", "NearHouse_roof": "#2a1f40",
        "Tree": "#2a1f3e", "Win_off": "#3a2a52",
    }.items():
        col(name, h)
    sky = bpy.data.objects["Night_sky"]
    sky.data.materials[0] = bs.gradient_mat("SunsetSky", "Z", 0.0, 1.0, [
        (0.0, "#ff9a5a"), (0.30, "#ffb46e"), (0.38, "#ff8f6a"), (0.48, "#e0718a"), (0.62, "#9a68a8"), (0.80, "#4a4a8a"),
        (1.0, "#262a62")], emit_strength=1.0, coords="Generated", pure_emission=True)
    for ob in bpy.data.objects:  # no stars or moon before dark
        if ob.name.startswith(("Star", "Night_moon", "Night_halo")):
            ob.hide_render = True
    sun = bmesh.new()
    bmesh.ops.create_circle(sun, cap_ends=True, segments=48, radius=0.34)
    bmesh.ops.rotate(sun, verts=sun.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, "X"))
    bs.mk("Sunset_sun", sun, bs.emissive("SunsetSun", "#ffe2a0", 5.0), (-1.05, 6.8, 1.45))
    # warm low sun through the window: the rim on her turns orange, the room fill a touch cooler to balance
    rim = bpy.data.objects["Rim_window"].data
    rim.color, rim.energy = (1.0, 0.58, 0.32), rim.energy * 1.2
    bpy.data.objects["Room_fill"].data.color = (0.95, 0.93, 0.92)
    bpy.data.objects["Lamp_spot"].data.color = (1.0, 0.62, 0.32)
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (*bs.lin("#2a2238"), 1)


def restyle5():
    """Ep 5's own look over Ep 4's: a bright morning instead of sunset (pale sky, daylit houses, green trees, no sun disc),
    warm sand walls, sage curtains, a teal rug, light oak, and Cleo in a cornflower-blue hoodie (still blue), khaki pants
    and red sneakers."""
    def col(name, hexcol, strength=None):
        m = bpy.data.materials.get(name)
        if m is None:
            print("RESTYLE5 missing", name)
            return
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED" and not n.inputs["Base Color"].is_linked:
                n.inputs["Base Color"].default_value = (*bs.lin(hexcol), 1)
            elif n.type == "EMISSION":
                n.inputs["Color"].default_value = (*bs.lin(hexcol), 1)
                if strength is not None:
                    n.inputs["Strength"].default_value = strength
        m.diffuse_color = (*bs.lin(hexcol), 1)

    for name, h in {
        "Sol_6e5266": "#c9a48f", "Sol_7a5c6c": "#d3b19c",            # walls: sage teal -> warm sand
        "Sol_c98b93": "#9fb39a",                                     # curtains: sage
        "Sol_b5654a": "#2f6f73", "Sol_c97a5a": "#3c8286",            # rug: teal
        "Sol_6b4429": "#7a5a40", "Desk": "#7a5a40",                  # mid oak
        "Sol_8fa58a": "#3b4a3f",                                     # desk mat: deep green
        "Lamp": "#e9e2d4", "Sol_a996d1": "#9fb39a", "Sol_b9a8de": "#f0ede6",
        "Keyboard": "#e8e4dc", "PhoneCase": "#f2c94c", "Sticky": "#9ad0ec", "Sol_d9a441": "#c75b5b",
        "V3_Cleo_Top": "#4f7fd9", "V3_Cleo_Trim": "#3f6bc0", "V3_Cleo_Accent": "#f2efe8",
        "V3_Cleo_Pants": "#d8c7a3", "V3_Cleo_PantsCuff": "#cbb894",
        "V3_Cleo_Shoe": "#d2453a", "V3_Cleo_Sole": "#f4f1ea", "V3_Cleo_Sock": "#f4f1ea",
    }.items():
        col(name, h)
    for name, h, st in (("FarHouse_wall", "#b4c2d2", 0.9), ("FarHouse_roof", "#93a3b8", 0.8), ("NearHouse_wall", "#d8cbb8", 0.8),
                        ("NearHouse_roof", "#8a5a4a", 0.7), ("Tree", "#4f7a4a", 0.7), ("Win_off", "#6a7f96", 0.6),
                        ("Win_amber", "#7d93ab", 0.7), ("Win_warm", "#7d93ab", 0.7), ("Win_soft", "#7d93ab", 0.7)):
        col(name, h, st)
    sky = bpy.data.objects["Night_sky"]
    sky.data.materials[0] = bs.gradient_mat("MorningSky", "Z", 0.0, 1.0, [
        (0.0, "#f6e7c8"), (0.30, "#f3e3c0"), (0.40, "#d6e6f0"), (0.55, "#a9cdea"), (0.75, "#7fb2e0"), (1.0, "#5d97d6")],
        emit_strength=1.0, coords="Generated", pure_emission=True)
    bpy.data.objects["Sunset_sun"].hide_render = True
    rim = bpy.data.objects["Rim_window"].data
    rim.color = (1.0, 0.96, 0.90)
    bpy.data.objects["Room_fill"].data.color = (1.0, 0.98, 0.95)
    ls = bpy.data.objects["Lamp_spot"].data
    ls.color, ls.energy = (1.0, 0.85, 0.65), ls.energy * 0.5
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (*bs.lin("#4a5466"), 1)


def desk_props():
    """A lived-in desk: the pencil cup beside the keyboard, a little succulent and a stack of sticky notes up front,
    her phone face down at the front, off her right hand. All kept clear of Claude's spots and of the camera lines to him."""
    cup = bpy.data.objects["PencilCup"]
    d = Vector((0.40, 0.06, cup.matrix_world.translation.z)) - cup.matrix_world.translation
    for ob in bpy.data.objects:
        if ob.name.startswith(("PencilCup", "Pencil")) and (ob.parent is None or not ob.parent.name.startswith("Pencil")):
            ob.matrix_world = Matrix.Translation(d) @ ob.matrix_world
    pot, soil = bs.mat("Pot", "#c4704f", 0.7), bs.mat("Soil", "#3a2a20", 0.95)
    leaf, sticky = bs.mat("Succulent", "#6fa86a", 0.55), bs.mat("Sticky", "#f2d36b", 0.8)
    phone, cover = bs.mat("PhoneGlass", "#16181d", 0.25, spec=0.6), bs.mat("PhoneCase", "#d98ca0", 0.6)
    x, y = -0.10, -0.11
    bs.mk("Prop_pot", bs.bm_cyl(0.032, 0.055, 20, r2=0.038), pot, (x, y, TOP + 0.0275), smooth=True)
    bs.mk("Prop_soil", bs.bm_cyl(0.034, 0.004, 20), soil, (x, y, TOP + 0.053))
    for i, (dx, dy, r, h) in enumerate(((0, 0, 0.022, 0.030), (0.016, 0.008, 0.015, 0.022), (-0.014, 0.010, 0.014, 0.020),
                                       (0.004, -0.016, 0.014, 0.020), (-0.010, -0.010, 0.012, 0.018))):
        bm = bs.bm_ico(1.0, 2)
        bs.scale_bm(bm, (r, r, h))
        bs.mk(f"Prop_leaf{i}", bm, leaf, (x + dx, y + dy, TOP + 0.058 + 0.4 * h), smooth=True)
    for i in range(4):  # a slightly messy stack of sticky notes
        bs.mk(f"Prop_sticky{i}", bs.bm_box(0.075, 0.075, 0.004), sticky, (0.42 + 0.002 * i, -0.07 - 0.001 * i, TOP + 0.002 + 0.004 * i),
              (0, 0, radians(-8 + 5 * i)))
    # her phone, face up, top toward her side of the desk (the PHONE insert looks down at it from the front)
    # a rounded case, a black glass front with a thin bezel, and the screen inset in it (screen ratio = the 600x1290 images)
    ph = bs.mk("Prop_phone", bs.bm_box(0.074, 0.152, 0.009, bevel=0.004, seg=3), cover, (*PHONE_AT, TOP + 0.005), (0, 0, radians(-12)))
    bs.mk("Prop_phone_front", bs.bm_box(0.066, 0.144, 0.0008, bevel=0.0003, seg=1), phone, (0, 0, 0.0049), parent=ph)
    glass = bpy.data.materials.new("PhoneScreen")
    bs.mk("Prop_phone_screen", bs.bm_box(0.061, 0.131, 0.0004), glass, (0, 0, 0.0055), parent=ph)
    ld = bpy.data.lights.new("Phone_glow", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = 0.0, (0.85, 0.85, 1.0), 0.03
    g = bs.link(bpy.data.objects.new("Phone_glow", ld))
    g.location = (PHONE_AT[0], PHONE_AT[1], TOP + 0.06)


def screen_states(mat, axes, folder, changes, strength):
    """Swap images on a screen over time: one image node per picture, chained through Mix nodes whose factors are
    keyed 0/1 (constant), so exactly one picture shows at a time. Mapped by the object's Generated coordinates
    (axes = which two of X/Y/Z run across and up the screen)."""
    nt = mat.node_tree
    em = next((n for n in nt.nodes if n.type == "EMISSION"), None)
    if em is None:  # a fresh material: pure emission
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    em.inputs["Strength"].default_value = strength
    tc, sep, comb = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs[axes[0]], comb.inputs["X"])
    nt.links.new(sep.outputs[axes[1]], comb.inputs["Y"])
    names = list(dict.fromkeys(n for _, n in changes))
    prev, mix = None, {}
    for nm in names:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(os.path.join(folder, nm + ".png"))
        tex.image.pack()
        tex.interpolation = "Cubic"
        nt.links.new(comb.outputs[0], tex.inputs["Vector"])
        if prev is None:
            prev = tex.outputs["Color"]
            first = nm
            continue
        m = nt.nodes.new("ShaderNodeMix")
        m.data_type = "RGBA"
        nt.links.new(prev, m.inputs[6])
        nt.links.new(tex.outputs["Color"], m.inputs[7])
        prev, mix[nm] = m.outputs[2], m
    nt.links.new(prev, em.inputs["Color"])
    cur = first
    for f, nm in changes:  # the first picture is the base of the chain: all factors 0 shows it
        for when, on in ((f - 1, cur), (f, nm)):  # hold the old picture to the frame before: a clean one-frame switch
            if when < 1:
                continue
            for k, m in mix.items():
                m.inputs[0].default_value = 1.0 if k == on else 0.0
                m.inputs[0].keyframe_insert("default_value", frame=when)
        cur = nm


def reparent(ob, parent, loc=None):
    mw = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse.identity()
    if loc is None:
        bpy.context.view_layer.update()
        ob.matrix_world = mw
    else:
        ob.location = loc


# --------------------------------------------------------------------------- Cleo rig

def seg_closest(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return t, (a + ab * t - p).length


def rig_cleo():
    root, body, head = (bpy.data.objects[N + k] for k in ("", "_body", "_head"))
    hip = bs.empty(N + "_hip", (0, 0.0, 0.58), root)            # lean pivot at the seat
    reparent(body, hip, (0, 0, -0.58))
    neck = bs.empty(N + "_neck", (0, 0.01, 0.99), body)         # head turns and nods from the neck
    hl = head.location.copy()
    reparent(head, neck, hl - Vector((0, 0.01, 0.99)))
    mug = bpy.data.objects[N + "_mug"]
    reparent(mug, root)                                         # the mug stays on the desk when she leans
    bpy.context.view_layer.update()

    # bake the fused, lumpy, faceted sweater so its sleeves can carry vertex weights
    torso = bpy.data.objects[N + "_torso"]
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(torso.evaluated_get(dg))
    torso.modifiers.clear()
    torso.data = me

    ad = bpy.data.armatures.new("CleoArms")
    arm = bs.link(bpy.data.objects.new("CleoRig", ad))
    arm.parent = body
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    chains = {}
    for s, tag in ((-1, "R"), (1, "L")):
        ctrl = mirror(ARM_SIT, s)
        pts, rad = [Vector(p) for p, _ in ctrl], [r for _, r in ctrl]
        up = ad.edit_bones.new("up_" + tag)
        up.head, up.tail = pts[0], pts[2]
        fo = ad.edit_bones.new("fo_" + tag)
        fo.head, fo.tail = pts[2], pts[4]
        fo.parent, fo.use_connect = up, True
        chains[tag] = (s, pts, rad)
    chest = ad.edit_bones.new("chest")  # never posed: holds the rest of each vertex's weight (see below)
    chest.head, chest.tail = Vector((0, 0, 0.75)), Vector((0, 0, 0.9))
    bpy.ops.object.mode_set(mode="OBJECT")

    # weights: sleeve vertices by distance to the arm's centre line, blended across the elbow
    groups = {k: torso.vertex_groups.new(name=k) for k in ("up_R", "fo_R", "up_L", "fo_L")}
    # signed distance to the torso as built before the sleeves were fused on: in the rest pose the hanging arm lies
    # against the body's side, so distance to the arm alone would drag the side of the sweater up with a raised arm
    cbm = bmesh.new()
    cbm.from_mesh(bpy.data.meshes[N + "_torso_core"])
    cbm.normal_update()
    core = BVHTree.FromBMesh(cbm)
    body_d = []
    for v in me.vertices:
        loc, nrm, _, dist = core.find_nearest(v.co)
        body_d.append(dist if (v.co - loc).dot(nrm) >= 0 else -dist)
    cbm.free()
    for tag, (s, pts, rad) in chains.items():
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + (b - a).length)
        a_el = cum[2]
        for v in me.vertices:
            best = None
            for i in range(4):
                t, d = seg_closest(v.co, pts[i], pts[i + 1])
                r = rad[i] + (rad[i + 1] - rad[i]) * t
                e = d - r
                if best is None or e < best[0]:
                    best = (e, cum[i] + t * (cum[i + 1] - cum[i]))
            e, a = best
            w = 1 - ss((e - 0.006) / 0.02)
            w *= ss(a / 0.05)
            w *= ss((body_d[v.index] - e) / 0.016 + 0.5)  # nearer the body's surface than the sleeve's: stays put
            if w <= 0.001:
                continue
            wf = w * ss((a - a_el) / 0.06 + 0.5)
            if w - wf > 0.001:
                groups["up_" + tag].add([v.index], w - wf, "REPLACE")
            if wf > 0.001:
                groups["fo_" + tag].add([v.index], wf, "REPLACE")
    # The armature modifier divides by a vertex's total weight, so a vertex with only a tiny arm weight would follow
    # the arm fully while its neighbour stays put, and the big decimated facets between them stretched into spikes
    # under the arms. Every vertex gets the remainder on the still chest bone, then the weights are smoothed over the
    # mesh so the sweater stretches gradually from sleeve to body.
    names = list(groups)
    nv = len(me.vertices)
    W = {k: [0.0] * nv for k in names}
    for v in me.vertices:
        for g in v.groups:
            W[torso.vertex_groups[g.group].name][v.index] = g.weight
    nbr = [[] for _ in range(nv)]
    for ed in me.edges:
        i, j = ed.vertices
        nbr[i].append(j); nbr[j].append(i)
    for _ in range(10):
        for k in names:
            w0 = W[k]
            W[k] = [0.5 * w0[i] + 0.5 * sum(w0[j] for j in nbr[i]) / len(nbr[i]) if nbr[i] else w0[i] for i in range(nv)]
    groups["chest"] = torso.vertex_groups.new(name="chest")
    for i in range(nv):
        arm_w = sum(W[k][i] for k in names)
        sc = 1.0 / arm_w if arm_w > 1.0 else 1.0
        for k in names:
            groups[k].add([i], W[k][i] * sc, "REPLACE")
        groups["chest"].add([i], max(0.0, 1.0 - arm_w * sc), "REPLACE")
    md = torso.modifiers.new("Arms", "ARMATURE")
    md.object = arm
    cs = torso.modifiers.new("Relax", "CORRECTIVE_SMOOTH")  # evens out what the arms still stretch, keeps the facets
    cs.rest_source, cs.smooth_type, cs.factor, cs.iterations = "ORCO", "LENGTH_WEIGHTED", 1.0, 30
    cs.use_pin_boundary = True
    bpy.context.view_layer.update()

    # hands and cuffs ride on the forearms
    for s, tag in ((-1, "R"), (1, "L")):
        for nm in [f"{N}_palm{s}", f"{N}_thumb{s}", f"{N}_cuff{s}"] + [f"{N}_finger{s}_{k}" for k in range(4)]:
            ob = bpy.data.objects[nm]
            mw = ob.matrix_world.copy()
            ob.parent, ob.parent_type, ob.parent_bone = arm, "BONE", "fo_" + tag
            ob.matrix_parent_inverse.identity()
            bpy.context.view_layer.update()
            ob.matrix_world = mw

    # a wrist joint per hand: palm, fingers and thumb hang on an empty at the forearm's tip (Y runs along the forearm),
    # so the hand can roll palm-down onto the keyboard (it is modelled palm-in, thumb on top, round a mug)
    wrists = {}
    for s, tag in ((-1, "R"), (1, "L")):
        w = bs.link(bpy.data.objects.new(f"{N}_wrist{tag}", None))
        w.parent, w.parent_type, w.parent_bone = arm, "BONE", "fo_" + tag
        w.matrix_parent_inverse.identity()
        w.location = (0, 0, 0)
        bpy.context.view_layer.update()
        for nm in [f"{N}_palm{s}", f"{N}_thumb{s}"] + [f"{N}_finger{s}_{k}" for k in range(4)]:
            ob = bpy.data.objects[nm]
            mw = ob.matrix_world.copy()
            ob.parent, ob.parent_type = w, "OBJECT"
            ob.matrix_parent_inverse.identity()
            bpy.context.view_layer.update()
            ob.matrix_world = mw
        wrists[tag] = w

    # IK: wrist targets live in root space (hands stay put on the desk when she leans); poles behind the elbows
    tg = {}
    for tag, (s, pts, rad) in chains.items():
        sh, el, wr = pts[0], pts[2], pts[4]
        ab = wr - sh
        proj = sh + ab * ((el - sh).dot(ab) / ab.length_squared)
        pole_loc = el + (el - proj).normalized() * 0.3
        pole = bs.empty(f"{N}_pole{tag}", pole_loc, body)
        tgt = bs.empty(f"{N}_tgt{tag}", wr.copy(), root)
        pb = arm.pose.bones["fo_" + tag]
        c = pb.constraints.new("IK")
        c.target, c.pole_target, c.chain_count, c.use_stretch = tgt, pole, 2, False
        best = None  # pick the pole angle whose solved elbow lands on the modelled elbow
        for k in range(72):
            c.pole_angle = -pi + k * pi / 36
            bpy.context.view_layer.update()
            d = (arm.pose.bones["up_" + tag].tail - el).length
            if best is None or d < best[0]:
                best = (d, c.pole_angle)
        c.pole_angle = best[1]
        tg[tag] = tgt
    bpy.context.view_layer.update()
    for tag in ("R", "L"):  # sanity: at rest the solved wrist must sit where the sleeve was modelled
        pb = arm.pose.bones["fo_" + tag]
        print("IKCHECK", tag, "elbow", tuple(round(x, 4) for x in pb.head), "wrist", tuple(round(x, 4) for x in pb.tail))
    return dict(root=root, hip=hip, neck=neck, head=head, arm=arm, tgt=tg, mug=mug, body=body, wrists=wrists)


# --------------------------------------------------------------------------- animation helpers

class Ch:
    """A pose channel: hold the current value, then ease to a new one; keys go in as Bezier (smooth, no noise)."""

    def __init__(self, v0):
        self.v = v0
        self.keys = [(1, v0)]

    def go(self, f, dur, v):
        f = max(f, self.keys[-1][0])
        if f > self.keys[-1][0]:
            self.keys.append((f, self.v))
        self.keys.append((f + max(dur, 1), v))
        self.v = v
        return self

    def at(self, f):
        k = self.keys
        if f <= k[0][0]:
            return k[0][1]
        for (fa, va), (fb, vb) in zip(k, k[1:]):
            if fa <= f <= fb:
                u = ss((f - fa) / max(fb - fa, 1e-6))
                if isinstance(va, (tuple, list, Vector)):
                    return tuple(a + (b - a) * u for a, b in zip(va, vb))
                return va + (vb - va) * u
        return k[-1][1]

    def bake(self, ob, path, fn=lambda v: v):
        for f, v in self.keys:
            setattr(ob, path, fn(v))
            ob.keyframe_insert(path, frame=int(round(f)))


def key(ob, path, f, value):
    setattr(ob, path, value)
    ob.keyframe_insert(path, frame=f)


def claude_open_mouth(name):
    """A dark D-shaped open mouth hung under the painted smile; scaling it in Z from its top edge opens it."""
    body = bpy.data.objects[f"{name}_body"]
    smile = bpy.data.objects[f"{name}_mouth"]
    pivot = bpy.data.objects[f"{name}_pivot"]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    co = [smile.location + v.co for v in smile.data.vertices]
    x0, x1 = min(c.x for c in co), max(c.x for c in co)
    ztop = max(c.z for c in co) - 0.0012
    xc, w, h = (x0 + x1) / 2, (x1 - x0) * 0.82, 0.0105

    def probe(x, z):
        hit, loc, *_ = ev.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        return loc.y if hit else smile.location.y

    bm = bmesh.new()
    nu, nv = 10, 8
    grid = []
    for i in range(nu + 1):
        col = []
        for j in range(nv + 1):
            v = j / nv
            x = xc + (i / nu - 0.5) * w * sqrt(max(0.0, 1 - (v * 0.97) ** 2))
            z = ztop - v * h
            col.append(bm.verts.new((x - xc, probe(x, z) - 0.0009, z - ztop)))
        grid.append(col)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bm.normal_update()
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.0012)
    ob = bs.mk(f"{name}_mouthopen", bm, smile.data.materials[0], (xc, 0, ztop), parent=pivot)
    ob.scale = (1, 1, 0.02)
    return ob


# --------------------------------------------------------------------------- main

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out, tl = args[0], json.load(open(args[1]))
    key_, R, rig0, croot, name, _ = build_room("R6")
    tidy()
    scn = bpy.context.scene
    fps, end = tl["fps"], tl["end"]
    scn.render.fps, scn.frame_start, scn.frame_end = fps, 1, end
    lines = {L["n"]: L for L in tl["lines"]}
    order = [L["n"] for L in tl["lines"]]

    def F(n, u):  # frame at fraction u through line n
        L = lines[n]
        return int(round(L["f0"] + u * (L["f1"] - L["f0"])))

    def G(n, u=0.5):  # frame in the gap before line n
        i = order.index(n)
        a = lines[order[i - 1]]["f1"] if i else 1
        return int(round(a + u * (lines[n]["f0"] - a)))

    # ---------------------------------------------------------------- Claude placement
    croot.location = (HOME.x, HOME.y, TOP)
    pivot = bpy.data.objects[f"{name}_pivot"]
    cmouth = claude_open_mouth(name)
    ceyes = [bpy.data.objects[f"{name}_eye{s}"] for s in (-1, 1)]

    def face(p, target):  # root yaw that turns his front (-Y) toward a point
        return atan2(target[0] - p[0], -(target[1] - p[1]))

    HAND = (-0.06, 0.37)      # her right hand
    HER = (0.0, 0.60)         # her face, seen from the desk
    MON = (0.43, 0.40)
    ev = tl["ev"]

    rg = rig_cleo()
    root, hip, neck, head, arm, mug = rg["root"], rg["hip"], rg["neck"], rg["head"], rg["arm"], rg["mug"]
    mug.hide_render = True    # no mug this time: her hands are on the keyboard
    for ob in mug.children_recursive:
        ob.hide_render = True
    eyes, mouth = rig0["eyes"], rig0["mouth"]
    eye_base = eyes.location.copy()
    brows = rig0["brows"]
    brow_base = [b.location.copy() for b in brows]

    # keyboard right under her hands, square to her
    kb = bpy.data.objects["Keyboard"]
    rl = root.matrix_world.translation
    kb.location = (rl.x, rl.y - 0.33, TOP)
    kb.rotation_euler = (0, 0, 0)

    # screens: monitor and phone pictures over time
    folder = os.path.join(os.path.dirname(os.path.abspath(args[1])), "screens")
    screen_states(bpy.data.objects["Mon_screen"].data.materials[0], ("X", "Z"), folder, tl["mon"], 1.5)
    screen_states(bpy.data.materials["PhoneScreen"], ("X", "Y"), folder, tl["phone"], 1.3)
    glow = bpy.data.objects["Monitor_glow"]
    for i, (f, col, e) in enumerate(tl["glow"]):  # hold each colour to the frame before the next: a clean switch
        key(glow.data, "color", f, col)
        key(glow.data, "energy", f, e)
        if i + 1 < len(tl["glow"]):
            key(glow.data, "color", tl["glow"][i + 1][0] - 1, col)
            key(glow.data, "energy", tl["glow"][i + 1][0] - 1, e)

    pg = bpy.data.objects["Phone_glow"]
    for i, (f, e) in enumerate(tl["pglow"]):
        key(pg.data, "energy", f, e)
        if i + 1 < len(tl["pglow"]):
            key(pg.data, "energy", tl["pglow"][i + 1][0] - 1, e)

    # ---------------------------------------------------------------- cameras
    eye1 = bpy.data.objects[f"{name}_eye1"]
    cz = TOP + 0.065
    scr = bpy.data.objects["Mon_screen"]
    bpy.context.view_layer.update()
    sc = scr.matrix_world.translation.copy()
    sn = (scr.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    phone = bpy.data.objects["Prop_phone"]

    def around(c, ang, dist, z):
        return (c[0] + dist * cos(radians(ang)), c[1] + dist * sin(radians(ang)), z)

    cams = {
        "WIDE": camera("CAM_WIDE", (0.12, -1.10, 1.31), Vector((0.035, 0.40, 0.95)), 29, 5.6, head),
        "TWO": camera("CAM_TWO", (-0.14, -1.02, 1.33), Vector((0.0, 0.40, 1.16)), 29, 5.6, head),
        "CLEO": camera("CAM_CLEO", (-0.03, -0.48, 1.05), Vector((-0.03, 0.55, 0.98)), 40, 2.0, eyes),
        "CLEOCU": camera("CAM_CLEOCU", (-0.09, -0.30, 1.04), Vector((0.0, 0.55, 1.00)), 38, 1.8, eyes),
        "CLAUDE": camera("CAM_CLAUDE", around(HOME, -10, 0.45, cz + 0.06), Vector((HOME.x, HOME.y, cz + 0.01)), 40, 2.8, eye1),
        # the monitor head on, a little above, cropped to the middle of the screen
        "MON": camera("CAM_MON", tuple(sc + sn * 0.56 + Vector((0, 0, 0.025))), sc, 35, 4.0, scr),
        "PHONE": camera("CAM_PHONE", (PHONE_AT[0] - 0.01, PHONE_AT[1] - 0.12, TOP + 0.24),
                        Vector((PHONE_AT[0], PHONE_AT[1] + 0.005, TOP)), 45, 4.0, phone),
    }
    cams["MON"].data.shift_y = -0.07   # closer, and the screen sits a little high so the captions stay under it
    f0 = {n: lines[n]["f0"] for n in order}
    cut_at = {1: f0[1] - 4, 3: f0[3] - 3, 5: f0[5] - 3, 6: ev["imp0"] - 2, 9: f0[9] - 4, 10: G(10, 0.4), 11: f0[11] - 3,
              13: ev["split0"] - 2, 14: f0[14] - 3, 16: f0[16] - 3, 18: f0[18] - 4, 22: f0[22] - 4}
    cuts = [(1, "MON")]                      # open on the stubborn blue button
    for n in order:
        cuts.append((cut_at.get(n, G(n)), SHOT[n]))
    cuts += [(ev["please0"] - 2, "MON"), (ev["cut7"], "CLEOCU"), (ev["ports0"] - 2, "MON"), (ev["url0"] - 2, "MON"),
             (lines[22]["f1"] + 14, "WIDE")]
    cuts.sort()
    prev = None
    for fr_, cam in cuts:
        if cam != prev:
            m = scn.timeline_markers.new(f"{fr_}_{cam}", frame=fr_)
            m.camera = cams[cam]
            prev = cam
    scn.camera = cams["MON"]

    # ---------------------------------------------------------------- Cleo poses (root space wrists)
    R_REST, L_REST = Vector((-0.054, -0.269, 0.795)), Vector((0.054, -0.269, 0.795))
    P = dict(
        r_type=Vector((-0.08, -0.29, 0.80)), l_type=Vector((0.08, -0.29, 0.80)),
        r_open=Vector((-0.11, -0.31, 0.90)), l_open=Vector((0.11, -0.31, 0.90)),
        r_plead=Vector((-0.03, -0.19, 0.92)), l_plead=Vector((0.03, -0.19, 0.92)),
        r_cheek=Vector((-0.075, -0.17, 1.00)), l_cheek=Vector((0.075, -0.17, 1.00)),
        r_shock=Vector((-0.125, -0.33, 0.94)), l_shock=Vector((0.125, -0.33, 0.94)),  # well in front of hair and glasses
        r_chin=Vector((-0.03, -0.18, 0.97)),
        r_jaw=Vector((-0.085, -0.15, 0.965)), l_jaw=Vector((0.085, -0.15, 0.965)),
        r_ask=Vector((-0.15, -0.33, 0.88)),
        r_push=Vector((-0.09, -0.37, 0.80)), l_push=Vector((0.09, -0.37, 0.80)),
    )
    hr, hl = Ch(P["r_type"]), Ch(P["l_type"])
    lean, twist = Ch(0.04), Ch(0.0)
    LOOK = {  # head (pitch, roll, yaw), eyes (dx, dz)
        "claude": ((0.16, 0.0, -0.50), (-0.006, -0.005)),
        "monitor": ((0.10, 0.0, 0.62), (0.007, -0.002)),
        "phone": ((0.38, 0.04, -0.22), (-0.003, -0.008)),
        "keys": ((0.30, 0.0, 0.05), (0.0, -0.007)),
        "down": ((0.28, 0.06, -0.22), (-0.002, -0.007)),
        "palm": ((0.30, 0.0, -0.05), (0.0, -0.007)),
        "slump": ((0.14, 0.05, -0.08), (0.0, -0.008)),
        "up": ((-0.06, -0.05, -0.30), (-0.004, 0.004)),
    }
    hd, ey = Ch(LOOK["monitor"][0]), Ch(LOOK["monitor"][1])
    smile, brow = Ch(0.0), Ch(0.0)

    def look(f, dur, k, head_extra=(0, 0, 0)):
        h, e = LOOK[k]
        hd.go(f, dur, tuple(a + b for a, b in zip(h, head_extra)))
        ey.go(f, max(3, dur // 2), e)

    def both(f, dur, r, l):
        hr.go(f, dur, P[r] if isinstance(r, str) else r)
        hl.go(f, dur, P[l] if isinstance(l, str) else l)

    def typing(f0, f1, step, seed):
        """Real typing: each hand hops between keys across its half of the keyboard (left/right and a row up or down),
        dips onto the key and lifts off; the hands alternate, now and then both at once; her head bobs a little
        as she reads what she types."""
        import random
        rnd = random.Random(seed)
        f = f0
        while f < f1 - step:
            for tag, ch, base, side in (("r", hr, P["r_type"], -1), ("l", hl, P["l_type"], 1)):
                if rnd.random() < 0.65:   # this hand strikes a key this beat
                    dx = side * rnd.uniform(-0.035, 0.045)
                    dy = rnd.uniform(-0.025, 0.02)
                    ch.go(f, 2, base + Vector((dx, dy, 0.028)))       # lift and travel to the key
                    ch.go(f + 2, 2, base + Vector((dx, dy, -0.004)))  # press
            f += step
        for g in range(f0, f1 - 10, 14):  # little nods and turns while reading the screen
            look(g, 6, "monitor", (rnd.uniform(-0.03, 0.05), rnd.uniform(-0.03, 0.03), rnd.uniform(-0.05, 0.05)))

    # opening: she clicks away at the stubborn button, glaring at the screen
    look(1, 1, "monitor")
    hd.keys[0] = (1, LOOK["monitor"][0]); ey.keys[0] = (1, LOOK["monitor"][1]); hd.v, ey.v = LOOK["monitor"][0], LOOK["monitor"][1]
    lean.go(1, 1, 0.10)
    brow.go(1, 1, -0.002)
    typing(4, F(1, 0.0) - 8, 6, 51)
    # 1 Cleo: "Claude. I have made this button green eleven times."  (CLEO) — turns to him, flat and fed up; both hands out on "eleven"
    look(F(1, 0.0) - 4, 10, "claude")
    both(F(1, 0.0) - 2, 10, R_REST, L_REST)
    lean.go(F(1, 0.0), 14, 0.02)
    both(F(1, 0.55), 10, "r_open", "l_open")
    brow.go(F(1, 0.6), 8, 0.007)
    both(F(1, 1.0), 12, R_REST, L_REST)
    # 2 Claude: "And?"  — she stares at him
    brow.go(F(2, 0.5), 8, 0.003)
    # 3 Cleo: "It's blue. It's been blue for forty minutes. It's doing it on purpose."  (CLEO CU) — points at the screen, glares at it
    hr.go(F(3, 0.0), 8, P["r_ask"])
    look(F(3, 0.05), 8, "monitor")
    brow.go(F(3, 0.05), 8, 0.006)
    look(F(3, 0.6), 10, "claude", (0.0, 0.05, 0.0))
    lean.go(F(3, 0.6), 12, -0.03)
    hr.go(F(3, 1.0), 10, R_REST)
    # 4 Claude: "Did you save?"  — offended, leans back
    lean.go(F(4, 0.3), 10, -0.07)
    brow.go(F(4, 0.3), 8, 0.010)
    # 5 Cleo: "I saved! I hard-refreshed! I switched browsers! I put important on everything!"  (CLEO) — each one bigger
    both(F(5, 0.0), 6, "r_open", "l_open")
    lean.go(F(5, 0.0), 8, -0.02)
    both(F(5, 0.22), 6, "r_shock", "l_shock")
    lean.go(F(5, 0.22), 8, 0.02)
    both(F(5, 0.45), 6, "r_open", "l_open")
    both(F(5, 0.66), 6, "r_shock", "l_shock")
    lean.go(F(5, 0.66), 8, 0.06)
    brow.go(F(5, 0.66), 6, 0.012)
    # 6 Claude (over the CSS): "Everything?"  — she nods at the screen
    both(ev["imp0"] + 6, 12, R_REST, L_REST)
    look(ev["imp0"] + 4, 8, "monitor")
    # 7 Cleo: "I even changed the text to PLEASE WORK. Look! It still says Add task! You broke CSS."  (CLEO, inserts, CLEO CU)
    look(F(7, 0.0), 8, "claude")
    both(F(7, 0.02), 8, "r_open", "l_open")
    hr.go(ev["look0"] - 4, 8, P["r_ask"])
    hl.go(ev["look0"] - 4, 8, L_REST)
    look(ev["look0"] - 2, 8, "monitor")
    look(ev["cut7"] - 4, 8, "claude", (0.0, -0.04, 0.0))
    both(ev["cut7"] - 2, 6, "r_shock", "l_shock")
    lean.go(ev["cut7"] - 2, 8, -0.05)
    brow.go(ev["cut7"] - 2, 6, 0.012)
    # 8 Claude: "Let me look at your terminals."  — hands down, she watches him go to the screen
    both(F(8, 0.2), 12, R_REST, L_REST)
    lean.go(F(8, 0.2), 14, 0.04)
    brow.go(F(8, 0.2), 10, 0.004)
    look(F(8, 0.6), 10, "monitor")
    # 9 Cleo: "Wait. Don't judge the folder names."  (CLEO CU) — hands up, a nervous smile
    both(F(9, 0.0) - 3, 6, "r_shock", "l_shock")
    look(F(9, 0.0) - 2, 6, "claude")
    brow.go(F(9, 0.0), 6, 0.011)
    smile.go(F(9, 0.3), 8, 0.35)
    both(F(9, 0.35), 10, "r_plead", "l_plead")
    # 10 Claude reads them out (MON) — she winces at each
    look(G(10, 0.4) + 4, 8, "monitor")
    smile.go(F(10, 0.3), 10, 0.15)
    both(F(10, 0.4), 12, "r_jaw", "l_jaw")
    both(F(10, 0.92), 10, R_REST, L_REST)
    # 11 Cleo: "They're backups!"  (CLEO CU) — defensive, a point
    look(F(11, 0.0) - 3, 6, "claude")
    hr.go(F(11, 0.0) - 2, 6, P["r_ask"])
    hl.go(F(11, 0.0) - 2, 8, L_REST)
    lean.go(F(11, 0.0), 8, -0.04)
    smile.go(F(11, 0.0), 6, 0.45)
    brow.go(F(11, 0.0), 6, 0.008)
    # 12 Claude: "They're all running. Three copies. Three servers."  — the smile goes
    hr.go(F(12, 0.1), 10, R_REST)
    smile.go(F(12, 0.4), 12, 0.0)
    lean.go(F(12, 0.4), 14, 0.03)
    brow.go(F(12, 0.4), 10, 0.003)
    # 13 Claude (MON): "You're editing final. Your browser is showing the original."  — she stares at the screen
    look(ev["split0"], 8, "monitor")
    lean.go(ev["split0"], 14, 0.10)
    # 14 Cleo: "But it says localhost!"  (CLEO CU) — at the screen, then at him
    hr.go(F(14, 0.0) - 2, 6, P["r_ask"])
    look(F(14, 0.0) - 2, 6, "claude", (0.0, 0.05, 0.0))
    lean.go(F(14, 0.0), 8, -0.02)
    brow.go(F(14, 0.0), 6, 0.010)
    # 15 Claude: "Different ports. When 5173 was taken, Vite just took the next one."  — she looks back at the ports
    hr.go(F(15, 0.2), 10, R_REST)
    look(ev["ports0"], 8, "monitor")
    lean.go(ev["ports0"], 14, 0.09)
    brow.go(ev["ports0"], 10, 0.004)
    # 16 Cleo: "So every fix I made went... somewhere else?"  (CLEO CU) — slow; hands to her jaw, eyes down, then to him
    look(F(16, 0.0) - 14, 10, "claude")
    both(F(16, 0.1), 16, "r_jaw", "l_jaw")
    lean.go(F(16, 0.1), 18, 0.06)
    look(F(16, 0.45), 14, "down")
    brow.go(F(16, 0.45), 14, 0.009)
    look(F(16, 0.78), 10, "claude", (0.03, 0.04, 0.0))
    # 17 Claude: "Every single one. Open 5175."  — she turns to the screen as he types it
    both(F(17, 0.3), 12, R_REST, L_REST)
    look(ev["url0"], 8, "monitor")
    lean.go(ev["url0"], 12, 0.10)
    brow.go(ev["url0"], 10, 0.004)
    # the reveal; 18 Cleo: "...Oh no."  (CLEO CU) — hands to her cheeks, she sinks back
    brow.go(ev["reveal"] + 4, 8, 0.013)
    lean.go(ev["reveal"] + 4, 10, 0.02)
    look(F(18, 0.0) - 10, 12, "claude", (0.0, 0.04, 0.0))   # to him, so the face reads
    both(F(18, 0.0) - 8, 12, "r_jaw", "l_jaw")
    lean.go(F(18, 0.1), 16, -0.06)
    # 19 Claude (TWO): "Forty minutes of fixes. They all worked."  — she slumps toward him
    look(F(19, 0.1), 14, "slump")
    both(F(19, 0.2), 14, R_REST, L_REST)
    lean.go(F(19, 0.2), 16, 0.07)
    brow.go(F(19, 0.2), 12, 0.007)
    # 20 Cleo: "Can we go back to blue?"  (CLEO) — small, hopeful, hands together
    look(F(20, 0.0) - 3, 10, "claude", (0.03, 0.05, 0.0))
    both(F(20, 0.0), 12, "r_plead", "l_plead")
    smile.go(F(20, 0.1), 12, 0.3)
    lean.go(F(20, 0.1), 14, 0.03)
    # 21 Claude: "Sure. Which folder?"  — the smile drops
    smile.go(F(21, 0.6), 8, 0.0)
    brow.go(F(21, 0.6), 8, 0.011)
    both(F(21, 0.9), 12, R_REST, L_REST)
    # 22 Cleo: "...I'm calling the next one my-app-final-final."  (CLEO CU) — eyes up, a beat, then a wry grin at him
    look(F(22, 0.0) - 8, 12, "up")
    lean.go(F(22, 0.0) - 6, 14, -0.04)
    brow.go(F(22, 0.0), 10, 0.004)
    look(F(22, 0.35), 12, "claude")
    smile.go(F(22, 0.4), 12, 0.6)
    hr.go(F(22, 0.4), 10, P["r_ask"])
    # tail (WIDE): back to the screen and straight to typing
    look(lines[22]["f1"] + 6, 10, "monitor")
    hr.go(lines[22]["f1"] + 4, 8, P["r_type"])
    hl.go(lines[22]["f1"] + 4, 8, P["l_type"])
    lean.go(lines[22]["f1"] + 4, 12, 0.10)
    smile.go(lines[22]["f1"] + 10, 14, 0.3)
    typing(lines[22]["f1"] + 14, end - 2, 5, 52)

    # ---------------------------------------------------------------- Claude acting
    face_her = face(HOME, HAND) - 0.15           # "to her": toward her hands, cheated toward his close-up camera
    face_mon = face(HOME, MON)
    cpos = Ch((HOME.x, HOME.y))
    cyaw, clean, ctilt, cpuff = Ch(face_her), Ch(0.0), Ch(0.0), Ch(1.0)
    hops = []

    def hop(f, dur, h, to=None):
        hops.append((f, dur, h))
        if to is not None:
            cpos.go(f, dur, tuple(to))

    # opening: watching her click
    cyaw.go(1, 1, face_mon)
    cyaw.keys[0] = (1, face_mon); cyaw.v = face_mon
    # 1: she turns to him; he turns to her
    cyaw.go(F(1, 0.0), 10, face_her)
    ctilt.go(F(1, 0.5), 12, 0.06)
    # 2 "And?" — deadpan tilt
    ctilt.go(F(2, 0.0) - 2, 6, 0.16)
    clean.go(F(2, 0.0) - 2, 6, 0.04)
    # 3: listening
    ctilt.go(F(3, 0.5), 12, 0.04)
    clean.go(F(3, 0.5), 12, 0.0)
    # 4 "Did you save?" — leans in, innocent
    clean.go(F(4, 0.0) - 2, 6, 0.10)
    ctilt.go(F(4, 0.0) - 2, 6, -0.10)
    # 5: leans back from the barrage
    clean.go(F(5, 0.2), 10, -0.08)
    ctilt.go(F(5, 0.2), 10, 0.0)
    # 6 "Everything?" — to the screen
    cyaw.go(ev["imp0"] - 4, 8, face_mon)
    clean.go(ev["imp0"], 8, 0.06)
    # 7: back to her, then the screen with her, then her
    cyaw.go(F(7, 0.0), 10, face_her)
    clean.go(F(7, 0.0), 10, 0.0)
    cyaw.go(ev["look0"], 8, face_mon)
    cyaw.go(ev["cut7"], 8, face_her)
    ctilt.go(ev["cut7"], 10, -0.12)
    # 8 "Let me look at your terminals." — to the screen with a hop
    ctilt.go(F(8, 0.0), 8, 0.0)
    cyaw.go(F(8, 0.3), 8, face_mon)
    hop(F(8, 0.6), 7, 0.014)
    # 9: back to her on "Wait"
    cyaw.go(F(9, 0.0), 6, face_her)
    ctilt.go(F(9, 0.3), 10, 0.10)
    # 10 reads the names off the screen, a little nod at each
    cyaw.go(G(10, 0.3), 8, face_mon)
    ctilt.go(G(10, 0.3), 8, 0.0)
    for f in ev["names"]:
        clean.go(f, 4, 0.09).go(f + 5, 6, 0.0)
    # 11: to her, skeptical tilt
    cyaw.go(F(11, 0.0) - 2, 8, face_her)
    ctilt.go(F(11, 0.3), 10, -0.14)
    # 12 "They're all running. Three copies. Three servers." — firm nods
    ctilt.go(F(12, 0.0), 8, 0.0)
    clean.go(F(12, 0.4), 5, 0.12).go(F(12, 0.55), 6, 0.02).go(F(12, 0.78), 5, 0.12).go(F(12, 0.92), 8, 0.0)
    # 13 (MON) to the screen
    cyaw.go(ev["split0"] - 4, 8, face_mon)
    # 14: back to her
    cyaw.go(F(14, 0.0), 8, face_her)
    ctilt.go(F(14, 0.3), 10, 0.12)
    # 15 "Different ports..." — patient, then the screen
    ctilt.go(F(15, 0.0), 8, 0.04)
    clean.go(F(15, 0.0), 8, 0.06)
    cyaw.go(ev["ports0"] - 4, 8, face_mon)
    # 16: to her, gentle
    cyaw.go(F(16, 0.0), 10, face_her)
    clean.go(F(16, 0.0), 10, 0.02)
    ctilt.go(F(16, 0.5), 12, 0.12)
    # 17 "Every single one. Open 5175." — a slow nod, then to the screen, hops as he types it
    clean.go(F(17, 0.05), 6, 0.12).go(F(17, 0.3), 10, 0.0)
    ctilt.go(F(17, 0.3), 8, 0.0)
    cyaw.go(ev["url0"] - 4, 8, face_mon)
    hop(ev["url1"] - 3, 6, 0.010)
    hop(ev["reveal"] - 3, 6, 0.016)
    # 18: to her
    cyaw.go(F(18, 0.0) - 6, 10, face_her)
    # 19 "Forty minutes of fixes. They all worked." — puffed, proud of her code, a wise nod
    cpuff.go(F(19, 0.0), 8, 1.07)
    clean.go(F(19, 0.6), 8, 0.10).go(F(19, 0.8), 10, 0.0)
    ctilt.go(F(19, 0.6), 10, 0.08)
    # 20: listening
    cpuff.go(F(20, 0.2), 12, 1.0)
    ctilt.go(F(20, 0.3), 12, 0.0)
    # 21 "Sure. Which folder?" — leans in, a slow sly tilt
    clean.go(F(21, 0.0), 8, 0.08)
    ctilt.go(F(21, 0.4), 14, 0.18)
    # 22: listening, then a tiny amused hop at the end
    clean.go(F(22, 0.2), 12, 0.0)
    ctilt.go(F(22, 0.5), 14, 0.06)
    hop(F(22, 0.98), 7, 0.012)
    cyaw.go(lines[22]["f1"] + 10, 12, face_mon)

    # ---------------------------------------------------------------- bake pose channels (Bezier keys at the poses)
    bpy.context.view_layer.update()
    hr.bake(rg["tgt"]["R"], "location", Vector)
    hl.bake(rg["tgt"]["L"], "location", Vector)
    lean.bake(hip, "rotation_euler", lambda v: (v, 0.0, 0.0))
    hd.bake(neck, "rotation_euler", lambda v: v)
    ey.bake(eyes, "location", lambda v: (eye_base.x + v[0], eye_base.y, eye_base.z + v[1]))
    for b, b0 in zip(brows, brow_base):
        brow.bake(b, "location", lambda v, b0=b0: (b0.x, b0.y, b0.z + v))
    cyaw.bake(croot, "rotation_euler", lambda v: (0.0, 0.0, v))
    cock = pivot.rotation_euler.y
    lift = pivot.location.z
    keys_l = sorted(set([k[0] for k in clean.keys] + [k[0] for k in ctilt.keys]))
    for f in keys_l:
        key(pivot, "rotation_euler", int(round(f)), (CK * clean.at(f), cock + CK * ctilt.at(f), 0.0))

    # ---------------------------------------------------------------- per-frame: mouths, blinks, Claude hops & body
    def env(who, f):
        for L in tl["lines"]:
            if L["who"] == who and L["f0"] <= f < L["f0"] + len(L["env"]):
                return L["env"][f - L["f0"]]
        return 0.0

    def slow_env(who, f):
        return sum(env(who, g) for g in range(f - 4, f + 5)) / 9

    blinks = [f for f in range(25, end, 97)] + [F(2, 0.5), F(4, 0.5), F(8, 0.5), F(12, 0.4), F(15, 0.2), F(19, 0.5), F(21, 0.5)]
    cblinks = [f for f in range(40, end, 83)] + [F(3, 0.6), F(9, 0.5), F(16, 0.5), F(20, 0.5)]

    def blink(f, lst, w=2.5):
        return max([1 - abs(f - b) / w for b in lst] + [0.0])

    def hop_state(f):
        """(height, squash) from the hop list: crouch before, stretch in the air, squash on landing."""
        z, sq = 0.0, 0.0
        for f0, dur, h in hops:
            u = (f - f0) / dur
            if 0 <= u <= 1:
                z += CK * h * sin(pi * u)
                sq += CK * 0.10 * sin(pi * u)
            pre = (f0 - f) / 5
            if 0 < pre <= 1:
                sq -= CK * 0.12 * sin(pi * (1 - pre))
            post = (f - f0 - dur) / 7
            if 0 < post <= 1:
                sq -= CK * 0.12 * sin(pi * post)
        return z, sq

    ROLL = radians(75)
    def roll(tag, f):
        ch, base = (hr, P["r_type"]) if tag == "R" else (hl, P["l_type"])
        d = (Vector(ch.at(f)) - base).length
        return ROLL * (1 - ss((d - 0.05) / 0.07))
    for f in range(1, end + 1):
        for tag, side in (("R", -1), ("L", 1)):
            key(rg["wrists"][tag], "rotation_euler", f, (0.0, side * WRIST_SIGN * roll(tag, f), 0.0))

    m0 = mouth.scale.copy()
    m0.x, m0.z = m0.x * 1.5, m0.z * 1.7   # a bigger mouth, so the lips read in every shot
    rest_mw = None
    for f in range(1, end + 1):
        t = f / fps
        # Cleo mouth: smile widens, the envelope opens it
        o = env("cleo", f)
        s = smile.at(f)
        key(mouth, "scale", f, (m0.x * (1 + 0.30 * s - 0.12 * o), m0.y, m0.z * (1 + 2.2 * o - 0.25 * s * (1 - o))))
        b = ss(blink(f, blinks) * 1.6)
        for e in (rig0["eye_l"], rig0["eye_r"]):
            key(e, "scale", f, (1, 1, 1 - 0.9 * b))
        # Claude
        z, sq = hop_state(f)
        x, y = cpos.at(f)
        key(croot, "location", f, (x, y, TOP + z))
        c = slow_env("claude", f)
        breath = CK * 0.012 * sin(2 * pi * t / 2.6)
        pf = 1 + CK * (cpuff.at(f) - 1)
        key(pivot, "scale", f, (pf * (1 - 0.5 * sq), pf, pf * (1 + sq + breath + CK * 0.035 * c)))
        key(cmouth, "scale", f, (1, 1, 0.02 + 0.98 * env("claude", f)))
        cb = ss(blink(f, cblinks, 3.0 if f in cblinks else 2.5) * 1.6)
        for e in ceyes:
            key(e, "scale", f, (1, 1, 1 - 0.85 * cb))

    scn.frame_set(1)

    bs.render_settings(scn)
    ee = scn.eevee
    ee.use_raytracing = False
    ee.use_bokeh_jittered = False
    ee.shadow_ray_count, ee.shadow_step_count = 1, 4
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out, "end", end)


main()
