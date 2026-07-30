"""Test auth cho /api/dashboard (JWT Bearer, server-side validate)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

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
print("DASHBOARD AUTH - JWT Bearer")
print("=" * 70)
client = TestClient(app)


def login(email, pw):
    r = client.post("/api/login", json={"email": email, "password": pw})
    return r.json().get("token")


# 1. Không có token → 401
r = client.get("/api/dashboard")
check("1.1 Không token → 401", r.status_code == 401, f"got {r.status_code}")

# 2. Token rác → 401
r = client.get("/api/dashboard", headers={"Authorization": "Bearer not-a-token"})
check("2.1 Token rác → 401", r.status_code == 401, f"got {r.status_code}")

# 3. Member → 403
mem = login("thanhbinh@bicholder.vn", "Member123!")
check("3.0 Member login có token", bool(mem))
r = client.get("/api/dashboard", headers={"Authorization": "Bearer " + mem})
check("3.1 Member → 403", r.status_code == 403, f"got {r.status_code}")
check("3.2 Error nêu role", "member" in r.text.lower() or "vai trò" in r.text.lower())

# 4. Admin → 200 + data
admin = login("nosdevai2k@gmail.com", "TestPass123!")
check("4.0 Admin login có token", bool(admin))
r = client.get("/api/dashboard", headers={"Authorization": "Bearer " + admin})
check("4.1 Admin → 200", r.status_code == 200, f"got {r.status_code}")
body = r.json()
check("4.2 Body có summary", "summary" in body and "total_tasks" in body["summary"])
check("4.3 Body có staff list", "staff" in body and len(body["staff"]) > 0)
check("4.4 Body có overdue_tasks", "overdue_tasks" in body)

# 5. Static page /dashboard vẫn render (JS auth check client-side)
r = client.get("/dashboard")
check("5.1 /dashboard HTML trả 200", r.status_code == 200)
check("5.2 HTML gửi Bearer token", "Bearer ' + session.token" in r.text or "Bearer '+session.token" in r.text)


print("\n" + "=" * 70)
print(f"DASHBOARD AUTH: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 70)
if failed:
    print("\nLỖI:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\n✅ Dashboard auth OK")
