"""Codex review package for a finished reel: frames 2/s as labeled sheets (4x4, 8 s each) + timed dialogue.
python3 review.py <video> <timeline.json|-> <outdir> [offset]   (offset: where the episode starts inside the video, for cold opens)"""
import json, os, subprocess, sys, glob
from PIL import Image, ImageDraw, ImageFont
v, tl, out = sys.argv[1:4]; off = float(sys.argv[4]) if len(sys.argv) > 4 else 0
os.makedirs(out + "/f", exist_ok=True)
for f in glob.glob(out + "/f/*.png") + glob.glob(out + "/sheet_*.jpg"): os.remove(f)
subprocess.run(["ffmpeg", "-loglevel", "error", "-i", v, "-vf", "fps=2,scale=270:480", out + "/f/%04d.png"], check=True)
fs = sorted(glob.glob(out + "/f/*.png")); F = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
sheets = []
for k in range(0, len(fs), 16):
    S = Image.new("RGB", (4 * 270, 4 * 480), "black"); d = ImageDraw.Draw(S)
    for i, f in enumerate(fs[k:k + 16]):
        x, y = (i % 4) * 270, (i // 4) * 480; S.paste(Image.open(f), (x, y))
        t = (k + i) / 2; d.rectangle([x, y, x + 74, y + 28], fill="yellow"); d.text((x + 4, y + 2), f"{t:.1f}s", font=F, fill="black")
    p = f"{out}/sheet_{k // 16:02d}.jpg"; S.save(p, quality=85); sheets.append(p)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout)
lines = []
if tl != "-":
    for l in json.load(open(tl))["lines"]:
        lines.append(f"{l['t0'] + off:6.2f}-{l['t1'] + off:6.2f}  {l['who'].upper():6s} {l['text']}")
open(out + "/dialogue.txt", "w").write(f"duration {dur:.1f}s\n" + "\n".join(lines) + "\n")
print(" ".join(sheets))
