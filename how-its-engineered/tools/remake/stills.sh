#!/bin/zsh
# usage: stills.sh <dir-name> <t1,t2,...> → syncs videos/_ember + videos/<dir> to the PC, renders stills there, pulls back a contact sheet
set -e
D=$1; TS=$2; H=~/insta-automation/how-its-engineered; SP=${SP:-$HOME/insta-automation/how-its-engineered/tools/remake/out}; mkdir -p $SP
K=(-e "ssh -i $HOME/.ssh/id_ed25519 -o BatchMode=yes")
rsync -a --delete "${K[@]}" $H/videos/_ember $H/tools sam@192.168.0.112:/mnt/ssd/hie/videos/ 2>/dev/null || true
rsync -a "${K[@]}" $H/tools sam@192.168.0.112:/mnt/ssd/hie/
rsync -a --delete --exclude vtest "${K[@]}" $H/videos/$D sam@192.168.0.112:/mnt/ssd/hie/videos/
ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes sam@192.168.0.112 "cd /mnt/ssd/hie && rm -rf st/$D && export PATH=\$HOME/.local/share/mise/shims:\$PATH CHROMIUM_PATH=/usr/bin/chromium && node tools/render.mjs videos/$D/video.html x.mp4 --stills $TS --outdir st/$D 2>&1 | grep -v '^$' | head -20; cd st/$D && i=0; for f in \$(ls still_*.png | sed 's/still_//; s/.png//' | sort -n); do ln -sf still_\$f.png seq_\$(printf %02d \$i).png; i=\$((i+1)); done; ffmpeg -loglevel error -y -i seq_%02d.png -frames:v 1 -vf \"scale=360:-1,tile=4x\$(( (i+3)/4 )):padding=4\" sheet.png"
mkdir -p $SP/st/$D; scp -q -i ~/.ssh/id_ed25519 "sam@192.168.0.112:/mnt/ssd/hie/st/$D/*.png" $SP/st/$D/
echo $SP/st/$D/sheet.png
