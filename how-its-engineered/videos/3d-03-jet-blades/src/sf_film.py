# ----------------------------------------------------------------------------------------------- film (new look)
# The airliner above the clouds -> its engine -> the turbine in the flame -> the hero blade in the gas stream.
# blender -b --factory-startup -P sf.py -- film <outdir> <height> <samples> <a-b>
BG = 'nodes["Background"].inputs[1].default_value'
CRUISE = 240.0                     # m/s: the cloud deck scrolls past at cruise speed
VOL_STEP_RATE = 3.0                # coarser volume steps: the fire and clouds are soft, 3x fewer steps is invisible


def film_world():
    W = build_sf()
    for k in ("hot", "hero"):        # the faint haze boxes cost more than they add
        for ob in [o for o in W[k] if o.name.startswith("Haze")]:
            W[k].remove(ob)
            bpy.data.objects.remove(ob)
    W["herog"] = W.pop("hero")
    W["hero"] = [o for o in W["herog"] if o.name == "Hero"][0]
    W["hero"].rotation_mode = "QUATERNION"
    W["fire"] = bpy.data.materials["Fire"]
    W["fireB"] = bpy.data.materials["FireB"]
    W["disc"] = [o for o in W["hot"] if o.name == "HotDisc"][0]
    by = {o.name: o for o in W["herog"]}
    W["P"] = {k: by[n] for k, n in (("chan", "Channels"), ("film", "Film"), ("blanket", "Blanket"),
                                     ("tbcS", "TBC_tbcS"), ("tbcP", "TBC_tbcP"), ("selector", "Selector"),
                                     ("gasN", "Gas_gasN"), ("gasF", "Gas_gasF"))}
    return W


def defaults(t, S, W):
    put(S, W["world"].node_tree, BG, 0.0)
    for ob in (W["sun"], W["clouds"], *W["hot"], *W["herog"]):
        put(S, ob, "hide_render", 1, const=True)
    for ob in W["P"].values():
        put(S, ob, "hide_render", 1, const=True)
    put(S, W["clouds"], "location", t * CRUISE, 0)
    for G in W["A"]["engines"]:
        put(S, G["fan"], "rotation_euler", t * 2 * math.pi * 5.0, 0)
        put(S, G["spool"], "rotation_euler", t * 2 * math.pi * 9.0, 0)
    put(S, W["disc"], "rotation_euler", t * 0.8, 0)
    G0 = W["A"]["engines"][0]
    put(S, G0["root"], "rotation_euler", 0.0, 0)
    for k in ("nacCut", "cowlCut"):
        for i in range(3):
            put(S, G0[k], "location", 0.0, i)
        put(S, G0[k], "hide_render", 0, const=True)
    put(S, G0["gas"], "hide_render", 1, const=True)
    mset(S, W["fire"], W=t * 1.6)
    mset(S, W["fireB"], W=t * 1.6)
    M = W["M"]
    mset(S, M["bladeH"], G=0.0, GB=0.0, FC=0.0, CK=0.0, SM=0.0, SF=-0.07, XA=0.0, XZ=0.07)
    mset(S, M["bladeD"], FC=0.0)
    mset(S, M["film"], S=0.0, FG=0.0, P=t * 1.2)
    mset(S, M["chan"], S=0.0, CF=0.0, P=t * 1.4)
    mset(S, M["blanket"], S=0.0)
    mset(S, M["tbc"], HF=0.0)
    for k in ("tbcS", "tbcP"):
        for i in range(3):
            put(S, W["P"][k], "location", 0.0, i)
            put(S, W["P"][k], "rotation_euler", 0.0, i)
    put(S, W["hero"], "scale", 1.0, 2)
    q = Quaternion((0, 0, 1), 0.0)
    for k in range(4):
        put(S, W["hero"], "rotation_quaternion", q[k], k)


def sky_on(S, W):
    put(S, W["world"].node_tree, BG, 0.3)
    for ob in (W["sun"], W["clouds"]):
        put(S, ob, "hide_render", 0, const=True)


def show(S, obs):
    for ob in obs:
        if not ob.name.startswith(("Channels", "Film", "Blanket", "Selector", "TBC_", "Gas_")):
            put(S, ob, "hide_render", 0, const=True)


