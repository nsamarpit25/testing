#!/bin/zsh
# assemble.sh <outname>: everything on the box (nothing heavy on the Mac): audio mix, overlay, merge out/ + out3/ frames,
# encode the 480p mp4, run cutcheck, then pull only the finished mp4 back.
cd /Users/samarpit/insta-automation/letsbuildsimply
S=ops/boxes/fridge/ssh_config; NAME=${1:-fridge_480p}
ssh -F $S fridge "cd ~/lbs/ep && mkdir -p build final && \
  ~/wv/bin/python mix.py out2/anchors.json voice/take_Puck.wav build/mix.wav && \
  ~/wv/bin/python overlay.py voice/timings.json out2/anchors.json script.json build/overlay.ass && \
  rm -rf merged && mkdir merged && cp out/frames/*.png merged/ && cp out3/frames/*.png merged/ 2>/dev/null; cp out4/frames/*.png merged/ 2>/dev/null; ls merged | wc -l
ffmpeg -v error -y -framerate 30 -start_number 0 -i merged/f_%05d.png -i build/mix.wav \
  -vf 'subtitles=build/overlay.ass:fontsdir=/home/ubuntu/lbs/fonts,format=yuv420p' \
  -c:v libx264 -preset slow -crf 17 -profile:v high -movflags +faststart -c:a aac -b:a 192k -shortest final/$NAME.mp4 && ls -la final/$NAME.mp4
~/wv/bin/python ~/lbs/cutcheck.py final/$NAME.mp4 final/cutcheck_$NAME; echo cutcheck_exit=\$?"
mkdir -p 01-fridge/final; scp -q -F $S fridge:lbs/ep/final/$NAME.mp4 01-fridge/final/ && ls -la 01-fridge/final/$NAME.mp4
