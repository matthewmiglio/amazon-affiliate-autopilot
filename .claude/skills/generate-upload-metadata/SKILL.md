---
name: generate-upload-metadata
description: Author per-platform upload copy (title, caption, description, hashtags, etc.) for an Amazon affiliate product across all 5 platforms (YouTube, Instagram, Facebook, Pinterest, X), drawing tag pools from `data/tags_mapping.json` and brand voice + narration angle from the manifest. Writes the metadata into `products/<slug>/manifest.json` under `uploads.<platform>.metadata`. Use when the user runs /generate-upload-metadata, says "write upload copy for X", "draft captions", or supplies a slug and asks for the pre-upload metadata step.
allowed-tools: Read, Glob, Bash, Edit, Write
---

# generate-upload-metadata

## What this skill does

For a given product slug (or all slugs missing metadata), author Claude-quality upload copy for **every** configured platform and write it into the product manifest. Once this runs, `/upload-ad` can proceed without falling back to templated copy.

This skill replaces the previous templated `_gen_<platform>()` functions in `scripts/upload_ad.py`. There is no script that runs Claude here — Claude (you) author the copy directly, using the inputs below.

## Inputs

`/generate-upload-metadata <target>` where `<target>` is one of:

- A single slug: `/generate-upload-metadata concealer-spf-27`
- A comma-list: `/generate-upload-metadata slug-a, slug-b`
- A full path to a product folder
- The literal flag `--all-needing` — every product whose manifest is missing metadata for any platform

If the user provides nothing, ask once. Don't guess.

Reads (per slug):
- `products/<slug>/manifest.json`:
  - `item-auxiliary-information` (brand, product, category, asin, affiliate-link)
  - `script-raw-text` (the narration, primary signal for the video's *angle*)
  - `video-prompt` (optional; useful for visual context but secondary)
- `data/tags_mapping.json` (platform-keyed tag pools; never invent tags outside these pools)

Writes:
- `products/<slug>/manifest.json` -> `uploads.<platform>.metadata` for all 5 platforms

## Workflow

1. **Resolve the product folder.** Read its `manifest.json`.
2. **Refuse to author** if `script-raw-text` is empty or `item-auxiliary-information` is missing the brand/product/affiliate-link fields. Tell the user what's missing and stop.
3. **Read `data/tags_mapping.json`** once into memory. Five keys: `youtube`, `instagram`, `facebook`, `pinterest`, `x`. Each is a flat list of tags/keywords.
4. **For each platform**, author the metadata block per the platform's rules below. Pick tags from that platform's pool by relevance to the product + narration angle, not at random. Never invent tags outside the pool.
5. **Save the manifest** with `uploads.<platform>.metadata` populated for all 5 platforms (`youtube`, `instagram`, `facebook`, `pinterest`, `x`). Preserve existing `uploaded` / `url` fields on each block — only the `metadata` sub-key changes.
6. **Print a confirmation line** per platform: `wrote uploads.<platform>.metadata -> products/<slug>/manifest.json (<N> tags, <M> chars)`.

If the manifest already has metadata for a platform, **overwrite it** (this skill always produces the canonical copy). If the user wants to preserve hand-edits they can `git stash` first; we don't try to merge.

## Per-platform rules

### YouTube (Shorts)

```jsonc
"youtube": {
  "title":       "<≤100 chars, opens with searchable hook, ends with 2-3 hashtags from the YT pool>",
  "description": "<see template below>",
  "tags":        ["<8-10 picked from the YT pool, no `#` prefix>"],
  "category":    "22",
  "privacy":     "public",
  "hashtags":    ["<3-4 picked from the YT pool, include `#shorts` always>"]
}
```

- **Title** ≤100 chars. Pattern: `<Hook or Benefit> <Product Short> <#tag> <#tag>`. Always include `#shorts` somewhere in title or hashtags.
- **Description** template:
  ```
  Shop on theluxedrawer.com: https://theluxedrawer.com/p/<slug>

  {narration body — can paraphrase the script for flow}

  {hashtags space-separated} #shorts
  ```
  Trailing spaces on each block separator stay (YouTube Shorts collapses newlines without inserting spaces).
