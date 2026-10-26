#!/bin/bash
# runs ON the PC: render_pc.sh <dir> <out-name> [chunks]  → /mnt/ssd/hie/out/<out-name>.mp4 (with voice)
# GPU (Vulkan) by default; RENDER_MJS=tools/render.mjs falls back to CPU (SwiftShader)
set -e
cd /mnt/ssd/hie; export PATH=$HOME/.local/share/mise/shims:$PATH CHROMIUM_PATH=/usr/bin/chromium
D=$1; OUT=$2; N=${3:-6}; mkdir -p out tmp/$OUT; rm -f tmp/$OUT/*
DUR=$(node -e "const fs=require('fs');const s=fs.readFileSync('videos/$D/voice/words.js','utf8');const T=JSON.parse(s.match(/window.TIMINGS=(\[.*?\]);/s)[1]);console.log(T[T.length-1].end+1.8)")
for i in $(seq 0 $((N-1))); do
  A=$(python3 -c "print($DUR*$i/$N)"); B=$(python3 -c "print($DUR*($i+1)/$N)")
  node ${RENDER_MJS:-tools/render_gpu.mjs} videos/$D/video.html tmp/$OUT/c$i.mp4 --from $A --to $B > tmp/$OUT/log$i.txt 2>&1 &
done
wait
grep -h -i 'error' tmp/$OUT/log*.txt | head -5 || true
for i in $(seq 0 $((N-1))); do echo "file 'c$i.mp4'"; done > tmp/$OUT/list.txt
ffmpeg -v error -y -f concat -safe 0 -i tmp/$OUT/list.txt -i videos/$D/voice/voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/$OUT.mp4
rm -rf tmp/$OUT
ffprobe -v error -show_entries format=duration -of csv=p=0 out/$OUT.mp4
