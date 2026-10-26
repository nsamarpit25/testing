
# ================================================================ ep 02: calculator -> gaming PC
import numpy as np
from mathutils import Matrix
V = Vector
T = dict(
    calc=ws(0, 'calculator'), congrats=ws(0, 'congratulations'),
    adds=ws(1, 'adds'), games=ws(1, 'games'),
    pack=ws(2, 'pack'), billions=ws(2, 'billions'), chip=ws(2, 'chip'), times=ws(2, 'times'), cpu=ws(2, 'cpu'),
    alone=ws(3, 'alone'), plug=ws(3, 'plug'), copper=ws(3, 'copper'), mobo=ws(3, 'motherboard'),
    waiting=ws(4, 'waiting'), slow=ws(4, 'slow'),
    desk=ws(5, 'desk'), ram=ws(5, 'ram'),
    off=ws(6, 'off'), wiped=ws(6, 'wiped'),
    drive=ws(7, 'drive'), remembers=ws(7, 'remembers'), ssd=ws(7, 'ssd'),
    hot=ws(8, 'hot'), egg=ws(8, 'egg'),
    bolt=ws(9, 'bolt'), fan=ws(9, 'fan'), cooler=ws(9, 'cooler'),
    pixels=ws(10, 'pixels'), slideshow=ws(10, 'slideshow'),
    card=ws(11, 'card'), cores=ws(11, 'cores'), gpu=ws(11, 'gpu'),
    hungry=ws(12, 'hungry'), flicker=ws(12, 'flicker'),
    box=ws(13, 'box'), wall=ws(13, 'wall'), psu=ws(13, 'power'),
    glass=ws(14, 'glass'), rainbow=ws(14, 'rainbow'), nothing=ws(14, 'nothing'), congrats2=ws(14, 'congratulations'),
    mine=ws(15, 'minecraft'),
)
END = LE[15]

# ---------------------------------------------------------------- materials
def emit_mat(name, color, strength=1.0):
    m, n, l, b = node_mat(name); pset(b, color=color, emit=color, estr=strength, rough=0.4); return m
M = dict(
    wall=mat('wall', (0.07, 0.2, 0.21), 0.85), base=mat('baseboard', (0.95, 0.94, 0.9), 0.4),
    floor=wood_mat('floor', (0.2, 0.1, 0.045), (0.36, 0.2, 0.09), scale=(1.5, 30, 30)),
    desk=wood_mat('desk', (0.32, 0.17, 0.07), (0.55, 0.32, 0.14), scale=(2, 40, 2)),
    white=mat('white', (0.92, 0.92, 0.9), 0.35), black=mat('black', (0.025, 0.025, 0.028), 0.35),
    plastic=mat('plastic', (0.06, 0.065, 0.07), 0.45, coat=0.3), grey=mat('grey', (0.35, 0.36, 0.38), 0.4),
    calc=mat('calc', (0.2, 0.21, 0.23), 0.5), key=mat('key', (0.85, 0.85, 0.82), 0.4), keyor=mat('keyor', (0.95, 0.45, 0.1), 0.4),
    lcd=mat('lcd', (0.55, 0.62, 0.45), 0.3), lcdtxt=mat('lcdtxt', (0.05, 0.07, 0.05), 0.5),
    pcb=mat('pcb', (0.02, 0.09, 0.05), 0.35, coat=0.5), copper=mat('copper', (0.95, 0.55, 0.3), 0.3, metal=1.0),
    gold=mat('gold', (1.0, 0.76, 0.33), 0.25, metal=1.0), steel=mat('steel', (0.75, 0.76, 0.78), 0.25, metal=1.0),
    alu=mat('alu', (0.82, 0.83, 0.86), 0.3, metal=1.0), chipm=mat('chipm', (0.04, 0.04, 0.045), 0.3),
    ramg=mat('ramg', (0.02, 0.12, 0.06), 0.35), heat=mat('heatspreader', (0.12, 0.12, 0.14), 0.3, metal=0.6),
    eggw=mat('eggw', (0.97, 0.97, 0.95), 0.25, sss=0.3, sssr=(0.5, 0.5, 0.5)), yolk=mat('yolk', (1.0, 0.62, 0.05), 0.15, coat=0.6),
    shell=mat('shell', (0.95, 0.88, 0.75), 0.6), glassm=mat('glassm', (0.9, 0.95, 1.0), 0.0, alpha=0.05, coat=0.4),
    rgb=emit_mat('rgb', (1.0, 0.2, 0.6), 3.0), rgb2=emit_mat('rgb2', (0.2, 0.6, 1.0), 3.0),
    shade=mat('shade', (0.92, 0.85, 0.7), 0.6), bulb=emit_mat('bulb', (1.0, 0.85, 0.6), 0.0),
    sky=mat('sky', (0.6, 0.8, 1.0), 0.5, emit=(0.6, 0.82, 1.0), estr=2.5), pot=mat('pot', (0.75, 0.42, 0.28), 0.6),
    plant=mat('plant', (0.18, 0.5, 0.2), 0.6), sock=mat('sockm', (0.93, 0.93, 0.9), 0.35), cable=mat('cable', (0.03, 0.03, 0.03), 0.6),
    mug=mat('mug', (0.85, 0.3, 0.2), 0.3, coat=0.6), paper=mat('paper', (0.95, 0.94, 0.9), 0.7),
    dot=dot_mat(), wisp=wisp_mat(),
)
pset(P(M['floor']), coat=0.0, rough=0.6)
def link(o):
    sc.collection.objects.link(o); return o
def tube3(name, pts, r, m):
    pts3 = [V(p) for p in pts]
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts3) - 1)
    for i, p in enumerate(pts3): sp.points[i].co = (p.x, p.y, p.z, 1)
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    o = link(bpy.data.objects.new(name, cu)); o.data.materials.append(m)
    return o, Path(pts3)
def grow(o, g):
    o.data.bevel_factor_end = max(g, 0.0005); o.hide_render = g < 0.002
def show(objs, s, base=None):
    for o in objs:
        o.hide_render = s < 0.01
        if base is not None: o.scale = tuple(b * max(s, 0.001) for b in base[o.name])

# ---------------------------------------------------------------- pixel textures (made here, no files)
def make_image(name, arr):
    h, w, _ = arr.shape
    im = bpy.data.images.new(name, w, h, alpha=False); im.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
    im.pack(); return im
