"""
Hedra Avatar video generator.

For one or more product slugs (folders under ../products/), upload that
product's lifestyle-1.png and narration.mp3 to Hedra, kick off a Hedra Avatar
generation (9:16, mobile resolution, duration auto = narration length), poll
to completion, and download the result to <product>/raw-speaker-video.mp4.

Manifest is kept in sync: raw-speaker-video-path -> "raw-speaker-video.mp4".

Idempotent: if raw-speaker-video.mp4 already exists for a product, no API
call is made (only the manifest is fixed if needed). Pass --overwrite to
re-render.

Usage:
  python generate.py --products slug1,slug2
  python generate.py --all-needing
  python generate.py --products slug1 --overwrite

Output rows are tab-separated: <slug>\t<STATUS>\t<detail>
STATUS in {OK, FIXED, SKIP, FAIL}.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
PRODUCTS_DIR = REPO_ROOT / "products"

API_BASE = "https://api.hedra.com/web-app/public"
LIFESTYLE_NAME = "lifestyle-1.png"
NARRATION_NAME = "narration.mp3"
OUTPUT_NAME = "raw-speaker-video.mp4"
MANIFEST_KEY = "raw-speaker-video-path"

POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 60 * 25  # 25 min hard cap per generation


def _api_key() -> str:
    load_dotenv(HERE / ".env")
    key = os.getenv("HEDRA_API_KEY")
    if not key:
        sys.exit("HEDRA_API_KEY missing in hedra-vid-gen/.env")
    return key


def _model_id() -> str:
    return os.getenv("HEDRA_AVATAR_MODEL_ID", "26f0fc66-152b-40ab-abed-76c43df99bc8")


def _headers(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def _create_asset(api_key: str, name: str, asset_type: str) -> str:
    r = requests.post(
        f"{API_BASE}/assets",
        headers={**_headers(api_key), "Content-Type": "application/json"},
        json={"name": name, "type": asset_type},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def _upload_asset(api_key: str, asset_id: str, path: Path) -> None:
    with path.open("rb") as f:
        r = requests.post(
            f"{API_BASE}/assets/{asset_id}/upload",
            headers=_headers(api_key),
            files={"file": (path.name, f)},
            timeout=600,
        )
    r.raise_for_status()


def _start_generation(
    api_key: str,
    *,
    image_id: str,
    audio_id: str,
    text_prompt: str,
) -> str:
    body = {
        "type": "video",
        "ai_model_id": _model_id(),
        "start_keyframe_id": image_id,
        "audio_id": audio_id,
        "generated_video_inputs": {
            "text_prompt": text_prompt,
            "aspect_ratio": "9:16",
            "resolution": "720p",
        },
    }
    r = requests.post(
        f"{API_BASE}/generations",
        headers={**_headers(api_key), "Content-Type": "application/json"},
        json=body,
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"generation start failed: {r.status_code} {r.text}")
    return r.json()["id"]


def _poll(api_key: str, generation_id: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    last_status = ""
    while time.time() < deadline:
        r = requests.get(
            f"{API_BASE}/generations/{generation_id}/status",
            headers=_headers(api_key),
            timeout=60,
        )
        r.raise_for_status()
        body = r.json()
        status = (body.get("status") or "").lower()
        if status != last_status:
            print(
                f"  [hedra] status={status} progress={body.get('progress')}",
                file=sys.stderr,
            )
            last_status = status
        if status in ("complete", "completed", "succeeded"):
            return body
        if status in ("failed", "error", "canceled", "cancelled"):
            raise RuntimeError(f"generation {generation_id} ended: {body}")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"generation {generation_id} timed out after {POLL_TIMEOUT_SECONDS}s")


def _download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve_slugs(args: argparse.Namespace) -> list[str]:
    if args.all_needing:
        # Defer to scripts/status.py if it has the right flag, else scan locally.
        slugs = []
        for child in sorted(PRODUCTS_DIR.iterdir()):
            if not child.is_dir():
                continue
            mpath = child / "manifest.json"
            if not mpath.exists():
                continue
            if not (child / LIFESTYLE_NAME).exists():
                continue
            if not (child / NARRATION_NAME).exists():
                continue
            if (child / OUTPUT_NAME).exists():
                continue
            slugs.append(child.name)
        return slugs
    if not args.products:
        sys.exit("provide --products <slug[,slug,...]> or --all-needing")
    return [s.strip() for s in args.products.split(",") if s.strip()]


def _process(slug: str, api_key: str, overwrite: bool) -> tuple[str, str]:
    folder = PRODUCTS_DIR / slug
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        return ("FAIL", f"missing {manifest_path}")
    manifest = _load_manifest(manifest_path)

    image_path = folder / LIFESTYLE_NAME
    audio_path = folder / NARRATION_NAME
    output_path = folder / OUTPUT_NAME

    if not image_path.exists():
        return ("FAIL", f"missing {LIFESTYLE_NAME}")
    if not audio_path.exists():
        return ("FAIL", f"missing {NARRATION_NAME} — run /generate-narration first")

    if output_path.exists() and not overwrite:
        if manifest.get(MANIFEST_KEY) != OUTPUT_NAME:
            manifest[MANIFEST_KEY] = OUTPUT_NAME
            _save_manifest(manifest_path, manifest)
            return ("FIXED", "manifest synced")
        return ("SKIP", "video already exists")

    text_prompt = manifest.get("video-prompt") or manifest.get("script-raw-text") or "A person speaking to the camera"

    print(f"[{slug}] uploading audio…", file=sys.stderr)
    audio_id = _create_asset(api_key, NARRATION_NAME, "audio")
    _upload_asset(api_key, audio_id, audio_path)

    print(f"[{slug}] uploading image…", file=sys.stderr)
    image_id = _create_asset(api_key, LIFESTYLE_NAME, "image")
    _upload_asset(api_key, image_id, image_path)

    print(f"[{slug}] starting generation…", file=sys.stderr)
    gen_id = _start_generation(
        api_key,
        image_id=image_id,
        audio_id=audio_id,
        text_prompt=text_prompt[:500],
    )

    body = _poll(api_key, gen_id)
    download_url: Optional[str] = body.get("download_url") or body.get("url")
    if not download_url:
        return ("FAIL", f"completed but no download_url in response: {body}")

    print(f"[{slug}] downloading mp4…", file=sys.stderr)
    _download(download_url, output_path)

    manifest[MANIFEST_KEY] = OUTPUT_NAME
    _save_manifest(manifest_path, manifest)
    return ("OK", f"generation {gen_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", help="comma-separated slugs")
    ap.add_argument("--all-needing", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    api_key = _api_key()
    slugs = _resolve_slugs(args)
    if not slugs:
        print("nothing to do.", file=sys.stderr)
        return 0

    counts = {"OK": 0, "FIXED": 0, "SKIP": 0, "FAIL": 0}
    for slug in slugs:
        try:
            status, detail = _process(slug, api_key, args.overwrite)
        except Exception as exc:  # noqa: BLE001
            status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
        counts[status] = counts.get(status, 0) + 1
        print(f"{slug}\t{status}\t{detail}")

    print(
        f"\n{counts['OK']} generated, {counts['FIXED']} manifest-fixed, "
        f"{counts['SKIP']} skipped, {counts['FAIL']} failed.",
        file=sys.stderr,
    )
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
