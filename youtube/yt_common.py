"""Shared helpers for the YouTube scripts: .env loading, token refresh, API calls.

Standard library only, so nothing needs installing.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO, ".env")
PREFIX = "YOUTUBE_LETSBUILD_SIMPLY_"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def cfg(env, key, required=True):
    val = env.get(PREFIX + key, "")
    if required and not val:
        raise SystemExit("Missing %s%s in .env" % (PREFIX, key))
    return val


def set_env_value(key, value):
    """Replace KEY=... in .env, or append it if absent. Keeps every other line as is."""
    with open(ENV_PATH) as f:
        lines = f.read().splitlines()
    out, found = [], False
    for line in lines:
        if line.split("=", 1)[0].strip() == key:
            out.append("%s=%s" % (key, value))
            found = True
        else:
            out.append(line)
    if not found:
        out.append("%s=%s" % (key, value))
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(out) + "\n")
    os.chmod(ENV_PATH, 0o600)


def post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body)) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit("%s failed (%s): %s" % (url, e.code, e.read().decode()))


def access_token(env):
    tok = post_form(TOKEN_URL, {
        "client_id": cfg(env, "CLIENT_ID"),
        "client_secret": cfg(env, "CLIENT_SECRET"),
        "refresh_token": cfg(env, "REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    })
    return tok["access_token"]


def api_get(token, path, params):
    url = "%s/%s?%s" % (API, path, urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit("GET %s failed (%s): %s" % (path, e.code, e.read().decode()))


def my_channel(token):
    items = api_get(token, "channels", {"part": "snippet", "mine": "true"}).get("items", [])
    if not items:
        raise SystemExit("This Google account has no YouTube channel.")
    return items[0]["id"], items[0]["snippet"]["title"]
