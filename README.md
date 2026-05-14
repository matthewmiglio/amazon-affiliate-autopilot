# amazon-affiliate-autopilot

End-to-end pipeline that turns Amazon affiliate products into AI talking-head Shorts — one consistent host, one product per video, affiliate funnel through `theluxedrawer.com/p/<slug>` → YouTube, Instagram, Facebook, Pinterest, and X.

Each pipeline stage is a slash-command skill — idempotent, manifest-driven, and accepts a single slug, a comma-list, or `--all-needing`.

## The Character

A pinned character folder defines the host. Same face, same voice across every Short.

<p align="center">
  <img width="240" alt="Host pose 1" src="https://github.com/user-attachments/assets/2901efcc-9d07-41c1-baf3-c7bf02eeef79" />
  <img width="240" alt="Host pose 2" src="https://github.com/user-attachments/assets/6203d864-c59a-4319-8dd6-3976c00ab58d" />
  <img width="240" alt="Host pose 3" src="https://github.com/user-attachments/assets/7cc1e1a5-75ad-420d-a51f-42c7d1dd3a5a" />
</p>

## Lifestyle Frames

Examples of starting frames across different products.

<p align="center">
  <img width="240" alt="Lifestyle 1" src="https://github.com/user-attachments/assets/6761df5f-e847-4810-bb93-359bc568dbac" />
  <img width="240" alt="Lifestyle 2" src="https://github.com/user-attachments/assets/20c74fdf-fea8-4a36-928e-f3b4930c15a9" />
  <img width="240" alt="Lifestyle 3" src="https://github.com/user-attachments/assets/b73cd8b7-8fbd-4f40-a3cd-b4976683235d" />
</p>

## Pipeline

Authoritative ordering lives in [`.claude/skills/PIPELINE.md`](.claude/skills/PIPELINE.md).

### 1. Character refs
Pin a host face + voice per channel — `characters/<channel>/`. See "The Character" above.

### 2. Scrape Amazon — `extensions/amazon-product-page-scraper/` (Chrome ext)
Pulls link + product details + main image from an Amazon product page into a Downloads dump.

<img width="200" src="https://github.com/user-attachments/assets/5a0ae8f4-49dd-4a10-9fc4-863b468c718b" />

### 3. Import scraped data — `/import-referral-data`
Converts the scrape dump into `products/<slug>/manifest.json`. Filters anything below 10% commission and dedupes by ASIN.

### 4. Video-gen prompt — `/generate-video-prompt`
Authors the image-to-video animation prompt and writes it to `manifest["video-prompt"]`.

### 5. Narration script — `/write-script`
15–20s podcast-tone voiceover, written into `script-raw-text` in the manifest.

> "Listen, your cleanser matters way more than people give it credit for. The Clé de Peau Beauté Clarifying Cleansing Foam — made in Japan, built around their Skin Intelligence research that's been their signature for over forty years. Clears the day off without that tight, stripped feeling. An affordable luxury, honestly. Tap the link to grab it on Amazon."

### 6. Narration audio — `/generate-narration`
ElevenLabs TTS with the channel voice pinned per character.

### 7. Starting frame — `/generate-starting-image`
Hedra image-gen produces a 9:16 lifestyle composite with the host holding the product.

<img width="240" src="https://github.com/user-attachments/assets/7a4e8a47-a587-4ad3-b42e-67df9b13f9e4" />

### 8. UGC talking head — `/generate-hedra-video`
Starting image + narration → Hedra Avatar. Audio is baked into the mp4 at low quality at this stage — that's fixed in the next step.

https://github.com/user-attachments/assets/b076a779-15fd-453d-8c82-2605f3636edf

### 9. Audio restitch — `/stitch-narration` (ffmpeg)
Swap Hedra's baked audio for the clean local ElevenLabs mp3.

https://github.com/user-attachments/assets/cb38d493-fcb4-45cc-9e56-34ed0720e2cb

### 10. Captions — `/caption-video`
WhisperX word-level transcription + auto-picked style preset, scored against the background.

https://github.com/user-attachments/assets/c4a164fa-5b65-4566-b7ac-f2c248588c6f

### 11. Background music — `/overlay-music`
Ducked random track from the `music/` library, with fade-in / fade-out under the narration.

https://github.com/user-attachments/assets/7f6f7bad-c77b-4862-b18d-eb6d94c1bd3b

### 12. Upload — `/upload-ad`
Pushes `final-with-music.mp4` to every configured platform, generates per-platform metadata, and writes the resulting URL back to `manifest["uploads"][platform]`. Each platform's metadata + URL is tracked independently, so re-running is safe — already-uploaded targets skip. Today YouTube and X are live; Meta (Instagram/Facebook) and Pinterest run through the same flow but with platform-specific uploader scripts under `uploader/`.

