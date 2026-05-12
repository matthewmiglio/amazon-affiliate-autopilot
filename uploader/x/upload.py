"""X (Twitter) video tweet uploader entry point.

Phase 2 only wires the `auth` subcommand. Phase 3 will add the chunked
media upload + POST /2/tweets flow and the `<slug>` form that
scripts/upload_ad.py invokes.

CLI:
    python uploader/x/upload.py auth          # one-time OAuth flow
    python uploader/x/upload.py whoami        # sanity-check the stored token
    python uploader/x/upload.py <slug> -y     # (Phase 3 — not implemented yet)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import x_auth  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: upload.py [auth|whoami|<product-slug>]")
        return 1
    cmd = sys.argv[1]
    if cmd == "auth":
        x_auth._run_pkce_flow()
        print(f"OK — token saved to {x_auth.TOKEN_FILE}")
        return 0
    if cmd == "whoami":
        print(json.dumps(x_auth.whoami(), indent=2))
        return 0
    # Anything else is treated as a product slug — Phase 3 territory.
    print(f"{cmd}\tFAIL\tx uploader not implemented yet (Phase 3)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
