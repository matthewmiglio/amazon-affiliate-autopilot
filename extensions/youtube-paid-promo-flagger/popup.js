const startBtn = document.getElementById('start');
const stopBtn = document.getElementById('stop');
const copyBtn = document.getElementById('copy');
const logEl = document.getElementById('log');
const phaseEl = document.getElementById('phase');

function renderLog(lines) {
  logEl.innerHTML = '';
  for (const line of lines) {
    const div = document.createElement('div');
    div.className = line.cls || '';
    div.textContent = line.text;
    logEl.appendChild(div);
  }
  logEl.scrollTop = logEl.scrollHeight;
}

function render(s) {
  document.getElementById('kTotal').textContent = s.total || 0;
  document.getElementById('kFlagged').textContent = s.flagged || 0;
  document.getElementById('kSkipped').textContent = s.skipped || 0;
  document.getElementById('kFailed').textContent = s.failed || 0;
  const remaining = (s.queue || []).length;
  const done = (s.total || 0) - remaining;
  phaseEl.textContent = `${s.phase || 'idle'}` + (s.total ? ` — ${done}/${s.total}` : '');
  startBtn.disabled = s.phase === 'collecting' || s.phase === 'running';
  stopBtn.disabled = !(s.phase === 'collecting' || s.phase === 'running');
  renderLog(s.log || []);
}

async function refresh() {
  const s = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
  if (s) render(s);
}

startBtn.addEventListener('click', async () => {
  await chrome.runtime.sendMessage({ type: 'START' });
  refresh();
});

stopBtn.addEventListener('click', async () => {
  await chrome.runtime.sendMessage({ type: 'STOP' });
  refresh();
});

copyBtn.addEventListener('click', async () => {
  const s = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
  const lines = (s.log || []).slice(-300).map(l => l.text).join('\n');
  await navigator.clipboard.writeText(lines);
  copyBtn.textContent = 'Copied!';
  setTimeout(() => { copyBtn.textContent = 'Copy log'; }, 1200);
});

setInterval(refresh, 600);
refresh();
