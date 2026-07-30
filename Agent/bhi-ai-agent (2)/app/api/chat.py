"""Chat API that works without Gemini - uses keyword matching to route to tools."""
import json
import re
import os
import uuid
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from app.config import settings
from app.services.mock_sheets import get_staff_by_email
from app.services.sheets_factory import sheets
from app.services.passwords import verify_password
from app.services.auth_token import create_session_token, get_current_user, get_user_query_or_header
from app.services.guardrails import HELP_RESPONSE, OFF_TOPIC_RESPONSE, is_greeting, is_help_request, is_in_scope
from app.services.openai_router import normalize_tool_name, route_with_openai
from app.services.query_context import analyze_query, enrich_params, is_compound_work_query, is_work_pool_query, needs_clarify
from app.services.chat_session import (
    clear_pending_write, expand_followup, get_pending_write, remember_turn, set_pending_write,
)
from app.services.rbac import has_permission, normalize_role
from app.services.sheet_writer import SheetWriter
from app.services.work_pool_service import get_employee_work_pool
from app.services.write_intent import parse_write_intent
from app.services.text_utils import (
    STAFF, detect_task_role, find_staff, find_staff_candidates, find_status,
    is_user_as_reviewer_query, normalize_text, parse_relative_date_range, wants_tasks_with_reviewer,
)
from app.services.mongo_service import get_chat_history, save_chat_message

from openai import AsyncOpenAI
import os

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()
writer = SheetWriter()

_CONFIRM_WORDS = ("ok", "okê", "oke", "xác nhận", "xac nhan", "đồng ý", "dong y", "yes", "có", "co")
_CANCEL_WORDS = ("hủy", "huy", "cancel", "không", "khong", "no")

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def _export_tasks_excel(tasks: list) -> str:
    """Export tasks to Excel, return filename."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Tasks"
    headers = ["ID", "Tên công việc", "Ngày bắt đầu", "Ngày kết thúc", "Thời lượng", "Trạng thái", "Thực hiện", "Phối hợp", "Kiểm tra", "Ghi chú"]
    ws.append(headers)
    for t in tasks:
        ws.append([t.get("id"), t.get("name"), t.get("start_date"), t.get("end_date"), t.get("duration_days"), t.get("status"), t.get("pic"), t.get("support"), t.get("reviewer"), t.get("note")])
    fname = f"tasks_{uuid.uuid4().hex[:8]}.xlsx"
    wb.save(os.path.join(EXPORT_DIR, fname))
    return fname


def _export_reports_excel(reports: list) -> str:
    """Export reports to Excel, return filename."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Reports"
    headers = ["Ngày", "Nhân sự", "Vai trò", "Dự án", "Nội dung", "Giờ", "Trạng thái", "Deadline", "Đánh giá", "Ghi chú"]
    ws.append(headers)
    for r in reports:
        ws.append([r.get("report_date", "")[:10], r.get("user"), r.get("role"), r.get("project"), r.get("task_content"), r.get("hours"), r.get("status"), r.get("deadline"), r.get("evaluation"), r.get("report_note")])
    fname = f"reports_{uuid.uuid4().hex[:8]}.xlsx"
    wb.save(os.path.join(EXPORT_DIR, fname))
    return fname


