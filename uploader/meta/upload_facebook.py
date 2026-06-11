"""Amazon-affiliate product -> Facebook Reels uploader.

Uses Meta Graph API's 3-phase resumable upload (no temp hosting needed for FB).

CLI:
  python upload_facebook.py <product-slug> -y
  python upload_facebook.py whoami
  python upload_facebook.py --list

Reads:
  - products/<slug>/manifest.json (uploads.facebook.metadata.caption)
  - products/<slug>/final-with-music.mp4

Writes on success:
  - prints `uploaded -> https://www.facebook.com/reel/<id>` (parsed by upload_ad.py)
  - history.json[<slug>] = {video_id, url, uploaded_at}
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

# Make sibling modules importable when run as a script.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import meta_auth
import graph_client

PRODUCTS = HERE.parent.parent / "products"
HISTORY_FILE = HERE / "history_facebook.json"
FINAL_VIDEO_NAME = "final-with-music.mp4"


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))


def save_history(h: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(h, indent=2), encoding="utf-8")


def manifest_path(slug: str) -> Path:
    return PRODUCTS / slug / "manifest.json"


def load_manifest(slug: str) -> dict | None:
    p = manifest_path(slug)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# FB Reels 3-phase upload
# ---------------------------------------------------------------------------

def _start_upload(page_id: str, file_size: int) -> dict:
    """Phase 1: tell Meta we're about to upload N bytes. Returns video_id + upload_url.

    Page-level video publishing requires the PAGE access token, not the bare
    system-user token ("Subject does not have permission to post videos on
    this target" otherwise)."""
    return graph_client.post(
        f"/{page_id}/video_reels",
        params={"upload_phase": "start",
                "access_token": meta_auth.page_access_token()},
    )


def _upload_bytes(upload_url: str, video_path: Path) -> None:
    """Phase 2: POST the raw mp4 body to the upload_url Meta gave us."""
    size = video_path.stat().st_size
    headers = {
        "Authorization": f"OAuth {meta_auth.page_access_token()}",
        "offset": "0",
        "file_size": str(size),
    }
    with video_path.open("rb") as f:
        resp = requests.post(upload_url, headers=headers, data=f, timeout=600)
    if resp.status_code >= 400:
        raise RuntimeError(f"FB upload bytes failed: HTTP {resp.status_code} {resp.text[:500]}")


def _finish_upload(page_id: str, video_id: str, caption: str) -> dict:
    """Phase 3: tell Meta the upload is done and publish the Reel."""
    return graph_client.post(
        f"/{page_id}/video_reels",
        params={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": meta_auth.page_access_token(),
        },
    )


def _poll_until_published(video_id: str, timeout_s: int = 600, interval_s: int = 5) -> None:
    """Reels can take 30s-2min to process. Block until Meta marks it published."""
    start = time.time()
    while time.time() - start < timeout_s:
        info = graph_client.get(f"/{video_id}", params={
            "fields": "status,published",
            "access_token": meta_auth.page_access_token(),
        })
        status = (info.get("status") or {}).get("video_status") if isinstance(info.get("status"), dict) else info.get("status")
        published = info.get("published")
        print(f"  [fb] {video_id} status={status} published={published}", flush=True)
        if published or status == "ready":
            return
        if status == "error":
            raise RuntimeError(f"FB Reel processing failed: {info}")
        time.sleep(interval_s)
    raise RuntimeError(f"FB Reel processing timed out after {timeout_s}s")


def _resolve_permalink(video_id: str) -> str:
    info = graph_client.get(f"/{video_id}", params={
        "fields": "permalink_url",
        "access_token": meta_auth.page_access_token(),
    })
    p = info.get("permalink_url")
    if p:
        return p if p.startswith("http") else f"https://www.facebook.com{p}"
    return f"https://www.facebook.com/reel/{video_id}"


# ---------------------------------------------------------------------------
# Upload flow
# ---------------------------------------------------------------------------

def upload_one(slug: str, assume_yes: bool, dry_run: bool, force: bool) -> str | None:
    manifest = load_manifest(slug)
    if manifest is None:
        print(f"  [skip] {slug}: no manifest")
        return None

    meta = ((manifest.get("uploads") or {}).get("facebook") or {}).get("metadata") or {}
    caption = (meta.get("caption") or "").strip()
    if not caption:
        print(f"  [skip] {slug}: no uploads.facebook.metadata.caption - run /upload-ad first")
        return None

    video_path = PRODUCTS / slug / FINAL_VIDEO_NAME
    if not video_path.exists():
        print(f"  [skip] {slug}: missing {FINAL_VIDEO_NAME}")
        return None

    history = load_history()
    if not force and slug in history:
        print(f"  [skip] {slug}: already uploaded -> {history[slug].get('url')}")
        return None

    size = video_path.stat().st_size
    print(f"\n{slug}")
    print(f"  video:    {video_path.name} ({size // 1024} KB)")
    print(f"  caption:  {caption[:100]}{'...' if len(caption) > 100 else ''}")

    if dry_run:
        print("  [dry-run] would upload to FB Reels")
        return None
    if not assume_yes:
        if input("  upload to FB Reels? [y/N] ").strip().lower() != "y":
            return None

    page_id = meta_auth.fb_page_id()
    print(f"  [fb] phase 1: start upload to page {page_id}...", flush=True)
    start = _start_upload(page_id, size)
    video_id = start["video_id"]
    upload_url = start["upload_url"]
    print(f"  [fb] phase 1 ok. video_id={video_id}", flush=True)

    print(f"  [fb] phase 2: streaming {size // 1024} KB...", flush=True)
    _upload_bytes(upload_url, video_path)
    print(f"  [fb] phase 2 ok.", flush=True)

    print(f"  [fb] phase 3: finish + publish...", flush=True)
    _finish_upload(page_id, video_id, caption)
    print(f"  [fb] phase 3 ok. polling status...", flush=True)

    try:
        _poll_until_published(video_id)
    except RuntimeError as e:
        print(f"  [fb] warning: {e}. Continuing — Reel often shows up post-timeout.", flush=True)

    permalink = _resolve_permalink(video_id)
    print(f"uploaded -> {permalink}")

    history[slug] = {
        "video_id": video_id,
        "url": permalink,
        "uploaded_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    save_history(history)
    return video_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_list() -> None:
    history = load_history()
    if not PRODUCTS.exists():
        print("(no products dir)")
        return
    names = sorted(p.name for p in PRODUCTS.iterdir() if p.is_dir())
    print(f"{'product':<40}{'video':<8}{'meta':<8}{'fb-up':<12}url")
    for name in names:
        manifest = load_manifest(name) or {}
        has_video = (PRODUCTS / name / FINAL_VIDEO_NAME).exists()
        meta = (((manifest.get("uploads") or {}).get("facebook") or {}).get("metadata") or {})
        has_meta = bool(meta.get("caption"))
        h = history.get(name)
        when = h["uploaded_at"][:10] if h else "-"
        url = h.get("url", "") if h else ""
        short = (name[:37] + "...") if len(name) > 40 else name
        print(f"{short:<40}{('yes' if has_video else 'no'):<8}{('yes' if has_meta else 'no'):<8}{when:<12}{url}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?", help='product slug or "whoami"')
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="ignore history")
    ap.add_argument("-y", "--yes", action="store_true")
    args = ap.parse_args()

    if args.list:
        cmd_list()
        return
    if args.target == "whoami":
        print(json.dumps(meta_auth.whoami(), indent=2))
        return
    if not args.target:
        ap.error('pass a product slug, "whoami", or --list')

    upload_one(args.target, assume_yes=args.yes, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
