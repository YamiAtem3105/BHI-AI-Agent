"""Webhook Zalo OA & Telegram Bot — ghi task/báo cáo vào sheet."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services.auth_token import get_current_user
from app.services.messaging_links import (
    bootstrap_links_from_staff,
    list_links_for_viewer,
    list_pending,
    upsert_link,
)
from app.services.messaging_service import MessagingService
from app.services.rbac import normalize_role

router = APIRouter(prefix="/api/messaging")


def _is_production() -> bool:
    return (settings.environment or "").strip().lower() == "production"


def _verify_telegram_secret(request: Request):
    secret = settings.telegram_webhook_secret
    if not secret:
        if _is_production() and settings.telegram_bot_token:
            raise HTTPException(
                status_code=503,
                detail="Telegram webhook secret chưa cấu hình (bắt buộc ở production)",
            )
        return
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if token != secret:
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")


def _verify_zalo_secret(request: Request):
    secret = settings.zalo_webhook_secret
    if not secret:
        if _is_production() and settings.zalo_oa_access_token:
            raise HTTPException(
                status_code=503,
                detail="Zalo webhook secret chưa cấu hình (bắt buộc ở production)",
            )
        return
    token = request.headers.get("X-Zalo-Secret", "") or request.query_params.get("secret", "")
    if token != secret:
        raise HTTPException(status_code=401, detail="Invalid Zalo webhook secret")


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_telegram_secret),
):
    """Nhận update từ Telegram Bot API. Cấu hình webhook:
    POST https://api.telegram.org/bot<TOKEN>/setWebhook
    body: {"url": "https://<domain>/api/messaging/telegram", "secret_token": "<secret>"}
    """
    update = await request.json()
    svc = MessagingService(db)
    result = await svc.handle_telegram_update(update)

    # Trả lời qua Telegram API nếu có token
    if settings.telegram_bot_token and result.get("method") == "sendMessage":
        import httpx
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json={
                "chat_id": result["chat_id"],
                "text": result["text"],
            })

    return {"ok": True}


@router.post("/zalo")
async def zalo_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_zalo_secret),
):
    """Nhận event từ Zalo Official Account webhook."""
    event = await request.json()
    svc = MessagingService(db)
    result = await svc.handle_zalo_event(event)

    if settings.zalo_oa_access_token and result.get("message"):
        import httpx
        url = "https://openapi.zalo.me/v3.0/oa/message/cs"
        headers = {"access_token": settings.zalo_oa_access_token}
        payload = {
            "recipient": result["recipient"],
            "message": result["message"],
        }
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload, headers=headers)

    return {"ok": True}


@router.get("/status")
async def messaging_status():
    """Kiểm tra cấu hình kênh chat."""
    base = (settings.public_base_url or "").rstrip("/")
    return {
        "telegram": {
            "enabled": bool(settings.telegram_bot_token),
            "webhook_path": "/api/messaging/telegram",
            "webhook_url": f"{base}/api/messaging/telegram" if base else None,
            "secret_configured": bool(settings.telegram_webhook_secret),
            "setup": "python scripts/setup_messaging_webhooks.py",
        },
        "zalo": {
            "enabled": bool(settings.zalo_oa_access_token),
            "webhook_path": "/api/messaging/zalo",
            "webhook_url": f"{base}/api/messaging/zalo?secret=<ZALO_WEBHOOK_SECRET>" if base else None,
            "secret_configured": bool(settings.zalo_webhook_secret),
            "setup": "python scripts/setup_messaging_webhooks.py",
        },
        "links_file": "data/messaging_links.json",
        "pending_unlinked": len(list_pending()),
        "field_report": True,
        "supported_commands": [
            "tạo task <tên> giao <người> deadline <dd/mm/yyyy>",
            "cập nhật <TASK_ID> <trạng thái>",
            "báo cáo: <nội dung>",
            "ok / hủy (xác nhận)",
            "/start (Telegram — lấy chat_id)",
        ],
    }


@router.get("/links")
async def messaging_links(user: dict = Depends(get_current_user)):
    """Danh sách liên kết Zalo/Telegram — admin/manager: tất cả; member: của mình."""
    role = normalize_role(user.get("role"))
    if role == "member" and not user.get("email"):
        raise HTTPException(status_code=403, detail="Khong co quyen")
    return {"links": list_links_for_viewer(role, user.get("email", ""))}


@router.post("/bootstrap")
async def messaging_bootstrap(user: dict = Depends(get_current_user)):
    """Admin: tạo messaging_links.json từ staff.json."""
    role = normalize_role(user.get("role"))
    if role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Chi admin duoc bootstrap links")
    count = bootstrap_links_from_staff()
    return {"ok": True, "links_count": count}


@router.get("/pending")
async def messaging_pending(user: dict = Depends(get_current_user)):
    """Admin: danh sách ID chưa liên kết (từ tin nhắn lạ)."""
    role = normalize_role(user.get("role"))
    if role not in ("admin", "super_admin", "manager"):
        raise HTTPException(status_code=403, detail="Khong co quyen")
    return {"pending": list_pending()}


@router.post("/link")
async def messaging_link(request: Request, user: dict = Depends(get_current_user)):
    """Admin: liên kết email nhân sự <-> telegram_chat_id / zalo_user_id."""
    role = normalize_role(user.get("role"))
    if role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Chi admin duoc lien ket")
    body = await request.json()
    email = body.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Thieu email")
    row = upsert_link(
        email=email,
        name=body.get("name", ""),
        telegram_chat_id=body.get("telegram_chat_id", ""),
        zalo_user_id=body.get("zalo_user_id", ""),
    )
    return {"ok": True, "link": row}
