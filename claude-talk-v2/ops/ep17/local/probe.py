import bpy
from mathutils import Vector
for o in bpy.data.objects:
    n=o.name.lower()
    if any(k in n for k in ("window","glass","frame","sill","curtain","rim_window","sky","pane")) and o.type in ("MESH","LIGHT","EMPTY"):
        if o.type=="MESH" and not o.hide_render:
            bb=[o.matrix_world @ Vector(c) for c in o.bound_box]
            mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
            print("OBJ", o.name, [round(x,2) for x in mn], [round(x,2) for x in mx])
        elif o.type=="LIGHT":
            print("LIGHT", o.name, [round(x,2) for x in o.location])
for c in bpy.data.objects:
    if c.type=="CAMERA": print("CAM", c.name, [round(x,2) for x in c.location])
