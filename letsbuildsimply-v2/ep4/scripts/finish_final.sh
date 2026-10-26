#!/bin/zsh
# finish_final.sh: all frames are on the PC (0-320 jpg from AWS, 321-1110 png). Merge, mix, overlay, copy back.
set -e; P=sam@192.168.0.115; R=/mnt/ssd/render/lbs-ep4; O=/Users/samarpit/insta-automation/letsbuildsimply-v2/ep4/output
scp -q overlay.py mix.py $P:$R/scripts/
ssh $P "cd $R && mv final_b/frames/f_*.png final/frames/ 2>/dev/null; n=\$(ls final/frames | sed 's/\.[a-z]*\$//' | sort -u | wc -l); echo frames \$n; [ \$n -eq 1111 ] || exit 3
cd scripts && ../venv/bin/python mix.py --voice ../voice/narration.wav --events ../final/events.json --out ../final/mix.wav \
 && ../venv/bin/python overlay.py --frames ../final/frames --labels ../final/labels.json --words ../voice/narration.words.json --events ../final/events.json --audio ../final/mix.wav --out ../final/final_video.mp4 --srt ../final/subtitles.srt --capvar A --crf 17"
scp -q $P:$R/final/final_video.mp4 $P:$R/final/subtitles.srt $P:$R/final/mix.wav $O/; echo FINISH_OK
