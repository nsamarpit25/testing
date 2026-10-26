

# ----------------------------------------------------------------------------------------------- shots

def put(S, idb, path, v, idx=0, const=False):
    S[(idb, path, idx)] = (float(v), const)


def nv(m, name="S"):  # (node tree, path) of a material's Value node
    return m.node_tree, f'nodes["{name}"].outputs[0].default_value'


def cam(S, eye, tgt, lens=28, roll=0.0, fstop=8.0, focus=None, yaw=0.0, pitch=0.0, clip=0.1, shake=0.0, t=0.0):
    eye, tgt = Vector(eye), Vector(tgt)
    d = tgt - eye
    if shake:   # slow, smooth handheld drift (degrees)
        yaw += rad(shake) * (math.sin(t * 1.7) * 0.6 + math.sin(t * 3.1 + 1.0) * 0.4)
        pitch += rad(shake) * (math.sin(t * 2.3 + 2.0) * 0.6 + math.sin(t * 0.9) * 0.4)
    if yaw or pitch:
        d = Matrix.Rotation(yaw, 3, "Z") @ d
        side = d.cross(Vector((0, 0, 1)))
        if side.length > 1e-6:
            d = Matrix.Rotation(pitch, 3, side.normalized()) @ d
    q = d.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), roll)
    S["cam"] = (eye, q, lens, fstop, focus if focus is not None else (tgt - eye).length, clip)


def whip(t, t_end=None, t_start=None, amt=rad(60), dur=0.16):
    y = 0.0
    if t_end is not None:
        y += amt * ein(seg(t, t_end - dur, t_end))
    if t_start is not None:
        y -= amt * (1 - eout(seg(t, t_start, t_start + dur)))
    return y


def label(S, name, p):
    S.setdefault("labels", {})[name] = Vector(p)


def place_train(S, W, s_front):
    for i, car in enumerate(W["train"]):
        sc = s_front - 1.35 - CAR_LEN / 2 - i * CAR_LEN
        m = frame_matrix(sc)
        q = m.to_quaternion()
        prev = W["qprev"].get(i)
        if prev is not None and q.dot(prev) < 0:
            q = -q
        W["qprev"][i] = q
        for k in range(3):
            put(S, car, "location", m.translation[k], k)
        for k in range(4):
            put(S, car, "rotation_quaternion", q[k], k)


def train_x(s_front):
    return track_frame(s_front)[0]


def ride_light(S, W, sun=2.6, world=1.0):
    put(S, W["sun"], "energy", sun)
    put(S, *nv_world(W, "W"), world)


def nv_world(W, name):
    return W["world"].node_tree, f'nodes["{name}"].outputs[0].default_value'


def studio(S, W):
    put(S, W["sun"], "energy", 0.0)
    put(S, W["fill"], "energy", 0.0)
    put(S, *nv_world(W, "W"), 0.06)


def defaults(t, S, W):
    M, K, F, R = W["M"], W["K"], W["F"], W["R"]
    ride_light(S, W)
    put(S, *nv(M["haze"], "D"), 0.00035)
    for i in range(N_CARS):
        put(S, *nv(M[f"mag{i}"]), 0.0)
    put(S, *nv(M["magstudio"]), 0.0)
    put(S, *nv(M["fin_world"], "H"), 0.0)
    put(S, *nv(M["fin_world"], "MX"), -1e4)
    put(S, *nv(M["fin_macro"], "H"), 0.0)
    put(S, *nv(M["fin_macro"], "X"), 0.0)
    put(S, *nv(M["fin_macro"], "MX"), -10.0)
    for k in ("eddyA", "eddyB"):
        put(S, *nv(M[k]), 0.0)
        put(S, *nv(M[k], "P"), 0.0)
    for k in ("field", "arrow_c", "arrow_a"):
        put(S, *nv(M[k]), 0.0)
        put(S, *nv(M[k], "A"), 0.0)
    for a in ("arrow_move", "arrow_back"):
        put(S, K[a], "scale", 0.001, 0)
    put(S, K["rig"], "location", MC.x - 1.4, 0)
    put(S, K["light2"], "energy", 0.0)
    put(S, *nv(M["backpanel"]), 0.0)
    put(S, *nv(M["xmetal"], "X"), 0.0)
    put(S, *nv(M["xmag"], "X"), 0.0)
    put(S, *nv(M["xmag"]), 0.0)
    put(S, W["fill"], "energy", 0.6)
    put(S, *nv(M["pad"]), 0.0)
    for p in F["pads"]:
        put(S, p, "scale", 0.13, 1)
    put(S, F["plate"], "location", FR.x, 0)
    for sp, *_ in F["sparks"]:
        put(S, sp, "hide_render", 1, const=True)
    beacon = 6.0 * (0.25 + 0.75 * (math.sin(t * 2 * math.pi / 1.6) > 0.6))
    put(S, *nv(M["redlamp"]), beacon)
    for k, ob in enumerate(R["lfins"]):
        put(S, ob, "rotation_euler", rad(-90), 0)
    place_train(S, W, RUN.at(0.0)[0])


