"""
Build the starting-image prompt for Hedra image generation.

Faithful port of the /generate-starting-image SKILL.md hard rules + axis
rotation. Picks one combination per (slug + reroll) seed so re-runs are
stable, but two different slugs almost never collide on the same combo.

Public:
    build_prompt(slug, manifest, *, reroll=0) -> str
"""
from __future__ import annotations

import hashlib
import random
from typing import Any

# --- Axis options (verbatim from SKILL.md) ----------------------------------

BODY_ANGLES = [
    "straight-on, body squared to camera, eyes on the lens",
    "slight 3/4 left toward camera, eyes still on the lens",
    "slight 3/4 right toward camera, eyes still on the lens",
]

CAMERA_ANGLES = [
    "eye-level chest-up framing, 35mm-equivalent lens feel",
    "slight low-angle chest-up framing, 35mm-equivalent lens feel",
    "slight high-angle face-and-product framing, 50mm-equivalent lens feel",
    "medium close-up tight on face and product, 50mm-equivalent lens feel",
]

HOLD_STYLES_GENERIC = [
    "with one hand at chest height, label squarely facing camera (cap on, lid closed)",
    "with both hands at chest cradling it label-out (cap on, lid closed)",
    "raised in one hand at face level showing the label to camera (cap on, lid closed)",
    "resting on the desk in front of the mic with one hand on top of it, label-out",
]

OUTFITS = {
    "bummy-casual": "an oversized cream hoodie with a messy half-bun, no jewelry, just-rolled-out-of-bed-but-glowing",
    "loungewear": "a matching ribbed-knit lounge set in oat or sage with a soft cardigan over the shoulders, hair down",
    "bathrobe": "a plush ivory waffle bathrobe with a terry collar, towel-dried damp hair, no jewelry",
    "silk-pajama": "a navy silk pajama set with piping, hair smooth and down",
    "denim-tee": "a well-fitting white tee tucked into vintage straight-leg denim, gold hoops, hair loose",
    "casual-cardigan": "a simple cream tee under a soft oat cardigan with gold hoops and hair in a low loose pony",
    "crewneck-sweater": "an oversized cream cotton crewneck, hair down, single thin gold necklace",
    "hoodie-pony": "a clean cream zip-hoodie with a slick high pony and small gold studs",
    "winter-cozy": "a chunky oat turtleneck with wool wide-leg pants, hair down",
}

ROOMS = {
    "home-bedroom-desk": (
        "her own bedroom corner — a small oak desk against a soft warm-beige wall, a few framed prints, "
        "a single warm lamp, an unmade-but-styled bed visible in soft blur behind, "
        "a desktop boom-arm condenser mic on the desk in front of her pointed at her mouth"
    ),
    "couch-corner-ringlight": (
        "a beige linen couch corner with a thrown knit blanket, a ring-light visible just out of the bottom-left "
        "of frame, a single lamp behind, a clip-on lapel mic clipped to her collar"
    ),
    "kitchen-counter-morning": (
        "a clean kitchen counter — soft-stone backsplash, ceramic mug, herbs on the windowsill, soft window light, "
        "a single short-stand condenser mic on the counter in front of her"
    ),
    "bedroom-bed-cozy": (
        "sitting cross-legged on her own unmade-but-styled bed, soft string lights, rattan headboard, "
        "a small handheld mic she's holding at her chin"
    ),
    "balcony-golden-hour": (
        "a small outdoor balcony with potted plants and warm golden-hour light, soft-blurred city behind, "
        "a clip-on lapel mic on her zip-up"
    ),
    "home-office-desk": (
        "a small clean home-office desk against a neutral wall — one framed print, a candle, a stack of two books, "
        "a desktop boom-arm condenser mic in front of her chest pointed at her mouth"
    ),
    "vanity-bedroom-corner": (
        "a plain bedroom vanity corner — a small mirror with one warm bulb, a few skincare bottles in soft blur, "
        "a short-stand mic on the vanity in front of her"
    ),
    "couch-podcast-rec": (
        "a podcast-recording couch corner — soft sage wall, an acoustic foam panel barely visible, a leafy plant in "
        "the corner, a black boom-arm desktop mic on a small side table directly in front of her chest, a ring-light "
        "bouncing soft fill"
    ),
}

