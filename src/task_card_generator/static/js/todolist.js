/* Todolist page: dynamic item list, Enter/Backspace handling, form submit */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('todolist-form');
  const itemList = document.getElementById('item-list');
  const addItemBtn = document.getElementById('add-item-btn');
  const submitBtn = document.getElementById('submit-btn');

  function createItemRow(value) {
    const row = document.createElement('div');
    row.className = 'item-row';
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Item...';
    input.value = value || '';
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'item-remove';
    removeBtn.textContent = '\u00d7';
    removeBtn.addEventListener('click', () => {
      if (itemList.children.length > 1) {
        const prev = row.previousElementSibling;
        row.remove();
        if (prev) prev.querySelector('input').focus();
        else if (itemList.children.length) itemList.children[0].querySelector('input').focus();
      }
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const newRow = createItemRow('');
        row.after(newRow);
        newRow.querySelector('input').focus();
      } else if (e.key === 'Backspace' && input.value === '' && itemList.children.length > 1) {
        e.preventDefault();
        const prev = row.previousElementSibling;
        const next = row.nextElementSibling;
        row.remove();
        if (prev) {
          const prevInput = prev.querySelector('input');
          prevInput.focus();
          prevInput.setSelectionRange(prevInput.value.length, prevInput.value.length);
        } else if (next) {
          next.querySelector('input').focus();
        }
      }
    });

    row.appendChild(input);
    row.appendChild(removeBtn);
    return row;
  }

  function addItem(value) {
    const row = createItemRow(value);
    itemList.appendChild(row);
    return row;
  }

  /* Initial empty item */
  const firstRow = addItem('');
  firstRow.querySelector('input').focus();

  addItemBtn.addEventListener('click', () => {
    const row = addItem('');
    row.querySelector('input').focus();
  });

  /* Form submit */
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = document.getElementById('todolist-title').value.trim();
    const items = Array.from(itemList.querySelectorAll('input'))
      .map(input => input.value.trim())
      .filter(v => v.length > 0);

    if (items.length === 0) {
      alert('Please add at least one item.');
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Printing...';

    try {
      const response = await fetch('/print-todolist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, items })
      });
      const result = await response.json();

      if (result.success) {
        const bodyHtml = `
          <p><strong>Items:</strong> ${result.item_count}</p>
          ${result.preview ? `<div class="preview"><img src="${result.preview}" alt="Todolist preview" /></div>` : ''}
        `;
        showDialog({ success: true, title: 'Sent to printer', bodyHtml });
        /* Reset form but keep one empty row */
        document.getElementById('todolist-title').value = '';
        itemList.innerHTML = '';
        const row = addItem('');
        row.querySelector('input').focus();
        loadHistory();
      } else {
        showDialog({ success: false, title: 'Print failed', bodyHtml: `<p>${escapeHtml(result.error)}</p>` });
      }
    } catch (err) {
      showDialog({ success: false, title: 'Error', bodyHtml: `<p>Network error: ${escapeHtml(err.message)}</p>` });
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Print Todolist!';
    }
  });

  /* Edit support: load history data into form */
  window.loadTodolistForEdit = function(item) {
    document.getElementById('todolist-title').value = item.name || '';
    itemList.innerHTML = '';
    const entries = item.items || [];
    if (entries.length === 0) {
      addItem('');
    } else {
      entries.forEach(text => addItem(text));
    }
    itemList.querySelector('input').focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /* Init shared components */
  initPrinterStatus();
  initDialog();
  loadHistory();

  /* Check for ?edit= query param */
  const editId = new URLSearchParams(window.location.search).get('edit');
  if (editId) {
    fetch('/history')
      .then(res => res.json())
      .then(data => {
        const entry = (data.items || []).find(i => String(i.id) === editId);
        if (entry) window.loadTodolistForEdit(entry);
      })
      .catch(() => {});
    /* Clean up URL */
    window.history.replaceState({}, '', '/todolist');
  }
});
