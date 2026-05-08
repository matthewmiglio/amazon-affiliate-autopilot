"""Stitch narration.mp3 over raw-speaker-video.mp4 to produce stitched-narration-speaker-video.mp4.

Mirrors the CLI shape of narration/generate.py:
    python scripts/stitch_narration.py --products slug1,slug2
    python scripts/stitch_narration.py --all-needing
    python scripts/stitch_narration.py --products slug1 --overwrite

Output rows: <slug>\\t<STATUS>\\t<detail>  where STATUS in {OK, FIXED, SKIP, FAIL}.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"
STATUS_PY = ROOT / "scripts" / "status.py"

RAW_VIDEO_NAME = "raw-speaker-video.mp4"
NARRATION_NAME = "narration.mp3"
OUTPUT_NAME = "stitched-narration-speaker-video.mp4"
MANIFEST_KEY = "stitched-narration-video-path"

FFMPEG_CANDIDATES = [r"C:\ffmpeg\bin\ffmpeg.exe", "ffmpeg"]


def find_ffmpeg() -> str:
    for c in FFMPEG_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    raise RuntimeError("ffmpeg not found (tried C:\\ffmpeg\\bin\\ffmpeg.exe and PATH)")


def load_manifest(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def save_manifest(path: Path, data: OrderedDict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def set_manifest_field(manifest: OrderedDict, value: str) -> OrderedDict:
    """Ensure MANIFEST_KEY is present and equal to value, inserted after raw-speaker-video-path."""
    if manifest.get(MANIFEST_KEY) == value and MANIFEST_KEY in manifest:
        return manifest
    new = OrderedDict()
    inserted = False
    for k, v in manifest.items():
        if k == MANIFEST_KEY:
            continue
        new[k] = v
        if k == "raw-speaker-video-path":
            new[MANIFEST_KEY] = value
            inserted = True
    if not inserted:
        new[MANIFEST_KEY] = value
    return new


def run_ffmpeg(ffmpeg: str, video: Path, audio: Path, out: Path) -> tuple[bool, str]:
    cmd = [
        ffmpeg, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()[-3:]
        return False, " | ".join(tail) or f"ffmpeg exit {r.returncode}"
    return True, ""


def resolve_all_needing() -> list[str]:
    r = subprocess.run(
        [sys.executable, str(STATUS_PY), "--needs-stitched-narration", "--json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout.strip() or "[]")


def process(slug: str, ffmpeg: str, overwrite: bool) -> tuple[str, str]:
    pdir = PRODUCTS_DIR / slug
    manifest_path = pdir / "manifest.json"
    if not manifest_path.exists():
        return "FAIL", f"no manifest.json at {manifest_path}"

    raw_video = pdir / RAW_VIDEO_NAME
    narration = pdir / NARRATION_NAME
    output = pdir / OUTPUT_NAME

    if not raw_video.exists():
        return "FAIL", f"missing {RAW_VIDEO_NAME} - generate the AI talking-head video first"
    if not narration.exists():
        return "FAIL", f"missing {NARRATION_NAME} - run /generate-narration first"

    manifest = load_manifest(manifest_path)
    expected = OUTPUT_NAME

    if output.exists() and not overwrite:
        if manifest.get(MANIFEST_KEY) == expected:
            return "SKIP", "stitched video already present, manifest aligned"
        new_manifest = set_manifest_field(manifest, expected)
        save_manifest(manifest_path, new_manifest)
        return "FIXED", f"manifest synced to {expected}"

    ok, err = run_ffmpeg(ffmpeg, raw_video, narration, output)
    if not ok:
        return "FAIL", err

    if manifest.get(MANIFEST_KEY) != expected:
        manifest = set_manifest_field(manifest, expected)
        save_manifest(manifest_path, manifest)
    size_mb = output.stat().st_size / 1_000_000
    return "OK", f"wrote {OUTPUT_NAME} ({size_mb:.2f} MB)"


def main() -> int:
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--products", help="Comma-separated product slugs.")
    g.add_argument("--all-needing", action="store_true",
                   help="Process every product missing a stitched-narration video.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-run ffmpeg even if the stitched output already exists.")
    args = parser.parse_args()

    if args.all_needing:
        slugs = resolve_all_needing()
    else:
        slugs = [s.strip() for s in args.products.split(",") if s.strip()]

    if not slugs:
        print("nothing to do.")
        return 0

    try:
        ffmpeg = find_ffmpeg()
    except RuntimeError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2

    counts = {"OK": 0, "FIXED": 0, "SKIP": 0, "FAIL": 0}
    for slug in slugs:
        status, detail = process(slug, ffmpeg, args.overwrite)
        counts[status] = counts.get(status, 0) + 1
        print(f"{slug}\t{status}\t{detail}")

    print(f"\n{counts['OK']} stitched, {counts['FIXED']} manifest-fixed, "
          f"{counts['SKIP']} skipped, {counts['FAIL']} failed.")
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
