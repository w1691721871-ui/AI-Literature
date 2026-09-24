"""Persist and return user-friendly ResearchAgent execution milestones."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_trace import AgentTrace
from app.services.database import SessionLocal, initialize_database


class AgentTraceService:
    """Stores process summaries, deliberately excluding chain-of-thought."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    @staticmethod
    def create_trace_id() -> str:
        return str(uuid4())

    def record(self, trace_id: str, step: str, message: str) -> dict[str, str]:
        record = AgentTrace(trace_id=trace_id, step=step, message=message)
        session: Session = self._session_factory()
        try:
            session.add(record)
            session.commit()
            return {
                "step": step,
                "message": message,
                "created_at": record.created_at.isoformat(),
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_steps(self, trace_id: str) -> list[dict[str, str]]:
        session: Session = self._session_factory()
        try:
            records = list(session.scalars(
                select(AgentTrace)
                .where(AgentTrace.trace_id == trace_id)
                .order_by(AgentTrace.created_at, AgentTrace.id)
            ))
            return [
                {"step": record.step, "message": record.message, "created_at": record.created_at.isoformat()}
                for record in records
            ]
        finally:
            session.close()
