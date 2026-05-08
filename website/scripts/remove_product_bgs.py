"""Strip backgrounds from website/public/products/* into website/public/products-nobg/<slug>.png.

Cached so re-runs of `npm run prebuild` don't blow them away. Imports remove_bg.py's
process() function directly to share a single rembg session across the batch.
"""
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
WEBSITE = HERE.parent.parent
SRC_DIR = WEBSITE / "public" / "products"
DST_DIR = WEBSITE / "public" / "products-nobg"

REMOVE_BG_DIR = Path(r"C:\My_Files\my_programs\wow_fishbot\ads\scripts")
sys.path.insert(0, str(REMOVE_BG_DIR))

# remove_bg.py calls os.add_dll_directory at import time for cudnn; if that fails,
# fall back to a CPU-only providers list.
USE_GPU = True
try:
    import remove_bg  # noqa: E402
except Exception as e:
    print(f"[warn] remove_bg import failed with GPU dll setup: {e}")
    print("[warn] retrying with CPU fallback")
    # monkeypatch out the dll add_directory call by stubbing os.add_dll_directory
    _orig = os.add_dll_directory

    def _noop(*a, **k):
        class _C:
            def close(self):
                pass
        return _C()

    os.add_dll_directory = _noop  # type: ignore
    try:
        import remove_bg  # noqa: E402
        USE_GPU = False
    finally:
        os.add_dll_directory = _orig  # type: ignore

from rembg import new_session  # noqa: E402


def main() -> int:
    DST_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SRC_DIR.iterdir() if p.is_file())
    if not files:
        print(f"[err] no source images in {SRC_DIR}")
        return 1

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if USE_GPU else ["CPUExecutionProvider"]
    print(f"[info] {len(files)} source images; providers={providers}")
    session = new_session("birefnet-general", providers=providers)

    total = len(files)
    created = skipped = failed = 0
    for i, src in enumerate(files, 1):
        slug = src.stem
        dst = DST_DIR / f"{slug}.png"
        if dst.exists():
            print(f"[{i}/{total}] {slug} SKIP (cached)")
            skipped += 1
            continue
        t0 = time.time()
        try:
            remove_bg.process(src, dst, session)
            ms = int((time.time() - t0) * 1000)
            print(f"[{i}/{total}] {slug} -> {ms}ms")
            created += 1
        except Exception as e:
            print(f"[{i}/{total}] {slug} FAIL: {e}")
            failed += 1

    print(f"DONE: {created} created, {skipped} skipped, {failed} failed")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
