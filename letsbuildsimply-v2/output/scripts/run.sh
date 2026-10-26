#!/bin/zsh
# run.sh: rebuild "How to Move a 100-Ton Rock Without a Crane" end to end.
# Heavy steps (Blender bake/render, whisper, overlay encode) run on the AWS render box (ssh alias in $BOX_SSH);
# TTS (Vertex Gemini, voice Puck) and the numpy audio mix run locally.
set -e
cd "$(dirname "$0")"; OUT=..; BOX=${BOX:-fridge}; SSH="ssh -F ${BOX_SSH:?set BOX_SSH to the box ssh_config} $BOX"; SCP="scp -q -F $BOX_SSH"
python3 tts.py script.json narration.wav --voice Puck                                   # 1. narration
$SCP narration.wav whisper_words.py $BOX:lbs/rock/voice/ 2>/dev/null || true
# 2. word timings (faster-whisper large-v3 on the box) -> narration.words.json
# 3. scene + frames (two halves in parallel on the L4; ~11 min for 1695 frames at 1080x1920, Eevee 24 samples)
#    blender -b -P scene.py -- --words narration.words.json --out final --res 1080 --samples 24 --frames 0:847 --save project.blend
#    blender -b -P scene.py -- --words narration.words.json --out finalB --res 1080 --samples 24 --frames 848:1694
#    quick test stills: --res 360 --samples 8 --stills 1.0,13.6,22.3,40.0
python3 mix.py --voice narration.wav --events final/events.json --sfx ../../../letsbuildsimply/assets/sfx --out mix.wav   # 4. audio
# 5. captions + labels + encode:
#    python3 overlay.py --frames final/frames --labels final/labels.json --words narration.words.json --audio mix.wav --out final_video.mp4 --srt subtitles.srt
#    python3 overlay.py --frames final/frames --labels final/labels.json --words narration.words.json --thumb 50.6 --thumb-out thumbnail.png
