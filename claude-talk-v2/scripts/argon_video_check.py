"""python3 ask_video.py <video.mp4> <prompt.md> <reply.md> [fps]: gemini-4-argon on Vertex with the whole video (audio included) inline."""
import base64, json, subprocess, sys, time, urllib.request, urllib.error
PROJECT, MODEL = "project-bebe18d3-83f6-445f-bdd", "gemini-4-argon"
v, prompt, out = sys.argv[1:4]; fps = float(sys.argv[4]) if len(sys.argv) > 4 else 10
tok = subprocess.check_output(["/opt/homebrew/bin/gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
url = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
parts = [{"inlineData": {"mimeType": "video/mp4", "data": base64.b64encode(open(v, "rb").read()).decode()}, "videoMetadata": {"fps": fps}},
         {"text": open(prompt).read()}]
body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": 65536, "mediaResolution": "MEDIA_RESOLUTION_HIGH"}}
req = urllib.request.Request(url, json.dumps(body).encode(), {"Authorization": f"Bearer {tok}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
t0 = time.time()
try:
    r = json.load(urllib.request.urlopen(req, timeout=1200))
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")
text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"] if not p.get("thought"))
open(out, "w").write(text)
print(f"{time.time()-t0:.0f}s, finish={r['candidates'][0].get('finishReason')}, usage={r.get('usageMetadata')}")
