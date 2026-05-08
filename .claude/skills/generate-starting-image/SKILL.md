---
name: generate-starting-image
description: |
  Build an image-gen prompt that places the user's recurring "product girl" reference into a unique podcast / UGC ad scene holding a specific product. The user submits the reference girl image AND a product image AND invokes /generate-starting-image; this skill outputs a single ready-to-paste prompt for ChatGPT image gen (or any T2I tool) that varies the girl's outfit, the camera angle, the room, and small staging details so consecutive generations don't feel templated. Works for jewelry, skincare, haircare, fragrance, cosmetics, apparel, and home goods. Use when the user says "/generate-starting-image", "generate starting image", "put my girl in a podcast scene with this product", or supplies a product image and asks for a podcast/demo composite.
allowed-tools: Read, Glob, Bash
---

# /generate-starting-image

## What this skill does

The user has a recurring "product girl" character (face + hair + styling already established in a reference image they re-upload each chat). They also have a product image (Amazon screenshot, hero PNG, packshot). They want a single unified output image of the girl in a **realistic podcast / UGC ad scene** holding the product so that the frame can be used as the opening shot of a Reel/Short ad.

The mood is **relatable creator**, not glossy magazine. Lived-in bedroom desk, clean kitchen counter, simple ring-light at home, golden-hour balcony — NOT luxury loft, NYC skyline, marble brand studio, library nook, walk-in-closet vanity, white clinical seamless. If it looks like a TV commercial set, it's wrong.

This skill produces the **prompt** for that image. The user pastes the prompt into ChatGPT alongside their two reference images.

## Required inputs

When invoked, look for / ask for:
1. **product image path** (required) — e.g. `products/<slug>/main.png` or `assets/products/<slug>/main.png`. If the user didn't provide one, ask for it.
2. **product type** (optional, infer if missing) — `jewelry`, `skincare`, `haircare`, `fragrance`, `cosmetics`, `apparel`, `home`.
3. **tone hint** (optional) — see § Tone presets.

Confirm the file exists before generating the prompt.

## HARD RULES — these never change, no matter what

These come from real user feedback. Violations break the look. Apply them to every prompt you write:

1. **She is facing the camera.** Body angle is `straight-on`, `slight 3/4 left toward camera`, or `slight 3/4 right toward camera`. **NEVER** profile, NEVER over-the-shoulder, NEVER back-to-camera, NEVER glancing-away. Her eyes are on (or close to) the lens.
2. **The mic is in front of her — between her and the camera — OR she's holding it.** Possible setups:
   - desktop podcast mic on a short stand or low boom arm in front of her chest, pointed at her mouth
   - clip-on lapel mic clipped to her collar / hoodie zipper, visible in the frame
   - small handheld wireless mic she's holding to her chin
   The mic must read in-frame as part of "she is recording right now." NEVER place the mic behind her, off to the side out of frame, or only "implied."
3. **She is HOLDING the product. She is NOT using it.** No applying, no swiping, no dispensing, no mid-press, no dropper-drop, no patting cream onto her face, no twisting open with mid-stroke, no wand-on-lash-line, no pump-mid-foam. Just holding the bottle / jar / case / tube / bullet **label-out** at chest height with one hand or two, like she's showing it to her audience. Cap stays on. Lid stays on. Bottle stays sealed.
4. **One product, never multiples.** Never "kit fanned out", never "set arranged on the desk", never "a shelf of bottles styled behind". The product image you were given is the one product in frame. Even if the product itself is a "kit", show the closed kit/box label-out — don't open it and spread it out.
5. **The scene is a real creator's room or casual everyday spot.** Bedroom desk corner, kitchen counter, couch with ring-light, balcony at golden hour, simple home office desk. NOT: luxury loft, library nook, walk-in-closet vanity, marble lab studio, NYC skyline windows, velvet evening glam set.
6. **Pretty face + done makeup, always.** Even in `bummy-casual` / `bathrobe` / `gym-clean`, the face is still polished. Never write "tired", "no-makeup", "barefaced", "messy face".
7. **Real-photo realism**, never illustrated, anime, painted, or 3D-render look.
8. **9:16 vertical framing** (Reel/Short source frames).

## Variation discipline (rotate, don't repeat)

You ALWAYS face the camera and you ALWAYS hold the product label-out (per the hard rules). Variety comes from these axes:

