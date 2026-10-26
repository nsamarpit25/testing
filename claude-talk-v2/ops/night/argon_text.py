import json, subprocess, sys, urllib.request
PROJECT, MODEL = "project-bebe18d3-83f6-445f-bdd", "gemini-4-argon"
prompt, out = sys.argv[1:3]
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
body = {"contents": [{"role": "user", "parts": [{"text": open(prompt).read()}]}], "generationConfig": {"maxOutputTokens": 32768}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=900))
open(out, "w").write("".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought")))
print("ok", r.get("usageMetadata", {}).get("totalTokenCount"))
