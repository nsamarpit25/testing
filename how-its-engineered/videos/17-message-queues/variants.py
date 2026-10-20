# Look variants for 17 Message Queues: one key frame (users -> web server -> message queue -> workers) in different styles.
# usage: blender -b -P videos/17-message-queues/variants.py -- <out.png> <clay|neon|studio|mini> [--res 720]
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

S = {
    'clay':   dict(bg='#2A1F38', bgs=0.7, floor='#3A2B4E', base='#5A4372', server='#2EC4B6', worker='#FF6B6B', user='#CBC0D3',
                   msg='#FFA20A', glass='#BFF7F2', label='#0E0B14', ltext='#FFF6EA', accent='#FF9F1C', line='#FF9F1C',
                   rough=0.72, sss=0.12, edges=False, key=240, look='AgX - High Contrast', exp=0.0, bloom=0.6, persp=False),
    'neon':   dict(bg='#05070F', bgs=1.0, floor='#0A0F1E', base='#0A0F1E', server='#0F1A33', worker='#0F1A33', user='#0F1A33',
                   msg='#FACC15', glass='#22D3EE', label='#05070F', ltext='#E6F6FF', accent='#22D3EE', line='#22D3EE',
                   rough=0.35, sss=0.0, edges=True, ecol={'server': '#22D3EE', 'worker': '#FF8A3D', 'user': '#A78BFA', 'base': '#1E3A8A'},
                   key=40, look='AgX - Base Contrast', exp=0.0, bloom=1.0, persp=False),
    'studio': dict(bg='#EFEAE2', bgs=1.0, floor='#ECE6DC', base='#E2DACD', server='#3B6FF6', worker='#F2652B', user='#9AA7BD',
                   msg='#22B864', glass='#DDF3FF', label='#1D2433', ltext='#FFFFFF', accent='#1D2433', line='#1D2433',
                   rough=0.6, sss=0.05, edges=False, key=420, look='AgX - Medium High Contrast', exp=0.25, bloom=0.0, persp=False),
    'mini':   dict(bg='#1A120C', bgs=0.5, floor='#8A5A36', base='#5A3A22', server='#F1E4C8', worker='#F1E4C8', user='#C9B79A',
                   msg='#FFB02E', glass='#E8F4F2', label='#14213D', ltext='#F1E4C8', accent='#D9A441', line='#D9A441',
                   rough=0.55, sss=0.08, edges=False, key=300, look='AgX - Medium High Contrast', exp=0.1, bloom=0.5, persp=True),
}[VAR]

def principled(m):
    try: m.use_nodes = True
    except Exception: pass
    return m.node_tree.nodes.get('Principled BSDF')
def mat(name, h, rough=None, metal=0.0, emit=0.0, alpha=1.0, sss=None):
    m = bpy.data.materials.new(name); b = principled(m)
    b.inputs['Base Color'].default_value = hx(h); b.inputs['Roughness'].default_value = S['rough'] if rough is None else rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Subsurface Weight'].default_value = S['sss'] if sss is None else sss
    if emit: b.inputs['Emission Color'].default_value = hx(h); b.inputs['Emission Strength'].default_value = emit
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.surface_render_method = 'BLENDED'
    if VAR == 'clay':
        nt = m.node_tree; tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); bp = nt.nodes.new('ShaderNodeBump')
        nz.inputs['Scale'].default_value = 60; bp.inputs['Strength'].default_value = 0.03
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m
def link(ob, m, bevel=0.0):
    col.objects.link(ob); ob.data.materials.append(m)
    if ob.type == 'MESH': ob.data.shade_smooth()
    if bevel:
        bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 3; bv.limit_method = 'ANGLE'
        ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return ob
def edges(ob, key):
    if not S['edges']: return
    e = ob.copy(); e.data = ob.data; e.modifiers.clear(); col.objects.link(e)
    w = e.modifiers.new('wf', 'WIREFRAME'); w.thickness = 0.025; w.use_replace = True
    e.data = ob.data.copy(); e.data.materials.clear(); e.data.materials.append(mat(f'edge_{key}', S['ecol'][key], emit=6.0))
