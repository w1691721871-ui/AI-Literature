"""P37 explicit, non-production enterprise demo scenario metadata."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def now(): return datetime.now(timezone.utc)

class EnterpriseScenario(Base):
    __tablename__ = "enterprise_scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    industry: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    customer_need: Mapped[str] = mapped_column(Text, nullable=False)
    expected_agents_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    expected_tools_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now)

class ScenarioRun(Base):
    __tablename__ = "scenario_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    benchmark_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="READY")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now)

class DemoDataSource(Base):
    __tablename__ = "demo_data_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    classification: Mapped[str] = mapped_column(String(30), nullable=False, default="DEMO_ONLY")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now)
