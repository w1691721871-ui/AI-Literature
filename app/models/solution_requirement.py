"""Draft requirement parsing records. They never represent customer confirmation by default."""

from uuid import uuid4

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


class SolutionRequirement(Base):
    __tablename__ = "solution_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    solution_project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requirement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="AI_GENERATED_DRAFT")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_CONFIRMATION")
