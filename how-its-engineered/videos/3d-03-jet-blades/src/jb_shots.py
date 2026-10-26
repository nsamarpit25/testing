

# ----------------------------------------------------------------------------------------------- shot helpers

def put(S, idb, path, v, idx=0, const=False):
    S[(idb, path, idx)] = (float(v), const)


def nv(m, name="S"):
    return m.node_tree, f'nodes["{name}"].outputs[0].default_value'


def mset(_S, _m, **kw):
    for k, v in kw.items():
        put(_S, *nv(_m, k), v)


def cam(S, eye, tgt, lens=50, roll=0.0, fstop=8.0, focus=None, clip=0.01, shake=0.0, t=0.0):
    eye, tgt = Vector(eye), Vector(tgt)
    d = tgt - eye
    yaw = pitch = 0.0
    if shake:
        yaw += rad(shake) * (math.sin(t * 1.7) * 0.6 + math.sin(t * 3.1 + 1.0) * 0.4)
        pitch += rad(shake) * (math.sin(t * 2.3 + 2.0) * 0.6 + math.sin(t * 0.9) * 0.4)
    if yaw or pitch:
        d = Matrix.Rotation(yaw, 3, "Z") @ d
        side = d.cross(Vector((0, 0, 1)))
        if side.length > 1e-6:
            d = Matrix.Rotation(pitch, 3, side.normalized()) @ d
    q = d.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), roll)
    S["cam"] = (eye, q, lens, fstop, focus if focus is not None else (tgt - eye).length, clip)


def label(S, name, p):
    S.setdefault("labels", {})[name] = Vector(p)


def hide(S, ob, h=True):
    put(S, ob, "hide_render", 1 if h else 0, const=True)


def disc_matrix(spin):
    return Matrix.Translation(DC) @ Matrix.Rotation(rad(90), 4, "Z") @ Matrix.Rotation(spin, 4, "X")


def hero_pose(S, W, Mh):
    loc, q, sc = Mh.decompose()
    S["hero"] = Mh
    for k in range(3):
        put(S, W["hero"], "location", loc[k], k)
    for k in range(4):
        put(S, W["hero"], "rotation_quaternion", q[k], k)


def hero_slot(S, W, spin=0.0, lift=0.0):
    hero_pose(S, W, Matrix.Translation((0, 0, lift)) @ disc_matrix(spin) @ Matrix.Translation((0, 0, R_P)))


B0 = Vector((200, 0, 0))                # blade studio: the hero alone in a pool of light, no floor, no neighbours
HOVER = B0 + Vector((0, 0, 0.70))


