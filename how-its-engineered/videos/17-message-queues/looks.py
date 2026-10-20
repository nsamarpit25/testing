# Five look variants (Argon's suggestions) for 17 Message Queues, same key frame:
# users -> web server -> message queue -> workers. Blocks turn by `yaw` so you see their sides while the layout stays vertical.
# usage: blender -b -P videos/17-message-queues/looks.py -- <out.png> <tactile|frosted|clay|darklab|gloss> [--res 720]
import bpy, bmesh, math, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, VAR = argv[0], argv[1]
RES = int(argv[argv.index('--res') + 1]) if '--res' in argv else 720
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection
FONT = bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf')

def hx(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

# m(color, rough, metal, emit, alpha, trans, coat, sss)
def m_(c, r=0.6, mt=0.0, e=0.0, a=1.0, tr=0.0, ct=0.0, ss=0.0, bump=0.0): return dict(c=c, r=r, mt=mt, e=e, a=a, tr=tr, ct=ct, ss=ss, bump=bump)
LOOKS = {
    'tactile': dict(bg='#D8D8D4', floor=m_('#D8D8D4', 0.8), dots='#9A9A96', plinth=m_('#C9C9C5', 0.35, 0.9),
                    user=m_('#5A5A58', 0.7), screen=m_('#FFFFFF', 0.4, e=1.2), server=m_('#EAEAE6', 0.7), worker=m_('#8C8C88', 0.7),
                    ring=m_('#222222', 0.35, 0.9), tube=m_('#FFFFFF', 0.05, a=0.18), msg=m_('#FF4F00', 0.5, e=1.5),
                    label=m_('#222222', 0.6), ltext=m_('#EAEAE6', 0.6), line=m_('#222222', 0.5), status=m_('#FF4F00', 0.5, e=2.0),
                    lights=[('area', (-4, -3, 7), (35, 0, -40), 1.5, 1400, '#FFFFFF'), ('area', (4, 5, 4), (-55, 0, 145), 4, 300, '#DCEBFF')],
                    world=('#D8D8D4', 1.0), look='AgX - Medium High Contrast', exp=0.35, bloom=0.0,
                    cam=dict(ortho=True, el=35.26, yaw=30, scale=8.6)),
    'frosted': dict(bg='#0B0C10', floor=m_('#0B0C10', 0.6), dots=None, plinth=m_('#12141B', 0.3),
                    user=m_('#1F2833', 0.5), screen=m_('#66FCF1', 0.4, e=4.0), server=m_('#3B82F6', 0.35, tr=1.0), worker=m_('#8B5CF6', 0.35, tr=1.0),
                    core_server=m_('#3B82F6', 0.5, e=14.0), core_worker=m_('#8B5CF6', 0.5, e=14.0),
                    ring=m_('#C9D2E0', 0.25, 1.0), tube=m_('#FFFFFF', 0.25, a=0.2), msg=m_('#F59E0B', 0.4, e=5.0),
                    label=m_('#0B0C10', 0.5), ltext=m_('#E6F0FF', 0.5, e=1.5), line=m_('#66FCF1', 0.5, e=3.0), status=m_('#66FCF1', 0.5, e=4.0),
                    lights=[('area', (0, 6, 4), (-60, 0, 180), 6, 1200, '#7C5CFF'), ('area', (-3, -5, 6), (40, 0, -30), 5, 450, '#9DB8FF'),
                            ('area', (4, -2, 3), (60, 0, 60), 3, 300, '#66FCF1')],
                    world=('#0B0C10', 1.0), look='AgX - Medium High Contrast', exp=0.3, bloom=0.8,
                    cam=dict(ortho=False, lens=85, el=40, yaw=15, dist=19)),
    'clay':    dict(bg='#F4EFE6', floor=m_('#F4EFE6', 0.85), dots=None, plinth=m_('#EAE1D2', 0.8, ss=0.1),
                    user=m_('#94A3B8', 0.8, ss=0.15), screen=m_('#E0F2FE', 0.6, e=0.6), server=m_('#10B981', 0.8, ss=0.15), worker=m_('#6366F1', 0.8, ss=0.15),
                    ring=m_('#F59E0B', 0.7, ss=0.1), tube=m_('#FFFFFF', 0.1, a=0.22), msg=m_('#EC4899', 0.7, ss=0.15, e=0.4),
                    label=m_('#FFFFFF', 0.8), ltext=m_('#334155', 0.8), line=m_('#CBB9A0', 0.8), status=m_('#F59E0B', 0.6, e=1.0),
                    lights=[('sun', None, (40, 0, -35), 15, 3.2, '#FFF5E1'), ('area', (0, 0, 8), (0, 0, 0), 10, 500, '#E0F2FE')],
                    world=('#F4EFE6', 0.9), look='AgX - Base Contrast', exp=0.2, bloom=0.0,
                    cam=dict(ortho=True, el=45, yaw=0, scale=8.4)),
    'darklab': dict(bg='#121316', floor=m_('#121316', 0.6), dots=None, plinth=m_('#1A1C20', 0.45, 0.5),
                    user=m_('#262930', 0.4, 0.5, bump=0.02), screen=m_('#00FF66', 0.4, e=4.0), server=m_('#1E2025', 0.4, 0.5, bump=0.02), worker=m_('#1E2025', 0.4, 0.5, bump=0.02),
                    ring=m_('#2E323B', 0.3, 0.8), tube=m_('#FFFFFF', 0.1, a=0.12), msg=m_('#00FF66', 0.4, e=7.0),
                    label=m_('#0D0E10', 0.5), ltext=m_('#D7DCE5', 0.5, e=0.8), line=m_('#00FF66', 0.4, e=4.0), status=m_('#00E5FF', 0.4, e=5.0),
                    lights=[('area', (-4.5, -0.5, 2.6), (70, 0, -85), 1.2, 700, '#E8F1FF'), ('area', (4.5, 1.5, 2.6), (70, 0, 95), 1.2, 600, '#E8F1FF'),
                            ('area', (0, -6, 6), (45, 0, 0), 6, 260, '#C9D6FF'), ('area', (0, 6, 4), (-55, 0, 180), 5, 300, '#00E5FF')],
                    world=('#121316', 1.0), look='AgX - High Contrast', exp=0.3, bloom=0.9,
                    cam=dict(ortho=False, lens=50, el=30, yaw=20, dist=12.5, fstop=2.8)),
    'gloss':   dict(bg='#E2E8F0', floor=m_('#E2E8F0', 0.3), dots=None, plinth=m_('#F1F5F9', 0.1, ct=1.0),
                    user=m_('#FFFFFF', 0.05, ct=1.0), screen=m_('#06B6D4', 0.1, e=1.0), server=m_('#06B6D4', 0.05, ct=1.0), worker=m_('#F43F5E', 0.05, ct=1.0),
                    ring=m_('#CBD5E1', 0.0, 1.0), tube=m_('#FFFFFF', 0.02, a=0.2), msg=m_('#FACC15', 0.05, ct=1.0, e=0.5),
                    label=m_('#0F172A', 0.1, ct=1.0), ltext=m_('#FFFFFF', 0.2), line=m_('#94A3B8', 0.1, 1.0), status=m_('#FACC15', 0.2, e=2.0),
                    lights=[('area', (-3, -4, 6), (40, 0, -30), 4, 900, '#FFFFFF'), ('area', (5, 0, 4), (60, 0, 90), 1.0, 600, '#FFFFFF'),
                            ('area', (-5, 2, 4), (60, 0, -90), 1.0, 500, '#FFFFFF')],
                    world=('#E2E8F0', 0.8), look='AgX - High Contrast', exp=-0.1, bloom=0.0,
                    cam=dict(ortho=False, lens=65, el=45, yaw=25, dist=15)),
}
S = LOOKS[VAR]

def mat(name, d, sh='solid'):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get('Principled BSDF'); nt = m.node_tree
    b.inputs['Base Color'].default_value = hx(d['c']); b.inputs['Roughness'].default_value = d['r']
    b.inputs['Metallic'].default_value = d['mt']; b.inputs['Subsurface Weight'].default_value = d['ss']
    b.inputs['Coat Weight'].default_value = d['ct']
    if d['e']: b.inputs['Emission Color'].default_value = hx(d['c']); b.inputs['Emission Strength'].default_value = d['e']
    if d['tr']:
        b.inputs['Transmission Weight'].default_value = d['tr']; m.use_raytrace_refraction = True
    if d['a'] < 1: b.inputs['Alpha'].default_value = d['a']; m.surface_render_method = 'BLENDED'
    if d['bump']:
        tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); bp = nt.nodes.new('ShaderNodeBump')
        nz.inputs['Scale'].default_value = 120; bp.inputs['Strength'].default_value = d['bump']
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m
M = {k: mat(k, v) for k, v in S.items() if isinstance(v, dict) and 'c' in v}
if S.get('dots'):  # dot grid on the floor
    nt = M['floor'].node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (5, 5, 5)
    fr = nt.nodes.new('ShaderNodeVectorMath'); fr.operation = 'FRACTION'
    ds = nt.nodes.new('ShaderNodeVectorMath'); ds.operation = 'DISTANCE'; ds.inputs[1].default_value = (0.5, 0.5, 0.0)
    lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.06
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = hx(S['floor']['c']); mx.inputs['B'].default_value = hx(S['dots'])
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); cmb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], sep.inputs[0])
    nt.links.new(sep.outputs['X'], cmb.inputs['X']); nt.links.new(sep.outputs['Y'], cmb.inputs['Y'])
    nt.links.new(cmb.outputs[0], fr.inputs[0]); nt.links.new(fr.outputs[0], ds.inputs[0]); nt.links.new(ds.outputs['Value'], lt.inputs[0])
    nt.links.new(lt.outputs[0], mx.inputs['Factor']); nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])

