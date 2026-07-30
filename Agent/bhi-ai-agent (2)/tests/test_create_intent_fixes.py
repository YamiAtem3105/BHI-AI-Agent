"""Fix UX luồng tạo task: ý định lịch sự, tên rác, đổi sheet đích."""
from app.services.write_intent import parse_create_task, parse_write_intent


# 1) "tôi muốn tạo task ..." vẫn nhận là tạo task
def test_polite_lead_is_create():
    a = parse_create_task("tôi muốn tạo task lắp PCCC tầng 3 giao Phan Minh Hoàng", "Admin")
    assert a is not None and a["tool"] == "create_task"
    assert "PCCC" in a["params"]["tasks"][0]["name"]


def test_muon_tao_task_via_write_intent():
    a = parse_write_intent("mình muốn tạo task kiểm tra điện", "Admin")
    assert a["tool"] == "create_task"
    assert "kiểm tra điện" in a["params"]["tasks"][0]["name"].lower()


# 2) Không tạo task tên rác khi chỉ có tiểu từ ("cơ mà", "đi"...)
def test_no_garbage_name_asks_instead():
    a = parse_create_task("tạo task mới cơ mà", "Admin")
    assert a is not None
    assert a.get("tool") is None  # hỏi lại tên, KHÔNG tạo
    assert "tên" in a["preview"].lower()


def test_strips_trailing_particle():
    a = parse_create_task("tạo task họp tổng kết đi nhé", "Admin")
    # bỏ tiểu từ 'đi nhé' ở cuối tên
    assert a["tool"] == "create_task"
    assert a["params"]["tasks"][0]["name"] == "họp tổng kết"


# 3) Không nhầm khi là báo cáo
def test_report_context_not_create():
    assert parse_create_task("báo cáo: hôm nay có tạo task phụ", "Admin") is None
