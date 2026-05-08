// Content script: scrapes the Amazon product page on demand.
if (window.__AMZN_AFFILIATE_SCRAPER_LOADED__) {
  // already injected — do nothing on re-injection
} else {
  window.__AMZN_AFFILIATE_SCRAPER_LOADED__ = true;

function textOf(sel) {
  const el = document.querySelector(sel);
  return el ? el.textContent.trim().replace(/\s+/g, ' ') : '';
}

function getProductTitle() {
  return (
    textOf('#productTitle') ||
    textOf('#title') ||
    textOf('#bond-title-desktop') ||
    textOf('#bondTitleBlock_feature_div h1') ||
    document.title.replace(/\s*:\s*Amazon[\s\S]*$/i, '').trim()
  );
}

function getBrand() {
  return (
    textOf('#bylineInfo') ||
    textOf('#bond-byline') ||
    textOf('#bond-byLine-desktop') ||
    ''
  );
}

function getPrice() {
  const whole = textOf('#corePrice_desktop .a-price-whole') || textOf('.a-price .a-price-whole');
  const fraction = textOf('#corePrice_desktop .a-price-fraction') || textOf('.a-price .a-price-fraction');
  const symbol = textOf('#corePrice_desktop .a-price-symbol') || textOf('.a-price .a-price-symbol') || '$';
  if (whole) return `${symbol}${whole}${fraction ? '.' + fraction : ''}`.replace(/\s+/g, '');
  return textOf('#priceblock_ourprice') || textOf('#priceblock_dealprice') || '';
}

function getFeatureBullets() {
  const bullets = [];
  // Standard Amazon feature bullets
  document.querySelectorAll('#feature-bullets ul li:not(.aok-hidden) span.a-list-item').forEach(li => {
    const t = li.textContent.trim().replace(/\s+/g, ' ');
    if (t) bullets.push(t);
  });
  // Bond detail page per-product feature bullets
  if (!bullets.length) {
    document.querySelectorAll('.bondFeatureBulletsList li .a-list-item').forEach(li => {
      const t = li.textContent.trim().replace(/\s+/g, ' ');
      if (t) bullets.push(t);
    });
  }
  return bullets;
}

function getProductDescription() {
  // Standard product description
  const std = textOf('#productDescription') || textOf('#productDescription_feature_div');
  if (std) return std;
  // Bond detail page: per-product description lives in the inner .bondExpanderText
  // (the outer one is just the "Description" header). The inner contains an a-section.
  const candidates = document.querySelectorAll('.bondExpanderText');
  for (const c of candidates) {
    const inner = c.querySelector('.a-section');
    if (!inner) continue;
    // Skip if the .a-section only contains the bullets list (no description paragraph)
    const txt = Array.from(inner.querySelectorAll('p'))
      .map(p => p.textContent.trim().replace(/\s+/g, ' '))
      .filter(Boolean)
      .join('\n\n');
    if (txt) return txt;
  }
  return '';
}

function getAboutDesigner() {
  return textOf('.bondAboutTheDesignerText') || '';
}

function getDescription() {
  const parts = [];
  const pd = getProductDescription();
  if (pd) parts.push(pd);
  const bullets = getFeatureBullets();
  if (bullets.length) parts.push(bullets.map(b => '• ' + b).join('\n'));
  const ad = getAboutDesigner();
  if (ad) parts.push('About the Designer: ' + ad);
  return parts.join('\n\n');
}

function getMainImageUrl() {
  const img = document.querySelector('#landingImage, #imgBlkFront, #main-image, #ebooksImgBlkFront');
  if (img) {
    const hires = img.getAttribute('data-old-hires');
    if (hires) return hires;
    const dyn = img.getAttribute('data-a-dynamic-image');
    if (dyn) {
      try {
        const obj = JSON.parse(dyn);
        // pick the largest by area
        let best = null, bestArea = 0;
        for (const [url, dims] of Object.entries(obj)) {
          const area = (dims[0] || 0) * (dims[1] || 0);
          if (area > bestArea) { bestArea = area; best = url; }
        }
        if (best) return best;
      } catch (_) {}
    }
    if (img.src) return img.src;
  }
  // fallback: look at ssf-share-icon json
  const ssf = document.querySelector('[data-ssf-share-icon]');
  if (ssf) {
    try {
      const data = JSON.parse(ssf.getAttribute('data-ssf-share-icon'));
      if (data && data.image) return data.image;
    } catch (_) {}
  }
  return '';
}

function getAsin() {
  const m = location.pathname.match(/\/(?:dp|gp\/product)\/([A-Z0-9]{10})/i);
  if (m) return m[1];
  const el = document.querySelector('input#ASIN, input[name="ASIN"]');
  return el ? el.value : '';
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function readCommissionRate() {
  const el = document.querySelector('#amzn-ss-commission-rate-content');
  if (!el) return '';
  // Skip if it is the hidden "Rate unavailable" twin
  if (el.classList.contains('aok-hidden')) return '';
  const text = el.textContent.trim();
  if (!text || /unavailable/i.test(text)) return '';
  return text;
}

async function getAffiliateLinkAndCommission() {
  const btn = document.querySelector('#amzn-ss-get-link-button');
  if (!btn) {
    return { link: '', commissionRate: '', error: 'Get Link button not found. Make sure you are signed into Amazon Associates / SiteStripe is visible.' };
  }
  btn.click();

  // Poll for the textarea to populate
  let link = '';
  const start = Date.now();
  while (Date.now() - start < 8000) {
    await sleep(150);
    const ta = document.querySelector('#amzn-ss-text-shortlink-textarea');
    if (ta && ta.value && /^https?:\/\//.test(ta.value)) {
      link = ta.value.trim();
      break;
    }
  }
  if (!link) {
    const ta = document.querySelector('#amzn-ss-text-shortlink-textarea');
    return { link: ta ? ta.value.trim() : '', commissionRate: readCommissionRate(), error: ta ? '' : 'Affiliate short link textarea did not appear.' };
  }

  // Give the commission rate a moment to populate (it sometimes lags the link)
  let commissionRate = readCommissionRate();
  if (!commissionRate) {
    const t0 = Date.now();
    while (Date.now() - t0 < 2000) {
      await sleep(120);
      commissionRate = readCommissionRate();
      if (commissionRate) break;
    }
  }
  return { link, commissionRate, error: '' };
}

async function scrape() {
  const data = {
    productName: getProductTitle(),
    brand: getBrand(),
    price: getPrice(),
    description: getDescription(),
    featureBullets: getFeatureBullets(),
    asin: getAsin(),
    sourceUrl: location.href.split('?')[0],
    imageUrl: getMainImageUrl(),
    affiliateLink: '',
    commissionRate: '',
    scrapedAt: new Date().toISOString()
  };

  const aff = await getAffiliateLinkAndCommission();
  data.affiliateLink = aff.link;
  data.commissionRate = aff.commissionRate;
  data._affiliateError = aff.error || undefined;

  return data;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'SCRAPE') {
    scrape().then(data => sendResponse({ ok: true, data }))
            .catch(err => sendResponse({ ok: false, error: String(err && err.message || err) }));
    return true; // async
  }
});

}

