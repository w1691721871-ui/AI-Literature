"""P39 governed decision and enterprise knowledge asset records."""
from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import DateTime,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.services.database import Base
def now():return datetime.now(timezone.utc)
class DecisionRecord(Base):
 __tablename__="decision_records"
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
 mission_id:Mapped[str]=mapped_column(String(36),nullable=False,unique=True,index=True)
 workspace_id:Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
 title:Mapped[str]=mapped_column(String(240),nullable=False);problem_summary:Mapped[str]=mapped_column(Text,nullable=False,default="")
 decision_summary:Mapped[str]=mapped_column(Text,nullable=False,default="");selected_solution:Mapped[str]=mapped_column(Text,nullable=False,default="")
 evidence_refs_json:Mapped[str]=mapped_column(Text,nullable=False,default="[]");artifact_refs_json:Mapped[str]=mapped_column(Text,nullable=False,default="[]")
 review_status:Mapped[str]=mapped_column(String(30),nullable=False,default="DRAFT");created_by:Mapped[str]=mapped_column(String(100),nullable=False,default="Decision Memory Service")
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
class KnowledgeAsset(Base):
 __tablename__="knowledge_assets"
 id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
 decision_id:Mapped[str|None]=mapped_column(String(36),nullable=True,index=True);asset_type:Mapped[str]=mapped_column(String(40),nullable=False)
 source_type:Mapped[str]=mapped_column(String(40),nullable=False);title:Mapped[str]=mapped_column(String(240),nullable=False);summary:Mapped[str]=mapped_column(Text,nullable=False)
 references_json:Mapped[str]=mapped_column(Text,nullable=False,default="[]");confidence:Mapped[int]=mapped_column(Integer,nullable=False,default=0);status:Mapped[str]=mapped_column(String(20),nullable=False,default="DRAFT")
 workspace_id:Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
