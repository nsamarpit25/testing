#!/usr/bin/env bash
# Voice every missing ep2 line with the one TTS model; when the daily quota is gone, wait and try again (it resets at
# midnight Pacific). Stops once all 17 clips exist.
cd "$(dirname "$0")/.."
eval "$(grep -E '^export GEMINI_API_KEY(_2|_3|_4)?=' ~/.zshrc)"
while [ "$(ls audio/ep2/l??.wav 2>/dev/null | wc -l)" -lt 17 ]; do
  python3 scripts/ep2_tts.py 2>&1 | grep -vE "^\s+key[0-9] .*out of daily quota"
  [ "$(ls audio/ep2/l??.wav 2>/dev/null | wc -l)" -ge 17 ] && break
  echo "$(date +%T) $(ls audio/ep2/l??.wav | wc -l)/17 voiced, waiting for quota"
  sleep 1200
done
echo "$(date +%T) ALL VOICED"
