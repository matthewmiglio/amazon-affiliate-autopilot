"""Per-pin stats fetcher (Pinterest API v5 pin analytics).

Returns normalized dicts: {views, likes, comments, saves, clicks, raw}.
Analytics window is capped at 90 days by the API, so `views`/`saves` etc are
"last 90 days" rather than lifetime for old pins.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from upload import API_BASE, auth_headers  # noqa: E402

METRIC_TYPES = "IMPRESSION,SAVE,PIN_CLICK,OUTBOUND_CLICK,VIDEO_MRC_VIEW"
WINDOW_DAYS = 90


def fetch_pin(pin_id: str) -> dict:
    end = dt.date.today()
    start = end - dt.timedelta(days=WINDOW_DAYS)
    resp = requests.get(
        f"{API_BASE}/pins/{pin_id}/analytics",
        headers=auth_headers(),
        params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "metric_types": METRIC_TYPES,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"pin analytics failed: HTTP {resp.status_code} {resp.text[:300]}")
    payload = resp.json()

    # Response shape: {"all": {"summary_metrics": {"IMPRESSION": n, "SAVE": n, ...}, "daily_metrics": [...]}}
    summary = ((payload.get("all") or {}).get("summary_metrics")) or {}

    def as_int(v):
        return int(v) if v is not None else None  # API returns floats

    video_views = as_int(summary.get("VIDEO_MRC_VIEW"))
    impressions = as_int(summary.get("IMPRESSION"))
    return {
        "views": video_views if video_views is not None else impressions,
        "likes": None,
        "comments": None,
        "saves": as_int(summary.get("SAVE")),
        "clicks": as_int(summary.get("OUTBOUND_CLICK")),
        "raw": payload,
    }
