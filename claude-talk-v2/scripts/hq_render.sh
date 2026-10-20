#!/bin/bash
# Full-quality render of a whole episode on the render PC, then encode with audio and captions.  Runs ON the PC:
#   hq_render.sh <blend> <episode dir with mix.wav + subs.ass> <out dir> <name>
# Frames already on disk are skipped, so a helper machine (the Mac, rendering backward from the end with
# blender/mac_helper.py) can claim frames by creating an empty file and then copying the finished frame over it.
set -u
blend=$1 ep=$2 O=$3 name=$4
B=/home/sam/apps/blender-5.2.2-linux-x64/blender
cd "$(dirname "$0")"
mkdir -p $O/frames && rm -f $O/DONE $O/FAILED
end=$($B -b $blend --python-expr 'import bpy; print("END", bpy.context.scene.frame_end)' 2>/dev/null | awk '/^END/{print $2}')
for pass in 1 2 3; do
  echo "$(date +%T) render pass $pass ($(find $O/frames -size +0 | wc -l)/$end frames done)"
  $B -b $blend -P blender/render.py -- animhq $O/frames 1920 64 1-$end >> $O/render.log 2>&1
  # let the helper finish frames it is still working on (claims are refreshed when it starts a frame)
  while [ -n "$(find $O/frames -size 0 -mmin -3)" ]; do sleep 20; done
  [ -z "$(find $O/frames -size 0)" ] && break
  echo "$(date +%T) clearing $(find $O/frames -size 0 | wc -l) abandoned claims"
  find $O/frames -size 0 -delete
done
n=$(find $O/frames -name 'f_*.png' -size +0 | wc -l)
echo "$(date +%T) rendered $n frames"
if [ "$n" -ne "$end" ]; then touch $O/FAILED; exit 1; fi
ffmpeg -y -loglevel error -framerate 30 -i $O/frames/f_%04d.png -i $ep/mix.wav -vf "ass=$ep/subs.ass" -c:v libx264 -crf 16 -preset slow \
  -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $O/$name.mp4 || { touch $O/FAILED; exit 1; }
echo "$(date +%T) done"; touch $O/DONE
