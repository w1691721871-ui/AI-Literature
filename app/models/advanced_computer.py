from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import DateTime,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.services.database import Base
def now():return datetime.now(timezone.utc)
class ComputerEnvironment(Base):
 __tablename__="computer_environments";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));mission_id:Mapped[str]=mapped_column(String(36),index=True);application:Mapped[str]=mapped_column(String(100),default="Workspace");window_title:Mapped[str]=mapped_column(String(240),default="");screen_summary:Mapped[str]=mapped_column(Text,default="Structured environment summary only.");available_actions:Mapped[str]=mapped_column(Text,default="[]");current_state:Mapped[str]=mapped_column(Text,default="{}");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class ComputerPlan(Base):
 __tablename__="computer_plans";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));mission_id:Mapped[str]=mapped_column(String(36),index=True);goal:Mapped[str]=mapped_column(Text);steps:Mapped[str]=mapped_column(Text,default="[]");risk_level:Mapped[str]=mapped_column(String(20),default="LOW");status:Mapped[str]=mapped_column(String(30),default="WAITING_APPROVAL");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ComputerObservation(Base):
 __tablename__="computer_observations";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));mission_id:Mapped[str]=mapped_column(String(36),index=True);environment_id:Mapped[str]=mapped_column(String(36));observation_type:Mapped[str]=mapped_column(String(20));summary:Mapped[str]=mapped_column(Text);detected_elements:Mapped[str]=mapped_column(Text,default="[]");created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ComputerExperience(Base):
 __tablename__="computer_experiences";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));task_type:Mapped[str]=mapped_column(String(80));solution_steps:Mapped[str]=mapped_column(Text);success_rate:Mapped[str]=mapped_column(String(20),default="0");approval_status:Mapped[str]=mapped_column(String(30),default="DRAFT")
