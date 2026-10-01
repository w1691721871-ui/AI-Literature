"""P38 user-readable workspace activity and review comments; no prompts or CoT."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def now(): return datetime.now(timezone.utc)
class ActivityEvent(Base):
    __tablename__="activity_events"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    source_event_id: Mapped[str]=mapped_column(String(36),nullable=False,unique=True,index=True)
    event_type: Mapped[str]=mapped_column(String(40),nullable=False)
    title: Mapped[str]=mapped_column(String(180),nullable=False)
    summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
class ArtifactComment(Base):
    __tablename__="artifact_comments"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    artifact_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    reviewer_id: Mapped[str]=mapped_column(String(80),nullable=False)
    comment: Mapped[str]=mapped_column(Text,nullable=False)
    status: Mapped[str]=mapped_column(String(40),nullable=False,default="COMMENTED")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
