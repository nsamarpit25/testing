#!/usr/bin/env bash
# Run Blender jobs on the render PC (sam@192.168.0.106, AMD RX 6600, Eevee on GPU).
#   scripts/pc.sh build                       -> push scripts, rebuild scene.blend
#   scripts/pc.sh lineup [V3,V1]              -> build the girl lineup (optionally only some variants)
#   scripts/pc.sh mascots [orb]               -> build the Claude mascot variants lineup (orb = the orb set)
#   scripts/pc.sh hero                        -> moody desk look-dev for the hero mascot (hero.blend)
#   scripts/pc.sh desk [E3,E4] [out.blend]              -> Claude candidates on Cleo's desk in the real scene (desk.blend), optionally only some
#   scripts/pc.sh rooms R1                     -> one room layout variant (rooms_R1.blend)
#   scripts/pc.sh stills [height] [samples] [shots]
#   scripts/pc.sh anim   [height] [samples]   -> headless animation frames
#   scripts/pc.sh gui    [height] [samples]   -> open Blender UI on the PC screen and render there
#   scripts/pc.sh pull <remote-subdir> <local-dir>
set -euo pipefail
HOST=sam@192.168.0.106
RROOT=${RROOT:-/mnt/ssd/claude-talk-v2}  # override when the SSD is not mounted, e.g. RROOT=/home/sam/ctv2
BLENDER=/home/sam/apps/blender-5.2.2-linux-x64/blender
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cmd=${1:-build}; shift || true

