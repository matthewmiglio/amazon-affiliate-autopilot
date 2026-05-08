"""Overlay random background music onto a product's stitched-narration video.

Reads `products/<slug>/stitched-narration-speaker-video.mp4`, picks a random
mp3 from `music/` that is at least as long as the video, mixes it under the
narration at a level that keeps the voice on top, fades music in/out, and
writes `final-with-music.mp4` next to the source.

    python scripts/overlay_music.py --product <slug-or-path>
    python scripts/overlay_music.py --product <...> --overwrite

Output rows: <slug>\\t<STATUS>\\t<detail>  where STATUS in {OK, SKIP, FAIL}.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"
MUSIC_DIR = ROOT / "music"

INPUT_NAME = "captioned-video.mp4"
OUTPUT_NAME = "final-with-music.mp4"
MANIFEST_KEY = "final-with-music-video-path"
MUSIC_TRACK_KEY = "background-music-track"

FFMPEG_CANDIDATES = [r"C:\ffmpeg\bin\ffmpeg.exe", "ffmpeg"]
FFPROBE_CANDIDATES = [r"C:\ffmpeg\bin\ffprobe.exe", "ffprobe"]

FADE_IN_SEC = 1.5
FADE_OUT_SEC = 2.0
# Target gap between narration mean loudness and music mean loudness.
# Music sits ~14 dB below the voice -> bed level, never competes.
DUCK_BELOW_VOICE_DB = 15.41
# Fallback music level if narration loudness can't be measured.
FALLBACK_MUSIC_VOLUME_DB = -23.41


def _find(candidates: list[str], label: str) -> str:
    for c in candidates:
        if Path(c).exists() or shutil.which(c):
            return c
    raise RuntimeError(f"{label} not found (tried {candidates})")


def find_ffmpeg() -> str:
    return _find(FFMPEG_CANDIDATES, "ffmpeg")


def find_ffprobe() -> str:
    return _find(FFPROBE_CANDIDATES, "ffprobe")


def load_manifest(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def save_manifest(path: Path, data: OrderedDict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def set_manifest_fields(manifest: OrderedDict, fields: dict) -> OrderedDict:
    """Insert/update fields after `stitched-narration-video-path` (or at end)."""
    new = OrderedDict()
    for k, v in manifest.items():
        if k in fields:
            continue
        new[k] = v
    for k, v in fields.items():
        new[k] = v
    return new


def probe_duration(ffprobe: str, path: Path) -> float:
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def measure_mean_volume_db(ffmpeg: str, path: Path) -> float | None:
    """Return mean_volume in dBFS via ffmpeg volumedetect, or None on failure."""
    cmd = [ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
           "-vn", "-af", "volumedetect", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stderr or "") + (r.stdout or "")
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", out)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def pick_music_track(min_duration: float, ffprobe: str) -> Path | None:
    candidates = list(MUSIC_DIR.glob("*.mp3"))
    random.shuffle(candidates)
    for c in candidates:
        try:
            if probe_duration(ffprobe, c) >= min_duration:
                return c
        except (subprocess.CalledProcessError, ValueError):
            continue
    return None


def resolve_product_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_absolute() and p.exists() and p.is_dir():
        return p
    candidate = PRODUCTS_DIR / arg
    return candidate


def run_mux(
    ffmpeg: str,
    video: Path,
    music: Path,
    music_volume_db: float,
    duration: float,
    out: Path,
) -> tuple[bool, str]:
    fade_out_start = max(0.0, duration - FADE_OUT_SEC)
    music_chain = (
        f"[1:a]volume={music_volume_db:.2f}dB,"
        f"afade=t=in:st=0:d={FADE_IN_SEC},"
        f"afade=t=out:st={fade_out_start:.3f}:d={FADE_OUT_SEC}[bg]"
    )
    mix = "[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
    filter_complex = f"{music_chain};{mix}"
    cmd = [
        ffmpeg, "-y",
        "-i", str(video),
        "-stream_loop", "0", "-i", str(music),
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
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


def process(product_arg: str, ffmpeg: str, ffprobe: str, overwrite: bool) -> tuple[str, str, str]:
    pdir = resolve_product_dir(product_arg)
    slug = pdir.name
    if not pdir.exists() or not pdir.is_dir():
        return slug, "FAIL", f"no product dir at {pdir}"

    manifest_path = pdir / "manifest.json"
    if not manifest_path.exists():
        return slug, "FAIL", f"no manifest.json at {manifest_path}"

    src_video = pdir / INPUT_NAME
    if not src_video.exists():
        return slug, "FAIL", f"missing {INPUT_NAME} - run /caption-video first"

    out_video = pdir / OUTPUT_NAME
    manifest = load_manifest(manifest_path)

    if out_video.exists() and not overwrite:
        if manifest.get(MANIFEST_KEY) == OUTPUT_NAME:
            return slug, "SKIP", "final-with-music already present, manifest aligned"
        manifest = set_manifest_fields(manifest, {MANIFEST_KEY: OUTPUT_NAME})
        save_manifest(manifest_path, manifest)
        return slug, "FIXED", f"manifest synced to {OUTPUT_NAME}"

    duration = probe_duration(ffprobe, src_video)
    music = pick_music_track(duration, ffprobe)
    if music is None:
        return slug, "FAIL", f"no music track in {MUSIC_DIR} long enough ({duration:.1f}s)"

    voice_db = measure_mean_volume_db(ffmpeg, src_video)
    if voice_db is None:
        music_volume_db = FALLBACK_MUSIC_VOLUME_DB
    else:
        music_db_target = voice_db - DUCK_BELOW_VOICE_DB
        # measure music to compute a relative gain
        music_native_db = measure_mean_volume_db(ffmpeg, music)
        if music_native_db is None:
            music_volume_db = FALLBACK_MUSIC_VOLUME_DB
        else:
            music_volume_db = music_db_target - music_native_db

    # clamp to a sane range
    music_volume_db = max(-40.0, min(0.0, music_volume_db))

    ok, err = run_mux(ffmpeg, src_video, music, music_volume_db, duration, out_video)
    if not ok:
        return slug, "FAIL", err

    manifest = set_manifest_fields(manifest, {
        MANIFEST_KEY: OUTPUT_NAME,
        MUSIC_TRACK_KEY: music.name,
    })
    save_manifest(manifest_path, manifest)
    size_mb = out_video.stat().st_size / 1_000_000
    return slug, "OK", f"wrote {OUTPUT_NAME} ({size_mb:.2f} MB) bg={music.name} gain={music_volume_db:.1f}dB"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", required=True,
                        help="Slug under products/, or absolute product folder path.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-run even if final-with-music.mp4 already exists.")
    args = parser.parse_args()

    try:
        ffmpeg = find_ffmpeg()
        ffprobe = find_ffprobe()
    except RuntimeError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2

    if not MUSIC_DIR.exists() or not any(MUSIC_DIR.glob("*.mp3")):
        print(f"FATAL: no music tracks in {MUSIC_DIR} - run /import-music first", file=sys.stderr)
        return 2

    slug, status, detail = process(args.product, ffmpeg, ffprobe, args.overwrite)
    print(f"{slug}\t{status}\t{detail}")
    return 0 if status not in ("FAIL",) else 1


if __name__ == "__main__":
    raise SystemExit(main())
