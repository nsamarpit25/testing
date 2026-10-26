"""Room layout variants: the film set rebuilt with the monitor, Claude (D2 Bubble), Cleo and the backdrop moved around.

blender -b --factory-startup -P rooms.py -- <out.blend> <R1|R2|R3|R4>
"""
import bpy, bmesh, os, sys
from math import pi, sin, cos, atan2
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_scene as bs  # noqa: E402
from build_scene import mk, bm_box, bm_cyl, bm_tube, ellipsoid, emissive, mat, empty, CLEO_Y  # noqa: E402
from lineup import camera  # noqa: E402
from mascots import SHAPE_OPTS, build_claude  # noqa: E402

WY = 1.25  # back wall plane

ROOMS = {
    # the film's sunset, moodier: monitor turned in toward her from the right, Claude front-left by the mug
    "R1_Sunset": dict(
        girl_x=0.0, mon=((0.52, 0.36), -2.05), claude=(-0.15, 0.06), lamp=(-0.64, 0.36), books=(-0.5, -0.02),
        plant=(-0.34, 0.47),
        sky=[(0.0, "#ffc27a"), (0.22, "#ff8a6b"), (0.45, "#e2678f"), (0.7, "#7d4a9e"), (1.0, "#231f4a")], sky_emit=1.8,
        sun=((-1.6, 0.9), 1.7, "#ffc98a", 4.0),
        wall="#5d4a5c", desk="#5a3a28",
        lights={"Key_warm": ("#ffb98a", 30), "Rim_window": ("#ff9a8a", 90), "Rim_window_L": ("#ffb07a", 45),
                "Front_fill": ("#ffd6b8", 4), "Monitor_glow": ("#8fb2ff", 14)},
        world=("#1d1830", 0.5)),
    # deep night: big moon, warm lamp as key, she sits left, monitor centre-right glowing back at her, Claude right of keys
    "R2_Night": dict(
        girl_x=-0.16, mon=((0.36, 0.44), -2.55), claude=(0.17, 0.04), lamp=(-0.66, 0.3), books=(0.5, 0.02),
        plant=(0.68, 0.42),
        sky=[(0.0, "#3a4a8a"), (0.35, "#22306a"), (0.7, "#141a42"), (1.0, "#0a0c22")], sky_emit=1.2,
        moon=((2.4, 5.2), 0.55, "#f3f1ff", 9.0),
        wall="#3e4058", desk="#4a3326", fairy=True,
        lights={"Key_warm": ("#ffb070", 16), "Rim_window": ("#8aa8ff", 70), "Rim_window_L": ("#9a8cff", 30),
                "Front_fill": ("#c8d4ff", 3), "Monitor_glow": ("#7fa8ff", 22)},
        lamp_energy=55, world=("#0f1226", 0.6)),
    # no window: a cosy wall of shelves, posters and an orange spark neon; monitor at left turned to her, Claude right
    "R3_Cozy": dict(
        girl_x=0.0, mon=((-0.5, 0.36), 2.05), claude=(0.15, 0.05), lamp=(0.64, 0.36), books=(0.52, 0.0),
        plant=(0.36, 0.47), cozy=True,
        wall="#3f5a5a", desk="#6e4a33",
        lights={"Key_warm": ("#ffc49a", 28), "Rim_window": ("#ff9a5a", 40), "Rim_window_L": ("#ffb58a", 25),
                "Front_fill": ("#ffe0c4", 5), "Monitor_glow": ("#8fb2ff", 14)},
        world=("#1a1c24", 0.5)),
    # blue hour, off-centre: she sits right, monitor centre-left facing her, Claude on a book stack front-left
    "R4_BlueHour": dict(
        girl_x=0.17, mon=((-0.5, 0.4), 2.2), claude=(-0.15, 0.0), on_books=True, lamp=(0.68, 0.34),
        books=(-0.15, 0.0), plant=(-0.66, 0.42),
        sky=[(0.0, "#ffb38a"), (0.12, "#e8a0a8"), (0.35, "#6fa0c8"), (0.7, "#2c5a8c"), (1.0, "#14254a")], sky_emit=1.6,
        wall="#4a5568", desk="#6a4630",
        lights={"Key_warm": ("#ffcfa8", 26), "Rim_window": ("#8fd0ff", 80), "Rim_window_L": ("#ffb8a0", 30),
                "Front_fill": ("#e0ecff", 4), "Monitor_glow": ("#9ac0ff", 20)},
        world=("#16203a", 0.6)),
    # Codex's pick: blue-hour attic, Cleo right of centre, Claude front-left in the lamp pool, monitor frame-right
    "R5_Codex": dict(
        girl_x=0.12, mon=((0.62, 0.34), -2.11), claude=(-0.30, 0.02), lamp=(-0.70, 0.37), books=(-0.66, -0.02),
        plant=None, codex=True,
        sky=[(0.0, "#ffc7a0"), (0.3, "#f2b0b0"), (0.6, "#c4a0d8"), (1.0, "#4a4a8a")], sky_emit=1.5,
        wall="#6e5266", desk="#6b4429", city="#1f2547",
        lights={"Key_warm": ("#ffc08a", 26), "Rim_window": ("#c9a8ff", 75), "Rim_window_L": ("#d8b0ff", 30),
                "Front_fill": ("#ffe0c4", 4), "Monitor_glow": ("#8fb2ff", 16)},
        lamp_energy=75, world=("#1d1a2e", 0.55)),
    # Codex gpt-6.1-sol: a lived-in evening study; Claude front-left turned to Cleo, bookcase with rocket + orb behind him
    "R6_Sol": dict(
        girl_x=0.0, kb=(0.16, 0.15), mon=((0.43, 0.40), -2.08), claude=(-0.43, 0.12), claude_face=(0.0, 0.45),
        lamp=(-0.70, 0.34), books=(-0.62, -0.08), plant=None, sol=True,
        wall="#6e5266", desk="#6b4429", lights={"Monitor_glow": ("#8fb2ff", 14)}, lamp_energy=70,
        world=("#1d1a2e", 0.45)),
}


