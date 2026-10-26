#!/bin/zsh
# box_render.sh OUT RES SAMPLES A:B : bake + render a frame range on the ep4 AWS box (BOX=<name>, default ep4sq) (runs detached there; log in ~/ep4/OUT_A.log)
cd "$(dirname "$0")/.."; X=${BOX:-ep4sq}; B=~/insta-automation/letsbuildsimply/ops/boxes/$X/ssh_config; ssh -F $B $X "mkdir -p ~/ep4/scripts ~/ep4/voice"; O=$1; RES=$2; SMP=$3; FR=$4
scp -q -F $B scripts/scene.py scripts/sqgeom.py ${X}:ep4/scripts/; scp -q -F $B voice/narration.words.json ${X}:ep4/voice/
ssh -F $B $X "cd ~/ep4/scripts && nohup ~/blender-5.2.2-linux-x64/blender -b -P scene.py -- --words ../voice/narration.words.json --out ../$O --res $RES --samples $SMP --frames $FR --save ../$O/project.blend > ../${O}_${FR%%:*}.log 2>&1 < /dev/null &"
