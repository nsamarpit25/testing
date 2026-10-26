#!/bin/zsh
# finish_box.sh: AWS-only finish on the Mumbai box ep4g6e. Waits for its three render jobs (421-779, 321-420, 1061-1110),
# merges all 1111 frames (0-320 and 780-1060 arrive as jpg), mixes, overlays, copies the results back, terminates the box.
set -e; X=ep4g6e; D=~/insta-automation/letsbuildsimply/ops/boxes/$X; B=$D/ssh_config; O=~/insta-automation/letsbuildsimply-v2/ep4/output
until ssh -F $B $X 'cat ~/ep4/final_421.log ~/ep4/final_b_321.log ~/ep4/final_c_1061.log 2>/dev/null | grep -c FRAMES_DONE' | grep -qx 3; do
  ssh -F $B $X 'cat ~/ep4/final_*.log | grep -qE "Traceback|Error:"' && { echo RENDER_ERROR; exit 1; }; sleep 20; done
ssh -F $B $X 'cd ~/ep4 && mv final_b/frames/f_*.png final_c/frames/f_*.png final/frames/ && n=$(ls final/frames | sed "s/\.[a-z]*$//" | sort -u | wc -l) && echo frames $n && [ $n -eq 1111 ] \
 && cd scripts && ~/wv/bin/python mix.py --voice ../voice/narration.wav --events ../final/events.json --out ../final/mix.wav \
 && ~/wv/bin/python overlay.py --frames ../final/frames --labels ../final/labels.json --words ../voice/narration.words.json --events ../final/events.json --audio ../final/mix.wav --out ../final/final_video.mp4 --srt ../final/subtitles.srt --capvar A --crf 17'
scp -q -F $B ${X}:ep4/final/final_video.mp4 ${X}:ep4/final/subtitles.srt ${X}:ep4/final/mix.wav $O/
ls -la $O/final_video.mp4
set -a; source ~/insta-automation/.env; set +a; unset AWS_PROFILE
aws ec2 terminate-instances --region $(cat $D/region) --instance-ids $(cat $D/iid) --query 'TerminatingInstances[0].CurrentState.Name' --output text
echo FINISH_OK
