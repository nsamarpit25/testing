"""Send a prompt file to gemini-4-argon on Vertex (ADC auth) and save the reply:  python3 scripts/ask_argon.py <prompt.md> <reply.md>"""
import json, subprocess, sys, time, urllib.request
PROJECT = "project-bebe18d3-83f6-445f-bdd"
MODEL = "gemini-4-argon"
prompt, out = sys.argv[1], sys.argv[2]
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
body = {"contents": [{"role": "user", "parts": [{"text": open(prompt).read()}]}], "generationConfig": {"maxOutputTokens": 65536}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
t0 = time.time()
try:
    r = json.load(urllib.request.urlopen(req, timeout=900))
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode()[:600]}")
text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought"))
open(out, "w").write(text)
print(f"{time.time()-t0:.0f}s, finish={r['candidates'][0].get('finishReason')}, usage={r.get('usageMetadata')}")
