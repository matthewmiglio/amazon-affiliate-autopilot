# Rules: Channel + Posting + Amazon Associates Compliance

The rules that keep the channel alive. Breaking any of the **HARD RULES** can terminate the Associates account, the YouTube channel, or both. Read before every batch.

---

## HARD RULES (account-killers)

### Amazon Associates

1. **Disclosure on every post, every time.** The exact required language:
   > "As an Amazon Associate I earn from qualifying purchases."
   - Goes in the **video description** (not just pinned comment)
   - Should also be visible **on-screen** or spoken in the video itself for FTC compliance
   - Never abbreviate to just "#ad" — Amazon's Operating Agreement requires the full statement somewhere accessible

2. **No affiliate links in:**
   - Email, PDFs, ebooks, or any offline medium
   - Private/closed groups (Discord servers, private FB groups, DMs)
   - Anywhere behind a login wall
   - Sites/channels not explicitly listed in your Associates account

3. **No link cloaking that hides the destination is Amazon.** Bit.ly with a custom domain is fine. URL shorteners that disguise the link are not. Amazon's own `amzn.to` shortener is preferred.

4. **No price claims that can go stale.** Don't say "only $12" in the video — Amazon prices change hourly and stating a wrong price violates the agreement. Say "under $20" or "affordable" instead.

5. **No fake reviews, no claiming to own the product if you don't, no false scarcity** ("only 3 left!" when you don't know).

6. **3 qualifying sales in 180 days** or the account is closed. Reapply allowed but resets the clock.

7. **No bidding on Amazon's branded keywords** in paid ads (e.g., "amazon kitchen gadgets") — irrelevant for Shorts but worth knowing if you ever run ads.

8. **Don't buy through your own links.** Self-purchases don't qualify and repeat attempts get flagged.

9. **No misrepresenting the relationship with Amazon.** Don't call yourself an "Amazon partner," "Amazon employee," or imply Amazon endorses your channel. You are an "Amazon Associate" — that's the only correct term.

10. **Trademark / logo restrictions.** Don't use the Amazon logo, "Amazon" wordmark, or any modified Amazon trademark in your channel name, handle, profile picture, banner, or thumbnails. Saying "Amazon finds" in titles/descriptions is fine; using the logo is not.

11. **Use official Amazon linking tools (SiteStripe or the Associates linking tool).** Don't construct affiliate URLs by hand or scrape product data — use the tools so the tracking ID attaches correctly.

12. **Keep account info current.** If your channel URL, payment info, or tax info changes, update it in Associates Central. Stale info can void payouts.

13. **Tax + payment info must be completed before payout.** W-9 (US) or W-8 (non-US) is required. Without it, earnings sit unpaid indefinitely and may be forfeited.

14. **Only link to Amazon.com product pages, storefronts, or Idea Lists** via your tracking ID. Don't redirect affiliate clicks to non-Amazon destinations.

15. **One Associate ID per property.** Use `theluxedrawer-20` only for the TheLuxeDrawer channel. If you launch other channels/sites, list them in your account or create separate tracking IDs.

### YouTube

1. **Toggle "contains paid promotion / includes paid promotion"** in YouTube Studio for every Short with an affiliate link. Required by YouTube's policy even though Amazon doesn't "pay" you per video.
   - **Not available in the YouTube Data API v3** — Studio UI only. Cannot be set at upload time via API.
   - **Workflow:** upload via API, then open Studio once daily and bulk-select the day's uploads → Edit → toggle paid promotion in one pass.
   - **Per-video, not channel-wide.** No global setting; must be flipped on each video.
   - Browser automation (Puppeteer/Playwright) can flip the toggle but is fragile and technically against TOS — manual bulk-toggle is the recommended path.

2. **No misleading thumbnails or titles.** Shorts have no thumbnails for the feed but the title still matters.

3. **No copyrighted music** unless using YouTube's free library or licensed tracks. Shorts get muted or demonetized for unlicensed audio.

4. **No reused content from other creators.** AI-generated is fine if it's *your* generation. Don't scrape someone else's TikTok and re-upload.

5. **Channel must stay public.** Going private kills affiliate validity.

