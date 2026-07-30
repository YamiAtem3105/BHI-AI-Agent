"""Ngữ cảnh hội thoại ngắn — xử lý follow-up kiểu 'performance cơ', 'của X thì sao'."""
from __future__ import annotations

import time

from app.services.text_utils import find_staff, normalize_text

_TTL_SEC = 600
_sessions: dict[str, dict] = {}

_PERF_KEYS = (
    "performance", "performnace", "perf", "hieu qua", "hieu suat", "nang luc",
    "hieu nang", "efficiency", "competency", "3p", "be cong viec", "luong 3p",
)
_FOLLOW_KEYS = ("thi sao", "the sao", "vay sao", "con gi", "co gi", "vay con", "the con")


def _now() -> float:
    return time.time()


def get_session(email: str) -> dict | None:
    if not email:
        return None
    sess = _sessions.get(email)
    if not sess or _now() - sess.get("ts", 0) > _TTL_SEC:
        return None
    return sess


def set_pending_write(email: str, action: dict) -> None:
    """Lưu thao tác ghi đang chờ xác nhận 'ok/hủy' (theo email, in-memory)."""
    if not email:
        return
    sess = _sessions.setdefault(email, {})
    sess["ts"] = _now()
    sess["pending_write"] = action


def get_pending_write(email: str) -> dict | None:
    sess = get_session(email)
    return sess.get("pending_write") if sess else None


def clear_pending_write(email: str) -> None:
    sess = _sessions.get(email)
    if sess:
        sess.pop("pending_write", None)


def remember_turn(email: str, tool_name: str, params: dict | None = None) -> None:
    if not email:
        return
    intent = None
    if tool_name == "work_pool_profile":
        intent = "work_pool"
    elif tool_name in ("work_summary", "hours_summary", "personal_log"):
        intent = tool_name
    elif tool_name in ("search_tasks", "search_archive", "get_task_detail", "get_subtasks"):
        intent = "tasks"

    user = (params or {}).get("user")
    sess = _sessions.setdefault(email, {})
    sess["ts"] = _now()
    if user:
        sess["last_user"] = user
    if intent:
        sess["last_intent"] = intent
    sess["last_tool"] = tool_name


def _mentions_performance(norm: str, raw: str) -> bool:
    if any(k in norm for k in _PERF_KEYS):
        return True
    # Viết tắt khớp nguyên từ: pf / kpi (P/Pf/Ps là các cột lương 3P)
    if any(t in norm.replace("?", " ").split() for t in ("pf", "kpi")):
        return True
    vi = ("hiệu quả", "năng lực", "hiệu suất", "bể công việc", "lương 3p")
    return any(k in raw.lower() for k in vi)


def expand_followup(message: str, email: str, logged_in_user: str | None = None) -> str:
    """Mở rộng câu hỏi lượt kế để router hiểu đúng ý performance / so sánh nhân sự."""
    raw = (message or "").strip()
    if not raw:
        return raw

    norm = normalize_text(raw)
    sess = get_session(email)
    staff = find_staff(raw)

    if _mentions_performance(norm, raw):
        target = staff or (sess or {}).get("last_user") or logged_in_user
        if target:
            return f"hiệu quả công việc của {target}"

    if staff and any(k in norm for k in _FOLLOW_KEYS):
        if sess and sess.get("last_intent") == "work_pool":
            return f"hiệu quả công việc của {staff}"
        return f"task của {staff}"

    if sess and len(norm.split()) <= 5:
        frag = norm in ("co", "cơ", "ma", "thoi", "performance", "performnace", "hieu qua")
        if frag or (sess.get("last_intent") == "work_pool" and any(k in norm for k in ("co", "cơ", "thoi"))):
            target = staff or sess.get("last_user") or logged_in_user
            if target:
                return f"hiệu quả công việc của {target}"

    return raw
