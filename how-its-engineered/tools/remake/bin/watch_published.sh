#!/bin/zsh
# Exit when a new "published:" line shows up in any HIE post log, or after ~48 min (keep-alive).
L=/Users/samarpit/insta-automation/how-its-engineered/tools/remake/out
base=$(cat $L/post_*.log 2>/dev/null | grep -c "published:")
for i in {1..96}; do
  sleep 30
  now=$(cat $L/post_*.log 2>/dev/null | grep -c "published:")
  if [ "$now" -gt "$base" ]; then ls -t $L/post_*.log | head -3 | xargs grep -h "^published: https"; grep -lE "Error|Traceback|failed" $L/post_*.log 2>/dev/null; exit 0; fi
done
echo "keepalive $(date +%T)"; grep -liE "error|traceback" $L/post_*.log 2>/dev/null
