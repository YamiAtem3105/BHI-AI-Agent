"""Parser write dùng chung cho cả web chat và Zalo/Telegram."""
from app.services.write_intent import parse_create_task, parse_update_task, parse_write_intent


def test_parse_update_task():
    a = parse_update_task("cập nhật CO-001 hoàn thành")
    assert a["tool"] == "update_task"
    assert a["params"]["task_id"] == "CO-001"
    assert a["params"]["status"] == "Hoàn thành"


def test_parse_update_task_none_for_other_text():
    assert parse_update_task("task của tôi") is None


def test_parse_create_task_full():
    a = parse_create_task("tạo task lắp PCCC tầng 3 giao Phan Minh Hoàng deadline 20/06/2026", "Admin")
    assert a["tool"] == "create_task"
    t = a["params"]["tasks"][0]
    assert "PCCC" in t["name"]
    assert t["pic"] == "Phan Minh Hoàng"
    assert t["end_date"] == "2026-06-20"


def test_parse_create_task_defaults_pic_to_self():
    a = parse_create_task("tạo task kiểm tra hệ thống điện", "Bùi Thanh Bình")
    assert a["params"]["tasks"][0]["pic"] == "Bùi Thanh Bình"


def test_parse_create_task_none_for_report():
    assert parse_create_task("báo cáo: làm xong tầng 3", "Admin") is None


def test_parse_write_intent_prefers_update_then_create():
    assert parse_write_intent("cập nhật CO-001 đang làm", "Admin")["tool"] == "update_task"
    assert parse_write_intent("tạo task abc xyz", "Admin")["tool"] == "create_task"
    assert parse_write_intent("task của tôi", "Admin") is None
