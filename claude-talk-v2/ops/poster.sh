#!/bin/zsh
# Post queued reels to @talkingagents one at a time, 2-3 h apart (random). Only files approved by review + cutcheck ($S/passed/<md5>) post. Queue items: $Q/<NN_name>/{video.mp4,caption.txt,cover.jpg,READY}
S=/private/tmp/claude-501/-Users-samarpit-insta-automation/090cc81c-2b8e-489f-b1db-92f85c47225e/scratchpad
set -a; source /Users/samarpit/insta-automation/.env; set +a; unset AWS_PROFILE
Q=$S/queue; D=$S/posted; LOG=$S/poster.log; IG=/Users/samarpit/insta-automation/how-its-engineered/tools/ig.py
STOP_AT=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-22 01:00" +%s)
last=$(cat $S/last_post 2>/dev/null || echo 0)
while (( $(date +%s) < STOP_AT )); do
  next=$(ls $Q 2>/dev/null | sort | head -1)
  [[ -z $next && ! -f $S/QUEUE_CLOSED ]] && { sleep 60; continue; }
  [[ -z $next ]] && { echo "$(date +%T) queue empty, done; staged files left in S3: $(aws s3 ls s3://hie-reel-staging-30c239/ --region ap-south-1 | grep -cE "[0-9]+-(video.mp4|cover.jpg)$")" >> $LOG; exit 0; }
  gap=$(cat $S/next_gap 2>/dev/null || echo 0)
  if [[ -n $next && -f $Q/$next/READY && ! -f $S/passed/$(md5 -q $Q/$next/video.mp4) ]]; then
    echo "$(date +%T) BLOCKED $next: video.mp4 is not the file that passed review + cut check - poster stopping" >> $LOG; exit 1
  fi
  if [[ -n $next && -f $Q/$next/READY ]] && (( $(date +%s) - last >= gap )); then
    sed "s/^TOKEN_FILE, TOKEN_VAR = .*/TOKEN_FILE, TOKEN_VAR = Path.home() \/ \".instagram_tokens\", \"IG_TALKINGAGENTS_TOKEN\"/; s/^AWS = \[\"aws\", \"--profile\", PROFILE, /AWS = [\"aws\", /" $IG > $S/ig_ta.py
    grep -q '"IG_TALKINGAGENTS_TOKEN"' $S/ig_ta.py || { echo "$(date +%T) token swap failed" >> $LOG; exit 1; }
    echo "$(date +%T) posting $next" >> $LOG
    if python3 $S/ig_ta.py post $Q/$next/video.mp4 --caption $Q/$next/caption.txt $([[ -f $Q/$next/cover.jpg ]] && echo --cover $Q/$next/cover.jpg) --yes >> $LOG 2>&1; then
      last=$(date +%s); echo $last > $S/last_post
      echo $(( 7200 + RANDOM % 3601 )) > $S/next_gap   # 2-3 h between posts
      mv $Q/$next $D/; echo "$(date +%T) OK $next; next gap $(( $(cat $S/next_gap) / 60 )) min" >> $LOG
    else
      echo "$(date +%T) FAILED $next - poster stopping" >> $LOG; exit 1
    fi
  fi
  sleep 30
done
echo "$(date +%T) poster stopped" >> $LOG