def shots(W):
    M, K, F, R = W["M"], W["K"], W["F"], W["R"]
    L = []

    # --- line 1: zero to 128 mph in 3.5 seconds ----------------------------------------------------------------
    def S1a(t, S):   # beside the lead car; the launch rips it out of frame
        tau = t - TAU_LAUNCH
        s = RUN.at(tau)[0]
        x0 = train_x(RUN.at(0)[0]).x
        u = seg(t, 0.0, 1.25)
        cam(S, V(x0 - 0.6 + 0.4 * u, -2.7 + 0.2 * u, 2.45), V(x0 - 2.6 + 0.4 * u, 0, 2.95), lens=30,
            fstop=2.8, roll=rad(-2), shake=0.25, t=t, yaw=whip(t, t_end=1.25, amt=rad(-55)))
        place_train(S, W, s)
    L.append((0.0, 1.25, S1a))

    def S1b(t, S):   # low and ahead: the nose comes at us and passes
        tau = t - TAU_LAUNCH
        s = RUN.at(tau)[0]
        x = train_x(s).x
        u = seg(t, 1.25, 2.8)
        cam(S, V(x + 6.5 - 9.0 * ein(u), -2.9, 2.05), V(x - 2.0, 0, 2.7), lens=21, fstop=4, roll=rad(lerp(4, -3, u)),
            yaw=whip(t, t_start=1.25, amt=rad(-55)))
        place_train(S, W, s)
    L.append((1.25, 2.8, S1b))

    def S1c(t, S):   # chase cam: the train pulls away towards the tower
        tau = t - TAU_LAUNCH + 1.7
        s = RUN.at(tau)[0]
        x = train_x(s).x
        u = seg(t, 2.8, 4.7)
        eye = V(x - TRAIN_LEN - 7.0 - 26 * ein(u), -3.6 - 1.5 * u, 4.2 + 1.5 * u)
        cam(S, eye, V(eye.x + 60, 0.0, eye.z + lerp(9, 20, ss(u))), lens=19, fstop=8, roll=rad(lerp(-5, 0, u)), clip=0.3)
        place_train(S, W, s)
    L.append((2.8, 4.7, S1c))

    # --- line 2: built for speed; stopping was the challenge ---------------------------------------------------
    T2A = RUN.tau_s(S_UP + 93)

    def S2a(t, S):   # from the top of the climb looking down: it rockets up at us
        tau = T2A + (t - 5.85)
        u = seg(t, 4.7, 6.4)
        cam(S, V(-8.8, -6.8, 122 + 1.2 * u), V(-0.8, 0, lerp(94, 104, ss(u))), lens=24, fstop=5.6, roll=rad(-6), clip=0.3)
        place_train(S, W, RUN.at(tau)[0])
    L.append((4.7, 6.4, S2a))

    T2B = RUN.tau_s(S_TOP)

    def S2b(t, S):   # the crest against the dusk sky
        tau = T2B + (t - 6.88)
        u = seg(t, 6.4, 7.25)
        cam(S, V(lerp(19, 16, u), lerp(-33, -30, u), lerp(140.5, 141.5, u)), V(15, 0, 134.5), lens=27, fstop=8, clip=0.5)
        place_train(S, W, RUN.at(tau)[0])
        label(S, "height", (15, 0, 139.8))
    L.append((6.4, 7.25, S2b))

    T2C = RUN.tau_s(s_of_x(150))

    def S2c(t, S):   # down on the brake run: it comes at us at full speed
        tau = T2C + (t - 8.95)
        u = seg(t, 7.25, 9.3)
        cam(S, V(152 + 2.0 * u, -2.4, 2.75), V(60, 0, lerp(10, 6, u)), lens=lerp(48, 40, u), fstop=4, clip=0.3,
            yaw=whip(t, t_end=9.3, amt=rad(65)), shake=0.15, t=t)
        s = RUN.at(tau)[0]
        place_train(S, W, s)
        put(S, *nv(M["fin_world"], "MX"), train_x(s).x - 1.4)
        put(S, *nv(M["fin_world"], "H"), 0.0)
    L.append((7.25, 9.3, S2c))

    # --- line 3: brake pads would wear out fast; magnets under every car ----------------------------------------
    def S3a(t, S):   # friction brake demo: pads clamp, glow, spark and wear
        studio(S, W)
        u = seg(t, 9.3, 11.3)
        cam(S, FR + V(-1.2, -1.35, 0.6).lerp(V(-0.95, -1.1, 0.45), ss(u)), FR + V(-0.2, 0, 0.02), lens=36, fstop=3.2,
            yaw=whip(t, t_start=9.3, amt=rad(-60)), shake=0.2, t=t)
        put(S, F["plate"], "location", FR.x + 14 - (t - 9.3) * 12.0, 0)
        heat = ss(seg(t, 9.45, 10.5))
        put(S, *nv(M["pad"]), 3.2 * heat)
        for p in F["pads"]:
            put(S, p, "scale", lerp(0.13, 0.035, ss(seg(t, 9.7, 11.1))), 1)
        for sp, ph, spd, vy, vz, life in F["sparks"]:
            if t < 9.42:
                continue
            c = ((t - 9.42) / life + ph) % 1.0
            a = c * life * min(1.0, (t - 9.42) / 0.25)
            vel = V(-spd, vy * spd * 0.18, vz - 9.8 * a)
            p = FR + V(-0.37, 0.025 * (1 if vy > 0 else -1), 0.0) + V(-spd * a, vy * spd * 0.18 * a, vz * a - 4.9 * a * a)
            put(S, sp, "hide_render", 0, const=True)
            for k in range(3):
                put(S, sp, "location", p[k], k)
            q = vel.normalized().to_track_quat("X", "Z")
            for k in range(4):
                put(S, sp, "rotation_quaternion", q[k], k)
        if 9.55 < t < 11.2:
            label(S, "pads", FR + V(0, -0.12, 0.19))
    L.append((9.3, 11.3, S3a))

    S3B_S = s_of_x(-155)

    def S3b(t, S):   # under the parked train: rows of magnets light up car by car
        u = seg(t, 11.3, 14.8)
        x0 = train_x(S3B_S).x
        cam(S, V(x0 - 0.8 - 7.0 * ss(u), -2.15, 1.82), V(x0 - 2.4 - 7.0 * ss(u), 0, 2.32), lens=28, fstop=2.8,
            roll=rad(-3), shake=0.15, t=t)
        place_train(S, W, S3B_S)
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 3.0 * ss(seg(t, 12.75 + 0.3 * i, 13.1 + 0.3 * i)))
        if 12.9 < t < 14.75:
            label(S, "magnets", (x0 - 2.6 - 7.0 * ss(u), -0.09, 2.2))
    L.append((11.3, 14.8, S3b))

    # --- line 4: on the track, thin copper fins ----------------------------------------------------------------
    def S4(t, S):    # three-quarter dolly along the fin row
        u = seg(t, 14.8, 17.4)
        x = lerp(101, 108, ss(u))
        cam(S, V(x, -1.75, 2.85), V(x + 3.2, 0, 2.2), lens=34, fstop=2.2, roll=rad(2), shake=0.12, t=t)
        place_train(S, W, s_of_x(372))
        if 15.6 < t < 17.35:
            label(S, "fins", (x + 3.2, 0, 2.42))
    L.append((14.8, 17.4, S4))

    # --- line 5: a magnet sweeps past a fin; swirling currents: eddy currents ----------------------------------
    def mx_at(t):   # macro magnet position along the fin (relative x)
        if t < 19.8:
            return lerp(-1.35, -0.02, eout(seg(t, 17.4, 19.6)))
        return -0.02 + 0.32 * seg(t, 19.8, 24.85) + 0.25 * seg(t, 24.85, 29.0) + 0.3 * seg(t, 29.95, 32.65)

    def macro_common(t, S, mx):
        studio(S, W)
        put(S, K["rig"], "location", MC.x + mx, 0)
        put(S, *nv(M["fin_macro"], "MX"), mx)
        put(S, *nv(M["magstudio"]), 0.35)
        put(S, *nv(M["xmag"]), 0.35)

    def eddy(S, t, s_amt, spin=1.0):
        for k, m in (("eddyA", 1), ("eddyB", -1)):
            put(S, *nv(M[k]), s_amt)
            put(S, *nv(M[k], "P"), m * spin * (t - 20.3) * 1.7)
        put(S, *nv(M["field"]), 2.2 * min(1, s_amt))
        put(S, *nv(M["field"], "A"), 0.85 * min(1, s_amt))

    def S5a(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        u = seg(t, 17.4, 19.8)
        cam(S, MC + V(mx * 0.4 + 0.95, -0.85, 0.78), MC + V(mx * 0.7, 0, 0.26), lens=36, fstop=2.8,
            yaw=whip(t, t_start=17.4, amt=rad(50)))
    L.append((17.4, 19.8, S5a))

    def S5b(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), ss(seg(t, 19.85, 20.5)))
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), 0.8 * ss(seg(t, 19.85, 20.5)))
        eddy(S, t, ss(seg(t, 20.35, 21.0)))
        u = ss(seg(t, 19.8, 23.8))
        a = rad(lerp(-90, -60, u))
        r = lerp(1.0, 0.86, u)
        cam(S, MC + V(mx + r * math.cos(a), r * math.sin(a), lerp(0.36, 0.56, u)), MC + V(mx, 0, 0.23), lens=38, fstop=3.2)
    L.append((19.8, 23.8, S5b))

    def S5c(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), 1.0)
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), 0.8)
        eddy(S, t, 1.0)
        u = ss(seg(t, 23.8, 24.85))
        ring = MC + V(mx + 0.27, 0, 0.21)
        cam(S, ring + V(0.22, -0.62, 0.3).lerp(V(0.08, -0.4, 0.14), u), ring, lens=40, fstop=2.8)
        if t > 23.85:
            label(S, "eddy", ring + V(0, 0, 0.11))
    L.append((23.8, 24.85, S5c))

    # --- line 6: their own field pushes back; speed becomes heat ------------------------------------------------
    def S6a(t, S):
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), 1.0)
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), 0.8)
        eddy(S, t, 1.0 + 0.7 * ss(seg(t, 25.8, 26.4)), spin=1.0)
        put(S, K["arrow_move"], "scale", max(0.001, eout(seg(t, 25.0, 25.45))), 0)
        put(S, *nv(M["arrow_c"]), 2.5 * seg(t, 25.0, 25.2))
        put(S, *nv(M["arrow_c"], "A"), 0.95 * seg(t, 25.0, 25.2))
        put(S, K["arrow_back"], "scale", max(0.001, eout(seg(t, 27.9, 28.3))), 0)
        put(S, *nv(M["arrow_a"]), 3.0 * seg(t, 27.9, 28.05))
        put(S, *nv(M["arrow_a"], "A"), 0.95 * seg(t, 27.9, 28.05))
        u = ss(seg(t, 24.85, 28.75))
        cam(S, MC + V(mx - 0.5 + 0.15 * u, -1.25 + 0.1 * u, 0.9 - 0.1 * u), MC + V(mx + 0.06, -0.08, 0.36), lens=32, fstop=4,
            yaw=whip(t, t_end=28.75, amt=rad(-60)))
        if 25.35 < t < 27.85:
            label(S, "motion", MC + V(mx + 0.2, 0, 0.68))
        if 27.98 < t < 28.72:
            label(S, "drag", MC + V(mx + 0.16, -0.32, 0.3))
    L.append((24.85, 28.75, S6a))

    T6B = RUN.tau_s(BR0 + 62)

    def S6b(t, S):   # wide: the train slows along the brake run, a thermal trail behind it
        tau = T6B + (t - 28.75)
        s = RUN.at(tau)[0]
        x = train_x(s).x
        place_train(S, W, s)
        put(S, *nv(M["fin_world"], "MX"), x - 1.4)
        put(S, *nv(M["fin_world"], "H"), ss(seg(t, 28.85, 29.3)) * 1.3)
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 0.9)
        cam(S, V(x - 3, -24, 10.5), V(x - 12, 0, 2.2), lens=32, fstop=8, clip=0.5,
            yaw=whip(t, t_start=28.75, amt=rad(-60)))
    L.append((28.75, 29.95, S6b))

    def S6c(t, S):   # macro thermal: the fin glows where the magnet has just passed
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "X"), lerp(1.0, 0.0, ss(seg(t, 29.95, 30.4))))
        for k in ("xmetal", "xmag"):
            put(S, *nv(M[k], "X"), lerp(0.8, 0.0, ss(seg(t, 29.95, 30.4))))
        eddy(S, t, lerp(1.0, 0.25, seg(t, 29.95, 30.6)))
        put(S, *nv(M["fin_macro"], "H"), 1.4 * ss(seg(t, 30.1, 30.8)))
        u = ss(seg(t, 29.95, 31.3))
        cam(S, MC + V(mx - 0.55 + 0.1 * u, -0.95, 0.3), MC + V(mx - 0.32, 0, 0.21), lens=42, fstop=2.8)
    L.append((29.95, 31.3, S6c))

    # --- line 7: nothing touches, nothing wears out, no power ---------------------------------------------------
    def S7a(t, S):   # end-on: light through both air gaps
        mx = mx_at(t)
        macro_common(t, S, mx)
        put(S, *nv(M["fin_macro"], "H"), lerp(1.4, 0.0, ss(seg(t, 31.3, 32.2))))
        put(S, K["light2"], "energy", 300.0)
        put(S, *nv(M["backpanel"]), 6.0)
        put(S, *nv(M["magstudio"]), 0.12)
        put(S, *nv(M["xmag"]), 0.12)
        u = ss(seg(t, 31.3, 32.65))
        cam(S, MC + V(mx + lerp(1.45, 1.05, u), 0.0, 0.3), MC + V(mx, 0, 0.3), lens=85, fstop=5.6)
    L.append((31.3, 32.65, S7a))

    T7B = RUN.tau_s(s_of_x(199))

    def S7b(t, S):   # low beside the fins as the cars glide over them
        tau = T7B + (t - 33.05)
        s = RUN.at(tau)[0]
        place_train(S, W, s)
        u = seg(t, 32.65, 33.85)
        cam(S, V(197.5 + 0.8 * u, -1.32, 2.2), V(214, 0.15, 2.45), lens=22, fstop=4, roll=rad(-2))
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 0.5)
    L.append((32.65, 33.85, S7b))

    T7C = RUN.tau_s(s_of_x(262))

    def S7c(t, S):   # straight down on the brake run: no cables, no power, it just glides to a stop
        tau = T7C + (t - 33.85)
        s = RUN.at(tau)[0]
        place_train(S, W, s)
        u = ss(seg(t, 33.85, 35.0))
        cam(S, V(276, 0.0, lerp(46, 38, u)), V(276, 0.001, 2), lens=40, roll=rad(90), fstop=11, clip=1.0)
    L.append((33.85, 35.0, S7c))

    # --- line 8: a launch falls short, rolls back, fins pop up and catch it ---------------------------------------
    T8A = ROLL.tau_apex()

    def S8a(t, S):
        tau = T8A + (t - 36.25)
        s = ROLL.at(tau)[0]
        place_train(S, W, s)
        z = train_x(s).z
        u = seg(t, 35.0, 36.7)
        cam(S, V(-45, -150, 66), V(-2, 0, lerp(z - 4, 104, 0.35)), lens=62, fstop=8, clip=1.0,
            yaw=whip(t, t_start=35.0, amt=rad(-45)))
    L.append((35.0, 36.7, S8a))

    def S8b(t, S):   # at the foot of the climb looking up: it comes back down, backwards
        tau = T8A + (t - 36.25)
        place_train(S, W, ROLL.at(tau)[0])
        u = seg(t, 36.7, 37.95)
        cam(S, V(-15.5, -9.5, 4.2), V(-1.5, 0, lerp(70, 40, ss(u))), lens=19, fstop=8, roll=rad(-8))
    L.append((36.7, 37.95, S8b))

    S8C_S = s_of_x(-110) + TRAIN_LEN
    T8C = ROLL.tau_s(S8C_S, falling=True)
    LFX = [ob.location.x for ob in R["lfins"]]

    def S8c(t, S):   # on the launch track: fins snap up in a wave, the train rolls back into them
        tau = T8C + (t - 39.4)
        s = ROLL.at(tau)[0]
        place_train(S, W, s)
        x_far, x_near = max(LFX), min(LFX)
        for ob, x in zip(R["lfins"], LFX):
            tp = 38.02 + 0.42 * (x_far - x) / (x_far - x_near)
            k = seg(t, tp, tp + 0.09)
            k = k + 0.12 * math.sin(math.pi * seg(t, tp + 0.09, tp + 0.2))
            put(S, ob, "rotation_euler", rad(-90) * (1 - k), 0)
        rear = train_x(s - TRAIN_LEN).x
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 1.4 * ss(seg(t, 38.75, 39.0)))
        u = seg(t, 37.95, 39.55)
        cam(S, V(-123.5 - 1.0 * u, -2.3, 2.5), V(-100, 0.2, 2.75), lens=30, fstop=4, roll=rad(2))
    L.append((37.95, 39.55, S8c))

    # --- line 9: follow ----------------------------------------------------------------------------------------
    def S9(t, S):
        u = ss(seg(t, 39.55, T_END))
        place_train(S, W, s_of_x(372) + TRAIN_LEN)
        cam(S, V(100, -205, 20).lerp(V(112, -250, 30), u), V(45, 0, 62).lerp(V(45, 0, 58), u), lens=28, fstop=11,
            clip=1.0)
        for i in range(N_CARS):
            put(S, *nv(M[f"mag{i}"]), 0.6)
        put(S, *nv(M["fin_world"], "MX"), 340)
        put(S, *nv(M["fin_world"], "H"), 0.0)
        for ob in R["lfins"]:
            put(S, ob, "rotation_euler", 0.0, 0)
    L.append((39.55, T_END, S9))
    return L


