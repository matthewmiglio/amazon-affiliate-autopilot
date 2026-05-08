# Video Pipeline — Image + Script → Talking-Head Short

## What It Is

The full-stack pipeline that takes a static image of an AI-generated woman + a written script and outputs a finished 9:16 vertical YouTube Short of her speaking the script with synced lips and audio. No manual editing required.

## The Stack

```
[script.txt]
    ↓ ElevenLabs TTS API
[narration.mp3]
    ↓ + [hero-podcast.png]
    ↓ Hedra Character-3 API
[talking-head.mp4]   (9:16, lip-synced, audio baked in)
    ↓ HyperFrames
[final-short.mp4]    (with captions + branding)
    ↓ YouTube upload script
[posted Short]
```

## Why Hedra Character-3 (not Kling)

Hedra Character-3 is purpose-built for "single image of a person + audio → talking head video." It preserves face identity strongly, handles natural head motion and micro-expressions, supports 9:16 natively, and is one API call (vs Kling's two-step image-to-video then lip-sync).

Kling 2.6 is still useful for **non-dialogue B-roll** — animating product flat-lays, scene clips, ambient shots. Use Kling there. Use Hedra for any clip where the woman is speaking.

## Cost per 30-second Short

| Stage | Service | Cost |
|---|---|---|
| TTS | ElevenLabs (Turbo v2.5, ~500 chars) | ~$0.03 |
| Talking video | Hedra Character-3 | $0.30–$0.90 |
| **Total** | | **~$0.33–$0.93/Short** |

Hedra cost depends on plan tier (see Provider Comparison below).

## Provider Comparison — Cheapest Hedra Character-3 Access

Ranked by cost per 30-second 9:16 video:

| Rank | Provider | Cost/30s | Notes |
|---|---|---|---|
| 1 | **Hedra direct, Pro tier** ($30/mo, 1500 credits) | **~$0.30** | Cheapest at scale, requires monthly commitment |
| 2 | Hedra direct, Creator tier ($10/mo, 400 credits) | ~$0.38 | Good for MVP volume |
| 3 | fal.ai (`hedra/character-3`) | ~$0.90 | $0.03/output-second, no commitment, pay-as-you-go |
| 4 | Replicate (`hedra-labs/character-3`) | ~$0.90–$1.20 | Per-second billing, no commitment |
| 5 | Segmind / AIMLAPI / PiAPI proxies | ~$1.00–$1.50 | Markup over direct, avoid unless rate-limited elsewhere |

**Recommendation for our volume:**
- **MVP / under 20 videos per day:** Hedra direct Pro tier — $0.30/Short, no infra to manage.
- **Scaling above 20 videos per day:** consider self-hosted open-source alternatives (see below).

## Self-Hosting Alternatives (for scale)

Once we're posting 20+ Shorts per day, the math shifts:

| Setup | Cost/30s | Quality vs Hedra | When |
|---|---|---|---|
| RunPod serverless + Sonic/Hallo3 | ~$0.06 | ~80% (indistinguishable on 9:16 mobile) | 20–100/day |
| Self-hosted LatentSync on Vast.ai 4090 spot | ~$0.02 | Lip-sync only, need separate base video | 50+/day with reusable base |
| Self-hosted Sonic on dedicated 4090 spot | ~$0.05 | ~80% Hedra quality | 100+/day |

**Break-even vs fal.ai ($0.90):** ~24 videos/day to justify keeping a spot A100 hot 24/7.

**Quality caveat:** Hedra Character-3 still leads on natural head motion and emotional nuance. Open-source alternatives (Sonic, Hallo3, EchoMimicV2) are ~80% there — usually indistinguishable at 9:16 mobile resolution where the face is smaller.

## ElevenLabs TTS Settings

- **Voice:** "Rachel" (warm female library voice) for MVP. Clone a custom voice later for unique brand sound (~$22/mo Creator tier includes voice cloning).
- **Model:** `eleven_turbo_v2_5` — cheap, fast, sufficient quality for Shorts.
- **Settings:** Stability 0.5, Similarity 0.75, Style 0.3 (conversational warmth).
- **Pricing:** $0.18 per 1,000 characters on Creator tier ($22/mo includes 100k characters). A 30s Short script is ~500 characters → ~$0.09 raw, less in bundle.

## API Endpoints

- **ElevenLabs TTS:**
  `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
  Body: `{ text, model_id: "eleven_turbo_v2_5", voice_settings: {...} }`
  Returns: mp3

- **Hedra (upload assets):**
  `POST https://api.hedra.com/web-app/public/assets`
  Upload the hero image and the narration mp3, get back asset IDs

- **Hedra (generate):**
  `POST https://api.hedra.com/web-app/public/generations`
  Body: `{ image_asset_id, audio_asset_id, aspect_ratio: "9:16", resolution: "720p", duration_ms: 30000 }`
  Poll status, download mp4 when complete.

## V2 Pipeline Implementation Order

Steps 3–5 are already built from V1. Steps 1–2 are the new work:

1. **ChatGPT API or local image generation** → hero image of the woman holding the product (already working manually; need to script)
2. **ElevenLabs TTS API** → narration audio from script
3. **Hedra Character-3 API** → talking-head video clip
4. **HyperFrames** → composite video + captions + branding overlays
5. **YouTube upload script** → post the Short

## What Kling Is Still For

Kling 2.6 stays in the toolkit for:
- B-roll animation (product flat-lays coming alive, ambient marble/gold scenes)
- Scene transitions
- Any non-dialogue motion clips

Don't use Kling for the woman speaking. Hedra wins that use case on quality, simplicity, and cost.

## Cost Research Notes

- Talking-head video pricing has been dropping ~30%/quarter through 2025 — re-verify provider prices before committing to a tier.
- ElevenLabs has a Pro tier ($99/mo) that drops per-character cost further if we scale past 100k chars/mo.
- Hedra has rumored Enterprise volume pricing not published — worth a sales email if we hit 500+ videos/month.

## Sources

- [Hedra Character-3 docs](https://www.hedra.com/)
- [Hedra on fal.ai](https://fal.ai/models/hedra/character-3)
- [Hedra on Replicate](https://replicate.com/hedra-labs)
- [ElevenLabs API docs](https://elevenlabs.io/docs/api-reference)
- [Sync.so Lipsync-2 (alternative)](https://sync.so/)
- [LatentSync (open source)](https://github.com/bytedance/LatentSync)

## Decision Log

- 2026-05-07: Switched primary talking-head model from Kling 2.6 to Hedra Character-3. Reasons: one-step API (image + audio → finished video), better identity preservation on AI-generated faces, native 9:16, lower cost at our planned volume. Kling retained for B-roll and non-dialogue clips.
