# Amazon Affiliate Video Pipeline

End-to-end flow for turning an Amazon product into a posted YouTube Short. Each stage (except scraping) has a dedicated skill in this folder.

| # | Stage | Skill |
|---|-------|-------|
| 1 | Scrape Amazon for a product | _(external — no skill)_ |
| 2 | Import scraped data into `products/` | `import-referral-data` |
| 3 | Write the video-gen prompt | `generate-video-prompt` |
| 4 | Write the narration script | `write-script` |
| 5 | Produce narration mp3 (ElevenLabs) | `generate-narration` |
| 6 | Produce 9:16 starting image (Hedra) | `generate-starting-image` |
| 7 | Produce raw speaker video (Hedra) | `generate-hedra-video` |
| 8 | Stitch clean narration onto the video | `stitch-narration` |
| 9 | Burn word-level captions | `caption-video` |
| 10 | Overlay background music | `overlay-music` |
| 11 | Upload to YouTube Shorts | `upload-ad` |

Supporting skill:
- `import-music` — ingest mp4 recordings into the `music/` library used by `overlay-music`.

Step 1 (the actual Amazon scrape) is done outside this repo; `import-referral-data` is what brings the scrape output in.
