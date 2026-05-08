"""Amazon-affiliate product video → YouTube Shorts uploader.

One-time setup:
  1. Create a Google Cloud project, enable YouTube Data API v3.
  2. Create an OAuth 2.0 Client ID (Desktop app), download the JSON, save it as
     client_secret.json in this directory.
  3. `poetry install`
  4. `poetry run python upload.py auth --channel <your-email>`   (runs OAuth, saves token)

Every subsequent upload:
  python upload.py <product-slug> -y                            # upload one (auto-picks channel)
  python upload.py <product-slug> -y --channel foo@gmail.com    # force channel
  python upload.py <product-slug> --force -y                    # re-upload (skips history check)
  python upload.py --list                                       # show status of all products
  python upload.py --channels                                   # show registered channels

Metadata for each product lives in metadata.json. Each entry drives the YouTube
snippet (title, description, tags, category). The actual video file is pulled
from ../videos/<product-slug>.mp4.

Multi-channel rotation:
  Each authenticated account has a token saved in tokens/<name>.json and a
  record in channels.json. When uploading without --channel, the script picks
  whichever channel has the oldest last-upload timestamp (round-robin).
"""
from __future__ import annotations

import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
import datetime as dt
import json
import random
import re
from pathlib import Path

from youtube_auth import (
    CHANNELS_FILE,
    CLIENT_SECRET,
    SCOPES,
    TOKEN_LEGACY as TOKEN,
    TOKENS_DIR,
    build_youtube,
    list_token_names,
    load_channels,
    save_channels,
    token_path as _token_path,
)

HERE = Path(__file__).resolve().parent
VIDEOS = HERE.parent / "videos"
METADATA_FILE = HERE / "metadata.json"
HISTORY_FILE = HERE / "history.json"

CATEGORY_PEOPLE_BLOGS = "22"

TITLE_HASHTAG_POOL = [
    "#AmazonFinds", "#AmazonMustHaves", "#AmazonDeals", "#AmazonHaul",
    "#TikTokMadeMeBuyIt", "#Shorts", "#YouTubeShorts", "#ProductReview",
    "#MustHave", "#OnlineShopping", "#AmazonReview", "#SmartBuy",
    "#JewelryFinds", "#JewelryLover", "#DaintyJewelry", "#FineJewelry",
]
TITLE_HASHTAG_COUNT = 3

BLACKLIST_CHARS = [
    "<", ">", "\\", "|", "@", "%", "^", "*", "+", "=", "`", "~",
    "—", "–", "‘", "’", "“", "”", "…", "«", "»", "‹", "›",
    "•", "·", "°", "\t", "\n",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize(text: str) -> str:
    for c in BLACKLIST_CHARS:
        text = text.replace(c, "")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def apply_title_hashtags(title: str) -> str:
    stripped = re.sub(r'\s*#\S+', '', title).strip()
    tags = random.sample(TITLE_HASHTAG_POOL, TITLE_HASHTAG_COUNT)
    result = f"{stripped} {' '.join(tags)}"
    if len(result) > 100:
        result = f"{stripped} {' '.join(tags[:2])}"
    if len(result) > 100:
        result = f"{stripped} {tags[0]}"
    if len(result) > 100:
        result = stripped
    return result


def load_metadata() -> dict:
    if not METADATA_FILE.exists():
        sys.exit(f"metadata.json missing at {METADATA_FILE}")
    return json.loads(METADATA_FILE.read_text(encoding="utf-8"))


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))


