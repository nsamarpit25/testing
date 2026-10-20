"""Episode 6: the whole dialogue in ONE multi-speaker Gemini-TTS call (Cloud Text-to-Speech, paid from the project's credits),
with the scene described end to end so the model can act it, pauses at the story beats, and strict Cleo/Claude turn-taking
(back-to-back lines of one speaker are merged into one turn, so the model never has to guess who speaks).
python3 scripts/ep6_onecall.py <take numbers...>   -> output/ep6_takes/take<N>.wav
"""
import base64, json, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"
PROMPT = """AUDIO PROFILE
Cleo: a young woman software developer in her mid twenties. Soft, natural, conversational voice. Real and understated, never cartoonish.
Claude: a young man's voice. Calm, warm and gently dry-witted, never theatrical. Few words, every one of them kind.

THE SCENE, END TO END
Late evening in her quiet room, lit by a desktop computer monitor. Cleo sits at her desk; Claude is a small companion standing next to her on the desk. She has made a silly webpage with one big button that plays a terrible trumpet noise. A small, tender moment between two friends, played completely real.
1. Cleo, trying to keep a straight face, a little shy, showing off something silly.
2. Claude, curious, warm.
3. A long pause while the terrible trumpet plays. Then Claude, delighted but deadpan, asking for more.
4. Cleo, laughing it off, a little embarrassed, moving on.
5. Claude, quickly, gently stopping her.
6. Cleo, amused, a bit puzzled.
7. Claude, simply, softly.
8. Cleo, quieter now, fond, a little wistful, remembering.
9. Claude, light, a small joke.
10. Cleo, soft, a half smile.
11. Claude, gently, a real question.
12. Cleo, after a beat, quiet and honest, a little sad, almost to herself.
13. Claude, completely serious, deadpan, the sweetest dare.
14. Cleo, the smallest smile spreading in her voice, mischievous.
15. A long pause while the even worse trumpet plays. Cleo, breaking into a real, helpless, unguarded laugh, saying the line through the laughter.
16. Claude, warm, quiet, a smile in his voice.

DIRECTOR'S NOTES
Unhurried and intimate, like late at night. Let the quiet lines breathe. Leave real silence at every [long pause] and a short beat at every [medium pause] and at every "..."; never read the bracketed tags aloud. Speak every word of the dialogue exactly as written, nothing added."""
TURNS = [
 ('Cleo', 'I spent three hours making this.'),
 ('Claude', 'Show me. [long pause] Again.'),
 ('Cleo', 'Okay. Back to something useful.'),
 ('Claude', "Wait. I wasn't done."),
 ('Cleo', 'It only does that.'),
 ('Claude', 'I know.'),
 ('Cleo', 'I used to make stuff like this all the time.'),
 ('Claude', 'Bad trumpets?'),
 ('Cleo', 'Things nobody asked for.'),
 ('Claude', "Why'd you stop?"),
 ('Cleo', '[medium pause] ...Started needing everything to go on my résumé.'),
 ('Claude', 'Can you make it worse?'),
 ('Cleo', "Oh, definitely. [long pause] That's disgusting."),
 ('Claude', 'Keep it.'),
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
        open(f"output/ep6_takes/take{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"take{n} OK"
    except urllib.error.HTTPError as e:
        return f"take{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    tok = token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(n, tok), sys.argv[1:]):
            print(r, flush=True)
