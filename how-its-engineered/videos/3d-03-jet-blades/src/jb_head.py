"""Jet engine blades that run hotter than their melting point: a procedural 3D product film for @how.its.engineered
(episode 3, no characters). Two studio sets far apart, each with its own floor and lights: a turbofan with a quarter
cutaway (E, engine axis along x, metres) and a macro studio with a high-pressure turbine disc on a stand and its hero
blade (D, disc axis along y, real scale: the blade is ~10 cm tall). Blade frame: z radial (span), x axial (gas flows
+x), y tangential; the origin sits on top of the platform. Every animated property is baked per frame from the shot
list; cuts get half-frame keys so motion blur never smears across a cut. Tracked labels are projected from 3D anchors
at bake time and written next to the .blend as labels.json.

blender -b --factory-startup -P jb.py -- build <out.blend>
blender -b jb.blend -P jb.py -- render <outdir> <height> <samples> [a-b | f,f,f] [--skip]
"""
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, Matrix, Quaternion

FPS = 30
T_END = 32.0
F_END = int(T_END * FPS) + 1
E0 = Vector((0, 0, 0))            # engine studio
D0 = Vector((100, 0, 0))          # disc / blade macro studio
ZE = 2.05                         # engine axis height
DC = D0 + Vector((0, 0, 0.62))    # disc centre
rad = math.radians

# blade (metres)
H_AF = 0.055                      # airfoil span
C_AX = 0.034                      # root chord
R_P = 0.300                       # platform radius on the disc
N_BL = 64
PITCH = 2 * math.pi * R_P / N_BL
Z_ROOT0, Z_ROOT1 = -0.016, -0.040  # fir-tree root top / bottom

PAL = dict(cyan="#2fd6ff", amber="#ff6a1a", gold="#ffc45a", ice="#bfe6ff")
THERMAL = [(0.0, "#05010f"), (0.22, "#2a0b5c"), (0.42, "#8e0f4a"), (0.58, "#d8242a"), (0.72, "#ff6a0e"),
           (0.85, "#ffb21c"), (0.94, "#ffe9a0"), (1.0, "#fffaf0")]
MELT = 0.84                       # melting point on the thermal scale (gas ~0.97, cooled metal ~0.6)
