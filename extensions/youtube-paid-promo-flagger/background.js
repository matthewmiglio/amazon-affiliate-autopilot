// Background service worker — owns the run state, log, and drives navigation.

const CHANNEL_VIDEOS_URL = 'https://studio.youtube.com/channel/UCKbyJ1ZgXhuzlFkcLPI-2vQ/videos';
const MAX_LOG = 600;

const DEFAULT_STATE = {
  phase: 'idle',          // idle | navigating | collecting | running | done | error
  tabId: null,
  queue: [],
  total: 0,
  flagged: 0,
  skipped: 0,
  failed: 0,
  lastSlug: '',
  error: '',
  log: []
};

async function getState() {
  const { state } = await chrome.storage.session.get('state');
  return state || { ...DEFAULT_STATE };
}

async function setState(patch) {
  const cur = await getState();
  const next = { ...cur, ...patch };
  await chrome.storage.session.set({ state: next });
  return next;
}

function ts() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
}

async function log(text, cls) {
  const s = await getState();
  const entry = { text: `[${ts()}] ${text}`, cls: cls || '' };
  const arr = (s.log || []).concat([entry]);
  if (arr.length > MAX_LOG) arr.splice(0, arr.length - MAX_LOG);
  await setState({ log: arr });
}

async function start() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    await setState({ phase: 'error', error: 'no active tab' });
    await log('no active tab', 'err');
    return;
  }
  await chrome.storage.session.set({ state: { ...DEFAULT_STATE } });
  await setState({ phase: 'navigating', tabId: tab.id });
  await log('navigating to channel videos page…', 'info');
  await chrome.tabs.update(tab.id, { url: CHANNEL_VIDEOS_URL });
  // onUpdated handler will pick it up after load
}

async function stop() {
  await log('stopped by user', 'info');
  await setState({ phase: 'idle', queue: [] });
}

async function processNext() {
  const s = await getState();
  if (s.phase !== 'running') return;
  if (!s.queue.length) {
    await setState({ phase: 'done' });
    await log(`done — ${s.flagged} flipped, ${s.skipped} skipped, ${s.failed} failed`, 'ok');
    return;
  }
  const next = s.queue[0];
  await setState({ lastSlug: next });
  const url = `https://studio.youtube.com/video/${next}/edit`;
  await log(`opening ${next}`, 'info');
  await chrome.tabs.update(s.tabId, { url });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (msg.type === 'GET_STATE') {
      sendResponse(await getState());
      return;
    }
    if (msg.type === 'START') {
      await start();
      sendResponse({ ok: true });
      return;
    }
    if (msg.type === 'STOP') {
      await stop();
      sendResponse({ ok: true });
      return;
    }
    if (msg.type === 'COLLECT_RESULT') {
      const ids = msg.ids || [];
      if (!ids.length) {
        await setState({ phase: 'error', error: 'no videos found' });
        await log('no videos found on this page', 'err');
        sendResponse({ ok: true });
        return;
      }
      await log(`found ${ids.length} videos — beginning run`, 'ok');
      await setState({ phase: 'running', queue: ids, total: ids.length });
      processNext();
      sendResponse({ ok: true });
      return;
    }
    if (msg.type === 'EDIT_DONE') {
      const s = await getState();
      if (s.phase !== 'running') { sendResponse({ ok: true }); return; }
      const slug = s.queue[0];
      const queue = s.queue.slice(1);
      const patch = { queue };
      if (msg.result === 'flagged') {
        patch.flagged = (s.flagged || 0) + 1;
        await log(`✓ flipped: ${slug}`, 'ok');
      } else if (msg.result === 'already') {
        patch.skipped = (s.skipped || 0) + 1;
        await log(`= skipped (already on): ${slug}`, 'info');
      } else {
        patch.failed = (s.failed || 0) + 1;
        await log(`✗ failed: ${slug} (${msg.reason || 'unknown'})`, 'err');
      }
      await setState(patch);
      processNext();
      sendResponse({ ok: true });
      return;
    }
    if (msg.type === 'LOG') {
      await log(msg.text, msg.cls);
      sendResponse({ ok: true });
      return;
    }
  })();
  return true;
});

chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (info.status !== 'complete') return;
  const s = await getState();
  if (s.tabId !== tabId) return;

  if (s.phase === 'navigating') {
    // Verify we landed on a /videos list page
    if (!/\/videos$/.test(tab.url || '') && !/\/videos\b/.test(tab.url || '')) {
      // YouTube studio sometimes redirects through several URLs; just wait
      return;
    }
    await setState({ phase: 'collecting' });
    await log('collecting video list…', 'info');
    try {
      await chrome.tabs.sendMessage(tabId, { type: 'COLLECT' });
    } catch (e) {
      await setState({ phase: 'error', error: 'content script not ready' });
      await log('content script not ready — refresh the page', 'err');
    }
    return;
  }

  if (s.phase === 'running' && s.queue.length) {
    try {
      await chrome.tabs.sendMessage(tabId, { type: 'PROCESS_EDIT', videoId: s.queue[0] });
    } catch (e) {
      // content script auto-kicks itself, but log if needed
    }
  }
});
