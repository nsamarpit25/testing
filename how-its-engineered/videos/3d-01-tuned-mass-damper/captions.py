"""words.json -> captions.ass: small white phrase captions near the bottom, key words coloured.
python3 captions.py  (writes audio/captions.ass)"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(os.path.join(HERE, "audio/words.json")))
CHUNKS = [(0, 3), (4, 8), (9, 13), (14, 16), (17, 20), (21, 25), (26, 32), (33, 39), (40, 45), (46, 47),
          (48, 51), (52, 56), (57, 63), (64, 71), (72, 76), (77, 80), (81, 83), (84, 87), (88, 92), (93, 96), (97, 101),
          (102, 105), (106, 110), (111, 114), (115, 117), (118, 125)]
SHOW = {2: "", 3: "2015,", 8: "Taipei 101,", 16: "101", 43: "87", 45: "92,", 49: "660-tonne", 100: "", 101: "40%."}
GOLD, CYAN, HEAT = "&H1AB2FF&", "&HFFE63F&", "&H1A5AFF&"   # ASS colours are BGR
COL = {3: GOLD, 16: GOLD, 20: GOLD, 25: CYAN, 43: GOLD, 45: GOLD, 49: GOLD, 51: GOLD, 54: GOLD, 55: GOLD, 56: GOLD,
       63: CYAN, 75: GOLD, 83: HEAT, 92: HEAT, 101: GOLD, 110: GOLD}


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans,58,&H00FFFFFF,&H00FFFFFF,&H00180D06,&H90000000,-1,0,0,0,100,100,0,0,1,6,3,2,150,150,360,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
for k, (a, b) in enumerate(CHUNKS):
    t0 = W[a][1] - 0.05
    end = W[b][2] + 0.25
    if k + 1 < len(CHUNKS):
        nxt = W[CHUNKS[k + 1][0]][1] - 0.05
        end = nxt if nxt - W[b][2] < 0.6 else end
    words = []
    for i in range(a, b + 1):
        s = SHOW.get(i, W[i][0])
        if not s:
            continue
        words.append(f"{{\\c{COL[i]}}}{s}{{\\c&HFFFFFF&}}" if i in COL else s)
    ev.append(f"Dialogue: 0,{ts(t0)},{ts(end)},Cap,,0,0,0,,{{\\fad(40,40)}}{' '.join(words)}")
out = os.path.join(HERE, "audio/captions.ass")
open(out, "w").write(head + "\n".join(ev) + "\n")
print("wrote", out, len(ev))
