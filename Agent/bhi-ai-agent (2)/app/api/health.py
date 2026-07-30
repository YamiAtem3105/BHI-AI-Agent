from fastapi import APIRouter

from app.config import settings
from app.services.openai_compat import model_catalog

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/api/config/openai-models")
async def openai_models():
    """Danh sách model OpenAI gợi ý — chọn qua OPENAI_MODEL trong .env."""
    return model_catalog(settings.openai_model)
