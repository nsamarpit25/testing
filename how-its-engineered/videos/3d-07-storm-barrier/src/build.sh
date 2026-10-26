#!/bin/sh
# assemble ../sb.py from the shared ep 3 / ep 5 modules and the ep 7 scene
cd "$(dirname "$0")"
J=../../3d-03-jet-blades/src
P=../../3d-05-shinkansen-kingfisher/src
cat $J/jb_head.py $J/helpers2.py $P/shared_jb_geo.py $P/shared_jb_mat.py $J/jb_shots.py $J/sf_air.py $J/sf_main.py sb_world.py sb_film.py > ../sb.py
