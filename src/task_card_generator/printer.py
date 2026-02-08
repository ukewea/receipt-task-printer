"""Thermal printer functionality."""

import io
import os
import socket
from typing import Optional, Union

from PIL import Image
from escpos.printer import Usb, Serial, Network, File

PrinterTransport = Union[Usb, Serial, Network, File]


def _get_printer() -> PrinterTransport:
    """Configure printer transport."""
    # Option 1: USB Connection (most common)
    # printer = Usb(0x0483, 0x5720)  # CHANGE THESE VALUES!

    # Option 2: Serial Connection
    # printer = Serial('/dev/ttyUSB0')

    # Option 3: Network/WiFi Printer (default)
    printer = Network(
        os.getenv("PRINTER_HOST", "192.168.2.120"),
        int(os.getenv("PRINTER_PORT", "9100")),
    )

    # Option 4: File Device (direct device access)
    # printer = File("/dev/usb/lp0")
    return printer


def print_to_thermal_printer(image_bytes: Optional[bytes] = None) -> None:
    """Print image to thermal printer.

    Supports multiple connection methods across Windows and Linux.
    Edit the connection method below based on your printer setup.
    Cut mode and feed are configurable via env:
      PRINTER_CUT_FEED=<int lines> (default 0)
    """
    if not image_bytes:
        raise ValueError("No image provided to print.")

    printer = _get_printer()

    try:
        cut_feed = os.getenv("PRINTER_CUT_FEED", "true").lower() not in {"false", "0", "no"}
    except ValueError:
        cut_feed = False

    img_source = Image.open(io.BytesIO(image_bytes))

    # Print the image (bitImageColumn works well for most printers)
    printer.image(img_source, impl="bitImageColumn", center=True)

    # Cut the paper
    printer.cut(feed=cut_feed)

    print("Successfully printed to thermal printer!")


def check_printer_reachable(timeout: float = 1.5) -> dict:
    """Best-effort network reachability check for the default printer."""
    host = os.getenv("PRINTER_HOST", "192.168.2.120")
    try:
        port = int(os.getenv("PRINTER_PORT", "9100"))
    except ValueError:
        port = 9100

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "host": host, "port": port}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)}
