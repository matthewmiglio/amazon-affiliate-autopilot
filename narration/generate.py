"""Generate narration mp3s for Amazon affiliate products via ElevenLabs.

Reads each product's `script-raw-text` from manifest.json, calls ElevenLabs's
text-to-speech API, and writes `narration.mp3` into the product folder.

Authoring the script is NOT this tool's job — see the /write-script skill.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PRODUCTS_DIR = PROJECT_ROOT / "products"
STATUS_SCRIPT = PROJECT_ROOT / "scripts" / "status.py"

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"


def generate_audio(text: str, voice_id: str, api_key: str, out_path: Path) -> int:
    client = ElevenLabs(api_key=api_key)
    audio_iter = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with out_path.open("wb") as f:
        for chunk in audio_iter:
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

    nbytes = generate_audio(script, voice_id, api_key, out_path)
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

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY missing from .env", file=sys.stderr)
        return 1
    if not voice_id:
        print("ERROR: ELEVENLABS_VOICE_ID is empty. Pin a voice id in narration/.env first.",
              file=sys.stderr)
        return 1

    slugs = resolve_slugs(args.products, args.all_needing)
    if not slugs:
        print("ERROR: pass --products <slug>[,<slug>...] or --all-needing", file=sys.stderr)
        return 1

    ok = skipped = fixed = failed = 0
    for slug in slugs:
        try:
            status, detail = generate_one(slug, voice_id, api_key, args.overwrite)
        except Exception as e:
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
