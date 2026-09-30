"""Persistence and review controls for non-executing Copilot suggestions."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.models.research_copilot_action import ResearchCopilotAction
from app.services.database import SessionLocal, initialize_database


class CopilotActionNotFoundError(Exception):
    pass


class ResearchCopilotActionService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._sessions = session_factory

    def create(self, data: dict[str, object]) -> dict[str, object]:
        session = self._sessions()
        try:
            item = ResearchCopilotAction(
                workspace_id=str(data["workspace_id"]), title=str(data["title"]), rationale=str(data["rationale"]),
                evidence_refs_json=json.dumps(data.get("evidence_refs", []), ensure_ascii=False),
            )
            session.add(item); session.commit(); session.refresh(item)
            return self._payload(item)
        finally:
            session.close()

    def list(self, workspace_id: str | None = None) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            query = select(ResearchCopilotAction).order_by(ResearchCopilotAction.updated_at.desc())
            if workspace_id:
                query = query.where(ResearchCopilotAction.workspace_id == workspace_id)
            return [self._payload(item) for item in session.scalars(query).all()]
        finally:
            session.close()

    def review(self, action_id: str, status: str) -> dict[str, object]:
        session = self._sessions()
        try:
            item = session.get(ResearchCopilotAction, action_id)
            if item is None:
                raise CopilotActionNotFoundError("Copilot 建议不存在。")
            item.status = status
            session.commit(); session.refresh(item)
            return self._payload(item)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _payload(item: ResearchCopilotAction) -> dict[str, object]:
        try: refs = json.loads(item.evidence_refs_json or "[]")
        except json.JSONDecodeError: refs = []
        return {"id": item.id, "workspace_id": item.workspace_id, "title": item.title, "rationale": item.rationale, "evidence_refs": refs, "status": item.status, "created_at": item.created_at, "updated_at": item.updated_at, "boundary": "该建议仅供人工选择；不会自动执行检索、创建正式 Action 或形成科研结论。"}
