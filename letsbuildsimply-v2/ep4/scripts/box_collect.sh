#!/bin/zsh
# box_collect.sh: pull the Mumbai box's frames (421-779, 321-420) as jpg into the PC's final/frames, then terminate the box.
set -e; X=ep4g6e; D=~/insta-automation/letsbuildsimply/ops/boxes/$X; B=$D/ssh_config; T=~/insta-automation/letsbuildsimply-v2/ep4/build/final/box
ssh -F $B $X 'cd ~/ep4 && mkdir -p jpg && ls final/frames/f_*.png final_b/frames/f_*.png | xargs -P 8 -I{} sh -c "ffmpeg -v error -y -i {} -q:v 1 jpg/\$(basename {} .png).jpg" && ls jpg | wc -l'
mkdir -p $T; rsync -a -e "ssh -F $B" ${X}:ep4/jpg/ $T/; n=$(ls $T | wc -l); echo "box jpgs $n"; [ $n -eq 459 ]
rsync -a $T/ sam@192.168.0.115:/mnt/ssd/render/lbs-ep4/final/frames/
set -a; source ~/insta-automation/.env; set +a; unset AWS_PROFILE
aws ec2 terminate-instances --region $(cat $D/region) --instance-ids $(cat $D/iid) --query 'TerminatingInstances[0].CurrentState.Name' --output text
echo COLLECT_OK
