#!/bin/zsh
# usage: final_review.sh <mp4> <timings.json> <name> → frames every 1s (timestamped) in sheets of 12, timed transcript, Codex verdict in $SP/fr_<name>.txt
set -e
SP=${SP:-$HOME/insta-automation/how-its-engineered/tools/remake/out}; mkdir -p $SP
V=$1; TJ=$2; N=$3; O=$SP/fr/$N; rm -rf $O; mkdir -p $O
ffmpeg -v error -y -i $V -vf "fps=1,scale=300:-1" $O/f_%03d.png
python3 - $O <<'PY'
import sys, glob
from PIL import Image, ImageDraw, ImageFont
fs = sorted(glob.glob(sys.argv[1] + '/f_*.png')); font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 20)
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB'); d = ImageDraw.Draw(im); d.rectangle([4, 4, 70, 30], fill=(0, 0, 0)); d.text((8, 6), f'{i}s', fill=(255, 230, 0), font=font); im.save(f)
for s in range(0, len(fs), 12):
    ims = [Image.open(f) for f in fs[s:s + 12]]; w, h = ims[0].size
    sh = Image.new('RGB', (6 * w + 20, 2 * h + 4), (40, 40, 40))
    for k, im in enumerate(ims): sh.paste(im, ((k % 6) * (w + 4), (k // 6) * (h + 4)))
    sh.save(f'{sys.argv[1]}/sheet_{s // 12}.png')
PY
s=$(ls $O/sheet_*.png | wc -l | tr -d ' ')
IMGS=(); for f in $O/sheet_*.png; do IMGS+=(-i $f); done
{ cat <<P
You are doing the FINAL pre-upload review of a complete Instagram reel for @how.its.engineered (system design for complete beginners and "vibe coders"). Attached are $s contact sheets covering the WHOLE video: one frame per second, timestamp in the yellow box, left to right, top to bottom, sheets in order. Below is the voiceover with timings.
Judge the finished video as a viewer would: (1) is each idea shown clearly at the moment it is said, (2) is anything confusing, misleading, cluttered, unreadable, overlapping or cut off at the frame edge, (3) do on-screen text and captions match the voiceover, (4) is anything factually wrong, (5) is the opening strong enough to stop the scroll. Ignore the intentional dark glowing-orange 3D art style. Small transitional frames (objects mid-animation) are fine.
Reply with VERDICT: PASS (good to upload) or FIX, then at most 5 numbered concrete issues (timestamp, what is wrong, the specific fix). Only say FIX for problems that genuinely hurt a beginner's understanding or look broken; minor polish is not FIX.
P
python3 -c "import json,sys;[print(f\"{t['start']:5.1f}-{t['end']:5.1f}  {t['say']}\") for t in json.load(open(sys.argv[1]))]" $TJ; } > $O/prompt.txt
/Users/samarpit/.local/bin/codex exec --skip-git-repo-check --ephemeral -s read-only "${IMGS[@]}" -o $SP/fr_$N.txt - < $O/prompt.txt >/dev/null 2>&1
cat $SP/fr_$N.txt
