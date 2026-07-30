"""MessagingService._parse_field_intent — tạo task qua Zalo/Telegram (voice/mobile)."""
from app.services.messaging_service import MessagingService


def _svc():
    # _parse_field_intent không dùng db/writer → khởi tạo với db=None là đủ cho unit test.
    return MessagingService(db=None)


def test_create_task_with_pic_and_deadline():
    action = _svc()._parse_field_intent(
        "tạo task lắp PCCC tầng 3 giao Phan Minh Hoàng deadline 20/06/2026",
        user_name="Admin",
    )
    assert action["needs_confirm"] is True
    assert action["tool"] == "create_task"
    task = action["params"]["tasks"][0]
    assert "PCCC" in task["name"]
    assert task["pic"] == "Phan Minh Hoàng"
    assert task["end_date"] == "2026-06-20"


def test_create_task_minimal_defaults_pic_to_self():
    action = _svc()._parse_field_intent(
        "tạo task kiểm tra hệ thống điện",
        user_name="Bùi Thanh Bình",
    )
    assert action["tool"] == "create_task"
    task = action["params"]["tasks"][0]
    assert "kiểm tra hệ thống điện" in task["name"].lower()
    assert task["pic"] == "Bùi Thanh Bình"


def test_report_intent_still_works():
    action = _svc()._parse_field_intent(
        "báo cáo: hoàn thành kiểm tra tầng 3 mất 2 giờ",
        user_name="Admin",
    )
    assert action["tool"] == "append_field_report"


def test_update_intent_still_works():
    action = _svc()._parse_field_intent(
        "cập nhật CO-001 hoàn thành",
        user_name="Admin",
    )
    assert action["tool"] == "update_task"
