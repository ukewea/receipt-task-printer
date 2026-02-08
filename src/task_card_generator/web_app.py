#!/usr/bin/env python3
"""Minimal web UI to submit a task and print to the receipt printer."""

import base64
import os
from collections import deque
from types import SimpleNamespace
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

from .html_generator import create_task_image
from . import print_to_thermal_printer

load_dotenv()
RETAIN_TICKET_FILES = os.getenv("RETAIN_TICKET_FILES", "false").lower() not in {"false", "0", "no"}
WEB_APP_HOST = os.getenv("WEB_APP_HOST", "127.0.0.1")
WEB_APP_PORT = int(os.getenv("WEB_APP_PORT", "8000"))
HISTORY_LIMIT = 10
_history = deque(maxlen=HISTORY_LIMIT)


FORM_HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Receipt Printer – Print Task</title>
    <style>
      * { box-sizing: border-box; }
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Arial, "Apple Color Emoji", "Segoe UI Emoji"; margin: 2rem; overflow-x: hidden; }
      .wrap { max-width: 640px; margin: 0 auto; }
      h1 { margin: 0 0 1rem; }
      form { display: grid; gap: 1rem; }
      label { display: grid; gap: 0.35rem; font-weight: 600; }
      input[type="text"], input[type="date"], select { padding: 0.6rem 0.7rem; font-size: 1rem; border: 1px solid #ccc; border-radius: 6px; }
      button { padding: 0.7rem 1rem; font-size: 1rem; background: #111; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }
      button:disabled { background: #666; cursor: not-allowed; }
      .msg { padding: 0.8rem 1rem; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; }

      /* Dialog styles */
      dialog { border: none; border-radius: 12px; padding: 0; max-width: 400px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); }
      dialog::backdrop { background: rgba(0,0,0,0.5); }
      .dialog-content { padding: 1.5rem; }
      .dialog-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
      .dialog-header.success { color: #059669; }
      .dialog-header.error { color: #dc2626; }
      .dialog-icon { font-size: 1.5rem; }
      .dialog-title { font-size: 1.25rem; font-weight: 600; margin: 0; }
      .dialog-body { color: #374151; line-height: 1.5; }
      .dialog-body p { margin: 0.5rem 0; }
      .dialog-body strong { color: #111; }
      .preview { margin-top: 0.75rem; text-align: center; }
      .preview img { max-width: 80%; margin: 0 auto; border-radius: 8px; border: 1px solid #e5e7eb; display: block; box-sizing: border-box; }
      .dialog-footer { padding: 1rem 1.5rem; background: #f9fafb; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; }
      .dialog-close { padding: 0.5rem 1rem; font-size: 0.95rem; background: #111; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }

      .history { margin: 2.5rem auto 0; max-width: 640px; width: 100%; }
      .history h2 { margin: 0 0 0.35rem; font-size: 1.15rem; }
      .history-note { color: #6b7280; font-size: 0.95rem; margin: 0 0 0.75rem; }
      .history-list { display: flex; flex-direction: column; gap: 0.9rem; width: 100%; }
      .history-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 0.9rem 1rem; background: #fff; display: grid; gap: 0.4rem; box-shadow: 0 6px 16px rgba(0,0,0,0.04); width: 100%; }
      .history-card header { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap; }
      .history-meta { color: #4b5563; font-size: 0.95rem; }
      .history-preview { text-align: center; margin-top: 0.5rem; display: flex; justify-content: center; }
      .history-preview img { max-width: 70%; border-radius: 6px; border: 1px solid #e5e7eb; display: block; box-sizing: border-box; }
      .history-actions { display: flex; gap: 0.5rem; justify-content: flex-end; }
      .btn-secondary { padding: 0.5rem 0.9rem; font-size: 0.95rem; background: #f8fafc; color: #111; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: background 120ms ease, transform 120ms ease; }
      .btn-secondary:hover { background: #eef2f7; }
      .btn-secondary:active { transform: translateY(1px); }

      .priority-group { display: grid; gap: 0.5rem; }
      .priority-options { display: flex; gap: 0.5rem; flex-wrap: wrap; }
      .priority-pill { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; border: 1px solid #d1d5db; border-radius: 999px; cursor: pointer; background: #fff; transition: border-color 120ms ease, box-shadow 120ms ease; flex: 1 1 140px; min-width: 120px; box-sizing: border-box; }
      .priority-pill input { display: none; }
      .priority-pill .glyph { font-size: 1.2rem; }
      .priority-pill .text { font-size: 0.95rem; font-weight: 600; }
      .priority-pill:hover { border-color: #9ca3af; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
      .priority-pill input:checked + .glyph { color: #111; }
      .priority-pill input:checked ~ .text { color: #111; }
      .priority-pill input:checked ~ .glyph { transform: translateY(-1px); }

      .row-split { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: end; }
      .attachment-block { display: grid; gap: 0.4rem; }
      .dropzone {
        border: 2px dashed #d1d5db;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        color: #4b5563;
        background: #f8fafc;
        transition: border-color 120ms ease, background 120ms ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
        min-height: 160px;
      }
      .dropzone.dragover {
        border-color: #111;
        background: #eef2f7;
      }
      .dropzone small { display: block; margin-top: 0.35rem; color: #6b7280; }
      .dropzone .overlay-text { position: relative; z-index: 1; }
      .dropzone.has-image .overlay-text { opacity: 0; pointer-events: none; }
      .preview-box { position: absolute; inset: 0; display: none; align-items: center; justify-content: center; padding: 0.5rem; background: #f8fafc; }
      .preview-box img { max-width: 100%; max-height: 280px; border-radius: 6px; border: 1px solid #e5e7eb; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }

      @media (max-width: 540px) {
        body { margin: 1.25rem; }
        .wrap, .history { margin: 0 auto; width: 100%; }
        .priority-options { flex-direction: column; }
        .priority-pill { width: 100%; flex: 1 1 auto; }
        .history-preview img { max-width: 70%; }
        .row-split { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>Print a Task</h1>
      <p class="msg">Enter a task and click Print! It will render a ticket and send it to your configured thermal printer.</p>
      <form id="print-form">
        <label>
          Task name
          <input type="text" name="name" id="name" required placeholder="e.g., Pick up dry cleaning" />
        </label>
        <div class="priority-group">
          <div>Priority</div>
          <div class="priority-options" role="radiogroup" aria-label="Priority">
            <label class="priority-pill">
              <input type="radio" name="priority" value="1" aria-label="High" />
              <span class="glyph">⚡⚡⚡</span>
              <span class="text">High</span>
            </label>
            <label class="priority-pill">
              <input type="radio" name="priority" value="2" aria-label="Medium" checked />
              <span class="glyph">⚡⚡</span>
              <span class="text">Medium</span>
            </label>
            <label class="priority-pill">
              <input type="radio" name="priority" value="3" aria-label="Low" />
              <span class="glyph">⚡</span>
              <span class="text">Low</span>
            </label>
          </div>
        </div>
        <div class="row-split">
          <label>
            Due date
            <input type="date" name="due_date" id="due_date" required inputmode="none" />
          </label>
          <label>
            Op. signature
            <input type="text" name="operator_signature" id="operator_signature" placeholder="e.g., Alice" />
          </label>
        </div>
        <div class="attachment-block">
          <label>
            Attachment image (optional)
            <input type="file" name="attachment" id="attachment" accept="image/*" style="display:none" />
            <div id="dropzone" class="dropzone">
              <div class="overlay-text">
                Drag an image here, click to browse, or paste from clipboard
                <small>Shown at the bottom of the ticket</small>
              </div>
              <div id="attachment-preview" class="preview-box">
                <img id="attachment-preview-img" alt="Attachment preview" />
              </div>
            </div>
          </label>
        </div>
        <div>
          <button type="submit" id="submit-btn">Print!</button>
        </div>
      </form>
    </div>

    <dialog id="result-dialog">
      <div class="dialog-content">
        <div class="dialog-header" id="dialog-header">
          <span class="dialog-icon" id="dialog-icon"></span>
          <h2 class="dialog-title" id="dialog-title"></h2>
        </div>
        <div class="dialog-body" id="dialog-body"></div>
      </div>
      <div class="dialog-footer">
        <button class="dialog-close" id="dialog-close">OK</button>
      </div>
    </dialog>

    <section class="history" aria-label="Recent prints">
      <h2>Recent prints</h2>
      <p class="history-note">Last 10 tickets stay in memory for quick reprint.</p>
      <div class="history-list" id="history-list"></div>
    </section>

    <script>
      const form = document.getElementById('print-form');
      const dialog = document.getElementById('result-dialog');
      const dialogHeader = document.getElementById('dialog-header');
      const dialogIcon = document.getElementById('dialog-icon');
      const dialogTitle = document.getElementById('dialog-title');
      const dialogBody = document.getElementById('dialog-body');
      const dialogClose = document.getElementById('dialog-close');
      const submitBtn = document.getElementById('submit-btn');
      const dueDateInput = document.getElementById('due_date');
      const historyList = document.getElementById('history-list');
      const priorityRadios = document.querySelectorAll('input[name=\"priority\"]');
      const attachmentInput = document.getElementById('attachment');
      const dropzone = document.getElementById('dropzone');
      const attachmentPreview = document.getElementById('attachment-preview');
      const attachmentPreviewImg = document.getElementById('attachment-preview-img');

      const priorityLabels = { '1': 'High', '2': 'Medium', '3': 'Low' };
      const priorityGlyphs = { '1': '⚡⚡⚡', '2': '⚡⚡', '3': '⚡' };

      function setDefaultDate() {
        if (!dueDateInput.value) {
          const today = new Date();
          // Normalize to local date string (yyyy-mm-dd)
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

      setDefaultDate();
      dueDateInput.addEventListener('click', openDatePicker);
      dueDateInput.addEventListener('focus', openDatePicker);
      dueDateInput.addEventListener('change', ensureDateValue);
      dueDateInput.addEventListener('blur', ensureDateValue);
      dueDateInput.addEventListener('input', ensureDateValue);

      async function loadHistory() {
        try {
          const res = await fetch('/history');
          const data = await res.json();
          renderHistory(data.items || []);
        } catch (err) {
          console.warn('Failed to load history', err);
        }
      }

      function renderHistory(items) {
        historyList.innerHTML = '';
        if (!items.length) {
          historyList.innerHTML = '<p class="history-meta">No recent prints yet.</p>';
          return;
        }

        for (const item of items) {
          const card = document.createElement('article');
          card.className = 'history-card';
          card.innerHTML = `
            <header>
              <div>
                <div><strong>${escapeHtml(item.name)}</strong></div>
                <div class="history-meta">Priority: ${priorityLabels[item.priority] || item.priority} · Due: ${escapeHtml(item.due_date)}</div>
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

      form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(form);
        submitBtn.disabled = true;
        submitBtn.textContent = 'Printing...';

        try {
          const response = await fetch('/print', {
            method: 'POST',
            body: formData
          });

          const result = await response.json();

          if (result.success) {
            dialogHeader.className = 'dialog-header success';
            dialogIcon.textContent = 'OK';
            dialogTitle.textContent = 'Sent to printer';
            dialogBody.innerHTML = `
              <p><strong>Task:</strong> ${escapeHtml(result.task.name)}</p>
              <p><strong>Priority:</strong> ${priorityGlyphs[result.task.priority] || ''} ${priorityLabels[result.task.priority] || result.task.priority}</p>
              <p><strong>Due:</strong> ${escapeHtml(result.task.due_date)}</p>
              ${result.preview ? `<div class="preview"><img src="${result.preview}" alt="Printed ticket preview" /></div>` : ''}
            `;
            // Clear form on success for next task, but keep due date
            const savedDueDate = dueDateInput.value;
            form.reset();
            dueDateInput.value = savedDueDate;
            // Reset default priority to Medium
            priorityRadios.forEach(r => r.checked = r.value === '2');
            // Clear attachment preview and input
            attachmentInput.value = '';
            showPreview(null);
            loadHistory();
          } else {
            dialogHeader.className = 'dialog-header error';
            dialogIcon.textContent = '!';
            dialogTitle.textContent = 'Print failed';
            dialogBody.innerHTML = `<p>${escapeHtml(result.error)}</p>`;
          }

          dialog.showModal();
        } catch (err) {
          dialogHeader.className = 'dialog-header error';
          dialogIcon.textContent = '!';
          dialogTitle.textContent = 'Error';
          dialogBody.innerHTML = `<p>Network error: ${escapeHtml(err.message)}</p>`;
          dialog.showModal();
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Print!';
        }
      });

      dialogClose.addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', (e) => {
        if (e.target === dialog) dialog.close();
      });

      function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
      }

      // Drag-and-drop for attachment
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
        if (files && files.length) {
          setAttachmentFile(files[0]);
        }
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
          // Fallback: show preview even if assignment not supported
          showPreview(file);
        }
      }

      // Paste support for images (desktop/mobile)
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
        if (file) {
          showPreview(file);
        }
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

      loadHistory();
    </script>
  </body>
</html>
"""


app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(FORM_HTML)


@app.post("/print")
async def handle_print(
    request: Request,
    name: Optional[str] = Form(default=None),
    priority: Optional[str] = Form(default=None),
    due_date: Optional[str] = Form(default=None),
    operator_signature: Optional[str] = Form(default=None),
    attachment: Optional[UploadFile] = File(default=None),
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        name = (payload.get("name") or "").strip()
        priority_raw = str(payload.get("priority") or "2").strip()
        due_date = (payload.get("due_date") or "").strip()
        operator_signature = (payload.get("operator_signature") or "").strip()
        attachment_bytes = None
    else:
        name = (name or "").strip()
        priority_raw = (priority or "2").strip()
        due_date = (due_date or "").strip()
        operator_signature = (operator_signature or "").strip()
        attachment_bytes = None
        if attachment:
            try:
                attachment_bytes = await attachment.read()
            except Exception:
                attachment_bytes = None

    if not name or not due_date:
        return JSONResponse(
            {"success": False, "error": "Missing name or due date."},
            status_code=400,
        )

    try:
        priority = int(priority_raw)
        if priority not in (1, 2, 3):
            priority = 2
    except Exception:
        priority = 2

    # Build a simple object with the attributes expected by the HTML generator
    task_obj = SimpleNamespace(
        name=name,
        priority=priority,
        due_date=due_date,
        operator_signature=operator_signature,
        attachment_bytes=attachment_bytes,
    )

    # Generate an image from the HTML ticket (optionally avoiding disk)
    image_path, image_bytes = create_task_image(task_obj, retain_file=RETAIN_TICKET_FILES)
    if image_path is None and image_bytes is None:
        return JSONResponse(
            {
                "success": False,
                "error": "Failed to render ticket image. Ensure wkhtmltoimage or Selenium+Chrome are installed.",
            },
            status_code=500,
        )

    # Convert to grayscale for thermal printer, and for preview/history storage
    preview_data = None
    if image_bytes is not None:
        try:
            with Image.open(BytesIO(image_bytes)) as im:
                gray = im.convert("L")
                buf = BytesIO()
                gray.save(buf, format="PNG")
                image_bytes = buf.getvalue()
                encoded = base64.b64encode(image_bytes).decode("ascii")
                preview_data = f"data:image/png;base64,{encoded}"
        except Exception:
            try:
                encoded = base64.b64encode(image_bytes).decode("ascii")
                preview_data = f"data:image/png;base64,{encoded}"
            except Exception:
                preview_data = None

    # Send image to thermal printer
    try:
        print_to_thermal_printer(image_bytes=image_bytes)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": f"Failed to print: {str(e)}"},
            status_code=500,
        )

    # Append to in-memory history
    try:
        _history.appendleft({
            "id": len(_history) + 1 if not _history else (_history[0]["id"] + 1),
            "name": name,
            "priority": priority,
            "due_date": due_date,
            "preview": preview_data,
            "image_bytes": image_bytes,
            "operator_signature": operator_signature,
        })
    except Exception:
        pass

    # Success response
    return JSONResponse({
        "success": True,
        "task": {
            "name": name,
            "priority": priority,
            "due_date": due_date,
            "operator_signature": operator_signature,
        },
        "preview": preview_data,
    })


@app.get("/history")
async def history(_: Request):
    """Return recent prints (excluding raw bytes)."""
    items = []
    for entry in _history:
        items.append({
            "id": entry["id"],
            "name": entry["name"],
            "priority": entry["priority"],
            "due_date": entry["due_date"],
            "preview": entry.get("preview"),
        })
    return JSONResponse({"items": items})


@app.post("/reprint")
async def reprint(request: Request):
    """Reprint a previous ticket by id."""
    payload = await request.json()
    target_id = str(payload.get("id"))

    entry = next((h for h in _history if str(h["id"]) == target_id), None)
    if not entry:
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)

    try:
        print_to_thermal_printer(image_bytes=entry.get("image_bytes"))
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Failed to reprint: {e}"}, status_code=500)

    return JSONResponse({"success": True})


def main():
    """Run the development server via a script entry point."""
    import uvicorn

    uvicorn.run(app, host=WEB_APP_HOST, port=WEB_APP_PORT)


if __name__ == "__main__":
    main()
