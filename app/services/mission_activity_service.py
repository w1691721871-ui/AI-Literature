"""Public-safe activity projection for the enterprise Mission workspace."""

from __future__ import annotations

from sqlalchemy import select

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.artifact import Artifact
from app.services.database import SessionLocal, initialize_database


class MissionActivityService:
    """Transforms persisted Mission events into user-understandable progress."""

    _LABELS = {
        "PLANNING": "Preparing", "REQUIREMENT_ANALYSIS": "Understanding", "EVIDENCE_RETRIEVAL": "Researching",
        "SOLUTION_GENERATION": "Developing", "RISK_ANALYSIS": "Validating", "WAITING_REVIEW": "Needs review",
        "NEEDS_REVISION": "Needs revision", "APPROVED": "Approved", "DELIVERY_READY": "Preparing delivery",
        "COMPLETED": "Completed", "PAUSED": "Waiting", "FAILED": "Needs attention",
    }

    def __init__(self, sessions=SessionLocal, *, initialize=True):
        if initialize:
            initialize_database()
        self._sessions = sessions

    def timeline(self, mission_id: str, workspace_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            mission = session.get(AIMission, mission_id)
            if mission is None or mission.workspace_id != workspace_id:
                raise PermissionError("Mission is not available in this Workspace.")
            events = session.scalars(select(AIMissionEvent).where(AIMissionEvent.mission_id == mission_id).order_by(AIMissionEvent.created_at.asc())).all()
            activities = [self._activity(event) for event in events[-12:]]
            artifacts = session.scalars(select(Artifact).where(Artifact.mission_id == mission_id).order_by(Artifact.updated_at.desc())).all()
            return {
                "mission_id": mission_id,
                "current_phase": self._LABELS.get(mission.status, "Preparing"),
                "current_summary": self._summary(mission.status, mission.current_step),
                "next_action": self._next_action(mission.status),
                "next_best_action": self._recommendation(mission, artifacts),
                "activities": activities,
                "boundary": "Activities are persisted user-readable summaries. Prompts, reasoning traces, model data and raw tool output are excluded.",
            }
        finally:
            session.close()

    def _activity(self, event: AIMissionEvent) -> dict[str, object]:
        return {"phase": self._LABELS.get(event.status, self._LABELS.get(event.stage, "Preparing")), "summary": self._safe(event.result_summary), "evidence_count": event.evidence_count, "status": self._status(event.status), "created_at": event.created_at}

    @classmethod
    def _summary(cls, status: str, step: str) -> str:
        return cls._safe(step) or "Mission is ready for the next controlled action."

    @classmethod
    def _next_action(cls, status: str) -> str:
        if status in {"WAITING_REVIEW", "NEEDS_REVISION"}:
            return "Human review is required before the Mission can advance."
        if status == "PAUSED":
            return "An authorized Workspace member can resume this Mission."
        if status == "FAILED":
            return "Prepare a bounded recovery plan or request human review."
        if status == "COMPLETED":
            return "Review the approved delivery and retain only validated knowledge."
        return "Continue through the next approved Mission stage."

    @classmethod
    def _recommendation(cls, mission: AIMission, artifacts: list[Artifact]) -> dict[str, str]:
        """Return one actionable suggestion derived only from persisted state."""
        evidence_count = len(cls._references(mission.evidence_refs_json))
        if mission.status in {"WAITING_REVIEW", "NEEDS_REVISION"}:
            return {
                "action": "OPEN_REVIEW", "label": "Review the research evidence",
                "description": "This Mission is waiting for an authorized reviewer before it can advance.",
            }
        if mission.status == "FAILED":
            return {
                "action": "PREPARE_RECOVERY", "label": "Prepare a recovery review",
                "description": "The last controlled step needs human attention before a bounded retry is considered.",
            }
        if evidence_count == 0:
            return {
                "action": "EXPAND_RESEARCH", "label": "Expand the research evidence",
                "description": "No traceable Evidence is linked yet, so ResearchOS cannot make a grounded research conclusion.",
            }
        if any(item.status in {"NEEDS_REVIEW", "REVISION_REQUESTED"} for item in artifacts):
            return {
                "action": "REVIEW_ARTIFACT", "label": "Review the prepared deliverable",
                "description": "A generated artifact is available, but remains a draft until a human review is complete.",
            }
        if mission.status == "COMPLETED":
            return {
                "action": "OPEN_DELIVERY", "label": "Review the completed delivery",
                "description": "The controlled Mission is complete. Reuse only the approved result and validated knowledge.",
            }
        return {
            "action": "CONTINUE_MISSION", "label": "Continue the controlled Mission",
            "description": "The next step remains within the existing Workspace, Evidence and approval boundaries.",
        }

    @staticmethod
    def _references(value: str) -> list[object]:
        import json
        try:
            decoded = json.loads(value or "[]")
            return decoded if isinstance(decoded, list) else []
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _status(value: str) -> str:
        if value in {"FAILED", "REJECTED"}:
            return "ATTENTION"
        if value in {"WAITING_REVIEW", "NEEDS_REVISION", "PAUSED"}:
            return "WAITING"
        if value in {"COMPLETED", "APPROVED"}:
            return "COMPLETED"
        return "ACTIVE"

    @staticmethod
    def _safe(value: object) -> str:
        text = str(value or "").replace("\n", " ").strip()
        return text[:360]
