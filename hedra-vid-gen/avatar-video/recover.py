"""Recover a Hedra avatar-video generation that polled-timed-out (e.g. 504)
but is likely still running on Hedra's side. Tolerates transient HTTP errors.

Usage:
    poetry run python avatar-video/recover.py <slug> <generation_id>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import _common as hc

PRODUCTS = ROOT.parent / "products"
OUTPUT_NAME = "raw-speaker-video.mp4"
MANIFEST_KEY = "raw-speaker-video-path"


def poll_tolerant(key: str, gen_id: str, *, interval_s: int = 15,
                  timeout_s: int = 60 * 60) -> dict:
    deadline = time.time() + timeout_s
    last_status = ""
    while time.time() < deadline:
        try:
            r = requests.get(
                f"{hc.API_BASE}/generations/{gen_id}/status",
                headers=hc.headers(key),
                timeout=60,
            )
            r.raise_for_status()
            body = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  [hedra] transient: {e}", file=sys.stderr)
            time.sleep(interval_s)
            continue
        status = (body.get("status") or "").lower()
        if status != last_status:
            print(f"  [hedra] status={status} progress={body.get('progress')}",
                  file=sys.stderr)
            last_status = status
        if status in ("complete", "completed", "succeeded"):
            return body
        if status in ("failed", "error", "canceled", "cancelled"):
            raise RuntimeError(f"generation {gen_id} ended: {body}")
        time.sleep(interval_s)
    raise TimeoutError(f"generation {gen_id} timed out after {timeout_s}s")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: _recover.py <slug> <generation_id>", file=sys.stderr)
        return 2
    slug, gen_id = sys.argv[1], sys.argv[2]
    product_dir = PRODUCTS / slug
    manifest_path = product_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"no manifest at {manifest_path}", file=sys.stderr)
        return 1
    output_path = product_dir / OUTPUT_NAME

    key = hc.api_key()
    body = poll_tolerant(key, gen_id)
    url = hc.extract_download_url(body)
    if not url:
        asset_id = body.get("asset_id")
        if asset_id:
            url = hc.fetch_asset_url(key, asset_id, "video")
    if not url:
        print(f"completed but no download_url: {body}", file=sys.stderr)
        return 1

    print(f"[{slug}] downloading mp4…", file=sys.stderr)
    hc.download(url, output_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[MANIFEST_KEY] = OUTPUT_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK\t{slug}\t{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
