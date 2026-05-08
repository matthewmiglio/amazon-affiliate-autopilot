"""Apply authored narration scripts to product folders.

Reads a JSON file mapping slug -> script text, then for each entry sets
manifest.json `script-raw-text` to the script string. The manifest is the
single source of truth — no sibling script.txt is written.

Usage:
  python apply_scripts.py path/to/scripts.json
  python apply_scripts.py path/to/scripts.json --overwrite
  cat scripts.json | python apply_scripts.py -    # read from stdin
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "products"


def load_scripts(source: str) -> dict[str, str]:
    if source == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(source).read_text(encoding="utf-8"))


def apply(scripts: dict[str, str], overwrite: bool) -> tuple[int, list[str]]:
    written = 0
    skipped: list[str] = []
    for slug, script in scripts.items():
        pdir = PRODUCTS / slug
        mpath = pdir / "manifest.json"
        if not mpath.exists():
            skipped.append(f"{slug} — no manifest")
            continue
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        if (manifest.get("script-raw-text") or "").strip() and not overwrite:
            skipped.append(f"{slug} — already has script (use --overwrite)")
            continue
        text = script.strip()
        manifest["script-raw-text"] = text
        mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        written += 1
    return written, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Path to JSON file with {slug: script} (or - for stdin).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite existing scripts.")
    args = parser.parse_args()

    scripts = load_scripts(args.source)
    written, skipped = apply(scripts, args.overwrite)
    print(f"Wrote {written} script(s). Skipped: {len(skipped)}")
    for s in skipped:
        print(f"  - {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
