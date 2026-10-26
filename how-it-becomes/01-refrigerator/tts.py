"""Per-line Gemini TTS (Cloud TTS REST, gcloud ADC) -> audio/lNN_raw.wav, trimmed lNN.wav, voice.wav and lines.json.
python3 tts.py [--voice Puck] [--reuse]"""
import base64, json, subprocess, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
args = sys.argv[1:]
OUT = HERE / (args[args.index("--out") + 1] if "--out" in args else "audio")
PROJECT = "project-bebe18d3-83f6-445f-bdd"
VOICE = args[args.index("--voice") + 1] if "--voice" in args else "Charon"
STYLE = ("You are the narrator of a viral YouTube explainer: a deep, warm, low American male voice, calm and deadpan with a hint of dry humour. "
         "Punchy and clear, steady confident pace, slight emphasis on the key word of each sentence, a short beat between sentences, "
         "never rushed, never theatrical.")
LINES = json.load(open(HERE / "script.json"))["lines"]
GAP, LEAD, TEMPO = 0.22, 0.25, float(args[args.index("--tempo") + 1]) if "--tempo" in args else 1.15
OUT.mkdir(exist_ok=True)
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"]).decode().strip()


def tts(i):
    raw = OUT / f"l{i + 1:02d}_raw.wav"
    if "--reuse" in args and raw.exists():
        return
    body = {"input": {"prompt": STYLE, "text": LINES[i]["say"]},
            "voice": {"languageCode": "en-US", "name": VOICE, "modelName": "gemini-2.5-pro-tts"},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT})
    for k in range(6):
        try:
            raw.write_bytes(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
            return
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == 5:
                raise
            time.sleep(15 * (k + 1))


def trimmed(src, dst):
    af = f"silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,atempo={TEMPO}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-af", af, "-ar", "48000", "-ac", "1", str(dst)], check=True)
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)]))


with ThreadPoolExecutor(1) as ex:
    list(ex.map(tts, range(len(LINES))))
t, timed, parts = LEAD, [], []
for i, L in enumerate(LINES, 1):
    d = trimmed(OUT / f"l{i:02d}_raw.wav", OUT / f"l{i:02d}.wav")
    timed.append({**L, "start": round(t, 3), "end": round(t + d, 3)})
    parts.append((OUT / f"l{i:02d}.wav", t))
    t += d + L.get("gap", GAP)
(OUT / "lines.json").write_text(json.dumps(timed, indent=1))
cmd = ["ffmpeg", "-loglevel", "error", "-y"] + sum((["-i", str(p)] for p, _ in parts), [])
fl = "".join(f"[{k}]adelay={int(s * 1000)}:all=1[a{k}];" for k, (_, s) in enumerate(parts))
fl += "".join(f"[a{k}]" for k in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0,"
fl += f"highpass=f=70,loudnorm=I=-14:TP=-1.5:LRA=9,apad=whole_dur={t + 0.8:.2f}[o]"
subprocess.run(cmd + ["-filter_complex", fl, "-map", "[o]", "-ar", "48000", str(OUT / "voice.wav")], check=True)
for L in timed:
    print(f"{L['start']:5.2f}-{L['end']:5.2f}  {L['say']}")
print("total", round(t, 2))
