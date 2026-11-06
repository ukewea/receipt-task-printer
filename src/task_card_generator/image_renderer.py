"""Render bounded, variable-height receipt PNGs without a browser process."""

import logging
import os
import tempfile
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Optional, Tuple

import fullbleed
from PIL import Image, ImageChops

logger = logging.getLogger(__name__)
RECEIPT_WIDTH = 576
INITIAL_HEIGHT = 1024
MAX_HEIGHT = 16384
_render_lock = Lock()


@lru_cache(maxsize=1)
def _engine() -> fullbleed.PdfEngine:
    font_dir = Path(os.getenv("RECEIPT_FONT_DIR", "/usr/local/share/receipt-fonts"))
    fonts = sorted(str(p) for p in font_dir.glob("*") if p.suffix.lower() in {".ttf", ".otf"})
    if not fonts:
        raise RuntimeError(f"No receipt fonts in {font_dir}; run scripts/prepare_fonts.py")
    return fullbleed.PdfEngine(font_files=fonts)


def _render_png(html_content: str) -> bytes:
    height = INITIAL_HEIGHT
    # Serialize the shared engine and bound simultaneous raster allocations.
    with _render_lock:
        while height <= MAX_HEIGHT:
            css = f"@page {{ size: {RECEIPT_WIDTH}px {height}px; margin: 0; }}"
            pages = _engine().render_image_pages(html_content, css, dpi=96)
            if len(pages) == 1:
                with Image.open(BytesIO(pages[0])) as page:
                    image = page.convert("L")
                if image.size != (RECEIPT_WIDTH, height):
                    raise RuntimeError("Unexpected Fullbleed raster dimensions")
                bounds = ImageChops.difference(image, Image.new("L", image.size, 255)).getbbox()
                if bounds is None:
                    raise ValueError("Receipt rendered without visible content")
                if bounds[3] < height - 8:
                    output = BytesIO()
                    image.crop((0, 0, RECEIPT_WIDTH, bounds[3] + 1)).save(output, format="PNG")
                    return output.getvalue()
            height *= 2
    raise ValueError(f"Receipt exceeds the supported height of {MAX_HEIGHT}px")


def html_to_image(html_content: str, retain_file: bool = True) -> Tuple[Optional[str], Optional[bytes]]:
    """Return a 576px grayscale PNG, or the existing failure tuple for the API."""
    try:
        image_bytes = _render_png(html_content)
        if retain_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as output:
                output.write(image_bytes)
                return output.name, image_bytes
        return None, image_bytes
    except Exception:
        logger.exception("Fullbleed receipt rendering failed")
        return None, None
