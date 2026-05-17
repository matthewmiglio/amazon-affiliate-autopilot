# Meta Upload Module Plan (`uploader/meta/`)

Plan for the Instagram Reels + Facebook Reels uploaders. Both share Meta's Graph API, so a single auth + helper layer serves both targets — that's why they live under one `meta/` folder rather than separate `instagram/` and `facebook/` folders.

**Goal:** upload `final-with-music.mp4` to IG Reels and FB Reels via the Graph API; drop into `scripts/upload_ad.py`'s per-platform iteration so `manifest["uploads"]["instagram"|"facebook"]` works the same as YouTube. Each platform's uploader matches the YouTube stdout contract: `uploaded -> <permalink_url>` on success.

**Status legend:** `[x]` done · `[ ]` to do · `[~]` partially done

**Critical-path warning:** Meta App Review is the longest external blocker (3–7 days, sometimes longer). **Submit it first** so the queue runs in parallel with everything else.

---

## Phase 0 — Manual prerequisites + App Review (start immediately)

This phase is mostly waiting; start it before writing any code.

### Day 1 — Account creation (DONE 2026-05-12)

- [x] **Instagram account created** under the brand handle, converted to Creator (Settings → For professionals → Account type and tools). Creator chosen over Business — same Graph API capabilities, slightly looser content guidelines.
- [x] IG bio + profile pic + brand colors aligned with X/Pinterest brand.
- [x] **Facebook personal account created** under a pseudonym (same email). Meta's real-name policy rejected the brand name directly, so we picked a plausible-American alias. Personal account is the admin shell; the Page (created Day 2) carries the brand name.
  - Profile pic / cover are *generic stock-style*, NOT the brand logo. Reusing brand assets here is the #1 thing that flags aliases.
  - Hometown / pronouns / hobbies filled in plausibly. Specific alias identity details are held out-of-repo so they aren't grep-able if this repo goes public.
  - Phone-verified via Accounts Center (single most important real-human signal).
  - Logged out, scrolled feed briefly first.
- [x] **Cooldown started.** No further FB activity for ≥12 h (target 24–48 h). Reason: same-session "create account → create Page → create developer app" is the highest-confidence anti-bot signal on Meta. Risk of skipping: temporary lock → ID-verification prompt → unrecoverable lockout if Meta asks for ID matching the alias.

### Day 2+ — Page, Business Suite

- [x] **Create a Facebook Page** for the brand (category: Shopping & Retail / Product/Service)
- [x] **Link IG ↔ Page** via business.facebook.com (Meta Business Suite → Linked accounts → Instagram → Connect)
- [x] **Set up Meta Business Manager** (Business Suite onboarding)

### Day 3 — Developer Account Verification (BLOCKED)

Quitting here for now — the developer-account verification gate at `developers.facebook.com` is a hostile loop. Documenting everything tried so the next session doesn't re-derive.

**Hard finding:** Meta's developer-account verifier maintains a **separate phone-uniqueness namespace** from the Facebook profile. A number already on any FB account is rejected with `"Your phone number has been added, please try another phone number."` Multiple Meta dev-forum threads confirm this is intentional anti-abuse, not a bug.

**What we tried (all failed):**

| Attempt | Result |
|---|---|
| Use the alias FB account's already-verified phone | Rejected — "complete this action in Accounts Center" → Accounts Center loop |
| Same number in E.164 (`+1...`) format | Rejected — same uniqueness check |
| Google Voice number (Charlotte 704 area code, then a 734) | **Send Verification SMS button greyed out entirely** — Meta auto-detects VOIP / GV ranges and blocks before submission. Confirmed dead end regardless of area code |
| Card-based verification path (Meta routes this through Meta Pay → Accounts Center) | **Rejected with "Couldn't verify ZIP code"** even when the billing address entered matches the bank's address-on-file *exactly* (same street, city, state, ZIP). Almost certainly NOT an AVS mismatch — likely a silent fraud-rule rejection from cardholder-name (real) vs FB-account-name (alias) mismatch. Meta deliberately obfuscates fraud rejections as generic ZIP errors to avoid leaking the rule. |

**Paths NOT tried (next-session options, ranked):**

