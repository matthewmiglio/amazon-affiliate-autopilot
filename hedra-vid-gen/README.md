# hedra-vid-gen

Generate Hedra **Avatar** (not Character-3) talking-head videos for product folders.

## Setup

```
cd hedra-vid-gen
poetry install --no-root
```

`.env` lives next to `generate.py` and holds:

```
HEDRA_API_KEY=sk_hedra_...
HEDRA_AVATAR_MODEL_ID=26f0fc66-152b-40ab-abed-76c43df99bc8
```

## Run

```
cd hedra-vid-gen
poetry run python generate.py --products <slug>[,<slug>,...]
poetry run python generate.py --all-needing
poetry run python generate.py --products <slug> --overwrite
```

Per product, the script:

1. Reads `products/<slug>/manifest.json`
2. Uploads `lifestyle-1.png` as the start keyframe and `narration.mp3` as the audio
3. Starts a Hedra Avatar generation at 9:16, 720p, duration auto-matched to the audio
4. Polls until complete, downloads the mp4 to `products/<slug>/raw-speaker-video.mp4`
5. Sets `manifest.json["raw-speaker-video-path"] = "raw-speaker-video.mp4"`

Idempotent — existing `raw-speaker-video.mp4` is never re-rendered unless `--overwrite` is passed.

## Cost

Each successful generation is billed against the Hedra account behind `HEDRA_API_KEY`.
Skipped/fixed rows cost nothing.
