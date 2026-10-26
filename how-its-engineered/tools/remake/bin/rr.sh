#!/bin/zsh
# usage: rr.sh <dir> <review-name> → sync, render on PC, pull back to media/<dir>/, final review into tools/remake/out/fr_<dir>.txt
cd /Users/samarpit/insta-automation/how-its-engineered; D=$1; O=tools/remake/out; mkdir -p $O
rsync -a -e "ssh -i $HOME/.ssh/id_ed25519 -o BatchMode=yes" videos/$D sam@192.168.0.112:/mnt/ssd/hie/videos/
ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes sam@192.168.0.112 "bash /mnt/ssd/hie/render_pc.sh $D $D 10" 2>&1 | tail -1
mkdir -p media/$D; scp -q -i ~/.ssh/id_ed25519 sam@192.168.0.112:/mnt/ssd/hie/out/$D.mp4 media/$D/
zsh tools/remake/final_review.sh media/$D/$D.mp4 videos/$D/voice/timings.json $2 > $O/fr_$D.txt 2>&1
grep -A10 VERDICT $O/fr_$D.txt || echo "no VERDICT (review empty or failed) — rerun final_review.sh"
