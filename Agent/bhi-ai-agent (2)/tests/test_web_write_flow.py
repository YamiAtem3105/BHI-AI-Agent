"""Web chat tạo/sửa task với xác nhận 'ok' — không gọi OpenAI (short-circuit trước routing)."""
import asyncio
import json

import pytest

from app.config import settings
from app.services import mock_sheets, sheet_writer, chat_session
from app.api import chat as chat_api


@pytest.fixture
def local_plan(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "apps_script_url", "")
    kh = tmp_path / "ke_hoach.json"
    plan = [{"id": "CO-001", "name": "Cũ", "status": "Chưa làm", "pic": "A"}]
    kh.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheet_writer, "KE_HOACH_PATH", str(kh))
    monkeypatch.setattr(mock_sheets, "_ke_hoach", plan)
    monkeypatch.setattr(mock_sheets, "_load", lambda: None)
    chat_session._sessions.clear()
    return kh


def _build(msg, email="tester@bicholder.vn", role="admin"):
    return asyncio.run(chat_api._build_chat_response(
        msg, user_name="Admin", is_privileged=True, user_role=role, user_email=email,
    ))


def test_web_create_task_asks_confirm_then_creates(local_plan):
    # B1: gửi lệnh tạo → hỏi xác nhận, CHƯA ghi
    text, display_tool, params, result, tool_name = _build(
        "tạo task lắp PCCC tầng 3 giao Phan Minh Hoàng deadline 20/06/2026",
    )
    assert tool_name == "confirm_write"
    assert "Tạo task" in text
    data = json.loads(local_plan.read_text(encoding="utf-8"))
    assert all("PCCC" not in t["name"] for t in data)  # chưa ghi

    # B2: gõ 'ok' → ghi thật
    text2, _, _, _, tool_name2 = _build("ok")
    assert tool_name2 == "write_done"
    data2 = json.loads(local_plan.read_text(encoding="utf-8"))
    assert any("PCCC" in t["name"] for t in data2)


def test_web_update_task_confirm_then_applies(local_plan):
    text, _, _, _, tool_name = _build("cập nhật CO-001 hoàn thành")
    assert tool_name == "confirm_write"
    text2, _, _, _, tool_name2 = _build("ok")
    assert tool_name2 == "write_done"
    data = json.loads(local_plan.read_text(encoding="utf-8"))
    assert next(t for t in data if t["id"] == "CO-001")["status"] == "Hoàn thành"


def test_web_change_sheet_while_pending(local_plan):
    text, _, _, _, tool_name = _build("tạo task ABC giao Phan Minh Hoàng")
    assert tool_name == "confirm_write" and "Sheet 1" in text
    # đổi sang sheet 2 trước khi xác nhận
    text2, _, params2, _, tool_name2 = _build("vào sheet 2")
    assert tool_name2 == "confirm_write"
    assert "Sheet 2" in text2
    assert params2["source"] == "2"


def test_web_cancel_discards_pending(local_plan):
    _build("cập nhật CO-001 hoàn thành")
    text, _, _, _, tool_name = _build("hủy")
    assert tool_name == "write_cancelled"
    data = json.loads(local_plan.read_text(encoding="utf-8"))
    assert next(t for t in data if t["id"] == "CO-001")["status"] == "Chưa làm"
