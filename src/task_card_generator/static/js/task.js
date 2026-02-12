/* Task page: form submit, image-only toggle, drag-drop, date picker, clipboard paste */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('print-form');
  const submitBtn = document.getElementById('submit-btn');
  const dueDateInput = document.getElementById('due_date');
  const priorityRadios = document.querySelectorAll('input[name="priority"]');
  const attachmentInput = document.getElementById('attachment');
  const dropzone = document.getElementById('dropzone');
  const attachmentPreview = document.getElementById('attachment-preview');
  const attachmentPreviewImg = document.getElementById('attachment-preview-img');
  const imageOnlyToggle = document.getElementById('image_only');
  const taskNameInput = document.getElementById('name');
  const modeHelp = document.getElementById('mode-help');
  const priorityGroup = document.querySelector('.priority-group');
  const dueDateLabel = dueDateInput.closest('label');
  const operatorSignatureInput = document.getElementById('operator_signature');
  const operatorSignatureLabel = operatorSignatureInput.closest('label');

  function setDefaultDate() {
    if (!dueDateInput.value) {
      const today = new Date();
      const offsetDate = new Date(today.getTime() - (today.getTimezoneOffset() * 60000));
      dueDateInput.value = offsetDate.toISOString().slice(0, 10);
    }
  }

  function openDatePicker() {
    setDefaultDate();
    if (typeof dueDateInput.showPicker === 'function') {
      dueDateInput.showPicker();
    } else {
      dueDateInput.focus();
    }
  }

  function ensureDateValue() {
    if (!dueDateInput.value) {
      setDefaultDate();
    }
  }

  function applyImageOnlyMode() {
    const isImageOnly = imageOnlyToggle.checked;
    taskNameInput.required = !isImageOnly;
    dueDateInput.required = !isImageOnly;
    if (isImageOnly) {
      taskNameInput.value = '';
      taskNameInput.setAttribute('disabled', 'disabled');
      taskNameInput.parentElement.classList.add('dimmed');
      dueDateInput.setAttribute('disabled', 'disabled');
      if (dueDateLabel) dueDateLabel.classList.add('dimmed');
      operatorSignatureInput.value = '';
      operatorSignatureInput.setAttribute('disabled', 'disabled');
      if (operatorSignatureLabel) operatorSignatureLabel.classList.add('dimmed');
      priorityRadios.forEach(r => r.setAttribute('disabled', 'disabled'));
      if (priorityGroup) priorityGroup.classList.add('dimmed');
      modeHelp.textContent = 'Image-only mode prints the attachment directly.';
    } else {
      taskNameInput.removeAttribute('disabled');
      taskNameInput.parentElement.classList.remove('dimmed');
      dueDateInput.removeAttribute('disabled');
      if (dueDateLabel) dueDateLabel.classList.remove('dimmed');
      operatorSignatureInput.removeAttribute('disabled');
      if (operatorSignatureLabel) operatorSignatureLabel.classList.remove('dimmed');
      priorityRadios.forEach(r => r.removeAttribute('disabled'));
      if (priorityGroup) priorityGroup.classList.remove('dimmed');
      modeHelp.textContent = 'Attach an image below to print it directly.';
    }
  }

  setDefaultDate();
  applyImageOnlyMode();
  dueDateInput.addEventListener('click', openDatePicker);
  dueDateInput.addEventListener('focus', openDatePicker);
  dueDateInput.addEventListener('change', ensureDateValue);
  dueDateInput.addEventListener('blur', ensureDateValue);
  dueDateInput.addEventListener('input', ensureDateValue);
  imageOnlyToggle.addEventListener('change', applyImageOnlyMode);

  /* Form submit */
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (imageOnlyToggle.checked && !(attachmentInput.files && attachmentInput.files.length)) {
      alert('Please attach an image to use image-only mode.');
      return;
    }

    const formData = new FormData(form);
    submitBtn.disabled = true;
    submitBtn.textContent = 'Printing...';

    try {
      const response = await fetch('/print', { method: 'POST', body: formData });
      const result = await response.json();

      if (result.success) {
        let bodyHtml;
        if (result.image_only) {
          bodyHtml = `
            <p><strong>Mode:</strong> Image-only</p>
            ${result.preview ? `<div class="preview"><img src="${result.preview}" alt="Printed image preview" /></div>` : ''}
          `;
        } else {
          bodyHtml = `
            <p><strong>Task:</strong> ${escapeHtml(result.task.name)}</p>
            <p><strong>Priority:</strong> ${priorityGlyphs[result.task.priority] || ''} ${priorityLabels[result.task.priority] || result.task.priority}</p>
            <p><strong>Due:</strong> ${escapeHtml(result.task.due_date)}</p>
            ${result.preview ? `<div class="preview"><img src="${result.preview}" alt="Printed ticket preview" /></div>` : ''}
          `;
        }
        showDialog({ success: true, title: 'Sent to printer', bodyHtml });
        const savedDueDate = dueDateInput.value;
        form.reset();
        dueDateInput.value = savedDueDate;
        priorityRadios.forEach(r => r.checked = r.value === '2');
        attachmentInput.value = '';
        showPreview(null);
        applyImageOnlyMode();
        loadHistory();
      } else {
        showDialog({ success: false, title: 'Print failed', bodyHtml: `<p>${escapeHtml(result.error)}</p>` });
      }
    } catch (err) {
      showDialog({ success: false, title: 'Error', bodyHtml: `<p>Network error: ${escapeHtml(err.message)}</p>` });
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Print!';
    }
  });

  /* Drag-and-drop */
  ['dragenter', 'dragover'].forEach(evt =>
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    })
  );
  ['dragleave', 'drop'].forEach(evt =>
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    })
  );
  dropzone.addEventListener('drop', e => {
    const files = e.dataTransfer.files;
    if (files && files.length) setAttachmentFile(files[0]);
  });
  dropzone.addEventListener('click', () => attachmentInput.click());

  function setAttachmentFile(file) {
    if (!file) return;
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      attachmentInput.files = dt.files;
      showPreview(file);
    } catch (err) {
      showPreview(file);
    }
  }

  /* Paste support */
  function handlePaste(e) {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type && item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) {
          setAttachmentFile(file);
          e.preventDefault();
          break;
        }
      }
    }
  }
  dropzone.addEventListener('paste', handlePaste);
  window.addEventListener('paste', handlePaste);

  attachmentInput.addEventListener('change', () => {
    const file = attachmentInput.files?.[0];
    if (file) showPreview(file);
  });

  function showPreview(file) {
    if (!file) {
      attachmentPreview.style.display = 'none';
      dropzone.classList.remove('has-image');
      attachmentPreviewImg.src = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = e => {
      attachmentPreviewImg.src = e.target.result;
      attachmentPreview.style.display = 'flex';
      dropzone.classList.add('has-image');
    };
    reader.onerror = () => {
      attachmentPreview.style.display = 'none';
      dropzone.classList.remove('has-image');
      attachmentPreviewImg.src = '';
    };
    reader.readAsDataURL(file);
  }

  /* Init shared components */
  initPrinterStatus();
  initDialog();
  loadHistory();
});
