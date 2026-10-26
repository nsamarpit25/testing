#!/bin/bash
# encode.sh [OUT] [SECONDS] -> mp4 on the PC: frames + bloom, vignette, grain, overlay.ass, mix.wav
cd /mnt/ssd/render/3d-03-jet-blades
OUT=${1:-jb_full.mp4}; LEN=${2:-}
DUR=""; [ -n "$LEN" ] && DUR="-t $LEN"
ffmpeg -loglevel error -y -framerate 30 -i out/f_%04d.png -i mix.wav -filter_complex \
 "[0:v]format=gbrp,split[a][b];[b]curves=all='0/0 0.62/0 1/1',gblur=sigma=26[g];[a][g]blend=all_mode=screen:all_opacity=0.32,\
vignette=angle=PI/5:mode=forward,noise=alls=3:allf=t,ass=overlay.ass,format=yuv420p[v]" \
 -map "[v]" -map 1:a $DUR -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $OUT
ls -l $OUT
