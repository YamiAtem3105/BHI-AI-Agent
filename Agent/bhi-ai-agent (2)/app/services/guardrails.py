"""Guardrails: chỉ cho phép câu hỏi liên quan công việc QLXD."""
import re

from app.services.text_utils import mentions_staff, normalize_text

GREETING_PHRASES = {
    "hello", "hi", "hey", "xin chao", "chao", "cam on", "thanks",
    "help", "giup", "huong dan",
}

IN_SCOPE_KEYWORDS = [
    "task", "cong viec", "viec", "ke hoach", "bao cao", "archive", "log", "nhat ky",
    "gio lam", "so gio", "tong gio", "chi tiet", "detail", "subtask", "wbs",
    "qua han", "tre han", "overdue", "hoan thanh", "dang lam", "chua lam",
    "pic", "phoi hop", "kiem tra", "reviewer", "masterplan", "pccc",
    "cao tang", "ha tang", "co-", "hh-", "zone", "deadline", "tien do",
    "cua toi", "my task", "tim", "xem", "liet ke", "danh sach",
    "performance", "performnace", "perf", "hieu qua", "hieu suat", "nang luc",
    "efficiency", "competency", "3p", "be cong viec", "luong 3p", "tien do cong viec",
]

_NORM_KEYWORDS = [normalize_text(kw) for kw in IN_SCOPE_KEYWORDS]

OFF_TOPIC_RESPONSE = (
    "⚠️ Mình chỉ hỗ trợ tra cứu **công việc, task, báo cáo, giờ làm, hiệu quả/năng lực** trong hệ thống QLXD.\n\n"
    "Ví dụ:\n"
    "• \"Task của tôi\"\n"
    "• \"Hiệu quả công việc của Phan Minh Hoàng\"\n"
    "• \"Performance của Hoàng Long\"\n"
    "• \"Task quá hạn\"\n"
    "• \"Giờ làm của tôi\""
)

HELP_RESPONSE = (
    "Xin chào! 👋 Tôi có thể giúp bạn:\n"
    "• **Task**: \"Task đang làm\", \"Task của [tên]\"\n"
    "• **Hiệu quả / Performance**: \"Hiệu quả công việc của Phan Minh Hoàng\"\n"
    "• **Chi tiết**: \"Chi tiết CO-001\"\n"
    "• **Báo cáo**: \"Báo cáo của [tên]\"\n"
    "• **Subtask**: \"Subtask của CO\"\n"
    "• **Giờ làm**: \"Giờ làm của tôi\"\n"
    "• **Log cá nhân**: \"Log cá nhân của tôi\""
)


def is_greeting(message: str) -> bool:
    norm = normalize_text(message)
    if norm in GREETING_PHRASES:
        return True
    return norm.startswith("xin chao") or norm.startswith("chao ban")


def is_help_request(message: str) -> bool:
    norm = normalize_text(message)
    return any(k in norm for k in (
        "giup gi", "giup duoc gi", "giup dc gi", "lam duoc gi", "lam dc gi",
        "ho tro gi", "ho tro duoc gi", "huong dan", "help",
    ))


def is_in_scope(message: str) -> bool:
    if is_greeting(message) or is_help_request(message):
        return True
    if re.search(r"[A-Z]{2,}-\d{3}", message.upper()):
        return True
    if re.search(r"\b[A-Z]{2,}\b", message):
        return True

    norm = normalize_text(message)
    if any(kw in norm for kw in _NORM_KEYWORDS):
        return True
    # mentions_staff dùng find_staff_candidates đã siết (khớp token đúng),
    # không còn lọt câu ngoài phạm vi qua chuỗi con ("phở" ~ "Phong").
    if mentions_staff(message):
        return True
    return False
