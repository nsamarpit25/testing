#!/bin/bash
# n6: Ep17 v2 = rebuild the blend from the new timeline, re-render only the changed ranges, swap them into f17, re-encode
cd ~/ctv2; B=~/blender-5.2.2-linux-x64/blender; e=ep17
rm -f $e.blend; $B -b --factory-startup -P blender/epx.py -- $PWD/$e.blend $PWD/audio/$e/timeline.json > b17c.log 2>&1
rm -rf f17fix; mkdir -p f17fix
for r in 39-105 1104-1218 1310-1442; do
  echo "$(date +%T) range $r"
  for pass in 1 2; do
    for k in 1 2 3; do $B -b $e.blend -P blender/render.py -- animhq $PWD/f17fix 1920 64 $r > rf_$k.log 2>&1 & sleep 8; done; wait
    find f17fix -size 0 -delete
  done
done
n=$(ls f17fix | wc -l); echo "$(date +%T) $n/314 frames"; [ $n -ge 314 ] || { echo FIX INCOMPLETE; exit 1; }
[ -d f17_v1 ] || cp -r f17 f17_v1
cp f17fix/*.png f17/
read end fade tail <<<$(python3 -c "import json;t=json.load(open('audio/$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
st=$(python3 -c "print($end/30-$fade)")
mv ${e}_final.mp4 ${e}_final_v1.mp4; mv ${e}_clean.mp4 ${e}_clean_v1.mp4
ffmpeg -y -loglevel error -framerate 30 -start_number 1 -i f17/f_%04d.png -frames:v $end -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p ${e}_clean.mp4
ffmpeg -y -loglevel error -i ${e}_clean.mp4 -i audio/$e/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=audio/$e/subs.ass:fontsdir=$HOME/fonts" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart ${e}_final.mp4 \
  && echo "$(date +%T) FINAL DONE" || echo "$(date +%T) FINAL FAILED"
