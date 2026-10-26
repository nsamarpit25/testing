"""Per-line Gemini TTS (Cloud TTS, same voices as scripts/epx_onecall.py) for a three.js episode.
python3 three/tts.py three/ep_test   reads <dir>/lines.json {"prompt": "...", "lines": [["Cleo", "..."], ...]} -> <dir>/lNN.wav
"""
import base64, json, subprocess, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
VOICES = {"Cleo": "Leda", "Claude": "Achird"}

d = sys.argv[1]
E = json.load(open(f"{d}/lines.json"))
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"]).decode().strip()


def line(i):
    who, text = E["lines"][i]["who"], E["lines"][i]["say"]
    body = {"input": {"prompt": f"{E['prompt']}\nThis line is spoken by {who}.", "text": text},
            "voice": {"languageCode": "en-US", "name": VOICES[who], "modelName": "gemini-2.5-pro-tts"},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT})
    open(f"{d}/l{i + 1:02d}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
    return f"l{i + 1:02d} {who}: {text}"


with ThreadPoolExecutor(4) as ex:
    for r in ex.map(line, range(len(E["lines"]))):
        print(r, flush=True)
