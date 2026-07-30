"""Load/save mapping Telegram & Zalo ID <-> nhân sự."""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
LINKS_PATH = os.path.join(DATA_DIR, "messaging_links.json")
PENDING_PATH = os.path.join(DATA_DIR, "messaging_pending.json")

_links_cache: list | None = None


def _load_links() -> list:
    global _links_cache
    if _links_cache is not None:
        return _links_cache
    if os.path.exists(LINKS_PATH):
        with open(LINKS_PATH, encoding="utf-8") as f:
            _links_cache = json.load(f)
    else:
        _links_cache = []
    return _links_cache


def find_staff_by_platform(platform: str, platform_id: str) -> dict | None:
    pid = str(platform_id).strip()
    key = "telegram_chat_id" if platform == "telegram" else "zalo_user_id"
    for row in _load_links():
        if str(row.get(key, "")).strip() == pid:
            return row
    return None


def find_staff_by_email(email: str) -> dict | None:
    email_key = email.strip().lower()
    for row in _load_links():
        if row.get("email", "").strip().lower() == email_key:
            return row
    return None


def log_pending_link(platform: str, platform_id: str, display_name: str = "") -> None:
    """Ghi ID chưa map de admin dien sau."""
    pending = []
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, encoding="utf-8") as f:
            pending = json.load(f)
    pid = str(platform_id)
    if any(p.get("platform") == platform and p.get("platform_id") == pid for p in pending):
        return
    pending.append({
        "platform": platform,
        "platform_id": pid,
        "display_name": display_name,
    })
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(pending[-100:], f, ensure_ascii=False, indent=2)


def list_pending() -> list:
    if not os.path.exists(PENDING_PATH):
        return []
    with open(PENDING_PATH, encoding="utf-8") as f:
        return json.load(f)


def list_links() -> list:
    return list(_load_links())


def list_links_for_viewer(viewer_role: str, viewer_email: str) -> list:
    """Admin/manager xem tất cả; member chỉ xem bản ghi của mình."""
    links = list_links()
    role = (viewer_role or "member").strip().lower()
    if role in ("super_admin", "admin", "manager"):
        return links
    email_key = (viewer_email or "").strip().lower()
    return [r for r in links if r.get("email", "").strip().lower() == email_key]


def clear_pending(platform: str, platform_id: str) -> None:
    pending = list_pending()
    pid = str(platform_id)
    pending = [p for p in pending if not (p.get("platform") == platform and p.get("platform_id") == pid)]
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)


def upsert_link(email: str, name: str = "", telegram_chat_id: str = "", zalo_user_id: str = "") -> dict:
    links = _load_links()
    email_key = email.strip().lower()
    row = next((r for r in links if r.get("email", "").lower() == email_key), None)
    if not row:
        row = {"email": email_key, "name": name}
        links.append(row)
    if name:
        row["name"] = name
    if telegram_chat_id:
        row["telegram_chat_id"] = str(telegram_chat_id)
    if zalo_user_id:
        row["zalo_user_id"] = str(zalo_user_id)
    with open(LINKS_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    global _links_cache
    _links_cache = links
    if telegram_chat_id:
        clear_pending("telegram", telegram_chat_id)
    if zalo_user_id:
        clear_pending("zalo", zalo_user_id)
    return row


def bootstrap_links_from_staff() -> int:
    """Tao messaging_links.json tu staff.json neu chua co."""
    if os.path.exists(LINKS_PATH):
        return len(_load_links())
    staff_path = os.path.join(DATA_DIR, "staff.json")
    with open(staff_path, encoding="utf-8") as f:
        staff = json.load(f)
    links = []
    for s in staff:
        if s.get("role") in ("admin", "super_admin"):
            continue
        links.append({
            "email": s["email"],
            "name": s["name"],
            "telegram_chat_id": s.get("telegram_chat_id", ""),
            "zalo_user_id": s.get("zalo_user_id", ""),
        })
    with open(LINKS_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    global _links_cache
    _links_cache = links
    return len(links)
