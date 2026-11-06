"""Printer lifetime regression tests; all transports are in-memory fakes."""

from io import BytesIO

import pytest
from PIL import Image

from task_card_generator import printer


class Transport:
    def __init__(self, fail=None):
        self.fail = fail
        self.closed = False
        self.calls = []

    def image(self, image, impl, center):
        self.calls.append("image")
        assert image.size == (576, 24)
        assert impl == "bitImageColumn"
        if self.fail == "image":
            raise OSError("image send failed")

    def cut(self, feed):
        self.calls.append("cut")
        if self.fail == "cut":
            raise OSError("cut send failed")

    def close(self):
        self.calls.append("close")
        self.closed = True


@pytest.fixture
def png():
    output = BytesIO()
    Image.new("L", (576, 24), 255).save(output, format="PNG")
    return output.getvalue()


def test_success_closes_transport_before_return(monkeypatch, png):
    transport = Transport()
    monkeypatch.setattr(printer, "_get_printer", lambda: transport)
    printer.print_to_thermal_printer(png)
    assert transport.closed
    assert transport.calls == ["image", "cut", "close"]


@pytest.mark.parametrize("failure", ["image", "cut"])
def test_send_failure_still_closes_transport(monkeypatch, png, failure):
    transport = Transport(fail=failure)
    monkeypatch.setattr(printer, "_get_printer", lambda: transport)
    with pytest.raises(OSError):
        printer.print_to_thermal_printer(png)
    assert transport.closed
    assert transport.calls[-1] == "close"


def test_bad_image_still_closes_transport(monkeypatch):
    transport = Transport()
    monkeypatch.setattr(printer, "_get_printer", lambda: transport)
    with pytest.raises(OSError):
        printer.print_to_thermal_printer(b"not an image")
    assert transport.calls == ["close"]
