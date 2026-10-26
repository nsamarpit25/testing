#!/bin/sh
# assemble ../sc.py from the shared ep 3 / ep 5 modules and the ep 6 scene
cd "$(dirname "$0")"
J=../../3d-03-jet-blades/src
K=../../3d-05-shinkansen-kingfisher/src
cat $J/jb_head.py $J/helpers2.py $K/shared_jb_geo.py $K/shared_jb_mat.py $J/jb_shots.py $J/sf_air.py $J/sf_main.py sc_world.py sc_film.py > ../sc.py
