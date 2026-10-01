"""Finite, user-readable adaptive decisions for an AI Mission."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def utc_now(): return datetime.now(timezone.utc)
class AdaptiveIteration(Base):
    __tablename__="adaptive_iterations"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    mission_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    iteration: Mapped[int]=mapped_column(Integer,nullable=False)
    trigger: Mapped[str]=mapped_column(String(80),nullable=False)
    previous_state: Mapped[str]=mapped_column(String(60),nullable=False)
    decision: Mapped[str]=mapped_column(String(60),nullable=False)
    graph_version: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
