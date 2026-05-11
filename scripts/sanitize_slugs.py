"""Rename product folders whose slug ends with punctuation a URL parser hates.

Trailing hyphens are the worst offender — YouTube's mobile auto-linkifier
greedily eats the next word across a newline boundary into URLs that end
with `-`. Same hazard for trailing `_`, `.`, `,`.

This script:
  - Scans products/<slug>/ folders.
  - Skips any slug whose manifest shows youtube.uploaded=true (live videos
    have descriptions baked with the old URL; renaming would break those).
  - For the rest, strips trailing `-`, `_`, `.`, `,` (and the few patterns
    like `-and-`, `-with-` left dangling) and renames the folder.

Run idempotently. Safe to re-run; only renames folders that need it.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "products"

TRAILING_JUNK = re.compile(r"(?:-(?:and|with|or|to|for|the|of|in|on)?-?|[-_.,]+)$", re.I)


def clean_slug(slug: str) -> str:
    out = slug
    while True:
        new = TRAILING_JUNK.sub("", out)
        if new == out:
            return new or slug  # never return empty
        out = new


def is_uploaded(manifest_path: Path) -> bool:
    try:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(((m.get("uploads") or {}).get("youtube") or {}).get("uploaded"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print actions without renaming.")
    args = ap.parse_args()

    renamed = 0
    skipped_uploaded = 0
    untouched = 0
    collisions = []

    for pdir in sorted(PRODUCTS.iterdir()):
        if not pdir.is_dir():
            continue
        slug = pdir.name
        new = clean_slug(slug)
        if new == slug:
            untouched += 1
            continue
        manifest = pdir / "manifest.json"
        if manifest.exists() and is_uploaded(manifest):
            print(f"SKIP  uploaded  {slug}")
            skipped_uploaded += 1
            continue
        target = PRODUCTS / new
        if target.exists():
            print(f"FAIL  collision {slug} -> {new} (target exists)")
            collisions.append((slug, new))
            continue
        print(f"{'DRY  ' if args.dry_run else 'RENAME'}  {slug}\n           -> {new}")
        if not args.dry_run:
            shutil.move(str(pdir), str(target))
        renamed += 1

    print(f"\n{renamed} renamed, {skipped_uploaded} uploaded-skip, {untouched} untouched, {len(collisions)} collisions.")
    return 1 if collisions else 0


if __name__ == "__main__":
    raise SystemExit(main())
