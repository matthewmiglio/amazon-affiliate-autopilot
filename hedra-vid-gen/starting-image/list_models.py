"""
List Hedra AI models. Print id/name/type so you can pick an image-capable
model and pin its id as HEDRA_IMAGE_MODEL_ID in hedra-vid-gen/.env.

Usage:
  poetry run python list_models.py
  poetry run python list_models.py --image-only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
sys.path.insert(0, str(PARENT))
import _common as hc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-only", action="store_true",
                    help="Only show models whose name/type hints at image generation.")
    args = ap.parse_args()

    key = hc.api_key()
    r = requests.get(f"{hc.API_BASE}/models", headers=hc.headers(key), timeout=60)
    r.raise_for_status()
    models = r.json()
    if isinstance(models, dict) and "models" in models:
        models = models["models"]

    rows = []
    for m in models:
        mid = m.get("id") or m.get("model_id") or ""
        name = m.get("name") or m.get("display_name") or ""
        mtype = m.get("type") or m.get("modality") or m.get("category") or ""
        blob = f"{name} {mtype}".lower()
        is_image = "image" in blob or "banana" in blob or "seedream" in blob or "flux" in blob or "gpt image" in blob
        if args.image_only and not is_image:
            continue
        rows.append((mid, name, mtype, "image" if is_image else ""))

    print("model_id\tname\ttype\timage?")
    for row in rows:
        print("\t".join(str(c) for c in row))
    print(f"\n{len(rows)} model(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
