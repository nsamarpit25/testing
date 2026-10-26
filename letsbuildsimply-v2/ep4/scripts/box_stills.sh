#!/bin/zsh
# box_stills.sh OUT TIMES [RES] [SAMPLES]: sync the scene to the ep4 AWS box, bake + render stills there, pull them back to build/OUT
cd "$(dirname "$0")/.."; B=~/insta-automation/letsbuildsimply/ops/boxes/ep4sq/ssh_config; O=$1; T=$2; RES=${3:-480}; SMP=${4:-24}
scp -q -F $B scripts/scene.py scripts/sqgeom.py ep4sq:ep4/scripts/; scp -q -F $B voice/narration.words.json ep4sq:ep4/voice/
ssh -F $B ep4sq "cd ~/ep4/scripts && rm -rf ../$O && timeout 2400 ~/blender-5.2.2-linux-x64/blender -b -P scene.py -- --words ../voice/narration.words.json --out ../$O --res $RES --samples $SMP --stills $T > ../$O.log 2>&1; grep -E 'beats|GPU|state loop|baked|cuts at|STILLS_DONE|Error|error' ../$O.log | grep -v -i 'denois' | head -20; grep -B2 -A8 Traceback ../$O.log | head -40"
mkdir -p build/$O; scp -q -F $B "ep4sq:ep4/$O/*" build/$O/ 2>/dev/null; ls build/$O | wc -l
