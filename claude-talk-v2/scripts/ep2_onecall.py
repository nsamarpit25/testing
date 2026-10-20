"""Episode 2: the whole dialogue in ONE multi-speaker Gemini-TTS call (Cloud Text-to-Speech, paid from the project's credits),
with the scene described end to end so the model can act it, pauses at the story beats, and strict Cleo/Claude turn-taking
(back-to-back lines of one speaker are merged into one turn, so the model never has to guess who speaks).
python3 scripts/ep2_onecall.py <take numbers...>   -> output/ep2_takes/take<N>.wav
"""
import base64, json, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"
PROMPT = """AUDIO PROFILE
Cleo: a young woman software developer in her mid twenties. Soft, natural, conversational voice; she gets more and more panicked as the scene goes on, but it always sounds real, never cartoonish.
Claude: a young man's voice. Calm, warm and gently dry-witted, never theatrical. Always one step ahead of her, quietly amused, never smug.

THE SCENE, END TO END
Late at night in a dim room, lit only by a computer monitor. Cleo sits at her desk; Claude is a small companion sitting next to her on the desk. A short comedy, played completely real, like two friends.
1. Her terminal shows she has just run git push, and the .env file with her live API key went with it. She freezes, then slowly asks Claude, full of quiet dread, with a small hang on his name. Claude confirms it, calm and gentle.
2. She pleads, hoping the repo is private. Claude, dry and deadpan: it's public, with a little weight on "very". In a tiny, scared voice she asks how public. The monitor shows the repo page: ninety stars. Claude says it flatly.
3. She is shocked, then confused and offended: she doesn't even have friends, so who is starring her repo? Claude, dry and quick, a touch ominous: bots, as in robots.
4. A long silence. Then her phone buzzes on the desk and lights up with a billing alert: two thousand dollars. She grabs it, stares, and panics at Claude, fast, voice rising at the end.
5. Claude is urgent and firm, quick, not shouting: revoke the key, now. Then a long stretch where she frantically mashes the keyboard, loud clattering keys, revoking the key, making a new one, committing and pushing again.
6. Out of breath and fast, she reports it done, then turns hopeful and relieved: we're okay now, right?
7. A long pause. On the monitor the star counter starts ticking up again, tick, tick, tick. She notices, slower, confused and worried.
8. Claude, gentle and deadpan, explains it: she pushed the new key too, because her .env file was never in her .gitignore. She facepalms.
9. A short beat, then Claude, calm, warm, reassuring and confident, takes over: don't worry, he's got this.
10. A long pause while Claude works: on the monitor his checklist ticks off item by item with little dings. Then he reports back, calm and efficient, warm, a tiny bit proud.
11. Cleo, tired, defeated and half joking, pushes her keyboard away. Claude, dry, matter-of-fact and gently amused, lands the last line. She laughs.

DIRECTOR'S NOTES
Natural, quick back-and-forth, at a normal conversational pace; the comedy comes from the timing. Leave real silence at every [long pause] and a short beat at every [medium pause]; never read the bracketed tags aloud. Speak every word of the dialogue exactly as written, nothing added."""
TURNS = [
 ("Cleo", "Claude… did I just push my API key to the repo?"),
 ("Claude", "Yeah. You did."),
 ("Cleo", "Please tell me the repo is private."),
 ("Claude", "It's public. Very public."),
 ("Cleo", "How public?"),
 ("Claude", "Ninety stars."),
 ("Cleo", "Ninety? I don't even have friends. Who is starring my repo?"),
 ("Claude", "Bots. Very fast bots."),
 ("Cleo", "[long pause] Claude. I just got a bill for two thousand dollars. What do I do?"),
 ("Claude", "Revoke the key. Right now. Fast."),
 ("Cleo", "[long pause] Done. Revoked it, made a new one, pushed again. We're okay now, right? [long pause] Why are the stars going up again?"),
 ("Claude", "You pushed the new key too. Your dot env file was never in your git ignore. [medium pause] Don't worry. I've got this from here. "
            "[long pause] I've revoked both keys, made the repo private, and opened a support ticket about the bill."),
 ("Cleo", "Can you also take my keyboard away from me?"),
 ("Claude", "I don't have arms, Cleo."),
]
VOICES = {"Cleo": "Leda", "Claude": "Achird"}


def token():
    return subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"]).decode().strip()


def take(n, tok):
    body = {"input": {"prompt": PROMPT, "text": "\n".join(f"{w}: {t}" for w, t in TURNS)},
            "voice": {"languageCode": "en-US", "modelName": MODEL,
                      "multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [{"speakerAlias": a, "speakerId": v} for a, v in VOICES.items()]}},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT})
    try:
        open(f"output/ep2_takes/take{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"take{n} OK"
    except urllib.error.HTTPError as e:
        return f"take{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    tok = token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(n, tok), sys.argv[1:]):
            print(r, flush=True)
