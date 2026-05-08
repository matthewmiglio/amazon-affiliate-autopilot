# first-vids — Design Rules & Inspo Library

This is the canonical playbook for our jewelry shorts. Read top-to-bottom before
generating new compositions. Distilled from the official HyperFrames docs +
Nate Herkai's student kit (cloned at `first-vids/_inspiration/student-kit/`).

---

## 0 · The Laws (memorize before authoring)

Adapted from `student-kit/MOTION_PHILOSOPHY.md` ("11 Laws") to our jewelry
shorts context. These are non-negotiable.

1. **One idea per beat. Cut fast.** ~1.5s average scene length. Each beat lands
   ONE word/concept and moves on. If a beat says two things, split it.
2. **Hold the hero shot.** Outro CTA = **5+ seconds**. Speed earns space for
   stillness to land. Kinetic → calm = catharsis. **This was our biggest miss
   in v2 — we had 0.4s CTA hold; user wants 5s.**
3. **Pause before you talk.** First narration line starts at **≥1.5s**. Open
   on visual breathing room — let the eye settle on the product/scene before
   the voice arrives.
4. **Use periods, not commas. Then PAD between sentences.** Kokoro alone
   barely audibly pauses on a period — even at speed 1.0 you'll get
   "Ruby red Always loved" run together. We split the line on `.`/`!`/`?`,
   synthesize each sentence separately, and inject **0.40s of silence** between
   them. That's the difference between "rushed" and "natural." See §10.
5. **Black/dark-luxe is canvas.** 80–90% of every frame is near-black. Color
   earns its place by carrying meaning (gold = CTA, accent = product hue).
6. **Light, not color, reads as premium.** Chrome gradients on type, soft
   halos, vignettes, light beams. The piece is *lit*, not *colored*.
7. **Camera never sleeps.** Even on still frames the bg drifts (ken-burns),
   the halo breathes, particles glint. Static = death.
8. **Type is a character.** Words SCALE, MORPH, COMPRESS, GLOW. Hero hook
   typography drives ~50% of the storytelling.
9. **Whip transitions, not hard cuts.** Streak/blur trail between scenes
   reads expensive. Hard cuts feel cheap (we used hard cuts in v2 — fix).
10. **Vary layouts hard.** No two of our 11 videos should put the product +
    headline in the same place. Use the 4 layout archetypes (§5) — rotate.
11. **Timelines fill their slots.** End every GSAP timeline with
    `tl.to({}, { duration: TOTAL_DURATION }, 0)` so the runtime doesn't show
    a black flash. Non-negotiable.

---

## 1 · Render Contract (must-dos & must-not-dos)

From `student-kit/CLAUDE.md`:

1. Root `<div>` needs `id`, `data-composition-id`, `data-start="0"`,
   `data-width`, `data-height`.
2. Timed visible elements need `class="clip"` — **except** `<video>` and
   `<audio>` (adding `clip` to `<video>` breaks it).
3. Every timed element needs `data-start`, `data-duration`, `data-track-index`.
4. `data-start` can be relative: `data-start="intro"` / `"intro + 2"` /
   `"intro - 0.5"`. Same-track clips can't overlap → use different
   `data-track-index`.
5. `<video>` must be `muted`; audio belongs in sibling `<audio>` for the mixer.
6. Every composition registers exactly one paused GSAP timeline on
   `window.__timelines["<data-composition-id>"]`. Key must match exactly.
7. `tl.duration()` must equal the slot duration — pad with `tl.to({},…)` if
   needed.

## 2 · Common Mistakes Checklist

From `hyperframes.heygen.com/guides/common-mistakes`:

