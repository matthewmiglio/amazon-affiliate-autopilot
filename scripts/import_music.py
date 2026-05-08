"""Import mp4 recordings as background-music mp3s.

Convert each mp4 to mp3, strip leading/trailing silence, and save into
`music/<adjective>-<animal>.mp3`.

    python scripts/import_music.py --src "D:/path/to/folder"
    python scripts/import_music.py --src "D:/path/to/file.mp4"

Output rows: <source>\\t<STATUS>\\t<detail>  where STATUS in {OK, SKIP, FAIL}.
"""
from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "music"

FFMPEG_CANDIDATES = [r"C:\ffmpeg\bin\ffmpeg.exe", "ffmpeg"]

ADJECTIVES = [
    "prickly", "velvet", "amber", "fuzzy", "drowsy", "lucid", "brisk",
    "dapper", "feral", "glassy", "honey", "icy", "jolly", "kooky", "lavender",
    "misty", "noble", "opaque", "plucky", "quiet", "rusty", "silken", "tawny",
    "umber", "vivid", "wily", "yonder", "zesty", "twilight", "moonlit",
    "stormy", "balmy", "crimson", "dusky", "ember", "frosty", "golden",
    "hazel", "ivory", "jagged", "kindred", "lonesome", "mellow",
]
ANIMALS = [
    "octopus", "raven", "otter", "lynx", "panda", "ferret", "heron", "wolf",
    "moth", "newt", "owl", "puffin", "quokka", "robin", "seal", "tiger",
    "urial", "viper", "walrus", "xerus", "yak", "zebra", "badger", "coyote",
    "dolphin", "egret", "fox", "gecko", "hyena", "ibis", "jackal", "koala",
    "lemur", "mantis", "narwhal", "ocelot", "pangolin", "quail",
]


def find_ffmpeg() -> str:
    for c in FFMPEG_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    raise RuntimeError("ffmpeg not found (tried C:\\ffmpeg\\bin\\ffmpeg.exe and PATH)")


def existing_slugs() -> set[str]:
    return {p.stem for p in MUSIC_DIR.glob("*.mp3")}


def coin_slug(taken: set[str]) -> str:
    for _ in range(500):
        slug = f"{random.choice(ADJECTIVES)}-{random.choice(ANIMALS)}"
        if slug not in taken:
            return slug
    # last resort
    n = 2
    while True:
        slug = f"{random.choice(ADJECTIVES)}-{random.choice(ANIMALS)}-{n}"
        if slug not in taken:
            return slug
        n += 1


def collect_inputs(src: Path) -> list[Path]:
    if src.is_file():
        return [src] if src.suffix.lower() == ".mp4" else []
    if src.is_dir():
        return sorted(src.glob("*.mp4"))
    return []


def convert_and_trim(ffmpeg: str, src: Path, dst: Path) -> tuple[bool, str]:
    """mp4 -> mp3 with silenceremove on both ends.

    silenceremove filter:
      start_periods=1, start_silence=0.1s, start_threshold=-45dB
      stop_periods=1, stop_silence=0.5s, stop_threshold=-45dB (detected mode)
    """
    # Use rms detection at -50dB so quiet musical passages aren't treated as
    # silence. Require a sustained run (>=0.5s leading, >=1.0s trailing) before
    # trimming, so brief gaps within the song stay intact.
    af = (
        "silenceremove="
        "start_periods=1:start_duration=0.5:start_threshold=-50dB:detection=rms,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=1.0:start_threshold=-50dB:detection=rms,"
        "areverse"
    )
    cmd = [
        ffmpeg, "-y",
        "-i", str(src),
        "-vn",
        "-af", af,
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()[-3:]
        return False, " | ".join(tail) or f"ffmpeg exit {r.returncode}"
    if not dst.exists() or dst.stat().st_size < 1024:
        return False, "output mp3 missing or too small"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Folder of mp4s or a single mp4 path.")
    args = parser.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"FATAL: src does not exist: {src}", file=sys.stderr)
        return 2

    inputs = collect_inputs(src)
    if not inputs:
        print("nothing to do (no .mp4 files found).")
        return 0

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    try:
        ffmpeg = find_ffmpeg()
    except RuntimeError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2

    taken = existing_slugs()
    counts = {"OK": 0, "SKIP": 0, "FAIL": 0}

    for mp4 in inputs:
        slug = coin_slug(taken)
        dst = MUSIC_DIR / f"{slug}.mp3"
        ok, err = convert_and_trim(ffmpeg, mp4, dst)
        if not ok:
            counts["FAIL"] += 1
            print(f"{mp4.name}\tFAIL\t{err}")
            if dst.exists():
                try:
                    dst.unlink()
                except OSError:
                    pass
            continue
        taken.add(slug)
        size_mb = dst.stat().st_size / 1_000_000
        counts["OK"] += 1
        try:
            mp4.unlink()
            note = "source mp4 deleted"
        except OSError as e:
            note = f"WARNING: could not delete source mp4 ({e})"
        print(f"{mp4.name}\tOK\t{slug}.mp3 ({size_mb:.2f} MB) — {note}")

    print(f"\n{counts['OK']} imported, {counts['SKIP']} skipped, {counts['FAIL']} failed.")
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
