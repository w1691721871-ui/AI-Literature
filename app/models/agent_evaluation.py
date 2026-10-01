"""Evidence-bounded evaluation record for an AI Mission."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now() -> datetime: return datetime.now(timezone.utc)

class AgentEvaluation(Base):
    __tablename__ = "agent_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    evaluation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planner_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adaptive_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    replan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_retrieval_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_decision: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    task_completion: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    evidence_coverage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    human_revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_result: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_APPLICABLE")
    execution_safety: Mapped[str] = mapped_column(String(40), nullable=False, default="PASS")
    failure_type: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
