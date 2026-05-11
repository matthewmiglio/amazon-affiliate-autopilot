---
name: generate-video-prompt
description: |
  Author the AI video-gen prompt that animates a product's existing starting-pic into a 15–20 second talking-head UGC ad clip aligned with its narration script. Reads the product folder's `manifest.json` (specifically `script-raw-text` and `starting-pic-path`), produces one concise prompt suitable for a Sora-class image-to-video tool, and writes it back to `manifest.json` under the `video-prompt` key. Use when the user runs `/generate-video-prompt`, says "write a video prompt for X", "draft the video animation prompt", or supplies a product folder and asks for the next-stage video prompt.
allowed-tools: Read, Glob, Bash, Edit, Write
---

# /generate-video-prompt

## What this skill does

Given a product folder (e.g. `products/<slug>/`), produce a single video-generation prompt that animates the product's existing `starting-pic.png` (the starting frame produced by `/generate-starting-image`) into a short UGC-style talking-head clip lip-synced to the existing `narration.mp3` and `script-raw-text`.

The output is a single ~80–120 word paragraph that the user pastes into a Sora-class first-frame-to-video tool (Sora 2, Runway Gen-3, Luma Dream Machine, Pika, Kling, etc.) along with the lifestyle image and (where supported) the narration audio. The skill ALSO writes the prompt back into the product's `manifest.json` under the `video-prompt` key so we don't have to re-author it next time.

## Required inputs

When invoked, look for / ask for:
1. **Product folder or slug** (required) — accepts:
   - an absolute path like `C:\My_Files\my_programs\amazon-affiliate\products\<slug>`
   - a repo-relative path like `products/<slug>` or `assets/products/<slug>`
   - a bare slug — resolve under `products/` first; if not found, try `assets/products/`
2. **Optional gesture override** — the user can pass a one-line gesture cue ("she taps the cap on the punchline") that the skill folds into the gesture beats.

Verify the folder exists and contains both `manifest.json` and the file referenced by its `starting-pic-path`. If `script-raw-text` is empty or `starting-pic-path` is missing/blank/nonexistent, stop and ask the user — don't fabricate.

## HARD RULES (carry forward from /generate-starting-image)

These describe the clip — apply to every prompt:

1. **One first-frame, one shot.** No scene changes, no cuts, no camera moves between rooms. The animation continues directly from `starting-pic.png`. Keep the same woman, same outfit, same hair, same room, same mic placement, same lighting.
2. **She faces camera.** Body angle stays roughly straight-on / slight 3/4 toward camera, just like in the starting frame. NEVER profile, NEVER over-the-shoulder, NEVER away.
3. **Mic stays in front of her or clipped to her collar** — same placement as in the starting frame. Do not have the mic disappear.
4. **She HOLDS the product. She does NOT use it.** Cap on, lid on, kit closed. No applying, no swiping, no spraying, no dispensing, no opening the box. She may *lift it slightly*, *tilt it toward camera*, or *re-grip with the other hand* — never use it.
5. **Only one product on screen.** The product visible in `starting-pic.png` is the only product. Don't introduce a second bottle, a swatch, or a kit fan-out.
6. **Real-photo realism**, never illustrated, anime, painted, or 3D-render look.
7. **9:16 vertical**, ~15–20 seconds, lip-synced to the narration.
8. **Pretty face + done makeup**, polished even in casual outfits. Never "tired" / "no-makeup".

## Variation discipline

The starting frame and script are fixed; what varies between products is the **gesture beat track** the skill picks based on the script's emphasis points. Each prompt should specify 2–4 micro-motion beats keyed to the script's natural moments:

- the brand-name beat — small upward lift of the product when she names the brand
- the claim beat — slight head tilt + soft smile at the product's main promise (e.g. "16-hour wear", "glassy skin", "Korean dupe")
- the punchline beat — a single nod or a beat-of-stillness on the closing line
- the close beat — a soft outward glance + relaxed exhale on the final word, mic still in frame

Always include subtle base motion: natural blinks, micro head bob, occasional subtle weight shift, breathing. Never robotic stillness, never frantic.

Pick gesture beats that line up with the actual script content — quote the trigger phrase in the prompt so the video model knows when each beat lands.

## Output template

Produce ONE paragraph, ~80–120 words. Format:

