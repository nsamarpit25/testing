"""One-time sign-in: gets a YouTube refresh token and saves it to .env.

    python3 youtube/yt_auth.py

Opens the Google sign-in page, waits for the redirect on the .env REDIRECT_URI
(http://localhost:8080), swaps the code for a refresh token and writes
YOUTUBE_LETSBUILD_SIMPLY_REFRESH_TOKEN into .env. Uploads nothing.
"""
import http.server
import secrets
import urllib.parse
import webbrowser

from yt_common import PREFIX, TOKEN_URL, cfg, load_env, my_channel, post_form, set_env_value

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",  # to confirm which channel signed in
]


def main():
    env = load_env()
    client_id = cfg(env, "CLIENT_ID")
    client_secret = cfg(env, "CLIENT_SECRET")
    redirect = cfg(env, "REDIRECT_URI")
    port = urllib.parse.urlparse(redirect).port or 80
    state = secrets.token_urlsafe(16)

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # forces Google to return a refresh token every time
        "state": state,
    })

    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" not in q and "error" not in q:
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = "Signed in. You can close this tab." if "code" in q else "Sign-in failed: " + q["error"][0]
            self.wfile.write(("<h2>%s</h2>" % msg).encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("localhost", port), Handler)
    print("Opening the Google sign-in page. If it doesn't open, paste this link into your browser:\n")
    print(auth_url + "\n")
    webbrowser.open(auth_url)
    while not result:
        server.handle_request()
    server.server_close()

    if "error" in result:
        raise SystemExit("Google returned an error: " + result["error"])
    if result.get("state") != state:
        raise SystemExit("State mismatch; ignoring this redirect.")

    tok = post_form(TOKEN_URL, {
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect,
        "grant_type": "authorization_code",
    })
    if "refresh_token" not in tok:
        raise SystemExit("No refresh token returned. Remove the app at "
                         "https://myaccount.google.com/permissions and run this again.")

    set_env_value(PREFIX + "REFRESH_TOKEN", tok["refresh_token"])
    channel_id, title = my_channel(tok["access_token"])
    print("Saved %sREFRESH_TOKEN to .env" % PREFIX)
    print("Signed in as channel: %s (%s)" % (title, channel_id))


if __name__ == "__main__":
    main()
