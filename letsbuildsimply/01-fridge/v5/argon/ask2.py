"""python3 ask2.py <prompt.md> <reply.md> vid1.mp4 [vid2.mp4 ...]: gemini-4-argon with several videos inline (labelled VIDEO 1, 2...)."""
import base64, json, subprocess, sys, time, urllib.request, urllib.error
PROJECT, MODEL = "project-bebe18d3-83f6-445f-bdd", "gemini-4-argon"
prompt, out, vids = sys.argv[1], sys.argv[2], sys.argv[3:]
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
parts = []
for i, v in enumerate(vids, 1):
    parts += [{"text": f"VIDEO {i}:"}, {"inlineData": {"mimeType": "video/mp4", "data": base64.b64encode(open(v, "rb").read()).decode()}, "videoMetadata": {"fps": 2}}]
parts.append({"text": open(prompt).read()})
body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": 65536}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
t0 = time.time()
for attempt in range(4):
    try:
        r = json.load(urllib.request.urlopen(req, timeout=1200)); break
    except urllib.error.HTTPError as e:
        if e.code == 429 and attempt < 3: time.sleep(40); continue
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")
text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought"))
open(out, "w").write(text)
print(f"{time.time()-t0:.0f}s, finish={r['candidates'][0].get('finishReason')}")
