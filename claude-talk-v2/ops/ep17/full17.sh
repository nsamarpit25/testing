#!/bin/bash
# n6: the whole of Ep17 = build, render every frame (3 Blender processes share the range; passes refill gaps), then the final
# with fade, black tail, captions and audio (as ops/night/fin.sh)
cd ~/ctv2; B=~/blender-5.2.2-linux-x64/blender; e=ep17
rm -f $e.blend; $B -b --factory-startup -P blender/epx.py -- $PWD/$e.blend $PWD/audio/$e/timeline.json > b17.log 2>&1
read end fade tail <<<$(python3 -c "import json;t=json.load(open('audio/$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
rm -rf f17; mkdir -p f17
for pass in 1 2 3; do
  echo "$(date +%T) pass $pass"
  for k in 1 2 3; do $B -b $e.blend -P blender/render.py -- animhq $PWD/f17 1920 64 1-$end > r17_$k.log 2>&1 & sleep 10; done; wait
  find f17 -size 0 -delete
  n=$(ls f17 | wc -l); echo "$(date +%T) $n/$end frames"; [ $n -ge $end ] && break
done
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -framerate 30 -start_number 1 -i f17/f_%04d.png -frames:v $end -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p ${e}_clean.mp4
ffmpeg -y -loglevel error -i ${e}_clean.mp4 -i audio/$e/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=audio/$e/subs.ass:fontsdir=$HOME/fonts" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart ${e}_final.mp4 \
  && echo "$(date +%T) FINAL DONE" || echo "$(date +%T) FINAL FAILED"
