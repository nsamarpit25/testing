#!/bin/zsh
# Posts Ep14, 15, 16, 17 to @talkingagents in order, each at least 5 h after the newest post on the account
# (checked live before every upload). Each upload goes through ops/epNN_hold/post_once.sh, so only the approved md5 posts.
# Stop it: touch ops/night/QUEUE_CANCEL. Log: ops/night/queue_5h.log. Any failure stops the queue.
C=/Users/samarpit/insta-automation/claude-talk-v2; N=$C/ops/night; LOG=$N/queue_5h.log; GAP=18000
for ep in 14 15 16 17; do
  H=$C/ops/ep${ep}_hold
  [[ -f $H/DONE ]] && { echo "$(date '+%F %T') ep$ep already posted, skipping" >> $LOG; continue; }
  while true; do
    [[ -f $N/QUEUE_CANCEL ]] && { echo "$(date '+%F %T') QUEUE_CANCEL found, stopping before ep$ep" >> $LOG; exit 0; }
    if ! last=$(python3 $N/last_post.py 2>>$LOG); then sleep 300; continue; fi
    due=$(( ${last%% *} + GAP )); now=$(date +%s)
    (( now >= due )) && break
    echo "$(date '+%F %T') ep$ep next; newest post ${last#* } at $(date -r ${last%% *} '+%H:%M'), due $(date -r $due '+%F %H:%M')" >> $LOG
    s=$(( due - now )); (( s > 900 )) && s=900; sleep $(( s + 30 ))   # re-check at least every 15 min
  done
  echo "$(date '+%F %T') ep$ep posting (newest post ${last#* } is $(( (now - ${last%% *}) / 60 )) min old)" >> $LOG
  zsh $H/post_once.sh "$(date '+%Y-%m-%d %H:%M')"
  if [[ -f $H/DONE ]]; then
    link=$(grep -o 'https://www.instagram.com/reel/[^ ]*' $H/post.log | tail -1)
    echo "$(date '+%F %T') ep$ep OK $link" >> $LOG
    python3 $N/after_post.py posted $ep $link >> $LOG 2>&1
    (set -a; source ~/.instagram_tokens; set +a; python3 /Users/samarpit/insta-automation/insights/build_tracker.py >> $LOG 2>&1) \
      && touch $N/TRACKER_NEEDS_PUBLISH && echo "$(date '+%F %T') tracker rebuilt (needs republish)" >> $LOG
  else
    echo "$(date '+%F %T') ep$ep FAILED or blocked, queue stopped; see $H/post.log" >> $LOG; exit 1
  fi
done
echo "$(date '+%F %T') queue finished" >> $LOG
