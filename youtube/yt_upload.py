"""Upload a video to the letsbuildsimply YouTube channel.

    python3 youtube/yt_upload.py --check
        Confirms the saved token works and prints the channel. Uploads nothing.

    python3 youtube/yt_upload.py VIDEO.mp4 --title "..." [--description "..."]
        [--tags a,b,c] [--privacy private|unlisted|public] [--yes]

Defaults to private. Asks for confirmation before uploading unless --yes is passed.
Vertical videos up to 3 minutes are shown as Shorts automatically.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from yt_common import access_token, load_env, my_channel

UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")


def upload(token, path, meta):
    size = os.path.getsize(path)
    init = urllib.request.Request(UPLOAD_URL, data=json.dumps(meta).encode(), method="POST", headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*",
        "X-Upload-Content-Length": str(size),
    })
    try:
        with urllib.request.urlopen(init) as r:
            session = r.headers["Location"]
        with open(path, "rb") as f:
            put = urllib.request.Request(session, data=f.read(), method="PUT", headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "video/*",
                "Content-Length": str(size),
            })
        with urllib.request.urlopen(put) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit("Upload failed (%s): %s" % (e.code, e.read().decode()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video", nargs="?")
    p.add_argument("--check", action="store_true", help="verify the token, upload nothing")
    p.add_argument("--title")
    p.add_argument("--description", default="")
    p.add_argument("--tags", default="", help="comma separated")
    p.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    p.add_argument("--category", default="28", help="28 = Science & Technology, 27 = Education")
    p.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = p.parse_args()

    env = load_env()
    token = access_token(env)
    channel_id, channel = my_channel(token)
    print("Channel: %s (%s)" % (channel, channel_id))
    if a.check:
        print("Token OK. Nothing uploaded.")
        return

    if not a.video or not a.title:
        p.error("VIDEO and --title are required unless --check")
    if not os.path.isfile(a.video):
        p.error("no such file: " + a.video)
    if len(a.title) > 100:
        p.error("title is over YouTube's 100 character limit")

    meta = {
        "snippet": {
            "title": a.title,
            "description": a.description,
            "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
            "categoryId": a.category,
        },
        "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False},
    }
    mb = os.path.getsize(a.video) / 1e6
    print("File: %s (%.1f MB)\nTitle: %s\nPrivacy: %s" % (a.video, mb, a.title, a.privacy))
    if not a.yes and input("Upload? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled.")

    video = upload(token, a.video, meta)
    print("Uploaded: https://youtube.com/shorts/%s (status: %s)"
          % (video["id"], video["status"]["privacyStatus"]))


if __name__ == "__main__":
    main()
