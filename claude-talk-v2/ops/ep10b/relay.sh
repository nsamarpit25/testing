#!/bin/zsh
# copy AWS's finished frames to the PC every 20 s (empty files are claims, never copied); stop after AWS is done
while true; do
  d=$(ssh -F /Users/samarpit/insta-automation/claude-talk-v2/ops/ep10b/aws_ssh_config aws10 'test -e ~/ctv2/DONE && echo done')
  rsync -a --min-size=1 -e "ssh -F /Users/samarpit/insta-automation/claude-talk-v2/ops/ep10b/aws_ssh_config" aws10:ctv2/out/frames/ /Users/samarpit/insta-automation/claude-talk-v2/ops/ep10b/awsframes/ 2>/dev/null
  rsync -a --min-size=1 --ignore-existing /Users/samarpit/insta-automation/claude-talk-v2/ops/ep10b/awsframes/ sam@192.168.0.112:ctv2_ep10b/out/frames/ 2>/dev/null
  echo "$(date +%T) relayed $(ls /Users/samarpit/insta-automation/claude-talk-v2/ops/ep10b/awsframes | wc -l)"
  [ "$d" = done ] && break
  sleep 20
done
