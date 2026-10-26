#!/bin/bash
# sfrun.sh TAG HEIGHT SAMPLES [ids] -> style frames on the AWS box, pulled to src/sf_TAG
set -e
S=$(cd "$(dirname "$0")" && pwd)

SSH="ssh -o BatchMode=yes -o HostKeyAlias=192.168.0.102 sam@192.168.0.103"
BL=/home/sam/apps/blender-5.2.2-linux-x64/blender
R=/mnt/ssd/render/3d-03-jet-blades
cat $S/jb_head.py $S/helpers2.py $S/jb_geo.py $S/jb_mat.py $S/jb_shots.py $S/sf_air.py $S/sf_main.py > $S/../sf.py
python3 -c "import ast;ast.parse(open('$S/../sf.py').read())"
scp -q -o BatchMode=yes -o HostKeyAlias=192.168.0.102 $S/../sf.py sam@192.168.0.103:$R/
$SSH "cd $R && rm -rf sf_$1 sf_$1.done && nohup sh -c '$BL -b --factory-startup -P sf.py -- sf_$1 $2 $3 $4 > s_$1.log 2>&1; touch sf_$1.done' > /dev/null 2>&1 < /dev/null &" < /dev/null
until $SSH "test -f $R/sf_$1.done" < /dev/null; do sleep 15; done
$SSH "cd $R && grep -E 'Error|Traceback' -A5 s_$1.log | head -30; grep -E 'Saved' s_$1.log" < /dev/null
rm -rf $S/sf_$1; mkdir -p $S/sf_$1
scp -q -o BatchMode=yes -o HostKeyAlias=192.168.0.102 "sam@192.168.0.103:$R/sf_$1/*" $S/sf_$1/
ls $S/sf_$1
