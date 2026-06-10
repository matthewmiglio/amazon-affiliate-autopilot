# amazon-affiliate

Pipeline that turns Amazon affiliate products into short-form video ads and publishes them across YouTube, Instagram, Facebook, and Pinterest. Per-product state lives in `products/<slug>/manifest.json`; each pipeline stage reads/writes its own keys there and drops artifacts (images, audio, video) into the same folder.

## Lay of the land

- `assets/` — branding images and character source images (used as Hedra refs, etc.)
- `captioning/` — module for burning word-level captions onto stitched narration videos
- `cron/` — local cron/scheduled-task setup for upload jobs and other recurring work (gitignored runtime state)
- `dashboard/` — Next.js app for analytics and pipeline visibility
- `docs/` — project documentation (gitignored)
- `extensions/` — Chrome extensions that support various parts of the app (e.g. Amazon scraping)
- `hedra/` — wrapper around the Hedra API for image generation (starting frames) and Avatar talking-head video generation
- `music/` — background-music mp3 library, mixed under final ad videos
- `narration/` — ElevenLabs TTS module; reads `script-raw-text` from manifests, writes `narration.mp3`
- `products/` — one folder per product slug; the source of truth for pipeline progress. Each folder holds `manifest.json` plus its stage artifacts (`starting-pic.png`, `narration.mp3`, `raw-speaker-video.mp4`, `stitched-narration-speaker-video.mp4`, `captioned-video.mp4`, `final-with-music.mp4`)
- `scripts/` — utility scripts
- `tests/` — tests (gitignored)
- `uploader/` — per-platform uploaders (YouTube live; Meta + Pinterest in progress). Reads `uploads.<platform>.metadata` from the manifest and writes back URLs + uploaded flags
- `website/` — public-facing landing page / catalog listing the affiliate products

## Pipeline order

1. `/import-referral-data` — ingest scraped products into `products/`
2. `/write-script` — draft narration script into `manifest.script-raw-text`
3. `/generate-starting-image` — Hedra image → `starting-pic.png`
4. `/generate-video-prompt` — author the video-gen prompt (manifest only)
5. `/generate-narration` — ElevenLabs → `narration.mp3`
6. `/generate-hedra-video` — Hedra Avatar → `raw-speaker-video.mp4`
7. `/stitch-narration` — ffmpeg swap audio → `stitched-narration-speaker-video.mp4`
8. `/caption-video` — WhisperX + burned captions → `captioned-video.mp4`
9. `/overlay-music` — duck bg music under narration → `final-with-music.mp4`
10. `/upload-ad` — publish to all configured platforms

All stage skills are idempotent — they skip when their output already exists and self-heal the manifest if it's out of sync.
