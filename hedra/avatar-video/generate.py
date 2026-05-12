"""
Hedra Avatar talking-head video generator.

For one or more product slugs (folders under ../../products/), upload that
product's starting-pic.png and narration.mp3 to Hedra, kick off a Hedra Avatar
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
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
sys.path.insert(0, str(PARENT))
import _common as hc  # noqa: E402

REPO_ROOT = PARENT.parent
PRODUCTS_DIR = REPO_ROOT / "products"

STARTING_PIC_NAME = "starting-pic.png"
NARRATION_NAME = "narration.mp3"
OUTPUT_NAME = "raw-speaker-video.mp4"
MANIFEST_KEY = "raw-speaker-video-path"

DEFAULT_AVATAR_MODEL_ID = "26f0fc66-152b-40ab-abed-76c43df99bc8"


def _model_id() -> str:
    return os.getenv("HEDRA_AVATAR_MODEL_ID", DEFAULT_AVATAR_MODEL_ID)


def _load_manifest(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _save_manifest(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve_slugs(args: argparse.Namespace) -> list[str]:
    if args.all_needing:
        slugs = []
        for child in sorted(PRODUCTS_DIR.iterdir()):
            if not child.is_dir():
                continue
            if not (child / "manifest.json").exists():
                continue
            if not (child / STARTING_PIC_NAME).exists():
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


def _process(slug: str, key: str, overwrite: bool) -> tuple[str, str]:
    folder = PRODUCTS_DIR / slug
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        return ("FAIL", f"missing {manifest_path}")
    manifest = _load_manifest(manifest_path)

    image_path = folder / STARTING_PIC_NAME
    audio_path = folder / NARRATION_NAME
    output_path = folder / OUTPUT_NAME

    if not image_path.exists():
        return ("FAIL", f"missing {STARTING_PIC_NAME}")
    if not audio_path.exists():
        return ("FAIL", f"missing {NARRATION_NAME} — run /generate-narration first")

    if output_path.exists() and not overwrite:
        if manifest.get(MANIFEST_KEY) != OUTPUT_NAME:
            manifest[MANIFEST_KEY] = OUTPUT_NAME
            _save_manifest(manifest_path, manifest)
            return ("FIXED", "manifest synced")
        return ("SKIP", "video already exists")

    text_prompt = (
        manifest.get("video-prompt")
        or manifest.get("script-raw-text")
        or "A person speaking to the camera"
    )

    print(f"[{slug}] uploading audio…", file=sys.stderr)
    audio_id = hc.upload_file(key, audio_path, "audio")

    print(f"[{slug}] uploading image…", file=sys.stderr)
    image_id = hc.upload_file(key, image_path, "image")

    print(f"[{slug}] starting generation…", file=sys.stderr)
    gen_id = hc.start_generation(
        key,
        {
            "type": "video",
            "ai_model_id": _model_id(),
            "start_keyframe_id": image_id,
            "audio_id": audio_id,
            "generated_video_inputs": {
                "text_prompt": text_prompt[:500],
                "aspect_ratio": "9:16",
                "resolution": "720p",
            },
        },
    )

    # Hedra Avatar can sit in `queued` for 30+ minutes when the queue is
    # backed up. Use a 60-minute cap and 15s poll interval. If we still
    # time out, the generation may finish later — `_recover_<slug>.py`
    # patterns can fetch the asset by id.
    body = hc.poll(key, gen_id, interval_s=15, timeout_s=60 * 60)
    url = hc.extract_download_url(body)
    if not url:
        # Avatar `complete` payload sometimes returns asset_id but no URL.
        # Fall back to GET /assets?type=video&ids=<asset_id>.
        asset_id = body.get("asset_id")
        if asset_id:
            url = hc.fetch_asset_url(key, asset_id, "video")
    if not url:
        return ("FAIL", f"completed but no download_url in response: {body}")

    print(f"[{slug}] downloading mp4…", file=sys.stderr)
    hc.download(url, output_path)

    manifest[MANIFEST_KEY] = OUTPUT_NAME
    _save_manifest(manifest_path, manifest)
    return ("OK", f"generation {gen_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", help="comma-separated slugs")
    ap.add_argument("--all-needing", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    key = hc.api_key()
    slugs = _resolve_slugs(args)
    if not slugs:
        print("nothing to do.", file=sys.stderr)
        return 0

    counts = {"OK": 0, "FIXED": 0, "SKIP": 0, "FAIL": 0}
    for slug in slugs:
        try:
            status, detail = _process(slug, key, args.overwrite)
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
