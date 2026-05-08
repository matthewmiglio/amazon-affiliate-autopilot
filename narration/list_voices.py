"""List available Hedra voices.

Prints `voice_id\\tname\\tlanguage` per line so the output is greppable.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
HEDRA_VOICES_URL = "https://api.hedra.com/web-app/public/voices"


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--language", help="Filter by language substring (case-insensitive).")
    args = parser.parse_args()

    api_key = os.environ.get("HEDRA_API_KEY", "").strip()
    if not api_key:
        print("ERROR: HEDRA_API_KEY missing from .env", file=sys.stderr)
        return 1

    voices: list[dict] = []
    for url in (HEDRA_VOICES_URL, "https://api.hedra.com/web-app/public/assets?type=voice"):
        r = requests.get(url, headers={"X-API-Key": api_key}, timeout=30)
        if r.status_code >= 300:
            print(f"ERROR: GET {url} {r.status_code}: {r.text}", file=sys.stderr)
            return 1
        payload = r.json()
        chunk = payload if isinstance(payload, list) else payload.get("voices") or payload.get("data") or []
        voices.extend(chunk)

    def label(asset: dict, key: str) -> str:
        for lbl in (asset or {}).get("labels", []) or []:
            if lbl.get("name") == key:
                return str(lbl.get("value", ""))
        return ""

    needle = (args.language or "").lower()
    rows = []
    for v in voices:
        vid = v.get("id") or v.get("voice_id") or ""
        name = v.get("name") or ""
        asset = v.get("asset") or {}
        lang = label(asset, "language")
        gender = label(asset, "gender")
        accent = label(asset, "accent")
        desc = (v.get("description") or "").replace("\n", " ").strip()
        if needle and needle not in lang.lower():
            continue
        rows.append((vid, name, lang, gender, accent, desc))

    rows.sort(key=lambda r: (r[2].lower(), r[3].lower(), r[1].lower()))
    print("voice_id\tname\tlanguage\tgender\taccent\tdescription")
    for row in rows:
        print("\t".join(row))
    print(f"\n{len(rows)} voice(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
