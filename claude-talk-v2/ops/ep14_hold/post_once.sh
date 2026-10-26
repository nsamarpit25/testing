#!/bin/zsh
# One upload to @talkingagents at a set time: Ep14 "fetch confetti", the caption + cover in this folder.
# post_once.sh "2026-10-22 08:00"  -> log in this folder. Posts only the exact file whose md5 is in APPROVED_MD5.
H=${0:A:h}; R=/Users/samarpit/insta-automation; C=$R/claude-talk-v2
V=$C/output/new/ep14_final.mp4; CAP=$H/caption.txt; COV=$H/cover.jpg; LOG=$H/post.log
AT=$(date -j -f "%Y-%m-%d %H:%M" "$1" +%s)
echo "$(date '+%F %T') waiting until $1 IST for $V" >> $LOG
while (( $(date +%s) < AT )); do sleep 20; done
[[ -f $H/CANCEL ]] && { echo "$(date +%T) CANCEL file found, not posting" >> $LOG; exit 0; }
[[ $(md5 -q $V) == $(cat $H/APPROVED_MD5) ]] || { echo "$(date +%T) BLOCKED: video changed since approval" >> $LOG; exit 1; }
set -a; source $R/.env; set +a; unset AWS_PROFILE
sed 's/^TOKEN_FILE, TOKEN_VAR = .*/TOKEN_FILE, TOKEN_VAR = Path.home() \/ ".instagram_tokens", "IG_TALKINGAGENTS_TOKEN"/' $R/how-its-engineered/tools/ig.py > $H/ig_ta.py
grep -q '"IG_TALKINGAGENTS_TOKEN"' $H/ig_ta.py || { echo "$(date +%T) token swap failed" >> $LOG; exit 1; }
echo "$(date +%T) posting" >> $LOG
if python3 $H/ig_ta.py post $V --caption $CAP --cover $COV --yes >> $LOG 2>&1; then
  echo "$(date +%T) OK" >> $LOG; touch $H/DONE
else
  echo "$(date +%T) FAILED" >> $LOG; touch $H/FAILED
fi
