"""Trial-reel repackage of a finished episode, no re-render: a cold open (a clip from later in the episode), then one
cut to the full episode. The user doesn't want on-screen text hooks, so --hook (text box at the top) is off by default.

python3 scripts/trial_a.py <final.mp4> <out.mp4> --cold START END [--hook "TEXT"] [--hook-secs 4]
  START/END are seconds in <final.mp4>.
"""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def hook_png(text, path, size=64, top=250, pad=(34, 22), maxw=900):
    """White bold text on a dark rounded box, centred near the top (above the faces, clear of Instagram's top bar)."""
    font = ImageFont.truetype(FONT, size)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    words, lines, cur = text.split(), [], ""
    for w in words:  # greedy wrap to maxw
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    lh = int(size * 1.22)
    bw = int(max(d.textlength(l, font=font) for l in lines)) + 2 * pad[0]
    bh = lh * len(lines) + 2 * pad[1]
    x0 = (W - bw) // 2
    d.rounded_rectangle([x0, top, x0 + bw, top + bh], radius=28, fill=(16, 16, 20, 225))
    for i, l in enumerate(lines):
        tw = d.textlength(l, font=font)
        d.text(((W - tw) / 2, top + pad[1] + i * lh - size * 0.08), l, font=font, fill=(255, 255, 255, 255))
    im.save(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src"); p.add_argument("out")
    p.add_argument("--hook")
    p.add_argument("--cold", nargs=2, type=float)
    p.add_argument("--hook-secs", type=float, default=4.0)
    a = p.parse_args()
    tmp = tempfile.mkdtemp()
    png = os.path.join(tmp, "hook.png")
    hook_png(a.hook, png) if a.hook else Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(png)
    enc = ["-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart"]
    if a.cold:
        s, e = a.cold
        d = e - s
        fc = (f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30[cv];[cv][2:v]overlay=0:0[cvh];"
              f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={d - 0.08}:d=0.08,aresample=48000[ca];"
              f"[1:v]fps=30,setpts=PTS-STARTPTS[mv];[1:a]aresample=48000,asetpts=PTS-STARTPTS[ma];"
              f"[cvh][ca][mv][ma]concat=n=2:v=1:a=1[v][a]")
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", a.src, "-i", a.src, "-loop", "1", "-t", str(d), "-i", png,
               "-filter_complex", fc, "-map", "[v]", "-map", "[a]", *enc, a.out]
    else:
        fc = f"[0:v][1:v]overlay=0:0:enable='lt(t,{a.hook_secs})'[v]"
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", a.src, "-loop", "1", "-i", png,
               "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-shortest", *enc, a.out]
    subprocess.run(cmd, check=True)
    print(a.out)


if __name__ == "__main__":
    main()
