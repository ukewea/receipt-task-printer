/* Quote page: form submit + random quote fetch */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('quote-form');
  const submitBtn = document.getElementById('submit-btn');
  const randomBtn = document.getElementById('random-btn');
  const quoteInput = document.getElementById('quote');
  const authorInput = document.getElementById('author');
  const taglineInput = document.getElementById('tagline');

  async function fetchRandom() {
    randomBtn.disabled = true;
    randomBtn.textContent = 'Loading...';
    try {
      const res = await fetch('/quotes/random');
      const data = await res.json();
      quoteInput.value = data.quote || '';
      authorInput.value = data.author || '';
      taglineInput.value = data.tagline || '';
      quoteInput.focus();
    } catch (err) {
      showDialog({ success: false, title: 'Random quote failed', bodyHtml: `<p>${escapeHtml(err.message || 'Network error')}</p>` });
    } finally {
      randomBtn.disabled = false;
      randomBtn.textContent = 'Random quote';
    }
  }

  randomBtn.addEventListener('click', fetchRandom);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
      quote: (quoteInput.value || '').trim(),
      author: (authorInput.value || '').trim(),
      tagline: (taglineInput.value || '').trim(),
      date: new Date().toISOString().slice(0, 10),
    };

    if (!payload.quote) {
      showDialog({ success: false, title: 'Missing quote', bodyHtml: '<p>Please enter a quote.</p>' });
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Printing...';

    try {
      const response = await fetch('/print-quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await response.json();

      if (result.success) {
        const bodyHtml = `
          <p><strong>Quote:</strong> ${escapeHtml(payload.quote)}</p>
          ${payload.author ? `<p><strong>Author:</strong> ${escapeHtml(payload.author)}</p>` : ''}
          ${payload.tagline ? `<p><strong>Tagline:</strong> ${escapeHtml(payload.tagline)}</p>` : ''}
          ${result.preview ? `<div class="preview"><img src="${result.preview}" alt="Printed quote preview" /></div>` : ''}
        `;
        showDialog({ success: true, title: 'Sent to printer', bodyHtml });
        loadHistory();
      } else {
        showDialog({ success: false, title: 'Print failed', bodyHtml: `<p>${escapeHtml(result.error)}</p>` });
      }
    } catch (err) {
      showDialog({ success: false, title: 'Error', bodyHtml: `<p>Network error: ${escapeHtml(err.message)}</p>` });
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Print Quote!';
    }
  });

  initPrinterStatus();
  initDialog();
  loadHistory();

  // Preload one random quote for convenience
  fetchRandom();
});
