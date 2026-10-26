#!/bin/zsh
# assemble5.sh <name>: bring the L4 box's frames (cold open + tail, near-lossless chunks) to the L40S box, dissolve the cold open
# into the icebox, burn captions + vignette, mux the mix, encode 480p.
cd /Users/samarpit/insta-automation/letsbuildsimply
A=fridge2; B=fridge; SA=ops/boxes/$A/ssh_config; SB=ops/boxes/$B/ssh_config; NAME=${1:-fridge_v5_480p}; START=1700; DA=120; DB=135
ssh -F $SB $B "cd ~/lbs/v5 && ffmpeg -v error -y -framerate 30 -start_number $START -i r5/frames/f_%05d.png -c:v libx264 -preset slow -crf 6 -pix_fmt yuv444p chunk_b.mp4 && \
  ffmpeg -v error -y -framerate 30 -start_number 0 -i r5/open/f_%05d.png -c:v libx264 -preset slow -crf 6 -pix_fmt yuv444p chunk_o.mp4 && ls -la chunk_*.mp4"
mkdir -p 01-fridge/v5/build; scp -q -F $SB "${B}:lbs/v5/chunk_*.mp4" 01-fridge/v5/build/
ssh -F $SA $A "mkdir -p ~/lbs/fonts"; scp -q -F $SA assets/fonts/*.ttf ${A}:lbs/fonts/
scp -q -F $SA 01-fridge/v5/build/chunk_b.mp4 01-fridge/v5/build/chunk_o.mp4 01-fridge/v5/mix.wav 01-fridge/v5/overlay.ass ${A}:lbs/v5/
ssh -F $SA $A "cd ~/lbs/v5 && mkdir -p r5/open && ffmpeg -v error -y -i chunk_b.mp4 -start_number $START r5/frames/f_%05d.png && \
  ffmpeg -v error -y -i chunk_o.mp4 -start_number 0 r5/open/f_%05d.png && \
  for f in \$(seq 0 $DB); do F=\$(printf %05d \$f); if [ \$f -lt $DA ]; then cp r5/open/f_\$F.png r5/frames/f_\$F.png; else \
    k=\$(python3 -c \"print((\$f-$DA)/($DB-$DA))\"); ffmpeg -v error -y -i r5/open/f_\$F.png -i r5/frames/f_\$F.png -filter_complex \"blend=all_expr='A*(1-\$k)+B*\$k'\" r5/frames/b_\$F.png && mv r5/frames/b_\$F.png r5/frames/f_\$F.png; fi; done && \
  ls r5/frames | wc -l && mkdir -p final && \
  ffmpeg -v error -y -framerate 30 -start_number 0 -i r5/frames/f_%05d.png -i mix.wav \
  -vf 'vignette=PI/5,subtitles=overlay.ass:fontsdir=/home/ubuntu/lbs/fonts,format=yuv420p' \
  -c:v libx264 -preset slow -crf 17 -profile:v high -movflags +faststart -c:a aac -b:a 192k -shortest final/$NAME.mp4 && ls -la final/$NAME.mp4"
mkdir -p 01-fridge/final; scp -q -F $SA ${A}:lbs/v5/final/$NAME.mp4 01-fridge/final/ && ls -la 01-fridge/final/$NAME.mp4
