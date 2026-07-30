from fastapi import FastAPI
from contextlib import asynccontextmanager
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.db import engine, Base
from app.models.models import User, Conversation, Message, ToolCall, TaskCache, AuditLog  # noqa
from app.api.health import router as health_router
from app.api.admin import router as admin_router
from app.api.chat import router as mock_chat_router
from app.api.chat_ui import router as chat_ui_router
from app.api.dashboard import router as dashboard_router
from app.api.dashboard_ui import router_dashboard_ui
from app.api.auth_google import router as auth_google_router
from app.api.messaging import router as messaging_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="BHI AI Agent", lifespan=lifespan)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.include_router(health_router)
app.include_router(admin_router)
app.include_router(mock_chat_router)
app.include_router(chat_ui_router)
app.include_router(dashboard_router)
app.include_router(router_dashboard_ui)
app.include_router(auth_google_router)
app.include_router(messaging_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)