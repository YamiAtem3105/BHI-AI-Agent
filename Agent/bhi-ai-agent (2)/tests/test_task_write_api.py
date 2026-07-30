"""API tạo/cập nhật task cho dashboard (form = xác nhận, gọi trực tiếp SheetWriter)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import mock_sheets, sheet_writer
from app.services.auth_token import create_session_token


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "apps_script_url", "")
    kh = tmp_path / "ke_hoach.json"
    plan = [{"id": "CO-001", "name": "Cũ", "status": "Chưa làm", "pic": "A"}]
    kh.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheet_writer, "KE_HOACH_PATH", str(kh))
    monkeypatch.setattr(mock_sheets, "_ke_hoach", plan)
    monkeypatch.setattr(mock_sheets, "_load", lambda: None)
    return TestClient(app), kh


def _auth(role="manager"):
    token = create_session_token("mgr@bicholder.vn", role, "Mgr")
    return {"Authorization": f"Bearer {token}"}


def test_create_task_endpoint_writes(client):
    c, kh = client
    r = c.post("/api/tasks/create",
               json={"name": "Lắp PCCC tầng 3", "pic": "Phan Minh Hoàng", "end_date": "2026-06-20"},
               headers=_auth())
    assert r.status_code == 200, r.text
    assert r.json().get("success")
    data = json.loads(kh.read_text(encoding="utf-8"))
    assert any(t["name"] == "Lắp PCCC tầng 3" for t in data)


def test_create_task_requires_name(client):
    c, _ = client
    r = c.post("/api/tasks/create", json={"name": "  "}, headers=_auth())
    assert r.status_code == 400


def test_update_task_endpoint_changes_status(client):
    c, kh = client
    r = c.post("/api/tasks/update",
               json={"task_id": "CO-001", "status": "Hoàn thành"}, headers=_auth())
    assert r.status_code == 200, r.text
    data = json.loads(kh.read_text(encoding="utf-8"))
    assert next(t for t in data if t["id"] == "CO-001")["status"] == "Hoàn thành"


def test_write_requires_auth(client):
    c, _ = client
    r = c.post("/api/tasks/create", json={"name": "X"})
    assert r.status_code == 401
