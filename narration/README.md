# narration

Hedra TTS narration generator for Amazon affiliate products.

Reads `script-raw-text` from each product's `manifest.json`, generates an mp3
via Hedra, writes it to `<product>/narration.mp3`, and updates the manifest.

Script authoring is handled separately by the `/write-script` skill — this
tool refuses to run if `script-raw-text` is empty.

## Setup

```bash
cd narration
poetry install
```

Set keys in `.env` (gitignored):

```
HEDRA_API_KEY=<from https://hedra.com/api-profile, requires Creator plan>
HEDRA_VOICE_ID=<leave blank until you've picked one>
```

## Pick a voice (one-time)

```bash
poetry run python list_voices.py
poetry run python list_voices.py --language English
```

Copy a `voice_id` into `HEDRA_VOICE_ID` in `.env`.

## Generate narrations

```bash
# single product
poetry run python generate.py --products concealer-spf-27

# multiple products
poetry run python generate.py --products concealer-spf-27,lip-glorifier

# every product missing narration
poetry run python generate.py --all-needing

# regenerate even if narration.mp3 exists
poetry run python generate.py --products concealer-spf-27 --overwrite
```

`--all-needing` shells out to `../scripts/status.py --needs-narration --json`
to discover the slug list.

## Notes

- Hedra TTS calls burn from the same credit pool as their video generations.
- The poll loop waits up to 120s per generation; TTS usually completes in seconds.
