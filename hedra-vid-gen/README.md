# hedra-vid-gen

Hedra Platform API tools for the Amazon affiliate pipeline. Two subfolders,
one shared `.env` / `pyproject.toml` / `_common.py` at the top.

```
hedra-vid-gen/
├── .env                  # HEDRA_API_KEY + a few model/asset pins (see below)
├── pyproject.toml
├── poetry.lock
├── _common.py            # shared API helpers (assets, generations, polling, download)
├── avatar-video/
│   └── generate.py       # talking-head video gen (image+audio -> mp4)
└── starting-image/
    ├── generate.py       # character ref(s) + product image -> 9:16 PNG
    ├── prompt_builder.py # ports /generate-starting-image SKILL.md axes
    └── list_models.py    # list Hedra models so you can pin an image model id
```

## Setup

```
cd hedra-vid-gen
poetry install --no-root
```

`.env` (gitignored):

```
HEDRA_API_KEY=sk_hedra_...
HEDRA_AVATAR_MODEL_ID=26f0fc66-152b-40ab-abed-76c43df99bc8
HEDRA_IMAGE_MODEL_ID=                 # optional — auto-discovers Nano Banana Pro if blank
```

Character references are pulled automatically: 3 random images from
`assets/character/` per generation, seeded by `(slug, reroll)` so re-runs of
the same slug always pick the same 3 (stable), but different slugs almost
never collide on the same trio.

## avatar-video — talking-head video

```
cd hedra-vid-gen
poetry run python avatar-video/generate.py --products <slug>
poetry run python avatar-video/generate.py --all-needing
poetry run python avatar-video/generate.py --products <slug> --overwrite
```

For each slug:
1. Reads `products/<slug>/manifest.json`
2. Uploads `lifestyle-1.png` (start keyframe) + `narration.mp3` (audio)
3. POSTs an Avatar generation at 9:16 / 720p, duration auto-matched to the audio
4. Downloads to `products/<slug>/raw-speaker-video.mp4`
5. Sets `manifest.json["raw-speaker-video-path"] = "raw-speaker-video.mp4"`

Idempotent — existing `raw-speaker-video.mp4` is never re-rendered without `--overwrite`.

## starting-image — composed UGC starting frame

```
cd hedra-vid-gen
poetry run python starting-image/list_models.py --image-only        # one-time setup
poetry run python starting-image/generate.py --products <slug>
poetry run python starting-image/generate.py --all-needing
poetry run python starting-image/generate.py --products <slug> --overwrite
poetry run python starting-image/generate.py --products <slug> --output-dir /some/dir
```

For each slug:
1. Picks 3 random character references from `assets/character/` (seeded by `(slug, reroll)`) → uploads each as an image asset
2. Resolves the product image (`manifest.main-product-image-path` or `main.{png,jpg,…}`) → upload
3. Builds a prompt with `prompt_builder.build_prompt(slug, manifest)` — picks one
   coherent combo from the SKILL.md axis table, seeded by slug so re-runs are stable
4. POSTs `/generations` with `type:"image"`, `reference_image_ids = [chars…, product]`,
   `aspect_ratio:"9:16"`, using `HEDRA_IMAGE_MODEL_ID`
5. Downloads to `products/<slug>/lifestyle-1.png` (default) and sets
   `manifest.json["lifestyle-image-path"]`. With `--output-dir` it writes to
   `<dir>/<slug>.png` and skips the manifest write — useful for benchmarking.

Idempotent — existing target file is never re-rendered without `--overwrite`.

## Cost

Every successful generation (video OR image) is billed against the Hedra account
behind `HEDRA_API_KEY`. SKIP and FIXED rows are free.
