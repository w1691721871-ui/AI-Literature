"""P36 benchmark definitions and observed evaluation results."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def now(): return datetime.now(timezone.utc)

class BenchmarkTask(Base):
    __tablename__="benchmark_tasks"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    name: Mapped[str]=mapped_column(String(180),nullable=False)
    category: Mapped[str]=mapped_column(String(30),nullable=False)
    difficulty: Mapped[str]=mapped_column(String(20),nullable=False)
    description: Mapped[str]=mapped_column(Text,nullable=False)
    expected_agents_json: Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    expected_tools_json: Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    evaluation_rules_json: Mapped[str]=mapped_column(Text,nullable=False,default="{}")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)

class BenchmarkRun(Base):
    __tablename__="benchmark_runs"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    task_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    status: Mapped[str]=mapped_column(String(20),nullable=False,default="RUNNING")
    score: Mapped[float|None]=mapped_column(Float,nullable=True)
    runtime_version: Mapped[str]=mapped_column(String(40),nullable=False,default="P35")
    planner_version: Mapped[str]=mapped_column(String(40),nullable=False,default="v1")
    model_version: Mapped[str]=mapped_column(String(100),nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)

class BenchmarkScore(Base):
    __tablename__="benchmark_scores"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    benchmark_id: Mapped[str]=mapped_column(String(36),nullable=False,unique=True,index=True)
    planning_score: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    tool_score: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    evidence_score: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    artifact_score: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    safety_score: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    human_score: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    total_score: Mapped[float]=mapped_column(Float,nullable=False,default=0)

class AgentVersion(Base):
    __tablename__="agent_versions"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    runtime_version: Mapped[str]=mapped_column(String(40),nullable=False)
    planner_version: Mapped[str]=mapped_column(String(40),nullable=False)
    model_version: Mapped[str]=mapped_column(String(100),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
