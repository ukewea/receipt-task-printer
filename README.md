# Receipt Printer Web UI

Minimal web UI for creating and printing task tickets on a thermal receipt printer.

## Features

- Web form to enter task name, priority, due date, and optional attachment
- Ticket rendering (HTML → image) with preview
- Print to a configured thermal printer
- In-memory reprint history

## Installation (with uv)

```bash
uv sync
```

### Alternative: pip

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and adjust as needed.

Required/optional environment variables:
- `WEB_APP_HOST` (default `127.0.0.1`)
- `WEB_APP_PORT` (default `8000`)
- `RETAIN_TICKET_FILES` (default `false`)
- `PRINTER_HOST` (default `192.168.2.120`)
- `PRINTER_CUT_FEED` (default `true`)
- `TICKET_PADDING_TOP` (default `0`)
- `TICKET_PADDING_RIGHT` (default `8`)

## Run

```bash
uv run web-print
```

Then open `http://127.0.0.1:8000`.

## Notes

- Ticket rendering uses `imgkit` (wkhtmltoimage) with a Selenium fallback. Install one of these toolchains if rendering fails.
- Configure your printer connection in `src/task_card_generator/printer.py` if you use USB/Serial instead of network.

## License

MIT License - see LICENSE file for details.
