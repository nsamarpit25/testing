"""Argon listens to TTS takes:  python3 ops/ep18/argon_audio.py <prompt.md> <out.md> take1.wav [take2.wav ...]"""
import base64, json, subprocess, sys, urllib.request
PROJECT, MODEL = "project-bebe18d3-83f6-445f-bdd", "gemini-4-argon"
prompt, out, wavs = sys.argv[1], sys.argv[2], sys.argv[3:]
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
parts = [{"text": open(prompt).read()}]
for i, w in enumerate(wavs, 1):
    parts += [{"text": f"TAKE {i} ({w.split('/')[-1]}):"}, {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(open(w, "rb").read()).decode()}}]
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
req = urllib.request.Request(url, json.dumps({"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": 32768}}).encode(),
                             {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=900))
open(out, "w").write("".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought")))
print("ok")