| Pitfall | Fix |
|---|---|
| GSAP animating `<video>` width/height/top/left | Wrap in non-timed `<div>`, animate the wrapper |
| Calling `video.play()`/`pause()` in JS | Don't — framework owns playback. Use `data-start`, `data-media-start`, `data-volume` |
| Composition shorter than video | `tl.set({}, {}, FINAL_TIME)` to extend timeline |
| Missing `class="clip"` | Element renders for full composition, ignoring its `data-start`/`data-duration` |
| Source images > 2× canvas | 7000×5000 → 140 MB bitmap → stutters. Cap at 3840×2160 for 1920×1080 (or 2160×3840 for 1080×1920) |
| Stacked `backdrop-filter: blur()` | Drops to 5–10 fps. Limit to 2–3 layers, radius < 64px, prefer pre-rendered PNG blurs |
| Timeline key ≠ `data-composition-id` | Animation never plays — keys must match exactly |
| `Math.random()`, `Date.now()`, `setInterval`, `repeat:-1` | Non-deterministic / breaks render. Use seeded PRNG, GSAP `repeat: N`, hard-coded timing |
| SVG `data:image/svg+xml` filter as `background-image` for grain | Taints canvas in Safari. Use CSS `radial-gradient` grain instead (recipe in §6) |
| Async timeline construction | Race conditions. Build synchronously at page load |
| `<audio>` tag in HTML when also muxing later | Hyperframes will mix it in too at unbalanced levels. We mux post-render → no `<audio>` tags in HTML |

---

## 3 · Banned Patterns (we used these in v2 — don't again)

| Banned | Why | Replace with |
|---|---|---|
| `Inter` font | Banned in HyperFrames design rules (overused, generic) | `Montserrat` (display), `Roboto Mono` (mono labels) |
| `Open Sans`, `Roboto`, `Poppins`, `Fraunces`, `Playfair Display`, `Cinzel`, `Syne`, `Nunito`, `Source Sans`, `PT Sans`, `Lato` | Same — banned/overused | `Cormorant Garamond` (italic display), `Montserrat`, `Bebas Neue`, `Space Mono` |
| Stacked `backdrop-filter: blur()` heavily | Frame-drops | One blur layer per region max |
| Hard scene cuts | "Cheap" feel | Whip-streak / shader transitions ≥0.3s |
| Same product position across all 11 videos | Templated | Vary across 4 layout archetypes |
| 1.0 second CTA hold | Too rushed | 5+ seconds (Law 2) |
| Narration starts at t=0 | Jarring | ≥1.5 s pre-roll silent breath |
| Heavy 0.10–0.15 grain opacity | "Too much fuzz" (user) | 0.04–0.06, CSS-radial recipe |
| Comma-heavy narration | Rushed sound | Periods between phrases |

---

## 4 · Approved Typography Stack

```
@import url("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500;1,600;1,700&family=Montserrat:wght@300;500;700;900&family=Bebas+Neue&family=Space+Mono:wght@400;700&display=block");
```

| Use | Family | Weight |
|---|---|---|
| Hero italic display | Cormorant Garamond | 600 italic |
| Bold sans display (alt hero) | Montserrat | 900 |
| Compressed labels / eyebrow | Bebas Neue | 400 |
| Mono ticker / micro-labels | Space Mono | 700 |

**Weight contrast must be dramatic** (300 vs 900, not 400 vs 700).
**Min sizes**: 80px+ headlines, 36px+ body, 18px+ labels (vertical 1080-wide).

---

## 5 · The 4 Layout Archetypes

We rotate one of these per slug so no two videos feel templated. Each
archetype has a distinct product position, headline placement, and motion
choreography.

### A. SPOTLIGHT (centered hero)
```
┌─────────────────┐
│ ▢ EYEBROW       │  top: eyebrow chip
│                 │
│  Italic hook    │  upper-third: kinetic headline
│  with GOLD word │
│                 │
│  ╔══════════╗   │
│  ║ PRODUCT  ║   │  center: large hero, halo + shimmer
│  ║   IMG    ║   │
│  ╚══════════╝   │
│                 │
│   tag — Daily   │  lower: subtle tag
└─────────────────┘
```
- Product: dead-center, ~70% of width, halo glow
- Motion: scale-pop 1.18 → 1.0 with `back.out(1.6)`, shimmer-sweep at 1.4s

### B. DIPTYCH (top/bottom split)
```
┌─────────────────┐
│  PRODUCT IMG    │  top half: product full-bleed
│   (cropped)     │
│  ─────────────  │  hairline divider
│  HOOK headline  │  bottom half: text + tag
│   stack on dark │
│   AMAZON gold   │
└─────────────────┘
```
- Product fills top 50% (cropped, ken-burns 1.0 → 1.06)
- Headline fills bottom 50% on dark slab, parallax-y entry

