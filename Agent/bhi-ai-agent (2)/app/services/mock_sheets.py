"""Mock sheets service - searches local JSON data instead of calling Apps Script."""
import json
import os
import unicodedata
from datetime import datetime
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
PERSONAL_DIR = os.path.join(DATA_DIR, "personal")

_ke_hoach = None
_archive = None
_staff = None
_personal_cache: dict = {}  # user_name → personal data dict


def _load():
    global _ke_hoach, _archive, _staff
    if _ke_hoach is None:
        with open(os.path.join(DATA_DIR, "ke_hoach.json"), encoding="utf-8") as f:
            _ke_hoach = json.load(f)
        with open(os.path.join(DATA_DIR, "archive_log.json"), encoding="utf-8") as f:
            _archive = json.load(f)
        with open(os.path.join(DATA_DIR, "staff.json"), encoding="utf-8") as f:
            _staff = json.load(f)


def _slugify(name: str) -> str:
    """'Phan Minh Hoàng' → 'phan_minh_hoang'."""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    no_accent = no_accent.replace("đ", "d").replace("Đ", "d")
    return no_accent.lower().replace(" ", "_")


def _load_personal(user_name: str) -> dict | None:
    """Load file JSON cá nhân của user, cache memo. Trả None nếu chưa có file."""
    if user_name in _personal_cache:
        return _personal_cache[user_name]
    path = os.path.join(PERSONAL_DIR, _slugify(user_name) + ".json")
    if not os.path.exists(path):
        _personal_cache[user_name] = None
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _personal_cache[user_name] = data
    return data



def get_staff_by_email(email: str) -> dict | None:
    _load()
    for s in _staff:
        if s["email"].lower() == email.lower():
            return s
    return None


def get_staff_by_name(name: str) -> dict | None:
    """Match nhân sự theo TÊN (chuẩn hoá không dấu/hoa-thường). Dùng khi
    email Google (gmail cá nhân) không khớp email công ty trong staff.json."""
    if not name or not name.strip():
        return None
    _load()
    target = _slugify(name.strip())
    for s in _staff:
        if _slugify(s["name"]) == target:
            return s
    return None


def get_staff_for_google_login(email: str, display_name: str = "") -> tuple[dict | None, str]:
    """Map tài khoản Google → nhân sự + role.

    Thứ tự: email công ty → google_email/gmail alias → tên hiển thị Google.
    """
    email_key = (email or "").strip().lower()
    if not email_key:
        return None, ""

    staff = get_staff_by_email(email_key)
    if staff:
        return staff, "email"

    _load()
    for s in _staff:
        alias = (s.get("google_email") or s.get("gmail") or "").strip().lower()
        if alias and alias == email_key:
            return s, "google_email"

    if display_name:
        staff = get_staff_by_name(display_name)
        if staff:
            return staff, "name"

    return None, ""


def _name_match(field: str, query: str) -> bool:
    """Match full name in comma-separated field. Avoids partial substring issues."""
    names = [n.strip() for n in field.split(",")]
    return any(query == n or query in n and len(query) > len(n) * 0.6 for n in names)


