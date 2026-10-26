#!/bin/bash
# jbaws.sh TAG FRAMES [HEIGHT] [SAMPLES] [cols] [--nobuild] -> like jbrun.sh, but builds and renders (Cycles, GPU)
# on the AWS box (ssh alias hie3 from $AWS/ssh_config)
set -e
S=$(cd "$(dirname "$0")" && pwd)
D=$(cd "$S/.." && pwd)
TAG=$1; FR=$2; H=${3:-640}; SM=${4:-64}; COLS=${5:-6}
AWS=${AWS:-/private/tmp/claude-501/-Users-samarpit-insta-automation/cb130588-c55e-4d43-8e2c-b5581a28a829/scratchpad/aws}
SSH="ssh -F $AWS/ssh_config hie3"
BL=/home/ubuntu/blender-5.2.2-linux-x64/blender
R=/home/ubuntu/jb
cat $S/jb_head.py $S/helpers2.py $S/jb_geo.py $S/jb_mat.py $S/jb_shots.py > $D/jb.py
python3 -c "import ast;ast.parse(open('$D/jb.py').read())"
$SSH "mkdir -p $R" < /dev/null
scp -q -F $AWS/ssh_config $D/jb.py hie3:$R/
BUILD="$BL -b --factory-startup -P jb.py -- build jb.blend > b_$TAG.log 2>&1; grep -E 'Error|Traceback' -A6 b_$TAG.log | head -30;"
[ "$6" = "--nobuild" ] && BUILD=""
$SSH "cd $R && rm -rf st_$TAG && $BUILD $BL -b jb.blend -P jb.py -- render st_$TAG $H $SM $FR > r_$TAG.log 2>&1; grep -E 'Error|Traceback|^GPU|no gpu' -A3 r_$TAG.log | head -20; ls st_$TAG | wc -l" < /dev/null
rm -rf $S/k_$TAG; mkdir -p $S/k_$TAG
scp -q -F $AWS/ssh_config "hie3:$R/st_$TAG/*" $S/k_$TAG/
scp -q -F $AWS/ssh_config hie3:$R/labels.json $D/labels.json
N=$(ls $S/k_$TAG | wc -l); ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -loglevel error -y -pattern_type glob -i "$S/k_$TAG/f_*.png" -vf "scale=300:-1,tile=${COLS}x${ROWS}:padding=4" -frames:v 1 $S/sheet_$TAG.png
echo sheet $S/sheet_$TAG.png
