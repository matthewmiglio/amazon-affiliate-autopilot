"""Per-post stats fetchers for Instagram + Facebook (Meta Graph API).

Returns normalized dicts: {views, likes, comments, saves, clicks, raw}.
Metrics our token can't access (IG insights need instagram_manage_insights,
FB video_insights need read_insights) degrade to None instead of failing —
basic like/comment counts always come through.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import meta_auth
import graph_client


def _safe_insights(path: str, params: dict) -> dict | None:
    """Insights endpoints fail with a permissions error on our token tier.
    Return None instead of raising so basic counts still flow."""
    try:
        return graph_client.get(path, params=params)
    except RuntimeError:
        return None


def fetch_instagram(media_id: str) -> dict:
    basic = graph_client.get(f"/{media_id}", params={
        "fields": "like_count,comments_count,permalink,timestamp",
    })
    insights = _safe_insights(f"/{media_id}/insights", {
        "metric": "views,reach,saved,shares",
        "access_token": meta_auth.access_token(),
    })

    views = saves = None
    if insights:
        for item in insights.get("data", []):
            vals = item.get("values") or [{}]
            v = vals[0].get("value")
            if item.get("name") == "views":
                views = v
            elif item.get("name") == "saved":
                saves = v

    return {
        "views": views,
        "likes": basic.get("like_count"),
        "comments": basic.get("comments_count"),
        "saves": saves,
        "clicks": None,
        "raw": {"basic": basic, "insights": insights},
    }


def fetch_facebook(video_id: str) -> dict:
    page_token = meta_auth.page_access_token()
    basic = graph_client.get(f"/{video_id}", params={
        "fields": "likes.summary(true),comments.summary(true),permalink_url",
        "access_token": page_token,
    })
    insights = _safe_insights(f"/{video_id}/video_insights", {
        "metric": "blue_reels_play_count,fb_reels_total_plays,post_impressions_unique,post_video_view_time",
        "access_token": page_token,
    })

    views = None
    if insights:
        for item in insights.get("data", []):
            if item.get("name") in ("fb_reels_total_plays", "blue_reels_play_count"):
                vals = item.get("values") or [{}]
                views = vals[0].get("value")
                if item.get("name") == "fb_reels_total_plays":
                    break  # prefer total plays when both present

    likes = ((basic.get("likes") or {}).get("summary") or {}).get("total_count")
    comments = ((basic.get("comments") or {}).get("summary") or {}).get("total_count")

    return {
        "views": views,
        "likes": likes,
        "comments": comments,
        "saves": None,
        "clicks": None,
        "raw": {"basic": basic, "insights": insights},
    }
