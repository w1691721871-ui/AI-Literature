"""Persisted, summary-only P32 collaboration records."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base

def utc_now() -> datetime: return datetime.now(timezone.utc)

class AgentMessage(Base):
    __tablename__="agent_messages"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    sender_agent: Mapped[str]=mapped_column(String(100),nullable=False)
    receiver_agent: Mapped[str]=mapped_column(String(100),nullable=False)
    message_type: Mapped[str]=mapped_column(String(30),nullable=False)
    payload_summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    status: Mapped[str]=mapped_column(String(30),nullable=False,default="CREATED")
    collaboration_round: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)

class CollaborationGraph(Base):
    __tablename__="collaboration_graphs"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    sender_agent: Mapped[str]=mapped_column(String(100),nullable=False)
    receiver_agent: Mapped[str]=mapped_column(String(100),nullable=False)
    message_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    status: Mapped[str]=mapped_column(String(30),nullable=False,default="ACTIVE")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)

class AgentConflict(Base):
    __tablename__="agent_conflicts"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    source_message_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    participants: Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    conflict_summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    status: Mapped[str]=mapped_column(String(40),nullable=False,default="WAITING_HUMAN_REVIEW")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
