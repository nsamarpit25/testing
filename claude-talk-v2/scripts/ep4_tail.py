"""Episode 4: Cleo's added closing line, voiced in context (the last exchange plus her new line, same voices and scene
notes as the main take) so it matches the take; only her last turn is cut out and used.
python3 scripts/ep4_tail.py <take numbers...>   -> output/ep4_takes/tail<N>.wav
"""
import base64, json, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import ep4_onecall as oc

PROMPT = oc.PROMPT.split("THE SCENE, END TO END")[0] + """THE SCENE
Late at night in a dim room. Cleo's app has just used up its whole daily database quota by accident, and her phone says
reads are blocked until tomorrow. A short comedy, played completely real, like two friends.
1. Cleo, small, hopeful and pleading.
2. Claude, gently deadpan, kind, a dry little smile in his voice.
3. A medium pause. Cleo sighs, deflated, then lands it with a small self-mocking laugh in her voice: she had thought her app went viral, and the only "user" was herself.

DIRECTOR'S NOTES
Natural, at a normal conversational pace; the comedy comes from the timing. Leave a short beat at every [medium pause] and at the "..."; never read the bracketed tags aloud. Speak every word of the dialogue exactly as written, nothing added."""
TURNS = [
    ("Cleo", "Claude... can you rewind the database too?"),
    ("Claude", "I can rewind my edits, Cleo. Not the calendar."),
    ("Cleo", "[medium pause] Great. I finally went viral... and my only fan was me."),
]


def take(n, tok):
    body = {"input": {"prompt": PROMPT, "text": "\n".join(f"{w}: {t}" for w, t in TURNS)},
            "voice": {"languageCode": "en-US", "modelName": oc.MODEL,
                      "multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [{"speakerAlias": a, "speakerId": v} for a, v in oc.VOICES.items()]}},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "x-goog-user-project": oc.PROJECT})
    try:
        open(f"output/ep4_takes/tail{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"tail{n} OK"
    except urllib.error.HTTPError as e:
        return f"tail{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    tok = oc.token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(n, tok), sys.argv[1:]):
            print(r, flush=True)