def save_history(history: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Channel rotation
# ---------------------------------------------------------------------------

def pick_channel(history: dict) -> str | None:
    channels = load_channels()
    if not channels:
        if TOKEN.exists():
            return None
        sys.exit("No channels registered. Run: python upload.py auth --channel <name>")

    channel_names = [c["name"] for c in channels]
    last_upload: dict[str, str | None] = {name: None for name in channel_names}
    for entry in history.values():
        ch = entry.get("channel")
        if ch in last_upload:
            ts = entry.get("uploaded_at", "")
            if last_upload[ch] is None or ts > last_upload[ch]:
                last_upload[ch] = ts

    sorted_channels = sorted(channel_names, key=lambda n: (last_upload[n] is not None, last_upload[n] or ""))
    return sorted_channels[0]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def do_auth(channel_name: str) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRET.exists():
        sys.exit(f"client_secret.json missing at {CLIENT_SECRET}.\n"
                 "Create an OAuth Desktop Client in Google Cloud Console and save the downloaded JSON here.")

    TOKENS_DIR.mkdir(exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)

    import socket
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import urlparse, parse_qs

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]

    flow.redirect_uri = f"http://localhost:{port}"
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

    print("\n" + "=" * 70, flush=True)
    print("PASTE THIS URL INTO ANY BROWSER (incognito / Edge / etc.):")
    print(auth_url, flush=True)
    print("=" * 70 + "\n", flush=True)

    code_holder: list[str] = []
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            code_holder.extend(qs.get("code", []))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Auth complete. You can close this tab.</h2>")
        def log_message(self, *a): pass

    server = HTTPServer(("localhost", port), _Handler)
    server.handle_request()
    if not code_holder:
        sys.exit("No auth code received.")
    flow.fetch_token(code=code_holder[0])
    creds = flow.credentials

    from googleapiclient.discovery import build as yt_build
    yt = yt_build("youtube", "v3", credentials=creds)
    resp = yt.channels().list(part="id,snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        sys.exit("Could not retrieve channel info from YouTube. The account may not have a YouTube channel.")
    channel_id = items[0]["id"]
    channel_title = items[0]["snippet"]["title"]

    channels = load_channels()
    existing = next((c for c in channels if c.get("channel_id") == channel_id), None)
    if existing and existing["name"] != channel_name:
        confirm = input(
            f"  [warn] This YouTube channel ('{channel_title}') is already registered as "
            f"'{existing['name']}'. Overwrite? [y/N] "
        ).strip().lower()
        if confirm != "y":
            print("  Aborted.")
            return
        channels = [c for c in channels if c.get("channel_id") != channel_id]

    _token_path(channel_name).write_text(creds.to_json(), encoding="utf-8")

    channels = [c for c in channels if c["name"] != channel_name]
    channels.append({"name": channel_name, "channel_id": channel_id, "channel_title": channel_title})
    save_channels(channels)

    print(f"Authenticated: {channel_title} ({channel_id})")
    print(f"Token saved  : tokens/{channel_name}.json")
    print(f"channels.json updated ({len(channels)} channel(s) registered)")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_one(product_slug: str, dry_run: bool, force: bool, assume_yes: bool = False,
               channel: str | None = None) -> str | None:
    metadata = load_metadata()
    history = load_history()

    if product_slug not in metadata:
        print(f"  [skip] {product_slug}: no entry in metadata.json")
        return None
    if not force and product_slug in history:
        prev = history[product_slug]
        print(f"  [skip] {product_slug}: already uploaded {prev['uploaded_at']} -> https://youtu.be/{prev['video_id']}")
        return None

    video_path = VIDEOS / f"{product_slug}.mp4"
    if not video_path.exists():
        print(f"  [skip] {product_slug}: video not rendered at {video_path}")
        return None

    if channel is None:
        channel = pick_channel(history)

    entry = metadata[product_slug]
    title = apply_title_hashtags(sanitize(entry["title"]))
    description = sanitize(entry["description"])
    tags = [sanitize(t) for t in entry.get("tags", [])]
    category = entry.get("category", CATEGORY_PEOPLE_BLOGS)
    privacy = entry.get("privacy", "public")

    if len(title) > 100:
        print(f"  [warn] {product_slug}: title is {len(title)} chars (YouTube limit 100); trimming")
        title = title[:100]

    channel_label = channel or "legacy"
    print(f"\n{product_slug}")
    print(f"  channel:     {channel_label}")
    print(f"  file:        {video_path.name} ({video_path.stat().st_size // 1024} KB)")
    print(f"  title:       {title}")
    print(f"  description: {description[:80] + ('...' if len(description) > 80 else '')}")
    print(f"  tags:        {', '.join(tags)}")
    print(f"  privacy:     {privacy}")

    if dry_run:
        print("  [dry-run] would upload")
        return None

    if not assume_yes:
        confirm = input("  upload? [y/N] ").strip().lower()
        if confirm != "y":
            print("  skipped by user")
            return None

    from googleapiclient.http import MediaFileUpload
    youtube = build_youtube(channel)
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()
    video_id = response["id"]
    print(f"  uploaded -> https://youtu.be/{video_id}")

    history[product_slug] = {
        "video_id": video_id,
        "uploaded_at": dt.datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "description": description,
        "tags": tags,
        "category": category,
        "privacy": privacy,
        "channel": channel_label,
        "url": f"https://youtu.be/{video_id}",
    }
    save_history(history)
    return video_id


# ---------------------------------------------------------------------------
# Status / list
# ---------------------------------------------------------------------------

def list_status() -> None:
    metadata = load_metadata()
    history = load_history()
    rendered = {p.stem for p in VIDEOS.glob("*.mp4")} if VIDEOS.exists() else set()
    all_names = sorted({k for k in metadata if not k.startswith("_")} | rendered)
    print(f"{'product':<32}{'rendered':<10}{'meta':<8}{'uploaded':<12}{'channel':<32}url")
    for name in all_names:
        has_render = "yes" if name in rendered else "no"
        has_meta = "yes" if name in metadata else "no"
        up = history.get(name)
        up_when = up["uploaded_at"][:10] if up else "-"
        ch = up.get("channel", "") if up else ""
        url = f"https://youtu.be/{up['video_id']}" if up else ""
        print(f"{name:<32}{has_render:<10}{has_meta:<8}{up_when:<12}{ch:<32}{url}")


def list_channels() -> None:
    channels = load_channels()
    token_names = set(list_token_names())
    if not channels and not token_names:
        print("No channels registered. Run: python upload.py auth --channel <name>")
        return
    print(f"{'name':<36}{'channel_id':<26}{'channel_title':<30}token")
    for c in channels:
        has_token = "yes" if c["name"] in token_names else "MISSING"
        cid = c.get("channel_id") or "-"
        ctitle = c.get("channel_title") or "-"
        print(f"{c['name']:<36}{cid:<26}{ctitle:<30}{has_token}")
    registered = {c["name"] for c in channels}
    orphans = token_names - registered
    for name in sorted(orphans):
        print(f"{name:<36}{'(not in channels.json)':<26}{'':<30}yes")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help='product slug or "auth"')
    ap.add_argument("--channel", help="channel name (email) to auth or force for upload")
    ap.add_argument("--list", action="store_true", help="print status table and exit")
    ap.add_argument("--channels", action="store_true", help="print registered channels and exit")
    ap.add_argument("--dry-run", action="store_true", help="preview without uploading")
    ap.add_argument("--force", action="store_true", help="ignore upload history (re-upload)")
    ap.add_argument("-y", "--yes", action="store_true", help="skip per-upload confirmation")
    args = ap.parse_args()

    if args.list:
        list_status()
        return
    if args.channels:
        list_channels()
        return
    if args.target == "auth":
        if not args.channel:
            ap.error('auth requires --channel, e.g.: python upload.py auth --channel you@gmail.com')
        do_auth(args.channel)
        return

    if not args.target:
        ap.error('pass a product slug, "--list", "--channels", or "auth"')

    upload_one(args.target, dry_run=args.dry_run, force=args.force,
               assume_yes=args.yes, channel=args.channel or None)


if __name__ == "__main__":
    main()
