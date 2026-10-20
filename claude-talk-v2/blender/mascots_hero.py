"""Moody hero look-dev, one stage per HERO mascot: dark desk, warm out-of-focus practicals behind, four portrait cameras.

blender -b --factory-startup -P mascots_hero.py -- <out.blend>
"""
import bpy, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import lin, mk, mat, bm_box, ellipsoid, emissive, eevee_defaults  # noqa: E402
from lineup import cyc, light, camera  # noqa: E402
from mascots import HERO, build_claude  # noqa: E402

TOP = 0.76
SPACING = 5.0  # stages far enough apart that their lights do not reach each other
CAM_D = 1.15


def stage(name, fn, x):
    """Desk, out-of-focus practicals, lights and four cameras for one mascot centred on x."""
    o = Vector((x, 0, 0))
    mk(f"Desk_{name}", bm_box(1.6, 0.9, 0.04, 0.006), mat("Desk", "#3a271d", 0.62), (x, 0.15, TOP - 0.02))
    bokeh = [(-0.62, TOP + 0.34, 0.035, "#ffb066", 4.0), (-0.38, TOP + 0.46, 0.025, "#ffc88a", 3.5), (-0.12, TOP + 0.3, 0.04, "#ff9a4a", 3.5),
             (0.1, TOP + 0.5, 0.028, "#ffd2a0", 3.0), (0.32, TOP + 0.36, 0.036, "#ffb070", 3.5), (0.58, TOP + 0.44, 0.03, "#ffa45c", 3.5),
             (-0.48, TOP + 0.16, 0.045, "#2f6280", 1.8), (0.42, TOP + 0.18, 0.04, "#2a566f", 1.6), (0.8, TOP + 0.28, 0.03, "#ffb878", 3.0),
             (-0.85, TOP + 0.24, 0.032, "#ffa860", 3.0), (0.0, TOP + 0.2, 0.03, "#ffbf80", 2.5), (0.22, TOP + 0.62, 0.022, "#ffe0b8", 2.5)]
    for i, (bx, z, r, col, k) in enumerate(bokeh):  # out-of-focus practicals far behind the desk
        ellipsoid(f"Bokeh_{name}{i}", (r, r, r), emissive(f"Bokeh{i}", col, k), (x + bx, 1.3 + 0.08 * (i % 3), z), sub=3)
    build_claude(name, fn, (x, 0, TOP))
    focus = bpy.data.objects[f"{name}_eye1"]
    cz = TOP + 0.108
    tgt = o + Vector((0, 0, cz))

    def at(x, y, z):  # camera spots around the mascot, pulled back by CAM_D so wide silhouettes fit
        return tgt + (Vector((x, y, TOP + z)) - Vector((0, 0, cz))) * CAM_D
    camera(f"CAM_{name}_hero", at(0.25, -0.58, 0.17), tgt - Vector((0, 0, 0.006)), 85, 2.4, focus)
    camera(f"CAM_{name}_front", at(0, -0.62, 0.15), tgt, 70, 5.6, focus)
    camera(f"CAM_{name}_34", at(-0.4, -0.46, 0.2), tgt, 70, 5.6, focus)
    camera(f"CAM_{name}_side", at(0.6, 0.12, 0.16), tgt, 70, 5.6, focus)
    light("AREA", f"Key_{name}", o + Vector((-0.7, -0.8, TOP + 0.6)), tgt, "#ffe1c4", 45, 0.8)
    light("AREA", f"Fill_{name}", o + Vector((0.8, -0.6, TOP + 0.25)), tgt, "#c9d8ff", 10, 0.8)
    for nm, loc, col, e in (("Rim", (0.45, 0.55, TOP + 0.62), "#ffc89a", 30), ("Rim2", (-0.55, 0.5, TOP + 0.5), "#9fc2ff", 12)):
        light("SPOT", f"{nm}_{name}", o + Vector(loc), tgt, col, e, 0.05)
        ld = bpy.data.lights[f"{nm}_{name}"]  # tight cones on the orb so they do not rake across the desk
        ld.spot_size, ld.spot_blend = 0.28, 0.6


def main():
    out = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    w = bpy.data.worlds.new("Night")
    scn.world = w
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*lin("#14110f"), 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    cyc(mat("Backdrop", "#2c2420", 0.95))
    bpy.data.objects["Cyc"].scale.x = 4.0  # one long backdrop behind every stage
    for k, (name, fn) in enumerate(HERO):
        stage(name, fn, (k - (len(HERO) - 1) / 2) * SPACING)
    eevee_defaults(scn, 64)
    scn.render.resolution_x, scn.render.resolution_y = 720, 1280
    scn.camera = bpy.data.objects[f"CAM_{HERO[0][0]}_hero"]
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


main()
