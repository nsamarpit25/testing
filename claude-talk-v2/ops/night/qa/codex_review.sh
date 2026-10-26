#!/bin/zsh
# codex_review.sh <name> <video> <audio dir> "<premise>"  -> ops/night/qa/codex/<name>/reply.md
# Codex can't take video: the whole reel goes as 2 fps contact sheets (time-labelled) plus the timed dialogue.
cd /Users/samarpit/insta-automation/claude-talk-v2
o=ops/night/qa/codex/$1; rm -rf $o; mkdir -p $o
ffmpeg -v error -i $2 -vf "fps=2,scale=270:480,drawbox=x=0:y=0:w=62:h=26:color=black@0.7:t=fill" -f image2 $o/f_%04d.png
python3 - $o $3 <<'EOF'
import json, glob, sys
from PIL import Image, ImageDraw
o, d = sys.argv[1], sys.argv[2]
fs = sorted(glob.glob(f"{o}/f_*.png"))
for s in range(0, len(fs), 24):  # 8x3 sheets
    sh = Image.new("RGB", (270 * 8, 480 * 3))
    for i, f in enumerate(fs[s:s + 24]):
        im = Image.open(f); ImageDraw.Draw(im).text((4, 6), f"{(s + i) / 2:.1f}s", fill=(255, 230, 0))
        sh.paste(im, ((i % 8) * 270, (i // 8) * 480))
    sh.save(f"{o}/sheet_{s // 24 + 1:02d}.jpg", quality=88)
t = json.load(open(f"{d}/timeline.json"))
open(f"{o}/dialogue.txt", "w").write("\n".join(f"{x['t0']:.1f}-{x['t1']:.1f}s {x['who'].capitalize()}: {x['text']}" for x in t["lines"]))
EOF
rm -f $o/f_*.png
cat > $o/brief.md <<B
You are the final reviewer for a vertical Instagram reel (1080x1920) on @talkingagents: a short 3D comedy where Cleo, a junior developer, talks to Claude, a small orange AI companion on her desk. The attached sheets are the COMPLETE video at 2 frames/second (yellow label = time in seconds), with burned-in word-by-word captions. Timed dialogue:

$(cat $o/dialogue.txt)

Premise: $4

Review the whole video for anything that would hurt it on Instagram or look broken: wrong or missing captions vs dialogue, captions overlapping important content, unreadable, cropped or wrong screen content, screens that contradict the dialogue, shots that are too short (flash cuts), a character facing the wrong way, visual glitches, a weak opening (no hook TEXT overlay is allowed in the first scene; dialogue captions are fine), the ending (fade to black is intended), and whether the joke lands.
Allowed by the channel owner, not issues: the small "@talkingagents" handle near the bottom on every frame; Cleo's hair falling over one eye (her design); a short silent beat before the first line; the blurred background in Claude's to-camera shots (shallow depth of field).

Reply with a short list of concrete issues (time, what, fix) ranked by severity, then a final line exactly "VERDICT: PASS" (good to upload as is, minor nits only) or "VERDICT: FAIL" (must fix first).
B
codex exec --skip-git-repo-check -s read-only -c model_reasoning_effort="high" $(for f in $o/sheet_*.jpg; do echo -i $f; done) -o $o/reply.md - < $o/brief.md > $o/log.txt 2>&1
echo "== $1"; cat $o/reply.md
