#!/bin/sh
# assemble ../sk.py from the shared ep 3 modules and the ep 5 scene
cd "$(dirname "$0")"
J=../../3d-03-jet-blades/src
cat $J/jb_head.py $J/helpers2.py shared_jb_geo.py shared_jb_mat.py $J/jb_shots.py $J/sf_air.py $J/sf_main.py sk_world.py sk_train.py sk_film.py > ../sk.py
