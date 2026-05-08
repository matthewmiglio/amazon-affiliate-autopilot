// Content script — runs on every studio.youtube.com page.
// Two responsibilities:
//   1. On the channel content (video list) page: collect video IDs.
//   2. On a video edit page: open "Show more", tick the paid promotion
//      checkbox (if not already on), click Save, then signal completion.

const LOG = (...a) => console.log('[ppp-flagger]', ...a);

function remoteLog(text, cls) {
  try { chrome.runtime.sendMessage({ type: 'LOG', text: '  · ' + text, cls: cls || '' }); } catch (e) {}
}

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

function findSaveButton({ enabledOnly = false } = {}) {
  // Preferred: the canonical wrapper used by ytcp-video-details-section.
  const primary = document.querySelector('ytcp-button#save');
  if (primary) {
    const disabled = primary.getAttribute('aria-disabled') === 'true';
    if (!enabledOnly || !disabled) return { btn: primary, disabled };
  }
  // Fallback: any ytcp-button or native button labeled "Save".
  const seen = new Set();
  const candidates = [
    ...document.querySelectorAll('ytcp-button'),
    ...document.querySelectorAll('button[aria-label="Save"]'),
  ];
  for (const b of candidates) {
    if (seen.has(b)) continue;
    seen.add(b);
    const label = (b.getAttribute('aria-label') || '').trim().toLowerCase();
    const text = (b.textContent || '').trim().toLowerCase();
    if (label !== 'save' && text !== 'save') continue;
    const disabled = b.getAttribute('aria-disabled') === 'true' || b.disabled === true;
    if (enabledOnly && disabled) continue;
    return { btn: b, disabled };
  }
  return null;
}

async function clickSave() {
  const found = await waitFor(() => findSaveButton({ enabledOnly: true }), { timeoutMs: 10000 });
  if (!found) return false;
  remoteLog('save button found, clicking');
  found.btn.click();
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
  // After save, YouTube Studio greys out the Save button (aria-disabled=true)
  // until the next edit. That's the most reliable signal.
  const ok = await waitFor(() => {
    const found = findSaveButton();
    if (!found) return false;
    return found.disabled ? true : false;
  }, { timeoutMs: 15000 });
  if (ok) {
    remoteLog('save confirmed (button disabled)');
    return true;
  }
  remoteLog('save NOT confirmed within 15s — button still enabled', 'err');
  return false;
}

let lastFailReason = '';

async function processEditPage() {
  lastFailReason = '';
  LOG('processing edit page', location.pathname);
  remoteLog('waiting for editor shell');
  // Wait for editor shell
  const shell = await waitFor(() => document.querySelector('ytcp-video-metadata-editor'), { timeoutMs: 20000 });
  if (!shell) {
    lastFailReason = 'editor shell never appeared';
    remoteLog(lastFailReason, 'err');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  await sleep(500);

  // 1. Click "Show more" to reveal advanced
  remoteLog('clicking Show more');
  const opened = await clickShowMore();
  if (!opened) {
    lastFailReason = 'show-more not found';
    remoteLog(lastFailReason, 'err');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  await sleep(500);

  // 2. Tick the paid-promotion checkbox if needed
  remoteLog('locating paid-promotion checkbox');
  const state = await ensurePaidPromotionChecked();
  if (!state.ok) {
    lastFailReason = 'checkbox: ' + (state.reason || 'unknown');
    remoteLog(lastFailReason, 'err');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  if (!state.changed) {
    remoteLog('already on — no save needed');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'already' });
    return;
  }
  remoteLog('checkbox toggled ON');

  // 3. Save
  const saved = await clickSave();
  if (!saved) {
    lastFailReason = 'save button never enabled';
    remoteLog(lastFailReason, 'err');
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  remoteLog('waiting 10s for save to land');
  await sleep(10000);
  const confirmed = await waitForSaveComplete();
  if (!confirmed) {
    lastFailReason = 'save did not complete';
    chrome.runtime.sendMessage({ type: 'EDIT_DONE', result: 'failed', reason: lastFailReason });
    return;
  }
  // After a successful save, click the "Channel content" back button so we
  // exit cleanly before the background advances the queue.
  await sleep(400);
  remoteLog('clicking Channel content (exit)');
  const exited = await clickExitToChannel();
  if (!exited) remoteLog('exit button not found (continuing anyway)', 'err');
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