- **Tags** are bare keywords (no `#`), used by YT's search index. Strip `#` from pool entries when copying into the `tags` array.
- **Affiliate funnel:** description leads with `https://theluxedrawer.com/p/<slug>`, NEVER the raw `amzn.to` link. Our site server-side-redirects to Amazon.

### Instagram (Reels)

```jsonc
"instagram": {
  "caption":  "<see template below>",
  "hashtags": ["<3-5 picked from the IG pool>"]
}
```

- **Caption** template:
  ```
  {hook line — restate the punchline from the narration in ~8 words}

  {1-2 sentence body, can paraphrase the script — IG captions are read, not heard}

  🛒 https://theluxedrawer.com/p/<slug>

  As an Amazon Associate I earn from qualifying purchases. #ad

  {hashtags space-separated}
  ```
- Max 5 hashtags. IG algorithm down-weights captions with 10+ hashtags now; under-5 reads as confident.
- The `🛒` emoji is required; it visually separates the link from the body.
- The `#ad` disclosure is mandatory (FTC + Meta branded-content policy).
- Pick hashtags that match the product type *and* the narration's angle. A skincare product with a "Korean dupe" angle should pull `#kbeauty` + `#skintok` even if `#beauty` would technically work.

### Facebook (Reels)

```jsonc
"facebook": {
  "caption":  "<see template below>",
  "hashtags": ["<2-3 picked from the FB pool>"]
}
```

- Facebook captions are nearly identical to Instagram captions but with two adjustments:
  - **Slightly more explanatory** — FB audience skews older, less context from short-form culture. Spell out e.g. "Korean cushion compact" instead of "K-beauty cushion."
  - **Fewer hashtags** (2-3 max). FB hashtags barely affect distribution; don't clutter.
- Same template structure (hook → body → 🛒 link → disclosure → hashtags).

### Pinterest

Pinterest is a **search engine**, not a follow-feed. Distribution is driven by keyword match in title + description + alt_text, plus board topic relevance. Write copy for Pinterest *search*, not for ears.

```jsonc
"pinterest": {
  "title":       "<≤100 chars, keyword-first>",
  "description": "<≤500 chars, keyword lead, then narrative, then 3-5 hashtags>",
  "alt_text":    "<≤500 chars, describe the image for visual search>",
  "category":    "<one of: skincare | makeup | fragrance | haircare | jewelry | clothing | home | beauty>",
  "link":        "https://theluxedrawer.com/p/<slug>"
}
```

**Title guidelines**
- **Lead with the searchable keywords**, not the brand. Pinterest weights the first ~40 chars most.
- Pattern: `<Search Phrase> — <Brand> <Product Short>` or `<Benefit/Use Case> <Product Type>: <Brand>`.
- Bad: `Cle De Peau Clarifying Cleansing Foam for Women`
- Good: `Luxury Japanese Foaming Cleanser for Glowy Skin — Cle de Peau`
- Good: `Best Anti-Aging Eye Cream for Dark Circles: Cle de Peau Supreme`
- ≤100 chars, no emojis, Title Case.

**Description guidelines**
- **First sentence is keyword-dense**, not conversational. "Listen, your cleanser matters..." is *terrible* opening copy for Pinterest. Save the narrative voice for sentence two onward.
- Structure: `[keyword lead, ~80 chars] [narrative body, can reuse parts of script-raw-text] [Shop: <link>] [3-5 hashtags]`
- Example opening: `Luxury Japanese foaming cleanser for sensitive, glowy skin. Made by Cle de Peau Beaute in Japan, built around their Skin Intelligence research.`
- End with 3-5 relevant hashtags on their own line. Pull hashtags AND keyword phrases from the Pinterest pool (the pool contains both).
- ≤500 chars total.

**alt_text guidelines**
- Describe **what's in the image** so Pinterest's visual search can match it.
- Pattern: `<Brand> <Product> — <image scene>. <Category context>.`
- Example: `Cle de Peau Clarifying Cleansing Foam bottle held by a woman in a soft-lit bathroom. Luxury Japanese skincare from Amazon.`
- ≤500 chars.

**Category guidelines**
- Pick the single lowercase keyword that best buckets the product. The uploader maps it to a board (creating `Luxe Skincare`, `Luxe Makeup`, etc. on first miss).
- Use the product's `item-auxiliary-information.category` as a hint, but normalize to one of: `skincare`, `makeup`, `fragrance`, `haircare`, `jewelry`, `clothing`, `home`, `beauty`.

