"""Build / extend the multi-platform posting schedule (cron/post_schedule.json).

Scans products/ for (slug, platform) pairs that have a final-with-music.mp4 but
aren't uploaded to that platform yet, and assigns each a future timestamp at
the platform's cadence. The hourly worker (post_due.py) posts whatever is
past-due and unattempted.

Pairs are EXCLUDED (and reported) when:
  - the platform's metadata block is incomplete  -> NEEDS-METADATA
  - the slug isn't in website/public/products.json -> NEEDS-WEBSITE
Both self-heal: fix the gap, re-run this builder, and the pair is appended.

Re-running never duplicates pairs and never touches existing entries (attempt
history is preserved). --rebuild wipes the schedule and starts fresh.

Usage:
  python cron/build_schedule.py
  python cron/build_schedule.py --dry-run
  python cron/build_schedule.py --rebuild
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PRODUCTS_DIR = ROOT / "products"
SCHEDULE_FILE = HERE / "post_schedule.json"
WEBSITE_PRODUCTS_JSON = ROOT / "website" / "public" / "products.json"

sys.path.insert(0, str(ROOT / "scripts"))
from upload_ad import is_metadata_complete, platform_enabled, PLATFORMS  # noqa: E402

FINAL_VIDEO_NAME = "final-with-music.mp4"

# Posting cadence per platform (hours between posts).
CADENCE_HOURS = {
    "youtube": 8,
    "instagram": 12,
    "facebook": 8,
    "pinterest": 5,
    "x": 6,
}

# Stagger anchors (minutes from build time) so platforms don't cluster in the
# same hour of the day.
ANCHOR_OFFSET_MINUTES = {
    "youtube": 60,
    "instagram": 120,
    "facebook": 180,
    "pinterest": 30,
    "x": 90,
}


def load_schedule() -> dict:
    if SCHEDULE_FILE.exists():
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    return {"built_at": None, "cadence_hours": CADENCE_HOURS, "entries": []}


def save_schedule(s: dict) -> None:
    SCHEDULE_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def website_slugs() -> set[str]:
    if not WEBSITE_PRODUCTS_JSON.exists():
        return set()
    data = json.loads(WEBSITE_PRODUCTS_JSON.read_text(encoding="utf-8"))
    items = data.get("products") if isinstance(data, dict) else data
    return {p.get("slug") for p in (items or []) if isinstance(p, dict)}


def pending_pairs() -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    """Returns (ready, needs_metadata, needs_website). Disabled platforms are
    excluded entirely (reported separately by build())."""
    active = [p for p in PLATFORMS if platform_enabled(p)[0]]
    on_site = website_slugs()
    ready: list[tuple[str, str]] = []
    needs_meta: list[tuple[str, str]] = []
    needs_site: list[str] = []
    for d in sorted(PRODUCTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        mf = d / "manifest.json"
        if not mf.exists() or not (d / FINAL_VIDEO_NAME).exists():
            continue
        slug = d.name
        if on_site and slug not in on_site:
            needs_site.append(slug)
            continue
        m = json.loads(mf.read_text(encoding="utf-8"))
        uploads = m.get("uploads") or {}
        for platform in active:
            block = uploads.get(platform) or {}
            if block.get("uploaded"):
                continue
            metadata = block.get("metadata") or {}
            if not is_metadata_complete(platform, metadata):
                needs_meta.append((slug, platform))
                continue
            ready.append((slug, platform))
    return ready, needs_meta, needs_site


def build(dry_run: bool, rebuild: bool) -> int:
    schedule = {"built_at": None, "cadence_hours": CADENCE_HOURS, "entries": []} if rebuild else load_schedule()
    existing_pairs = {(e["slug"], e["platform"]) for e in schedule["entries"]}

    ready, needs_meta, needs_site = pending_pairs()
    new_pairs = [(s, p) for (s, p) in ready if (s, p) not in existing_pairs]

    # Per-platform: find the latest already-scheduled timestamp so appended
    # entries continue the timeline instead of restarting it.
    now = datetime.now().replace(second=0, microsecond=0)
    last_scheduled: dict[str, datetime] = {}
    for e in schedule["entries"]:
        t = datetime.fromisoformat(e["scheduled_at"])
        if e["platform"] not in last_scheduled or t > last_scheduled[e["platform"]]:
            last_scheduled[e["platform"]] = t

    # Fixed per-platform minute (e.g. :23) for a human-readable timeline.
    # Stable across runs: derive from existing entries when present.
    platform_minute: dict[str, int] = {}
    for e in schedule["entries"]:
        platform_minute.setdefault(e["platform"], datetime.fromisoformat(e["scheduled_at"]).minute)
    rng = random.Random()
    for p in PLATFORMS:
        platform_minute.setdefault(p, rng.randint(0, 59))

    added = []
    for platform in PLATFORMS:
        slugs = [s for (s, p) in new_pairs if p == platform]
        if not slugs:
            continue
        step = timedelta(hours=CADENCE_HOURS[platform])
        if platform in last_scheduled and last_scheduled[platform] >= now:
            cursor = last_scheduled[platform] + step
        else:
            cursor = (now + timedelta(minutes=ANCHOR_OFFSET_MINUTES[platform])).replace(
                minute=platform_minute[platform])
            if cursor <= now:
                cursor += timedelta(hours=1)
        for slug in slugs:
            added.append(OrderedDict([
                ("slug", slug),
                ("platform", platform),
                ("scheduled_at", cursor.isoformat(timespec="minutes")),
                ("attempted", False),
                ("attempted_at", None),
                ("result", None),
                ("url", None),
                ("detail", None),
            ]))
            cursor += step

    # ---- report ----
    for p in PLATFORMS:
        on, reason = platform_enabled(p)
        if not on:
            print(f"DISABLED: {p} ({reason or 'no reason given'}) — not scheduled")
    print(f"ready pairs already scheduled: {len(existing_pairs & set(ready))}")
    print(f"new pairs scheduled this run:  {len(added)}")
    for e in added:
        print(f"  {e['scheduled_at']}  {e['platform']:<10} {e['slug']}")
    if needs_meta:
        print(f"\nNEEDS-METADATA ({len(needs_meta)} pairs) — run /generate-upload-metadata, then re-run this builder:")
        by_slug: dict[str, list[str]] = {}
        for s, p in needs_meta:
            by_slug.setdefault(s, []).append(p)
        for s in sorted(by_slug):
            print(f"  {s}  [{', '.join(by_slug[s])}]")
    if needs_site:
        print(f"\nNEEDS-WEBSITE ({len(needs_site)} slugs) — not in website/public/products.json; run npm prebuild + deploy:")
        for s in needs_site:
            print(f"  {s}")

    if dry_run:
        print("\n[dry-run] schedule NOT written")
        return 0

    schedule["entries"].extend(added)
    schedule["entries"].sort(key=lambda e: e["scheduled_at"])
    schedule["built_at"] = now.isoformat(timespec="minutes")
    schedule["cadence_hours"] = CADENCE_HOURS
    save_schedule(schedule)
    unattempted = sum(1 for e in schedule["entries"] if not e["attempted"])
    print(f"\nwrote {SCHEDULE_FILE.name}: {len(schedule['entries'])} total entries, {unattempted} unattempted")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild", action="store_true", help="wipe the schedule (loses attempt history)")
    args = ap.parse_args()
    return build(dry_run=args.dry_run, rebuild=args.rebuild)


if __name__ == "__main__":
    raise SystemExit(main())
