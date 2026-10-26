#!/bin/zsh
# usage: trial_variant.sh <src.mp4> <out-dir-name> <speed> [hook text | @] [hook y] [hook size] [accent]
#   → media/<out>/<out>.mp4: src sped up by <speed> (pitch kept), optional hook line (tools/remake/bin/hook_png.py) for
#     the first 3.8 s, then cutcheck + approved.md5. Caption and cover are written separately.
cd /Users/samarpit/insta-automation/how-its-engineered
SRC=$1; D=$2; SP=$3; HOOK=$4; Y=${5:-220}; SZ=${6:-64}; AC=${7:-ff7a2f}
mkdir -p media/$D
if [[ -n $HOOK ]]; then
  # "@" = use the media/<out>/hook.png already made (e.g. with --band)
  [[ $HOOK == @ ]] || python3 tools/remake/bin/hook_png.py "$HOOK" media/$D/hook.png --y $Y --size $SZ --accent $AC >/dev/null || exit 1
  ffmpeg -v error -y -i $SRC -loop 1 -t 4 -i media/$D/hook.png -filter_complex "[0:v]setpts=PTS/${SP},fps=30[s];[1:v]format=rgba,fade=t=out:st=3.4:d=0.4:alpha=1[h];[s][h]overlay=0:0:eof_action=pass:enable='lt(t,3.8)'[v];[0:a]atempo=${SP}[a]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart media/$D/$D.mp4 || exit 1
else
  ffmpeg -v error -y -i $SRC -filter_complex "[0:v]setpts=PTS/${SP},fps=30[v];[0:a]atempo=${SP}[a]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart media/$D/$D.mp4 || exit 1
fi
md5 -q media/$D/$D.mp4 > media/$D/approved.md5
echo "$D: $(ffprobe -v error -show_entries format=duration -of csv=p=0 $SRC) s → $(ffprobe -v error -show_entries format=duration -of csv=p=0 media/$D/$D.mp4) s, md5 $(cat media/$D/approved.md5)"
python3 ../claude-talk-v2/scripts/cutcheck.py media/$D/$D.mp4 ${TMPDIR:-/tmp}/cutcheck_$D 2>&1 | tail -3
