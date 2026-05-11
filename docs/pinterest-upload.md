# Pinterest Upload Module Plan (`uploader/pinterest/`)

Plan for the Pinterest video-pin uploader. Pinterest is the highest-ROI affiliate platform after IG/FB Reels because pins have a months-long half-life vs. Shorts that die in 48 h, and the destination URL on a pin can be the raw Amazon affiliate link with no "link in bio" friction.

**Goal:** upload `final-with-music.mp4` as a video pin with the Amazon affiliate link as the destination URL, drop into `scripts/upload_ad.py`'s per-platform iteration so `manifest["uploads"]["pinterest"]` works the same as YouTube. Match the YouTube uploader's stdout contract: `uploaded -> <pin_url>` on success.

**Status legend:** `[x]` done · `[ ]` to do · `[~]` partially done

---

## Phase 0 — Manual prerequisites (no code)

External setup that must happen before any code runs. None of this is blocked by anything else; do it first so the rest can move.

- [x] Convert Pinterest account to **Business** (Content creator, Beauty focus, username `theluxedrawer`)
- [x] Profile filled in (name "Soft Luxe Daily", disclosure in About, she/her, avatar)
- [x] Create at least one **board per niche** (boards created)
- [x] Public privacy policy hosted (GitHub gist — see `docs/pinterest-privacy-policy.md` for source)
- [x] Register an app at `developers.pinterest.com` — **App ID: `1568898`** ("Soft Luxe Daily uploader")
- [x] Add redirect URI `http://localhost:8085/` to the app
- [~] Capture `client_id` + `client_secret` — `client_id=1568898` captured; `client_secret` **gated behind "Trial access pending"** (Pinterest review, usually hours to ~2 days)
- [ ] Confirm required scopes are checked: `boards:read`, `pins:read`, `pins:write`, `user_accounts:read` (gated until trial access approved)

---

## Phase 1 — Already-done groundwork (parent refactor)

This is what the multi-platform refactor already laid down — the Pinterest module slots into all of this with no further changes.

- [x] `uploader/pinterest/` folder exists (empty placeholder, `.gitkeep`)
- [x] Manifest schema includes `uploads.pinterest.{uploaded,url,metadata}` on every product
- [x] `scripts/upload_ad.py` iterates `pinterest` and skips with `"pinterest not implemented"` while the script is absent
- [x] `scripts/status.py` has a `pint-up` column that reads `uploads.pinterest.uploaded`
- [x] Stub `_gen_pinterest()` metadata builder in `scripts/upload_ad.py` (currently writes empty `title` / `description` / `board` and pre-fills `destination_url` from the affiliate link)

---

## Phase 2 — Auth (`pinterest_auth.py`)

Mirrors the `youtube_auth.py` pattern.

- [ ] `pinterest_auth.py` with OAuth 2.0 authorization-code flow
  - Opens browser to `https://www.pinterest.com/oauth/?client_id=...&redirect_uri=http://localhost:8085&scope=boards:read,pins:read,pins:write,user_accounts:read&response_type=code`
  - Local listener catches `?code=...`
  - Exchanges code at `POST https://api.pinterest.com/v5/oauth/token` (`grant_type=authorization_code`)
- [ ] Persist `tokens/user_token.json`: `{ access_token, refresh_token, expires_at }`
  - `access_token` — ~1 year
  - `refresh_token` — 60 days, sliding
- [ ] Auto-refresh on every uploader invocation if `expires_at` is within 7 days (use `grant_type=refresh_token`)
- [ ] CLI: `python uploader/pinterest/upload.py auth` — runs the flow, saves the token

---

## Phase 3 — Core uploader (`upload.py` + `api_client.py`)

Pinterest video-pin creation is **two-step**: register a media upload, upload bytes, poll status, then create the pin pointing at the registered media.

### 3a — HTTP client

- [ ] `api_client.py` — `requests.Session` wrapper around `https://api.pinterest.com/v5`
  - Auto-attaches `Authorization: Bearer <access_token>`
  - Retries 5xx + transient rate-limit errors
  - Logs requests for debugging

### 3b — Upload flow

- [ ] **Step 1 — Register media:** `POST /v5/media { "media_type": "video" }` → `{ media_id, upload_url, upload_parameters }`
- [ ] **Step 2 — Upload bytes:** `POST <upload_url>` as multipart form (all `upload_parameters` as fields, `final-with-music.mp4` as the `file` field — Pinterest backs media uploads with S3 pre-signed POST)
- [ ] **Step 3 — Poll status:** `GET /v5/media/{media_id}` until `status == "succeeded"` (typically 10–60 s)
- [ ] **Step 4 — Create pin:**
  ```
  POST /v5/pins
  {
    "board_id": "<resolved from boards.json>",
    "title": "<≤60 chars>",
    "description": "<≤500 chars, includes #ad + 'As an Amazon Associate...'>",
    "link": "<amazon affiliate URL>",
    "media_source": {
      "source_type": "video_id",
      "cover_image_url": "<public URL of starting-pic.png>",
      "media_id": "<from step 1>"
    }
  }
  ```
