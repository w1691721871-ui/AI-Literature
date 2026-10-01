"""Persisted, user-readable execution graph nodes for dynamic AI Missions."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now() -> datetime: return datetime.now(timezone.utc)

class ExecutionGraph(Base):
    __tablename__ = "execution_graphs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(160), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    node_order: Mapped[int] = mapped_column(Integer, nullable=False)
    depends_on: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="Initial plan")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
