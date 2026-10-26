# ----------------------------------------------------------------------------------------------- style frames
# blender -b --factory-startup -P sf.py -- <outdir> <height> <samples> [ids]
HS = Vector((0, 300, 300))         # hot section: a turbine disc in the flame, dark world (near the origin: float precision)
HB = HS + Vector((0, 3.0, 0))      # hero blade in the gas stream


def setv(m, name, v):
    m.node_tree.nodes[name].outputs[0].default_value = v


def fire_mat(name, axis_r=True, strength=26.0):
    """combustion gas as an emissive volume: streaks stretched along +x, white-hot upstream, orange downstream"""
    m, nt, out = new_mat(name)
    P = obj_co(nt)
    x, y, z = xyz(nt, P)
    W = val(nt, "W", 0.0)
    nz = node(nt, "ShaderNodeTexNoise", noise_dimensions="4D")
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 7.0
    nz.inputs["Roughness"].default_value = 0.62
    sc = node(nt, "ShaderNodeVectorMath", operation="MULTIPLY")
    sc.inputs[1].default_value = (7.0, 70.0, 70.0)
    link(nt, P, sc.inputs[0])
    link(nt, sc.outputs[0], nz.inputs["Vector"])
    link(nt, W, nz.inputs["W"])
    n = nz.outputs[0]
    if axis_r:   # an annulus round the x axis, through the blade ring
        r = mth(nt, "SQRT", mth(nt, "ADD", mth(nt, "MULTIPLY", y, y), mth(nt, "MULTIPLY", z, z)))
        band = mul(nt, sstep(nt, r, 0.262, 0.29), inv(nt, sstep(nt, r, 0.36, 0.40)))
    else:        # a slab of gas around the hero blade
        band = mul(nt, sstep(nt, z, -0.012, 0.004), inv(nt, sstep(nt, z, 0.058, 0.075)))
    up = inv(nt, sstep(nt, x, -0.2, 0.12))                 # 1 upstream .. 0 downstream
    ends = mul(nt, sstep(nt, x, -0.34, -0.22), inv(nt, sstep(nt, x, -0.03, 0.10)))
    d = mul(nt, band, ends, mth(nt, "MAXIMUM", mth(nt, "SUBTRACT", n, mth(nt, "MULTIPLY_ADD", up, -0.08, 0.56)), 0.0))
    T = mth(nt, "MULTIPLY_ADD", up, 0.32, mth(nt, "MULTIPLY", n, 0.5))
    col = ramp3(nt, T, [(0.15, "#a51a04"), (0.4, "#ff4d0a"), (0.62, "#ff9b2e"), (0.8, "#ffd88a"), (1.0, "#fff4de")])
    v = node(nt, "ShaderNodeVolumePrincipled")
    v.inputs["Color"].default_value = (*lin("#2a1a12"), 1)
    link(nt, mth(nt, "MULTIPLY", d, 6.0), v.inputs["Density"])
    link(nt, col, v.inputs["Emission Color"])
    link(nt, mth(nt, "MULTIPLY", d, strength), v.inputs["Emission Strength"])
    link(nt, v.outputs[0], out.inputs["Volume"])
    return m


def haze_mat(name, density, col="#ffffff"):
    m, nt, out = new_mat(name)
    v = node(nt, "ShaderNodeVolumeScatter")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*lin(col), 1)
    v.inputs["Anisotropy"].default_value = 0.4
    link(nt, v.outputs[0], out.inputs["Volume"])
    return m


def vol_box(name, c, s, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = V(v.co.x * s[0], v.co.y * s[1], v.co.z * s[2])
    return obj_from_bm(name, bm, mat, None, c)


def embers(name, c, n, box, seed=5):
    random.seed(seed)
    m = emis("Ember", "#ffb35a", 18.0)
    bm = bmesh.new()
    for _ in range(n):
        p = V(random.uniform(-box[0], box[0]), random.uniform(-box[1], box[1]), random.uniform(-box[2], box[2]))
        r = random.uniform(0.00025, 0.0006)
        bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=r,
                                  matrix=Matrix.Translation(p) @ Matrix.Diagonal((6.0, 1.0, 1.0, 1.0)))
    return obj_from_bm(name, bm, m, None, c)


