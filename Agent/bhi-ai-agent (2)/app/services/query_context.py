"""Phân tích ngữ cảnh câu hỏi → trích xuất đủ field query (GPT hay bỏ sót)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.text_utils import (
    detect_task_role,
    find_staff,
    find_staff_candidates,
    find_status,
    is_user_as_reviewer_query,
    normalize_text,
    parse_relative_date_range,
    wants_tasks_with_reviewer,
)

PROJECT_KEYWORDS = [
    ("chuyen doi so", "chuyển đổi số"),
    ("cao tang", "cao tầng"),
    ("ha tang", "hạ tầng"),
    ("pccc", "pccc"),
    ("masterplan", "masterplan"),
    ("ke hoach chuyen doi", "KẾ HOẠCH CHUYỂN ĐỔI SỐ"),
]

SEARCH_KEYWORDS = [
    "training", "pccc", "cao tầng", "hạ tầng", "masterplan", "setup", "core",
    "admin", "tool", "wbs",
]

ZONE_PATTERNS = [
    r"zone\s*(\d+)",
    r"khu vuc\s*(\d+)",
    r"zone\s*([a-z0-9]+)",
]


@dataclass
class QueryContext:
    message: str
    norm: str = ""
    user: str | None = None
    is_self_query: bool = False
    role: str | None = None
    has_reviewer: bool = False
    status: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    keyword: str | None = None
    zone: str | None = None
    project: str | None = None
    task_id: str | None = None
    parent_id: str | None = None
    is_overdue: bool = False
    wants_hours: bool = False
    wants_task_count: bool = False
    wants_completed_tasks: bool = False
    is_personal_log: bool = False
    is_archive: bool = False
    is_subtask: bool = False
    is_task_detail: bool = False
    extra: dict = field(default_factory=dict)


def _is_self_query(norm: str) -> bool:
    return any(m in norm for m in ("cua toi", "my task", "viec toi", "cua minh"))


def _is_hours_query(msg: str, norm: str) -> bool:
    keys = (
        "gio lam", "so gio", "tong gio", "bao nhieu gio", "lam bao nhieu gio",
        "thoi gian lam", "da lam bao nhieu gio",
    )
    return any(k in norm for k in keys) or any(
        k in msg for k in ("giờ làm", "số giờ", "tổng giờ", "bao nhiêu giờ")
    )


def _is_personal_log_query(msg: str, norm: str) -> bool:
    return any(
        k in msg for k in ("log cá nhân", "nhật ký cá nhân", "personal log")
    ) or any(k in norm for k in ("log ca nhan", "nhat ky ca nhan"))


def _is_archive_query(msg: str, norm: str) -> bool:
    if _is_personal_log_query(msg, norm):
        return False
    return any(
        k in msg for k in ("báo cáo", "archive", "lịch sử", "report")
    ) or any(k in norm for k in ("bao cao", "lich su", "log viec"))


def _is_task_count_query(norm: str) -> bool:
    return any(k in norm for k in (
        "bao nhieu task", "may task", "so task", "da lam bao nhieu task",
        "lam bao nhieu task", "bao nhieu cong viec", "hoan thanh bao nhieu task",
        "da hoan thanh bao nhieu", "xong bao nhieu task",
    ))


def _is_completed_task_query(norm: str) -> bool:
    return any(k in norm for k in (
        "hoan thanh bao nhieu", "da hoan thanh bao nhieu", "xong bao nhieu task",
        "task hoan thanh", "task da xong", "task da hoan thanh",
    ))


def _parse_absolute_date(msg: str) -> tuple[str | None, str | None]:
    iso = re.search(r"(\d{4}-\d{2}-\d{2})", msg)
    if iso:
        d = iso.group(1)
        return d, d
    dmy = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", msg)
    if dmy:
        d = f"{dmy.group(3)}-{dmy.group(2).zfill(2)}-{dmy.group(1).zfill(2)}"
        return d, d
    return None, None


def _find_project(msg: str, norm: str) -> str | None:
    for key, value in PROJECT_KEYWORDS:
        if key in norm or value.lower() in msg.lower():
            return value
    return None


def _find_search_keyword(msg: str, norm: str) -> str | None:
    for kw in SEARCH_KEYWORDS:
        if kw in msg.lower() or normalize_text(kw) in norm:
            return kw
    return None


def _find_zone(msg: str, norm: str) -> str | None:
    for pat in ZONE_PATTERNS:
        m = re.search(pat, norm, re.I)
        if m:
            return f"Zone {m.group(1)}"
    if "zone" in norm:
        return "zone"
    return None


def _find_task_id(msg: str) -> str | None:
    m = re.search(r"[A-Z]{2,}-\d{3}(?:\.\d+)?", msg.upper())
    return m.group() if m else None


def _find_parent_id(msg: str, norm: str) -> str | None:
    if not any(k in norm for k in ("subtask", "task con", "breakdown", "hang muc")):
        return None
    candidates = re.findall(r"\b([A-Z]{2,})\b", msg.upper())
    for c in candidates:
        if c not in ("SUBTASK", "TASK", "CON"):
            return c
    return candidates[-1] if candidates else None


def analyze_query(message: str, logged_in_user: str | None = None) -> QueryContext:
    """Trích xuất toàn bộ ngữ cảnh từ câu hỏi người dùng."""
    msg = message.strip()
    norm = normalize_text(msg)
    ctx = QueryContext(message=msg, norm=norm)

    # Dò tên cụ thể TRƯỚC: nếu câu nhắc đích danh một nhân sự thì ưu tiên người đó,
    # tránh "của Minh…" bị hiểu nhầm thành "của mình" (hỏi về bản thân).
    mentioned = find_staff(msg)
    ctx.is_self_query = _is_self_query(norm) and mentioned is None
    if mentioned:
        ctx.user = mentioned
    elif ctx.is_self_query and logged_in_user:
        ctx.user = logged_in_user

    ctx.wants_hours = _is_hours_query(msg, norm)
    ctx.wants_task_count = _is_task_count_query(norm)
    ctx.wants_completed_tasks = _is_completed_task_query(norm)
    ctx.is_personal_log = _is_personal_log_query(msg, norm)
    ctx.is_archive = _is_archive_query(msg, norm)
    ctx.is_overdue = any(
        k in norm for k in ("qua han", "tre han", "overdue")
    ) or any(k in msg for k in ("quá hạn", "trễ hạn"))

    ctx.task_id = _find_task_id(msg)
    ctx.parent_id = _find_parent_id(msg, norm)
    ctx.is_subtask = ctx.parent_id is not None
    ctx.is_task_detail = bool(
        ctx.task_id and any(k in norm for k in ("chi tiet", "detail", "thong tin"))
    )

    ctx.status = find_status(msg)
    if ctx.wants_completed_tasks and not ctx.status:
        ctx.status = "Hoàn thành"

    date_from, date_to = parse_relative_date_range(msg)
    if not date_from:
        date_from, date_to = _parse_absolute_date(msg)
    ctx.date_from = date_from
    ctx.date_to = date_to

    ctx.project = _find_project(msg, norm)
    ctx.keyword = _find_search_keyword(msg, norm)
    ctx.zone = _find_zone(msg, norm)

    if is_user_as_reviewer_query(msg):
        ctx.role = "reviewer"
        ctx.has_reviewer = False
    elif wants_tasks_with_reviewer(msg):
        ctx.has_reviewer = True
    elif ctx.user:
        ctx.role = detect_task_role(msg, has_user=True)
    elif any(k in norm for k in ("kiem tra", "reviewer")) and not ctx.has_reviewer:
        ctx.role = detect_task_role(msg, has_user=False)

    return ctx


def is_compound_work_query(ctx: QueryContext) -> bool:
    """Câu hỏi kết hợp nhiều chỉ số (vd: 'giờ và task quá hạn').

    Chỉ đếm task quá hạn (không hỏi giờ) → không phải compound.
    """
    if ctx.wants_hours and (
        ctx.wants_task_count or ctx.wants_completed_tasks or ctx.is_overdue
    ):
        return True
    return sum([ctx.wants_task_count, ctx.wants_completed_tasks]) >= 2


def needs_clarify(ctx: QueryContext, params: dict) -> dict | None:
    if ctx.user or find_staff(ctx.message):
        return None
    if ctx.has_reviewer or ctx.is_overdue or ctx.wants_hours or ctx.is_archive:
        return None
    if ctx.is_personal_log or ctx.task_id or ctx.parent_id:
        return None
    if params.get("status") or params.get("keyword") or params.get("project"):
        return None
    if wants_tasks_with_reviewer(ctx.message) or is_user_as_reviewer_query(ctx.message):
        return None
    candidates = find_staff_candidates(ctx.message)
    if len(candidates) <= 1:
        return None
    lines = [f"👤 Mình tìm thấy **{len(candidates)}** nhân sự khớp tên:"]
    for name in candidates[:6]:
        lines.append(f"  • {name}")
    lines.append('\nBạn gõ rõ hơn giúp mình nhé, vd: "Task của Phan Minh Hoàng"')
    return {"message": "\n".join(lines), "candidates": candidates}


def enrich_params(tool_name: str, params: dict | None, ctx: QueryContext) -> dict:
    """Gộp params từ GPT với ngữ cảnh phân tích — field code có ưu tiên khi GPT bỏ sót."""
    out = dict(params or {})

    if ctx.user and not out.get("user"):
        out["user"] = ctx.user

    if tool_name == "search_tasks":
        if ctx.role and not out.get("role"):
            out["role"] = ctx.role
        if is_user_as_reviewer_query(ctx.message):
            out["role"] = "reviewer"
            out.pop("has_reviewer", None)
        elif wants_tasks_with_reviewer(ctx.message):
            out["has_reviewer"] = True
        elif ctx.has_reviewer:
            out["has_reviewer"] = True
        if out.get("role") == "reviewer":
            out.pop("has_reviewer", None)

        if ctx.status and not out.get("status"):
            out["status"] = ctx.status
        if ctx.keyword and not out.get("keyword"):
            out["keyword"] = ctx.keyword
        if ctx.zone and not out.get("zone"):
            out["zone"] = ctx.zone
        if ctx.date_from and not out.get("date_from"):
            out["date_from"] = ctx.date_from
            out["date_to"] = ctx.date_to or ctx.date_from

    if tool_name in ("get_personal_log", "get_hours_summary", "search_archive"):
        if ctx.project and not out.get("project"):
            out["project"] = ctx.project
        if ctx.date_from and not out.get("date_from"):
            out["date_from"] = ctx.date_from
            out["date_to"] = ctx.date_to or ctx.date_from

    if tool_name == "get_task_detail" and ctx.task_id and not out.get("task_id"):
        out["task_id"] = ctx.task_id

    if tool_name == "get_subtasks" and ctx.parent_id and not out.get("parent_id"):
        out["parent_id"] = ctx.parent_id

    if tool_name == "search_overdue_tasks":
        if ctx.user and not out.get("user"):
            out["user"] = ctx.user
        if ctx.role and not out.get("role"):
            out["role"] = ctx.role
        out.setdefault("role", "pic")

    return out


def is_work_pool_query(ctx: QueryContext) -> bool:
    """Hỏi hiệu quả / performance / năng lực / bể công việc / lương 3P."""
    msg, norm = ctx.message, ctx.norm
    keys_vi = ("hiệu quả", "năng lực", "bể công việc", "lương 3p", "trình độ", "hiệu suất", "performance")
    keys_na = (
        "hieu qua", "nang luc", "be cong viec", "luong 3p", "trinh do",
        "hieu suat", "efficiency", "competency", "work pool",
        "performance", "performnace", "perf",
    )
    if any(k in msg.lower() for k in keys_vi) or any(k in norm for k in keys_na):
        return True
    # Viết tắt khớp nguyên từ (tránh dính trong từ khác): pf / 3p / kpi
    tokens = norm.replace("?", " ").split()
    if any(t in tokens for t in ("pf", "3p", "kpi")):
        return True
    # "đang ntn / thế nào" kèm tên nhân sự — ưu tiên work pool nếu không hỏi task cụ thể
    if ctx.user and any(k in norm for k in ("dang ntn", "the nao", "ntn", "ra sao", "the nao")):
        if not any(k in norm for k in ("task", "bao cao", "gio lam", "qua han")):
            return True
    return False
