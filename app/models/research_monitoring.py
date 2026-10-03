from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
class ResearchMonitoringTask(Base):
 __tablename__="research_monitoring_tasks"
 id:Mapped[str]=mapped_column(String(64),primary_key=True,default=lambda:str(uuid4()))
 workspace_id:Mapped[str]=mapped_column(String(64),index=True)
 topic:Mapped[str]=mapped_column(String(500)); goal:Mapped[str]=mapped_column(Text,default="")
 keywords_json:Mapped[str]=mapped_column(Text,default="[]"); baseline_json:Mapped[str]=mapped_column(Text,default="[]")
 status:Mapped[str]=mapped_column(String(40),default="ACTIVE")
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))
