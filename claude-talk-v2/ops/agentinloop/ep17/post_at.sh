#!/bin/zsh
# One timed upload to @agentinloop: ep17_agentinloop.mp4 with the caption + cover in this folder.
# post_at.sh "YYYY-MM-DD HH:MM" (IST). Touch CANCEL in this folder to stop it. Posts only the file whose md5 is in APPROVED_MD5.
H=${0:A:h}; R=/Users/samarpit/insta-automation
V=$H/ep17_agentinloop.mp4; CAP=$H/caption.txt; COV=$H/cover.jpg; LOG=$H/post.log
AT=$(date -j -f "%Y-%m-%d %H:%M" "$1" +%s)
echo "$(date '+%F %T') waiting until $1 IST" >> $LOG
while (( $(date +%s) < AT )); do sleep 20; [[ -f $H/CANCEL ]] && break; done
[[ -f $H/CANCEL ]] && { echo "$(date +%T) CANCEL file found, not posting" >> $LOG; exit 0; }
[[ -f $H/APPROVED_MD5 && $(md5 -q $V) == $(cat $H/APPROVED_MD5) ]] || { echo "$(date +%T) BLOCKED: not the approved file" >> $LOG; exit 1; }
set -a; source $R/.env; set +a; unset AWS_PROFILE
sed 's/^TOKEN_FILE, TOKEN_VAR = .*/TOKEN_FILE, TOKEN_VAR = Path("\/Users\/samarpit\/insta-automation\/.env"), "IG_AGENTINLOOP_TOKEN"/' $R/how-its-engineered/tools/ig.py > $H/ig_ail.py
grep -q '"IG_AGENTINLOOP_TOKEN"' $H/ig_ail.py || { echo "$(date +%T) token swap failed" >> $LOG; exit 1; }
echo "$(date +%T) posting" >> $LOG
if python3 $H/ig_ail.py post $V --caption $CAP --cover $COV --yes >> $LOG 2>&1; then
  echo "$(date +%T) OK" >> $LOG; touch $H/DONE
else
  echo "$(date +%T) FAILED" >> $LOG; touch $H/FAILED
fi