push() { ssh "$HOST" "mkdir -p $RROOT/blender $RROOT/out"; scp -q "$HERE"/blender/*.py "$HOST:$RROOT/blender/"; }

case "$cmd" in
  build)
    push
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/build_scene.py -- $RROOT/scene.blend 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  lineup)
    push
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/lineup.py -- $RROOT/lineup.blend ${1:-} 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  mascots)
    push
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/mascots_lineup.py -- $RROOT/mascots.blend ${1:-} 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  hero)
    push
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/mascots_hero.py -- $RROOT/hero.blend 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  desk)
    push
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/mascots_desk.py -- $RROOT/${2:-desk.blend} ${1:-} 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  rooms)  # rooms <R1> -> rooms_R1.blend
    push
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/rooms.py -- $RROOT/rooms_$1${2:+_$2}.blend $1 ${2:-} 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  cams)  # cams <blend> <outsub> [height] [samples] [filters]
    ssh "$HOST" "cd $RROOT && rm -rf out/$2 && $BLENDER -b $1 -P blender/render.py -- cams $RROOT/out/$2 ${3:-1280} ${4:-64} ${5:-} 2>&1 | grep -E 'STILL|Error|Traceback' | head -40" ;;
  stills)
    ssh "$HOST" "cd $RROOT && rm -rf out/stills && $BLENDER -b scene.blend -P blender/render.py -- stills $RROOT/out/stills ${1:-640} ${2:-32} ${3:-} 2>&1 | grep -E 'STILL|Error|Traceback' | head -30" ;;
  anim)
    ssh "$HOST" "cd $RROOT && rm -rf out/anim && $BLENDER -b scene.blend -P blender/render.py -- anim $RROOT/out/anim ${1:-640} ${2:-24} 2>&1 | grep -E 'Error|Traceback' | head" ;;
  gui)
    ssh "$HOST" "rm -rf $RROOT/out/anim; sig=\$(ls /run/user/\$(id -u)/hypr | head -1); \
      HYPRLAND_INSTANCE_SIGNATURE=\$sig XDG_RUNTIME_DIR=/run/user/\$(id -u) hyprctl dispatch exec \
      \"$BLENDER $RROOT/scene.blend -P $RROOT/blender/render.py -- gui $RROOT/out/anim ${1:-640} ${2:-24}\"" ;;
  ep1)  # ep1 <audio dir> -> ep1.blend from blender/ep1.py and the timeline
    push; ssh "$HOST" "mkdir -p $RROOT/ep1"; scp -q "$HERE/$1/timeline.json" "$HERE/$1/mix.wav" "$HERE/$1/subs.ass" "$HOST:$RROOT/ep1/"
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/ep1.py -- $RROOT/ep1.blend $RROOT/ep1/timeline.json 2>&1 | grep -E 'SAVED|POLE|SIGNS|Error|Traceback|line [0-9]+' | head -30" ;;
  ep1frames)  # ep1frames <f,f,...> [height] [samples] -> out/ep1frames
    scp -q "$HERE"/blender/render.py "$HOST:$RROOT/blender/"
    ssh "$HOST" "cd $RROOT && rm -rf out/ep1frames && $BLENDER -b ep1.blend -P blender/render.py -- frames $RROOT/out/ep1frames ${2:-480} ${3:-8} $1 2>&1 | grep -E 'STILL|Error|Traceback' | head -60" ;;
  ep1anim)  # ep1anim [height] [samples] -> out/ep1anim/f_####.png, then ep1/ep1_preview.mp4 with voices and captions
    ssh "$HOST" "cd $RROOT && rm -rf out/ep1anim && $BLENDER -b ep1.blend -P blender/render.py -- anim $RROOT/out/ep1anim ${1:-480} ${2:-8} 2>&1 | grep -E 'Error|Traceback' | head; \
      ffmpeg -loglevel error -y -framerate 30 -i out/ep1anim/f_%04d.png -i ep1/mix.wav -vf \"scale=540:960:flags=lanczos,subtitles=ep1/subs.ass\" \
      -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -shortest ep1/ep1_preview.mp4 && ls -la ep1/ep1_preview.mp4" ;;
  ep2)  # ep2 <audio dir> -> ep2.blend from blender/ep2.py, the timeline and the screen images
    push; ssh "$HOST" "mkdir -p $RROOT/ep2/screens"; scp -q "$HERE/$1/timeline.json" "$HERE/$1/mix.wav" "$HERE/$1/subs.ass" "$HOST:$RROOT/ep2/"
    scp -q "$HERE/$1"/screens/*.png "$HOST:$RROOT/ep2/screens/"
    ssh "$HOST" "cd $RROOT && $BLENDER -b --factory-startup -P blender/ep2.py -- $RROOT/ep2.blend $RROOT/ep2/timeline.json 2>&1 | grep -E 'SAVED|Error|Traceback|line [0-9]+' | head -30" ;;
  ep2frames)  # ep2frames <f,f,...> [height] [samples] -> out/ep2frames
    scp -q "$HERE"/blender/render.py "$HOST:$RROOT/blender/"
    ssh "$HOST" "cd $RROOT && rm -rf out/ep2frames && $BLENDER -b ep2.blend -P blender/render.py -- frames $RROOT/out/ep2frames ${2:-480} ${3:-8} $1 2>&1 | grep -E 'STILL|Error|Traceback' | head -60" ;;
  ep2anim)  # ep2anim [height] [samples] -> out/ep2anim/f_####.png, then ep2/ep2_preview.mp4 with voices and captions
    ssh "$HOST" "cd $RROOT && rm -rf out/ep2anim && $BLENDER -b ep2.blend -P blender/render.py -- anim $RROOT/out/ep2anim ${1:-480} ${2:-8} 2>&1 | grep -E 'Error|Traceback' | head; \
      ffmpeg -loglevel error -y -framerate 30 -i out/ep2anim/f_%04d.png -i ep2/mix.wav -vf \"scale=540:960:flags=lanczos,subtitles=ep2/subs.ass\" \
      -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -shortest ep2/ep2_preview.mp4 && ls -la ep2/ep2_preview.mp4" ;;
  pull)
    mkdir -p "$2"; scp -q -r "$HOST:$RROOT/out/$1/." "$2/" ;;
esac