| Axis | Options |
|---|---|
| **Body angle** | straight-on · slight 3/4 left toward camera · slight 3/4 right toward camera |
| **Camera angle** | eye-level chest-up · slight low-angle chest-up · slight high-angle face+product · medium close-up tight on face & product |
| **Hold style** | one hand at chest label-out · two hands at chest cradling label-out · one hand raised to face level showing label · resting on the desk in front of the mic with hand on top of it |
| **Outfit** | see § Outfit options |
| **Room** | see § Room options |
| **Mic style** | desktop boom arm in front · short-stand condenser in front · clip-on lapel on collar · small handheld at chin |

Pick a combination the user hasn't recently used. If unsure, choose at random — but **NEVER** the default "straight-on, eye-level chest-up, one-hand label-out, denim-tee + home-bedroom" combo two calls in a row.

## Outfit options

Always describe specifically — fabric, fit, color. Pretty face + done makeup is always-on.

| Outfit | Description |
|---|---|
| `bummy-casual` | oversized cream hoodie or vintage-band tee + messy half-bun, no jewelry, just-rolled-out-of-bed-but-glowing |
| `loungewear` | matching ribbed-knit lounge set (oat or sage), soft cardigan over shoulders, hair down |
| `bathrobe` | plush ivory waffle bathrobe with terry collar, silk hair towel turban OR towel-dried damp hair, no jewelry |
| `silk-pajama` | navy or cream silk pajama set with piping, hair smooth and down |
| `gym-clean` | matte-black cropped sports bra + zip-up half-open + high-rise leggings, slicked-back ponytail, dewy gym-glow finish |
| `denim-tee` | well-fitting white tee tucked into vintage straight-leg denim, gold hoops, hair loose |
| `casual-cardigan` | simple cream tee + soft oat cardigan + gold hoops, hair in low loose pony |
| `crewneck-sweater` | oversized cream or sage cotton crewneck, hair down, single thin gold necklace |
| `hoodie-pony` | clean black or cream zip-hoodie + slick high pony, single small gold studs |
| `winter-cozy` | chunky oat turtleneck + leggings or wool wide-leg, hair down |

(`evening-glam`, `office-luxe`, `quiet-luxury` are intentionally removed — they pulled scenes toward TV-commercial gloss.)

## Room options (only relatable creator spaces)

| Room | Description |
|---|---|
| `home-bedroom-desk` | her own bedroom corner — small white or oak desk against a soft-painted wall (warm beige, sage, dusty pink), a few framed prints, a string-light strand or a single warm lamp, an unmade-but-styled bed visible in soft blur behind, **mic on the desk in front of her** pointed at her mouth |
| `couch-corner-ringlight` | beige linen couch, a thrown knit blanket, a ring-light visible just out of the bottom-left corner of frame, a single lamp behind, **clip-on lapel mic on her collar** OR **small mic on a low stand in front of the couch** |
| `kitchen-counter-morning` | clean kitchen counter — white tile or soft-stone backsplash, ceramic mug, herbs on the windowsill, soft window light, **single short-stand condenser mic on the counter in front of her** |
| `bedroom-bed-cozy` | sitting cross-legged on her own unmade-but-styled bed, soft string lights, rattan headboard, **clip-on lapel mic on her collar OR a small handheld mic she's holding at her chin** |
| `balcony-golden-hour` | small outdoor balcony, potted plants, soft golden-hour light, city soft-blurred behind, **clip-on lapel mic on her zip-up OR small handheld she's gripping** |
| `home-office-desk` | small clean home-office desk — neutral wall behind, one framed print, a candle, a stack of two books, **desktop boom-arm condenser mic in front of her chest pointed at her mouth** |
| `vanity-bedroom-corner` | plain bedroom vanity (NOT walk-in-closet) — small mirror with one warm bulb, a few skincare bottles in soft blur, **short-stand mic on the vanity in front of her** |
| `couch-podcast-rec` | she's recording from the couch — soft sage or beige wall, an acoustic foam panel barely visible behind, a leafy plant in the corner, **boom-arm desktop mic on a small side table directly in front of her**, a ring-light bouncing soft fill |

Removed and forbidden: `luxury-loft`, `cozy-library`, `clinical-studio`, `walk-in-closet`, `joe-rogan-style` (too masculine/aspirational for our girl), `beauty-channel` glossy-marble version. None of those.

## Outfit ⇄ Room pairings

