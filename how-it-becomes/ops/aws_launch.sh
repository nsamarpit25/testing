#!/bin/zsh
# Launch a g6e.xlarge (L40S) for how-it-becomes renders: Mumbai then Virginia, retry on capacity, install Blender 5.2.2 + ffmpeg. Self-terminates after 4 h.
# State: $ST/{iid,region,ip}; ssh config $ST/ssh_config (Host hib)
ST=${ST:-/private/tmp/claude-501/-Users-samarpit-insta-automation/fae067fe-af78-4a1b-aeb4-0354ce3a47ae/scratchpad/aws}; mkdir -p $ST; C=$ST/ssh_config
export AWS_PROFILE=manmeet
typeset -A SG AM; SG[ap-south-1]=sg-018e981a45e15e25b; SG[us-east-1]=sg-03fe01f82969e513d
for reg in ap-south-1 us-east-1; do AM[$reg]=$(aws ec2 describe-images --region $reg --owners amazon --filters "Name=name,Values=Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*" "Name=state,Values=available" --query "sort_by(Images,&CreationDate)[-1].ImageId" --output text); done
ip=$(curl -s https://checkip.amazonaws.com)
for reg in ap-south-1 us-east-1; do aws ec2 authorize-security-group-ingress --region $reg --group-id $SG[$reg] --protocol tcp --port 22 --cidr $ip/32 >/dev/null 2>&1; done
rm -f $ST/iid; end=$(( $(date +%s) + 7200 ))
while (( $(date +%s) < end )); do
 for reg in ap-south-1 us-east-1; do
  AMI=$AM[$reg]
  out=$(aws ec2 run-instances --region $reg --image-id $AMI --instance-type g6e.xlarge --key-name ctv2-bench --security-group-ids $SG[$reg] \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=80,VolumeType=gp3,DeleteOnTermination=true}' --instance-initiated-shutdown-behavior terminate \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=hib-render}]' --query 'Instances[0].InstanceId' --output text 2>&1)
  case $out in i-*) echo $out > $ST/iid; echo $reg > $ST/region; export AWS_REGION=$reg; echo "GOT g6e.xlarge $reg $out $(date +%T)"; break 2;; *) echo "$(date +%T) $reg $(echo $out | tail -c 200)";; esac
 done
 sleep 10
done
[ -s $ST/iid ] || { echo "NO CAPACITY"; exit 1; }
aws ec2 wait instance-running --instance-ids $(cat $ST/iid)
aws ec2 describe-instances --instance-ids $(cat $ST/iid) --query 'Reservations[0].Instances[0].PublicIpAddress' --output text > $ST/ip
printf "Host hib\n  HostName %s\n  User ubuntu\n  IdentityFile ~/.ssh/ctv2-bench.pem\n  StrictHostKeyChecking accept-new\n  UserKnownHostsFile %s/known_hosts\n  ServerAliveInterval 30\n" $(cat $ST/ip) $ST > $C
for i in $(seq 1 60); do ssh -F $C -o ConnectTimeout=5 hib true 2>/dev/null && break; sleep 5; done
ssh -F $C hib 'sudo shutdown -h +240 >/dev/null 2>&1
(sudo apt-get -qq update && sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y ffmpeg libegl1 libgl1 libxkbcommon0 libsm6 libxi6 libxrender1 libxxf86vm1 libxfixes3 libxkbcommon-x11-0 >/dev/null 2>&1) &
U=https://mirrors.ocf.berkeley.edu/blender/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz
N=$(curl -sIL -A "Mozilla/5.0" $U | grep -i "^content-length" | tail -1 | tr -dc 0-9); P=10; ch=$(( (N + P - 1) / P ))
for i in $(seq 0 $((P-1))); do a=$((i*ch)); b=$((a+ch-1)); curl -sL -A "Mozilla/5.0" -r $a-$b -o part$i $U & done; wait
cat $(for i in $(seq 0 $((P-1))); do echo part$i; done) > b.tar.xz; rm part*; tar xJf b.tar.xz; rm b.tar.xz; wait; ./blender-5.2.2-linux-x64/blender --version | head -1; nvidia-smi --query-gpu=name --format=csv,noheader; which ffmpeg'
echo "READY $(date +%T)"
