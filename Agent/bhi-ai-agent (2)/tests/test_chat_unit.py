"""Unit tests for BHI AI Agent chatbot - all query cases."""
import sys, os, asyncio, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.chat import _find_status, _route_message
from app.services.text_utils import detect_task_role, find_staff, normalize_text, wants_tasks_with_reviewer
from app.services.mock_sheets import MockSheetsService, get_staff_by_email

passed = 0
failed = 0

def test(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")
        print(f"    Expected: {expected}")
        print(f"    Got:      {actual}")

def test_in(name, actual, substring):
    global passed, failed
    if substring in str(actual):
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")
        print(f"    Expected to contain: {substring}")
        print(f"    Got: {actual}")

def run(coro):
    return asyncio.run(coro)


print("=" * 60)
print("TEST 1: find_staff - name matching")
print("=" * 60)

# Exact with accent
test("exact accent", find_staff("Task của Phan Minh Hoàng"), "Phan Minh Hoàng")
test("exact accent 2", find_staff("Nguyễn Anh Tuấn Khanh"), "Nguyễn Anh Tuấn Khanh")
test("exact accent 3", find_staff("Lê Chí Hoàng Long"), "Lê Chí Hoàng Long")

# No accent
test("no accent full", find_staff("Phan Minh Hoang"), "Phan Minh Hoàng")
test("no accent 2", find_staff("Nguyen Van Cuong"), "Nguyễn Văn Cường")
test("no accent 3", find_staff("Le Chi Hoang Long"), "Lê Chí Hoàng Long")
test("no accent 4", find_staff("Ngo Thi Dung"), "Ngô Thị Dung")
test("no accent 5", find_staff("Do Thi Bich Hang"), "Đỗ Thị Bích Hằng")

# Last name unique
test("last name Binh", find_staff("task cua Binh"), "Bùi Thanh Bình")
test("last name Dung", find_staff("Dung"), "Ngô Thị Dung")
test("last name Kien", find_staff("task Kien"), "Vũ Đức Kiên")

# Ambiguous (multiple people with same last name)
test("ambiguous Hoang", find_staff("Hoang"), None)  # PMH + THH
test("ambiguous Trung", find_staff("Trung"), "Nguyễn Trọng Trung")  # unique last name

# Partial match
test("partial Minh Hoang", find_staff("Minh Hoang"), "Phan Minh Hoàng")
test("partial Huy Hoang", find_staff("Huy Hoang"), "Trần Huy Hoàng")

# Not found
test("not found", find_staff("Elon Musk"), None)
test("empty", find_staff(""), None)


print("\n" + "=" * 60)
print("TEST 1b: detect_task_role + has_reviewer")
print("=" * 60)

test("role reviewer", detect_task_role("Task kiem tra cua Nguyen Anh Tuan Khanh", has_user=True), "reviewer")
test("role pic default", detect_task_role("Task cua Phan Minh Hoang", has_user=True), "pic")
test("role support", detect_task_role("task phoi hop cua Binh", has_user=True), "support")
test("role all", detect_task_role("tat ca task cua Binh", has_user=True), None)
test("has reviewer query", wants_tasks_with_reviewer("cac task co nguoi kiem tra"), True)
test("not has reviewer", wants_tasks_with_reviewer("task kiem tra cua Khanh"), False)

from app.services.text_utils import is_user_as_reviewer_query
test("user as reviewer query", is_user_as_reviewer_query("co task nao le chi hoang long la nguoi kiem tra khong"), True)


print("\n" + "=" * 60)
print("TEST 2: _find_status - status matching")
print("=" * 60)

test("dang lam", _find_status("task dang lam"), "Đang làm")
test("hoan thanh", _find_status("hoan thanh"), "Hoàn thành")
test("chua lam", _find_status("chua lam"), "Chưa làm")
test("done", _find_status("done"), "Hoàn thành")
test("doing", _find_status("doing"), "Đang làm")
test("todo", _find_status("todo"), "Chưa làm")
test("in progress", _find_status("in progress"), "Đang làm")
test("xong", _find_status("xong"), "Hoàn thành")
test("none", _find_status("hello"), None)


print("\n" + "=" * 60)
print("TEST 3: _route_message - intent routing")
print("=" * 60)

# Greeting
r = run(_route_message("hello"))
test("greeting hello", r[0], "greeting")
r = run(_route_message("xin chao"))
test("greeting xin chao", r[0], "greeting")

# Search by status
r = run(_route_message("Task dang lam"))
test("search status tool", r[0], "search_tasks")
test("search status params", r[1], {"status": "Đang làm"})
test("search status count>0", r[2]["count"] > 0, True)

# Search by name
r = run(_route_message("Task cua Phan Minh Hoang"))
test("search name tool", r[0], "search_tasks")
test("search name params", r[1], {"user": "Phan Minh Hoàng", "role": "pic"})

# Reviewer role
r = run(_route_message("Task kiem tra cua Nguyen Anh Tuan Khanh"))
test("reviewer tool", r[0], "search_tasks")
test("reviewer role param", r[1].get("role"), "reviewer")
test("reviewer user", r[1].get("user"), "Nguyễn Anh Tuấn Khanh")
test("reviewer count", r[2]["count"], 53)

r = run(_route_message("cac task co nguoi kiem tra"))
test("has_reviewer tool", r[0], "search_tasks")
test("has_reviewer param", r[1].get("has_reviewer"), True)
test("has_reviewer count", r[2]["count"], 53)

r = run(_route_message("co task nao le chi hoang long la nguoi kiem tra khong"))
test("LCHL reviewer tool", r[0], "search_tasks")
test("LCHL reviewer role", r[1].get("role"), "reviewer")
test("LCHL reviewer user", r[1].get("user"), "Lê Chí Hoàng Long")
test("LCHL not has_reviewer", r[1].get("has_reviewer"), None)

# Task detail
r = run(_route_message("Chi tiet CO-001"))
test("detail tool", r[0], "get_task_detail")
test("detail task found", r[2].get("task", {}).get("id"), "CO-001")

r = run(_route_message("detail CO-003"))
test("detail english", r[0], "get_task_detail")

r = run(_route_message("Chi tiet XX-999"))
test("detail not found", "error" in r[2], True)

# Subtasks
r = run(_route_message("Subtask cua CO"))
test("subtask tool", r[0], "get_subtasks")
test("subtask count", r[2]["count"], 14)

r = run(_route_message("task con TN"))
test("subtask task con", r[0], "get_subtasks")
test("subtask TN count>0", r[2]["count"] > 0, True)

# Archive
r = run(_route_message("bao cao Phan Minh Hoang"))
test("archive bao cao", r[0], "search_archive")
test("archive has reports", r[2]["count"] > 0, True)

r = run(_route_message("archive log Nguyen Van Cuong"))
test("archive english", r[0], "search_archive")

r = run(_route_message("lich su bao cao"))
test("archive lich su", r[0], "search_archive")

r = run(_route_message("report Phan Minh Hoang"))
test("archive report", r[0], "search_archive")

# Archive with project filter
r = run(_route_message("bao cao du an cao tang"))
test("archive project", r[0], "search_archive")

# Overdue
r = run(_route_message("task qua han"))
test("overdue qua han", r[0], "search_tasks")
test("overdue filter", r[1].get("filter"), "overdue")
test("overdue count>0", r[2]["count"] > 0, True)

r = run(_route_message("task tre han"))
test("overdue tre han", r[0], "search_tasks")

r = run(_route_message("overdue"))
test("overdue english", r[0], "search_tasks")

# Keyword search
r = run(_route_message("tim task training"))
test("keyword training", r[0], "search_tasks")
test("keyword params", "keyword" in r[1], True)
test("keyword count>0", r[2]["count"] > 0, True)

# "Cua toi" with user context
r = run(_route_message("task cua toi", user_name="Phan Minh Hoàng"))
test("cua toi tasks", r[0], "search_tasks")
test("cua toi user", r[1]["user"], "Phan Minh Hoàng")

r = run(_route_message("bao cao cua toi", user_name="Phan Minh Hoàng"))
test("cua toi archive", r[0], "search_archive")

# Ambiguous input
r = run(_route_message("Hoang"))
test("ambiguous clarify", r[0], "clarify")
test("ambiguous has candidates", len(r[2].get("candidates", [])) > 1, True)

r = run(_route_message("xyz abc 123"))
test("random input off topic", r[0], "off_topic")


print("\n" + "=" * 60)
print("TEST 4: MockSheetsService")
print("=" * 60)

s = MockSheetsService()

r = run(s.search_tasks())
test("all tasks > 100", r["count"] > 100, True)

r = run(s.search_tasks(status="Hoàn thành"))
test("done tasks > 0", r["count"] > 0, True)

r = run(s.search_tasks(user="Phan Minh Hoàng"))
test("PMH tasks > 0", r["count"] > 0, True)

r = run(s.search_tasks(keyword="training"))
test("training keyword", r["count"] > 0, True)

r = run(s.get_task_detail("CO-001"))
test("detail has task", "task" in r, True)
test("detail id", r["task"]["id"], "CO-001")

r = run(s.get_task_detail("FAKE-999"))
test("detail not found", "error" in r, True)

r = run(s.get_subtasks("CO"))
test("subtasks CO", r["count"], 14)

r = run(s.get_subtasks("FAKE"))
test("subtasks empty", r["count"], 0)

r = run(s.search_archive(user="Phan Minh Hoàng"))
test("archive PMH", r["count"] > 0, True)

r = run(s.search_archive(user="NOBODY"))
test("archive nobody", r["count"], 0)


print("\n" + "=" * 60)
print("TEST 5: Login / Staff lookup")
print("=" * 60)

test("login valid", get_staff_by_email("hoangpm@bicholder.vn")["name"], "Phan Minh Hoàng")
test("login admin", get_staff_by_email("nosdevai2k@gmail.com")["role"], "admin")
test("login case insensitive", get_staff_by_email("HoangPM@bicholder.vn")["name"], "Phan Minh Hoàng")
test("login invalid", get_staff_by_email("fake@test.com"), None)
test("login empty", get_staff_by_email(""), None)


print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
