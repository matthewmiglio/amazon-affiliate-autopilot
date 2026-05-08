"""Shared YouTube auth + token registry helpers.

Used by both `uploader/upload.py` and `youtube-channel-cleanup/cleanup.py`.
The token directory at `uploader/tokens/` is the single source of truth for
authenticated channels in this repo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKENS_DIR = HERE / "tokens"
CHANNELS_FILE = HERE / "channels.json"
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN_LEGACY = HERE / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def token_path(channel_name: str) -> Path:
    return TOKENS_DIR / f"{channel_name}.json"


def list_token_names() -> list[str]:
    if not TOKENS_DIR.exists():
        return []
    return [p.stem for p in sorted(TOKENS_DIR.glob("*.json"))]


def load_channels() -> list[dict]:
    if not CHANNELS_FILE.exists():
        return []
    return json.loads(CHANNELS_FILE.read_text(encoding="utf-8"))


def save_channels(channels: list[dict]) -> None:
    CHANNELS_FILE.write_text(json.dumps(channels, indent=2), encoding="utf-8")


def build_youtube(channel_name: str | None = None):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if channel_name is not None:
        path = token_path(channel_name)
        if not path.exists():
            sys.exit(
                f"Token not found for channel '{channel_name}' at {path}.\n"
                f"Run: python upload.py auth --channel \"{channel_name}\""
            )
        creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    else:
        if not TOKEN_LEGACY.exists():
            sys.exit("No tokens found. Run: python upload.py auth --channel <name>")
        creds = Credentials.from_authorized_user_file(str(TOKEN_LEGACY), SCOPES)

    return build("youtube", "v3", credentials=creds)
