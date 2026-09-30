"""Minimal, non-sensitive local onboarding state for the product experience."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserOnboardingState(Base):
    __tablename__ = "user_onboarding_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    first_visit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    completed_steps_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
