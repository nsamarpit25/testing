#!/bin/zsh
# usage: post_at.sh <dir> <HH:MM IST> [trial|live]  → waits until that IST time (rolls to tomorrow if already past; or pass "YYYY-MM-DD HH:MM"), then posts media/<dir> (default: auto trial reel)
D=$1
MODE=${3:-trial}; TRIAL=(--trial auto); [[ $MODE == live ]] && TRIAL=()
# $2 is "HH:MM" (today, or tomorrow if that time has already passed) or "YYYY-MM-DD HH:MM"
if [[ $2 == *-*-*' '* ]]; then WHEN=$2; else WHEN="$(TZ=Asia/Kolkata date +%Y-%m-%d) $2"; fi
target=$(TZ=Asia/Kolkata date -j -f "%Y-%m-%d %H:%M" "$WHEN" +%s) || { echo "bad time: $2"; exit 1; }
now=$(date +%s)
if (( target <= now )); then
  [[ $2 == *-*-*' '* ]] && { echo "time already passed: $2 — not posting"; exit 1; }
  target=$(( target + 86400 ))
fi
echo "posting $D ($MODE) at $(TZ=Asia/Kolkata date -r $target '+%Y-%m-%d %H:%M IST')"
sleep $(( target - now ))
cd /Users/samarpit/insta-automation/how-its-engineered
set -a; source ../.env; set +a; source ~/.instagram_tokens
M=media/$D
TZ=Asia/Kolkata date; echo "mode: $MODE"
python3 -I tools/ig.py post $M/$D.mp4 --cover $M/cover.png --caption $M/caption.txt $TRIAL --yes 2>&1 | sed -E 's/(X-Amz-[A-Za-z]+=)[^& ]*/\1REDACTED/g'
echo "--- bucket:"
aws --region ap-south-1 s3 ls s3://hie-reel-staging-30c239/ 2>&1
echo "--- done"
