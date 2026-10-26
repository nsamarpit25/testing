# ----------------------------------------------------------------------------------------------- film
# blender -b --factory-startup -P sb.py -- film <outdir> <height> <samples> <a-b | f,f,f>
OCEAN_T = 'modifiers["Ocean"].time'
OCEAN_W = 'modifiers["Ocean"].wave_scale'


def wnode(W, name):
    return W["world"].node_tree, f'nodes["{name}"].outputs[0].default_value'


def wset(S, W, **kw):
    for k, v in kw.items():
        put(S, *wnode(W, k), v)


def gate_parts(W, k):
    return [o for n, o in W["G"][k].items() if n not in ("root", "piv", "tilt", "geo")]


def defaults(t, S, W):
    M = W["M"]
    wset(S, W, STORM=1.0, FL=0.0, XR=0.0, BGS=1.3, CW=t * 0.004)
    put(S, W["sun"].data, "energy", 3.0)
    put(S, W["sun"].data, "color", 0.73, 0)
    put(S, W["sun"].data, "color", 0.78, 1)
    put(S, W["sun"].data, "color", 0.83, 2)
    put(S, W["flash"].data, "energy", 0.0)
    for f in W["floods"]:
        put(S, f.data, "energy", 3e5)
    put(S, W["sea"], OCEAN_T, 20.0 + t * 1.0)
    put(S, W["sea"], OCEAN_W, 1.6)
    put(S, W["sea"], "location", 0.0, 2)
    mset(S, M["water"], XA=0.0, RB=0.5, FO=1.0)
    mset(S, M["dockwater"], XA=0.0, RB=0.15, FO=0.0, FN=0.0, FW=t * 0.6)
    for m in ("gate", "truss", "rail", "land", "conc", "ball"):
        mset(S, M[m], XA=0.0)
    mset(S, M["fill"], FH=-100.0)
    mset(S, M["lamp"], S=30.0)
    mset(S, M["red"], S=0.0)
    mset(S, M["rain"], S=0.0)
    put(S, W["haze"].data.materials[0].node_tree, 'nodes["HZ"].outputs[0].default_value', 0.0006)
    for ob in (W["haze"], W["sea"], W["far"], *W["docks"], *W["land"]):
        hide(S, ob, False)
    for ob in XDOCK:
        hide(S, ob, True)
    hide(S, W["rain"], True)
    hide(S, W["bolt"], True)
    mset(S, M["bolt"], S=0.0)
    for k in ("N", "S"):
        for ob in gate_parts(W, k):
            hide(S, ob, ob.name.startswith(("GateNWalls", "GateSWalls", "GateNFill", "GateSFill")))
    dock_level(S, W, ZB_DOCK - 1.0)
    gates(S, W, PARK, ZB_DOCK)


def gates(S, W, swing, zb, swing_s=None):
    """both gates at swing (deg, 0 = closed) with their bottoms at zb"""
    al = math.asin(clamp((ZB_FLOAT - zb) / R, -0.2, 0.2))
    for k, sw in (("N", swing), ("S", swing if swing_s is None else swing_s)):
        put(S, W["G"][k]["piv"], "rotation_euler", rad(sw), 2)
        put(S, W["G"][k]["tilt"], "rotation_euler", al, 1)


def dock_level(S, W, z, xr=False):
    """the dock water is a box from the dock floor up to z"""
    for d in W["docks"]:
        put(S, d, "location", ZB_DOCK, 2)
        put(S, d, "scale", max(z - ZB_DOCK, 0.01) / -ZB_DOCK, 2)
        hide(S, d, z < ZB_DOCK + 0.05 or xr)
    for d in DOCKX:
        put(S, d, "location", ZB_DOCK, 2)
        put(S, d, "scale", max(z - ZB_DOCK, 0.01) / -ZB_DOCK, 2)
        hide(S, d, not xr or z < ZB_DOCK + 0.05)


def storm(S, W, k=1.0):
    """k = 1 stormy dusk, 0 calm golden evening"""
    wset(S, W, STORM=k)
    put(S, W["sea"], OCEAN_W, lerp(0.35, 1.6, k))
    mset(S, W["M"]["water"], FO=k, RB=lerp(0.2, 0.5, k))
    put(S, W["sun"].data, "energy", lerp(4.2, 3.0, k))
    for i, (a, b) in enumerate(zip((1.0, 0.70, 0.42), (0.73, 0.78, 0.83))):
        put(S, W["sun"].data, "color", lerp(a, b, k), i)
    for f in W["floods"]:
        put(S, f.data, "energy", lerp(1e5, 3e5, k))
    put(S, W["haze"].data.materials[0].node_tree, 'nodes["HZ"].outputs[0].default_value', lerp(0.00025, 0.0006, k))


