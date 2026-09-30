"""Persistence for Research Computer Agent sessions and approval-gated actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.computer_action import ComputerAction
from app.models.computer_execution_event import ComputerExecutionEvent
from app.models.computer_session import ComputerSession
from app.services.database import SessionLocal, initialize_database


class ComputerSessionNotFoundError(Exception):
    pass


class ComputerActionNotFoundError(Exception):
    pass


class ResearchComputerService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def create_session(self, *, user_goal: str, workspace_id: str | None, task_type: str, plan: list[dict[str, object]]) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            item = ComputerSession(workspace_id=workspace_id, user_goal=user_goal, task_type=task_type, status="executing", plan_json=self._encode(plan))
            session.add(item); session.commit(); session.refresh(item)
            return self._payload(item, [])
        finally: session.close()

    def update_session(self, task_id: str, *, status: str, plan: list[dict[str, object]], artifact: dict[str, object]) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            item = self._session(session, task_id)
            item.status, item.plan_json, item.artifact_json = status, self._encode(plan), self._encode(artifact)
            if status in {"completed", "rejected", "failed", "insufficient_evidence"}: item.ended_at = datetime.now(timezone.utc)
            session.commit(); session.refresh(item)
            return self._payload(item, self._actions(session, task_id))
        except Exception:
            session.rollback(); raise
        finally: session.close()

    def add_action(self, task_id: str, *, tool_name: str, action_type: str, input_data: dict[str, object], result: dict[str, object], status: str, approval_required: bool) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            self._session(session, task_id)
            item = ComputerAction(task_id=task_id, tool_name=tool_name, action_type=action_type, input_data=self._encode(input_data), result=self._encode(result), status=status, approval_required=approval_required)
            session.add(item); session.commit(); session.refresh(item)
            return self._action_payload(item)
        except Exception:
            session.rollback(); raise
        finally: session.close()

    def add_event(self, task_id: str, *, agent_name: str, event_type: str, tool_name: str = "", status: str, message: str, result_summary: str = "") -> dict[str, object]:
        """Persist a public operator event, never prompts or hidden reasoning."""
        session: Session = self._session_factory()
        try:
            self._session(session, task_id)
            item = ComputerExecutionEvent(task_id=task_id, agent_name=agent_name, event_type=event_type, tool_name=tool_name, status=status, message=message[:2000], result_summary=result_summary[:4000])
            session.add(item); session.commit(); session.refresh(item)
            return self._event_payload(item)
        except Exception:
            session.rollback(); raise
        finally: session.close()

    def events(self, task_id: str) -> list[dict[str, object]]:
        session: Session = self._session_factory()
        try:
            self._session(session, task_id)
            rows = session.scalars(select(ComputerExecutionEvent).where(ComputerExecutionEvent.task_id == task_id).order_by(ComputerExecutionEvent.created_at.asc())).all()
            return [self._event_payload(item) for item in rows]
        finally: session.close()

    def get(self, task_id: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            item = self._session(session, task_id)
            return self._payload(item, self._actions(session, task_id))
        finally: session.close()

    def list(self) -> list[dict[str, object]]:
        session: Session = self._session_factory()
        try:
            items = session.scalars(select(ComputerSession).order_by(ComputerSession.started_at.desc())).all()
            return [self._payload(item, self._actions(session, item.id)) for item in items]
        finally: session.close()

    def review_action(self, action_id: str, *, approved: bool, reviewer_note: str) -> tuple[dict[str, object], dict[str, object]]:
        session: Session = self._session_factory()
        try:
            action = session.get(ComputerAction, action_id)
            if action is None: raise ComputerActionNotFoundError("Computer Action 不存在。")
            if not action.approval_required or action.status != "PENDING_APPROVAL": raise ValueError("该操作当前不需要或无法接受审批。")
            action.status = "APPROVED" if approved else "REJECTED"
            result = self._decode(action.result, {})
            result["reviewer_note"] = reviewer_note or "未填写备注"
            result["approval_boundary"] = "审批只确认该受控操作计划；不会自动修改原始文件或对外发布内容。"
            action.result = self._encode(result)
            item = self._session(session, action.task_id)
            item.status = "approved" if approved else "rejected"
            if not approved: item.ended_at = datetime.now(timezone.utc)
            session.commit(); session.refresh(action); session.refresh(item)
            return self._payload(item, self._actions(session, item.id)), self._action_payload(action)
        except Exception:
            session.rollback(); raise
        finally: session.close()

    @staticmethod
    def _encode(value: object) -> str: return json.dumps(value, ensure_ascii=False, default=str)
    @staticmethod
    def _decode(value: str, fallback: object) -> object:
        try: return json.loads(value or "")
        except json.JSONDecodeError: return fallback
    @staticmethod
    def _session(session: Session, task_id: str) -> ComputerSession:
        item = session.get(ComputerSession, task_id)
        if item is None: raise ComputerSessionNotFoundError("Computer Agent 任务不存在。")
        return item
    def _actions(self, session: Session, task_id: str) -> list[dict[str, object]]:
        return [self._action_payload(item) for item in session.scalars(select(ComputerAction).where(ComputerAction.task_id == task_id).order_by(ComputerAction.created_at.asc())).all()]
    def _action_payload(self, item: ComputerAction) -> dict[str, object]:
        return {"id": item.id, "task_id": item.task_id, "tool_name": item.tool_name, "action_type": item.action_type, "input_data": self._decode(item.input_data, {}), "result": self._decode(item.result, {}), "status": item.status, "approval_required": item.approval_required, "created_at": item.created_at, "updated_at": item.updated_at}
    @staticmethod
    def _event_payload(item: ComputerExecutionEvent) -> dict[str, object]:
        return {"id": item.id, "task_id": item.task_id, "agent_name": item.agent_name, "event_type": item.event_type, "tool_name": item.tool_name, "status": item.status, "message": item.message, "result_summary": item.result_summary, "created_at": item.created_at}
    def _payload(self, item: ComputerSession, actions: list[dict[str, object]]) -> dict[str, object]:
        return {"id": item.id, "workspace_id": item.workspace_id, "user_goal": item.user_goal, "task_type": item.task_type, "status": item.status, "plan": self._decode(item.plan_json, []), "artifact": self._decode(item.artifact_json, {}), "actions": actions, "started_at": item.started_at, "ended_at": item.ended_at, "updated_at": item.updated_at}