All outfits work in all rooms; just keep the mood coherent.

| Vibe | Use these combos |
|---|---|
| morning ritual | `bathrobe` / `silk-pajama` / `loungewear` / `bummy-casual` + `bedroom-bed-cozy` / `kitchen-counter-morning` / `home-bedroom-desk` |
| podcast recording | `denim-tee` / `casual-cardigan` / `crewneck-sweater` / `hoodie-pony` + `home-office-desk` / `couch-podcast-rec` / `home-bedroom-desk` |
| GRWM beauty chat | `casual-cardigan` / `denim-tee` / `crewneck-sweater` + `vanity-bedroom-corner` / `couch-corner-ringlight` |
| outdoor casual | `gym-clean` / `denim-tee` / `casual-cardigan` + `balcony-golden-hour` |
| cozy late-night | `winter-cozy` / `loungewear` / `silk-pajama` + `bedroom-bed-cozy` / `couch-corner-ringlight` |

## Tone presets (lighting + small accent objects)

| Preset | Lighting | Accent objects |
|---|---|---|
| `morning-soft` | warm window light, soft front fill | ceramic mug, eucalyptus stem |
| `kbeauty-bright` | bright clean key, soft shadows | small jade roller, ceramic mug |
| `late-night-warm` | warm tungsten + string-lights | small candle, folded throw blanket |
| `golden-hour` | warm rim from window/sun + soft front fill | leafy potted plant, glass of iced coffee |
| `ringlight-natural` | ring-light catch in eyes + soft fill | one tube of her own water, single framed print on wall |

Match the preset to the brand world if obvious (Korean → `kbeauty-bright`, Sturm/Obagi clinical → `ringlight-natural`, niche perfume → `late-night-warm`).

## Output template

Produce ONE paragraph, ending with a single-line camera directive. Format:

```
Use the woman from the existing reference image and the product shown in the new image.
Now put her in a {room — concrete description with the mic placement called out specifically},
wearing {outfit description}, {body angle facing camera}, holding the {natural-language
description of the product} {hold style — label-out, cap on, NOT using it} so the brand
label is clearly readable to camera.
Set: {one or two small accent objects, the wall/surface, the mic again — no extra products,
no shelf-of-bottles styling}.
Lighting: {lighting specifics from the tone preset}.
Mood: {one-line vibe phrase — relatable creator, NOT magazine}.
Same woman from the reference image — match her face, hair, skin tone, and eyebrow shape
exactly. She is facing the camera. She is HOLDING the product, not using or applying it.
Hair and makeup polished and pretty even in casual outfits.
Real-photo realism, NOT illustrated. 9:16 vertical framing.
Camera: {angle + framing + lens feel}.
```

Keep it under ~120 words. One paragraph. No multi-shot scripts.

## Product-type adapters

- **jewelry** — She holds the closed jewelry box label-out at chest, OR she's already wearing the piece (necklace at collarbone / earring at her ear / ring on her hand visible in frame) AND her other hand holds the empty branded box label-out so it reads. Never have her actively putting the jewelry on.
- **skincare** — Hold the bottle/tube/jar at chest, label-out, **cap on**. Never dispense, drop, or pat onto skin.
- **haircare** — Hold the bottle at chest, label-out, cap on. Hair is styled, NOT being washed/applied to.
- **fragrance** — Hold the bottle at chest, label-out, **cap on**. Never spraying, never near her neck mid-application.
- **cosmetics (lipstick / compact / mascara / foundation)** — Hold it closed at chest, label-out. NEVER open, NEVER mid-application, NEVER mid-swipe, NEVER twisted up.
- **apparel** — She's wearing the garment; the garment is what we frame. Mic still in front of her.
- **home** — Hold the closed product at chest, label-out, like she's "showing it off."

## Worked examples (use this style)

### Skincare, podcast recording, denim-tee
User: `/generate-starting-image products/dr-barbara-sturm-peptide-serum/main.png`

