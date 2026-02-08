# Repository Guidelines

## Project Structure & Module Organization
- Core package lives under `src/task_card_generator/`.
- Web UI is `src/task_card_generator/web_app.py`.
- Ticket rendering: `src/task_card_generator/html_generator.py`.
- Printer wiring: `src/task_card_generator/printer.py`.
- Config via `.env` (copy from `.env.example`).

## Build, Test, and Development Commands
- Install deps: `uv sync` (preferred) or `pip install -r requirements.txt`.
- Run web UI: `uv run web-print` (then open `http://127.0.0.1:8000`).

## Coding Style & Naming Conventions
- Python 3.9+, 4-space indentation, type hints for public functions, concise docstrings.
- Naming: snake_case for functions/variables, PascalCase for classes.

## Testing Guidelines
- No automated suite yet—add `tests/` with `test_*.py` via `pytest`.
- Printer-dependent tests should be marked (e.g., `@pytest.mark.printer`).

## Commit & Pull Request Guidelines
- Conventional Commit style (`feat:`, `fix:`, `build:`), subject under ~72 chars.
- PRs: summarize change, list tests, include screenshots if UI output changes.
- Keep secrets out of commits; `.env` stays local.
