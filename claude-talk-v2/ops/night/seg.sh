#!/bin/bash
# on a box: render frames a-b of episode e with N Blender processes (placeholders share the range, passes refill gaps),
# then encode them to a near-lossless video-only segment out/<e>_seg_<a>.mp4 for the final join.   seg.sh e a b [N] [blender]
e=$1; a=$2; b=$3; N=${4:-3}; B=${5:-~/blender-5.2.2-linux-x64/blender}; cd ~/ctv2
[ -f $e.blend ] || $B -b --factory-startup -P blender/epx.py -- $PWD/$e.blend $PWD/audio/$e/timeline.json > build_$e.log 2>&1
mkdir -p out/$e/frames
for pass in 1 2 3; do
  echo "$(date +%T) $e $a-$b pass $pass"
  for k in $(seq 1 $N); do $B -b $e.blend -P blender/render.py -- animhq $PWD/out/$e/frames 1920 64 $a-$b > out/$e/s${a}_$k.log 2>&1 & sleep 20; done; wait
  find out/$e/frames -size 0 -delete
  n=0; for f in $(seq $a $b); do [ -s out/$e/frames/f_$(printf %04d $f).png ] && n=$((n+1)); done
  [ $n -eq $((b-a+1)) ] && break
done
ffmpeg -y -loglevel error -framerate 30 -start_number $a -i out/$e/frames/f_%04d.png -frames:v $((b-a+1)) -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p out/${e}_seg_$a.mp4 \
  && echo "$(date +%T) $e SEG $a-$b DONE" || echo "$(date +%T) $e SEG $a-$b FAILED"
