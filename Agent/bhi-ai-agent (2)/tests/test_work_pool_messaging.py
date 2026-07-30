"""Tests: RBAC, work pool, messaging, dashboard APIs."""
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.services.rbac import has_permission, normalize_role, ROLE_RANK
from app.services.work_pool_service import get_employee_work_pool, ai_organize_data, _task_job_level, _infer_priority

passed = 0
failed = 0
errors = []


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {label}")
    else:
        failed += 1
        errors.append(f"{label} | {detail}")
        print(f"  FAIL {label} | {detail}")


print("\n" + "=" * 70)
print("RBAC + WORK POOL + MESSAGING")
print("=" * 70)

# --- RBAC unit ---
check("RBAC super_admin rank", ROLE_RANK["super_admin"] > ROLE_RANK["admin"])
check("RBAC member dashboard.work_pool.self", has_permission("member", "dashboard.work_pool.self"))
check("RBAC member no ai_organize", not has_permission("member", "dashboard.ai_organize"))
check("RBAC manager ai_organize", has_permission("manager", "dashboard.ai_organize"))
check("RBAC normalize unknown", normalize_role("xyz") == "member")

# --- Work pool unit ---
check("Job level CO", _task_job_level("CO") == 1)
check("Job level CO-001", _task_job_level("CO-001") == 2)
check("Job level CO-001.3", _task_job_level("CO-001.3") == 3)

pool = get_employee_work_pool("Phan Minh Hoàng")
check("Work pool has employee", pool.get("employee") == "Phan Minh Hoàng")
check("Work pool has profile", "salary_3p" in pool.get("profile", {}))
check("Work pool has tasks", "current_tasks" in pool)
check("Work pool has comparisons", "job_comparisons" in pool)

ai = ai_organize_data()
check("AI organize suggestions", "suggestions" in ai and len(ai["suggestions"]) > 0)
check("AI organize note", "note" in ai)

# --- API integration ---
client = TestClient(app)


def login(email, pw):
    r = client.post("/api/login", json={"email": email, "password": pw})
    return r.json().get("token")


admin = login("nosdevai2k@gmail.com", "TestPass123!")
manager = login("hoangpm@bicholder.vn", "PmhPass123!")
member = login("thanhbinh@bicholder.vn", "Member123!")

check("Admin token", bool(admin))
check("Manager token", bool(manager))
check("Member token", bool(member))

# Dashboard overview — member blocked
r = client.get("/api/dashboard", headers={"Authorization": f"Bearer {member}"})
check("Member overview -> 403", r.status_code == 403, f"got {r.status_code}")

r = client.get("/api/dashboard", headers={"Authorization": f"Bearer {admin}"})
check("Admin overview -> 200", r.status_code == 200, f"got {r.status_code}")

# Work pool — member sees self
r = client.get("/api/dashboard/work-pool", headers={"Authorization": f"Bearer {member}"})
check("Member work-pool -> 200", r.status_code == 200, f"got {r.status_code}")
if r.status_code == 200:
    body = r.json()
    check("Member work-pool count=1", body.get("count") == 1, f"count={body.get('count')}")

# Work pool — admin sees all
r = client.get("/api/dashboard/work-pool", headers={"Authorization": f"Bearer {admin}"})
check("Admin work-pool -> 200", r.status_code == 200)
if r.status_code == 200:
    check("Admin work-pool many", r.json().get("count", 0) > 1)

# AI organize — member blocked
r = client.get("/api/dashboard/ai-organize", headers={"Authorization": f"Bearer {member}"})
check("Member ai-organize -> 403", r.status_code == 403)

r = client.get("/api/dashboard/ai-organize", headers={"Authorization": f"Bearer {manager}"})
check("Manager ai-organize -> 200", r.status_code == 200, f"got {r.status_code}")

# Messaging status
r = client.get("/api/messaging/status")
check("Messaging status -> 200", r.status_code == 200)
check("Messaging field_report", r.json().get("field_report") is True)
check("Staff profiles count", len(json.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "staff_profiles.json"), encoding="utf-8"))) >= 19)

# Telegram webhook — unknown user (cô lập file pending để không ghi đè data thật)
_pending_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "messaging_pending.json")
_pending_backup = None
if os.path.exists(_pending_path):
    with open(_pending_path, encoding="utf-8") as f:
        _pending_backup = f.read()
try:
    r = client.post("/api/messaging/telegram", json={
        "message": {
            "chat": {"id": 999888777},
            "from": {"first_name": "Unknown", "last_name": "User"},
            "text": "help",
        }
    })
    check("Telegram unknown user -> 200", r.status_code == 200)
finally:
    if _pending_backup is not None:
        with open(_pending_path, "w", encoding="utf-8") as f:
            f.write(_pending_backup)
    elif os.path.exists(_pending_path):
        os.remove(_pending_path)

# Sheet writer — append report (temp file)
from app.services.sheet_writer import SheetWriter
import app.services.mock_sheets as ms

writer = SheetWriter()
orig_archive = None
archive_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "archive_log.json")
with open(archive_path, encoding="utf-8") as f:
    orig_archive = json.load(f)
try:
    import asyncio
    result = asyncio.run(writer.execute("append_field_report", {
        "user": "Bùi Thanh Bình",
        "task_content": "Test báo cáo hiện trường từ chatbot",
        "report_date": "2026-06-16",
        "hours": 2,
        "project": "Hiện trường",
        "status": "Đang làm",
    }))
    check("Sheet writer append", result.get("success") is True, str(result))
finally:
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(orig_archive, f, ensure_ascii=False, indent=2)
    ms._archive = None

print("\n" + "=" * 70)
print(f"RESULT: {passed} passed, {failed} failed")
print("=" * 70)
if failed:
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\nAll new feature tests OK")
