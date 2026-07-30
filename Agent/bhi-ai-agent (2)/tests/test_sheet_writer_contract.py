"""SheetWriter phải gửi đúng contract Apps Script (action create/update/report).

Bug cũ: gửi {"action": "update_task"/"append_field_report", "params": ...} →
Apps Script chỉ hiểu create/update và không có handler ghi archive → fail trên sheet thật.
"""
import asyncio

import pytest

from app.config import settings
from app.services import sheet_writer


class _FakeResponse:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


class _FakeAsyncClient:
    """Giả lập Apps Script: chỉ chấp nhận đúng các action create/update/report."""

    captured = {}
    init_kwargs = {}

    def __init__(self, *args, **kwargs):
        _FakeAsyncClient.init_kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None):
        _FakeAsyncClient.captured = {"url": url, "json": json}
        action = (json or {}).get("action")
        if action == "update":
            return _FakeResponse({
                "success": True,
                "task_id": json.get("taskId"),
                "updated_fields": list((json.get("fields") or {}).keys()),
            })
        if action == "report":
            return _FakeResponse({"success": True, "appended": True})
        if action == "create":
            return _FakeResponse({"created": len(json.get("tasks") or [])})
        return _FakeResponse({"error": f"Unknown action: {action}"})


@pytest.fixture
def apps_script_mode(monkeypatch):
    monkeypatch.setattr(settings, "apps_script_url", "https://example.test/exec")
    monkeypatch.setattr(settings, "apps_script_secret", "s3cr3t")
    monkeypatch.setattr(sheet_writer.httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.captured = {}
    return _FakeAsyncClient


def test_update_task_maps_to_apps_script_update_contract(apps_script_mode):
    writer = sheet_writer.SheetWriter()
    result = asyncio.run(writer.execute(
        "update_task", {"task_id": "CO-001", "status": "Hoàn thành"},
    ))
    body = apps_script_mode.captured["json"]
    assert body["action"] == "update"
    assert body["taskId"] == "CO-001"
    assert body["fields"] == {"status": "Hoàn thành"}
    assert body["secret"] == "s3cr3t"
    assert not result.get("error")


def test_append_field_report_maps_to_report_action(apps_script_mode):
    writer = sheet_writer.SheetWriter()
    params = {
        "user": "Phan Minh Hoàng",
        "task_content": "Kiểm tra tầng 3",
        "report_date": "2026-06-17",
        "status": "Đang làm",
        "hours": 2.0,
        "project": "Cao tầng",
    }
    result = asyncio.run(writer.execute("append_field_report", params))
    body = apps_script_mode.captured["json"]
    assert body["action"] == "report"
    assert body["report"]["user"] == "Phan Minh Hoàng"
    assert body["report"]["task_content"] == "Kiểm tra tầng 3"
    assert not result.get("error")


def test_apps_script_call_follows_redirects(apps_script_mode):
    # Apps Script /exec luôn 302 → client BẮT BUỘC follow_redirects, nếu không sẽ 302 fail.
    writer = sheet_writer.SheetWriter()
    asyncio.run(writer.execute("update_task", {"task_id": "CO-001", "status": "Đang làm"}))
    assert apps_script_mode.init_kwargs.get("follow_redirects") is True


def test_create_task_maps_to_create_action(apps_script_mode):
    writer = sheet_writer.SheetWriter()
    params = {"tasks": [{"name": "Lắp PCCC tầng 3", "pic": "Phan Minh Hoàng", "duration": 2}]}
    result = asyncio.run(writer.execute("create_task", params))
    body = apps_script_mode.captured["json"]
    assert body["action"] == "create"
    assert body["tasks"][0]["name"] == "Lắp PCCC tầng 3"
    assert not result.get("error")
