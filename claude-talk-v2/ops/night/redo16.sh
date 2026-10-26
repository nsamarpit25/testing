#!/bin/bash
# n2: after its Ep15 piece, re-render the Ep16 shots that changed (DOC framing, line 3/5/8/9/11/12 fixes) and re-encode Ep16
cd ~/ctv2
while ! grep -q "SEG 1-1250" run2.log; do sleep 15; done
[ -f out/ep16_final_v1.mp4 ] || mv out/ep16_final.mp4 out/ep16_final_v1.mp4
for r in 243-609 692-768 1117-2149; do for f in $(seq ${r%-*} ${r#*-}); do rm -f out/ep16/frames/f_$(printf %04d $f).png; done; done
echo "$(date +%T) changed frames removed: $(ls out/ep16/frames | wc -l) kept"
bash aws_run.sh ep16
