# ---------- the canary: a real-looking bird. Metaball body (one smooth skin), layered wing and tail feathers, a horn beak ----------
def feather_mat(name, lo, hi, tip, fluff=True):
    m = mat(name, hi, 0.6); v = OC(m)
    g = NZ(m, v, 30.0, 4)
    sc_ = VO(m, OC(m, (0.5, 1.0, 1.0)), 230.0, 'SMOOTH_F1')   # overlapping feather tips
    col = RAMP(m, g, [(0.3, lo), (0.7, hi)])
    col = MIXB(m, MR(m, sc_, 0.1, 0.7, 0.0, 0.18), col, hx(tip or lo))   # darker at each feather's edge
    SET(m, 'Base Color', grime(m, col, 0.015, 0.8))
    if fluff: SET(m, 'Sheen Weight', 0.3); SET(m, 'Sheen Roughness', 0.4); SET(m, 'Sheen Tint', hx('#FFE9A0')); SET(m, 'Subsurface Weight', 0.15); SET(m, 'Subsurface Scale', 0.004)
    fine = WV(m, OC(m, (1.0, 1.0, 1.0)), 900.0, 2.0, 'Y')    # barbs
    SET(m, 'Normal', BMP(m, NZ(m, v, 700.0, 3), 0.25, 0.0002, BMP(m, fine, 0.12, 0.00005, BMP(m, sc_, 0.35, 0.0012))))
    SET(m, 'Roughness', MR(m, g, 0.3, 0.7, 0.45, 0.65)); return m
M['canary'] = feather_mat('canary', '#F2A900', '#FFD21A', '#D98E00')
M['canary_w'] = feather_mat('canary_w', '#D29A00', '#F7C51A', '#7A6410')
M['canary_t'] = feather_mat('canary_t', '#9A7A10', '#E0B21C', '#4A4214', fluff=False)
M['beak'] = mat('beak', '#E7C39A', 0.35); SET(M['beak'], 'Subsurface Weight', 0.5); SET(M['beak'], 'Subsurface Scale', 0.003)
M['leg'] = mat('leg', '#D9A28A', 0.45); SET(M['leg'], 'Subsurface Weight', 0.4); SET(M['leg'], 'Subsurface Scale', 0.002)
SET(M['leg'], 'Normal', BMP(M['leg'], VO(M['leg'], OC(M['leg']), 900.0), 0.4, 0.0002))

