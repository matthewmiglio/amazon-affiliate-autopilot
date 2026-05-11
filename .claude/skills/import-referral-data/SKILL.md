---
name: import-referral-data
description: Import scraped Amazon affiliate product data from the Downloads folder into the project's products folder, converting raw scrape output into the project's manifest.json format. Filters out items with commission rates below 10% and skips dupes by ASIN. Use when the user runs /import-referral-data or asks to "import scraped products", "pull in new affiliate products", or similar.
---

# import-referral-data

Take newly scraped Amazon affiliate products from the scraper extension's Downloads dump and convert each one into the project's standard product folder format. Filter out anything below 10% commission, dedupe against what's already imported.

## Inputs

- **Source:** `C:\Users\matt\Downloads\amazon-product-scrape\`
  - One subfolder per product (slugified product name)
  - Each subfolder contains: `data.json`, `row.json`, `product.<ext>` (jpg/png/etc.)
  - `data.json` top-level fields: `product-name`, `description`, `product-pic-path`, `affiliate-link`, `commission-rate`, `product-page-url`
  - `data.json` `meta`: `{ brand, price, asin, featureBullets, scrapedAt, ... }`

- **Destination:** `C:\My_Files\my_programs\amazon-affiliate\products\`
  - One subfolder per imported product, **same folder name as the source folder**
  - Each destination folder contains:
    - `product.<ext>` — the product image, copied from the scraper's `product.<ext>` (keep original extension; do NOT convert)
    - `manifest.json` — see schema below

## Destination manifest.json schema

This matches the existing `assets/products/<x>/manifest.json` shape used elsewhere in the project. Always emit all keys, even when empty.

```json
{
  "starting-pic-path": "",
  "narration-audio-path": "",
  "raw-speaker-video-path": "",
  "stitched-narration-video-path": "",
  "captioned-video-path": "",
  "final-with-music-video-path": "",
  "product-pic-path": "product.jpg",
  "item-auxiliary-information": {
    "brand": "...",
    "product": "...",
    "category": "skincare / makeup | fragrance | makeup | jewelry | beauty",
    "notes": "",
    "asin": "...",
    "price": "$...",
    "affiliate-link": "https://amzn.to/...",
    "product-page-url": "https://www.amazon.com/...",
    // ↑ INTERNAL lookup only. These never appear in generated scripts /
    //   captions / YouTube descriptions / Pinterest destinations. The funnel
    //   goes through https://theluxedrawer.com/p/<slug>, which redirects to
    //   `affiliate-link` server-side. Downstream skills must NOT quote these
    //   raw Amazon URLs in viewer-facing content.
    "description": "..."
  },
  "script-raw-text": "",
  "video-prompt": "",
  "commission-percentage": "10.00%",
  "background-music-track": "",
  "uploads": {
    "youtube": {
      "uploaded": false,
      "url": "",
      "metadata": {
        "title": "",
        "description": "",
        "tags": [],
        "category": "22",
        "privacy": "public",
        "hashtags": []
      }
    },
    "instagram": {
      "uploaded": false,
      "url": "",
      "metadata": { "caption": "", "hashtags": [] }
    },
    "facebook": {
      "uploaded": false,
      "url": "",
      "metadata": { "caption": "", "hashtags": [] }
    },
    "pinterest": {
      "uploaded": false,
      "url": "",
      "metadata": {
        "title": "",
        "description": "",
        "destination_url": "",
        "board": ""
      }
    }
  }
}
```

- `starting-pic-path`, `narration-audio-path`, `raw-speaker-video-path`, `stitched-narration-video-path`, and `captioned-video-path` stay empty — those get filled in by downstream skills (starting-pic generation, Hedra TTS, the AI video gen output, `/stitch-narration`, and `/caption-video` respectively).
- `script-raw-text` and `video-prompt` stay empty — narration and the Hedra video prompt are authored later.
- `background-music-track` stays empty — populated by `/overlay-music` once a track is mixed in.
- `category` is inferred from brand + product name. Reasonable buckets: skincare/makeup, fragrance, makeup, jewelry, beauty (fallback).
- `commission-percentage` keeps the original string from the scrape (e.g. `"10.00%"`).

## Rules

1. **Commission filter:** strip `%` from `data.commission-rate`, parse as float; skip if `< 10` or unparseable.
2. **Dedupe:** read every existing `<dest>/<folder>/manifest.json` and collect each `item-auxiliary-information.asin` into a Set. Skip a source if its ASIN is already present. Add newly-imported ASINs to the Set as you go so two source folders for the same ASIN don't both copy.
3. **Don't move, don't mutate the source.** The Downloads scrape folder must stay intact for re-runs.
4. **Image handling:** copy `product.<ext>` from the scrape folder → `product.<ext>` in the destination (preserve extension exactly — don't transcode).
5. **Folder naming:** keep the source folder name as the slug, BUT strip trailing punctuation and dangling stop-words before creating the destination folder. Specifically: peel off any trailing `-`, `_`, `.`, `,`, AND any trailing `-and`, `-with`, `-or`, `-to`, `-for`, `-the`, `-of`, `-in`, `-on` until the slug ends on a content word. Reason: YouTube's mobile auto-linkifier eats the next word across a newline boundary into URLs that end with `-`, breaking `theluxedrawer.com/p/<slug>` links. There's a helper at `scripts/sanitize_slugs.py` — use the `clean_slug()` function in it as the canonical implementation; do not reinvent. Skip-if-empty: never end with an empty string; if cleaning produces "", fall back to the original (something is better than nothing).
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
     - Copy `product.<ext>` from scrape → `product.<ext>` in destination if present.
     - Write `manifest.json` per the schema above.
     - Add ASIN to the Set.
5. Print a concise summary: counts (imported / skipped-low-commission / skipped-dupe / errored) + per-item line `"<folder> — IMPORTED (pct%, ASIN, product.<ext>) | SKIPPED (reason)"`.

## Re-runs and migrations

If the destination still contains old-format folders from an earlier (broken) run — i.e. folders with `data.json` + raw image instead of `manifest.json` + `product.<ext>` — delete those folders first before importing. Only do this for folders that match the raw-scrape signature; leave anything that already has `manifest.json` alone.

## Implementation tips

- Use `mcp__plugin_context-mode_context-mode__ctx_execute(language: "shell")` driving Node via `node - <<'EOF' ... EOF`. `bun` may not be installed.
- Use `fs.copyFileSync` for the image. Use `fs.writeFileSync` with `JSON.stringify(obj, null, 2)` for the manifest.
- Don't use Bash for file walking — keep raw output out of context. Process and print only the summary.

## Out of scope

- Don't re-fetch, re-scrape, or re-validate any product data.
- Don't author scripts, narration, or starting-pic imagery — those belong to other skills.
- Don't delete from the source folder.