### C. OFF-CENTER (asymmetric)
```
┌─────────────────┐
│  PRODUCT        │  upper-right: product, ~50% width
│  ▶ IMG (right)  │
│                 │
│  HOOK gold      │  middle-left: large headline
│  Kinetic line   │
│   ───           │
│  ▢ EYEBROW      │  lower-left: eyebrow + tag
└─────────────────┘
```
- Product positioned in right 60% / upper 60% intersection
- Headline left-aligned on left 55%, breaks across multiple lines

### D. UGC-FIRST (model-led)
```
┌─────────────────┐
│  ▢ EYEBROW      │
│                 │
│  FULL-BLEED     │  scene 1 IS the UGC photo (not scene 2)
│  UGC PHOTO      │  with kinetic caption strip + product inset
│  + caption      │
│                 │
│  product chip   │  small 200px product chip lower-right
└─────────────────┘
```
- UGC photo full-bleed in scene 1 (not 2)
- Caption strip with per-word kinetic reveal
- Small product "chip" overlays bottom-right (so viewer connects model → SKU)
- Scene 2 = product hero closeup

---

## 6 · Recipes

### 6.1 Composition shell (vertical 1080×1920, 12s)
```html
<div id="root"
     data-composition-id="main"
     data-start="0" data-duration="12"
     data-width="1080" data-height="1920">
  <div class="scene clip" id="hold"  data-start="0"   data-duration="1.5" data-track-index="0">…</div>
  <div class="scene clip" id="hook"  data-start="1.5" data-duration="3.0" data-track-index="0">…</div>
  <div class="scene clip" id="ugc"   data-start="4.5" data-duration="2.5" data-track-index="0">…</div>
  <div class="scene clip" id="cta"   data-start="7.0" data-duration="5.0" data-track-index="0">…</div>
</div>
```
- Scene `data-track-index="0"` always
- Each scene `data-start` = previous's `data-start + data-duration`
- Root `data-duration` = sum of scenes (12s)
- HOLD scene = 1.5s of silent visual breath before narration
- CTA = 5s (per Law 2)

### 6.2 GSAP timeline registration
```javascript
window.__timelines = window.__timelines || {};
const tl = gsap.timeline({ paused: true });

// per-scene tweens here…

tl.to({}, { duration: 12 }, 0);   // ← non-negotiable slot anchor
window.__timelines["main"] = tl;
```

### 6.3 Chrome-gradient text (the gold for hero/CTA)
```css
.gold-chrome {
  background: linear-gradient(180deg, #f5d77b 0%, #d4a017 45%, #b8860b 70%, #f5d77b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 4px 18px rgba(212,160,23,0.35));
}
```

### 6.4 CSS-only grain (Safari-safe, no canvas taint)
```css
.grain {
  position:absolute; inset:0; pointer-events:none; z-index:50;
  opacity: 0.06;            /* was 0.10 — too heavy. user feedback */
  background-image:
    radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1.2px),
    radial-gradient(rgba(0,0,0,0.18) 1px, transparent 1.2px);
  background-size: 3px 3px, 5px 5px;
  background-position: 0 0, 1px 2px;
  mix-blend-mode: overlay;
}
```
(Replaces the SVG-filter `data:image/svg+xml` grain we used in v1/v2.)

### 6.5 Per-word kinetic typography (use this everywhere there's >3 words)
```html
<span class="word">Adding</span>
<span class="word">this</span>
<span class="word gold-chrome">to</span>
<span class="word gold-chrome">your</span>
<span class="word">list.</span>
```
```javascript
tl.from(".hook .word", {
  y: 32, opacity: 0, scale: 0.9,
  duration: 0.45, ease: "power3.out",
  stagger: 0.08
}, 1.7);
```

### 6.6 Whip-streak transition (replaces our hard cut at 3s)
```css
.whip-streak {
  position:absolute; inset:0; pointer-events:none; z-index:60;
  background: linear-gradient(110deg, transparent 0%, rgba(255,255,255,0) 30%,
              rgba(255,255,255,0.95) 50%, rgba(255,255,255,0) 70%, transparent 100%);
  transform: translateX(-100%); opacity:0;
  filter: blur(40px);
}
```
```javascript
tl.to("#whip", { x: "100%", opacity: 1, duration: 0.18, ease: "power3.in" }, 4.4)
  .to("#whip", { x: "200%", opacity: 0, duration: 0.18, ease: "power3.out" }, 4.58);
```

