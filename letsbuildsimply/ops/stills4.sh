#!/bin/zsh
# stills4.sh <box> <tag> <t1,t2,...> [samples]: upload scene_v4 + timings, render stills on <box>, pull a JPG contact sheet + JPGs.
cd /Users/samarpit/insta-automation/letsbuildsimply
B=$1; S=ops/boxes/$B/ssh_config; TAG=$2; TS=$3; SMP=${4:-24}
ssh -F $S $B 'mkdir -p ~/lbs/ep/voice4'
scp -q -F $S 01-fridge/scene_v4.py ${B}:lbs/ep/; scp -q -F $S 01-fridge/voice4/timings_final.json ${B}:lbs/ep/voice4/
ssh -F $S $B "cd ~/lbs/ep && rm -rf st && ~/blender-5.2.2-linux-x64/blender -b -y -P scene_v4.py -- --out st --stills $TS --samples $SMP 2>&1 | grep -E 'Error|Traceback|line [0-9]+,|NF' | tail -15
cd st && for f in still_*.png; do ffmpeg -v error -y -i \$f -q:v 3 \${f%.png}.jpg; done && ffmpeg -v error -y -pattern_type glob -i 'still_*.png' -vf 'scale=240:-1,tile=8x3:padding=3' -frames:v 1 -q:v 3 sheet.jpg"
mkdir -p 01-fridge/qc/$TAG; rm -rf 01-fridge/qc/$TAG; mkdir -p 01-fridge/qc/$TAG; scp -q -F $S "${B}:lbs/ep/st/*.jpg" 01-fridge/qc/$TAG/ && ls 01-fridge/qc/$TAG | wc -l
