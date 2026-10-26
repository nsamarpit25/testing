"""The Claude desk candidates in the real scene: on Cleo's desk, one close camera each plus a wide group shot.

blender -b --factory-startup -P mascots_desk.py -- <out.blend> [E3,E4]   (optional: only the candidates whose names start so)
"""
import bpy, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_scene as bs  # noqa: E402
from lineup import camera  # noqa: E402
from mascots import ONE_PIECE, REF, MIX, STARS, OURS, SHAPE_OPTS, build_claude  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = args[0]
    pick = [p for p in (args[1] if len(args) > 1 else "").split(",") if p]
    every = ONE_PIECE + REF + MIX + STARS + OURS + SHAPE_OPTS
    desk = [e for p in pick for e in every if e[0].startswith(p)] if pick else every  # in the order asked
    xs = [(i - (len(desk) - 1) / 2) * 0.16 for i in range(len(desk))]
    y = 0.0
    if len(desk) == 1:  # a single candidate goes where Claude lives in the film: left of the keyboard, by Cleo's mug
        xs, y = [-0.13], 0.08  # nudged right of the old -0.17 so a 1.3x build stays inside the over-shoulder frame
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    M = bs.materials()
    bs.build_world()
    bs.build_set(M)
    bs.build_cleo(M)
    bs.build_lights()
    row = bs.link(bpy.data.objects.new("FocusRow", None))
    row.location = (0, 0.0, 0.85)
    for (name, fn), x in zip(desk, xs):
        root = build_claude(name, fn, (x, y, 0.76))
        k = root.scale.z  # bigger builds: pull every camera back and up by the same factor
        eye = bpy.data.objects[f"{name}_eye1"]
        base = Vector((x, y, 0.76))

        def shot(tag, loc, tgt, lens, f):
            camera(f"CAM_{name}_{tag}", base + (Vector(loc) - base) * k, base + (Vector(tgt) - base) * k, lens, f, eye)
        shot("close", (x + 0.06, y - 0.37, 0.915), (x, y, 0.835), 55, 2.8)
        if len(desk) == 1:  # the film's angles: low hero close-up with Cleo soft behind, a 3/4, and a side look
            shot("low", (x + 0.035, y - 0.3, 0.805), (x, y, 0.812), 50, 2.0)
            shot("34", (x - 0.2, y - 0.26, 0.88), (x, y, 0.81), 60, 2.8)
            shot("side", (x + 0.3, y - 0.12, 0.85), (x, y, 0.81), 60, 2.8)
            camera(f"CAM_{name}_overshoulder", (-0.07, y - 0.62, 1.02), Vector((-0.03, y + 0.15, 0.88)), 35, 4.0, eye)  # fixed on the desk
        logo = bpy.data.objects.get(f"{name}_logo")
        if logo:  # a tight look at the spark
            bpy.context.view_layer.update()
            c = logo.matrix_world @ (sum((v.co for v in logo.data.vertices), Vector()) / len(logo.data.vertices))
            spot = bs.link(bpy.data.objects.new(f"{name}_LogoFocus", None))
            spot.location = c
            camera(f"CAM_{name}_logo", c + Vector((0.03, -0.2, 0.05)), c + Vector((0, 0, -0.008)), 85, 8.0, spot)
    bpy.context.view_layer.update()
    mug = bpy.data.objects["V3_Cleo_mug"]  # a look at Cleo's hands round her mug
    m = mug.matrix_world.translation
    camera("CAM_cleo_mug", m + Vector((0.07, -0.42, 0.1)), m + Vector((0, 0, 0.01)), 60, 4.0, mug)
    camera("CAM_desk_group", (0, -0.8, 1.0), Vector((0, 0.22, 0.9)), 30, 5.6, row)
    bs.render_settings(scn)
    scn.camera = bpy.data.objects["CAM_desk_group"]
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


main()
