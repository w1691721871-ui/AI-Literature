"""Persistence for resumable, user-readable Computer Operator checkpoints."""

from __future__ import annotations

import json

from app.models.computer_task_checkpoint import ComputerTaskCheckpoint
from app.services.database import SessionLocal, initialize_database


class ComputerCheckpointService:
    def __init__(self, session_factory=SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._session_factory = session_factory

    def save(self, task_id: str, current_step: str, completed: list[dict[str, object]], remaining: list[dict[str, object]], status: str = "ACTIVE") -> dict[str, object]:
        session = self._session_factory()
        try:
            row = session.query(ComputerTaskCheckpoint).filter_by(task_id=task_id).one_or_none()
            if row is None:
                row = ComputerTaskCheckpoint(task_id=task_id)
                session.add(row)
            row.current_step = current_step[:160]
            row.completed_actions_json = json.dumps(completed, ensure_ascii=False, default=str)
            row.remaining_actions_json = json.dumps(remaining, ensure_ascii=False, default=str)
            row.status = status
            session.commit(); session.refresh(row)
            return self._payload(row)
        finally:
            session.close()

    def get(self, task_id: str) -> dict[str, object] | None:
        session = self._session_factory()
        try:
            row = session.query(ComputerTaskCheckpoint).filter_by(task_id=task_id).one_or_none()
            return self._payload(row) if row else None
        finally:
            session.close()

    @staticmethod
    def _payload(row: ComputerTaskCheckpoint) -> dict[str, object]:
        return {
            "task_id": row.task_id, "current_step": row.current_step, "status": row.status,
            "completed_actions": json.loads(row.completed_actions_json or "[]"),
            "remaining_actions": json.loads(row.remaining_actions_json or "[]"),
            "updated_at": row.updated_at,
        }
