---
name: overlay-music
description: Mix a random track from `music/` under a product's `captioned-video.mp4`, ducked below the narration with fade-in / fade-out, and write `final-with-music.mp4` into the same product folder. Manifest gets `final-with-music-video-path` and `background-music-track`. Use when the user runs /overlay-music or asks to "add bg music to X", "lay music under the captioned video", or similar.
---

# overlay-music

Pick a random song from the project's `music/` library, lay it under the product's captioned video at a level that keeps the voice on top, fade it in and out, and write `final-with-music.mp4`.

## Inputs

`/overlay-music <product>` where `<product>` is one of:

- A slug under `products/`: `/overlay-music cle-de-peau-clarifying-cleansing-foam-for-women-4-2-oz-cleanser`
- An absolute path to a product folder: `/overlay-music C:\My_Files\my_programs\amazon-affiliate\products\<slug>`

If the user provides nothing, ask once. Don't guess.

## Pre-flight bail

- `products/<slug>/captioned-video.mp4` missing → FAIL with `"missing captioned-video.mp4 - run /caption-video first"`. Do **not** continue.
- No mp3s in `music/` → FAIL with `"no music tracks - run /import-music first"`.
- No music track in `music/` is at least as long as the video → FAIL.

## Workflow

1. **Resolve the product folder** (slug or absolute path).
2. **Delegate to `scripts/overlay_music.py`.** Run:
   ```
   python scripts/overlay_music.py --product <slug-or-path>
   ```
   The script:
   - probes the stitched video's duration
   - picks a random `.mp3` from `music/` whose duration ≥ video duration
   - measures mean dBFS of the narration video (`volumedetect`) and of the chosen music
   - sets the music gain so its mean lands ~14 dB below the voice
   - mixes with `amix`, applies a 1.5s fade-in and 2.0s fade-out
   - copies the video stream (no re-encode), re-encodes audio to 192k AAC
   - writes `final-with-music.mp4` and updates manifest fields
     `final-with-music-video-path` and `background-music-track`
3. **Surface the row** the script prints (`<slug>\t<STATUS>\t<detail>`).
4. **Do NOT** add `--overwrite` unless the user explicitly asks to re-render.

## State machine (per product)

| `final-with-music.mp4` exists? | manifest `final-with-music-video-path` set? | Action |
|---|---|---|
| ✅ | ✅ | SKIP |
| ✅ | ❌ | FIXED — manifest synced, no ffmpeg |
| ❌ | * | OK — ffmpeg runs, manifest written |

## Existing helpers (do not duplicate)

- `scripts/overlay_music.py` — owns track selection, loudness measurement, mixing filtergraph, manifest sync.

## ffmpeg filtergraph (for reference)

```
[1:a]volume=<gainDB>dB,afade=t=in:st=0:d=1.5,afade=t=out:st=<dur-2>:d=2.0[bg];
[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]
```

Map `0:v` (copy), `[aout]` (AAC 192k). `-shortest` plus `duration=first` keeps the output exactly the length of the narration video — music tail is cut by the fade-out.

## Out of scope

- **No music import.** If `music/` is empty, FAIL and tell the user to run `/import-music` first.
- **No narration generation, video generation, or stitching.** Those are upstream.
- **No sidechain compression / ducking around speech.** The static gap (-14 dB under voice mean) plus fades is intentionally simple.

## Cost note

Local-only — no API spend.
