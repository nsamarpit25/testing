#!/bin/bash
# n6: Ep17 v2b = finish the two Claude shots that fix17 split mid-shot (1058-1103, 1219-1309) from the same blend, re-encode
cd ~/ctv2; B=~/blender-5.2.2-linux-x64/blender; e=ep17
rm -rf f17fixb; mkdir -p f17fixb
for r in 1058-1103 1219-1309; do
  echo "$(date +%T) range $r"
  for pass in 1 2; do
    for k in 1 2 3; do $B -b $e.blend -P blender/render.py -- animhq $PWD/f17fixb 1920 64 $r > rfb_$k.log 2>&1 & sleep 8; done; wait
    find f17fixb -size 0 -delete
  done
done
n=$(ls f17fixb | wc -l); echo "$(date +%T) $n/137 frames"; [ $n -ge 137 ] || { echo FIX INCOMPLETE; exit 1; }
cp f17fixb/*.png f17/
read end fade tail <<<$(python3 -c "import json;t=json.load(open('audio/$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -framerate 30 -start_number 1 -i f17/f_%04d.png -frames:v $end -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p ${e}_clean.mp4
ffmpeg -y -loglevel error -i ${e}_clean.mp4 -i audio/$e/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=audio/$e/subs.ass:fontsdir=$HOME/fonts" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart ${e}_final.mp4 \
  && echo "$(date +%T) FINAL DONE" || echo "$(date +%T) FINAL FAILED"
