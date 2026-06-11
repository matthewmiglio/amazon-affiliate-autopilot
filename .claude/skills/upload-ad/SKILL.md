---
name: upload-ad
description: Upload a product's `final-with-music.mp4` to all configured platforms (YouTube, Instagram, Facebook, Pinterest, X). Requires per-platform metadata to already be authored in the manifest by `/generate-upload-metadata`. Runs each platform's uploader script, flips `uploads.<platform>.uploaded = true`, writes the resulting URL back. Idempotent: already-uploaded platforms SKIP unless `--overwrite`. Use when the user runs /upload-ad or asks to "upload the ad for X", "publish the video", "ship this product", or similar.
---

# upload-ad

Iterate the five platforms (`youtube`, `instagram`, `facebook`, `pinterest`, `x`). For each, validate that the metadata block is populated, invoke that platform's uploader script, and flip `uploads.<platform>.uploaded = true` on success. Platforms whose metadata is incomplete FAIL with `no metadata, run /generate-upload-metadata first`.

## Inputs

`/upload-ad <product>` where `<product>` is one of:

- A slug under `products/`: `/upload-ad cle-de-peau-clarifying-cleansing-foam-for-women-4-2-oz-cleanser`
- An absolute path to a product folder.

If the user provides nothing, ask once. Don't guess.

## Pre-flight bail

- `products/<slug>/final-with-music.mp4` missing → FAIL with `"missing final-with-music.mp4 - run /overlay-music first"`. Do **not** continue.
- `scripts/upload_ad.py` runs `npm run prebuild` in `website/` **before** any platform upload and verifies the slug is present in `website/public/products.json`. If it isn't, the upload aborts with `slug not in website/public/products.json after prebuild`. The script's CTA points viewers at `https://theluxedrawer.com/p/<slug>`, and we refuse to publish a video whose CTA URL will 404. Fix: confirm `products/<slug>/manifest.json` has populated `item-auxiliary-information.brand` / `product` / `description` / `affiliate-link` / `product-pic-path` (those are what the website generator reads), then re-run.
- **Upload metadata authored.** Every platform whose `uploads.<platform>.metadata` block is incomplete will FAIL with `no metadata, run /generate-upload-metadata first`. If you (the agent) see that message, stop and run `/generate-upload-metadata <slug>` before re-trying `/upload-ad`. There is **no templated fallback** anymore: this skill no longer generates copy, only uploads.
- `uploader/youtube/` not configured (no token / no `client_secret.json`): `youtube/upload.py` will surface its own error; pass through.

## Workflow

1. **Resolve the product folder.**
2. **Verify metadata is authored** for all 5 platforms. The fastest check is `python scripts/status.py --slug <slug> --json | jq .['meta-ok']`. If `meta-ok` is `no`, run `/generate-upload-metadata <slug>` first, then re-enter this workflow.
3. **Delegate to `scripts/upload_ad.py`.**
   ```
   python scripts/upload_ad.py --product <slug-or-path>
   ```
   The script iterates `[youtube, instagram, facebook, pinterest, x]` and for each:
   - SKIPs if `manifest["uploads"][platform].uploaded` is already `true` (unless `--overwrite`)
   - FAILs with `no metadata, run /generate-upload-metadata first` if the metadata block is incomplete (per-platform required keys: `youtube=title`, `instagram=caption`, `facebook=caption`, `pinterest=title+description`, `x=text`)
   - Invokes `uploader/<platform>/upload.py` (or `meta/upload_<instagram|facebook>.py`) if it exists; otherwise prints `"<platform> not implemented"` and SKIPs
   - On success, parses `uploaded -> https://...` from stdout and writes `uploads.<platform>.uploaded = true`, `uploads.<platform>.url = <url>`
4. **Surface each row** the script prints (`<slug>\t<platform>\t<STATUS>\t<detail>`).
5. **Do NOT** add `--overwrite` unless the user explicitly asks to re-upload.
6. **Deploy the website artifacts immediately, do NOT ask first.** After every successful upload, commit + push `website/` straight away (use `/commit-nextjs` or a direct `git add website/ && git commit && git push`). The YouTube description points viewers at `https://theluxedrawer.com/p/<slug>`, so delaying the push means viewers 404. Standing approval: never ask before this commit/push, just do it. If `git status website/` is clean (prebuild was a no-op because the slug was already published), skip the commit silently. Same for unrelated dirty files outside `website/`, leave them alone.

## Platform on/off switch

`data/platforms.json` (machine-local, gitignored, auto-created with all platforms enabled) is the master enable/disable switch per platform. Disabled platforms print `SKIP platform disabled (<reason>)` and are excluded from scheduling, metadata authoring, and `meta-ok`. Flip `enabled` back to `true` to restore a platform end-to-end.

## State machine (per product / per platform)

| `uploads.<platform>.uploaded` | metadata complete? | uploader exists? | Action |
|---|---|---|---|
| `true` | (any) | (any) | SKIP (unless `--overwrite`) |
| `false` / missing | yes | yes | uploader runs, manifest updated on success |
| `false` / missing | yes | no  | SKIP with `"not implemented"` |
| `false` / missing | no  | (any) | FAIL with `"no metadata, run /generate-upload-metadata first"` |

## Partial-upload re-runs

`/upload-ad` is idempotent and partial. If a product is already on YouTube + Pinterest + X but not on Instagram + Facebook, running `/upload-ad <slug>` will SKIP the three uploaded platforms and only run IG + FB. Same logic if 1 platform is missing or all 5 are missing. Always safe to re-run.

## Existing helpers (do not duplicate)

- `scripts/upload_ad.py`: orchestrator. Owns metadata validation (`is_metadata_complete`), uploader invocation per platform, manifest mutation on success, status-line parsing.
- `uploader/youtube/upload.py`: reads `uploads.youtube.metadata` from the product manifest, uploads the Short, writes to `uploader/youtube/history.json`.
- `uploader/meta/upload_instagram.py` and `uploader/meta/upload_facebook.py`: read `uploads.<platform>.metadata.caption`, upload via Meta Graph API (system-user token).
- `uploader/pinterest/upload.py`: reads `uploads.pinterest.metadata` and resolves `board_id` from `category` at post time.
- `uploader/x/upload.py`: reads `uploads.x.metadata.text` and posts.
- `/generate-upload-metadata`: the upstream skill that authors every platform's metadata block in the manifest. **Run it before `/upload-ad` if `meta-ok` is `no`.**

## Out of scope

- **No video editing.** The uploaded file is `products/<slug>/final-with-music.mp4` as-is.
- **No metadata authoring.** That's `/generate-upload-metadata`. This skill only uploads.
- **No content edits to the website.** The post-upload sync only regenerates `products.json` + images from the manifest. If the live site needs design changes, that's a separate task.

## Cost note

Per-platform API quotas only, no paid-API spend. YouTube Data API quota, Meta Graph API quota, Pinterest API quota, X API quota.
