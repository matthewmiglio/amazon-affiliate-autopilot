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
        "script": yn(bool((m.get("script-raw-text") or "").strip())),
        "video-prompt": yn(bool((m.get("video-prompt") or "").strip())),
        "description": yn(bool((info.get("description") or "").strip())),
        "product-page-url": info.get("product-page-url", "") or "",
        "affiliate-link": info.get("affiliate-link", "") or "",
        "category": info.get("category", "") or "",
        "main-product-image": yn(has_file(m.get("main-product-image-path", ""))),
        "narration-audio": yn(has_file(m.get("narration-audio-path", ""))),
        "lifestyle-image": yn(has_file(m.get("lifestyle-image-path", ""))),
        "raw-speaker-video": yn(has_file(m.get("raw-speaker-video-path", ""))),
        "stitched-narration-video": yn(has_file(m.get("stitched-narration-video-path", ""))),
        "captioned-video": yn(has_file(m.get("captioned-video-path", ""))),
        "final-with-music": yn(has_file(m.get("final-with-music-video-path", ""))),
        "uploaded": yn(bool(m.get("uploaded"))),
    }


COL_HEADERS = {
    "commission": "comm%",
    "video-prompt": "vid prompt",
    "description": "desc",
    "main-product-image": "product img",
    "narration-audio": "narration",
    "lifestyle-image": "start img",
    "raw-speaker-video": "raw-gen-vid",
    "stitched-narration-video": "stitch-narration",
    "captioned-video": "captioned",
    "final-with-music": "with-music",
    "uploaded": "uploaded",
}


GREEN = "\033[32m"
RESET = "\033[0m"

DONE_VALUES = {"yes"}


def _colorize(col: str, value: str, width: int) -> str:
    padded = str(value).ljust(width)
    if str(value) in DONE_VALUES:
        return f"{GREEN}{padded}{RESET}"
    return padded


def print_matrix(rows: list[dict]) -> None:
    # Columns ordered to match the pipeline progression (steps 2-10).
    cols = [
        "item", "commission", "category", "affiliate-link",
        "description", "main-product-image",
        "video-prompt",              # step 2: video prompt
        "script",                    # step 3: script
        "narration-audio",           # step 4: narration
        "lifestyle-image",           # step 5: starting image
        "raw-speaker-video",         # step 6: raw hedra video
        "stitched-narration-video",  # step 7: stitched narration
        "captioned-video",           # step 8: captions
        "final-with-music",          # step 9: bg music
        "uploaded",                  # step 10: youtube
    ]
    headers = [COL_HEADERS.get(c, c) for c in cols]
    display = [{**r, "item": (r["item"][:27] + "...") if len(r["item"]) > 30 else r["item"]}
               for r in rows]
    widths = {c: max(len(h), *(len(str(r[c])) for r in display))
              for c, h in zip(cols, headers)} if display \
        else {c: len(h) for c, h in zip(cols, headers)}

    def fmt_header(values):
        return "| " + " | ".join(str(v).ljust(widths[c]) for c, v in zip(cols, values)) + " |"

    def fmt_row(values):
        return "| " + " | ".join(_colorize(c, v, widths[c]) for c, v in zip(cols, values)) + " |"

    print(fmt_header(headers))
    print("|" + "|".join("-" * (widths[c] + 2) for c in cols) + "|")
    for r in display:
        print(fmt_row([r[c] for c in cols]))


NEEDS_FLAGS = {
    "needs-script": "script",
    "needs-video-prompt": "video-prompt",
    "needs-description": "description",
    "needs-main-image": "main-product-image",
    "needs-narration": "narration-audio",
    "needs-lifestyle-pic": "lifestyle-image",
    "needs-raw-speaker-video": "raw-speaker-video",
    "needs-stitched-narration": "stitched-narration-video",
    "needs-captioned": "captioned-video",
    "needs-final-with-music": "final-with-music",
    "needs-upload": "uploaded",
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
            lacking = [c for c in active_needs if r[c] == "no"]
            print(f"{r['item']}\t{', '.join(lacking)}")
        print(f"\n{len(missing)} of {len(rows)} missing: {', '.join(active_needs)}")
    elif args.json:
        print(json.dumps([r["item"] for r in rows]))
    elif args.matrix:
        progress_cols = [
            "video-prompt", "script", "narration-audio", "lifestyle-image",
            "raw-speaker-video", "stitched-narration-video", "captioned-video",
            "final-with-music", "uploaded",
        ]
        rows.sort(key=lambda r: -sum(1 for c in progress_cols if r.get(c) == "yes"))
        print_matrix(rows)
    else:
        print(f"{len(rows)} product(s) in {PRODUCTS_DIR}")
        for r in rows:
            print(f"  - {r['item']} ({r['commission']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