- [ ] **Step 5 — Emit:** print exactly `uploaded -> https://www.pinterest.com/pin/<id>/`

### 3c — Cover image hosting

Pinterest requires a public HTTPS URL for the cover. Reuse the same temp S3 bucket the Meta uploader uses (see `docs/meta-upload.md`). Falls under "shared infra" — done once, used by both platforms.

- [ ] Reuse `starting-pic.png` as cover (already 9:16, on-brand, optimized)
- [ ] Upload to temp S3 with 1-hour presigned URL, delete after pin is created

### 3d — Board selection

- [ ] `boards.json` — niche → board ID mapping, e.g.:
  ```json
  {
    "beauty":  "1234567890",
    "kitchen": "9876543210",
    "home":    "..."
  }
  ```
- [ ] Read `manifest["item-auxiliary-information"]["category"]` → look up board ID → use in step 4
- [ ] If no board exists for the category, log a warning and exit 1 (don't dump everything to one board — Pinterest's spam detection penalizes that)

---

## Phase 4 — Metadata builder (replace stub in `upload_ad.py`)

The current `_gen_pinterest()` in `scripts/upload_ad.py` writes empty placeholders. Phase 4 replaces it with a real builder.

- [ ] Read `manifest["item-auxiliary-information"]["affiliate-link"]` for `destination_url` (already wired)
- [ ] Build `title` — product name truncated to 60 chars, leading with product type ("Hydrating Lipstick — Cle de Peau") not brand
- [ ] Build `description` — 2–3 sentences from `manifest["script-raw-text"]`, ending with disclosure + hashtags, capped at 500 chars
- [ ] Set `board` — human-readable category from `item-auxiliary-information.category` (resolved to ID at upload time via `boards.json`)

### Description template

```
{1-line product hook from narration}

{1-line value prop}

🛒 {amazon affiliate URL}

As an Amazon Associate I earn from qualifying purchases. #affiliate

#amazonfinds #{niche} #{product-type}
```

---

## Phase 5 — End-to-end verification

- [ ] OAuth flow runs end-to-end, `tokens/user_token.json` populated
- [ ] `boards.json` covers every `category` value present in `products/*/manifest.json`
- [ ] Manual `python uploader/pinterest/upload.py <test-slug>` — confirm pin appears on the right board, video plays, click goes to Amazon with our tracking ID preserved (`tag=theluxedrawer-20`)
- [ ] `/upload-ad <slug>` end-to-end — confirm `uploads.pinterest.uploaded=true` + URL written to manifest
- [ ] `python scripts/status.py --matrix` — confirm `pint-up` column reflects state

---

## Manifest schema (decided in parent plan, already migrated for all 55 products)

```json
"uploads": {
  "pinterest": {
    "uploaded": false,
    "url": "",
    "metadata": {
      "title": "",
      "description": "",
      "destination_url": "",
      "board": ""
    }
  }
}
```

## File layout (target)

```
uploader/pinterest/
  pyproject.toml           # just `requests`; no SDK needed
  pinterest_auth.py        # OAuth flow + token refresh
  upload.py                # invoked by scripts/upload_ad.py for platform=pinterest
  api_client.py            # thin wrapper around api.pinterest.com/v5
  tokens/
    user_token.json        # { access_token, refresh_token, expires_at }
  boards.json              # niche → board ID
  history.json             # slug -> {pin_id, pin_url, board_id}
  .gitignore               # tokens/, history.json
```

## CLI contract

```
python uploader/pinterest/upload.py <product-slug> -y
```

1. Read `products/<slug>/manifest.json`
2. Read `products/<slug>/final-with-music.mp4`
3. Read `products/<slug>/starting-pic.png` (cover)
4. Read `manifest["uploads"]["pinterest"]["metadata"]`
5. Resolve board ID via `boards.json`
6. Upload media → poll → create pin
7. Print `uploaded -> https://www.pinterest.com/pin/<id>/` on success
8. Non-zero exit + stderr JSON on failure

## Rate limits & idempotency

- 1000 requests/hour per user token — generous (we use ~5 calls per pin)
- No documented per-day pin cap on Business accounts via API; soft-throttle anecdotal at >25 pins/day from one account
- Skip if `manifest["uploads"]["pinterest"]["uploaded"]` is `true` unless `--overwrite`

## Compliance hooks (per `docs/rules.md`)

- Description **must** include `#affiliate` or `Amazon Associate` text — enforce in the metadata builder, not optional
- Destination URL must be a raw `amazon.com` or `amzn.to` link — no third-party redirect/cloaker
- Image must accurately represent the destination product — already true since we use the product's lifestyle frame

## Out of scope for v1

- **Multi-board pinning** (cross-pin same product to multiple boards with varied title/description). Add as `--repin-to` flag in v2 once we have ~20 boards.
- **Per-pin analytics** (`/v5/pins/{id}/analytics`) — cheap to wire into `status.py` later for performance tracking.
