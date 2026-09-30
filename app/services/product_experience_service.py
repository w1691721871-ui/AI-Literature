"""P20 product experience metadata built on top of existing, real runtime data."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.models.computer_artifact import ComputerArtifact
from app.models.computer_mission import ComputerMission
from app.models.research_document_revision import ResearchDocumentRevision
from app.models.user_onboarding_state import UserOnboardingState
from app.services.database import SessionLocal, initialize_database


class ProductExperienceService:
    """Stores only UI progress metadata; it does not create research evidence or conclusions."""

    def __init__(self, session_factory=SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._session_factory = session_factory

    def onboarding(self, user_key: str = "local") -> dict[str, object]:
        session = self._session_factory()
        try:
            row = session.scalar(select(UserOnboardingState).where(UserOnboardingState.user_key == user_key))
            if row is None:
                row = UserOnboardingState(user_key=user_key)
                session.add(row); session.commit(); session.refresh(row)
            return self._onboarding(row)
        finally:
            session.close()

    def complete_onboarding_step(self, user_key: str, step: str) -> dict[str, object]:
        if step not in {"welcome", "research", "workflow", "computer"}:
            raise ValueError("不支持的引导步骤。")
        session = self._session_factory()
        try:
            row = session.scalar(select(UserOnboardingState).where(UserOnboardingState.user_key == user_key))
            if row is None:
                row = UserOnboardingState(user_key=user_key)
                session.add(row)
            steps = self._decode_list(row.completed_steps_json)
            if step not in steps:
                steps.append(step)
            row.completed_steps_json = json.dumps(steps, ensure_ascii=False)
            row.first_visit = False
            session.commit(); session.refresh(row)
            return self._onboarding(row)
        finally:
            session.close()

    def create_mission(self, task_id: str, goal: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            row = ComputerMission(task_id=task_id, mission_name=self._mission_name(goal), progress=20, current_stage="ANALYZING")
            session.add(row); session.commit(); session.refresh(row)
            return self._mission(row)
        finally:
            session.close()

    def mission(self, task_id: str) -> dict[str, object] | None:
        session = self._session_factory()
        try:
            row = session.scalar(select(ComputerMission).where(ComputerMission.task_id == task_id))
            return self._mission(row) if row else None
        finally:
            session.close()

    def update_mission(self, task_id: str, progress: int, stage: str) -> dict[str, object] | None:
        session = self._session_factory()
        try:
            row = session.scalar(select(ComputerMission).where(ComputerMission.task_id == task_id))
            if row is None:
                return None
            row.progress = max(0, min(100, int(progress)))
            row.current_stage = stage[:60]
            session.commit(); session.refresh(row)
            return self._mission(row)
        finally:
            session.close()

    def artifacts(self, limit: int = 40) -> list[dict[str, object]]:
        """Returns only persisted artifacts/drafts. Empty remains empty; no demo content is injected."""
        session = self._session_factory()
        try:
            computer = [
                {"id": row.id, "category": "Computer", "type": row.artifact_type, "title": row.name,
                 "status": row.status, "created_at": row.created_at, "reference": row.runtime_id}
                for row in session.scalars(select(ComputerArtifact).order_by(ComputerArtifact.created_at.desc()).limit(limit)).all()
            ]
            documents = [
                {"id": row.id, "category": "Research", "type": row.document_type, "title": row.title,
                 "status": row.status, "created_at": row.created_at, "reference": row.workspace_id}
                for row in session.scalars(select(ResearchDocumentRevision).order_by(ResearchDocumentRevision.updated_at.desc()).limit(limit)).all()
            ]
            return sorted(computer + documents, key=lambda item: str(item["created_at"]), reverse=True)[:limit]
        finally:
            session.close()

    @staticmethod
    def demo_scenarios() -> list[dict[str, object]]:
        return [
            {"id": "research", "title": "AI Research Assistant", "steps": ["Research goal", "Workflow", "Evidence", "Review", "Deliverable"], "boundary": "Demo flow only; research results still require indexed sources."},
            {"id": "coding", "title": "AI Coding Assistant", "steps": ["Workspace scan", "Code analysis", "Patch proposal", "Review", "Verification"], "boundary": "Demo flow only; source changes remain pending approval."},
            {"id": "enterprise", "title": "Enterprise Solution Delivery", "steps": ["Customer need", "Solution blueprint", "Delivery package"], "boundary": "Demo scenario only; it is not a customer engagement record."},
        ]

    @staticmethod
    def _decode_list(value: str) -> list[str]:
        try:
            result = json.loads(value or "[]")
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _onboarding(row: UserOnboardingState) -> dict[str, object]:
        return {"user_key": row.user_key, "first_visit": row.first_visit, "completed_steps": ProductExperienceService._decode_list(row.completed_steps_json)}

    @staticmethod
    def _mission(row: ComputerMission) -> dict[str, object]:
        return {"id": row.id, "task_id": row.task_id, "mission_name": row.mission_name, "progress": row.progress, "current_stage": row.current_stage, "created_at": row.created_at}

    @staticmethod
    def _mission_name(goal: str) -> str:
        lowered = goal.lower()
        if any(word in lowered for word in ("ui", "frontend", "style", "首页", "样式")):
            return "Frontend Optimization"
        if any(word in lowered for word in ("bug", "error", "报错", "fix")):
            return "Controlled Debugging"
        return "Controlled Workspace Mission"
