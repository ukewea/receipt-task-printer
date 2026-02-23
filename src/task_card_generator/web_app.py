#!/usr/bin/env python3
"""Minimal web UI to submit a task and print to the receipt printer."""

import base64
import os
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

from .html_generator import create_task_image, create_todolist_image, create_quote_image
from . import print_to_thermal_printer
from .printer import check_printer_reachable

load_dotenv()
RETAIN_TICKET_FILES = os.getenv("RETAIN_TICKET_FILES", "false").lower() not in {"false", "0", "no"}
WEB_APP_HOST = os.getenv("WEB_APP_HOST", "127.0.0.1")
WEB_APP_PORT = int(os.getenv("WEB_APP_PORT", "8000"))
PRINTER_IMAGE_WIDTH = int(os.getenv("PRINTER_IMAGE_WIDTH", "576"))
HISTORY_LIMIT = 10
_history = deque(maxlen=HISTORY_LIMIT)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC_DIR / "task.html", media_type="text/html")


@app.get("/todolist", response_class=HTMLResponse)
def todolist_page():
    return FileResponse(STATIC_DIR / "todolist.html", media_type="text/html")


@app.get("/quote", response_class=HTMLResponse)
def quote_page():
    return FileResponse(STATIC_DIR / "quote.html", media_type="text/html")


def normalize_image_for_printer(image_bytes: bytes, target_width: int) -> bytes:
    """Scale and pad image bytes to the printer width to avoid cropping."""
    with Image.open(BytesIO(image_bytes)) as im:
        im = im.convert("L")
        width, height = im.size
        if width <= 0 or height <= 0:
            raise ValueError("Invalid image dimensions.")
        if width != target_width:
            scale = target_width / float(width)
            new_height = max(1, int(height * scale))
            im = im.resize((target_width, new_height), Image.LANCZOS)
        if im.size[0] != target_width:
            canvas = Image.new("L", (target_width, im.size[1]), 255)
            canvas.paste(im, (0, 0))
            im = canvas
        buf = BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()


def _to_grayscale_preview(image_bytes):
    """Convert image bytes to grayscale and return (image_bytes, preview_data_uri)."""
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
    return image_bytes, preview_data


def _next_history_id():
    return (_history[0]["id"] + 1) if _history else 1


@app.post("/print")
async def handle_print(
    request: Request,
    name: Optional[str] = Form(default=None),
    priority: Optional[str] = Form(default=None),
    due_date: Optional[str] = Form(default=None),
    operator_signature: Optional[str] = Form(default=None),
    image_only: Optional[str] = Form(default=None),
    attachment: Optional[UploadFile] = File(default=None),
):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        name = (payload.get("name") or "").strip()
        priority_raw = str(payload.get("priority") or "2").strip()
        due_date = (payload.get("due_date") or "").strip()
        operator_signature = (payload.get("operator_signature") or "").strip()
        image_only_flag = bool(payload.get("image_only"))
        attachment_bytes = None
    else:
        name = (name or "").strip()
        priority_raw = (priority or "2").strip()
        due_date = (due_date or "").strip()
        operator_signature = (operator_signature or "").strip()
        image_only_flag = bool(image_only)
        attachment_bytes = None
        if attachment:
            try:
                attachment_bytes = await attachment.read()
            except Exception:
                attachment_bytes = None

    if image_only_flag and not attachment_bytes:
        return JSONResponse(
            {"success": False, "error": "Image-only mode requires an attachment."},
            status_code=400,
        )

    if not image_only_flag and (not name or not due_date):
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

    if image_only_flag:
        image_bytes = attachment_bytes
        if image_bytes:
            try:
                image_bytes = normalize_image_for_printer(image_bytes, PRINTER_IMAGE_WIDTH)
            except Exception:
                pass
    else:
        task_obj = SimpleNamespace(
            name=name,
            priority=priority,
            due_date=due_date,
            operator_signature=operator_signature,
            attachment_bytes=attachment_bytes,
        )

        _, image_bytes = create_task_image(task_obj, retain_file=RETAIN_TICKET_FILES)
        if image_bytes is None:
            return JSONResponse(
                {
                    "success": False,
                    "error": "Failed to render ticket image. Ensure wkhtmltoimage or Selenium+Chrome are installed.",
                },
                status_code=500,
            )

    image_bytes, preview_data = _to_grayscale_preview(image_bytes)

    try:
        print_to_thermal_printer(image_bytes=image_bytes)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": f"Failed to print: {str(e)}"},
            status_code=500,
        )

    try:
        _history.appendleft({
            "id": _next_history_id(),
            "type": "task",
            "name": name or "Image-only print",
            "priority": priority,
            "due_date": due_date,
            "preview": preview_data,
            "image_bytes": image_bytes,
            "operator_signature": operator_signature,
            "image_only": image_only_flag,
        })
    except Exception:
        pass

    return JSONResponse({
        "success": True,
        "image_only": image_only_flag,
        "task": {
            "name": name,
            "priority": priority,
            "due_date": due_date,
            "operator_signature": operator_signature,
        },
        "preview": preview_data,
    })


