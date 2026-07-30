"""Test phân tích ngữ cảnh câu hỏi và enrich params."""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.chat import _format_response, _route_message
from app.services.query_context import analyze_query, enrich_params, is_compound_work_query, is_work_pool_query

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL {name} | {detail}")


def run(coro):
    return asyncio.run(coro)


print("=" * 60)
print("QUERY CONTEXT — phân tích field")
print("=" * 60)

ctx = analyze_query("co task nao le chi hoang long la nguoi kiem tra khong")
check("reviewer role", ctx.role == "reviewer")
check("reviewer user", ctx.user == "Lê Chí Hoàng Long")
check("not has_reviewer", not ctx.has_reviewer)

ctx = analyze_query("cac task co nguoi kiem tra")
check("has_reviewer flag", ctx.has_reviewer)
check("no user", ctx.user is None)

ctx = analyze_query("task dang lam")
check("status dang lam", ctx.status == "Đang làm")

ctx = analyze_query("bao cao du an cao tang Nguyen Van Cuong")
check("archive project", ctx.project == "cao tầng")
check("archive user", ctx.user == "Nguyễn Văn Cường")

ctx = analyze_query("Phan Minh Hoang lam bao nhieu gio tuan nay")
check("hours query", ctx.wants_hours)
check("user PMH", ctx.user == "Phan Minh Hoàng")
check("date range", ctx.date_from is not None and ctx.date_to is not None)

ctx = analyze_query(
    "Phan Minh Hoang lam bao nhieu gio va hoan thanh bao nhieu task",
)
check("compound hours+done", is_compound_work_query(ctx))
check("compound completed", ctx.wants_completed_tasks)

ctx = analyze_query("gio lam cua toi", logged_in_user="Phan Minh Hoàng")
check("self query user", ctx.user == "Phan Minh Hoàng")
check("self flag", ctx.is_self_query)

params = enrich_params("search_tasks", {}, analyze_query("task training dang lam"))
check("enrich keyword", params.get("keyword") == "training")
check("enrich status", params.get("status") == "Đang làm")

print("\n" + "=" * 60)
print("QUERY CONTEXT — routing end-to-end")
print("=" * 60)

r = run(_route_message(
    "Phan Minh Hoang lam bao nhieu gio va hoan thanh bao nhieu task",
    user_name="Admin", is_privileged=True,
))
check("compound tool", r[0] == "work_summary", f"got={r[0]}")
check("compound user", r[1].get("user") == "Phan Minh Hoàng")
text = _format_response(r[0], r[2], "compound", r[1])
check("format has hours", "h" in text.lower() or "giờ" in text.lower())
check("format has task count", "task" in text.lower())

r = run(_route_message("Le Chi Hoang Long tuan nay lam bao nhieu gio, da lam bao nhieu task"))
check("LCHL compound", r[0] == "work_summary")
check("LCHL user", r[1].get("user") == "Lê Chí Hoàng Long")
check("LCHL has dates", r[1].get("date_from") is not None)

r = run(_route_message("Le Chi Hoang Long co bao nhieu task qua han"))
check("LCHL overdue tool", r[0] == "search_tasks")
check("LCHL overdue user", r[1].get("user") == "Lê Chí Hoàng Long")
check("LCHL overdue role pic", r[1].get("role") == "pic")
check("LCHL overdue count", r[2]["count"] == 7, f"got={r[2]['count']}")

r = run(_route_message(
    "Phan Minh Hoang lam bao nhieu gio va co bao nhieu task qua han tuan nay",
))
check("PMH overdue+hours compound", r[0] == "work_summary")
check("PMH overdue+hours flag", r[1].get("is_overdue") is True)
text = _format_response(r[0], r[2], "pmh compound", r[1])
check("PMH format overdue", "quá hạn" in text.lower() or "qua han" in text.lower())

ctx = analyze_query("hiệu quả công việc của Phan Minh Hoàng")
check("work pool query flag", is_work_pool_query(ctx))
check("work pool user PMH", ctx.user == "Phan Minh Hoàng")

r = run(_route_message("hiệu quả công việc của Phan Minh Hoàng", user_name="Admin", is_privileged=True))
check("work pool tool", r[0] == "work_pool_profile", f"got={r[0]}")
check("work pool employee", r[2].get("employee") == "Phan Minh Hoàng")
text = _format_response(r[0], r[2], "hieu qua", r[1])
check("format efficiency score", "hiệu quả" in text.lower())
check("format competency", "năng lực" in text.lower())
check("format 3p", "3p" in text.lower())

r = run(_route_message("nang luc cua toi", user_name="Phan Minh Hoàng", is_privileged=False))
check("member self work pool", r[0] == "work_pool_profile")
check("member self name", r[2].get("employee") == "Phan Minh Hoàng")

print("\n" + "=" * 60)
print(f"RESULT: {passed} passed, {failed} failed")
print("=" * 60)
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