1. **Prepaid cellular SIM** ($10–25 at Walmart / 7-Eleven / CVS — Tracfone, Total by Verizon, AT&T Prepaid). Activate, use the number ONLY on the dev verify screen (do NOT add it to the FB profile). Cleanest path; doesn't compromise the alias.
2. **SMSPool burner** (Facebook-specific service, ~$1, ~50% success rate against Meta).
3. **Nuclear: rename FB to a real name** to match the real card. Resolves the card path in 30s but kills the alias plan (FB only allows 1 name change per 60 days, audit-logged). Per the risk register below, this is arguably the right long-term call anyway since App Review business verification will likely demand a real-named admin.

**Forum / source references (for next session — don't re-derive):**

- Meta dev forum threads 2358191007966080, 1267770634201429, 868811611528882, 1390605858472686 — all describe variants of this loop in 2024–2025.
- BHW thread 1768747 — consensus solution is the credit-card path (which we couldn't get past due to name mismatch).
- Meta help: `facebook.com/help/167551763306531` documents the card path as the official escape hatch.

### Day 4+ — Pending (post-verification)

- [ ] **Create the Meta Developer App** at `developers.facebook.com`
  - [ ] Type: **Business**
  - [ ] Use case: **Other** (avoids the funneled templates; gives full product access)
  - [ ] Link the Business portfolio set up in Suite
  - [ ] Add product: **Instagram Graph API**
  - [ ] Add product: **Facebook Login for Business** (for token generation)
- [ ] Permissions to request:
  - `instagram_basic`
  - `instagram_content_publish`
  - `pages_show_list`
  - `pages_read_engagement`
  - `pages_manage_posts`
  - `business_management`
- [ ] App Review prerequisites:
  - [ ] App icon (1024×1024, brand logo is fine — the app is the brand, not the alias)
  - [ ] Privacy policy URL (live HTTPS — one-page site is enough)
  - [ ] Terms URL
  - [ ] Category: Shopping
- [ ] **Submit for App Review** for `instagram_content_publish` + `pages_manage_posts` (3–7 days; expect screencast demo request + possibly business verification)
- [ ] **App Review approved**
- [ ] Capture `app_id` + `app_secret` from app dashboard, store in `uploader/meta/.env`

### Risk register

- **Cardholder-name ≠ account-name fraud signal.** Confirmed live during Day 3 verification attempts. Meta's anti-fraud silently rejects real-name cards on alias accounts. Any future card-based action on the alias account (App Review billing, ads, etc.) hits the same wall.
- **ID-verification ambush during App Review.** If Meta asks the alias admin to verify ID, the alias becomes a sticking point. Mitigation paths: dispute with workaround docs, or transfer Page admin to a real-named secondary account before re-submitting.
- **Same-session signup flag.** Spreading Day-2 actions across a session (Page → 30 min gap → Business Manager → 30 min gap → Dev app) reduces risk vs. doing them back-to-back.
- **Strategic re-evaluation:** the cumulative friction (verification loop + likely ID ambush at App Review) is high enough that the alias strategy may cost more time than it saves. Worth reconsidering whether to admin the Page under a real name from the start.

---

## Phase 1 — Already-done groundwork (parent refactor)

What the multi-platform refactor already laid down.

- [x] `uploader/meta/` folder exists (empty placeholder, `.gitkeep`)
- [x] Manifest schema includes `uploads.instagram.{uploaded,url,metadata}` and `uploads.facebook.{...}` on every product
- [x] `scripts/upload_ad.py` iterates `instagram` and `facebook` independently and skips with `"<platform> not implemented"` while the scripts are absent
- [x] `scripts/status.py` has `insta-up` and `fb-up` columns reading `uploads.instagram.uploaded` / `uploads.facebook.uploaded`
- [x] Stub `_gen_instagram()` / `_gen_facebook()` metadata builders in `scripts/upload_ad.py` (currently write empty `caption` + `hashtags`)

---

## Phase 2 — Shared infra: temp video hosting (S3 / R2)

Instagram's video-publish API does **not** support direct binary upload — it needs a public HTTPS URL it can pull from. Pinterest also needs a public cover-image URL. So both platforms share one temp bucket.

- [ ] Provision bucket `theluxedrawer-uploads-tmp` (S3 or Cloudflare R2)
  - [ ] Lifecycle rule: auto-delete objects after 24 h
  - [ ] Public read on the bucket OR generate signed URLs per upload
- [ ] Add `boto3` (or `r2`-compatible S3 SDK) to `uploader/meta/pyproject.toml`
- [ ] Store AWS creds in `tokens/aws_creds.json` (or env vars)
- [ ] Helper: `upload_temp(local_path) -> public_url` — used by both Meta IG flow and Pinterest cover hosting

> Alternative for dev/testing only: ngrok local tunnel. Not viable for batch / scheduled runs.

---

## Phase 3 — Auth (`meta_auth.py`)

- [ ] `meta_auth.py` — Facebook Login OAuth flow
  - Browser → `https://www.facebook.com/v21.0/dialog/oauth?...` with required scopes
  - Localhost listener catches the redirect (mirror `youtube_auth.py` pattern)
- [ ] Exchange short-lived user token → long-lived user token at `/oauth/access_token?grant_type=fb_exchange_token`
- [ ] Fetch `/me/accounts` → pick the Page → grab its **Page access token** (Page tokens derived from a long-lived user token never expire as long as the user doesn't change password / revoke perms)
- [ ] Fetch IG Business Account ID from the Page: `/{page-id}?fields=instagram_business_account`
- [ ] Persist `tokens/page_token.json`: `{ page_id, ig_user_id, access_token, expires_at }`
- [ ] CLI: `python uploader/meta/upload_instagram.py auth` — runs the flow once and saves credentials for both IG and FB

---

## Phase 4 — Shared HTTP client (`graph_client.py`)

- [ ] `graph_client.py` — `requests.Session` wrapper around `https://graph.facebook.com/v21.0`
  - Auto-attaches `access_token`
  - Retries 5xx + Meta's transient codes: `error.code in {1, 2, 4, 17, 32, 613}`
  - Logs every request to `meta/history.json` for debugging
  - Bump API version yearly

---

## Phase 5 — Instagram uploader (`upload_instagram.py`)

Two-step container → publish flow.

- [ ] **Step 1 — Upload `final-with-music.mp4` to temp bucket** → public HTTPS URL
- [ ] **Step 2 — Create media container:** `POST /{ig-user-id}/media`
  - `media_type=REELS`
  - `video_url=<public URL from step 1>`
  - `caption=<title + disclosure + hashtags + affiliate link>`
  - `share_to_feed=true`
- [ ] **Step 3 — Poll status:** `GET /{container-id}?fields=status_code` until `FINISHED` (typically 5–60 s)
- [ ] **Step 4 — Publish:** `POST /{ig-user-id}/media_publish?creation_id=<container-id>` → returns IG media `id`
- [ ] **Step 5 — Resolve permalink:** `GET /{media-id}?fields=permalink`
- [ ] **Step 6 — Cleanup:** delete the temp video from the bucket
- [ ] **Step 7 — Emit:** print exactly `uploaded -> <permalink>`

---

## Phase 6 — Facebook uploader (`upload_facebook.py`)

FB Reels uses a **3-phase resumable upload** — direct binary, no public URL needed (contrast with IG).

- [ ] **Step 1 — Initialize:** `POST /{page-id}/video_reels?upload_phase=start` → returns `video_id` + `upload_url`
- [ ] **Step 2 — Upload bytes:** `POST <upload_url>` with raw mp4 body
  - Headers: `Authorization: OAuth <page_token>`, `offset: 0`, `file_size: <bytes>`
- [ ] **Step 3 — Finish:** `POST /{page-id}/video_reels?upload_phase=finish&video_id=<id>&video_state=PUBLISHED&description=<caption>`
- [ ] **Step 4 — Resolve permalink:** `GET /{video-id}?fields=permalink_url`
- [ ] **Step 5 — Emit:** print `uploaded -> https://www.facebook.com/reel/<id>`

---

## Phase 7 — Metadata builders (replace stubs in `upload_ad.py`)

Current `_gen_instagram()` / `_gen_facebook()` write empty placeholders. Phase 7 replaces them with real builders. IG and FB share caption text — internally call one shared `_build_meta_caption()` and write into both sub-objects.

- [ ] Build `caption` from `manifest["item-auxiliary-information"]` + `manifest["script-raw-text"]`:
  - title line + narration hook + amazon affiliate link + disclosure + hashtags
- [ ] Build `hashtags` — same niche set as YouTube (`#amazonfinds`, `#beauty`, etc.) capped at 5 (more clutters the visual)
- [ ] Pull affiliate link from `manifest["item-auxiliary-information"]["affiliate-link"]`

### Caption template (used by both IG and FB)

```
{title}

{narration first line restated}

🛒 {amazon_affiliate_url}

As an Amazon Associate I earn from qualifying purchases. #ad

{hashtags}
```

---

## Phase 8 — End-to-end verification

- [ ] OAuth flow runs end-to-end, `tokens/page_token.json` populated
- [ ] Manual `python uploader/meta/upload_instagram.py <test-slug> -y` — Reel appears on the IG account, permalink printed
- [ ] Manual `python uploader/meta/upload_facebook.py <test-slug> -y` — Reel appears on the linked Page, permalink printed
- [ ] `/upload-ad <slug>` end-to-end — both platforms flip `uploaded=true` and write URLs to manifest
- [ ] `python scripts/status.py --matrix` — `insta-up` + `fb-up` columns reflect state
- [ ] Click each permalink → confirm Amazon link in caption resolves with `tag=theluxedrawer-20` preserved

---

## Manifest schema (decided in parent plan, already migrated for all 55 products)

```json
"uploads": {
  "instagram": {
    "uploaded": false,
    "url": "",
    "metadata": { "caption": "", "hashtags": [] }
  },
  "facebook": {
    "uploaded": false,
    "url": "",
    "metadata": { "caption": "", "hashtags": [] }
  }
}
```

## File layout (target)

```
uploader/meta/
  pyproject.toml          # requests + boto3
  meta_auth.py            # token load + refresh helpers
  graph_client.py         # shared HTTP wrapper around graph.facebook.com
  upload_instagram.py     # invoked by scripts/upload_ad.py for platform=instagram
  upload_facebook.py      # invoked by scripts/upload_ad.py for platform=facebook
  temp_host.py            # S3/R2 upload helper, also reused by uploader/pinterest
  tokens/
    page_token.json       # { page_id, ig_user_id, access_token, expires_at }
    aws_creds.json        # bucket creds (or env vars)
  history.json            # slug -> { ig_media_id, fb_post_id, permalinks }
  .gitignore              # tokens/, history.json
```

## CLI contracts (mirror `uploader/youtube/upload.py`)

```
python uploader/meta/upload_instagram.py <product-slug> -y
python uploader/meta/upload_facebook.py  <product-slug> -y
```

Each:
1. Reads `products/<slug>/manifest.json`
2. Reads `products/<slug>/final-with-music.mp4`
3. Reads `manifest["uploads"][platform]["metadata"]` for caption/hashtags
4. On success, prints exactly one line: `uploaded -> <permalink_url>`
5. On failure, exits non-zero with the Meta error JSON on stderr

## Rate limits & idempotency

- IG: 50 published posts / IG account / 24 h
- FB Reels: ~25 / Page / 24 h (soft, undocumented)
- Our cadence (~3/day) is well under
- Skip when `manifest["uploads"][platform]["uploaded"]` is `true` unless `--overwrite`

## Branded-content / paid-partnership label

Meta has API support for the **Branded Content** tag but only between two accounts (sponsor → creator). For self-affiliate, the recommended path is:

- Disclosure in caption (`#ad`, `As an Amazon Associate...`)
- On-screen disclosure baked into the video (already done by the captioning skill)

No API call needed for the toggle (unlike YouTube's paid-promotion flag).

## Open questions / future

- **Cross-post via IG `share_to_facebook` flag** instead of running `upload_facebook.py` separately? Saves a second upload but ties FB caption/permalink to IG. Decision: upload separately for now (independent permalinks → cleaner per-platform analytics).
- **Threads** shares the IG Graph API. Cheap to add `upload_threads.py` later if it becomes a real referral source.
- **TikTok** is *not* part of this module (no official upload API for personal accounts).
