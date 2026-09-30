"""Reviewable compact Agent memory, distinct from RAG source knowledge."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now() -> datetime: return datetime.now(timezone.utc)

class AgentMemory(Base):
    __tablename__ = "agent_memories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, default="MISSION_MEMORY")
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Planner Agent")
    content_summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_mission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING_REVIEW")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
