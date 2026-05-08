# Amazon Affiliate Scraper (Chrome Extension)

Scrapes the current Amazon product page, downloads the main image, grabs the SiteStripe short affiliate link, and saves everything into `Downloads/amazon-product-scrape/{slugified-product-name}/`.

## Install

1. Open `chrome://extensions`.
2. Toggle **Developer mode** on (top right).
3. Click **Load unpacked** and select this `extension/` folder.
4. (Optional) Pin the extension so the icon is always visible.

## Usage

1. Sign into Amazon Associates so the **SiteStripe** bar (with the **Get Link** button) shows at the top of every Amazon product page.
2. Visit a product page (must contain `/dp/` or `/gp/product/`).
3. Click the extension icon → **Scrape this page**.
4. Files land in:
   ```
   C:\Users\<you>\Downloads\amazon-product-scrape\<product-slug>\
       image.<ext>
       data.json
       row.txt   (pipe-delimited row: |name|description|image-path|affiliate-link|)
   ```

Repeat for each product page.

## Notes

- The extension cannot pick a custom Downloads root, that's a Chrome limitation. Keep your default Downloads folder at `C:\Users\matt\Downloads` to match the requested layout.
- If the affiliate link comes back empty, make sure SiteStripe is visible on the page (`#amzn-ss-get-link-button` must exist in the DOM). Sign into your Associates account.
- Permissions used: `downloads`, `scripting`, `activeTab`, `storage`, plus host access to amazon.com / .co.uk / .ca and media-amazon.com (for image fetch).
