"""Test cho tính năng personal data (Số giờ làm, Log cá nhân)."""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from app.main import app
from app.services.mock_sheets import MockSheetsService

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


def run(coro):
    return asyncio.run(coro)


print("\n" + "=" * 70)
print("PERSONAL DATA - service layer")
print("=" * 70)
s = MockSheetsService()

# 1. list_personal_users
users = s.list_personal_users()
check("1.1 list_personal_users không rỗng", len(users) >= 1, f"got {users}")
check("1.2 PMH có trong list", "Phan Minh Hoàng" in users)

# 2. get_personal_log của PMH (có data)
r = run(s.get_personal_log("Phan Minh Hoàng"))
check("2.1 PMH personal log > 0", r["count"] > 0, f"got {r['count']}")
check("2.2 Trả max 50 records", len(r["reports"]) <= 50)
check("2.3 Có schema personal (progress)",
      any("progress" in rep for rep in r["reports"]))

# 3. get_personal_log với filter project
r = run(s.get_personal_log("Phan Minh Hoàng", project="KẾ HOẠCH CHUYỂN ĐỔI SỐ"))
check("3.1 Filter project > 0", r["count"] > 0)
check("3.2 Tất cả result match project",
      all("KẾ HOẠCH CHUYỂN ĐỔI SỐ" in (rep.get("project") or "") for rep in r["reports"]))

# 4. get_personal_log với filter date
r = run(s.get_personal_log("Phan Minh Hoàng", date_from="2026-04-01", date_to="2026-04-30"))
check("4.1 Filter tháng 4/2026 > 0", r["count"] > 0)
check("4.2 Date trong range",
      all("2026-04-01" <= rep["report_date"][:10] <= "2026-04-30"
          for rep in r["reports"] if rep.get("report_date")))

# 5. get_personal_log của user chưa có file
r = run(s.get_personal_log("Bùi Thanh Bình"))
check("5.1 User chưa có file → error", "error" in r and r["count"] == 0)

# 6. get_hours_summary
r = run(s.get_hours_summary("Phan Minh Hoàng"))
check("6.1 PMH total_hours >= 0", r["total_hours"] >= 0)
check("6.2 by_project là dict", isinstance(r["by_project"], dict))
check("6.3 report_count > 0", r["report_count"] > 0)
check("6.4 Có project KẾ HOẠCH CHUYỂN ĐỔI SỐ",
      any("CHUYỂN ĐỔI SỐ" in p for p in r["by_project"].keys()))

# 7. get_hours_summary user chưa có file
r = run(s.get_hours_summary("Bùi Thanh Bình"))
check("7.1 User chưa có file → error", "error" in r)

# 8. get_personal_tasks
r = run(s.get_personal_tasks("Phan Minh Hoàng"))
check("8.1 PMH personal tasks > 0", r["count"] > 0)
check("8.2 Có cột hours và log_history",
      all("hours" in t and "log_history" in t for t in r["tasks"]))


print("\n" + "=" * 70)
print("PERSONAL DATA - API endpoint /api/chat (JWT)")
print("=" * 70)
client = TestClient(app)


def _login(email, pw):
    return client.post("/api/login", json={"email": email, "password": pw}).json().get("token")


def _chat(token, msg):
    h = {"Authorization": "Bearer " + token} if token else {}
    return client.post("/api/chat", headers=h, json={"message": msg}).json()


pmh = _login("hoangpm@bicholder.vn", "PmhPass123!")   # admin
btb = _login("thanhbinh@bicholder.vn", "Member123!")   # member

check("8.9 PMH login có token", bool(pmh))
check("8.10 BTB login có token", bool(btb))

# 9. "Giờ làm của tôi" với PMH
body = _chat(pmh, "giờ làm của tôi")
check("9.1 chat tool=hours_summary", body["tool"] == "hours_summary", f"got tool={body.get('tool')}")
check("9.2 params user=PMH", body["params"].get("user") == "Phan Minh Hoàng")
check("9.3 response có thông tin giờ làm",
      "ghi nhận" in body["response"].lower() or "giờ" in body["response"].lower())

# 10. Admin (PMH) hỏi giờ của PMH bằng tên đầy đủ → cho phép
body = _chat(pmh, "Số giờ làm của Phan Minh Hoàng")
check("10.1 admin parse tên → hours_summary", body["tool"] == "hours_summary")
check("10.2 user=PMH", body["params"].get("user") == "Phan Minh Hoàng")

# 11. Không có token → 401
r = client.post("/api/chat", json={"message": "tổng giờ"})
check("11.1 Không token → 401", r.status_code == 401, f"got {r.status_code}")

# 12. "Log cá nhân của tôi" với PMH
body = _chat(pmh, "log cá nhân của tôi")
check("12.1 chat tool=personal_log", body["tool"] == "personal_log")
check("12.2 user=PMH", body["params"].get("user") == "Phan Minh Hoàng")
check("12.3 response có log cá nhân", "log cá nhân" in body["response"].lower())

# 13. Member (BTB) hỏi log của PMH → bị ép về chính mình (không xem được người khác)
body = _chat(btb, "log ca nhan Phan Minh Hoang")
check("13.1 member → personal_log", body["tool"] == "personal_log")
check("13.2 member bị ép user=BTB", body["params"].get("user") == "Bùi Thanh Bình",
      f"got {body['params'].get('user')}")

# 14. PMH chưa-có-file? PMH có file; dùng member BTB (chưa có file) hỏi giờ của mình → error friendly
body = _chat(btb, "giờ làm của tôi")
check("14.1 BTB chưa có file → hours_summary + error",
      body["tool"] == "hours_summary" and "error" in body["data"])
check("14.2 Response thân thiện",
      "Chưa có" in body["response"] or "chưa" in body["response"].lower() or "❌" in body["response"])


print("\n" + "=" * 70)
print(f"PERSONAL DATA: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 70)
if failed:
    print("\nLỖI:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\n✅ Personal data feature OK")
