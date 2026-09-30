"""Enterprise collaboration entities for ResearchOS."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base
def now(): return datetime.now(timezone.utc)
class Organization(Base):
    __tablename__="organizations"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    name: Mapped[str]=mapped_column(String(200),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class OrganizationMember(Base):
    __tablename__="organization_members"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    organization_id: Mapped[str]=mapped_column(String(36),index=True)
    display_name: Mapped[str]=mapped_column(String(120),nullable=False)
    role: Mapped[str]=mapped_column(String(30),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class OrganizationActivity(Base):
    __tablename__="organization_activities"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    organization_id: Mapped[str]=mapped_column(String(36),index=True)
    actor: Mapped[str]=mapped_column(String(120),nullable=False)
    event_type: Mapped[str]=mapped_column(String(80),nullable=False)
    summary: Mapped[str]=mapped_column(Text,nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class OrganizationProject(Base):
    """Organization-level project metadata that safely links existing project records."""

    __tablename__ = "organization_projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    research_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    research_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Planning")
    owner_member_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class KnowledgeAccessGrant(Base):
    """Visibility metadata only; it deliberately does not modify the FAISS index."""

    __tablename__ = "knowledge_access_grants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    paper_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    owner_member_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    knowledge_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="Private")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OrganizationMeeting(Base):
    """Human-confirmed meeting proposals, never automatic formal decisions or tasks."""

    __tablename__ = "organization_meetings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    submitted_by_member_id: Mapped[str] = mapped_column(String(36), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decisions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    action_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_human_confirmation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