def shift(names, d):
    for ob in bpy.data.objects:
        if ob.parent is None and any(ob.name.startswith(n) for n in names):
            ob.location += Vector(d)


def recolor(name, hexcol):
    m = bpy.data.materials[name]
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*bs.lin(hexcol), 1)


def disc(name, c, r, col, strength, seg=40):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=seg, radius=r)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(pi / 2, 3, "X"))
    mk(name, bm, emissive(name, col, strength), c)


def star_pts(c, R, r, n=8, rot=0.0):
    pts = []
    for i in range(2 * n):
        a = rot + pi * i / n
        rad = R if i % 2 == 0 else r
        pts.append((c[0] + rad * cos(a), c[1], c[2] + rad * sin(a)))
    return pts


def cozy_wall(M):
    """Fill the window: shelves of books and plants, two posters, a glowing orange spark neon."""
    for n in ("Frame_", "Mullion_", "Sky", "Bldg", "City_windows", "Fairy", "Cactus", "Sill"):
        for ob in [o for o in bpy.data.objects if o.name.startswith(n)]:
            bpy.data.objects.remove(ob)
    mk("Wall_fill", bm_box(1.9, 0.1, 1.35), M["wall"], (0, WY, 1.625))
    wood = mat("Shelf", "#7a5236", 0.5)
    cols = ["#3d5a80", "#e0b04c", "#9a4c4c", "#6b8f71", "#d98a5a", "#5b4a7a", "#e8dcc8"]
    k = 0
    for sx, sz, w in [(-0.62, 1.32, 0.6), (-0.62, 1.68, 0.6), (0.66, 1.42, 0.55)]:
        mk("Shelf", bm_box(w, 0.2, 0.03, 0.004), wood, (sx, WY - 0.15, sz))
        x = sx - w / 2 + 0.04
        while x < sx + w / 2 - 0.12:
            k += 1
            if k % 7 == 3:  # a little pot plant between the books
                mk("ShelfPot", bm_cyl(0.035, 0.06, 8, 0.028), M["pot"], (x + 0.04, WY - 0.15, sz + 0.045))
                ellipsoid("ShelfLeaf", (0.045, 0.035, 0.05), M["plant"], (x + 0.04, WY - 0.15, sz + 0.1), sub=1, jit=0.004)
                x += 0.1
                continue
            bw, bh = 0.022 + (k * 7 % 5) * 0.005, 0.15 + (k * 3 % 4) * 0.025
            lean = 0.18 if k % 9 == 5 else 0.0
            mk("ShelfBook", bm_box(bw, 0.14, bh, 0.002), mat(f"SB{k}", cols[k % len(cols)], 0.7),
               (x + bw / 2, WY - 0.15, sz + 0.015 + bh / 2), (0, lean, 0))
            x += bw + 0.004
    # posters: a sunset print and a code-y print, framed
    for name, c, size, top, bot in [("PosterA", (-0.05, 1.95), (0.36, 0.48), "#ffb07a", "#7d4a9e"),
                                    ("PosterB", (0.4, 1.9), (0.26, 0.34), "#9fd2ff", "#3d5a80")]:
        mk(f"{name}_frame", bm_box(size[0] + 0.03, 0.02, size[1] + 0.03, 0.003), M["frame"], (c[0], WY - 0.055, c[1]))
        art = bs.gradient_mat(name, "Z", -size[1] / 2, size[1] / 2, [(0.0, bot), (1.0, top)], emit_strength=0.25, rough=0.8)
        mk(name, bm_box(size[0], 0.004, size[1]), art, (c[0], WY - 0.067, c[1]))
    disc("PosterA_sun", (-0.05, WY - 0.071, 1.9), 0.07, "#ffe2a8", 1.2)
    # the neon: an 8-point spark outline above the girl's head, with its own light
    neon = emissive("Neon", "#ff7a3d", 18.0)
    mk("Neon_spark", bm_tube(star_pts((-0.62, WY - 0.08, 2.05), 0.16, 0.07, 8, pi / 16), 0.007, 6, True, (0, 1, 0)), neon)
    pt = bpy.data.lights.new("Neon_glow", "POINT")
    pt.color, pt.energy, pt.shadow_soft_size = bs.lin("#ff7a3d"), 25, 0.15
    ob = bs.link(bpy.data.objects.new("Neon_glow", pt))
    ob.location = (-0.62, WY - 0.25, 2.05)
    # string lights draped over the right shelf
    pts = [(0.35 + 0.65 * i / 20, WY - 0.1, 1.8 - 0.08 * sin(pi * i / 20)) for i in range(21)]
    mk("Shelf_wire", bm_tube(pts, 0.002, 4), M["wire"])
    for i in range(1, 9):
        u = i / 9
        ellipsoid(f"ShelfFairy{i}", (0.01, 0.01, 0.012), M["fairy"],
                  (0.35 + 0.65 * u, WY - 0.105, 1.8 - 0.08 * sin(pi * u) - 0.015), sub=1)


