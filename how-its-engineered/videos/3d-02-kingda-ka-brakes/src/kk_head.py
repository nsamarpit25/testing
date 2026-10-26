"""Kingda Ka's magnetic brakes: a fully procedural 3D reel for @how.its.engineered (episode 2, no characters).
Sets, far apart so each shot sees only its own: the ride at dusk (origin, metres: launch track along +x, the top hat
between x=0 and x=30, then the brake run), a friction-brake demo studio (FR) and a macro studio with one magnet
sweeping over one copper fin (MC). The train is placed from a 1-D physics run along the track (launch, gravity,
eddy-current braking), so every shot shows believable speeds. Every animated property is baked per frame from the
shot list; cuts get half-frame keys so motion blur never smears across a cut. Tracked on-screen labels are projected
from 3D anchors at bake time and written next to the .blend as labels.json.

blender -b --factory-startup -P kk.py -- build <out.blend>
blender -b kk.blend -P kk.py -- render <outdir> <height> <samples> [a-b | f,f,f] [--skip]
"""
import bpy, bmesh, json, math, os, random, sys
from mathutils import Vector, Matrix, Quaternion

FPS = 30
T_END = 43.0
F_END = int(T_END * FPS) + 1
FR = Vector((5000, 0, 0))
MC = Vector((6000, 0, 0))
PAL = dict(sky0="#0d1015", sky1="#232b36", hz="#9a7458", track="#a7b0ba", lattice="#59626d", ground="#171b20",
           cyan="#19e3ff", amber="#ff6a1a", copper="#d0835a", nickel="#c9d2da", body="#1d232a", seat="#0e1115")
rad = math.radians
SUN_DIR = Vector((-0.6, -0.75, 0.13)).normalized()   # towards the low sun: front-left of the usual camera side (-y)


