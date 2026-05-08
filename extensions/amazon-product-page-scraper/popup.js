const status = document.getElementById('status');

function setStatus(msg, cls) {
  status.textContent = msg;
  status.className = cls || '';
}

(async () => {
  setStatus('waiting');
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !/amazon\./i.test(tab.url || '')) {
      setStatus('not amazon', 'err');
      return;
    }

    setStatus('scraping');

    try {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
    } catch (e) {}

    const response = await chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE' });
    if (!response || !response.ok) {
      setStatus('failed', 'err');
      return;
    }

    const saveResult = await chrome.runtime.sendMessage({ type: 'SAVE', data: response.data });
    if (!saveResult || !saveResult.ok) {
      setStatus('failed', 'err');
      return;
    }

    setStatus('done', 'ok');
  } catch (e) {
    setStatus('failed', 'err');
  }
})();
