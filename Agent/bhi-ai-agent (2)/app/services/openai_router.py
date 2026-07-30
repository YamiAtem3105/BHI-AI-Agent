"""OpenAI tool router: GPT chỉ chọn tool, response format bằng code (không hallucinate)."""
from openai import OpenAI

from app.config import settings
from app.services.openai_compat import completion_limit_kwargs
from app.services.guardrails import (
    HELP_RESPONSE, OFF_TOPIC_RESPONSE, is_greeting, is_help_request, is_in_scope,
)
from app.services.mock_sheets import get_staff_by_name
from app.services.query_context import analyze_query, enrich_params, needs_clarify
from app.services.sheets_factory import sheets
from app.services.text_utils import find_staff, normalize_text
from app.services.tools_schema import OPENAI_TOOLS, SYSTEM_PROMPT_ROUTER

READ_TOOLS = {
    "search_tasks", "search_overdue_tasks", "get_task_detail", "get_subtasks",
    "search_archive", "get_personal_log", "get_hours_summary",
}


def _client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def _resolve_user_params(params: dict, message: str) -> dict:
    """Chuẩn hóa tên nhân sự từ message/GPT — tránh không dấu / inject user thừa."""
    params = dict(params or {})
    norm = normalize_text(message)
    self_query = any(m in norm for m in ("cua toi", "my task", "viec toi"))

    mentioned = find_staff(message)
    if mentioned:
        params["user"] = mentioned
        return params

    if "user" not in params:
        return params

    if self_query:
        return params

    staff = get_staff_by_name(params.get("user", ""))
    if staff and normalize_text(staff["name"]) in norm:
        params["user"] = staff["name"]
        return params

    params.pop("user", None)
    return params


def _apply_permissions(tool_name: str, params: dict, user_name: str, is_privileged: bool) -> dict:
    params = dict(params or {})
    if not is_privileged:
        if tool_name in ("search_tasks", "search_overdue_tasks", "search_archive"):
            params["user"] = user_name
        if tool_name in ("get_personal_log", "get_hours_summary"):
            params["user"] = user_name
    else:
        for key in ("user",):
            if params.get(key) in ("tôi", "toi", "của tôi", "cua toi", "me", "my"):
                params[key] = user_name
    return params


async def execute_tool(tool_name: str, params: dict) -> dict:
    if tool_name == "search_tasks":
        return await sheets.search_tasks(**params)
    if tool_name == "search_overdue_tasks":
        return await sheets.search_overdue_tasks(
            user=params.get("user"),
            role=params.get("role", "pic"),
        )
    if tool_name == "get_task_detail":
        return await sheets.get_task_detail(params["task_id"])
    if tool_name == "get_subtasks":
        return await sheets.get_subtasks(params["parent_id"])
    if tool_name == "search_archive":
        return await sheets.search_archive(**params)
    if tool_name == "get_personal_log":
        return await sheets.get_personal_log(
            params["user"],
            project=params.get("project"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
        )
    if tool_name == "get_hours_summary":
        return await sheets.get_hours_summary(
            params["user"],
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
        )
    return {"error": f"Tool không hỗ trợ: {tool_name}"}


async def route_with_openai(
    message: str,
    user_name: str,
    user_role: str,
    is_privileged: bool,
) -> tuple[str, dict, dict] | tuple[str, None, dict]:
    """Trả (tool_name, params, result) hoặc (response_type, None, greeting_dict)."""
    if is_greeting(message):
        return "greeting", None, {"message": HELP_RESPONSE}
    if is_help_request(message):
        return "greeting", None, {"message": HELP_RESPONSE}
    if not is_in_scope(message):
        return "off_topic", None, {"message": OFF_TOPIC_RESPONSE}

    system = SYSTEM_PROMPT_ROUTER.format(user_name=user_name, user_role=user_role)

    try:
        response = _client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            tools=OPENAI_TOOLS,
            tool_choice="required",
            temperature=0,
            **completion_limit_kwargs(settings.openai_model, 256),
        )
    except Exception as e:
        return "error", None, {"error": f"Lỗi OpenAI API: {e}"}

    choice = response.choices[0]
    tool_calls = choice.message.tool_calls
    if not tool_calls:
        return "off_topic", None, {"message": OFF_TOPIC_RESPONSE}

    call = tool_calls[0]
    tool_name = call.function.name
    import json
    try:
        params = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        return "error", None, {"error": "GPT trả về tham số tool không hợp lệ."}

    if tool_name not in READ_TOOLS:
        return "error", None, {"error": f"Tool '{tool_name}' chưa được bật trên web chat."}

    ctx = analyze_query(message, logged_in_user=user_name)
    if tool_name in READ_TOOLS:
        params = _resolve_user_params(params, message)
    params = enrich_params(tool_name, params, ctx)
    if tool_name == "search_tasks":
        clarify = needs_clarify(ctx, params)
        if clarify:
            return "clarify", {}, clarify
    params = _apply_permissions(tool_name, params, user_name, is_privileged)
    result = await execute_tool(tool_name, params)
    return tool_name, params, result


# Tool name từ OpenAI → tên hiển thị / format trong chat API
TOOL_DISPLAY_NAMES = {
    "get_hours_summary": "hours_summary",
    "get_personal_log": "personal_log",
}


def normalize_tool_name(tool_name: str) -> str:
    return TOOL_DISPLAY_NAMES.get(tool_name, tool_name)


POLISH_SYSTEM_PROMPT = """Bạn là trợ lý QLXD thân thiện, nói tiếng Việt tự nhiên.

NHIỆM VỤ: Diễn đạt lại thông tin được cung cấp — KHÔNG thêm, bớt hay đổi số liệu/tên/ngày/task ID.

Quy tắc:
- Giữ nguyên mọi con số, tên người, mã task (CO-001...), ngày tháng
- Giữ emoji và cấu trúc danh sách
- Dùng giọng thân thiện: "Mình thấy...", "Bạn có...", "Hiện tại..."
- Ngắn gọn, dễ đọc trên chat
- KHÔNG bịa thêm task hay báo cáo không có trong dữ liệu"""


def stream_polish_response(message: str, facts: str):
    """Stream câu trả lời thân thiện từ OpenAI (giữ nguyên facts)."""
    if not settings.openai_api_key:
        chunk_size = 24
        for i in range(0, len(facts), chunk_size):
            yield facts[i:i + chunk_size]
        return

    try:
        stream = _client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": POLISH_SYSTEM_PROMPT},
                {"role": "user", "content": f"Câu hỏi: {message}\n\nDữ liệu (giữ nguyên số liệu):\n{facts}"},
            ],
            stream=True,
            temperature=0.2,
            **completion_limit_kwargs(settings.openai_model, 1500),
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception:
        chunk_size = 24
        for i in range(0, len(facts), chunk_size):
            yield facts[i:i + chunk_size]
