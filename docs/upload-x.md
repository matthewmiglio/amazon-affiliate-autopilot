# X (Twitter) Upload Module Plan (`uploader/x/`)

Plan for the X video-post uploader. X is a long-tail addition to the affiliate pipeline — posts have a much shorter half-life than Pinterest pins (hours, not months) but the network is huge and links in-tweet are clickable (unlike IG/FB Reels), so click-through can match or beat Reels when a post catches the algorithm.

**Goal:** upload `final-with-music.mp4` as a video tweet with the Amazon affiliate link in the tweet body, drop into `scripts/upload_ad.py`'s per-platform iteration so `manifest["uploads"]["x"]` works the same as YouTube. Match the YouTube uploader's stdout contract: `uploaded -> <tweet_url>` on success.

**Status legend:** `[x]` done · `[ ]` to do · `[~]` partially done

---

## Phase 0 — Manual prerequisites (no code)

External setup that must happen before any code runs. None of this is blocked; do it first.

### Account warm-up (done / in progress)

- [x] Brand-handle X account created, email + phone verified
- [x] Profile bio set (per Option A draft — covers automation disclosure + `#ad` + brand domain)
- [x] Profile website field set to the brand domain
- [x] Followed ~niche accounts to seed the timeline
- [~] **Organic warm-up tweets** — drip-posting 2–3/day across 3–5 days before flipping on automation, to avoid day-one bot pattern-match. Day 1 in progress (2 scheduled, 3 h apart, 1 already live). 10 + 10 = 20 candidate tweets drafted in chat history if more needed.
- [x] Bio includes automation disclosure (X policy requirement for automated accounts)

### Developer portal (next up)

