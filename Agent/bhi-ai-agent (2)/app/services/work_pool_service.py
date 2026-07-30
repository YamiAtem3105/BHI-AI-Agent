"""Bể công việc nhân viên — so sánh việc đang làm với job lớn, 3P, năng lực."""
import json
import os
import re
from collections import defaultdict
from datetime import date

from app.config import settings
from app.services.openai_compat import completion_limit_kwargs
from app.services import mock_sheets
from app.services.mock_sheets import _name_match, get_staff_by_name
from app.services.rbac import can_view_staff_data, normalize_role

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

_profiles_cache: dict | None = None

PRIORITY_ORDER = {"Khẩn cấp": 4, "Cao": 3, "Trung bình": 2, "Thấp": 1}


def _load_profiles() -> dict:
    global _profiles_cache
    if _profiles_cache is None:
        path = os.path.join(DATA_DIR, "staff_profiles.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rows = json.load(f)
            _profiles_cache = {r["name"]: r for r in rows}
        else:
            _profiles_cache = {}
    return _profiles_cache


def _task_job_level(task_id: str) -> int:
    """CO=1, CO-001=2, CO-001.3=3, ..."""
    if not task_id:
        return 0
    parts = re.split(r"[-.]", task_id)
    return len([p for p in parts if p])


def _parent_job_id(task_id: str) -> str:
    """CO-001.3 → CO, CO-001 → CO."""
    if not task_id:
        return ""
    if "-" in task_id:
        return task_id.split("-")[0]
    if "." in task_id:
        return task_id.split(".")[0]
    return task_id


def _infer_priority(task: dict) -> str:
    status = (task.get("status") or "").strip()
    if status == "Hoàn thành":
        return "Thấp"
    end = task.get("end_date")
    if not end:
        return "Trung bình"
    today = date.today().isoformat()
    if end < today:
        return "Khẩn cấp"
    days_left = (date.fromisoformat(end) - date.today()).days
    if days_left <= 3:
        return "Cao"
    if days_left <= 7:
        return "Trung bình"
    return "Thấp"


def _default_profile(name: str) -> dict:
    return {
        "name": name,
        "salary_3p": {"position": 6.0, "person": 6.0, "performance": 6.0},
        "skill_level": 2,
        "competency_score": 60,
        "efficiency_score": 60,
        "job_grade": "Junior",
        "default_priority": "Trung bình",
    }


def _tasks_for_user(name: str) -> list[dict]:
    mock_sheets._load()
    results = []
    for t in mock_sheets._ke_hoach:
        if not t.get("id") or "-" not in t["id"]:
            continue
        if _name_match(t["pic"], name):
            role = "pic"
        elif _name_match(t["support"], name):
            role = "support"
        elif _name_match(t["reviewer"], name):
            role = "reviewer"
        else:
            continue
        parent = _parent_job_id(t["id"])
        parent_task = next((x for x in mock_sheets._ke_hoach if x["id"] == parent), None)
        priority = _infer_priority(t)
        results.append({
            "id": t["id"],
            "name": t["name"],
            "role": role,
            "status": (t.get("status") or "").strip() or "Chưa làm",
            "start_date": t.get("start_date"),
            "end_date": t.get("end_date"),
            "job_level": _task_job_level(t["id"]),
            "priority": priority,
            "parent_job_id": parent,
            "parent_job_name": parent_task["name"] if parent_task else parent,
        })
    results.sort(key=lambda x: (-PRIORITY_ORDER.get(x["priority"], 0), x.get("end_date") or "9999"))
    return results


def _pool_stats(tasks: list[dict]) -> dict:
    by_status = defaultdict(int)
    by_parent = defaultdict(int)
    by_priority = defaultdict(int)
    for t in tasks:
        by_status[t["status"]] += 1
        by_parent[t["parent_job_id"]] += 1
        by_priority[t["priority"]] += 1
    active = [t for t in tasks if t["status"] != "Hoàn thành"]
    done = by_status.get("Hoàn thành", 0)
    total = len(tasks)
    return {
        "total": total,
        "active": len(active),
        "done": done,
        "completion_rate": round(done / total * 100) if total else 0,
        "by_status": dict(by_status),
        "by_parent_job": dict(by_parent),
        "by_priority": dict(by_priority),
    }


def _compare_with_parent_job(tasks: list[dict], parent_job_id: str) -> dict:
    """So sánh việc đang làm của nhân viên với toàn bộ bể job lớn."""
    mock_sheets._load()
    parent_tasks = [t for t in mock_sheets._ke_hoach if t["id"].startswith(parent_job_id + "-") or t["id"] == parent_job_id]
    parent_children = [t for t in parent_tasks if t["id"] != parent_job_id and "-" in t["id"]]
    user_in_parent = [t for t in tasks if t["parent_job_id"] == parent_job_id]
    user_active = [t for t in user_in_parent if t["status"] != "Hoàn thành"]
    pool_total = len(parent_children) or len(parent_tasks)
    pool_done = sum(1 for t in parent_children if (t.get("status") or "").strip() == "Hoàn thành")
    return {
        "parent_job_id": parent_job_id,
        "parent_job_name": next((t["name"] for t in mock_sheets._ke_hoach if t["id"] == parent_job_id), parent_job_id),
        "pool_total_tasks": pool_total,
        "pool_done": pool_done,
        "pool_completion_rate": round(pool_done / pool_total * 100) if pool_total else 0,
        "user_assigned": len(user_in_parent),
        "user_active": len(user_active),
        "user_share_pct": round(len(user_in_parent) / pool_total * 100, 1) if pool_total else 0,
        "coverage_gap": max(0, pool_total - len(user_in_parent)),
        "user_tasks": user_in_parent[:15],
    }


def get_employee_work_pool(name: str) -> dict:
    profiles = _load_profiles()
    profile = profiles.get(name) or _default_profile(name)
    tasks = _tasks_for_user(name)
    stats = _pool_stats(tasks)
    parent_ids = list({t["parent_job_id"] for t in tasks if t["parent_job_id"]})
    comparisons = [_compare_with_parent_job(tasks, pid) for pid in parent_ids[:5]]
    salary = profile.get("salary_3p", {})
    return {
        "employee": name,
        "profile": {
            "salary_3p": salary,
            "salary_3p_avg": round(sum(salary.values()) / len(salary), 2) if salary else 0,
            "skill_level": profile.get("skill_level", 2),
            "competency_score": profile.get("competency_score", 60),
            "efficiency_score": profile.get("efficiency_score", 60),
            "job_grade": profile.get("job_grade", "Junior"),
            "default_priority": profile.get("default_priority", "Trung bình"),
        },
        "work_pool": stats,
        "current_tasks": tasks[:20],
        "job_comparisons": comparisons,
    }


def list_work_pools(viewer_role: str, viewer_name: str, target: str | None = None) -> dict:
    mock_sheets._load()
    role = normalize_role(viewer_role)
    profiles = _load_profiles()

    if target:
        if not can_view_staff_data(role, viewer_name, target):
            return {"error": f"Không có quyền xem bể công việc của {target}"}
        staff_names = [target]
    elif role == "member":
        staff_names = [viewer_name] if viewer_name else []
    else:
        staff_names = [s["name"] for s in mock_sheets._staff if s.get("role") not in ("admin", "super_admin")]
        for name in profiles:
            if name not in staff_names:
                staff_names.append(name)

    pools = [get_employee_work_pool(n) for n in staff_names if n]
    pools.sort(key=lambda x: (-x["work_pool"]["active"], -x["profile"]["efficiency_score"]))
    return {"count": len(pools), "employees": pools}


def ai_organize_data(scope: str = "work_pool") -> dict:
    """AI helper — gợi ý sắp xếp dữ liệu hợp lý (rule-based, logic chi tiết sẽ bổ sung sau)."""
    mock_sheets._load()
    all_pools = list_work_pools("super_admin", "System", target=None)
    employees = all_pools.get("employees", [])

    overloaded = []
    underutilized = []
    priority_alerts = []
    suggestions = []

    for emp in employees:
        name = emp["employee"]
        active = emp["work_pool"]["active"]
        eff = emp["profile"]["efficiency_score"]
        comp = emp["profile"]["competency_score"]

        if active >= 8:
            overloaded.append({"name": name, "active_tasks": active, "efficiency": eff})
        elif active <= 2 and comp >= 75:
            underutilized.append({"name": name, "active_tasks": active, "competency": comp})

        urgent = [t for t in emp["current_tasks"] if t["priority"] in ("Khẩn cấp", "Cao") and t["status"] != "Hoàn thành"]
        if urgent:
            priority_alerts.append({
                "name": name,
                "urgent_count": len(urgent),
                "tasks": [{"id": t["id"], "name": t["name"][:50], "priority": t["priority"]} for t in urgent[:3]],
            })

        for cmp in emp.get("job_comparisons", []):
            if cmp["user_share_pct"] > 40 and cmp["pool_completion_rate"] < 50:
                suggestions.append(
                    f"{name} đang gánh {cmp['user_share_pct']}% job {cmp['parent_job_id']} "
                    f"nhưng tiến độ chung chỉ {cmp['pool_completion_rate']}% — cân nhắc hỗ trợ thêm."
                )

    if overloaded:
        suggestions.append(
            "Phân bổ lại task cho: " + ", ".join(o["name"] for o in overloaded[:3])
            + " (quá tải >8 việc đang active)."
        )
    if underutilized:
        suggestions.append(
            "Có thể giao thêm việc cho: " + ", ".join(u["name"] for u in underutilized[:3])
            + " (năng lực cao, ít việc)."
        )

    gpt_hints = _gpt_organize_hints(
        overloaded, underutilized, priority_alerts, suggestions,
    )
    if gpt_hints:
        suggestions = (suggestions + gpt_hints)[:12]

    return {
        "scope": scope,
        "generated_at": date.today().isoformat(),
        "summary": {
            "total_employees": len(employees),
            "overloaded": len(overloaded),
            "underutilized": len(underutilized),
            "priority_alerts": len(priority_alerts),
        },
        "overloaded": overloaded[:10],
        "underutilized": underutilized[:10],
        "priority_alerts": priority_alerts[:15],
        "suggestions": suggestions[:10] or ["Dữ liệu hiện tại phân bổ ổn định. Chờ logic chỉ số chi tiết từ team."],
        "note": "Logic chỉ số chi tiết sẽ được cập nhật khi team cung cấp quy tắc tính toán.",
    }


def _gpt_organize_hints(overloaded, underutilized, priority_alerts, base_suggestions: list) -> list[str]:
    """GPT bổ sung gợi ý sắp xếp — không thay thế rule-based."""
    if not settings.openai_api_key:
        return []
    try:
        from openai import OpenAI

        payload = {
            "overloaded": overloaded[:5],
            "underutilized": underutilized[:5],
            "priority_alerts": priority_alerts[:5],
            "existing": base_suggestions[:5],
        }
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý quản lý công việc QLXD. Dựa trên JSON, đưa 2-4 gợi ý ngắn "
                        "(mỗi gợi ý 1 câu) về phân bổ task, ưu tiên, cân bằng tải. "
                        "Không bịa tên hay số liệu mới. Trả về JSON: {\"hints\": [\"...\"]}"
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            **completion_limit_kwargs(settings.openai_model, 400),
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        hints = data.get("hints") or data.get("suggestions") or []
        return [str(h).strip() for h in hints if str(h).strip()][:4]
    except Exception:
        return []
