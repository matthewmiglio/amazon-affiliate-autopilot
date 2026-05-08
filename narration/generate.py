"""Generate narration mp3s for Amazon affiliate products via Hedra TTS.

Reads each product's `script-raw-text` from manifest.json, calls Hedra's
text-to-speech API, and writes `narration.mp3` into the product folder.

Authoring the script is NOT this tool's job — see the /write-script skill.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PRODUCTS_DIR = PROJECT_ROOT / "products"
STATUS_SCRIPT = PROJECT_ROOT / "scripts" / "status.py"

HEDRA_BASE = "https://api.hedra.com/web-app/public"
POLL_INTERVAL_S = 2
POLL_MAX_S = 120


class HedraError(RuntimeError):
    pass


def hedra_headers(api_key: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def post_tts(text: str, voice_id: str, api_key: str) -> str:
    body = {
        "type": "text_to_speech",
        "voice_id": voice_id,
        "text": text,
        "stability": 0.5,
        "speed": 1.0,
        "language": "English",
    }
    r = requests.post(f"{HEDRA_BASE}/generations", json=body, headers=hedra_headers(api_key), timeout=30)
    if r.status_code >= 300:
        raise HedraError(f"POST /generations failed: {r.status_code} {r.text}")
    data = r.json()
    gid = data.get("generation_id") or data.get("id")
    if not gid:
        raise HedraError(f"no generation_id in response: {data}")
    return gid


def poll_until_complete(gen_id: str, api_key: str) -> dict:
    deadline = time.time() + POLL_MAX_S
    last: dict = {}
    while time.time() < deadline:
        r = requests.get(f"{HEDRA_BASE}/generations/{gen_id}/status", headers=hedra_headers(api_key), timeout=30)
        if r.status_code >= 300:
            raise HedraError(f"GET status failed: {r.status_code} {r.text}")
        last = r.json()
        status = (last.get("status") or "").lower()
        if status == "complete":
            return last
        if status in ("failed", "error"):
            raise HedraError(f"generation failed: {last}")
        time.sleep(POLL_INTERVAL_S)
    raise HedraError(f"timeout after {POLL_MAX_S}s; last={last}")


def extract_audio_url(status_payload: dict, api_key: str) -> str:
    """Find the mp3 URL in the completed-generation payload.

    The exact shape isn't fully pinned in public docs, so we probe a few common
    locations and fall back to fetching the asset record by id.
    """
    for key in ("url", "asset_url", "audio_url", "output_url"):
        v = status_payload.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
    asset = status_payload.get("asset") or {}
    if isinstance(asset, dict):
        for key in ("url", "download_url"):
            v = asset.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
    asset_id = status_payload.get("asset_id") or (asset.get("id") if isinstance(asset, dict) else None)
    if asset_id:
        r = requests.get(f"{HEDRA_BASE}/assets/{asset_id}", headers=hedra_headers(api_key), timeout=30)
        if r.status_code < 300:
            ad = r.json()
            for key in ("url", "download_url", "asset_url"):
                v = ad.get(key)
                if isinstance(v, str) and v.startswith("http"):
                    return v
    raise HedraError(f"could not locate audio url; payload keys={list(status_payload.keys())}")


def download(url: str, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = 0
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
    return total


def resolve_slugs(products: str | None, all_needing: bool) -> list[str]:
    if all_needing:
        out = subprocess.run(
            [sys.executable, str(STATUS_SCRIPT), "--needs-narration", "--json"],
            check=True, capture_output=True, text=True,
        )
        return json.loads(out.stdout)
    if products:
        return [s.strip() for s in products.split(",") if s.strip()]
    return []


def generate_one(slug: str, voice_id: str, api_key: str, overwrite: bool) -> tuple[str, str]:
    pdir = PRODUCTS_DIR / slug
    mpath = pdir / "manifest.json"
    if not mpath.exists():
        return "FAIL", "no manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    script = (manifest.get("script-raw-text") or "").strip()
    if not script:
        return "FAIL", "empty script-raw-text — run /write-script first"

    out_path = pdir / "narration.mp3"
    manifest_points_to_mp3 = (manifest.get("narration-audio-path") or "").strip() == "narration.mp3"

    if out_path.exists() and not overwrite:
        if manifest_points_to_mp3:
            return "SKIP", "narration.mp3 already exists, manifest aligned"
        manifest["narration-audio-path"] = "narration.mp3"
        mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return "FIXED", "narration.mp3 existed, manifest updated"

    gen_id = post_tts(script, voice_id, api_key)
    payload = poll_until_complete(gen_id, api_key)
    url = extract_audio_url(payload, api_key)
    nbytes = download(url, out_path)

    manifest["narration-audio-path"] = "narration.mp3"
    mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return "OK", f"{nbytes} bytes"


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--products", help="Single slug or comma-list of slugs.")
    parser.add_argument("--all-needing", action="store_true",
                        help="Generate for every product missing narration.mp3.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Regenerate even if narration.mp3 already exists.")
    args = parser.parse_args()

    api_key = os.environ.get("HEDRA_API_KEY", "").strip()
    voice_id = os.environ.get("HEDRA_VOICE_ID", "").strip()
    if not api_key:
        print("ERROR: HEDRA_API_KEY missing from .env", file=sys.stderr)
        return 1
    if not voice_id:
        print("ERROR: HEDRA_VOICE_ID is empty. Run `poetry run python list_voices.py` "
              "and pin a voice id in narration/.env first.", file=sys.stderr)
        return 1

    slugs = resolve_slugs(args.products, args.all_needing)
    if not slugs:
        print("ERROR: pass --products <slug>[,<slug>...] or --all-needing", file=sys.stderr)
        return 1

    ok = skipped = fixed = failed = 0
    for slug in slugs:
        try:
            status, detail = generate_one(slug, voice_id, api_key, args.overwrite)
        except (HedraError, requests.RequestException) as e:
            status, detail = "FAIL", str(e)
        print(f"{slug}\t{status}\t{detail}")
        if status == "OK":
            ok += 1
        elif status == "SKIP":
            skipped += 1
        elif status == "FIXED":
            fixed += 1
        else:
            failed += 1

    print(f"\n{ok} generated, {fixed} manifest-fixed, {skipped} skipped, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
