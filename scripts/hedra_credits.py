"""Print Hedra credit balance for the workspace behind HEDRA_API_KEY.

  python scripts/hedra_credits.py            # human-readable
  python scripts/hedra_credits.py --json     # raw JSON

Endpoint: GET https://api.hedra.com/web-app/public/billing/credits
Auth:     X-API-Key (same key used by the rest of hedra-vid-gen)

Hedra does NOT expose a billing-period reset date via API as of 2026-05.
Only counts (remaining / expiring / used / per-workspace) are returned.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "hedra-vid-gen" / ".env"
URL = "https://api.hedra.com/web-app/public/billing/credits"


def fetch() -> dict:
    load_dotenv(ENV_FILE)
    key = os.environ.get("HEDRA_API_KEY", "").strip()
    if not key:
        sys.exit(f"HEDRA_API_KEY missing in {ENV_FILE}")
    r = requests.get(URL, headers={"X-API-Key": key}, timeout=20)
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit raw JSON.")
    args = ap.parse_args()

    data = fetch()

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    remaining = data.get("remaining", 0)
    expiring = data.get("expiring", 0)
    used = data.get("used", 0)
    ws_credits = data.get("workspace_credits") or {}

    print(f"Hedra credits")
    print(f"  remaining : {remaining:>8,}")
    print(f"  expiring  : {expiring:>8,}  (credits scheduled to expire)")
    print(f"  used      : {used:>8,}  (this billing period)")
    if ws_credits:
        print("  per-workspace:")
        for ws_id, amount in ws_credits.items():
            print(f"    {ws_id}: {amount:,}")
    print()
    print("note: Hedra's API does not expose a credit reset date — check the")
    print("dashboard at https://www.hedra.com/app/settings/billing for that.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
