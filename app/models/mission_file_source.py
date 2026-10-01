"""Traceable link from an existing AI Mission to customer-provided source material."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base


def utc_now(): return datetime.now(timezone.utc)


class MissionFileSource(Base):
    __tablename__ = "mission_file_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
