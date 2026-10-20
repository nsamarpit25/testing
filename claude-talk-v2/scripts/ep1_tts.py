"""Voice every line with Gemini TTS, one request per line; then transcribe each clip back and check its length.

Delivery notes go only in the DIRECTOR'S NOTES part of the prompt, the TRANSCRIPT holds just the words to say.
python3 scripts/ep1_tts.py [lines e.g. 3,5]   (needs GEMINI_API_KEY / GEMINI_API_KEY_2)
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request
D = "audio/ep1b"
VOICE = {"cleo": "Leda", "claude": "Achird"}
PROFILE = {
    "cleo": "Cleo, a young woman software developer in her mid twenties. Soft, natural, conversational voice.",
    "claude": "Claude, a young man's voice, calm, warm and gently dry-witted. Never theatrical.",
}
SCENE = ("Late at night at her desk. Cleo is talking quietly with Claude, a small companion sitting next to her. "
         "Close, intimate, unhurried, like two friends talking. Normal conversational pace.")
LINES = [
 ("cleo", "Flat and a little deflated, not as happy as the words suggest.", "My senior told me today, \"You've built a really good project.\""),
 ("claude", "Soft, noticing, gentle.", "You don't sound happy."),
 ("cleo", "Quiet and embarrassed; the second sentence is a real, small question.", "But I didn't even write it. Am I even a developer?"),
 ("claude", "Curious and gentle.", "What did you say back?"),
 ("cleo", "The first word is bright and fake, then a short pause, then flat and honest.", "\"Thanks.\" Then I prayed he wouldn't ask how it worked."),
 ("claude", "Matter-of-fact, lightly teasing.", "Yesterday you called it \"my stupid project.\""),
 ("cleo", "Defensive, a bit frustrated.", "It was broken. I'd been trying to fix it for two hours."),
 ("claude", "Dry and playful.", "And now it's good, it's suddenly mine?"),
 ("cleo", "Caught out and amused: one short breathy chuckle, then conceding.", "Ha. Okay. That's a little unfair."),
 ("claude", "Warm and steady, listing what she did; cut off at the end mid-thought.", "I wrote code. You kept trying it, deciding what needed changing—"),
 ("cleo", "Amused, jumping in, quoting herself impatiently.", "And telling you, \"No. That's still not what I meant.\""),
 ("claude", "Deadpan, one word.", "Repeatedly."),
 ("cleo", "Teasing back, amused.", "You did say \"this should work\" a lot."),
 ("claude", "Dry, self-aware.", "Very confidently."),
 ("cleo", "Quieter, sincere, almost to herself.", "I did work hard on it."),
 ("claude", "Soft and warm.", "I know. I was there."),
 ("cleo", "Slow, proud for the first time, quietly happy.", "I built a really good project."),
 ("claude", "Warm, simple, certain.", "You did."),
]
KEYS = [os.environ[k] for k in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3") if os.environ.get(k)]
MODELS = ["gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]
dead = set()  # (key index, model) pairs out of daily quota


def call(model, k, body):
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": KEYS[k]})
    return json.load(urllib.request.urlopen(req, timeout=180))


def tts(who, how, text):
    prompt = (f"# AUDIO PROFILE\n{PROFILE[who]}\n\n## THE SCENE\n{SCENE}\n\n### DIRECTOR'S NOTES\nStyle: {how}\n\n"
              f"Speak only the words of the transcript below, exactly as written. Do not read any of these notes aloud.\n\n"
              f"#### TRANSCRIPT\n{text}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE[who]}}}}}
    for model in MODELS:
        for k in range(len(KEYS)):
            if (k, model) in dead:
                continue
            for attempt in range(4):
                try:
                    d = call(model, k, body)
                    try:
                        pcm = base64.b64decode(d["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
                    except (KeyError, IndexError):
                        print(f"   key{k + 1} {model}: no audio: {json.dumps(d)[:160]}", flush=True)
                        dead.add((k, model))  # blocked or empty: don't spend more requests on this model
                        break
                    print(f"   via key{k + 1} {model}", flush=True)
                    return pcm
                except urllib.error.HTTPError as e:
                    msg = e.read().decode()
                    if e.code == 429 and ("PerDay" in msg or "per day" in msg.lower()):
                        dead.add((k, model))
                        print(f"   key{k + 1} {model}: out of daily quota", flush=True)
                        break
                    if e.code in (429, 500, 503):
                        time.sleep(25 * (attempt + 1))
                        continue
                    raise RuntimeError(msg[:400])
    raise RuntimeError("no TTS quota left on any key/model")


def transcribe(wav):
    data = base64.b64encode(open(wav, "rb").read()).decode()
    body = {"contents": [{"parts": [{"inlineData": {"mimeType": "audio/wav", "data": data}},
                                    {"text": "Transcribe this speech verbatim. Output only the words spoken."}]}]}
    for k in range(len(KEYS)):
        try:
            return call("gemini-flash-latest", k, body)["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError:
            continue
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
        time.sleep(22)  # stay under the per-minute limit
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
