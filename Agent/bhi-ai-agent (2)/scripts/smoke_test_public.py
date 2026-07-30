"""Smoke test public demo URL before user testing."""
import httpx
import json
import sys
import time

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://households-asks-industry-mil.trycloudflare.com"
TIMEOUT = 20

results = {"pass": [], "fail": [], "warn": []}


def ok(name, detail=""):
    results["pass"].append({"test": name, "detail": detail})


def fail(name, detail=""):
    results["fail"].append({"test": name, "detail": detail})


def warn(name, detail=""):
    results["warn"].append({"test": name, "detail": detail})


client = httpx.Client(timeout=TIMEOUT, follow_redirects=True)

# Stability: 5 health checks
latencies = []
for i in range(5):
    t0 = time.perf_counter()
    try:
        r = client.get(f"{BASE}/health")
        ms = round((time.perf_counter() - t0) * 1000)
        latencies.append(ms)
        if r.status_code != 200 or r.json().get("status") != "ok":
            fail("stability_health", f"run{i+1} status={r.status_code}")
    except Exception as e:
        fail("stability_health", f"run{i+1} {e}")
if len(latencies) == 5:
    ok(
        "stability_health",
        f"5/5 OK, latency ms: min={min(latencies)} avg={sum(latencies)//5} max={max(latencies)}",
    )

for path, needle in [("/", "BHI Agent"), ("/dashboard", "BHI Dashboard"), ("/admin/", "BHI Agent")]:
    try:
        r = client.get(f"{BASE}{path}")
        if r.status_code == 200 and needle in r.text:
            ok(f"page{path}", f"{len(r.text)} bytes")
        else:
            fail(f"page{path}", f"status={r.status_code}")
    except Exception as e:
        fail(f"page{path}", str(e))

try:
    r = client.post(
        f"{BASE}/admin/login",
        json={"username": "admin", "password": "local-dev-change-me"},
    )
    if r.status_code == 200 and r.json().get("token"):
        ok("admin_login", "token ok")
    else:
        fail("admin_login", r.text[:120])
except Exception as e:
    fail("admin_login", str(e))

tokens = {}
for email, pwd, role in [
    ("nosdevai2k@gmail.com", "TestPass123!", "admin"),
    ("thanhbinh@bicholder.vn", "Member123!", "member"),
]:
    try:
        r = client.post(f"{BASE}/api/login", json={"email": email, "password": pwd})
        d = r.json()
        if d.get("success") and d.get("token"):
            tokens[role] = d["token"]
            ok(f"login_{role}", d.get("name", ""))
        else:
            fail(f"login_{role}", d.get("error", ""))
    except Exception as e:
        fail(f"login_{role}", str(e))

if "admin" in tokens:
    h = {"Authorization": "Bearer " + tokens["admin"]}
    queries = [
        ("xin chao", lambda d: len(d.get("response", "")) > 5),
        ("Task qua han", lambda d: bool(d.get("response"))),
        ("Chi tiet CO-001", lambda d: "CO-001" in d.get("response", "").upper()),
    ]
    for q, check in queries:
        try:
            r = client.post(f"{BASE}/api/chat", json={"message": q}, headers=h, timeout=45)
            d = r.json()
            if r.status_code == 200 and check(d):
                ok(f"chat_admin:{q[:20]}", (d.get("response", "")[:60] + "..."))
            else:
                fail(f"chat_admin:{q[:20]}", f"status={r.status_code} resp={str(d)[:100]}")
        except Exception as e:
            fail(f"chat_admin:{q[:20]}", str(e))

    try:
        r = client.get(f"{BASE}/api/dashboard", headers={"Authorization": "Bearer " + tokens["admin"]})
        d = r.json()
        s = d.get("summary", {})
        if r.status_code == 200 and s.get("total_tasks", 0) > 0:
            ok("dashboard_admin", f"tasks={s.get('total_tasks')} staff={s.get('total_staff')}")
        else:
            fail("dashboard_admin", str(d)[:120])
    except Exception as e:
        fail("dashboard_admin", str(e))

if "member" in tokens:
    try:
        r = client.get(
            f"{BASE}/api/dashboard",
            headers={"Authorization": "Bearer " + tokens["member"]},
        )
        if r.status_code == 403:
            ok("member_dashboard_blocked", "403 as expected")
        else:
            fail("member_dashboard_blocked", f"status={r.status_code}")
    except Exception as e:
        fail("member_dashboard_blocked", str(e))

try:
    r = client.post(f"{BASE}/api/chat", json={"message": "test"})
    if r.status_code == 401:
        ok("chat_no_auth", "401 as expected")
    else:
        fail("chat_no_auth", f"status={r.status_code}")
except Exception as e:
    fail("chat_no_auth", str(e))

try:
    r = client.get(f"{BASE}/auth/google/redirect-uri")
    d = r.json()
    uri = d.get("redirect_uri", "")
    if "trycloudflare.com" in uri:
        ok("oauth_redirect_uri", uri)
    else:
        warn("oauth_redirect_uri", uri)
except Exception as e:
    fail("oauth_redirect_uri", str(e))

client.close()
print(json.dumps(results, ensure_ascii=False, indent=2))
print("SUMMARY:", len(results["pass"]), "pass,", len(results["fail"]), "fail,", len(results["warn"]), "warn")
sys.exit(1 if results["fail"] else 0)
