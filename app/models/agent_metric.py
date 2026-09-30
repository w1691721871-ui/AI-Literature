"""Aggregate, user-readable Agent quality metrics; no model reasoning is stored."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now() -> datetime: return datetime.now(timezone.utc)

class AgentMetric(Base):
    __tablename__ = "agent_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    total_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_duration: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_evidence_count: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
