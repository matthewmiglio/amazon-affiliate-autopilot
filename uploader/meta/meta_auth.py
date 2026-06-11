"""Token + identity loader for the Meta uploader.

System-user token never expires, so there's no OAuth refresh dance. This module
just reads tokens/system_user_token.json plus a handful of IDs from .env and
exposes them to the rest of the package.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE / "tokens" / "system_user_token.json"


def _load_token_file() -> dict:
    if not TOKEN_FILE.exists():
        sys.exit(
            f"Token file missing at {TOKEN_FILE}.\n"
            "Generate one in Business Suite -> System users -> uploader-bot -> Generate token."
        )
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def access_token() -> str:
    tok = os.environ.get("META_ACCESS_TOKEN")
    if tok:
        return tok
    return _load_token_file()["access_token"]


def app_id() -> str:
    return os.environ["META_APP_ID"]


def app_secret() -> str:
    return os.environ["META_APP_SECRET"]


def graph_version() -> str:
    return os.environ.get("META_GRAPH_API_VERSION", "v21.0")


def fb_page_id() -> str:
    return os.environ["META_FB_PAGE_ID"]


def ig_user_id() -> str:
    return os.environ["META_IG_USER_ID"]


PAGE_TOKEN_FILE = HERE / "tokens" / "page_token.json"


def page_access_token() -> str:
    """Page access token for the FB Page (needed for posting videos/Reels).

    Derived from the never-expiring system-user token via /me/accounts, so it
    is itself never-expiring. Fetched once and cached to tokens/page_token.json;
    delete that file to force a re-fetch.
    """
    if PAGE_TOKEN_FILE.exists():
        cached = json.loads(PAGE_TOKEN_FILE.read_text(encoding="utf-8"))
        if cached.get("page_id") == fb_page_id() and cached.get("access_token"):
            return cached["access_token"]

    import requests  # local import; only needed on first fetch
    url = f"https://graph.facebook.com/{graph_version()}/me/accounts"
    resp = requests.get(url, params={
        "fields": "id,name,access_token",
        "access_token": access_token(),
    }, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"page token fetch failed: HTTP {resp.status_code} {resp.text[:400]}")
    for page in resp.json().get("data", []):
        if page.get("id") == fb_page_id() and page.get("access_token"):
            PAGE_TOKEN_FILE.write_text(json.dumps({
                "page_id": page["id"],
                "page_name": page.get("name", ""),
                "access_token": page["access_token"],
                "derived_from": "system_user_token via /me/accounts",
            }, indent=2), encoding="utf-8")
            return page["access_token"]
    raise RuntimeError(f"page {fb_page_id()} not found in /me/accounts response")


def whoami() -> dict:
    """Return a quick identity dump for debugging."""
    return {
        "graph_version": graph_version(),
        "app_id": app_id(),
        "fb_page_id": fb_page_id(),
        "ig_user_id": ig_user_id(),
        "access_token_tail": access_token()[-8:],
    }


if __name__ == "__main__":
    print(json.dumps(whoami(), indent=2))
