"""Chuẩn hóa text tiếng Việt (có/không dấu) và khớp tên nhân sự."""
import json
import os
import re
import unicodedata
from datetime import date, timedelta

# Cụm chỉ thời gian — gỡ khỏi câu TRƯỚC khi dò tên để tránh đụng độ
# (vd: "tuần này" bỏ dấu thành "tuan nay" sẽ khớp nhầm họ tên "Tuấn").
_TIME_PHRASES = [
    "tuần này", "tuần trước", "tuần sau", "tháng này", "tháng trước", "tháng sau",
    "năm nay", "năm ngoái", "hôm nay", "hôm qua", "hôm kia", "ngày mai",
    "this week", "last week", "next week", "this month", "last month", "today", "yesterday",
]

# Họ/tên đơn mà khi bỏ dấu trùng với TỪ CHỨC NĂNG tần suất cao (đại từ, từ thời gian).
# Với các tên này, CHỈ chấp nhận khớp họ đơn khi token CÓ DẤU trùng khớp.
# Chỉ giữ những từ thực sự dễ gây nhầm — các họ khác vẫn cho khớp không dấu
# (người dùng hay gõ không dấu: "task Kien", "cua Long"…).
_COLLISION_SURNAMES = {
    "tuan",  # Tuấn ↔ "tuần" (tuần này/tuần trước) — cực kỳ hay gặp
    "anh",   # Anh  ↔ "anh"  (đại từ: anh ơi, của anh)
}

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
_STAFF_CACHE: list[str] | None = None


def _load_staff_names() -> list[str]:
    global _STAFF_CACHE
    if _STAFF_CACHE is not None:
        return _STAFF_CACHE
    path = os.path.join(_DATA_DIR, "staff.json")
    try:
        with open(path, encoding="utf-8") as f:
            _STAFF_CACHE = [s["name"] for s in json.load(f) if s.get("name")]
    except (OSError, json.JSONDecodeError, KeyError):
        _STAFF_CACHE = [
            "Bùi Thanh Bình", "Nguyễn Văn Cường", "Ngô Thị Dung", "Phan Minh Hoàng",
            "Trần Huy Hoàng", "Đỗ Thị Bích Hằng", "Nguyễn Anh Tuấn Khanh", "Vũ Đức Kiên",
            "Lê Chí Hoàng Long", "Nguyễn Văn Mạnh", "Nguyễn Hải Phong", "Nguyễn Trọng Phúc",
            "Nguyễn Thị Quyên", "Nguyễn Phan Toàn", "Lê Trung Anh", "Nguyễn Trọng Trung",
            "Nguyễn Thị Tuyết", "Hoàng Anh Tuấn",
        ]
    return _STAFF_CACHE


@property
def STAFF():
    return _load_staff_names()


# Module-level list — đồng bộ từ staff.json khi import
STAFF = _load_staff_names()


