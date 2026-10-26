"""Render stills or the animation from scene.blend.

blender -b scene.blend -P render.py -- stills <outdir> <height> <samples> [shot,shot...]
blender -b scene.blend -P render.py -- anim   <outdir> <height> <samples>
blender -b scene.blend -P render.py -- frameshq <outdir> <height> <samples> f1,f2,...   (full quality)
blender -b scene.blend -P render.py -- animhq <outdir> <height> <samples> <first>-<last>   (full-quality Eevee settings)
blender    scene.blend -P render.py -- gui    <outdir> <height> <samples>   (opens the UI and renders there)
"""
import bpy, sys, os

args = sys.argv[sys.argv.index("--") + 1:]
mode, outdir, height, samples = args[0], args[1], int(args[2]), int(args[3])
only = args[4].split(",") if len(args) > 4 and mode != "animhq" else None
os.makedirs(outdir, exist_ok=True)

scn = bpy.context.scene
scn.render.resolution_y = height
scn.render.resolution_x = round(height * 9 / 16 / 2) * 2
scn.render.resolution_percentage = 100
scn.eevee.taa_render_samples = samples
scn.render.image_settings.file_format = "PNG"
scn.render.image_settings.color_mode = "RGB"

markers = sorted(scn.timeline_markers, key=lambda m: m.frame)


def shot_bounds():
    out = []
    for i, m in enumerate(markers):
        end = markers[i + 1].frame - 1 if i + 1 < len(markers) else scn.frame_end
        out.append((m.name, m.frame, end, m.camera))
    return out


def hq():
    """Full-quality Eevee: raytracing, soft shadows, true bokeh."""
    ee = scn.eevee
    ee.use_raytracing, ee.use_bokeh_jittered, ee.use_fast_gi = True, True, True
    ee.shadow_ray_count, ee.shadow_step_count = 2, 8


if mode == "cams":  # render through every camera whose name contains one of the filters
    for cam in sorted([o for o in scn.objects if o.type == "CAMERA"], key=lambda o: o.name):
        if only and not any(k in cam.name for k in only):
            continue
        scn.camera = cam
        wide = "_group" in cam.name  # group shots are landscape
        scn.render.resolution_x = round(height * (16 / 9 if wide else 9 / 16) / 2) * 2
        scn.render.filepath = os.path.join(outdir, cam.name.replace("CAM_", "") + ".png")
        bpy.ops.render.render(write_still=True)
        print("STILL", cam.name)
elif mode == "stills":
    for name, f0, f1, cam in shot_bounds():
        if only and name not in only:
            continue
        f = (f0 + f1) // 2
        scn.frame_set(f)
        scn.camera = cam
        scn.render.filepath = os.path.join(outdir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", name, f)
elif mode in ("frames", "frameshq"):  # render listed frames through whichever camera the markers give at that frame
    if mode == "frameshq":
        hq()
    bounds = shot_bounds()
    for f in [int(x) for x in only]:
        name, cam = next((n, c) for n, a, b, c in bounds if a <= f <= b)
        scn.frame_set(f)
        scn.camera = cam
        scn.render.filepath = os.path.join(outdir, f"{f:05d}_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", name, f)
elif mode == "animhq":  # full quality over a frame range; skips frames that exist (done, or claimed by a helper)
    hq()
    scn.render.use_overwrite, scn.render.use_placeholder = False, True
    scn.frame_start, scn.frame_end = (int(x) for x in args[4].split("-"))
    scn.render.filepath = os.path.join(outdir, "f_")
    bpy.ops.render.render(animation=True)
elif mode == "anim":
    scn.render.filepath = os.path.join(outdir, "f_")
    bpy.ops.render.render(animation=True)
elif mode == "gui":
    scn.render.filepath = os.path.join(outdir, "f_")
    done = os.path.join(outdir, "DONE")
    if os.path.exists(done):
        os.remove(done)

    def finished(*_):
        open(done, "w").write("ok")

    bpy.app.handlers.render_complete.append(finished)
    bpy.app.handlers.render_cancel.append(finished)

    def start():
        win = bpy.context.window_manager.windows[0]
        with bpy.context.temp_override(window=win):
            bpy.ops.render.render("INVOKE_DEFAULT", animation=True)
        return None

    bpy.app.timers.register(start, first_interval=3.0)
