from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # "production" để bắt buộc webhook secret
    database_url: str = "sqlite:///bhi_agent.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    apps_script_url: str = ""
    apps_script_secret: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    zalo_oa_access_token: str = ""
    zalo_webhook_secret: str = ""
    cache_ttl_seconds: int = 300

    # URL public cố định (Render/Railway/Cloudflare tunnel). Dùng cho OAuth callback.
    # Ví dụ: https://bhi-ai-agent.onrender.com
    public_base_url: str = ""

    # Google OAuth (SSO đăng nhập web). Lấy từ Google Cloud Console > Credentials.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    @field_validator(
        "public_base_url", "google_client_id", "google_client_secret", "google_redirect_uri",
        mode="before",
    )
    @classmethod
    def _strip_oauth_fields(cls, value):
        return value.strip().rstrip("/") if isinstance(value, str) else value

    # Bắt buộc từ env - không có default để tránh leak secret hardcode.
    jwt_secret: str
    admin_username: str
    admin_password: str


settings = Settings()
