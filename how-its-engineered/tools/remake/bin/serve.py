#!/usr/bin/env python3
"""Serve the reel library on the local network, with HTTP Range support so videos play and seek (iPhone Safari needs it).

usage: python3 -I tools/remake/bin/serve.py [port]   → http://localhost:8765/ and http://<mac's LAN IP>:8765/
Serves how-its-engineered/; / is tools/remake/out/library.html. Only /, /media/, /outputs/, /videos/*/voice/ and the thumbnails in tools/remake/out/t/ are reachable.
"""
import http.server, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
PAGE = os.path.join(ROOT, 'tools', 'remake', 'out', 'library.html')
ALLOW = re.compile(r'^/((media|outputs)/[^?#]+\.(mp4|png|jpg)|videos/[^/]+/voice/voice\.wav|tools/remake/out/t/[^/]+\.jpg)$', re.I)
TYPES = {'.mp4': 'video/mp4', '.png': 'image/png', '.jpg': 'image/jpeg', '.wav': 'audio/wav'}


class H(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self): self.serve(head=True)
    def do_GET(self): self.serve()

    def serve(self, head=False):
        path = self.path.split('?')[0]
        from urllib.parse import unquote
        path = unquote(path)
        if path in ('/', '/index.html'): f, ctype = PAGE, 'text/html; charset=utf-8'
        elif ALLOW.match(path) and '..' not in path: f = os.path.join(ROOT, path.lstrip('/')); ctype = TYPES.get(os.path.splitext(f)[1].lower(), 'application/octet-stream')
        else: return self.send_error(404)
        if not os.path.isfile(f): return self.send_error(404)
        size = os.path.getsize(f); a, b = 0, size - 1
        m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
        if m and (m.group(1) or m.group(2)):
            if m.group(1): a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else size - 1
            else: a = size - int(m.group(2))
            b = min(b, size - 1)
            if a > b: self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return
            self.send_response(206); self.send_header('Content-Range', f'bytes {a}-{b}/{size}')
        else: self.send_response(200)
        self.send_header('Content-Type', ctype); self.send_header('Accept-Ranges', 'bytes'); self.send_header('Content-Length', str(b - a + 1))
        self.send_header('Cache-Control', 'no-cache' if ctype.startswith('text/html') else 'max-age=600'); self.end_headers()
        if head: return
        with open(f, 'rb') as fh:
            fh.seek(a); left = b - a + 1
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk: break
                    self.wfile.write(chunk); left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError): pass

    def log_message(self, fmt, *args): sys.stderr.write('%s %s\n' % (self.command, self.path))


port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
print(f'serving http://localhost:{port}/', flush=True)
http.server.ThreadingHTTPServer(('0.0.0.0', port), H).serve_forever()