def codex_room(M, R):
    """Codex's layout: smaller window off to the left (x -0.75..0.35, z 0.96..2.05), navy rooftops with three lit
    windows, one shelf with books and a trailing plant, a PC tower under the desk, a mouse, chunkier legs."""
    for n in ("Wall_L", "Wall_R", "Wall_B", "Wall_T", "Frame_", "Mullion_", "Sill", "Cactus", "Fairy", "Bldg", "City_windows",
              "Plant_pot", "Leaf", "Note_b", "Book2"):
        for ob in [o for o in bpy.data.objects if o.name.startswith(n)]:
            bpy.data.objects.remove(ob)
    x0, x1, z0, z1 = -0.75, 0.35, 0.96, 2.05
    for name, c, sz in [("Wall_L", ((x0 - 1.85) / 2, WY, 1.6), (x0 + 1.85, 0.1, 3.2)),
                        ("Wall_R", ((x1 + 1.85) / 2, WY, 1.6), (1.85 - x1, 0.1, 3.2)),
                        ("Wall_B", ((x0 + x1) / 2, WY, z0 / 2), (x1 - x0, 0.1, z0)),
                        ("Wall_T", ((x0 + x1) / 2, WY, (z1 + 3.2) / 2), (x1 - x0, 0.1, 3.2 - z1))]:
        mk(name, bm_box(*sz), M["wall"], c)
    fr, xc, zc = 0.045, (x0 + x1) / 2, (z0 + z1) / 2
    for name, c, sz in [("Frame_L", (x0 + fr / 2, WY - 0.02, zc), (fr, 0.08, z1 - z0)),
                        ("Frame_R", (x1 - fr / 2, WY - 0.02, zc), (fr, 0.08, z1 - z0)),
                        ("Frame_T", (xc, WY - 0.02, z1 - fr / 2), (x1 - x0, 0.08, fr)),
                        ("Mullion_V", (xc, WY - 0.01, zc), (0.032, 0.05, z1 - z0)),
                        ("Mullion_H", (xc, WY - 0.01, zc + 0.05), (x1 - x0, 0.05, 0.032))]:
        mk(name, bm_box(*sz), M["frame"], c)
    mk("Sill", bm_box(x1 - x0 + 0.12, 0.22, 0.04, 0.006), M["sill"], (xc, WY - 0.07, z0 - 0.02))
    # rooftops: a few navy blocks with pitched caps, three warm windows
    roof = mat("Roofs", R["city"], 0.9, emit=R["city"], strength=0.5)
    lit = emissive("RoofWin", "#ffcf8a", 9.0)
    for i, (x, w, h, y) in enumerate([(-2.6, 1.6, 0.7, 5.0), (-1.0, 1.3, 1.25, 4.2), (0.5, 1.5, 0.85, 4.6),
                                      (1.9, 1.2, 1.4, 5.4), (-0.2, 1.0, 0.45, 6.5)]):
        mk(f"Roof{i}", bm_box(w, 1.0, h + 4), roof, (x, y, h / 2 - 2))
        cap = bm_box(w * 0.98, 1.0, 0.001)
        for v in cap.verts:  # pitch: lift the centre line
            if abs(v.co.x) < 1e-6:
                pass
        mk(f"RoofCap{i}", bmesh_prism(w, 1.0, 0.35), roof, (x, y, h))
    for i, (x, z, y) in enumerate([(-1.3, 1.05, 4.2 - 0.51), (-0.85, 1.05, 4.2 - 0.51), (-1.3, 0.75, 4.2 - 0.51)]):
        mk(f"RoofWin{i}", bm_box(0.16, 0.01, 0.2), lit, (x, y, z))
    # one shelf: three uneven books and a trailing plant
    wood = mat("Shelf", "#7a5236", 0.5)
    mk("Shelf", bm_box(0.5, 0.18, 0.025, 0.004), wood, (0.67, WY - 0.14, 1.65))
    for k, (bw, bh, col, lean) in enumerate([(0.035, 0.2, "#3d5a80", 0.0), (0.03, 0.17, "#e0b04c", 0.0),
                                             (0.04, 0.15, "#9a4c4c", -0.25)]):
        mk(f"ShelfBook{k}", bm_box(bw, 0.13, bh, 0.002), mat(f"SB{k}", col, 0.7),
           (0.47 + k * 0.045 + (0.012 if lean else 0), WY - 0.14, 1.6625 + bh / 2 - (0.01 if lean else 0)), (0, lean, 0))
    mk("ShelfPot", bm_cyl(0.045, 0.075, 8, 0.036), M["pot"], (0.8, WY - 0.14, 1.7))
    for i in range(7):  # trailing vine down the front of the shelf
        a = -0.6 + 0.2 * i
        ellipsoid(f"Vine{i}", (0.02, 0.008, 0.035), M["plant"], (0.8 + 0.06 * sin(a * 3), WY - 0.2, 1.66 - 0.05 * i),
                  (0.2, 0.5 * sin(i), 0), sub=1)
    # PC tower under the right of the desk, amber status light; a mouse; chunkier walnut legs
    mk("PC_tower", bm_box(0.2, 0.42, 0.44, 0.012), mat("PCCase", "#2a2a30", 0.45), (0.65, 0.35, 0.22))
    mk("PC_led", bm_box(0.012, 0.004, 0.012), emissive("PCLed", "#ffb04a", 8.0), (0.65, 0.138, 0.4))
    mk("PC_vent", bm_box(0.14, 0.004, 0.12), mat("PCVent", "#1a1a1f", 0.6), (0.65, 0.139, 0.12))
    mk("Mouse", bm_box(0.055, 0.09, 0.028, 0.012), M["kb"], (0.43, 0.22, 0.774))
    for ob in [o for o in bpy.data.objects if o.name.startswith("Desk_leg")]:
        ob.scale = (1.8, 1.8, 1)
    bpy.data.objects["Note_a"].location = (0.38, 0.05, 0.7615)
    recolor("Keyboard", "#5a3f5e")
    recolor("Claude", "#b9a8de")  # mug band: lavender stripe


