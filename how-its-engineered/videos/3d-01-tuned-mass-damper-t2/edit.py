"""t2 re-edit of the damper reel from the clean EEVEE frames (PC: /mnt/ssd/render/3d-01-tuned-mass-damper/out/f_%04d.png, 30 fps).
Each new script line gets source shots (orig seconds) retimed to fill its window, each with its own static punch-in reframe.
python3 edit.py -> audio/captions.ass (word-by-word) + edit.sh (run on the PC)"""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
L = json.load(open(HERE / "audio/lines.json"))
W = json.load(open(HERE / "audio/words.json"))
END = 38.29
# per line: [(src_a, src_b, zoom, x_frac, y_frac)]  x/y_frac = where the crop window sits (0..1, 0.5 = centre)
PLAN = [
    [(17.15, 18.4, 1.10, 0.5, 0.42), (18.4, 19.5, 1.0, 0.5, 0.5), (3.92, 5.95, 1.12, 0.62, 0.3), (19.5, 20.6, 1.08, 0.5, 0.6)],
    [(7.5, 9.45, 1.12, 0.45, 0.35), (9.45, 11.3, 1.06, 0.5, 0.5), (11.3, 12.35, 1.1, 0.4, 0.55), (12.35, 13.4, 1.0, 0.5, 0.5)],
    [(16.2, 17.15, 1.08, 0.5, 0.4), (13.4, 16.2, 1.04, 0.5, 0.45), (21.75, 23.75, 1.1, 0.5, 0.4)],
    [(23.75, 25.4, 1.06, 0.4, 0.4), (25.4, 27.5, 1.0, 0.5, 0.5)],
    [(27.5, 28.7, 1.1, 0.5, 0.45), (29.2, 30.8, 1.06, 0.6, 0.5), (31.0, 33.0, 1.08, 0.5, 0.4)],
    [(0.0, 1.45, 1.12, 0.45, 0.6), (1.45, 2.65, 1.05, 0.5, 0.35), (5.95, 7.5, 1.1, 0.5, 0.5), (33.5, 35.35, 1.06, 0.5, 0.55)],
    [(20.6, 21.75, 1.12, 0.5, 0.45), (35.35, 37.5, 1.08, 0.55, 0.5)],
    [(37.5, 40.4, 1.04, 0.5, 0.4)],
]
FPS, NF = 30, 1213
cmds, cut_at, k = [], [], 0
for i, segs in enumerate(PLAN):
    t0 = 0.0 if i == 0 else L[i]["start"]
    t1 = L[i + 1]["start"] if i + 1 < len(L) else END
    src = sum(b - a for a, b, *_ in segs)
    f = (t1 - t0) / src
    print(f"line {i+1}: {t0:5.2f}-{t1:5.2f} src {src:.2f}s  speed x{1/f:.2f}")
    t = t0
    for a, b, z, xf, yf in segs:
        o0, o1 = round(t * FPS), round((t + (b - a) * f) * FPS)
        t += (b - a) * f
        n_src = min(round((b - a) * FPS), NF - round(a * FPS))
        zw, zh = round(1080 * z / 2) * 2, round(1920 * z / 2) * 2
        vf = (f"setpts=(PTS-STARTPTS)*{f:.5f},fps=30,scale={zw}:{zh}:flags=lanczos,"
              f"crop=1080:1920:{round((zw - 1080) * xf)}:{round((zh - 1920) * yf)},eq=contrast=1.04:saturation=1.08,"
              f"tpad=stop_mode=clone:stop_duration=1")
        cmds.append(f"ffmpeg -loglevel error -y -framerate 30 -start_number {round(a * FPS) + 1} -i $SRC/f_%04d.png -frames:v {n_src} "
                    f"-vf '{vf}' -frames:v {o1 - o0} -c:v libx264 -crf 13 -preset fast -pix_fmt yuv420p seg{k:02d}.mp4")
        cut_at.append(round(o0 / FPS, 3))
        k += 1
