"""Live test GPT routing — kiểm tra tool chọn đúng và không bịa data."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api.chat import _format_response, _route_message
from app.config import settings
from app.services.mock_sheets import MockSheetsService

sheets = MockSheetsService()
passed = failed = 0
issues = []


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        issues.append(f"{name}: {detail}")


async def main():
    if not settings.openai_api_key:
        print("SKIP: OPENAI_API_KEY chưa cấu hình")
        sys.exit(0)

    print("=" * 60)
    print(f"GPT LIVE TEST — model={settings.openai_model}")
    print("=" * 60)

    cases = [
        ("Task cua Phan Minh Hoang", "search_tasks", {"user": "Phan Minh Hoàng"}),
        ("task dang lam", "search_tasks", {"status": "Đang làm"}),
        ("bao cao Nguyen Van Cuong", "search_archive", {"user": "Nguyễn Văn Cường"}),
        ("chi tiet CO-001", "get_task_detail", {"task_id": "CO-001"}),
        ("Subtask cua CO", "get_subtasks", {"parent_id": "CO"}),
        ("task qua han", "search_tasks", {"filter": "overdue"}),
        ("gio lam cua Do Thi Bich Hang", "get_hours_summary", {"user": "Đỗ Thị Bích Hằng"}),
        ("thoi tiet hom nay", "off_topic", None),
        ("ke cho toi nghe", "off_topic", None),
    ]

    for msg, exp_tool, exp_params in cases:
        tool, params, result = await _route_message(
            msg, user_name="Phan Minh Hoàng", is_privileged=True,
        )
        check(f"tool[{msg[:35]}]", tool == exp_tool, f"got={tool}")
        if exp_params:
            for k, v in exp_params.items():
                got = (params or {}).get(k)
                check(f"param.{k}[{msg[:20]}]", got == v, f"exp={v!r} got={got!r}")
        if tool == "get_task_detail" and exp_params:
            tid = (result.get("task") or {}).get("id")
            check(f"real_task[{msg[:20]}]", tid == exp_params["task_id"], f"got={tid}")
        print(f"  OK  {msg!r} -> {tool} {params}")

    # Fake task — không được bịa task
    tool, params, result = await _route_message("chi tiet XX-999")
    check("fake_tool", tool == "get_task_detail", f"got={tool}")
    check("fake_no_invent", "error" in result or not result.get("task"), str(result)[:100])

    # Count phải khớp MockSheets
    tool, params, result = await _route_message("Task cua Phan Minh Hoang")
    direct = await sheets.search_tasks(user="Phan Minh Hoàng", role="pic")
    check(
        "count_match_PMH",
        result.get("count") == direct["count"],
        f"gpt={result.get('count')} direct={direct['count']}",
    )

    # Text response chỉ từ data thật
    tool, params, result = await _route_message("chi tiet CO-001")
    text = _format_response(tool, result, "chi tiet CO-001", params)
    real = await sheets.get_task_detail("CO-001")
    t = real["task"]
    check("text_has_real_name", t["name"] in text, "missing name")
    check("text_has_real_id", t["id"] in text, "missing id")

    print("\n" + "=" * 60)
    print(f"RESULT: {passed} passed, {failed} failed")
    if issues:
        print("\nISSUES:")
        for i in issues:
            print("  -", i)
    print("=" * 60)
    sys.exit(1 if failed else 0)


asyncio.run(main())
