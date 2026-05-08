---
name: import-referral-data
description: Import scraped Amazon affiliate product data from the Downloads folder into the project's products folder, converting raw scrape output into the project's manifest.json format. Filters out items with commission rates below 10% and skips dupes by ASIN. Use when the user runs /import-referral-data or asks to "import scraped products", "pull in new affiliate products", or similar.
---

# import-referral-data

Take newly scraped Amazon affiliate products from the scraper extension's Downloads dump and convert each one into the project's standard product folder format. Filter out anything below 10% commission, dedupe against what's already imported.

## Inputs

- **Source:** `C:\Users\matt\Downloads\amazon-product-scrape\`
  - One subfolder per product (slugified product name)
  - Each subfolder contains: `data.json`, `row.json`, `image.<ext>` (jpg/png/etc.)
  - `data.json` top-level fields: `product-name`, `description`, `image-path`, `affiliate-link`, `commission-rate`, `product-page-url`
  - `data.json` `meta`: `{ brand, price, asin, featureBullets, scrapedAt, ... }`

- **Destination:** `C:\My_Files\my_programs\amazon-affiliate\products\`
  - One subfolder per imported product, **same folder name as the source folder**
  - Each destination folder contains:
    - `main.<ext>` — the product image, renamed from `image.<ext>` (keep original extension; do NOT convert)
    - `manifest.json` — see schema below

## Destination manifest.json schema

This matches the existing `assets/products/<x>/manifest.json` shape used elsewhere in the project. Always emit all keys, even when empty.

```json
{
  "lifestyle-image-path": "",
  "narration-audio-path": "",
  "raw-speaker-video-path": "",
  "stitched-narration-video-path": "",
  "captioned-video-path": "",
  "final-with-music-video-path": "",
  "main-product-image-path": "main.jpg",
  "item-auxiliary-information": {
    "brand": "...",
    "product": "...",
    "category": "skincare / makeup | fragrance | makeup | jewelry | beauty",
    "notes": "",
    "asin": "...",
    "price": "$...",
    "affiliate-link": "https://amzn.to/...",
    "product-page-url": "https://www.amazon.com/...",
    "description": "..."
  },
  "script-raw-text": "",
  "commission-percentage": "10.00%",
  "youtube-metadata": {
    "title": "",
    "description": "",
    "tags": [],
    "category": "22",
    "privacy": "public",
    "hashtags": []
  },
  "uploaded": false,
  "uploaded-video-url": ""
}
```

- `lifestyle-image-path`, `narration-audio-path`, `raw-speaker-video-path`, `stitched-narration-video-path`, and `captioned-video-path` stay empty — those get filled in by downstream skills (lifestyle image gen, Hedra TTS, the AI video gen output, `/stitch-narration`, and `/caption-video` respectively).
- `script-raw-text` stays empty — narration is authored later.
- `category` is inferred from brand + product name. Reasonable buckets: skincare/makeup, fragrance, makeup, jewelry, beauty (fallback).
- `commission-percentage` keeps the original string from the scrape (e.g. `"10.00%"`).

## Rules

1. **Commission filter:** strip `%` from `data.commission-rate`, parse as float; skip if `< 10` or unparseable.
2. **Dedupe:** read every existing `<dest>/<folder>/manifest.json` and collect each `item-auxiliary-information.asin` into a Set. Skip a source if its ASIN is already present. Add newly-imported ASINs to the Set as you go so two source folders for the same ASIN don't both copy.
3. **Don't move, don't mutate the source.** The Downloads scrape folder must stay intact for re-runs.
4. **Image handling:** copy `image.<ext>` → `main.<ext>` (preserve extension exactly — don't transcode).
5. **Folder naming:** keep the source folder name verbatim (it's already a slug).
6. **No `data.json` / `row.json` in the destination.** All info must be folded into `manifest.json`.

## Steps

1. If the source root doesn't exist: report nothing to import and stop.
2. Ensure destination root exists (`mkdir -p`).
3. Build the existing-ASIN Set from destination manifests.
4. For each source subfolder:
   - Parse `data.json`. On error, skip with reason.
   - Check commission. Skip if `< 10` or missing.
   - Check ASIN. Skip if dupe.
   - Otherwise:
     - `mkdir <dest>/<folder>`
     - Copy `image.<ext>` → `main.<ext>` if present.
     - Write `manifest.json` per the schema above.
     - Add ASIN to the Set.
5. Print a concise summary: counts (imported / skipped-low-commission / skipped-dupe / errored) + per-item line `"<folder> — IMPORTED (pct%, ASIN, main.<ext>) | SKIPPED (reason)"`.

## Re-runs and migrations

If the destination still contains old-format folders from an earlier (broken) run — i.e. folders with `data.json` + `image.<ext>` instead of `manifest.json` + `main.<ext>` — delete those folders first before importing. Only do this for folders that match the raw-scrape signature; leave anything that already has `manifest.json` alone.

## Implementation tips

- Use `mcp__plugin_context-mode_context-mode__ctx_execute(language: "shell")` driving Node via `node - <<'EOF' ... EOF`. `bun` may not be installed.
- Use `fs.copyFileSync` for the image. Use `fs.writeFileSync` with `JSON.stringify(obj, null, 2)` for the manifest.
- Don't use Bash for file walking — keep raw output out of context. Process and print only the summary.

## Out of scope

- Don't re-fetch, re-scrape, or re-validate any product data.
- Don't author scripts, narration, or lifestyle imagery — those belong to other skills.
- Don't delete from the source folder.
