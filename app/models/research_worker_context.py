"""Short-lived, user-visible context for one controlled Worker run."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchWorkerContext(Base):
    """Stores summaries only, never raw documents or hidden model reasoning."""

    __tablename__ = "research_worker_context"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    context_data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