### 6.7 Hold-the-hero CTA (5s with breathing motion)
- Card slides up at t=7.0, settles at t=7.4
- "Amazon" gold-chrome scaleY 0.7 → 1.0 with `back.out(1.7)` over 0.45s
- Light leak: opacity yoyo 0.85 → 0.5 → 0.85 over the 5s hold (sine.inOut)
- Sub-line "TAP THE LINK IN BIO" word-stagger reveal at t=7.8
- Faint particle glints behind card (4–6 absolute-positioned dots, opacity yoyo)

---

## 7 · Narration Authoring Rules

1. **Use periods between phrases**, not commas. Each `.` is a 0.3s natural
   pause kokoro respects.
2. **Two lines max per video** (hook + reaction). Each line ≤9 words.
3. **First line starts at ≥1.5s** (template enforces this via the HOLD scene).
4. **Avoid trailing commas** before "trust me" / "I promise" — make them
   separate sentences.

| Bad (commas, no breath) | Good (periods, room to breathe) |
|---|---|
| Adding this to your Amazon list, trust me. | Adding this. To my Amazon list. Trust me. |
| Bow meets butterfly — the cutest stack I own. | Bow meets butterfly. The cutest stack I own. |
| This little Amazon find gets so many compliments. | Such an Amazon find. So many compliments. |

---

## 8 · Reference Templates (cloned, do not modify)

The student kit is cloned to `first-vids/_inspiration/student-kit/`. Treat as
read-only; copy patterns into our project as needed.

Most relevant projects to study:

| Path (under `_inspiration/student-kit/video-projects/`) | Why |
|---|---|
| `may-shorts-19/` | Vertical 1080×1920 — face-video bottom-half mode, exact aspect we use |
| `may-shorts-18/`, `may-shorts-6/` | More 1080×1920 examples |
| `golden-ratio-demo/` | Classic geometry-driven layout — useful for the OFF-CENTER archetype |
| `linear-promo-30s/` | Minimal premium pacing, chrome gradients, whip transitions |
| `clickup-demo/` | Product-screen pacing (their format ≠ ours but the timing rhythm is gold) |
| `hyperframes-sizzle/` | Fast-cut kinetic montage — reference for HOOK scene energy |

Workspace docs at the kit root:
- `MOTION_PHILOSOPHY.md` — the 11 Laws + 8 background textures + recipes
- `CLAUDE.md` — Render Contract, skills, workflow
- `DESIGN.ais-example.md` — full brand-spec template

---

## 9 · Reference Repos (cloned, do not modify)

In addition to the student-kit, the following are cloned to
`hyperframes/_inspiration/`:

| Path | Why it's useful |
|---|---|
| `student-kit/` | Nate Herkai's playbook — 12 reference projects + MOTION_PHILOSOPHY.md (11 Laws) + CLAUDE.md (Render Contract). The canonical aesthetic playbook. |
| `msw-brand-video/` | Mount Sinai brand video skill: 2 production templates (`full-hero` 15s, `bg-only` 12s) with proven timing maps and brand tokens. Concrete "what to edit" guidance per element. **Steal**: brightness:0/invert:1 logo trick, ken-burns inset:-120/-200 overshoot, gradient text via `linear-gradient(135deg, …) + -webkit-background-clip: text`, the `h-line1/h-line2/h-line3` 3-line headline pattern. |
| `study-arc/` | A 1080×1920 HyperFrames composition (our exact aspect). DESIGN.md is a **gold-standard format** for our future per-batch design docs (Style Prompt / Colors / Typography / Motion / What NOT to Do). |
| `vercel-template/` | Reference render server — patterns for parallel Chrome workers (`--workers auto`) and dimension-agnostic compositions. Skip for content; useful for infra. |

### MSW timing-map pattern (steal this for our hook scene)

MSW's `full-hero` template documents reveal anchors verbatim:

