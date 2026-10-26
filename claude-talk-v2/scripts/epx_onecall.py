"""Generic one-call multi-speaker Gemini TTS (as ep6_onecall.py), the prompt and turns read from <audio dir>/tts.json
({"prompt": "...", "turns": [["Cleo", "..."], ["Claude", "..."]]}).
python3 scripts/epx_onecall.py audio/ep7 1 2 3      -> output/ep7_takes/take<N>.wav
"""
import base64, json, os, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"
VOICES = {"Cleo": "Leda", "Claude": "Achird"}


def token():
    return subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"]).decode().strip()


def take(d, n, tok):
    T = json.load(open(f"{d}/tts.json"))
    ep = os.path.basename(d.rstrip("/"))
    os.makedirs(f"output/{ep}_takes", exist_ok=True)
    body = {"input": {"prompt": T["prompt"], "text": "\n".join(f"{w}: {t}" for w, t in T["turns"])},
            "voice": {"languageCode": "en-US", "modelName": MODEL,
                      "multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [{"speakerAlias": a, "speakerId": v} for a, v in VOICES.items()]}},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT})
    try:
        open(f"output/{ep}_takes/take{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"{ep} take{n} OK"
    except urllib.error.HTTPError as e:
        return f"{ep} take{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    d, ns = sys.argv[1], sys.argv[2:]
    tok = token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(d, n, tok), ns):
            print(r, flush=True)
