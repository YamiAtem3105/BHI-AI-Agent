from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    google_chat_id = Column(String(255), unique=True, nullable=True)
    display_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), default="member")
    department = Column(String(100))
    masterplan_name = Column(String(100))
    personal_sheet_id = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversations = relationship("Conversation", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_message_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    context = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    tool_calls = relationship("ToolCall", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")


class ToolCall(Base):
    __tablename__ = "tool_calls"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    tool_name = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=False)
    result = Column(JSON)
    status = Column(String(20), default="pending")
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="tool_calls")


class TaskCache(Base):
    __tablename__ = "task_cache"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(50), nullable=False)
    sheet_name = Column(String(100))
    data = Column(JSON, nullable=False)
    cached_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(20), nullable=False)
    target_task_id = Column(String(50))
    payload = Column(JSON)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")
