"""Codex (gpt-6.1-sol) room: a lived-in evening study. Window and curtains behind Cleo, a bookcase with a toy rocket
and an amber orb behind Claude, corkboard, shelf, rug, floor plant, blanket basket. Positions follow Codex's spec."""
import bpy, bmesh
from math import pi, sin, cos
from mathutils import Vector, Matrix
import build_scene as bs
from build_scene import mk, bm_box, bm_cyl, bm_tube, ellipsoid, emissive, mat

_C = {}


def C(hexcol, rough=0.75):
    """One matte material per colour."""
    if hexcol not in _C:
        _C[hexcol] = mat(f"Sol_{hexcol[1:]}", hexcol, rough)
    return _C[hexcol]


def box(name, c, size, col, rot=(0, 0, 0), bevel=0.004):
    return mk(name, bm_box(*size, bevel), col if not isinstance(col, str) else C(col), c, rot)


def cyl(name, c, r, h, col, seg=10, r2=None, rot=(0, 0, 0)):
    return mk(name, bm_cyl(r, h, seg, r2), col if not isinstance(col, str) else C(col), c, rot)


def light(name, kind, loc, col, energy, size=0.2, target=None):
    ld = bpy.data.lights.new(name, kind)
    ld.color, ld.energy = bs.lin(col), energy
    if kind == "AREA":
        ld.shape, ld.size = "DISK", size
    else:
        ld.shadow_soft_size = size
    ld.use_shadow_jitter = True
    ob = bs.link(bpy.data.objects.new(name, ld))
    ob.location = loc
    if target:
        bs.aim(ob, target)
    return ob


def star_bm(R, r, n=5, depth=0.02):
    bm = bmesh.new()
    vs = []
    for i in range(2 * n):
        a = pi / 2 + pi * i / n
        rad = R if i % 2 == 0 else r
        vs.append(bm.verts.new((rad * cos(a), 0, rad * sin(a))))
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, depth, 0), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def leaves(prefix, base, n, size, col, spread=0.06, droop=0.6, seed=0):
    for i in range(n):
        a = 2 * pi * i / n + seed
        ellipsoid(f"{prefix}{i}", (size[0], size[1], size[2] * (0.8 + 0.3 * ((i * 7) % 3) / 2)), C(col, 0.6),
                  (base[0] + spread * cos(a), base[1] + spread * sin(a), base[2] + size[2] * 0.7),
                  (droop * sin(a), -droop * cos(a), 0), sub=1)


