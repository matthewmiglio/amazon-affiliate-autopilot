"""Status report for Amazon affiliate products."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"


def yn(v) -> str:
    return "yes" if v else "no"


def row_for(product_dir: Path) -> dict | None:
    manifest_path = product_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    info = m.get("item-auxiliary-information", {}) or {}

    def has_file(rel: str) -> bool:
        if not rel:
            return False
        return (product_dir / rel).exists()

    return {
        "item": product_dir.name,
        "commission": m.get("commission-percentage", "") or "",
        "has script": yn(bool((m.get("script-raw-text") or "").strip())),
        "has video-prompt": yn(bool((m.get("video-prompt") or "").strip())),
        "has description": yn(bool((info.get("description") or "").strip())),
        "product-page-url": info.get("product-page-url", "") or "",
        "affiliate-link": info.get("affiliate-link", "") or "",
        "category": info.get("category", "") or "",
        "has main-product-image": yn(has_file(m.get("main-product-image-path", ""))),
        "has narration-audio": yn(has_file(m.get("narration-audio-path", ""))),
        "has lifestyle-image": yn(has_file(m.get("lifestyle-image-path", ""))),
    }


def print_matrix(rows: list[dict]) -> None:
    cols = [
        "item", "commission", "has script", "has video-prompt", "has description",
        "affiliate-link", "category",
        "has main-product-image", "has narration-audio", "has lifestyle-image",
    ]
    display = [{**r, "item": (r["item"][:27] + "...") if len(r["item"]) > 30 else r["item"]}
               for r in rows]
    widths = {c: max(len(c), *(len(str(r[c])) for r in display)) for c in cols} if display \
        else {c: len(c) for c in cols}

    def fmt(values):
        return "| " + " | ".join(str(v).ljust(widths[c]) for c, v in zip(cols, values)) + " |"

    print(fmt(cols))
    print("|" + "|".join("-" * (widths[c] + 2) for c in cols) + "|")
    for r in display:
        print(fmt([r[c] for c in cols]))


NEEDS_FLAGS = {
    "needs-script": "has script",
    "needs-video-prompt": "has video-prompt",
    "needs-description": "has description",
    "needs-main-image": "has main-product-image",
    "needs-narration": "has narration-audio",
    "needs-lifestyle-pic": "has lifestyle-image",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", action="store_true", help="Print the full status matrix.")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON of matching slugs (combine with --needs-* flags).")
    for flag in NEEDS_FLAGS:
        parser.add_argument(f"--{flag}", action="store_true",
                            help=f"List products missing {NEEDS_FLAGS[flag]}.")
    args = parser.parse_args()

    rows = []
    for sub in sorted(PRODUCTS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        r = row_for(sub)
        if r is not None:
            rows.append(r)

    active_needs = [col for flag, col in NEEDS_FLAGS.items()
                    if getattr(args, flag.replace("-", "_"))]

    if active_needs:
        missing = [r for r in rows if any(r[c] == "no" for c in active_needs)]
        if args.json:
            print(json.dumps([r["item"] for r in missing]))
            return 0
        for r in missing:
            lacking = [c.replace("has ", "") for c in active_needs if r[c] == "no"]
            print(f"{r['item']}\t{', '.join(lacking)}")
        print(f"\n{len(missing)} of {len(rows)} missing: {', '.join(active_needs)}")
    elif args.json:
        print(json.dumps([r["item"] for r in rows]))
    elif args.matrix:
        print_matrix(rows)
    else:
        print(f"{len(rows)} product(s) in {PRODUCTS_DIR}")
        for r in rows:
            print(f"  - {r['item']} ({r['commission']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
