/* Shared utilities for all pages */

const priorityLabels = { '1': 'High', '2': 'Medium', '3': 'Low' };
const priorityGlyphs = { '1': '\u26A1\u26A1\u26A1', '2': '\u26A1\u26A1', '3': '\u26A1' };

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/* Printer status polling */
function initPrinterStatus() {
  const printerStatus = document.getElementById('printer-status');
  if (!printerStatus) return;
  const printerStatusText = printerStatus.querySelector('.status-text');

  async function refresh() {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      if (data.ok) {
        printerStatus.classList.remove('status-bad');
        printerStatus.classList.add('status-ok');
        printerStatusText.textContent = `Printer reachable at ${data.host}:${data.port}`;
      } else {
        printerStatus.classList.remove('status-ok');
        printerStatus.classList.add('status-bad');
        const details = data.error ? ` (${data.error})` : '';
        printerStatusText.textContent = `Printer offline at ${data.host}:${data.port}${details}`;
      }
    } catch (err) {
      printerStatus.classList.remove('status-ok');
      printerStatus.classList.add('status-bad');
      printerStatusText.textContent = 'Printer status unavailable';
    }
  }

  refresh();
  setInterval(refresh, 15000);
}

/* Dialog helpers */
function initDialog() {
  const dialog = document.getElementById('result-dialog');
  const dialogClose = document.getElementById('dialog-close');
  if (!dialog || !dialogClose) return;
  dialogClose.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) dialog.close();
  });
}

function showDialog({ success, title, bodyHtml }) {
  const dialog = document.getElementById('result-dialog');
  const dialogHeader = document.getElementById('dialog-header');
  const dialogIcon = document.getElementById('dialog-icon');
  const dialogTitle = document.getElementById('dialog-title');
  const dialogBody = document.getElementById('dialog-body');
  dialogHeader.className = success ? 'dialog-header success' : 'dialog-header error';
  dialogIcon.textContent = success ? 'OK' : '!';
  dialogTitle.textContent = title;
  dialogBody.innerHTML = bodyHtml;
  dialog.showModal();
}

/* History loading and rendering */
function loadHistory() {
  const historyList = document.getElementById('history-list');
  if (!historyList) return;

  fetch('/history')
    .then(res => res.json())
    .then(data => renderHistory(data.items || []))
    .catch(err => console.warn('Failed to load history', err));
}

function renderHistory(items) {
  const historyList = document.getElementById('history-list');
  historyList.innerHTML = '';
  if (!items.length) {
    historyList.innerHTML = '<p class="history-meta">No recent prints yet.</p>';
    return;
  }

  for (const item of items) {
    let titleText, metaText;
    if (item.type === 'todolist') {
      titleText = item.name ? escapeHtml(item.name) : 'Todolist';
      metaText = `${item.item_count || 0} items`;
    } else if (item.image_only) {
      titleText = 'Image-only print';
      metaText = 'Mode: Image-only';
    } else {
      titleText = escapeHtml(item.name || 'Untitled task');
      metaText = `Priority: ${priorityLabels[item.priority] || item.priority} \u00b7 Due: ${escapeHtml(item.due_date)}`;
    }
    const card = document.createElement('article');
    card.className = 'history-card';
    card.innerHTML = `
      <header>
        <div>
          <div><strong>${titleText}</strong></div>
          <div class="history-meta">${metaText}</div>
        </div>
        <div class="history-actions">
          <button class="btn-secondary" data-reprint="${item.id}">Reprint</button>
        </div>
      </header>
      ${item.preview ? `<div class="history-preview"><img src="${item.preview}" alt="Ticket preview" /></div>` : ''}
    `;
    historyList.appendChild(card);
  }

  historyList.querySelectorAll('[data-reprint]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = e.currentTarget.getAttribute('data-reprint');
      btn.disabled = true;
      btn.textContent = 'Reprinting...';
      try {
        const res = await fetch('/reprint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const result = await res.json();
        if (!result.success) {
          alert(result.error || 'Reprint failed');
        }
      } catch (err) {
        alert('Network error while reprinting');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Reprint';
      }
    });
  });
}
