"""Cấu hình test chung.

.env thật có thể đã cấu hình APPS_SCRIPT_URL → mặc định ép test dùng mock,
tránh test vô tình gọi mạng tới Apps Script. Test ghi vẫn tự monkeypatch lại
giá trị riêng trong fixture của chúng (override per-test).
"""
import pytest

from app.config import settings

# Ép ngay ở thời điểm import (trước khi các test-module import app.api.chat),
# để `sheets` proxy phân giải ra MockSheetsService trong test.
settings.apps_script_url = ""


@pytest.fixture(autouse=True)
def _force_mock_sheets(monkeypatch):
    monkeypatch.setattr(settings, "apps_script_url", "", raising=False)
