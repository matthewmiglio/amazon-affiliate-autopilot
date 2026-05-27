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
- `scripts/upload_ad.py` runs `npm run prebuild` in `website/` **before** any platform upload and verifies the slug is present in `website/public/products.json`. If it isn't, the upload aborts with `slug not in website/public/products.json after prebuild` — the script's CTA points viewers at `https://theluxedrawer.com/p/<slug>`, and we refuse to publish a video whose CTA URL will 404. Fix: confirm `products/<slug>/manifest.json` has populated `item-auxiliary-information.brand` / `product` / `description` / `affiliate-link` / `product-pic-path` (those are what the website generator reads), then re-run.
- `uploader/youtube/` not configured (no token / no `client_secret.json`) — `youtube/upload.py` will surface its own error; pass through.

## Workflow

1. **Resolve the product folder.**
2. **Author Pinterest metadata BEFORE delegating.** See `## Pinterest metadata (agent-authored)` below — you (the agent) must write `uploads.pinterest.metadata` directly into the manifest with `title`, `description`, `alt_text`, `category`, `link`. The script's templated fallback exists only for cron paths that skip /upload-ad; if you let it fire here, you're shipping weak SEO copy.
3. **Delegate to `scripts/upload_ad.py`.**
   ```
   python scripts/upload_ad.py --product <slug-or-path>
   ```
   The script iterates `[youtube, instagram, facebook, pinterest]` and for each:
   - skips if `manifest["uploads"][platform].uploaded` is already `true` (unless `--overwrite`)
   - generates platform metadata if missing (regen with `--regen-meta`):
     - **youtube**: tagline = brand + product trimmed to ~60 chars, 1 evergreen UGC hashtag + 2 category hashtags, description leads with `Shop on theluxedrawer.com: https://theluxedrawer.com/p/<slug>` (NOT the raw `amzn.to` link — funnel goes through our site), then `script-raw-text`, then hashtags + `#shorts`, tags from hashtag stems + brand/product keywords (max 10), title capped at 100 chars
     - **instagram / facebook**: empty `caption` + `hashtags` placeholders (real generators land with the Meta uploader)
     - **pinterest**: empty `title`, `description`, `board`; `destination_url` pre-filled with `https://theluxedrawer.com/p/<slug>` (NOT the raw affiliate link — our page handles the redirect)
   - invokes `uploader/<platform>/upload.py` (or `meta/upload_<instagram|facebook>.py`) if it exists; otherwise prints `"<platform> not implemented"` and SKIPs
   - on success, parses `uploaded -> https://...` from stdout and writes `uploads.<platform>.uploaded = true`, `uploads.<platform>.url = <url>`
3. **Surface each row** the script prints (`<slug>\t<platform>\t<STATUS>\t<detail>`). The script auto-runs `npm run prebuild` in `website/` **before** the upload (the pre-flight) and emits `<slug>\t-\tOK\tproduct present on website; commit + push so /p/<slug> ships before viewers click`. No action needed for the regen itself.
4. **Do NOT** add `--overwrite` unless the user explicitly asks to re-upload.
5. **Deploy the website artifacts immediately — do NOT ask first.** After every successful upload, commit + push `website/` straight away (use `/commit-nextjs` or a direct `git add website/ && git commit && git push`). The YouTube description points viewers at `https://theluxedrawer.com/p/<slug>` — delaying the push means viewers 404. Standing approval: never ask before this commit/push, just do it. If `git status website/` is clean (prebuild was a no-op because the slug was already published), skip the commit silently — no need to notify the user. Same for unrelated dirty files outside `website/` — leave them alone.

## State machine (per product / per platform)

| `uploads.<platform>.uploaded` | uploader exists? | Action |
|---|---|---|
| `true` | — | SKIP (unless `--overwrite`) |
| `false` / missing | yes | uploader runs, manifest updated on success |
| `false` / missing | no  | SKIP with `"not implemented"` |