@app.post("/print-quote")
async def handle_print_quote(request: Request):
    payload = await request.json()
    quote = (payload.get("quote") or "").strip()
    author = (payload.get("author") or "").strip()
    tagline = (payload.get("tagline") or "").strip()
    date_str = (payload.get("date") or "").strip()

    if not quote:
        return JSONResponse({"success": False, "error": "Quote is required."}, status_code=400)

    _, image_bytes = create_quote_image(
        quote=quote,
        zh_tw=(payload.get("zh_tw") or payload.get("zh") or "").strip(),
        author=author,
        tagline=tagline,
        date_str=date_str,
        retain_file=RETAIN_TICKET_FILES,
    )
    if image_bytes is None:
        return JSONResponse(
            {
                "success": False,
                "error": "Failed to render quote image. Ensure wkhtmltoimage or Selenium+Chrome are installed.",
            },
            status_code=500,
        )

    image_bytes, preview_data = _to_grayscale_preview(image_bytes)

    try:
        print_to_thermal_printer(image_bytes=image_bytes)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Failed to print: {str(e)}"}, status_code=500)

    try:
        _history.appendleft({
            "id": _next_history_id(),
            "type": "quote",
            "name": (author and f"Quote — {author}") or "Quote",
            "quote": quote,
            "author": author,
            "tagline": tagline,
            "preview": preview_data,
            "image_bytes": image_bytes,
        })
    except Exception:
        pass

    return JSONResponse({
        "success": True,
        "preview": preview_data,
        "quote": {"quote": quote, "author": author, "tagline": tagline, "date": date_str},
    })


@app.post("/print-todolist")
async def handle_print_todolist(request: Request):
    payload = await request.json()
    title = (payload.get("title") or "").strip()
    items = [s.strip() for s in (payload.get("items") or []) if s and s.strip()]

    if not items:
        return JSONResponse(
            {"success": False, "error": "At least one item is required."},
            status_code=400,
        )

    _, image_bytes = create_todolist_image(title, items, retain_file=RETAIN_TICKET_FILES)
    if image_bytes is None:
        return JSONResponse(
            {
                "success": False,
                "error": "Failed to render todolist image. Ensure wkhtmltoimage or Selenium+Chrome are installed.",
            },
            status_code=500,
        )

    image_bytes, preview_data = _to_grayscale_preview(image_bytes)

    try:
        print_to_thermal_printer(image_bytes=image_bytes)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": f"Failed to print: {str(e)}"},
            status_code=500,
        )

    try:
        _history.appendleft({
            "id": _next_history_id(),
            "type": "todolist",
            "name": title or "Todolist",
            "items": items,
            "item_count": len(items),
            "preview": preview_data,
            "image_bytes": image_bytes,
        })
    except Exception:
        pass

    return JSONResponse({
        "success": True,
        "item_count": len(items),
        "preview": preview_data,
    })


@app.get("/history")
async def history(_: Request):
    """Return recent prints (excluding raw bytes)."""
    items = []
    for entry in _history:
        item = {
            "id": entry["id"],
            "type": entry.get("type", "task"),
            "name": entry.get("name", ""),
            "preview": entry.get("preview"),
        }
        if item["type"] == "todolist":
            item["item_count"] = entry.get("item_count", 0)
            item["items"] = entry.get("items", [])
        elif item["type"] == "quote":
            item["author"] = entry.get("author", "")
            item["quote"] = entry.get("quote", "")
            item["tagline"] = entry.get("tagline", "")
        else:
            item["priority"] = entry.get("priority", 2)
            item["due_date"] = entry.get("due_date", "")
            item["image_only"] = entry.get("image_only", False)
        items.append(item)
    return JSONResponse({"items": items})


@app.get("/health")
def health():
    return JSONResponse(check_printer_reachable())


def _quotes_path() -> Path:
    return Path(__file__).parent / "quotes.json"


