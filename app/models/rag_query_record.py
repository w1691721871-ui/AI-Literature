"""SQLite model for saved multi-paper RAG questions and generated reports."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RagQueryRecord(Base):
    """Persist a lightweight RAG interaction without storing paper full text."""

    __tablename__ = "rag_query_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str] = mapped_column(Text, nullable=False)
    paper_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, default="question")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
