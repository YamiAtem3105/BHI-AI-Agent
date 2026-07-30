"""Webhook Zalo / Telegram — chatbot ghi task vào sheet cho hiện trường."""
import json
import logging
import re
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import User
from app.services.messaging_links import find_staff_by_platform, log_pending_link
from app.services.mock_sheets import get_staff_by_email, get_staff_by_name
from app.services.rbac import has_permission, normalize_role
from app.services.sheet_writer import SheetWriter
from app.services.write_intent import parse_write_intent

logger = logging.getLogger(__name__)


class MessagingService:
    def __init__(self, db: Session):
        self.db = db
        self.writer = SheetWriter()

    async def handle_telegram_update(self, update: dict) -> dict:
        message = update.get("message") or update.get("edited_message")
        if not message:
            return {"ok": True, "skipped": "no_message"}

        chat_id = str(message["chat"]["id"])
        text = (message.get("text") or "").strip()
        if not text and message.get("voice"):
            text = await self._transcribe_voice(message.get("voice", {}))
            if not text:
                return {
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": (
                        "Mình chưa nghe được tin nhắn thoại.\n"
                        "Vui lòng gõ text: `bao cao: <noi dung>` hoặc bật OPENAI_API_KEY để nhận diện giọng nói."
                    ),
                }
        if not text:
            return {"ok": True, "skipped": "empty_text"}

        # /start — hien thi chat_id de admin lien ket
        if text.lower().startswith("/start"):
            return {
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": (
                    f"Xin chao! Telegram chat_id cua ban: `{chat_id}`\n"
                    "Gui ID nay cho Admin de lien ket tai khoan BHI.\n"
                    "Sau khi lien ket, go: bao cao: <noi dung cong viec>"
                ),
            }

        from_user = message.get("from", {})
        display_name = " ".join(
            filter(None, [from_user.get("first_name"), from_user.get("last_name")])
        ).strip()
        username = from_user.get("username", "")

        user = self._resolve_user(
            platform="telegram",
            platform_id=chat_id,
            email_hint=from_user.get("email"),
            display_name=display_name,
            username=username,
        )
        if not user:
            log_pending_link("telegram", chat_id, display_name or username)
            return {
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": (
                    f"Ban chua duoc lien ket.\n"
                    f"Telegram ID: `{chat_id}`\n"
                    "Lien he Admin hoac gui ID nay de dang ky."
                ),
            }

        reply = await self._process_field_message(user, text)
        return {"method": "sendMessage", "chat_id": chat_id, "text": reply}

    async def handle_zalo_event(self, event: dict) -> dict:
        """Zalo OA webhook — event_name MESSAGE/text."""
        event_name = event.get("event_name") or event.get("event")
        if event_name not in ("user_send_text", "message", "USER_SEND_TEXT"):
            return {"ok": True, "skipped": event_name}

        sender = event.get("sender", {}) or event.get("message", {}).get("sender", {})
        message = event.get("message", {})
        text = (message.get("text") or event.get("text") or "").strip()
        if not text:
            return {"ok": True, "skipped": "empty_text"}

        zalo_id = str(sender.get("id") or sender.get("user_id") or "")
        display_name = sender.get("name", "")

        user = self._resolve_user(
            platform="zalo",
            platform_id=zalo_id,
            display_name=display_name,
        )
        if not user:
            log_pending_link("zalo", zalo_id, display_name)
            return {
                "recipient": {"user_id": zalo_id},
                "message": {
                    "text": f"Ban chua duoc lien ket Zalo OA.\nZalo user_id: {zalo_id}\nLien he Admin.",
                },
            }

        reply = await self._process_field_message(user, text)
        return {
            "recipient": {"user_id": zalo_id},
            "message": {"text": reply},
        }

    async def _transcribe_voice(self, voice: dict) -> str:
        """Chuyển voice Telegram → text (Whisper qua OpenAI)."""
        if not settings.openai_api_key or not settings.telegram_bot_token:
            return ""
        file_id = voice.get("file_id")
        if not file_id:
            return ""
        try:
            import httpx
            from openai import OpenAI

            async with httpx.AsyncClient(timeout=30) as client:
                fr = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
                    params={"file_id": file_id},
                )
                fr.raise_for_status()
                file_path = fr.json()["result"]["file_path"]
                audio = await client.get(
                    f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}",
                )
                audio.raise_for_status()
            client_ai = OpenAI(api_key=settings.openai_api_key)
            import io
            buf = io.BytesIO(audio.content)
            buf.name = "voice.ogg"
            tr = client_ai.audio.transcriptions.create(
                model="whisper-1",
                file=buf,
                language="vi",
            )
            return (tr.text or "").strip()
        except Exception as e:
            logger.warning("Voice transcribe failed: %s", e)
            return ""

    def _resolve_user(
        self,
        platform: str,
        platform_id: str,
        display_name: str = "",
        email_hint: str | None = None,
        username: str = "",
    ) -> User | None:
        """Map platform ID -> User DB qua messaging_links.json hoac ten/email."""
        tag = f"{platform}:{platform_id}"
        user = self.db.query(User).filter(User.google_chat_id == tag).first()
        if user:
            return user

        staff = None
        link = find_staff_by_platform(platform, platform_id)
        if link:
            staff = get_staff_by_email(link["email"])
        if not staff and email_hint:
            staff = get_staff_by_email(email_hint)
        if not staff and display_name:
            staff = get_staff_by_name(display_name)
        if not staff and username:
            staff = get_staff_by_name(username)

        if not staff:
            return None

        user = self.db.query(User).filter(User.email == staff["email"]).first()
        if not user:
            user = User(
                email=staff["email"],
                display_name=staff["name"],
                role=staff.get("role", "member"),
                google_chat_id=tag,
                masterplan_name=staff["name"],
            )
            self.db.add(user)
        else:
            user.google_chat_id = tag
        self.db.commit()
        return user

    async def _process_field_message(self, user: User, text: str) -> str:
        role = normalize_role(user.role)
        if not has_permission(role, "messaging.field_report"):
            return "⚠️ Tài khoản không có quyền ghi báo cáo."

        msg_lower = text.lower().strip()
        if msg_lower in ("help", "/help", "hướng dẫn", "huong dan"):
            return self._help_text()

        # Xác nhận pending
        from app.models.models import Conversation
        conv = self.db.query(Conversation).filter(
            Conversation.user_id == user.id, Conversation.is_active == True,
        ).first()
        pending = (conv.context or {}).get("pending_write") if conv else None
        if pending and msg_lower in ("ok", "xác nhận", "xac nhan", "đồng ý", "dong y", "yes"):
            result = await self.writer.execute_pending(pending)
            self._clear_pending(user)
            if not result.get("error"):
                self._invalidate_cache()
            if result.get("error"):
                return f"❌ Lỗi ghi sheet: {result['error']}"
            return f"✅ Đã ghi vào sheet!\n{result.get('message', '')}"

        if pending and msg_lower in ("hủy", "huy", "cancel", "không", "khong"):
            self._clear_pending(user)
            return "❌ Đã hủy."

        action = self._parse_field_intent(text, user.display_name)

        # Tạo task cần quyền data.write.task (cao hơn báo cáo hiện trường)
        if action.get("tool") == "create_task" and not has_permission(role, "data.write.task"):
            return "⚠️ Tài khoản của bạn không có quyền tạo task. Liên hệ quản lý nhé."

        if action.get("needs_confirm"):
            self._set_pending(user, action)
            return action["preview"]

        if action.get("execute"):
            result = await self.writer.execute(action["tool"], action["params"])
            if not result.get("error"):
                self._invalidate_cache()
            return f"✅ {result.get('message', 'Đã ghi.')}"

        return action.get("reply") or "🤔 Mình chưa hiểu. Gõ 'help' để xem hướng dẫn."

    def _invalidate_cache(self):
        """Xoá cache đọc của web-chat sau khi ghi để tránh trả số liệu cũ."""
        try:
            from app.services import cache_service
            cache_service.invalidate(self.db)
        except Exception as e:  # pragma: no cover - cache best-effort
            logger.warning("Cache invalidate failed: %s", e)

    def _parse_field_intent(self, text: str, user_name: str) -> dict:
        """Parse tin nhắn hiện trường → tạo task / cập nhật task / ghi báo cáo."""
        t = text.strip()
        tl = t.lower()

        # Tạo task / cập nhật task — dùng parser chung với web chat
        write = parse_write_intent(t, user_name)
        if write is not None:
            if not write.get("tool"):  # gợi ý thiếu tên task
                return {"reply": write["preview"]}
            return {
                "needs_confirm": True,
                "tool": write["tool"],
                "params": write["params"],
                "preview": write["preview"],
            }

        # Báo cáo hiện trường: "báo cáo: ..." hoặc "ghi: ..."
        report_prefixes = ("báo cáo:", "bao cao:", "ghi:", "report:", "log:")
        for prefix in report_prefixes:
            if tl.startswith(prefix):
                content = t[len(prefix):].strip()
                if not content:
                    return {"reply": "📝 Gõ nội dung sau 'báo cáo:', VD: báo cáo: Hoàn thành kiểm tra tầng 3"}
                params = {
                    "user": user_name,
                    "task_content": content,
                    "report_date": date.today().isoformat(),
                    "status": "Đang làm",
                    "hours": self._extract_hours(content),
                    "project": self._extract_project(content),
                }
                preview = (
                    f"📝 Ghi báo cáo hiện trường:\n"
                    f"• Người: {user_name}\n"
                    f"• Nội dung: {content[:200]}\n"
                    f"• Giờ: {params['hours'] or '—'}\n\n"
                    f"✅ Gõ 'ok' xác nhận | ❌ 'hủy'"
                )
                return {"needs_confirm": True, "tool": "append_field_report", "params": params, "preview": preview}

        # Mặc định: coi như báo cáo tự do
        if len(t) >= 10:
            params = {
                "user": user_name,
                "task_content": t,
                "report_date": date.today().isoformat(),
                "status": "Đang làm",
                "hours": self._extract_hours(t),
                "project": self._extract_project(t),
            }
            preview = (
                f"📝 Ghi báo cáo:\n• {t[:200]}\n\n✅ Gõ 'ok' | ❌ 'hủy'"
            )
            return {"needs_confirm": True, "tool": "append_field_report", "params": params, "preview": preview}

        return {"reply": self._help_text()}

    @staticmethod
    def _extract_hours(text: str) -> float | None:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:giờ|h|gio)\b", text.lower())
        return float(m.group(1).replace(",", ".")) if m else None

    @staticmethod
    def _extract_project(text: str) -> str:
        keywords = {
            "cao tầng": "Cao tầng", "hạ tầng": "Hạ tầng", "pccc": "PCCC",
            "training": "Training", "core": "Core Team",
        }
        tl = text.lower()
        for k, v in keywords.items():
            if k in tl:
                return v
        return "Hiện trường"

    @staticmethod
    def _help_text() -> str:
        return (
            "📱 **Hướng dẫn chatbot hiện trường**\n\n"
            "• `tạo task <tên> giao <người> deadline <dd/mm/yyyy>` — tạo task mới\n"
            "• `cập nhật CO-001 hoàn thành` — đổi trạng thái task\n"
            "• `báo cáo: <nội dung>` — ghi log vào sheet\n"
            "• Gõ nội dung tự do (≥10 ký tự) → hệ thống hỏi xác nhận\n"
            "• Gửi **tin nhắn thoại** (Telegram) → tự nhận diện nếu có OpenAI\n"
            "• `ok` / `hủy` — xác nhận hoặc hủy thao tác\n\n"
            "_Hỗ trợ Zalo OA & Telegram_"
        )

    def _set_pending(self, user: User, action: dict):
        from app.models.models import Conversation
        conv = self.db.query(Conversation).filter(
            Conversation.user_id == user.id, Conversation.is_active == True,
        ).first()
        if not conv:
            conv = Conversation(user_id=user.id, context={})
            self.db.add(conv)
            self.db.commit()
        ctx = conv.context or {}
        ctx["pending_write"] = {"tool": action["tool"], "params": action["params"]}
        conv.context = ctx
        self.db.commit()

    def _clear_pending(self, user: User):
        from app.models.models import Conversation
        conv = self.db.query(Conversation).filter(
            Conversation.user_id == user.id, Conversation.is_active == True,
        ).first()
        if conv and conv.context:
            ctx = dict(conv.context)
            ctx.pop("pending_write", None)
            conv.context = ctx
            self.db.commit()
