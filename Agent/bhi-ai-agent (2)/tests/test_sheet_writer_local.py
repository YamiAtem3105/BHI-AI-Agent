"""SheetWriter chế độ mock (không có APPS_SCRIPT_URL) ghi vào ke_hoach.json local."""
import asyncio
import json

import pytest

from app.config import settings
from app.services import mock_sheets, sheet_writer


@pytest.fixture
def local_plan(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "apps_script_url", "")
    kh = tmp_path / "ke_hoach.json"
    plan = [{"id": "CO-001", "name": "Cũ", "status": "Chưa làm", "pic": "A"}]
    kh.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheet_writer, "KE_HOACH_PATH", str(kh))
    monkeypatch.setattr(mock_sheets, "_ke_hoach", plan)
    monkeypatch.setattr(mock_sheets, "_load", lambda: None)
    return kh


def test_create_task_local_appends_to_plan(local_plan):
    writer = sheet_writer.SheetWriter()
    result = asyncio.run(writer.execute(
        "create_task", {"tasks": [{"name": "Lắp PCCC tầng 3", "pic": "Phan Minh Hoàng"}]},
    ))
    assert result.get("success")
    data = json.loads(local_plan.read_text(encoding="utf-8"))
    assert any(t["name"] == "Lắp PCCC tầng 3" for t in data)


def test_update_task_local_changes_status(local_plan):
    writer = sheet_writer.SheetWriter()
    result = asyncio.run(writer.execute(
        "update_task", {"task_id": "CO-001", "status": "Hoàn thành"},
    ))
    assert result.get("success")
    data = json.loads(local_plan.read_text(encoding="utf-8"))
    co = next(t for t in data if t["id"] == "CO-001")
    assert co["status"] == "Hoàn thành"
