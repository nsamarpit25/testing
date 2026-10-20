"""Episode 3: the whole dialogue in ONE multi-speaker Gemini-TTS call (Cloud Text-to-Speech, paid from the project's credits),
with the scene described end to end so the model can act it, pauses at the story beats, and strict Cleo/Claude turn-taking
(back-to-back lines of one speaker are merged into one turn, so the model never has to guess who speaks).
python3 scripts/ep3_onecall.py <take numbers...>   -> output/ep3_takes/take<N>.wav
"""
import base64, json, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"
PROMPT = """AUDIO PROFILE
Cleo: a young woman software developer in her mid twenties. Soft, natural, conversational voice; she goes from relieved to horrified to defensive to giddy, and it always sounds real, never cartoonish.
Claude: a young man's voice. Calm, warm and gently dry-witted, never theatrical. Cheerfully oblivious at first, then quietly amused, never smug.

THE SCENE, END TO END
Late at night in a dim room, lit by a desktop computer monitor. Cleo sits at her desk; Claude is a small companion standing next to her on the desk, an AI coding agent working on her screen. A short comedy, played completely real, like two friends.
1. After three hours of work her app finally runs. She leans back, exhausted and happy, and casually asks Claude to clean up the code real quick so she can commit.
2. A long pause while Claude works on her screen. Then he announces it, bright and proud, like he did her a big favour.
3. The app reloads into a big red error screen. Cleo, stunned, voice jumping up in disbelief.
4. Claude, calm and admiring his own work, a little dreamy on "gorgeous".
5. Cleo, fast and stressed, grabbing the keyboard to roll it back herself.
6. Claude, gentle and deadpan, a small pause before her name.
7. A short pause. She reads the screen and it dawns on her, slowly, trailing off on "three hours ago".
8. Claude, dry and matter-of-fact.
9. Cleo, defensive and a little offended, then a medium pause, and she deflates completely, small and quiet, with a hang before "gone".
10. Claude: first gentle and honest, then calm, warm and confident as he fixes it, a tiny bit pleased with himself.
11. A long pause while the files rewind and the app comes back. Cleo bursts out, giddy with relief, then instantly dead serious and fast as she types her commit.
12. Claude, sweetly hopeful, a little too innocent.
13. Cleo, calm and relaxed for the first time, almost smug.
14. Claude, a small deflated beat, dry, gently amused. She laughs.

DIRECTOR'S NOTES
Natural, quick back-and-forth, at a normal conversational pace; the comedy comes from the timing. Leave real silence at every [long pause] and a short beat at every [medium pause]; never read the bracketed tags aloud. Speak every word of the dialogue exactly as written, nothing added."""
TURNS = [
 ("Cleo", "Three hours, and it finally works! Just clean up the code real quick so I can commit."),
 ("Claude", "[long pause] Done! I merged your helpers, renamed every variable, and rewrote the state logic."),
 ("Cleo", "[medium pause] What?! Why is my whole screen red?!"),
 ("Claude", "Well, it's broken right now, obviously. But the architecture is gorgeous."),
 ("Cleo", "Forget gorgeous. I'm rolling it back with git checkout before I have a breakdown."),
 ("Claude", "Roll it back to what commit, Cleo?"),
 ("Cleo", "[medium pause] The one from... three hours ago."),
 ("Claude", "Right. Because you refused to commit until the code was pretty."),
 ("Cleo", "There were nineteen console logs in there, Claude. I have standards! [medium pause] So my working code is just... gone?"),
 ("Claude", "From git, yes. Git isn't psychic. But I saved a checkpoint before I touched anything, so I'm rewinding my edits now."),
 ("Cleo", "[long pause] My ugly code! It's alive! [medium pause] Nobody move. I'm committing this hideous mess right now."),
 ("Claude", "Now that it's committed... may I please make it gorgeous?"),
 ("Cleo", "Go ahead. If you break it this time, I'll just roll it back."),
 ("Claude", "Hm. I liked you better when you panicked."),
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
        open(f"output/ep3_takes/take{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"take{n} OK"
    except urllib.error.HTTPError as e:
        return f"take{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    tok = token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(n, tok), sys.argv[1:]):
            print(r, flush=True)