def game_image():  # a side-on block world: sky, clouds, grass/dirt/stone columns, trees
    W_, H_, B = 768, 128, 8; cols, rows = W_ // B, H_ // B
    rng = np.random.default_rng(4); img = np.zeros((H_, W_, 4), np.float32); img[..., 3] = 1
    for y in range(H_): img[y, :, :3] = np.array((0.35, 0.6, 1.0)) * (0.75 + 0.25 * y / H_)
    def blk(cx, cy, col):
        y0 = H_ - (cy + 1) * B; c = np.array(col) * rng.uniform(0.9, 1.08)
        img[y0:y0 + B, cx * B:(cx + 1) * B, :3] = c
        img[y0:y0 + 1, cx * B:(cx + 1) * B, :3] = c * 1.15; img[y0 + B - 1:y0 + B, cx * B:(cx + 1) * B, :3] = c * 0.75
    for cx in range(cols):
        hgt = int(5 + 2 * math.sin(cx * 0.21) + 1.5 * math.sin(cx * 0.53 + 1))
        for cy in range(hgt):
            blk(cx, cy, (0.4, 0.4, 0.42) if cy < hgt - 3 else ((0.45, 0.28, 0.14) if cy < hgt - 1 else (0.3, 0.68, 0.2)))
        if cx % 11 == 5:
            for k in range(3): blk(cx, hgt + k, (0.4, 0.25, 0.1))
            for dx in (-1, 0, 1):
                for dy in (3, 4): blk((cx + dx) % cols, hgt + dy, (0.15, 0.5, 0.12))
            blk(cx, hgt + 5, (0.15, 0.5, 0.12))
    for cx0 in (6, 30, 55, 80):
        for dx in range(5):
            blk((cx0 + dx) % cols, rows - 3, (0.97, 0.97, 1.0))
            if 0 < dx < 4: blk((cx0 + dx) % cols, rows - 2, (0.97, 0.97, 1.0))
    return make_image('game', img)
GAME = game_image()
def screen_mat():
    m, n, l, b = node_mat('screen')
    tc = n.new('ShaderNodeTexCoord'); mp = n.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.3, 1, 1)
    tx = n.new('ShaderNodeTexImage'); tx.image = GAME; tx.interpolation = 'Closest'; tx.extension = 'REPEAT'
    l.new(tc.outputs['UV'], mp.inputs['Vector']); l.new(mp.outputs['Vector'], tx.inputs['Vector'])
    l.new(tx.outputs['Color'], b.inputs['Emission Color']); pset(b, color=(0.0, 0.0, 0.0), rough=0.15, coat=1.0, estr=0.0)
    m['map'] = mp.name; return m
M['screen'] = screen_mat()
def set_screen(on, offset):
    pset(P(M['screen']), estr=1.6 * on); M['screen'].node_tree.nodes[M['screen']['map']].inputs['Location'].default_value[0] = offset
def grid_mat(name, col, cells=40.0):  # flickering grid of "switches" (CPU top / GPU cores)
    m, n, l, b = node_mat(name)
    tc = n.new('ShaderNodeTexCoord'); ch = n.new('ShaderNodeTexChecker'); ch.inputs['Scale'].default_value = cells
    nz = n.new('ShaderNodeTexNoise'); nz.noise_dimensions = '4D'; nz.inputs['Scale'].default_value = cells; nz.inputs['Detail'].default_value = 0
    br = n.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = cells / 2; br.inputs['Mortar Size'].default_value = 0.12
    gt = n.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.52
    mu = n.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu2 = n.new('ShaderNodeMath'); mu2.operation = 'MULTIPLY'
    l.new(tc.outputs['Generated'], nz.inputs['Vector']); l.new(tc.outputs['Generated'], br.inputs['Vector'])   # boxes have no UVs
    l.new(nz.outputs['Fac'], gt.inputs[0]); l.new(gt.outputs[0], mu.inputs[0]); l.new(br.outputs['Fac'], mu.inputs[1])
    l.new(mu.outputs[0], mu2.inputs[0]); mu2.inputs[1].default_value = 0.0
    l.new(mu2.outputs[0], b.inputs['Emission Strength']); pset(b, color=(0.06, 0.06, 0.07), emit=col, rough=0.3, metal=0.4)
    m['w'] = nz.name; m['k'] = mu2.name; return m
M['cpugrid'] = grid_mat('cpugrid', (0.3, 0.9, 1.0), 36.0); M['gpugrid'] = grid_mat('gpugrid', (0.5, 1.0, 0.4), 70.0)
def set_grid(m, k, t):
    m.node_tree.nodes[m['w']].inputs['W'].default_value = t * 2.5; m.node_tree.nodes[m['k']].inputs[1].default_value = 6.0 * k

# ---------------------------------------------------------------- the room
DZ = 0.75
box('floor', -4, 4, -5, 1.2, -0.03, 0.0, M['floor'], bev=0)
box('wall', -4, 4, 0.62, 0.7, 0.0, 3.6, M['wall'], bev=0)
box('baseboard', -3, 3, 0.58, 0.62, 0.0, 0.08, M['base'], bev=0.004)
box('desktop', -0.85, 0.85, -0.42, 0.45, DZ - 0.035, DZ, M['desk'], bev=0.006)
for x in (-0.8, 0.8):
    for y in (-0.37, 0.4): box(f'leg{x}{y}', x - 0.025, x + 0.025, y - 0.025, y + 0.025, 0, DZ - 0.035, M['desk'], bev=0.004)
box('win_frame', -1.25, -0.55, 0.585, 0.6, 0.95, 1.75, M['white'], bev=0.006)
box('win_sky', -1.21, -0.59, 0.6, 0.605, 0.99, 1.71, M['sky'], bev=0)
box('win_bar', -0.91, -0.89, 0.58, 0.585, 0.99, 1.71, M['white'], bev=0)
box('shelf', 0.35, 1.0, 0.42, 0.6, 1.45, 1.47, M['desk'], bev=0.004)
for i, (x, h, c) in enumerate(((0.42, 0.2, (0.8, 0.25, 0.2)), (0.46, 0.18, (0.2, 0.4, 0.75)), (0.5, 0.22, (0.9, 0.75, 0.3)), (0.54, 0.17, (0.25, 0.55, 0.35)))):
    box(f'book{i}', x - 0.018, x + 0.018, 0.45, 0.58, 1.47, 1.47 + h, mat(f'bookm{i}', c, 0.6), bev=0.003)
