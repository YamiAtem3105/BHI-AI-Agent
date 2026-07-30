"""SheetsService (Apps Script) dẫn xuất overdue/hours/personal_log từ search/archive."""
import asyncio

import pytest

from app.config import settings
from app.services.sheets_service import SheetsService


class _Resp:
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


class _FakeClient:
    def __init__(self, tasks=None, reports=None):
        self.tasks = tasks or []
        self.reports = reports or []

    async def get(self, url, params=None):
        action = (params or {}).get("action")
        if action == "search":
            return _Resp({"tasks": self.tasks, "count": len(self.tasks)})
        if action == "archive":
            return _Resp({"reports": self.reports, "count": len(self.reports)})
        return _Resp({"error": "unexpected"})


def _svc(monkeypatch, tasks=None, reports=None):
    monkeypatch.setattr(settings, "apps_script_url", "https://x/exec")
    monkeypatch.setattr(settings, "apps_script_secret", "s")
    s = SheetsService()
    s.client = _FakeClient(tasks, reports)
    return s


def test_overdue_filters_incomplete_past_due(monkeypatch):
    tasks = [
        {"id": "A", "status": "Đang làm", "end_date": "2020-01-01", "pic": "X"},
        {"id": "B", "status": "Hoàn thành", "end_date": "2020-01-01", "pic": "X"},
        {"id": "C", "status": "Chưa làm", "end_date": "2999-01-01", "pic": "X"},
    ]
    s = _svc(monkeypatch, tasks=tasks)
    r = asyncio.run(s.search_overdue_tasks(user="X", role="pic"))
    assert r["count"] == 1
    assert r["tasks"][0]["id"] == "A"
    assert r["filter"] == "overdue"


def test_hours_summary_aggregates_archive(monkeypatch):
    reports = [
        {"project": "P1", "hours": 2}, {"project": "P1", "hours": 3}, {"project": "P2", "hours": 1},
    ]
    s = _svc(monkeypatch, reports=reports)
    r = asyncio.run(s.get_hours_summary("X"))
    assert r["total_hours"] == 6
    assert r["report_count"] == 3
    assert r["by_project"]["P1"] == 5
    assert r["by_project"]["P2"] == 1


def test_personal_log_returns_archive_reports(monkeypatch):
    reports = [{"project": "P1", "task_content": "abc", "hours": 2}]
    s = _svc(monkeypatch, reports=reports)
    r = asyncio.run(s.get_personal_log("X"))
    assert r["count"] == 1
    assert r["reports"][0]["task_content"] == "abc"
    assert r["user"] == "X"
