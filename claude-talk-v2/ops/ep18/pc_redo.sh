#!/bin/zsh
# PC renders the Ep18 v2 tail ranges and relays them to n7 (after n7 has cleared the old frames)
C=/Users/samarpit/insta-automation/claude-talk-v2; P=sam@192.168.0.112; A=(ssh -F $C/ops/night/n7/ssh_config); L=$C/ops/ep18/pc_redo.log; D=$C/output/ep18_pcframes; mkdir -p $D
until $A n7 'test -e ~/ctv2/REDO_READY'; do sleep 10; done
for r in 1352-1381 1325-1351 1305-1324; do
  $A n7 "test -e ~/ctv2/f18/f_$(printf %04d ${r%-*}).png" && { echo "$(date +%T) n7 has $r, skip" >> $L; continue; }
  echo "$(date +%T) PC $r" >> $L
  ssh $P "cd ~/ctv2_18 && mkdir -p f18 && ~/apps/blender-5.2.2-linux-x64/blender -b ep18.blend -P blender/render.py -- animhq \$PWD/f18 1920 64 $r > r18.log 2>&1; find f18 -size 0 -delete"
  rsync -a --remove-source-files "${P}:ctv2_18/f18/" $D/ && rsync -a --ignore-existing -e "$A[*]" $D/ n7:ctv2/f18/
done
echo "$(date +%T) PC done" >> $L