smooth(prim('cylinder', 'pot', (0.82, 0.5, 1.53), M['pot'], radius=0.06, depth=0.12, vertices=32))
smooth(prim('ico_sphere', 'plant', (0.82, 0.5, 1.66), M['plant'], radius=0.1, subdivisions=3), 1)
mugo = smooth(prim('cylinder', 'mug', (0.62, -0.25, DZ + 0.05), M['mug'], radius=0.04, depth=0.1, vertices=40))
box('papers', -0.68, -0.48, -0.32, -0.18, DZ, DZ + 0.012, M['paper'], bev=0.002).rotation_euler.z = 0.2
# wall socket
box('socket', 0.66, 0.78, 0.6, 0.62, 0.95, 1.07, M['sock'], bev=0.006)
for dx in (-0.02, 0.02): box(f'pin{dx}', 0.72 + dx - 0.004, 0.72 + dx + 0.004, 0.595, 0.6, 1.0, 1.02, M['black'], bev=0)
# desk lamp (it flickers when the GPU gets hungry)
LX, LY = -0.62, 0.22
smooth(prim('cylinder', 'lampbase', (LX, LY, DZ + 0.012), M['black'], radius=0.07, depth=0.024, vertices=40))
tube3('lamparm', [(LX, LY, DZ + 0.02), (LX + 0.02, LY - 0.02, DZ + 0.36), (LX + 0.2, LY - 0.08, DZ + 0.45)], 0.008, M['black'])
shade = smooth(prim('cone', 'shade', (LX + 0.22, LY - 0.09, DZ + 0.42), M['shade'], radius1=0.08, radius2=0.03, depth=0.1, vertices=40))
shade.rotation_euler = (math.radians(-20), math.radians(35), 0)
bulb = smooth(prim('uv_sphere', 'bulb', (LX + 0.225, LY - 0.09, DZ + 0.395), M['bulb'], radius=0.022))
ll = bpy.data.lights.new('lamp', 'POINT'); ll.energy = 0; ll.color = (1.0, 0.8, 0.55); ll.shadow_soft_size = 0.05
LAMP = link(bpy.data.objects.new('lamp', ll)); LAMP.location = (LX + 0.225, LY - 0.09, DZ + 0.37)
# monitor
MX, MY, MZ, MW, MH = 0.0, 0.3, DZ + 0.4, 0.56, 0.32
box('mon_body', MX - MW / 2 - 0.012, MX + MW / 2 + 0.012, MY, MY + 0.025, MZ - MH / 2 - 0.012, MZ + MH / 2 + 0.02, M['plastic'], bev=0.006)
bpy.ops.mesh.primitive_plane_add(size=1, location=(MX, MY - 0.001, MZ)); scr = bpy.context.active_object; scr.name = 'screen'
scr.scale = (MW, MH, 1); scr.rotation_euler = (math.radians(90), 0, 0); scr.data.materials.append(M['screen'])
box('mon_neck', MX - 0.02, MX + 0.02, MY + 0.02, MY + 0.05, DZ, MZ - 0.1, M['plastic'], bev=0.004)
box('mon_foot', MX - 0.12, MX + 0.12, MY - 0.06, MY + 0.1, DZ, DZ + 0.012, M['plastic'], bev=0.004)
# keyboard (for scale)
box('kb', -0.2, 0.12, -0.38, -0.27, DZ, DZ + 0.018, M['plastic'], bev=0.004).rotation_euler.z = 0.04

# ---------------------------------------------------------------- the calculator
CC = V((-0.03, -0.01, DZ))   # same spot as the CPU: the calculator shrinks into the chip
calc_parts = [box('calc', CC.x - 0.045, CC.x + 0.045, CC.y - 0.07, CC.y + 0.07, DZ, DZ + 0.014, M['calc'], bev=0.006),
              box('lcdwin', CC.x - 0.035, CC.x + 0.035, CC.y + 0.03, CC.y + 0.06, DZ + 0.014, DZ + 0.016, M['lcd'], bev=0.002)]
for r in range(4):
    for c in range(4):
        kx, ky = CC.x - 0.03 + c * 0.02, CC.y - 0.055 + r * 0.02
        calc_parts.append(box(f'k{r}{c}', kx - 0.007, kx + 0.007, ky - 0.006, ky + 0.006, DZ + 0.014, DZ + 0.018, M['keyor'] if c == 3 else M['key'], bev=0.002))
bpy.ops.object.text_add(location=(CC.x + 0.031, CC.y + 0.039, DZ + 0.0165)); lcdt = bpy.context.active_object; lcdt.name = 'lcdtext'
lcdt.data.body = '2+2=4'; lcdt.data.align_x = 'RIGHT'; lcdt.data.size = 0.016; lcdt.data.materials.append(M['lcdtxt']); calc_parts.append(lcdt)
CALC_BASE = {o.name: o.location.copy() for o in calc_parts}

