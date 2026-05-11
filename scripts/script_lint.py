"""Quality gate for narration scripts.

Checks each <products>/<slug>/manifest.json `script-raw-text` against rules:
  - 45-60 words (warn outside)
  - 280-380 chars (warn outside)
  - no '$' character (TTS reads inconsistently — spell out prices)
  - no bare digits other than years embedded in words handled separately (warn on any \\d)
  - must contain CTA phrase 'Tap the link'
  - must contain 'in my bio' (link-in-bio funnel via theluxedrawer.com)
  - must NOT mention 'on Amazon' directly

Usage:
  python script_lint.py                    # lint all
  python script_lint.py <slug> [<slug>...]  # lint specific
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "products"

WORD_MIN, WORD_MAX = 45, 60
CHAR_MIN, CHAR_MAX = 280, 380
CTA = "Tap the link"
BIO_PHRASE = "in my bio"


def lint(text: str) -> list[str]:
    issues: list[str] = []
    words = len(text.split())
    chars = len(text)
    if not (WORD_MIN <= words <= WORD_MAX):
        issues.append(f"word count {words} outside {WORD_MIN}-{WORD_MAX}")
    if not (CHAR_MIN <= chars <= CHAR_MAX):
        issues.append(f"char count {chars} outside {CHAR_MIN}-{CHAR_MAX}")
    if "$" in text:
        issues.append("contains '$' — Amazon Associates rule: no exact prices")
    if re.search(r"\d", text):
        issues.append("contains digits — spell out numbers for TTS")
    if re.search(r"\b(dollars?|bucks?|cents?)\b", text, re.IGNORECASE):
        issues.append("mentions price (dollars/bucks/cents) — Amazon Associates rule: no exact prices, use 'affordable', 'splurge', 'under X' instead")
    if CTA.lower() not in text.lower():
        issues.append(f"missing CTA phrase '{CTA}'")
    if BIO_PHRASE.lower() not in text.lower():
        issues.append(f"missing bio phrase '{BIO_PHRASE}' — CTA must point to link-in-bio (theluxedrawer.com)")
    if re.search(r"\bon Amazon\b", text, re.IGNORECASE):
        issues.append("CTA mentions Amazon directly — point to link-in-bio instead")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slugs", nargs="*", help="Product slugs to lint (default: all).")
    args = parser.parse_args()

    if args.slugs:
        targets = [PRODUCTS / s for s in args.slugs]
    else:
        targets = sorted(p for p in PRODUCTS.iterdir() if p.is_dir())

    bad = 0
    for pdir in targets:
        mp = pdir / "manifest.json"
        if not mp.exists():
            print(f"{pdir.name}\tNO MANIFEST")
            bad += 1
            continue
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        text = (manifest.get("script-raw-text") or "").strip()
        if not text:
            print(f"{pdir.name}\tNO SCRIPT")
            bad += 1
            continue
        issues = lint(text)
        if issues:
            bad += 1
            print(f"{pdir.name}\tFAIL\t{'; '.join(issues)}")
        else:
            print(f"{pdir.name}\tOK\t{len(text.split())}w / {len(text)}c")

    print(f"\n{len(targets) - bad}/{len(targets)} passed.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