def project(eye, q, lens, p, w=1080, h=1920):
    pc = q.inverted() @ (Vector(p) - eye)
    if pc.z >= -0.01:
        return None
    k = lens / 36.0     # sensor fit AUTO: the 36 mm sensor spans the longer (vertical) side
    u = 0.5 + (pc.x / -pc.z) * k * (h / w)
    v = 0.5 + (pc.y / -pc.z) * k
    return round(u * w, 1), round((1 - v) * h, 1)


def bake(W, labels_out):
    tracks, camk, labels = {}, [], {}
    W["qprev"] = {}
    L = shots(W)
    for i, (t0, t1, fn) in enumerate(L):
        f0 = math.ceil(t0 * FPS - 1e-6) + 1
        f1 = math.ceil(t1 * FPS - 1e-6)
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
            c = S.pop("cam")
            camk.append((f,) + c)
            lb = S.pop("labels", {})
            if f == int(f):
                for name, p in lb.items():
                    xy = project(c[0], c[1], c[2], p)
                    if xy:
                        labels.setdefault(name, []).append([int(f), *xy])
            for k, (v, const) in S.items():
                tracks.setdefault(k, []).append((f, v, const))
    hud = []
    for f in range(1, int(4.8 * FPS)):
        t = (f - 1) / FPS
        s, v = RUN.at(t - TAU_LAUNCH)
        hud.append([f, round(v * 2.23694, 1), round(clamp(t - TAU_LAUNCH, 0, 99), 2)])
    labels["hud"] = hud
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

