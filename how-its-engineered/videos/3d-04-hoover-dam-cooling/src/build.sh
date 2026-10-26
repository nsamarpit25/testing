#!/bin/sh
# assemble ../hd.py from the shared ep 3 modules and the ep 4 scene
cd "$(dirname "$0")"
J=../../3d-03-jet-blades/src
cat $J/jb_head.py $J/helpers2.py $J/jb_geo.py $J/jb_mat.py $J/jb_shots.py $J/sf_air.py $J/sf_main.py hd_world.py hd_cool.py hd_film.py > ../hd.py
