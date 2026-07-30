"""OpenAI function-calling schema — model chỉ chọn tool, không tự bịa data."""

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_tasks",
            "description": "Tìm task trong kế hoạch masterplan (19 cột: id, name, dates, pic, support, reviewer, check_*, zone...).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string", "description": "Tên nhân sự"},
                    "role": {"type": "string", "enum": ["pic", "support", "reviewer"], "description": "pic=Thực hiện (mặc định). support=Phối hợp. reviewer=Kiểm tra khi hỏi 'task kiểm tra của X'"},
                    "status": {"type": "string", "description": "Đang làm | Hoàn thành | Chưa làm"},
                    "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                    "keyword": {"type": "string", "description": "Lọc theo tên/ghi chú/zone"},
                    "zone": {"type": "string", "description": "Zone / Hạng mục / Công tác"},
                    "has_reviewer": {"type": "boolean", "description": "true = chỉ task đã có người kiểm tra (cột reviewer không trống)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_overdue_tasks",
            "description": "Lấy danh sách task quá hạn (chưa hoàn thành, đã qua deadline).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string", "description": "Lọc theo nhân sự, bỏ trống = tất cả (admin)"},
                    "role": {"type": "string", "enum": ["pic", "support", "reviewer"], "description": "Vai trò lọc quá hạn, mặc định pic"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_detail",
            "description": "Chi tiết đầy đủ 1 task theo ID (VD: CO-001).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_subtasks",
            "description": "Task con của hạng mục cha (VD: CO → CO-001, CO-002).",
            "parameters": {
                "type": "object",
                "properties": {
                    "parent_id": {"type": "string"},
                },
                "required": ["parent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_archive",
            "description": "Lịch sử báo cáo hàng ngày (archive chung masterplan).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string"},
                    "project": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_personal_log",
            "description": "Nhật ký cá nhân chi tiết (file Excel riêng từng nhân sự).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string"},
                    "project": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                },
                "required": ["user"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hours_summary",
            "description": "Tổng giờ làm theo dự án từ file cá nhân.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                },
                "required": ["user"],
            },
        },
    },
]

SYSTEM_PROMPT_ROUTER = """Bạn là bộ định tuyến tool cho BHI Agent (QLXD - quản lý công việc).

NHIỆM VỤ DUY NHẤT: chọn đúng 1 function call từ danh sách tools. KHÔNG trả lời tự do.

Quy tắc routing:
- Task/kế hoạch → search_tasks (mặc định role=pic khi hỏi "task của X")
- "X là người kiểm tra" / "task kiểm tra của X" → search_tasks, role=reviewer, user=X
- "task phối hợp/hỗ trợ của X" → search_tasks, role=support
- "task có người kiểm tra" (không chỉ định người) → search_tasks, has_reviewer=true
- "quá hạn"/"trễ" → search_overdue_tasks
- "chi tiết CO-001" → get_task_detail, task_id=CO-001
- "subtask của CO" → get_subtasks, parent_id=CO
- "báo cáo"/"archive" (không phải log cá nhân) → search_archive
- "log cá nhân"/"nhật ký" → get_personal_log
- "giờ làm"/"tổng giờ"/"bao nhiêu giờ" → get_hours_summary
- "của tôi" → user={user_name}

Trích xuất tham số (điền đủ nếu nhận ra trong câu hỏi):
- user: tên nhân sự đầy đủ
- role: pic | support | reviewer
- status: Đang làm | Hoàn thành | Chưa làm
- date_from/date_to: YYYY-MM-DD hoặc "tuần này"/"tháng này"
- keyword, zone, project: nếu có trong câu
- has_reviewer: true chỉ khi hỏi task ĐÃ CÓ người KT (không phải hỏi X là KT)

User đăng nhập: {user_name} | Role: {user_role}
"""
