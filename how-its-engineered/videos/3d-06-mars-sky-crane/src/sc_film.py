# ----------------------------------------------------------------------------------------------- film
# blender -b --factory-startup -P sc.py -- film <outdir> <height> <samples> <a-b | f,f,f>
T_END = 32.2
F_END = int(T_END * FPS) + 1
BG = 'nodes["BG"].inputs[1].default_value'
SUNE = 3.6
STOW = 55.0                     # wheel fold angle while stowed


def sc_world():
    W = build_sc()
    for i, pl in enumerate(W["S"]["plumes"]):          # one engine per pod keeps running in the sky crane phase
        if i % 2:
            pl.data.materials[0] = W["M"]["plumeB"]
    return W


def defaults(t, S, W):
    M, R, St = W["M"], W["R"], W["S"]
    put(S, W["world"].node_tree, BG, 1.0)
    mset(S, W["world"], STU=0.0)
    put(S, W["sun"].data, "energy", SUNE)
    for ob in W["mars"]:
        put(S, ob, "hide_render", 0, const=True)
    for ob in [W["floorS"], W["bags"]["ball"], W["dust"], W["dustT"], W["dustC"], W["flash"]] + W["sparks"] + \
            W["fly"] + W["BR"] + St["parts"] + St["plumes"]:
        put(S, ob, "hide_render", 1, const=True)
    for ob in R["parts"]:
        put(S, ob, "hide_render", 0, const=True)
    for i in range(3):
        put(S, R["root"], "location", 0.0, i)
        put(S, R["root"], "rotation_euler", 0.0, i)
        put(S, St["root"], "location", (0.0, 0.0, -500.0)[i], i)
        put(S, St["root"], "rotation_euler", 0.0, i)
        put(S, W["bags"]["ball"], "scale", 1.0, i)
    put(S, W["bags"]["ball"], "location", 2.15, 2)
    for sd in R["sides"]:
        put(S, sd, "rotation_euler", 0.0, 0)
    put(S, R["mast"], "rotation_euler", rad(-90.0), 1)
    mset(S, M["plume"], S=0.0, W=t * 6.0)
    mset(S, M["plumeB"], S=0.0, W=t * 6.0 + 3.0)
    for k in ("dust", "dustT", "dustC"):
        mset(S, M[k], D=0.0, W=t * 0.35)
    mset(S, M["reg"], SC=0.0)
    mset(S, M["flash"], S=0.0)
    mset(S, M["spark"], S=0.0)
    put(S, St["glow"].data, "energy", 0.0)
    for lt in W["lights"]:
        put(S, lt.data, "energy", 0.0)


def fold(S, W, k):
    """k = 1 stowed (wheels folded up beside the body), 0 deployed"""
    for sd, s in zip(W["R"]["sides"], (1, -1)):
        put(S, sd, "rotation_euler", rad(STOW * s * k), 0)


def stage(S, W, p, pitch=0.0, yaw=0.0, burn=1.0, burnB=1.0):
    St = W["S"]
    for ob in St["parts"] + St["plumes"]:
        put(S, ob, "hide_render", 0, const=True)
    for i in range(3):
        put(S, St["root"], "location", p[i], i)
    put(S, St["root"], "rotation_euler", rad(pitch), 1)
    put(S, St["root"], "rotation_euler", rad(yaw), 2)
    mset(S, W["M"]["plume"], S=burn)
    mset(S, W["M"]["plumeB"], S=burnB)


def hang(S, W, belly, L, fold_k=0.0, burn=1.0, burnB=0.0, cables=True, glow=0.0):
    """the sky crane: the stage with its belly at `belly`, the rover L metres further down on the bridles"""
    belly = Vector(belly)
    stage(S, W, belly, burn=burn, burnB=burnB)
    rz = belly.z - (HANG + L)
    for i, v in enumerate((belly.x, belly.y, rz)):
        put(S, W["R"]["root"], "location", v, i)
    fold(S, W, fold_k)
    if cables:
        ln = belly.z - 0.15 - (rz + DECK + 0.06)
        for b in W["BR"]:
            a = Vector(b["att"])
            put(S, b, "hide_render", 0, const=True)
            for i, v in enumerate((belly.x + a.x, belly.y + a.y, belly.z - 0.15)):
                put(S, b, "location", v, i)
            put(S, b, "scale", max(ln, 0.01), 2)
    put(S, W["S"]["glow"].data, "energy", glow)
    return rz


