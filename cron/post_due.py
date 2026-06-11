"""Hourly posting worker. Posts every past-due, unattempted entry in
cron/post_schedule.json (built by build_schedule.py).

Invoked hourly by the Windows Scheduled Task `AmazonAffiliateHourlyPoster`:
  schtasks /Create /TN AmazonAffiliateHourlyPoster /TR "<python> <this file>" /SC HOURLY /F

Rules (per design):
  - Every entry is attempted AT MOST ONCE. Success or failure, it's marked
    attempted in the schedule. The schedule records attempts; the product
    manifest (products/<slug>/manifest.json) records GROUND TRUTH and is only
    updated on confirmed success (uploader printed `uploaded -> <url>`).
  - Missing metadata is a PRECONDITION failure, not a post failure: the entry
    is skipped WITHOUT burning its attempt, and self-heals once metadata is
    authored.
  - Due entries are shuffled so platform order varies run to run.
  - Random jitter at startup and between posts so the timing isn't
    machine-perfect.
  - Safety cap per run (machine-was-off catch-up must not burst).

Usage:
  python cron/post_due.py                 # normal cron invocation
  python cron/post_due.py --no-jitter     # skip sleeps (manual testing)
  python cron/post_due.py --dry-run       # show what would post, post nothing
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PRODUCTS_DIR = ROOT / "products"
SCHEDULE_FILE = HERE / "post_schedule.json"
LOG_FILE = HERE / "post_cron.log"

sys.path.insert(0, str(ROOT / "scripts"))
from upload_ad import (  # noqa: E402
    UPLOADERS, _URL_PATTERNS, is_metadata_complete, platform_enabled,
)

STARTUP_JITTER_MAX_S = 300
BETWEEN_POSTS_JITTER_S = (60, 180)
MAX_PER_PLATFORM_PER_RUN = 2
MAX_TOTAL_PER_RUN = 6
UPLOAD_TIMEOUT_S = 15 * 60


def log(msg: str) -> None:
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_schedule() -> dict | None:
    if not SCHEDULE_FILE.exists():
        return None
    return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))


def save_schedule(s: dict) -> None:
    SCHEDULE_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def load_manifest(slug: str) -> OrderedDict | None:
    p = PRODUCTS_DIR / slug / "manifest.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def save_manifest(slug: str, m: OrderedDict) -> None:
    p = PRODUCTS_DIR / slug / "manifest.json"
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def mark(entry: dict, result: str, url: str | None = None, detail: str | None = None) -> None:
    entry["attempted"] = True
    entry["attempted_at"] = datetime.now().isoformat(timespec="seconds")
    entry["result"] = result
    entry["url"] = url
    entry["detail"] = detail


def run_uploader(slug: str, platform: str) -> tuple[bool, str | None, str]:
    """Returns (success, url, detail)."""
    uploader = UPLOADERS[platform]
    if not uploader.exists():
        return False, None, f"uploader missing: {uploader}"
    cmd = [sys.executable, str(uploader), slug, "-y"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=UPLOAD_TIMEOUT_S, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return False, None, f"upload timed out after {UPLOAD_TIMEOUT_S}s"
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(_URL_PATTERNS[platform], out)
    if r.returncode == 0 and m:
        return True, m.group(1), ""
    tail = " | ".join(out.strip().splitlines()[-3:])
    return False, None, tail or f"exit {r.returncode}, no URL in output"


def process_entry(entry: dict, dry_run: bool) -> str:
    """Returns one of: posted, failed, already-uploaded, skip-no-manifest,
    skip-no-metadata, skip-disabled, dry-run."""
    slug, platform = entry["slug"], entry["platform"]

    on, reason = platform_enabled(platform)
    if not on:
        # Precondition, not a post failure: leave unattempted. If the platform
        # is re-enabled later the entry posts on the next hourly tick.
        return f"skip-disabled ({reason or 'no reason given'})"

    manifest = load_manifest(slug)
    if manifest is None:
        mark(entry, "fail", detail="manifest.json missing")
        return "skip-no-manifest"

    block = (manifest.get("uploads") or {}).get(platform) or {}
    if block.get("uploaded"):
        mark(entry, "already-uploaded", url=block.get("url"))
        return "already-uploaded"

    metadata = block.get("metadata") or {}
    if not is_metadata_complete(platform, metadata):
        # Precondition failure: leave unattempted, self-heals next hour.
        return "skip-no-metadata"

    if dry_run:
        return "dry-run"

    success, url, detail = run_uploader(slug, platform)
    if success:
        # Re-load before writing: the uploader itself may have touched the file.
        m2 = load_manifest(slug) or manifest
        pblock = m2.setdefault("uploads", OrderedDict()).setdefault(
            platform, OrderedDict([("uploaded", False), ("url", ""), ("metadata", OrderedDict())]))
        pblock["uploaded"] = True
        pblock["url"] = url or ""
        save_manifest(slug, m2)
        mark(entry, "success", url=url)
        return "posted"
    mark(entry, "fail", detail=detail[:500])
    return "failed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-jitter", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schedule = load_schedule()
    if schedule is None:
        log("no post_schedule.json — run build_schedule.py first; exiting")
        return 0

    now = datetime.now()
    due = [e for e in schedule["entries"]
           if not e["attempted"]
           and datetime.fromisoformat(e["scheduled_at"]) <= now
           and platform_enabled(e["platform"])[0]]
    if not due:
        remaining = sum(1 for e in schedule["entries"] if not e["attempted"])
        log(f"nothing due (unattempted remaining: {remaining})")
        return 0

    random.shuffle(due)

    # Safety caps: never burst, even after machine downtime.
    picked: list[dict] = []
    per_platform: dict[str, int] = {}
    for e in due:
        if len(picked) >= MAX_TOTAL_PER_RUN:
            break
        if per_platform.get(e["platform"], 0) >= MAX_PER_PLATFORM_PER_RUN:
            continue
        picked.append(e)
        per_platform[e["platform"]] = per_platform.get(e["platform"], 0) + 1

    log(f"due={len(due)} picked={len(picked)} caps={MAX_PER_PLATFORM_PER_RUN}/platform {MAX_TOTAL_PER_RUN}/run"
        + (" [dry-run]" if args.dry_run else ""))

    if not args.no_jitter and not args.dry_run:
        delay = random.randint(0, STARTUP_JITTER_MAX_S)
        log(f"startup jitter: sleeping {delay}s")
        time.sleep(delay)

    for i, entry in enumerate(picked):
        outcome = process_entry(entry, dry_run=args.dry_run)
        log(f"{entry['platform']:<10} {entry['slug']}: {outcome}"
            + (f" -> {entry.get('url')}" if entry.get("url") else "")
            + (f" ({entry.get('detail')})" if entry.get("detail") else ""))
        if not args.dry_run:
            save_schedule(schedule)  # crash-safe: persist after every entry
        if i < len(picked) - 1 and not args.no_jitter and not args.dry_run:
            delay = random.randint(*BETWEEN_POSTS_JITTER_S)
            log(f"between-posts jitter: sleeping {delay}s")
            time.sleep(delay)

    remaining = sum(1 for e in schedule["entries"] if not e["attempted"])
    if remaining == 0:
        log("schedule drained — all entries attempted (task stays registered for future builds)")
    else:
        log(f"run complete; unattempted remaining: {remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
