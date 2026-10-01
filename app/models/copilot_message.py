"""Safe intent and outcome summaries for a Copilot session."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def utc_now(): return datetime.now(timezone.utc)
class CopilotMessage(Base):
    __tablename__="copilot_messages"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    session_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    role: Mapped[str]=mapped_column(String(20),nullable=False)
    content_summary: Mapped[str]=mapped_column(Text,nullable=False)
    intent: Mapped[str]=mapped_column(String(40),nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now)
