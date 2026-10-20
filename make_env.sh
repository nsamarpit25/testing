#!/bin/zsh
# Collect every key on this Mac into ~/insta-automation/.env (git-ignored, only you can read it).
# Prints names only, never values. Then moves the Gemini keys out of ~/.zshrc (it loads .env instead)
# and copies the whole .env to the clipboard so you can paste it into another Claude Code.
#   zsh ~/insta-automation/make_env.sh
OUT=~/insta-automation/.env
umask 077
tmp=$(mktemp)

add() { [ -n "$2" ] && print -r -- "$1=$2" >> $tmp && echo "  $1"; }

echo "Instagram:"
source ~/.instagram_tokens
for v in IG_TALKINGAGENTS_ID IG_TALKINGAGENTS_TOKEN IG_HOWITSENGINEERED_ID IG_HOWITSENGINEERED_TOKEN; do add $v "${(P)v}"; done

echo "Gemini:"
typeset -U keys
for line in ${(f)"$(grep -E '^export GEMINI_API_KEY' ~/.zshrc)"}; do keys+=("$(eval "${line#export }"; print -r -- ${(P)${${line#export }%%=*}})"); done
i=1; for k in $keys; do [ -n "$k" ] || continue; add "GEMINI_API_KEY$([ $i -gt 1 ] && echo _$i)" "$k"; i=$((i+1)); done

echo "AWS:"
# Permanent keys only: the default profile (S3), plus the insta-automation IAM key already in .env, if any.
# The manmeet `aws login` keys expire within hours, so they are not exported.
for l in ${(f)"$(aws configure export-credentials --profile default --format env-no-export 2>/dev/null)"}; do add "AWS_S3${${l%%=*}#AWS}" "${l#*=}"; done
if grep -q '^AWS_ACCESS_KEY_ID=AKIA' $OUT 2>/dev/null; then  # AKIA = permanent key, ASIA = temporary
  for v in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY; do add $v "$(grep "^$v=" $OUT | cut -d= -f2-)"; done
fi
add AWS_DEFAULT_REGION ap-south-1

echo "Google Cloud:"
ADC=~/.config/gcloud/application_default_credentials.json
if [ -f $ADC ]; then
  add GOOGLE_ADC_JSON_B64 "$(base64 < $ADC | tr -d '\n')"
  add GOOGLE_CLOUD_PROJECT "$(python3 -c "import json;print(json.load(open('$ADC')).get('quota_project_id',''))")"
fi

mv $tmp $OUT && chmod 600 $OUT
echo "Wrote $OUT ($(grep -c = $OUT) values)"

# Gemini keys now live in .env: drop them from ~/.zshrc and load .env there instead.
if grep -q '^GEMINI_API_KEY=' $OUT && grep -qE '^export GEMINI_API_KEY' ~/.zshrc; then
  sed -i '' '/^export GEMINI_API_KEY/d' ~/.zshrc
  grep -q 'insta-automation/.env' ~/.zshrc || print '[ -f ~/insta-automation/.env ] && { set -a; source ~/insta-automation/.env; set +a; }' >> ~/.zshrc
  echo "Removed Gemini keys from ~/.zshrc (it now loads $OUT)"
fi

pbcopy < $OUT && echo "Copied .env to the clipboard"
