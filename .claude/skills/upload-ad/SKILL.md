---
name: upload-ad
description: Upload a product's `final-with-music.mp4` to all configured platforms (YouTube, Instagram, Facebook, Pinterest). Validates / generates per-platform metadata under `manifest["uploads"][platform].metadata`, runs each platform's uploader script, then flips `uploads.<platform>.uploaded = true` and writes the resulting URL back. Idempotent — already-uploaded platforms SKIP unless `--overwrite`. Today only YouTube actually uploads; Meta and Pinterest skip with "not implemented" until those uploaders land. Use when the user runs /upload-ad or asks to "upload the ad for X", "publish the video", "ship this product", or similar.
---

# upload-ad

Iterate the four platforms (`youtube`, `instagram`, `facebook`, `pinterest`). For each, validate metadata in `manifest["uploads"][platform].metadata`, generate if missing, invoke that platform's uploader script if it exists, and flip `uploads.<platform>.uploaded = true` on success. Platforms whose uploader script doesn't yet exist (Meta, Pinterest) skip cleanly with `"not implemented"`.

## Inputs

`/upload-ad <product>` where `<product>` is one of:

- A slug under `products/`: `/upload-ad cle-de-peau-clarifying-cleansing-foam-for-women-4-2-oz-cleanser`
- An absolute path to a product folder.

If the user provides nothing, ask once. Don't guess.

## Pre-flight bail

- `products/<slug>/final-with-music.mp4` missing → FAIL with `"missing final-with-music.mp4 - run /overlay-music first"`. Do **not** continue.
- `uploader/youtube/` not configured (no token / no `client_secret.json`) — `youtube/upload.py` will surface its own error; pass through.

## Workflow

1. **Resolve the product folder.**
2. **Delegate to `scripts/upload_ad.py`.**
   ```
   python scripts/upload_ad.py --product <slug-or-path>
   ```
   The script iterates `[youtube, instagram, facebook, pinterest]` and for each:
   - skips if `manifest["uploads"][platform].uploaded` is already `true` (unless `--overwrite`)
   - generates platform metadata if missing (regen with `--regen-meta`):
     - **youtube**: tagline = brand + product trimmed to ~60 chars, 1 evergreen UGC hashtag + 2 category hashtags, description from `script-raw-text` + affiliate link + `#shorts`, tags from hashtag stems + brand/product keywords (max 10), title capped at 100 chars
     - **instagram / facebook**: empty `caption` + `hashtags` placeholders (real generators land with the Meta uploader)
     - **pinterest**: empty `title`, `description`, `board`; `destination_url` pre-filled from the affiliate link
   - invokes `uploader/<platform>/upload.py` (or `meta/upload_<instagram|facebook>.py`) if it exists; otherwise prints `"<platform> not implemented"` and SKIPs
   - on success, parses `uploaded -> https://...` from stdout and writes `uploads.<platform>.uploaded = true`, `uploads.<platform>.url = <url>`
3. **Surface each row** the script prints (`<slug>\t<platform>\t<STATUS>\t<detail>`).
4. **Do NOT** add `--overwrite` unless the user explicitly asks to re-upload.

## State machine (per product / per platform)

| `uploads.<platform>.uploaded` | uploader exists? | Action |
|---|---|---|
| `true` | — | SKIP (unless `--overwrite`) |
| `false` / missing | yes | uploader runs, manifest updated on success |
| `false` / missing | no  | SKIP with `"not implemented"` |

## Hashtag bank

Single source of truth: `scripts/upload_ad.py` — see `EVERGREEN_HASHTAGS` and `CATEGORY_HASHTAGS`. Edit the script to add/remove hashtags or categories.

Selection rule: 1 evergreen + 2 from the matching category pool, baked into the manifest at generation time (no runtime shuffle by the uploader). Re-runs reuse the saved title verbatim. Pass `--regen-meta` to overwrite the saved metadata.

## Existing helpers (do not duplicate)

- `scripts/upload_ad.py` — owns per-platform metadata generation, manifest mutation, uploader invocation per platform, status-line parsing.
- `uploader/youtube/upload.py` — the YouTube upload itself; reads `uploads.youtube.metadata` from the product manifest, posts the title verbatim, writes to `uploader/youtube/history.json`.
- `uploader/meta/` and `uploader/pinterest/` — empty placeholders. Drop in `upload_instagram.py`, `upload_facebook.py`, `pinterest/upload.py` to wire those platforms in. Each must accept `<slug> -y` and print `uploaded -> <https-url>` on success.

## Out of scope

- **No video editing.** The uploaded file is `products/<slug>/final-with-music.mp4` as-is.
- **No metadata authoring beyond the template.** If the user wants a hand-crafted title, they can edit `manifest["uploads"][platform].metadata` directly and re-run; this skill won't overwrite populated metadata without `--regen-meta`.

## Cost note

YouTube Data API quota only — no paid-API spend. Future Meta/Pinterest uploaders should also stay quota-only (no paid-API spend).
