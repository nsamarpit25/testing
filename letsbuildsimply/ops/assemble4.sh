#!/bin/zsh
# assemble4.sh <name>: pull the L4 box's frames (as a near-lossless chunk) over to the L40S box, burn captions, mux the mix, encode 480p.
cd /Users/samarpit/insta-automation/letsbuildsimply
A=fridge2; B=fridge; SA=ops/boxes/$A/ssh_config; SB=ops/boxes/$B/ssh_config; NAME=${1:-fridge_v4_480p}; START=1720
ssh -F $SB $B "cd ~/lbs/ep && ffmpeg -v error -y -framerate 30 -start_number $START -i r4/frames/f_%05d.png -c:v libx264 -preset slow -crf 6 -pix_fmt yuv444p chunk_b.mp4 && ls -la chunk_b.mp4"
ssh -F $SA $A "mkdir -p ~/lbs/fonts"; scp -q -F $SA assets/fonts/*.ttf ${A}:lbs/fonts/
mkdir -p 01-fridge/build4; scp -q -F $SB ${B}:lbs/ep/chunk_b.mp4 01-fridge/build4/
scp -q -F $SA 01-fridge/build4/chunk_b.mp4 01-fridge/build4/mix.wav 01-fridge/build4/overlay.ass ${A}:lbs/ep/
ssh -F $SA $A "cd ~/lbs/ep && ffmpeg -v error -y -i chunk_b.mp4 -start_number $START r4/frames/f_%05d.png && ls r4/frames | wc -l && mkdir -p final && \
ffmpeg -v error -y -framerate 30 -start_number 0 -i r4/frames/f_%05d.png -i mix.wav \
  -vf 'vignette=PI/5,subtitles=overlay.ass:fontsdir=/home/ubuntu/lbs/fonts,format=yuv420p' \
  -c:v libx264 -preset slow -crf 17 -profile:v high -movflags +faststart -c:a aac -b:a 192k -shortest final/$NAME.mp4 && ls -la final/$NAME.mp4"
mkdir -p 01-fridge/final; scp -q -F $SA ${A}:lbs/ep/final/$NAME.mp4 01-fridge/final/ && ls -la 01-fridge/final/$NAME.mp4
