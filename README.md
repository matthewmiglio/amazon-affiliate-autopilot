# amazon-affiliate-autopilot

End-to-end pipeline that turns Amazon affiliate products into AI talking-head Shorts — one consistent host, one product per video, affiliate funnel through `theluxedrawer.com/p/<slug>` → YouTube, Instagram, Facebook, Pinterest, and X.

Each pipeline stage is a slash-command skill — idempotent, manifest-driven, and accepts a single slug, a comma-list, or `--all-needing`.

## The Character

A pinned character folder defines the host. Same face, same voice across every Short.

<p align="center">
  <img width="240" alt="Host pose 1" src="https://github.com/user-attachments/assets/584dd08a-7946-48f7-9818-4d0783c72d5d" />
  <img width="240" alt="Host pose 2" src="https://github.com/user-attachments/assets/cf70e254-5141-43f6-b327-652cc3afff30" />
  <img width="240" alt="Host pose 3" src="https://github.com/user-attachments/assets/89671cef-ba2f-4e90-9df6-c64d38acd819" />
</p>

## Lifestyle Frames

Examples of starting frames across different products.

<p align="center">
  <img width="240" alt="Lifestyle 1" src="https://github.com/user-attachments/assets/6761df5f-e847-4810-bb93-359bc568dbac" />
  <img width="240" alt="Lifestyle 2" src="https://github.com/user-attachments/assets/20c74fdf-fea8-4a36-928e-f3b4930c15a9" />
  <img width="240" alt="Lifestyle 3" src="https://github.com/user-attachments/assets/b73cd8b7-8fbd-4f40-a3cd-b4976683235d" />
</p>

## Pipeline

Authoritative ordering lives in [`.claude/skills/PIPELINE.md`](.claude/skills/PIPELINE.md). Twelve stages, grouped into four phases.

### Asset gathering

<table>
  <tr>
    <td align="center" width="33%"><img width="220" alt="Character refs" src="https://github.com/user-attachments/assets/584dd08a-7946-48f7-9818-4d0783c72d5d" /><br/><sub><b>1. Character refs</b><br/>Pin a host face + voice per channel under <code>characters/&lt;channel&gt;/</code> — same identity across every Short.</sub></td>
    <td align="center" width="33%"><img width="220" alt="Scraped product image" src="https://github.com/user-attachments/assets/f2511824-5d75-49fd-a36a-58042e2453a9" /><br/><sub><b>2. Scrape Amazon</b><br/><code>extensions/amazon-product-page-scraper/</code> Chrome ext pulls link + details + main image into a Downloads dump.</sub></td>
    <td align="center" width="33%"><img width="220" alt="Scraped product folder" src="https://github.com/user-attachments/assets/40b91b20-fdf4-4593-8cf2-7197d21dd6c3" /><br/><sub><b>3. Import scraped data</b><br/><code>/import-referral-data</code><br/>Converts the scrape dump into <code>products/&lt;slug&gt;/manifest.json</code>. Filters &lt;10% commission, dedupes by ASIN.</sub></td>
  </tr>
</table>

### Scripting

<table>
  <tr>
    <td align="center" width="33%"><sub><b>4. Video-gen prompt</b><br/><code>/generate-video-prompt</code><br/>Authors the image-to-video animation prompt and writes it to <code>manifest["video-prompt"]</code>.</sub></td>
    <td align="center" width="33%"><sub><b>5. Narration script</b><br/><code>/write-script</code><br/>15–20s podcast-tone voiceover into <code>script-raw-text</code>.<br/><br/><i>"Listen, your cleanser matters way more than people give it credit for…"</i></sub></td>
    <td align="center" width="33%"><sub><b>6. Narration audio</b><br/><code>/generate-narration</code><br/>ElevenLabs TTS with the channel voice pinned per character.</sub></td>
  </tr>
</table>

### Video generation

<table>
  <tr>
    <td align="center" width="33%"><img width="220" alt="Starting frame" src="https://github.com/user-attachments/assets/7a4e8a47-a587-4ad3-b42e-67df9b13f9e4" /><br/><sub><b>7. Starting frame</b><br/><code>/generate-starting-image</code><br/>Hedra image-gen → 9:16 lifestyle composite of the host holding the product.</sub></td>
    <td align="center" width="33%"><video src="https://github.com/user-attachments/assets/b076a779-15fd-453d-8c82-2605f3636edf" width="220" controls muted></video><br/><sub><b>8. UGC talking head</b><br/><code>/generate-hedra-video</code><br/>Starting image + narration → Hedra Avatar. Audio baked low-quality — fixed next step.</sub></td>
    <td align="center" width="33%"><video src="https://github.com/user-attachments/assets/cb38d493-fcb4-45cc-9e56-34ed0720e2cb" width="220" controls muted></video><br/><sub><b>9. Audio restitch</b><br/><code>/stitch-narration</code> (ffmpeg)<br/>Swap Hedra's baked audio for the clean local ElevenLabs mp3.</sub></td>
  </tr>
</table>

### Post-production & distribution

<table>
  <tr>
    <td align="center" width="33%"><video src="https://github.com/user-attachments/assets/c4a164fa-5b65-4566-b7ac-f2c248588c6f" width="220" controls muted></video><br/><sub><b>10. Captions</b><br/><code>/caption-video</code><br/>WhisperX word-level transcription + auto-picked style preset, scored against the background.</sub></td>
    <td align="center" width="33%"><video src="https://github.com/user-attachments/assets/7f6f7bad-c77b-4862-b18d-eb6d94c1bd3b" width="220" controls muted></video><br/><sub><b>11. Background music</b><br/><code>/overlay-music</code><br/>Ducked random track from <code>music/</code>, fade-in / fade-out under the narration.</sub></td>
    <td align="center" width="33%"><img width="220" alt="Multi-platform upload" src="https://github.com/user-attachments/assets/b6553d79-0be6-467d-bd13-6b63948ac638" /><br/><sub><b>12. Upload</b><br/><code>/upload-ad</code><br/>Pushes the final mp4 to every configured platform, generates per-platform metadata, writes URLs back to <code>manifest["uploads"]</code>. YouTube + X live; Meta + Pinterest in progress.</sub></td>
  </tr>
</table>

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

<table>
  <tr>
    <td align="center"><img width="280" alt="Instagram post" src="https://github.com/user-attachments/assets/b6553d79-0be6-467d-bd13-6b63948ac638" /><br/><sub><b>Instagram</b></sub></td>
    <td align="center"><img width="280" alt="Facebook post" src="https://github.com/user-attachments/assets/77d634a8-e957-496b-8dd4-abc96b62d7d7" /><br/><sub><b>Facebook</b></sub></td>
    <td align="center"><img width="280" alt="X post" src="https://github.com/user-attachments/assets/1a760835-923a-42fc-a746-bbe1ea6c0945" /><br/><sub><b>X</b></sub></td>
  </tr>
</table>

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
