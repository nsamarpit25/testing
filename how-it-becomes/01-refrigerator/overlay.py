"""One-word pop captions (centre screen, white with black outline) + @handle watermark -> overlay.ass
python3 overlay.py [@handle]"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
HANDLE = sys.argv[1] if len(sys.argv) > 1 else "@letsbuildsimply"
WORDS = json.load(open(os.path.join(HERE, "audio/words.json")))
END = json.load(open(os.path.join(HERE, "audio/lines.json")))[-1]["end"] + 1.1


def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: W,Montserrat ExtraBold,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,3,5,40,40,0,1
Style: H,Montserrat ExtraBold,38,&H50FFFFFF,&H00FFFFFF,&H60000000,&H00000000,0,0,0,0,100,100,1,0,1,2.5,0,2,40,40,330,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
for i, (w, a, b, li) in enumerate(WORDS):
    txt = re.sub(r"[^\w'\-]", "", w).strip("-")
    if not txt:
        continue
    nxt = WORDS[i + 1][1] if i + 1 < len(WORDS) else b + 0.4
    end = nxt if nxt - b < 0.45 else b + 0.25          # hold until the next word unless there's a real pause
    ev.append(f"Dialogue: 1,{ts(a)},{ts(end)},W,,0,0,0,,{{\\pos(540,960)\\fscx78\\fscy78\\t(0,90,\\fscx104\\fscy104)\\t(90,150,\\fscx100\\fscy100)}}{txt.capitalize() if i == 0 or WORDS[i-1][3] != li else txt[0].upper() + txt[1:]}")
ev.append(f"Dialogue: 0,{ts(0)},{ts(END)},H,,0,0,0,,{HANDLE}")
open(os.path.join(HERE, "overlay.ass"), "w").write(hdr + "\n".join(ev) + "\n")
print(len(ev), "events")