def flash(S, W, t, t0, k=1.0, lat=-260.0):
    """lightning: two quick pulses from t0"""
    a = max(0.0, 1 - abs(t - t0) / 0.07) + 0.6 * max(0.0, 1 - abs(t - t0 - 0.2) / 0.06)
    if a > 0:
        wset(S, W, FL=a * k)
        put(S, W["flash"].data, "energy", 14.0 * a * k)
        eye, q = S["cam"][0], S["cam"][1]
        fw = q @ V(0, 0, -1)
        fw.z = 0
        fw.normalize()
        rt = V(fw.y, -fw.x, 0)
        p = eye + fw * 1700 + rt * lat
        hide(S, W["bolt"], False)
        mset(S, W["M"]["bolt"], S=60.0 * a * k)
        for i in range(3):
            put(S, W["bolt"], "location", (p.x, p.y, -5.0)[i], i)


def rain(S, W, eye, t, t0, k=1.0):
    hide(S, W["rain"], False)
    mset(S, W["M"]["rain"], S=2.2 * k)
    for i, v in enumerate(eye + V(0, 0, 32.0 - 11.0 * (t - t0))):
        put(S, W["rain"], "location", v, i)


def xray(S, W, k=1.0, land=True):
    """the river turns to glass in a dark void; the gates' shells go clear and their chambers show"""
    M = W["M"]
    wset(S, W, XR=k, BGS=lerp(1.3, 0.25, k))
    mset(S, M["water"], XA=k)
    mset(S, M["dockwater"], XA=k)
    for m in ("gate", "truss", "rail", "conc", "ball"):
        mset(S, M[m], XA=k)
    mset(S, M["land"], XA=k if land else 0.0)
    put(S, W["haze"].data.materials[0].node_tree, 'nodes["HZ"].outputs[0].default_value', 0.0)
    if k > 0.5:
        hide(S, W["far"], True)
        hide(S, W["haze"], True)
    put(S, W["sun"].data, "energy", lerp(3.0, 0.0, k))
    for f in W["floods"]:
        put(S, f.data, "energy", lerp(3e5, 0.0, k))
    mset(S, M["lamp"], S=lerp(30.0, 4.0, k))
    for kk in ("N", "S"):
        for ob in gate_parts(W, kk):
            if ob.name.startswith(("Gate" + kk + "Walls", "Gate" + kk + "Fill")):
                hide(S, ob, False)


def gpos(side, swing, zb, psi, r, z):
    return world_pt(side, swing, zb, gpt(psi, r, z))


