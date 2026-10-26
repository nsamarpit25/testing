# ----------------------------------------------------------------------------------------------- device bench
if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "benchdev":
    import time
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = film_world()
    bake(W, os.path.join(argv[1] + "_labels.json"))
    scn = bpy.context.scene
    render_settings(scn, int(argv[2]), int(argv[3]))
    pr = bpy.context.preferences.addons["cycles"].preferences
    os.makedirs(argv[1], exist_ok=True)
    for tag, cpu, dgpu, tile in (("hip+cpu", True, False, 2048), ("hip", False, False, 2048),
                                 ("hip+cpu dgpu", True, True, 2048), ("hip dgpu", False, True, 2048),
                                 ("hip dgpu t1024", False, True, 1024), ("hip+cpu dgpu t512", True, True, 512)):
        for d in pr.devices:
            d.use = d.type == "HIP" or (cpu and d.type == "CPU")
        try:
            scn.cycles.denoising_use_gpu = dgpu
        except Exception as e:
            print("no dgpu", e, flush=True)
        scn.cycles.tile_size = tile
        for f in [int(x) for x in argv[4].split(",")]:
            scn.frame_set(f)
            scn.render.filepath = os.path.join(argv[1], f"{tag.replace(' ', '_')}_{f}.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print("TIME", tag, f, round(time.time() - t0, 2), flush=True)
