"""Helper renderer for a second machine: renders full-quality frames backward from the end and hands each one to the
render PC, which renders forward and skips frames that already exist. Gentle on the helper: run under `nice`, and it
pauses between frames so the desktop stays usable.

blender -b ep1.blend -P mac_helper.py -- <host> <remote frames dir> <local tmp dir> [pause seconds]
Stop it any time with:  touch ~/stop_render   (it finishes the current frame; the PC renders whatever is left)
"""
import bpy, os, subprocess, sys, time

host, rdir, ldir = sys.argv[sys.argv.index("--") + 1:][:3]
pause = float(sys.argv[sys.argv.index("--") + 4]) if len(sys.argv) > sys.argv.index("--") + 4 else 4.0
stop = os.path.expanduser("~/stop_render")
os.makedirs(ldir, exist_ok=True)

scn = bpy.context.scene
scn.render.resolution_x, scn.render.resolution_y, scn.render.resolution_percentage = 1080, 1920, 100
scn.render.image_settings.file_format, scn.render.image_settings.color_mode = "PNG", "RGB"
ee = scn.eevee
ee.taa_render_samples = 64
ee.use_raytracing, ee.use_bokeh_jittered, ee.use_fast_gi = True, True, True
ee.shadow_ray_count, ee.shadow_step_count = 2, 8

markers = sorted(scn.timeline_markers, key=lambda m: m.frame)


def cam_at(f):
    return [m for m in markers if m.frame <= f][-1].camera


def ssh(cmd):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, cmd], capture_output=True, text=True).returncode


done = 0
for f in range(scn.frame_end, scn.frame_start - 1, -1):
    if os.path.exists(stop):
        print("HELPER stop file found")
        break
    remote = f"{rdir}/f_{f:04d}.png"
    local = os.path.join(ldir, f"f_{f:04d}.png")
    if os.path.exists(local) and os.path.getsize(local) > 0:  # rendered and handed over by an earlier run
        continue
    if ssh(f"set -o noclobber; : > {remote}") != 0:  # already there or claimed by the PC: we have met in the middle
        print("HELPER met the PC at frame", f)
        break
    t = time.time()
    scn.frame_set(f)
    scn.camera = cam_at(f)
    scn.render.filepath = local
    bpy.ops.render.render(write_still=True)
    for _ in range(3):
        if subprocess.run(["scp", "-q", "-o", "BatchMode=yes", local, f"{host}:{remote}"]).returncode == 0:
            break
        time.sleep(5)
    done += 1
    print(f"HELPER frame {f} in {time.time() - t:.1f}s ({done} done)", flush=True)
    time.sleep(pause)
print("HELPER finished,", done, "frames")
