#!/bin/zsh
# spot_loop.sh <name>: retry launch.sh every 5 s for a g6e.xlarge in REGIONS (default us-east-1) (spot first; ONDEMAND=1 adds on-demand fallback) until granted.
N=$1; LOG=/Users/samarpit/insta-automation/letsbuildsimply/ops/boxes/launch_$N.log; n=0
while true; do n=$((n+1)); echo "--- try $n $(date +%T)"
  SPOT_ONLY=$([[ -n $ONDEMAND ]] || echo 1) REGION=${REGIONS:-us-east-1} TYPES=g6e.xlarge /Users/samarpit/insta-automation/letsbuildsimply/ops/launch.sh $N 2>&1 | tee -a $LOG
  grep -q READY $LOG && { echo "BOX READY $N"; break; }
  grep -q '^GOT' $LOG && { echo "GOT box but setup did not finish"; break; }
  sleep 5; done
