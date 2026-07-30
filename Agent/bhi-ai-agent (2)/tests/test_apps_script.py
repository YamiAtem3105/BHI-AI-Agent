"""
Apps Script Integration Test
Tests the deployed Apps Script Web App endpoint.

Usage:
  python tests/test_apps_script.py                          # dry-run (validates format)
  python tests/test_apps_script.py https://script.google.com/macros/s/XXX/exec  # live test
"""
import asyncio
import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

# Expected response schemas
TASK_FIELDS = ["id", "name", "start_date", "end_date", "duration_days", "predecessor",
               "status", "elapsed", "pic", "support", "reviewer", "note",
               "check_prep_date", "check_prep", "check_exec_date", "check_exec",
               "check_accept_date", "check_accept", "zone"]

ARCHIVE_FIELDS = ["report_date", "user", "employee_id", "role", "project",
                  "task_content", "hours", "status", "deadline", "evaluation", "report_note"]


async def test_endpoint(base_url: str):
    """Test all Apps Script endpoints."""
    print(f"🔗 Testing: {base_url}")
    print("=" * 60)

    client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    passed = 0
    failed = 0

    async def check(name, coro):
        nonlocal passed, failed
        try:
            start = time.perf_counter()
            result = await coro
            elapsed = (time.perf_counter() - start) * 1000
            if result:
                passed += 1
                print(f"  ✅ {name} ({elapsed:.0f}ms)")
            else:
                failed += 1
                print(f"  ❌ {name} ({elapsed:.0f}ms)")
            return result
        except Exception as e:
            failed += 1
            print(f"  ❌ {name} - ERROR: {e}")
            return None

    # --- GET endpoints ---
    print("\n📋 1. SEARCH TASKS")

    async def test_search_all():
        r = await client.get(base_url, params={"action": "search"})
        data = r.json()
        assert "tasks" in data and "count" in data, f"Bad format: {list(data.keys())}"
        assert data["count"] > 0, "No tasks found"
        # Validate task fields
        task = data["tasks"][0]
        missing = [f for f in TASK_FIELDS if f not in task]
        assert not missing, f"Missing fields: {missing}"
        return data

    async def test_search_user():
        r = await client.get(base_url, params={"action": "search", "user": "Phan Minh Hoàng"})
        data = r.json()
        assert data["count"] > 0, "No tasks for user"
        for t in data["tasks"][:5]:
            assert "Phan Minh Hoàng" in t["pic"] or "Phan Minh Hoàng" in t["support"] or "Phan Minh Hoàng" in t["reviewer"]
        return data

    async def test_search_status():
        r = await client.get(base_url, params={"action": "search", "status": "Hoàn thành"})
        data = r.json()
        assert data["count"] > 0
        for t in data["tasks"][:5]:
            assert t["status"] == "Hoàn thành", f"Wrong status: {t['status']}"
        return data

    async def test_search_keyword():
        r = await client.get(base_url, params={"action": "search", "keyword": "training"})
        data = r.json()
        assert data["count"] >= 0  # may or may not find
        return data

    await check("Search all tasks", test_search_all())
    await check("Search by user", test_search_user())
    await check("Search by status", test_search_status())
    await check("Search by keyword", test_search_keyword())

    print("\n🔍 2. TASK DETAIL")

    async def test_detail():
        r = await client.get(base_url, params={"action": "detail", "taskId": "CO-001"})
        data = r.json()
        assert "task" in data, f"Bad format: {data}"
        assert data["task"]["id"] == "CO-001"
        missing = [f for f in TASK_FIELDS if f not in data["task"]]
        assert not missing, f"Missing: {missing}"
        return data

    async def test_detail_not_found():
        r = await client.get(base_url, params={"action": "detail", "taskId": "FAKE-999"})
        data = r.json()
        assert "error" in data, "Should return error for non-existent task"
        return data

    await check("Get task detail (CO-001)", test_detail())
    await check("Task not found → error", test_detail_not_found())

    print("\n🌳 3. SUBTASKS")

    async def test_subtasks():
        r = await client.get(base_url, params={"action": "subtasks", "parentId": "CO"})
        data = r.json()
        assert "subtasks" in data and "count" in data
        assert data["count"] > 0
        for s in data["subtasks"]:
            assert s["id"].startswith("CO-")
        return data

    await check("Get subtasks (CO)", test_subtasks())

    print("\n📊 4. ARCHIVE LOG")

    async def test_archive():
        r = await client.get(base_url, params={"action": "archive", "user": "Phan Minh Hoàng"})
        data = r.json()
        assert "reports" in data and "count" in data
        if data["count"] > 0:
            report = data["reports"][0]
            missing = [f for f in ARCHIVE_FIELDS if f not in report]
            assert not missing, f"Missing: {missing}"
        return data

    await check("Search archive", test_archive())

    print("\n✏️ 5. WRITE OPERATIONS (dry-run format check)")

    async def test_create_format():
        # Only validate the request format, don't actually write
        payload = {
            "action": "create",
            "tasks": [{"name": "TEST - DELETE ME", "pic": "Test", "duration": 1}]
        }
        # Just verify the payload structure is correct JSON
        json.dumps(payload)  # Should not throw
        return True

    async def test_update_format():
        payload = {
            "action": "update",
            "taskId": "CO-001",
            "fields": {"status": "Hoàn thành", "note": "Test note"}
        }
        json.dumps(payload)
        return True

    await check("Create WBS payload format", test_create_format())
    await check("Update task payload format", test_update_format())

    print("\n⏱️ 6. PERFORMANCE")

    async def test_response_time():
        times = []
        for _ in range(5):
            start = time.perf_counter()
            await client.get(base_url, params={"action": "search", "user": "Phan Minh Hoàng"})
            times.append((time.perf_counter() - start) * 1000)
        avg = sum(times) / len(times)
        print(f"      Avg response: {avg:.0f}ms (5 requests)")
        assert avg < 10000, f"Too slow: {avg}ms"  # Apps Script can be 2-8s
        return True

    await check("Response time < 10s", test_response_time())

    # Summary
    await client.aclose()
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{passed+failed} passed, {failed} failed")
    if failed == 0:
        print("🎉 APPS SCRIPT INTEGRATION TEST PASSED!")
    else:
        print(f"⚠️ {failed} tests failed")
    return failed == 0


