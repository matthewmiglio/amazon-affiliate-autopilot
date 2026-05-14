"""Amazon-affiliate product → Pinterest pin uploader.

One-time setup:
  1. Create app in Pinterest Developer Platform (already done: app id 1568946).
  2. Add `http://localhost:8085/` to the app's Redirect URIs (for local OAuth).
  3. Copy `.env.example` to `.env` and fill in PINTEREST_APP_ID + PINTEREST_APP_SECRET.
  4. `pip install requests python-dotenv`
  5. `python upload.py auth`           (runs OAuth in browser, saves refresh token)
  6. `python upload.py boards`         (lists boards, pick one to use as default)

Every subsequent upload:
  python upload.py <product-slug> -y
  python upload.py <product-slug> --board <board_id> -y
  python upload.py <product-slug> --force -y
  python upload.py --list

Metadata for each product lives in `products/<slug>/manifest.json` under
`uploads.pinterest.metadata` (title, description, board_id, link).
The pin image is read from `products/<slug>/starting-pic.png`.

Pinterest scopes required: pins:write, boards:read, user_accounts:read.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
PRODUCTS = HERE.parent.parent / "products"
TOKEN_FILE = HERE / "token.json"
HISTORY_FILE = HERE / "history.json"

API_BASE = "https://api-sandbox.pinterest.com/v5"
OAUTH_AUTHORIZE = "https://www.pinterest.com/oauth/"
OAUTH_TOKEN = f"{API_BASE}/oauth/token"

SCOPES = "pins:read,pins:write,boards:read,boards:write,user_accounts:read"
REDIRECT_URI = "http://localhost:8085/"
PIN_IMAGE_NAME = "starting-pic.png"


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------

def load_token() -> dict | None:
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def save_token(tok: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(tok, indent=2), encoding="utf-8")


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))


def save_history(h: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(h, indent=2), encoding="utf-8")


def app_credentials() -> tuple[str, str]:
    cid = os.environ.get("PINTEREST_APP_ID")
    sec = os.environ.get("PINTEREST_APP_SECRET")
    if not cid or not sec:
        sys.exit("PINTEREST_APP_ID / PINTEREST_APP_SECRET missing. See .env.example.")
    return cid, sec


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------

def do_auth() -> None:
    print("[auth] loading app credentials from .env...", flush=True)
    cid, sec = app_credentials()
    print(f"[auth] app_id={cid} secret={'*' * 4}{sec[-4:]}", flush=True)

    params = {
        "client_id": cid,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    }
    auth_url = f"{OAUTH_AUTHORIZE}?{urlencode(params)}"

    print("\n" + "=" * 70, flush=True)
    print("PASTE THIS URL INTO A BROWSER WHERE YOU'RE LOGGED INTO PINTEREST:", flush=True)
    print(auth_url, flush=True)
    print("=" * 70 + "\n", flush=True)
    print("(Make sure http://localhost:8085/ is registered as a redirect URI on the app.)\n", flush=True)

    code_holder: list[str] = []
    error_holder: list[str] = []

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            print(f"[auth] callback hit: path={self.path}", flush=True)
            code_holder.extend(qs.get("code", []))
            error_holder.extend(qs.get("error", []))
            error_holder.extend(qs.get("error_description", []))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Auth complete. You can close this tab.</h2>")
        def log_message(self, fmt, *a):
            print(f"[auth][http] {fmt % a}", flush=True)

    print("[auth] binding HTTP server on http://localhost:8085/ (waiting for browser callback)...", flush=True)
    try:
        server = HTTPServer(("localhost", 8085), _Handler)
    except OSError as e:
        sys.exit(f"[auth] could not bind localhost:8085 — {e}. Is something else using the port?")
    print("[auth] server ready. Open the URL above in your browser now.", flush=True)
    server.handle_request()
    print("[auth] callback handled.", flush=True)
    if error_holder:
        sys.exit(f"[auth] Pinterest returned error: {' | '.join(error_holder)}")
    if not code_holder:
        sys.exit("[auth] No auth code received (callback had no ?code=).")
    print(f"[auth] got auth code: {code_holder[0][:8]}...", flush=True)

    print("[auth] exchanging code for token...", flush=True)
    basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    resp = requests.post(
        OAUTH_TOKEN,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code_holder[0],
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    print(f"[auth] token endpoint -> HTTP {resp.status_code}", flush=True)
    if resp.status_code != 200:
        sys.exit(f"Token exchange failed: {resp.status_code} {resp.text}")
    tok = resp.json()
    tok["obtained_at"] = dt.datetime.now().isoformat(timespec="seconds")
    save_token(tok)
    print(f"Auth ok. Token saved to {TOKEN_FILE.name}")
    print(f"  scopes: {tok.get('scope')}")
    print(f"  expires_in: {tok.get('expires_in')}s")


def refresh_access_token() -> str:
    tok = load_token()
    if not tok:
        sys.exit("No token. Run: python upload.py auth")
    rt = tok.get("refresh_token")
    if not rt:
        sys.exit("Token has no refresh_token. Re-run auth.")

    cid, sec = app_credentials()
    basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    resp = requests.post(
        OAUTH_TOKEN,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": rt, "scope": SCOPES},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"Refresh failed: {resp.status_code} {resp.text}")
    new = resp.json()
    tok["access_token"] = new["access_token"]
    tok["expires_in"] = new.get("expires_in")
    tok["obtained_at"] = dt.datetime.now().isoformat(timespec="seconds")
    if new.get("refresh_token"):
        tok["refresh_token"] = new["refresh_token"]
    save_token(tok)
    return tok["access_token"]


def access_token() -> str:
    tok = load_token()
    if not tok:
        sys.exit("No token. Run: python upload.py auth")
    obtained = tok.get("obtained_at")
    expires_in = tok.get("expires_in") or 0
    if obtained:
        age = (dt.datetime.now() - dt.datetime.fromisoformat(obtained)).total_seconds()
        if age < expires_in - 60:
            return tok["access_token"]
    return refresh_access_token()


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {access_token()}"}


# ---------------------------------------------------------------------------
# Pinterest API
# ---------------------------------------------------------------------------

def list_boards(verbose: bool = False) -> list[dict]:
    """Paginate through /boards. Sandbox sometimes serves an empty first page;
    we follow `bookmark` until exhausted. Set verbose=True to dump raw payloads."""
    items: list[dict] = []
    params: dict[str, str] = {"page_size": "250"}
    page = 0
    while True:
        page += 1
        resp = requests.get(f"{API_BASE}/boards", headers=auth_headers(),
                            params=params, timeout=30)
        if verbose:
            print(f"[boards] page={page} url={resp.url} -> HTTP {resp.status_code}", flush=True)
        resp.raise_for_status()
        payload = resp.json()
        if verbose:
            print(f"[boards] payload keys={list(payload.keys())} "
                  f"items={len(payload.get('items') or [])} "
                  f"bookmark={payload.get('bookmark')!r}", flush=True)
            if not payload.get("items"):
                print(f"[boards] raw: {json.dumps(payload)[:400]}", flush=True)
        items.extend(payload.get("items") or [])
        bookmark = payload.get("bookmark")
        if not bookmark:
            break
        params["bookmark"] = bookmark
        if page > 20:
            break
    return items


def get_board(board_id: str) -> dict:
    resp = requests.get(f"{API_BASE}/boards/{board_id}", headers=auth_headers(), timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Get board failed: {resp.status_code} {resp.text}")
    return resp.json()


def delete_board(board_id: str) -> None:
    resp = requests.delete(f"{API_BASE}/boards/{board_id}", headers=auth_headers(), timeout=30)
    if resp.status_code not in (200, 204):
        raise RuntimeError(f"Delete board failed: {resp.status_code} {resp.text}")


def get_user_account() -> dict:
    resp = requests.get(f"{API_BASE}/user_account", headers=auth_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def create_board(name: str, description: str = "", privacy: str = "PUBLIC") -> dict:
    body = {"name": name, "description": description, "privacy": privacy}
    resp = requests.post(
        f"{API_BASE}/boards",
        headers={**auth_headers(), "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Create board failed: {resp.status_code} {resp.text}")
    return resp.json()


def create_pin(board_id: str, title: str, description: str, link: str, image_path: Path) -> dict:
    with image_path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    body = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/png",
            "data": b64,
        },
    }
    resp = requests.post(
        f"{API_BASE}/pins",
        headers={**auth_headers(), "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=120,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Create pin failed: {resp.status_code} {resp.text}")
    return resp.json()


# ---------------------------------------------------------------------------
# Upload flow
# ---------------------------------------------------------------------------

def manifest_path(slug: str) -> Path:
    return PRODUCTS / slug / "manifest.json"


def load_manifest(slug: str) -> dict | None:
    p = manifest_path(slug)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def upload_one(slug: str, dry_run: bool, force: bool, assume_yes: bool, board_override: str | None) -> str | None:
    manifest = load_manifest(slug)
    if manifest is None:
        print(f"  [skip] {slug}: no manifest")
        return None

    meta = ((manifest.get("uploads") or {}).get("pinterest") or {}).get("metadata") or {}
    title = meta.get("title")
    description = meta.get("description", "")
    link = meta.get("link") or manifest.get("affiliate-link") or manifest.get("amazon-link")
    board_id = board_override or meta.get("board_id")

    if not title:
        print(f"  [skip] {slug}: no uploads.pinterest.metadata.title - run /upload-ad first")
        return None
    if not link:
        print(f"  [skip] {slug}: no affiliate link in manifest")
        return None
    if not board_id:
        print(f"  [skip] {slug}: no board_id (set uploads.pinterest.metadata.board_id or pass --board)")
        return None

    image_path = PRODUCTS / slug / PIN_IMAGE_NAME
    if not image_path.exists():
        print(f"  [skip] {slug}: image not found at {image_path}")
        return None

    history = load_history()
    if not force and slug in history:
        prev = history[slug]
        print(f"  [skip] {slug}: already pinned {prev['uploaded_at']} -> {prev.get('url')}")
        return None

    print(f"\n{slug}")
    print(f"  board:       {board_id}")
    print(f"  image:       {image_path.name} ({image_path.stat().st_size // 1024} KB)")
    print(f"  title:       {title}")
    print(f"  description: {description[:80] + ('...' if len(description) > 80 else '')}")
    print(f"  link:        {link}")

    if dry_run:
        print("  [dry-run] would upload")
        return None
    if not assume_yes:
        if input("  upload? [y/N] ").strip().lower() != "y":
            return None

    pin = create_pin(board_id, title, description, link, image_path)
    pin_id = pin.get("id")
    pin_url = f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else None
    print(f"  pinned -> {pin_url}")

    history[slug] = {
        "pin_id": pin_id,
        "url": pin_url,
        "board_id": board_id,
        "uploaded_at": dt.datetime.now().isoformat(timespec="seconds"),
        "title": title,
    }
    save_history(history)
    return pin_id


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def cmd_boards(verbose: bool = False) -> None:
    boards = list_boards(verbose=verbose)
    print(f"[boards] API_BASE={API_BASE}", flush=True)
    if not boards:
        print("No boards. Create one with: python upload.py create-board --name \"Name\"")
        return
    print(f"{'id':<22}{'name':<40}privacy")
    for b in boards:
        print(f"{b['id']:<22}{b.get('name',''):<40}{b.get('privacy','')}")


def cmd_list() -> None:
    history = load_history()
    if not PRODUCTS.exists():
        print("(no products dir)")
        return
    names = sorted(p.name for p in PRODUCTS.iterdir() if p.is_dir())
    print(f"{'product':<40}{'image':<8}{'meta':<8}{'pinned':<12}url")
    for name in names:
        manifest = load_manifest(name) or {}
        has_image = (PRODUCTS / name / PIN_IMAGE_NAME).exists()
        meta = (((manifest.get("uploads") or {}).get("pinterest") or {}).get("metadata") or {})
        has_meta = bool(meta.get("title"))
        h = history.get(name)
        when = h["uploaded_at"][:10] if h else "-"
        url = h.get("url", "") if h else ""
        short = (name[:37] + "...") if len(name) > 40 else name
        print(f"{short:<40}{('yes' if has_image else 'no'):<8}{('yes' if has_meta else 'no'):<8}{when:<12}{url}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?",
                    help='product slug, "auth", "boards", "create-board", "delete-board", "get-board", or "whoami"')
    ap.add_argument("--board", help="override board_id for upload; or target id for delete-board/get-board")
    ap.add_argument("--name", help='board name (for "create-board")')
    ap.add_argument("--list", action="store_true", help="print status table")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="ignore history (re-pin)")
    ap.add_argument("-y", "--yes", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true", help="dump raw API responses")
    args = ap.parse_args()

    if args.list:
        cmd_list()
        return
    if args.target == "auth":
        do_auth()
        return
    if args.target == "boards":
        cmd_boards(verbose=args.verbose)
        return
    if args.target == "whoami":
        print(json.dumps(get_user_account(), indent=2))
        return
    if args.target == "get-board":
        if not args.board:
            ap.error("get-board requires --board <id>")
        print(json.dumps(get_board(args.board), indent=2))
        return
    if args.target == "delete-board":
        if not args.board:
            ap.error("delete-board requires --board <id>")
        delete_board(args.board)
        print(f"deleted board {args.board}")
        return
    if args.target == "create-board":
        if not args.name:
            ap.error("create-board requires --name")
        b = create_board(args.name)
        print(f"created board: id={b.get('id')}  name={b.get('name')}  privacy={b.get('privacy')}")
        if args.verbose:
            print(f"[create-board] full response: {json.dumps(b, indent=2)}")
        return
    if not args.target:
        ap.error('pass a product slug, "auth", "boards", or "--list"')

    upload_one(args.target, dry_run=args.dry_run, force=args.force,
               assume_yes=args.yes, board_override=args.board)


if __name__ == "__main__":
    main()
