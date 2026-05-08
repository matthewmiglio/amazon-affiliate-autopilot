---
name: stitch-narration
description: Replace the bad baked-in audio of a product's `raw-speaker-video.mp4` with the clean Hedra `narration.mp3` via ffmpeg, producing `stitched-narration-speaker-video.mp4`. Reads/writes per-product manifest.json and keeps `stitched-narration-video-path` in sync. Idempotent — never re-runs ffmpeg when the output already exists, but does fix a manifest that's out of sync. Accepts a single slug, a comma-list, or `--all-needing`. Use when the user runs /stitch-narration or asks to "stitch narration for X", "swap the audio in the AI video", "overlay the Hedra mp3", or similar.
---

# stitch-narration

Take one or more product slugs, mux each product's `narration.mp3` (clean Hedra TTS) over its `raw-speaker-video.mp4` (AI talking-head with bad baked-in audio), and write `stitched-narration-speaker-video.mp4` into the same product folder. Keep `manifest.json["stitched-narration-video-path"]` aligned. Idempotent and free to re-run — ffmpeg only runs when the output is genuinely missing.

## Inputs

`/stitch-narration <slugs>` where `<slugs>` is one of:

- A single slug: `/stitch-narration concealer-spf-27`
- A comma-list: `/stitch-narration concealer-spf-27, lip-glorifier`
- The literal flag `--all-needing` to target every product missing a stitched video.

If the user provides nothing, ask once. Don't guess.

## State machine (per product)

Four cases, ranked by what's already on disk and in the manifest:

| `stitched-narration-speaker-video.mp4` exists? | manifest has `"stitched-narration-speaker-video.mp4"`? | Action | Cost |
|---|---|---|---|
| ✅ | ✅ | Do nothing | free |
| ✅ | ❌ | Fix manifest only — set `stitched-narration-video-path` to `"stitched-narration-speaker-video.mp4"` | free |
| ❌ | ✅ | Run ffmpeg, write mp4 (manifest already correct) | one local ffmpeg run |
| ❌ | ❌ | Run ffmpeg, write mp4, set `stitched-narration-video-path` | one local ffmpeg run |

Pre-flight bail per product (FAIL row):
- `raw-speaker-video.mp4` missing → `"missing raw-speaker-video.mp4 — generate the AI talking-head video first"`
- `narration.mp3` missing → `"missing narration.mp3 — run /generate-narration first"`

## Workflow

1. **Resolve slugs.** Validate each `products/<slug>/manifest.json` exists. For `--all-needing`, the helper script shells into `python scripts/status.py --needs-stitched-narration --json` for the list.
2. **Verify ffmpeg.** The script tries `C:\ffmpeg\bin\ffmpeg.exe` first, then falls back to `ffmpeg` on PATH. Hard-fail if neither resolves.
3. **Delegate to `scripts/stitch_narration.py`.** Run:
   ```
   python scripts/stitch_narration.py --products <comma-joined-slugs>
   # or
   python scripts/stitch_narration.py --all-needing
   ```
   The script implements the full state machine above. Each row of output is `<slug>\t<STATUS>\t<detail>` where STATUS ∈ {OK, FIXED, SKIP, FAIL}.
4. **Surface the summary** the script prints (e.g. `5 stitched, 2 manifest-fixed, 1 skipped, 0 failed.`). On any FAIL, repeat that row to the user with the reason.
5. **Do NOT** add `--overwrite` unless the user explicitly asks to re-stitch.

## Existing helpers (do not duplicate)

- `scripts/stitch_narration.py` — owns the actual ffmpeg pipeline (mux video stream + AAC narration, `-shortest`, `+faststart`), manifest sync, the four-state idempotent logic, and batch slug resolution.
- `scripts/status.py --needs-stitched-narration --json` — feeds `--all-needing`.

## ffmpeg command (for reference)

```
ffmpeg -y -i raw-speaker-video.mp4 -i narration.mp3 \
  -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 192k \
  -shortest -movflags +faststart \
  stitched-narration-speaker-video.mp4
```

Video stream is copied (no re-encode); narration is re-encoded to 192k AAC. Output ends at the shorter of the two streams.

## Out of scope

- **No narration generation.** If `narration.mp3` is missing, FAIL and tell the user to run `/generate-narration` first.
- **No video generation.** If `raw-speaker-video.mp4` is missing, FAIL and tell the user to render the AI talking-head video first.
- **No audio normalization, ducking, or cleanup.** Just a clean mux + AAC re-encode.
- **No regeneration of good output.** Honor existing stitched mp4s strictly; the only file mutation is creating a missing mp4 or touching the manifest's `stitched-narration-video-path` field.

## Re-runs

Safe and free. Existing-output products do nothing; misaligned manifests get fixed in O(1) IO. Only genuinely-missing stitched videos invoke ffmpeg.

## Cost note

Local-only — no API spend, no third-party calls. Re-running across the whole catalog is free.