```
Animate this first-frame image into a {15–18}-second 9:16 vertical UGC talking-head clip.
The same woman stays in the same room, same outfit, same lighting, same mic placement —
no scene change, no camera cut, no zoom. She is facing camera and speaking the following
narration with natural lip-sync: "{full script-raw-text}".
She is HOLDING the {product description} (cap on, NOT using it). Subtle base motion
throughout: natural blinks, gentle head bob, light breathing, an occasional small weight
shift. Specific gesture beats:
- on "{brand-name trigger phrase}" — {gesture beat}
- on "{claim trigger phrase}" — {gesture beat}
- on "{closing trigger phrase}" — {gesture beat}
Real-photo realism, NOT illustrated. Hair and makeup stay polished. Same woman as the
starting frame — do not change her face, hair, skin tone, or eyebrows.
```

Keep it under ~120 words. One paragraph. No extra preamble, no caption copy, no hashtags.

## Workflow

1. Resolve the product folder. Read `manifest.json`.
2. Pull `script-raw-text` (string) and `starting-pic-path` (relative file in the folder). Validate both — non-empty + image file exists. If either fails, tell the user what's missing and stop.
3. Pull the product description from `item-auxiliary-information` (`brand`, `product`, `category`) so the prompt can name the product naturally (e.g. "the closed Charlotte Tilbury Pillow Talk Dreams Come True 15-piece makeup kit").
4. Identify 2–4 trigger phrases from the script — one for the brand, one for the main claim, one for the close. Map each to a gesture beat from the variation list (or the user's override).
5. Compose the paragraph from the template.
6. Show the prompt to the user.
7. Use `Edit` to write the prompt back into `manifest.json` under the `video-prompt` key. Preserve key order (`video-prompt` sits between `script-raw-text` and `commission-percentage`). If the key doesn't exist yet, add it. If it already has content, ask before overwriting.
8. Confirm the manifest update with a short status line: `wrote video-prompt → products/<slug>/manifest.json (XX chars)`.

## Out of scope

- **Don't author the script.** That's `/write-script`. If `script-raw-text` is missing, tell the user to run that first.
- **Don't author or regenerate the starting frame.** That's `/generate-starting-image`. If `starting-pic.png` is missing, tell the user.
- **Don't emit a separate `script.txt` or `video-prompt.txt`** — `manifest.json` is the single source of truth. Never write sibling text files.
- **Don't render or invoke the video tool yourself.** This skill produces the prompt only. The user runs the video model.

## Examples

### Skincare, Korean cushion compact

`script-raw-text`: "Have you tried a Korean cushion compact yet? The AMOREPACIFIC Color Control Cushion Compact has SPF 50 plus, a buildable dewy finish, and it's the one I throw in my bag every morning. Glassy skin, ten seconds. Link's in the description."

```
Animate this first-frame image into a 16-second 9:16 vertical UGC talking-head clip.
The same woman stays in the same room, same outfit, same lighting, same mic placement —
no scene change, no camera cut, no zoom. She is facing camera and speaking the following
narration with natural lip-sync: "Have you tried a Korean cushion compact yet? The
AMOREPACIFIC Color Control Cushion Compact has SPF 50 plus, a buildable dewy finish,
and it's the one I throw in my bag every morning. Glassy skin, ten seconds. Link's in
the description."
She is HOLDING the closed AmorePacific Color Control Cushion Compact (lid shut, NOT
using it). Subtle base motion throughout: natural blinks, gentle head bob, light
breathing, occasional small weight shift. Specific gesture beats:
- on "AMOREPACIFIC" — small upward lift of the compact toward camera
- on "Glassy skin, ten seconds" — slight head tilt + soft smile
- on "Link's in the description" — single soft nod, relaxed exhale
Real-photo realism, NOT illustrated. Hair and makeup stay polished. Same woman as the
starting frame — do not change her face, hair, skin tone, or eyebrows.
```

## Don'ts

- Don't introduce camera cuts, zooms, scene changes, or B-roll inserts.
- Don't have her open, apply, dispense, or use the product mid-clip.
- Don't change outfit, room, lighting, or mic placement from the first frame.
- Don't add a second product, a swatch, a hand close-up insert, or a styled shelf.
- Don't write the prompt without first reading `script-raw-text` from the manifest.
- Don't overwrite an existing non-empty `video-prompt` without asking.
- Don't emit a sibling `video-prompt.txt` or `script.txt` — `manifest.json` is canonical.
