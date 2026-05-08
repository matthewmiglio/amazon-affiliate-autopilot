---
name: generate-narration
description: Generate narration mp3s for Amazon affiliate products via ElevenLabs TTS, using the channel voice pinned in `narration/.env`. Reads `script-raw-text` from each product's manifest.json, generates `<product>/narration.mp3`, and keeps `narration-audio-path` in sync. Idempotent — never regenerates an existing mp3, but does fix a manifest that's out of sync. Accepts a single slug, a comma-list, or `--all-needing`. Use when the user runs /generate-narration or asks to "generate narration for X", "narrate these products", or similar.
---

# generate-narration

Take one or more product slugs, run their `script-raw-text` through Hedra TTS, save `narration.mp3` into each product folder, and keep `manifest.json["narration-audio-path"]` aligned. Idempotent and cheap to re-run — only the truly-missing-audio cases burn credits.

## Inputs

`/generate-narration <slugs>` where `<slugs>` is one of:

- A single slug: `/generate-narration concealer-spf-27`
- A comma-list: `/generate-narration concealer-spf-27, lip-glorifier`
- The literal flag `--all-needing` to target every product missing narration.

If the user provides nothing, ask once. Don't guess.

## State machine (per product)

Four cases, ranked by what's already on disk and in the manifest:

| `narration.mp3` exists? | manifest has `"narration.mp3"`? | Action | Cost |
|---|---|---|---|
| ✅ | ✅ | Do nothing | free |
| ✅ | ❌ | Fix manifest only — set `narration-audio-path` to `"narration.mp3"` | free |
| ❌ | ✅ | Generate audio, save mp3 (manifest already correct) | 1 Hedra TTS call |
| ❌ | ❌ | Generate audio, save mp3, set `narration-audio-path` | 1 Hedra TTS call |

Pre-flight bail: if `manifest["script-raw-text"]` is empty, FAIL the product with the message `"empty script-raw-text — run /write-script first"`. Do not attempt generation.

## Workflow

1. **Resolve slugs.** Validate each `products/<slug>/manifest.json` exists. For `--all-needing`, run `python scripts/status.py --needs-narration --json` and use that list.
2. **Verify env.** `narration/.env` must have both `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`. The pinned voice is the channel's signature — do not change it without explicit user direction. If `ELEVENLABS_VOICE_ID` is unset, abort — do not fall back to a default and do not burn credits.
3. **Delegate to `narration/generate.py`.** Run:
   ```
   cd narration
   poetry run python generate.py --products <comma-joined-slugs>
   # or
   poetry run python generate.py --all-needing
   ```
   The script already implements the full state machine above. Each row of output is `<slug>\t<STATUS>\t<detail>` where STATUS ∈ {OK, FIXED, SKIP, FAIL}.
4. **Surface the summary** the script prints (e.g. `5 generated, 2 manifest-fixed, 1 skipped, 0 failed.`). On any FAIL, repeat that row to the user with the reason.
5. **Do NOT** add `--overwrite` unless the user explicitly asks to regenerate.

## Existing helpers (do not duplicate)

- `narration/generate.py` — owns the actual TTS pipeline (POST → poll → download), manifest sync, the four-state idempotent logic, batch slug resolution, and the hard error if `HEDRA_VOICE_ID` is unset.
- `scripts/status.py --needs-narration --json` — feeds `--all-needing`.
- `narration/list_voices.py` — for swapping voices later (already includes cloned voices via `/assets?type=voice`).

## Out of scope

- **No script authoring.** If `script-raw-text` is empty, FAIL and tell the user to run `/write-script` first.
- **No voice selection.** Voice is whatever `HEDRA_VOICE_ID` is currently pinned to in `narration/.env`. The skill does not change `.env`.
- **No regeneration of good audio.** Honor existing mp3s strictly; the only file mutation is creating a missing mp3 or touching the manifest's `narration-audio-path` field.

## Re-runs

Safe and cheap. Existing-mp3 products cost zero credits; misaligned manifests get fixed in O(1) IO. Only genuinely-missing narrations hit the Hedra API.

## Cost note

Each generated mp3 is one ElevenLabs TTS call billed against the user's credit pool. The user has standing approval — proceed without per-call confirmation, even for `--all-needing` on the full catalog.

## Credit accounting (mandatory)

Before AND after the generation step, run `python scripts/credits.py` and capture the ElevenLabs `tokens left` value. After the run, report the delta to the user:

- Single slug: `"Burned <N> ElevenLabs characters (<before> → <after>)."`
- Batch (>1 slug, including `--all-needing`): `"Burned <N> ElevenLabs characters across <K> narrations (<before> → <after>, avg <N/K>/clip)."`

If 0 audio was generated (all SKIP/FIXED), you can omit the line. Don't run the credits check if the run fails before making any API call.
