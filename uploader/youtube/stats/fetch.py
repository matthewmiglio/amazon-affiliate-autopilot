"""Fetch YouTube stats for every uploaded ad, append to stats.csv, then open the dashboard."""
from __future__ import annotations

import csv
import http.server
import json
import re
import socketserver
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPLOAD_DIR = HERE.parent
HISTORY = UPLOAD_DIR / "history.json"
TOKENS_DIR = UPLOAD_DIR / "tokens"
STATS_CSV = HERE / "stats.csv"
COMMENTS_JSON = HERE / "comments.json"

CSV_FIELDS = [
    "snapshot_epoch", "ad_name", "video_id", "channel",
    "views", "likes", "comments",
    "views_per_day", "likes_per_1k_views",
    "duration_seconds", "days_since_upload",
]

SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.force-ssl"]
PORT = 8770


def parse_duration(iso: str) -> int:
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mn, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mn * 60 + s


def get_token_path() -> Path:
    if not TOKENS_DIR.exists():
        sys.exit(f"Tokens dir missing at {TOKENS_DIR}.")
    tokens = sorted(TOKENS_DIR.glob("*.json"))
    if not tokens:
        sys.exit(f"No token .json files in {TOKENS_DIR}.")
    return tokens[0]


def build_youtube():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(get_token_path()), SCOPES)
    return build("youtube", "v3", credentials=creds)


def append_to_csv(rows: list[dict], snapshot_epoch: int) -> None:
    write_header = not STATS_CSV.exists()
    with STATS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        now = datetime.now(timezone.utc)
        for r in rows:
            uploaded = r.get("uploaded_at", "")
            try:
                up_dt = datetime.fromisoformat(uploaded.replace("Z", "+00:00"))
                if up_dt.tzinfo is None:
                    up_dt = up_dt.replace(tzinfo=timezone.utc)
                days = max((now - up_dt).total_seconds() / 86400, 1)
            except (ValueError, AttributeError):
                days = 1
            views = r["views"]
            likes = r["likes"]
            w.writerow({
                "snapshot_epoch": snapshot_epoch,
                "ad_name": r["ad_name"],
                "video_id": r["video_id"],
                "channel": r.get("channel", ""),
                "views": views,
                "likes": likes,
                "comments": r["comments"],
                "views_per_day": round(views / days, 1),
                "likes_per_1k_views": round(likes / max(views, 1) * 1000, 2),
                "duration_seconds": parse_duration(r.get("duration", "")),
                "days_since_upload": round(days, 1),
            })


def fetch_video_comments(youtube, video_id: str, max_results: int = 100) -> list[dict]:
    comments = []
    try:
        page_token = None
        while len(comments) < max_results:
            resp = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_results - len(comments)),
                order="relevance",
                pageToken=page_token,
            ).execute()
            for item in resp.get("items", []):
                s = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": s.get("authorDisplayName", ""),
                    "text": s.get("textOriginal", ""),
                    "likes": s.get("likeCount", 0),
                    "published_at": s.get("publishedAt", ""),
                })
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    except Exception:
        pass
    return comments


def fetch_all_comments(youtube, history: dict, existing: dict) -> dict:
    todo = [(name, e["video_id"]) for name, e in history.items() if e["video_id"] not in existing]
    if not todo:
        print(f"  all {len(existing)} videos already cached, skipping.")
        return existing

    print(f"  {len(existing)} cached, fetching {len(todo)} new videos…")
    out = dict(existing)
    for i, (_, vid) in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {vid}…", end=" ", flush=True)
        comments = fetch_video_comments(youtube, vid)
        out[vid] = comments
        print(f"{len(comments)} comments")
    return out


def fetch_all_stats(youtube, video_ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=",".join(batch),
        ).execute()
        for item in resp.get("items", []):
            out[item["id"]] = item
    return out


def serve_dashboard() -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(HERE), **kwargs)
        def log_message(self, *_):
            pass

    url = f"http://localhost:{PORT}/stats.html"
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    webbrowser.open(url)
    print(f"Dashboard running at {url}  (Ctrl+C to stop)", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        httpd.shutdown()


def main() -> None:
    if not HISTORY.exists():
        sys.exit(f"history.json missing at {HISTORY}.")

    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    if not history:
        sys.exit("No videos in history.")

    from google.auth.exceptions import RefreshError
    youtube = build_youtube()

    video_ids = [e["video_id"] for e in history.values()]
    try:
        stats = fetch_all_stats(youtube, video_ids)
    except RefreshError as e:
        sys.exit(f"Token expired. Re-auth via the youtube uploader.\n{e}")

    rows = []
    for name in sorted(history.keys()):
        entry = history[name]
        vid = entry["video_id"]
        s = stats.get(vid, {})
        statistics = s.get("statistics", {})
        content = s.get("contentDetails", {})
        rows.append({
            "ad_name": name,
            "video_id": vid,
            "channel": entry.get("channel", ""),
            "uploaded_at": entry.get("uploaded_at", ""),
            "duration": content.get("duration", ""),
            "views": int(statistics.get("viewCount", 0)),
            "likes": int(statistics.get("likeCount", 0)),
            "comments": int(statistics.get("commentCount", 0)),
        })

    append_to_csv(rows, int(datetime.now(timezone.utc).timestamp()))

    existing_comments = json.loads(COMMENTS_JSON.read_text(encoding="utf-8")) if COMMENTS_JSON.exists() else {}
    print("Fetching comments…", flush=True)
    all_comments = fetch_all_comments(youtube, history, existing_comments)
    COMMENTS_JSON.write_text(json.dumps(all_comments, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Opening dashboard…", flush=True)
    serve_dashboard()


if __name__ == "__main__":
    main()