TONES = {
    "morning-soft": ("warm window light with soft front fill", "ceramic mug, eucalyptus stem"),
    "kbeauty-bright": ("bright clean key light, soft shadows", "small jade roller, ceramic mug"),
    "late-night-warm": ("warm tungsten plus string-lights", "small candle, folded throw blanket"),
    "golden-hour": ("warm rim light from a window with soft front fill", "leafy potted plant, glass of iced coffee"),
    "ringlight-natural": ("ring-light catch in eyes plus soft front fill", "single framed print on the wall"),
}

VIBE_LINES = {
    "morning-soft": "relatable morning-routine creator, calm and warm",
    "kbeauty-bright": "relatable creator GRWM, bright and friendly",
    "late-night-warm": "relatable late-night creator chat, cozy and intimate",
    "golden-hour": "relatable creator on the balcony, easy and bright",
    "ringlight-natural": "relatable podcast creator, \"let me tell you about this\"",
}

# Coherent vibe pairings (outfit set, room set, tone) from SKILL.md "Outfit ⇄ Room"
PAIRINGS = [
    {
        "name": "morning-ritual",
        "outfits": ["bathrobe", "silk-pajama", "loungewear", "bummy-casual"],
        "rooms": ["bedroom-bed-cozy", "kitchen-counter-morning", "home-bedroom-desk"],
        "tone": "morning-soft",
    },
    {
        "name": "podcast-recording",
        "outfits": ["denim-tee", "casual-cardigan", "crewneck-sweater", "hoodie-pony"],
        "rooms": ["home-office-desk", "couch-podcast-rec", "home-bedroom-desk"],
        "tone": "ringlight-natural",
    },
    {
        "name": "grwm-beauty-chat",
        "outfits": ["casual-cardigan", "denim-tee", "crewneck-sweater"],
        "rooms": ["vanity-bedroom-corner", "couch-corner-ringlight"],
        "tone": "kbeauty-bright",
    },
    {
        "name": "outdoor-casual",
        "outfits": ["denim-tee", "casual-cardigan"],
        "rooms": ["balcony-golden-hour"],
        "tone": "golden-hour",
    },
    {
        "name": "cozy-late-night",
        "outfits": ["winter-cozy", "loungewear", "silk-pajama"],
        "rooms": ["bedroom-bed-cozy", "couch-corner-ringlight"],
        "tone": "late-night-warm",
    },
]

# --- Product-type adapters --------------------------------------------------

def _infer_product_type(manifest: dict[str, Any]) -> str:
    aux = manifest.get("item-auxiliary-information") or {}
    blob = " ".join(
        str(v) for v in (
            aux.get("category", ""),
            aux.get("product", ""),
            aux.get("description", ""),
        )
    ).lower()
    if any(k in blob for k in ("perfume", "fragrance", "eau de parfum", "cologne")):
        return "fragrance"
    if any(k in blob for k in ("lipstick", "mascara", "foundation", "concealer", "lip serum",
                                "lip balm", "lip glorifier", "rouge", "lip liner", "eyelash",
                                "lash", "brow", "eye patch", "compact", "cushion")):
        return "cosmetics"
    if any(k in blob for k in ("shampoo", "conditioner", "hair", "scalp")):
        return "haircare"
    if any(k in blob for k in ("necklace", "earring", "ring", "bracelet", "pendant", "jewelry")):
        return "jewelry"
    return "skincare"


HOLD_OVERRIDES = {
    "fragrance": "with one hand at chest holding the closed perfume bottle, cap on, label squarely facing camera "
                 "(NOT spraying, NOT near her neck)",
    "jewelry": "wearing the piece visibly on her body and holding the closed branded box label-out at chest with "
               "her other hand (NOT putting it on)",
    "cosmetics": "with two hands at chest cradling the closed product label-out (cap on, NOT opened, NOT mid-application)",
    "haircare": "with one hand at chest holding the closed bottle label-out (cap on, hair already styled)",
    "apparel": "wearing the garment so it frames cleanly to camera",
    "home": "with one hand at chest holding the closed product label-out, like she's showing it off",
    "skincare": "with one hand at chest holding the closed bottle / jar / tube label-out (cap on, lid closed, "
                "NOT applying, NOT dispensing, NOT patting onto skin)",
}