```
t=0.0  Ken Burns starts (full duration, scale 1.0→1.28, pan −60/+20)
t=0.4  Logo fades in       (→ opacity 0.85, 1.0s)
t=0.7  Badge rises         (y +16 → 0, 0.7s)
t=1.0  Bottom bar sweep    (scaleX 0→1 over full duration)
t=1.1  Line 1 reveal       (y +40, 0.75s)
…
```

Each tween offset is hand-tuned and **documented in a comment block** so future
edits don't have to re-derive timing. Adopt this when extending our layouts.

### MSW gradient-text recipe (better than our current `gold-chrome`)

For variety, mix accent colors instead of monochrome gold:
```css
.h-line2 {
  background: linear-gradient(135deg, var(--cyan) 0%, var(--pink) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
```
Works for any 2-color brand pair. Use when a video needs a non-gold accent
(e.g. emerald → silver, ruby → rose-gold, citrine → champagne).

### MSW logo treatment (universal)

```css
filter: brightness(0) invert(1);   /* turns any logo white */
opacity: 0.85;                      /* never 1.0 — fights with content */
```

---

## 10 · Narration Pacing (the v3→v4 lesson)

Symptom in v3: phrases like *"Sparkles for days"* and *"Linked in my bio. Trust."*
sounded rushed because kokoro's intra-sentence pause is ~80ms (insufficient to
read as a beat).

**Implementation in `scripts/narrate_ad.py`:**

```python
INTER_SENTENCE_PAUSE = 0.40   # seconds of silence between "." separated chunks
MAX_SPEED = 1.15              # cap (was 1.40 in v3 — too rushed)

# Split text on sentence boundaries:
sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

# Synthesize each sentence at speed=1.0; concat with 0.40s silence between.
# If total exceeds scene budget, ramp speed up to 1.15 max — never beyond.
```

**Knock-on rule:** if budget at speed 1.15 still doesn't fit, **extend the scene
duration**, don't sacrifice pacing. v4 timings:

| Slot | v3 | v4 | Why |
|---|---|---|---|
| HOLD  | 1.5s | 1.5s | Unchanged — silent breath before voice |
| HOOK  | 3.0s | 3.5s | Room for 2 sentences + pause |
| UGC   | 2.5s | 4.0s | Most-bumped — UGC line is usually longer |
| CTA   | 5.0s | 5.0s | Unchanged — Law 2 |
| **Total** | 12.0s | **14.0s** | |

### Author rule: 1–2 short sentences per scene

When writing `narration[0]` and `narration[1]` in a creative-plan, aim for:
- 1–2 sentences
- 3–6 words per sentence
- Period between (not comma — see Law 4)

Good: `"Linked in my bio. Trust."` (5 words, 2 sentences, pause naturally lands)
Bad:  `"Linked in my bio, trust me."` (kokoro reads as one breath)

---

## 11 · Pre-flight Checklist (before claiming a video done)

Run through this mentally before rendering each batch.

**Structural:**
- [ ] Root has `data-composition-id="main"`, matching `window.__timelines["main"]`
- [ ] Every scene has `class="scene clip"` + all data-attributes
- [ ] Scene windows tile end-to-end (no gaps/overlaps): hold(0–1.5) + hook(1.5–4.5) + ugc(4.5–7) + cta(7–12)
- [ ] Total duration = 12s; `tl.to({}, { duration: 12 }, 0)` anchor present
- [ ] No `<audio>` tags in HTML (mux step handles audio)
- [ ] Image source files ≤ 2× canvas (≤2160×3840)
- [ ] No banned patterns (§3)

**Aesthetic:**
- [ ] CTA visible for 5+ seconds
- [ ] Narration starts at ≥1.5s
- [ ] Narration uses periods, not commas
- [ ] Layout archetype assigned (A/B/C/D) — varies across the 11 videos
- [ ] Grain opacity ≤ 0.06
- [ ] Hero gold-chrome on at least one word per video
- [ ] At least one whip / shader transition between scenes (no hard cuts)
- [ ] Camera never sleeps — every scene has ≥1 mid-scene activity
- [ ] ≥3 different easings per scene

**Audio:**
- [ ] `mean_volume ≥ −22 dB` (verified via `ffmpeg -af volumedetect`)
- [ ] Music ducks under narration through the drop
- [ ] No `<audio>`-tag bleed from hyperframes render
