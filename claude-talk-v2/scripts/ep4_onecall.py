"""Episode 4: the whole dialogue in ONE multi-speaker Gemini-TTS call (Cloud Text-to-Speech, paid from the project's credits),
with the scene described end to end so the model can act it, pauses at the story beats, and strict Cleo/Claude turn-taking
(back-to-back lines of one speaker are merged into one turn, so the model never has to guess who speaks).
python3 scripts/ep4_onecall.py <take numbers...>   -> output/ep4_takes/take<N>.wav
"""
import base64, json, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"
PROMPT = """AUDIO PROFILE
Cleo: a young woman software developer in her mid twenties. Soft, natural, conversational voice; she goes from thrilled to confused to defensive to panicked to relieved to crushed, and it always sounds real, never cartoonish.
Claude: a young man's voice. Calm, warm and gently dry-witted, never theatrical. Patient, a little deadpan, never smug.

THE SCENE, END TO END
Late at night in a dim room, lit by a desktop computer monitor. Cleo sits at her desk; Claude is a small companion standing next to her on the desk, an AI coding agent working on her screen. A short comedy, played completely real, like two friends.
1. Cleo glances at her phone and lights up, thrilled, fast and excited: she thinks her app has gone viral.
2. Claude, gentle and deadpan, a small hesitation after her name.
3. A short pause. Cleo, her excitement fading into confusion.
4. Claude, calm and patient, explaining.
5. Cleo, small and quiet, it slowly dawns on her.
6. Claude, matter-of-fact, kind, a tiny pause before the verdict.
7. Cleo, defensive and flustered, a bit louder.
8. Claude, calm, simply pointing it out.
9. A long pause while she stares at the screen. Then Cleo, horrified, voice jumping up.
10. Claude, calm and curious, a little suspicious on the question.
11. Cleo, defensive and proud of herself, a bit too confident.
12. Claude, patient and clear, walking her through it, landing dry on "Forever."
13. Cleo, panicked, fast, pleading.
14. A long pause while Claude fixes it on her screen. Then Claude, calm and a little pleased, then gently wise for the advice.
15. Cleo, exhaling with relief, relaxed, almost smug. Then a long pause: her phone buzzes. She reads the notification aloud, flat and slow, dread creeping in. Then a medium pause, and she turns to him, small, hopeful and pleading.
16. Claude, gently deadpan, kind, a dry little smile in his voice.

DIRECTOR'S NOTES
Natural, quick back-and-forth, at a normal conversational pace; the comedy comes from the timing. Leave real silence at every [long pause] and a short beat at every [medium pause]; never read the bracketed tags aloud. Say "DDoSing" as "dee-doss-ing" and "useEffect" as "use effect". Speak every word of the dialogue exactly as written, nothing added."""
TURNS = [
 ("Cleo", "Claude! Forty-five thousand database reads in three minutes! We're going viral!"),
 ("Claude", "Cleo... you haven't deployed it yet."),
 ("Cleo", "[medium pause] Then who's reading it?"),
 ("Claude", "Your app only runs on localhost. Every one of those reads came from this desk."),
 ("Cleo", "...From me?"),
 ("Claude", "From you. You're DDoSing yourself."),
 ("Cleo", "I'm not even touching anything! The page is just sitting there!"),
 ("Claude", "Look at the Network tab."),
 ("Cleo", "[long pause] Why is it counting like a slot machine?!"),
 ("Claude", "I wrote your useEffect with an empty array, so it fetched once. Did you touch it?"),
 ("Cleo", "I made it refresh whenever the tasks change. That's called being responsive!"),
 ("Claude", "So it fetches your tasks, gets a brand-new array, thinks the tasks changed, and fetches again. Forever."),
 ("Cleo", "Make it stop! Make it stop!"),
 ("Claude", "[long pause] Done. The empty array is back. One request. Next time, test with the Network tab open."),
 ("Cleo", "Phew. At least we caught it before it cost anything. [long pause] Daily read limit reached. Reads blocked until tomorrow. [medium pause] Claude... can you rewind the database too?"),
 ("Claude", "I can rewind my edits, Cleo. Not the calendar."),
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
        open(f"output/ep4_takes/take{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"take{n} OK"
    except urllib.error.HTTPError as e:
        return f"take{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    tok = token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(n, tok), sys.argv[1:]):
            print(r, flush=True)
