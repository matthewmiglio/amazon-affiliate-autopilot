# narration

ElevenLabs narration generator for Amazon affiliate products.

Reads `script-raw-text` from each product's `manifest.json`, generates an mp3
via ElevenLabs, writes it to `<product>/narration.mp3`, and updates the manifest.

Script authoring is handled by the `/write-script` skill — this tool refuses
to run if `script-raw-text` is empty.

## Setup

```bash
cd narration
poetry install
```

`.env` (gitignored):
```
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=6u6JbqKdaQy89ENzLSju
```

Library voices (any voice from the ElevenLabs voice library) require a paid
ElevenLabs plan to use via the API.

## Generate narrations

```bash
poetry run python generate.py --products concealer-spf-27
poetry run python generate.py --products concealer-spf-27,lip-glorifier
poetry run python generate.py --all-needing
poetry run python generate.py --products concealer-spf-27 --overwrite
```

`--all-needing` shells out to `../scripts/status.py --needs-narration --json`.

## List voices

```bash
poetry run python list_voices.py
poetry run python list_voices.py --language English
```
