#!/bin/zsh
# stills.sh <tag> <t1,t2,...> [samples]: upload scene + timings, render stills on the box, pull one JPG contact sheet + JPGs.
cd /Users/samarpit/insta-automation/letsbuildsimply
S=ops/boxes/fridge/ssh_config; TAG=$1; TS=$2; SMP=${3:-32}
scp -q -F $S 01-fridge/scene.py fridge:lbs/ep/
ssh -F $S fridge "cd ~/lbs/ep && rm -rf st && timeout 1200 ~/blender-5.2.2-linux-x64/blender -b -y -P scene.py -- --out st --stills $TS --samples $SMP 2>&1 | grep -E 'Error|Traceback|line [0-9]+,|NF' | tail -15
cd st && for f in still_*.png; do ffmpeg -v error -y -i \$f -q:v 3 \${f%.png}.jpg; done && ffmpeg -v error -y -pattern_type glob -i 'still_*.png' -vf 'scale=320:-1,tile=7x2:padding=4' -frames:v 1 -q:v 3 sheet.jpg"
mkdir -p 01-fridge/qc/$TAG; scp -q -F $S "fridge:lbs/ep/st/*.jpg" 01-fridge/qc/$TAG/ && ls 01-fridge/qc/$TAG | wc -l
