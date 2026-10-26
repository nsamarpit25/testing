#!/usr/bin/env python3
"""One server for both accounts' reel pages, with a tab per account and a Refresh button that rebuilds the pages with
fresh Instagram numbers. HTTP Range support, so the videos play and seek (Safari and iPhone need it).

    python3 insights/reels_server.py [port] [bind address]      default 8780 on 0.0.0.0 (reachable from the phone)

/                 the page with the account tabs
/hie/, /hie/tracker   How It's Engineered: reel library (tools/remake/out/library.html), tracker (insights/hie-reels.html)
/ta/, /ta/tracker     @talkingagents: review page (insights/review/index.html), tracker (insights/reels-tracker.html)
POST /api/refresh?acct=hie|ta   runs that account's build scripts with ~/.instagram_tokens (and .env) sourced
"""
import http.server, json, os, re, subprocess, sys, threading
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlsplit

INS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(INS)
HIE = os.path.join(REPO, "how-its-engineered")
PAGES = {
    "/hie/": os.path.join(HIE, "tools", "remake", "out", "library.html"),
    "/hie/tracker": os.path.join(INS, "hie-reels.html"),
    "/ta/": os.path.join(INS, "review", "index.html"),
    "/ta/tracker": os.path.join(INS, "reels-tracker.html"),
}
# the library links its files from the server root; the review page links v/ and t/ next to itself
HIE_FILES = re.compile(r"^/((media|outputs)/[^?#]+\.(mp4|png|jpg)|videos/[^/]+/voice/voice\.wav|tools/remake/out/t/[^/]+\.jpg)$", re.I)
TA_FILES = re.compile(r"^/ta/((v/[^/]+\.mp4)|(t/[^/]+\.jpg))$", re.I)
TYPES = {".mp4": "video/mp4", ".png": "image/png", ".jpg": "image/jpeg", ".wav": "audio/wav", ".html": "text/html; charset=utf-8"}
BUILD = {
    "hie": (HIE, "set -a; source ../.env; set +a; source ~/.instagram_tokens; "
                 "python3 -I tools/remake/bin/tracker.py && python3 -I tools/remake/bin/library.py"),
    "ta": (INS, "source ~/.instagram_tokens; python3 build_tracker.py && python3 build_review.py"),
}
MAIN = {"hie": PAGES["/hie/"], "ta": PAGES["/ta/"]}
LOCKS = {a: threading.Lock() for a in BUILD}

SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reels</title>
<style>
:root { --bg: #f6f6f4; --bar: #ffffff; --fg: #1d1d1b; --mute: #6b6b66; --line: #e2e2dd; --pick: #1d1d1b; --pickfg: #ffffff; --bad: #b42318; }
@media (prefers-color-scheme: dark) { :root { --bg: #121211; --bar: #1b1b1a; --fg: #ecece8; --mute: #9a9a94; --line: #2c2c2a; --pick: #ecece8; --pickfg: #121211; --bad: #f97066; } }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--fg); font: 14px/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
body { display: flex; flex-direction: column; }
header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; padding: 8px 16px; background: var(--bar); border-bottom: 1px solid var(--line); }
.tabs, .views { display: flex; gap: 4px; }
button { font: inherit; color: var(--fg); background: none; border: 1px solid var(--line); border-radius: 8px; padding: 6px 12px; cursor: pointer; }
.tabs button { font-weight: 600; border-color: transparent; }
button[aria-pressed="true"] { background: var(--pick); color: var(--pickfg); border-color: var(--pick); }
.views button { padding: 4px 10px; font-size: 13px; }
.right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
#when { color: var(--mute); font-size: 13px; white-space: nowrap; }
#when.bad { color: var(--bad); }
#refresh:disabled { opacity: .55; cursor: progress; }
iframe { flex: 1; width: 100%; border: 0; background: var(--bg); }
</style></head><body>
<header>
  <div class="tabs" role="group" aria-label="Account">
    <button data-acct="hie">How It's Engineered</button>
    <button data-acct="ta">@talkingagents</button>
  </div>
  <div class="views" role="group" aria-label="Page"></div>
  <div class="right"><span id="when"></span><button id="refresh">Refresh data</button></div>
</header>
<iframe id="page" title="Reel page"></iframe>
<script>
const VIEWS = { hie: [["", "Library"], ["tracker", "Tracker"]], ta: [["", "Review"], ["tracker", "Tracker"]] };
const frame = document.getElementById("page"), when = document.getElementById("when"), btn = document.getElementById("refresh");
let acct = "hie", view = "", status = {};

function readHash() {
  const [a, v] = location.hash.slice(1).split("/");
  acct = VIEWS[a] ? a : "hie";
  view = VIEWS[acct].some(x => x[0] === (v || "")) ? (v || "") : "";
}
function render(keepScroll) {
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-pressed", b.dataset.acct === acct));
  document.querySelector(".views").innerHTML = VIEWS[acct].map(([v, label]) =>
    `<button data-view="${v}" aria-pressed="${v === view}">${label}</button>`).join("");
  const src = `/${acct}/${view}`;
  let y = 0;
  try { if (keepScroll) y = frame.contentWindow.scrollY; } catch (e) {}
  frame.onload = () => { try { if (y) frame.contentWindow.scrollTo(0, y); } catch (e) {} };
  if (keepScroll) frame.contentWindow.location.reload();
  else if (frame.getAttribute("src") !== src) frame.setAttribute("src", src);
  showStatus();
}
function showStatus(msg, bad) {
  const s = status[acct] || {};
  btn.disabled = !!s.running;
  btn.textContent = s.running ? "Refreshing…" : "Refresh data";
  when.classList.toggle("bad", !!bad);
  when.textContent = msg || (s.updated ? "Updated " + s.updated : "");
}
async function loadStatus() {
  try { status = await (await fetch("/api/status")).json(); } catch (e) {}
  showStatus();
}
document.querySelector(".tabs").onclick = e => { const b = e.target.closest("button"); if (b) location.hash = b.dataset.acct; };
document.querySelector(".views").onclick = e => { const b = e.target.closest("button"); if (b) location.hash = acct + (b.dataset.view ? "/" + b.dataset.view : ""); };
window.onhashchange = () => { readHash(); render(); loadStatus(); };
document.addEventListener("visibilitychange", () => { if (!document.hidden) loadStatus(); });
btn.onclick = async () => {
  const a = acct;
  status[a] = Object.assign({}, status[a], { running: true });
  showStatus();
  let r = {};
  try { r = await (await fetch("/api/refresh?acct=" + a, { method: "POST" })).json(); } catch (e) { r = { ok: false, error: "Server not reachable" }; }
  await loadStatus();
  if (a !== acct) return;
  if (r.ok) render(true);
  else showStatus("Refresh failed: " + (r.error || "unknown error"), true);
};
readHash(); render(); loadStatus();
</script>
</body></html>
"""


def updated(acct):
    f = MAIN[acct]
    return datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d %b, %H:%M") if os.path.exists(f) else None


def refresh(acct):
    """Run the account's builds; returns (ok, error). Never echoes the scripts' output, which could carry a token."""
    if not LOCKS[acct].acquire(blocking=False):
        LOCKS[acct].acquire()  # a refresh is already running: wait for it and report its result as ours
        LOCKS[acct].release()
        return True, None
    try:
        cwd, cmd = BUILD[acct]
        p = subprocess.run(["/bin/zsh", "-c", cmd], cwd=cwd, capture_output=True, text=True, timeout=600)
        if p.returncode == 0:
            return True, None
        last = (p.stderr.strip() or p.stdout.strip() or "exit code %d" % p.returncode).splitlines()[-1]
        return False, re.sub(r"[A-Za-z0-9_\-]{40,}", "***", last)[:200]
    except subprocess.TimeoutExpired:
        return False, "timed out after 10 minutes"
    finally:
        LOCKS[acct].release()


class H(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self): self.serve(head=True)
    def do_GET(self): self.serve()

    def do_POST(self):
        u = urlsplit(self.path)
        acct = parse_qs(u.query).get("acct", [""])[0]
        if u.path != "/api/refresh" or acct not in BUILD:
            return self.send_error(404)
        ok, err = refresh(acct)
        self.json({"ok": ok, "error": err, "updated": updated(acct)})

    def json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def serve(self, head=False):
        path = unquote(urlsplit(self.path).path)
        if path in ("/", "/index.html"):
            body = SHELL.encode()
            self.send_response(200); self.send_header("Content-Type", TYPES[".html"]); self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache"); self.end_headers()
            if not head: self.wfile.write(body)
            return
        if path == "/api/status":
            return self.json({a: {"updated": updated(a), "running": LOCKS[a].locked()} for a in BUILD})
        if path in ("/hie", "/ta"):
            self.send_response(301); self.send_header("Location", path + "/"); self.end_headers(); return
        if ".." in path: return self.send_error(404)
        if path in PAGES: f = PAGES[path]
        elif HIE_FILES.match(path): f = os.path.join(HIE, path.lstrip("/"))
        elif TA_FILES.match(path): f = os.path.join(INS, "review", path[len("/ta/"):])
        else: return self.send_error(404)
        if not os.path.isfile(f): return self.send_error(404)
        ctype = TYPES.get(os.path.splitext(f)[1].lower(), "application/octet-stream")
        size = os.path.getsize(f); a, b = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and (m.group(1) or m.group(2)):
            if m.group(1): a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else size - 1
            else: a = max(0, size - int(m.group(2)))
            b = min(b, size - 1)
            if a > b: self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
            self.send_response(206); self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        else: self.send_response(200)
        self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(b - a + 1))
        self.send_header("Cache-Control", "no-cache" if ctype.startswith("text/html") else "max-age=600"); self.end_headers()
        if head: return
        with open(f, "rb") as fh:
            fh.seek(a); left = b - a + 1
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk: break
                    self.wfile.write(chunk); left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError): pass

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    bind = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
    print(f"serving http://localhost:{port}/", flush=True)
    http.server.ThreadingHTTPServer((bind, port), H).serve_forever()
