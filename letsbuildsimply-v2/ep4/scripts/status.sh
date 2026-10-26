#!/bin/zsh
# status.sh: one-line progress of the 1080p render. Frames 0-320: old AWS box (jpg, already on the PC).
# PC renders 780-1110 (final); the Mumbai g6e box ep4g6e renders 421-779 (final) then 321-420 (final_b).
p=$(ssh -o BatchMode=yes -o ConnectTimeout=8 sam@192.168.0.115 'cd /mnt/ssd/render/lbs-ep4; ls final/frames/f_*.png 2>/dev/null | wc -l; grep -cE "Traceback|Error:" final_780.log; grep -c FRAMES_DONE final_780.log' 2>/dev/null | tr '\n' ' ')
b=$(ssh -F ~/insta-automation/letsbuildsimply/ops/boxes/ep4g6e/ssh_config -o ConnectTimeout=8 ep4g6e 'cd ~/ep4; ls final/frames/f_*.png 2>/dev/null | wc -l; ls final_b/frames/f_*.png 2>/dev/null | wc -l; cat final_421.log final_b_321.log 2>/dev/null | grep -cE "Traceback|Error:"; cat final_421.log final_b_321.log 2>/dev/null | grep -c FRAMES_DONE' 2>/dev/null | tr '\n' ' ')
echo "$(date +%H:%M) PC 780-1110 [frames errors done]: ${p:-UNREACHABLE}/331 | box [421-779 321-420 errors done]: ${b:-UNREACHABLE}(/359 /100, done=2)"
