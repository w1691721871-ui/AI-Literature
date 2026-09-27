"""Services for research actions and human confirmation records."""

import json
from datetime import datetime

from sqlalchemy import select

from app.models.research_action import ResearchAction
from app.models.research_decision import ResearchDecision
from app.schemas.decision_loop import (
    ResearchActionCreate,
    ResearchActionUpdate,
    ResearchDecisionCreate,
)
from app.services.database import SessionLocal, initialize_database


class ResearchActionNotFoundError(ValueError):
    """Raised when an action does not exist."""


class ResearchActionService:
    """Keep human-owned action state separate from existing Agent results."""

    @staticmethod
    def _action_payload(action: ResearchAction) -> dict[str, object]:
        try:
            evidence_refs = json.loads(action.evidence_refs or "[]")
        except json.JSONDecodeError:
            evidence_refs = []
        return {
            "id": action.id,
            "project_id": action.project_id,
            "title": action.title,
            "description": action.description,
            "status": action.status,
            "source_agent": action.source_agent,
            "source_context": action.source_context,
            "rationale": action.rationale,
            "evidence_refs": evidence_refs,
            "created_at": action.created_at,
            "updated_at": action.updated_at,
        }

    def create_action(self, payload: ResearchActionCreate) -> dict[str, object]:
        """Persist an action only when the caller supplies its result evidence."""
        initialize_database()
        session = SessionLocal()
        try:
            action = ResearchAction(
                project_id=payload.project_id,
                title=payload.title.strip(),
                description=payload.description.strip(),
                status=payload.status,
                source_agent=payload.source_agent.strip(),
                source_context=payload.source_context.strip(),
                rationale=(payload.rationale.strip() or ResearchActionService._fallback_rationale(payload)),
                evidence_refs=json.dumps([item.model_dump() for item in payload.evidence_refs], ensure_ascii=False),
            )
            session.add(action)
            session.commit()
            session.refresh(action)
            return self._action_payload(action)
        finally:
            session.close()

    @staticmethod
    def _fallback_rationale(payload: ResearchActionCreate) -> str:
        """State a conservative, user-readable basis without inventing facts."""
        if payload.evidence_refs:
            return (
                f"该建议来自 {payload.source_agent.strip()} 的现有输出，并关联了 "
                f"{len(payload.evidence_refs)} 条已展示的资料依据；仍需科研负责人确认和后续验证。"
            )
        return (
            f"该建议来自 {payload.source_agent.strip()} 的现有输出，但当前未返回可验证资料；"
            "建议先补充资料或人工核验后再推进。"
        )

    def list_actions(self, project_id: str | None = None) -> list[dict[str, object]]:
        initialize_database()
        session = SessionLocal()
        try:
            statement = select(ResearchAction).order_by(ResearchAction.created_at.desc())
            if project_id:
                statement = statement.where(ResearchAction.project_id == project_id)
            return [self._action_payload(action) for action in session.scalars(statement).all()]
        finally:
            session.close()

    def update_action(self, action_id: str, payload: ResearchActionUpdate) -> dict[str, object]:
        initialize_database()
        session = SessionLocal()
        try:
            action = session.get(ResearchAction, action_id)
            if action is None:
                raise ResearchActionNotFoundError(action_id)
            for field, value in payload.model_dump(exclude_none=True).items():
                setattr(action, field, value.strip() if isinstance(value, str) and field != "status" else value)
            session.commit()
            session.refresh(action)
            return self._action_payload(action)
        finally:
            session.close()

    def save_decision(self, payload: ResearchDecisionCreate) -> dict[str, object]:
        """Upsert the latest human decision for an action."""
        initialize_database()
        session = SessionLocal()
        try:
            action = session.get(ResearchAction, payload.action_id)
            if action is None:
                raise ResearchActionNotFoundError(payload.action_id)
            decision = session.scalar(select(ResearchDecision).where(ResearchDecision.action_id == payload.action_id))
            if decision is None:
                decision = ResearchDecision(action_id=payload.action_id)
                session.add(decision)
            decision.decision = payload.decision
            decision.decided_by = payload.decided_by.strip()
            decision.note = payload.note.strip()
            decision.decided_at = None if payload.decision == "待确认" else datetime.utcnow()
            session.commit()
            session.refresh(decision)
            return self._decision_payload(decision, action)
        finally:
            session.close()

    @staticmethod
    def _decision_payload(decision: ResearchDecision, action: ResearchAction) -> dict[str, object]:
        return {
            "id": decision.id,
            "action_id": decision.action_id,
            "project_id": action.project_id,
            "action_title": action.title,
            "decision": decision.decision,
            "decided_by": decision.decided_by,
            "decided_at": decision.decided_at,
            "note": decision.note,
            "created_at": decision.created_at,
            "updated_at": decision.updated_at,
        }

    def list_decisions(self, project_id: str | None = None) -> list[dict[str, object]]:
        initialize_database()
        session = SessionLocal()
        try:
            statement = (
                select(ResearchDecision, ResearchAction)
                .join(ResearchAction, ResearchDecision.action_id == ResearchAction.id)
                .order_by(ResearchDecision.updated_at.desc())
            )
            if project_id:
                statement = statement.where(ResearchAction.project_id == project_id)
            return [self._decision_payload(decision, action) for decision, action in session.execute(statement).all()]
        finally:
            session.close()