**Link:** always `https://theluxedrawer.com/p/<slug>`, not the raw `amzn.to` link.

### X (Twitter)

```jsonc
"x": {
  "text":            "<≤280 chars total, includes the destination_url inline>",
  "destination_url": "https://theluxedrawer.com/p/<slug>"
}
```

- **One tweet, ≤280 chars including the URL.** X counts the URL as 23 chars regardless of actual length (t.co shortening).
- Structure: `{punchy hook line — 1-2 sentences, max ~120 chars} {2-3 hashtags from X pool} {URL}`
- Example: `Korean cushion compact with SPF 50, dewy buildable finish. The one I throw in my bag every day. #amazonfinds #kbeauty https://theluxedrawer.com/p/<slug>`
- Use the `destination_url` field as well — the uploader uses it for click tracking even though it's also embedded in the text.
- Affiliate funnel: NEVER the raw `amzn.to` URL, always `theluxedrawer.com/p/<slug>`.

## Tag selection guidance

- Tags MUST be drawn from the platform's pool in `data/tags_mapping.json`. Don't invent.
- Pick tags that fit *both* the product AND the narration's angle. A makeup product whose narration angle is "Korean-style dewy finish" should pull `#kbeauty` even though it's in the makeup category.
- Don't repeat the same hashtag across more than ~half of your picks — diversify.
- If the pool is missing an obvious tag the user clearly needs, surface it to them (e.g. "I noticed you don't have `#perfumelover` in the X pool — should I add it?"). Don't silently invent.

## Brand voice + niche reminder

Soft Luxe Daily / The Luxe Drawer is a **beauty + lifestyle affiliate** channel. Narration is podcast-tone, conversational, talking to one hidden listener. The same AI host appears in every video. Categories covered:

- skincare, makeup, fragrance, haircare, jewelry, clothing, home, beauty

The host is positioned as a *recommender*, not a marketer. Captions should sound like a friend texting you about something they like. Disclosure (`#ad` / "As an Amazon Associate...") is non-negotiable but the *tone* around it stays casual.

## --all-needing semantics

Iterate every `products/<slug>/manifest.json`. A product is "needing" if ANY of the 5 platform metadata blocks fails the completeness check:

- `youtube`: `title` empty
- `instagram`: `caption` empty
- `facebook`: `caption` empty
- `pinterest`: `title` OR `description` empty
- `x`: `text` empty

For each needing product, run the full Workflow (above). Print one line per platform per slug.

Already-uploaded platforms (`uploads.<platform>.uploaded == true`) still get their metadata re-authored. That metadata won't be re-uploaded, but having canonical copy in the manifest is the source of truth (e.g. for status reporting, future re-uploads under `--overwrite`, analytics).

## Existing helpers (do not duplicate)

- `data/tags_mapping.json` — single source of truth for hashtag/keyword pools per platform.
- `scripts/upload_ad.py::_is_complete(platform, metadata_block)` — validates whether a metadata block is populated. Use the SAME shape it expects (don't add/rename keys).

## Out of scope

- **Don't upload anything.** That's `/upload-ad` (the next pipeline step).
- **Don't author scripts or video prompts.** Those are `/write-script` and `/generate-video-prompt`.
- **Don't edit `data/tags_mapping.json` silently.** If the pool is missing tags, tell the user; don't auto-extend.
- **Don't deduplicate hashtags across platforms.** Pinterest can reuse #beauty even if YouTube also uses it.
- **Don't translate / localize.** English-only for now.

## Don'ts

- Don't write captions without first reading `script-raw-text` from the manifest.
- Don't use the raw Amazon `amzn.to` link in any platform's copy; always `https://theluxedrawer.com/p/<slug>`.
- Don't put the `#ad` disclosure on Pinterest or X — they're handled by platform policy differently. Keep it on IG/FB/YouTube (where Meta + FTC enforce branded-content tags).
- Don't write more than 5 hashtags on IG, more than 3 on FB, more than 5 on Pinterest's description tail.
- Don't omit the `🛒` emoji on IG/FB captions; it's the visual link marker.
- Don't author metadata for any platform NOT in this skill (no TikTok, no Threads, etc. until they're wired into `uploads`).
