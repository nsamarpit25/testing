#!/bin/zsh
# usage: cover.sh <dir> <time>  → media/<dir>/cover.png
set -e
D=$1; TT=$2; H=~/insta-automation/how-its-engineered
rsync -a --delete --exclude vtest -e "ssh -i $HOME/.ssh/id_ed25519 -o BatchMode=yes" $H/videos/$D $H/videos/_ember ${HIE_PC:-sam@192.168.0.115}:/mnt/ssd/hie/videos/
ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes ${HIE_PC:-sam@192.168.0.115} "cd /mnt/ssd/hie && rm -rf cov/$D && export PATH=\$HOME/.local/share/mise/shims:\$PATH CHROMIUM_PATH=/usr/bin/chromium && node tools/render.mjs 'videos/$D/video.html#cover' x.mp4 --stills $TT --outdir cov/$D"
mkdir -p $H/media/$D; scp -q -i ~/.ssh/id_ed25519 "${HIE_PC:-sam@192.168.0.115}:/mnt/ssd/hie/cov/$D/still_*.png" $H/media/$D/cover.png; echo $H/media/$D/cover.png
