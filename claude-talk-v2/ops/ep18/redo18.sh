#!/bin/bash
# n7: Ep18 v2/v3 = rebuild the blend, re-render only the frames the review fixes touched, then the final (as full18.sh)
cd ~/ctv2; B=~/blender-5.2.2-linux-x64/blender; e=ep18; R="945-1121 1305-1381"
rm -f $e.blend; $B -b --factory-startup -P blender/epx.py -- $PWD/$e.blend $PWD/audio/$e/timeline.json > b18.log 2>&1
read end fade tail <<<$(python3 -c "import json;t=json.load(open('audio/$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
for f in $(ls f18); do n=$((10#${f:2:4})); for r in $R; do [ $n -ge ${r%-*} ] && [ $n -le ${r#*-} ] && rm -f f18/$f; done; [ $n -gt $end ] && rm -f f18/$f; done
echo "$(date +%T) cleared, $(ls f18 | wc -l) kept"; touch REDO_READY
for pass in 1 2; do
  for r in $R; do for k in 1 2 3; do $B -b $e.blend -P blender/render.py -- animhq $PWD/f18 1920 64 $r > r18_$k.log 2>&1 & sleep 8; done; wait; done
  find f18 -size 0 -delete; n=$(ls f18 | wc -l); echo "$(date +%T) $n/$end frames"; [ $n -ge $end ] && break
done
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -framerate 30 -start_number 1 -i f18/f_%04d.png -frames:v $end -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p ${e}_clean.mp4
ffmpeg -y -loglevel error -i ${e}_clean.mp4 -i audio/$e/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=audio/$e/subs.ass:fontsdir=$HOME/fonts" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart ${e}_final.mp4 \
  && echo "$(date +%T) FINAL DONE" || echo "$(date +%T) FINAL FAILED"
