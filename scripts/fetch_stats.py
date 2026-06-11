"""Unified per-post stats snapshot across all enabled platforms.

For every product with uploads.<platform>.uploaded == true (enabled platforms
only — data/platforms.json), fetch current performance counts and append one
row per (slug, platform) to stats/stats.csv. Full raw API payloads go to
stats/raw/<date>.json so the CSV stays clean without losing anything.

Designed as a daily snapshot (Scheduled Task AmazonAffiliateDailyStats).
Re-running on the same day requires --force (prevents double-snapshots).

Usage:
  python scripts/fetch_stats.py
  python scripts/fetch_stats.py --dry-run
  python scripts/fetch_stats.py --platform instagram --slug concealer-spf-27
  python scripts/fetch_stats.py --force
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "products"
STATS_DIR = ROOT / "stats"
STATS_CSV = STATS_DIR / "stats.csv"
RAW_DIR = STATS_DIR / "raw"

sys.path.insert(0, str(ROOT / "scripts"))
from upload_ad import enabled_platforms  # noqa: E402

CSV_COLUMNS = ["date", "slug", "platform", "views", "likes", "comments", "saves", "clicks", "url"]

# History files store the platform-native post IDs directly (preferred source).
HISTORY_FILES = {
    "instagram": ROOT / "uploader" / "meta" / "history_instagram.json",
    "facebook":  ROOT / "uploader" / "meta" / "history_facebook.json",
    "pinterest": ROOT / "uploader" / "pinterest" / "history.json",
}
HISTORY_ID_KEYS = {
    "instagram": "media_id",
    "facebook":  "video_id",
    "pinterest": "pin_id",
}

# Fallback: parse the platform post ID out of the manifest URL.
URL_ID_PATTERNS = {
    "pinterest": re.compile(r"pinterest\.com/pin/(\d+)"),
    "facebook":  re.compile(r"facebook\.com/reel/(\d+)"),
    # IG permalinks use shortcodes, not numeric media ids — history file only.
}


def _fetcher(platform: str):
    """Lazy import so a broken platform module doesn't kill the others."""
    if platform in ("instagram", "facebook"):
        sys.path.insert(0, str(ROOT / "uploader" / "meta"))
        import meta_stats
        return meta_stats.fetch_instagram if platform == "instagram" else meta_stats.fetch_facebook
    if platform == "pinterest":
        sys.path.insert(0, str(ROOT / "uploader" / "pinterest"))
        import pinterest_stats
        return pinterest_stats.fetch_pin
    return None


def _load_history(platform: str) -> dict:
    f = HISTORY_FILES.get(platform)
    if f and f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}


def resolve_post_id(platform: str, slug: str, url: str) -> str | None:
    h = _load_history(platform).get(slug) or {}
    pid = h.get(HISTORY_ID_KEYS.get(platform, ""))
    if pid:
        return str(pid)
    pat = URL_ID_PATTERNS.get(platform)
    if pat and url:
        m = pat.search(url)
        if m:
            return m.group(1)
    return None


def posted_pairs(platform_filter: str | None, slug_filter: str | None):
    """Yield (slug, platform, url) for everything uploaded on enabled platforms."""
    active = enabled_platforms()
    for d in sorted(PRODUCTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        if slug_filter and d.name != slug_filter:
            continue
        mf = d / "manifest.json"
        if not mf.exists():
            continue
        uploads = (json.loads(mf.read_text(encoding="utf-8")).get("uploads")) or {}
        for platform in active:
            if platform_filter and platform != platform_filter:
                continue
            block = uploads.get(platform) or {}
            if block.get("uploaded"):
                yield d.name, platform, (block.get("url") or "")


def already_ran_today() -> bool:
    if not STATS_CSV.exists():
        return False
    today = dt.date.today().isoformat()
    with STATS_CSV.open(encoding="utf-8") as f:
        return any(row.startswith(today + ",") for row in f)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", choices=["instagram", "facebook", "pinterest", "youtube", "x"])
    ap.add_argument("--slug")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="append even if today already has rows")
    args = ap.parse_args()

    if not args.dry_run and not args.force and already_ran_today():
        print("stats already snapshotted today; use --force to append again")
        return 0

    today = dt.date.today().isoformat()
    rows: list[dict] = []
    raws: dict[str, dict] = {}
    failures = 0

    for slug, platform, url in posted_pairs(args.platform, args.slug):
        fetch = _fetcher(platform)
        if fetch is None:
            print(f"  [skip] {platform}: no stats fetcher implemented", file=sys.stderr)
            continue
        post_id = resolve_post_id(platform, slug, url)
        if not post_id:
            print(f"  [skip] {slug}/{platform}: could not resolve post id", file=sys.stderr)
            continue
        if args.dry_run:
            print(f"{today}  {platform:<10} {slug}  (post_id={post_id})  [dry-run]")
            rows.append({})
            continue
        try:
            data = fetch(post_id)
        except Exception as e:
            failures += 1
            print(f"  [fail] {slug}/{platform}: {e}", file=sys.stderr)
            continue
        row = {
            "date": today, "slug": slug, "platform": platform,
            "views": data.get("views"), "likes": data.get("likes"),
            "comments": data.get("comments"), "saves": data.get("saves"),
            "clicks": data.get("clicks"), "url": url,
        }
        rows.append(row)
        raws[f"{slug}/{platform}"] = data.get("raw")
        print(f"{today}  {platform:<10} {slug}  views={row['views']} likes={row['likes']} "
              f"comments={row['comments']} saves={row['saves']} clicks={row['clicks']}")

    if args.dry_run:
        print(f"\n[dry-run] {len(rows)} pairs would be fetched")
        return 0

    if rows:
        STATS_DIR.mkdir(exist_ok=True)
        RAW_DIR.mkdir(exist_ok=True)
        new_file = not STATS_CSV.exists()
        with STATS_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if new_file:
                w.writeheader()
            w.writerows(rows)
        raw_path = RAW_DIR / f"{today}.json"
        existing_raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
        existing_raw.update(raws)
        raw_path.write_text(json.dumps(existing_raw, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {len(rows)} rows -> {STATS_CSV.relative_to(ROOT)} (+raw/{today}.json), {failures} failures")

    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