def _load_quotes_list() -> list[dict]:
    quotes_path = _quotes_path()
    if quotes_path.exists():
        try:
            data = json.loads(quotes_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            return []
    return []


def _daily_quote_dir() -> Path:
    # Default to a repo-local data directory. Can override with env.
    base = os.getenv("DAILY_QUOTES_DIR")
    if base:
        return Path(base)
    return Path.cwd() / "data" / "daily-quotes"


def _today_key(tz: str) -> str:
    try:
        zone = ZoneInfo(tz)
    except Exception:
        zone = ZoneInfo("Asia/Taipei")
    return datetime.now(zone).strftime("%Y-%m-%d")


def _daily_quote_path(day: str) -> Path:
    d = _daily_quote_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{day}.json"


@app.get("/quotes/random")
def random_quote():
    """Return a random upbeat quote for the Quote UI.

    Reads from src/task_card_generator/quotes.json if present.
    """
    quotes = _load_quotes_list()

    if not quotes:
        quotes = [
            {"quote": "Make today ridiculously effective.", "author": ""},
            {"quote": "Start small. Start now.", "author": ""},
            {"quote": "Do one thing that makes everything else easier.", "author": ""},
            {"quote": "Momentum beats motivation.", "author": ""},
            {"quote": "Tiny steps count.", "author": ""},
        ]

    pick = random.choice(quotes)
    quote = (pick.get("quote") or "").strip()
    author = (pick.get("author") or "").strip()
    tagline = (pick.get("tagline") or "").strip()
    return JSONResponse({"quote": quote, "author": author, "tagline": tagline})


@app.get("/quotes/daily")
def get_daily_quote(tz: str = "Asia/Taipei"):
    """Return today's cached daily quote if it exists.

    NOTE: This endpoint does not generate quotes. Generation is done by the caller,
    then stored via /print-quote-daily.
    """
    day = _today_key(tz)
    p = _daily_quote_path(day)
    if not p.exists():
        return JSONResponse({"ok": False, "day": day, "tz": tz, "error": "not_set"}, status_code=404)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return JSONResponse({"ok": False, "day": day, "tz": tz, "error": f"read_failed: {exc}"}, status_code=500)

    # Normalize output
    en = (data.get("en") or data.get("quote") or "").strip()
    zh_tw = (data.get("zh_tw") or data.get("zh") or "").strip()
    author = (data.get("author") or "").strip()
    tagline = (data.get("tagline") or "").strip()
    return JSONResponse({"ok": True, "day": day, "tz": tz, "en": en, "zh_tw": zh_tw, "author": author, "tagline": tagline})


@app.post("/print-quote-daily")
async def print_quote_daily(request: Request):
    """Print today's quote with a server-side daily cache.

    Behavior:
    - First call of the day stores the provided quote payload to disk and prints it.
    - Subsequent calls ignore the incoming payload and re-print the cached quote.

    Caller must generate the English quote and (optionally) zh-TW translation.
    """
    payload = await request.json()

    tz = (payload.get("tz") or "Asia/Taipei").strip() or "Asia/Taipei"
    day = _today_key(tz)
    p = _daily_quote_path(day)

    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return JSONResponse({"success": False, "error": f"Failed to read daily cache: {exc}"}, status_code=500)
        source = "cache"
    else:
        en = (payload.get("en") or payload.get("quote") or "").strip()
        if not en:
            return JSONResponse({"success": False, "error": "Missing required field: en"}, status_code=400)

        data = {
            "day": day,
            "tz": tz,
            "en": en,
            "zh_tw": (payload.get("zh_tw") or payload.get("zh") or "").strip(),
            "author": (payload.get("author") or "").strip(),
            "tagline": (payload.get("tagline") or "").strip(),
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }
        try:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            return JSONResponse({"success": False, "error": f"Failed to write daily cache: {exc}"}, status_code=500)
        source = "new"

    # Print using existing quote layout (English always; Chinese currently not rendered in the template).
    # We still store zh_tw for future bilingual template support.
    _, image_bytes = create_quote_image(
        quote=data.get("en") or "",
        zh_tw=data.get("zh_tw") or "",
        author=data.get("author") or "",
        tagline=data.get("tagline") or "",
        date_str=day,
        retain_file=RETAIN_TICKET_FILES,
    )
    if image_bytes is None:
        return JSONResponse({"success": False, "error": "Failed to render quote image."}, status_code=500)

    image_bytes, preview_data = _to_grayscale_preview(image_bytes)

    try:
        print_to_thermal_printer(image_bytes=image_bytes)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Failed to print: {str(e)}"}, status_code=500)

    return JSONResponse({
        "success": True,
        "source": source,
        "day": day,
        "tz": tz,
        "en": (data.get("en") or "").strip(),
        "zh_tw": (data.get("zh_tw") or "").strip(),
        "preview": preview_data,
    })


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
