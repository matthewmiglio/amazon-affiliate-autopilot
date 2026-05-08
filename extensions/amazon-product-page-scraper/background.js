// Service worker: saves image, JSON, and pipe-row text into
// Downloads/amazon-product-scrape/{slug}/

const ROOT = 'amazon-product-scrape';

// Single-slot pending filename, set just before each chrome.downloads.download
// call and consumed in onDeterminingFilename. We always issue downloads
// sequentially (await each), so one slot is enough.
let pendingFilename = null;

chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
  if (pendingFilename) {
    const f = pendingFilename;
    pendingFilename = null;
    suggest({ filename: f, conflictAction: 'uniquify' });
  } else {
    suggest();
  }
});

function slugify(s) {
  return (s || 'product')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'product';
}

function extFromUrl(url, fallback = 'jpg') {
  try {
    const u = new URL(url);
    const m = u.pathname.match(/\.([a-zA-Z0-9]{2,5})(?:$|[?#])/);
    if (m) return m[1].toLowerCase();
  } catch (_) {}
  return fallback;
}

async function blobToDataUrl(blob) {
  const buf = await blob.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let bin = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  const b64 = btoa(bin);
  const type = blob.type || 'application/octet-stream';
  return `data:${type};base64,${b64}`;
}

function startDownloadAndWait(url, filename) {
  pendingFilename = filename;
  return new Promise((resolve, reject) => {
    chrome.downloads.download({ url, conflictAction: 'uniquify', saveAs: false }, (id) => {
      if (chrome.runtime.lastError) {
        pendingFilename = null;
        return reject(new Error(chrome.runtime.lastError.message));
      }
      if (typeof id !== 'number') {
        pendingFilename = null;
        return reject(new Error('No download id'));
      }
      // Wait for completion before issuing the next download so the
      // pendingFilename slot is safely consumed in order.
      const timeout = setTimeout(() => {
        chrome.downloads.onChanged.removeListener(onChange);
        resolve(id);
      }, 30000);
      function onChange(delta) {
        if (delta.id !== id) return;
        if (delta.state && (delta.state.current === 'complete' || delta.state.current === 'interrupted')) {
          clearTimeout(timeout);
          chrome.downloads.onChanged.removeListener(onChange);
          resolve(id);
        }
      }
      chrome.downloads.onChanged.addListener(onChange);
    });
  });
}

async function saveImage(imageUrl, folder) {
  if (!imageUrl) return '';
  try {
    const res = await fetch(imageUrl);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const blob = await res.blob();
    const ext = extFromUrl(imageUrl, (blob.type.split('/')[1] || 'jpg').toLowerCase());
    const filename = `${ROOT}/${folder}/image.${ext}`;
    const url = await blobToDataUrl(blob);
    await startDownloadAndWait(url, filename);
    return filename;
  } catch (e) {
    console.error('Image save failed', e);
    return '';
  }
}

async function saveText(text, mime, filename) {
  const url = 'data:' + mime + ';base64,' + btoa(unescape(encodeURIComponent(text)));
  await startDownloadAndWait(url, filename);
}

async function handleSave(data) {
  const folder = slugify(data.productName || data.asin || 'product');
  const imagePath = await saveImage(data.imageUrl, folder);

  const record = {
    'product-name': data.productName,
    'description': data.description,
    'image-path': imagePath,
    'affiliate-link': data.affiliateLink,
    'commission-rate': data.commissionRate || '',
    'product-page-url': data.sourceUrl || '',
    meta: {
      brand: data.brand,
      price: data.price,
      asin: data.asin,
      featureBullets: data.featureBullets,
      scrapedAt: data.scrapedAt,
      affiliateError: data._affiliateError || undefined
    }
  };

  await saveText(
    JSON.stringify(record, null, 2),
    'application/json;charset=utf-8',
    `${ROOT}/${folder}/data.json`
  );

  const row = {
    'product-name': data.productName || '',
    'description': data.description || '',
    'image-path': imagePath || '',
    'affiliate-link': data.affiliateLink || '',
    'commission-rate': data.commissionRate || '',
    'product-page-url': data.sourceUrl || ''
  };
  await saveText(
    JSON.stringify(row, null, 2),
    'application/json;charset=utf-8',
    `${ROOT}/${folder}/row.json`
  );

  return { ok: true, folder };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'SAVE') {
    handleSave(msg.data)
      .then(result => sendResponse(result))
      .catch(err => sendResponse({ ok: false, error: String(err && err.message || err) }));
    return true; // async
  }
});
