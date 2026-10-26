#!/bin/bash
# encode.sh [OUT] -> mp4 on the PC: frames (810x1440) scaled to 1080x1920 + bloom, vignette, grain, overlay.ass, mix.wav
cd /mnt/ssd/render/3d-07-storm-barrier
OUT=${1:-sb_final.mp4}
ffmpeg -loglevel error -y -framerate 30 -i r/x/f_%04d.png -i mix.wav -filter_complex \
 "[0:v]scale=1080:1920:flags=lanczos,format=gbrp,split[a][b];[b]curves=all='0/0 0.62/0 1/1',gblur=sigma=34[g];[a][g]blend=all_mode=screen:all_opacity=0.32,\
vignette=angle=PI/5:mode=forward,noise=alls=3:allf=t,ass=overlay.ass,format=yuv420p[v]" \
 -map "[v]" -map 1:a -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $OUT
ls -l $OUT
