"""Google OAuth SSO: đăng nhập bằng tài khoản Google công ty.

Luồng: /auth/google → Google consent → /auth/google/callback.
Callback đổi `code` lấy id_token, verify, map email→staff (staff.json) để cấp
JWT session token. Nếu email Google (gmail cá nhân) không khớp email công ty,
fallback match theo TÊN hiển thị. Không khớp cả hai → từ chối. KHÔNG dùng mật khẩu.
"""
import logging
import secrets
import time
import urllib.parse

import httpx
import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

from app.config import settings
from app.services.mock_sheets import get_staff_for_google_login
from app.services.auth_token import create_session_token

router = APIRouter()
logger = logging.getLogger(__name__)

# PyJWKClient tự refresh JWKS khi Google rotate key (tránh lỗi kid không tìm thấy).
_jwk_client: PyJWKClient | None = None

# State lưu server-side — tránh lỗi cookie khi user dùng localhost vs 127.0.0.1
# Value: {"ts": float, "redirect_uri": str}
_oauth_states: dict[str, dict] = {}
_STATE_TTL_SEC = 600


def _cleanup_expired_states() -> None:
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if now - v.get("ts", 0) > _STATE_TTL_SEC]
    for k in expired:
        del _oauth_states[k]


def _store_oauth_state(state: str, redirect_uri: str) -> None:
    _cleanup_expired_states()
    _oauth_states[state] = {"ts": time.time(), "redirect_uri": redirect_uri}


def _consume_oauth_state(state: str) -> str | None:
    """Kiểm tra state hợp lệ (dùng một lần). Trả về redirect_uri đã lưu lúc login."""
    if not state:
        return None
    _cleanup_expired_states()
    entry = _oauth_states.pop(state, None)
    if not entry or time.time() - entry.get("ts", 0) > _STATE_TTL_SEC:
        return None
    return entry.get("redirect_uri")


def _oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def _oauth_redirect_uri(request: Request) -> str:
    """Callback OAuth — ưu tiên PUBLIC_BASE_URL, tránh redirect về localhost khi user vào URL public."""
    public = (settings.public_base_url or "").strip().rstrip("/")
    if public:
        return f"{public}/auth/google/callback"

    explicit = (settings.google_redirect_uri or "").strip()
    if explicit and "localhost" not in explicit and "127.0.0.1" not in explicit:
        return explicit

    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    host = host.split(",")[0].strip()
    if host and "localhost" not in host and "127.0.0.1" not in host:
        return f"{proto}://{host}/auth/google/callback"

    return explicit or f"{proto}://{host}/auth/google/callback"


@router.get("/auth/google/status")
async def google_status():
    """Public: OAuth đã cấu hình chưa (không lộ secret)."""
    return {"configured": _oauth_configured()}


@router.get("/auth/google/redirect-uri")
async def google_redirect_uri_info(request: Request):
    """Public: redirect URI app đang dùng — thêm CHÍNH XÁC URI này vào Google Cloud Console."""
    uri = _oauth_redirect_uri(request)
    return {
        "redirect_uri": uri,
        "hint": "Google Cloud Console > OAuth Client > Authorized redirect URIs",
        "console_url": "https://console.cloud.google.com/auth/clients",
    }


_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
# Cho phép lệch giờ máy chủ vs Google (tránh ImmatureSignatureError trên iat/exp).
_JWT_LEEWAY_SEC = 120


def _get_jwk_client(*, force_refresh: bool = False) -> PyJWKClient:
    global _jwk_client
    if force_refresh or _jwk_client is None:
        _jwk_client = PyJWKClient(_CERTS_URL, cache_keys=True, lifespan=300)
    return _jwk_client


def _get_signing_key(id_token: str):
    """Lấy public key theo kid; refresh JWKS một lần nếu Google vừa rotate key."""
    try:
        return _get_jwk_client().get_signing_key_from_jwt(id_token)
    except jwt.PyJWKClientError:
        return _get_jwk_client(force_refresh=True).get_signing_key_from_jwt(id_token)


@router.get("/auth/google")
async def google_login(request: Request):
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth chưa được cấu hình.")
    state = secrets.token_urlsafe(16)
    redirect_uri = _oauth_redirect_uri(request)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    _store_oauth_state(state, redirect_uri)
    return RedirectResponse(f"{_AUTH_URL}?{urllib.parse.urlencode(params)}")


