"""Upload a product's final-with-music video to all configured platforms.

Iterates through [youtube, instagram, facebook, pinterest, x]. For each platform:
  - skips if `manifest["uploads"][platform]["uploaded"]` is true (unless --overwrite)
  - **fails** if the metadata block for the platform is incomplete with the message
    `"no metadata, run /generate-upload-metadata first"`. There is no templated
    fallback — metadata is now authored by the /generate-upload-metadata skill.
  - invokes the per-platform uploader script if it exists
  - skips with "[platform] not implemented, skipping" if the uploader script
    is absent

    python scripts/upload_ad.py --product <slug-or-path>
    python scripts/upload_ad.py --product <...> --overwrite

Output: <slug>\\t<platform>\\t<STATUS>\\t<detail>  STATUS in {OK, SKIP, FAIL}.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"

UPLOADERS: dict[str, Path] = {
    "youtube":   ROOT / "uploader" / "youtube"   / "upload.py",
    "instagram": ROOT / "uploader" / "meta"      / "upload_instagram.py",
    "facebook":  ROOT / "uploader" / "meta"      / "upload_facebook.py",
    "pinterest": ROOT / "uploader" / "pinterest" / "upload.py",
    "x":         ROOT / "uploader" / "x"         / "upload.py",
}

PLATFORMS = ("youtube", "instagram", "facebook", "pinterest", "x")

FINAL_VIDEO_NAME = "final-with-music.mp4"

def load_manifest(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def save_manifest(path: Path, data: OrderedDict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_product_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_absolute() and p.exists() and p.is_dir():
        return p
    return PRODUCTS_DIR / arg


# ---------------------------------------------------------------------------
# Metadata completeness validation
# ---------------------------------------------------------------------------
#
# Copy authoring moved to /generate-upload-metadata. This script no longer
# generates copy on the fly. It only checks that each platform's metadata
# block is populated before invoking that platform's uploader. If a block is
# incomplete, the upload row FAILs with `no metadata, run /generate-upload-metadata first`.

REQUIRED_METADATA_KEYS = {
    "youtube":   ("title",),
    "instagram": ("caption",),
    "facebook":  ("caption",),
    "pinterest": ("title", "description"),
    "x":         ("text",),
}


def is_metadata_complete(platform: str, metadata: dict) -> bool:
    """True if every required key for the platform is present and non-empty."""
    if not metadata:
        return False
    for key in REQUIRED_METADATA_KEYS.get(platform, ()):
        value = metadata.get(key)
        if isinstance(value, str):
            if not value.strip():
                return False
        elif not value:
            return False
    return True


def get_platform_block(manifest: OrderedDict, platform: str) -> dict:
    return ((manifest.get("uploads") or {}).get(platform) or {})


def validate_platform_metadata(manifest: OrderedDict, platform: str) -> tuple[bool, str]:
    """Returns (ok, reason). Reason is empty when ok=True."""
    block = get_platform_block(manifest, platform)
    metadata = block.get("metadata") or {}
    if not is_metadata_complete(platform, metadata):
        return False, "no metadata, run /generate-upload-metadata first"
    return True, ""


def set_uploaded(manifest: OrderedDict, platform: str, url: str) -> OrderedDict:
    uploads = manifest.setdefault("uploads", OrderedDict())
    pblock = uploads.setdefault(platform, OrderedDict([("uploaded", False), ("url", ""), ("metadata", OrderedDict())]))
    pblock["uploaded"] = True
    pblock["url"] = url or ""
    return manifest


# ---------------------------------------------------------------------------
# Per-platform upload runners
# ---------------------------------------------------------------------------

_URL_PATTERNS = {
    "youtube":   r"uploaded\s*->\s*(https://youtu\.be/\S+)",
    "instagram": r"uploaded\s*->\s*(https://\S+)",
    "facebook":  r"uploaded\s*->\s*(https://\S+)",
    "pinterest": r"uploaded\s*->\s*(https://\S+)",
    "x":         r"uploaded\s*->\s*(https://x\.com/\S+)",
}


def run_uploader(slug: str, platform: str) -> tuple[str, str | None, str]:
    """Returns (status, url, detail). status in {OK, SKIP, FAIL}."""
    uploader = UPLOADERS[platform]
    if not uploader.exists():
        return "SKIP", None, f"{platform} not implemented (no {uploader.relative_to(ROOT)})"

    cmd = [sys.executable, str(uploader), slug, "-y"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(_URL_PATTERNS[platform], out)
    if r.returncode != 0:
        tail = out.strip().splitlines()[-3:]
        return "FAIL", None, " | ".join(tail) or f"upload exit {r.returncode}"
    if not m:
        if "[skip]" in out:
            tail = [l for l in out.splitlines() if "[skip]" in l][-1:]
            return "FAIL", None, tail[0].strip() if tail else "uploader skipped without URL"
        return "FAIL", None, "no upload URL in uploader output"
    return "OK", m.group(1), ""


def process_platform(manifest_path: Path, slug: str, platform: str,
                     overwrite: bool) -> tuple[str, str]:
    manifest = load_manifest(manifest_path)
    block = get_platform_block(manifest, platform)
    if block.get("uploaded") and not overwrite:
        url = block.get("url") or "(no url)"
        return "SKIP", f"already uploaded: {url}"

    ok, reason = validate_platform_metadata(manifest, platform)
    if not ok:
        return "FAIL", reason

    status, url, detail = run_uploader(slug, platform)
    if status != "OK":
        return status, detail

    manifest = load_manifest(manifest_path)
    manifest = set_uploaded(manifest, platform, url or "")
    save_manifest(manifest_path, manifest)
    return "OK", f"uploaded -> {url}"


def process(product_arg: str, overwrite: bool) -> int:
    pdir = resolve_product_dir(product_arg)
    slug = pdir.name
    if not pdir.exists() or not pdir.is_dir():
        print(f"{slug}\t-\tFAIL\tno product dir at {pdir}")
        return 1

    manifest_path = pdir / "manifest.json"
    if not manifest_path.exists():
        print(f"{slug}\t-\tFAIL\tno manifest.json at {manifest_path}")
        return 1

    if not (pdir / FINAL_VIDEO_NAME).exists():
        print(f"{slug}\t-\tFAIL\tmissing {FINAL_VIDEO_NAME} - run /overlay-music first")
        return 1

    # Pre-flight: make sure the product is in website/public/products.json so
    # that https://theluxedrawer.com/p/<slug> resolves once Vercel deploys.
    # The YouTube description points viewers at that URL, so we refuse to
    # upload until the build artifact contains the slug.
    if not ensure_product_on_website(slug):
        return 1

    any_failed = False
    any_uploaded = False
    for platform in PLATFORMS:
        status, detail = process_platform(manifest_path, slug, platform, overwrite)
        print(f"{slug}\t{platform}\t{status}\t{detail}")
        if status == "FAIL":
            any_failed = True
        if status == "OK":
            any_uploaded = True

    if any_uploaded:
        print(f"{slug}\t-\tOK\tcommit + push website/ now so /p/{slug} goes live before viewers click")

    return 1 if any_failed else 0


def ensure_product_on_website(slug: str) -> bool:
    """Regenerate website/public/products.json and verify the slug is included.

    Returns True if the slug now appears in products.json (safe to upload).
    Prints a FAIL row and returns False otherwise.
    """
    website_dir = ROOT / "website"
    if not website_dir.exists():
        print(f"{slug}\t-\tSKIP\tno website/ dir; pre-flight sync skipped")
        return True
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        result = subprocess.run(
            [npm, "run", "prebuild"],
            cwd=website_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print(f"{slug}\t-\tFAIL\tnpm not found; cannot verify product is on website")
        return False
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-3:]
        print(f"{slug}\t-\tFAIL\tnpm run prebuild exited {result.returncode}: {' | '.join(tail)}")
        return False
    products_json = website_dir / "public" / "products.json"
    if not products_json.exists():
        print(f"{slug}\t-\tFAIL\twebsite/public/products.json missing after prebuild")
        return False
    try:
        data = json.loads(products_json.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"{slug}\t-\tFAIL\tcould not parse products.json: {e}")
        return False
    items = data.get("products") if isinstance(data, dict) else data
    slugs_on_site = {p.get("slug") for p in (items or []) if isinstance(p, dict)}
    if slug not in slugs_on_site:
        print(f"{slug}\t-\tFAIL\tslug not in website/public/products.json after prebuild; aborting upload to keep /p/{slug} from 404ing")
        return False
    print(f"{slug}\t-\tOK\tproduct present on website; commit + push so /p/{slug} ships before viewers click")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", required=True,
                        help="Slug under products/, or absolute product folder path.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-upload platforms even if uploads.<platform>.uploaded is true.")
    parser.add_argument("--regen-meta", action="store_true",
                        help="DEPRECATED: copy is now authored by /generate-upload-metadata. Flag is ignored.")
    args = parser.parse_args()

    if args.regen_meta:
        print("warning: --regen-meta is deprecated. Run /generate-upload-metadata to re-author copy.", file=sys.stderr)

    return process(args.product, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
