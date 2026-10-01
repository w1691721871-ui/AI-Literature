from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import DateTime,Float,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.services.database import Base
def now():return datetime.now(timezone.utc)
class ComputerVisionObservation(Base):
 __tablename__='computer_vision_observations';id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));mission_id:Mapped[str]=mapped_column(String(36),index=True);environment_id:Mapped[str]=mapped_column(String(36));observation_type:Mapped[str]=mapped_column(String(30));image_reference:Mapped[str]=mapped_column(String(240),default='SAFE_REFERENCE_ONLY');detected_elements:Mapped[str]=mapped_column(Text,default='[]');screen_summary:Mapped[str]=mapped_column(Text);confidence:Mapped[float]=mapped_column(Float,default=0.0);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ComputerUIElement(Base):
 __tablename__='computer_ui_elements';id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));mission_id:Mapped[str]=mapped_column(String(36),index=True);element_type:Mapped[str]=mapped_column(String(40));name:Mapped[str]=mapped_column(String(120));location:Mapped[str]=mapped_column(String(80),default='unknown');confidence:Mapped[float]=mapped_column(Float,default=0.0);available_actions:Mapped[str]=mapped_column(Text,default='[]')
class ComputerSimulationSession(Base):
 __tablename__='computer_simulation_sessions';id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()));mission_id:Mapped[str]=mapped_column(String(36),index=True);scenario:Mapped[str]=mapped_column(String(120));current_screen:Mapped[str]=mapped_column(Text);actions:Mapped[str]=mapped_column(Text,default='[]');status:Mapped[str]=mapped_column(String(30),default='WAITING_APPROVAL')
