# ID: ISS-20260223-add-print-quote-endpoint

Title: Add dedicated poster-style quote printing endpoint and layout
Status: resolved
Reported: 2026-02-23
Reporter: Andy
Severity: medium
Component: web+printing+templates
Environment: receipt-task-printer (FastAPI + python-escpos), thermal printer via TCP:9100

## Symptom

Wanted a daily upbeat-quote print with a good-looking receipt layout, and the existing endpoints were task/todolist focused.

## Expected

- A dedicated endpoint to print a quote with typographic hierarchy (header/date, big quote text, author, optional tagline).
- Should appear in print history for quick reprint.

## Actual

No dedicated quote endpoint/layout existed.

## Reproduction

1. Start server.
2. Attempt to print a quote without misusing task/todolist.

## Root Cause

Feature gap: quote-as-a-first-class printable template was missing.

## Fix Plan

- Add a dedicated quote HTML template and image renderer.
- Add `POST /print-quote` endpoint.
- Extend `/history` response and UI history renderer to support quote items.

## Validation

- Server started and `POST /print-quote` returned `{ success: true }`.
- Confirmed the printer "spitting paper" with the quote layout printed.

## References

- Code changes:
  - `src/task_card_generator/html_generator.py` (add `create_quote_html`, `create_quote_image`)
  - `src/task_card_generator/web_app.py` (add `POST /print-quote`, history support)
  - `src/task_card_generator/static/js/common.js` (render quote items in history)

## Timeline

- 2026-02-23 21:4x - Implemented quote template + endpoint.
- 2026-02-23 21:5x - Started uvicorn, tested printing.
- 2026-02-23 22:1x - Restarted server for config changes; confirmed physical print output.
