from fastapi.testclient import TestClient

from task_card_generator import web_app


def test_index_returns_html():
    client = TestClient(web_app.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Print a Task" in resp.text


def test_print_missing_fields_returns_400():
    client = TestClient(web_app.app)
    resp = client.post("/print", json={"name": "", "due_date": ""})
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False


def test_print_success_with_json(monkeypatch):
    def fake_create_task_image(task_obj, retain_file=True):
        return None, b"fakeimagebytes"

    printed = {"called": False}

    def fake_print_to_thermal_printer(image_bytes=None):
        assert image_bytes == b"fakeimagebytes"
        printed["called"] = True

    monkeypatch.setattr(web_app, "create_task_image", fake_create_task_image)
    monkeypatch.setattr(web_app, "print_to_thermal_printer", fake_print_to_thermal_printer)

    client = TestClient(web_app.app)
    resp = client.post(
        "/print",
        json={
            "name": "Test task",
            "priority": 2,
            "due_date": "2026-02-08",
            "operator_signature": "QA",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["task"]["name"] == "Test task"
    assert printed["called"] is True
