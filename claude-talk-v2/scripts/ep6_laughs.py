"""Episode 6: her short laughs between the lines (the snort after the second trumpet, the soft laugh after the third),
in Cleo's voice (Gemini TTS, voice Leda), a few takes each.  python3 scripts/ep6_laughs.py -> output/ep6_laughs/<name>_<k>.wav"""
import base64, json, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts")
from ep6_onecall import PROJECT, MODEL, token

ASK = {
    "snort": ("A young woman, alone at her desk late at night, trying to keep a straight face, suddenly can't hold it: one "
              "short surprised snort of laughter through her nose, then a tiny breathy giggle. Under two seconds. No words.",
              "[snorts a laugh] hm-hm."),
    "soft": ("A young woman, quietly amused and fond, a soft breathy laugh to herself, warm and gentle, under two seconds. "
             "No words.", "[soft laugh] heh-heh."),
}


def take(job, tok):
    name, k = job
    prompt, text = ASK[name]
    body = {"input": {"prompt": prompt, "text": text},
            "voice": {"languageCode": "en-US", "modelName": MODEL, "name": "Leda"},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT})
    try:
        data = base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"])
        open(f"output/ep6_laughs/{name}_{k}.wav", "wb").write(data)
        return f"{name}_{k} OK"
    except urllib.error.HTTPError as e:
        return f"{name}_{k} {e.code}"


if __name__ == "__main__":
    tok = token()
    jobs = [(n, k) for n in ASK for k in range(1, 4)]
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda j: take(j, tok), jobs):
            print(r, flush=True)
