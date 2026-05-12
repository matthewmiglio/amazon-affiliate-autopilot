"""
Shared Hedra Platform API helpers used by both the avatar-video and
starting-image subfolders. Loads HEDRA_API_KEY from the top-level .env.

Each subfolder's `generate.py` does:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import _common as hc

and then calls `hc.api_key()`, `hc.create_asset(...)`, etc.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
API_BASE = "https://api.hedra.com/web-app/public"


def api_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.getenv("HEDRA_API_KEY")
    if not key:
        sys.exit("HEDRA_API_KEY missing in hedra/.env")
    return key


def headers(key: str) -> dict:
    return {"X-API-Key": key}


def create_asset(key: str, name: str, asset_type: str) -> str:
    """asset_type ∈ {image, audio, video}. Returns the new asset's id."""
    r = requests.post(
        f"{API_BASE}/assets",
        headers={**headers(key), "Content-Type": "application/json"},
        json={"name": name, "type": asset_type},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def upload_asset(key: str, asset_id: str, path: Path) -> None:
    with path.open("rb") as f:
        r = requests.post(
            f"{API_BASE}/assets/{asset_id}/upload",
            headers=headers(key),
            files={"file": (path.name, f)},
            timeout=600,
        )
    r.raise_for_status()


def upload_file(key: str, path: Path, asset_type: str) -> str:
    """Convenience: create + upload in one shot. Returns the asset id."""
    asset_id = create_asset(key, path.name, asset_type)
    upload_asset(key, asset_id, path)
    return asset_id


def start_generation(key: str, body: dict) -> str:
    """POST /generations and return the generation id."""
    r = requests.post(
        f"{API_BASE}/generations",
        headers={**headers(key), "Content-Type": "application/json"},
        json=body,
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"generation start failed: {r.status_code} {r.text}")
    return r.json()["id"]


def poll(key: str, generation_id: str, *, interval_s: int = 10, timeout_s: int = 25 * 60) -> dict:
    deadline = time.time() + timeout_s
    last_status = ""
    while time.time() < deadline:
        r = requests.get(
            f"{API_BASE}/generations/{generation_id}/status",
            headers=headers(key),
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
        time.sleep(interval_s)
    raise TimeoutError(f"generation {generation_id} timed out after {timeout_s}s")


def extract_download_url(body: dict) -> Optional[str]:
    """Hedra's completed-generation payload puts the URL in different
    spots depending on the generation type. Probe the common keys."""
    for key in ("download_url", "url", "asset_url", "output_url"):
        v = body.get(key)
        if v:
            return v
    asset = body.get("asset") or {}
    for key in ("url", "download_url", "signed_url"):
        v = asset.get(key) if isinstance(asset, dict) else None
        if v:
            return v
    return None


def fetch_asset_url(key: str, asset_id: str, asset_type: str = "image") -> Optional[str]:
    """For image generations, the completed body has asset_id but no url —
    the URL lives on the asset record. Hit `/assets?type=<t>&ids=<id>`,
    which returns a list whose [0].asset.url is the actual download URL."""
    try:
        r = requests.get(
            f"{API_BASE}/assets",
            params={"type": asset_type, "ids": asset_id},
            headers=headers(key),
            timeout=60,
        )
        if not r.ok:
            return None
        body = r.json()
        if isinstance(body, list) and body:
            entry = body[0]
            inner = entry.get("asset") if isinstance(entry, dict) else None
            if isinstance(inner, dict):
                for k in ("url", "download_url", "signed_url"):
                    v = inner.get(k)
                    if v:
                        return v
            for k in ("url", "download_url", "signed_url", "thumbnail_url"):
                v = entry.get(k) if isinstance(entry, dict) else None
                if v and k != "thumbnail_url":  # don't fall back to thumbnail
                    return v
        return None
    except requests.RequestException:
        return None


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
