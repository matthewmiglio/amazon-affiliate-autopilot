"""Print Hedra + ElevenLabs credit balances.

  python scripts/credits.py            # human-readable
  python scripts/credits.py --json     # raw JSON
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent / ".env"
HEDRA_URL = "https://api.hedra.com/web-app/public/billing/credits"
ELEVEN_URL = "https://api.elevenlabs.io/v1/user/subscription"


def fetch_hedra(key: str) -> dict:
    r = requests.get(HEDRA_URL, headers={"X-API-Key": key}, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_eleven(key: str) -> dict:
    r = requests.get(ELEVEN_URL, headers={"xi-api-key": key}, timeout=20)
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit raw JSON.")
    args = ap.parse_args()

    load_dotenv(ENV_FILE)
    hedra_key = os.environ.get("HEDRA_API_KEY", "").strip()
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not hedra_key:
        sys.exit(f"HEDRA_API_KEY missing in {ENV_FILE}")
    if not eleven_key:
        sys.exit(f"ELEVENLABS_API_KEY missing in {ENV_FILE}")

    hedra = fetch_hedra(hedra_key)
    eleven = fetch_eleven(eleven_key)

    if args.json:
        print(json.dumps({"hedra": hedra, "elevenlabs": eleven}, indent=2))
        return 0

    used = eleven.get("character_count", 0)
    limit = eleven.get("character_limit", 0)
    eleven_remaining = max(limit - used, 0)
    reset_unix = eleven.get("next_character_count_reset_unix")
    reset_str = (
        datetime.fromtimestamp(int(reset_unix), tz=timezone.utc).strftime("%Y-%m-%d")
        if reset_unix else "unknown"
    )
    hedra_remaining = sum((hedra.get("workspace_credits") or {}).values())

    print(f"ElevenLabs : {eleven_remaining:>8,} tokens left  (resets {reset_str})")
    print(f"Hedra      : {hedra_remaining:>8,} tokens left  (resets {reset_str})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