def shots(W):
    M = W["M"]
    L = []
    CN = gpos(1, 0, ZB_FLOAT, 0, R, 0)          # north gate centre, closed

    def A(t, S):     # "When a storm could push the sea": low over the storm waves at the mouth, lightning
        u = ss(seg(t, 0.0, 1.85))
        eye = V(lerp(-640, -610, u), lerp(40, 46, u), lerp(5.5, 4.6, u))
        cam(S, eye, V(-420, 175, 3.0), lens=24, fstop=11, clip=0.2)
        flash(S, W, t, 0.55)
        rain(S, W, eye, t, 0.0)
    L.append((0.0, 1.85, A))

    def B(t, S):     # "three metres higher": the tide staff, the water climbing to the red +3 m band
        k = ss(seg(t, 1.95, 3.0))
        put(S, W["sea"], "location", 3.05 * k, 2)
        mset(S, M["red"], S=6.0 * seg(t, 2.85, 3.05))
        u = ss(seg(t, 1.85, 3.4))
        g = GAUGE
        eye = g + V(lerp(-7.0, -6.0, u), lerp(-15.0, -13.0, u), lerp(2.4, 3.6, u))
        cam(S, eye, g + V(0.0, 0, lerp(1.7, 2.6, u)), lens=45, fstop=4.0, clip=0.1)
        rain(S, W, eye, t, 1.85, 0.7)
        label(S, "plus3", g + V(0.55, -0.3, 3.0))
    L.append((1.85, 3.4, B))

    def C(t, S):     # "Rotterdam shuts its river": high over the sea, the two doors swinging across
        u = seg(t, 3.4, 4.9)
        gates(S, W, lerp(-42, -14, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(-640, -600, u), lerp(-260, -240, u), lerp(260, 240, u)), V(lerp(60, 70, u), 0, 0), lens=30,
            fstop=16, clip=1.0)
        flash(S, W, t, 4.3, 0.6)
    L.append((3.4, 4.9, C))

    def D(t, S):     # "with two floating doors": at the waterline mid-river, the two ends closing on each other
        u = seg(t, 4.9, 6.27)
        gates(S, W, lerp(-14, -3, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        eye = V(lerp(-150, -138, u), lerp(-14, -10, u), 4.2)
        cam(S, eye, V(70, 6, 6.0), lens=32, fstop=11, clip=0.2)
        rain(S, W, eye, t, 4.9, 0.8)
    L.append((4.9, 6.27, D))

    def E(t, S):     # "Each one is two hundred": skimming along the north door's sea face
        u = seg(t, 6.27, 7.7)
        gates(S, W, 0.0, ZB_FLOAT)
        dock_level(S, W, 0.0)
        p = lerp(-PSI + 4, PSI - 10, ss(u))
        eye = gpos(1, 0, ZB_FLOAT, p, R + GD / 2 + 26.0, 9.0)
        tg = gpos(1, 0, ZB_FLOAT, p + 9.0, R + GD / 2, 6.0)
        cam(S, eye, tg, lens=28, fstop=8, clip=0.2)
    L.append((6.27, 7.7, E))

    def F(t, S):     # "...and ten metres long": the whole north door square on from the sea, 210 m drawn on
        u = seg(t, 7.7, 9.6)
        gates(S, W, 0.0, ZB_FLOAT)
        dock_level(S, W, 0.0)
        n = (CN - JN).normalized()
        n.z = 0
        eye = CN + n * lerp(345, 330, u) + V(0, -30, lerp(195, 185, u))
        cam(S, eye, CN + V(0, -20, 0.0), lens=30, fstop=16, clip=1.0)
        label(S, "g0", gpos(1, 0, ZB_FLOAT, -PSI, R + GD / 2, ZB_FLOAT + GH + 1.0))
        label(S, "g1", gpos(1, 0, ZB_FLOAT, PSI, R + GD / 2, ZB_FLOAT + GH + 1.0))
    L.append((7.7, 9.6, F))

    def G(t, S):     # "Most days, they hide in dry docks": a calm golden evening, the door resting in its dry dock
        storm(S, W, 0.0)
        u = ss(seg(t, 9.6, 11.6))
        c = gpos(1, PARK, ZB_FLOAT, 0, R, 0)
        cam(S, c + V(lerp(-150, -135, u), lerp(-210, -190, u), lerp(120, 105, u)), c + V(0, 0, -6), lens=30, fstop=16,
            clip=1.0)
        label(S, "dock", gpos(1, PARK, ZB_FLOAT, 6, R + GD / 2 + 3, ZB_DOCK + 2.0))
    L.append((9.6, 11.6, G))

    def H(t, S):     # "When a surge is coming": the storm rolls in off the sea, lightning
        u = seg(t, 11.6, 12.75)
        put(S, W["sea"], OCEAN_W, 2.2)
        eye = V(lerp(-300, -320, u), -60, 6.0)
        cam(S, eye, V(-900, -10, 8.0), lens=26, fstop=11, clip=0.2)
        flash(S, W, t, 11.95)
        rain(S, W, eye, t, 11.6)
    L.append((11.6, 12.75, H))

    def xdock(S, t, t0):
        """the real dock under the storm; only the door and the water inside the dock turn to x-ray"""
        k = ss(seg(t, t0, t0 + 0.12))
        for m in ("gate", "truss", "rail", "ball"):
            mset(S, M[m], XA=k)
        mset(S, M["dockwater"], XA=k, RB=0.6, FO=0.0, FN=0.0)
        mset(S, M["lamp"], S=lerp(30.0, 4.0, k))
        for kk in ("N", "S"):
            for ob in gate_parts(W, kk):
                if ob.name.startswith(("Gate" + kk + "Walls", "Gate" + kk + "Fill")):
                    hide(S, ob, False)
        hide(S, W["haze"], True)
        lv = lerp(ZB_DOCK, 0.0, ss(seg(t, 12.85, 14.75)))
        dock_level(S, W, lv, xr=k > 0.5)
        gates(S, W, PARK, max(ZB_DOCK, lv - 7.0))

    def I(t, S):     # "the docks flood": the door turns to glass, its dry dock filling round it
        xdock(S, t, 12.75)
        u = seg(t, 12.75, 13.85)
        eye = gpos(1, PARK, ZB_FLOAT, lerp(14, 11, u), R + 85, 72.0)
        cam(S, eye, gpos(1, PARK, ZB_FLOAT, 5, R, -6.0), lens=26, fstop=16, clip=0.5)
    L.append((12.75, 13.85, I))

    def Jx(t, S):    # "and the hollow doors float": closer, the hollow door lifting off the dock floor
        xdock(S, t, 12.75)
        u = seg(t, 13.85, 14.94)
        eye = gpos(1, PARK, ZB_FLOAT, lerp(-2, -4, u), R + 48, lerp(40, 36, u))
        cam(S, eye, gpos(1, PARK, ZB_FLOAT, -9, R, -4.0), lens=28, fstop=11, clip=0.5)
    L.append((13.85, 14.94, Jx))

    def K(t, S):     # "Motors swing them out": high above, both doors swinging out of their docks
        u = seg(t, 14.94, 16.25)
        gates(S, W, lerp(PARK, -26, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(330, 300, u), lerp(-120, -90, u), lerp(470, 430, u)), V(lerp(110, 100, u), 0, 0), lens=24,
            fstop=16, clip=1.0)
    L.append((14.94, 16.25, K))

    def Lb(t, S):    # "on ball joints ten metres wide": close on the north ball turning in its seat
        u = seg(t, 16.25, 18.25)
        gates(S, W, lerp(-26, -7, u), ZB_FLOAT)
        dock_level(S, W, 0.0)
        j = JN + V(0, 0, ZJ)
        a = rad(lerp(-35, -20, ss(u)))
        eye = j + V(34 * math.cos(a) + 8, 34 * math.sin(a), lerp(17, 15, ss(u)))
        cam(S, eye, j + V(-7, 0, 1.0), lens=40, fstop=5.6, clip=0.2)
        for f in W["floods"]:
            put(S, f.data, "energy", 6e4)
        side = (eye - j).cross(V(0, 0, 1)).normalized()
        label(S, "b0", j - side * 5.0 + V(0, 0, 6.5))
        label(S, "b1", j + side * 5.0 + V(0, 0, 6.5))
    L.append((16.25, 18.25, Lb))

    def Mm(t, S):    # "In the middle": low on the river side, the two ends meeting mid-channel
        u = seg(t, 18.25, 19.35)
        gates(S, W, lerp(-7, 0, eout(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        mid = gpos(1, 0, ZB_FLOAT, PSI, R, 0)
        eye = mid + V(lerp(-150, -140, u), -12, lerp(48, 44, u))
        cam(S, eye, mid + V(15, 0, 2.0), lens=30, fstop=11, clip=0.5)
        rain(S, W, eye, t, 18.25, 0.7)
    L.append((18.25, 19.35, Mm))

    def N(t, S):     # "they fill with water and sink to the riverbed": x-ray, chambers flood blue, the doors go down
        xray(S, W, ss(seg(t, 19.35, 19.55)), land=False)
        hide(S, W["land"][0], True)
        hide(S, W["land"][1], True)
        fh = lerp(ZB_FLOAT, ZB_FLOAT + GH, ss(seg(t, 19.45, 20.5)))
        mset(S, M["fill"], FH=fh)
        zb = lerp(ZB_FLOAT, ZB_SUNK, ss(seg(t, 19.95, 21.0)))
        gates(S, W, 0.0, zb)
        mid = gpos(1, 0, ZB_FLOAT, PSI, R, 0)
        cam(S, gpos(1, 0, ZB_FLOAT, PSI - 9, R + GD / 2 + 105, -3.0), gpos(1, 0, ZB_FLOAT, PSI - 10, R, -5.0), lens=36,
            fstop=16, clip=0.5)
        label(S, "bed", gpos(1, 0, ZB_FLOAT, PSI - 13, R + GD / 2 + 14, SILL))
    L.append((19.35, 21.1, N))

    def O(t, S):     # "Now a steel wall holds back the North Sea": low on the sea side, the storm against the wall
        u = seg(t, 21.1, 23.5)
        gates(S, W, 0.0, ZB_SUNK)
        dock_level(S, W, 0.0)
        put(S, W["sea"], OCEAN_W, 2.2)
        put(S, W["sea"], "location", 1.5, 2)
        n = (CN - JN).normalized()
        n.z = 0
        eye = gpos(1, 0, ZB_FLOAT, lerp(PSI - 12, PSI - 15, ss(u)), R + GD / 2 + lerp(36, 28, ss(u)), 8.0)
        cam(S, eye, gpos(1, 0, ZB_FLOAT, PSI - 30, R + GD / 2, 3.0), lens=24, fstop=11, clip=0.2)
        flash(S, W, t, 22.45)
        rain(S, W, eye, t, 21.1)
        label(S, "sea", gpos(1, 0, ZB_FLOAT, PSI - 18, R + GD / 2 + 14, 2.5))
    L.append((21.1, 23.5, O))

    def P(t, S):     # "When the storm passes": the sky breaks to gold over the closed barrier
        u = seg(t, 23.5, 24.75)
        storm(S, W, 1 - ss(seg(t, 23.6, 24.6)))
        gates(S, W, 0.0, ZB_SUNK)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(-420, -400, u), lerp(-330, -310, u), lerp(120, 115, u)), V(60, 20, 0), lens=30, fstop=16,
            clip=1.0)
    L.append((23.5, 24.75, P))

    def Q(t, S):     # "they're pumped empty": x-ray again, the chambers drain and the doors rise
        storm(S, W, 0.0)
        xray(S, W, ss(seg(t, 24.75, 24.95)), land=False)
        hide(S, W["land"][0], True)
        hide(S, W["land"][1], True)
        fh = lerp(ZB_FLOAT + GH, ZB_FLOAT - 0.5, ss(seg(t, 24.8, 25.6)))
        mset(S, M["fill"], FH=fh)
        zb = lerp(ZB_SUNK, ZB_FLOAT, ss(seg(t, 24.95, 25.8)))
        gates(S, W, 0.0, zb)
        mid = gpos(1, 0, ZB_FLOAT, PSI, R, 0)
        cam(S, gpos(1, 0, ZB_FLOAT, PSI - 9, R + GD / 2 + 105, -3.0), gpos(1, 0, ZB_FLOAT, PSI - 10, R, -5.0), lens=36,
            fstop=16, clip=0.5)
    L.append((24.75, 25.8, Q))

    def Rr(t, S):    # "and float home": golden light, the doors swing back into their docks
        storm(S, W, 0.0)
        u = seg(t, 25.8, 27.4)
        gates(S, W, lerp(0, PARK, ss(u)), ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(520, 500, u), lerp(-230, -215, u), lerp(260, 250, u)), V(60, 20, 0), lens=26, fstop=16, clip=1.0)
    L.append((25.8, 27.4, Rr))

    def U(t, S):     # "Follow for how the world is really engineered": crane up and out over the open barrier
        storm(S, W, 0.0)
        u = ss(seg(t, 27.4, T_END))
        gates(S, W, PARK, ZB_FLOAT)
        dock_level(S, W, 0.0)
        cam(S, V(lerp(-160, -700, u), lerp(-120, -420, u), lerp(40, 420, u)), V(lerp(60, 120, u), 0, lerp(5, 0, u)),
            lens=28, fstop=16, clip=1.0)
    L.append((27.4, T_END + 0.1, U))
    return L


if __name__ == "__main__" and sys.argv[sys.argv.index("--") + 1] == "film":
    argv = sys.argv[sys.argv.index("--") + 1:]
    W = build_sb()
    bake(W, os.path.join(os.path.dirname(os.path.abspath(argv[1])) or ".", "labels_sb.json"))
    if os.environ.get("BAKEONLY"):
        sys.exit(0)
    if os.environ.get("SAVEBLEND"):
        bpy.ops.wm.save_as_mainfile(filepath=os.environ["SAVEBLEND"])
    render(argv[1], int(argv[2]), int(argv[3]), argv[4])
