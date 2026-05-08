"""List available ElevenLabs voices. Print id, name, labels for greppability."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

ROOT = Path(__file__).resolve().parent


def main() -> int:
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--language", help="Filter by language label substring (case-insensitive).")
    args = parser.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY missing from .env", file=sys.stderr)
        return 1

    client = ElevenLabs(api_key=api_key)
    res = client.voices.get_all()
    voices = getattr(res, "voices", None) or res

    needle = (args.language or "").lower()
    rows = []
    for v in voices:
        labels = getattr(v, "labels", {}) or {}
        lang = str(labels.get("language") or labels.get("accent") or "")
        gender = str(labels.get("gender") or "")
        desc = (getattr(v, "description", "") or "").replace("\n", " ").strip()
        if needle and needle not in lang.lower():
            continue
        rows.append((getattr(v, "voice_id", ""), getattr(v, "name", ""), lang, gender, desc[:80]))

    rows.sort(key=lambda r: (r[2].lower(), r[3].lower(), r[1].lower()))
    print("voice_id\tname\tlanguage\tgender\tdescription")
    for row in rows:
        print("\t".join(row))
    print(f"\n{len(rows)} voice(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
