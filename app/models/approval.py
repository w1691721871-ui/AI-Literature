"""Workspace-scoped, human approval requests without model reasoning content."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now(): return datetime.now(timezone.utc)

class ApprovalRequest(Base):
    __tablename__="approval_requests"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    mission_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    source_type: Mapped[str]=mapped_column(String(40),nullable=False)
    source_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    request_type: Mapped[str]=mapped_column(String(40),nullable=False)
    creator_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    reviewer_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    status: Mapped[str]=mapped_column(String(30),nullable=False,default="PENDING")
    priority: Mapped[str]=mapped_column(String(20),nullable=False,default="NORMAL")
    comment: Mapped[str]=mapped_column(Text,nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,onupdate=utc_now)
    resolved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