## Pinterest metadata (agent-authored)

Pinterest is a **search engine**, not a follow-feed. Distribution is driven by keyword match in title + description + alt_text, plus board topic relevance. Write copy for Pinterest *search*, not for ears.

Before running `scripts/upload_ad.py`, write `manifest["uploads"]["pinterest"]["metadata"]` with these five fields. The uploader will use them verbatim and resolve `board_id` from `category` automatically (auto-creating the board if it doesn't exist yet — see `uploader/pinterest/boards.json`).

```json
{
  "title":       "<≤100 chars, keyword-first>",
  "description": "<≤500 chars, keyword lead, then narrative, then 3-5 hashtags>",
  "alt_text":    "<≤500 chars, describe the image for visual search>",
  "category":    "<one of: skincare | makeup | fragrance | haircare | jewelry | clothing | home | beauty>",
  "link":        "https://theluxedrawer.com/p/<slug>"
}
```

### Title guidelines
- **Lead with the searchable keywords**, not the brand. Pinterest weights the first ~40 chars most.
- Pattern: `<Search Phrase> — <Brand> <Product Short>` or `<Benefit/Use Case> <Product Type>: <Brand>`.
- Bad (current templated output): `Cle De Peau Clarifying Cleansing Foam for Women`
- Good: `Luxury Japanese Foaming Cleanser for Glowy Skin — Cle de Peau`
- Good: `Best Anti-Aging Eye Cream for Dark Circles: Cle de Peau Supreme`
- ≤100 chars, no emojis, Title Case.

### Description guidelines
- **First sentence is keyword-dense**, not conversational. "Listen, your cleanser matters…" is *terrible* opening copy for Pinterest. Save the narrative voice for sentence two onward.
- Structure: `[keyword lead, ~80 chars] [narrative body, can reuse parts of script-raw-text] [Shop: <link>] [3-5 hashtags]`
- Example opening: `Luxury Japanese foaming cleanser for sensitive, glowy skin. Made by Cle de Peau Beauté in Japan — built around their Skin Intelligence research…`
- End with 3-5 relevant hashtags on their own line: `#skincareroutine #luxuryskincare #amazonfinds #jbeauty #skintok`
- ≤500 chars total.

### alt_text guidelines
- Describe **what's in the image** so Pinterest's visual search can match it.
- Pattern: `<Brand> <Product> — <image scene>. <Category context>.`
- Example: `Cle de Peau Clarifying Cleansing Foam bottle held by a woman in a soft-lit bathroom. Luxury Japanese skincare from Amazon.`
- ≤500 chars.

### Category guidelines
- Pick the single lowercase keyword that best buckets the product. The uploader maps it to a board (creating `Luxe Skincare`, `Luxe Makeup`, etc. on first miss).
- Use the product's `item-auxiliary-information.category` as a hint, but normalize to one of: `skincare`, `makeup`, `fragrance`, `haircare`, `jewelry`, `clothing`, `home`, `beauty`.

### `--regen-meta`
If the user asks to rewrite Pinterest copy for a product that already has metadata, you (the agent) author a fresh `uploads.pinterest.metadata` block following the rules above, save the manifest, then run `scripts/upload_ad.py --product <slug>` (no `--regen-meta` needed — your block is already there). `--regen-meta` only invokes the templated fallback and should NOT be used for Pinterest.

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
- **No content edits to the website.** The post-upload sync only regenerates `products.json` + images from the manifest. If the live site needs design changes, that's a separate task.

## Pinterest exit code is noisy (harmless)

`upload_ad.py` exits 1 whenever any platform row is FAIL — but today every product hits a benign FAIL on pinterest because that uploader doesn't exist yet and the metadata stub bails. **If the youtube row is OK, the upload succeeded** — read the rows, not the exit code. Don't re-run on this kind of failure.

## Cost note

YouTube Data API quota only — no paid-API spend. Future Meta/Pinterest uploaders should also stay quota-only (no paid-API spend).
