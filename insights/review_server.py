#!/usr/bin/env python3
"""Serve insights/review/ with HTTP Range support, so the reel previews play and seek (python -m http.server has no
Range support, which Safari and seeking need).

    python3 insights/review_server.py [port] [bind address]      default 8770 on 127.0.0.1
"""
import http.server, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review")


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def send_head(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = os.path.getsize(path)
        a = int(m.group(1)) if m and m.group(1) else 0
        b = int(m.group(2)) if m and m.group(2) else size - 1
        if a >= size:
            self.send_error(416)
            return None
        b = min(b, size - 1)
        f = open(path, "rb")
        f.seek(a)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        self._left = b - a + 1
        return f

    def copyfile(self, src, dst):
        left = getattr(self, "_left", None)
        if left is None:
            return super().copyfile(src, dst)
        while left > 0:
            chunk = src.read(min(1 << 16, left))
            if not chunk:
                break
            dst.write(chunk)
            left -= len(chunk)
        self._left = None

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    bind = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    print(f"serving {ROOT} on http://{bind}:{port}", flush=True)
    http.server.ThreadingHTTPServer((bind, port), H).serve_forever()
