"""Task cache layer: memoize read-tool results in TaskCache (TTL), clear on writes."""
import hashlib
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import TaskCache

READ_TOOLS = ("search_tasks", "get_task_detail", "get_subtasks", "search_archive")


def _key(tool_name: str, params: dict) -> str:
    raw = tool_name + ":" + json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def get_cached(db: Session, tool_name: str, params: dict) -> dict | None:
    row = db.query(TaskCache).filter(TaskCache.task_id == _key(tool_name, params)).first()
    if not row:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        db.delete(row)
        db.commit()
        return None
    return row.data


def set_cache(db: Session, tool_name: str, params: dict, data: dict):
    now = datetime.now(timezone.utc)
    row = db.query(TaskCache).filter(TaskCache.task_id == _key(tool_name, params)).first()
    if row:
        row.data, row.cached_at = data, now
        row.expires_at = now + timedelta(seconds=settings.cache_ttl_seconds)
    else:
        db.add(TaskCache(task_id=_key(tool_name, params), sheet_name=tool_name, data=data,
                         cached_at=now, expires_at=now + timedelta(seconds=settings.cache_ttl_seconds)))
    db.commit()


def invalidate(db: Session):
    db.query(TaskCache).delete()
    db.commit()
