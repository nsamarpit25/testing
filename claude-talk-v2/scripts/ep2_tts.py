"""Voice every line with Gemini TTS, one request per line; then transcribe each clip back and check its length.

Delivery notes go only in the DIRECTOR'S NOTES part of the prompt, the TRANSCRIPT holds just the words to say.
python3 scripts/ep2_tts.py [lines e.g. 3,5]   (needs a gcloud application-default login)
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request
D = "audio/ep2"
VOICE = {"cleo": "Leda", "claude": "Achird"}
PROFILE = {
    "cleo": "Cleo, a young woman software developer in her mid twenties. Soft, natural, conversational voice.",
    "claude": "Claude, a young man's voice, calm, warm and gently dry-witted. Never theatrical.",
}
SCENE = ("Late at night at her desk. Cleo, a junior developer, has just realised she leaked her API key and is talking with "
         "Claude, a small companion sitting next to her on the desk. Natural, quick back-and-forth, comedic but real.")
LINES = [
 ("cleo", "Frozen, quiet dread, slow; a small pause after the first word.", "Claude… did I just push my API key to the repo?"),
 ("claude", "Calm and matter-of-fact, a little gentle.", "Yeah. You did."),
 ("cleo", "Pleading and hopeful, a bit fast.", "Please tell me the repo is private."),
 ("claude", "Dry and deadpan, a little weight on the word very.", "It's public. Very public."),
 ("cleo", "Small, scared voice.", "How public?"),
 ("claude", "Deadpan.", "Ninety stars."),
 ("cleo", "First word shocked, then confused and offended, rising.", "Ninety? I don't even have friends. Who is starring my repo?"),
 ("claude", "Dry and quick, a touch ominous. Say bots clearly, rhymes with dots.", "Bots. Very fast bots."),
 ("cleo", "Panicking, fast, voice rising at the end.", "Claude. I just got a bill for two thousand dollars. What do I do?"),
 ("claude", "Urgent and firm, quick, not shouting.", "Revoke the key. Right now. Fast."),
 ("cleo", "Out of breath and fast, then hopeful and relieved at the end.", "Done. Revoked it, made a new one, pushed again. We're okay now, right?"),
 ("cleo", "Confused and worried, slower.", "Why are the stars going up again?"),
 ("claude", "Gentle and deadpan.", "You pushed the new key too. Your .env file was never in your .gitignore."),
 ("claude", "Calm, warm, reassuring and confident.", "Don't worry. I've got this from here."),
 ("claude", "Calm and efficient, reporting back, warm.", "I've revoked both keys, made the repo private, and opened a support ticket about the bill."),
 ("cleo", "Tired, defeated, half joking.", "Can you also take my keyboard away from me?"),
 ("claude", "Dry, matter-of-fact, gently amused.", "I don't have arms, Cleo."),
]
# Voices come from Cloud Text-to-Speech (Gemini-TTS) on the Google Cloud project, signed in with
# `gcloud auth application-default login`; usage is paid from that project's credits.
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-2.5-pro-tts"  # one model only, so every line has the same voice
_tok = [None, 0]


def token():
    if time.time() - _tok[1] > 1800:
        _tok[0] = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"]).decode().strip()
        _tok[1] = time.time()
    return _tok[0]


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "Authorization": f"Bearer {token()}",
                                                                  "x-goog-user-project": PROJECT})
    return json.load(urllib.request.urlopen(req, timeout=180))


def tts(who, how, text):
    prompt = f"AUDIO PROFILE: {PROFILE[who]} THE SCENE: {SCENE} DIRECTOR'S NOTES: Style: {how}"
    text = text.replace(".gitignore", "git ignore").replace(".env", "dot env")  # say it the way a developer would
    body = {"input": {"prompt": prompt, "text": text},
            "voice": {"languageCode": "en-US", "name": VOICE[who], "modelName": MODEL},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    for attempt in range(5):
        try:
            d = post("https://texttospeech.googleapis.com/v1/text:synthesize", body)
            print(f"   via {MODEL}", flush=True)
            return base64.b64decode(d["audioContent"])
        except urllib.error.HTTPError as e:
            msg = e.read().decode()
            if e.code in (429, 500, 503):
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(msg[:400])
    raise RuntimeError("TTS kept failing")


def transcribe(wav):
    data = base64.b64encode(open(wav, "rb").read()).decode()
    body = {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": "audio/wav", "data": data}},
                                                    {"text": "Transcribe this speech verbatim. Output only the words spoken."}]}]}
    try:
        d = post(f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/gemini-2.5-flash:generateContent", body)
        return d["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (urllib.error.HTTPError, KeyError, IndexError):
        return "?"


def words(s):
    return re.findall(r"[a-z']+", s.lower().replace("’", "'"))


os.makedirs(D, exist_ok=True)
only = {int(x) for x in sys.argv[1].split(",")} if len(sys.argv) > 1 else None
rows = []
for i, (who, how, text) in enumerate(LINES, 1):
    wav = f"{D}/l{i:02d}.wav"
    if (only and i in only) or (not only and not os.path.exists(wav)):
        pcm = tts(who, how, text)
        open(f"{D}/l{i:02d}.pcm", "wb").write(pcm)
        # trim the silence the model leaves at both ends, keep a few ms of air
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", f"{D}/l{i:02d}.pcm",
                        "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
                               "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
                        "-ar", "48000", wav], check=True)
        time.sleep(3)
    if not os.path.exists(wav):
        continue
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]))
    n = len(words(text))
    if only and i not in only:  # checked on an earlier run
        rows.append(f"{i:02d} {who} {dur:.3f}")
        continue
    heard = transcribe(wav)
    ok = words(heard) == words(text)
    wps = n / dur
    flag = "" if ok and 1.6 <= wps <= 4.2 else "  <-- CHECK"
    print(f"{i:02d} {who:6s} {dur:5.2f}s {n:2d}w {wps:4.2f}w/s match={ok} | {heard}{flag}", flush=True)
    rows.append(f"{i:02d} {who} {dur:.3f}")
open(f"{D}/durs.txt", "w").write("\n".join(rows) + "\n")
open(f"{D}/lines.tsv", "w").write("".join(f"{w}\t{t}\n" for w, _, t in LINES))
