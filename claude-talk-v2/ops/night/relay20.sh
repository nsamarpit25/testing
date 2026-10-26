#!/bin/zsh
# relay20.sh: copy n8's finished Ep20 tail frames to n9 every 30 s, until n9's full.sh reaches its final
cd /Users/samarpit/insta-automation/claude-talk-v2; T=/private/tmp/claude-501/-Users-samarpit-insta-automation/11b16e3a-d2d7-41c2-a928-cedbe92ac99f/scratchpad/f20h; mkdir -p $T
A8=(ssh -F $PWD/ops/night/n8/ssh_config); A9=(ssh -F $PWD/ops/night/n9/ssh_config)
while ! ssh -F ops/night/n9/ssh_config n9 'grep -q "frames" ~/ctv2/full_ep20.log'; do
  rsync -a --min-size=1 -e "$A8[*]" "n8:ctv2/f_ep20h/" $T/
  rsync -a --min-size=1 --ignore-existing -e "$A9[*]" $T/ "n9:ctv2/f_ep20/" 2>/dev/null
  rsync -a --min-size=1 -e "$A9[*]" --existing --size-only $T/ "n9:ctv2/f_ep20/" 2>/dev/null
  sleep 30
done
echo "$(date +%T) relay stop, $(ls $T | wc -l) frames relayed"
