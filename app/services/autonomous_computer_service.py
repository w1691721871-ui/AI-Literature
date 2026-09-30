"""SQLite persistence for P17 sessions, artifacts and bounded recovery attempts."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.models.computer_artifact import ComputerArtifact
from app.models.computer_recovery_attempt import ComputerRecoveryAttempt
from app.models.computer_runtime_session import ComputerRuntimeSession
from app.services.database import SessionLocal, initialize_database


class AutonomousComputerNotFoundError(Exception): pass


class AutonomousComputerService:
    def __init__(self, session_factory=SessionLocal, *, initialize: bool = True) -> None:
        if initialize: initialize_database()
        self._session_factory = session_factory

    def create(self, computer_task_id: str, goal: str, plan: list[dict[str, object]]) -> dict[str, object]:
        session = self._session_factory()
        try:
            row = ComputerRuntimeSession(computer_task_id=computer_task_id, user_goal=goal, plan_json=self._encode(plan))
            session.add(row); session.commit(); session.refresh(row); return self._payload(row)
        finally: session.close()

    def get(self, runtime_id: str) -> dict[str, object]:
        session = self._session_factory()
        try: return self._payload(self._row(session, runtime_id))
        finally: session.close()

    def update(self, runtime_id: str, *, status: str | None = None, loop_count: int | None = None) -> dict[str, object]:
        session = self._session_factory()
        try:
            row = self._row(session, runtime_id)
            if status is not None: row.status = status
            if loop_count is not None: row.loop_count = loop_count
            session.commit(); session.refresh(row); return self._payload(row)
        finally: session.close()

    def add_artifact(self, runtime_id: str, artifact_type: str, name: str, status: str, metadata: dict[str, object]) -> dict[str, object]:
        session = self._session_factory()
        try:
            self._row(session, runtime_id)
            row = ComputerArtifact(runtime_id=runtime_id, artifact_type=artifact_type, name=name[:300], status=status, metadata_json=self._encode(metadata))
            session.add(row); session.commit(); session.refresh(row); return self._artifact(row)
        finally: session.close()

    def artifacts(self, runtime_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try:
            self._row(session, runtime_id)
            return [self._artifact(row) for row in session.scalars(select(ComputerArtifact).where(ComputerArtifact.runtime_id == runtime_id).order_by(ComputerArtifact.created_at.asc())).all()]
        finally: session.close()

    def add_recovery(self, runtime_id: str, attempt: int, status: str, summary: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            self._row(session, runtime_id)
            row = ComputerRecoveryAttempt(runtime_id=runtime_id, attempt_number=attempt, status=status, summary=summary[:2000])
            session.add(row); session.commit(); session.refresh(row)
            return {"attempt_number": row.attempt_number, "status": row.status, "summary": row.summary, "created_at": row.created_at}
        finally: session.close()

    def recoveries(self, runtime_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try:
            return [{"attempt_number": row.attempt_number, "status": row.status, "summary": row.summary, "created_at": row.created_at} for row in session.scalars(select(ComputerRecoveryAttempt).where(ComputerRecoveryAttempt.runtime_id == runtime_id).order_by(ComputerRecoveryAttempt.attempt_number.asc())).all()]
        finally: session.close()

    @staticmethod
    def _encode(value: object) -> str: return json.dumps(value, ensure_ascii=False, default=str)
    @staticmethod
    def _decode(value: str) -> object:
        try: return json.loads(value or "{}")
        except json.JSONDecodeError: return {}
    def _row(self, session, runtime_id: str) -> ComputerRuntimeSession:
        row = session.get(ComputerRuntimeSession, runtime_id)
        if row is None: raise AutonomousComputerNotFoundError("Autonomous Computer Runtime 不存在。")
        return row
    def _payload(self, row: ComputerRuntimeSession) -> dict[str, object]:
        return {"id": row.id, "computer_task_id": row.computer_task_id, "user_goal": row.user_goal, "status": row.status, "plan": self._decode(row.plan_json), "loop_count": row.loop_count, "created_at": row.created_at, "updated_at": row.updated_at}
    def _artifact(self, row: ComputerArtifact) -> dict[str, object]:
        return {"id": row.id, "type": row.artifact_type, "name": row.name, "status": row.status, "metadata": self._decode(row.metadata_json), "created_at": row.created_at}
