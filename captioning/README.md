# captioning

Burn styled, word-level captions onto an mp4. Uses **WhisperX** for ASR
with per-word alignment and **ffmpeg + ASS subtitles** for rendering.

## Layout

```
captioning/
  pyproject.toml
  cli.py          # argparse CLI -> transcribe + render
  transcribe.py   # WhisperX word-level transcription
  render.py       # ASS builder + ffmpeg burn-in
```

Flat module layout — run scripts directly from this folder, no package
import path needed.

## Requirements

- Python 3.11+
- `ffmpeg` on PATH
- A CUDA GPU is used automatically when available; otherwise CPU
  (`int8`) is used as a fallback.
- The font passed to `--font` must be installed on the system.

## Install

```powershell
poetry install
```

## Usage

Caption a video using all defaults (Inter, 72px, white-on-black,
bottom-aligned, per-word karaoke style):

```powershell
poetry run python cli.py --video input.mp4 --out output.mp4
```

Reuse a previously saved transcription (skips ASR):

```powershell
poetry run python cli.py `
  --video input.mp4 `
  --out output.mp4 `
  --timestamps cached.json
```

Save the transcription as you render so the next pass is instant:

```powershell
poetry run python cli.py `
  --video input.mp4 `
  --out output.mp4 `
  --save-timestamps cached.json
```

## Common style flags

| Flag | What it does |
| ---- | ------------ |
| `--font NAME` | Font family (must be installed) |
| `--font-size N` | Pixel size at the configured play resolution |
| `--color RRGGBB` | Text fill color |
| `--outline-color RRGGBB` | Stroke color |
| `--outline-width N` | Stroke width in px |
| `--shadow N` | Drop-shadow distance |
| `--box` | Draw an opaque background box behind text |
| `--alignment` | `top`/`middle`/`bottom` (+ `-left`/`-right`) |
| `--margin-v N` | Vertical margin from edge (default 300) |
| `--play-res-x / --play-res-y` | Target render resolution (default 1080x1920) |
| `--no-uppercase` | Keep original casing |
| `--per-segment` | One event per segment instead of per word |

Run `python cli.py --help` for the full list.

## How it fits together

1. `cli.py` parses flags and resolves a `CaptionStyle`.
2. `transcribe.transcribe_video()` extracts mono 16 kHz audio with
   ffmpeg, runs WhisperX, then aligns segments to word-level timestamps.
3. `render.build_ass()` turns those segments into an ASS script using
   the chosen style.
4. `render.render()` invokes ffmpeg with the `ass` video filter to burn
   captions onto the video, copying the original audio stream.
