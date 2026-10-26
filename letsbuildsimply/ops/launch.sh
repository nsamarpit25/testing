#!/bin/zsh
# launch.sh <name>: one GPU render box for @letsbuildsimply (ops/boxes/<name>/{iid,region,ssh_config,lifecycle}).
# Tries SPOT first (g6e/g6/g5, 2xlarge then xlarge) in ap-south-1 then us-east-1, then falls back to on-demand.
# Env: SPOT_ONLY=1 (no on-demand), REGION="<regions>", TYPES="<types>" narrow the search.
# Installs Blender 5.2.2, ffmpeg and faster-whisper. Safety: the box shuts itself down (= terminates) after 6 h.
N=$1; L=/Users/samarpit/insta-automation/letsbuildsimply/ops/boxes/$N; mkdir -p $L
set -a; source /Users/samarpit/insta-automation/.env; set +a; unset AWS_PROFILE
SPOT='MarketType=spot,SpotOptions={SpotInstanceType=one-time,InstanceInterruptionBehavior=terminate}'
try() {  # try <market:spot|ondemand>
  for cfg in "ap-south-1 ami-0d2d551d15423a971 sg-018e981a45e15e25b subnet-08873d09e6df8b202 subnet-04301346c1051e837 subnet-0dacd9dcd7989d65f" \
             "us-east-1 ami-07ab2d4b1490816c3 sg-05192d8b67f0c91d5 subnet-0648f6e3da55349b1 subnet-05f6162ec26b8b423 subnet-0a6d9689a4fbb5034 subnet-0b1291b31c4e5c25c subnet-0c4662e8aca3cc53e subnet-049fe4e59e4e896cf"; do
    set -- ${=cfg}; reg=$1 ami=$2 sg=$3; shift 3; [[ -n $REGION && " $REGION " != *" $reg "* ]] && continue
    for t in ${=${TYPES:-g6e.2xlarge g6.2xlarge g5.2xlarge g6e.xlarge g6.xlarge g5.xlarge}}; do for sn in "$@"; do
      mk=(); [[ $market == spot ]] && mk=(--instance-market-options $SPOT)
      out=$(aws ec2 run-instances --region $reg --image-id $ami --instance-type $t --key-name ctv2-bench --security-group-ids $sg --subnet-id $sn $mk \
        --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=100,VolumeType=gp3,DeleteOnTermination=true}' --instance-initiated-shutdown-behavior terminate \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=lbs-$N}]" --query 'Instances[0].InstanceId' --output text 2>&1)
      case $out in i-*) echo $out > $L/iid; echo $reg > $L/region; echo "$market $t" > $L/lifecycle; echo "GOT $market $t $reg $out $(date +%T)"; return 0;;
                   *) echo "$(date +%T) $market $reg $t $(echo $out | grep -oE '\(\w+\)' | head -1)";; esac
    done; done
  done; return 1
}
if [[ -n $SPOT_ONLY ]]; then market=spot; try || { echo "NO SPOT CAPACITY"; exit 1; }; else market=spot; try || { market=ondemand; try; } || { echo "NO CAPACITY"; exit 1; }; fi
export AWS_REGION=$(cat $L/region)
aws ec2 wait instance-running --instance-ids $(cat $L/iid)
ip=$(aws ec2 describe-instances --instance-ids $(cat $L/iid) --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
printf 'Host %s\n  HostName %s\n  User ubuntu\n  IdentityFile ~/.ssh/ctv2-bench.pem\n  UserKnownHostsFile /dev/null\n  StrictHostKeyChecking no\n  LogLevel ERROR\n  ServerAliveInterval 30\n' $N $ip > $L/ssh_config
for i in $(seq 1 60); do ssh -F $L/ssh_config -o ConnectTimeout=5 $N true 2>/dev/null && break; sleep 5; done
ssh -F $L/ssh_config $N 'mkdir -p ~/lbs; sudo shutdown -h +360 >/dev/null 2>&1
(sudo apt-get -qq update && sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y ffmpeg python3-pip python3-venv libegl1 libgl1 libxkbcommon0 libsm6 libxi6 libxrender1 libxxf86vm1 libxfixes3 libxkbcommon-x11-0 >/dev/null 2>&1 \
  && python3 -m venv ~/wv && ~/wv/bin/pip -q install faster-whisper >/dev/null 2>&1) &
U=https://mirrors.ocf.berkeley.edu/blender/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz
S=$(curl -sIL -A "Mozilla/5.0" $U | grep -i content-length | tail -1 | tr -dc 0-9); P=10; ch=$(( (S + P - 1) / P ))
for i in $(seq 0 $((P-1))); do a=$((i*ch)); b=$((a+ch-1)); curl -sL -A "Mozilla/5.0" -r $a-$b -o part$i $U & done; wait
cat $(for i in $(seq 0 $((P-1))); do echo part$i; done) > b.tar.xz; rm part*; tar xJf b.tar.xz; rm b.tar.xz; wait
./blender-5.2.2-linux-x64/blender --version | head -1; nvidia-smi --query-gpu=name --format=csv,noheader; ~/wv/bin/python -c "import faster_whisper; print(\"whisper ok\")"'
echo "READY $(date +%T)"
