"""
Hedra image generator: 3 character refs + product image -> composed
"podcast / UGC ad" starting frame at 9:16.

Per slug, this script:
  1. Picks 3 random images from the FACE_ANCHOR_REFS whitelist in
     assets/character/ (slug-seeded for stable re-runs). Whitelist is
     curated from QA — refs that hurt face lock are excluded.
  2. Loads the product image at products/<slug>/<product-pic-path>
     (falls back to product.png / product.jpg / product.webp).
  3. Builds a starting-image prompt via prompt_builder.build_prompt.
     The prompt leads with hard rules (face lock, mic in front, torso
     squared to camera, no vignette) before the scene description.
  4. POSTs /generations with type:"image" and reference_image_ids =
     [3 char refs..., product]. Uses Nano Banana Pro I2I by default
     ($HEDRA_IMAGE_MODEL_ID overrides). Resolution: 1K, aspect: 9:16.
  5. Polls, fetches the asset URL from /assets, downloads to
     <output-dir>/<slug>/<output-name> (default
     products/<slug>/starting-pic.png), and updates the manifest's
     `starting-pic-path`.

Idempotent: skips slugs whose target file already exists unless --overwrite.

Usage:
  python generate.py --products <slug>[,<slug>,...]
  python generate.py --all-needing
  python generate.py --products <slug> --overwrite
  python generate.py --products <slug> --reroll 1
  python generate.py --products <slug> --output-dir ../../hedra-starting-image-benchmarking/outputs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
sys.path.insert(0, str(PARENT))
import _common as hc  # noqa: E402

from prompt_builder import build_prompt  # noqa: E402  (same dir)

REPO_ROOT = PARENT.parent
PRODUCTS_DIR = REPO_ROOT / "products"
CHARACTER_DIR = REPO_ROOT / "assets" / "character"

OUTPUT_NAME = "starting-pic.png"
MANIFEST_KEY = "starting-pic-path"

PRODUCT_IMAGE_CANDIDATES = ["product.png", "product.jpg", "product.jpeg", "product.webp"]
CHARACTER_REF_COUNT = 3
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Whitelist of face-anchor character refs — the empirically-strongest set.
# Curated from QA: each one of these landed in outputs that the user verified
# matched her face. Refs that appeared in "not her" / "close-but-off" outputs
# (white-pantsuit-power-pose, champagne-slip-head-tilted-dreamy,
# smoky-eyes-extreme-closeup, cream-slip-three-quarter-soft) are intentionally
# excluded — they're still her, but their pose / camera / framing confuses
# the I2I model and drags consistency down.
FACE_ANCHOR_REFS = {
    "cable-knit-mug-laughing-warm",
    "laughing-white-tee-daylight",
    "lavender-sweater-whisper-pink",
    "cream-sweater-knees-up-contemplative",
    "crouched-tank-shorts-looking-up",
}

# Nano Banana Pro I2I — image-to-image variant. Strong multi-reference
# character lock. T2I variants ignore the uploaded references.
DEFAULT_IMAGE_MODEL_ID = "c81e401b-6036-4e1f-9165-60eafcee9dd3"


def _model_id(key: str) -> str:
    """Use HEDRA_IMAGE_MODEL_ID if set; otherwise default to Nano Banana Pro I2I.
    `key` is unused now but kept for signature compat with callers."""
    return os.getenv("HEDRA_IMAGE_MODEL_ID", "").strip() or DEFAULT_IMAGE_MODEL_ID


def _all_character_images() -> list[Path]:
    if not CHARACTER_DIR.is_dir():
        sys.exit(f"character dir not found: {CHARACTER_DIR}")
    # Only include files in the FACE_ANCHOR_REFS whitelist (matched by stem).
    paths = sorted(
        p for p in CHARACTER_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.stem in FACE_ANCHOR_REFS
    )
    if not paths:
        sys.exit(
            f"no whitelisted character images in {CHARACTER_DIR}. "
            f"Expected stems: {sorted(FACE_ANCHOR_REFS)}"
        )
    return paths


def _pick_character_refs(slug: str, reroll: int, n: int = CHARACTER_REF_COUNT) -> list[Path]:
    """Pick `n` random character images, seeded by (slug, reroll) so the same
    slug+reroll always picks the same 3 (stable re-runs), but different slugs
    almost never collide. Falls back to all if fewer than n exist."""
    pool = _all_character_images()
    if len(pool) <= n:
        return pool
    seed = int.from_bytes(hashlib.sha256(f"{slug}|{reroll}".encode()).digest()[:8], "big")
    rng = random.Random(seed)
    return rng.sample(pool, n)


def _product_image(folder: Path, manifest: dict) -> Path:
    rel = (manifest.get("product-pic-path") or "").strip()
    if rel:
        cand = folder / rel
        if cand.exists():
            return cand
    for name in PRODUCT_IMAGE_CANDIDATES:
        cand = folder / name
        if cand.exists():
            return cand
    sys.exit(f"no product image in {folder} (looked for product.png/jpg/jpeg/webp)")


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
            if (child / OUTPUT_NAME).exists():
                continue
            slugs.append(child.name)
        return slugs
    if not args.products:
        sys.exit("provide --products <slug[,slug,...]> or --all-needing")
    return [s.strip() for s in args.products.split(",") if s.strip()]


def generate_one(
    slug: str,
    *,
    key: str,
    char_paths: list[Path] | None = None,
    output_path: Path,
    reroll: int = 0,
    update_manifest: bool = True,
) -> tuple[str, str]:
    """Core: one slug -> one image. Used by CLI and benchmark.
    If char_paths is None, picks 3 random refs from assets/character/ seeded by (slug, reroll)."""
    folder = PRODUCTS_DIR / slug
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        return ("FAIL", f"missing {manifest_path}")
    manifest = _load_manifest(manifest_path)

    if char_paths is None:
        char_paths = _pick_character_refs(slug, reroll)

    product_img = _product_image(folder, manifest)

    print(
        f"[{slug}] uploading {len(char_paths)} character ref(s): "
        f"{', '.join(p.name for p in char_paths)}",
        file=sys.stderr,
    )
    char_ids = [hc.upload_file(key, p, "image") for p in char_paths]

    print(f"[{slug}] uploading product image…", file=sys.stderr)
    product_id = hc.upload_file(key, product_img, "image")

    prompt = build_prompt(slug, manifest, reroll=reroll, n_character_refs=len(char_paths))
    print(f"[{slug}] prompt: {prompt[:200]}…", file=sys.stderr)

    body = {
        "type": "image",
        "ai_model_id": _model_id(key),
        "text_prompt": prompt,
        "reference_image_ids": char_ids + [product_id],
        "aspect_ratio": "9:16",
        "resolution": "1K",
    }
    print(f"[{slug}] starting image generation…", file=sys.stderr)
    gen_id = hc.start_generation(key, body)

    # Banana I2I usually finishes in ~30-60s but occasionally stalls; 20 min cap.
    completed = hc.poll(key, gen_id, interval_s=5, timeout_s=20 * 60)
    url = hc.extract_download_url(completed)
    if not url:
        asset_id = completed.get("asset_id")
        if asset_id:
            url = hc.fetch_asset_url(key, asset_id)
    if not url:
        return ("FAIL", f"completed but no download_url: {completed}")

    print(f"[{slug}] downloading png…", file=sys.stderr)
    hc.download(url, output_path)

    if update_manifest:
        rel = output_path.name if output_path.parent == folder else str(output_path.relative_to(folder)) if output_path.is_relative_to(folder) else None
        if rel is not None:
            manifest[MANIFEST_KEY] = rel
            _save_manifest(manifest_path, manifest)

    return ("OK", f"generation {gen_id} -> {output_path}")


_PRINT_LOCK = threading.Lock()


def _process_one(
    slug: str,
    *,
    key: str,
    out_dir: Path | None,
    overwrite: bool,
    reroll: int,
) -> tuple[str, str, str]:
    """Per-slug worker. Returns (slug, status, detail). Idempotency check
    runs here so the SKIP / FIXED paths do zero API work even when called
    in a thread pool."""
    if out_dir is not None:
        output_path = out_dir / f"{slug}.png"
        update_manifest = False
    else:
        output_path = PRODUCTS_DIR / slug / OUTPUT_NAME
        update_manifest = True

    if output_path.exists() and not overwrite:
        if update_manifest:
            manifest_path = PRODUCTS_DIR / slug / "manifest.json"
            if manifest_path.exists():
                m = _load_manifest(manifest_path)
                if m.get(MANIFEST_KEY) != OUTPUT_NAME:
                    m[MANIFEST_KEY] = OUTPUT_NAME
                    _save_manifest(manifest_path, m)
                    return (slug, "FIXED", "manifest synced")
        return (slug, "SKIP", "image already exists")

    try:
        status, detail = generate_one(
            slug,
            key=key,
            output_path=output_path,
            reroll=reroll,
            update_manifest=update_manifest,
        )
    except Exception as exc:  # noqa: BLE001
        status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
    return (slug, status, detail)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", help="comma-separated slugs")
    ap.add_argument("--all-needing", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument(
        "--output-dir",
        help="If set, write each slug's image to <output-dir>/<slug>.png instead of "
             "the product folder. Useful for benchmarking.",
    )
    ap.add_argument("--reroll", type=int, default=0,
                    help="Bump to get a different prompt combo for the same slug.")
    ap.add_argument("--workers", type=int, default=4,
                    help="Concurrent slug workers. Hedra's per-account concurrency "
                         "cap is around 5-10; 4 is a safe default.")
    args = ap.parse_args()

    key = hc.api_key()
    slugs = _resolve_slugs(args)
    if not slugs:
        print("nothing to do.", file=sys.stderr)
        return 0

    out_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    workers = max(1, min(args.workers, len(slugs)))
    print(f"[hedra] {len(slugs)} slug(s), {workers} worker(s)", file=sys.stderr)

    counts = {"OK": 0, "FIXED": 0, "SKIP": 0, "FAIL": 0}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _process_one,
                slug,
                key=key,
                out_dir=out_dir,
                overwrite=args.overwrite,
                reroll=args.reroll,
            ): slug
            for slug in slugs
        }
        for fut in as_completed(futures):
            slug, status, detail = fut.result()
            counts[status] = counts.get(status, 0) + 1
            with _PRINT_LOCK:
                print(f"{slug}\t{status}\t{detail}", flush=True)

    print(
        f"\n{counts['OK']} generated, {counts['FIXED']} manifest-fixed, "
        f"{counts['SKIP']} skipped, {counts['FAIL']} failed.",
        file=sys.stderr,
    )
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
