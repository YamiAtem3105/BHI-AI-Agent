"""Dashboard API - stats tổng hợp cho quản lý.

Auth: JWT Bearer. Phân quyền qua rbac.py (super_admin/admin/manager/member).
"""
import json
import os
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.services.auth_token import get_current_user
from app.services.rbac import has_permission, normalize_role, require_permission
from app.services.sheet_writer import SheetWriter
from app.services.sheets_factory import get_sheets_service
from app.services.work_pool_service import ai_organize_data, list_work_pools

router = APIRouter()
_writer = SheetWriter()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

_staff_cache: list | None = None


def _num(v) -> float:
    """Ép giá trị giờ (có thể là số hoặc chuỗi từ sheet) về float, lỗi → 0."""
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _get_staff() -> list:
    global _staff_cache
    if _staff_cache is None:
        with open(os.path.join(DATA_DIR, "staff.json"), encoding="utf-8") as f:
            _staff_cache = json.load(f)
    return _staff_cache


def _require_dashboard_view(user: dict = Depends(get_current_user)) -> dict:
    role = normalize_role(user.get("role"))
    if not has_permission(role, "dashboard.view"):
        raise HTTPException(
            status_code=403,
            detail=f"Vai trò '{role}' không có quyền xem dashboard.",
        )
    user["role"] = role
    return user


async def _load_data():
    """Task + báo cáo: từ Google Sheet thật khi có APPS_SCRIPT_URL, ngược lại file local."""
    if settings.apps_script_url:
        svc = get_sheets_service()
        tasks_res = await svc.search_tasks()
        reports_res = await svc.search_archive()
        return tasks_res.get("tasks", []), reports_res.get("reports", []), _get_staff()
    with open(os.path.join(DATA_DIR, "ke_hoach.json"), encoding="utf-8") as f:
        tasks = json.load(f)
    with open(os.path.join(DATA_DIR, "archive_log.json"), encoding="utf-8") as f:
        reports = json.load(f)
    return tasks, reports, _get_staff()


@router.get("/api/dashboard")
async def dashboard_stats(user: dict = Depends(_require_dashboard_view)):
    tasks, reports, staff = await _load_data()

    # Task stats by status
    status_count = Counter(t["status"].strip() for t in tasks if t["status"])

    # Tasks by person (PIC)
    by_person = defaultdict(lambda: {"total": 0, "done": 0, "doing": 0, "todo": 0})
    for t in tasks:
        for pic in [p.strip() for p in t["pic"].split(",") if p.strip()]:
            by_person[pic]["total"] += 1
            if t["status"].strip() == "Hoàn thành":
                by_person[pic]["done"] += 1
            elif t["status"].strip() == "Đang làm":
                by_person[pic]["doing"] += 1
            else:
                by_person[pic]["todo"] += 1

    # Completion rate per person
    staff_stats = []
    for s in staff:
        if s.get("role") in ("admin", "super_admin"):
            continue
        name = s["name"]
        p = by_person.get(name, {"total": 0, "done": 0, "doing": 0, "todo": 0})
        report_count = sum(1 for r in reports if r["user"] == name)
        hours = sum(_num(r.get("hours")) for r in reports if r["user"] == name)
        rate = round(p["done"] / p["total"] * 100) if p["total"] > 0 else 0
        staff_stats.append({
            "name": name, "email": s["email"],
            "tasks_total": p["total"], "tasks_done": p["done"],
            "tasks_doing": p["doing"], "tasks_todo": p["todo"],
            "completion_rate": rate,
            "reports": report_count, "hours": round(hours, 1),
        })

    staff_stats.sort(key=lambda x: x["tasks_total"], reverse=True)

    # Overdue tasks (status != Hoàn thành and end_date < today)
    from datetime import date
    today = date.today().isoformat()
    overdue = [t for t in tasks
               if t["status"].strip() != "Hoàn thành"
               and t.get("end_date")
               and t["end_date"] < today]

    return {
        "summary": {
            "total_tasks": len(tasks),
            "done": status_count.get("Hoàn thành", 0),
            "doing": status_count.get("Đang làm", 0),
            "todo": status_count.get("Chưa làm", 0),
            "overdue": len(overdue),
            "total_staff": len([s for s in staff if s.get("role") not in ("admin", "super_admin")]),
            "total_reports": len(reports),
        },
        "staff": staff_stats,
        "overdue_tasks": [
            {"id": t["id"], "name": t["name"], "end_date": t["end_date"],
             "pic": t["pic"], "status": t["status"]}
            for t in overdue[:20]
        ],
    }


@router.get("/api/dashboard/work-pool")
async def dashboard_work_pool(
    employee: str | None = Query(None, description="Lọc 1 nhân viên"),
    user: dict = Depends(get_current_user),
):
    """Tab Bể công việc — 3P, năng lực, so sánh job lớn, bậc việc, ưu tiên."""
    role = normalize_role(user.get("role"))
    if employee:
        if not has_permission(role, "dashboard.work_pool.all") and not has_permission(role, "dashboard.work_pool.self"):
            raise HTTPException(status_code=403, detail="Không có quyền xem bể công việc.")
    elif not has_permission(role, "dashboard.work_pool.all"):
        if has_permission(role, "dashboard.work_pool.self"):
            employee = user.get("name")
        else:
            raise HTTPException(status_code=403, detail="Không có quyền xem bể công việc.")

    result = list_work_pools(role, user.get("name", ""), target=employee)
    if result.get("error"):
        raise HTTPException(status_code=403, detail=result["error"])
    return result


class TaskCreateBody(BaseModel):
    name: str
    pic: str | None = ""
    support: str | None = ""
    reviewer: str | None = ""
    duration: int | None = None
    predecessor: str | None = ""
    start_date: str | None = None
    end_date: str | None = None
    zone: str | None = ""
    note: str | None = ""
    source: str | None = None  # '1' sheet chính | '2' sheet masterplan


class TaskUpdateBody(BaseModel):
    task_id: str
    status: str | None = None
    note: str | None = None
    pic: str | None = None
    support: str | None = None
    reviewer: str | None = None
    duration: int | None = None
    predecessor: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    zone: str | None = None
    source: str | None = None


@router.post("/api/tasks/create")
async def create_task(
    body: TaskCreateBody,
    user: dict = Depends(require_permission("data.write.task")),
):
    """Tạo task mới từ dashboard (form là xác nhận, ghi thẳng qua SheetWriter)."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Thiếu tên task.")
    payload = body.model_dump()
    source = payload.pop("source", None)
    spec = {k: v for k, v in payload.items() if v not in (None, "")}
    spec["name"] = name
    result = await _writer.execute("create_task", {"tasks": [spec], "source": source})
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/api/tasks/update")
async def update_task(
    body: TaskUpdateBody,
    user: dict = Depends(require_permission("data.write.task")),
):
    """Cập nhật task từ dashboard. Chỉ gửi các trường cần đổi."""
    task_id = (body.task_id or "").strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="Thiếu task_id.")
    payload = body.model_dump()
    source = payload.pop("source", None)
    fields = {k: v for k, v in payload.items() if k != "task_id" and v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Không có trường nào để cập nhật.")
    result = await _writer.execute("update_task", {"task_id": task_id, "source": source, **fields})
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/api/dashboard/ai-organize")
async def dashboard_ai_organize(
    scope: str = Query("work_pool"),
    user: dict = Depends(require_permission("dashboard.ai_organize")),
):
    """AI gợi ý sắp xếp, tổ chức dữ liệu hợp lý (logic chi tiết sẽ bổ sung sau)."""
    return ai_organize_data(scope=scope)
