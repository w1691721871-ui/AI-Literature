"""Services for project outcomes and their knowledge-asset status."""

from sqlalchemy import select

from app.models.research_outcome import ResearchOutcome
from app.models.research_project import ResearchProject
from app.models.research_action import ResearchAction
from app.schemas.decision_loop import (
    KnowledgeStatusUpdate,
    ResearchOutcomeCreate,
    ResearchOutcomeUpdate,
)
from app.services.database import SessionLocal, initialize_database


class ResearchOutcomeNotFoundError(ValueError):
    """Raised when an outcome does not exist."""


class ResearchOutcomeProjectNotFoundError(ValueError):
    """Raised when an outcome is attached to a missing project."""


class ResearchOutcomeSourceActionNotFoundError(ValueError):
    """Raised when a requested outcome source action cannot be verified."""


class ResearchOutcomeService:
    @staticmethod
    def _payload(outcome: ResearchOutcome) -> dict[str, object]:
        return {
            "id": outcome.id,
            "project_id": outcome.project_id,
            "outcome_type": outcome.outcome_type,
            "title": outcome.title,
            "status": outcome.status,
            "description": outcome.description,
            "knowledge_status": outcome.knowledge_status,
            "source_action_id": outcome.source_action_id,
            "created_at": outcome.created_at,
            "updated_at": outcome.updated_at,
        }

    def create_outcome(self, project_id: str, payload: ResearchOutcomeCreate) -> dict[str, object]:
        initialize_database()
        session = SessionLocal()
        try:
            if session.get(ResearchProject, project_id) is None:
                raise ResearchOutcomeProjectNotFoundError(project_id)
            if payload.source_action_id:
                action = session.get(ResearchAction, payload.source_action_id)
                if action is None or (action.project_id and action.project_id != project_id):
                    raise ResearchOutcomeSourceActionNotFoundError(payload.source_action_id)
            outcome = ResearchOutcome(
                project_id=project_id,
                outcome_type=payload.outcome_type,
                title=payload.title.strip(),
                status=payload.status,
                description=payload.description.strip(),
                source_action_id=payload.source_action_id,
            )
            session.add(outcome)
            session.commit()
            session.refresh(outcome)
            return self._payload(outcome)
        finally:
            session.close()

    def list_outcomes(self, project_id: str) -> list[dict[str, object]]:
        initialize_database()
        session = SessionLocal()
        try:
            outcomes = session.scalars(
                select(ResearchOutcome)
                .where(ResearchOutcome.project_id == project_id)
                .order_by(ResearchOutcome.created_at.desc())
            ).all()
            return [self._payload(outcome) for outcome in outcomes]
        finally:
            session.close()

    def update_outcome(self, outcome_id: str, payload: ResearchOutcomeUpdate) -> dict[str, object]:
        initialize_database()
        session = SessionLocal()
        try:
            outcome = session.get(ResearchOutcome, outcome_id)
            if outcome is None:
                raise ResearchOutcomeNotFoundError(outcome_id)
            for field, value in payload.model_dump(exclude_none=True).items():
                if field == "source_action_id" and value:
                    action = session.get(ResearchAction, value)
                    if action is None or (action.project_id and action.project_id != outcome.project_id):
                        raise ResearchOutcomeSourceActionNotFoundError(value)
                setattr(outcome, field, value.strip() if isinstance(value, str) and field not in {"status", "outcome_type"} else value)
            session.commit()
            session.refresh(outcome)
            return self._payload(outcome)
        finally:
            session.close()

    def delete_outcome(self, outcome_id: str) -> None:
        initialize_database()
        session = SessionLocal()
        try:
            outcome = session.get(ResearchOutcome, outcome_id)
            if outcome is None:
                raise ResearchOutcomeNotFoundError(outcome_id)
            session.delete(outcome)
            session.commit()
        finally:
            session.close()

    def update_knowledge_status(self, outcome_id: str, payload: KnowledgeStatusUpdate) -> dict[str, object]:
        initialize_database()
        session = SessionLocal()
        try:
            outcome = session.get(ResearchOutcome, outcome_id)
            if outcome is None:
                raise ResearchOutcomeNotFoundError(outcome_id)
            outcome.knowledge_status = payload.knowledge_status
            session.commit()
            session.refresh(outcome)
            return self._payload(outcome)
        finally:
            session.close()
