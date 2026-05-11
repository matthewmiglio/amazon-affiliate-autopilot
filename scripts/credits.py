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

# Empirical per-asset costs measured over recent batches.
HEDRA_CREDITS_PER_VIDEO = 151
HEDRA_CREDITS_PER_IMAGE = 15
ELEVENLABS_CHARS_PER_NARRATION = 146


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

    used = eleven.get("character_count", 0)
    limit = eleven.get("character_limit", 0)
    eleven_remaining = max(limit - used, 0)
    reset_unix = eleven.get("next_character_count_reset_unix")
    reset_str = (
        datetime.fromtimestamp(int(reset_unix), tz=timezone.utc).strftime("%Y-%m-%d")
        if reset_unix else "unknown"
    )
    hedra_remaining = sum((hedra.get("workspace_credits") or {}).values())

    approx_hedra_vids_left = hedra_remaining // HEDRA_CREDITS_PER_VIDEO
    approx_narrations_left = eleven_remaining // ELEVENLABS_CHARS_PER_NARRATION
    approx_hedra_images_left = (
        hedra_remaining // HEDRA_CREDITS_PER_IMAGE
        if HEDRA_CREDITS_PER_IMAGE else None
    )

    if args.json:
        print(json.dumps({
            "hedra": hedra,
            "elevenlabs": eleven,
            "approx_hedra_vids_left": approx_hedra_vids_left,
            "approx_narrations_left": approx_narrations_left,
            "approx_hedra_image_gen_left": approx_hedra_images_left,
        }, indent=2))
        return 0

    print(f"ElevenLabs : {eleven_remaining:>8,} tokens left  (resets {reset_str})")
    print(f"Hedra      : {hedra_remaining:>8,} tokens left  (resets {reset_str})")
    print()
    print(f"  approx_hedra_vids_left     : {approx_hedra_vids_left:>5,}  (~{HEDRA_CREDITS_PER_VIDEO} credits/vid)")
    print(f"  approx_narrations_left     : {approx_narrations_left:>5,}  (~{ELEVENLABS_CHARS_PER_NARRATION} chars/narration)")
    if approx_hedra_images_left is None:
        print(f"  approx_hedra_image_gen_left:    ??  (rate not measured yet -- TODO)")
    else:
        print(f"  approx_hedra_image_gen_left: {approx_hedra_images_left:>5,}  (~{HEDRA_CREDITS_PER_IMAGE} credits/image)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
