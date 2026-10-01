"""Versioned prompt-template metadata only; template bodies and inputs are not persisted."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now(): return datetime.now(timezone.utc)

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    schema_version: Mapped[str] = mapped_column(String(30), nullable=False, default="structured-plan-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