def render_settings(scn, h=1920, samples=32):
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_y = h
    scn.render.resolution_x = round(h * 9 / 16 / 2) * 2
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    ee = scn.eevee
    ee.taa_render_samples = samples
    for k, v in (("use_raytracing", True), ("use_shadows", True), ("use_fast_gi", True), ("volumetric_start", 0.5),
                 ("volumetric_end", 1500.0), ("volumetric_tile_size", "8"), ("volumetric_samples", 48),
                 ("use_volumetric_shadows", True), ("motion_blur_steps", 1), ("use_bokeh_jittered", False),
                 ("shadow_ray_count", 2), ("shadow_step_count", 8)):
        try:
            setattr(ee, k, v)
        except Exception as e:
            print("skip", k, e)
    scn.render.use_motion_blur = True
    scn.render.motion_blur_shutter = 0.5
    scn.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scn.view_settings.look = look
            break
        except TypeError:
            pass
    scn.view_settings.exposure = 0.25
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.image_settings.compression = 15


def build(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, F_END
    M = materials()
    world = sky_world()
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "AUTO"
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.clip_end = 6000
    camo = bpy.data.objects.new("Cam", cd)
    scn.collection.objects.link(camo)
    camo.rotation_mode = "QUATERNION"
    scn.camera = camo
    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 2.6
    sd.color = lin("#ffcfa8")
    sd.angle = rad(3)
    so = bpy.data.objects.new("Sun", sd)
    scn.collection.objects.link(so)
    so.rotation_mode = "QUATERNION"
    so.rotation_quaternion = SUN_DIR.to_track_quat("Z", "Y")
    fd = bpy.data.lights.new("Fill", "SUN")   # soft cool fill from the camera side
    fd.energy, fd.color, fd.angle = 0.6, lin("#a9bde0"), rad(25)
    try:
        fd.use_shadow = False
    except Exception:
        pass
    fo = bpy.data.objects.new("Fill", fd)
    scn.collection.objects.link(fo)
    fo.rotation_mode = "QUATERNION"
    fo.rotation_quaternion = Vector((0.45, 0.6, 0.65)).normalized().to_track_quat("Z", "Y")
    W = dict(M=M, cam=camo, sun=sd, world=world, fill=fd)
    W["R"] = build_ride(M)
    W["train"] = build_train(M)
    W["F"] = build_friction(M)
    W["K"] = build_macro(M)
    bake(W, os.path.join(os.path.dirname(os.path.abspath(out)), "labels.json"))
    render_settings(scn)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("SAVED", out)
    print("RUN: launch end s=%.1f, top v=%.1f m/s, brake entry v=%.1f, stop t=%.1f" % (
        RUN.at(3.5)[0], RUN.at(RUN.tau_s(S_TOP))[1], RUN.at(RUN.tau_s(BR0))[1], RUN.tau_s(BR1)))
    print("ROLL apex z=%.1f at tau=%.2f" % (track_frame(max(ROLL.s))[0].z, ROLL.tau_apex()))


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