def box(name, loc, size, m, bevel=0.04, ekey=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; link(ob, m, 0 if S['edges'] else bevel)
    if ekey: edges(ob, ekey)
    return ob
def cyl(name, loc, r, h, m, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=r, radius2=r, depth=h); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.rotation_euler = rot; return link(ob, m)
def ball(name, loc, r, m):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc; return link(ob, m)
def text(name, body, loc, size, m, rot=(math.pi / 2, 0, 0)):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.006
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = rot; col.objects.link(ob); ob.data.materials.append(m); return ob
def curve(name, pts, r, m):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts): p.co = c; p.handle_left_type = p.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu); col.objects.link(ob); ob.data.materials.append(m); return ob

M = dict(floor=mat('floor', S['floor']), base=mat('base', S['base']), server=mat('server', S['server']), worker=mat('worker', S['worker']),
         user=mat('user', S['user']), msg=mat('msg', S['msg'], emit=3.0 if VAR != 'studio' else 0.0, rough=0.3),
         glass=mat('glass', S['glass'], rough=0.05, alpha=0.25 if VAR != 'neon' else 0.12, emit=0.3 if VAR != 'studio' else 0.0),
         label=mat('label', S['label'], sss=0.0), ltext=mat('ltext', S['ltext'], emit=2.0 if VAR in ('neon',) else 0.0, sss=0.0),
         accent=mat('accent', S['accent'], emit=4.0 if VAR in ('neon', 'clay') else 0.0, metal=1.0 if VAR == 'mini' else 0.0, rough=0.3),
         line=mat('line', S['line'], emit=3.0 if VAR != 'studio' else 0.0, sss=0.0),
         screen=mat('screen', S['glass'] if VAR != 'studio' else '#3B6FF6', emit=2.5 if VAR != 'studio' else 0.5, sss=0.0))

# ---- the key frame: users -> web server -> queue -> workers (depth axis reads as up in a vertical frame) ----
box('ground', (0, 0, -0.06), (40, 40, 0.1), M['floor'], 0)
box('plinth', (0, 0.1, 0.05), (3.8, 7.6, 0.12), M['base'], 0.04, 'base')
# users
for i, x in enumerate((-1.2, -0.6, 0.0, 0.6, 1.2)):
    u = box(f'user{i}', (x, -3.0, 0.32), (0.36, 0.24, 0.52), M['user'], 0.05, 'user')
    box(f'userscr{i}', (x, -3.125, 0.36), (0.26, 0.01, 0.36), M['screen'], 0.0)
    curve(f'uline{i}', [(x, -2.85, 0.3), (x * 0.5, -2.3, 0.35), (0, -1.95, 0.45)], 0.012, M['line'])
