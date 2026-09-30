"""Approval-gated file change snapshots for P18 Computer Use."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime: return datetime.now(timezone.utc)


class ComputerFileChange(Base):
    __tablename__ = "computer_file_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False)
    before_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    after_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    diff_content: Mapped[str] = mapped_column(Text, nullable=False)
    before_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    after_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
