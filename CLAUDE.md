# Receipt Task Printer

Minimal FastAPI web UI for printing task tickets on a thermal receipt printer.

## Commands

- Install: `uv sync`
- Run locally: `uv run web-print` (serves at http://127.0.0.1:8000)
- Build container: `docker build -t receipt-printer-web .`
- Deploy: push to `main` branch, GitHub Actions builds and pushes to `ghcr.io/ukewea/receipt-task-printer`

## Architecture

- `src/task_card_generator/web_app.py` — FastAPI app, all endpoints (`/print`, `/health`, `/history`, `/reprint`)
- `src/task_card_generator/html_generator.py` — HTML ticket templates; `image_renderer.py` produces bounded Fullbleed PNGs
- `src/task_card_generator/printer.py` — ESC-POS thermal printer communication over TCP
- `Dockerfile` — Python 3.12 image with a separate font preparation stage
- `.github/workflows/container.yml` — multi-arch (amd64/arm64) container image build

## API

POST `/print` accepts both `multipart/form-data` and `application/json`:
- `name` (string, required unless image_only)
- `priority` (1=high, 2=medium, 3=low; default 2)
- `due_date` (ISO date string, required unless image_only)
- `operator_signature` (optional)
- `image_only` (bool, requires attachment)
- `attachment` (file upload, optional)

## Conventions

- Priority icons: `★` unicode stars (not emoji) for clean thermal output
- Fonts in container: extracted Noto Sans CJK TC Regular/Bold and DejaVu Sans; see README for local font setup
- Font-family order: Noto Sans CJK TC/SC, Noto Color Emoji, fallbacks
- Run `docker build --target test .` to check APIs and real PNG rendering without contacting the printer
- Config via environment variables (see `.env.example`)
- Printer default: network ESC-POS at 192.168.2.120:9100
