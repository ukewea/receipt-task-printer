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

## Rendering and fonts

Requires Python 3.10+. Fullbleed 2.5.51 renders static ticket HTML directly to
576px grayscale PNGs; no browser, wkhtmltoimage or PDF rasterizer is required.
The container includes explicit Noto Sans CJK TC Regular/Bold faces and DejaVu
Sans fallbacks, extracted in a build stage. Font license notices are retained.

For local development, install Noto CJK and DejaVu fonts plus `fonttools`, then run
`python scripts/prepare_fonts.py --destination ./fonts` and set
`RECEIPT_FONT_DIR=./fonts`. Use `--source` and `--fallback` for non-Debian font paths.
The renderer caches one engine and serializes rendering to bound concurrent
allocations. Canvas height grows from 1024px up to 16384px, then rendering fails
instead of silently printing only the first page. Blank bottom space is cropped.
Arbitrary emoji are not guaranteed; receipt stars use the provided fallback fonts.

Run tests, including real PNG rendering without contacting the printer:

```bash
docker build --target test .
```

The image-only API and ESC/POS transport retain their existing behavior.
Memory and speed improvements on a given host require workload measurements.

## Configuration

Copy `.env.example` to `.env` and adjust as needed.

Required/optional environment variables:
- `WEB_APP_HOST` (default `127.0.0.1`)
- `WEB_APP_PORT` (default `8000`)
- `RECEIPT_FONT_DIR` (default `/usr/local/share/receipt-fonts`)
- `RETAIN_TICKET_FILES` (default `false`)
- `PRINTER_HOST` (default `192.168.2.120`)
- `PRINTER_PORT` (default `9100`)
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

- Ticket rendering uses Fullbleed. Check renderer logs and `RECEIPT_FONT_DIR` if rendering fails.
- Configure your printer connection in `src/task_card_generator/printer.py` if you use USB/Serial instead of network.
- Image-only mode prints the attachment scaled to `PRINTER_IMAGE_WIDTH` to avoid cropping.
- The web UI polls `/health` to show printer reachability on the home page.

## Issue Tracking

Issues are tracked in-repo under `issues/` (filesystem-based).

- Start with `issues/README.md`
- Use `issues/templates/ISSUE_TEMPLATE.md`
- Optional helper: `scripts/new-issue.sh --title "..."`
- Keep `issues/index.md` updated when adding/changing issue status
- Move issue files across status folders: `open`, `in_progress`, `resolved`, `rejected`

## License

MIT License - see LICENSE file for details.