def normalize_text(text: str) -> str:
    """Lowercase, bỏ dấu, đ/Đ → d — dùng chung cho guardrails và routing."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d").replace("ð", "d")


def _strip_time_phrases(msg: str) -> str:
    """Gỡ các cụm chỉ thời gian để chúng không bị khớp nhầm thành tên người."""
    out = msg
    for phrase in _TIME_PHRASES:
        out = re.sub(re.escape(phrase), " ", out, flags=re.IGNORECASE)
    return out


def find_staff(msg: str) -> str | None:
    """Tìm tên nhân sự — khớp có dấu, không dấu, họ/tên lót.

    Thứ tự ưu tiên (cụ thể → mơ hồ): tên đầy đủ → cụm 2 từ → họ/tên đơn.
    Cụm 2 từ chạy TRƯỚC họ đơn để 'minh hoàng' khớp Phan Minh Hoàng,
    không bị 'tuấn' (trong 'tuần') giành mất.
    """
    msg = _strip_time_phrases(msg)
    msg_lower = msg.lower()
    msg_na = normalize_text(msg)

    # 1) Tên đầy đủ (có dấu)
    for name in STAFF:
        if name.lower() in msg_lower:
            return name

    # 2) Tên đầy đủ (không dấu)
    for name in STAFF:
        if normalize_text(name) in msg_na:
            return name

    # 3) Cụm 2 từ liên tiếp (vd "minh hoàng") — cụ thể hơn họ đơn nên ưu tiên.
    #    Yêu cầu TÊN (token cuối) phải xuất hiện trong câu, tránh khớp nhầm
    #    họ+đệm phổ biến (vd "Nguyễn Văn ..." khớp nhầm "Nguyễn Văn Cường").
    msg_lower_tokens = set(msg_lower.split())
    msg_na_tokens_set = set(msg_na.split())
    for name in STAFF:
        parts = name.split()
        parts_na = [normalize_text(p) for p in parts]
        last_present = parts[-1].lower() in msg_lower_tokens or parts_na[-1] in msg_na_tokens_set
        if not last_present:
            continue
        for i in range(len(parts) - 1):
            combo = parts[i].lower() + " " + parts[i + 1].lower()
            combo_na = parts_na[i] + " " + parts_na[i + 1]
            if combo in msg_lower or combo_na in msg_na:
                return name

    # 4) Họ/tên đơn duy nhất — chống đụng độ từ thông dụng (tuần/Tuấn, mình/Minh…)
    msg_tokens = set(msg_lower.split())
    msg_na_tokens = set(msg_na.split())
    for name in STAFF:
        last = name.split()[-1].lower()
        last_na = normalize_text(name.split()[-1])
        is_unique = sum(1 for n in STAFF if n.split()[-1].lower() == last) == 1
        if not is_unique:
            continue
        if last in msg_tokens:  # khớp CÓ DẤU luôn an toàn
            return name
        # Khớp không dấu: chặn nếu là họ dễ đụng độ (chỉ chấp nhận khi có dấu)
        if last_na in msg_na_tokens and last_na not in _COLLISION_SURNAMES:
            return name

    return None


def find_staff_candidates(msg: str) -> list[str]:
    """Gợi ý nhân sự khi chỉ gõ một phần tên (vd: Hoang → PMH, THH...)."""
    msg_na = normalize_text(msg)
    words = [w for w in msg_na.split() if len(w) >= 3]
    if not words:
        return []

    found: list[str] = []
    for name in STAFF:
        name_na = normalize_text(name)
        if name_na in msg_na:
            found.append(name)
            continue
        parts = [p for p in name_na.split() if len(p) >= 3]
        # Khớp ĐÚNG token tên (không khớp chuỗi con: tránh "pho" ⊂ "phong"
        # khiến câu ngoài phạm vi lọt guardrail).
        if any(word in parts for word in words):
            found.append(name)
    return found


def mentions_staff(msg: str) -> bool:
    """True nếu message có thể liên quan đến nhân sự (đủ để không chặn guardrails)."""
    if find_staff(msg):
        return True
    return len(find_staff_candidates(msg)) > 0


def is_user_as_reviewer_query(msg: str) -> bool:
    """True nếu hỏi X là người kiểm tra (vai trò reviewer), không phải 'task có KT'."""
    norm = normalize_text(msg)
    if not any(k in norm for k in (
        "la nguoi kiem tra", "lam nguoi kiem tra", "vai tro kiem tra",
        "la reviewer", "lam reviewer",
    )):
        return False
    return find_staff(msg) is not None


def wants_tasks_with_reviewer(msg: str) -> bool:
    """True nếu hỏi các task ĐÃ CÓ người kiểm tra (khác với vai trò reviewer)."""
    if is_user_as_reviewer_query(msg):
        return False
    norm = normalize_text(msg)
    return any(k in norm for k in (
        "co nguoi kiem tra", "co reviewer", "da co nguoi kiem tra",
        "task co kiem tra", "nhung task co nguoi kiem tra",
        "danh sach task co nguoi kiem tra",
    ))


def detect_task_role(msg: str, *, has_user: bool = False) -> str | None:
    """Suy ra vai trò lọc: pic | support | reviewer | None (mọi vai trò)."""
    low = msg.lower()
    norm = normalize_text(msg)
    if is_user_as_reviewer_query(msg):
        return "reviewer"
    if not has_user:
        return None
    if any(k in low for k in ("tất cả", "tat ca", "toàn bộ", "toan bo", "mọi vai trò", "moi vai tro")):
        return None
    if any(k in low for k in ("phối hợp", "phoi hop", "hỗ trợ", "ho tro")):
        return "support"
    if any(k in low or k in norm for k in (
        "kiem tra cua", "kiểm tra của", "task kiem tra", "task kiểm tra",
        "reviewer cua", "reviewer của", "review cua", "review của",
    )):
        return "reviewer"
    if not wants_tasks_with_reviewer(msg) and any(
        k in low or k in norm for k in ("kiểm tra", "kiem tra", "review", "reviewer")
    ):
        return "reviewer"
    return "pic"


STATUS_MAP = {
    "hoan thanh": "Hoàn thành", "xong": "Hoàn thành", "done": "Hoàn thành",
    "dang lam": "Đang làm", "doing": "Đang làm", "in progress": "Đang làm",
    "chua lam": "Chưa làm", "todo": "Chưa làm", "not started": "Chưa làm",
    "hoàn thành": "Hoàn thành", "đang làm": "Đang làm", "chưa làm": "Chưa làm",
    "đang tiến hành": "Đang làm",
}


def find_status(msg: str) -> str | None:
    msg_na = normalize_text(msg)
    for key, value in STATUS_MAP.items():
        if key in msg.lower() or normalize_text(key) in msg_na:
            return value
    return None


def parse_relative_date_range(msg: str) -> tuple[str | None, str | None]:
    """Parse 'tuần này', 'tháng này'... → (date_from, date_to) ISO."""
    norm = normalize_text(msg)
    today = date.today()

    if any(k in norm for k in ("tuan nay", "this week")):
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat()
    if any(k in norm for k in ("tuan truoc", "last week")):
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        return start.isoformat(), end.isoformat()
    if any(k in norm for k in ("thang nay", "this month")):
        return today.replace(day=1).isoformat(), today.isoformat()
    if any(k in norm for k in ("hom nay", "today")):
        d = today.isoformat()
        return d, d
    return None, None
