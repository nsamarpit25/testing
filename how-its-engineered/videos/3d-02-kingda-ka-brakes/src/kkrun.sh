#!/bin/bash
# kkrun.sh TAG FRAMES [HEIGHT] [SAMPLES] [cols]  -> assemble kk.py, build on PC, render stills, pull, contact sheet
set -e
S=$(cd "$(dirname "$0")" && pwd)
D=$(cd "$S/.." && pwd)
TAG=$1; FR=$2; H=${3:-640}; SM=${4:-12}; COLS=${5:-8}
SSH="ssh -o BatchMode=yes -o HostKeyAlias=192.168.0.102 sam@192.168.0.103"
cat $S/kk_head.py $S/helpers2.py $S/kk_body.py $S/kk_shots.py > $D/kk.py
python3 -c "import ast;ast.parse(open('$D/kk.py').read())"
scp -q -o BatchMode=yes -o HostKeyAlias=192.168.0.102 $D/kk.py sam@192.168.0.103:/mnt/ssd/render/3d-02-kingda-ka-brakes/
$SSH "cd /mnt/ssd/render/3d-02-kingda-ka-brakes && rm -rf st_$TAG && ~/apps/blender-5.2.2-linux-x64/blender -b --factory-startup -P kk.py -- build kk.blend > b_$TAG.log 2>&1; grep -E 'Error|Traceback' -A3 b_$TAG.log | head -20; ~/apps/blender-5.2.2-linux-x64/blender -b kk.blend -P kk.py -- render st_$TAG $H $SM $FR > r_$TAG.log 2>&1; grep -E 'Error|Traceback' -A3 r_$TAG.log | head; ls st_$TAG | wc -l" < /dev/null
rm -rf $S/k_$TAG; mkdir -p $S/k_$TAG
scp -q -o BatchMode=yes -o HostKeyAlias=192.168.0.102 "sam@192.168.0.103:/mnt/ssd/render/3d-02-kingda-ka-brakes/st_$TAG/*" $S/k_$TAG/
scp -q -o BatchMode=yes -o HostKeyAlias=192.168.0.102 sam@192.168.0.103:/mnt/ssd/render/3d-02-kingda-ka-brakes/labels.json $D/labels.json
N=$(ls $S/k_$TAG | wc -l); ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -loglevel error -y -pattern_type glob -i "$S/k_$TAG/f_*.png" -vf "scale=240:-1,tile=${COLS}x${ROWS}" -frames:v 1 $S/sheet_$TAG.png
echo sheet $S/sheet_$TAG.png