- [ ] Apply for an **X Developer account** at `developer.x.com` (free, ~10 min — needs phone-verified X account). Answer the "will this app post automated content?" question honestly: *"automated posting of short-form product video, ~1 post/day, all videos uniquely generated, FTC #ad disclosure on every affiliate post"*
- [ ] Create a **Project + App** inside the developer portal (one project, one app)
- [x] **Pricing model (verified 2026-05-12):** X has moved to **pay-per-use credits, no free posting tier**. Empirically ~$0.11 per POST /2/tweets regardless of whether the tweet has media — text and video cost the same. The Free tier shown in the dev portal gates *which endpoints you can call*, not how many calls; **all** outbound posts deduct from a prepaid credit balance. At 1 post/day that's ~$40/yr; at 3/day ~$120/yr. Sets a hard floor: there's no path to "free posting" on X — budget for it or skip the platform.
- [ ] In the App settings, set **User authentication settings**:
  - Type: **Web App, Automated App or Bot**
  - App permissions: **Read and write** (media uploads + tweet creation)
  - Callback URI: `http://localhost:8086/` (8086 to avoid colliding with Pinterest's 8085)
  - Website URL: the brand domain
- [ ] Capture **API Key**, **API Key Secret**, **Client ID**, **Client Secret** from the app's Keys & Tokens tab — store in `uploader/x/.env` as `X_API_KEY`, `X_API_KEY_SECRET`, `X_CLIENT_ID`, `X_CLIENT_SECRET` (NOT committed)
- [ ] Confirm required OAuth 2.0 scopes are checked: `tweet.read`, `tweet.write`, `users.read`, `media.write`, `offline.access` (last one is required to get a refresh token)
- [ ] **Read the Automation Rules** — already satisfied via the bio disclosure above, but re-read at portal time in case policy shifted.
- [ ] **Read the Affiliate / Spam policy** — bulk identical posts get flagged. Our descriptions are already unique per product, so we're fine.

---

## Phase 1 — Already-done groundwork (parent refactor)

What the multi-platform refactor laid down — the X module slots in with no further changes.

- [x] `scripts/upload_ad.py` iterates a `platforms` list and per-platform `manifest["uploads"][platform]`
- [x] `scripts/status.py` matrix is platform-agnostic — `x-up` column + `--needs-x-upload` flag added
- [x] `uploader/x/` folder created with `.gitkeep` + `.env.example` (placeholders for the four credentials)
- [x] **No bulk migrator needed** — `ensure_platform_metadata()` lazily creates `uploads.x.{uploaded,url,metadata:{text,destination_url}}` on first run via `setdefault`. Pre-fills `destination_url` from the affiliate link the moment any product is processed.
- [x] `_gen_x()` stub added in `scripts/upload_ad.py` (writes empty `text`, pre-fills `destination_url` from the affiliate link)
- [x] `scripts/upload_ad.py` includes `"x"` in `PLATFORMS`, registers `_gen_x` in `_GENERATORS`, adds `x` URL regex to `_URL_PATTERNS` (matches `https://x.com/...`), and `has_content` check now also considers `metadata["text"]`. Until `uploader/x/upload.py` exists, the runner naturally returns `SKIP — x not implemented (no uploader/x/upload.py)` because of the existing missing-uploader branch.

---

## Phase 2 — Auth (`x_auth.py`)

Mirrors `youtube_auth.py` / planned `pinterest_auth.py`. X requires **OAuth 2.0 with PKCE** for user-context tweets (the older OAuth 1.0a still works but Twitter is pushing everything to v2/OAuth 2.0).

- [x] `x_auth.py` with OAuth 2.0 authorization-code + PKCE flow (confidential client — Basic auth with Client ID/Secret on the token endpoint)
- [x] Persist `tokens/user_token.json`: `{ access_token, refresh_token, expires_at, scope, token_type }`
- [x] `get_access_token()` auto-refreshes when `expires_at - 120s` has passed (refresh-token grant)
- [x] CLI: `python uploader/x/upload.py auth` runs PKCE flow; `whoami` calls `/2/users/me` to verify
- [x] **Verified end-to-end on 2026-05-12:** authorized as the brand handle (user id stored in token JSON), token saved, `whoami` returns the right user. `X_AUTH_NO_BROWSER=1` env var added so the URL is printed instead of auto-opening (lets you paste into the right browser session when default browser is signed into a different account).

> **Note on OAuth 1.0a fallback:** the legacy `media/upload` endpoint historically required OAuth 1.0a, but the v2 `POST /2/media/upload` endpoint (GA 2025) accepts OAuth 2.0 user-context. Use v2 throughout; only fall back to 1.0a if a future endpoint we need doesn't support 2.0.

---

## Phase 3 — Core uploader (`upload.py` + `api_client.py`)

X video tweet creation is **two-step**: chunked media upload → poll status → create tweet referencing the media_id.

> **Auth twist discovered 2026-05-12:** the plan originally said v2 throughout with OAuth 2.0. Reality is a hybrid:
> - `POST /2/tweets` and `GET /2/users/me` — **OAuth 2.0 bearer** (works fine)
> - Chunked media upload — **MUST use the legacy `upload.twitter.com/1.1/media/upload.json` endpoint signed with OAuth 1.0a HMAC**. The v2 `/2/media/upload` endpoint only accepts images / subtitles (enum: `tweet_image`, `dm_image`, `subtitles`) — no video. v1.1 chunked upload returns 403 to OAuth 2.0 bearers.
>
> So we need both flavors of credentials in `.env`:
> - `X_CLIENT_ID` + `X_CLIENT_SECRET` (OAuth 2.0)
> - `X_API_KEY` + `X_API_KEY_SECRET` + `X_ACCESS_TOKEN` + `X_ACCESS_TOKEN_SECRET` (OAuth 1.0a)
>
> The Access Token + Secret are generated one-time in the dev portal under Keys & Tokens → OAuth 1.0 Keys → "Access Token and Secret → Generate". App permissions must be "Read and write" before generating, otherwise the token is read-only and media upload returns 403.

### 3a — HTTP client

- [ ] `api_client.py` — `requests.Session` wrapper around `https://api.x.com/2`
  - Auto-attaches `Authorization: Bearer <access_token>`
  - Auto-refreshes via `x_auth` when a 401 comes back
  - Retries 5xx + 429 (X is aggressive on 429 — respect `x-rate-limit-reset` header)
  - Logs requests for debugging

### 3b — Upload flow

X's media upload is **chunked** — required for video, even small clips. Steps:

- [x] **Step 1 — INIT:** `POST upload.twitter.com/1.1/media/upload.json` (form-urlencoded) with `command=INIT`, `media_type=video/mp4`, `media_category=tweet_video`, `total_bytes=<size>` → `{ media_id_string }`
- [x] **Step 2 — APPEND (loop):** read `final-with-music.mp4` in 5 MB chunks. For each chunk: same endpoint, multipart/form-data with `command=APPEND`, `media_id=<id>`, `segment_index=<0..N>`, `media=<bytes>`
- [x] **Step 3 — FINALIZE:** same endpoint with `command=FINALIZE`, `media_id=<id>` → `{ processing_info: { state, check_after_secs } }`
- [x] **Step 4 — STATUS poll:** `GET upload.twitter.com/1.1/media/upload.json?command=STATUS&media_id=<id>` every `check_after_secs` until `state == "succeeded"`. Observed: pending → in_progress (20% → 75%) → succeeded in ~3s for a 3.5 MB / 17 s clip.
- [x] **Step 5 — Create tweet:** `POST api.x.com/2/tweets` (OAuth 2.0 bearer, JSON) with `{ text, media: { media_ids: [<id>] } }`. **All 5 steps 1-4 use OAuth 1.0a; only step 5 uses the OAuth 2.0 bearer.**
- [x] **Step 6 — Emit:** print exactly `uploaded -> https://x.com/<username>/status/<id>` (username pulled via `GET /2/users/me` so the URL works for any account)

### 3c — Cover / thumbnail

X auto-generates the in-feed thumbnail from the first frame of the video. No cover-image hosting needed (unlike Pinterest). Our `starting-pic.png` is already the first frame of the video, so this works for us natively — no Phase 3c work.

---

## Phase 4 — Metadata builder (replace stub in `upload_ad.py`)

Replace `_gen_x()` stub with a real builder.

- [ ] Read `manifest["item-auxiliary-information"]["affiliate-link"]` for `destination_url` (already wired)
- [ ] Build `text` — single-tweet body, capped at **280 chars including the URL** (X counts URLs as 23 chars via `t.co` wrapping, regardless of actual length)
- [ ] Set `destination_url` to the raw Amazon affiliate link (the URL goes in the tweet body, not a separate field — X doesn't have a "link" field like Pinterest)

### Tweet template

```
{1-line hook from narration — ~120 chars}

{🛒 emoji} {amazon affiliate URL}

#ad #amazonfinds #{niche}
```

Budget:
- Hook: ≤ 120 chars
- Spacer + emoji + URL: 28 chars (URL is t.co-wrapped to 23)
- Hashtag block: ~30 chars
- Disclosure: `#ad` (3 chars) — X allows this as the FTC-compliant disclosure inline; no need for "As an Amazon Associate..." text in-tweet because it's in the account bio per Phase 0

Total: ~180 chars, leaves margin for variance.

---

## Phase 5 — End-to-end verification

- [ ] OAuth flow runs end-to-end, `tokens/user_token.json` populated
- [ ] Token auto-refresh exercised (manually expire access_token, confirm uploader transparently refreshes)
- [ ] Manual `python uploader/x/upload.py <test-slug>` — confirm tweet appears, video plays inline, the t.co link resolves to Amazon with `tag=<associates-tracking-id>` preserved
- [ ] `/upload-ad <slug>` end-to-end — confirm `uploads.x.uploaded=true` + URL written to manifest
- [ ] `python scripts/status.py --matrix` — confirm `x-up` column reflects state
- [ ] Spot-check the **X Analytics** view (`x.com/i/analytics`) shows impressions for the test tweet within 1 hour

---

## Manifest schema (to be migrated alongside this work)

```json
"uploads": {
  "x": {
    "uploaded": false,
    "url": "",
    "metadata": {
      "text": "",
      "destination_url": ""
    }
  }
}
```

## File layout (target)

```
uploader/x/
  pyproject.toml           # just `requests`; no SDK needed
  x_auth.py                # OAuth 2.0 PKCE flow + token refresh
  upload.py                # invoked by scripts/upload_ad.py for platform=x
  api_client.py            # thin wrapper around api.x.com/2
  tokens/
    user_token.json        # { access_token, refresh_token, expires_at }
  history.json             # slug -> {tweet_id, tweet_url}
  .gitignore               # tokens/, history.json
```

## CLI contract

```
python uploader/x/upload.py <product-slug> -y
```

1. Read `products/<slug>/manifest.json`
2. Read `products/<slug>/final-with-music.mp4`
3. Read `manifest["uploads"]["x"]["metadata"]`
4. INIT → APPEND → FINALIZE → STATUS poll → POST /2/tweets
5. Print `uploaded -> https://x.com/<username>/status/<id>` on success
6. Non-zero exit + stderr JSON on failure

## Rate limits & idempotency

- **Free tier:** 500 posts/month (rolling 30-day window), 1 project/app
- **Per-user POST /2/tweets:** 17 requests / 24 h on free, 100 / 24 h on basic (more than enough — we post once per day)
- **Media upload:** 615 chunks / 15 min — never going to hit this
- **429 handling:** respect `x-rate-limit-reset` epoch in the response header; sleep then retry once
- Skip if `manifest["uploads"]["x"]["uploaded"]` is `true` unless `--overwrite`

## Compliance hooks (per `docs/rules.md`)

- Tweet **must** include `#ad` (FTC-compliant for affiliate links on X)
- Account bio **must** disclose automation + affiliate relationship (Phase 0 manual setup)
- Destination URL must be a raw `amazon.com` or `amzn.to` link — t.co wrapping is fine and unavoidable
- Video must accurately represent the destination product — already true since we use the product's own ad clip

## Out of scope for v1

- **Thread replies** (1st tweet = hook, 2nd reply = link + disclosure). Worth A/B-testing in v2 because some affiliate accounts report better engagement with link-in-reply.
- **Polls / quote-tweets / reposts** of older successful posts.
- **Per-tweet analytics ingestion** (`GET /2/tweets/:id?tweet.fields=public_metrics`) — wire into `status.py` later for performance tracking.
- **Multi-account posting** (cross-poster to a second X account). Single-account only for v1.
