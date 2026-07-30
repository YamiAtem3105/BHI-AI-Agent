"""Chọn sheet ghi (source) — chat detect + payload Apps Script."""
import asyncio

import pytest

from app.config import settings
from app.services import sheet_writer
from app.services.write_intent import parse_create_task


def test_chat_detects_sheet2():
    a = parse_create_task("tạo task abc vào sheet 2 giao Phan Minh Hoàng", "Admin")
    assert a["params"]["source"] == "2"


def test_chat_defaults_sheet1():
    a = parse_create_task("tạo task abc giao Phan Minh Hoàng", "Admin")
    assert a["params"]["source"] == "1"


class _FakeResp:
    def __init__(self, d): self._d = d
    def raise_for_status(self): return None
    def json(self): return self._d


class _FakeClient:
    captured = {}
    def __init__(self, *a, **k): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def post(self, url, json=None):
        _FakeClient.captured = json
        return _FakeResp({"created": 1})


@pytest.fixture
def apps(monkeypatch):
    monkeypatch.setattr(settings, "apps_script_url", "https://x/exec")
    monkeypatch.setattr(settings, "apps_script_secret", "s")
    monkeypatch.setattr(sheet_writer.httpx, "AsyncClient", _FakeClient)
    return _FakeClient


def test_create_payload_carries_source(apps):
    w = sheet_writer.SheetWriter()
    asyncio.run(w.execute("create_task", {"tasks": [{"name": "X"}], "source": "2"}))
    assert apps.captured["action"] == "create"
    assert apps.captured["source"] == "2"


def test_update_payload_excludes_source_from_fields(apps):
    w = sheet_writer.SheetWriter()
    asyncio.run(w.execute("update_task", {"task_id": "CO-001", "status": "Đang làm", "source": "2"}))
    assert apps.captured["taskId"] == "CO-001"
    assert apps.captured["fields"] == {"status": "Đang làm"}  # source KHÔNG lọt vào fields
    assert apps.captured["source"] == "2"