def link(ob, m, bevel=0.0, parent=None):
    col.objects.link(ob); ob.data.materials.append(m)
    if parent: ob.parent = parent
    if ob.type == 'MESH': ob.data.shade_smooth()
    if bevel:
        bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 4; bv.limit_method = 'ANGLE'; ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return ob
def box(name, loc, size, m, bevel=0.05, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m, bevel, parent)
def cyl(name, loc, r, h, m, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=64, radius1=r, radius2=r, depth=h); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.rotation_euler = rot; return link(ob, m)
def torus(loc, m):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.31, minor_radius=0.04, location=loc, rotation=(math.pi / 2, 0, 0))
    r = bpy.context.active_object; r.data.materials.append(m); r.data.shade_smooth(); return r
def text(name, body, loc, size, m, parent=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.005
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = (math.pi / 2, 0, 0); return link(ob, m, 0, parent)
def curve(name, pts, r, m):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts): p.co = c; p.handle_left_type = p.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu); return link(ob, m)
YAW = math.radians(S['cam']['yaw'])
def block(name, loc, size, m, label, lsize, core=None, slots=0, status=False):
    g = bpy.data.objects.new(name, None); g.location = loc; g.rotation_euler = (0, 0, YAW); col.objects.link(g)
    box(f'{name}_b', (0, 0, 0), size, m, 0.07, g)
    if core: box(f'{name}_core', (0, 0, 0), tuple(v * 0.55 for v in size), core, 0.04, g)
    fy = -size[1] / 2
    if label:
        box(f'{name}_lbl', (0, fy - 0.01, size[2] * 0.18), (size[0] * 0.78, 0.02, 0.22), M['label'], 0.02, g)
        text(f'{name}_t', label, (0, fy - 0.025, size[2] * 0.18), lsize, M['ltext'], g)
    for j in range(slots): box(f'{name}_s{j}', (0, fy - 0.01, -size[2] * 0.12 - j * 0.13), (size[0] * 0.62, 0.02, 0.055), M['status'], 0.0, g)
    if status: box(f'{name}_st', (size[0] * 0.3, fy - 0.01, -size[2] * 0.25), (0.12, 0.02, 0.06), M['status'], 0.01, g)
    return g