def sol_room(M, R):
    for n in ("Wall_", "Frame_", "Mullion_", "Sill", "Cactus", "Fairy", "Bldg", "City_windows", "Sky",
              "Plant_pot", "Leaf", "Note_", "Book", "Desk_leg"):
        for ob in [o for o in bpy.data.objects if o.name.startswith(n) and o.type in ("MESH", "EMPTY")]:
            bpy.data.objects.remove(ob)
    bs_rec = lambda name, h: bpy.data.materials[name].node_tree.nodes["Principled BSDF"].inputs["Base Color"].__setattr__(
        "default_value", (*bs.lin(h), 1))
    bs_rec("Floor", "#8a5a3c")
    bs_rec("Keyboard", "#5a3f5e")

    # shell: back wall with the window hole (x -1.475..-0.025, z 1.0..2.28), side walls, skirting
    plum, mauve, cream = C("#6e5266", 0.9), C("#7a5c6c", 0.9), C("#efe4d2", 0.6)
    x0, x1, z0, z1, H = -1.475, -0.025, 1.0, 2.28, 2.6
    for name, c, s in [("Wall_BL", ((x0 - 1.8) / 2, 1.29, H / 2), (x0 + 1.8, 0.08, H)),
                       ("Wall_BR", ((x1 + 1.8) / 2, 1.29, H / 2), (1.8 - x1, 0.08, H)),
                       ("Wall_BB", ((x0 + x1) / 2, 1.29, z0 / 2), (x1 - x0, 0.08, z0)),
                       ("Wall_BT", ((x0 + x1) / 2, 1.29, (z1 + H) / 2), (x1 - x0, 0.08, H - z1))]:
        mk(name, bm_box(*s), plum, c)
    for sx in (-1.84, 1.84):
        mk("Wall_side", bm_box(0.08, 2.8, H), mauve, (sx, -0.15, H / 2))
    mk("Skirt_back", bm_box(3.6, 0.015, 0.08), cream, (0, 1.2425, 0.04))
    for sx in (-1.7925, 1.7925):
        mk("Skirt_side", bm_box(0.015, 2.8, 0.08), cream, (sx, -0.15, 0.04))

    # window: cream frame, four panes, sill, rod and gathered dusty-rose curtains
    xc, zc, fr = (x0 + x1) / 2, (z0 + z1) / 2, 0.045
    for name, c, s in [("Frame_L", (x0 + fr / 2, 1.23, zc), (fr, 0.06, z1 - z0)), ("Frame_R", (x1 - fr / 2, 1.23, zc), (fr, 0.06, z1 - z0)),
                       ("Frame_T", (xc, 1.23, z1 - fr / 2), (x1 - x0, 0.06, fr)), ("Frame_B", (xc, 1.23, z0 + fr / 2), (x1 - x0, 0.06, fr)),
                       ("Mullion_V", (xc, 1.235, zc), (0.03, 0.04, z1 - z0)), ("Mullion_H", (xc, 1.235, zc), (x1 - x0, 0.04, 0.03))]:
        mk(name, bm_box(*s, 0.004), cream, c)
    box("Sill", (xc, 1.14, 0.985), (1.61, 0.22, 0.065), "#e8dcc8")
    brass = mat("SolBrass", "#b08d57", 0.35, metal=0.8)
    cyl("CurtainRod", (xc, 1.12, 2.38), 0.02, 1.9, brass, 8, rot=(0, pi / 2, 0))
    rose = C("#c98b93", 0.9)
    for side, cx in (("L", -1.53), ("R", 0.02)):
        for k in range(5):  # gathered folds
            ellipsoid(f"Curtain{side}{k}", (0.035, 0.06, 0.75), rose,
                      (cx - 0.08 + k * 0.04, 1.13 - 0.015 * (k % 2), 1.63 - 0.01 * k), (0, 0.02 * (k - 2), 0), sub=2)
    # outside: periwinkle sky, midnight rooftops, three amber windows, ivory crescent
    sky = bs.gradient_mat("SolSky", "Z", 0.0, 1.0, [(0.0, "#c9a8d8"), (0.35, "#8f94d8"), (1.0, "#3a3f86")],
                          emit_strength=1.4, coords="Generated", pure_emission=True)
    sb = bmesh.new()
    bmesh.ops.create_grid(sb, x_segments=1, y_segments=1, size=1.0)
    bmesh.ops.rotate(sb, verts=sb.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, "X"))
    bs.scale_bm(sb, (4.0, 1, 2.2))
    mk("Sky", sb, sky, (xc, 3.2, 1.7))
    roofs = mat("SolRoofs", "#1c2148", 0.9, emit="#1c2148", strength=0.4)
    amber = emissive("SolWin", "#ffbf6e", 9.0)
    for i, (x, w, h, y) in enumerate([(-2.0, 1.0, 1.15, 2.4), (-1.2, 0.8, 1.45, 2.2), (-0.45, 0.9, 1.25, 2.5), (0.3, 0.8, 1.6, 2.3)]):
        box(f"Roof{i}", (x, y, h / 2), (w, 0.6, h), roofs, bevel=0)
        pr = bmesh.new()  # pitched cap
        V = [pr.verts.new(p) for p in [(-w / 2, -0.3, 0), (w / 2, -0.3, 0), (w / 2, 0.3, 0), (-w / 2, 0.3, 0), (0, -0.3, 0.22), (0, 0.3, 0.22)]]
        for f in [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4), (0, 3, 2, 1)]:
            pr.faces.new([V[j] for j in f])
        bmesh.ops.recalc_face_normals(pr, faces=pr.faces)
        mk(f"RoofCap{i}", pr, roofs, (x, y, h))
    for i, (x, z, y) in enumerate([(-1.3, 1.25, 2.2 - 0.31), (-1.05, 1.25, 2.2 - 0.31), (-0.3, 1.05, 2.5 - 0.31)]):
        box(f"RoofWin{i}", (x, y, z), (0.12, 0.01, 0.15), amber, bevel=0)
    moon = bmesh.new()
    bmesh.ops.create_circle(moon, cap_ends=True, segments=24, radius=0.11)
    bmesh.ops.rotate(moon, verts=moon.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, "X"))
    mk("Moon", moon, emissive("SolMoon", "#fff4dc", 6.0), (-1.0, 3.15, 2.05))
    bite = bmesh.new()
    bmesh.ops.create_circle(bite, cap_ends=True, segments=24, radius=0.1)
    bmesh.ops.rotate(bite, verts=bite.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(pi / 2, 3, "X"))
    mk("MoonBite", bite, emissive("SolMoonBite", "#5a5fa8", 1.4), (-0.95, 3.14, 2.08))
    # sill: cactus and a folded paper star on a stand
    cyl("Cactus_pot", (-1.18, 1.12, 1.06), 0.045, 0.08, "#c0694a", 8, 0.036)
    ellipsoid("Cactus", (0.032, 0.032, 0.065), C("#7a9a6a", 0.6), (-1.18, 1.12, 1.15), sub=1, jit=0.003)
    mk("PaperStar", star_bm(0.075, 0.032, 5, 0.03), C("#f0d890", 0.8), (-0.35, 1.1, 1.17), (0, 0, 0.3))
    cyl("PaperStar_stand", (-0.35, 1.115, 1.04), 0.006, 0.07, brass, 6)

    # right of the window: floating shelf, books, photo, fern, fairy lights; corkboard below
    walnut = C("#6b4429", 0.5)
    box("Shelf", (0.8, 1.1, 1.8), (1.0, 0.26, 0.045), walnut)
    box("ShelfBook0", (0.46, 1.11, 1.945), (0.06, 0.15, 0.24), "#3d5a80")
    box("ShelfBook1", (0.54, 1.11, 1.925), (0.07, 0.15, 0.20), "#d9a441")
    box("Photo_frame", (0.74, 1.09, 1.94), (0.18, 0.045, 0.23), "#efe4d2", rot=(0.12, 0, 0))
    art = bs.gradient_mat("PhotoArt", "Z", -0.1, 0.1, [(0.0, "#e8a87c"), (1.0, "#9fc4e0")], emit_strength=0.1, rough=0.8)
    mk("Photo", bm_box(0.14, 0.004, 0.19), art, (0.74, 1.064, 1.943), (0.12, 0, 0))
    cyl("Fern_pot", (1.08, 1.1, 1.87), 0.07, 0.11, "#d8a0a0", 10, 0.055)
    leaves("Fern", (1.08, 1.1, 1.9), 9, (0.022, 0.01, 0.12), "#6b7d3a", 0.04, 0.9, 0.4)
    wire = M["wire"]
    pts = [(0.3 + 1.0 * i / 20, 1.17, 1.72 - 0.1 * sin(pi * i / 20)) for i in range(21)]
    mk("Fairy_wire", bm_tube(pts, 0.002, 4), wire)
    for i in range(1, 7):
        u = i / 7
        ellipsoid(f"Fairy_{i}", (0.011, 0.011, 0.014), M["fairy"], (0.3 + u, 1.165, 1.72 - 0.1 * sin(pi * u) - 0.016), sub=1)
    box("Cork_frame", (0.86, 1.225, 1.27), (0.67, 0.03, 0.48), walnut)
    box("Cork", (0.86, 1.205, 1.27), (0.62, 0.02, 0.43), "#c49a6c", bevel=0)
    for name, c, s, col, ry in [("Note_y", (0.67, 1.192, 1.35), (0.13, 0.004, 0.13), "#f5d76e", 0.12),
                                ("Note_b", (0.97, 1.192, 1.34), (0.14, 0.004, 0.10), "#9fc4e0", -0.08),
                                ("Postcard", (0.85, 1.19, 1.14), (0.22, 0.004, 0.13), "#e8c9a0", 0.05)]:
        box(name, c, s, col, (0, ry, 0), bevel=0)
    for i, (x, z, col) in enumerate([(0.67, 1.41, "#c0392b"), (0.97, 1.385, "#efe4d2"), (0.85, 1.2, "#b08d57")]):
        ellipsoid(f"Pin{i}", (0.008, 0.008, 0.008), C(col, 0.4), (x, 1.186, z), sub=1)
    for i in range(3):  # pencil marks on the notes
        box(f"NoteLine{i}", (0.67, 1.189, 1.38 - 0.03 * i), (0.08, 0.002, 0.005), "#8a6a3a", (0, 0.12, 0), bevel=0)

    # behind Claude: open bookcase against the left wall, facing +x
    bx = -1.61
    box("Case_back", (bx - 0.14, 0.38, 0.86), (0.02, 0.98, 1.72), walnut, bevel=0.002)
    for sy in (-0.1, 0.86):
        box("Case_side", (bx, 0.38 + (sy - 0.38), 0.86), (0.3, 0.025, 1.72), walnut)
    for z in (0.12, 0.47, 0.835, 1.19, 1.72):
        box("Case_shelf", (bx, 0.38, z), (0.3, 0.96, 0.025), walnut)
    for y, z, h, col in [(0.02, 0.985, 0.30, "#2f3e66"), (0.085, 0.965, 0.26, "#efe4d2"), (0.15, 0.995, 0.32, "#a64b2a"),
                         (0.215, 0.955, 0.24, "#7a9a6a"), (0.28, 0.975, 0.28, "#d9a441")]:
        box("CaseBook", (bx + 0.02, y, 0.8475 + h / 2), (0.18, 0.055, h), col)
    # toy rocket
    rk = (bx + 0.03, 0.42, 0.8475)
    cyl("Rocket_body", (rk[0], rk[1], rk[2] + 0.12), 0.035, 0.17, "#efe4d2", 10)
    cyl("Rocket_nose", (rk[0], rk[1], rk[2] + 0.245), 0.035, 0.08, "#c0392b", 10, 0.002)
    for i in range(3):
        a = 2 * pi * i / 3
        box(f"Rocket_fin{i}", (rk[0] + 0.04 * cos(a), rk[1] + 0.04 * sin(a), rk[2] + 0.05), (0.05, 0.008, 0.07), "#6f8fb8",
            (0, 0, a))
    ellipsoid("Rocket_port", (0.014, 0.014, 0.014), C("#6f8fb8", 0.3), (rk[0] + 0.033, rk[1], rk[2] + 0.15), sub=1)
    # amber orb lamp with its own glow
    cyl("Orb_base", (bx + 0.04, 0.64, 0.86), 0.05, 0.025, walnut, 10)
    ellipsoid("Orb", (0.075, 0.075, 0.075), emissive("SolOrb", "#ffb45e", 4.0), (bx + 0.04, 0.64, 0.945), sub=2)
    light("Orb_glow", "POINT", (bx + 0.12, 0.62, 0.97), "#ffa24a", 18, 0.08)
    box("Wicker", (bx, 0.35, 0.29), (0.23, 0.53, 0.33), "#c99a52")
    box("Wicker_label", (bx + 0.117, 0.35, 0.33), (0.004, 0.12, 0.06), "#efe4d2", bevel=0)
    for i, col in enumerate(("#5b4a7a", "#efe4d2", "#6f8fb8")):
        box(f"CaseStack{i}", (bx, 0.17, 1.2025 + 0.04 * i + 0.02), (0.22 - 0.01 * i, 0.3 - 0.02 * i, 0.04), col, (0, 0, 0.06 * i))
    cyl("Pothos_pot", (bx, 0.7, 1.79), 0.08, 0.12, "#c0694a", 10, 0.065)
    sage = C("#7a9a6a", 0.6)
    import random
    rnd = random.Random(4)
    for v, (vy, ln) in enumerate([(0.6, 5), (0.68, 7), (0.75, 4), (0.82, 6)]):  # vines of uneven length spilling down
        pts = [(bx + 0.12 + 0.03 * sin(j * 1.3 + v), vy + 0.03 * sin(j * 0.9 + v * 2), 1.8 - 0.1 * j) for j in range(ln)]
        mk(f"PothosVine{v}", bm_tube(pts, 0.003, 4), C("#4f6a3a", 0.7))
        for j, p in enumerate(pts[1:]):
            for side in (-1, 1):
                ellipsoid(f"Pothos{v}_{j}_{side}", (0.026 + rnd.uniform(-0.006, 0.006), 0.01, 0.02), sage,
                          (p[0] + 0.012, p[1] + side * 0.018, p[2] + rnd.uniform(-0.02, 0.02)),
                          (rnd.uniform(-0.5, 0.5), 0.4, side * 0.6 + rnd.uniform(-0.3, 0.3)), sub=1)

    # desktop
    box("DeskMat", (0.23, 0.14, 0.765), (0.8, 0.36, 0.01), "#8fa58a", bevel=0.002)
    box("Notebook", (0.18, -0.13, 0.775), (0.25, 0.12, 0.03), "#d9a441", rot=(0, 0, -0.08))
    cyl("Pen", (0.2, -0.13, 0.795), 0.006, 0.14, "#7a2a3a", 6, rot=(0, pi / 2, 0.5))
    cyl("PencilCup", (0.73, 0.38, 0.81), 0.045, 0.1, "#c0694a", 10)
    for i, (col, dx) in enumerate([("#efe4d2", -0.015), ("#6f8fb8", 0.01), ("#f2c14e", 0.0)]):
        cyl(f"Pencil{i}", (0.73 + dx, 0.38 + 0.012 * (i - 1), 0.88 + 0.01 * i), 0.006, 0.17, col, 6, rot=(0.15 * (i - 1), 0.15 * dx * 20, 0))
    box("Book_low", (-0.62, -0.08, 0.7775), (0.29, 0.18, 0.035), "#2f3e66")
    box("Book_up", (-0.61, -0.075, 0.81), (0.27, 0.17, 0.03), "#e8a87c", rot=(0, 0, 0.1))
    box("Mouse", (0.51, 0.13, 0.785), (0.06, 0.1, 0.03), "#b9a8de", bevel=0.012)
    # task card leaning by Claude
    box("TaskCard", (-0.66, 0.04, 0.9), (0.17, 0.003, 0.15), "#f6d5bf", rot=(-0.25, 0, 0.35), bevel=0)
    for i in range(3):
        box(f"TaskLine{i}", (-0.66 + 0.004 * i, 0.034 - 0.009 * i, 0.935 - 0.034 * i), (0.11 - 0.02 * i, 0.002, 0.008), "#5a3a3a",
            (-0.25, 0, 0.35), bevel=0)
    # headphones hanging on a hook at the desk's right edge
    box("Hook", (0.86, 0.3, 0.71), (0.03, 0.03, 0.05), "#2a2a30")
    band = [(0.88, 0.3 + 0.08 * cos(a), 0.7 - 0.09 + 0.09 * sin(a) + 0.0) for a in [pi * k / 10 for k in range(11)]]
    mk("Headphone_band", bm_tube([(x, y, z - 0.0) for x, y, z in band], 0.008, 6), C("#2a2a30", 0.5))
    for s in (-1, 1):
        ellipsoid(f"Headphone_cup{s}", (0.03, 0.045, 0.045), C("#b9a8de", 0.8), (0.88, 0.3 + s * 0.085, 0.6), sub=2)
    # PC tower and its cable
    box("PC_tower", (0.61, 0.28, 0.27), (0.24, 0.38, 0.54), "#2a2a30", bevel=0.012)
    box("PC_led", (0.61, 0.088, 0.47), (0.014, 0.004, 0.014), emissive("SolLed", "#ffb04a", 8.0), bevel=0)
    mk("Cable", bm_tube([(0.43, 0.5, 0.78), (0.5, 0.52, 0.74), (0.58, 0.5, 0.5), (0.5, 0.46, 0.3), (0.61, 0.49, 0.12)], 0.006, 6),
       C("#3a2a22", 0.6))
    # desk: walnut top, chunky dark legs
    for sx in (-0.76, 0.76):
        for sy in (-0.12, 0.42):
            box("Desk_leg", (sx, sy, 0.36), (0.06, 0.06, 0.72), "#3a2a22")

    # room: rug, right-wall print, floor plant, blanket basket
    box("Rug", (0, 0.05, 0.012), (2.65, 2.2, 0.012), "#b5654a", rot=(0, 0, 0.04), bevel=0)
    box("Rug_inner", (0, 0.05, 0.0195), (2.35, 1.9, 0.004), "#c97a5a", rot=(0, 0, 0.04), bevel=0)
    mk("Rug_border", bm_tube([(-1.22, -1.0, 0.021), (1.18, -1.04, 0.021), (1.22, 1.1, 0.021), (-1.18, 1.14, 0.021)], 0.035, 4, True,
                             (0, 0, 1)), C("#efe4d2", 0.95))
    box("Print_frame", (1.77, 0.5, 1.65), (0.04, 0.48, 0.64), "#a07a4a")
    box("Print_paper", (1.748, 0.5, 1.65), (0.004, 0.42, 0.58), "#efe4d2", bevel=0)
    mtn = bmesh.new()
    V = [mtn.verts.new(p) for p in [(0, -0.18, -0.2), (0, 0.18, -0.2), (0, 0.05, 0.12), (0, -0.04, 0.02)]]
    mtn.faces.new(V)
    mk("Print_mountain", mtn, C("#c0694a", 0.8), (1.745, 0.5, 1.62))
    cyl("FloorPot", (1.42, 0.94, 0.17), 0.17, 0.34, "#d9c7a0", 10, 0.13)
    leaves("FloorLeaf", (1.42, 0.94, 0.38), 9, (0.07, 0.018, 0.3), "#5f7a4a", 0.07, 0.55, 0.2)
    cyl("Basket", (1.22, -0.36, 0.2), 0.2, 0.4, "#d4b06a", 12, 0.18)
    ellipsoid("Blanket", (0.2, 0.2, 0.08), C("#a996d1", 0.95), (1.22, -0.36, 0.42), sub=2, jit=0.01)
    box("Blanket_drape", (1.05, -0.4, 0.3), (0.04, 0.24, 0.24), C("#a996d1", 0.95), rot=(0, 0.25, 0.1), bevel=0.015)

    # lights: lamp key, cool window, fill
    L = bpy.data.objects
    L["Rim_window"].location = (-0.75, 1.9, 2.0)
    bs.aim(L["Rim_window"], (-0.2, 0.4, 1.0))
    L["Rim_window"].data.color, L["Rim_window"].data.energy, L["Rim_window"].data.size = bs.lin("#a8c0ff"), 45, 1.2
    L["Rim_window_L"].data.energy = 0
    L["Front_fill"].location = (0.85, -0.85, 1.9)
    bs.aim(L["Front_fill"], (0, 0.4, 0.9))
    L["Front_fill"].data.color, L["Front_fill"].data.energy = bs.lin("#ffe6d0"), 11
    L["Key_warm"].data.color, L["Key_warm"].data.energy = bs.lin("#ffc89a"), 14
    L["Fairy_glow"].location, L["Fairy_glow"].data.energy = (0.8, 1.0, 1.65), 4
    light("Corner_warm", "POINT", (1.3, 0.3, 1.2), "#ffb27a", 12, 0.3)  # lifts the plant / basket corner
