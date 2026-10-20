"""Square Instagram profile-photo stills from the built episode scene.

blender -b ep1.blend -P insta_pfp.py -- <outdir> <size or WxH> <samples> [variant,...]
"""
import bpy, sys, os
from math import atan2
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out, samples = args[0], int(args[2])
w, h = (int(x) for x in args[1].split("x")) if "x" in args[1] else (int(args[1]),) * 2
only = args[3].split(",") if len(args) > 3 else None
os.makedirs(out, exist_ok=True)
scn = bpy.context.scene
scn.render.resolution_x, scn.render.resolution_y = w, h
scn.render.resolution_percentage = 100
scn.eevee.taa_render_samples = samples
ee = scn.eevee
ee.use_raytracing, ee.use_bokeh_jittered, ee.use_fast_gi = True, True, True
ee.shadow_ray_count, ee.shadow_step_count = 2, 8
scn.render.image_settings.file_format, scn.render.image_settings.color_mode = "PNG", "RGB"
O = bpy.data.objects
scn.timeline_markers.clear()  # the episode markers would switch back to their own cameras


def aim(cam, target):
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(target) - cam.location).to_track_quat("-Z", "Y")


def shoot(tag, frame, loc, target, lens, fstop, focus):
    scn.frame_set(frame)
    cd = bpy.data.cameras.new("PFP_" + tag)
    cd.lens, cd.sensor_fit, cd.clip_start = lens, "AUTO", 0.02
    cd.dof.use_dof, cd.dof.aperture_fstop, cd.dof.focus_object = True, fstop, O[focus]
    cam = bpy.data.objects.new("PFP_" + tag, cd)
    scn.collection.objects.link(cam)
    cam.location = Vector(loc)
    aim(cam, target)
    scn.camera = cam
    scn.render.filepath = os.path.join(out, f"{tag}.png")
    bpy.ops.render.render(write_still=True)
    print("PFP", tag)


V = {  # tag: frame, camera, target, lens, f-stop, focus
    "cleo_front": (1538, (-0.05, -0.28, 1.10), (-0.03, 0.55, 1.08), 50, 2.8, "V3_Cleo_eyes"),
    "cleo_look": (865, (-0.22, -0.24, 1.10), (-0.05, 0.55, 1.08), 50, 2.8, "V3_Cleo_eyes"),
    "claude_smile": (865, (0.03, 0.17, 0.86), (-0.315, 0.26, 0.815), 60, 2.8, "D2_Bubble_eye1"),
}
for tag, v in V.items():
    if not only or tag in only:
        shoot(tag, *v)


def claude_near(frame, at, look):
    """For the duo shots: lift Claude off his animated path and stand him on the desk beside her, turned toward `look`."""
    scn.frame_set(frame)
    root = O["D2_Bubble_eye1"]
    while root.parent:
        root = root.parent
    z = root.location.z
    root.animation_data_clear()
    root.location = (at[0], at[1], z)
    root.rotation_mode = "XYZ"
    root.rotation_euler = (0, 0, atan2(look[0] - at[0], -(look[1] - at[1])))


D = {
    "duo": (865, (-0.06, -0.34, 1.03), (-0.12, 0.42, 0.98), 40, 4.0, "D2_Bubble_eye1"),
    "duo_close": (865, (-0.10, -0.14, 1.01), (-0.13, 0.42, 0.98), 30, 4.0, "D2_Bubble_eye1"),
    "cover": (865, (-0.09, -0.38, 1.04), (-0.09, 0.42, 0.99), 26, 4.0, "D2_Bubble_eye1"),  # portrait reel cover: sky left for the title
}
if not only or any(t in only for t in D):
    claude_near(865, (-0.22, 0.29), (0.05, -0.20))
    for tag, v in D.items():
        if not only or tag in only:
            if tag == "cover":  # the front props sit right under the title-free bottom of the frame as soft blobs
                for ob in O:
                    if ob.name.startswith(("Prop_pot", "Prop_soil", "Prop_leaf", "Prop_phone")):
                        ob.hide_render = True
            shoot(tag, *v)
