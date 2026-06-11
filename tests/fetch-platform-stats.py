"""Live integration test for the per-platform stats fetchers.

Hits REAL platform APIs (read-only, no quota spend beyond rate limits) using
post IDs from the uploader history files. Platforms that are disabled in
data/platforms.json or have no posted items SKIP rather than FAIL.

Run:  python tests/fetch-platform-stats.py
Exit: 0 if no FAILs, 1 otherwise.
"""
from __future__ import annotations

import json
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from upload_ad import enabled_platforms, PLATFORMS  # noqa: E402

RESULTS: list[tuple[str, str, str]] = []  # (test, PASS|FAIL|SKIP, detail)


def record(test: str, status: str, detail: str = "") -> None:
    RESULTS.append((test, status, detail))
    print(f"  [{status}] {test}{': ' + detail if detail else ''}")


def _history(platform: str) -> dict:
    paths = {
        "instagram": ROOT / "uploader" / "meta" / "history_instagram.json",
        "facebook":  ROOT / "uploader" / "meta" / "history_facebook.json",
        "pinterest": ROOT / "uploader" / "pinterest" / "history.json",
    }
    p = paths.get(platform)
    if p and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _assert_count(name: str, v) -> None:
    assert v is None or (isinstance(v, int) and v >= 0), f"{name} should be int>=0 or None, got {v!r}"


def test_enabled_platforms_respected() -> None:
    """Every enabled platform with posts must have a fetcher; disabled ones must not run."""
    name = "enabled_platforms_respected"
    try:
        import fetch_stats
        active = enabled_platforms()
        for p in active:
            if p in ("instagram", "facebook", "pinterest"):
                assert fetch_stats._fetcher(p) is not None, f"no fetcher for enabled platform {p}"
        disabled = [p for p in PLATFORMS if p not in active]
        record(name, "PASS", f"enabled={active} disabled={tuple(disabled)}")
    except Exception as e:
        record(name, "FAIL", str(e))


def test_instagram_live() -> None:
    name = "instagram_live"
    if "instagram" not in enabled_platforms():
        record(name, "SKIP", "platform disabled")
        return
    h = _history("instagram")
    if not h:
        record(name, "SKIP", "no IG posts in history")
        return
    slug, rec = next(iter(h.items()))
    try:
        sys.path.insert(0, str(ROOT / "uploader" / "meta"))
        import meta_stats
        data = meta_stats.fetch_instagram(rec["media_id"])
        _assert_count("likes", data["likes"])
        _assert_count("comments", data["comments"])
        assert data["raw"], "raw payload empty"
        record(name, "PASS", f"{slug}: likes={data['likes']} comments={data['comments']} views={data['views']}")
    except Exception as e:
        record(name, "FAIL", f"{type(e).__name__}: {e}")


def test_facebook_live() -> None:
    name = "facebook_live"
    if "facebook" not in enabled_platforms():
        record(name, "SKIP", "platform disabled")
        return
    h = _history("facebook")
    if not h:
        record(name, "SKIP", "no FB posts in history")
        return
    slug, rec = next(iter(h.items()))
    try:
        sys.path.insert(0, str(ROOT / "uploader" / "meta"))
        import meta_stats
        data = meta_stats.fetch_facebook(rec["video_id"])
        _assert_count("likes", data["likes"])
        _assert_count("comments", data["comments"])
        assert data["raw"], "raw payload empty"
        record(name, "PASS", f"{slug}: likes={data['likes']} comments={data['comments']} views={data['views']}")
    except Exception as e:
        record(name, "FAIL", f"{type(e).__name__}: {e}")


def test_pinterest_live() -> None:
    name = "pinterest_live"
    if "pinterest" not in enabled_platforms():
        record(name, "SKIP", "platform disabled")
        return
    h = _history("pinterest")
    if not h:
        record(name, "SKIP", "no pins in history")
        return
    # Most recent pin: oldest history entries can point at deleted/sandbox pins (404).
    slug, rec = max(h.items(), key=lambda kv: kv[1].get("uploaded_at", ""))
    try:
        sys.path.insert(0, str(ROOT / "uploader" / "pinterest"))
        import pinterest_stats as pin_stats
        data = pin_stats.fetch_pin(rec["pin_id"])
        _assert_count("views", data["views"])
        _assert_count("saves", data["saves"])
        _assert_count("clicks", data["clicks"])
        assert data["raw"], "raw payload empty"
        record(name, "PASS", f"{slug}: views={data['views']} saves={data['saves']} clicks={data['clicks']}")
    except Exception as e:
        record(name, "FAIL", f"{type(e).__name__}: {e}")


def test_orchestrator_dry_run() -> None:
    name = "orchestrator_dry_run"
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "fetch_stats.py"), "--dry-run"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        assert r.returncode == 0, f"exit {r.returncode}: {(r.stderr or '')[-200:]}"
        n = sum(1 for line in (r.stdout or "").splitlines() if "[dry-run]" in line)
        assert n >= 1, "dry-run listed zero pairs"
        record(name, "PASS", f"{n} pairs listed")
    except Exception as e:
        record(name, "FAIL", f"{type(e).__name__}: {e}")


def main() -> int:
    print("fetch-platform-stats live test\n" + "=" * 40)
    test_enabled_platforms_respected()
    test_instagram_live()
    test_facebook_live()
    test_pinterest_live()
    test_orchestrator_dry_run()

    print("\n" + "=" * 40)
    passes = sum(1 for _, s, _ in RESULTS if s == "PASS")
    fails = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    skips = sum(1 for _, s, _ in RESULTS if s == "SKIP")
    print(f"PASS={passes} FAIL={fails} SKIP={skips}")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
