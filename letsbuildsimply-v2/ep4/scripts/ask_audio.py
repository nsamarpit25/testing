"""python3 ask_audio.py <prompt.md> <reply.md> <a.wav> [b.wav ...]: gemini-4-argon on Vertex listens to the takes (in order) and answers."""
import base64, json, subprocess, sys, urllib.request
PROJECT, MODEL = "project-bebe18d3-83f6-445f-bdd", "gemini-4-argon"
prompt, out, files = sys.argv[1], sys.argv[2], sys.argv[3:]
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
parts = []
for i, f in enumerate(files, 1):
    parts += [{"text": f"TAKE {i}:"}, {"inlineData": {"mimeType": "audio/wav", "data": base64.b64encode(open(f, "rb").read()).decode()}}]
parts.append({"text": open(prompt).read()})
body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": 8192}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=600))
text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought"))
open(out, "w").write(text); print(text)
