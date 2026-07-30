"""Chọn nguồn ĐỌC dữ liệu: Apps Script (sheet thật) khi có APPS_SCRIPT_URL, ngược lại mock JSON.

Phân giải tại thời điểm gọi (lazy) để test monkeypatch settings.apps_script_url được.
"""
from app.config import settings

_mock = None
_real = None


def get_sheets_service():
    global _mock, _real
    if settings.apps_script_url:
        if _real is None:
            from app.services.sheets_service import SheetsService
            _real = SheetsService()
        return _real
    if _mock is None:
        from app.services.mock_sheets import MockSheetsService
        _mock = MockSheetsService()
    return _mock


class SheetsProxy:
    """Đại diện cho `sheets`: mỗi lần truy cập method sẽ phân giải service hiện hành."""

    def __getattr__(self, name):
        return getattr(get_sheets_service(), name)


sheets = SheetsProxy()
