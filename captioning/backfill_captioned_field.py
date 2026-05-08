"""One-shot: insert ``"captioned-video-path": ""`` into every product manifest.

Idempotent — manifests that already have the key are left alone. The
new key is inserted directly after ``stitched-narration-video-path``
to keep ordering aligned with ``import-referral-data``'s schema.

    poetry run python backfill_captioned_field.py
"""
from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"

KEY = "captioned-video-path"
INSERT_AFTER = "stitched-narration-video-path"


def insert_after(d: OrderedDict, after_key: str, new_key: str, value) -> OrderedDict:
    new = OrderedDict()
    inserted = False
    for k, v in d.items():
        if k == new_key:
            continue
        new[k] = v
        if k == after_key:
            new[new_key] = value
            inserted = True
    if not inserted:
        new[new_key] = value
    return new


def main() -> int:
    if not PRODUCTS_DIR.exists():
        print(f"products dir missing: {PRODUCTS_DIR}", file=sys.stderr)
        return 2

    backfilled = 0
    already = 0
    skipped = 0
    for sub in sorted(PRODUCTS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        manifest = sub / "manifest.json"
        if not manifest.exists():
            skipped += 1
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"),
                          object_pairs_hook=OrderedDict)
        if KEY in data:
            already += 1
            continue
        data = insert_after(data, INSERT_AFTER, KEY, "")
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        backfilled += 1

    print(f"backfilled {backfilled} manifest(s), {already} already had '{KEY}', "
          f"{skipped} folder(s) without manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
