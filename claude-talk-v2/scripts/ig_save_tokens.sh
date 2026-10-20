#!/bin/zsh
# Save the Instagram API tokens for both accounts into ~/.instagram_tokens (only you can read it), then check each one works.
# Paste each token when asked (it isn't shown on screen). Press Enter on an empty prompt to keep the token already saved.
#   zsh scripts/ig_save_tokens.sh
F=~/.instagram_tokens
[ -f $F ] && source $F

typeset -A ID=(TALKINGAGENTS 17841417684477377 HOWITSENGINEERED 17841460018282599)
typeset -A NAME=(TALKINGAGENTS talkingagents HOWITSENGINEERED how.its.engineered)

for K in TALKINGAGENTS HOWITSENGINEERED; do
  read -rs "tok?Paste the token for @${NAME[$K]} (Enter to keep the saved one): "; echo
  [ -n "$tok" ] && typeset -g IG_${K}_TOKEN="$tok"
done

umask 077
cat > $F <<EOF
# Instagram API (app talkingagents-uploader). Long-lived tokens, valid 60 days from when they were made.
export IG_TALKINGAGENTS_ID=${ID[TALKINGAGENTS]}
export IG_TALKINGAGENTS_TOKEN="${IG_TALKINGAGENTS_TOKEN}"
export IG_HOWITSENGINEERED_ID=${ID[HOWITSENGINEERED]}
export IG_HOWITSENGINEERED_TOKEN="${IG_HOWITSENGINEERED_TOKEN}"
EOF
chmod 600 $F
echo "saved to $F"

for K in TALKINGAGENTS HOWITSENGINEERED; do
  T=${(P)${:-IG_${K}_TOKEN}}
  if [ -z "$T" ]; then echo "@${NAME[$K]}: no token yet"; continue; fi
  R=$(curl -s "https://graph.instagram.com/v23.0/me?fields=username,media_count" -H "Authorization: Bearer $T")
  if echo "$R" | grep -q '"username"'; then echo "@${NAME[$K]}: works ($R)"; else echo "@${NAME[$K]}: NOT working: $(echo $R | head -c 200)"; fi
done
