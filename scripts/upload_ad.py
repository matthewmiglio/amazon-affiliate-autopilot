"""Upload a product's final-with-music video to all configured platforms.

Iterates through [youtube, instagram, facebook, pinterest]. For each platform:
  - skips if `manifest["uploads"][platform]["uploaded"]` is true (unless --overwrite)
  - generates platform metadata if missing
  - invokes the per-platform uploader script if it exists
  - skips with "[platform] not implemented, skipping" if the uploader script
    is absent (placeholder for meta/ and pinterest/ until those land)

    python scripts/upload_ad.py --product <slug-or-path>
    python scripts/upload_ad.py --product <...> --overwrite
    python scripts/upload_ad.py --product <...> --regen-meta

Output: <slug>\\t<platform>\\t<STATUS>\\t<detail>  STATUS in {OK, SKIP, FIXED, FAIL}.
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

UPLOADERS: dict[str, Path] = {
    "youtube":   ROOT / "uploader" / "youtube"   / "upload.py",
    "instagram": ROOT / "uploader" / "meta"      / "upload_instagram.py",
    "facebook":  ROOT / "uploader" / "meta"      / "upload_facebook.py",
    "pinterest": ROOT / "uploader" / "pinterest" / "upload.py",
    "x":         ROOT / "uploader" / "x"         / "upload.py",
}

PLATFORMS = ("youtube", "instagram", "facebook", "pinterest", "x")

FINAL_VIDEO_NAME = "final-with-music.mp4"

WEBSITE_URL = "https://theluxedrawer.com"

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


def build_description(brand: str, product: str, script: str, slug: str, hashtags: list[str]) -> str:
    parts = []
    site_link = f"{WEBSITE_URL}/p/{slug}" if slug else WEBSITE_URL
    parts.append(f"Shop on theluxedrawer.com: {site_link}")
    if script:
        parts.append(script.strip())
    elif product:
        parts.append(f"{brand + ' ' if brand else ''}{product}.")
    tail_tags = list(hashtags) + ["#shorts"]
    parts.append(" ".join(tail_tags))
    # YouTube Shorts collapses newlines without inserting spaces — without a
    # trailing space on each segment, the URL slug smashes into the next
    # sentence ("...-dYour girlfriend") and the script's final period welds
    # to the first hashtag ("grab it.#TikTokMadeMeBuyIt"). Trailing spaces
    # are invisible in normal rendering and survive the collapse.
    return " \n\n".join(p for p in parts if p).strip()


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


# ---------------------------------------------------------------------------
# Per-platform metadata generators
# ---------------------------------------------------------------------------

def _info(manifest: OrderedDict, slug: str = "") -> dict:
    info = manifest.get("item-auxiliary-information") or {}
    return {
        "brand":    (info.get("brand") or "").strip(),
        "product":  (info.get("product") or "").strip(),
        "category": (info.get("category") or "").strip(),
        "link":     (info.get("affiliate-link") or "").strip(),
        "script":   (manifest.get("script-raw-text") or "").strip(),
        "slug":     slug,
    }


def _gen_youtube(manifest: OrderedDict, slug: str = "") -> OrderedDict:
    i = _info(manifest, slug)
    tagline = short_tagline(i["brand"], i["product"])
    hashtags_budget = max(0, YT_TITLE_MAX - len(tagline) - 1)
    hashtags = pick_hashtags(i["category"], hashtags_budget)
    return OrderedDict([
        ("title",       build_title(tagline, hashtags)),
        ("description", build_description(i["brand"], i["product"], i["script"], i["slug"], hashtags)),
        ("tags",        build_yt_tags(i["brand"], i["product"], i["category"], hashtags)),
        ("category",    YT_DEFAULT_CATEGORY),
        ("privacy",     YT_DEFAULT_PRIVACY),
        ("hashtags",    hashtags),
    ])


def _gen_instagram(manifest: OrderedDict, slug: str = "") -> OrderedDict:
    return OrderedDict([("caption", ""), ("hashtags", [])])


def _gen_facebook(manifest: OrderedDict, slug: str = "") -> OrderedDict:
    return OrderedDict([("caption", ""), ("hashtags", [])])


def _gen_pinterest(manifest: OrderedDict, slug: str = "") -> OrderedDict:
    """Templated fallback for Pinterest metadata.

    Prefer agent-authored metadata (see .claude/skills/upload-ad/SKILL.md
    "Pinterest metadata" section): the agent writes title/description/alt_text/
    category directly into the manifest before this fallback ever fires. This
    function only runs when /upload-ad was skipped (e.g. cron sees a slug with
    no metadata at all). board_id is intentionally omitted — the uploader
    resolves it from `category` at post time via resolve_board().
    """
    i = _info(manifest, slug)
    site_link = f"{WEBSITE_URL}/p/{slug}" if slug else WEBSITE_URL
    title_raw = short_tagline(i["brand"], i["product"]) or "Amazon find"
    title = title_raw[:97] + "..." if len(title_raw) > 100 else title_raw
    hashtags = pick_hashtags(i["category"], max_chars_for_tags=120)
    desc_parts = []
    if i["product"]:
        lead = f"{i['brand'] + ' ' if i['brand'] else ''}{i['product']}"
        desc_parts.append(lead)
    if i["script"]:
        desc_parts.append(i["script"].strip())
    desc_parts.append(f"Shop: {site_link}")
    if hashtags:
        desc_parts.append(" ".join(hashtags))
    description = "\n\n".join(p for p in desc_parts if p)[:500]
    alt_text = (f"{i['brand']} {i['product']}".strip() or "Amazon find")[:500]
    return OrderedDict([
        ("title", title),
        ("description", description),
        ("alt_text", alt_text),
        ("category", i["category"] or "beauty"),
        ("link", site_link),
    ])


def _gen_x(manifest: OrderedDict, slug: str = "") -> OrderedDict:
    i = _info(manifest, slug)
    # X tweets carry the affiliate link inline in the body (no separate URL
    # field like Pinterest). Pre-fill destination_url from the affiliate link
    # so the eventual uploader can build the tweet text without re-reading
    # item-auxiliary-information.
    return OrderedDict([
        ("text", ""),
        ("destination_url", i["link"]),
    ])


_GENERATORS = {
    "youtube":   _gen_youtube,
    "instagram": _gen_instagram,
    "facebook":  _gen_facebook,
    "pinterest": _gen_pinterest,
    "x":         _gen_x,
}


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def get_platform_block(manifest: OrderedDict, platform: str) -> dict:
    return ((manifest.get("uploads") or {}).get(platform) or {})


def ensure_platform_metadata(manifest: OrderedDict, slug: str, platform: str, regen: bool) -> tuple[OrderedDict, bool]:
    block = get_platform_block(manifest, platform)
    metadata = block.get("metadata") or {}
    has_content = bool(metadata.get("title") or metadata.get("caption") or metadata.get("text"))
    if has_content and not regen:
        return manifest, False
    new_meta = _GENERATORS[platform](manifest, slug)
    uploads = manifest.setdefault("uploads", OrderedDict())
    pblock = uploads.setdefault(platform, OrderedDict([("uploaded", False), ("url", ""), ("metadata", OrderedDict())]))
    pblock["metadata"] = new_meta
    return manifest, True


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
                     overwrite: bool, regen_meta: bool) -> tuple[str, str]:
    manifest = load_manifest(manifest_path)
    block = get_platform_block(manifest, platform)
    if block.get("uploaded") and not overwrite:
        url = block.get("url") or "(no url)"
        return "SKIP", f"already uploaded: {url}"

    manifest, changed = ensure_platform_metadata(manifest, slug, platform, regen=regen_meta)
    if changed:
        save_manifest(manifest_path, manifest)

    status, url, detail = run_uploader(slug, platform)
    if status != "OK":
        return status, detail

    manifest = load_manifest(manifest_path)
    manifest = set_uploaded(manifest, platform, url or "")
    save_manifest(manifest_path, manifest)
    return "OK", f"uploaded -> {url}"


def process(product_arg: str, overwrite: bool, regen_meta: bool) -> int:
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
        status, detail = process_platform(manifest_path, slug, platform, overwrite, regen_meta)
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
                        help="Regenerate platform metadata even if already present.")
    args = parser.parse_args()

    return process(args.product, args.overwrite, args.regen_meta)


if __name__ == "__main__":
    raise SystemExit(main())
