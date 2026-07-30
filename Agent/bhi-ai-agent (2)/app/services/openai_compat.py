"""Tương thích tham số OpenAI Chat Completions giữa các đời model."""
from __future__ import annotations

# Gợi ý model — user chọn qua OPENAI_MODEL trong .env
OPENAI_CHAT_MODELS: list[dict] = [
    {
        "id": "gpt-4o-mini",
        "token_param": "max_tokens",
        "supports_tools": True,
        "supports_stream": True,
        "note": "Rẻ, ổn định — khuyến nghị production nếu chưa cần GPT-5",
    },
    {
        "id": "gpt-4o",
        "token_param": "max_tokens",
        "supports_tools": True,
        "supports_stream": True,
        "note": "Chất lượng cao hơn 4o-mini, chi phí cao hơn",
    },
    {
        "id": "gpt-4.1-mini",
        "token_param": "max_completion_tokens",
        "supports_tools": True,
        "supports_stream": True,
        "note": "Model mới — dùng max_completion_tokens",
    },
    {
        "id": "gpt-4.1",
        "token_param": "max_completion_tokens",
        "supports_tools": True,
        "supports_stream": True,
        "note": "GPT-4.1 full — reasoning tốt hơn 4o",
    },
    {
        "id": "gpt-5.4-mini",
        "token_param": "max_completion_tokens",
        "supports_tools": True,
        "supports_stream": True,
        "note": "Mặc định hiện tại — nhẹ, phù hợp routing tool",
    },
    {
        "id": "gpt-5.4",
        "token_param": "max_completion_tokens",
        "supports_tools": True,
        "supports_stream": True,
        "note": "GPT-5.4 full — chất lượng cao nhất trong nhóm 5.x",
    },
    {
        "id": "o4-mini",
        "token_param": "max_completion_tokens",
        "supports_tools": True,
        "supports_stream": False,
        "note": "Reasoning model — có thể chậm hơn, không stream polish",
    },
]


def uses_max_completion_tokens(model: str) -> bool:
    """GPT-5.x / o-series / gpt-4.1+ dùng max_completion_tokens thay max_tokens."""
    m = (model or "").strip().lower()
    if not m:
        return False
    prefixes = (
        "gpt-5",
        "gpt-4.1",
        "chatgpt-4o-latest",
        "o1",
        "o3",
        "o4",
    )
    return any(m.startswith(p) for p in prefixes)


def completion_limit_kwargs(model: str, limit: int) -> dict:
    """Trả dict tham số giới hạn token phù hợp model."""
    if uses_max_completion_tokens(model):
        return {"max_completion_tokens": limit}
    return {"max_tokens": limit}


def model_catalog(current: str | None = None) -> dict:
    """Danh sách model gợi ý + model đang cấu hình."""
    cur = (current or "").strip()
    known = {m["id"] for m in OPENAI_CHAT_MODELS}
    items = list(OPENAI_CHAT_MODELS)
    if cur and cur not in known:
        items.insert(0, {
            "id": cur,
            "token_param": "max_completion_tokens" if uses_max_completion_tokens(cur) else "max_tokens",
            "supports_tools": True,
            "supports_stream": True,
            "note": "Model tùy chỉnh từ OPENAI_MODEL",
        })
    return {
        "current": cur or None,
        "models": items,
        "hint": "Đặt OPENAI_MODEL trong .env rồi restart app. Model gpt-5.x/o-series cần max_completion_tokens.",
    }
