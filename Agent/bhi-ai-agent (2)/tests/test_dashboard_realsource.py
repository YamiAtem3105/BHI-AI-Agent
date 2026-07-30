"""Dashboard Tổng quan đọc task/báo cáo từ sheet thật khi có APPS_SCRIPT_URL."""
import asyncio

from app.api import dashboard
from app.config import settings


class _FakeSvc:
    async def search_tasks(self, **k):
        return {"tasks": [{"id": "X-1", "name": "n", "status": "Đang làm",
                           "pic": "A", "end_date": "2030-01-01"}], "count": 1}

    async def search_archive(self, **k):
        return {"reports": [{"user": "A", "hours": 3, "project": "P"}], "count": 1}


def test_load_data_uses_sheet_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "apps_script_url", "https://x/exec")
    monkeypatch.setattr(dashboard, "get_sheets_service", lambda: _FakeSvc())
    tasks, reports, staff = asyncio.run(dashboard._load_data())
    assert tasks[0]["id"] == "X-1"
    assert reports[0]["user"] == "A"


def test_load_data_uses_local_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "apps_script_url", "")
    tasks, reports, staff = asyncio.run(dashboard._load_data())
    # data demo local có nhiều task
    assert isinstance(tasks, list) and len(tasks) > 5