(HERE / "cuts.json").write_text(json.dumps(cut_at))
sh = ["set -e", "SRC=/mnt/ssd/render/3d-01-tuned-mass-damper/out", "cd /mnt/ssd/hie/tmd2", *cmds,
      "rm -f list.txt; for s in seg*.mp4; do echo \"file '$s'\" >> list.txt; done",
      "ffmpeg -loglevel error -y -f concat -safe 0 -i list.txt -c copy silent.mp4",
      "ffmpeg -loglevel error -y -i silent.mp4 -i mix.wav -vf ass=captions.ass -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p "
      "-r 30 -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart t2.mp4", "ls -la t2.mp4"]
(HERE / "edit.sh").write_text("\n".join(sh) + "\n")

# word-by-word captions
SHOW = {"six-hundred-sixty-tonne": "660-TONNE", "one-oh-one.": "101", "eighty-seven": "87", "ninety-two,": "92",
        "twenty": "2015", "fifteen,": "", "forty": "40%", "percent.": ""}
GOLD, CYAN, HEAT = "&H1AB2FF&", "&HFFE63F&", "&H1A5AFF&"   # BGR
KEY = {"six-hundred-sixty-tonne": CYAN, "Taipei": GOLD, "one-oh-one.": GOLD, "purpose.": GOLD,
       "sway": CYAN, "ruler": CYAN, "seasick.": CYAN, "cables": GOLD, "eighty-seven": GOLD, "ninety-two,": GOLD, "rhythm.": CYAN,
       "lags": CYAN, "back.": CYAN, "Eight": GOLD, "pistons": GOLD, "heat,": HEAT, "forty": GOLD, "twenty": GOLD,
       "Soudelor": HEAT, "full": GOLD, "metre,": GOLD, "record.": GOLD, "barely": CYAN, "hidden": GOLD}
ts = lambda t: f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{max(t, 0) % 60:05.2f}"
head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: W,Noto Sans Black,80,&H00FFFFFF,&H00FFFFFF,&H00140B05,&H96000000,0,0,0,0,100,100,1,0,1,8,4,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
vis = [(w, a, b) for w, a, b, _ in W if SHOW.get(w, w) != ""]
# karaoke lines: up to 3 words / 16 chars, the line fills word by word, the spoken word lit yellow
LIVE = "&H4DC3FF&"
lines, cur = [], []
for j, x in enumerate(vis):
    txt = SHOW.get(x[0]) or re.sub(r"[.,:;!?]+$", "", x[0]).upper()
    if cur and (len(cur) >= 3 or sum(len(t) + 1 for t, _ in cur) + len(txt) > 16 or x[1] - vis[j - 1][2] > 0.6
                or re.search(r"[.,:;!?]$", vis[j - 1][0])):
        lines.append(cur); cur = []
    cur.append((txt, j))
lines.append(cur)
ev = []
for li, ln in enumerate(lines):
    lend = vis[lines[li + 1][0][1]][1] - 0.03 if li + 1 < len(lines) else END
    lend = min(lend, vis[ln[-1][1]][2] + 0.5)
    for k, (txt, j) in enumerate(ln):
        a = vis[j][1] - 0.03
        e = vis[ln[k + 1][1]][1] - 0.03 if k + 1 < len(ln) else lend
        parts = []
        for m, (t2, j2) in enumerate(ln):
            base = KEY.get(vis[j2][0], "&HFFFFFF&")
            if m < k: parts.append(f"{{\\alpha&H00&\\c{base}\\fscx100\\fscy100}}{t2}")
            elif m == k: parts.append(f"{{\\alpha&H00&\\c{KEY.get(vis[j2][0], LIVE)}\\fscx118\\fscy118\\t(0,120,\\fscx108\\fscy108)}}{t2}")
            else: parts.append(f"{{\\alpha&HFF&\\fscx100\\fscy100}}{t2}")
        ev.append(f"Dialogue: 0,{ts(a)},{ts(e)},W,,0,0,0,,{{\\an5\\pos(540,1330)}}" + " ".join(parts))
(HERE / "audio/captions.ass").write_text(head + "\n".join(ev) + "\n")
print(len(ev), "caption events; cuts", cut_at)