def reveal(S, W, *keys):
    for k in keys:
        put(S, W["P"][k], "hide_render", 0, const=True)


def hcam(S, az, el, dist, lens=70, tz=0.025, fstop=8, shake=0.0, t=0.0):
    """camera on the hero blade in the gas stream: azimuth az (deg, 0 = from -y), elevation el, distance dist"""
    c = HB + V(0, 0, tz)
    eye = c + Matrix.Rotation(rad(az), 3, "Z") @ V(0, -dist * math.cos(rad(el)), dist * math.sin(rad(el)))
    cam(S, eye, c, lens=lens, fstop=fstop, shake=shake, t=t)


def hp(deg, p):
    """blade-frame point -> world, hero turned deg about z"""
    return HB + Matrix.Rotation(rad(deg), 3, "Z") @ Vector(p)


def hero_rot(S, W, deg):
    q = Quaternion((0, 0, 1), rad(deg))
    for k in range(4):
        put(S, W["hero"], "rotation_quaternion", q[k], k)


def shots(W):
    L = []
    bpy.context.view_layer.update()
    fan = W["A"]["engines"][0]["root"].matrix_world.translation.copy() + V(-1.7, 0, 0)

    def A(t, S):     # "Jet engine blades spin": the airliner cruising above a sea of cloud at golden hour
        sky_on(S, W)
        u = ss(seg(t, 0.0, 1.6))
        cam(S, V(lerp(-78, -64, u), lerp(97, 89, u), lerp(-19, -15, u)), V(-1, 0, -2), lens=lerp(48, 54, u), fstop=16)
    L.append((0.0, 1.6, A))

    def B(t, S):     # "in gas up to two hundred": push in on the engine, the fan a blur
        sky_on(S, W)
        u = ss(seg(t, 1.6, 2.9))
        eye = fan + V(lerp(-12.5, -4.2, u), lerp(8.2, 6.4, u), lerp(-2.9, -1.1, u))
        cam(S, eye, fan + V(lerp(1.2, 1.7, u), lerp(-0.8, 0.0, u), lerp(0.55, 0.05, u)), lens=30, fstop=11)
        # cut the near quarter of the nacelle away to show the combustor and the hot turbine deep in the core
        G0 = W["A"]["engines"][0]
        put(S, G0["root"], "rotation_euler", rad(-160), 0)     # turn the cutaway sector to face the camera
        mset(S, W["M"]["flame"], S=40.0)
        mset(S, W["M"]["gas"], S=1.5)
        put(S, G0["gas"], "hide_render", 0, const=True)
        k = ss(seg(t, 2.0, 2.4))
        for key in ("nacCut", "cowlCut"):
            for i, d in enumerate((0.0, -0.883, 0.469)):
                put(S, G0[key], "location", d * 4.5 * k, i)
            if k > 0.98:
                put(S, G0[key], "hide_render", 1, const=True)
        if t > 2.2:
            label(S, "core", fan + V(2.28, 0, 0))
    L.append((1.6, 2.9, B))

    def C(t, S):     # "degrees Celsius above their melting point": inside, the turbine wheel turning in the flame
        show(S, W["hot"])
        u = ss(seg(t, 2.9, 4.85))
        cam(S, HS + V(lerp(0.42, 0.37, u), lerp(-0.30, -0.15, u), lerp(0.46, 0.50, u)), HS + V(-0.02, 0.0, 0.31),
            lens=45, fstop=8)
    L.append((2.9, 4.85, C))

    def D(t, S):     # "Each palm-sized blade": the hero blade alone in the gas stream
        show(S, W["herog"])
        u = ss(seg(t, 4.85, 6.4))
        hero_rot(S, W, lerp(-28, -12, u))
        cam(S, HB + V(lerp(0.10, 0.07, u), lerp(-0.32, -0.23, u), lerp(0.08, 0.06, u)), HB + V(0, 0, 0.022),
            lens=70, fstop=8)
    L.append((4.85, 6.4, D))

    def E(t, S):     # "makes the power of a Formula One car": low orbit, the blade as a monument
        show(S, W["herog"])
        u = ss(seg(t, 6.4, 8.15))
        a = rad(lerp(-62, -38, u))
        hero_rot(S, W, -12)
        cam(S, HB + V(0.20 * math.sin(a), -0.20 * math.cos(a), lerp(0.004, 0.012, u)), HB + V(0, 0, 0.03),
            lens=55, fstop=8)
        label(S, "blade", hp(-12, (0.0, 0.0, H_AF - 0.004)))
    L.append((6.4, 8.15, E))

    def F(t, S):     # "Normal metal is a patchwork of tiny crystals": close, the grains etch in
        show(S, W["herog"])
        u = ss(seg(t, 8.15, 10.0))
        hero_rot(S, W, -18)
        mset(S, W["M"]["bladeH"], G=ss(seg(t, 8.4, 9.2)), GB=0.8 * ss(seg(t, 8.9, 9.8)))
        cam(S, HB + V(lerp(0.035, 0.025, u), lerp(-0.13, -0.105, u), lerp(0.045, 0.04, u)), HB + V(0, 0, 0.03),
            lens=70, fstop=8)
        label(S, "grains", hp(-18, af_point(-0.004, 0.032)[0]))
    L.append((8.15, 10.9, F))

    M, P = W["M"], W["P"]

    def G(t, S):     # "Heat and pull crack it along the seams": the blade strains, a crack runs along the boundaries
        show(S, W["herog"])
        hero_rot(S, W, -18)
        jit = 0.0025 * math.sin(t * 61) * seg(t, 11.3, 11.6)
        put(S, W["hero"], "scale", 1.0 + 0.02 * ss(seg(t, 11.2, 12.0)) + jit, 2)
        mset(S, M["bladeH"], G=1.0, GB=0.8, CK=ss(seg(t, 11.55, 12.9)))
        u = ss(seg(t, 10.9, 13.4))
        hcam(S, 14, 14, lerp(0.15, 0.13, u), tz=0.03, shake=0.35 * seg(t, 11.3, 11.7), t=t)
        label(S, "crack", hp(-18, af_point(0.0, 0.0302)[0]))
    L.append((10.9, 13.4, G))

    def H(t, S):     # "So each blade is grown as one single crystal": one crystal grows up out of the spiral selector
        show(S, W["herog"])
        reveal(S, W, "selector")
        hero_rot(S, W, -22)
        sf = lerp(Z_ROOT1 - 0.036, H_AF + 0.003, ss(seg(t, 13.45, 15.35)))
        mset(S, M["bladeH"], SM=1.0, SF=sf)
        hcam(S, lerp(10, 16, seg(t, 13.4, 15.5)), 9, 0.40, tz=-0.008)
        label(S, "crystal", hp(-22, (0, 0, clamp(sf, Z_ROOT1, H_AF))))
    L.append((13.4, 15.5, H))

    def I(t, S):     # "No seams": the finished blade turns, one flawless surface
        show(S, W["herog"])
        u = seg(t, 15.5, 17.55)
        hero_rot(S, W, lerp(-48, 4, u))
        hcam(S, 16, 12, lerp(0.30, 0.27, ss(u)), tz=0.02)
    L.append((15.5, 17.55, I))

    def J(t, S):     # "Inside, cool air snakes through hidden channels": an x-ray wipe from the tip down
        show(S, W["herog"])
        reveal(S, W, "chan")
        hero_rot(S, W, -10)
        mset(S, M["chan"], S=1.0, CF=0.35)
        mset(S, M["bladeH"], XA=1.0, XZ=lerp(H_AF + 0.003, Z_ROOT1 - 0.004, ss(seg(t, 17.6, 18.6))))
        hcam(S, 14, 10, 0.38, tz=0.012)
    L.append((17.55, 18.75, J))

    def K(t, S):     # cool air races up and down the passage
        show(S, W["herog"])
        reveal(S, W, "chan")
        u = seg(t, 18.75, 19.95)
        hero_rot(S, W, lerp(-10, -2, u))
        mset(S, M["chan"], S=1.0, CF=1.0)
        mset(S, M["bladeH"], XA=1.0, XZ=Z_ROOT1 - 0.006)
        hcam(S, 14, 10, lerp(0.38, 0.32, ss(u)), tz=0.016)
        label(S, "chan", hp(lerp(-10, -2, u), camber_pt(0.20, 0.036)[0]))
    L.append((18.75, 19.95, K))

    def Lh(t, S):    # "then streams from tiny holes": closer, cool air streams out of every hole
        show(S, W["herog"])
        reveal(S, W, "film")
        hero_rot(S, W, -24)
        mset(S, M["bladeH"], FC=ss(seg(t, 20.0, 20.4)))
        mset(S, M["film"], S=1.0, FG=ss(seg(t, 20.1, 21.1)))
        hcam(S, 18, 14, lerp(0.21, 0.19, seg(t, 19.95, 21.45)), tz=0.03)
        label(S, "holes", hp(-24, af_point(-0.0110, 0.040)[0]))
    L.append((19.95, 21.45, Lh))

    def Mb(t, S):    # "to blanket the surface": the whole blade wrapped in a film of cool air
        show(S, W["herog"])
        reveal(S, W, "film", "blanket")
        u = seg(t, 21.45, 23.1)
        hero_rot(S, W, lerp(-30, -16, u))
        mset(S, M["bladeH"], FC=1.0)
        mset(S, M["film"], S=1.0, FG=1.0)
        mset(S, M["blanket"], S=ss(seg(t, 21.5, 22.3)))
        hcam(S, 15, 10, lerp(0.38, 0.35, u), tz=0.02)
        label(S, "film", hp(lerp(-30, -16, u), af_point(-0.014, 0.046, off=0.0006)[0]))
    L.append((21.45, 23.1, Mb))

    def shells(S, k):
        for key, sgn in (("tbcS", 1), ("tbcP", -1)):
            reveal(S, W, key)
            put(S, P[key], "location", sgn * 0.016 * k, 1)
            put(S, P[key], "location", 0.006 * k, 2)
            put(S, P[key], "rotation_euler", sgn * rad(-10) * k, 0)

    def N(t, S):     # "On top, a ceramic coat": the coated blade, the coat lifts away from the metal
        show(S, W["herog"])
        u = seg(t, 23.1, 24.55)
        hero_rot(S, W, lerp(62, 74, u))
        shells(S, ss(seg(t, 23.5, 24.4)))
        hcam(S, 16, 14, 0.42, tz=0.02)
        label(S, "tbc", hp(lerp(62, 74, u), af_point(0.009, 0.044, off=0.0008)[0]))
    L.append((23.1, 24.55, N))

    def O(t, S):     # "holds back more heat": the coat's outer face takes the heat, the metal inside stays cool
        show(S, W["herog"])
        u = seg(t, 24.55, 26.0)
        hero_rot(S, W, lerp(74, 92, u))
        shells(S, 1.0)
        mset(S, M["tbc"], HF=ss(seg(t, 24.6, 25.3)))
        hcam(S, 16, 14, lerp(0.40, 0.36, u), tz=0.02)
    L.append((24.55, 26.0, O))

    def Pp(t, S):    # "So the metal never reaches its melting point": back in the flame, the wheel turning, holes breathing
        show(S, W["hot"])
        mset(S, M["bladeD"], FC=1.0)
        u = ss(seg(t, 26.0, 28.6))
        cam(S, HS + V(lerp(0.36, 0.50, u), lerp(-0.16, -0.40, u), lerp(0.50, 0.56, u)),
            HS + V(-0.02, 0.0, lerp(0.31, 0.26, u)), lens=lerp(50, 40, u), fstop=8)
    L.append((26.0, 28.6, Pp))

    def Q(t, S):     # "Follow for how the world is really engineered": the airliner sails on into the evening
        sky_on(S, W)
        u = ss(seg(t, 28.6, T_END))
        cam(S, V(lerp(-46, -96, u), lerp(58, 104, u), lerp(-9, -21, u)), V(lerp(-6, 4, u), 0, -2),
            lens=lerp(40, 46, u), fstop=16)
    L.append((28.6, T_END + 0.1, Q))
    return L


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = film_world()
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_film.json"))
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
