#!/bin/bash
# n4: Ep15 v3 = the four video-only segments + the c1 screen patch + six BOARDCU inserts, then fade, black tail, captions, audio
cd /home/sam/ctv2_test; F=$HOME/fonts; e=ep15
read end fade tail <<<$(python3 -c "import json;t=json.load(open('$e/timeline.json'));print(t['end'],t['fade'],t['tail'])")
st=$(python3 -c "print($end/30-$fade)")
P="185 cu_422 cu_700 cu_935 cu_1212 cu_1424 cu_1779"
in=""; fc=""; last="0:v"; i=2
for p in $P; do
  f=out/${p}.mp4; [ $p = 185 ] && f=out/ep15_patch_185.mp4
  a=${p#cu_}; in="$in -i $f"
  fc="$fc[$i:v]setpts=PTS+$((a-1))/30/TB[p$i];[$last][p$i]overlay=eof_action=pass:repeatlast=0[o$i];"; last="o$i"; i=$((i+1))
done
fc="$fc[$last]fade=t=out:st=$st:d=$fade,tpad=stop_mode=add:stop_duration=$tail:color=black,ass=$e/subs.ass:fontsdir=$F[v]"
ffmpeg -y -loglevel error -f concat -safe 0 -i out/${e}_list.txt -i $e/mix.wav $in -filter_complex "$fc" \
  -map "[v]" -map 1:a -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart out/${e}_final_v3.mp4 \
  && echo "$(date +%T) $e FINAL V3 DONE" || echo "$(date +%T) $e FINAL V3 FAILED"
