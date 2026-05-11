---
name: caption-video
description: Auto-pick a caption style and burn word-level captions onto a product's stitched-narration video. For each slug, the script transcribes the stitched mp4 with WhisperX, samples background colors at the top + middle regions, scores every preset by WCAG contrast, randomly picks one of the top three, renders `captioned-video.mp4` into the product folder, and keeps `captioned-video-path` in sync. Idempotent — never re-runs when the output already exists, but does fix a manifest that's out of sync. Accepts a single slug, a comma-list, or `--all-needing`. Use when the user runs /caption-video or asks to "caption the video for X", "burn captions on these products", "add subtitles to the stitched video", or similar.
---

# caption-video

## Background invocation gotcha

If you launch the captioner as a backgrounded bash task, **use the absolute path** — backgrounded shells reset cwd to the repo root, so `cd captioning && poetry run ...` will fail. Use `cd /c/My_Files/my_programs/amazon-affiliate/captioning && poetry run python caption_video.py --products <slug>`. Foreground invocations are fine.

Take one or more product slugs, transcribe each product's `stitched-narration-speaker-video.mp4`, choose a caption preset whose color contrasts well with that specific video's background, render burned-in word-level captions, and write `captioned-video.mp4` into the same product folder. Keep `manifest.json["captioned-video-path"]` aligned. Idempotent and free to re-run — rendering only fires when the output is genuinely missing.

## Inputs

`/caption-video <slugs>` where `<slugs>` is one of:

- A single slug: `/caption-video concealer-spf-27`
- A comma-list: `/caption-video concealer-spf-27, lip-glorifier`
- The literal flag `--all-needing` to target every product missing a captioned video.

If the user provides nothing, ask once. Don't guess.

## State machine (per product)

| `captioned-video.mp4` exists? | manifest has `"captioned-video.mp4"`? | Action | Cost |
|---|---|---|---|
| ✅ | ✅ | Do nothing | free |
| ✅ | ❌ | Fix manifest only — set `captioned-video-path` to `"captioned-video.mp4"` | free |
| ❌ | ✅ | Transcribe (cached), pick style, render | one local WhisperX + ffmpeg pass |
| ❌ | ❌ | Same as above + manifest update | one local WhisperX + ffmpeg pass |

Pre-flight bail per product (FAIL row):
- `manifest.json` missing → `"no manifest.json at <path>"`
- `stitched-narration-speaker-video.mp4` missing → `"missing stitched-narration-speaker-video.mp4 — run /stitch-narration first"`

## Workflow

1. **Resolve slugs.** Validate each `products/<slug>/manifest.json` exists. For `--all-needing`, the helper script shells into `python scripts/status.py --needs-captioned --json` for the list.
2. **Verify ffmpeg + ffprobe.** `style_select.find_ffmpeg()` / `find_ffprobe()` try `C:\ffmpeg\bin\ffmpeg.exe` (and `.../ffprobe.exe`) first, then fall back to PATH. Hard-fail if neither resolves.
3. **Delegate to `captioning/caption_video.py`.** Run from the captioning poetry env so WhisperX is on the path:
   ```
   cd captioning
   poetry run python caption_video.py --products <comma-joined-slugs>
   # or
   poetry run python caption_video.py --all-needing
   ```
   The script implements the full state machine above. Each row of output is `<slug>\t<STATUS>\t<detail>` where STATUS ∈ {OK, FIXED, SKIP, FAIL}.
4. **Surface the summary** the script prints (e.g. `5 captioned, 2 manifest-fixed, 1 skipped, 0 failed.`). On any FAIL, repeat that row to the user with the reason.
5. **Do NOT** add `--overwrite` unless the user explicitly asks to re-caption (a re-roll picks a fresh random style from the top-3 contrast band).

## Existing helpers (do not duplicate)

- `captioning/caption_video.py` — owns the per-slug pipeline (pre-flight, transcription cache, style selection, render, manifest sync).
- `captioning/style_select.py` — pure scoring logic: `sample_frame_avgs`, `region_avg`, `wcag_contrast`, `pick_best`.
- `captioning/presets.py` — the 8 surviving caption styles (5 top, 3 middle).
- `captioning/render.py` — the ffmpeg + ASS burn-in.
- `captioning/transcribe.py` — WhisperX wrapper.
- `scripts/status.py --needs-captioned --json` — feeds `--all-needing`.

## How style selection works

1. Sample 3 frames evenly across the middle of the duration (avoids leader/tail freeze frames).
2. For each candidate region (`top`, `middle`), crop a horizontal band, scale to 1×1 with ffmpeg → that pixel IS the region's average RGB at that moment.
3. Aggregate the 3 per-frame averages per region into one final (r,g,b) per region.
4. For every preset, score = max(WCAG-contrast(text, bg), WCAG-contrast(outline, bg)) where bg is the avg color at the preset's placement.
5. Sort scores, take the top 3, pick one at random. Same input video can re-roll a different style with `--overwrite`.

## Caching

`captioning/caption_video.py` writes `products/<slug>/captions.json` after the first WhisperX run for that stitched video. Re-runs (including `--overwrite`) skip transcription if this file exists. Delete it manually if you want to force a fresh transcription.

## Out of scope

- **No narration generation.** If `narration.mp3` is missing, the upstream `/stitch-narration` skill catches it.
- **No raw-video generation.** Same — handled upstream.
- **No music overlay.** `/overlay-music` still mixes onto `stitched-narration-speaker-video.mp4`. (If you later want music to layer over the captioned video instead, that's a one-line change in `/overlay-music`.)
- **No manual style override** in this skill. The algorithm decides. For interactive style picking, use `captioning/cli.py` directly with `--font`, `--color`, etc.
- **No regeneration of good output.** Existing `captioned-video.mp4` files are honored; only missing ones invoke the pipeline.

## Re-runs

Safe and free. Existing-output products do nothing; misaligned manifests get fixed in O(1) IO. Only genuinely-missing captioned videos invoke transcription + render. `--overwrite` re-rolls a (possibly new) random style from the top-3 contrast band.

## Cost note

Local-only — no API spend, no third-party calls. WhisperX runs locally; ffmpeg runs locally. Re-running across the whole catalog is free aside from compute time.
