"""X (Twitter) OAuth 2.0 + PKCE auth + token storage for @theluxedrawer.

Single-account uploader, so we keep one token at tokens/user_token.json
(unlike YouTube which keys by channel). Access tokens last 2 h; refresh
tokens last 6 months and slide on every refresh as long as offline.access
was granted.

CLI:
    python x_auth.py login        # one-time interactive PKCE flow
    python x_auth.py refresh      # manual refresh test
    python x_auth.py whoami       # print authed user via /2/users/me

Programmatic:
    from x_auth import get_access_token
    token = get_access_token()    # auto-refreshes if expired
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
TOKENS_DIR = HERE / "tokens"
TOKEN_FILE = TOKENS_DIR / "user_token.json"
ENV_FILE = HERE / ".env"

AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
USERS_ME_URL = "https://api.x.com/2/users/me"

SCOPES = ["tweet.read", "tweet.write", "users.read", "media.write", "offline.access"]
CALLBACK_PORT = 8086
CALLBACK_PATH = "/"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"

# Refresh access tokens this many seconds before they actually expire, so we
# never hand out a token that dies mid-request.
REFRESH_SAFETY_WINDOW_S = 120


def _env() -> tuple[str, str]:
    load_dotenv(ENV_FILE)
    cid = os.environ.get("X_CLIENT_ID", "").strip()
    cs = os.environ.get("X_CLIENT_SECRET", "").strip()
    if not cid or not cs:
        sys.exit(f"X_CLIENT_ID / X_CLIENT_SECRET missing from {ENV_FILE}")
    return cid, cs


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def _save_token(payload: dict) -> None:
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    expires_at = int(time.time()) + int(payload.get("expires_in", 0))
    out = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token", ""),
        "expires_at": expires_at,
        "scope": payload.get("scope", " ".join(SCOPES)),
        "token_type": payload.get("token_type", "bearer"),
    }
    TOKEN_FILE.write_text(json.dumps(out, indent=2), encoding="utf-8")


def _load_token() -> dict | None:
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Catches the OAuth redirect, stores `?code=...` on the server."""

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        self.server.oauth_code = (params.get("code") or [""])[0]  # type: ignore[attr-defined]
        self.server.oauth_state = (params.get("state") or [""])[0]  # type: ignore[attr-defined]
        self.server.oauth_error = (params.get("error") or [""])[0]  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        body = (
            "<html><body style='font-family:system-ui;padding:2rem'>"
            "<h2>X auth complete</h2>"
            "<p>You can close this tab and return to the terminal.</p>"
            "</body></html>"
        )
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *_args, **_kwargs) -> None:  # silence stdlib logging
        pass


def _run_pkce_flow() -> dict:
    cid, cs = _env()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)

    # Bind early so a stale process holding :8086 fails loudly here, not after
    # the user has clicked Authorize.
    try:
        server = http.server.HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    except OSError as e:
        sys.exit(
            f"Could not bind callback listener on port {CALLBACK_PORT}: {e}\n"
            "Another process is using the port — close it and retry."
        )
    server.oauth_code = ""  # type: ignore[attr-defined]
    server.oauth_state = ""  # type: ignore[attr-defined]
    server.oauth_error = ""  # type: ignore[attr-defined]

    qs = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    authorize_url = f"{AUTHORIZE_URL}?{qs}"
    no_browser = os.environ.get("X_AUTH_NO_BROWSER", "").strip() == "1"
    if no_browser:
        print("Open this URL in the browser session signed in as @theluxedrawer:")
        print(authorize_url, flush=True)
    else:
        print("Opening browser to authorize @theluxedrawer ...", flush=True)
        print(f"If it doesn't open, visit:\n  {authorize_url}", flush=True)
        webbrowser.open(authorize_url, new=1, autoraise=True)

    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    t.join(timeout=300)  # 5 min to click Authorize
    if t.is_alive():
        server.server_close()
        sys.exit("Auth timed out (no callback within 5 minutes).")

    if server.oauth_error:  # type: ignore[attr-defined]
        sys.exit(f"X returned error: {server.oauth_error}")  # type: ignore[attr-defined]
    if server.oauth_state != state:  # type: ignore[attr-defined]
        sys.exit("State mismatch — possible CSRF, aborting.")
    code = server.oauth_code  # type: ignore[attr-defined]
    if not code:
        sys.exit("No authorization code returned in callback.")

    # Confidential client (Web App, Automated App or Bot) — must use Basic auth
    # with Client ID + Client Secret on the token endpoint, even with PKCE.
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
            "client_id": cid,
        },
        auth=(cid, cs),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"Token exchange failed: {resp.status_code} {resp.text}")
    payload = resp.json()
    _save_token(payload)
    return payload


def _refresh(refresh_token: str) -> dict:
    cid, cs = _env()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": cid,
        },
        auth=(cid, cs),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(
            f"Refresh failed: {resp.status_code} {resp.text}\n"
            "Run `python x_auth.py login` to re-authorize."
        )
    payload = resp.json()
    _save_token(payload)
    return payload


def get_access_token() -> str:
    """Return a valid access token, refreshing if needed."""
    tok = _load_token()
    if tok is None:
        sys.exit("No token on disk. Run: python x_auth.py login")
    now = int(time.time())
    if tok["expires_at"] - REFRESH_SAFETY_WINDOW_S <= now:
        if not tok.get("refresh_token"):
            sys.exit("Token expired and no refresh_token on file. Run `login` again.")
        tok = _refresh(tok["refresh_token"])
    return tok["access_token"]


def whoami() -> dict:
    token = get_access_token()
    r = requests.get(USERS_ME_URL, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: x_auth.py [login|refresh|whoami]")
        return 1
    cmd = sys.argv[1].lower()
    if cmd == "login":
        _run_pkce_flow()
        print(f"OK — token saved to {TOKEN_FILE}")
    elif cmd == "refresh":
        tok = _load_token()
        if tok is None or not tok.get("refresh_token"):
            sys.exit("No refresh_token on disk. Run `login` first.")
        _refresh(tok["refresh_token"])
        print("OK — refreshed.")
    elif cmd == "whoami":
        print(json.dumps(whoami(), indent=2))
    else:
        print(f"unknown command: {cmd}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
