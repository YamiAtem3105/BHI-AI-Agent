# BHI AI Agent

Chatbot trợ lý ảo quản lý công việc cho khối QLXD - BHI: Web chat + Telegram/Zalo, định tuyến bằng OpenAI (tùy chọn), dữ liệu trên Google Sheets.

## Kiến trúc

```
Web UI / Telegram / Zalo → FastAPI → Auth (JWT + Google OAuth)
                                       ↓ routing: OpenAI tool-call (tùy chọn) | keyword fallback
                                 Tools Layer → Apps Script → Google Sheets (Masterplan + file cá nhân)
                                       ↓
                                 SQLite (users, conversations, audit)
```

## Cài đặt

```bash
# 1. Clone & setup
cp .env.example .env
# Điền OPENAI_API_KEY và APPS_SCRIPT_URL (+ GOOGLE_CLIENT_ID/SECRET nếu dùng OAuth)

# 2. Chạy với Docker
docker-compose up -d

# 3. Seed users
python scripts/seed_users.py
```

> Chạy/deploy trên **máy khác** (clone, `.env`, dữ liệu PII, redeploy Apps Script, múi giờ,
> Render): xem [`docs/deploy-may-khac.md`](docs/deploy-may-khac.md).


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

### UC3 - Nhật ký cập nhật (Audit log)
Mọi thao tác **tạo/cập nhật task** (qua chatbot hoặc dashboard) tự động ghi lại:
**ai** (tên member) · **task nào** · **đổi từ gì sang gì** · **lúc nào**.
VD: *"Lê Chí Hoàng Long • CO-001 • trạng thái: Đang làm → Hoàn thành • 23/06 14:30"*.

- **Lưu ở:** `data/audit_log.json` — **tự tạo** khi thiếu, nên chạy được ngay trên
  máy khác / khi deploy mà không cần thao tác thủ công.
  ⚠️ Ổ đĩa ephemeral (vd Render) sẽ reset log khi redeploy; muốn bền lâu thì mirror
  sang một tab Google Sheet (chưa làm).
- **Dashboard:** thẻ "🕒 Nhật ký cập nhật" hiện 3–4 log mới nhất; bấm → popup 20 log.
- **Chatbot (chỉ admin/quản lý):** "ai cập nhật gì", "lịch sử cập nhật của Hoàng Long".
  **Member KHÔNG xem được** nhật ký của người khác (chống spy phòng ban).
- **API:** `GET /api/audit?limit=N&member=<tên>` (admin/quản lý; member → 403).

### UC4 - Quản lý file cá nhân + gating (chống spy)
Mỗi member có **link file công việc cá nhân** (Google Sheet) lưu ở `staff.json[].file`.

- **Admin/manager** quản lý link trên Dashboard, mục **"📁 Quản lý file cá nhân"**:
  bảng nhân sự + ô dán link + nút **Lưu** (từng người) + nút **Reload** (xóa cache →
  chatbot đọc dữ liệu mới nhất, **real-time**).
- **Gating:** member chỉ dùng được chatbot khi (1) là nhân sự hợp lệ **và** (2) đã
  được gán link file. Member chưa có file → chatbot báo *"⛔ Bạn chưa được gán file
  công việc, liên hệ admin"*. Admin/manager miễn (xem Masterplan chung).
- **Chống spy phòng ban:** `read_scope` giới hạn member chỉ đọc file của chính mình.
- **API** (admin/manager; member → 403): `GET /api/staff-files`,
  `POST /api/staff-files {email, file}`, `POST /api/staff-files/reload`.

> Link sửa lúc chạy ghi đè `staff.json`. ⚠️ Ổ ephemeral (Render) reset khi redeploy;
> sửa lại trên Dashboard sau deploy, hoặc commit link vào `staff.json`.

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
