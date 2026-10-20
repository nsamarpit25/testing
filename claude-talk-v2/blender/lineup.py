"""Studio look-dev: the five girl variants side by side, one portrait camera each (front + 3/4).

blender -b --factory-startup -P lineup.py -- <out.blend>
"""
import bpy, bmesh, os, sys
from math import pi, sin, cos
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import lin, link, mk, mat, aim, eevee_defaults  # noqa: E402
from girls import VARIANTS, build_girl  # noqa: E402

SPACING = 0.62


def cyc(m):
    """Seamless studio backdrop: floor curving up into a wall."""
    bm = bmesh.new()
    prof = [(y, 0.0) for y in (-4.0, 0.6)]
    R = 0.9
    for i in range(1, 12):
        a = pi / 2 * i / 11
        prof.append((0.6 + R * sin(a), R - R * cos(a)))
    prof.append((0.6 + R, 4.0))
    rows = []
    for x in (-6.0, 6.0):
        rows.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    mk("Cyc", bm, m, smooth=True)


def light(kind, name, loc, target, hexcol, energy, size):
    ld = bpy.data.lights.new(name, kind)
    ld.color, ld.energy = lin(hexcol), energy
    if kind == "AREA":
        ld.shape, ld.size = "DISK", size
    else:
        ld.shadow_soft_size = size
    ld.use_shadow_jitter = True
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    aim(ob, target)


def camera(name, loc, target, lens, fstop, focus, clip=0.05):
    cd = bpy.data.cameras.new(name)
    cd.lens, cd.sensor_fit = lens, "AUTO"
    cd.dof.use_dof, cd.dof.aperture_fstop, cd.dof.focus_object = True, fstop, focus
    cd.clip_start = clip
    cam = link(bpy.data.objects.new(name, cd))
    cam.location = loc
    aim(cam, target)
    return cam


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = args[0]
    pick = args[1].split(",") if len(args) > 1 and args[1] else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    w = bpy.data.worlds.new("Studio")
    scn.world = w
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*lin("#2a2730"), 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    cyc(mat("Backdrop", "#b39a90", 0.95))
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=8.0)
    mk("BackWall", bm, mat("BackWall", "#b39a90", 0.95), (0, -5.0, 4.0), (pi / 2, 0, 0))

    cfgs = VARIANTS
    if pick and pick[0] == "faceopts":  # V3 with the reference face shape, from "her features" to "reference proportions"
        base = next(c for c in VARIANTS if c["name"].startswith("V3"))
        shape = dict(face_sq=2.25, face_fill=2.2, face_flat=2.25, face_chin=0.95, face_cheek=0.035, seed=3)
        opts = [dict(mouth_z=-0.09, nose_z=-0.052),
                dict(eye_x=0.062, lens=0.045, lens_x=0.064, mouth_z=-0.096, nose_z=-0.056, mouth_w=1.15),
                dict(eye_x=0.07, lens=0.055, lens_x=0.074, mouth_z=-0.102, nose_z=-0.058, mouth_w=1.35)]
        long = dict(base, hair_style="long_front", **shape, **opts[1])
        cfgs = [dict(long, name="L0"),
                dict(long, name="L1", hair_len=0.2, hair_count=26, frame_n=2, frame_hang=0.16),
                dict(long, name="L2", hair_len=0.16, hair_count=22, frame_n=2, frame_hang=0.12)]
        pick = None
    for i, cfg in enumerate(cfgs):
        if pick and not any(k in cfg["name"] for k in pick):
            continue
        x = (i - 2) * SPACING
        g = build_girl(cfg, (x, 0, 0), seed=cfg.get("seed", i + 1))
        tgt = Vector((x, 0, 1.07))
        camera(f"CAM_{cfg['name']}_front", (x, -1.45, 1.1), tgt, 75, 4.0, g["head"])
        camera(f"CAM_{cfg['name']}_34", (x + 0.55, -1.25, 1.16), Vector((x, 0, 1.06)), 70, 4.0, g["head"])
        camera(f"CAM_{cfg['name']}_full", (x, -2.35, 0.78), Vector((x, 0, 0.665)), 50, 5.6, g["head"])
        camera(f"CAM_{cfg['name']}_full34", (x + 1.3, -1.95, 0.86), Vector((x, 0, 0.665)), 50, 5.6, g["head"])
        camera(f"CAM_{cfg['name']}_legs", (x + 0.45, -1.15, 0.36), Vector((x, 0, 0.3)), 50, 4.0, g["root"])
        camera(f"CAM_{cfg['name']}_back", (x - 0.45, 1.05, 1.18), Vector((x, 0, 1.06)), 70, 5.6, g["head"])
        camera(f"CAM_{cfg['name']}_fullback", (x - 1.0, 2.15, 0.86), Vector((x, 0, 0.665)), 50, 5.6, g["head"],
               clip=1.0)  # starts past the cyc wall behind her

    if len([c for c in cfgs if not pick or any(k in c["name"] for k in pick)]) > 1:
        camera("CAM_group", (0, -4.6, 0.95), Vector((0, 0, 0.68)), 50, 8.0, None)
    light("AREA", "Key", (-1.4, -2.0, 2.2), (0, 0, 1.1), "#ffe3c9", 600, 1.6)
    light("AREA", "Fill", (2.2, -1.6, 1.3), (0, 0, 1.0), "#cfdcff", 110, 1.6)
    light("AREA", "Rim", (0.4, 0.9, 2.2), (0, 0, 1.15), "#ffe6d2", 220, 2.2)
    light("AREA", "Rim2", (-1.5, 0.8, 1.7), (0, 0, 1.1), "#ffd9c2", 180, 1.4)

    eevee_defaults(scn, 64)
    scn.render.resolution_x, scn.render.resolution_y = 720, 1280
    scn.camera = next(o for o in scn.objects if o.type == "CAMERA")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


if __name__ == "__main__":
    main()