# --- Builder ---------------------------------------------------------------

def _seed(slug: str, reroll: int) -> int:
    h = hashlib.sha256(f"{slug}|{reroll}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def _product_phrase(manifest: dict[str, Any]) -> str:
    aux = manifest.get("item-auxiliary-information") or {}
    brand = (aux.get("brand") or "").strip()
    product = (aux.get("product") or "").strip()
    if brand and product:
        return f"{brand} {product}"
    if product:
        return product
    if brand:
        return f"{brand} product"
    return "product"


def build_prompt(
    slug: str,
    manifest: dict[str, Any],
    *,
    reroll: int = 0,
    n_character_refs: int = 3,
) -> str:
    rng = random.Random(_seed(slug, reroll))

    pairing = rng.choice(PAIRINGS)
    outfit_key = rng.choice(pairing["outfits"])
    room_key = rng.choice(pairing["rooms"])
    tone_key = pairing["tone"]
    body_angle = rng.choice(BODY_ANGLES)
    camera_angle = rng.choice(CAMERA_ANGLES)

    ptype = _infer_product_type(manifest)
    hold = HOLD_OVERRIDES.get(ptype, rng.choice(HOLD_STYLES_GENERIC))

    outfit = OUTFITS[outfit_key]
    room = ROOMS[room_key]
    lighting, accents = TONES[tone_key]
    vibe = VIBE_LINES[tone_key]
    product_phrase = _product_phrase(manifest)

    # Reference images are passed in this order: <n_character_refs> shots of
    # the woman, then 1 shot of the product. The prompt has to make that
    # explicit so the model uses them correctly.
    last_char_idx = n_character_refs
    product_idx = n_character_refs + 1
    if n_character_refs == 1:
        char_phrase = "Reference image 1 shows the woman."
    else:
        char_phrase = (
            f"Reference images 1 through {last_char_idx} show the SAME woman in "
            "different poses and outfits. Use her exact face, hair, skin tone, and eyebrow shape — "
            "treat all of these refs as one identity. Do NOT alter her facial features."
        )

    return (
        # ── Must-haves first, before scene description ──
        f"{char_phrase} "
        f"Reference image {product_idx} is the product to put in her hands. "
        "HARD RULES that must be obeyed: "
        "(1) She is FACING THE CAMERA. Her torso is squared toward camera (or at most a slight 3/4 toward "
        "camera). Her eyes are on the lens. NEVER profile, NEVER over-the-shoulder, NEVER back-to-camera, "
        "NEVER glancing away. "
        "(2) A microphone is IN FRONT OF HER, between her and the camera, clearly visible in the frame "
        "(desktop boom-arm condenser on a stand pointed at her mouth, or a clip-on lapel mic on her collar, "
        "or a small handheld mic she's holding to her chin). The mic is NEVER behind her, NEVER off-frame. "
        "(3) She is HOLDING the product label-out at chest height, cap on, lid closed. NEVER applying, "
        "dispensing, swiping, spraying, or mid-use. "
        "(4) Real-photo realism. NOT illustrated, NOT 3D-render, NOT anime, NOT painted. "
        "(5) 9:16 vertical framing. "
        # ── Now the scene ──
        f"Scene: she is in {room}, wearing {outfit}, {body_angle}, holding the closed {product_phrase} "
        f"{hold} so the brand label is clearly readable to camera. "
        f"Set details: {accents}, no extra products, no shelf-of-bottles styling, no fanned-out kit. "
        f"Lighting: {lighting}. Mood: {vibe}. "
        f"Camera: {camera_angle}. "
        "Hair and makeup polished and pretty even in casual outfits."
    )


if __name__ == "__main__":
    # Quick smoke: print a prompt for whatever slug you pass.
    import json
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        sys.exit("usage: prompt_builder.py <slug> [reroll]")
    slug = sys.argv[1]
    reroll = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    repo_root = Path(__file__).resolve().parent.parent.parent
    mpath = repo_root / "products" / slug / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    print(build_prompt(slug, manifest, reroll=reroll))
