#!/bin/bash
# encode.sh [OUT] (runs on the render box): frames + mix.wav + overlay.ass (one-word captions, handle) -> mp4
cd "$(dirname "$0")"
OUT=${1:-fridge_final.mp4}
ffmpeg -loglevel error -y -framerate 30 -i frames/f_%04d.png -i audio/mix.wav -filter_complex \
 "[0:v]format=gbrp,split[a][b];[b]curves=all='0/0 0.7/0 1/1',gblur=sigma=24[g];[a][g]blend=all_mode=screen:all_opacity=0.18,\
eq=saturation=1.12:contrast=1.04,vignette=angle=PI/6,ass=overlay.ass:fontsdir=fonts,format=yuv420p[v]" \
 -map "[v]" -map 1:a -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart $OUT
ls -l $OUT
