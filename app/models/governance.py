"""P33 deployment governance records; user identities are display-only in this local prototype."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def now(): return datetime.now(timezone.utc)
class GovernanceWorkspace(Base):
    __tablename__="governance_workspaces"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    organization_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    owner_id: Mapped[str | None]=mapped_column(String(36),nullable=True,index=True)
    name: Mapped[str]=mapped_column(String(160),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
class WorkspaceUserRole(Base):
    __tablename__="workspace_user_roles"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False,index=True)
    user_id: Mapped[str]=mapped_column(String(80),nullable=False,index=True)
    role: Mapped[str]=mapped_column(String(20),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    user_id: Mapped[str]=mapped_column(String(80),nullable=False)
    workspace_id: Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    action: Mapped[str]=mapped_column(String(100),nullable=False)
    resource_type: Mapped[str]=mapped_column(String(80),nullable=False)
    resource_id: Mapped[str]=mapped_column(String(80),nullable=False)
    summary: Mapped[str]=mapped_column(Text,nullable=False,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
class AgentPolicy(Base):
    __tablename__="agent_policies"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False,unique=True,index=True)
    max_iterations: Mapped[int]=mapped_column(Integer,nullable=False,default=3)
    max_tool_calls: Mapped[int]=mapped_column(Integer,nullable=False,default=10)
    require_human_review: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    allowed_connectors: Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now)
