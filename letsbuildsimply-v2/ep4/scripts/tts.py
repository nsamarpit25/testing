"""python3 tts.py <script.json> <out.wav> [--voice Charon] [--model gemini-3.8-flash-tts]
One-take Gemini TTS on Vertex (global region, gcloud application-default credentials). Lines are joined with newlines.
3.x TTS models read a spoken-direction prefix aloud, so the style goes in one [bracketed] tag."""
import argparse, base64, json, subprocess, time, urllib.request, urllib.error, wave

PROJECT = "project-bebe18d3-83f6-445f-bdd"
STYLE = ("curious, conversational male narrator of a cinematic science short; crisp but unhurried cadence, about 140 words per minute, with a short breath between sentences; "
         "a genuinely puzzled, intrigued hook; a dry surprised beat on 'Now change the road'; precise and clear on the explanation; "
         "pronounce catenary as KAT-uh-nair-ee; quiet satisfied delight on the last line, landing 'part of the machine'")
p = argparse.ArgumentParser()
p.add_argument('script'); p.add_argument('out')
p.add_argument('--voice', default="Puck"); p.add_argument('--model', default='gemini-3.8-flash-tts')
a = p.parse_args()
text = '\n'.join(json.load(open(a.script))['lines'])
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{a.model}:generateContent"
body = {"contents": [{"role": "user", "parts": [{"text": f"[{STYLE}] {text}"}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": a.voice}}}}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT,
                                                               "Content-Type": "application/json"})
t0 = time.time()
for attempt in range(4):
    try:
        r = json.load(urllib.request.urlopen(req, timeout=600)); break
    except urllib.error.HTTPError as e:
        if e.code in (429, 500, 503) and attempt < 3: time.sleep(20); continue
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:600]}")
part = r["candidates"][0]["content"]["parts"][0]["inlineData"]
pcm = base64.b64decode(part["data"])
rate = int(part.get("mimeType", "rate=24000").split("rate=")[-1].split(";")[0]) if "rate=" in part.get("mimeType", "") else 24000
w = wave.open(a.out, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm); w.close()
print(f"{a.out}: {len(pcm) / 2 / rate:.1f}s, {time.time() - t0:.0f}s")
