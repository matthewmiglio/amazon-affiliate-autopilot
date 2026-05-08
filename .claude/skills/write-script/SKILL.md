---
name: write-script
description: Author 15-20 second narration scripts (podcast / social-post tone, talking to one hidden listener) for Amazon affiliate products and apply them to product folders. Accepts a single slug, a comma-list, or `--all-needing` to target every product missing a script. Use when the user runs /write-script or asks to "write a script for X", "draft narration for these products", or similar.
---

# write-script

Draft narration scripts for one or more products, lint them, and write to `products/<slug>/script.txt` + the matching `manifest.json` `script-raw-text` field.

## Inputs

The user invokes `/write-script` with one of:

- A single slug: `/write-script lip-glorifier`
- A comma-list of slugs: `/write-script lip-glorifier, eye-contour-cream-supreme`
- The literal flag `--all-needing` to target every product where `script-raw-text` is empty.

If the user does not specify, ask once. Do not guess.

## Tone & content rules

These rules are NON-NEGOTIABLE. Lint enforces most of them.

1. **Length:** 45-60 words / 280-380 chars. Aim for ~50 words. The lint will fail outside this range.
2. **Voice:** conversational, talking to ONE hidden listener across a table — like sharing a tip with a friend. Not QVC. Not a press release. Read 1-2 existing `script.txt` files first to anchor the tone.
3. **NEVER STATE PRICE.** Amazon Associates Operating Agreement (see `docs/rules.md` HARD RULE 4) forbids exact price claims in audio/video — prices change hourly and a stale price can terminate the account. NEVER say "seventy-five dollars," "fifty bucks," "thirty cents," or any specific number-of-dollars phrase. Replace with vague tier language:
   - Cheaper end → "affordable", "shockingly affordable", "approachably priced"
   - Mid → "an everyday luxury", "fairly priced", "worth the spend"
   - High → "splurge", "investment-tier", "a serious investment", "true luxury"
   The lint hard-fails on `$`, `dollars`, `bucks`, `cents`.
4. **TTS-safe numbers:** spell out any remaining digits (years, SPF, count). E.g. `1982` → "nineteen eighty-two", `SPF 27` → "SPF twenty-seven", `60 count` → "sixty count". Lint hard-fails on any `\d`.
5. **Grounded claims only:** every fact must trace to the manifest's `item-auxiliary-information.description`, brand, or product. Do NOT invent stats, percentages, "clinically proven", or efficacy claims unless the description literally says so. Price stays in the manifest only — never in the script.
6. **Required beats, in roughly this order:**
   - Hook (a question, callout, or "okay, listen…")
   - Brand + product name (natural, can be partial — e.g. "the Clé de Peau Eye Contour Cream Supreme")
   - One concrete differentiator pulled from the description
   - Optional vague price-tier line ("affordable", "a serious splurge") — NEVER an exact figure
   - CTA: must contain the literal phrase **"Tap the link"** — recommended ending: "Tap the link to grab it on Amazon."
7. **Skip-if-present:** if `manifest["script-raw-text"]` is non-empty, skip unless the user passes `--overwrite`. Surface every skip in the summary.

## Workflow

1. **Resolve target slugs.**
   - For `--all-needing`: run `python scripts/status.py --needs-script --json` and parse the JSON list.
   - For an explicit slug list: validate each `products/<slug>/manifest.json` exists.
2. **Read tone references.** Read 1-2 existing populated scripts (e.g. `products/concealer-spf-27/script.txt`) into context to anchor voice. Do this once, not per product.
3. **Read each target's manifest** for brand, product, price, description. Use `ctx_execute` (shell + node) if reading >3 manifests, to keep raw context small — print only the compact `{slug, brand, product, price, description}` JSON.
4. **Draft scripts.** Author the full set in one pass. Build a `{slug: script_text}` dict.
5. **Stage to a temp JSON file.** Write the dict to `scripts/_pending_scripts.json` via the Write tool.
6. **Apply.** Run `python scripts/apply_scripts.py scripts/_pending_scripts.json` (add `--overwrite` if requested). Delete `_pending_scripts.json` after success.
7. **Lint.** Run `python scripts/script_lint.py <slug> [<slug>...]` on what was just written. If anything fails, redraft only the failing slugs and re-apply with `--overwrite`. Do NOT ship failing scripts.
8. **Report.** Print: `<N> scripts written, <M> skipped, all passing lint.` Per-slug one-liners only on failure.

## Helper scripts (in `scripts/`)

- `status.py --needs-script --json` — list of slugs missing scripts as JSON array.
- `apply_scripts.py <json> [--overwrite]` — atomically writes both `script.txt` and the manifest field per slug. Skips already-populated unless `--overwrite`.
- `script_lint.py [slugs...]` — checks word count, char count, no `$`, no digits, contains "Tap the link". Exits non-zero on failure.

## Out of scope

- No audio generation — that's the narration tool's job.
- No description, lifestyle image, or main image authoring — separate skills.
- Don't touch the source scrape under `Downloads/`.
- Don't rewrite an existing passing script just because you're processing the slug — honor `--overwrite` strictly.

## Re-runs

Safe to re-run. The skip-if-present rule + lint mean re-runs are idempotent: only failing or missing scripts get rewritten.