def chord_normal_angle():
    """blade-frame angle of the normal to the mid-span chord, on the concave (pressure) side"""
    ring, nrm, sal, le = af_ring(0.5)
    cv = ring[0] - ring[le]
    mid = ring[le // 2]                  # a point on the suction surface
    n = Vector((-cv.y, cv.x, 0)).normalized()
    if (Vector((mid.x, mid.y, 0)) - Vector((ring[le].x, ring[le].y, 0))).dot(n) > 0:
        n = -n                           # point away from the convex side
    return math.atan2(n.y, n.x)


PHI = chord_normal_angle()


def hero_float(S, W, yaw=0.0, tilt=0.0, t=0.0, bob=True):
    z = 0.0012 * math.sin(t * 1.3) if bob else 0.0
    Mh = Matrix.Translation(HOVER + Vector((0, 0, z))) @ Matrix.Rotation(rad(90) + yaw, 4, "Z") @ \
        Matrix.Rotation(tilt, 4, "X")
    hero_pose(S, W, Mh)


def face(az, off=0.0, side=1):
    """hero yaw that turns the blade's pressure side (side=1) or suction side (-1) to a camera at azimuth az, plus
    off degrees"""
    base = PHI if side > 0 else PHI + math.pi
    return rad(az) - rad(90) - base - rad(90) + rad(off)


def bcam(S, az, el, dist, lens=85, tz=-0.004, fstop=9.0, focus=None, shake=0.0, t=0.0, c=None):
    """camera on the hero at the blade studio: azimuth az (deg, 0 = from -y), elevation el, distance dist"""
    c = (HOVER + Vector((0, 0, tz))) if c is None else c
    eye = c + Matrix.Rotation(rad(az), 3, "Z") @ Vector((0, -dist * math.cos(rad(el)), dist * math.sin(rad(el))))
    cam(S, eye, c, lens=lens, fstop=fstop, focus=focus, shake=shake, t=t)


def bw(S, p):
    """blade-frame point -> world (current hero pose)"""
    return S["hero"] @ Vector(p)


def spin_disc(S, W, a):
    put(S, W["disc"], "rotation_euler", a, 0)


def lights(S, W, which, k=1.0):
    for name, ob, e in W["lights"]:
        on = name.startswith(which)
        put(S, ob.data, "energy", e * k if on else 0.0)
    for name, m, s in W["cards"]:
        put(S, *nv(m), s * k if name == which else 0.0)


def thermal_on(S, W, tb_hero=0.74, tb_disc=0.74, disc=0.4, k=1.0):
    M = W["M"]
    mset(S, M["bladeH"], TH=k, TB=tb_hero)
    mset(S, M["bladeD"], TH=k, TB=tb_disc)
    mset(S, M["disc"], TH=k, TB=disc)
    put(S, *nv_world(W, "W"), lerp(1.0, 0.2, k))


def nv_world(W, name):
    return W["world"].node_tree, f'nodes["{name}"].outputs[0].default_value'


def defaults(t, S, W):
    M, G, P = W["M"], W["G"], W["P"]
    lights(S, W, "none")
    put(S, *nv_world(W, "W"), 1.0)
    put(S, *nv_world(W, "A"), 0.18)
    put(S, G["fan"], "rotation_euler", t * 1.9, 0)
    put(S, G["spool"], "rotation_euler", t * 3.2, 0)
    for k in ("nacCut", "cowlCut"):
        for i in range(3):
            put(S, G[k], "location", 0.0, i)
        hide(S, G[k], False)
    spin_disc(S, W, 0.0)
    mset(S, M["bladeH"], G=0.0, GB=0.0, CK=0.0, SM=0.0, SF=-0.07, TH=0.0, TB=0.62, XA=0.0, XZ=0.07, FC=0.0, HT=1.0)
    mset(S, M["bladeD"], TH=0.0, TB=0.62, FC=0.0)
    mset(S, M["disc"], TH=0.0, TB=0.35)
    mset(S, M["tbc"], HF=0.0, TH=0.0)
    mset(S, M["gas"], S=0.0, P=t * 1.1)
    mset(S, M["gasD"], S=0.0, P=t * 1.6)
    mset(S, M["film"], S=0.0, FG=0.0, P=t * 1.2)
    mset(S, M["chan"], S=0.0, CF=0.0, P=t * 1.4)
    mset(S, M["blanket"], S=0.0)
    mset(S, M["flame"], S=3.0)
    for k in ("chan", "film", "blanket", "tbcS", "tbcP", "gasN", "gasF", "selector"):
        hide(S, P[k])
    for k in ("tbcS", "tbcP"):
        for i in range(3):
            put(S, P[k], "location", 0.0, i)
            put(S, P[k], "rotation_euler", 0.0, i)
    put(S, W["hero"], "scale", 1.0, 2)
    hide(S, W["discgas"])
    hide(S, G["gas"])
    hero_slot(S, W)


def shots(W):
    M, G, P = W["M"], W["G"], W["P"]
    L = []
    EC = Vector((0, 0, ZE))
    AZ = -24                              # the standard hero azimuth: every blade beat starts from this framing

    def opened(S, k):
        d = Vector((0, -0.35, 1.0)).normalized()
        for key in ("nacCut", "cowlCut"):
            for i in range(3):
                put(S, G[key], "location", d[i] * 4.5 * k, i)
            hide(S, G[key], k > 0.98)

    def disc_cam(S, t, t0, t1, a0, a1, d0, d1):
        """the whole disc, three-quarter front, with room around it"""
        u = ss(seg(t, t0, t1))
        a = rad(lerp(a0, a1, u))
        d = lerp(d0, d1, u)
        c = DC + V(0, 0, -0.07)
        eye = c + Matrix.Rotation(a, 3, "Z") @ V(0, -d, d * 0.24)
        cam(S, eye, c, lens=42, fstop=8)

    # --- 1: jet engine blades spin in gas up to 200 C above their melting point ------------------------------------
    def S1a(t, S):   # the whole engine, front three-quarter, fan turning
        lights(S, W, "E")
        u = seg(t, 0.0, 1.25)
        a = rad(lerp(-6, 0, u))
        eye = EC + Matrix.Rotation(a, 3, "Z") @ Vector((-9.4, -5.6, 0.9 + 0.2 * u))
        cam(S, eye, EC + V(-1.25, 0, -0.5), lens=42, fstop=8, clip=0.05)
    L.append((0.0, 1.25, S1a))

    def S1b(t, S):   # the cutaway lifts away: the core inside, the turbine glowing at the back
        lights(S, W, "E")
        u = seg(t, 1.25, 2.35)
        opened(S, ein(seg(t, 1.3, 2.1)))
        hide(S, G["gas"], False)
        mset(S, M["gasD"], S=1.0)
        eye = EC + V(lerp(-0.4, 0.0, u), lerp(-10.6, -10.0, u), lerp(1.6, 1.7, u))
        cam(S, eye, EC + V(-0.45, 0, -0.45), lens=32, fstop=8, clip=0.05)
    L.append((1.25, 2.35, S1b))

    def S1c(t, S):   # the turbine disc on its own, the whole ring of blades turning
        lights(S, W, "D")
        a = t * 0.5
        spin_disc(S, W, a)
        hero_slot(S, W, a)
        disc_cam(S, t, 2.35, 3.5, -34, -28, 1.75, 1.6)
    L.append((2.35, 3.5, S1c))

    def S1d(t, S):   # same disc in thermal view: white-hot gas streaming through, blades glowing orange
        lights(S, W, "D", 0.12)
        a = t * 0.5
        spin_disc(S, W, a)
        hero_slot(S, W, a)
        hide(S, W["discgas"], True)
        thermal_on(S, W, 0.76, 0.76, 0.22)
        disc_cam(S, t, 3.5, 4.85, -28, -22, 1.6, 1.5)
    L.append((3.5, 4.85, S1d))

    # --- 2: each palm-sized blade makes the power of a Formula One car --------------------------------------------
    def S2a(t, S):   # one blade slides up out of its slot
        lights(S, W, "D")
        lift = 0.10 * ss(seg(t, 4.95, 6.2))
        hero_slot(S, W, 0.0, lift)
        u = seg(t, 4.85, 6.35)
        c = DC + V(0, 0, R_P + 0.012 + lift * 0.55)
        eye = c + Matrix.Rotation(rad(lerp(-34, -26, u)), 3, "Z") @ V(0, -0.40, 0.12)
        cam(S, eye, c, lens=70, fstop=10)
    L.append((4.85, 6.35, S2a))

    def S2b(t, S):   # the blade alone in the light, turning
        lights(S, W, "B")
        u = seg(t, 6.35, 8.15)
        hero_float(S, W, yaw=face(AZ, lerp(-60, -35, u)), t=t)
        bcam(S, AZ, 16, lerp(0.40, 0.37, u))
        label(S, "blade", bw(S, V(0.0, 0.0, H_AF - 0.004)))
    L.append((6.35, 8.15, S2b))

    # --- 3: normal metal is a patchwork of tiny crystals; heat and pull crack it along the seams -------------------
    def S3a(t, S):   # same framing: the blade turns into a patchwork of crystal grains
        lights(S, W, "B")
        u = seg(t, 8.15, 9.65)
        hero_float(S, W, yaw=face(AZ, lerp(-35, -28, u)), t=t)
        mset(S, M["bladeH"], G=ss(seg(t, 8.25, 9.0)), HT=0.4)
        bcam(S, AZ, 16, lerp(0.37, 0.32, ss(u)))
        label(S, "grains", bw(S, V(0.0, 0.0, 0.03)) + (S["hero"].to_3x3() @ Vector((0, 0, 0))))
    L.append((8.15, 9.65, S3a))

    def S3b(t, S):   # closer on the airfoil: the grain boundaries heat up and glow
        lights(S, W, "B", lerp(1.0, 0.55, seg(t, 9.9, 10.9)))
        u = seg(t, 9.65, 11.1)
        hero_float(S, W, yaw=face(AZ, -28), t=t, bob=False)
        mset(S, M["bladeH"], G=1.0, GB=ss(seg(t, 9.8, 10.8)), HT=0.4)
        bcam(S, AZ, 10, lerp(0.24, 0.22, u), tz=0.024)
    L.append((9.65, 11.1, S3b))

    def S3c(t, S):   # heat and pull: the blade strains, a crack runs along the boundaries
        lights(S, W, "B", 0.55)
        hero_float(S, W, yaw=face(AZ, -28), t=t, bob=False)
        jit = 0.0025 * math.sin(t * 61) * seg(t, 11.3, 11.6)
        put(S, W["hero"], "scale", 1.0 + 0.02 * ss(seg(t, 11.2, 12.0)) + jit, 2)
        mset(S, M["bladeH"], G=1.0, GB=0.7, CK=ss(seg(t, 11.55, 12.9)), HT=0.4)
        put(S, *nv_world(W, "W"), 0.8)
        bcam(S, AZ, 10, 0.22, tz=0.024, shake=0.35 * seg(t, 11.3, 11.7), t=t)
        label(S, "crack", bw(S, af_point(0.0, 0.0302)[0]))
    L.append((11.1, 13.4, S3c))

    # --- 4: so each blade is grown as one single crystal. No seams. -----------------------------------------------
    def S4a(t, S):   # the whole blade with its spiral grain selector: one crystal grows up from the bottom
        lights(S, W, "B", 0.6)
        hero_float(S, W, yaw=face(AZ, -30), t=t, bob=False)
        hide(S, P["selector"], False)
        sf = lerp(Z_ROOT1 - 0.036, H_AF + 0.003, ss(seg(t, 13.45, 15.35)))
        mset(S, M["bladeH"], SM=1.0, SF=sf, HT=0.0)
        bcam(S, AZ, 10, 0.50, tz=-0.012)
        label(S, "crystal", bw(S, V(0, 0, clamp(sf, Z_ROOT1, H_AF))))
    L.append((13.4, 15.5, S4a))

    def S4b(t, S):   # the finished blade: one flawless surface, a highlight sweeps across it
        lights(S, W, "B")
        u = seg(t, 15.5, 17.55)
        hero_float(S, W, yaw=face(AZ, lerp(-70, -20, u)), t=t)
        mset(S, M["bladeH"], HT=0.6)
        bcam(S, AZ, 16, lerp(0.39, 0.36, u))
    L.append((15.5, 17.55, S4b))

    # --- 5: inside, cool air snakes through hidden channels --------------------------------------------------------
    def S5a(t, S):   # x-ray wipe from the tip down reveals the hidden passage
        lights(S, W, "B", 0.4)
        put(S, *nv_world(W, "W"), 0.6)
        hero_float(S, W, yaw=face(AZ, -20), t=t)
        hide(S, P["chan"], False)
        mset(S, M["chan"], S=1.0, CF=0.35)
        mset(S, M["bladeH"], XA=1.0, XZ=lerp(H_AF + 0.003, Z_ROOT1 - 0.004, ss(seg(t, 17.6, 18.6))))
        bcam(S, AZ, 12, 0.40)
    L.append((17.55, 18.75, S5a))

    def S5b(t, S):   # cool air races up and down the passage
        lights(S, W, "B", 0.4)
        put(S, *nv_world(W, "W"), 0.6)
        u = seg(t, 18.75, 19.95)
        hero_float(S, W, yaw=face(AZ, lerp(-20, -8, u)), t=t)
        hide(S, P["chan"], False)
        mset(S, M["chan"], S=1.0, CF=1.0)
        mset(S, M["bladeH"], XA=1.0, XZ=Z_ROOT1 - 0.006)
        bcam(S, AZ, 12, lerp(0.40, 0.34, ss(u)))
        label(S, "chan", bw(S, camber_pt(0.20, 0.036)[0]))
    L.append((18.75, 19.95, S5b))

    # --- 6: then streams from tiny holes to blanket the surface --------------------------------------------------
    def S6a(t, S):   # closer on the leading edge: cool air streams out of every hole
        lights(S, W, "B", 0.8)
        hero_float(S, W, yaw=face(AZ, -35), t=t, bob=False)
        hide(S, P["film"], False)
        mset(S, M["bladeH"], FC=ss(seg(t, 20.0, 20.4)), HT=0.6)
        mset(S, M["film"], S=1.0, FG=ss(seg(t, 20.1, 21.1)))
        bcam(S, AZ, 14, lerp(0.30, 0.27, seg(t, 19.95, 21.45)), tz=0.024)
        label(S, "holes", bw(S, af_point(0.0011, 0.040)[0]))
    L.append((19.95, 21.45, S6a))

    def S6b(t, S):   # the whole blade wrapped in a film of cool air; hot gas streams past outside it
        lights(S, W, "B", 0.55)
        put(S, *nv_world(W, "W"), 0.7)
        u = seg(t, 21.45, 23.1)
        hero_float(S, W, yaw=face(AZ, lerp(-30, -15, u)), t=t)
        for k in ("film", "blanket", "gasF"):
            hide(S, P[k], False)
        mset(S, M["bladeH"], FC=1.0, HT=0.6)
        mset(S, M["film"], S=1.0, FG=1.0)
        mset(S, M["blanket"], S=ss(seg(t, 21.5, 22.3)))
        mset(S, M["gas"], S=0.8)
        bcam(S, AZ, 14, lerp(0.40, 0.37, u), tz=0.0)
        label(S, "film", bw(S, af_point(0.010, 0.046, off=0.0006)[0]))
    L.append((21.45, 23.1, S6b))

    # --- 7: on top, a ceramic coat holds back more heat ------------------------------------------------------------
    def shells(S, k_open):
        for key, sgn in (("tbcS", 1), ("tbcP", -1)):
            hide(S, P[key], False)
            put(S, P[key], "location", sgn * 0.016 * k_open, 1)
            put(S, P[key], "location", 0.006 * k_open, 2)
            put(S, P[key], "rotation_euler", sgn * rad(-10) * k_open, 0)

    def S7a(t, S):   # the coated blade; the ceramic coat lifts away from the metal
        lights(S, W, "B")
        u = seg(t, 23.1, 24.55)
        hero_float(S, W, yaw=face(AZ, lerp(60, 75, u)), t=t)
        shells(S, ss(seg(t, 23.5, 24.4)))
        bcam(S, AZ, 14, 0.42, tz=0.0)
        label(S, "tbc", bw(S, af_point(0.009, 0.044, off=0.0008)[0]))
    L.append((23.1, 24.55, S7a))

    def S7b(t, S):   # the outer face of the coat takes the heat, the metal inside stays cool
        lights(S, W, "B", 0.6)
        u = seg(t, 24.55, 26.0)
        hero_float(S, W, yaw=face(AZ, lerp(75, 95, u)), t=t)
        shells(S, 1.0)
        mset(S, M["tbc"], HF=ss(seg(t, 24.6, 25.3)))
        bcam(S, AZ, 16, lerp(0.40, 0.36, u), tz=0.0)
    L.append((24.55, 26.0, S7b))

    # --- 8: so the metal never reaches its melting point -----------------------------------------------------------
    def S8a(t, S):   # coat on, the blade drops home into the disc
        lights(S, W, "D")
        lift = 0.10 * (1 - ss(seg(t, 26.1, 27.0)))
        hero_slot(S, W, 0.0, lift)
        c = DC + V(0, 0, R_P + 0.012 + lift * 0.55)
        eye = c + Matrix.Rotation(rad(-26), 3, "Z") @ V(0, -0.40, 0.12)
        cam(S, eye, c, lens=70, fstop=10)
    L.append((26.0, 27.3, S8a))

    def S8b(t, S):   # thermal payoff: the same disc, white-hot gas, the blades now well below the melting point
        lights(S, W, "D", 0.12)
        a = (t - 27.3) * 0.5
        spin_disc(S, W, a)
        hero_slot(S, W, a)
        hide(S, W["discgas"], True)
        mset(S, M["bladeH"], FC=1.0)
        mset(S, M["bladeD"], FC=1.0)
        thermal_on(S, W, 0.58, 0.58, 0.2)
        disc_cam(S, t, 27.3, 28.6, -22, -28, 1.5, 1.6)
    L.append((27.3, 28.6, S8b))

    # --- 9: follow for how the world is really engineered ----------------------------------------------------------
    def S9a(t, S):   # the open engine in profile, the core glowing
        lights(S, W, "E")
        opened(S, 1.0)
        hide(S, G["gas"], False)
        mset(S, M["gasD"], S=1.0)
        u = seg(t, 28.6, 30.3)
        eye = EC + V(lerp(0.0, 0.4, u), -10.0, lerp(1.7, 1.5, u))
        cam(S, eye, EC + V(0.0, 0, -0.45), lens=32, fstop=8, clip=0.05)
    L.append((28.6, 30.3, S9a))

    def S9b(t, S):   # the cowl closes, slow pull-back on the whole engine
        lights(S, W, "E")
        opened(S, 1.0 - ss(seg(t, 30.4, 31.2)))
        u = seg(t, 30.3, 32.0)
        a = rad(lerp(-30, -24, u))
        eye = EC + Matrix.Rotation(a, 3, "Z") @ V(-8.6 - 1.4 * eout(u), -2.8, 1.0 + 0.4 * eout(u))
        cam(S, eye, EC + V(0.4, 0, -0.55), lens=40, fstop=8, clip=0.05)
    L.append((30.3, T_END + 0.1, S9b))
    return L


# ----------------------------------------------------------------------------------------------- bake

def project(eye, q, lens, p, w=1080, h=1920):
    pc = q.inverted() @ (Vector(p) - eye)
    if pc.z >= -0.001:
        return None
    k = lens / 36.0
    u = 0.5 + (pc.x / -pc.z) * k * (h / w)
    v = 0.5 + (pc.y / -pc.z) * k
    return round(u * w, 1), round((1 - v) * h, 1)


def bake(W, labels_out):
    tracks, camk, labels = {}, [], {}
    L = shots(W)
    qprev = {}
    for i, (t0, t1, fn) in enumerate(L):
        f0 = math.ceil(t0 * FPS - 1e-6) + 1
        f1 = min(math.ceil(t1 * FPS - 1e-6), F_END)
        fr = list(range(f0, f1 + 1))
        if i > 0:
            fr = [f0 - 0.49] + fr
        if i < len(L) - 1:
            fr = fr + [f1 + 0.49]
        for f in fr:
            t = (f - 1) / FPS
            S = {}
            defaults(t, S, W)
            fn(t, S)
            S.pop("hero", None)
            c = S.pop("cam")
            camk.append((f,) + c)
            lb = S.pop("labels", {})
            if f == int(f):
                for name, p in lb.items():
                    xy = project(c[0], c[1], c[2], p)
                    if xy:
                        labels.setdefault(name, []).append([int(f), *xy])
            hq = [S.get((W["hero"], "rotation_quaternion", k)) for k in range(4)]
            if all(hq):
                q = Quaternion([v for v, _ in hq])
                pq = qprev.get("hero")
                if pq is not None and q.dot(pq) < 0:
                    for k in range(4):
                        S[(W["hero"], "rotation_quaternion", k)] = (-q[k], False)
                    q = -q
                qprev["hero"] = q
            for k, (v, const) in S.items():
                tracks.setdefault(k, []).append((f, v, const))
    with open(labels_out, "w") as fh:
        json.dump(labels, fh)
    camo = W["cam"]
    prev = None
    for f, eye, q, lens, fstop, focus, clip in camk:
        if prev is not None and q.dot(prev) < 0:
            q = -q
        prev = q
        for i in range(3):
            tracks.setdefault((camo, "location", i), []).append((f, eye[i], False))
        for i in range(4):
            tracks.setdefault((camo, "rotation_quaternion", i), []).append((f, q[i], False))
        cd = camo.data
        tracks.setdefault((cd, "lens", 0), []).append((f, lens, False))
        tracks.setdefault((cd, "dof.aperture_fstop", 0), []).append((f, fstop, False))
        tracks.setdefault((cd, "dof.focus_distance", 0), []).append((f, focus, False))
        tracks.setdefault((cd, "clip_start", 0), []).append((f, clip, False))
    n = 0
    for (idb, path, idx), keys in tracks.items():
        keys.sort(key=lambda k: k[0])
        ad = idb.animation_data or idb.animation_data_create()
        if ad.action is None:
            ad.action = bpy.data.actions.new(f"{idb.name}_A")
        fc = ad.action.fcurve_ensure_for_datablock(idb, path, index=idx)
        fc.keyframe_points.add(len(keys))
        fc.keyframe_points.foreach_set("co", [c for f, v, _ in keys for c in (f, v)])
        const = keys[0][2]
        try:
            fc.keyframe_points.foreach_set("interpolation", [0 if const else 1] * len(keys))
        except Exception:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT" if const else "LINEAR"
        fc.update()
        n += len(keys)
    print("BAKED", len(tracks), "tracks", n, "keys")


# ----------------------------------------------------------------------------------------------- main

def cycles_settings(scn, samples):
    scn.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        kinds = () if os.environ.get("CPU_ONLY") else ("OPTIX", "CUDA", "HIP", "METAL")   # CPU_ONLY: leave the GPU to another job
        for kind in kinds:
            try:
                pr.compute_device_type = kind
                pr.get_devices()
                gpus = [d for d in pr.devices if d.type == kind]
                if gpus:
                    for d in pr.devices:          # an AMD card renders faster with the CPU helping
                        d.use = d.type == kind or (kind == "HIP" and d.type == "CPU")
                    scn.cycles.device = "GPU"
                    print("GPU", kind, [d.name for d in gpus])
                    break
            except TypeError:
                pass
    except Exception as e:
        print("no gpu", e)
    cy = scn.cycles
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.015
    cy.use_denoising = True
    try:
        optix = bpy.context.preferences.addons["cycles"].preferences.compute_device_type == "OPTIX"
        cy.denoiser = "OPTIX" if optix and scn.cycles.device == "GPU" else "OPENIMAGEDENOISE"
        cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        cy.denoising_use_gpu = scn.cycles.device == "GPU"     # OIDN on the GPU: ~20% faster per frame on the PC
    except Exception as e:
        print("skip denoise opt", e)
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 6
    cy.transmission_bounces, cy.transparent_max_bounces = 8, 32
    cy.sample_clamp_indirect = 8.0
    cy.volume_bounces = 0
    try:
        cy.volume_step_rate = globals().get("VOL_STEP_RATE", 1.0)
    except Exception as e:
        print("skip volume step", e)
    cy.caustics_reflective = cy.caustics_refractive = False
    scn.render.use_persistent_data = True
    for ob in bpy.data.objects:            # Cycles area lights reflect on their own: the Eevee reflection cards go
        if ob.name.startswith("Card"):
            ob.hide_render = True
            ob.animation_data_clear()


def render_settings(scn, h=1920, samples=64):
    if "--eevee" not in sys.argv:
        cycles_settings(scn, samples)
    else:
        scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_y = h
    scn.render.resolution_x = round(h * 9 / 16 / 2) * 2
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    ee = scn.eevee
    ee.taa_render_samples = samples
    for k, v in (("use_raytracing", True), ("use_shadows", True), ("use_fast_gi", True), ("motion_blur_steps", 1),
                 ("shadow_ray_count", 2), ("shadow_step_count", 10), ("use_shadow_jitter_viewport", True),
                 ("fast_gi_distance", 0.5), ("use_bokeh_jittered", True), ("bokeh_overblur", 3.0)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print("skip", k, e)
    try:
        ee.ray_tracing_options.resolution_scale = "1"
        ee.ray_tracing_options.trace_max_roughness = 0.6
    except Exception as e:
        print("skip rt", e)
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.5
    scn.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scn.view_settings.look = look
            break
        except TypeError:
            pass
    scn.view_settings.exposure = 0.0
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.compression = 15


def card(name, light_ob, mat, sx, sy):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
    ob = obj_from_bm(name, bm, mat)
    ob.location = light_ob.location + (light_ob.rotation_quaternion @ Vector((0, 0, 1))) * 0.02
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = light_ob.rotation_quaternion
    for k in ("visible_camera", "visible_shadow"):
        try:
            setattr(ob, k, False)
        except Exception:
            pass
    return ob


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    M = materials()
    world = studio_world()
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "AUTO"
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_blades = 7
    cd.clip_end = 400
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    me_blade, rxr = blade_mesh("Blade")
    me_blade.materials.append(M["bladeD"])
    G = build_engine(M, me_blade, rxr)
    floor("FloorE", E0, 9.0, M["floorE"])
    # disc studio: disc on an axle, a slim column behind, the hero blade
    disc, body, posts, blades = build_disc(M, "Disc", me_blade, rxr, skip_hero=True, loc=DC, rot=(0, 0, rad(90)))
    ax = cyl("Axle", 0.06, 0.34, DC + V(0, 0.12, 0), M["steel"], n=96)
    ax.rotation_euler = (rad(90), 0, 0)
    col = cyl("Column", 0.045, DC.z - 0.03, D0 + V(0, 0.27, (DC.z - 0.03) / 2), M["paint"], n=96)
    bevel_mod = col.modifiers.new("B", "BEVEL")
    bevel_mod.width, bevel_mod.segments = 0.006, 4
    weighted(col)
    floor("FloorD", D0, 2.2, M["floorD"])
    gr = empty("DiscGasRoot", DC)
    gr.rotation_euler = (0, 0, rad(90))
    dg = gas_disc(M, "DiscGas", gr)
    floor("FloorB", HOVER - V(0, 0, 0.10), 1.2, M["floorB"])
    hero = mesh_obj("Hero", me_blade, None)
    hero.rotation_mode = "QUATERNION"
    hero.material_slots[0].link = "OBJECT"
    hero.material_slots[0].material = M["bladeH"]
    P = build_blade_parts(M, me_blade, hero)
    for k in ("tbcS", "tbcP"):
        P[k].rotation_mode = "XYZ"
    # lights: (name, object, energy); names start with the set letter
    LT = []
    hc = DC + V(0, 0, R_P + 0.08)
    for name, loc, tgt, sx, sy, colr, e, shape in (
            ("Ekey", (-3.2, -6.2, 7.2), (0, 0, ZE), 6.0, 2.6, "#fff3e6", 5200, "RECTANGLE"),
            ("Efill", (6.5, -7.0, 2.2), (0, 0, ZE), 6.0, 6.0, "#9aa0a8", 650, "RECTANGLE"),
            ("ErimA", (6.5, 6.0, 3.6), (0, 0, ZE), 0.5, 7.0, "#fff1e2", 3400, "RECTANGLE"),
            ("ErimC", (-6.5, 6.0, 3.6), (0, 0, ZE), 0.5, 7.0, "#e6eeff", 3400, "RECTANGLE"),
            ("Etop", (0.5, 0.0, 9.5), (0, 0, ZE), 5.0, 5.0, "#ffffff", 2200, "DISK"),
            ("Dkey", tuple(D0 + V(-0.75, -1.05, 1.95)), tuple(hc), 1.2, 0.5, "#fff3e6", 170, "RECTANGLE"),
            ("Dfill", tuple(D0 + V(1.4, -1.2, 0.75)), tuple(hc), 1.5, 1.5, "#9aa0a8", 30, "RECTANGLE"),
            ("DrimA", tuple(D0 + V(0.95, 0.95, 1.15)), tuple(hc), 0.08, 1.4, "#fff1e2", 95, "RECTANGLE"),
            ("DrimC", tuple(D0 + V(-0.95, 0.95, 1.05)), tuple(hc), 0.08, 1.4, "#e6eeff", 95, "RECTANGLE"),
            ("Dtop", tuple(D0 + V(0.05, 0.25, 2.25)), tuple(hc), 0.6, 0.6, "#ffffff", 60, "DISK"),
            ("Bkey", tuple(HOVER + V(-0.9, -1.2, 1.3)), tuple(HOVER), 1.2, 0.55, "#fff3e6", 150, "RECTANGLE"),
            ("Bfill", tuple(HOVER + V(1.3, -1.1, 0.2)), tuple(HOVER), 1.2, 1.2, "#9aa0a8", 30, "RECTANGLE"),
            ("BrimA", tuple(HOVER + V(0.9, 0.9, 0.5)), tuple(HOVER), 0.06, 1.4, "#fff1e2", 150, "RECTANGLE"),
            ("BrimC", tuple(HOVER + V(-0.9, 0.9, 0.45)), tuple(HOVER), 0.06, 1.4, "#e6eeff", 150, "RECTANGLE"),
            ("Btop", tuple(HOVER + V(0.05, 0.2, 1.6)), tuple(HOVER), 0.5, 0.5, "#ffffff", 50, "DISK")):
        ob = area(name, loc, tgt, sx, sy, colr, e, shape)
        LT.append((name, ob, e))
    cards = []
    for setname, keyname, sx, sy, s in (("E", "Ekey", 6.0, 2.6, 5.0), ("D", "Dkey", 1.0, 0.45, 6.0),
                                        ("B", "Bkey", 1.0, 0.45, 6.0)):
        m = card_mat("Card" + setname, "#ffffff", s)
        lo = [o for n, o, _ in LT if n == keyname][0]
        card("Card" + setname, lo, m, sx, sy)
        cards.append((setname, m, s))
    W = dict(M=M, cam=camo, world=world, G=G, P=P, hero=hero, disc=disc, discgas=dg, lights=LT, cards=cards)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(out)), "labels.json"))
    render_settings(scn)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)


def render(outdir, h, samples, which):
    scn = bpy.context.scene
    render_settings(scn, h, samples)
    if which and "-" in which:
        a, b = (int(x) for x in which.split("-"))
        frames = range(a, b + 1)
    elif which:
        frames = [int(x) for x in which.split(",")]
    else:
        frames = range(scn.frame_start, scn.frame_end + 1)
    os.makedirs(outdir, exist_ok=True)
    for f in frames:
        p = os.path.join(outdir, f"f_{f:04d}.png")
        if os.path.exists(p) and "--skip" in sys.argv:
            continue
        scn.frame_set(f)
        scn.render.filepath = p
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv and argv[0] == "build":
        build(argv[1])
    elif argv and argv[0] == "render":
        render(argv[1], int(argv[2]), int(argv[3]), argv[4] if len(argv) > 4 and not argv[4].startswith("--") else None)