# ---- key frame ----
box('ground', (0, 0, -0.06), (60, 60, 0.1), M['floor'], 0)
box('plinth', (0, 0.1, 0.05), (3.8, 7.6, 0.12), M['plinth'], 0.04)
for i, x in enumerate((-1.2, -0.6, 0.0, 0.6, 1.2)):
    u = block(f'user{i}', (x, -3.0, 0.38), (0.36, 0.24, 0.52), M['user'], None, 0)
    box(f'userscr{i}', (0, -0.125, 0.03), (0.26, 0.01, 0.36), M['screen'], 0.0, u)
    curve(f'uline{i}', [(x, -2.85, 0.3), (x * 0.5, -2.3, 0.35), (0, -1.95, 0.45)], 0.014, M['line'])
block('server', (0, -1.5, 0.77), (1.1, 0.8, 1.3), M['server'], 'WEB SERVER', 0.11, core=M.get('core_server'), slots=3)
cyl('tube', (0, 0.45, 0.75), 0.3, 3.1, M['tube'], rot=(math.pi / 2, 0, 0))
for y in (-1.1, 0.45, 2.0): torus((0, y, 0.75), M['ring'])
for j in range(7): box(f'msg{j}', (0, -0.75 + j * 0.36, 0.75), (0.34, 0.22, 0.24), M['msg'], 0.04)
box('q_lbl', (0, -0.3, 1.33), (1.3, 0.04, 0.28), M['label'], 0.03)
text('q_t', 'MESSAGE QUEUE', (0, -0.325, 1.33), 0.12, M['ltext'])
for i, x in enumerate((-1.15, 0.0, 1.15)):
    block(f'worker{i}', (x, 2.9, 0.62), (0.85, 0.7, 1.0), M['worker'], 'WORKER', 0.09, core=M.get('core_worker'), status=True)
    curve(f'wline{i}', [(0, 2.05, 0.75), (x * 0.6, 2.3, 0.7), (x, 2.5, 0.55)], 0.014, M['line'])
