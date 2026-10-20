#!/bin/zsh
# Launch a g6e.xlarge (L40S) for ep4, trying Mumbai then Virginia, retrying on capacity errors, then install Blender. Auto-shutdown (terminate) after 4 h.
S=/private/tmp/claude-501/-Users-samarpit-claude-talk-v2/8b4ae08d-047d-4694-a2eb-0d4d38b02b4a/scratchpad; C=$S/aws/ssh_config
export AWS_PROFILE=manmeet
ip=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress --region ap-south-1 --group-id $(cat $S/mum/sg) --protocol tcp --port 22 --cidr $ip/32 >/dev/null 2>&1 && echo "Mumbai SG opened for $ip"
aws ec2 authorize-security-group-ingress --region us-east-1 --group-id $(cat $S/aws/sg) --protocol tcp --port 22 --cidr $ip/32 >/dev/null 2>&1 && echo "Virginia SG opened for $ip"
rm -f $S/aws/iid; end=$(( $(date +%s) + 21600 ))
while (( $(date +%s) < end )); do
 for reg in ap-south-1 us-east-1; do
  if [ $reg = us-east-1 ]; then AMI=ami-028357be7d5b15c53; SG=$(cat $S/aws/sg); else AMI=$(cut -f1 $S/mum/ami); SG=$(cat $S/mum/sg); fi
  out=$(aws ec2 run-instances --region $reg --image-id $AMI --instance-type g6e.xlarge --key-name ctv2-bench --security-group-ids $SG \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=80,VolumeType=gp3,DeleteOnTermination=true}' --instance-initiated-shutdown-behavior terminate \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ctv2-ep4}]' --query 'Instances[0].InstanceId' --output text 2>&1)
  case $out in i-*) echo $out > $S/aws/iid; echo $reg > $S/aws/region; export AWS_REGION=$reg; echo "GOT g6e.xlarge $reg $out $(date +%T)"; break 2;; *) echo "$(date +%T) $reg $(echo $out | grep -oE '\(\w+\)' | head -1)";; esac
 done
 sleep 10
done
[ -s $S/aws/iid ] || { echo "NO CAPACITY"; exit 1; }
aws ec2 wait instance-running --instance-ids $(cat $S/aws/iid)
aws ec2 describe-instances --instance-ids $(cat $S/aws/iid) --query 'Reservations[0].Instances[0].PublicIpAddress' --output text > $S/aws/ip
sed -i '' "s/HostName .*/HostName $(cat $S/aws/ip)/" $C; : > $S/aws/known_hosts
for i in $(seq 1 40); do ssh -F $C -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 aws true 2>/dev/null && break; sleep 5; done
ssh -F $C aws 'sudo shutdown -h +240 >/dev/null 2>&1
(sudo apt-get -qq update && sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y ffmpeg libegl1 libgl1 libxkbcommon0 libsm6 libxi6 libxrender1 libxxf86vm1 libxfixes3 libxkbcommon-x11-0 >/dev/null 2>&1) &
U=https://mirrors.ocf.berkeley.edu/blender/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz
N=383295504; P=10; ch=$(( (N + P - 1) / P ))
for i in $(seq 0 $((P-1))); do a=$((i*ch)); b=$((a+ch-1)); curl -sL -A "Mozilla/5.0" -r $a-$b -o part$i $U & done; wait
cat $(for i in $(seq 0 $((P-1))); do echo part$i; done) > b.tar.xz; rm part*; tar xJf b.tar.xz; wait; ./blender-5.2.2-linux-x64/blender --version | head -1; nvidia-smi --query-gpu=name --format=csv,noheader; which ffmpeg'
echo "READY $(date +%T)"