@router.get("/api/export/{filename}")
async def download_export(filename: str, user: dict = Depends(get_user_query_or_header)):
    # Chống path traversal: chỉ cho phép tên file thuần, phải nằm trong EXPORT_DIR
    if "/" in filename or "\\" in filename or os.path.isabs(filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    path = os.path.realpath(os.path.join(EXPORT_DIR, filename))
    if os.path.commonpath([path, os.path.realpath(EXPORT_DIR)]) != os.path.realpath(EXPORT_DIR):
        raise HTTPException(status_code=400, detail="Tên file không hợp lệ.")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.post("/api/login")
async def login(request: Request):
    body = await request.json()
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    if not email or not password:
        return {"success": False, "error": "Vui lòng nhập email và mật khẩu."}
    staff = get_staff_by_email(email)
    if not staff or not staff.get("password_hash") or not verify_password(password, staff["password_hash"]):
        return {"success": False, "error": "Email hoặc mật khẩu không đúng."}
    role = staff.get("role", "member")
    token = create_session_token(staff["email"], role, staff["name"])
    return {"success": True, "name": staff["name"], "email": staff["email"], "role": role, "token": token}

def _find_status(msg: str) -> str | None:
    return find_status(msg)


def _suggest_similar(msg: str) -> str:
    """Generate suggestions when no results found."""
    suggestions = []
    msg_na = normalize_text(msg)    

    for name in STAFF:
        name_na = normalize_text(name)
        for word in msg_na.split():
            if len(word) >= 3 and word in name_na:
                suggestions.append(f"👤 Bạn có ý \"{name}\"?")
                break

    if any(w in msg_na for w in ["tre", "late", "qua han"]):
        suggestions.append("💡 Thử: \"Task đang làm\" rồi kiểm tra deadline")

    if not suggestions:
        suggestions = [
            "💡 Thử gõ tên đầy đủ có dấu: VD \"Phan Minh Hoàng\"",
            "💡 Hoặc hỏi: \"Task đang làm\", \"Task hoàn thành\"",
            "💡 Hoặc: \"Chi tiết CO-001\", \"Subtask của CO\"",
        ]

    return "\n".join(suggestions)


async def _chat_context(user: dict) -> tuple[str, bool, str]:
    staff = get_staff_by_email(user["email"])
    user_name = staff["name"] if staff else user.get("name")
    is_privileged = user.get("role") in ("super_admin", "admin", "manager")
    user_role = user.get("role", "member")
    return user_name, is_privileged, user_role


def _detect_sheet_change(msg: str) -> str | None:
    """Phát hiện ý muốn đổi sheet đích: '2' | '1' | None."""
    if any(k in msg for k in ("sheet 2", "sheet2", "sheet hai", "masterplan", "master plan", "qlxd")):
        return "2"
    if any(k in msg for k in ("sheet 1", "sheet1", "sheet mot", "sheet chinh", "sheet chính")):
        return "1"
    return None


def _create_preview(params: dict) -> str:
    task = (params.get("tasks") or [{}])[0]
    label = "Sheet 2 (Masterplan)" if str(params.get("source")) == "2" else "Sheet 1"
    return (
        f"🆕 Tạo task mới:\n• Tên: {task.get('name', '')}\n"
        f"• Thực hiện (PIC): {task.get('pic', '')}\n"
        f"• Deadline: {task.get('end_date') or '—'}\n• Ghi vào: {label}\n\n"
        f"✅ Gõ 'ok' xác nhận | ❌ 'hủy'"
    )


async def _handle_write_flow(message: str, user_name: str, user_role: str, user_email: str):
    """Tạo/sửa task từ web chat với xác nhận 'ok/hủy'. Trả tuple response hoặc None."""
    if not user_email:
        return None  # cần email để giữ trạng thái pending
    msg = message.strip().lower()
    pending = get_pending_write(user_email)

    # Đang chờ xác nhận
    if pending:
        # Đổi sheet đích trước khi xác nhận: "vào sheet 2", "ghi sheet 1"...
        sheet_sel = _detect_sheet_change(msg)
        if (sheet_sel and pending.get("tool") == "create_task"
                and msg not in _CONFIRM_WORDS and msg not in _CANCEL_WORDS):
            pending["params"]["source"] = sheet_sel
            set_pending_write(user_email, pending)
            return _create_preview(pending["params"]), None, pending["params"], {}, "confirm_write"
        if msg in _CONFIRM_WORDS:
            result = await writer.execute(pending["tool"], pending["params"])
            clear_pending_write(user_email)
            if result.get("error"):
                return f"❌ Lỗi ghi: {result['error']}", None, pending["params"], result, "error"
            text = f"✅ Đã thực hiện!\n{result.get('message', '')}"
            return text, None, pending["params"], result, "write_done"
        if msg in _CANCEL_WORDS:
            clear_pending_write(user_email)
            return "❌ Đã hủy thao tác.", None, {}, {}, "write_cancelled"
        return (
            "⏳ Đang chờ bạn xác nhận thao tác trước đó. Gõ **ok** để thực hiện hoặc **hủy** để bỏ.",
            None, {}, {}, "confirm_write",
        )

    # Phát hiện ý định ghi mới
    write = parse_write_intent(message, user_name)
    if write is None:
        return None
    if not write.get("tool"):  # gợi ý thiếu tên task
        return write["preview"], None, {}, {}, "clarify"
    if not has_permission(normalize_role(user_role), "data.write.task"):
        return (
            "⚠️ Tài khoản của bạn không có quyền tạo/sửa task. Liên hệ quản lý nhé.",
            None, {}, {}, "error",
        )
    set_pending_write(user_email, {"tool": write["tool"], "params": write["params"]})
    return write["preview"], None, write["params"], {}, "confirm_write"

async def _rewrite_query_with_history(message: str, history: list) -> str:
    """Sử dụng 5 câu lịch sử chat từ MongoDB để làm sạch và bổ nghĩa cho câu hỏi mới."""
    print("\n================ [DEBUG REWRITER START] ================")
    print(f"-> Câu hỏi GỐC của User: '{message}'")

    if not history:
        print("-> Thông báo: Không có lịch sử chat (Phiên mới). Giữ nguyên câu hỏi gốc.")
        print("================ [DEBUG REWRITER END] ==================\n")
        return message

    # Đảo ngược lịch sử để câu cũ lên trước, câu mới xuống sau cho đúng mạch thời gian
    ordered_history = list(reversed(history))

    # Xây dựng mạch hội thoại làm ngữ cảnh cho LLM
    conversation_context = ""
    for msg in ordered_history:
        role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
        conversation_context += f"{role_label}: {msg['content']}\n"
    
    # Prompt 
    system_prompt = (
        "Bạn là một trợ lý ảo chuyên xử lý và tinh chỉnh câu lệnh (Query Rewriter) cho hệ thống quản lý công việc.\n"
        "Nhiệm vụ của bạn là đọc lịch sử chat (từ cũ đến mới) để bổ sung thông tin bị khuyết (Mã task, tên nhân sự, dự án) vào câu hỏi hiện tại của User.\n\n"
        
        "🚨 QUY TẮC RỪNG NGHIÊM NGẶT:\n"
        "1. KHÔNG ĐƯỢC tự ý trả lời câu hỏi, KHÔNG thêm các câu lịch sự như 'Câu hỏi của bạn đã...', 'Bạn muốn làm gì...'.\n"
        "2. ĐẶC BIỆT CHÚ Ý CÁC CÂU LỆNH CẬP NHẬT/THAY ĐỔI TRẠNG THÁI:\n"
        "   - Nếu câu hiện tại của User chứa các từ khóa hành động (như: 'xong rồi', 'hoàn thành rồi', 'đang làm', 'chuyển sang đang làm', 'hủy bỏ').\n"
        "   - Hãy nhìn vào lịch sử ngay trước đó xem họ đang xem hoặc nhắc đến mã task nào (Ví dụ: TN-001.4, CO-002...).\n"
        "   - Viết lại thành một câu lệnh đầy đủ cấu trúc hành động, ví dụ: 'Cập nhật task TN-001.4 thành Hoàn thành' hoặc 'Task TN-001.4 xong rồi'.\n"
        "3. Nếu câu hỏi hiện tại đã rõ nghĩa hoặc không có thông tin liên quan trong lịch sử, hãy trả về chính xác câu hỏi gốc của user, tuyệt đối không chế thêm chữ."

        "🧠 NGUYÊN TẮC SUY LUẬN NGỮ CẢNH:\n"
        "1. Xác định hành động ẩn sâu: Khi người dùng nói những câu cực ngắn như 'hoàn thành rồi', 'xong rồi', 'chuyển sang đang làm', bản chất họ đang muốn thay đổi trạng thái của công việc được nhắc đến ngay trước đó.\n"
        "2. Nhặt thực thể khuyết: Hãy tìm xem ở các lượt chat ngay trước đó, hệ thống hoặc người dùng đang hiển thị/nhắc đến mã Task cụ thể nào (Ví dụ: TN-001.4, CO-002...). Hãy tự động nhặt mã Task đó gài vào câu hiện tại để làm rõ nghĩa.\n"
        "3. Giữ nguyên bản chất câu lệnh: Tuyệt đối KHÔNG tự trả lời câu hỏi, KHÔNG thêm bớt cảm xúc cá nhân hay thêm các câu lịch sự dẫn chuyện (Ví dụ không viết kiểu: 'Bạn muốn cập nhật task...', 'Câu hỏi của bạn là...'). Chỉ trả về duy nhất câu lệnh sau khi đã làm rõ bối cảnh.\n"
        "4. Nếu câu hiện tại đã quá rõ nghĩa hoặc lịch sử không có gì liên quan, hãy giữ nguyên câu gốc của user.\n\n"
        
        "🎯 VÍ DỤ MẪU ĐỂ BẠN HỌC TƯ DUY:\n"
        "- Lịch sử: Hệ thống vừa hiển thị chi tiết task 'TN-001.4'\n"
        "  User gõ: 'hoàn thành rồi'\n"
        "  -> Viết lại: 'Cập nhật trạng thái task TN-001.4 thành Hoàn thành'\n\n"
        
        "- Lịch sử: User hỏi 'Task của Phan Minh Hoàng'\n"
        "  User gõ: 'Ủa sao nhiều việc quá vậy ông?'\n"
        "  -> Viết lại: 'Tại sao Phan Minh Hoàng lại có nhiều task như vậy?'\n\n"
        
        "- Lịch sử: Trống\n"
        "  User gõ: 'hello'\n"
        "  -> Viết lại: 'hello'"    
    )
    

    try:
        # Gọi mô hình rẻ và nhanh nhất (gpt-4o-mini hoặc tương đương)
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"--- LỊCH SỬ HỘI THOẠI ---\n{conversation_context}\n--- CÂU HỎI MỚI CỦA USER ---\n{message}"}
            ],
            temperature=0.0, # Để lặp đi lặp lại kết quả deterministic nhất
            max_tokens=150
        )
        rewritten = response.choices[0].message.content.strip()
        print(f"--- [DEBUG REWRITER] --- Gốc: '{message}' -> Viết lại: '{rewritten}'")
        return rewritten
    except Exception as e:
        print(f"--- [DEBUG REWRITER ERROR] --- Lỗi khi viết lại câu hỏi: {e}")
        return message # Nếu lỗi API thì fallback dùng luôn câu gốc của user cho an toàn