@router.get("/auth/google/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return _result_page(error=f"Google trả về lỗi: {error}")
    if not code:
        return _result_page(error="State không hợp lệ. Vui lòng đăng nhập lại.")
    redirect_uri = _consume_oauth_state(state)
    if not redirect_uri:
        return _result_page(error="State không hợp lệ. Vui lòng đăng nhập lại.")

    async with httpx.AsyncClient(timeout=15.0) as client:
        tok = await client.post(_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        if tok.status_code != 200:
            logger.warning(
                "Google token exchange thất bại: status=%s body=%s",
                tok.status_code,
                tok.text[:500],
            )
            return _result_page(error="Không đổi được token với Google.")
        id_token = tok.json().get("id_token")
        if not id_token:
            return _result_page(error="Google không trả về id_token.")

    try:
        claims = _verify_id_token(id_token)
    except jwt.InvalidAudienceError:
        _log_verify_failure(id_token, jwt.InvalidAudienceError("audience"))
        return _result_page(
            error="Client ID OAuth không khớp token Google. "
                  "Kiểm tra GOOGLE_CLIENT_ID trong .env trùng Client ID trên Google Cloud Console.",
        )
    except jwt.ImmatureSignatureError:
        _log_verify_failure(id_token, jwt.ImmatureSignatureError("iat"))
        return _result_page(
            error="Đồng hồ máy tính/server lệch so với Google. "
                  "Chỉnh lại giờ hệ thống (Windows: Date & time → Đồng bộ ngay) rồi thử lại.",
        )
    except jwt.ExpiredSignatureError:
        return _result_page(error="Phiên Google đã hết hạn. Vui lòng đăng nhập lại.")
    except jwt.PyJWKClientError:
        return _result_page(
            error="Không tải được khóa xác thực của Google. Kiểm tra kết nối mạng rồi thử lại.",
        )
    except Exception as exc:
        _log_verify_failure(id_token, exc)
        return _result_page(error="Xác minh token Google thất bại.")

    if not claims.get("email_verified"):
        return _result_page(error="Email Google chưa được xác minh.")

    email = claims["email"].strip().lower()
    staff, matched_by = get_staff_for_google_login(email, claims.get("name", ""))
    if not staff:
        return _result_page(error=f"Tài khoản Google '{email}' không khớp nhân sự nào "
                                  f"(email công ty / gmail alias / tên). Liên hệ Admin.")

    role = staff.get("role", "member")
    token = create_session_token(staff["email"], role, staff["name"])
    return _result_page(session={
        "success": True, "name": staff["name"], "email": staff["email"],
        "role": role, "token": token, "matched_by": matched_by,
    })


def _log_verify_failure(id_token: str, exc: Exception) -> None:
    """Ghi log chi tiết (server-side) để chẩn đoán lỗi audience/issuer/kid."""
    detail = f"{type(exc).__name__}: {exc}"
    try:
        unverified = jwt.decode(id_token, options={"verify_signature": False})
        detail += (
            f" | aud={unverified.get('aud')!r} azp={unverified.get('azp')!r}"
            f" iss={unverified.get('iss')!r}"
            f" expected_aud={settings.google_client_id!r}"
        )
    except Exception:
        pass
    logger.warning("Xác minh token Google thất bại: %s", detail)


def _audience_matches(claims: dict, client_id: str) -> bool:
    """Google có thể đặt aud là string hoặc list; azp là client thực sự authorize."""
    aud = claims.get("aud")
    if aud == client_id:
        return True
    if isinstance(aud, list) and client_id in aud:
        return True
    return claims.get("azp") == client_id


def _verify_id_token(id_token: str) -> dict:
    """Verify chữ ký RS256, audience (client_id) và issuer của Google id_token."""
    client_id = (settings.google_client_id or "").strip()
    if not client_id:
        raise ValueError("Google OAuth chưa được cấu hình.")

    signing_key = _get_signing_key(id_token)
    decode_kwargs = dict(
        key=signing_key.key,
        algorithms=["RS256"],
        issuer=_GOOGLE_ISSUERS,
        leeway=_JWT_LEEWAY_SEC,
    )
    try:
        return jwt.decode(id_token, audience=client_id, **decode_kwargs)
    except jwt.InvalidAudienceError:
        # Fallback: verify chữ ký/issuer trước, tự kiểm tra aud/azp (tránh false-negative)
        claims = jwt.decode(
            id_token,
            options={"verify_aud": False},
            **decode_kwargs,
        )
        if not _audience_matches(claims, client_id):
            raise jwt.InvalidAudienceError(
                f"aud={claims.get('aud')!r} azp={claims.get('azp')!r} expected={client_id!r}"
            )
        return claims


def _result_page(session: dict = None, error: str = "") -> HTMLResponse:
    """Trang trung gian: lưu session vào localStorage rồi về trang chính (hoặc báo lỗi)."""
    import json
    import html
    if error:
        body = f"""<p style="color:#d32f2f">{html.escape(error)}</p>
        <a href="/">← Quay lại đăng nhập</a>"""
    else:
        body = f"""<p>Đăng nhập thành công, đang chuyển hướng...</p>
        <script>
        const s = {json.dumps(session)};
        s.expires = Date.now() + 24*60*60*1000;
        s.origin = window.location.origin;
        localStorage.setItem('bhi_user_session', JSON.stringify(s));
        location.href = '/';
        </script>"""
    return HTMLResponse(f"""<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
    <title>Đăng nhập</title></head><body style="font-family:system-ui;text-align:center;padding:3rem">
    {body}</body></html>""")