```
Use the woman from the existing reference image and the product shown in the new image.
Now put her at a small clean home-office desk against a warm beige wall — one framed
print, a candle, a stack of two books, a black desktop boom-arm condenser mic on a
short stand directly in front of her chest pointed at her mouth — wearing a well-fitting
white tee tucked into vintage straight-leg denim with gold hoops and hair loose,
straight-on body angle facing camera, holding the closed Dr. Barbara Sturm Peptide
Serum bottle (cap on) at chest height with one hand, label squarely facing camera so
the Sturm typography is clearly readable. Set: single ceramic mug, soft sage wall,
mic boom in frame between her and the camera. Lighting: ring-light catch in eyes plus
soft front fill, ringlight-natural tone. Mood: relatable creator podcast, "let me
tell you about this." Same woman from the reference image — match her face, hair,
skin tone, and eyebrow shape exactly. She is facing the camera. She is HOLDING the
product, not using or applying it. Hair and makeup polished and pretty.
Real-photo realism, NOT illustrated. 9:16 vertical framing.
Camera: eye-level chest-up, 35mm-equivalent lens feel.
```

### Cosmetics (lipstick), GRWM corner, casual-cardigan
User: `/generate-starting-image products/satin-gold-lipstick-with-diamond-powder-house-of-sillage/main.png`

```
Use the woman from the existing reference image and the product shown in the new image.
Now put her at a plain bedroom vanity corner — small mirror with one warm bulb, a few
skincare bottles in soft blur, a short-stand condenser mic on the vanity in front of
her pointed at her chest — wearing a simple cream tee under a soft oat cardigan with
gold hoops and hair in a low loose pony, slight 3/4 right toward camera, holding the
House of Sillage Satin Gold Lipstick bullet closed (cap on) at chest height with two
hands cradling it label-out so the engraved gold case reads clearly to camera. Set:
single peony in a small jar, warm-painted bedroom wall, mic in front of her between
her and lens. Lighting: warm bulb halo + soft front fill, late-night-warm tone. Mood:
relatable GRWM creator, "this is the one I keep grabbing." Same woman from the
reference image — match her face, hair, skin tone, and eyebrow shape exactly. She is
facing the camera. She is HOLDING the product, not using or applying it. Hair and
makeup polished and pretty.
Real-photo realism, NOT illustrated. 9:16 vertical framing.
Camera: medium close-up tight on face and lipstick case, 50mm-equivalent lens feel.
```

### Jewelry (already worn), couch-podcast-rec, casual-cardigan
User: `/generate-starting-image products/twin-stone-forever-heart/main.png`

```
Use the woman from the existing reference image and the product shown in the new image.
Now put her on a beige linen couch in a podcast-recording corner — a soft sage wall
behind, an acoustic foam panel barely visible, a leafy plant in the corner, a black
boom-arm desktop mic on a small side table directly in front of her chest, a ring-
light bouncing soft fill — wearing a simple cream tee with a soft oat cardigan and
hair in a low loose pony, straight-on body angle facing camera, the Twin Stone Heart
Pendant already worn at her collarbone clearly visible, one hand resting at her sternum
just below the chain so the pendant reads to camera. Set: thrown knit blanket, single
ceramic mug, mic in frame between her and lens. Lighting: ring-light catch + soft front
fill, ringlight-natural tone. Mood: relatable podcast chat, "I never take this off."
Same woman from the reference image — match her face, hair, skin tone, and eyebrow
shape exactly. She is facing the camera. She is wearing the jewelry, not putting it on.
Hair and makeup polished and pretty.
Real-photo realism, NOT illustrated. 9:16 vertical framing.
Camera: eye-level chest-up, 35mm-equivalent lens feel.
```

## Don'ts (recap, applied every time)

- Don't have her face away from camera, profile-glance, or look-over-shoulder.
- Don't put the mic behind her, off to the side, or only implied — mic in front of her or held by her, every time.
- Don't have her using/applying/dispensing/swiping the product. Closed bottle, closed cap, closed kit. Just holding.
- Don't render multiple products, a fanned-out kit, a styled shelf, or a "product line" in frame.
- Don't pick aspirational/glossy sets: no luxury loft, no library nook, no walk-in-closet vanity, no clinical-marble brand studio, no NYC skyline. Real creator rooms only.
- Don't write more than one prompt unless asked for variations.
- Don't add affiliate copy, hashtags, or CTAs — this is the IMAGE prompt, not the caption.
- Don't change the girl's race, hair, or face — the whole point is consistency.
- Don't reference brands the product isn't actually from (no hallucinated brand names).
- Don't ever write "use illustration style" or "anime" or "3D render" — always real-photo.
- Don't write "no makeup", "barefaced", "tired", or "messy face". Even casual outfits get polished face + makeup.
