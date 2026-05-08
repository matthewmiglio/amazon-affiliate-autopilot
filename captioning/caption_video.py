"""Auto-pick a caption style and burn it onto a product's stitched video.

CLI mirrors ``scripts/stitch_narration.py``:

    python captioning/caption_video.py --products slug1,slug2
    python captioning/caption_video.py --all-needing
    python captioning/caption_video.py --products slug1 --overwrite

For each slug, the script:
  1. Pre-flights (manifest + stitched-narration mp4 must exist).
  2. Transcribes the stitched video with WhisperX (cached as
     ``products/<slug>/captions.json`` so re-runs are fast).
  3. Samples background colors at top + middle regions across 3 frames.
  4. Scores every preset in ``presets.PRESETS`` by WCAG contrast
     (text or outline vs sampled bg, whichever wins) and randomly
     picks one from the top 3.
  5. Renders ``captioned-video.mp4`` next to the stitched mp4 using
     :func:`render.render`.
  6. Sets ``captioned-video-path`` in the manifest right after
     ``stitched-narration-video-path``.

Output rows: ``<slug>\\t<STATUS>\\t<detail>`` where STATUS in
{OK, FIXED, SKIP, FAIL}.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PRODUCTS_DIR = ROOT / "products"
STATUS_PY = ROOT / "scripts" / "status.py"

# Add this folder to sys.path so the flat-layout siblings import.
sys.path.insert(0, str(HERE))

from render import render  # noqa: E402
from transcribe import transcribe_video  # noqa: E402
from presets import PRESETS  # noqa: E402
from style_select import sample_frame_avgs, region_avg, pick_best  # noqa: E402


STITCHED_NAME = "stitched-narration-speaker-video.mp4"
CAPTIONS_JSON = "captions.json"
OUTPUT_NAME = "captioned-video.mp4"
MANIFEST_KEY = "captioned-video-path"
INSERT_AFTER = "stitched-narration-video-path"


def load_manifest(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def save_manifest(path: Path, data: OrderedDict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def set_manifest_field(manifest: OrderedDict, value: str) -> OrderedDict:
    if manifest.get(MANIFEST_KEY) == value and MANIFEST_KEY in manifest:
        return manifest
    new = OrderedDict()
    inserted = False
    for k, v in manifest.items():
        if k == MANIFEST_KEY:
            continue
        new[k] = v
        if k == INSERT_AFTER:
            new[MANIFEST_KEY] = value
            inserted = True
    if not inserted:
        new[MANIFEST_KEY] = value
    return new


def load_or_make_segments(stitched: Path) -> list[dict]:
    cache = stitched.parent / CAPTIONS_JSON
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        return data["segments"] if isinstance(data, dict) else data
    segments = transcribe_video(stitched)
    cache.write_text(json.dumps({"segments": segments}, indent=2),
                     encoding="utf-8")
    return segments


def resolve_all_needing() -> list[str]:
    r = subprocess.run(
        [sys.executable, str(STATUS_PY), "--needs-captioned", "--json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout.strip() or "[]")


def process(slug: str, overwrite: bool) -> tuple[str, str]:
    pdir = PRODUCTS_DIR / slug
    manifest_path = pdir / "manifest.json"
    if not manifest_path.exists():
        return "FAIL", f"no manifest.json at {manifest_path}"

    stitched = pdir / STITCHED_NAME
    output = pdir / OUTPUT_NAME

    if not stitched.exists():
        return "FAIL", f"missing {STITCHED_NAME} - run /stitch-narration first"

    manifest = load_manifest(manifest_path)
    expected = OUTPUT_NAME

    if output.exists() and not overwrite:
        if manifest.get(MANIFEST_KEY) == expected:
            return "SKIP", "captioned video already present, manifest aligned"
        save_manifest(manifest_path, set_manifest_field(manifest, expected))
        return "FIXED", f"manifest synced to {expected}"

    # Transcribe (cached).
    try:
        segments = load_or_make_segments(stitched)
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"transcription failed: {e}"

    # Sample backgrounds at top + middle and pick a style.
    try:
        per_frame = sample_frame_avgs(stitched, n_frames=3,
                                      regions=("top", "middle"))
        region_avgs = {r: region_avg(samples) for r, samples in per_frame.items()}
        name, style, score = pick_best(PRESETS, region_avgs, top_k=3)
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"style selection failed: {e}"

    # Render.
    try:
        render(stitched, segments, output, style)
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"render failed: {e}"

    if manifest.get(MANIFEST_KEY) != expected:
        manifest = set_manifest_field(manifest, expected)
        save_manifest(manifest_path, manifest)

    size_mb = output.stat().st_size / 1_000_000
    return "OK", (f"wrote {OUTPUT_NAME} ({size_mb:.2f} MB) "
                  f"using preset '{name}' contrast={score:.2f}")


def main() -> int:
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--products", help="Comma-separated product slugs.")
    g.add_argument("--all-needing", action="store_true",
                   help="Process every product missing a captioned video.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-run rendering even if the captioned mp4 exists.")
    args = parser.parse_args()

    if args.all_needing:
        slugs = resolve_all_needing()
    else:
        slugs = [s.strip() for s in args.products.split(",") if s.strip()]

    if not slugs:
        print("nothing to do.")
        return 0

    counts = {"OK": 0, "FIXED": 0, "SKIP": 0, "FAIL": 0}
    for slug in slugs:
        status, detail = process(slug, args.overwrite)
        counts[status] = counts.get(status, 0) + 1
        print(f"{slug}\t{status}\t{detail}")

    print(f"\n{counts['OK']} captioned, {counts['FIXED']} manifest-fixed, "
          f"{counts['SKIP']} skipped, {counts['FAIL']} failed.")
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
