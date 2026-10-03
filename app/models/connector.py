"""Auditable, credential-free connector metadata for P31."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Connector(Base):
    __tablename__ = "connectors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    permission: Mapped[str] = mapped_column(String(30), nullable=False, default="READ_ONLY")
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    config_summary: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class ConnectorTrace(Base):
    __tablename__ = "connector_traces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETED")
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class MissionDataSource(Base):
    __tablename__ = "mission_data_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)


class ArtifactDataSource(Base):
    __tablename__ = "artifact_data_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    data_source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
