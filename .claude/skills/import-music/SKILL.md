---
name: import-music
description: Import mp4 recordings (single file or folder) into the project's music library as background-music mp3s. Strips leading/trailing silence and saves each track as `music/<adjective>-<animal>.mp3` with a fresh slug. Use when the user runs /import-music or asks to "import music from <folder>", "ingest these recordings as bg music", or similar.
---

# import-music

Take a folder of .mp4s, or a single .mp4, and turn each one into a clean background-music mp3 in `music/`. The conversion drops the video stream, trims silence at both ends, and gives the file a memorable two-word slug (e.g. `prickly-octopus.mp3`). On a successful import, the source `.mp4` is deleted so the input folder doesn't accumulate already-ingested recordings. Failed conversions leave the source mp4 untouched.

## Inputs

`/import-music <path>` where `<path>` is one of:

- A folder of mp4s: `/import-music D:\my_files\my_videos\obs_recordings`
- A single mp4: `/import-music D:\stuff\track.mp4`

If the user provides nothing, ask once. Don't guess.

## Workflow

1. **Verify the path exists.** Hard-fail if it doesn't.
2. **Delegate to `scripts/import_music.py`.** Run:
   ```
   python scripts/import_music.py --src "<path>"
   ```
   The script handles directory-vs-file detection, silence trimming, slug generation, and dedupe (it never reuses an existing slug in `music/`).
3. **Surface the summary** the script prints (`<source>\t<STATUS>\t<detail>` rows + final tally `N imported, N skipped, N failed.`).
4. On any FAIL, repeat that row with the reason.

## Existing helpers (do not duplicate)

- `scripts/import_music.py` — owns ffmpeg pipeline (mp4 → mp3 with `silenceremove` on both ends), slug coining, and the music/ output directory.

## ffmpeg silence trim (for reference)

```
ffmpeg -y -i input.mp4 -vn \
  -af "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB:\
       stop_periods=1:stop_silence=0.5:stop_threshold=-45dB:detection=peak,\
       areverse,\
       silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB:detection=peak,\
       areverse" \
  -c:a libmp3lame -b:a 192k output.mp3
```

The `areverse` sandwich is what reliably strips trailing silence — `silenceremove` only operates from the front, so we trim, reverse, trim again, reverse back.

## Out of scope

- **No loudness normalization** of the resulting music. Bed level is decided at overlay time, not here.
- **No re-import / dedupe by content.** Files coming in get fresh slugs; if the user re-imports the same folder, they will get new slugs (cheap to delete by hand). Note that successful imports delete the source mp4, so a re-import of the same folder generally finds nothing new.

## Cost note

Local-only — no API spend. Re-running on the same folder costs only ffmpeg time.
