"""A concise enterprise audit trail. Prompts and internal reasoning are excluded."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now(): return datetime.now(timezone.utc)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    user_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    action_type: Mapped[str]=mapped_column(String(50),nullable=False)
    resource_type: Mapped[str]=mapped_column(String(50),nullable=False)
    resource_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    mission_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    result: Mapped[str]=mapped_column(String(30),nullable=False,default="SUCCESS")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
