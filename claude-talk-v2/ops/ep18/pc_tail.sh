#!/bin/zsh
# PC renders Ep18 from the end backwards in 30-frame chunks; each chunk is relayed PC -> Mac -> AWS f18 (AWS skips existing frames).
# Stops when AWS's ascending render has reached the chunk. Log: ops/ep18/pc_tail.log
C=/Users/samarpit/insta-automation/claude-talk-v2; cd $C; P=sam@192.168.0.112; A=(ssh -F $C/ops/night/n7/ssh_config)
L=$C/ops/ep18/pc_tail.log; D=$C/output/ep18_pcframes; mkdir -p $D; hi=1677
while (( hi > 1 )); do
  lo=$(( hi - 29 )); (( lo < 1 )) && lo=1
  if $A n7 "test -e ~/ctv2/f18/f_$(printf %04d $lo).png"; then echo "$(date +%T) AWS reached $lo, stop" >> $L; break; fi
  echo "$(date +%T) PC $lo-$hi" >> $L
  ssh $P "cd ~/ctv2_18 && mkdir -p f18 && ~/apps/blender-5.2.2-linux-x64/blender -b ep18.blend -P blender/render.py -- animhq \$PWD/f18 1920 64 $lo-$hi > r18.log 2>&1; find f18 -size 0 -delete"
  rsync -a --remove-source-files "${P}:ctv2_18/f18/" $D/ && rsync -a --ignore-existing -e "$A[*]" $D/ n7:ctv2/f18/
  echo "$(date +%T) relayed, $(ls $D | wc -l) PC frames" >> $L
  hi=$(( lo - 1 ))
done
