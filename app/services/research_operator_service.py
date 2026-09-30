"""SQLite persistence for safe, human-approved Operator task summaries."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operator_action import OperatorAction
from app.models.operator_task import OperatorTask
from app.services.database import SessionLocal, initialize_database


class OperatorTaskNotFoundError(Exception):
    pass


class ResearchOperatorService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def create(self, *, user_goal: str, workspace_id: str | None, task_type: str, plan: list[dict[str, object]]) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = OperatorTask(workspace_id=workspace_id, user_goal=user_goal, task_type=task_type, plan_json=self._encode(plan))
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._payload(record, [])
        finally:
            session.close()

    def update_execution(self, task_id: str, *, status: str, plan: list[dict[str, object]], tools: list[dict[str, object]], evidence_refs: list[dict[str, object]], artifact: dict[str, object], approval_status: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = self._record(session, task_id)
            record.status = status
            record.plan_json = self._encode(plan)
            record.tool_execution_json = self._encode(tools)
            record.evidence_refs_json = self._encode(evidence_refs)
            record.artifact_json = self._encode(artifact)
            record.approval_status = approval_status
            session.commit()
            session.refresh(record)
            return self._payload(record, self._actions(session, task_id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_action(self, task_id: str, *, tool_name: str, action: str, result: dict[str, object]) -> None:
        session: Session = self._session_factory()
        try:
            self._record(session, task_id)
            session.add(OperatorAction(task_id=task_id, tool_name=tool_name, action=action, result=self._encode(result)))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, task_id: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = self._record(session, task_id)
            return self._payload(record, self._actions(session, task_id))
        finally:
            session.close()

    def list(self) -> list[dict[str, object]]:
        session: Session = self._session_factory()
        try:
            records = session.scalars(select(OperatorTask).order_by(OperatorTask.created_at.desc())).all()
            return [self._payload(record, self._actions(session, record.id)) for record in records]
        finally:
            session.close()

    def approve(self, task_id: str, reviewer_note: str) -> dict[str, object]:
        return self._review(task_id, "approved", "approved", reviewer_note)

    def reject(self, task_id: str, reviewer_note: str) -> dict[str, object]:
        return self._review(task_id, "rejected", "rejected", reviewer_note)

    def _review(self, task_id: str, status: str, approval_status: str, note: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = self._record(session, task_id)
            if record.approval_status != "pending":
                raise ValueError("该任务当前不处于待人工审核状态。")
            record.status = status
            record.approval_status = approval_status
            record.reviewer_note = note
            session.add(OperatorAction(task_id=task_id, tool_name="human_approval", action=status, result=self._encode({"reviewer_note": note or "未填写备注"})))
            session.commit()
            session.refresh(record)
            return self._payload(record, self._actions(session, task_id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _encode(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode(value: str, fallback: object) -> object:
        try:
            return json.loads(value or "")
        except json.JSONDecodeError:
            return fallback

    @staticmethod
    def _record(session: Session, task_id: str) -> OperatorTask:
        record = session.get(OperatorTask, task_id)
        if record is None:
            raise OperatorTaskNotFoundError("Research Operator 任务不存在。")
        return record

    def _actions(self, session: Session, task_id: str) -> list[dict[str, object]]:
        rows = session.scalars(select(OperatorAction).where(OperatorAction.task_id == task_id).order_by(OperatorAction.timestamp.asc())).all()
        return [{"id": row.id, "tool_name": row.tool_name, "action": row.action, "result": self._decode(row.result, {}), "timestamp": row.timestamp} for row in rows]

    def _payload(self, record: OperatorTask, actions: list[dict[str, object]]) -> dict[str, object]:
        return {"id": record.id, "workspace_id": record.workspace_id, "user_goal": record.user_goal, "task_type": record.task_type, "status": record.status, "plan": self._decode(record.plan_json, []), "tool_executions": self._decode(record.tool_execution_json, []), "evidence_refs": self._decode(record.evidence_refs_json, []), "artifact": self._decode(record.artifact_json, {}), "approval_status": record.approval_status, "reviewer_note": record.reviewer_note, "actions": actions, "created_at": record.created_at, "updated_at": record.updated_at}