Supporting skill: `/import-music` — ingest local mp4 recordings into the `music/` library that stage 11 picks from.

## The Storefront

Every CTA across every platform funnels through [`theluxedrawer.com`](https://theluxedrawer.com) — our Next.js site (`website/`) owns the redirect to Amazon, so we control routing, analytics, and link rot.

<p align="center">
  <img width="720" alt="theluxedrawer home page hero" src="https://github.com/user-attachments/assets/03ed6acf-1fee-4d0d-9442-30add442ea4b" />
</p>

<p align="center">
  <img width="720" alt="theluxedrawer product storefront" src="https://github.com/user-attachments/assets/9fd4b5d8-a229-4c5c-a2fc-6a520bbe3c2f" />
</p>

## Published Examples

One product, four platforms — picked from `products/amika-aura-hair-and-body-mist.../manifest.json`:

| Platform | URL |
|---|---|
| YouTube | https://youtu.be/8ukBc7rg9KE |
| Instagram | https://www.instagram.com/reels/DYSevZwAoJL/ |
| Facebook | https://www.facebook.com/reel/2731583150551450 |
| X | https://x.com/theluxedrawer/status/2054224433208840328 |

What the same product looks like once it lands on each social platform:

<p align="center">
  <img width="300" alt="Instagram post" src="https://github.com/user-attachments/assets/b6553d79-0be6-467d-bd13-6b63948ac638" />
  <img width="300" alt="Facebook post" src="https://github.com/user-attachments/assets/77d634a8-e957-496b-8dd4-abc96b62d7d7" />
  <img width="240" alt="X post" src="https://github.com/user-attachments/assets/1a760835-923a-42fc-a746-bbe1ea6c0945" />
</p>

## Layout

| Path | Purpose |
|---|---|
| `characters/` | Per-channel character refs + pinned voice (the host identity) |
| `extensions/amazon-product-page-scraper/` | Chrome extension — scrapes Amazon product pages into a Downloads dump |
| `extensions/youtube-paid-promo-flagger/` | Chrome extension — flips the YouTube "paid promotion" toggle automatically |
| `products/` | Per-product folders — manifest + all generated media (gitignored) |
| `hedra/` | Hedra API client — starting-image + Avatar video generation |
| `narration/` | ElevenLabs TTS generation |
| `captioning/` | WhisperX transcription + word-level caption renderer + style presets |
| `music/` | Background music library — `<adjective>-<animal>.mp3` (gitignored) |
| `scripts/` | Per-stage CLIs: `import_music`, `stitch_narration`, `overlay_music`, `upload_ad`, `status`, `credits`, `script_lint`, `sanitize_slugs`, `apply_scripts` |
| `uploader/` | Per-platform upload CLIs — `youtube/`, `meta/` (Instagram + Facebook), `pinterest/`, `x/` |
| `website/` | Public Next.js site — `theluxedrawer.com`. Hosts the `/p/<slug>` product pages that every video CTA funnels through |
| `dashboard/` | Private Next.js dashboard — Supabase-backed pipeline analytics + per-product status |
| `assets/` | Branding + character assets (gitignored) |
| `.claude/skills/` | Slash-command wrappers for every pipeline stage |
| `docs/` | Channel strategy, niche, compliance rules, per-platform upload playbooks |

## Stack

- **Starting frame + talking head:** Hedra (image-gen + Character-3 avatar)
- **TTS:** ElevenLabs Turbo v2.5 (channel voice pinned per character)
- **Audio restitch:** ffmpeg (swap Hedra's baked audio for the clean ElevenLabs mp3)
- **Captions:** WhisperX word-level transcription + local caption renderer with auto-picked style presets
- **Background music:** local `music/` library, ducked under narration
- **Upload:**
  - YouTube — Data API v3 via `uploader/youtube/upload.py`
  - X — v2 API via `uploader/x/upload.py`
  - Instagram + Facebook — Graph API via `uploader/meta/` (in progress)
  - Pinterest — Pinterest API via `uploader/pinterest/` (in progress)
- **Funnel:** `theluxedrawer.com/p/<slug>` (Next.js) → Amazon affiliate link. Every platform CTA points at our site so we control the redirect.

## Compliance

- Every description: "As an Amazon Associate I earn from qualifying purchases."
- YouTube "paid promotion" toggle ON for every Short (automated by `extensions/youtube-paid-promo-flagger/`)
- Affiliate funnel in the first line of the description on every platform (Shorts can't link in-video)
- All distribution channels stay public
- Per-platform upload playbooks live in `docs/upload-meta.md`, `docs/upload-pinterest.md`, `docs/upload-x.md`
