"""Episode 5, variant C (new opening, lines 1-3; the rest as in ep5_onecall). Episode 5: the whole dialogue in ONE multi-speaker Gemini-TTS call (Cloud Text-to-Speech, paid from the project's credits),
with the scene described end to end so the model can act it, pauses at the story beats, and strict Cleo/Claude turn-taking
(back-to-back lines of one speaker are merged into one turn, so the model never has to guess who speaks).
python3 scripts/ep5c_onecall.py <take numbers...>   -> output/ep5c_takes/take<N>.wav
"""
import base64, json, subprocess, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"
PROMPT = """AUDIO PROFILE
Cleo: a young woman software developer in her mid twenties. Soft, natural, conversational voice; she goes from exasperated to defensive to sheepish to horrified to quietly defeated, and it always sounds real, never cartoonish.
Claude: a young man's voice. Calm, warm and gently dry-witted, never theatrical. Patient, a little deadpan, never smug.

THE SCENE, END TO END
Late evening in her room, lit by a desktop computer monitor. Cleo sits at her desk; Claude is a small companion standing next to her on the desk, an AI coding agent working on her screen. A short comedy, played completely real, like two friends.
1. Cleo, exasperated, at the end of her rope, staring at a button on her screen, half joking.
2. Claude, calm, mildly curious.
3. Cleo, building up, betrayed by a button, a little unhinged.
4. Claude, gentle, the obvious question.
5. Cleo, defensive, rapid-fire, each claim faster and louder than the last.
6. Claude, a beat, dry and quietly alarmed.
7. Cleo, flustered, pointing at the screen, then accusing him.
8. Claude, calm, unbothered.
9. Cleo, suddenly embarrassed, quick.
10. Claude, slow and deadpan, reading three folder names out loud one by one, a tiny pause between each.
11. Cleo, defensive, too fast.
12. Claude, calm and patient, matter-of-fact, then a short beat, then he explains, simply.
13. Cleo, confused, protesting.
14. Claude, patient and clear.
15. Cleo, slowly, the horror dawning.
16. Claude, gentle and deadpan.
17. A long pause while the page loads. Then Cleo, very small and quiet: she sees the result.
18. Claude, dry, a little admiring.
19. Cleo, small and hopeful.
20. Claude, kind, with a dry little smile in his voice.
21. A medium pause. Cleo, flat and defeated, resigned, with a tiny self-mocking edge.

DIRECTOR'S NOTES
Natural, quick back-and-forth, at a normal conversational pace; the comedy comes from the timing. Leave real silence at every [long pause] and a short beat at every [medium pause] and at every "..."; never read the bracketed tags aloud. Say "Vite" as "veet". Say "localhost" as "local host". Speak every word of the dialogue exactly as written, nothing added."""
TURNS = [
 ("Cleo", "Claude. Either my CSS is haunted, or I am."),
 ("Claude", "What happened?"),
 ("Cleo", "I made this button green eleven times. It's been blue for forty minutes. It's doing it on purpose."),
 ("Claude", "Did you save?"),
 ("Cleo", "I saved! I hard-refreshed! I switched browsers! I put important on everything!"),
 ("Claude", "Everything?"),
 ("Cleo", "I even changed the text to PLEASE WORK. Look! It still says Add task! You broke CSS."),
 ("Claude", "Let me look at your terminals."),
 ("Cleo", "Wait. Don't judge the folder names."),
 ("Claude", "My app... my app v two... my app final."),
 ("Cleo", "They're backups!"),
 ("Claude", "They're all running. Three copies. Three servers. [medium pause] You're editing final. Your browser is showing the original."),
 ("Cleo", "But it says localhost!"),
 ("Claude", "Different ports. When fifty-one seventy-three was taken, Vite just took the next one."),
 ("Cleo", "So every fix I made went... somewhere else?"),
 ("Claude", "Every single one. Open fifty-one seventy-five."),
 ("Cleo", "[long pause] ...Oh no."),
 ("Claude", "Forty minutes of fixes. They all worked."),
 ("Cleo", "Can we go back to blue?"),
 ("Claude", "Sure. Which folder?"),
 ("Cleo", "[medium pause] ...I'm calling the next one my app final final."),
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
        open(f"output/ep5c_takes/take{n}.wav", "wb").write(base64.b64decode(json.load(urllib.request.urlopen(req, timeout=300))["audioContent"]))
        return f"take{n} OK"
    except urllib.error.HTTPError as e:
        return f"take{n} {e.code} {e.read().decode()[:300]}"


if __name__ == "__main__":
    tok = token()
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(lambda n: take(n, tok), sys.argv[1:]):
            print(r, flush=True)
