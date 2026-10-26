#!/bin/bash
# on a box: join episode e's video-only segments (in frame order) and encode the final with fade, black tail, captions, audio.
# fin.sh e seg1.mp4 seg2.mp4 ...
e=$1; shift; cd ~/ctv2
read end fade tail <<<$(python3 -c "import json;t=json.load(open('audio/$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
rm -f out/${e}_list.txt; for s in "$@"; do echo "file '$PWD/$s'" >> out/${e}_list.txt; done
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -f concat -safe 0 -i out/${e}_list.txt -i audio/$e/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=audio/$e/subs.ass:fontsdir=$HOME/fonts" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart out/${e}_final.mp4 \
  && echo "$(date +%T) $e FINAL DONE" || echo "$(date +%T) $e FINAL FAILED"
