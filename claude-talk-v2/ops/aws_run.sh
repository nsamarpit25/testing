#!/bin/bash
# on AWS: build each episode's .blend, render with 3 Blender processes sharing the range (placeholders), encode with fade + captions
B=~/blender-5.2.2-linux-x64/blender; cd ~/ctv2
for e in "$@"; do
  $B -b --factory-startup -P blender/epx.py -- $PWD/$e.blend $PWD/audio/$e/timeline.json > build_$e.log 2>&1 || { echo "$(date +%T) $e BUILD FAILED"; continue; }
  end=$(python3 -c "import json;print(json.load(open('audio/$e/timeline.json'))['end'])")
  read fade tail <<<$(python3 -c "import json;t=json.load(open('audio/$e/timeline.json'));print(t['fade'],t['tail'])")
  mkdir -p out/$e/frames
  for pass in 1 2 3; do
    echo "$(date +%T) $e pass $pass"
    for k in 1 2 3; do $B -b $e.blend -P blender/render.py -- animhq $PWD/out/$e/frames 1920 64 1-$end > out/$e/r$k.log 2>&1 & sleep 20; done; wait
    find out/$e/frames -size 0 -delete
    [ "$(find out/$e/frames -name 'f_*.png' -size +0 | wc -l)" -ge "$end" ] && break
  done
  st=$(python3 -c "print($end/30-$fade)")
  ffmpeg -y -loglevel error -framerate 30 -i out/$e/frames/f_%04d.png -i audio/$e/mix.wav \
    -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=audio/$e/subs.ass:fontsdir=$HOME/fonts" \
    -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart out/${e}_final.mp4 \
    && echo "$(date +%T) $e DONE" || echo "$(date +%T) $e ENCODE FAILED"
done
echo ALLDONE