def dust(S, W, key, c, R, H, D, t=None):
    ob = W[key]
    put(S, ob, "hide_render", 0, const=True)
    for i in range(3):
        put(S, ob, "location", c[i], i)
    put(S, ob, "scale", R, 0)
    put(S, ob, "scale", R, 1)
    put(S, ob, "scale", H, 2)
    mset(S, W["M"][key], D=D)


def studio(S, W):
    for ob in W["mars"]:
        put(S, ob, "hide_render", 1, const=True)
    put(S, W["floorS"], "hide_render", 0, const=True)
    mset(S, W["world"], STU=1.0)
    put(S, W["sun"].data, "energy", 0.0)
    for lt in W["lights"]:
        put(S, lt.data, "energy", {"Key": 2600.0, "Rim": 4200.0, "Top": 1400.0}[lt.name])


def gz(x, y):
    return ground(x, y)


def shots(W):
    M = W["M"]
    L = []
    O = V(0, 0, 0)

    def A(t, S):     # "To land a one-tonne rover on Mars": from the ground, the sky crane coming down out of the sky
        u = ss(seg(t, 0.0, 2.1))
        belly = V(2.0, 1.0, lerp(17.5, 15.5, u))
        hang(S, W, belly, 6.0, burn=1.0, glow=0.0)
        cam(S, V(lerp(-15, -13, u), lerp(-18, -16, u), 1.1), belly + V(0, 0, -4.4), lens=34, fstop=11, clip=0.1)
    L.append((0.0, 2.1, A))

    def B(t, S):     # "NASA hung it": close under the stage, looking up past the cables
        u = ss(seg(t, 2.1, 3.55))
        belly = V(0, 0, 15.0 - 0.6 * u)
        hang(S, W, belly, 6.0)
        a = rad(lerp(-150, -110, u))
        c = belly + V(0, 0, -4.2)
        cam(S, c + V(5.2 * math.cos(a), 5.2 * math.sin(a), -2.6), belly + V(0, 0, -0.2), lens=24, fstop=8, clip=0.05)
    L.append((2.1, 3.55, B))

    def B2(t, S):    # "from a flying rocket": side on, the whole rig against the sky, slow push
        u = ss(seg(t, 3.55, 4.95))
        belly = V(0, 0, 14.0 - 0.6 * u)
        hang(S, W, belly, 6.0)
        cam(S, belly + V(lerp(3, 2, u), lerp(-24, -20, u), -3.2), belly + V(0, 0, -3.6), lens=40, fstop=11, clip=0.1)
    L.append((3.55, 4.95, B2))

    def C(t, S):     # "too heavy for airbags": in the studio the rover drops onto an airbag ball and flattens it
        studio(S, W)
        put(S, W["bags"]["ball"], "hide_render", 0, const=True)
        k = ss(seg(t, 5.55, 5.95))
        sz, sxy = lerp(1.0, 0.58, k), lerp(1.0, 1.22, k)
        for i, v in enumerate((sxy, sxy, sz)):
            put(S, W["bags"]["ball"], "scale", v, i)
        put(S, W["bags"]["ball"], "location", 2.17 * sz, 2)
        top = 4.32 * sz
        z = max(lerp(9.5, top - 0.05, ein(seg(t, 4.95, 5.55))), top - 0.05)
        for i, v in enumerate((ST.x, ST.y, z)):
            put(S, W["R"]["root"], "location", v, i)
        u = ss(seg(t, 4.95, 6.45))
        cam(S, ST + V(lerp(9.5, 8.5, u), -11.0, 3.4), ST + V(0, 0, 3.3), lens=40, fstop=11, clip=0.1)
        label(S, "rover", ST + V(0.0, 0, z + 1.4))
        label(S, "bag", ST + V(-1.6, -1.2, 2.2 * sz))
    L.append((4.95, 6.45, C))

    def blast(S, t, t0=6.45):
        k = seg(t, t0, t0 + 3.4)
        dust(S, W, "dust", V(0, 0, -0.2), lerp(1.5, 9.0, eout(k)), lerp(0.6, 4.0, eout(k)), lerp(0.3, 0.9, ss(k * 3)))
        mset(S, M["reg"], SC=ss(seg(t, t0, t0 + 1.2)))
        for ob in W["fly"]:
            tf = t - (t0 + 0.35 + ob["dt"])
            if tf < 0:
                continue
            p0, v0 = Vector(ob["p0"]), Vector(ob["v0"])
            p = p0 + v0 * tf + V(0, 0, -0.5 * 3.71 * tf * tf)
            if p.z < -0.5:
                continue
            put(S, ob, "hide_render", 0, const=True)
            for i in range(3):
                put(S, ob, "location", p[i], i)
                put(S, ob, "rotation_euler", ob["spin"] * tf * (1, 0.7, 0.4)[i], i)

    def D(t, S):     # "and rockets firing near the ground": a lander with its engines close to the ground
        hang(S, W, V(0, 0, 3.4), 0.0, fold_k=1.0, burn=1.3, burnB=1.3, cables=False, glow=2500.0)
        blast(S, t)
        u = ss(seg(t, 6.45, 8.5))
        sh = 0.5 * seg(t, 6.8, 7.2)
        cam(S, V(lerp(-15, -13, u), lerp(-13, -11, u), 1.6), V(0, 0, 2.2), lens=28, fstop=11, clip=0.1, shake=sh,
            t=t * 4)
    L.append((6.45, 8.5, D))

    def E(t, S):     # "would blast dust and rocks everywhere": low by the ground, stones flying at the lens
        hang(S, W, V(0, 0, 3.4), 0.0, fold_k=1.0, burn=1.3, burnB=1.3, cables=False, glow=2500.0)
        blast(S, t)
        u = ss(seg(t, 8.5, 10.6))
        cam(S, V(lerp(-12.5, -11.5, u), lerp(-8.0, -7.4, u), 0.5), V(0, 0, 1.6), lens=30, fstop=8, clip=0.05,
            shake=0.8, t=t * 5)
    L.append((8.5, 10.6, E))

    def F(t, S):     # "So twenty metres up": side on, a long way down to the ground
        u = ss(seg(t, 10.6, 12.5))
        belly = V(0, 0, 20.5 - 0.4 * u)
        hang(S, W, belly, 0.0, fold_k=1.0, burn=1.0, burnB=lerp(1.0, 0.0, seg(t, 11.9, 12.3)), cables=False,
             glow=800.0)
        dust(S, W, "dustT", V(0, 0, -0.1), 9.0, 1.2, 0.25)
        cam(S, V(lerp(5, 3, u), -31.0, 7.0), V(0, 0, 10.5), lens=40, fstop=16, clip=0.2)
        label(S, "belly", belly)
        label(S, "gnd", V(0, 0, gz(0, 0)))
    L.append((10.6, 12.5, F))

    def G(t, S):     # "the descent stage slows to a crawl": close on the engines, four throttle down, four keep firing
        u = ss(seg(t, 12.5, 14.55))
        belly = V(0, 0, 19.8 - 0.75 * (t - 12.5))
        hang(S, W, belly, 0.0, fold_k=1.0, burn=1.0, burnB=lerp(0.6, 0.0, seg(t, 12.5, 13.1)), cables=False)
        dust(S, W, "dustT", V(0, 0, -0.1), 9.0, 1.2, 0.25)
        a = rad(lerp(-60, -35, u))
        cam(S, belly + V(5.0 * math.cos(a), 5.0 * math.sin(a), lerp(-1.2, -0.8, u)), belly + V(0.9, -0.9, -0.1),
            lens=35, fstop=5.6, clip=0.05)
    L.append((12.5, 14.55, G))

    def H(t, S):     # "and lowers the rover on three nylon cables": from below and to the side, the rover drops away
        u = ss(seg(t, 14.55, 16.97))
        belly = V(0, 0, 18.3 - 0.75 * (t - 14.55))
        Lp = 6.0 * ss(seg(t, 14.6, 16.1))
        rz = hang(S, W, belly, Lp, fold_k=1.0)
        dust(S, W, "dustT", V(0, 0, -0.1), 9.0, 1.2, 0.3)
        cam(S, belly + V(lerp(9.0, 8.0, u), lerp(-13.0, -12.0, u), -5.5), belly + V(0, 0, -4.6), lens=28, fstop=11,
            clip=0.1)
        label(S, "belly", belly + V(0, 0, -0.2))
        label(S, "wheels", V(0, 0, rz))
    L.append((14.55, 16.97, H))

    def I(t, S):     # "Its wheels drop down to become the landing gear": close on one side as the wheels swing down
        belly = V(0, 0, 15.0 - 0.75 * (t - 16.97))
        k = 1.0 - ss(seg(t, 17.35, 18.4))
        rz = hang(S, W, belly, 6.0, fold_k=k)
        u = ss(seg(t, 16.97, 19.36))
        c = V(0.0, 0, rz + 0.7)
        cam(S, c + V(lerp(4.0, 3.4, u), lerp(-4.4, -3.8, u), lerp(-0.2, 0.1, u)), c + V(0, -0.6, -0.1), lens=32,
            fstop=5.6, clip=0.05)
    L.append((16.97, 19.36, I))

    def J(t, S):     # "Once its wheels touch down": low on the ground as the wheels settle in a puff of dust
        td = 20.05
        rz = 0.75 * max(0.0, td - t)
        belly = V(0, 0, rz + HANG + 6.0)
        hang(S, W, belly, 6.0)
        k = seg(t, td - 0.1, td + 1.0)
        dust(S, W, "dustT", V(0, 0, -0.1), lerp(2.0, 6.0, eout(k)), lerp(0.4, 1.0, eout(k)), 0.25 + 0.6 * ss(k))
        u = ss(seg(t, 19.36, 20.92))
        cam(S, V(lerp(5.5, 5.0, u), lerp(-5.0, -4.6, u), 0.35), V(0.0, -0.4, 0.9), lens=26, fstop=5.6, clip=0.05)
    L.append((19.36, 20.92, J))

    def K(t, S):     # "blades slice the cables": on the deck, a flash at each bridle, the cables whip away upwards
        tc = 21.15
        belly = V(0, 0, HANG + 6.0 + 0.5 * ein(seg(t, tc, 22.2)))
        hang(S, W, belly, 6.0, cables=t < tc + 0.05)
        if t >= tc + 0.05:     # the cut ends ride back up into the stage
            g = ss(seg(t, tc, tc + 0.7))
            for b in W["BR"]:
                a = Vector(b["att"])
                put(S, b, "hide_render", 0, const=True)
                for i, v in enumerate((a.x, a.y, belly.z - 0.15)):
                    put(S, b, "location", v, i)
                put(S, b, "scale", max(lerp(belly.z - 0.15 - DECK - 0.06, 0.2, g), 0.05), 2)
        f = seg(t, tc, tc + 0.05) * (1 - seg(t, tc + 0.12, tc + 0.6))
        for sp, b in zip(W["sparks"], W["BR"]):
            a = Vector(b["att"])
            put(S, sp, "hide_render", 0 if f > 0 else 1, const=True)
            for i, v in enumerate((a.x, a.y, DECK + 0.1)):
                put(S, sp, "location", v, i)
        mset(S, M["spark"], S=40.0 * f)
        dust(S, W, "dustT", V(0, 0, -0.1), 6.0, 1.0, 0.7)
        u = ss(seg(t, 20.92, 22.19))
        cam(S, V(lerp(2.6, 2.3, u), lerp(-2.9, -2.6, u), DECK + 2.0), V(-0.1, 0.05, DECK + 0.6), lens=28, fstop=4,
            clip=0.05)
    L.append((20.92, 22.19, K))

    def flight(t):
        """the stage after the cut: climbs, tips over and heads for CR, then dives in"""
        t0 = 21.25
        k = clamp((t - t0) / 3.5)
        kh = ss(seg(k, 0.1, 0.75))
        d = V(CR.x, CR.y, 0).normalized()
        cz = gz(CR.x, CR.y)
        h = lerp(HANG + 6.5, 40.0, kh)
        h = lerp(h, cz + 1.0, ein(seg(k, 0.72, 1.0)))
        p = d * (V(CR.x, CR.y, 0).length * k ** 3.2) + V(0, 0, h)
        yaw = math.degrees(math.atan2(d.y, d.x))
        pitch = 48.0 * ss(seg(k, 0.12, 0.5))
        return p, pitch, yaw, k

    def Lf(t, S):    # "The stage flies away": throttles up, tips and heads off; from beside the rover
        p, pitch, yaw, k = flight(t)
        stage(S, W, p, pitch, yaw, burn=1.3, burnB=1.3)
        put(S, W["R"]["mast"], "rotation_euler", rad(-90.0), 1)
        dust(S, W, "dustT", V(0, 0, -0.1), 8.0, 1.6, 0.9 * (1 - seg(t, 22.2, 24.2)))
        u = ss(seg(t, 22.19, 24.2))
        cam(S, V(lerp(8.0, 8.6, u), lerp(-12.0, -12.8, u), 1.4), p.lerp(V(0, 0, 1.0), lerp(0.45, 0.0, u)),
            lens=lerp(28, 70, ss(u)), fstop=11, clip=0.05)
    L.append((22.19, 24.2, Lf))

    def Mc(t, S):    # "and crashes a safe distance off": wide, the rover in front, the impact far away
        p, pitch, yaw, k = flight(t + 0.6)
        if k < 1.0:
            stage(S, W, p, pitch, yaw, burn=1.3, burnB=1.3)
        ti = 24.75
        g = seg(t, ti, ti + 1.5)
        if t >= ti:
            put(S, W["flash"], "hide_render", 0, const=True)
            for i in range(3):
                put(S, W["flash"], "scale", lerp(2.0, 7.0, eout(seg(t, ti, ti + 0.3))), i)
            mset(S, M["flash"], S=50.0 * (1 - seg(t, ti, ti + 0.45)) ** 2)
            cz = gz(CR.x, CR.y)
            dust(S, W, "dustC", V(CR.x, CR.y, cz - 2.0), lerp(6.0, 20.0, eout(g)), lerp(5.0, 48.0, eout(g)),
                 lerp(0.16, 0.07, g))
        u = ss(seg(t, 24.2, 26.28))
        cam(S, V(lerp(2.2, 2.1, u), lerp(-4.6, -5.1, u), 2.5), V(CR.x, CR.y, gz(CR.x, CR.y) + 12.0), lens=lerp(50, 56, u),
            fstop=16, clip=0.05)
        label(S, "crash", V(CR.x, CR.y, gz(CR.x, CR.y) + 25.0))
    L.append((24.2, 26.28, Mc))

    def N(t, S):     # "Curiosity and Perseverance both landed this way": the rover alone, its mast rising, the sun low
        put(S, W["R"]["mast"], "rotation_euler", rad(lerp(-90, 0, ss(seg(t, 26.5, 27.7)))), 1)
        cz = gz(CR.x, CR.y)
        dust(S, W, "dustC", V(CR.x, CR.y, cz - 2.0), 22.0, 52.0, 0.06)
        u = ss(seg(t, 26.28, 29.27))
        a = rad(lerp(-25, 5, u))
        cam(S, V(6.2 * math.cos(a), 6.2 * math.sin(a), 1.1), V(0, 0, 1.15), lens=35, fstop=5.6, clip=0.05)
        label(S, "roverN", V(0, 0, 2.6))
    L.append((26.28, 29.27, N))

    def P(t, S):     # "Follow for how the world is really engineered": crane up and away over the plain
        put(S, W["R"]["mast"], "rotation_euler", 0.0, 1)
        cz = gz(CR.x, CR.y)
        dust(S, W, "dustC", V(CR.x, CR.y, cz - 2.0), 24.0, 56.0, 0.05)
        u = ss(seg(t, 29.27, T_END))
        cam(S, V(lerp(4.0, 14.0, u), lerp(-6.0, -26.0, u), lerp(1.4, 16.0, u)), V(lerp(0, -40, u), lerp(0, 160, u),
            lerp(1.0, 6.0, u)), lens=lerp(30, 26, u), fstop=16, clip=0.05)
    L.append((29.27, T_END + 0.1, P))
    return L


def camcheck(W):
    L = shots(W)
    for f in range(1, F_END + 1, 6):
        t = (f - 1) / FPS
        fn = next(fn for t0, t1, fn in L if t0 <= t < t1)
        S = {}
        defaults(t, S, W)
        fn(t, S)
        eye = S["cam"][0]
        if abs(eye.x) < 15000:
            clr = eye.z - ground(eye.x, eye.y)
            print("CC %4d %5.2f %-3s clr %7.2f %s" % (f, t, fn.__name__, clr, "UNDERGROUND" if clr < 0.1 else ""))


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = sc_world()
    if os.environ.get("CAMCHECK"):
        camcheck(W)
        sys.exit(0)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_sc.json"))
    if os.environ.get("BAKEONLY"):
        sys.exit(0)
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
