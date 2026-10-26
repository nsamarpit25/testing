"""Generic screen images (monitor 1600x944, phone 600x1290) from <audio dir>/screens.json:
{"name": {"kind": "code"|"term"|"page"|"mail"|"phone"|"off", ...}}
  code:  title, lines [str], hi [line idx] (boxed red), ok [line idx] (boxed green)
  term:  title, lines [str] ("$ " prompt lines white, "!" prefix red, "+" prefix green), hi [idx]
  page:  url, title, body [str], badge {text, color}, accent "#hex", big {text, color, top (above the body)}
  mail:  app, from, subject, body [str], badge, hi [body idx] (boxed red)
  phone: app, title, body, size                             (a notification on the lock screen)
  chat:  title, msgs [[me|them, text(, [file, sub])]], typing, size   (a messages thread, big type)
Content sits in the middle 60% of the width (the MON camera crops the sides).
python3 scripts/epx_screens.py audio/ep7
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

d = sys.argv[1]
S = json.load(open(f"{d}/screens.json"))
out = f"{d}/screens"
os.makedirs(out, exist_ok=True)
W, H = 1600, 944
SF = "/Library/Fonts/SF-Pro-Display-%s.otf"
MONO = "/System/Library/Fonts/Menlo.ttc"
X0, X1 = 320, 1280
TXT, DIM, GREEN, RED, AMBER, BLUE = (230, 237, 243), (139, 148, 158), (63, 185, 80), (248, 81, 73), (227, 179, 65), (88, 166, 255)
KW, FN, STR, COM, NUM = (198, 120, 221), (97, 175, 239), (152, 195, 121), (106, 115, 135), (209, 154, 102)


def font(size, w="Bold"):
    return ImageFont.truetype(SF % w, size)


def mono(size, bold=False):
    return ImageFont.truetype(MONO, size, index=1 if bold else 0)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def bar(dr, title, dark=True, url=None):
    dr.rectangle((0, 0, W, 64), fill=(34, 38, 46) if dark else (225, 222, 235))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        dr.ellipse((24 + i * 38, 20, 48 + i * 38, 44), fill=c)
    if url:
        dr.rounded_rectangle((X0 + 20, 10, X1 - 20, 56), 23, fill=(255, 255, 255), outline=(190, 184, 210), width=2)
        dr.text((W // 2, 33), url, font=mono(30, True), fill=(30, 30, 40), anchor="mm")
    else:
        dr.text((W // 2, 32), title, font=font(30, "Medium"), fill=DIM if dark else (110, 104, 130), anchor="mm")


def fit(dr, text, f0, maxw, mk):
    s = f0
    while s > 18 and dr.textlength(text, font=mk(s)) > maxw:
        s -= 1
    return mk(s)


TOKS = re.compile(r"(//.*|#.*|--.*|\"[^\"]*\"|'[^']*'|`[^`]*`|\b(?:const|let|var|function|return|if|else|async|await|import|from|export|"
                  r"def|for|in|new|DELETE|FROM|WHERE|SELECT|UPDATE|SET|INSERT|INTO|true|false|null|None)\b|\b\d+\b|\w+|.)")


KWS = set("const let var function return if else async await import from export def for in new DELETE FROM WHERE SELECT UPDATE "
          "SET INSERT INTO true false null None".split())


def code_line(dr, x, y, s, f, lit=False):
    for m in TOKS.finditer(s):
        t = m.group(0)
        c = TXT
        if t.startswith(("//", "#", "--")):
            c = (255, 205, 200) if lit else COM
        elif t[0] in "\"'`":
            c = STR
        elif re.fullmatch(r"\d+", t):
            c = NUM
        elif t in KWS:
            c = KW
        elif re.fullmatch(r"\w+", t) and s[m.end():m.end() + 1] == "(":
            c = FN
        dr.text((x, y), t, font=f, fill=c)
        x += dr.textlength(t, font=f)


def code(nm, sp):
    im = Image.new("RGB", (W, H), (30, 30, 38))
    dr = ImageDraw.Draw(im)
    bar(dr, sp.get("title", ""))
    rows = sp["lines"]
    lh = min(70, (H - 130) // max(len(rows), 1))
    longest = max(rows, key=len) if rows else ""
    f = fit(dr, longest + "  ", 40, X1 - X0 + 120, mono)
    y = 100
    for i, s in enumerate(rows):
        dr.text((X0 - 40, y + 4), str(i + 1), font=mono(int(f.size * 0.85)), fill=(90, 92, 110), anchor="ra")
        if i in sp.get("hi", []) or i in sp.get("ok", []):
            red = i in sp.get("hi", [])
            dr.rounded_rectangle((X0 - 14, y - 8, X0 + dr.textlength(s, font=f) + 14, y + f.size + 14), 8,
                                 fill=(90, 22, 28) if red else (22, 70, 36), outline=RED if red else GREEN, width=3)
        code_line(dr, X0, y, s, f, i in sp.get("hi", []))
        y += lh
    im.save(f"{out}/{nm}.png")


def term(nm, sp):
    """Lines centred in the part of the screen the MON push-in keeps (about x 360-1100), as large as fits."""
    im = Image.new("RGB", (W, H), hexc(sp["bg"]) if "bg" in sp else (16, 18, 24))
    dr = ImageDraw.Draw(im)
    bar(dr, sp.get("title", "Terminal"))
    rows = sp["lines"]
    shown = [r[1:].lstrip() if r[:1] in "!+*" else r for r in rows]
    f = fit(dr, max(shown, key=len) + " ", 56, 700, mono)
    lh = min(int(f.size * 1.55), (H - 160) // max(len(rows), 1))
    bw = max(dr.textlength(t, font=f) for t in shown)
    x = 730 - bw / 2
    y = 130
    for i, (s, t) in enumerate(zip(rows, shown)):
        c = (255, 130, 120) if s.startswith("!") else (120, 230, 140) if s.startswith("+") else TXT if s[:1] in "$*" else DIM
        if i in sp.get("hi", []):
            dr.rounded_rectangle((x - 14, y - 8, x + dr.textlength(t, font=f) + 14, y + f.size + 14), 8, fill=(90, 22, 28), outline=RED, width=3)
        dr.text((x, y), t, font=f, fill=c)
        y += lh
    im.save(f"{out}/{nm}.png")


def page(nm, sp):
    im = Image.new("RGB", (W, H), (250, 248, 252))
    dr = ImageDraw.Draw(im)
    bar(dr, sp.get("tab", ""), dark=False, url=sp.get("url"))
    acc = hexc(sp.get("accent", "#5b5bd6"))
    dr.rectangle((0, 64, W, 64 + 150), fill=acc)
    dr.text((W // 2, 139), sp.get("title", ""), font=fit(dr, sp.get("title", ""), 76, X1 - X0, font), fill=(255, 255, 255), anchor="mm")
    y = 290
    if sp.get("url_hi"):  # the address itself, big and boxed red under the header, readable on a phone
        f = mono(64, True)
        tw = dr.textlength(sp["url"], font=f)
        dr.rounded_rectangle((W // 2 - tw / 2 - 30, 250, W // 2 + tw / 2 + 30, 350), 18, fill=(255, 255, 255), outline=RED, width=7)
        dr.text((W // 2, 300), sp["url"], font=f, fill=(30, 30, 40), anchor="mm")
        y = 430
    def big(y):
        b = sp["big"]
        col = hexc(b.get("color", "#d64545"))
        dr.rounded_rectangle((X0 + 20, y + 10, X1 - 20, min(H - 30, y + 230)), 28, fill=col)
        dr.text((W // 2, (y + 10 + min(H - 30, y + 230)) // 2), b["text"], font=fit(dr, b["text"], 84, X1 - X0 - 100, lambda z: font(z, "Black")),
                fill=(255, 255, 255), anchor="mm")
    if "big" in sp and sp["big"].get("top"):  # the big box first, then the body under it
        big(y - 60)
        y += 230
    for s in sp.get("body", []):
        f = fit(dr, s, 62, X1 - X0, lambda z: font(z, "Medium"))
        dr.text((W // 2, y), s, font=f, fill=(40, 36, 60), anchor="mm")
        y += 96
    if "big" in sp and not sp["big"].get("top"):
        big(y)
    if "badge" in sp:
        b = sp["badge"]
        f = fit(dr, b["text"], 54, X1 - X0 - 60, font)
        tw = dr.textlength(b["text"], font=f)
        dr.rounded_rectangle((W // 2 - tw / 2 - 34, H - 190, W // 2 + tw / 2 + 34, H - 100), 45, fill=hexc(b.get("color", "#2f9e44")))
        dr.text((W // 2, H - 145), b["text"], font=f, fill=(255, 255, 255), anchor="mm")
    im.save(f"{out}/{nm}.png")


def mail(nm, sp):
    im = Image.new("RGB", (W, H), (245, 246, 250))
    dr = ImageDraw.Draw(im)
    bar(dr, sp.get("app", "Mail"), dark=False)
    dr.text((X0, 120), sp.get("from", ""), font=font(36, "Semibold"), fill=(90, 90, 110), anchor="lm")
    dr.text((X0, 190), sp.get("subject", ""), font=fit(dr, sp.get("subject", ""), 54, X1 - X0, font), fill=(25, 25, 40), anchor="lm")
    dr.line((X0, 240, X1, 240), fill=(210, 210, 222), width=3)
    y = 300
    for i, s in enumerate(sp.get("body", [])):
        f = fit(dr, s, 42, X1 - X0, lambda z: font(z, "Regular"))
        if i in sp.get("hi", []):
            dr.rounded_rectangle((X0 - 16, y - f.size * 0.8, X0 + dr.textlength(s, font=f) + 16, y + f.size * 0.8), 10, fill=(255, 226, 226), outline=RED, width=5)
        dr.text((X0, y), s, font=f, fill=(50, 50, 66), anchor="lm")
        y += 66
    if "badge" in sp:
        b = sp["badge"]
        f = font(40)
        tw = dr.textlength(b["text"], font=f)
        dr.rounded_rectangle((X0, H - 130, X0 + tw + 60, H - 60), 35, fill=hexc(b.get("color", "#d64545")))
        dr.text((X0 + 30 + tw / 2, H - 95), b["text"], font=f, fill=(255, 255, 255), anchor="mm")
    im.save(f"{out}/{nm}.png")


def phone(nm, sp):
    im = Image.new("RGB", (600, 1290), (24, 30, 52))
    dr = ImageDraw.Draw(im)
    for yy in range(1290):  # a soft wallpaper gradient
        dr.line((0, yy, 600, yy), fill=(24 + yy // 30, 30 + yy // 40, 52 + yy // 25))
    dr.text((300, 200), sp.get("time", "9:41"), font=font(130, "Semibold"), fill=(240, 240, 250), anchor="mm")
    dr.rounded_rectangle((30, 420, 570, 760), 40, fill=(245, 245, 250))
    dr.text((70, 480), sp.get("app", "Messages").upper(), font=font(30, "Semibold"), fill=(120, 120, 135), anchor="lm")
    dr.text((70, 550), sp.get("title", ""), font=fit(dr, sp.get("title", ""), 46, 460, font), fill=(20, 20, 30), anchor="lm")
    words, rows, cur = sp.get("body", "").split(), [], ""
    f = font(sp.get("size", 38), "Regular")
    for w in words:
        if dr.textlength(cur + " " + w, font=f) > 460:
            rows.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    rows.append(cur)
    for i, r in enumerate(rows[:3]):
        dr.text((70, 620 + i * (f.size + 10)), r, font=f, fill=(50, 50, 66), anchor="lm")
    im.save(f"{out}/{nm}.png")


def chat(nm, sp):
    """A messages thread, big type so it reads in the PHONE shot: title, msgs [[me|them, text] or [me, text, attachment]],
    typing (dots under the last bubble). Only the newest bubbles that fit are drawn, bottom-aligned."""
    im = Image.new("RGB", (600, 1290), (12, 12, 16))
    dr = ImageDraw.Draw(im)
    dr.rectangle((0, 0, 600, 190), fill=(28, 28, 34))
    dr.ellipse((250, 40, 350, 140), fill=(120, 124, 140))
    dr.text((300, 92), sp.get("title", "?")[0], font=font(56, "Semibold"), fill=(240, 240, 248), anchor="mm")
    dr.text((300, 166), sp.get("title", ""), font=fit(dr, sp.get("title", ""), 34, 540, lambda s: font(s, "Semibold")), fill=(235, 235, 245), anchor="mm")
    f, pad, maxw = font(sp.get("size", 50), "Regular"), 26, 470
    blocks = []
    for m in sp.get("msgs", []):
        who, text = m[0], m[1]
        rows, cur = [], ""
        for w in text.split():
            if dr.textlength((cur + " " + w).strip(), font=f) > maxw - 2 * pad:
                rows.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        rows.append(cur)
        lh = f.size + 12
        h = len(rows) * lh + 2 * pad + (110 if len(m) > 2 else 0)
        blocks.append((who, rows, m[2] if len(m) > 2 else None, h, lh))
    y = 1290 - sp.get("bottom", 60) - (90 if sp.get("typing") else 0)
    drawn = []
    for b in reversed(blocks):
        if y - b[3] < 210:
            break
        drawn.append((y - b[3], b))
        y -= b[3] + 24
    for top, (who, rows, att, h, lh) in drawn:
        bw = max(dr.textlength(r, font=f) for r in rows) + 2 * pad
        if att:
            bw = maxw
        x0 = 600 - 24 - bw if who == "me" else 24
        dr.rounded_rectangle((x0, top, x0 + bw, top + h), 34, fill=(10, 132, 255) if who == "me" else (58, 58, 64))
        yy = top + pad
        if att:
            dr.rounded_rectangle((x0 + 16, yy, x0 + bw - 16, yy + 92), 18, fill=(255, 255, 255))
            dr.rectangle((x0 + 30, yy + 14, x0 + 80, yy + 78), fill=(229, 57, 53))
            dr.text((x0 + 55, yy + 46), "PDF", font=font(18, "Bold"), fill=(255, 255, 255), anchor="mm")
            dr.text((x0 + 96, yy + 30), att[0], font=fit(dr, att[0], 30, bw - 130, lambda s: font(s, "Semibold")), fill=(20, 20, 30), anchor="lm")
            dr.text((x0 + 96, yy + 66), att[1], font=font(26, "Regular"), fill=(110, 110, 125), anchor="lm")
            yy += 110
        for r in rows:
            dr.text((x0 + pad, yy + lh / 2), r, font=f, fill=(255, 255, 255), anchor="lm")
            yy += lh
    if sp.get("typing"):
        dr.rounded_rectangle((24, 1290 - 140, 164, 1290 - 64), 38, fill=(58, 58, 64))
        for i in range(3):
            dr.ellipse((52 + i * 32, 1290 - 114, 76 + i * 32, 1290 - 90), fill=(160, 160, 170))
    im.save(f"{out}/{nm}.png")


def off(nm, sp):
    """A monitor with no power: glass, nearly black."""
    Image.new("RGB", (W, H), (6, 7, 10)).save(f"{out}/{nm}.png")


KIND = dict(code=code, term=term, page=page, mail=mail, phone=phone, chat=chat, off=off)
for nm, sp in S.items():
    KIND[sp["kind"]](nm, sp)
Image.new("RGB", (600, 1290), (6, 7, 10)).save(f"{out}/phone_off.png")
print("screens", sorted(os.listdir(out)))
