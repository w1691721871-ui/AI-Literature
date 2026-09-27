"""Task-scoped context persistence for Research Worker, separate from long-term memory."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.research_worker_context import ResearchWorkerContext
from app.services.database import SessionLocal, initialize_database


class ResearchWorkerContextService:
    """Persist only concise, user-readable status for a single run."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def save(self, run_id: str, context: dict[str, object]) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = session.query(ResearchWorkerContext).filter_by(run_id=run_id).one_or_none()
            if record is None:
                record = ResearchWorkerContext(run_id=run_id)
                session.add(record)
            record.context_data = json.dumps(context, ensure_ascii=False, default=str)
            session.commit()
            return context
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, run_id: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = session.query(ResearchWorkerContext).filter_by(run_id=run_id).one_or_none()
            if record is None:
                return {}
            try:
                return json.loads(record.context_data or "{}")
            except json.JSONDecodeError:
                return {}
        finally:
            session.close()
