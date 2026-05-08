---
name: generate-hedra-video
description: Generate Hedra Avatar talking-head videos for Amazon affiliate products. For each product slug, uploads the product's `lifestyle-1.png` (start frame) and `narration.mp3` (audio + duration source) to the Hedra API, runs a 9:16 mobile-resolution Avatar generation, downloads the result to `<product>/raw-speaker-video.mp4`, and syncs `raw-speaker-video-path` in the manifest. Idempotent — existing videos are never re-rendered without `--overwrite`. Accepts a single slug, a comma-list, or `--all-needing`. Use when the user runs /generate-hedra-video or asks to "render the speaker video for X", "make the Hedra avatar video", or similar.
---

# generate-hedra-video

Take one or more product slugs, render each into a Hedra **Avatar** talking-head video (9:16, 720p, duration auto-matched to the narration), and write `raw-speaker-video.mp4` into each product folder. Keep `manifest.json["raw-speaker-video-path"]` aligned. Each genuinely-missing video is one Hedra Avatar generation billed to the user's account.

## Inputs

`/generate-hedra-video <slugs>` where `<slugs>` is one of:

- A single slug: `/generate-hedra-video color-control-cushion-compact-broad-spectrum-spf-50-korean-foundation-with-build`
- A comma-list: `/generate-hedra-video slug-a, slug-b`
- A full path to a product folder (e.g. `C:\...\products\<slug>`) — extract the slug from the last path component
- The literal flag `--all-needing` — every product that has both `lifestyle-1.png` and `narration.mp3` but no `raw-speaker-video.mp4`

If the user provides nothing, ask once. Don't guess.

## State machine (per product)

| `raw-speaker-video.mp4` exists? | manifest has `"raw-speaker-video.mp4"`? | Action | Cost |
|---|---|---|---|
| ✅ | ✅ | Do nothing | free |
| ✅ | ❌ | Fix manifest only — set `raw-speaker-video-path` to `"raw-speaker-video.mp4"` | free |
| ❌ | ✅ | Run Hedra generation, download mp4 (manifest already correct) | 1 Hedra Avatar generation |
| ❌ | ❌ | Run Hedra generation, download mp4, set `raw-speaker-video-path` | 1 Hedra Avatar generation |

Pre-flight bail per product (FAIL row):
- `lifestyle-1.png` missing → `"missing lifestyle-1.png — generate the starting frame first"`
- `narration.mp3` missing → `"missing narration.mp3 — run /generate-narration first"`

## Cost confirmation (mandatory)

Hedra Avatar generations are paid. Before kicking off, **always** print the slugs that will hit the API and ask the user to confirm. This is true for a single slug, a comma-list, and especially `--all-needing`. Never run the script with `--overwrite` unless the user explicitly asked to re-render an existing video.

## Workflow

1. **Resolve slugs.** Validate each `products/<slug>/manifest.json` exists. If a full folder path was supplied, take the basename.
2. **Verify env.** `hedra-vid-gen/.env` must have `HEDRA_API_KEY`. Abort if missing — do not invent one.
3. **Confirm cost** with the user (see above).
4. **Delegate to `hedra-vid-gen/avatar-video/generate.py`.** Run:
   ```
   cd hedra-vid-gen
   poetry run python avatar-video/generate.py --products <comma-joined-slugs>
   # or
   poetry run python avatar-video/generate.py --all-needing
   ```
   The script implements the full state machine. Each row of output is `<slug>\t<STATUS>\t<detail>` where STATUS ∈ {OK, FIXED, SKIP, FAIL}.
5. **Surface the summary** the script prints (e.g. `3 generated, 1 manifest-fixed, 0 skipped, 0 failed.`). On any FAIL, repeat that row to the user with the reason.

## Pinned generation parameters

- Model: **Hedra Avatar** (`ai_model_id=26f0fc66-152b-40ab-abed-76c43df99bc8`) — NOT Character-3.
- Aspect ratio: `9:16`
- Resolution: `720p` (mobile)
- Duration: auto — Hedra matches the uploaded audio length
- Start keyframe: `lifestyle-1.png`
- Audio: `narration.mp3`
- Text prompt: `manifest["video-prompt"]` if present, else `manifest["script-raw-text"]`, truncated to 500 chars. Hedra Avatar is audio-driven; the text prompt is just a stylistic hint, NOT the spoken script. The narration mp3 drives lipsync.
- Poll cap: 60 minutes, 15s interval.
- Asset URL: completed video generations sometimes return `asset_id` with no `download_url`; the script falls back to `GET /assets?type=video&ids=<asset_id>` and reads `[0].asset.url`.

Do NOT change the model, aspect ratio, or resolution without explicit user direction.

## Queue stalls + recovery

Hedra Avatar can sit in `status=queued, progress=0.0` for tens of minutes when the platform queue is busy — even though the generation is otherwise valid. **A timeout from the script does NOT mean the generation failed**; Hedra often finishes it on their side, billed.

If a slug times out:

1. Look at the FAIL row — it includes the generation id (e.g. `8896f94f-c267-4a9b-8952-e0c8d6f701cb`).
2. Probe `GET https://api.hedra.com/web-app/public/generations/<gen_id>/status`. If `status == "complete"`, fetch the URL via `/assets?type=video&ids=<asset_id>` and download to `products/<slug>/raw-speaker-video.mp4`, then set `manifest["raw-speaker-video-path"] = "raw-speaker-video.mp4"`.
3. Only re-run the slug if the generation truly failed (`status` ∈ `{error, failed, canceled}`) — re-running while the original is still queued double-bills.

A one-off recovery script that polls a known generation id and downloads on completion is cheap to spin up; do that before assuming a re-run is needed.

## Out of scope

- **No starting-frame generation.** If `lifestyle-1.png` is missing, FAIL. Use `/generate-starting-image` separately.
- **No narration generation.** If `narration.mp3` is missing, FAIL. Use `/generate-narration` first.
- **No audio stitching.** The output is the raw Hedra mp4 (with its baked-in audio). `/stitch-narration` is the next step that swaps in the clean narration.
- **No regeneration of good output.** Honor existing `raw-speaker-video.mp4` files strictly.

## Re-runs

Safe and cheap. Existing-output products cost zero credits; misaligned manifests get fixed in O(1) IO. Only genuinely-missing videos hit the Hedra API. `--overwrite` exists for forced re-renders but only when the user explicitly asks.
