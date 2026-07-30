"""Đăng ký webhook Telegram & Zalo OA trỏ về BHI Agent."""
import json
import os
import secrets
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from app.config import settings  # noqa: E402


def _base_url() -> str:
    url = (settings.public_base_url or os.environ.get("PUBLIC_BASE_URL", "")).strip().rstrip("/")
    if not url:
        raise SystemExit(
            "Thieu PUBLIC_BASE_URL trong .env (vd: https://bhi-ai-agent.onrender.com)"
        )
    return url


def setup_telegram(base: str, secret: str | None = None) -> dict:
    token = settings.telegram_bot_token
    if not token:
        return {"skipped": True, "reason": "TELEGRAM_BOT_TOKEN chua cau hinh"}

    webhook_secret = secret or settings.telegram_webhook_secret or secrets.token_urlsafe(24)
    webhook_url = f"{base}/api/messaging/telegram"

    r = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": webhook_url,
            "secret_token": webhook_secret,
            "allowed_updates": ["message", "edited_message"],
            "drop_pending_updates": True,
        },
        timeout=30,
    )
    data = r.json()
    if not data.get("ok"):
        return {"ok": False, "response": data}

    info = httpx.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=15).json()
    return {
        "ok": True,
        "webhook_url": webhook_url,
        "secret_token": webhook_secret,
        "webhook_info": info.get("result", {}),
        "env_hint": f"TELEGRAM_WEBHOOK_SECRET={webhook_secret}",
    }


def setup_zalo(base: str, secret: str | None = None) -> dict:
    token = settings.zalo_oa_access_token
    if not token:
        return {"skipped": True, "reason": "ZALO_OA_ACCESS_TOKEN chua cau hinh"}

    webhook_secret = secret or settings.zalo_webhook_secret or secrets.token_urlsafe(16)
    webhook_url = f"{base}/api/messaging/zalo?secret={webhook_secret}"

    # Zalo OA: dang ky webhook qua Open API
    r = httpx.post(
        "https://openapi.zalo.me/v2.0/oa/webhook",
        params={"access_token": token},
        json={"webhook_url": webhook_url, "secret_key": webhook_secret},
        timeout=30,
    )
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text, "status": r.status_code}

    return {
        "ok": r.status_code == 200 and data.get("error", 0) == 0,
        "webhook_url": webhook_url,
        "secret_key": webhook_secret,
        "response": data,
        "env_hint": f"ZALO_WEBHOOK_SECRET={webhook_secret}",
        "manual_note": "Neu API loi, dang ky thu cong tai https://developers.zalo.me/ -> OA -> Webhook",
    }


def main():
    base = _base_url()
    print(f"PUBLIC_BASE_URL = {base}\n")

    tg = setup_telegram(base)
    print("=== TELEGRAM ===")
    print(json.dumps(tg, ensure_ascii=False, indent=2))

    zalo = setup_zalo(base)
    print("\n=== ZALO OA ===")
    print(json.dumps(zalo, ensure_ascii=False, indent=2))

    print("\n=== LUU VAO .env ===")
    for block in (tg, zalo):
        if block.get("env_hint"):
            print(block["env_hint"])
    print("\nCopy data/messaging_links.example.json -> data/messaging_links.json va dien chat_id.")


if __name__ == "__main__":
    main()