# web server
box('server', (0, -1.5, 0.75), (1.1, 0.8, 1.3), M['server'], 0.06, 'server')
box('server_lbl', (0, -1.91, 0.95), (0.86, 0.02, 0.24), M['label'], 0.02)
text('server_t', 'WEB SERVER', (0, -1.925, 0.95), 0.11, M['ltext'])
for j in range(3): box(f'slot{j}', (0, -1.91, 0.55 - j * 0.14), (0.7, 0.02, 0.06), M['screen'], 0.0)
# the queue: a glass tube with messages lined up
cyl('tube', (0, 0.45, 0.75), 0.3, 3.1, M['glass'], rot=(math.pi / 2, 0, 0))
for j, y in enumerate((-1.1, 0.45, 2.0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.31, minor_radius=0.035, location=(0, y, 0.75), rotation=(math.pi / 2, 0, 0))
    r = bpy.context.active_object; r.data.materials.append(M['accent']); r.data.shade_smooth()
for j in range(7):
    m = box(f'msg{j}', (0, -0.75 + j * 0.36, 0.75), (0.34, 0.22, 0.24), M['msg'], 0.03)
box('q_lbl', (0, -0.3, 1.32), (1.3, 0.04, 0.28), M['label'], 0.03)
text('q_t', 'MESSAGE QUEUE', (0, -0.325, 1.32), 0.12, M['accent'] if VAR != 'studio' else M['ltext'])
# workers
for i, x in enumerate((-1.15, 0.0, 1.15)):
    box(f'worker{i}', (x, 2.9, 0.6), (0.85, 0.7, 1.0), M['worker'], 0.06, 'worker')
    box(f'wlbl{i}', (x, 2.54, 0.75), (0.66, 0.02, 0.2), M['label'], 0.02)
    text(f'wt{i}', 'WORKER', (x, 2.525, 0.75), 0.09, M['ltext'])
    curve(f'wline{i}', [(0, 2.05, 0.75), (x * 0.6, 2.3, 0.7), (x, 2.5, 0.55)], 0.012, M['line'])
box('flying', (-0.55, 2.3, 0.95), (0.3, 0.2, 0.22), M['msg'], 0.03)
box('incoming', (0, -2.3, 0.6), (0.3, 0.2, 0.22), M['msg'], 0.03)

# ---- camera: high three-quarter view so depth stacks up the 9:16 frame ----
tgt = bpy.data.objects.new('tgt', None); tgt.location = (0.15, 0.0, 0.55); col.objects.link(tgt)
camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); col.objects.link(cam); sc.camera = cam
az, el = math.radians(-14), math.radians(40)
dist = 30 if not S['persp'] else 26
cam.location = tuple(Vector(tgt.location) + dist * Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
if S['persp']:
    camd.lens = 115; camd.dof.use_dof = True; camd.dof.focus_object = tgt; camd.dof.aperture_fstop = 1.2
else:
    camd.type = 'ORTHO'; camd.ortho_scale = 8.4
camd.clip_end = 100

# ---- lights / world ----
def area(loc, rot, size, power, h):
    ld = bpy.data.lights.new('a', 'AREA'); ld.energy = power; ld.size = size; ld.color = hx(h)[:3]
    ob = bpy.data.objects.new('a', ld); ob.location = loc; ob.rotation_euler = [math.radians(v) for v in rot]; col.objects.link(ob)
area((-3, -5, 7), (40, 0, -25), 6, S['key'] * 2.2, '#FFF4E6')
area((4, 4, 5), (-40, 0, 140), 4, S['key'] * 0.8, {'clay': '#FF4D8D', 'neon': '#4F8CFF', 'studio': '#FFFFFF', 'mini': '#FFB46B'}[VAR])
if VAR == 'mini':
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 3.5; ld.color = hx('#FFD9A8')[:3]; ld.angle = 0.2
    ob = bpy.data.objects.new('sun', ld); ob.rotation_euler = (math.radians(50), 0, math.radians(-35)); col.objects.link(ob)
w = bpy.data.worlds.new('w'); sc.world = w
try: w.use_nodes = True
except Exception: pass
w.node_tree.nodes['Background'].inputs['Color'].default_value = hx(S['bg']); w.node_tree.nodes['Background'].inputs['Strength'].default_value = S['bgs']

sc.render.engine = 'BLENDER_EEVEE'; ee = sc.eevee; ee.taa_render_samples = 48
ee.use_raytracing = True; ee.use_shadows = True; ee.use_fast_gi = True
sc.render.resolution_x, sc.render.resolution_y = RES, RES * 16 // 9
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = S['look']; sc.view_settings.exposure = S['exp']
if S['bloom']:
    ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new('CompositorNodeRLayers'); gl = ng.nodes.new('CompositorNodeGlare'); go = ng.nodes.new('NodeGroupOutput')
    gl.inputs['Type'].default_value = 'Bloom'; gl.inputs['Threshold'].default_value = 1.0
    gl.inputs['Size'].default_value = 0.6; gl.inputs['Strength'].default_value = S['bloom']
    ng.links.new(rl.outputs['Image'], gl.inputs['Image']); ng.links.new(gl.outputs['Image'], go.inputs[0])
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
