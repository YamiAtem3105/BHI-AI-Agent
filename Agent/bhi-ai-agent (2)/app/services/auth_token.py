"""Shared JWT session tokens for web chat + dashboard."""
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException
from app.config import settings

ALGO = "HS256"
TTL_HOURS = 24


def create_session_token(email: str, role: str, name: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": email, "role": role, "name": name,
               "iat": now, "exp": now + timedelta(hours=TTL_HOURS)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_session_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None


def get_current_user(request: Request) -> dict:
    token = _bearer(request)
    if not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    try:
        p = decode_session_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
    return {"email": p["sub"], "role": p.get("role", "member"), "name": p.get("name", "")}


def get_user_query_or_header(request: Request) -> dict:
    """Như get_current_user nhưng cũng chấp nhận ?token= (dùng cho link tải file)."""
    token = _bearer(request) or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    try:
        p = decode_session_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")
    return {"email": p["sub"], "role": p.get("role", "member"), "name": p.get("name", "")}


def get_optional_user(request: Request) -> dict | None:
    try:
        return get_current_user(request)
    except HTTPException:
        return None
