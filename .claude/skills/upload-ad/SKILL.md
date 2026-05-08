---
name: upload-ad
description: Upload a product's `final-with-music.mp4` to YouTube Shorts. Validates / generates the per-product `youtube-metadata` block in `manifest.json` (title with category-aware hashtags, description, tags), runs `uploader/upload.py`, then flips `uploaded: true` and writes `uploaded-video-url` back to the manifest. Idempotent — already-uploaded products SKIP unless `--overwrite`. Use when the user runs /upload-ad or asks to "upload the ad for X", "publish the video to YouTube", "ship this product", or similar.
---

# upload-ad

Validate that the product's YouTube metadata is in its `manifest.json`, generate it if missing, push the final mp4 to YouTube via the existing `uploader/upload.py`, and flip the `uploaded` flag.

## Inputs

`/upload-ad <product>` where `<product>` is one of:

- A slug under `products/`: `/upload-ad cle-de-peau-clarifying-cleansing-foam-for-women-4-2-oz-cleanser`
- An absolute path to a product folder.

If the user provides nothing, ask once. Don't guess.

## Pre-flight bail

- `products/<slug>/final-with-music.mp4` missing → FAIL with `"missing final-with-music.mp4 - run /overlay-music first"`. Do **not** continue.
- `uploader/` not configured (no token / no `client_secret.json`) — `upload.py` will surface its own error; pass through.

## Workflow

1. **Resolve the product folder.**
2. **Delegate to `scripts/upload_ad.py`.**
   ```
   python scripts/upload_ad.py --product <slug-or-path>
   ```
   The script:
   - bails if `final-with-music.mp4` is missing
   - if `manifest["youtube-metadata"].title` is empty, builds metadata from the manifest:
     - tagline = brand + product (trimmed to ~60 chars, size/pack noise stripped)
     - 1 evergreen UGC hashtag + 2 from the matching category pool
     - description from `script-raw-text` + affiliate link + `#shorts`
     - YouTube `tags` = hashtag stems + brand/product keywords (max 10)
     - title is final form including hashtags, capped at 100 chars
   - skips if `manifest.uploaded` is already `true` (unless `--overwrite`)
   - runs `python uploader/upload.py <slug> -y`
   - on success, parses the `uploaded -> https://youtu.be/<id>` line
   - sets `manifest.uploaded = true`, `manifest["uploaded-video-url"] = <url>`
3. **Surface the row** the script prints (`<slug>\t<STATUS>\t<detail>`).
4. **Do NOT** add `--overwrite` unless the user explicitly asks to re-upload.

## State machine (per product)

| `manifest.uploaded` | Action |
|---|---|
| `true` | SKIP (unless `--overwrite`) |
| `false` / missing | uploader runs, manifest updated on success |

## Hashtag bank

Single source of truth: `scripts/upload_ad.py` — see `EVERGREEN_HASHTAGS` and `CATEGORY_HASHTAGS`. Edit the script to add/remove hashtags or categories.

Selection rule: 1 evergreen + 2 from the matching category pool, baked into the manifest at generation time (no runtime shuffle by the uploader). Re-runs reuse the saved title verbatim. Pass `--regen-meta` to overwrite the saved metadata.

## Existing helpers (do not duplicate)

- `scripts/upload_ad.py` — owns metadata generation, manifest mutation, uploader invocation, status-line parsing.
- `uploader/upload.py` — the YouTube upload itself; reads `youtube-metadata` from the product manifest, posts the title verbatim, writes to `uploader/history.json`.

## Out of scope

- **No video editing.** The uploaded file is `products/<slug>/final-with-music.mp4` as-is.
- **No multi-platform upload.** YouTube Shorts only.
- **No metadata authoring beyond the template.** If the user wants a hand-crafted title, they can edit `manifest["youtube-metadata"]` directly and re-run; this skill won't overwrite a populated title without `--regen-meta`.

## Cost note

YouTube Data API quota only — no paid-API spend.
