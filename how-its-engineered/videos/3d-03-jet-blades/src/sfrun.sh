#!/bin/bash
# sfrun.sh TAG HEIGHT SAMPLES [ids] -> style frames on the AWS box, pulled to src/sf_TAG
set -e
S=$(cd "$(dirname "$0")" && pwd)
AWS=${AWS:-/private/tmp/claude-501/-Users-samarpit-insta-automation/cb130588-c55e-4d43-8e2c-b5581a28a829/scratchpad/aws}
SSH="ssh -F $AWS/ssh_config hie3"
BL=/home/ubuntu/blender-5.2.2-linux-x64/blender
R=/home/ubuntu/jb
cat $S/jb_head.py $S/helpers2.py $S/jb_geo.py $S/jb_mat.py $S/jb_shots.py $S/sf_air.py $S/sf_main.py > $S/../sf.py
python3 -c "import ast;ast.parse(open('$S/../sf.py').read())"
scp -q -F $AWS/ssh_config $S/../sf.py hie3:$R/
$SSH "cd $R && rm -rf sf_$1 && $BL -b --factory-startup -P sf.py -- sf_$1 $2 $3 $4 > s_$1.log 2>&1; grep -E 'Error|Traceback|DONE' -A5 s_$1.log | head -30; grep -E 'Time:' s_$1.log | tail -5" < /dev/null
rm -rf $S/sf_$1; mkdir -p $S/sf_$1
scp -q -F $AWS/ssh_config "hie3:$R/sf_$1/*" $S/sf_$1/
ls $S/sf_$1