6. **No engagement-bait that violates spam policy** ("comment YES if you want the link" is borderline; "subscribe to see the link" is a violation).

### Instagram + Facebook Reels (Meta)

1. **Affiliate links are allowed**, but Meta's Community/Commerce policies forbid:
   - Cloaked redirects, link shorteners that hide the destination, or links to malware/scam pages.
   - Driving traffic to "low-quality" landing pages (interstitials, pop-up farms). Amazon product pages are fine.
2. **Branded Content / Paid Partnership disclosure.** Reels containing affiliate links must use Meta's **Branded Content tool** (paid partnership label) or include a clear caption disclosure (`#ad`, `#affiliate`, "Amazon Associate"). On-screen text disclosure is still required for FTC.
3. **Account type.** Uploading via the Graph API requires:
   - An **Instagram Business or Creator account**
   - Linked to a **Facebook Page** (not a personal profile)
   - A Meta Developer App with `instagram_content_publish` + `pages_manage_posts` permissions, App Review approved.
4. **Reels API rate limits.** 50 API-published posts per Instagram account per 24 hours. Plenty of headroom for our cadence but worth knowing.
5. **No dedicated affiliate program from Meta** for Amazon — the affiliate relationship is purely between us and Amazon. Meta just hosts the content.
6. **No automated/scripted engagement.** Don't run bots that like/follow/comment. Account-killer.
7. **Music licensing.** Reels has its own music library; using non-licensed audio in a Business-account Reel will mute it (Business accounts can't use most popular tracks). Stick to our own `music/` library or the Meta Sound Collection.
8. **Same video on Reels + Shorts is fine** — neither platform penalizes cross-posting, but Meta does down-rank videos with a visible TikTok watermark, so render clean.

### Pinterest

1. **Affiliate links are explicitly allowed** (Pinterest reversed its 2017 ban in 2020). Direct Amazon links work.
2. **Disclosure is mandatory.** Pin description must include `#affiliate` or "Amazon Associate" — Pinterest's own Community Guidelines + FTC.
3. **No cloaked links.** Pinterest auto-rejects pins whose destination URL doesn't resolve to the displayed domain. Use raw `amzn.to` or full `amazon.com` URLs.
4. **One pin per product, varied titles/descriptions.** Pinterest's spam detection flags identical pins repeated across boards. Re-pinning the same affiliate link to 10 boards = ban risk.
5. **No misleading pins.** Pin image must represent what the click destination actually sells.
6. **Idea Pins (now "Pins" with video) support a destination URL** — that's our affiliate link. No "link in bio" workaround needed.
7. **API access.** The Pinterest API v5 supports video pin creation with a `link` field. Requires:
   - A Pinterest **Business account** (free conversion from personal)
   - A registered app at `developers.pinterest.com`
   - OAuth user token with `pins:write`, `boards:read` scopes.
8. **Rate limits.** 1000 API calls/hour per user token — generous.
9. **No engagement manipulation.** Don't run pin-loop groups, bot saves, or buy followers.
10. **Adult / restricted categories.** Beauty and home are fine; supplements, weapons, and "before/after" body content are restricted — avoid for affiliate pins.

### FTC (US disclosure law)

1. **Disclosure must be "clear and conspicuous"** — meaning a viewer cannot reasonably miss it. In a 15s Short, this means: on-screen text + spoken + in description. All three.

2. **Disclosure goes BEFORE the affiliate link in the description**, not buried at the bottom.

3. **"On-screen" disclosure** = text burned into the video pixels themselves (overlay), NOT in the title or description. Requirements:
   - **Clear and conspicuous** — large enough to read on a phone, contrasting color, not in a corner
   - **Visible long enough to read** — minimum 2-3 seconds, ideally the full duration
   - **Near the start** — not only at the end after viewers have swiped away
   - **Not obscured** — captions, stickers, product overlays cannot cover it

4. **Acceptable on-screen disclosure phrases:**
   - `#ad`
   - `#sponsored`
   - `Paid promotion`
   - `Affiliate`
   - `Amazon Associate`
   - `Commission earned`

5. **Recommended on-screen pattern for this channel:** a small persistent text overlay in the top-left or top-right corner reading `#ad • Affiliate link below` or `Amazon Associate` for the full duration of every Short. Bake into the template so it's never forgotten.

6. **Three-layer disclosure (bulletproof):** on-screen text + spoken in voiceover ("this is an affiliate link") + written disclosure line above the link in the description. The YouTube paid-promotion toggle is a fourth layer required by YouTube policy on top of FTC.

---

## SOFT RULES (channel hygiene — won't get banned, but matter for growth)

### Posting cadence

- **1–3 Shorts per day** is the sweet spot. More than 3 dilutes algorithmic favor.
- **Don't dump.** Schedule across the day (morning, afternoon, evening).
- **Consistency matters more than volume.** 1/day for 30 days beats 30 in one day.

### Content rules

- **First 2 seconds = the hook.** Algorithm uses retention curve from the very start.
- **Loop it.** Last frame should connect back to first frame so the viewer watches twice. Doubles watch time.
- **No dead air.** Music or VO from frame 1.
- **Vertical 9:16, 1080×1920**, under 60s (under 30s preferred for retention).
- **One product per Short.** Don't list five things; algorithm rewards focus.
- **Captions on-screen always.** ~85% of Shorts viewers watch muted.

### Description format (template)

```
[Product name] → [affiliate link]

As an Amazon Associate I earn from qualifying purchases.

[1–2 line hook restating the value]

#niche #amazonfinds #shorts
```

### Tagging

- 3–5 hashtags max. More than 5 hurts.
- One niche-specific (`#makeupfinds`), one broad (`#amazonfinds`), one format (`#shorts`).

### Safety net

- **Back up every video** to `videos/` locally. If YouTube terminates the channel, you keep the assets.
- **Track which products converted** in `data/`. Repeat winners; kill duds after 5 posts.
- **Save the affiliate ID** somewhere outside this repo (password manager). Don't commit it.

---

## DON'T-EVEN-THINK-ABOUT-IT

- Buying views, likes, or subscribers. Instant termination on detection.
- Sub4Sub or engagement pods.
- AI voiceovers that impersonate real people (especially celebrities reviewing products).
- Health/medical/financial product claims without sourcing. Amazon and FTC both care.
- Anything involving children's products with a child in the video unless you're prepared for COPPA paperwork.
- Reuploading the same Short twice. YouTube flags duplicates and tanks the channel.

---

## Amazon Associates Application Rules (US)

Extracted from the Amazon Associates application page.

### Scope
- This application is **only for the Amazon Associates Program in the US (amazon.com)**.
- You must apply **separately for each international Amazon Associates Program**.

### Required listing
- List **all** of your top-level website domains, mobile application app store links, and Alexa Link detail pages where you will be placing ads from Amazon Associates.

### Review and qualifying-sales requirement
- Your application will be reviewed shortly after you've referred qualified sales to Amazon.com.
- Your account will be **closed if you do not make qualified referrals within the first 180 days**.
- You can **re-apply** once you've made adjustments to your website, app, and/or Alexa skill.

### Site / app readiness
- All websites and Alexa skills must be **fully developed prior to the review**.
- **Popular websites are not accepted** unless you are the specific owner of the website.
- **Facebook Fan Pages and Verified Twitter accounts** will be considered for participation if:
  - You provide the **specific URL** for these sites
    - Correct: `www.facebook.com/account_id`
    - Incorrect: `www.facebook.com`
  - You have **enough followers**.

### App store requirements
- All apps must be available from at least one of the following app stores: **Amazon, Google Play, or Apple**.
- You must add **separate links for each instance of the same title across app stores**.

---

## Pre-publish checklist (run before every upload)

- [ ] Disclosure in description, above the fold
- [ ] Affiliate link is the right tracking ID for *this* channel
- [ ] "Includes paid promotion" toggle ON
- [ ] Captions on-screen
- [ ] No price stated in audio/video
- [ ] Music is from YT free library or licensed
- [ ] Thumbnail/first frame isn't misleading
- [ ] Title is under 60 chars and front-loads the hook
- [ ] Hashtags: 3–5, niche-relevant
