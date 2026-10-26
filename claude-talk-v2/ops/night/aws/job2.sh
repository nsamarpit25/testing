#!/bin/bash
# n4 round 2: new screens (Ep14 c2/c4 POST + wrapped throw, Ep15 c1 full URL) -> rebuild the blends, re-render only the MON frames
# that show them (plus a few unchanged frames each side to check the splice), Ep15 re-joined with the new captions.
cd /home/sam/ctv2_test; B=$HOME/blender-5.2.2-linux-x64/blender; F=$HOME/fonts
echo "$(date +%T) start"
mv ep14.blend ep14_r1.blend; mv ep15.blend ep15_r1.blend
$B -b --factory-startup -P blender/epx.py -- $PWD/ep14.blend $PWD/ep14/timeline.json > b14b.log 2>&1 &
$B -b --factory-startup -P blender/epx.py -- $PWD/ep15.blend $PWD/ep15/timeline.json > b15b.log 2>&1 &
wait; ls -la ep14.blend ep15.blend
mkdir -p g14 g15
for k in 1 2; do $B -b ep14.blend -P blender/render.py -- animhq $PWD/g14 1920 64 1208-1352 > s14_$k.log 2>&1 & sleep 8; done
$B -b ep15.blend -P blender/render.py -- animhq $PWD/g15 1920 64 185-250 > s15.log 2>&1 &
wait; find g14 g15 -size 0 -delete
echo "$(date +%T) frames: ep14 $(ls g14 | wc -l)/145, ep15 $(ls g15 | wc -l)/66"
ffmpeg -y -loglevel error -framerate 30 -start_number 1208 -i g14/f_%04d.png -frames:v 145 \
  -vf "setpts=PTS+1207/30/TB,ass=ep14/subs.ass:fontsdir=$F,setpts=PTS-STARTPTS" -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p out/ep14_patch_1208.mp4 && echo "$(date +%T) PATCH14 DONE"
ffmpeg -y -loglevel error -framerate 30 -start_number 185 -i g15/f_%04d.png -frames:v 66 -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p out/ep15_patch_185.mp4 && echo "$(date +%T) PATCH15 DONE"
e=ep15; read end fade tail <<<$(python3 -c "import json;t=json.load(open('$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -f concat -safe 0 -i out/${e}_list.txt -i $e/mix.wav -i out/ep15_patch_185.mp4 \
  -filter_complex "[2:v]setpts=PTS+184/30/TB[p];[0:v][p]overlay=eof_action=pass:repeatlast=0,fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=$e/subs.ass:fontsdir=$F[v]" \
  -map "[v]" -map 1:a -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart out/${e}_final_v2.mp4 \
  && echo "$(date +%T) $e FINAL DONE" || echo "$(date +%T) $e FINAL FAILED"
echo "$(date +%T) JOBDONE"
