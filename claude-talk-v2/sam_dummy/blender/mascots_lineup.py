"""Look-dev for the Claude mascot variants: all five on a desk-height table, a front and a 3/4 camera each.

blender -b --factory-startup -P mascots_lineup.py -- <out.blend> [orb]
"""
import bpy, bmesh, os, sys
from math import pi
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import lin, mk, mat, bm_box, eevee_defaults  # noqa: E402
from lineup import cyc, light, camera  # noqa: E402
from mascots import VARIANTS, ORBS, build_claude  # noqa: E402

SPACING, TOP = 0.26, 0.76


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = args[0]
    orbs = len(args) > 1 and args[1] == "orb"
    D = 1.4 if orbs else 1.0  # orbs with rings are wider: pull the cameras back
    H = 0.016 if orbs else 0.0  # and they hover higher
    U = 0.1 if orbs else 0.0  # look down a little so the desk and the hover shadow show
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    w = bpy.data.worlds.new("Studio")
    scn.world = w
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*lin("#2a2730"), 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    cyc(mat("Backdrop", "#b7a3a0", 0.95))
    mk("Table", bm_box(1.6, 0.5, 0.04, 0.008), mat("Table", "#8a6047", 0.45, coat=0.2), (0, 0.05, TOP - 0.02))
    for i, (name, fn) in enumerate(ORBS if orbs else VARIANTS):
        x = (i - 2) * SPACING
        build_claude(name, fn, (x, 0, TOP))
        focus = bpy.data.objects[f"{name}_eye1"]
        camera(f"CAM_{name}_front", (x, -0.56 * D, TOP + 0.1 + H + U), Vector((x, 0, TOP + 0.064 + H)), 70, 8.0, focus)
        camera(f"CAM_{name}_34", (x + 0.3 * D, -0.47 * D, TOP + 0.13 * D + H + U), Vector((x, 0, TOP + 0.062 + H)), 70, 8.0, focus)
    light("AREA", "Key", (-0.9, -1.1, TOP + 0.9), (0, 0, TOP + 0.06), "#ffe3c9", 130, 1.0)
    light("AREA", "Fill", (1.2, -0.9, TOP + 0.4), (0, 0, TOP + 0.05), "#cfdcff", 28, 1.0)
    light("AREA", "Rim", (0.3, 0.7, TOP + 0.6), (0, 0, TOP + 0.07), "#ffe6d2", 60, 1.2)
    light("AREA", "Rim2", (-0.8, 0.6, TOP + 0.4), (0, 0, TOP + 0.06), "#ffd9c2", 36, 0.8)
    eevee_defaults(scn, 64)
    scn.render.resolution_x, scn.render.resolution_y = 720, 1280
    scn.camera = next(o for o in scn.objects if o.type == "CAMERA")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


main()