def meta_mesh(name, elems, m, res=0.0035, thresh=0.25):
    md = bpy.data.metaballs.new(name + '_md'); md.resolution = md.render_resolution = res; md.threshold = thresh
    for kind, co, r, sz, rot in elems:
        e = md.elements.new(type=kind); e.co = co; e.radius = r
        if sz: e.size_x, e.size_y, e.size_z = sz
        if rot: e.rotation = Euler(rot).to_quaternion()
    mo = bpy.data.objects.new(name + '_mo', md); col.objects.link(mo); bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(mo.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(mo); bpy.data.metaballs.remove(md)
    me.materials.clear(); me.materials.append(m); me.shade_smooth(); return me
def feather(mb, root_, tip, w, th, m, flat=False):  # a long leaf-shaped feather from root to tip, thin across the flank (or flat for the tail)
    a, b = Vector(root_), Vector(tip); d = b - a; L_ = d.length
    R = d.to_track_quat('X', 'Z').to_matrix().to_4x4()
    mx = Matrix.Translation((a + b) / 2) @ R @ Matrix.Diagonal((L_ / 2, w, th, 1.0) if flat else (L_ / 2, th, w, 1.0))
    res = bmesh.ops.create_uvsphere(mb.bm, u_segments=16, v_segments=8, radius=1.0, matrix=mx); return mb._fin(res['verts'], m)
BIRD_ME = None
def bird_mesh():
    E = 'ELLIPSOID'
    body = [('BALL', (0.03, 0, 0.062), 0.050, None, None),                       # breast
            (E, (-0.005, 0, 0.064), 0.058, (1.25, 0.82, 0.8), (0, rad(-28), 0)),   # body, tilted head-up
            (E, (-0.05, 0, 0.042), 0.04, (1.4, 0.7, 0.55), (0, rad(-30), 0)),      # rump
            ('BALL', (0.045, 0, 0.095), 0.034, None, None),                       # neck
            (E, (0.06, 0, 0.113), 0.034, (1.12, 0.95, 0.98), None),               # head
            (E, (0.078, 0, 0.107), 0.016, (1.2, 1.0, 0.9), None)]                 # cheek / face
    me_b = meta_mesh('canary_body', body, M['canary'])
    mb = MB()
    for sy in (-1, 1):  # folded wing: coverts then primaries, lying along the flank
        for k in range(5):
            r0 = Vector((0.03 - 0.008 * k, sy * (0.036 - 0.001 * k), 0.083 - 0.004 * k)); t0 = Vector((-0.06 - 0.008 * k, sy * (0.029 - 0.002 * k), 0.034 + 0.002 * k))
            feather(mb, r0, t0, 0.017 - 0.0015 * k, 0.0026, M['canary_w'] if k < 3 else M['canary_t'])
        feather(mb, (0.035, sy * 0.037, 0.08), (-0.015, sy * 0.039, 0.058), 0.02, 0.003, M['canary_w'])
    for k in range(5):  # tail fan
        sy = (k - 2) * 0.0045
        feather(mb, (-0.055, sy, 0.04), (-0.125, sy * 2.4, 0.012), 0.0085, 0.0018, M['canary_t'], flat=True)
    mb.cyl((0.094, 0, 0.112), 0.0085, 0.017, M['beak'], rot=(0, PI / 2 + rad(6), 0), seg=16, r2=0.0012)
    for sy in (-1, 1):
        mb.sph((0.071, sy * 0.0215, 0.119), 0.0046, M['eye'], seg=14, ring=8)
        mb.cyl((0.004, sy * 0.012, 0.016), 0.0026, 0.032, M['leg'], rot=(rad(-sy * 6), rad(10), 0), seg=8)
        for a in (-0.5, 0.0, 0.5):  # three toes forward, one back, curled on the perch
            mb.cyl((0.006 + 0.008 * math.cos(a), sy * 0.012 + 0.008 * math.sin(a), 0.001), 0.0017, 0.017, M['leg'], rot=(0, PI / 2, a), seg=6)
        mb.cyl((-0.004, sy * 0.012, 0.001), 0.0017, 0.012, M['leg'], rot=(0, PI / 2, 0), seg=6)
    me_d = bpy.data.meshes.new('canary_detail'); mb.bm.to_mesh(me_d); mb.bm.free()
    for m_ in mb.mats: me_d.materials.append(m_)
    me_d.shade_smooth()
    jb = MB(); jb.cyl((0.008, 0, -0.002), 0.0062, 0.015, M['beak'], rot=(0, PI / 2 + rad(14), 0), seg=12, r2=0.001)
    me_j = bpy.data.meshes.new('canary_jaw'); jb.bm.to_mesh(me_j); jb.bm.free(); me_j.materials.append(M['beak']); me_j.shade_smooth()
    return me_b, me_d, me_j
def note(name, parent): return None
def bird(name, parent, loc, s, yaw):
    global BIRD_ME
    if BIRD_ME is None: BIRD_ME = bird_mesh()
    root = empty(name, parent, loc, (0, 0, yaw)); root.scale = (s, s, s); body = empty(name + '_b', root)
    for k, me in enumerate(BIRD_ME[:2]):
        o = bpy.data.objects.new(f'{name}_m{k}', me); col.objects.link(o); o.parent = body
    jaw = empty(name + '_jaw', body, (0.084, 0, 0.106))
    o = bpy.data.objects.new(name + '_jm', BIRD_ME[2]); col.objects.link(o); o.parent = jaw
    body['jaw'] = jaw.name
    return root, body, []
def sing(body, notes, ivals, droops):
    on = lambda t: any(a <= t < b for a, b in ivals)
    def dr(t):
        v = 0.0
        for a, b in droops:
            if a <= t: v = max(v, sm((t - a) / 0.45) * (1 - sm((t - b) / 0.35)))
        return v
    def song(t):  # phrases of quick trills: the beak opens and closes, the throat shivers
        if not on(t): return 0.0
        ph = 0.5 + 0.5 * math.sin(2 * PI * 0.55 * t)
        return clamp(ph * 1.3 - 0.25) * (0.55 + 0.45 * math.sin(2 * PI * 7.5 * t)) * (0.7 + 0.3 * math.sin(2 * PI * 2.1 * t + 1))
    look = lambda t: rad(10) * math.sin(0.9 * t) * math.sin(0.37 * t + 1.3) + rad(6) * math.sin(2.3 * t) * (1 - dr(t))
    fn(body, 'rotation_euler', 0.0, END, lambda t: (rad(1.2) * math.sin(2 * PI * 13 * t) * song(t), rad(-6) * song(t) + rad(42) * dr(t), look(t) * (1 - dr(t))))
    fn(body, 'scale', 0.0, END, lambda t: (1.0, 1.0 + 0.06 * dr(t), 1.0 + 0.03 * dr(t)))  # fluffed up when sick
    jaw = bpy.data.objects[body['jaw']]
    fn(jaw, 'rotation_euler', 0.0, END, lambda t: (0.0, rad(24) * song(t), 0.0))
