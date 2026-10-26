#!/bin/zsh
# run.sh: rebuild "What If You Drilled Straight Through the Earth?" end to end.
# Heavy steps (Whisper, Blender bake/render, overlay encode) run on an AWS GPU box (letsbuildsimply/ops/launch.sh);
# TTS (Vertex Gemini, voice Puck) and the numpy audio mix are light and run locally.
set -e; cd "$(dirname "$0")"
python3 tts.py script.json take.wav --voice Puck                                    # 1. narration (one take)
python3 tighten.py take.wav narration.wav --cut <end of last word> --keep 1.9,16.2,23.9,30.9   # 2. trim long pauses + tail noise
# 3. on the box: ~/wv/bin/python whisper_words.py narration.wav  -> narration.words.json
# 4. on the box (L40S ~0.4 s/frame at 1080p, L4 ~4 s):
#    blender -b -P scene.py -- --words narration.words.json --out final --res 1080 --samples 24 --frames 0:1340 --save project.blend
#    preview: --res 480 --samples 16; test stills: --stills 1.0,13.6,31.3
python3 mix.py --voice narration.wav --events final/events.json --sfx ../../../letsbuildsimply/assets/sfx --out mix.wav   # 5. audio
# 6. on the box: python overlay.py --frames final/frames --labels final/labels.json --words narration.words.json --audio mix.wav --out final_video.mp4 --srt subtitles.srt --crf 16
