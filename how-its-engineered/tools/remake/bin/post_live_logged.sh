#!/bin/zsh
# usage: post_live_logged.sh <dir> "YYYY-MM-DD HH:MM" "<topic>" <kind>  → post_at.sh live, then add the registry row
cd /Users/samarpit/insta-automation/how-its-engineered
D=$1; WHEN=$2; TOPIC=$3; KIND=${4:-new}
out=$(zsh tools/remake/bin/post_at.sh $D "$WHEN" live 2>&1); echo "$out"
code=$(echo "$out" | grep -o 'reel/[A-Za-z0-9_-]*' | tail -1 | cut -d/ -f2)
[[ -z $code ]] && { echo "FAILED $D"; exit 1; }
python3 - "$code" "$TOPIC" "$KIND" "$D" "$(md5 -q media/$D/$D.mp4)" "$(TZ=Asia/Kolkata date '+%d %b %H:%M')" <<'PY'
import json,sys
code,topic,kind,d,md5,t=sys.argv[1:]
p='../insights/hie-reels.json'; j=json.load(open(p))
j['reels'].append({"code":code,"topic":topic,"kind":kind,"dir":d,"note":f"{topic}, live {t} IST on Sam's OK. md5 {md5}."})
json.dump(j,open(p,'w'),indent=1,ensure_ascii=False)
PY
echo "logged $code"