box('flying', (-0.55, 2.3, 0.95), (0.3, 0.2, 0.22), M['msg'], 0.04)
box('incoming', (0, -2.3, 0.6), (0.3, 0.2, 0.22), M['msg'], 0.04)

# ---- camera: looks straight down the pipeline so it stacks up the 9:16 frame ----
C = S['cam']
tgt = bpy.data.objects.new('tgt', None); tgt.location = (0, 0.0, 0.55); col.objects.link(tgt)
camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); col.objects.link(cam); sc.camera = cam
el = math.radians(C['el']); dist = C.get('dist', 30)
cam.location = tuple(Vector(tgt.location) + dist * Vector((0, -math.cos(el), math.sin(el))))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
if C['ortho']: camd.type = 'ORTHO'; camd.ortho_scale = C['scale']
else:
    camd.lens = C['lens']
    if C.get('fstop'): camd.dof.use_dof = True; camd.dof.focus_object = tgt; camd.dof.aperture_fstop = C['fstop']
camd.clip_end = 200

for kind, loc, rot, size, power, h in S['lights']:
    ld = bpy.data.lights.new(kind, kind.upper()); ld.energy = power; ld.color = hx(h)[:3]
    if kind == 'area': ld.size = size
    elif kind == 'sun': ld.angle = math.radians(size)
    elif kind == 'spot': ld.spot_size = math.radians(40); ld.shadow_soft_size = size
    ob = bpy.data.objects.new(kind, ld); ob.rotation_euler = [math.radians(v) for v in rot]
    if loc: ob.location = loc
    col.objects.link(ob)
w = bpy.data.worlds.new('w'); sc.world = w
try: w.use_nodes = True
except Exception: pass
w.node_tree.nodes['Background'].inputs['Color'].default_value = hx(S['world'][0]); w.node_tree.nodes['Background'].inputs['Strength'].default_value = S['world'][1]

sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = 64
ee.use_raytracing = True; ee.use_shadows = True; ee.use_fast_gi = True
sc.render.resolution_x, sc.render.resolution_y = RES, RES * 16 // 9
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = S['look']; sc.view_settings.exposure = S['exp']
if S['bloom']:
    ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new('CompositorNodeRLayers'); gl = ng.nodes.new('CompositorNodeGlare'); go = ng.nodes.new('NodeGroupOutput')
    gl.inputs['Type'].default_value = 'Bloom'; gl.inputs['Threshold'].default_value = 0.8
    gl.inputs['Size'].default_value = 0.6; gl.inputs['Strength'].default_value = S['bloom']
    ng.links.new(rl.outputs['Image'], gl.inputs['Image']); ng.links.new(gl.outputs['Image'], go.inputs[0])
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
