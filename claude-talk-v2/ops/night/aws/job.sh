#!/bin/bash
# n4: finish what the PC couldn't. Same paths as the PC (the .blend files were built there): /home/sam/ctv2_test
cd /home/sam/ctv2_test; B=$HOME/blender-5.2.2-linux-x64/blender; F=$HOME/fonts
mkdir -p f15 f14 cov out
echo "$(date +%T) start"
for k in 1 2; do $B -b ep15.blend -P blender/render.py -- animhq $PWD/f15 1920 64 1616-1714 > r15_$k.log 2>&1 & sleep 10; done
$B -b ep14.blend -P blender/render.py -- animhq $PWD/f14 1920 64 1358-1410 > r14.log 2>&1 &
wait; find f15 f14 -size 0 -delete
echo "$(date +%T) frames: ep15 $(ls f15 | wc -l)/99, ep14 $(ls f14 | wc -l)/53"
$B -b ep14.blend -P blender/render.py -- frameshq $PWD/cov/e14 1920 64 720 > c14.log 2>&1 &
$B -b ep15.blend -P blender/render.py -- frameshq $PWD/cov/e15 1920 64 331 > c15.log 2>&1 &
$B -b ep16v3.blend -P blender/render.py -- frameshq $PWD/cov/e16 1920 64 1960 > c16.log 2>&1 &
ffmpeg -y -loglevel error -framerate 30 -start_number 1616 -i f15/f_%04d.png -frames:v 99 -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p out/ep15_seg_1616.mp4 && echo "$(date +%T) SEG 1616 DONE"
# Ep14 patch: captions burned at the frames' real times, then rebased to 0 for the overlay on the Mac
ffmpeg -y -loglevel error -framerate 30 -start_number 1358 -i f14/f_%04d.png -frames:v 53 \
  -vf "setpts=PTS+1357/30/TB,ass=ep14/subs.ass:fontsdir=$F,setpts=PTS-STARTPTS" -c:v libx264 -crf 8 -preset medium -pix_fmt yuv420p out/ep14_patch_1358.mp4 && echo "$(date +%T) PATCH DONE"
# Ep15 final, as ops/night/fin.sh
e=ep15; read end fade tail <<<$(python3 -c "import json;t=json.load(open('$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
rm -f out/${e}_list.txt; for s in 1 1251 1616 1715; do echo "file '$PWD/out/ep15_seg_$s.mp4'" >> out/${e}_list.txt; done
st=$(python3 -c "print($end/30-$fade)")
ffmpeg -y -loglevel error -f concat -safe 0 -i out/${e}_list.txt -i $e/mix.wav \
  -vf "fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=$e/subs.ass:fontsdir=$F" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart out/${e}_final.mp4 \
  && echo "$(date +%T) $e FINAL DONE" || echo "$(date +%T) $e FINAL FAILED"
wait; find cov -type f; echo "$(date +%T) JOBDONE"