class MockSheetsService:
    def __init__(self):
        _load()

    async def search_tasks(self, user=None, status=None, date_from=None, date_to=None, keyword=None, zone=None, role=None, has_reviewer=None):
        results = []
        for t in _ke_hoach:
            if has_reviewer and not str(t.get("reviewer") or "").strip():
                continue
            if user:
                if role == "pic":
                    if not _name_match(t["pic"], user):
                        continue
                elif role == "support":
                    if not _name_match(t["support"], user):
                        continue
                elif role == "reviewer":
                    if not _name_match(t["reviewer"], user):
                        continue
                elif not _name_match(t["pic"], user) and not _name_match(t["support"], user) and not _name_match(t["reviewer"], user):
                    continue
            if status and t["status"].strip() != status:
                continue
            if date_from and date_from == date_to:
                # Single date query: find tasks where date falls within start-end range
                d = date_from
                if t.get("end_date") and t.get("start_date"):
                    if not (t["start_date"] <= d <= t["end_date"]):
                        continue
                elif t.get("end_date"):
                    if t["end_date"] != d:
                        continue
                else:
                    continue
            else:
                if date_to and t["end_date"] and t["end_date"] > date_to:
                    continue
                if date_from and t["end_date"] and t["end_date"] < date_from:
                    continue
            if keyword and keyword.lower() not in (t["name"] + " " + t["note"] + " " + t["zone"]).lower():
                continue
            if zone and zone.lower() not in (t.get("zone") or "").lower():
                continue
            results.append(t)
        out = {"tasks": results[:50], "count": len(results)}
        if user:
            out["role_breakdown"] = {
                "pic": sum(1 for t in _ke_hoach if _name_match(t["pic"], user)),
                "support": sum(1 for t in _ke_hoach if _name_match(t["support"], user)),
                "reviewer": sum(1 for t in _ke_hoach if _name_match(t["reviewer"], user)),
            }
        return out

    async def search_overdue_tasks(self, user=None, role="pic"):
        """Task quá hạn: chưa hoàn thành và end_date < hôm nay. Lọc đủ toàn bộ kế hoạch."""
        from datetime import date
        today = date.today().isoformat()
        results = []
        for t in _ke_hoach:
            if (t.get("status") or "").strip() == "Hoàn thành":
                continue
            if not t.get("end_date") or t["end_date"] >= today:
                continue
            if user:
                if role == "pic":
                    if not _name_match(t["pic"], user):
                        continue
                elif role == "support":
                    if not _name_match(t["support"], user):
                        continue
                elif role == "reviewer":
                    if not _name_match(t["reviewer"], user):
                        continue
                elif not _name_match(t["pic"], user) and not _name_match(t["support"], user) and not _name_match(t["reviewer"], user):
                    continue
            results.append(t)
        return {"tasks": results[:50], "count": len(results), "filter": "overdue"}

    async def get_task_detail(self, task_id):
        for t in _ke_hoach:
            if t["id"] == task_id:
                return {"task": t}
        return {"error": f"Task not found: {task_id}"}

    async def get_subtasks(self, parent_id):
        subtasks = [t for t in _ke_hoach if t["id"].startswith(parent_id + "-")]
        return {"parent_id": parent_id, "subtasks": subtasks, "count": len(subtasks)}

    async def search_archive(self, user=None, project=None, date_from=None, date_to=None):
        results = []
        for r in _archive:
            if user and user != r["user"]:
                continue
            if project and project.lower() not in r["project"].lower():
                continue
            if date_from and r["report_date"] and r["report_date"][:10] < date_from:
                continue
            if date_to and r["report_date"] and r["report_date"][:10] > date_to:
                continue
            results.append(r)
        return {"reports": results[:50], "count": len(results)}

    async def create_wbs(self, parent_name, children):
        return {"message": f"[MOCK] Sẽ tạo '{parent_name}' với {len(children)} task con", "created": len(children)}

    async def update_task(self, task_id, fields):
        return {"message": f"[MOCK] Sẽ cập nhật task {task_id}: {fields}", "success": True}

    # ============================================================
    # PERSONAL DATA - đọc từ data/personal/<slug>.json
    # ============================================================

    async def get_personal_log(self, user_name, project=None, date_from=None, date_to=None,
                                status=None):
        """Trả _ARCHIVE_LOG cá nhân của user (chi tiết hơn archive chung,
        có cột Tiến độ + Ghi chú phát sinh). Filter giống search_archive."""
        data = _load_personal(user_name)
        if not data:
            return {"reports": [], "count": 0,
                    "error": f"Chưa có file cá nhân của {user_name}"}
        results = []
        for r in data.get("archive", []):
            if project and project.lower() not in (r.get("project") or "").lower():
                continue
            if date_from and r.get("report_date") and r["report_date"][:10] < date_from:
                continue
            if date_to and r.get("report_date") and r["report_date"][:10] > date_to:
                continue
            if status and (r.get("status") or "").strip() != status:
                continue
            results.append(r)
        return {"user": user_name, "reports": results[:50], "count": len(results)}

    async def get_hours_summary(self, user_name, date_from=None, date_to=None):
        """Tổng giờ làm theo project trong khoảng thời gian (từ archive cá nhân)."""
        data = _load_personal(user_name)
        if not data:
            return {"by_project": {}, "total_hours": 0, "report_count": 0,
                    "error": f"Chưa có file cá nhân của {user_name}"}
        by_project = defaultdict(float)
        report_count = 0
        for r in data.get("archive", []):
            if date_from and r.get("report_date") and r["report_date"][:10] < date_from:
                continue
            if date_to and r.get("report_date") and r["report_date"][:10] > date_to:
                continue
            hours = r.get("hours") or 0
            project = (r.get("project") or "Khác").strip() or "Khác"
            by_project[project] += hours
            report_count += 1
        total = sum(by_project.values())
        return {
            "user": user_name,
            "by_project": dict(sorted(by_project.items(), key=lambda x: x[1], reverse=True)),
            "total_hours": round(total, 1),
            "report_count": report_count,
            "date_from": date_from,
            "date_to": date_to,
        }

    async def get_personal_tasks(self, user_name, status=None):
        """Trả tasks trong file cá nhân (có cột 'hours' và 'log_history' riêng)."""
        data = _load_personal(user_name)
        if not data:
            return {"tasks": [], "count": 0,
                    "error": f"Chưa có file cá nhân của {user_name}"}
        tasks = data.get("tasks", [])
        if status:
            tasks = [t for t in tasks if (t.get("status") or "").strip() == status]
        return {"user": user_name, "tasks": tasks[:50], "count": len(tasks)}

    @staticmethod
    def list_personal_users() -> list:
        """Liệt kê các nhân sự đã có file cá nhân (để chatbot biết ai có data)."""
        if not os.path.isdir(PERSONAL_DIR):
            return []
        slugs = [f[:-5] for f in os.listdir(PERSONAL_DIR) if f.endswith(".json")]
        _load()
        result = []
        for s in _staff:
            if _slugify(s["name"]) in slugs:
                result.append(s["name"])
        return result
