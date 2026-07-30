"""Test luồng hỏi performance + follow-up hội thoại."""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.chat import _format_response, _route_message
from app.services.chat_session import expand_followup, get_session, remember_turn
from app.services.query_context import analyze_query, is_work_pool_query

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} | {detail}")


def run(coro):
    return asyncio.run(coro)


print("=" * 60)
print("PERFORMANCE + FOLLOW-UP CHAT")
print("=" * 60)

email = "test-admin@bicholder.vn"

ctx = analyze_query("performnace của Hoàng Long đang ntn")
check("typo performance detected", is_work_pool_query(ctx))
check("Hoàng Long resolved", ctx.user == "Lê Chí Hoàng Long", f"got={ctx.user}")

r = run(_route_message("performnace của Hoàng Long đang ntn", user_name="Admin", is_privileged=True))
check("route PMH performance", r[0] == "work_pool_profile", f"got={r[0]}")
check("LCHL pool", r[2].get("employee") == "Lê Chí Hoàng Long")

remember_turn(email, r[0], r[1])

expanded = expand_followup("của Phan Minh Hoàng thì sao", email, "Admin")
check("follow-up expand PMH", "Phan Minh Hoàng" in expanded and "hiệu quả" in expanded, expanded)

r2 = run(_route_message(expanded, user_name="Admin", is_privileged=True))
check("follow-up PMH work pool", r2[0] == "work_pool_profile", f"got={r2[0]}")
remember_turn(email, r2[0], r2[1])

expanded2 = expand_followup("performance cơ", email, "Admin")
check("perf co expand", expanded2.startswith("hiệu quả"), expanded2)

r3 = run(_route_message(expanded2, user_name="Admin", is_privileged=True))
check("perf co not off_topic", r3[0] != "off_topic", f"got={r3[0]}")
check("perf co work pool", r3[0] == "work_pool_profile", f"got={r3[0]}")

text = _format_response(r3[0], r3[2], expanded2, r3[1])
check("format has 3P", "3P" in text or "3p" in text.lower())
check("format has năng lực", "năng lực" in text.lower() or "Năng lực" in text)

sess = get_session(email)
check("session remembers user", sess and sess.get("last_user") == "Phan Minh Hoàng")

print("\n" + "=" * 60)
print(f"RESULT: {passed} passed, {failed} failed")
print("=" * 60)
# Chỉ thoát mã lỗi khi chạy trực tiếp (python tests/...); tránh làm vỡ pytest collection.
if __name__ == "__main__":
    sys.exit(1 if failed else 0)
