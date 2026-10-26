#!/bin/bash
# runs ON the AWS box: render_aws.sh <dir> [chunks] → ~/hie/out/<dir>.mp4 (CPU SwiftShader, same steps as render_pc.sh)
set -e
cd ~/hie; D=$1; N=${2:-8}; mkdir -p out tmp/$D; rm -f tmp/$D/*
DUR=$(node -e "const fs=require('fs');const s=fs.readFileSync('videos/$D/voice/words.js','utf8');const T=JSON.parse(s.match(/window.TIMINGS=(\[.*?\]);/s)[1]);console.log(T[T.length-1].end+1.8)")
for i in $(seq 0 $((N-1))); do
  A=$(python3 -c "print($DUR*$i/$N)"); B=$(python3 -c "print($DUR*($i+1)/$N)")
  node tools/render.mjs videos/$D/video.html tmp/$D/c$i.mp4 --from $A --to $B > tmp/$D/log$i.txt 2>&1 &
done
wait
grep -h -i 'error' tmp/$D/log*.txt | head -5 || true
for i in $(seq 0 $((N-1))); do echo "file 'c$i.mp4'"; done > tmp/$D/list.txt
ffmpeg -v error -y -f concat -safe 0 -i tmp/$D/list.txt -i videos/$D/voice/voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/$D.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 out/$D.mp4
echo RENDER_DONE
