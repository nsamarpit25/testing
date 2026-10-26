# ----------------------------------------------------------------------------------------------- film
# blender -b --factory-startup -P hd.py -- film <outdir> <height> <samples> <a-b | f,f,f>
BG = 'nodes["Background"].inputs[1].default_value'
SUN = 5.0


def hd_world():
    W = build_hd()
    W.update(build_cool(W["M"]))
    W["cons"] = W["cols"] + W["pipes"] + [W["mono"], W["monocut"], W["grout"]]
    return W


def defaults(t, S, W):
    M = W["M"]
    put(S, W["world"].node_tree, BG, 0.32)
    put(S, W["sun"].data, "energy", SUN)
    for ob in W["ext"]:
        put(S, ob, "hide_render", 0, const=True)
    for ob in W["cons"]:
        put(S, ob, "hide_render", 1, const=True)
    mset(S, M["rock"], RING=1.0)
    mset(S, M["column"], TH=0.0, TT=0.8, SK=0.0, CK=0.0, CO=0.0, XA=0.0)
    mset(S, M["pipe"], WF=0.0, IC=0.0, P=t * 2.2)
    mset(S, M["grout"], F=0.0)
    for ob in W["cols"]:
        for i in range(3):
            put(S, ob, "scale", 1.0, i)


def site(S, W, th=0.0):
    """the dam site under construction: dry canyon, no lake, no ring; th dims the world for the thermal view"""
    for ob in W["ext"]:
        if ob is not W["sun"] and ob.name != "Canyon":
            put(S, ob, "hide_render", 1, const=True)
    mset(S, W["M"]["rock"], RING=0.0)
    put(S, W["world"].node_tree, BG, lerp(0.32, 0.03, th))
    put(S, W["sun"].data, "energy", lerp(SUN, 0.25, th))
    mset(S, W["M"]["column"], TH=th)


def show_cols(S, W, rise=None, t=0.0, pipes=False):
    for ob in W["cols"]:
        put(S, ob, "hide_render", 0, const=True)
        if rise is not None:
            x, y = ob.location.x, ob.location.y
            d = 0.35 * ((y - ROWS_Y[0]) / (ROWS_Y[-1] - ROWS_Y[0])) + 0.25 * abs(mn.noise(V(x * 0.2, y * 0.2, 1.7)))
            k = ss(seg(t, rise[0] + d, rise[1] + d))
            put(S, ob, "scale", lerp(0.03, 1.0, k), 2)
    if pipes:
        for ob in W["pipes"]:
            put(S, ob, "hide_render", 0, const=True)


def gaps(S, W, k):
    for ob in W["cols"]:
        for i in range(2):
            put(S, ob, "scale", lerp(1.0, 0.94, k), i)


