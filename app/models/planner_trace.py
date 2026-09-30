"""Safe planner decision records. No prompts or hidden reasoning are stored."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now() -> datetime: return datetime.now(timezone.utc)

class PlannerTrace(Base):
    __tablename__ = "planner_traces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    planner_action: Mapped[str] = mapped_column(String(160), nullable=False, default="PLAN_CREATED")
    selected_agents_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    skipped_agents_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reason_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
