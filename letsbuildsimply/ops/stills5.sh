#!/bin/zsh
# stills5.sh <box> <tag> <t1,t2,...> [samples] [--open]: upload scene_v5 + timings, render stills on <box>, pull JPGs + a contact sheet.
cd /Users/samarpit/insta-automation/letsbuildsimply
B=$1; S=ops/boxes/$B/ssh_config; TAG=$2; TS=$3; SMP=${4:-24}; OPN=$5
ssh -F $S $B 'mkdir -p ~/lbs/v5/voice'
scp -q -F $S 01-fridge/v5/scene_v5.py ${B}:lbs/v5/; scp -q -F $S 01-fridge/v5/voice/timings.json ${B}:lbs/v5/voice/
ssh -F $S $B "cd ~/lbs/v5 && rm -rf st && ~/blender-5.2.2-linux-x64/blender -b -y -P scene_v5.py -- --timings voice/timings.json --out st --stills $TS --samples $SMP $OPN 2>&1 | grep -E 'Error|Traceback|line [0-9]+,|NF' | tail -15
cd st && for f in still_*.png; do ffmpeg -v error -y -i \$f -q:v 3 \${f%.png}.jpg; done && ffmpeg -v error -y -pattern_type glob -i 'still_*.png' -vf 'scale=240:-1,tile=8x3:padding=3' -frames:v 1 -q:v 3 sheet.jpg"
rm -rf 01-fridge/qc/$TAG; mkdir -p 01-fridge/qc/$TAG; scp -q -F $S "${B}:lbs/v5/st/*.jpg" 01-fridge/qc/$TAG/ && ls 01-fridge/qc/$TAG | wc -l
