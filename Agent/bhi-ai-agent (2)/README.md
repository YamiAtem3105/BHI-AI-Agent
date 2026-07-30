# BHI AI Agent

Chatbot trợ lý ảo quản lý công việc cho khối QLXD - BHI, tích hợp Google Chat + Gemini AI + Google Sheets.

## Kiến trúc

```
Google Chat → FastAPI Webhook → Auth Service → Agent (Gemini 1.5 Pro)
                                                    ↓ function calling
                                              Tools Layer → Apps Script → Google Sheets
                                                    ↓
                                              PostgreSQL (users, conversations, audit)
```

## Cài đặt

```bash
# 1. Clone & setup
cp .env.example .env
# Điền GEMINI_API_KEY và APPS_SCRIPT_URL

# 2. Chạy với Docker
docker-compose up -d

# 3. Seed users
python scripts/seed_users.py
```

## Cấu trúc project

```
app/
├── api/google_chat.py      # Webhook endpoint nhận message từ Google Chat
├── services/
│   ├── auth_service.py     # Map email → user, phân quyền
│   ├── agent_service.py    # Gemini LLM + Function Calling orchestration
│   └── sheets_service.py   # HTTP client gọi Apps Script API
├── models/models.py        # SQLAlchemy models (6 tables)
├── prompts/system_prompt.py
└── config.py
scripts/
├── apps_script/Code.gs     # Deploy lên Google Sheets
└── seed_users.py           # Seed 18 nhân sự QLXD
```

## Use Cases

### UC1 - Truy vấn (Read)
- "Hôm nay tôi có task nào đến hạn?"
- "Tiến độ training core team đến đâu?"
- "Task nào đang bị trễ hạn?"

### UC2 - Nhập liệu (Write) 
- "Tạo kế hoạch Ra mắt dự án T6 gồm 3 task: ..."
- "Cập nhật task CO-005 thành Hoàn thành"

Write operations yêu cầu xác nhận trước khi thực thi.

## Deploy Apps Script

1. Mở Google Sheets Masterplan
2. Extensions → Apps Script
3. Paste nội dung `scripts/apps_script/Code.gs`
4. Deploy → New Deployment → Web App → Execute as Me → Anyone
5. Copy URL vào `.env` APPS_SCRIPT_URL

## Phân quyền

| Role | Quyền |
|------|--------|
| admin | Xem tất cả tasks |
| manager | Xem tasks trong department |
| member | Chỉ xem tasks mình là PIC |
