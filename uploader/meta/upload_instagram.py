"""Amazon-affiliate product -> Instagram Reels uploader.

Uses Meta Graph API's resumable direct-binary upload (NO public URL needed).
Workflow:
  1. POST /{ig-user-id}/media?media_type=REELS&upload_type=resumable
       -> returns container id + rupload URI
  2. POST raw mp4 bytes to https://rupload.facebook.com/ig-api-upload/<ver>/<container-id>
       headers: Authorization: OAuth <token>, offset: 0, file_size: <bytes>
  3. Poll container status until FINISHED
  4. POST /{ig-user-id}/media_publish?creation_id=<container-id>
  5. Resolve permalink

CLI:
  python upload_instagram.py <product-slug> -y
  python upload_instagram.py whoami
  python upload_instagram.py --list

Reads:
  - products/<slug>/manifest.json (uploads.instagram.metadata.caption)
  - products/<slug>/final-with-music.mp4
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import time
from pathlib import Path

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import meta_auth
import graph_client

PRODUCTS = HERE.parent.parent / "products"
HISTORY_FILE = HERE / "history_instagram.json"
FINAL_VIDEO_NAME = "final-with-music.mp4"

CONTAINER_POLL_TIMEOUT_S = 600
CONTAINER_POLL_INTERVAL_S = 5
RUPLOAD_HOST = "https://rupload.facebook.com/ig-api-upload"


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
# IG Reels resumable upload flow
# ---------------------------------------------------------------------------

def _create_resumable_container(ig_user_id: str, caption: str) -> dict:
    """Step 1: open a resumable session. Returns dict with id + uri (rupload URL)."""
    return graph_client.post(
        f"/{ig_user_id}/media",
        params={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "share_to_feed": "true",
        },
    )


def _upload_bytes(container_id: str, video_path: Path) -> None:
    """Step 2: POST raw mp4 to rupload.facebook.com."""
    size = video_path.stat().st_size
    url = f"{RUPLOAD_HOST}/{meta_auth.graph_version()}/{container_id}"
    headers = {
        "Authorization": f"OAuth {meta_auth.access_token()}",
        "offset": "0",
        "file_size": str(size),
    }
    with video_path.open("rb") as f:
        resp = requests.post(url, headers=headers, data=f, timeout=600)
    if resp.status_code >= 400:
        raise RuntimeError(f"IG rupload failed: HTTP {resp.status_code} {resp.text[:500]}")


def _poll_container(container_id: str) -> None:
    """Step 3: wait for Meta to finish processing the uploaded video."""
    start = time.time()
    while time.time() - start < CONTAINER_POLL_TIMEOUT_S:
        info = graph_client.get(f"/{container_id}", params={"fields": "status_code,status"})
        code = info.get("status_code")
        status = info.get("status")
        print(f"  [ig] {container_id} status_code={code} status={status}", flush=True)
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"IG container failed: {info}")
        time.sleep(CONTAINER_POLL_INTERVAL_S)
    raise RuntimeError(f"IG container polling timed out after {CONTAINER_POLL_TIMEOUT_S}s")


def _publish(ig_user_id: str, container_id: str) -> str:
    """Step 4: publish the processed container as a Reel."""
    resp = graph_client.post(
        f"/{ig_user_id}/media_publish",
        params={"creation_id": container_id},
    )
    mid = resp.get("id")
    if not mid:
        raise RuntimeError(f"IG publish returned no id: {resp}")
    return mid


def _resolve_permalink(media_id: str) -> str:
    info = graph_client.get(f"/{media_id}", params={"fields": "permalink"})
    p = info.get("permalink")
    if p:
        return p
    return f"https://www.instagram.com/reel/{media_id}/"


# ---------------------------------------------------------------------------
# Upload flow
# ---------------------------------------------------------------------------

def upload_one(slug: str, assume_yes: bool, dry_run: bool, force: bool) -> str | None:
    manifest = load_manifest(slug)
    if manifest is None:
        print(f"  [skip] {slug}: no manifest")
        return None

    meta = ((manifest.get("uploads") or {}).get("instagram") or {}).get("metadata") or {}
    caption = (meta.get("caption") or "").strip()
    if not caption:
        print(f"  [skip] {slug}: no uploads.instagram.metadata.caption - run /upload-ad first")
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
        print("  [dry-run] would upload to IG Reels")
        return None
    if not assume_yes:
        if input("  upload to IG Reels? [y/N] ").strip().lower() != "y":
            return None

    ig_user_id = meta_auth.ig_user_id()
    print(f"  [ig] step 1: opening resumable session for IG user {ig_user_id}...", flush=True)
    session = _create_resumable_container(ig_user_id, caption)
    container_id = session.get("id")
    if not container_id:
        raise RuntimeError(f"IG resumable session has no id: {session}")
    print(f"  [ig] container_id={container_id}", flush=True)

    print(f"  [ig] step 2: streaming {size // 1024} KB to rupload...", flush=True)
    _upload_bytes(container_id, video_path)
    print(f"  [ig] step 2 ok. polling container...", flush=True)
    _poll_container(container_id)

    print(f"  [ig] step 4: publishing...", flush=True)
    media_id = _publish(ig_user_id, container_id)
    print(f"  [ig] published media_id={media_id}", flush=True)

    permalink = _resolve_permalink(media_id)
    print(f"uploaded -> {permalink}")

    history[slug] = {
        "media_id": media_id,
        "container_id": container_id,
        "url": permalink,
        "uploaded_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    save_history(history)
    return media_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_list() -> None:
    history = load_history()
    if not PRODUCTS.exists():
        print("(no products dir)")
        return
    names = sorted(p.name for p in PRODUCTS.iterdir() if p.is_dir())
    print(f"{'product':<40}{'video':<8}{'meta':<8}{'ig-up':<12}url")
    for name in names:
        manifest = load_manifest(name) or {}
        has_video = (PRODUCTS / name / FINAL_VIDEO_NAME).exists()
        meta = (((manifest.get("uploads") or {}).get("instagram") or {}).get("metadata") or {})
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
