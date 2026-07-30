"""work_pool không được crash khi _ke_hoach chưa nạp (reads đã chuyển sang sheet thật)."""
from app.services import mock_sheets, work_pool_service


def test_work_pool_loads_plan_itself(monkeypatch):
    # Giả lập tiến trình mới: chưa ai gọi _load() → _ke_hoach/_staff = None
    monkeypatch.setattr(mock_sheets, "_ke_hoach", None)
    monkeypatch.setattr(mock_sheets, "_staff", None)
    r = work_pool_service.get_employee_work_pool("Phan Minh Hoàng")
    # Không TypeError; trả profile hoặc lỗi 'có kiểm soát', không phải crash
    assert isinstance(r, dict)
    assert r.get("employee") or r.get("error")
