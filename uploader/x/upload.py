"""X (Twitter) video tweet uploader.

CLI:
    python uploader/x/upload.py auth                # one-time OAuth flow
    python uploader/x/upload.py whoami              # sanity-check token
    python uploader/x/upload.py <product-slug> [-y] # post final-with-music.mp4 as a video tweet

On success the slug branch prints `uploaded -> https://x.com/<user>/status/<id>`
so scripts/upload_ad.py can parse it.

Chunked upload flow (v2 endpoints throughout):
    INIT → APPEND (5 MB chunks) → FINALIZE → STATUS poll → POST /2/tweets
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import OrderedDict
from pathlib import Path

import os

import requests
from dotenv import load_dotenv
from requests_oauthlib import OAuth1

# Force utf-8 stdout/stderr so emojis in the composed tweet body (🛒) don't
# crash debug prints on Windows' default cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import x_auth  # noqa: E402

ROOT = HERE.parent.parent
PRODUCTS_DIR = ROOT / "products"
FINAL_VIDEO = "final-with-music.mp4"

MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEETS_URL = "https://api.x.com/2/tweets"
USERS_ME_URL = "https://api.x.com/2/users/me"

CHUNK_BYTES = 5 * 1024 * 1024  # 5 MB — well under X's 5 MB-per-chunk cap

HISTORY_FILE = HERE / "history.json"

# Tweet body budget. X t.co-wraps every URL to 23 chars regardless of actual
# length, so we treat the affiliate URL as 23 chars when fitting text.
TWEET_HARD_LIMIT = 280
URL_T_CO_LEN = 23


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _bearer() -> dict:
    return {"Authorization": f"Bearer {x_auth.get_access_token()}"}


def _oauth1() -> OAuth1:
    """OAuth 1.0a signer for v1.1 media upload — bearer tokens are rejected
    by upload.twitter.com so we sign with the app's Consumer Key/Secret plus
    the per-user Access Token/Secret from the dev portal."""
    load_dotenv(x_auth.ENV_FILE)
    ck = os.environ.get("X_API_KEY", "").strip()
    cs = os.environ.get("X_API_KEY_SECRET", "").strip()
    at = os.environ.get("X_ACCESS_TOKEN", "").strip()
    ats = os.environ.get("X_ACCESS_TOKEN_SECRET", "").strip()
    if not all([ck, cs, at, ats]):
        sys.exit(
            "OAuth1 credentials missing — set X_API_KEY, X_API_KEY_SECRET, "
            "X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET in uploader/x/.env."
        )
    return OAuth1(ck, cs, at, ats, signature_type="auth_header")


def _username() -> str:
    r = requests.get(USERS_ME_URL, headers=_bearer(), timeout=30)
    r.raise_for_status()
    return r.json()["data"]["username"]


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def _save_manifest(path: Path, data: OrderedDict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _hook_from_script(script: str, max_chars: int) -> str:
    s = (script or "").strip()
    if not s:
        return "New Amazon find."
    # Take the first sentence; fall back to the first N chars.
    parts = re.split(r"(?<=[\.\?!])\s+", s, maxsplit=1)
    hook = parts[0].strip()
    if len(hook) > max_chars:
        hook = hook[: max_chars - 1].rstrip() + "…"
    return hook


def _build_tweet_text(manifest: dict) -> str:
    """Compose a single-tweet body that includes the affiliate URL + #ad.

    Layout:
        <hook>
        \n\n
        🛒 <affiliate URL>
        \n\n
        #ad #amazonfinds
    """
    pre_meta = (manifest.get("uploads", {}).get("x", {}) or {}).get("metadata", {}) or {}
    explicit = (pre_meta.get("text") or "").strip()
    if explicit:
        return explicit
    info = manifest.get("item-auxiliary-information") or {}
    affiliate = pre_meta.get("destination_url") or info.get("affiliate-link") or ""
    affiliate = affiliate.strip()
    script = manifest.get("script-raw-text") or ""
    tail = "🛒 " + affiliate + "\n\n#ad #amazonfinds"
    # Hook budget = 280 - (tail length with URL treated as 23 chars) - 2 newlines
    tail_chars = len(tail) - len(affiliate) + URL_T_CO_LEN
    hook_budget = max(40, TWEET_HARD_LIMIT - tail_chars - 2)
    hook = _hook_from_script(script, hook_budget)
    return f"{hook}\n\n{tail}"


# ---------------------------------------------------------------------------
# Chunked media upload
# ---------------------------------------------------------------------------

def _post_form(fields: dict, files: dict | None = None) -> requests.Response:
    # v1.1 chunked upload requires OAuth 1.0a-signed requests; OAuth 2.0
    # bearers come back 403.
    return requests.post(
        MEDIA_UPLOAD_URL,
        data=fields,
        files=files,
        auth=_oauth1(),
        timeout=300,
    )


def _media_init(total_bytes: int, media_type: str = "video/mp4") -> str:
    r = _post_form({
        "command": "INIT",
        "total_bytes": str(total_bytes),
        "media_type": media_type,
        "media_category": "tweet_video",
    })
    if r.status_code not in (200, 201, 202):
        sys.exit(f"INIT failed: {r.status_code} {r.text}")
    data = r.json()
    media_id = str(data.get("media_id_string") or data.get("media_id") or "")
    if not media_id:
        sys.exit(f"INIT returned no media id: {r.text}")
    return media_id


def _media_append(media_id: str, video: Path) -> None:
    # APPEND keeps the multipart/form-data shape: `media_id` and
    # `segment_index` as form fields alongside the file part. Only INIT /
    # FINALIZE / STATUS moved to JSON in the v2 GA endpoint.
    with video.open("rb") as f:
        idx = 0
        while True:
            chunk = f.read(CHUNK_BYTES)
            if not chunk:
                break
            r = requests.post(
                MEDIA_UPLOAD_URL,
                data={
                    "command": "APPEND",
                    "media_id": media_id,
                    "segment_index": str(idx),
                },
                files={"media": ("chunk", chunk, "application/octet-stream")},
                auth=_oauth1(),
                timeout=300,
            )
            if r.status_code not in (200, 201, 204):
                sys.exit(f"APPEND seg {idx} failed: {r.status_code} {r.text}")
            idx += 1
    print(f"appended {idx} chunk(s)")


def _media_finalize(media_id: str) -> dict:
    r = _post_form({"command": "FINALIZE", "media_id": media_id})
    if r.status_code not in (200, 201):
        sys.exit(f"FINALIZE failed: {r.status_code} {r.text}")
    return r.json().get("processing_info") or {}


def _media_status_poll(media_id: str, processing_info: dict) -> None:
    info = processing_info
    elapsed = 0
    while info and info.get("state") in ("pending", "in_progress"):
        delay = int(info.get("check_after_secs") or 5)
        print(f"processing… state={info.get('state')} progress={info.get('progress_percent', '?')}%  sleep {delay}s")
        time.sleep(delay)
        elapsed += delay
        if elapsed > 600:
            sys.exit("STATUS poll exceeded 10 min; aborting")
        r = requests.get(
            MEDIA_UPLOAD_URL,
            params={"command": "STATUS", "media_id": media_id},
            auth=_oauth1(),
            timeout=30,
        )
        if r.status_code != 200:
            sys.exit(f"STATUS failed: {r.status_code} {r.text}")
        info = r.json().get("processing_info") or {}
    if info.get("state") == "failed":
        sys.exit(f"media processing failed: {json.dumps(info)}")


def _create_tweet(text: str, media_id: str) -> tuple[str, str]:
    r = requests.post(
        TWEETS_URL,
        json={"text": text, "media": {"media_ids": [media_id]}},
        headers={**_bearer(), "Content-Type": "application/json"},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        sys.exit(f"POST /2/tweets failed: {r.status_code} {r.text}")
    data = r.json().get("data") or {}
    return str(data.get("id") or ""), data.get("text") or ""


# ---------------------------------------------------------------------------
# History (per-slug record, separate from manifest for debugging)
# ---------------------------------------------------------------------------

def _record_history(slug: str, tweet_id: str, url: str) -> None:
    hist = {}
    if HISTORY_FILE.exists():
        try:
            hist = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            hist = {}
    hist[slug] = {"tweet_id": tweet_id, "tweet_url": url, "ts": int(time.time())}
    HISTORY_FILE.write_text(json.dumps(hist, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Slug branch
# ---------------------------------------------------------------------------

def upload_for_slug(slug: str) -> int:
    pdir = PRODUCTS_DIR / slug
    if not pdir.is_dir():
        sys.exit(f"no product dir at {pdir}")
    manifest_path = pdir / "manifest.json"
    video_path = pdir / FINAL_VIDEO
    if not manifest_path.exists():
        sys.exit(f"no manifest.json at {manifest_path}")
    if not video_path.exists():
        sys.exit(f"missing {FINAL_VIDEO} at {video_path} — run /overlay-music first")

    manifest = _load_manifest(manifest_path)
    text = _build_tweet_text(manifest)
    if len(text) > TWEET_HARD_LIMIT + URL_T_CO_LEN:  # generous: URLs t.co-shrink
        sys.exit(f"tweet text too long ({len(text)} chars):\n{text}")

    size = video_path.stat().st_size
    print(f"video: {video_path} ({size} bytes)")
    print(f"tweet text ({len(text)} raw chars):\n----\n{text}\n----")

    media_id = _media_init(size)
    print(f"INIT ok — media_id={media_id}")
    _media_append(media_id, video_path)
    info = _media_finalize(media_id)
    print(f"FINALIZE ok — initial state={info.get('state') or 'succeeded'}")
    _media_status_poll(media_id, info)
    print("media processing succeeded")

    tweet_id, posted_text = _create_tweet(text, media_id)
    username = _username()
    url = f"https://x.com/{username}/status/{tweet_id}"
    print(f"uploaded -> {url}")

    # Persist to manifest so scripts/upload_ad.py sees it as done even when
    # invoked directly (out-of-band from the orchestrator).
    uploads = manifest.setdefault("uploads", OrderedDict())
    xblock = uploads.setdefault("x", OrderedDict([
        ("uploaded", False), ("url", ""), ("metadata", OrderedDict()),
    ]))
    xblock["uploaded"] = True
    xblock["url"] = url
    meta = xblock.setdefault("metadata", OrderedDict())
    meta["text"] = text
    if not meta.get("destination_url"):
        meta["destination_url"] = (manifest.get("item-auxiliary-information") or {}).get("affiliate-link", "")
    _save_manifest(manifest_path, manifest)

    _record_history(slug, tweet_id, url)
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", help="auth | whoami | <product-slug>")
    p.add_argument("-y", action="store_true", help="non-interactive (currently a no-op)")
    args = p.parse_args()

    if args.cmd == "auth":
        x_auth._run_pkce_flow()
        print(f"OK — token saved to {x_auth.TOKEN_FILE}")
        return 0
    if args.cmd == "whoami":
        print(json.dumps(x_auth.whoami(), indent=2))
        return 0
    return upload_for_slug(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
