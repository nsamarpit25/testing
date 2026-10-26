#!/bin/bash
# Cut the Zack D.-style test from zdf.py's clips (runs on the render box): hard cuts A | B | lapse | C | D, the lapse
# clips cross-dissolved over their 8-frame handles (ghosting), scaled to 1080x1920, captions burned, the mix laid in.
# usage: scripts/zdf_cut.sh <clips dir> <ep audio dir> <out.mp4>    (frame numbers match blender/zdf.py CLIPS)
set -euo pipefail
C=$1; A=$2; OUT=$3; FONTS=${FONTS:-$HOME/fonts}
seq() { echo "-framerate 30 -start_number $2 -i $C/$1/f_%04d.png"; }
# input start frames: where each clip enters the master timeline (B, L1-L3, C trimmed past their handles)
ffmpeg -y -loglevel error \
  $(seq A 1) $(seq B 64) $(seq L0 118) $(seq L1 142) $(seq L2 167) $(seq L3 192) $(seq C 219) $(seq D 247) -i "$A/mix.wav" \
  -filter_complex "
    [0]trim=end_frame=63,setpts=PTS-STARTPTS,setsar=1[a];
    [1]trim=end_frame=54,setpts=PTS-STARTPTS,setsar=1[b];
    [2]setpts=PTS-STARTPTS,setsar=1[l0]; [3]setpts=PTS-STARTPTS,setsar=1[l1]; [4]setpts=PTS-STARTPTS,setsar=1[l2]; [5]setpts=PTS-STARTPTS,setsar=1[l3];
    [l0][l1]xfade=transition=fade:duration=0.2667:offset=0.8[x1];
    [x1][l2]xfade=transition=fade:duration=0.2667:offset=1.6333[x2];
    [x2][l3]xfade=transition=fade:duration=0.2667:offset=2.4667[x3];
    [6]trim=end_frame=28,setpts=PTS-STARTPTS,setsar=1[c];
    [7]trim=end_frame=54,setpts=PTS-STARTPTS,setsar=1[d];
    [a][b][x3][c][d]concat=n=5:v=1:a=0,
    scale=1080:1920:flags=lanczos,eq=saturation=1.06:contrast=1.03,ass=$A/subs.ass:fontsdir=$FONTS[v]" \
  -map "[v]" -map 8:a -af apad -shortest -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration -show_entries stream=nb_frames -of csv=p=0 "$OUT"
