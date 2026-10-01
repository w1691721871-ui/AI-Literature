"""Summary-only P28 Copilot sessions; no raw conversation transcript."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def utc_now(): return datetime.now(timezone.utc)
class CopilotSession(Base):
    __tablename__="copilot_sessions"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    user_id: Mapped[str]=mapped_column(String(100),nullable=False,default="local-user")
    conversation_summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    current_mission_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    status: Mapped[str]=mapped_column(String(30),nullable=False,default="ACTIVE")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