# ---------------------------------------------------------------- motherboard + parts
BX, BY, BZ = 0.0, -0.05, DZ + 0.004
board = box('board', BX - 0.15, BX + 0.15, BY - 0.12, BY + 0.12, DZ + 0.004, DZ + 0.01, M['pcb'], bev=0.002)
for i in range(6): box(f'stand{i}', 0, 0.006, 0, 0.006, DZ, DZ + 0.004, M['gold'], bev=0).location = (BX + (-0.14, 0.14)[i % 2], BY + (-0.11, 0, 0.11)[i // 2], DZ + 0.002)
BT = DZ + 0.01                                  # board top
CPU = V((BX - 0.03, BY + 0.04, BT))
socket = box('socket_cpu', CPU.x - 0.026, CPU.x + 0.026, CPU.y - 0.026, CPU.y + 0.026, BT, BT + 0.004, M['plastic'], bev=0.002)
RAMX = (BX + 0.06, BX + 0.075)
ramslots = [box(f'ramslot{i}', x - 0.003, x + 0.003, BY - 0.02, BY + 0.11, BT, BT + 0.008, M['black'], bev=0.001) for i, x in enumerate(RAMX)]
M2 = V((BX - 0.03, BY - 0.035, BT))
m2slot = box('m2slot', M2.x - 0.05, M2.x - 0.042, M2.y - 0.006, M2.y + 0.006, BT, BT + 0.004, M['black'], bev=0.001)
PCIE = V((BX, BY - 0.075, BT))
pcieslot = box('pcieslot', PCIE.x - 0.09, PCIE.x + 0.09, PCIE.y - 0.003, PCIE.y + 0.003, BT, BT + 0.008, M['black'], bev=0.001)
atx = box('atx24', BX + 0.13, BX + 0.145, BY - 0.03, BY + 0.03, BT, BT + 0.01, M['black'], bev=0.001)
# copper roads: Manhattan traces, plus the routes the data dots ride
rng = random.Random(11); traces = []
for i in range(46):
    x0, y0 = rng.uniform(-0.14, 0.14), rng.uniform(-0.11, 0.11); horiz = rng.random() < 0.5; L = rng.uniform(0.03, 0.12)
    x1, y1 = (min(0.145, x0 + L), y0) if horiz else (x0, min(0.115, y0 + L))
    traces.append(box(f'tr{i}', BX + min(x0, x1) - 0.0008, BX + max(x0, x1) + 0.0008, BY + min(y0, y1) - 0.0008, BY + max(y0, y1) + 0.0008, BT, BT + 0.0006, M['copper'], bev=0))
ROUTE_RAM = Path([V((CPU.x + 0.027, CPU.y, BT + 0.002)), V((RAMX[0] - 0.01, CPU.y, BT + 0.002)), V((RAMX[0] - 0.01, BY + 0.1, BT + 0.002))])
ROUTE_M2 = Path([V((CPU.x, CPU.y - 0.027, BT + 0.002)), V((CPU.x, M2.y + 0.01, BT + 0.002)), V((M2.x + 0.04, M2.y + 0.01, BT + 0.002))])
ROUTE_GPU = Path([V((CPU.x - 0.02, CPU.y - 0.027, BT + 0.002)), V((CPU.x - 0.02, PCIE.y + 0.012, BT + 0.002)), V((PCIE.x + 0.08, PCIE.y + 0.012, BT + 0.002))])
road_objs = [tube3(f'road{i}', [p for p in R.p], 0.0012, M['copper'])[0] for i, R in enumerate((ROUTE_RAM, ROUTE_M2, ROUTE_GPU))]
mobo = [board, socket, *ramslots, m2slot, pcieslot, atx, *traces, *road_objs] + [o for o in bpy.data.objects if o.name.startswith('stand')]
# CPU chip
cpu_sub = box('cpu_sub', CPU.x - 0.022, CPU.x + 0.022, CPU.y - 0.022, CPU.y + 0.022, BT + 0.004, BT + 0.007, M['pcb'], bev=0.001)
cpu_ihs = box('cpu_ihs', CPU.x - 0.017, CPU.x + 0.017, CPU.y - 0.017, CPU.y + 0.017, BT + 0.007, BT + 0.011, M['cpugrid'], bev=0.0015)
cpu_parts = [cpu_sub, cpu_ihs]
# RAM sticks
ram = []
for i, x in enumerate(RAMX):
    s_ = box(f'ram{i}', x - 0.0015, x + 0.0015, BY - 0.015, BY + 0.105, BT + 0.006, BT + 0.036, M['ramg'], bev=0.0008); ram.append(s_)
    for k in range(4): ram.append(box(f'ramchip{i}{k}', x - 0.0032, x - 0.0015, BY - 0.005 + k * 0.028, BY + 0.015 + k * 0.028, BT + 0.012, BT + 0.03, M['chipm'], bev=0.0005))
    ram.append(box(f'ramheat{i}', x - 0.0026, x + 0.0026, BY - 0.016, BY + 0.106, BT + 0.03, BT + 0.04, M['rgb2'], bev=0.0008))
RAM_BASE = {o.name: o.location.copy() for o in ram}
# SSD (M.2 stick) and the old slow hard drive it replaces
ssd = [box('ssd', M2.x - 0.042, M2.x + 0.04, M2.y - 0.011, M2.y + 0.011, BT + 0.003, BT + 0.0045, M['pcb'], bev=0.0005),
       box('ssdchip', M2.x - 0.025, M2.x + 0.01, M2.y - 0.008, M2.y + 0.008, BT + 0.0045, BT + 0.0065, M['chipm'], bev=0.0005),
       box('ssdlabel', M2.x + 0.012, M2.x + 0.035, M2.y - 0.008, M2.y + 0.008, BT + 0.0045, BT + 0.005, M['white'], bev=0)]
SSD_BASE = {o.name: o.location.copy() for o in ssd}
HD = V((-0.5, -0.05, DZ))
hdd = [box('hdd', HD.x - 0.07, HD.x + 0.07, HD.y - 0.05, HD.y + 0.05, DZ, DZ + 0.026, M['grey'], bev=0.003)]
platter = smooth(prim('cylinder', 'platter', (HD.x - 0.01, HD.y, DZ + 0.027), M['steel'], radius=0.038, depth=0.002, vertices=48)); hdd.append(platter)
harm = box('harm', 0, 0.045, -0.003, 0.003, 0, 0.002, M['alu'], bev=0); harm.location = (HD.x + 0.05, HD.y + 0.035, DZ + 0.029); hdd.append(harm)
hdd_cable, HDD_ROUTE = tube3('hddcable', [(HD.x + 0.07, HD.y, DZ + 0.006), (BX - 0.2, BY + 0.0, DZ + 0.006), (BX - 0.15, BY + 0.0, BT + 0.003), (CPU.x - 0.025, CPU.y - 0.01, BT + 0.003)], 0.0025, M['cable'])
HDD_BASE = {o.name: o.location.copy() for o in hdd}
# the egg
egg_shell = smooth(prim('uv_sphere', 'eggshell', (0, 0, 0), M['shell'], radius=0.02, segments=32, ring_count=16)); egg_shell.scale = (1, 1, 1.3)
egg_white = smooth(prim('cylinder', 'eggwhite', (CPU.x, CPU.y, BT + 0.0115), M['eggw'], radius=0.028, depth=0.002, vertices=48))
dw = egg_white.modifiers.new('wob', 'DISPLACE'); twob = bpy.data.textures.new('wob', 'CLOUDS'); twob.noise_scale = 0.03; dw.texture = twob; dw.strength = 0.004; dw.direction = 'X'
yolk = smooth(prim('uv_sphere', 'yolk', (CPU.x + 0.003, CPU.y - 0.002, BT + 0.0125), M['yolk'], radius=0.0095, segments=32, ring_count=16)); yolk.scale = (1, 1, 0.55)
# cooler: tower of aluminium fins, copper heat pipes, a fan with an RGB ring
CL = V((CPU.x, CPU.y, BT + 0.011))
cooler = [box('clbase', CL.x - 0.019, CL.x + 0.019, CL.y - 0.019, CL.y + 0.019, CL.z, CL.z + 0.008, M['copper'], bev=0.001)]
for k in range(4):
    cooler.append(tube3(f'hp{k}', [(CL.x - 0.012 + k * 0.008, CL.y, CL.z + 0.004), (CL.x - 0.012 + k * 0.008, CL.y, CL.z + 0.13)], 0.003, M['copper'])[0])
for k in range(26):
    z = CL.z + 0.03 + k * 0.0038
    cooler.append(box(f'fin{k}', CL.x - 0.03, CL.x + 0.03, CL.y - 0.025, CL.y + 0.025, z, z + 0.0008, M['alu'], bev=0))
fan_frame = box('fanframe', CL.x - 0.032, CL.x + 0.032, CL.y - 0.034, CL.y - 0.026, CL.z + 0.028, CL.z + 0.128, M['plastic'], bev=0.002); cooler.append(fan_frame)
FANC = V((CL.x, CL.y - 0.036, CL.z + 0.078))
def make_fan(name, c, r, axis='Y'):
    hub = smooth(prim('cylinder', name + '_hub', (0, 0, 0), M['plastic'], radius=r * 0.3, depth=0.006, vertices=32))
    blades = [hub]
    for k in range(7):
        bl = box(f'{name}_bl{k}', 0, r * 0.95, -r * 0.18, r * 0.18, -0.0012, 0.0012, M['plastic'], bev=0.001)
        bl.data.transform(Matrix.Translation((r * 0.475, 0, 0))); bl.parent = hub
        bl.location = (0, 0, 0); bl.rotation_euler = (0.35, 0, k * 2 * math.pi / 7); blades.append(bl)
    ring = smooth(prim('torus', name + '_ring', (0, 0, 0), M['rgb'], major_radius=r * 1.02, minor_radius=0.0018, major_segments=48, minor_segments=8))
    for o in (hub, ring):
        o.location = c; o.rotation_euler = (math.radians(90), 0, 0) if axis == 'Y' else (0, 0, 0)
    return hub, ring, blades
fan_hub, fan_ring, fan_blades = make_fan('cfan', FANC, 0.042)
cooler += [fan_hub, fan_ring] + fan_blades[1:]
COOL_BASE = {o.name: o.location.copy() for o in cooler if o.parent is None}
# GPU: a card standing in the PCIe slot, fans facing the camera
G = V((PCIE.x, PCIE.y - 0.004, BT + 0.008))
gpu = [box('gpu_pcb', G.x - 0.11, G.x + 0.11, G.y - 0.001, G.y + 0.001, G.z, G.z + 0.1, M['pcb'], bev=0.0005),
       box('gpu_shroud', G.x - 0.115, G.x + 0.115, G.y - 0.026, G.y - 0.001, G.z + 0.004, G.z + 0.105, M['plastic'], bev=0.004),
       box('gpu_back', G.x - 0.11, G.x + 0.11, G.y + 0.001, G.y + 0.004, G.z + 0.004, G.z + 0.1, M['gpugrid'], bev=0.001),
       box('gpu_strip', G.x - 0.1, G.x + 0.1, G.y - 0.024, G.y - 0.004, G.z + 0.105, G.z + 0.108, M['rgb'], bev=0.0005),
       box('gpu_io', G.x - 0.125, G.x - 0.115, G.y - 0.028, G.y + 0.004, G.z - 0.01, G.z + 0.11, M['steel'], bev=0.001)]
gfans = []
for k, dx in enumerate((-0.055, 0.055)):
    h, r_, bl = make_fan(f'gfan{k}', V((G.x + dx, G.y - 0.028, G.z + 0.055)), 0.042); gpu += [h, r_] + bl[1:]; gfans.append(h)
GPU_BASE = {o.name: o.location.copy() for o in gpu if o.parent is None}
# PSU on the desk, sleeved cables to the board and the GPU, a plug to the wall
PS = V((0.33, -0.04, DZ))
psu = [box('psu', PS.x - 0.075, PS.x + 0.075, PS.y - 0.07, PS.y + 0.07, DZ, DZ + 0.086, M['plastic'], bev=0.004),
       box('psu_label', PS.x - 0.074, PS.x - 0.02, PS.y - 0.0705, PS.y - 0.07, DZ + 0.02, DZ + 0.066, M['steel'], bev=0)]
ph, pr, pb = make_fan('pfan', V((PS.x + 0.0, PS.y, DZ + 0.087)), 0.05, axis='Z'); psu += [ph, pr] + pb[1:]
PSU_BASE = {o.name: o.location.copy() for o in psu if o.parent is None}
pc_board, PC_BOARD = tube3('pcab_board', [(PS.x - 0.075, PS.y + 0.0, DZ + 0.05), (BX + 0.2, BY + 0.0, DZ + 0.05), (BX + 0.16, BY, BT + 0.012), (BX + 0.145, BY, BT + 0.006)], 0.005, M['cable'])
pc_gpu, PC_GPU = tube3('pcab_gpu', [(PS.x - 0.075, PS.y - 0.04, DZ + 0.03), (BX + 0.17, BY - 0.12, DZ + 0.04), (G.x + 0.08, G.y - 0.012, G.z + 0.13), (G.x + 0.08, G.y - 0.012, G.z + 0.105)], 0.004, M['cable'])
pc_wall, PC_WALL = tube3('pcab_wall', [(PS.x + 0.075, PS.y + 0.03, DZ + 0.04), (0.6, 0.2, DZ + 0.004), (0.7, 0.55, DZ + 0.004), (0.72, 0.595, 1.01)], 0.004, M['cable'])
# glass case + frame, drops over the whole build
case = []
CX0, CX1, CY0, CY1, CZ1 = -0.19, 0.43, -0.24, 0.13, DZ + 0.29
for nm, a in (('front', (CX0, CX1, CY0 - 0.003, CY0, DZ, CZ1)), ('back', (CX0, CX1, CY1, CY1 + 0.003, DZ, CZ1)), ('left', (CX0 - 0.003, CX0, CY0, CY1, DZ, CZ1)),
              ('right', (CX1, CX1 + 0.003, CY0, CY1, DZ, CZ1)), ('top', (CX0, CX1, CY0, CY1, CZ1, CZ1 + 0.003))):
    case.append(box('glass_' + nm, *a, M['glassm'], bev=0))
for i, (x, y) in enumerate(((CX0, CY0), (CX1, CY0), (CX0, CY1), (CX1, CY1))):
    case.append(box(f'post{i}', x - 0.006, x + 0.006, y - 0.006, y + 0.006, DZ, CZ1 + 0.004, M['black'], bev=0.002))
CASE_BASE = {o.name: o.location.copy() for o in case}

# ---------------------------------------------------------------- dots, puffs, lights, camera
data = {k: Flow('dat_' + k, R, sp, r, 0.0) for k, R, sp, r in (('ram', ROUTE_RAM, 0.012, 0.0022), ('m2', ROUTE_M2, 0.012, 0.0022),
                                                           ('gpu', ROUTE_GPU, 0.012, 0.0022), ('hdd', HDD_ROUTE, 0.03, 0.003))}
for k, f_ in data.items(): f_.r_ = {'hdd': 0.003}.get(k, 0.0022)
sparks = Pool('spark', 40, M['dot']); wisps = Pool('wisp', 40, M['wisp'])
key = area('key', (-1.4, -1.8, 2.4), (55, 0, -35), 1.4, 70, (1.0, 0.93, 0.84))
fill = area('fill', (1.8, -1.6, 1.4), (70, 0, 45), 2.5, 30, (0.55, 0.7, 1.0))
top = area('top', (0.0, -0.1, 2.6), (0, 0, 0), 1.4, 14, (1.0, 0.97, 0.92))
for o in (key, fill, top): o.visible_camera = False; o.visible_glossy = False
sl = bpy.data.lights.new('sun', 'SUN'); sl.energy = 4.0; sl.color = (1.0, 0.68, 0.4); sl.angle = 0.06
SUN = link(bpy.data.objects.new('sun', sl)); SUN.rotation_euler = (math.radians(60), 0, math.radians(-62))
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.25, 0.35, 0.55, 1); bg.inputs['Strength'].default_value = 0.12
cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 35; cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24 * 1.5; cam_d.clip_start = 0.003
cam = link(bpy.data.objects.new('cam', cam_d)); sc.camera = cam
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 4.0

def F(tg, d, yaw, pitch, lens=35): return (V(tg), d, yaw, pitch, lens)
def lerpF(a, b, k): return (a[0].lerp(b[0], k),) + tuple(x + (y - x) * k for x, y in zip(a[1:], b[1:]))
CPUT = V((CPU.x, CPU.y, BT + 0.01)); BC = V((BX, BY, BT)); MON = V((MX, MY, MZ))
# shots: (start, framing at start, framing at end) -- hard cut at each start, slow move inside
SHOTS = [
    (0.0, F(CC + V((0, 0, 0.01)), 0.42, -20, 42, 45), F(CC + V((0, 0, 0.01)), 0.3, -10, 44, 45)),
    (LS[1], F(CC + V((0, 0.045, 0.016)), 0.2, 12, 40, 50), F(CC + V((0, 0.045, 0.016)), 0.16, 4, 44, 50)),
    (T['pack'] - 0.05, F(CPUT, 0.32, -12, 52, 50), F(CPUT, 0.13, -4, 46, 50)),
    (T['cpu'] - 0.25, F(CPUT, 0.12, 28, 28, 50), F(CPUT, 0.11, 40, 26, 50)),
    (LS[3], F(BC, 0.6, 0, 70), F(BC, 0.46, 8, 62)),
    (T['mobo'] - 0.3, F(BC + V((0, 0.02, 0)), 0.42, 38, 12, 35), F(BC + V((0, 0.02, 0)), 0.38, 25, 14, 35)),
    (LS[4], F(V((-0.22, -0.04, DZ + 0.02)), 0.95, -28, 38), F(V((-0.2, -0.04, DZ + 0.02)), 0.85, -18, 36)),
    (LS[5], F(V((RAMX[0], BY + 0.045, BT + 0.02)), 0.3, 24, 34, 45), F(V((RAMX[0], BY + 0.045, BT + 0.02)), 0.25, 14, 32, 45)),
    (LS[6], F(BC + V((0.02, 0.02, 0)), 0.5, 12, 42), F(BC + V((0.02, 0.02, 0)), 0.46, 4, 44)),
    (LS[7], F(M2 + V((0, 0, 0.004)), 0.2, -22, 40, 50), F(M2 + V((0, 0, 0.004)), 0.16, -12, 42, 50)),
    (LS[8], F(CPUT, 0.2, -10, 42, 50), F(CPUT, 0.14, -4, 40, 50)),
    (LS[9], F(CPUT + V((0, 0, 0.06)), 0.5, 32, 20), F(CPUT + V((0, 0, 0.06)), 0.44, 22, 18)),
    (LS[10], F(MON, 0.7, 0, 4, 40), F(MON, 0.6, 0, 3, 40)),
    (LS[11], F(G + V((0, 0, 0.06)), 0.62, -30, 24), F(G + V((0, 0, 0.06)), 0.52, -18, 20)),
    (T['gpu'] - 0.2, F(MON + V((0, -0.2, -0.12)), 1.0, -8, 14, 35), F(MON + V((0, -0.2, -0.12)), 0.92, -2, 14, 35)),
    (LS[12], F(V((-0.1, 0.1, DZ + 0.25)), 1.7, -22, 14), F(V((-0.1, 0.1, DZ + 0.25)), 1.55, -14, 13)),
    (LS[13], F(PS + V((0, 0, 0.05)), 0.6, 26, 30), F(PS + V((0, 0, 0.05)), 0.5, 18, 28)),
    (LS[14], F(V((0.12, -0.05, DZ + 0.13)), 1.15, -22, 26), F(V((0.12, -0.05, DZ + 0.13)), 0.95, -8, 22)),
    (T['congrats2'] - 0.15, F(V((0.12, -0.05, DZ + 0.12)), 0.8, 18, 16, 35), F(V((0.12, -0.05, DZ + 0.12)), 0.75, 30, 15, 35)),
    (LS[15], F(MON + V((0, 0, 0.04)), 0.6, 0, 4, 45), F(MON + V((0, 0, 0.04)), 0.52, 0, 4, 45)),
]
IMPACTS = [(T['plug'] + 0.2, 0.004), (T['bolt'] + 0.25, 0.006), (T['card'] + 0.25, 0.005), (T['box'] + 0.3, 0.006), (T['glass'] + 0.35, 0.01)]
def cam_state(t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    t0 = SHOTS[i][0]; t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else END + 0.8
    fr = lerpF(SHOTS[i][1], SHOTS[i][2], ss(t, t0, t1) * 0.6 + lin(t, t0, t1) * 0.4)
    tg, d, yaw, pitch, lens = fr
    ya, pa = math.radians(yaw), math.radians(pitch)
    p = tg + d * V((math.sin(ya) * math.cos(pa), -math.cos(ya) * math.cos(pa), math.sin(pa)))
    sh = V((0, 0, 0))
    for ti, a in IMPACTS:
        if ti <= t < ti + 0.6:
            e = a * math.exp(-(t - ti) * 9) * d; sh += V((e * math.sin(t * 71), 0, e * math.sin(t * 53 + 1)))
    return p + sh, tg + sh * 0.5, lens, d
def apply_cam(t):
    p, g, l, d = cam_state(t)
    cam.location = p; cam.rotation_euler = (g - p).to_track_quat('-Z', 'Y').to_euler(); cam_d.lens = l
    cam_d.dof.focus_distance = (g - p).length; cam_d.dof.aperture_fstop = 2.8 if d < 0.35 else 5.6

def place(objs, base, off=V((0, 0, 0)), s=1.0):
    for o in objs:
        if o.parent is not None: continue
        o.location = base[o.name] + off; o.hide_render = s < 0.01
        o.scale = (max(s, 0.001),) * 3
        for ch in o.children: ch.hide_render = s < 0.01
def rgb_hue(t, k=0.0):
    h = (t * 0.25 + k) % 1.0; i = int(h * 6); f = h * 6 - i
    q, u = 1 - f, f; return [(1, u, 0), (q, 1, 0), (0, 1, u), (0, q, 1), (u, 0, 1), (1, 0, q)][i % 6]

# ---------------------------------------------------------------- per-frame state
def state(t):
    f_idx = int(round(t * FPS)); apply_cam(t)
    # power: everything goes dark on "off", lights flicker when the GPU gets hungry
    off = win(t, T['off'] - 0.05, T['wiped'] + 0.9, 0.08, 0.25)
    flick = 0.0
    if T['flicker'] - 0.3 < t < LS[13]:
        rs = random.Random(int(t * 14)); flick = 0.75 if rs.random() < 0.45 else 0.0
    lamp_on = ss(t, LS[12] - 0.6, LS[12] - 0.3)
    LAMP.data.energy = 6 * lamp_on * (1 - flick); pset(P(M['bulb']), estr=6 * lamp_on * (1 - flick))
    dim = 1 - 0.55 * flick
    key.data.energy = 70 * dim; top.data.energy = 14 * dim; SUN.data.energy = 4.0 * (1 - 0.4 * flick)
    # calculator morphs into the chip
    cs = 1 - ss(t, T['pack'] + 0.1, T['chip'] + 0.1)
    place(calc_parts, CALC_BASE, V((0, 0, 0)), cs)
    for o in calc_parts: o.location = CC + (CALC_BASE[o.name] - CC) * max(cs, 0.001)
    lcdt.data.body = '2+2=4' if t < LS[1] + 1.2 else ('2+3=5' if t < T['games'] else '...')
    chip_s = ss(t, T['pack'] + 0.4, T['chip'] + 0.35)
    for o in cpu_parts: o.hide_render = chip_s < 0.01; o.scale = (max(chip_s, 0.001),) * 3
    # the chip sits on the desk until the board slides in under it
    b_in = ss(t, T['plug'] - 0.1, T['plug'] + 0.45)
    board_drop = (1 - b_in) * 0.0
    for o in mobo:
        o.hide_render = b_in < 0.01
    board.scale = (max(b_in, 0.001), max(b_in, 0.001), 1)
    for o in mobo:
        if o is board: continue
        o.scale = (max(b_in, 0.001),) * 3 if o.name.startswith(('tr', 'stand')) else (1, 1, 1)
        o.hide_render = b_in < 0.9 and not o.name.startswith('tr')
    lift = (1 - b_in) * -(BT + 0.004 - DZ)            # chip rests on the desk, then rides up onto the socket
    for o in cpu_parts: o.location.z = (BT + 0.0055 if o is cpu_sub else BT + 0.009) + lift
    glow_roads = win(t, T['copper'] - 0.1, T['mobo'] + 1.0, 0.2, 0.4)
    pset(P(M['copper']), emit=(1.0, 0.5, 0.15), estr=2.0 * glow_roads)
    set_grid(M['cpugrid'], win(t, T['billions'] - 0.1, T['cpu'] + 1.2, 0.2, 0.5) + 0.25 * ss(t, T['mobo'], T['mobo'] + 1) * (1 - off), t)
    # RAM drops into its slots
    rd = ss(t, T['desk'] - 0.2, T['desk'] + 0.35)
    for o in ram: o.location = RAM_BASE[o.name] + V((0, 0, 0.12 * (1 - rd))); o.hide_render = rd < 0.01
    pset(P(M['rgb2']), estr=3.0 * (1 - off) * (rd > 0.5))
    # slow HDD, replaced by the SSD
    hd_s = 1 - ss(t, T['drive'] - 0.2, T['drive'] + 0.4); hd_in = ss(t, LS[4] - 0.3, LS[4] + 0.2)
    place(hdd, HDD_BASE, V((0, 0, 0)), hd_s * hd_in)
    platter.rotation_euler.z = t * 4
    grow(hdd_cable, hd_in * hd_s)
    sd = ss(t, T['drive'] + 0.1, T['drive'] + 0.6)
    place(ssd, SSD_BASE, V((-0.08 * (1 - sd), 0, 0.0)), 1.0 if sd > 0.01 else 0.0)
    # the egg: falls, cracks, fries; flung off when the cooler lands
    egg_t = T['egg'] - 0.35; land = T['bolt'] + 0.25
    eg = clamp((t - egg_t) / 0.3)
    egg_shell.hide_render = not (egg_t < t < egg_t + 0.36)
    egg_shell.location = (CPU.x, CPU.y, BT + 0.035 + 0.25 * (1 - eg * eg))
    fry = ss(t, egg_t + 0.3, egg_t + 0.5); fly = clamp((t - land) / 0.5)
    for o, base in ((egg_white, V((CPU.x, CPU.y, BT + 0.0115))), (yolk, V((CPU.x + 0.003, CPU.y - 0.002, BT + 0.0125)))):
        o.hide_render = fry < 0.01 or fly >= 1
        o.location = base + V((0.25 * fly, -0.2 * fly, 0.3 * fly - 0.6 * fly * fly)); o.rotation_euler = (fly * 7, fly * 4, 0)
    egg_white.scale = (max(fry, 0.001), max(fry, 0.001), 1)
    # cooler drops on
    cd = clamp((t - (T['bolt'] - 0.05)) / 0.3)
    place(cooler, COOL_BASE, V((0, 0, 0.25 * (1 - cd * cd))), 1.0 if t > T['bolt'] - 0.05 else 0.0)
    fan_on = (t > T['fan']) * (1 - off)
    spin = 40 * max(0.0, t - T['fan'] - 0.3) + 20 * min(0.3, max(0.0, t - T['fan'])) ** 2
    fan_hub.rotation_euler = (math.radians(90), spin, 0)
    # GPU slots in
    gd = clamp((t - (T['card'] - 0.05)) / 0.35)
    place(gpu, GPU_BASE, V((0, 0, 0.3 * (1 - gd * gd))), 1.0 if t > T['card'] - 0.05 else 0.0)
    gspin = max(0.0, t - T['gpu']) * 30
    for h in gfans: h.rotation_euler = (math.radians(90), gspin, 0)
    set_grid(M['gpugrid'], win(t, T['cores'] - 0.15, T['gpu'] + 0.8, 0.2, 0.4), t)
    # PSU + cables
    pd = clamp((t - (T['box'] - 0.05)) / 0.3)
    place(psu, PSU_BASE, V((0, 0, 0.25 * (1 - pd * pd))), 1.0 if t > T['box'] - 0.05 else 0.0)
    ph.rotation_euler.z = max(0.0, t - T['wall']) * 25
    grow(pc_board, ss(t, T['box'] + 0.3, T['wall'])); grow(pc_gpu, ss(t, T['box'] + 0.5, T['wall'] + 0.2)); grow(pc_wall, ss(t, T['wall'], T['psu'] + 0.2))
    # glass case drops; RGB everywhere
    gc = clamp((t - (T['glass'] - 0.05)) / 0.4)
    place(case, CASE_BASE, V((0, 0, 0.5 * (1 - gc * gc))), 1.0 if t > T['glass'] - 0.05 else 0.0)
    rg = ss(t, T['rainbow'] - 0.1, T['rainbow'] + 0.3)
    c1 = mix((1.0, 0.2, 0.6), rgb_hue(t), rg); c2 = mix((0.2, 0.6, 1.0), rgb_hue(t, 0.33), rg)
    pset(P(M['rgb']), color=c1, emit=c1, estr=3.0 * (1 - off) * (1 - 0.6 * flick)); pset(P(M['rgb2']), color=c2, emit=c2)
    # the monitor: off, then a slideshow, then smooth after the GPU, Minecraft-ish at the end
    on = ss(t, LS[10] - 0.2, LS[10]) * (1 - 0.7 * flick)
    if t < T['card']: off_x = math.floor(t / 0.45) * 0.045
    else: off_x = (T['card'] / 0.45) * 0.045 + (t - T['card']) * 0.1
    set_screen(on, off_x)
    # data dots
    ph_ = t * 0.07
    pw = 1 - off
    data['hdd'].update(t * 0.012, hd_in * hd_s, (hd_in * hd_s) * (t < T['desk'] + 0.6) * pw, lambda f: (0.2, 0.8, 1.0), 1.5)
    data['ram'].update(ph_ * 2, rd, rd * pw * (t > T['desk'] + 0.2), lambda f: (0.2, 0.8, 1.0), 1.5)
    data['m2'].update(ph_ * 1.5, sd, sd * (t > T['drive'] + 0.4), lambda f: (0.3, 1.0, 0.6), 1.5)
    data['gpu'].update(ph_ * 2.5, gd, gd * (t > T['card'] + 0.3), lambda f: (0.6, 1.0, 0.3), 1.5)
    # sparks + smoke
    sparks.reset(); wisps.reset()
    if T['hot'] - 0.2 < t < T['bolt'] + 0.2:          # heat shimmer + sizzle off the CPU
        for j in range(14):
            t0 = T['hot'] - 0.2 + j * 0.2; u = (t - t0) / 1.2
            if 0 <= u <= 1:
                rs = random.Random(j); wisps.put(CPUT + V((rs.uniform(-0.015, 0.015), rs.uniform(-0.015, 0.015), 0.01 + 0.08 * u)), 0.003 + 0.006 * u,
                                                  (0.95, 0.95, 0.95), 0.3 * math.sin(u * math.pi))
    pset(P(M['cpugrid']), emit=mix((0.3, 0.9, 1.0), (1.0, 0.25, 0.05), ss(t, T['hot'] - 0.2, T['hot'] + 0.3) * (1 - ss(t, T['fan'], T['cooler']))))
    if T['hot'] - 0.2 < t < T['bolt']:
        set_grid(M['cpugrid'], 0.6, t)
    if LS[6] - 0.1 < t < T['wiped'] + 1.0:             # RAM contents fly off when the power dies
        for j in range(16):
            u = (t - T['off'] - j * 0.04) / 0.8
            if 0 <= u <= 1:
                rs = random.Random(70 + j); x = rs.choice(RAMX); y = BY + rs.uniform(-0.01, 0.1)
                sparks.put(V((x, y, BT + 0.04 + 0.12 * u)), 0.003 * (1 - u), (0.2, 0.8, 1.0))
    if T['cores'] - 0.1 < t < T['gpu'] + 1.0:        # thousands of cores light up
        for j in range(20):
            u = ((t - T['cores']) * 2 + j / 20) % 1
            sparks.put(V((G.x - 0.1 + 0.2 * ((j * 0.37) % 1), G.y + 0.006, G.z + 0.01 + 0.09 * u)), 0.0025, (0.6, 1.0, 0.3))
    if T['glass'] + 0.3 < t < T['glass'] + 1.0:       # little dust puff when the case lands
        for j in range(8):
            u = (t - T['glass'] - 0.3) / 0.7; a = j * 0.8
            wisps.put(V((0.12 + 0.33 * math.cos(a), -0.05 + 0.2 * math.sin(a), DZ + 0.01)), 0.01 + 0.03 * u, (0.95, 0.9, 0.85), 0.4 * (1 - u))

# ---------------------------------------------------------------- anchors for the overlay
ANCH = dict(cpu=CPUT + V((0, 0, 0.006)), mobo=V((BX + 0.12, BY - 0.1, BT)), ram=V((RAMX[1], BY + 0.11, BT + 0.04)), ssd=M2 + V((0, 0, 0.006)),
            cooler=CPUT + V((0, 0, 0.13)), gpu=G + V((0, -0.02, 0.11)), psu=PS + V((0, 0, 0.09)), mon=MON + V((0, 0, 0.12)), calc=CC + V((0, 0.045, 0.02)),
            hdd=HD + V((0, 0, 0.03)), egg=CPUT + V((0, 0, 0.02)))
def anchors():
    out = []; W, H = sc.render.resolution_x, sc.render.resolution_y
    for f in range(NF):
        t = f / FPS; state(t); bpy.context.view_layer.update()
        row = {'t': round(t, 3), 'on': 0}
        for k, v in ANCH.items():
            p = world_to_camera_view(sc, cam, v)
            row[k] = (round(p.x * W, 1), round((1 - p.y) * H, 1), int(0.03 < p.x < 0.97 and 0.03 < p.y < 0.97 and p.z > 0))
        out.append(row)
    json.dump(dict(fps=FPS, w=W, h=H, T=T, swap=-1, frames=out, cuts=[s[0] for s in SHOTS]), open(os.path.join(OUT, 'anchors.json'), 'w'))
def render_frame(f, path):
    t = f / FPS; sc.frame_set(f); state(t); sc.cycles.seed = f
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)
if '--anchors' in argv: anchors()
if '--stills' in argv:
    for s in arg('--stills').split(','):
        render_frame(int(round(float(s) * FPS)), os.path.join(OUT, f'still_{float(s):06.2f}.png'))
if '--frames' in argv:
    a, b = arg('--frames').split(':'); a = int(a); b = min(int(b), NF)
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    for f in range(a, b):
        p = os.path.join(OUT, 'frames', f'f_{f:05d}.png')
        if not os.path.exists(p): render_frame(f, p)
print('NF', NF, 'DONE')
