"""Unit tests for chat guardrails."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.guardrails import (
    HELP_RESPONSE,
    OFF_TOPIC_RESPONSE,
    is_greeting,
    is_help_request,
    is_in_scope,
)

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


print("=" * 60)
print("TEST: Guardrails")
print("=" * 60)

test("greeting xin chao", is_greeting("xin chào"), True)
test("greeting hello", is_greeting("hello"), True)
test("not greeting", is_greeting("task dang lam"), False)

test("help request", is_help_request("bạn giúp gì được"), True)
test("not help", is_help_request("task cua toi"), False)

test("in scope task", is_in_scope("task dang lam"), True)
test("in scope task id", is_in_scope("chi tiet CO-001"), True)
test("in scope staff", is_in_scope("bao cao Phan Minh Hoang"), True)
test("in scope no accent dang lam", is_in_scope("task dang lam"), True)
test("in scope mixed accent", is_in_scope("task đang lam"), True)
test("in scope partial staff", is_in_scope("Hoang"), True)
test("in scope chi tiet no accent", is_in_scope("chi tiet co-001"), True)
test("in scope performance", is_in_scope("performance cua Phan Minh Hoang"), True)
test("in scope performance short", is_in_scope("performance co"), True)
test("off topic weather", is_in_scope("thoi tiet hom nay the nao"), False)
test("off topic joke", is_in_scope("ke cho toi nghe mot cau chuyen vui"), False)

test("off topic response text", OFF_TOPIC_RESPONSE.startswith("⚠️"), True)
test("help response text", "Task" in HELP_RESPONSE, True)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
