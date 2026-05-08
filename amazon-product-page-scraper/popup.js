const btn = document.getElementById('scrape');
const status = document.getElementById('status');

function setStatus(msg, cls) {
  status.textContent = msg;
  status.className = cls || '';
}

btn.addEventListener('click', async () => {
  btn.disabled = true;
  setStatus('Scraping...');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !/amazon\./i.test(tab.url || '')) {
      setStatus('Open an Amazon product page first.', 'err');
      btn.disabled = false;
      return;
    }

    // Make sure the content script is loaded in this tab (it won't be if the
    // tab was opened before the extension was installed/reloaded).
    try {
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
    } catch (e) {
      // ignore — already injected, or a restricted page
    }

    const response = await chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE' });
    if (!response || !response.ok) {
      setStatus('Failed: ' + (response && response.error || 'no response'), 'err');
      btn.disabled = false;
      return;
    }

    setStatus('Saving to Downloads...');
    const saveResult = await chrome.runtime.sendMessage({ type: 'SAVE', data: response.data });
    if (!saveResult || !saveResult.ok) {
      setStatus('Save failed: ' + (saveResult && saveResult.error || 'unknown'), 'err');
      btn.disabled = false;
      return;
    }

    setStatus('Saved to:\namazon-product-scrape/' + saveResult.folder, 'ok');
  } catch (e) {
    setStatus('Error: ' + (e && e.message || e), 'err');
  } finally {
    btn.disabled = false;
  }
});
