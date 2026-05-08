// Content script — runs on every studio.youtube.com page.
// Two responsibilities:
//   1. On the channel content (video list) page: collect video IDs.
//   2. On a video edit page: open "Show more", tick the paid promotion
//      checkbox (if not already on), click Save, then signal completion.

const LOG = (...a) => console.log('[ppp-flagger]', ...a);

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitFor(predicate, { timeoutMs = 15000, intervalMs = 200 } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const v = predicate();
      if (v) return v;
    } catch (e) {}
    await sleep(intervalMs);
  }
  return null;
}

async function clickShortsTab() {
  const tab = await waitFor(() => {
    const tabs = document.querySelectorAll('tp-yt-paper-tab');
    for (const t of tabs) {
      const ve = t.querySelector('ytcp-ve');
      const label = ((ve && ve.textContent) || t.textContent || '').trim();
      if (label === 'Shorts') return t;
    }
    return null;
  }, { timeoutMs: 15000 });
  if (!tab) return false;
  if (tab.getAttribute('aria-selected') === 'true') return true;
  tab.click();
  return true;
}

function collectVideoIds() {
  const links = document.querySelectorAll('a#video-title[href*="/video/"][href*="/edit"]');
  const ids = [];
  for (const a of links) {
    const m = a.getAttribute('href').match(/\/video\/([^/]+)\/edit/);
    if (m) ids.push(m[1]);
  }
  return [...new Set(ids)];
}

function isEditPage() {
  return /\/video\/[^/]+\/edit/.test(location.pathname);
}

function isListPage() {
  return /\/channel\/[^/]+\/videos/.test(location.pathname) || /\/videos\//.test(location.pathname);
}

async function clickShowMore() {
  const btn = await waitFor(() => {
    const candidates = document.querySelectorAll('ytcp-button#toggle-button');
    for (const c of candidates) {
      if (c.getAttribute('aria-label') === 'Show advanced settings') return c;
    }
    return null;
  });
  if (!btn) return false;
  btn.click();
  return true;
}

async function getPaidPromotionCheckbox() {
  return await waitFor(() => {
    const host = document.querySelector('ytcp-checkbox-lit#has-ppp');
    if (!host) return null;
    const inner = host.shadowRoot
      ? host.shadowRoot.querySelector('#checkbox')
      : host.querySelector('#checkbox');
    return inner || null;
  });
}

async function ensurePaidPromotionChecked() {
  const cb = await getPaidPromotionCheckbox();
  if (!cb) return { ok: false, changed: false, reason: 'checkbox not found' };
  const checked = cb.getAttribute('aria-checked') === 'true';
  if (checked) return { ok: true, changed: false };
  cb.click();
  // verify
  await sleep(300);
  const cb2 = await getPaidPromotionCheckbox();
  const nowChecked = cb2 && cb2.getAttribute('aria-checked') === 'true';
  if (!nowChecked) return { ok: false, changed: false, reason: 'click did not toggle' };
  return { ok: true, changed: true };
}

async function clickSave() {
  // Hunt for a Save button — YouTube Studio uses ytcp-button with text "Save"
  const btn = await waitFor(() => {
    const all = document.querySelectorAll('ytcp-button');
    for (const b of all) {
      const t = (b.textContent || '').trim().toLowerCase();
      if (t === 'save' && b.getAttribute('aria-disabled') !== 'true' && !b.disabled) {
        return b;
      }
    }
    return null;
  }, { timeoutMs: 10000 });
  if (!btn) return false;
  btn.click();
  return true;
}

async function clickExitToChannel() {
  const item = await waitFor(() => {
    const items = document.querySelectorAll('tp-yt-paper-icon-item.ytcp-navigation-drawer, ytcp-navigation-drawer tp-yt-paper-icon-item');
    for (const el of items) {
      const txt = (el.textContent || '').trim();
      if (/channel content/i.test(txt)) return el;
    }
    return null;
  }, { timeoutMs: 5000 });
  if (!item) return false;
  item.click();
  return true;
}

async function waitForSaveComplete() {
  // After save, the Save button typically becomes disabled or a "Changes saved"
  // message appears. We poll for either.
  return await waitFor(() => {
    const all = document.querySelectorAll('ytcp-button');
    for (const b of all) {
      const t = (b.textContent || '').trim().toLowerCase();
      if (t === 'save') {
        if (b.getAttribute('aria-disabled') === 'true' || b.disabled) return true;
      }
    }
    // fallback — text "saved"
    if (/saved/i.test(document.body.innerText)) return true;
    return false;
  }, { timeoutMs: 10000 });
}

let lastFailReason = '';

async function processEditPage() {
  lastFailReason = '';
  LOG('processing edit page', location.pathname);
  // Wait for editor shell
  await waitFor(() => document.querySelector('ytcp-video-metadata-editor'), { timeoutMs: 20000 });
  await sleep(500);

  // 1. Click "Show more" to reveal advanced
  const opened = await clickShowMore();
  if (!opened) {
    lastFailReason = 'show-more not found';
    LOG('show-more not found');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  await sleep(500);

  // 2. Tick the paid-promotion checkbox if needed
  const state = await ensurePaidPromotionChecked();
  if (!state.ok) {
    lastFailReason = 'checkbox: ' + (state.reason || 'unknown');
    LOG('checkbox failed', state.reason);
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  if (!state.changed) {
    LOG('already on');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'already' });
    return;
  }

  // 3. Save
  const saved = await clickSave();
  if (!saved) {
    lastFailReason = 'save button not found';
    LOG('save button not found');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  await waitForSaveComplete();
  // After a successful save, click the "Channel content" back button so we
  // exit cleanly before the background advances the queue.
  await sleep(400);
  await clickExitToChannel();
  LOG('flagged + saved');
  chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'flagged' });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    if (msg.type === 'COLLECT') {
      // Click the Shorts tab first so we collect Shorts, not long-form videos.
      const tabbed = await clickShortsTab();
      if (!tabbed) {
        chrome.runtime.sendMessage({ type: 'LOG', text: 'Shorts tab not found', cls: 'err' });
      } else {
        await sleep(800);
      }
      // Wait for the list to render
      await waitFor(() => collectVideoIds().length > 0, { timeoutMs: 20000 });
      const ids = collectVideoIds();
      chrome.runtime.sendMessage({ type: 'COLLECT_RESULT', ids });
      sendResponse({ ok: true, count: ids.length });
      return;
    }
    if (msg.type === 'PROCESS_EDIT') {
      await processEditPage();
      sendResponse({ ok: true });
      return;
    }
  })();
  return true;
});

// Self-kick on edit pages — onUpdated may have already fired before this script
// registered its listener. Ask the background if we should be processing.
(async () => {
  if (!isEditPage()) return;
  try {
    const s = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
    if (s && s.phase === 'running' && s.queue && s.queue.length) {
      // Only auto-run if URL matches the head of the queue.
      const expected = s.queue[0];
      if (location.pathname.includes('/video/' + expected + '/edit')) {
        processEditPage();
      }
    }
  } catch (e) {}
})();
