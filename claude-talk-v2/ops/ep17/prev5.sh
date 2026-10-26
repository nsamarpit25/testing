#!/bin/bash
# n6: Ep17 5 s preview = frames 1-150 at full quality, captions + audio
cd ~/ctv2; B=~/blender-5.2.2-linux-x64/blender
$B -b --factory-startup -P blender/epx.py -- $PWD/ep17.blend $PWD/audio/ep17/timeline.json > b17.log 2>&1
mkdir -p f17
for k in 1 2 3; do $B -b ep17.blend -P blender/render.py -- animhq $PWD/f17 1920 64 1-150 > r17_$k.log 2>&1 & sleep 8; done; wait
find f17 -size 0 -delete; echo "frames $(ls f17 | wc -l)"
ffmpeg -y -loglevel error -framerate 30 -start_number 1 -i f17/f_%04d.png -i audio/ep17/mix.wav -frames:v 150 \
  -vf "ass=audio/ep17/subs.ass:fontsdir=$HOME/fonts" -map 0:v -map 1:a -t 5 -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart ep17_preview5.mp4 && echo PREVDONE
