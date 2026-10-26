#!/bin/bash
# Full-quality render of an epx episode, then the encode: picture fades out over the last FADE s, BLACK s of black after,
# captions burned in.  Runs on the render machine:  epx_render.sh <blend> <episode dir> <out dir> <name> [blender]
set -u
blend=$1 ep=$2 O=$3 name=$4 B=${5:-/home/sam/apps/blender-5.2.2-linux-x64/blender}
cd "$(dirname "$0")"
mkdir -p $O/frames && rm -f $O/DONE $O/FAILED
end=$(python3 -c "import json;print(json.load(open('$ep/timeline.json'))['end'])")
read fade tail <<<$(python3 -c "import json;t=json.load(open('$ep/timeline.json'));print(t['fade'],t['tail'])")
for pass in 1 2; do
  echo "$(date +%T) render pass $pass ($(find $O/frames -size +0 | wc -l)/$end)"
  $B -b $blend -P blender/render.py -- animhq $O/frames 1920 64 1-$end >> $O/render.log 2>&1
  [ "$(find $O/frames -name 'f_*.png' -size +0 | wc -l)" -ge "$end" ] && break
done
n=$(find $O/frames -name 'f_*.png' -size +0 | wc -l)
echo "$(date +%T) rendered $n/$end frames"
[ "$n" -lt "$end" ] && { touch $O/FAILED; exit 1; }
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -framerate 30 -i $O/frames/f_%04d.png -i $ep/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=$ep/subs.ass" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart $O/$name.mp4 \
  || { touch $O/FAILED; exit 1; }
echo "$(date +%T) done"; touch $O/DONE