def bmesh_prism(w, d, h):
    bm = bmesh.new()
    a, b, c, e = (-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0)
    t0, t1 = (0, -d / 2, h), (0, d / 2, h)
    V = [bm.verts.new(p) for p in (a, b, c, e, t0, t1)]
    for f in [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4), (0, 3, 2, 1)]:
        bm.faces.new([V[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def side_walls(M, R):
    """Dress the bare wall either side of the window: a framed print and a floating shelf, a floor plant, a rug."""
    wood = mat("SideShelf", "#7a5236", 0.5)
    pa, pb = R.get("prints", ("#ffb07a", "#7d4a9e"))
    mk("Print_frame", bm_box(0.42, 0.02, 0.56, 0.003), M["frame"], (-1.38, WY - 0.055, 1.62))
    mk("Print", bm_box(0.36, 0.004, 0.5), bs.gradient_mat("PrintArt", "Z", -0.25, 0.25, [(0.0, pb), (1.0, pa)],
                                                         emit_strength=0.15, rough=0.8), (-1.38, WY - 0.067, 1.62))
    disc("Print_sun", (-1.38, WY - 0.071, 1.56), 0.06, "#ffe2a8", 0.8)
    mk("Print2_frame", bm_box(0.26, 0.02, 0.32, 0.003), M["frame"], (-1.2, WY - 0.055, 1.12))
    mk("Print2", bm_box(0.21, 0.004, 0.27), mat("Print2Art", "#e8dcc8", 0.8), (-1.2, WY - 0.067, 1.12))
    mk("Print2_spark", bm_tube(star_pts((-1.2, WY - 0.072, 1.12), 0.07, 0.03, 8, pi / 16), 0.006, 5, True, (0, 1, 0)),
       M["claude"])
    cols = ["#3d5a80", "#e0b04c", "#9a4c4c", "#6b8f71", "#d98a5a", "#5b4a7a"]
    for j, sz in enumerate((1.25, 1.62)):
        mk("SideShelf", bm_box(0.5, 0.18, 0.025, 0.004), wood, (1.36, WY - 0.14, sz))
        x = 1.15
        for k in range(9 - 3 * j):
            bw, bh = 0.024 + (k * 7 % 4) * 0.005, 0.14 + (k * 5 % 3) * 0.025
            mk("SideBook", bm_box(bw, 0.13, bh, 0.002), mat(f"SdB{j}{k}", cols[(k + j) % 6], 0.7),
               (x + bw / 2, WY - 0.14, sz + 0.0125 + bh / 2))
            x += bw + 0.004
    mk("SideShelfPot", bm_cyl(0.04, 0.07, 8, 0.032), M["pot"], (1.52, WY - 0.14, 1.668))
    for i in range(6):
        a = 2 * pi * i / 6
        ellipsoid(f"SideVine{i}", (0.015, 0.008, 0.06 + 0.03 * (i % 2)), M["plant"],
                  (1.52 + 0.03 * cos(a), WY - 0.14 + 0.02 * sin(a), 1.68 - 0.02), (pi - 0.5 * sin(a), 0.5 * cos(a), 0), sub=1)
    # tall floor plant in the corner and a rug under the chair
    mk("FloorPot", bm_cyl(0.13, 0.32, 10, 0.1), M["pot"], (-1.05, 1.0, 0.16))
    for i in range(9):
        a = 2 * pi * i / 9 + 0.2
        ellipsoid(f"FloorLeaf{i}", (0.05, 0.015, 0.28 + 0.06 * (i % 3)), M["plant"],
                  (-1.05 + 0.06 * cos(a), 1.0 + 0.06 * sin(a), 0.55 + 0.04 * (i % 3)), (0.5 * sin(a), -0.5 * cos(a), 0), sub=1)
    rug = mat("Rug", R.get("rug", "#6b4f7a"), 0.95)
    mk("Rug", bm_cyl(0.85, 0.008, 28), rug, (R["girl_x"], 0.55, 0.004))
    mk("Rug_ring", bm_tube(bs.ring_pts((R["girl_x"], 0.55, 0.009), 0.74, (0, 0, 1), 48), 0.012, 6, True, (0, 0, 1)),
       mat("RugRing", "#e8c9a0", 0.9))


def apply(R, M):
    gx = R["girl_x"]
    # sink the skyline so the sky reads through the window, and lift the silhouettes off pure black
    if not R.get("codex"):
        shift(("Bldg0_", "City_windows"), (0, 0, -1.5))
    shift(("Bldg1_",), (0, 0, -0.7))
    recolor("CityNear", R.get("city", "#2a2340"))
    cn = bpy.data.materials["CityNear"].node_tree.nodes["Principled BSDF"]
    cn.inputs["Emission Color"].default_value = (*bs.lin(R.get("city", "#2a2340")), 1)
    cn.inputs["Emission Strength"].default_value = 0.6
    for sx in (-1.8, 1.8):  # side walls close the room for the 3/4 views
        mk("Wall_side", bm_box(0.1, 3.4, 3.2), M["wall"], (sx, WY - 1.7, 1.6))
    shift(("V3_Cleo", "Chair_"), (gx, 0, 0))
    bpy.data.objects["Keyboard"].location.x = gx + 0.02
    if "kb" in R:
        bpy.data.objects["Keyboard"].location.x, bpy.data.objects["Keyboard"].location.y = R["kb"]
    # monitor: turned so its screen faces the given way (local -Y), its glow light in front of the screen
    (mx, my), rz = R["mon"]
    mon = bpy.data.objects["Monitor"]
    mon.location.x, mon.location.y, mon.rotation_euler.z = mx, my, rz
    nrm = Vector((sin(rz), -cos(rz), 0))
    glow = bpy.data.objects["Monitor_glow"]
    glow.location = Vector((mx, my, 1.03)) + nrm * 0.12
    bs.aim(glow, (gx, CLEO_Y, 1.1))
    # lamp and its spot follow
    lx, ly = R["lamp"]
    lamp = bpy.data.objects["Lamp"]
    s = 1 if lx < 0 else -1  # mirror the arm so the head leans in toward the desk centre
    lamp.location.x, lamp.location.y = lx, ly
    lamp.scale.x = s
    spot = bpy.data.objects["Lamp_spot"]
    spot.location = (lx + s * 0.15, ly - 0.14, 1.1)
    bs.aim(spot, (lx + s * 0.32, ly - 0.3, 0.76))
    if "lamp_energy" in R:
        spot.data.energy = R["lamp_energy"]
    bx, by = R["books"]
    for i in range(3):
        b = bpy.data.objects[f"Book{i}" if i else "Book0"]
        b.location.x, b.location.y = bx + 0.01 * i, by - 0.005 * i
    if R["plant"]:
        px, py = R["plant"]
        shift(("Plant_pot", "Leaf"), (px + 0.36, py - 0.44, 0))
    if R["mon"][0][0] < 0:  # sticky notes go by the monitor
        shift(("Note_",), (-0.9, 0.0, 0))
    # backdrop
    if R.get("cozy"):
        cozy_wall(M)
    if R.get("sol"):
        from room_sol import sol_room
        sol_room(M, R)
    elif R.get("codex"):
        codex_room(M, R)
    else:
        side_walls(M, R)
    if "sky" in R:
        bpy.data.objects["Sky"].data.materials[0] = bs.gradient_mat(
            "SkyR", "Z", 0.0, 1.0, R["sky"], emit_strength=R["sky_emit"], coords="Generated", pure_emission=True)
    if "sun" in R:
        (sx, sz), r, col, e = R["sun"]
        disc("Sun", (sx, 17.9, sz), r, col, e)
    if "moon" in R:
        (sx, sz), r, col, e = R["moon"]
        disc("Moon", (sx, 17.9, sz), r, col, e)
    recolor("Wall", R["wall"])
    recolor("Desk", R["desk"])
    for name, (col, e) in R["lights"].items():
        L = bpy.data.objects[name].data
        L.color, L.energy = bs.lin(col), e
    w = bpy.context.scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (*bs.lin(R["world"][0]), 1)
    w.inputs["Strength"].default_value = R["world"][1]


def build_room(pick, tests=None):
    """Build the set, Cleo and Claude for one room variant; returns (key, R, claude_root, claude_name, (cx, cy, cz))."""
    if tests:  # sweater test: soft = gentle lumps, bigger even facets; smooth = no facets at all
        from girls import VARIANTS
        cleo = next(c for c in VARIANTS if c["name"] == "V3_Cleo")
        opts = {"soft": dict(sweater_lumps=0.008, lump_size=0.07, sweater_facets=0.4),
                 "smooth": dict(sweater_lumps=0.006, lump_size=0.08, sweater_facets=None),
                 "h1": dict(hair_front=0.17, frame_hang=0.13), "h2": dict(hair_front=0.23, frame_hang=0.19)}
        for t in tests.split(","):  # e.g. soft,h1
            cleo.update(opts[t])
    key = next(k for k in ROOMS if k.startswith(pick))
    R = ROOMS[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    M = bs.materials()
    bs.build_world()
    bs.build_set(M)
    rig = bs.build_cleo(M)
    bs.build_lights()
    apply(R, M)
    cx, cy = R["claude"]
    cz = 0.76
    if R.get("on_books"):
        cz = 0.76 + 0.03 * 2 + 0.022
    name, fn = next(e for e in SHAPE_OPTS if e[0].startswith("D2"))
    croot = build_claude(name, fn, (cx, cy, cz))
    k = croot.scale.z
    if "claude_face" in R:  # turn him to face Cleo (his front is local -Y)
        fx, fy = R["claude_face"]
        from math import atan2
        croot.rotation_euler.z = atan2(fx - cx, -(fy - cy))
    bpy.context.view_layer.update()
    return key, R, rig, croot, name, (cx, cy, cz)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out, pick = args[0], args[1]
    key, R, _, croot, name, (cx, cy, cz) = build_room(pick, args[2] if len(args) > 2 else None)
    scn = bpy.context.scene
    k = croot.scale.z
    eye = bpy.data.objects[f"{name}_eye1"]
    head = bpy.data.objects["V3_Cleo_head"]
    hz = head.matrix_world.translation
    gx = R["girl_x"]
    p = key.split("_")[0]
    camera(f"CAM_{p}_wide_group", (0.0, -1.9, 1.3), Vector((0.0, 0.4, 1.05)), 24, 11.0, head)
    camera(f"CAM_{p}_34_group", (-1.15, -1.0, 1.4), Vector((0.05, 0.45, 0.98)), 24, 11.0, head)
    camera(f"CAM_{p}_34r_group", (1.15, -1.0, 1.35), Vector((-0.05, 0.45, 0.98)), 24, 11.0, head)
    mx = (cx + hz.x) / 2  # frame Claude and her together
    camera(f"CAM_{p}_overshoulder", (mx + 0.6 * (cx - mx), cy - 0.66, cz + 0.27), Vector((mx, cy + 0.2, cz + 0.13)), 32, 4.0, eye)
    camera(f"CAM_{p}_girl", (hz.x + 0.12, hz.y - 1.15, hz.z + 0.0), Vector((hz.x, hz.y, hz.z - 0.17)), 45, 2.8, head)
    if R.get("codex"):  # Codex's main vertical: her face in the upper third, Claude lower-left, mug between
        camera(f"CAM_{p}_main", (-0.14, -1.05, 1.26), Vector((-0.08, 0.3, 0.97)), 30, 5.6, head)
        camera(f"CAM_{p}_insert", (0.02, -0.12, 1.06), Vector((0.42, 0.4, 0.95)), 32, 5.6, bpy.data.objects["Monitor"])
    if R.get("sol"):  # Codex's vertical cameras
        camera(f"CAM_{p}_vwide", (0.95, -1.30, 1.48), Vector((-0.10, 0.30, 1.05)), 26, 8.0, head)
        camera(f"CAM_{p}_vclaude", (cx + 0.58, cy - 0.16, cz + 0.12), Vector((cx, cy, cz + 0.08)), 60, 2.8, eye)
        camera(f"CAM_{p}_vcleo", (-0.20, -0.06, 1.31), Vector((hz.x, hz.y, hz.z - 0.06)), 45, 2.8, head)
        camera(f"CAM_{p}_vtwo", (0.12, -0.62, 1.04), Vector((-0.24, 0.36, 0.93)), 26, 4.0, eye)
    camera(f"CAM_{p}_claude", (cx + 0.05 * k, cy - 0.38 * k, cz + 0.06 * k), Vector((cx, cy, cz + 0.07 * k)), 50, 2.0, eye)
    bs.render_settings(scn)
    scn.camera = bpy.data.objects[f"CAM_{p}_wide_group"]
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


if __name__ == "__main__":
    main()
