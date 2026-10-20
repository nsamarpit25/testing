#!/bin/zsh
# usage: sheet.sh <dir> <out.png> [cols]
cd "$1" || exit 1
rm -f seq_*.png(N)
i=0
for f in $(ls still_*.png | sed 's/still_//; s/.png//' | sort -n); do ln -sf "still_$f.png" seq_$(printf %02d $i).png; i=$((i+1)); done
ffmpeg -loglevel error -y -i seq_%02d.png -frames:v 1 -vf "scale=300:-1,tile=${3:-7}x$(( (i + ${3:-7} - 1) / ${3:-7} )):padding=4" "$2"
