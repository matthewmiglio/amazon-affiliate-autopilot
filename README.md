# amazon-affiliate-autopilot

End-to-end pipeline that turns Amazon affiliate products into AI talking-head YouTube Shorts — one consistent host, one product per video, affiliate link in the description.

Each pipeline stage is a slash-command skill — idempotent, manifest-driven, and accepts a single slug, a comma-list, or `--all-needing`.

## The Character

A pinned character folder defines the host. Same face, same voice across every Short.

<p align="center">
  <img width="240" alt="Host pose 1" src="https://github.com/user-attachments/assets/2901efcc-9d07-41c1-baf3-c7bf02eeef79" />
  <img width="240" alt="Host pose 2" src="https://github.com/user-attachments/assets/6203d864-c59a-4319-8dd6-3976c00ab58d" />
  <img width="240" alt="Host pose 3" src="https://github.com/user-attachments/assets/7cc1e1a5-75ad-420d-a51f-42c7d1dd3a5a" />
</p>

## Lifestyle Frames

Examples of stage-3 starting frames across different products.

<p align="center">
  <img width="240" alt="Lifestyle 1" src="https://github.com/user-attachments/assets/6761df5f-e847-4810-bb93-359bc568dbac" />
  <img width="240" alt="Lifestyle 2" src="https://github.com/user-attachments/assets/20c74fdf-fea8-4a36-928e-f3b4930c15a9" />
  <img width="240" alt="Lifestyle 3" src="https://github.com/user-attachments/assets/b73cd8b7-8fbd-4f40-a3cd-b4976683235d" />
</p>

## Pipeline

### 1. Character refs
Pin a host face + voice per channel — `characters/<channel>/`. See "The Character" above.

### 2. Scrape Amazon — `amazon-product-page-scraper/` (Chrome ext)
Pulls link + product details + main image into `products/<slug>/manifest.json`.

<img width="200" src="https://github.com/user-attachments/assets/5a0ae8f4-49dd-4a10-9fc4-863b468c718b" />

### 3. Starting frame — `/generate-starting-image`
Hedra image-gen produces a 9:16 lifestyle composite with the host holding the product.

<img width="240" src="https://github.com/user-attachments/assets/7a4e8a47-a587-4ad3-b42e-67df9b13f9e4" />

### 4. Narration script — `/write-script`
15–20s podcast-tone voiceover, written into `script-raw-text` in the manifest.

> "Listen, your cleanser matters way more than people give it credit for. The Clé de Peau Beauté Clarifying Cleansing Foam — made in Japan, built around their Skin Intelligence research that's been their signature for over forty years. Clears the day off without that tight, stripped feeling. An affordable luxury, honestly. Tap the link to grab it on Amazon."

### 5. Narration audio — `/generate-narration`
ElevenLabs TTS with the channel voice pinned per character.

https://github.com/user-attachments/assets/fb628d39-0bb2-43f3-8910-8ee74dab9202

### 6. UGC talking head — `/generate-hedra-video`
Starting image + narration → Hedra Avatar. Audio is baked into the mp4 at low quality at this stage — that's fixed in the next step.

https://github.com/user-attachments/assets/b076a779-15fd-453d-8c82-2605f3636edf

### 7. Audio restitch — `/stitch-narration` (ffmpeg)
Swap Hedra's baked audio for the clean local ElevenLabs mp3.

https://github.com/user-attachments/assets/cb38d493-fcb4-45cc-9e56-34ed0720e2cb

### 8. Captions — `/caption-video`
WhisperX word-level transcription + auto-picked style preset, scored against the background.

https://github.com/user-attachments/assets/c4a164fa-5b65-4566-b7ac-f2c248588c6f

### 9. Background music — `/overlay-music`
Ducked random track from the `music/` library, with fade-in / fade-out under the narration.

https://github.com/user-attachments/assets/7f6f7bad-c77b-4862-b18d-eb6d94c1bd3b

## Layout

| Path | Purpose |
|---|---|
| `characters/` | Per-channel character refs + pinned voice (the host identity) |
| `amazon-product-page-scraper/` | Chrome extension — scrapes Amazon product pages into manifests |
| `products/` | Per-product folders — manifest + all generated media (gitignored) |
| `hedra-vid-gen/` | Hedra API client — starting-image + avatar-video generation |
| `narration/` | ElevenLabs TTS generation |
| `captioning/` | WhisperX transcription + word-level caption renderer + style presets |
| `music/` | Background music library (`<adjective>-<animal>.mp3`) |
| `scripts/` | Per-stage CLIs: import_music, stitch_narration, overlay_music, upload_ad, status |
| `uploader/` | Multi-channel YouTube OAuth + upload CLI |
| `.claude/skills/` | Slash-command wrappers for every pipeline stage |
| `docs/` | Channel strategy, niche, compliance rules |

## Stack

- **Starting frame + talking head:** Hedra (image-gen + Character-3 avatar)
- **TTS:** ElevenLabs Turbo v2.5 (channel voice pinned per character)
- **Audio restitch:** ffmpeg (swap Hedra's baked audio for the clean ElevenLabs mp3)
- **Captions:** WhisperX word-level transcription + local caption renderer with auto-picked style presets
- **Background music:** local `music/` library, ducked under narration
- **Upload:** YouTube Data API via `uploader/upload.py`

## Compliance

- Every description: "As an Amazon Associate I earn from qualifying purchases."
- YouTube "paid promotion" toggle ON for every Short
- Affiliate link in the first line of the description (Shorts can't link in-video)
- Channel must stay public
