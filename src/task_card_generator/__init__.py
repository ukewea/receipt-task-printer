"""Task Card Generator - web UI for printing tasks to a thermal printer."""

__version__ = "1.0.0"
__author__ = "Your Name"

from .html_generator import create_task_image
from .printer import print_to_thermal_printer

__all__ = [
    "create_task_image",
    "print_to_thermal_printer",
]
