---
name: generate-starting-image
description: Generate the 9:16 starting-frame image for Amazon affiliate products via Hedra's image-generation endpoint. For each product slug, uploads the channel's pinned character reference(s) plus the product pic to Hedra, calls `type:"image"` generation with a prompt built from the SKILL.md axes (room / outfit / mic / hold / camera angle), downloads the result to `<product>/starting-pic.png`, and syncs `starting-pic-path` in the manifest. Idempotent — existing images are never re-rendered without `--overwrite`. Accepts a single slug, a comma-list, or `--all-needing`. Use when the user runs /generate-starting-image, says "generate starting image for X", "make the starting pic", or supplies a product folder and asks for the next-stage image.
---

# generate-starting-image

Take one or more product slugs, render each into a 9:16 "podcast / UGC ad" starting frame via Hedra's multi-reference image generation, and write `starting-pic.png` into each product folder. Keep `manifest.json["starting-pic-path"]` aligned. Each genuinely-missing image is one Hedra image generation billed to the user's account.

## Inputs

`/generate-starting-image <slugs>` where `<slugs>` is one of:

- A single slug: `/generate-starting-image concealer-spf-27`
- A comma-list: `/generate-starting-image slug-a, slug-b`
- A full path to a product folder (e.g. `C:\...\products\<slug>`) — extract the slug from the last path component
- The literal flag `--all-needing` — every product that has a `manifest.json` but no `starting-pic.png`

If the user provides nothing, ask once. Don't guess.

## State machine (per product)

| `starting-pic.png` exists? | manifest has `"starting-pic.png"`? | Action | Cost |
|---|---|---|---|
| ✅ | ✅ | Do nothing | free |
| ✅ | ❌ | Fix manifest only — set `starting-pic-path` to `"starting-pic.png"` | free |
| ❌ | ✅ | Run Hedra image generation, download png (manifest already correct) | 1 Hedra image generation |
| ❌ | ❌ | Run Hedra image generation, download png, set `starting-pic-path` | 1 Hedra image generation |

Pre-flight bail per product (FAIL row):
- `manifest.json` missing → `"missing manifest.json"`
- product image missing (no `product.png` / `product.jpg` / `product.webp`) → `"no product image — run /import-referral-data first"`
- env missing (see below) → script aborts globally before any API call

## Cost note

Hedra image generations are paid, but the user has standing approval — proceed without per-call confirmation. Never run with `--overwrite` unless the user explicitly asked to re-render.

## Credit accounting (mandatory)

Before AND after the generation step, run `python scripts/credits.py` and capture the Hedra `tokens left` value. After the run, report the delta to the user:

- Single slug: `"Burned <N> Hedra credits (<before> → <after>)."`
- Batch (>1 slug, including `--all-needing`): `"Burned <N> Hedra credits across <K> images (<before> → <after>, avg <N/K>/image)."`

If 0 images were generated (all SKIP/FIXED), you can omit the line. Don't run the credits check if the run fails before making any API call.

## Workflow

1. **Resolve slugs.** Validate each `products/<slug>/manifest.json` exists. If a full folder path was supplied, take the basename.
2. **Verify env.** `hedra/.env` must have `HEDRA_API_KEY`. `HEDRA_IMAGE_MODEL_ID` is optional — when blank the script defaults to Nano Banana Pro I2I (`c81e401b-6036-4e1f-9165-60eafcee9dd3`), the empirically-best model for character lock on this pipeline. Character references are pulled automatically: **3 random images per slug from a hand-curated 5-ref whitelist** (`FACE_ANCHOR_REFS` in `starting-image/generate.py`), seeded by `(slug, reroll)` so re-runs are stable.
3. **Delegate to `hedra/starting-image/generate.py`.** Run:
   ```
   cd hedra
   poetry run python starting-image/generate.py --products <comma-joined-slugs>
   # or
   poetry run python starting-image/generate.py --all-needing
   # tune parallelism (default 4):
   poetry run python starting-image/generate.py --all-needing --workers 4
   ```
   The script implements the full state machine and runs slugs in parallel via a `ThreadPoolExecutor` (default 4 workers). Each row of output is `<slug>\t<STATUS>\t<detail>` where STATUS ∈ {OK, FIXED, SKIP, FAIL}; rows arrive as each future completes (not in submission order). Bump `--workers` only if you've confirmed Hedra's per-account concurrency cap allows it (typically 5-10).
