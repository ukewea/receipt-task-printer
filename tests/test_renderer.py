"""Exercise the real renderer without contacting a printer."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from task_card_generator import html_generator as html
from task_card_generator import image_renderer as renderer


@pytest.mark.parametrize("content", [
    html.create_task_html(SimpleNamespace(name="練習英文十五分鐘，完成每日運動", priority=2,
        due_date="2026-11-07", operator_signature="TEST", attachment_bytes=None)),
    html.create_quote_html("Small steps every day.", zh_tw="臺灣繁體字：臺、灣、龍、龜、鬱"),
    html.create_todolist_html("明日待辦", ["練習英文（Speak English）", "整理帳單與備份資料" * 5]),
])
def test_receipts_are_visible_fixed_width_pngs(content):
    path, data = renderer.html_to_image(content, retain_file=False)
    assert path is None
    with Image.open(BytesIO(data)) as image:
        assert image.width == 576
        assert 50 < image.height < 1024
        assert image.mode == "L"
        assert image.getextrema() == (0, 255)


def test_long_checklist_grows_instead_of_truncating():
    _, data = html.create_todolist_image("長清單", [f"第 {i} 項：核對收據" for i in range(50)], retain_file=False)
    with Image.open(BytesIO(data)) as image:
        assert 2000 < image.height < renderer.MAX_HEIGHT
        assert image.width == 576


def test_overheight_receipt_fails_instead_of_printing_first_page(monkeypatch):
    monkeypatch.setattr(renderer, "MAX_HEIGHT", 1024)
    _, data = html.create_todolist_image("長清單", ["整理帳單" for _ in range(50)], retain_file=False)
    assert data is None


def test_checklist_item_separators_are_painted():
    _, data = html.create_todolist_image("", ["第一項", "第二項", "第三項"], retain_file=False)
    with Image.open(BytesIO(data)) as image:
        # Rows have no other gray paint spanning the receipt. Two dotted
        # separators must each paint a visible row with wide gray coverage.
        gray_rows = [y for y in range(130)
                     if sum(130 <= image.getpixel((x, y)) <= 180 for x in range(4, 560)) > 150]
        assert len(gray_rows) >= 2


def test_retained_file_matches_returned_png(tmp_path, monkeypatch):
    monkeypatch.setattr(renderer.tempfile, "tempdir", str(tmp_path))
    path, data = renderer.html_to_image("<p>Receipt</p>", retain_file=True)
    from pathlib import Path
    assert Path(path).read_bytes() == data


def test_base64_attachment_is_rendered():
    attachment = BytesIO()
    Image.new("RGB", (240, 120), (128, 128, 128)).save(attachment, format="PNG")
    _, data = html.create_task_image(SimpleNamespace(name="圖片附件", priority=2,
        due_date="2026-11-07", operator_signature="TEST", attachment_bytes=attachment.getvalue()), retain_file=False)
    with Image.open(BytesIO(data)) as image:
        assert image.width == 576
        assert image.height > 300
        assert image.histogram()[128] > 1000


@pytest.mark.parametrize("endpoint,payload", [
    ("/print", {"name": "中文測試", "priority": 2, "due_date": "2026-11-07"}),
    ("/print-todolist", {"title": "待辦", "items": ["整理收據", "核對帳單"]}),
    ("/print-quote", {"quote": "Small steps every day.", "zh_tw": "每天前進一小步。"}),
])
def test_api_sends_real_png_and_returns_matching_preview(monkeypatch, endpoint, payload):
    import base64
    from fastapi.testclient import TestClient
    from task_card_generator import web_app
    printed = []
    monkeypatch.setattr(web_app, "print_to_thermal_printer", lambda image_bytes: printed.append(image_bytes))
    response = TestClient(web_app.app).post(endpoint, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert base64.b64decode(body["preview"].split(",", 1)[1]) == printed[0]
    with Image.open(BytesIO(printed[0])) as image:
        assert image.width == 576
