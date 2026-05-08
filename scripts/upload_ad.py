"""Upload a product's final-with-music video to YouTube Shorts.

Validates / generates `youtube-metadata` in the product manifest, runs
`uploader/upload.py`, then flips `manifest.uploaded = true` plus the resulting
`uploaded-video-url`.

    python scripts/upload_ad.py --product <slug-or-path>
    python scripts/upload_ad.py --product <...> --overwrite
    python scripts/upload_ad.py --product <...> --regen-meta

Output: <slug>\\t<STATUS>\\t<detail>  where STATUS in {OK, SKIP, FIXED, FAIL}.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"
UPLOADER = ROOT / "uploader" / "upload.py"

FINAL_VIDEO_NAME = "final-with-music.mp4"
YT_METADATA_KEY = "youtube-metadata"
UPLOADED_KEY = "uploaded"
UPLOADED_URL_KEY = "uploaded-video-url"

YT_TITLE_MAX = 100
YT_DEFAULT_CATEGORY = "22"  # People & Blogs
YT_DEFAULT_PRIVACY = "public"

EVERGREEN_HASHTAGS = [
    "#TikTokMadeMeBuyIt", "#UGC", "#amazonfinds", "#FYP",
]

CATEGORY_HASHTAGS = {
    "skincare":  ["#skincare", "#skincareroutine", "#glowup", "#skintok", "#cleanbeauty"],
    "makeup":    ["#makeup", "#makeuptutorial", "#beautytok", "#grwm", "#eyeslipsface"],
    "fragrance": ["#perfumetok", "#fragrance", "#smellgood", "#signaturescent"],
    "haircare":  ["#haircare", "#hairtok", "#hairgoals", "#healthyhair"],
    "jewelry":   ["#jewelry", "#jewelrytok", "#dailyjewelry", "#amazonjewelry"],
    "clothing":  ["#ootd", "#fashiontok", "#amazonfashion", "#stylehaul"],
    "apparel":   ["#ootd", "#fashiontok", "#amazonfashion", "#stylehaul"],
    "home":      ["#homefinds", "#amazonhome", "#tiktokmademebuyit", "#homehaul"],
    "beauty":    ["#beauty", "#beautyhacks", "#beautytok", "#amazonfinds"],
}


def load_manifest(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def save_manifest(path: Path, data: OrderedDict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_product_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_absolute() and p.exists() and p.is_dir():
        return p
    return PRODUCTS_DIR / arg


def category_pool(category: str) -> list[str]:
    c = (category or "").lower()
    for key, pool in CATEGORY_HASHTAGS.items():
        if key in c:
            return pool
    return CATEGORY_HASHTAGS["beauty"]


def _ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()


def short_tagline(brand: str, product: str) -> str:
    """Build a punchy ≤60-char tagline. Prefer brand + the first salient phrase
    from the product name; fall back to product name alone."""
    p = (product or "").strip()
    p = re.split(r"\s+-\s+|,|\(", p)[0].strip()
    p = re.sub(r"\s+\d+(\.\d+)?\s*(oz|ml|g|kg|lb|pack|count|ct)\b.*$", "", p, flags=re.I).strip()

    b_tokens = _ascii_fold(brand).split()
    p_tokens = _ascii_fold(p).split()
    overlap = 0
    for i in range(min(len(b_tokens), len(p_tokens))):
        if b_tokens[i] == p_tokens[i]:
            overlap += 1
        else:
            break
    if brand and overlap >= 2:
        tag = p
    elif brand:
        tag = f"{brand} {p}".strip()
    else:
        tag = p

    if len(tag) > 60:
        tag = tag[:57].rstrip() + "..."
    return tag or "Amazon find"


HASHTAG_TOTAL = 4
HASHTAG_EVERGREEN_COUNT = 1
HASHTAG_CATEGORY_COUNT = HASHTAG_TOTAL - HASHTAG_EVERGREEN_COUNT


def pick_hashtags(category: str, max_chars_for_tags: int) -> list[str]:
    pool = category_pool(category)
    chosen: list[str] = []
    rng = random.Random()
    chosen.extend(rng.sample(EVERGREEN_HASHTAGS, k=min(HASHTAG_EVERGREEN_COUNT, len(EVERGREEN_HASHTAGS))))
    for tag in rng.sample(pool, k=min(HASHTAG_CATEGORY_COUNT, len(pool))):
        if tag.lower() not in (c.lower() for c in chosen):
            chosen.append(tag)

    while chosen and len(" ".join(chosen)) > max_chars_for_tags:
        chosen.pop()
    return chosen


def build_title(tagline: str, hashtags: list[str]) -> str:
    title = f"{tagline} {' '.join(hashtags)}".strip()
    while hashtags and len(title) > YT_TITLE_MAX:
        hashtags = hashtags[:-1]
        title = f"{tagline} {' '.join(hashtags)}".strip()
    if len(title) > YT_TITLE_MAX:
        title = tagline[: YT_TITLE_MAX - 3].rstrip() + "..."
    return title


def build_description(brand: str, product: str, script: str, link: str, hashtags: list[str]) -> str:
    parts = []
    if script:
        parts.append(script.strip())
    elif product:
        parts.append(f"{brand + ' ' if brand else ''}{product}.")
    tail_tags = list(hashtags) + ["#shorts"]
    tail = " ".join(tail_tags)
    if link:
        parts.append(f"\nShop on Amazon: {link} {tail}")
    else:
        parts.append(f"\n{tail}")
    return "\n".join(parts).strip()


def build_yt_tags(brand: str, product: str, category: str, hashtags: list[str]) -> list[str]:
    pool = [h.lstrip("#") for h in hashtags + category_pool(category)[:4]]
    extras = []
    for s in (brand, product):
        for word in re.split(r"\W+", _ascii_fold(s)):
            if len(word) >= 3:
                extras.append(word)
    seen, out = set(), []
    for t in pool + extras:
        k = t.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t)
        if len(out) >= 10:
            break
    return out


def generate_metadata(manifest: OrderedDict) -> dict:
    info = manifest.get("item-auxiliary-information") or {}
    brand = (info.get("brand") or "").strip()
    product = (info.get("product") or "").strip()
    category = (info.get("category") or "").strip()
    link = (info.get("affiliate-link") or "").strip()
    script = (manifest.get("script-raw-text") or "").strip()

    tagline = short_tagline(brand, product)
    hashtags_budget = max(0, YT_TITLE_MAX - len(tagline) - 1)
    hashtags = pick_hashtags(category, hashtags_budget)
    title = build_title(tagline, hashtags)
    description = build_description(brand, product, script, link, hashtags)
    tags = build_yt_tags(brand, product, category, hashtags)

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category": YT_DEFAULT_CATEGORY,
        "privacy": YT_DEFAULT_PRIVACY,
        "hashtags": hashtags,
    }


def ensure_metadata(manifest: OrderedDict, regen: bool) -> tuple[OrderedDict, bool]:
    existing = manifest.get(YT_METADATA_KEY) or {}
    if existing.get("title") and not regen:
        return manifest, False
    meta = generate_metadata(manifest)
    new = OrderedDict()
    inserted = False
    for k, v in manifest.items():
        if k == YT_METADATA_KEY:
            continue
        new[k] = v
        if k == "commission-percentage" and not inserted:
            new[YT_METADATA_KEY] = meta
            inserted = True
    if not inserted:
        new[YT_METADATA_KEY] = meta
    return new, True


def set_uploaded(manifest: OrderedDict, url: str) -> OrderedDict:
    new = OrderedDict()
    for k, v in manifest.items():
        if k in (UPLOADED_KEY, UPLOADED_URL_KEY):
            continue
        new[k] = v
    new[UPLOADED_KEY] = True
    new[UPLOADED_URL_KEY] = url
    return new


def run_uploader(slug: str) -> tuple[bool, str | None, str]:
    cmd = [sys.executable, str(UPLOADER), slug, "-y"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"uploaded\s*->\s*(https://youtu\.be/\S+)", out)
    if r.returncode != 0:
        tail = out.strip().splitlines()[-3:]
        return False, None, " | ".join(tail) or f"upload.py exit {r.returncode}"
    if not m:
        if "[skip]" in out:
            tail = [l for l in out.splitlines() if "[skip]" in l][-1:]
            return False, None, tail[0].strip() if tail else "uploader skipped without URL"
        return False, None, "no upload URL in uploader output"
    return True, m.group(1), ""


def process(product_arg: str, overwrite: bool, regen_meta: bool) -> tuple[str, str, str]:
    pdir = resolve_product_dir(product_arg)
    slug = pdir.name
    if not pdir.exists() or not pdir.is_dir():
        return slug, "FAIL", f"no product dir at {pdir}"

    manifest_path = pdir / "manifest.json"
    if not manifest_path.exists():
        return slug, "FAIL", f"no manifest.json at {manifest_path}"

    if not (pdir / FINAL_VIDEO_NAME).exists():
        return slug, "FAIL", f"missing {FINAL_VIDEO_NAME} - run /overlay-music first"

    manifest = load_manifest(manifest_path)

    if manifest.get(UPLOADED_KEY) and not overwrite:
        url = manifest.get(UPLOADED_URL_KEY) or "(no url)"
        return slug, "SKIP", f"already uploaded: {url}"

    manifest, changed = ensure_metadata(manifest, regen=regen_meta)
    if changed:
        save_manifest(manifest_path, manifest)

    ok, url, err = run_uploader(slug)
    if not ok:
        return slug, "FAIL", err

    manifest = load_manifest(manifest_path)
    manifest = set_uploaded(manifest, url or "")
    save_manifest(manifest_path, manifest)

    return slug, "OK", f"uploaded -> {url}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", required=True,
                        help="Slug under products/, or absolute product folder path.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-upload even if manifest.uploaded is true.")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate youtube-metadata even if already present.")
    args = parser.parse_args()

    if not UPLOADER.exists():
        print(f"FATAL: uploader not found at {UPLOADER}", file=sys.stderr)
        return 2

    slug, status, detail = process(args.product, args.overwrite, args.regen_meta)
    print(f"{slug}\t{status}\t{detail}")
    return 0 if status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