async def _build_chat_response(message: str, user_name: str, is_privileged: bool, user_role: str, user_email: str = "", history: list = None):
    write_resp = await _handle_write_flow(message, user_name, user_role, user_email)
    if write_resp is not None:
        return write_resp

    ai_rewritten_message = await _rewrite_query_with_history(message, history)
    
    routed_message = expand_followup(ai_rewritten_message, user_email, user_name)

    tool_name, params, result = await _route_message(
        routed_message, user_name, is_privileged, user_role=user_role,
    )
    remember_turn(user_email, tool_name, params)
    response_text = await _format_response(tool_name, result, routed_message, params, history=history)
    display_tool = tool_name if tool_name not in ("greeting", "off_topic", "error", "clarify") else None
    return response_text, display_tool, params, result, tool_name


@router.post("/api/chat")
async def chat(request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    message = body.get("message", "").strip()
    
    if not message:
        return {"response": "Bạn gõ giúp mình câu hỏi nhé 🙂", "tool": None, "data": None}
    
    user_name, is_privileged, user_role = await _chat_context(user)
    response_text, display_tool, params, result, tool_name = await _build_chat_response(
        message, user_name, is_privileged, user_role, user.get("email", ""),
    )
    return {
        "response": response_text, "tool": display_tool, "params": params, "data": result,
        "awaiting_confirm": tool_name == "confirm_write",
    }


@router.post("/api/chat/stream")
async def chat_stream(request: Request, user: dict = Depends(get_current_user)):
    """SSE streaming — tool routing deterministic, OpenAI stream chỉ polish văn phong."""
    body = await request.json()
    message = body.get("message", "").strip()

    if not message:
        async def empty_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Bạn gõ giúp mình câu hỏi nhé 🙂'})}\n\n"
        return StreamingResponse(empty_gen(), media_type="text/event-stream")

    # 1. SESSION ID 
    session_id = body.get("session_id", "").strip()
    is_new_session = False
    
    if not session_id:
        # Lấy email user làm gốc, ví dụ: "session_tuan@gmail.com"
        user_email = user.get("email", "anonymous").split("@")[0]
        session_id = f"session_{user_email}_test"

    # 2. GỌI MONGO ĐỂ ĐỌC LỊCH SỬ VÀ IN RA TERMINAL DEBUG
    history_messages = await get_chat_history(session_id, limit=10)
    print(f"\n===== [MONITOR MONGO] =====")
    print(f"-> Session ID hiện tại: {session_id} ({'PHIÊN MỚI TẠO' if is_new_session else 'PHIÊN CŨ'})")
    print(f"-> Lịch sử bốc từ DB: {history_messages}")
    print(f"===========================\n")

    
    # 3. LƯU TIN NHẮN CỦA USER XUỐNG MONGO
    await save_chat_message(session_id=session_id, role="user", content=message)

    user_name, is_privileged, user_role = await _chat_context(user)

    async def event_generator():
        response_text, display_tool, params, result, tool_name = await _build_chat_response(
            message, user_name, is_privileged, user_role, user.get("email", ""), history=history_messages
        )

        # 4. LƯU TIN NHẮN CỦA AI XUỐNG MONGO
        await save_chat_message(session_id=session_id, role="assistant", content=response_text)

        # 5. TRẢ VỀ SESSION_ID 
        meta = {
            "type": "meta", 
            "tool": display_tool, 
            "params": params,
            "session_id": session_id, # 
            "awaiting_confirm": tool_name == "confirm_write",
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        chunk_size = 28
        for i in range(0, len(response_text), chunk_size):
            yield f"data: {json.dumps({'type': 'token', 'content': response_text[i:i + chunk_size]}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'data': result}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _route_compound_work(ctx, user_name: str, is_privileged: bool):
    """Câu hỏi kết hợp: giờ làm + số task / quá hạn (vd: 'giờ và task quá hạn tuần này')."""
    target = ctx.user or user_name
    if not target:
        return "hours_summary", {}, {"error": "Bạn gõ tên nhân sự hoặc đăng nhập giúp mình nhé."}
    if not is_privileged:
        target = user_name

    hours = None
    if ctx.wants_hours:
        hours = await sheets.get_hours_summary(
            target, date_from=ctx.date_from, date_to=ctx.date_to,
        )

    tasks = None
    overdue = None
    if ctx.is_overdue:
        overdue_params = enrich_params(
            "search_overdue_tasks",
            {"user": target, "role": ctx.role or "pic"},
            ctx,
        )
        overdue = await sheets.search_overdue_tasks(**overdue_params)
    elif ctx.wants_task_count or ctx.wants_completed_tasks:
        task_params = enrich_params("search_tasks", {"user": target, "role": "pic"}, ctx)
        if ctx.wants_completed_tasks:
            task_params["status"] = "Hoàn thành"
        tasks = await sheets.search_tasks(**task_params)

    personal = None
    if ctx.wants_task_count and not ctx.is_overdue:
        personal = await sheets.get_personal_log(
            target, date_from=ctx.date_from, date_to=ctx.date_to,
        )

    params = {
        "user": target,
        "date_from": ctx.date_from,
        "date_to": ctx.date_to,
        "wants_hours": ctx.wants_hours,
        "wants_task_count": ctx.wants_task_count,
        "wants_completed_tasks": ctx.wants_completed_tasks,
        "is_overdue": ctx.is_overdue,
        "role": ctx.role or "pic",
    }
    result = {
        "user": target,
        "hours": hours,
        "tasks": tasks,
        "overdue": overdue,
        "personal": personal,
        "date_from": ctx.date_from,
        "date_to": ctx.date_to,
    }
    return "work_summary", params, result


async def _route_message(
    message: str,
    user_name: str = None,
    is_privileged: bool = True,
    user_role: str = "member",
):
    ctx = analyze_query(message, logged_in_user=user_name)
    if ctx.is_overdue and not ctx.wants_hours and ctx.user:
        oparams = enrich_params(
            "search_overdue_tasks",
            {"user": ctx.user, "role": ctx.role or "pic"},
            ctx,
        )
        if not is_privileged:
            oparams["user"] = user_name
        result = await sheets.search_overdue_tasks(**oparams)
        return "search_tasks", {**oparams, "filter": "overdue"}, result
    if is_compound_work_query(ctx):
        return await _route_compound_work(ctx, user_name, is_privileged)
    if is_work_pool_query(ctx):
        target = ctx.user or user_name
        if not target:
            staff = find_staff(message)
            if staff:
                target = staff
        if not target:
            return "clarify", {}, {
                "message": "👤 Bạn gõ tên nhân sự giúp mình nhé (vd: **hiệu quả công việc của Phan Minh Hoàng**).",
            }
        if not is_privileged:
            target = user_name
        pool = get_employee_work_pool(target)
        if pool.get("error"):
            return "error", {"user": target}, {"error": pool["error"]}
        return "work_pool_profile", {"user": target}, pool
    if settings.openai_api_key:
        return await _route_with_openai(message, user_name, user_role, is_privileged)
    return await _route_keyword(message, user_name, is_privileged)


async def _route_with_openai(
    message: str,
    user_name: str,
    user_role: str,
    is_privileged: bool,
):
    """GPT chỉ chọn tool (tool_choice=required); response format bằng code."""
    tool_name, params, result = await route_with_openai(
        message, user_name, user_role, is_privileged,
    )
    if tool_name in ("greeting", "off_topic", "error", "clarify"):
        return tool_name, params or {}, result
    if tool_name == "search_overdue_tasks":
        return "search_tasks", {**(params or {}), "filter": "overdue"}, result
    return normalize_tool_name(tool_name), params or {}, result


async def _route_keyword(message: str, user_name: str = None, is_privileged: bool = True):
    if is_greeting(message) or is_help_request(message):
        return "greeting", {}, {"message": HELP_RESPONSE}
    if not is_in_scope(message):
        return "off_topic", {}, {"message": OFF_TOPIC_RESPONSE}

    msg = message.lower()

    msg_na_full = normalize_text(msg)

    # Personal hours summary - "giờ làm của tôi" / "tổng giờ"
    is_hours_query = any(k in msg for k in ["giờ làm", "số giờ", "tổng giờ", "bao nhiêu giờ"]) \
        or any(k in msg_na_full for k in ["gio lam", "so gio", "tong gio", "bao nhieu gio"])
    if is_hours_query:
        target_user = (find_staff(message) or user_name) if is_privileged else user_name
        if not target_user:
            return "hours_summary", {}, {
                "error": "Bạn đăng nhập hoặc gõ tên nhân sự giúp mình nhé (vd: 'Giờ làm của Phan Minh Hoàng')."
            }
        hparams = {"user": target_user}
        date_from, date_to = parse_relative_date_range(message)
        if date_from:
            hparams["date_from"] = date_from
            hparams["date_to"] = date_to
        result = await sheets.get_hours_summary(target_user, date_from=hparams.get("date_from"), date_to=hparams.get("date_to"))
        return "hours_summary", hparams, result

    # Personal log - "log cá nhân của tôi" (chi tiết hơn search_archive)
    is_personal_log = any(k in msg for k in ["log cá nhân", "log ca nhan", "nhật ký cá nhân", "personal log"]) \
        or any(k in msg_na_full for k in ["log ca nhan", "nhat ky ca nhan"])
    if is_personal_log:
        target_user = (find_staff(message) or user_name) if is_privileged else user_name
        if not target_user:
            return "personal_log", {}, {
                "error": "Vui lòng đăng nhập hoặc chỉ định tên nhân sự"
            }
        plog_params = {"user": target_user}
        date_from, date_to = parse_relative_date_range(message)
        if date_from:
            plog_params["date_from"] = date_from
            plog_params["date_to"] = date_to
        result = await sheets.get_personal_log(
            target_user, date_from=plog_params.get("date_from"), date_to=plog_params.get("date_to"),
        )
        return "personal_log", plog_params, result

    # "task của tôi" / "việc của tôi" → auto-filter by logged-in user
    if user_name and any(k in msg for k in ["của tôi", "cua toi", "my task", "việc tôi", "viec toi"]):
        # If asking for reports/archive
        if any(k in msg for k in ["báo cáo", "bao cao", "archive", "report", "log"]):
            result = await sheets.search_archive(user=user_name)
            return "search_archive", {"user": user_name}, result
        result = await sheets.search_tasks(user=user_name, role="pic")
        return "search_tasks", {"user": user_name, "role": "pic"}, result

    # Overdue / quá hạn detection
    msg_na = normalize_text(msg)
    if any(k in msg for k in ["quá hạn", "trễ hạn", "overdue"]) or any(k in msg_na for k in ["qua han", "tre han"]):
        staff = find_staff(message)
        target = staff if is_privileged else user_name
        role = detect_task_role(message, has_user=bool(target)) if target else "pic"
        oparams = {"role": role or "pic"}
        if target:
            oparams["user"] = target
        result = await sheets.search_overdue_tasks(**oparams)
        return "search_tasks", {**oparams, "filter": "overdue"}, result

    # Detect task ID pattern (e.g. CO-001, HH-002)
    task_id_match = re.search(r'[A-Z]{2,}-\d{3}', message.upper())

    # Check if asking for subtasks
    if any(k in msg for k in ["subtask", "task con", "breakdown", "chi tiết hạng mục", "chi tiet hang muc"]):
        parent_match = re.search(r'\b([A-Z]{2,})\b', message)
        if parent_match:
            # Skip the word SUBTASK itself
            candidates = re.findall(r'\b([A-Z]{2,})\b', message)
            parent_id = next((c for c in candidates if c not in ("SUBTASK",)), candidates[-1] if candidates else None)
            if parent_id:
                result = await sheets.get_subtasks(parent_id)
                return "get_subtasks", {"parent_id": parent_id}, result

    # Check for specific task detail
    if task_id_match and any(k in msg for k in ["chi tiết", "detail", "thông tin", "chi tiet", "thong tin"]):
        task_id = task_id_match.group()
        result = await sheets.get_task_detail(task_id)
        return "get_task_detail", {"task_id": task_id}, result

    # Check for archive/report search
    msg_na = normalize_text(msg)
    if any(k in msg for k in ["báo cáo", "archive", "lịch sử", "log việc", "report"]) or any(k in msg_na for k in ["bao cao", "lich su", "log viec"]):
        params = {}
        staff = find_staff(message)
        if staff:
            params["user"] = staff
        if not is_privileged:
            params["user"] = user_name  # member chỉ xem archive của mình
        # Extract project
        projects = ["cao tầng", "hạ tầng", "pccc", "chuyển đổi số"]
        for p in projects:
            if p in msg or normalize_text(p) in msg_na:
                params["project"] = p
                break
        result = await sheets.search_archive(**params)
        return "search_archive", params, result

    # Default: search tasks
    params = {}
    if is_user_as_reviewer_query(message):
        staff = find_staff(message)
        if staff:
            params["user"] = staff
            params["role"] = "reviewer"
    elif wants_tasks_with_reviewer(message):
        params["has_reviewer"] = True
    staff = find_staff(message)
    if staff:
        params["user"] = staff
        role = detect_task_role(message, has_user=True)
        if role is not None:
            params["role"] = role
    if not is_privileged:
        params["user"] = user_name  # member chỉ xem task của mình
        params.setdefault("role", "pic")

    # Detect status (with no-accent support)
    status = _find_status(message)
    if status:
        params["status"] = status

    # Detect date (YYYY-MM-DD or DD/MM/YYYY)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
    if not date_match:
        dmy = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', message)
        if dmy:
            date_match_str = f"{dmy.group(3)}-{dmy.group(2).zfill(2)}-{dmy.group(1).zfill(2)}"
        else:
            date_match_str = None
    else:
        date_match_str = date_match.group(1)

    if date_match_str:
        params["date_from"] = date_match_str
        params["date_to"] = date_match_str

    # If no filters detected, try keyword hoặc gợi ý nhân sự mơ hồ
    if not params:
        msg_na = normalize_text(msg)
        keywords = ["training", "pccc", "cao tầng", "hạ tầng", "masterplan", "setup", "core"]
        for kw in keywords:
            if kw in msg or normalize_text(kw) in msg_na:
                params["keyword"] = kw
                break
        if not params:
            candidates = find_staff_candidates(message)
            if candidates:
                lines = [f"👤 Tìm thấy **{len(candidates)}** nhân sự khớp tên:"]
                for name in candidates[:6]:
                    lines.append(f"  • {name}")
                lines.append('\nGõ rõ hơn, vd: "Task của Phan Minh Hoàng"')
                return "clarify", {}, {"message": "\n".join(lines), "candidates": candidates}
            return "search_tasks", {}, {"tasks": [], "count": 0}

    msg_na = normalize_text(msg)
    keywords = ["training", "pccc", "cao tầng", "hạ tầng", "masterplan", "setup", "core"]
    for kw in keywords:
        if kw in msg or normalize_text(kw) in msg_na:
            params["keyword"] = kw
            break

    # If task_id found, get detail
    if task_id_match and not params:
        task_id = task_id_match.group()
        result = await sheets.get_task_detail(task_id)
        return "get_task_detail", {"task_id": task_id}, result

    result = await sheets.search_tasks(**params)
    return "search_tasks", params, result

async def _generate_general_chat(message: str, history: list) -> str:
    """Xử lý hội thoại thông thường (chào hỏi, giải thích, chém gió) bằng LLM kèm Memory."""
    print("\n================ [DEBUG FALLBACK CHAT START] ================")
    
    # Đảo ngược lịch sử để câu cũ lên trước cho LLM đọc đúng mạch
    ordered_history = list(reversed(history)) if history else []

    messages = [
        {
            "role": "system", 
            "content": (
                "Bạn là một trợ lý ảo phục vụ tra cứu thông tin nhân sự và tiến độ công việc dựa trên dữ liệu Excel có sẵn.\n"
                "Nhiệm vụ của bạn chỉ là: Chào hỏi hoặc giải thích, làm rõ các thắc mắc của người dùng về kết quả tra cứu phía trên dựa vào lịch sử trò chuyện.\n"
                "\nQUY ĐỊNH NGHIÊM NGẶT VỀ PHẠM VI NĂNG LỰC:\n"
                "- Bạn KHÔNG CÓ TÍNH NĂNG lập kế hoạch, phân chia lại nhiệm vụ, tạo task mới hay chỉnh sửa dữ liệu hệ thống.\n"
                "- Tuyệt đối KHÔNG hứa hẹn hoặc gợi ý người dùng thực hiện các hành động nằm ngoài phạm vi tra cứu dữ liệu (như 'để mình lập kế hoạch cho', 'để mình phân chia lại việc').\n"
                "- Nếu người dùng hỏi các câu ngoài phạm vi tra cứu hoặc hỏi vặn vẹo về năng lực, hãy khéo léo từ chối hoặc nhắc nhở họ sử dụng các nút bấm gợi ý dưới màn hình để xem Task, Giờ làm hoặc Báo cáo.\n"
                "- Văn văn phong ngắn gọn, đi thẳng vào vấn đề, không dài dòng văn tự."
            )
        }
    ]

    # Bơm lịch sử chat vào ngữ cảnh cho OpenAI
    for msg in ordered_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # Thêm câu hỏi hiện tại của user vào cuối
    messages.append({"role": "user", "content": message})

    try:
        # Gọi OpenAI để sinh câu trả lời tự do
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7, # Tăng độ sáng tạo một chút để chém gió mượt hơn
            max_tokens=400
        )
        ai_reply = response.choices[0].message.content.strip()
        print(f"-> AI Fallback Reply: '{ai_reply}'")
        print("================ [DEBUG FALLBACK CHAT END] ==================\n")
        return ai_reply
    except Exception as e:
        print(f"❌ LỖI KHI GỌI FALLBACK CHAT: {e}")
        print("================ [DEBUG FALLBACK CHAT END] ==================\n")
        return "😅 Hiện tại mình đang gặp một chút sự cố kết nối, bạn thử lại sau nhé!"



async def _format_response(tool_name: str, result: dict, message: str, params: dict = None, history: list = None) -> str:
    params = params or {}
    tool_name = normalize_tool_name(tool_name)

    if result.get("error"):
        err = result["error"]
        if "Chưa có file cá nhân" in err:
            who = params.get("user") or result.get("user") or "nhân sự này"
            return (
                f"📂 Mình chưa tìm thấy file cá nhân của **{who}**.\n\n"
                "Có thể file Excel cá nhân chưa được import — bạn liên hệ admin để cập nhật nhé."
            )
        return f"😅 {err}"

    # === 1. NHÁNH HARD-CORE CHUẨN (Giữ nguyên template hướng dẫn của hệ thống) ===
    if tool_name == "greeting":
        return result["message"] 

    if tool_name == "clarify":
        return result["message"] 

    # === 2. NHÁNH OPENAI CHAT GENERAL (Chỉ kích hoạt khi thực sự off_topic) ===
    if tool_name == "off_topic":
        # Gọi OpenAI đọc 5 câu lịch sử từ Mongo để giải thích tự do cho user
        general_reply = await _generate_general_chat(message, history)
        return general_reply

    if tool_name == "work_pool_profile":
        name = result.get("employee") or params.get("user", "")
        p = result.get("profile") or {}
        w = result.get("work_pool") or {}
        s3p = p.get("salary_3p") or {}
        lines = [
            f"📊 **Hiệu quả công việc — {name}**",
            f"\n🎯 **Năng lực:** {p.get('competency_score', '—')}% · **Hiệu quả:** {p.get('efficiency_score', '—')}%",
            f"📐 Bậc {p.get('job_grade', '—')} · Trình độ L{p.get('skill_level', '—')}",
            f"💰 Lương 3P: P={s3p.get('position', '—')} / Pf={s3p.get('person', '—')} / Ps={s3p.get('performance', '—')}",
            f"\n📋 Đang làm **{w.get('active', 0)}** · Hoàn thành **{w.get('done', 0)}/{w.get('total', 0)}** ({w.get('completion_rate', 0)}%)",
            f"⚡ Ưu tiên mặc định: {p.get('default_priority', '—')}",
        ]
        tasks = (result.get("current_tasks") or [])[:6]
        if tasks:
            lines.append("\n**Việc đang phụ trách:**")
            for t in tasks:
                lines.append(
                    f"  • `{t.get('id', '')}` {str(t.get('name', ''))[:48]} — {t.get('status', '')} ({t.get('priority', '')})"
                )
        comps = (result.get("job_comparisons") or [])[:3]
        if comps:
            lines.append("\n**So sánh job lớn:**")
            for c in comps:
                lines.append(
                    f"  • {c.get('parent_job_id', '')}: gánh **{c.get('user_share_pct', 0)}%** · tiến độ chung **{c.get('pool_completion_rate', 0)}%**"
                )
        return "\n".join(lines)

    if tool_name == "work_summary":
        user = result.get("user") or params.get("user", "")
        period = ""
        if result.get("date_from") and result.get("date_to"):
            period = f" ({result['date_from']} → {result['date_to']})"

        lines = [f"📊 **Tổng hợp công việc của {user}**{period}"]

        if params.get("wants_hours") or result.get("hours"):
            h = result.get("hours") or {}
            if h.get("error"):
                lines.append(f"\n⏱️ Giờ làm: {h['error']}")
            else:
                total = h.get("total_hours", 0)
                cnt = h.get("report_count", 0)
                lines.append(f"\n⏱️ **{total}h** đã ghi nhận — {cnt} báo cáo")
                for project, hours in list((h.get("by_project") or {}).items())[:5]:
                    lines.append(f"   • {project[:35]}: {hours}h")

        if params.get("is_overdue") or result.get("overdue"):
            oc = (result.get("overdue") or {}).get("count", 0)
            role_label = {"pic": "PIC", "support": "phối hợp", "reviewer": "kiểm tra"}.get(
                params.get("role", "pic"), "PIC",
            )
            lines.append(f"\n⚠️ **{oc}** task quá hạn ({role_label})")
        elif params.get("wants_completed_tasks"):
            tc = (result.get("tasks") or {}).get("count", 0)
            lines.append(f"\n✅ **{tc}** task đã hoàn thành (PIC trong kế hoạch)")
        elif params.get("wants_task_count"):
            tc = (result.get("tasks") or {}).get("count", 0)
            lines.append(f"\n📋 **{tc}** task đang phụ trách (PIC)")
            pr = (result.get("personal") or {}).get("count", 0)
            if pr:
                lines.append(f"📝 **{pr}** báo cáo cá nhân trong kỳ")

        return "\n".join(lines)

    if tool_name == "hours_summary":
        bp = result.get("by_project", {})
        total = result.get("total_hours", 0)
        cnt = result.get("report_count", 0)
        user = result.get("user") or params.get("user", "")
        period = ""
        if result.get("date_from") and result.get("date_to"):
            period = f" ({result['date_from']} → {result['date_to']})"
        if not bp and cnt == 0:
            return f"📊 **{user}** chưa có giờ làm nào được ghi nhận{period} trong file cá nhân."
        lines = [f"⏱️ **{user}** đã ghi nhận **{total}h**{period} — {cnt} báo cáo"]
        lines.append("\nPhân bổ theo dự án:")
        for project, hours in list(bp.items())[:10]:
            bar = "█" * min(int(hours / 2), 20)
            lines.append(f"  • {project[:40]:<40} {hours:>5.1f}h {bar}")
        if len(bp) > 10:
            lines.append(f"  _…và {len(bp) - 10} dự án khác_")
        return "\n".join(lines)

    if tool_name == "personal_log":
        reports = result.get("reports", [])
        user = result.get("user", "")
        if not reports:
            return f"📒 **{user}** chưa có log cá nhân nào trong khoảng thời gian bạn hỏi."
        total = result["count"]
        show = reports[:15]
        lines = [f"📒 Đây là log cá nhân của **{user}** — **{total}** báo cáo"]
        if total > 15:
            lines.append(f"_(hiển thị 15/{total} báo cáo gần nhất, hỏi cụ thể theo ngày/dự án để lọc)_")
        lines.append("")
        for r in show:
            status = (r.get("status") or "").strip()
            emoji = {"Hoàn thành": "🟢", "Đang làm": "⏳", "Chưa làm": "⭐"}.get(status, "📝")
            date = (r.get("report_date") or "")[:10]
            progress = r.get("progress", "")
            hours = r.get("hours")
            project = r.get("project", "Khác")
            content = r.get("task_content", "")
            note = r.get("report_note", "")

            # Dòng 1: ngày + tiến độ + giờ
            meta = [f"📅 **{date}**"]
            if progress:
                meta.append(f"{emoji} {progress}")
            elif status:
                meta.append(f"{emoji} {status}")
            if hours:
                meta.append(f"⏱️ {hours}h")
            lines.append(" • ".join(meta))

            # Dòng 2: dự án + nội dung (có thể có ghi chú)
            content_short = content[:100] + ("…" if len(content) > 100 else "")
            lines.append(f"   📌 _{project}_ — {content_short}")
            if note and len(note.strip()) > 3:
                note_short = note[:80] + ("…" if len(note) > 80 else "")
                lines.append(f"   💬 {note_short}")
            lines.append("")  # spacer

        return "\n".join(lines).rstrip()

    if tool_name == "get_task_detail":
        t = result.get("task", {})
        status_emoji = {"Hoàn thành": "🟢", "Đang làm": "⏳", "Chưa làm": "⭐"}.get(t.get("status"), "❓")
        lines = [
            f"**{t['id']}** - {t['name']} {status_emoji}",
            f"📅 {t.get('start_date', '?')} → {t.get('end_date', '?')} ({t.get('duration_days', '?')} ngày)",
            f"👤 Thực hiện: {t.get('pic', '-')}",
            f"🤝 Phối hợp: {t.get('support', '-')}",
            f"✅ Kiểm tra: {t.get('reviewer', '-')}",
            f"📊 Trạng thái: {t.get('status', '-')}",
        ]
        if t.get("predecessor"):
            lines.append(f"⬅️ Việc trước: {t['predecessor']}")
        if t.get("note"):
            lines.append(f"📝 Ghi chú: {t['note']}")
        if t.get("zone"):
            lines.append(f"📍 Zone: {t['zone']}")
        if t.get("elapsed") is not None:
            lines.append(f"⏳ Đã qua: {t['elapsed']} ngày")
        for label, dkey, ckey in (
            ("Chuẩn bị", "check_prep_date", "check_prep"),
            ("Thực hiện", "check_exec_date", "check_exec"),
            ("Nghiệm thu", "check_accept_date", "check_accept"),
        ):
            if t.get(dkey) or t.get(ckey):
                lines.append(f"🔍 KT {label}: {t.get(dkey) or '-'} — {t.get(ckey) or '-'}")
        return "\n".join(lines)

    elif tool_name == "get_subtasks":
        subs = result.get("subtasks", [])
        if not subs:
            return f"Mình không thấy task con nào thuộc **{result.get('parent_id')}**."
        lines = [f"📂 **{result['parent_id']}** có **{result['count']}** task con:"]
        for t in subs[:20]:
            emoji = {"Hoàn thành": "🟢", "Đang làm": "⏳", "Chưa làm": "⭐"}.get(t.get("status"), "❓")
            rev = t.get("reviewer") or "-"
            lines.append(f"  {emoji} {t['id']} - {t['name']} | PIC: {t.get('pic', '-')} | KT: {rev}")
        return "\n".join(lines)

    elif tool_name == "search_archive":
        reports = result.get("reports", [])
        if not reports:
            return "Mình chưa tìm thấy báo cáo phù hợp.\n\n" + _suggest_similar(message)
        total = result['count']
        show = reports[:20]
        lines = [f"📋 Mình tìm thấy **{total}** báo cáo:"]
        for r in show:
            emoji = {"Hoàn thành": "🟢", "Đang làm": "⏳"}.get(r.get("status"), "❓")
            lines.append(f"  {emoji} [{r.get('report_date', '')[:10]}] {r['user']} - {r['task_content'][:60]}")
        if total > 20:
            fname = _export_reports_excel(reports)
            lines.append(f"\n📥 Có **{total}** báo cáo, hiển thị 20. [Tải file Excel đầy đủ](/api/export/{fname})")
        return "\n".join(lines)

    elif tool_name == "search_tasks":
        tasks = result.get("tasks", [])
        if not tasks:
            if params.get("user"):
                if params.get("role") == "reviewer":
                    return f"👤 **{params['user']}** hiện chưa được gán kiểm tra (reviewer) task nào."
                if params.get("role") == "support":
                    return f"👤 **{params['user']}** chưa có task phối hợp nào."
                return f"👤 **{params['user']}** chưa có task nào trong kế hoạch."
            if params.get("has_reviewer"):
                return "Hiện chưa có task nào đã gán người kiểm tra."
            if params.get("filter") == "overdue":
                return "✅ Tin vui — không có task nào quá hạn!"
            if params.get("date_from"):
                return f"📅 Không có task nào trong ngày **{params['date_from']}**."
            return "Mình chưa tìm thấy task phù hợp.\n\n" + _suggest_similar(message)

        if not params:
            return "🤔 Mình chưa hiểu rõ bạn cần gì.\n\n" + _suggest_similar(message)

        total = result['count']
        show = tasks[:20]
        header = f"📋 Mình tìm thấy **{total}** task"
        if params.get("role") == "reviewer" and params.get("user"):
            header = f"📋 **{params['user']}** là người kiểm tra (KT) của **{total}** task"
        elif params.get("role") == "support" and params.get("user"):
            header = f"📋 **{params['user']}** phối hợp **{total}** task"
        elif params.get("role") == "pic" and params.get("user"):
            header = f"📋 **{params['user']}** thực hiện chính (PIC) **{total}** task"
        elif params.get("has_reviewer"):
            header = f"📋 Có **{total}** task đã gán người kiểm tra"
        if params.get("filter") == "overdue":
            header += " ⚠️ quá hạn"
        if params.get("date_from"):
            header += f" (ngày {params['date_from']})"
        header += ":"
        lines = [header]
        for t in show:
            emoji = {"Hoàn thành": "🟢", "Đang làm": "⏳", "Chưa làm": "⭐"}.get(t.get("status"), "❓")
            deadline = t.get("end_date", "")
            pic = (t.get("pic") or "-")[:20]
            rev = (t.get("reviewer") or "-")[:20]
            lines.append(f"  {emoji} **{t['id']}** {t['name'][:45]} | PIC: {pic} | KT: {rev} | {deadline}")
        if total > 20:
            fname = _export_tasks_excel(tasks)
            lines.append(f"\n📥 Có **{total}** tasks, hiển thị 20. [Tải file Excel đầy đủ](/api/export/{fname})")
        rb = result.get("role_breakdown")
        if rb and params.get("role") in (None, "pic") and (rb.get("support") or rb.get("reviewer")):
            extra = []
            if rb.get("support"):
                extra.append(f"{rb['support']} phối hợp")
            if rb.get("reviewer"):
                extra.append(f"{rb['reviewer']} kiểm tra")
            lines.append(
                f"\n💡 Ngoài ra **{params.get('user', '')}** còn {' · '.join(extra)} "
                f"— gõ \"tất cả task của {params.get('user', '')}\" để xem đầy đủ nhé."
            )
        return "\n".join(lines)

    return str(result)
