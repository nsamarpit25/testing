#!/bin/zsh
# box_stills.sh OUT TIMES [RES]: sync scene to the ep3 box, render stills there, pull them back to build/OUT
cd "$(dirname "$0")/.."; B=~/insta-automation/letsbuildsimply/ops/boxes/ep3/ssh_config; O=$1; T=$2; RES=${3:-480}
scp -q -F $B scripts/scene.py voice/narration.words.json ep3:ep3/scripts/
ssh -F $B ep3 "cd ~/ep3/scripts && rm -rf ../$O && timeout 1500 ~/blender-5.2.2-linux-x64/blender -b -P scene.py -- --words narration.words.json --out ../$O --res $RES --samples 16 --stills $T > ../$O.log 2>&1; grep -E 'state loop|baked|cuts at|STILLS_DONE' ../$O.log; grep -B2 -A6 Traceback ../$O.log | head -30"
mkdir -p build/$O; scp -q -F $B "ep3:ep3/$O/*" build/$O/ 2>/dev/null; ls build/$O | wc -l
