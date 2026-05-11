---
name: write-script
description: Author 15-20 second narration scripts (podcast / social-post tone, talking to one hidden listener) for Amazon affiliate products and apply them to product folders. Accepts a single slug, a comma-list, or `--all-needing` to target every product missing a script. Use when the user runs /write-script or asks to "write a script for X", "draft narration for these products", or similar.
---

# write-script

Draft narration scripts for one or more products, lint them, and write them into `products/<slug>/manifest.json` under the `script-raw-text` field. The manifest is the single source of truth — no sibling `script.txt` is created.

## Inputs

The user invokes `/write-script` with one of:

- A single slug: `/write-script lip-glorifier`
- A comma-list of slugs: `/write-script lip-glorifier, eye-contour-cream-supreme`
- The literal flag `--all-needing` to target every product where `script-raw-text` is empty.

If the user does not specify, ask once. Do not guess.

## Tone & content rules

These rules are NON-NEGOTIABLE. Lint enforces most of them.

1. **Length:** 45-60 words / 280-380 chars. Aim for ~50 words. The lint will fail outside this range.
2. **Voice & framing:** speaker is a relatable woman creator, but the **hidden listener is a man** being recommended a women's product as a gift for a woman in his life. Frame every script as "buy this for your <recipient>" — never "you should try this yourself." This pivot is intentional and audience-driven (YouTube analytics show ~80% male viewers despite the female-skewed catalog). Tone is conversational, like a sister or female friend telling him what to actually get. Not QVC. Not a press release. Read 1-2 existing populated `manifest.json["script-raw-text"]` values first to anchor the tone (e.g. `defining-lip-liner`, `discovery-skincare-kit-7-piece-...`, `enzyme-cleanser-...`).
   - **Recipient pool — ONLY `your girlfriend` or `your wife`. Nothing else.** Do not write "your mom / sister / aunt / niece / fiancée / stepmom / cousin / female bestie / female roommate / female coworker" or "the woman in your life." The audience is partnered men shopping for their partner; family-recipient framings underperformed this segment. Mix girlfriend and wife roughly evenly across a batch — match wife to the longer-commitment / higher-tier products (anniversary fragrance, prestige anti-aging) and girlfriend to the trend-led / younger-skewing products (TikTok cult makeup, K-beauty drops).
   - **Recipient must appear in the FIRST sentence.** Open with `Your girlfriend …` or `Your wife …` (or a hook line immediately followed by `Buy her …`). Do not bury the recipient mid-script. Example openers: `Your wife has been window-shopping serums all month.` / `Your girlfriend keeps borrowing her friends' glosses.` / `Your wife mentioned wanting something fancier than drugstore.`
   - **Hook pool — vary across the batch:** front-loaded recipient observation (`Your girlfriend has been …`), recipient-stated complaint callout (`Your wife mentioned …`), "Buy her X" command, "PSA —", "Real talk —". Do NOT open every script with "Hey."
   - **Occasion anchors — ALLOWED:** birthday, anniversary, just-because, apology gift, "the next holiday", big-gesture, small-thoughtful, add-on gift. **FORBIDDEN — no seasonal/holiday references:** Christmas, Christmases, Mother's Day, Valentine's, stocking-stuffer, Easter, holiday-season. If you want to gesture at an upcoming gift moment without naming a date, say "the next holiday" or "her birthday is coming." Year-evergreen only — these videos run on YouTube indefinitely.
   - **Starter-intro toolkit (curated, ~36 frames).** Use these as inspiration for the opening 1-2 sentences. Rotate across a batch — never reuse the same frame in adjacent slugs. Frames marked with `{placeholder}` need the slug-specific token filled in (trait, brand, complaint, category, product, item, occasion).
     1. "If your girlfriend is the {trait} girly, she already wants this."
     2. "You haven't heard of {brand}, but every woman has — it's the {category} gold standard."
     3. "Want your wife coming home asking 'where did you find this'? Buy her {product}."
     4. "Your girlfriend complains about {complaint} all the time. This is the fix."
     5. "The only {category} gift you cannot get wrong — even if you have no idea what you're doing."
     6. "Her birthday is two weeks out and you still have nothing. Lock this in."
     7. "Every creator she follows on TikTok uses this. Get it for her, take the credit."
     8. "Want a gift she actually tells her friends about? Buy her {product}."
     9. "Stop overthinking the gift. This is the answer."
     10. "Her {item} has seen better days. Replace it before she does."
     11. "Is your girlfriend mad at you right now? Buy her this."
     12. "Your girlfriend will not splurge on herself — that's where you come in."
     13. "Be the boyfriend she brags about — buy her this."
     14. "Skip the flowers. Buy her {product} instead."
     15. "Your wife has been rotating the same three {category} since you met. End that."
     16. "Want a gift she actually uses every day? Buy her {product}."
     17. "The 'I-paid-attention' gift, without you having to say it."
     18. "Even the women who have everything do not have this yet."
     19. "{occasion} is five days away and you still haven't bought her anything?"
     20. "Show me a guy who buys {category} and I'll show you a happy girl."
     21. "Want her texting you a mirror selfie wearing this? Buy {product}."
     22. "Your wife pretends she doesn't want gifts. She does. Get her this."
     23. "Your wife is hard to shop for. This is the cheat code."
     24. "Your girlfriend sees this on her FYP every day. Let her have it."
     25. "Your girlfriend will brag about this to every friend she has — get her one worth bragging about."
     26. "Your wife is having a week. Drop this on her desk."
     27. "Your wife stopped asking for things years ago. Surprise her."
     28. "Your wife is the type who quietly notices everything. Notice her back."
     29. "Want to be the guy whose girlfriend recommends him to her single friends?"
     30. "Does your wife ask for things directly? Didn't think so."
     31. "Tired of guessing wrong on your wife's gifts?"
     32. "Most boyfriends don't know this brand. The ones who do, win."
     33. "Real talk — you have no idea what {category} does. Doesn't matter. Your girlfriend does."
     34. "Hot take: stop asking your wife what she wants. Just buy this."
     35. "Your wife's FYP is about to recommend this. Beat the algorithm."
     36. "Bad at gifts? Same. This is the cheat."
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
2. **Read tone references.** Read 1-2 existing populated `script-raw-text` values from manifests (e.g. `products/concealer-spf-27/manifest.json`) into context to anchor voice. Do this once, not per product.
3. **Read each target's manifest** for brand, product, price, description. Use `ctx_execute` (shell + node) if reading >3 manifests, to keep raw context small — print only the compact `{slug, brand, product, price, description}` JSON.
4. **Draft scripts.** Author the full set in one pass. Build a `{slug: script_text}` dict.
5. **Stage to a temp JSON file.** Write the dict to `scripts/_pending_scripts.json` via the Write tool.
6. **Apply.** Run `python scripts/apply_scripts.py scripts/_pending_scripts.json` (add `--overwrite` if requested). Delete `_pending_scripts.json` after success.
7. **Lint.** Run `python scripts/script_lint.py <slug> [<slug>...]` on what was just written. If anything fails, redraft only the failing slugs and re-apply with `--overwrite`. Do NOT ship failing scripts.
8. **Report.** Print: `<N> scripts written, <M> skipped, all passing lint.` Per-slug one-liners only on failure.

## Helper scripts (in `scripts/`)

- `status.py --needs-script --json` — list of slugs missing scripts as JSON array.
- `apply_scripts.py <json> [--overwrite]` — writes the manifest's `script-raw-text` field per slug. Skips already-populated unless `--overwrite`.
- `script_lint.py [slugs...]` — checks word count, char count, no `$`, no digits, contains "Tap the link". Exits non-zero on failure.

## Out of scope

- No audio generation — that's the narration tool's job.
- No description, lifestyle image, or main image authoring — separate skills.
- Don't touch the source scrape under `Downloads/`.
- Don't rewrite an existing passing script just because you're processing the slug — honor `--overwrite` strictly.

## Re-runs

Safe to re-run. The skip-if-present rule + lint mean re-runs are idempotent: only failing or missing scripts get rewritten.
