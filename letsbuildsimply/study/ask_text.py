"""python3 ask_text.py <prompt.md> <reply.md>: text-only gemini-4-argon on Vertex."""
import json, subprocess, sys, time, urllib.request, urllib.error
PROJECT, MODEL = "project-bebe18d3-83f6-445f-bdd", "gemini-4-argon"
prompt, out = sys.argv[1:3]
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
body = {"contents": [{"role": "user", "parts": [{"text": open(prompt).read()}]}], "generationConfig": {"maxOutputTokens": 65536}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
t0 = time.time()
for attempt in range(4):
    try:
        r = json.load(urllib.request.urlopen(req, timeout=1200)); break
    except urllib.error.HTTPError as e:
        if e.code == 429 and attempt < 3: time.sleep(30); continue
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")
text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought"))
open(out, "w").write(text)
print(f"{time.time()-t0:.0f}s, finish={r['candidates'][0].get('finishReason')}")
