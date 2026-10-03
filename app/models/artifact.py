"""P30 versioned, approval-gated enterprise delivery artifacts."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def utc_now(): return datetime.now(timezone.utc)
class Artifact(Base):
    __tablename__="artifacts"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    project_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    artifact_type: Mapped[str]=mapped_column(String(40),nullable=False)
    title: Mapped[str]=mapped_column(String(240),nullable=False)
    version: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    status: Mapped[str]=mapped_column(String(40),nullable=False,default="DRAFT")
    release_status: Mapped[str]=mapped_column(String(30),nullable=False,default="DRAFT")
    source_type: Mapped[str]=mapped_column(String(40),nullable=False,default="AI_GENERATED")
    file_path: Mapped[str]=mapped_column(String(1000),nullable=False,default="")
    content_summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    evidence_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    evidence_coverage: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    generation_rounds: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    created_by: Mapped[str]=mapped_column(String(100),nullable=False,default="Artifact Agent")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,onupdate=utc_now)
class ArtifactVersion(Base):
    __tablename__="artifact_versions"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    artifact_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    version: Mapped[int]=mapped_column(Integer,nullable=False)
    change_summary: Mapped[str]=mapped_column(Text,nullable=False)
    content_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    created_by: Mapped[str]=mapped_column(String(100),nullable=False,default="Artifact Agent")
class ArtifactEvidence(Base):
    __tablename__="artifact_evidence"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    artifact_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    evidence_type: Mapped[str]=mapped_column(String(40),nullable=False)
    paper_id: Mapped[str|None]=mapped_column(String(36),nullable=True)
    chunk_id: Mapped[str|None]=mapped_column(String(36),nullable=True)
    source: Mapped[str]=mapped_column(String(500),nullable=False)
    section: Mapped[str]=mapped_column(String(500),nullable=False,default="")
    claim_summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