def sun_lamp(d, strength, col, angle=0.6):
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy = strength
    ld.color = lin(col)
    ld.angle = rad(angle)
    ob = bpy.data.objects.new("Sun", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (-Vector(d)).to_track_quat("-Z", "Y")
    return ob


def place_cam(camo, eye, tgt, lens, fstop=11.0, roll=0.0, focus=None):
    eye, tgt = Vector(eye), Vector(tgt)
    camo.location = eye
    camo.rotation_quaternion = (tgt - eye).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), rad(roll))
    camo.data.lens = lens
    camo.data.dof.aperture_fstop = fstop
    camo.data.dof.focus_distance = focus or (tgt - eye).length


def build_sf():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    M = materials()
    M["livery"] = livery_mat()
    M["wingpaint"] = pbr("WingPaint", "#c3c7cc", 0.34, 0.25)
    M["tailpaint"] = pbr("TailPaint", "#14254a", 0.3, 0.0)
    for k in ("wingpaint", "tailpaint"):
        b = M[k].node_tree.nodes["Principled BSDF"]
        b.inputs["Coat Weight"].default_value = 0.7
        b.inputs["Coat Roughness"].default_value = 0.08
    pb = M["paint"].node_tree.nodes["Principled BSDF"]       # nacelles in white paint
    pb.inputs["Base Color"].default_value = (*lin("#e6e8ea"), 1)
    pb.inputs["Metallic"].default_value = 0.0
    pb.inputs["Roughness"].default_value = 0.3
    world = sky_world(1.4, 96.5)
    me_blade, rxr = blade_mesh("Blade")
    me_blade.materials.append(M["bladeD"])
    A = build_airliner(M, me_blade, rxr)
    clouds = cloud_deck(-700.0, -1600.0, 40000.0)
    sun = sun_lamp((-0.97, -0.11, 0.07), 4.5, "#ffb070")
    # hot section: disc in the flame, haze, embers, fire lights
    disc, body, posts, blades = build_disc(M, "HotDisc", me_blade, rxr, loc=HS)
    fire = vol_box("Fire", HS + V(-0.02, 0, 0), (0.70, 0.84, 0.84), fire_mat("Fire", strength=420.0))
    haze = vol_box("Haze", HS, (2.0, 2.0, 2.0), haze_mat("Haze", 0.004, "#ffd2a8"))
    emb = embers("Embers", HS + V(0.05, 0, 0.33), 1, (0.25, 0.25, 0.05))
    hot = [disc, fire, haze, emb]
    for name, loc, tgt, sx, sy, col, e in (
            ("Hfire", HS + V(-0.35, 0.0, 0.33), HS + V(0, 0, 0.33), 0.3, 0.3, "#ff7a2a", 12),
            ("Hfire2", HS + V(-0.30, -0.25, 0.25), HS + V(0, 0, 0.33), 0.3, 0.3, "#ff5a10", 0),
            ("Hkey", HS + V(0.6, -0.45, 0.75), HS + V(0, 0, 0.33), 0.5, 0.25, "#cfd8e6", 8)):
        hot.append(area(name, loc, tgt, sx, sy, col, e))
    # hero blade in the gas slab, cooling air out of its holes
    hero = mesh_obj("Hero", me_blade, None)
    hero.location = HB
    hero.material_slots[0].link = "OBJECT"
    hero.material_slots[0].material = M["bladeH"]
    P = build_blade_parts(M, me_blade, hero)
    for k, ob in P.items():
        ob.hide_render = k not in ("film",)
    setv(M["bladeH"], "FC", 1.0)
    setv(M["bladeH"], "TB", 0.62)
    setv(M["film"], "S", 1.0)
    setv(M["film"], "FG", 1.0)
    gas = vol_box("GasB", HB + V(-0.02, 0.0, 0.025), (0.62, 0.20, 0.11), fire_mat("FireB", axis_r=False, strength=380.0))
    hazeb = vol_box("HazeB", HB, (1.2, 1.2, 1.2), haze_mat("HazeB", 0.004, "#ffd2a8"))
    embb = embers("EmbersB", HB + V(0, 0.03, 0.025), 1, (0.2, 0.06, 0.04), 9)
    herog = [hero, gas, hazeb, embb, *P.values()]
    for name, loc, tgt, sx, sy, col, e in (
            ("Bfire", HB + V(-0.25, 0.10, 0.03), HB + V(0, 0, 0.03), 0.2, 0.2, "#ff6a1a", 6),
            ("Bkey", HB + V(0.35, -0.45, 0.35), HB + V(0, 0, 0.03), 0.4, 0.18, "#d6e0ee", 2.5),
            ("Brim", HB + V(0.1, 0.35, 0.15), HB + V(0, 0, 0.03), 0.04, 0.5, "#ffb070", 4)):
        herog.append(area(name, loc, tgt, sx, sy, col, e))
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_start, cd.clip_end = 0.01, 40000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    return dict(M=M, A=A, clouds=clouds, sun=sun, world=world, hot=hot, hero=herog, cam=camo)


