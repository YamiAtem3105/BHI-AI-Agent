"""Test ĐỘ PHỦ tìm kiếm: đảm bảo mọi truy vấn của user trả về ĐỦ data so với nguồn.

So sánh kết quả qua _route_message / MockSheetsService với việc đếm trực tiếp
trên ke_hoach.json + archive_log.json. Mục tiêu: không bỏ sót nhân sự/trạng thái/zone.
"""
import os
import sys
import json
import asyncio
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.chat import _route_message
from app.services.text_utils import find_staff
from app.services.mock_sheets import MockSheetsService

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
KE_HOACH = json.load(open(os.path.join(DATA, "ke_hoach.json"), encoding="utf-8"))
ARCHIVE = json.load(open(os.path.join(DATA, "archive_log.json"), encoding="utf-8"))
STAFF = json.load(open(os.path.join(DATA, "staff.json"), encoding="utf-8"))

sheets = MockSheetsService()
passed = failed = 0
gaps = []


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        gaps.append(f"{label} | {detail}")
        print(f"  FAIL {label} | {detail}")


def run(c):
    return asyncio.run(c)


def _name_in_field(field, name):
    return any(name == p.strip() for p in str(field or "").split(","))


# ---- 1. Mọi nhân sự xuất hiện trong KẾ HOẠCH phải search ra đủ task ----
print("=" * 64)
print("1. Độ phủ search_tasks theo từng nhân sự (KẾ HOẠCH)")
print("=" * 64)
plan_names = set()
for t in KE_HOACH:
    for f in ("pic", "support", "reviewer"):
        for p in str(t.get(f) or "").split(","):
            if p.strip():
                plan_names.add(p.strip())

for name in sorted(plan_names):
    expected = sum(1 for t in KE_HOACH
                   if _name_in_field(t.get("pic"), name)
                   or _name_in_field(t.get("support"), name)
                   or _name_in_field(t.get("reviewer"), name))
    got = run(sheets.search_tasks(user=name))["count"]
    check(f"1.{name}", got >= expected, f"expected>={expected}, got={got}")

# ---- 2. Mọi user trong ARCHIVE phải search ra đủ báo cáo ----
print("=" * 64)
print("2. Độ phủ search_archive theo từng nhân sự (ARCHIVE)")
print("=" * 64)
arch_counter = Counter(str(r.get("user") or "").strip() for r in ARCHIVE)
for name, expected in arch_counter.items():
    if not name:
        continue
    got = run(sheets.search_archive(user=name))["count"]
    check(f"2.{name}", got == expected, f"expected={expected}, got={got}")

# ---- 3. Mọi trạng thái phải lọc đúng số lượng ----
print("=" * 64)
print("3. Độ phủ theo trạng thái")
print("=" * 64)
for status in ["Hoàn thành", "Đang làm", "Chưa làm"]:
    expected = sum(1 for t in KE_HOACH if str(t.get("status") or "").strip() == status)
    got = run(sheets.search_tasks(status=status))["count"]
    check(f"3.{status}", got == expected, f"expected={expected}, got={got}")

# ---- 4. find_staff phải nhận diện được TẤT CẢ nhân sự (đủ dấu & không dấu) ----
print("=" * 64)
print("4. find_staff nhận diện mọi nhân sự (có dấu + không dấu)")
print("=" * 64)
import unicodedata


def no_accent(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).lower().replace("đ", "d")


for s in STAFF:
    name = s["name"]
    if name == "Admin":
        continue
    check(f"4a.{name} (có dấu)", find_staff(name) == name, f"got={find_staff(name)}")
    na = no_accent(name)
    check(f"4b.{name} (không dấu)", find_staff(na) == name, f"input={na} got={find_staff(na)}")

# ---- 5. Câu hỏi tự nhiên end-to-end qua _route_message ----
print("=" * 64)
print("5. Câu hỏi tự nhiên (end-to-end routing)")
print("=" * 64)
cases = [
    ("Task của Phan Minh Hoàng", "search_tasks"),
    ("task dang lam", "search_tasks"),
    ("task hoan thanh", "search_tasks"),
    ("báo cáo của Nguyễn Văn Cường", "search_archive"),
    ("task qua han", "search_tasks"),
    ("Chi tiết CO-001", "get_task_detail"),
    ("Subtask của CO", "get_subtasks"),
]
for q, tool in cases:
    r = run(_route_message(q))
    check(f"5.[{q}] tool", r[0] == tool, f"got={r[0]}")
    if r[0] in ("search_tasks", "search_archive"):
        check(f"5.[{q}] có data", r[2]["count"] > 0, f"count={r[2]['count']}")

# ---- 6. Tổng tài nguyên: search rỗng phải trả về toàn bộ task ----
print("=" * 64)
print("6. Tổng quát")
print("=" * 64)
all_tasks = run(sheets.search_tasks())["count"]
non_empty = sum(1 for t in KE_HOACH if str(t.get("id") or "").strip())
check("6.1 search rỗng trả toàn bộ task", all_tasks == non_empty, f"got={all_tasks}, data={non_empty}")
all_arch = run(sheets.search_archive())["count"]
check("6.2 archive rỗng trả toàn bộ", all_arch == len(ARCHIVE), f"got={all_arch}, data={len(ARCHIVE)}")

print("\n" + "=" * 64)
print(f"KẾT QUẢ: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 64)
if gaps:
    print("\nLỖ HỔNG TÌM KIẾM:")
    for g in gaps:
        print("  -", g)
    sys.exit(1)
print("✅ Không có lỗ hổng — mọi truy vấn trả về đủ data.")