4. **Surface the summary** the script prints (e.g. `3 generated, 1 manifest-fixed, 0 skipped, 0 failed.`). On any FAIL, repeat that row to the user with the reason.

## Pinned generation parameters

- Endpoint: `POST /web-app/public/generations` with `type:"image"`
- Model: **Nano Banana Pro I2I** (`c81e401b-6036-4e1f-9165-60eafcee9dd3`). T2I variants ignore reference images and produce drift — never use them. `HEDRA_IMAGE_MODEL_ID` overrides for experiments.
- Aspect ratio: `9:16`
- Resolution: `1K` (Hedra rejects `1080p` / `2K` is overkill — accepted values are `1K` / `2K` / `4K`)
- Reference images: **3 random images** from the curated 5-ref `FACE_ANCHOR_REFS` whitelist in `starting-image/generate.py` for face lock (seeded by `(slug, reroll)`), followed by **1** product image — all passed as `reference_image_ids` in that order.
- Asset URL: completed `type:"image"` generations don't include the URL inline. The script falls back to `GET /assets?type=image&ids=<asset_id>` and reads `[0].asset.url`.
- Poll cap: 20 minutes. Banana I2I usually finishes in ~30-60s but occasionally stalls server-side at 10% — when that happens, retry the slug.
- Text prompt: built by `hedra/starting-image/prompt_builder.build_prompt(slug, manifest, reroll, n_character_refs)`. The builder leads with hard rules (refs 1-N are the SAME woman, torso squared to camera, mic in front of her, holding closed product label-out, real-photo realism, no vignette / circle crop / soft-edge oval), then layers the scene (room/outfit/lighting/camera). Don't author a prompt by hand — use the builder.

Do NOT change the model, aspect ratio, resolution, reference-image order, or the prompt-builder hard rules without explicit user direction.

## Mic rule (HARD)

The avatar **never holds the mic** — both hands stay on the product. Allowed mic types in the prompt builder:

- desktop boom-arm condenser on a stand
- short-stand / table-stand condenser sitting on the surface in front of her
- clip-on lapel mic on her collar

**Forbidden:** handheld mics, mics-at-chin, anything she's gripping. Enforced in `prompt_builder.build_prompt` HARD RULE (2). If you tweak the rooms list, don't reintroduce "small handheld mic she's holding…" — use a stand variant instead.

## Variation / re-rolls

If a generated image is OK but the user wants a different combo (different outfit / room / camera) for the same slug, re-run with `--overwrite` plus `--reroll 1` (or 2, 3, …). The seed changes, so the builder picks a new combo while keeping the same hard rules.

## Out of scope

- **No script authoring or video generation.** Subsequent stages (`/generate-narration`, `/generate-hedra-video`) own those.
- **No character-reference selection.** Refs are pulled from the `FACE_ANCHOR_REFS` whitelist in `starting-image/generate.py`. To change which faces qualify, edit that set — don't bypass it. Removing a ref or adding one requires the same kind of QA round we ran during initial curation (generate, eyeball, correlate output quality back to which refs were used).
- **No regeneration of good output.** Honor existing `starting-pic.png` files strictly. `--overwrite` exists for forced re-renders but only when the user explicitly asks.

## Re-runs

Safe and cheap. Existing-output products cost zero credits; misaligned manifests get fixed in O(1) IO. Only genuinely-missing images hit the Hedra API.