def frames(W):
    bpy.context.view_layer.update()
    eng = W["A"]["engines"][0]["root"].matrix_world.translation.copy()
    fan = eng + V(-1.7, 0, 0)
    return {
        "wide": dict(sky=True, eye=(-70, 92, -16), tgt=(-1, 0, -2), lens=50, fstop=16),
        "engine": dict(sky=True, eye=tuple(fan + V(-9.5, 6.5, -2.4)), tgt=tuple(fan + V(1.2, -0.8, 0.6)), lens=30,
                       fstop=11),
        "fan": dict(sky=True, eye=tuple(fan + V(-4.2, 2.2, -0.8)), tgt=tuple(fan + V(0, -0.2, 0.05)), lens=24,
                    fstop=8),
        "hot": dict(hot=True, eye=tuple(HS + V(0.40, -0.26, 0.47)), tgt=tuple(HS + V(-0.02, 0.0, 0.31)), lens=45,
                    fstop=8),
        "hero": dict(hero=True, eye=tuple(HB + V(0.07, -0.23, 0.06)), tgt=tuple(HB + V(0.0, 0.0, 0.022)),
                     lens=70, fstop=8),
    }


def render_sf(W, outdir, h, samples, ids, setup=True):
    scn = bpy.context.scene
    if setup:
        render_settings(scn, h, samples)
    scn.render.use_motion_blur = False
    scn.cycles.volume_bounces = 1
    os.makedirs(outdir, exist_ok=True)
    bg = W["world"].node_tree.nodes["Background"]
    for k, F in frames(W).items():
        if ids and k not in ids:
            continue
        sky = F.get("sky", False)
        bg.inputs[1].default_value = 0.3 if sky else 0.0
        W["sun"].hide_render = not sky
        W["clouds"].hide_render = not sky
        for ob in W["hot"]:
            ob.hide_render = not F.get("hot", False)
        for ob in W["hero"]:
            if ob.name.startswith(("Channels", "Blanket", "Selector")):
                continue
            ob.hide_render = not F.get("hero", False)
        place_cam(W["cam"], F["eye"], F["tgt"], F["lens"], F["fstop"])
        scn.render.filepath = os.path.join(outdir, f"{k}.png")
        bpy.ops.render.render(write_still=True)
        print("DONE", k)


def bench(W, outdir, h, samples, ids):
    """time the same frames under several device setups"""
    import time
    scn = bpy.context.scene
    pr = bpy.context.preferences.addons["cycles"].preferences
    print("PROPS", [p.identifier for p in pr.bl_rna.properties if "hip" in p.identifier.lower() or "rt" == p.identifier[-2:]])
    for tag, kind, cpu, hiprt in (("hip", "HIP", False, False), ("hiprt", "HIP", False, True),
                                  ("hip+cpu", "HIP", True, False), ("cpu", "NONE", True, False)):
        pr.compute_device_type = kind if kind != "NONE" else "NONE"
        pr.get_devices()
        for d in pr.devices:
            d.use = (d.type == "CPU" and cpu) or (d.type == kind)
        if hasattr(pr, "use_hiprt"):
            pr.use_hiprt = hiprt
        elif hiprt:
            continue
        scn.render.engine = "CYCLES"
        scn.cycles.device = "GPU" if kind != "NONE" else "CPU"
        print("CFG", tag, [(d.name, d.use) for d in pr.devices], flush=True)
        for k in ids:
            t0 = time.time()
            render_sf(W, os.path.join(outdir, tag), h, samples, [k], setup=False)
            print("TIME", tag, k, round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = build_sf() if argv[0] not in ("film", "benchdev") else None
    if W is None:
        pass
    elif argv[0] == "bench":
        render_settings(bpy.context.scene, int(argv[2]), int(argv[3]))
        bench(W, argv[1], int(argv[2]), int(argv[3]), argv[4].split(","))
        sys.exit(0)
    else:
        render_sf(W, argv[0], int(argv[1]), int(argv[2]), argv[3].split(",") if len(argv) > 3 else None)
