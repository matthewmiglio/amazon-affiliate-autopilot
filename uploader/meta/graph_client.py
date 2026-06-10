"""Thin Graph API wrapper. Auto-attaches the system-user access token,
retries on transient errors, and logs every request to meta/history.json
for debugging.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests

from meta_auth import access_token, graph_version

HERE = Path(__file__).resolve().parent
HISTORY_FILE = HERE / "history.json"

# Meta error codes worth retrying — transient infra hiccups, not validation failures.
TRANSIENT_CODES = {1, 2, 4, 17, 32, 613}
DEFAULT_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


def _base() -> str:
    return f"https://graph.facebook.com/{graph_version()}"


def _log_history(entry: dict) -> None:
    history: dict = {}
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = {}
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    history.setdefault("calls", []).append({"ts": ts, **entry})
    # Cap at 200 most-recent calls so the file doesn't grow forever.
    history["calls"] = history["calls"][-200:]
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def _attach_token(params: dict | None) -> dict:
    p = dict(params or {})
    p.setdefault("access_token", access_token())
    return p


def _is_transient(resp: requests.Response) -> bool:
    if resp.status_code >= 500:
        return True
    try:
        err = resp.json().get("error", {})
    except Exception:
        return False
    return err.get("code") in TRANSIENT_CODES


def request(method: str, path: str, *,
            params: dict | None = None,
            data: dict | None = None,
            files: dict | None = None,
            headers: dict | None = None,
            timeout: int = DEFAULT_TIMEOUT,
            absolute_url: str | None = None) -> dict:
    """Issue a Graph API request and return parsed JSON. Raises RuntimeError on
    final failure (after retries). `absolute_url` overrides the path-based URL
    builder — used by FB Reels upload step 2, which posts to an upload_url
    Meta hands back from step 1."""
    url = absolute_url if absolute_url else f"{_base()}{path}"
    p = _attach_token(params)

    last_resp: requests.Response | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.request(method, url, params=p, data=data, files=files,
                                headers=headers, timeout=timeout)
        last_resp = resp
        if resp.status_code < 400:
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text}
        if not _is_transient(resp):
            break
        time.sleep(RETRY_BACKOFF ** attempt)

    detail = (last_resp.text or "")[:600] if last_resp else ""
    code = last_resp.status_code if last_resp else "?"
    _log_history({"method": method, "url": url, "status": code, "error": detail})
    raise RuntimeError(f"Graph API {method} {path} -> HTTP {code}: {detail}")


def get(path: str, **kw) -> dict:
    return request("GET", path, **kw)


def post(path: str, **kw) -> dict:
    return request("POST", path, **kw)


def delete(path: str, **kw) -> dict:
    return request("DELETE", path, **kw)