def shots(W):
    M = W["M"]
    L = []
    HC = V(0.0, ROWS_Y[-1] + CELL / 2, BED)          # foot of the hero columns' downstream faces

    def A(t, S):     # "A hundred and twenty-five years": the dam at golden hour, Lake Mead behind it
        u = ss(seg(t, 0.0, 2.3))
        cam(S, V(lerp(96, 78, u), lerp(660, 590, u), lerp(330, 312, u)), V(0, 60, 135), lens=lerp(27, 29, u),
            fstop=16, clip=1.0)
    L.append((0.0, 2.3, A))

    def B(t, S):     # "That's how long Hoover Dam would take to cool": low along the curved face
        u = ss(seg(t, 2.3, 4.2))
        cam(S, V(lerp(-96, -80, u), lerp(440, 400, u), lerp(190, 172, u)), V(20, 80, 120), lens=28, fstop=16,
            clip=1.0)
    L.append((2.3, 4.2, B))

    def C(t, S):     # "in one pour": the same canyon, one giant block, the thermal camera switches on
        site(S, W, ss(seg(t, 4.55, 5.35)))
        put(S, W["mono"], "hide_render", 0, const=True)
        mset(S, M["column"], TT=0.8)
        u = ss(seg(t, 4.2, 6.25))
        cam(S, V(lerp(62, 52, u), lerp(440, 400, u), lerp(150, 135, u)), V(0, 100, 25), lens=30, fstop=16, clip=1.0)
    L.append((4.2, 6.25, C))

    def D(t, S):     # "Setting cement makes heat": closer on a corner, the block heating up
        site(S, W, 1.0)
        put(S, W["mono"], "hide_render", 0, const=True)
        mset(S, M["column"], TT=lerp(0.45, 0.82, ss(seg(t, 6.3, 7.9))))
        u = ss(seg(t, 6.25, 8.2))
        cam(S, V(lerp(22, 12, u), lerp(340, 310, u), lerp(225, 205, u)), V(0, 110, 35), lens=26, fstop=16, clip=1.0)
    L.append((6.25, 8.2, D))

    def E(t, S):     # "The hot core fights the cooling skin, and it cracks": the block cut open, core glowing
        site(S, W, 1.0)
        put(S, W["monocut"], "hide_render", 0, const=True)
        mset(S, M["column"], TT=0.82, SK=ss(seg(t, 8.3, 9.6)), CK=ss(seg(t, 10.15, 10.55)))
        if t > 8.5:
            label(S, "core", V(0.0, 100.0, 22.0))
        if t > 9.3:
            label(S, "skin", V(0.0, 150.0, 73.0))
        u = ss(seg(t, 8.2, 11.25))
        cam(S, V(lerp(72, 62, u), lerp(250, 232, u), lerp(125, 112, u)), V(0, 100, 25), lens=22, fstop=16, clip=1.0,
            shake=0.5 * seg(t, 10.55, 10.9) * (1 - seg(t, 10.9, 11.25)), t=t)
    L.append((8.2, 11.25, E))

    def F(t, S):     # "So it went up in separate columns": the columns rise lift by lift
        site(S, W, 0.0)
        show_cols(S, W, rise=(11.2, 12.3), t=t)
        if t > 12.4:
            label(S, "col", V(0.0, ROWS_Y[-1] + CELL / 2, BED + 0.7 * W["herocols"][1]["h"]))
        u = ss(seg(t, 11.25, 13.2))
        cam(S, V(lerp(66, 56, u), lerp(400, 360, u), lerp(190, 168, u)), V(0, 95, 20), lens=28, fstop=16, clip=1.0)
    L.append((11.25, 13.2, F))

    def G(t, S):     # "Inside each, coils of one-inch steel pipe": x-ray into the hero columns
        site(S, W, 0.0)
        show_cols(S, W, pipes=True)
        mset(S, M["column"], XA=ss(seg(t, 13.25, 13.9)))
        if t > 13.9:
            label(S, "coil", V(1.75, ROWS_Y[-1] + 7.0, BED + LIFT * 16 - 0.05))
        u = ss(seg(t, 13.2, 15.9))
        cam(S, HC + V(lerp(14, 9, u), lerp(42, 30, u), lerp(34, 30, u)), HC + V(0, -6, 24), lens=34, fstop=11,
            clip=0.5)
    L.append((13.2, 15.9, G))

    def H(t, S):     # "Over five hundred eighty miles": pull back, the coils run on and on
        site(S, W, 0.0)
        show_cols(S, W, pipes=True)
        mset(S, M["column"], XA=1.0)
        mset(S, M["pipe"], WF=0.35)
        u = ss(seg(t, 15.9, 18.55))
        cam(S, HC + V(lerp(20, 70, u), lerp(60, 170, u), lerp(40, 105, u)), HC + V(0, -20, 20), lens=32, fstop=16,
            clip=0.5)
    L.append((15.9, 18.55, H))

    def I(t, S):     # "River water first": water fills the coils
        site(S, W, 0.0)
        show_cols(S, W, pipes=True)
        mset(S, M["column"], XA=1.0)
        mset(S, M["pipe"], WF=ss(seg(t, 18.6, 19.4)))
        u = ss(seg(t, 18.55, 20.0))
        cam(S, HC + V(lerp(-10, -7, u), lerp(16, 12, u), lerp(16, 18, u)), HC + V(-9, -8, 14), lens=38, fstop=8,
            clip=0.2)
    L.append((18.55, 20.0, I))

    def J(t, S):     # "then ice water from a giant refrigeration plant": the coils go ice-bright
        site(S, W, 0.0)
        show_cols(S, W, pipes=True)
        mset(S, M["column"], XA=1.0)
        mset(S, M["pipe"], WF=1.0, IC=ss(seg(t, 20.05, 20.7)))
        u = ss(seg(t, 20.0, 22.65))
        cam(S, HC + V(lerp(16, -12, u), lerp(30, 27, u), lerp(32, 30, u)), HC + V(lerp(4, -4, u), -8, 26), lens=34,
            fstop=11, clip=0.3)
    L.append((20.0, 22.65, J))

    def K(t, S):     # "As heat drains, the columns shrink apart": thermal view, cold spreads from every coil
        site(S, W, 1.0)
        show_cols(S, W)
        mset(S, M["column"], TT=0.8, CO=ss(seg(t, 22.8, 25.2)))
        gaps(S, W, ss(seg(t, 23.7, 25.3)))
        u = ss(seg(t, 22.65, 25.6))
        cam(S, HC + V(lerp(60, 48, u), lerp(80, 62, u), lerp(44, 46, u)), HC + V(0, -26, 26), lens=32, fstop=16,
            clip=0.5)
    L.append((22.65, 25.6, K))

    def Lg(t, S):    # "Grout fills the gaps and pipes": grout rises in the joints
        site(S, W, 1.0 - ss(seg(t, 25.6, 26.2)))
        show_cols(S, W)
        mset(S, M["column"], TT=0.8, CO=1.0)
        gaps(S, W, 1.0)
        put(S, W["grout"], "hide_render", 0, const=True)
        mset(S, M["grout"], F=ss(seg(t, 26.0, 27.9)))
        if t > 26.2:
            label(S, "grout", V(-8.0, ROWS_Y[-1] + CELL / 2, BED + 20.0))
        u = ss(seg(t, 25.6, 27.95))
        cam(S, HC + V(lerp(-34, -24, u), lerp(52, 42, u), lerp(30, 42, u)), HC + V(-4, -6, lerp(26, 34, u)), lens=32,
            fstop=11, clip=0.3)
    L.append((25.6, 27.95, Lg))

    def Md(t, S):    # "making one solid dam": match cut to the finished face, crane up
        u = ss(seg(t, 27.95, 29.5))
        cam(S, V(lerp(36, 52, u), lerp(232, 290, u), lerp(30, 120, u)), V(0, 60, lerp(70, 140, u)), lens=30, fstop=16,
            clip=1.0)
    L.append((27.95, 29.5, Md))

    def N(t, S):     # "Cooled in under two years, not a century": along the crest, the lake on the left
        u = ss(seg(t, 29.5, 32.4))
        cam(S, V(lerp(-170, -132, u), lerp(70, 46, u), lerp(262, 252, u)), V(150, 55, 212), lens=24, fstop=16,
            clip=1.0)
    L.append((29.5, 32.4, N))

    def O(t, S):     # "Follow for how the world is really engineered": rise away over the canyon
        u = ss(seg(t, 32.4, T_END))
        cam(S, V(lerp(40, 30, u), lerp(700, 960, u), lerp(330, 440, u)), V(0, 40, 130), lens=30, fstop=16, clip=2.0)
    L.append((32.4, T_END + 0.1, O))
    return L


def camcheck(W):
    """per-frame camera clearance over the terrain and distance to the first rock along the view axis"""
    ter = bpy.data.objects["Canyon"]
    L = shots(W)
    for f in range(1, F_END + 1, 6):
        t = (f - 1) / FPS
        fn = next(fn for t0, t1, fn in L if t0 <= t < t1)
        S = {}
        defaults(t, S, W)
        fn(t, S)
        eye, q, lens, fs, foc, clip = S["cam"]
        d = q @ Vector((0, 0, -1))
        hit, loc, *_ = ter.ray_cast(eye, d, distance=foc)
        clr = eye.z - canyon_h(eye.x, eye.y)
        flag = ("UNDERGROUND " if clr < 0 else "") + ("BLOCKED %.0f/%.0f" % ((loc - eye).length, foc) if hit else "")
        print("CC %4d %5.2f %-3s clr %7.1f %s" % (f, t, fn.__name__, clr, flag))


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = hd_world()
    if os.environ.get("CAMCHECK"):
        camcheck(W)
        sys.exit(0)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_hd.json"))
    if os.environ.get("BAKEONLY"):
        sys.exit(0)
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
