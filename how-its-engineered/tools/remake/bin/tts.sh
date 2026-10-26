#!/bin/zsh
# usage: tts.sh <dir>...  → voice + words.js, prints transcript and the end word
ADC=${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}
cd /Users/samarpit/insta-automation/how-its-engineered
set -a; source ../.env; set +a; export GOOGLE_APPLICATION_CREDENTIALS=$ADC
export TTS_STYLE="confident, energetic tech explainer narrating a short Instagram reel; natural and conversational, like talking to a friend; fast, punchy pace with short pauses between sentences"
for d in "$@"; do
  D=videos/$d
  "$HOME/Developer/how its enginereed/.venv-fish/bin/python" voice/gemini_tts.py $D/script.json $D/voice --voice Puck --vertex --tempo 1.15 2>&1 | tail -1
  (cd $D/voice && python3 -c "import json;print('window.TIMINGS='+json.dumps(json.load(open('timings.json')))+';\nwindow.WORDS='+json.dumps(json.load(open('words.json')))+';')" > words.js)
  echo "== $d"; python3 -c "import json;w=json.load(open('$D/voice/words.json'));print(' '.join(f'{x[0].strip()}@{x[1]:.1f}' for x in w))"
done
