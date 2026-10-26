#!/bin/bash
# render Ep15 BOARDCU inserts:  cu.sh <procs> a-b [a-b ...]  -> out/cu_<a>.mp4 (video only, frames a..b)
cd /home/sam/ctv2_test; B=$HOME/blender-5.2.2-linux-x64/blender; N=$1; shift
mkdir -p cu
for r in "$@"; do
  for k in $(seq 1 $N); do $B -b ep15.blend -P blender/render.py -- animhq $PWD/cu 1920 64 $r > cu_${r}_$k.log 2>&1 & sleep 6; done; wait
  find cu -size 0 -delete
  a=${r%-*}; b=${r#*-}
  ffmpeg -y -loglevel error -framerate 30 -start_number $a -i cu/f_%04d.png -frames:v $((b-a+1)) -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p out/cu_$a.mp4 \
    && echo "$(date +%T) CU $r DONE $(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 out/cu_$a.mp4)" || echo "CU $r FAILED"
done
echo "$(date +%T) CUJOBDONE"
