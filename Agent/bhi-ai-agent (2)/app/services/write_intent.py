"""Parse ý định ghi (tạo/cập nhật task) từ ngôn ngữ tự nhiên.

Dùng chung cho web chat (app/api/chat.py) và messaging Zalo/Telegram
(app/services/messaging_service.py) — một nguồn sự thật, có test.

Mỗi parser trả về dict {"tool", "params", "preview"} hoặc None.
"""
import re

from app.services.text_utils import find_staff, normalize_text

# Cụm mở đầu báo hiệu lệnh tạo task (đã bỏ dấu)
_CREATE_TRIGGERS = ("tao task", "tao cong viec", "tao cong vc", "task moi", "them task", "tao viec")
_TRIGGER_TOKENS = [tr.split() for tr in _CREATE_TRIGGERS] + [["/task"]]
# Từ lịch sự cho phép đứng TRƯỚC trigger ("tôi muốn tạo task...")
_LEAD_FILLERS = {"toi", "minh", "muon", "hay", "giup", "gium", "cho", "lam", "on",
                 "vui", "long", "ban", "oi", "xin", "nho", "can", "lam on"}
# Từ filler ở đầu TÊN task cần bỏ (sau trigger)
_NAME_LEAD_FILLERS = {"moi", "mot", "1", "la"}
# Mốc kết thúc tên task (sau đó là người/deadline/sheet)
_CREATE_STOP = {"giao", "cho", "deadline", "han", "truoc", "den"}
# Tiểu từ cuối câu cần bỏ khỏi tên
_TRAIL_PARTICLES = {"di", "nhe", "nha", "voi", "luon", "nhi", "ha", "oi", "day", "do", "gium", "giup"}
# Tên chỉ gồm tiểu từ vô nghĩa → hỏi lại tên
_PARTICLE_ONLY = {"co ma", "the", "vay", "a", "oi", "u", "di", "nhe", "gi"}
# Từ báo hiệu đây là báo cáo, không phải tạo task
_REPORT_WORDS = {"bao", "cao", "ghi", "report", "log"}

_STATUS_MAP = {
    "hoàn thành": "Hoàn thành", "hoan thanh": "Hoàn thành",
    "đang làm": "Đang làm", "dang lam": "Đang làm",
    "chưa làm": "Chưa làm", "chua lam": "Chưa làm",
}


def parse_date(text: str) -> str | None:
    """Trích ngày YYYY-MM-DD hoặc DD/MM/YYYY → ISO."""
    iso = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)
    dmy = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if dmy:
        return f"{dmy.group(3)}-{dmy.group(2).zfill(2)}-{dmy.group(1).zfill(2)}"
    return None


def parse_update_task(text: str) -> dict | None:
    """'cập nhật CO-001 hoàn thành' → update_task. None nếu không khớp."""
    m = re.search(
        r"(?:cập nhật|cap nhat|update)\s+([A-Z]{2,}-\d+(?:\.\d+)?)\s+"
        r"(hoàn thành|hoan thanh|đang làm|dang lam|chưa làm|chua lam)",
        text,
        re.I,
    )
    if not m:
        return None
    task_id = m.group(1).upper()
    status = _STATUS_MAP.get(m.group(2).lower(), m.group(2))
    return {
        "tool": "update_task",
        "params": {"task_id": task_id, "status": status},
        "preview": f"📋 Cập nhật **{task_id}** → {status}\n\n✅ Gõ 'ok' xác nhận | ❌ 'hủy'",
    }


def _ask_name() -> dict:
    return {
        "tool": None, "params": {},
        "preview": "📝 Bạn cho mình **tên task** nhé. VD: "
        "tạo task lắp PCCC tầng 3 giao Nguyễn Văn A deadline 20/06/2026",
    }


def parse_create_task(text: str, user_name: str) -> dict | None:
    """'tạo task <tên> giao <người> deadline <ngày>' → create_task. None nếu không phải.

    Cho phép từ lịch sự phía trước ('tôi muốn tạo task...'); không tạo task tên rác
    (chỉ tiểu từ) mà hỏi lại tên; bỏ phần 'vào sheet N' khỏi tên.
    """
    t = text.strip()
    norm = normalize_text(t)
    orig_tokens = t.split()
    norm_tokens = norm.split()
    n = len(norm_tokens)

    # Tìm trigger trong ~5 token đầu (cho phép vài từ lịch sự phía trước)
    trig_at, trig_len = None, 0
    for j in range(min(n, 5)):
        for tt in _TRIGGER_TOKENS:
            if norm_tokens[j:j + len(tt)] == tt:
                trig_at, trig_len = j, len(tt)
                break
        if trig_at is not None:
            break
    if trig_at is None:
        return None

    lead = norm_tokens[:trig_at]
    if any(w in _REPORT_WORDS for w in lead):
        return None  # ngữ cảnh báo cáo
    if any(w not in _LEAD_FILLERS for w in lead):
        return None  # có từ lạ phía trước → không chắc là lệnh tạo

    # Tên bắt đầu sau trigger, bỏ filler đầu tên (mới, một…)
    i = trig_at + trig_len
    while i < n and norm_tokens[i] in _NAME_LEAD_FILLERS:
        i += 1
    name_tokens = []
    k = i
    while k < n:
        w = norm_tokens[k]
        if w in _CREATE_STOP or w in ("sheet", "masterplan", "qlxd"):
            break
        if w == "vao" and k + 1 < n and norm_tokens[k + 1] in ("sheet", "masterplan"):
            break
        name_tokens.append(orig_tokens[k])
        k += 1
    # Bỏ tiểu từ cuối tên
    while name_tokens and normalize_text(name_tokens[-1]) in _TRAIL_PARTICLES:
        name_tokens.pop()
    name = " ".join(name_tokens).strip(" :,-")
    if not name or normalize_text(name) in _PARTICLE_ONLY:
        return _ask_name()

    pic = find_staff(t) or user_name
    end_date = parse_date(t)
    source = _detect_sheet(norm)
    task = {"name": name, "pic": pic, "status": "Chưa làm"}
    if end_date:
        task["end_date"] = end_date

    sheet_label = "Sheet 2 (Masterplan)" if source == "2" else "Sheet 1"
    preview = (
        f"🆕 Tạo task mới:\n"
        f"• Tên: {name}\n"
        f"• Thực hiện (PIC): {pic}\n"
        f"• Deadline: {end_date or '—'}\n"
        f"• Ghi vào: {sheet_label}\n\n"
        f"✅ Gõ 'ok' xác nhận | ❌ 'hủy'"
    )
    return {"tool": "create_task", "params": {"tasks": [task], "source": source}, "preview": preview}


def _detect_sheet(norm: str) -> str:
    """Phát hiện sheet đích từ câu: 'sheet 2'/'masterplan' → '2'; mặc định '1'."""
    if any(k in norm for k in ("sheet 2", "sheet2", "sheet hai", "masterplan", "master plan", "qlxd")):
        return "2"
    return "1"


def parse_write_intent(text: str, user_name: str) -> dict | None:
    """Thử cập nhật trước, rồi tạo task. None nếu không phải lệnh ghi."""
    action = parse_update_task(text)
    if action:
        return action
    create = parse_create_task(text, user_name)
    if create and create.get("tool"):
        return create
    return create  # có thể là gợi ý thiếu tên (tool=None) hoặc None
