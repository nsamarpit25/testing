#!/bin/zsh
# HIE AirTag B: launch a CPU box in Mumbai, install node + playwright chromium + ffmpeg. Safety: it terminates itself after 4 h.
L=/Users/samarpit/insta-automation/how-its-engineered/tools/remake/out/aws; mkdir -p $L
set -a; source /Users/samarpit/insta-automation/.env; set +a; unset AWS_PROFILE; export AWS_REGION=ap-south-1
rm -f $L/iid
for t in c7i.16xlarge c6i.16xlarge c7i.12xlarge c7i.8xlarge c6i.8xlarge c7i.4xlarge; do for sn in subnet-08873d09e6df8b202 subnet-04301346c1051e837 subnet-0dacd9dcd7989d65f; do
  out=$(aws ec2 run-instances --image-id ami-094adff9b24048c5c --instance-type $t --key-name ctv2-bench --security-group-ids sg-018e981a45e15e25b --subnet-id $sn \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=40,VolumeType=gp3,DeleteOnTermination=true}' --instance-initiated-shutdown-behavior terminate \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=hie-airtag-b}]' --query 'Instances[0].InstanceId' --output text 2>&1)
  case $out in i-*) echo $out > $L/iid; echo $t > $L/itype; echo "GOT $t $sn $out $(date +%T)"; break 2;; *) echo "$(date +%T) $t $sn $(echo $out | grep -oE '\(\w+\)' | head -1)";; esac
done; done
[ -s $L/iid ] || { echo "NO CAPACITY"; exit 1; }
aws ec2 wait instance-running --instance-ids $(cat $L/iid)
ip=$(aws ec2 describe-instances --instance-ids $(cat $L/iid) --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
printf 'Host hieb\n  HostName %s\n  User ubuntu\n  IdentityFile ~/.ssh/ctv2-bench.pem\n  UserKnownHostsFile /dev/null\n  StrictHostKeyChecking no\n  LogLevel ERROR\n' $ip > $L/ssh_config
for i in $(seq 1 60); do ssh -F $L/ssh_config -o ConnectTimeout=5 hieb true 2>/dev/null && break; sleep 5; done
ssh -F $L/ssh_config hieb 'sudo shutdown -h +240 >/dev/null 2>&1; mkdir -p ~/hie
sudo apt-get -qq update >/dev/null 2>&1 && sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y ffmpeg python3 >/dev/null 2>&1
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null 2>&1 && sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y nodejs >/dev/null 2>&1
node -v; ffmpeg -version | head -1; nproc'
echo "READY $(date +%T)"