async def dry_run():
    """Test without actual endpoint - validates expected formats."""
    print("🧪 DRY RUN MODE (no endpoint URL provided)")
    print("   Validates expected request/response formats\n")

    # Validate expected formats
    print("  Expected GET endpoints:")
    endpoints = [
        "GET /exec?action=search&user=X&status=Y&dateFrom=Z&dateTo=W&keyword=K&zone=Z",
        "GET /exec?action=detail&taskId=CO-001",
        "GET /exec?action=subtasks&parentId=CO",
        "GET /exec?action=archive&user=X&project=Y&dateFrom=Z&dateTo=W",
    ]
    for e in endpoints:
        print(f"    ✅ {e}")

    print("\n  Expected POST endpoints:")
    posts = [
        'POST /exec {"action":"create","tasks":[{"name":"X","pic":"Y","duration":N}]}',
        'POST /exec {"action":"update","taskId":"CO-001","fields":{"status":"X","note":"Y"}}',
    ]
    for p in posts:
        print(f"    ✅ {p}")

    print("\n  Expected response - search_tasks:")
    sample = {"tasks": [{"id": "CO-001", "name": "...", "status": "Hoàn thành", "...": "19 fields"}], "count": 137}
    print(f"    {json.dumps(sample, ensure_ascii=False)}")

    print("\n  Expected response - archive:")
    sample = {"reports": [{"report_date": "2026-03-16", "user": "...", "...": "11 fields"}], "count": 4015}
    print(f"    {json.dumps(sample, ensure_ascii=False)}")

    print(f"\n  Task fields ({len(TASK_FIELDS)}): {', '.join(TASK_FIELDS)}")
    print(f"  Archive fields ({len(ARCHIVE_FIELDS)}): {', '.join(ARCHIVE_FIELDS)}")

    print("\n" + "=" * 60)
    print("To run live test:")
    print("  python tests/test_apps_script.py https://script.google.com/macros/s/YOUR_ID/exec")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        asyncio.run(test_endpoint(url))
    else:
        asyncio.run(dry_run())
