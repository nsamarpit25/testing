#!/bin/zsh
# usage: rr_mac.sh <dir> <review-name> [chunks] → render on THIS Mac (when the PC is down), into media/<dir>/, then the Codex final review
# Same steps as render_pc.sh + rr.sh, minus the ssh. Needs `npm ci` in how-its-engineered/ (playwright + fonts).
set -e
cd /Users/samarpit/insta-automation/how-its-engineered; D=$1; N=${3:-6}; O=tools/remake/out; TMP=tools/remake/out/tmp_$D
rm -rf $TMP; mkdir -p $O media/$D $TMP
DUR=$(node -e "const fs=require('fs');const s=fs.readFileSync('videos/$D/voice/words.js','utf8');const T=JSON.parse(s.match(/window.TIMINGS=(\[.*?\]);/s)[1]);console.log(T[T.length-1].end+1.8)")
for i in $(seq 0 $((N-1))); do
  A=$(python3 -c "print($DUR*$i/$N)"); B=$(python3 -c "print($DUR*($i+1)/$N)")
  node tools/render.mjs videos/$D/video.html $TMP/c$i.mp4 --from $A --to $B > $TMP/log$i.txt 2>&1 &
done
wait
grep -h -i 'error' $TMP/log*.txt | head -5 || true
for i in $(seq 0 $((N-1))); do echo "file 'c$i.mp4'"; done > $TMP/list.txt
ffmpeg -v error -y -f concat -safe 0 -i $TMP/list.txt -i videos/$D/voice/voice.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart media/$D/$D.mp4
rm -rf $TMP
ffprobe -v error -show_entries format=duration -of csv=p=0 media/$D/$D.mp4
zsh tools/remake/final_review.sh media/$D/$D.mp4 videos/$D/voice/timings.json $2 > $O/fr_$D.txt 2>&1 || true
grep -A10 VERDICT $O/fr_$D.txt || echo "no VERDICT (review empty or failed) — rerun final_review.sh"
