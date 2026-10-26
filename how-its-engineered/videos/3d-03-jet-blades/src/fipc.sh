#!/bin/bash
# fipc.sh TAG HEIGHT SAMPLES FRAMES [cols] -> film frames on the PC (GPU + CPU), pulled to src/fi_TAG + a contact sheet
set -e
S=$(cd "$(dirname "$0")" && pwd)
SSH="ssh -o BatchMode=yes -o HostKeyAlias=192.168.0.102 sam@192.168.0.103"
SCP="scp -q -o BatchMode=yes -o HostKeyAlias=192.168.0.102"
BL=/home/sam/apps/blender-5.2.2-linux-x64/blender
R=/mnt/ssd/render/3d-03-jet-blades
TAG=$1; COLS=${5:-6}
cat $S/jb_head.py $S/helpers2.py $S/jb_geo.py $S/jb_mat.py $S/jb_shots.py $S/sf_air.py $S/sf_main.py $S/sf_film.py > $S/../sf.py
python3 -c "import ast;ast.parse(open('$S/../sf.py').read())"
$SCP $S/../sf.py sam@192.168.0.103:$R/
$SSH "cd $R && rm -rf fi_$TAG fi_$TAG.done && nohup sh -c '$BL -b --factory-startup -P sf.py -- film fi_$TAG $2 $3 $4 > f_$TAG.log 2>&1; touch fi_$TAG.done' > /dev/null 2>&1 < /dev/null &" < /dev/null
[ "$6" = "--detach" ] && { echo detached; exit 0; }
until $SSH "test -f $R/fi_$TAG.done" < /dev/null; do sleep 15; done
$SSH "cd $R && grep -E 'Error|Traceback' -A6 f_$TAG.log | head -30; grep -E '^GPU|BAKED' f_$TAG.log; grep -c Saved f_$TAG.log" < /dev/null
rm -rf $S/fi_$TAG; mkdir -p $S/fi_$TAG
$SCP "sam@192.168.0.103:$R/fi_$TAG/*" $S/fi_$TAG/
N=$(ls $S/fi_$TAG | wc -l); ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -loglevel error -y -pattern_type glob -i "$S/fi_$TAG/f_*.png" -vf "scale=300:-1,tile=${COLS}x${ROWS}:padding=4" -frames:v 1 $S/sheet_fi_$TAG.png
echo sheet $S/sheet_fi_$TAG.png
