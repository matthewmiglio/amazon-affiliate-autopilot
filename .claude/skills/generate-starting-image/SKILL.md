---
name: generate-starting-image
description: Generate the 9:16 starting-frame image for Amazon affiliate products via Hedra's image-generation endpoint. For each product slug, uploads the channel's pinned character reference(s) plus the product's main image to Hedra, calls `type:"image"` generation with a prompt built from the SKILL.md axes (room / outfit / mic / hold / camera angle), downloads the result to `<product>/lifestyle-1.png`, and syncs `lifestyle-image-path` in the manifest. Idempotent — existing images are never re-rendered without `--overwrite`. Accepts a single slug, a comma-list, or `--all-needing`. Use when the user runs /generate-starting-image, says "generate starting image for X", "make the lifestyle frame", or supplies a product folder and asks for the next-stage image.
---

# generate-starting-image

Take one or more product slugs, render each into a 9:16 "podcast / UGC ad" starting frame via Hedra's multi-reference image generation, and write `lifestyle-1.png` into each product folder. Keep `manifest.json["lifestyle-image-path"]` aligned. Each genuinely-missing image is one Hedra image generation billed to the user's account.

## Inputs

`/generate-starting-image <slugs>` where `<slugs>` is one of:

- A single slug: `/generate-starting-image concealer-spf-27`
- A comma-list: `/generate-starting-image slug-a, slug-b`
- A full path to a product folder (e.g. `C:\...\products\<slug>`) — extract the slug from the last path component
- The literal flag `--all-needing` — every product that has a `manifest.json` but no `lifestyle-1.png`

If the user provides nothing, ask once. Don't guess.

## State machine (per product)

| `lifestyle-1.png` exists? | manifest has `"lifestyle-1.png"`? | Action | Cost |
|---|---|---|---|
| ✅ | ✅ | Do nothing | free |
| ✅ | ❌ | Fix manifest only — set `lifestyle-image-path` to `"lifestyle-1.png"` | free |
| ❌ | ✅ | Run Hedra image generation, download png (manifest already correct) | 1 Hedra image generation |
| ❌ | ❌ | Run Hedra image generation, download png, set `lifestyle-image-path` | 1 Hedra image generation |

Pre-flight bail per product (FAIL row):
- `manifest.json` missing → `"missing manifest.json"`
- product image missing (no `main.png` / `main.jpg` / `main.webp`) → `"no product image — run /import-referral-data first"`
- env missing (see below) → script aborts globally before any API call

## Cost confirmation (mandatory)

Hedra image generations are paid. Before kicking off, **always** print the slugs that will hit the API and ask the user to confirm. True for a single slug, a comma-list, and especially `--all-needing`. Never run the script with `--overwrite` unless the user explicitly asked to re-render an existing image.

## Workflow

1. **Resolve slugs.** Validate each `products/<slug>/manifest.json` exists. If a full folder path was supplied, take the basename.
2. **Verify env.** `hedra-vid-gen/.env` must have `HEDRA_API_KEY`. `HEDRA_IMAGE_MODEL_ID` is optional — if blank, the script auto-discovers a Nano-Banana / image-capable model from `GET /models` on first run and prints which one it picked. Character references are pulled automatically: **3 random images from `assets/character/` per slug**, seeded by `(slug, reroll)` so re-runs are stable. Don't set or expect `HEDRA_CHARACTER_REF_PATHS`.
3. **Confirm cost** with the user (see above).
4. **Delegate to `hedra-vid-gen/starting-image/generate.py`.** Run:
   ```
   cd hedra-vid-gen
   poetry run python starting-image/generate.py --products <comma-joined-slugs>
   # or
   poetry run python starting-image/generate.py --all-needing
   ```
   The script implements the full state machine. Each row of output is `<slug>\t<STATUS>\t<detail>` where STATUS ∈ {OK, FIXED, SKIP, FAIL}.
5. **Surface the summary** the script prints (e.g. `3 generated, 1 manifest-fixed, 0 skipped, 0 failed.`). On any FAIL, repeat that row to the user with the reason.

## Pinned generation parameters

- Endpoint: `POST /web-app/public/generations` with `type:"image"`
- Model: whatever `HEDRA_IMAGE_MODEL_ID` is pinned to in `.env`
- Aspect ratio: `9:16`
- Resolution: `1080p`
- Reference images: 3 random character images from `assets/character/` first (for face lock, seeded by slug for stable re-runs), then the product image — passed as `reference_image_ids`
- Text prompt: built by `hedra-vid-gen/starting-image/prompt_builder.build_prompt(slug, manifest)` — picks one coherent (room, outfit, body angle, camera angle, hold, tone) combo seeded by slug so re-runs are stable. Hard rules from the channel style (facing camera, mic in front, holding closed product label-out, real-photo realism, NOT illustrated, NOT applying/dispensing/spraying) are baked into every prompt. Don't author a prompt by hand — use the builder.

Do NOT change the aspect ratio, the reference-image order, or the prompt-builder hard rules without explicit user direction.

## Variation / re-rolls

If a generated image is OK but the user wants a different combo (different outfit / room / camera) for the same slug, re-run with `--overwrite` plus `--reroll 1` (or 2, 3, …). The seed changes, so the builder picks a new combo while keeping the same hard rules.

## Out of scope

- **No script authoring or video generation.** Subsequent stages (`/generate-narration`, `/generate-hedra-video`) own those.
- **No character-reference selection.** The reference is whatever `HEDRA_CHARACTER_REF_PATHS` is pinned to. The skill does not change `.env`.
- **No regeneration of good output.** Honor existing `lifestyle-1.png` files strictly. `--overwrite` exists for forced re-renders but only when the user explicitly asks.

## Re-runs

Safe and cheap. Existing-output products cost zero credits; misaligned manifests get fixed in O(1) IO. Only genuinely-missing images hit the Hedra API.
