#!/bin/zsh
# One upload to @agentinloop: the trimmed ep6 ("trumpet button") with the caption + cover in this folder.
# post_once.sh  -> log in this folder. Posts only the exact file whose md5 is in APPROVED_MD5.
H=${0:A:h}; R=/Users/samarpit/insta-automation
V=$H/ep6_agentinloop.mp4; CAP=$H/caption.txt; COV=$H/cover.jpg; LOG=$H/post.log
[[ -f $H/APPROVED_MD5 && $(md5 -q $V) == $(cat $H/APPROVED_MD5) ]] || { echo "$(date +%T) BLOCKED: not the approved file" >> $LOG; exit 1; }
set -a; source $R/.env; set +a; unset AWS_PROFILE
sed 's/^TOKEN_FILE, TOKEN_VAR = .*/TOKEN_FILE, TOKEN_VAR = Path("\/Users\/samarpit\/insta-automation\/.env"), "IG_AGENTINLOOP_TOKEN"/' $R/how-its-engineered/tools/ig.py > $H/ig_ail.py
grep -q '"IG_AGENTINLOOP_TOKEN"' $H/ig_ail.py || { echo "$(date +%T) token swap failed" >> $LOG; exit 1; }
echo "$(date '+%F %T') posting" >> $LOG
if python3 $H/ig_ail.py post $V --caption $CAP --cover $COV --yes >> $LOG 2>&1; then
  echo "$(date +%T) OK" >> $LOG; touch $H/DONE
else
  echo "$(date +%T) FAILED" >> $LOG; touch $H/FAILED
fi
