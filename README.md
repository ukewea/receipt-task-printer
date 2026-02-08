# Receipt Printer Web UI

Minimal web UI for creating and printing task tickets on a thermal receipt printer.

## Features

- Web form to enter task name, priority, due date, and optional attachment
- Ticket rendering (HTML → image) with preview
- Print to a configured thermal printer
- In-memory reprint history
- Image-only mode to print a raw attachment directly (skips ticket layout)

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
- `PRINTER_IMAGE_WIDTH` (default `576`, pixels; used to scale image-only prints)
- `TICKET_PADDING_TOP` (default `0`)
- `TICKET_PADDING_RIGHT` (default `8`)

## Run

```bash
uv run web-print
```

Then open `http://127.0.0.1:8000`.

## Container

Build locally:

```bash
docker build -t receipt-printer-web .
docker run --rm -p 8000:8000 \\
  -e PRINTER_HOST=192.168.2.120 \\
  -e PRINTER_CUT_FEED=true \\
  -e PRINTER_IMAGE_WIDTH=576 \\
  receipt-printer-web
```

GitHub Actions builds and pushes to GHCR on `main` and tags. The image name is `ghcr.io/<owner>/<repo>`.

## Notes

- Ticket rendering uses `imgkit` (wkhtmltoimage) with a Selenium fallback. Install one of these toolchains if rendering fails.
- Configure your printer connection in `src/task_card_generator/printer.py` if you use USB/Serial instead of network.
- Image-only mode prints the attachment scaled to `PRINTER_IMAGE_WIDTH` to avoid cropping.

## License

MIT License - see LICENSE file for details.
