"""Builds the only context projection injected into the AI Worker Runtime."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select

from app.models.enterprise_memory import DecisionRecord, KnowledgeAsset
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.solution_project import SolutionProject
from app.models.mission_collaboration import MissionParticipant, MissionReviewComment
from app.models.identity import User
from app.models.computer_project_memory import ComputerProjectMemory
from app.services.database import SessionLocal, initialize_database
from app.services.context_retrieval_service import ContextRetrievalService
from app.services.workspace_memory_service import WorkspaceMemoryService


class WorkspaceContextService:
    """Joins identity, workspace, mission, knowledge and memory without raw content."""

    def __init__(self, sessions=SessionLocal, *, initialize=True, memories=None, selector=None, retrieval=None):
        if initialize:
            initialize_database()
        self._sessions = sessions
        self._memories = memories or WorkspaceMemoryService(sessions, initialize=False)
        self._retrieval = retrieval or ContextRetrievalService(selector)

    def build(self, mission: Mapping[str, object], *, actor=None) -> dict[str, object]:
        workspace_id = str(mission.get("workspace_id") or "")
        mission_id = str(mission.get("id") or "")
        if not workspace_id or not mission_id:
            raise ValueError("AI Context requires a workspace-bound Mission.")
        actor_workspace = getattr(actor, "workspace_id", None)
        if actor_workspace and actor_workspace != workspace_id:
            raise PermissionError("Cross-workspace AI Context access denied.")
        user_id = getattr(actor, "user_id", None)
        session = self._sessions()
        try:
            workspace = session.get(GovernanceWorkspace, workspace_id)
            if workspace is None:
                raise ValueError("Mission Workspace is unavailable.")
            workspace_name = workspace.name
            member_count = int(session.scalar(select(func.count(WorkspaceUserRole.id)).where(WorkspaceUserRole.workspace_id == workspace_id)) or 0)
            approved_assets = int(session.scalar(select(func.count(KnowledgeAsset.id)).where(KnowledgeAsset.workspace_id == workspace_id, KnowledgeAsset.status == "VERIFIED")) or 0)
            approved_decisions = int(session.scalar(select(func.count(DecisionRecord.id)).where(DecisionRecord.workspace_id == workspace_id, DecisionRecord.review_status == "APPROVED")) or 0)
            approved_artifacts = [
                {
                    "id": artifact.id, "title": artifact.title, "artifact_type": artifact.artifact_type,
                    "status": artifact.status, "summary": artifact.content_summary[:600],
                    "evidence_count": artifact.evidence_count, "updated_at": artifact.updated_at,
                }
                for artifact in session.scalars(
                    select(Artifact)
                    .join(AIMission, Artifact.mission_id == AIMission.id)
                    .where(AIMission.workspace_id == workspace_id, Artifact.status == "APPROVED")
                    .order_by(Artifact.updated_at.desc())
                    .limit(12)
                ).all()
            ]
            project_row = session.get(SolutionProject, mission.get("solution_project_id")) if mission.get("solution_project_id") else None
            project = None if project_row is None else {
                "id": project_row.id, "title": project_row.title, "industry": project_row.industry,
                "status": project_row.status, "review_status": project_row.review_status, "objective": project_row.objective,
            }
            participants = []
            for row in session.scalars(select(MissionParticipant).where(MissionParticipant.mission_id == mission_id, MissionParticipant.workspace_id == workspace_id).order_by(MissionParticipant.created_at)).all():
                member = session.get(User, row.user_id)
                role = session.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == workspace_id, WorkspaceUserRole.user_id == row.user_id))
                participants.append({"display_name": member.display_name if member else "Workspace member", "role": role.role if role else "VIEWER", "responsibility": row.responsibility})
            review_comments = [
                {"author": (session.get(User, row.user_id).display_name if session.get(User, row.user_id) else "Workspace member"), "summary": row.comment[:240], "status": row.status}
                for row in session.scalars(select(MissionReviewComment).where(MissionReviewComment.mission_id == mission_id, MissionReviewComment.workspace_id == workspace_id).order_by(MissionReviewComment.created_at.desc()).limit(3)).all()
            ]
            computer_memory = [
                {"memory_type": row.memory_type, "summary": str(row.content)[:240], "strategy_hint": row.strategy_hint, "confidence": row.confidence, "validation_count": row.validation_count}
                for row in session.scalars(
                    select(ComputerProjectMemory)
                    .where(ComputerProjectMemory.workspace_id == workspace_id)
                    .order_by(ComputerProjectMemory.created_at.desc())
                    .limit(8)
                ).all()
            ]
        finally:
            session.close()
        evidence_refs = mission.get("evidence_refs") if isinstance(mission.get("evidence_refs"), list) else []
        memory_selection = self._retrieval.retrieve(
            mission,
            self._memories.list(workspace_id, user_id=user_id),
            approved_artifacts,
            project,
        )
        self._memories.mark_used(memory_selection["selected_ids"], workspace_id)
        return {
            "identity": {"user_id": user_id, "role": getattr(actor, "role", "SYSTEM"), "source": "SESSION" if actor else "MISSION_OWNER_OR_SYSTEM"},
            "workspace": {"id": workspace_id, "name": workspace_name, "member_count": member_count, "is_demo": workspace_name == "ResearchOS Demo Workspace"},
            "project": memory_selection["project_context"] or {"id": mission.get("solution_project_id"), "status": "not_linked"},
            "mission": {"id": mission_id, "goal": str(mission.get("goal") or mission.get("title") or ""), "status": mission.get("status"), "evidence_count": len(evidence_refs)},
            "knowledge": {"traceable_evidence_refs": evidence_refs[:20], "approved_assets": approved_assets, "approved_decisions": approved_decisions},
            "artifacts": memory_selection["artifact_summaries"],
            "collaboration": {"participants": participants, "recent_review_comments": review_comments, "member_count": member_count},
            "computer_memory": computer_memory,
            "memory": memory_selection,
            "boundary": "Context contains only authorized workspace metadata, approved knowledge summaries and traceable Evidence references. Prompts, CoT, credentials and source-document bodies are excluded.",
        }

    @staticmethod
    def presentation(context: Mapping[str, object]) -> dict[str, object]:
        workspace = context.get("workspace") if isinstance(context.get("workspace"), Mapping) else {}
        mission = context.get("mission") if isinstance(context.get("mission"), Mapping) else {}
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), Mapping) else {}
        memory = context.get("memory") if isinstance(context.get("memory"), Mapping) else {}
        selected = memory.get("selected") if isinstance(memory.get("selected"), list) else []
        artifacts = context.get("artifacts") if isinstance(context.get("artifacts"), list) else []
        collaboration = context.get("collaboration") if isinstance(context.get("collaboration"), Mapping) else {}
        computer_memory = context.get("computer_memory") if isinstance(context.get("computer_memory"), list) else []
        return {"workspace": workspace, "mission": mission, "knowledge": {"traceable_evidence_count": len(knowledge.get("traceable_evidence_refs", [])), "approved_assets": knowledge.get("approved_assets", 0), "approved_decisions": knowledge.get("approved_decisions", 0)}, "memory": {"selected_count": len(selected), "selection_summary": memory.get("selection_summary")}, "artifacts": {"selected_count": len(artifacts)}, "collaboration": {"participant_count": len(collaboration.get("participants", [])), "review_comment_count": len(collaboration.get("recent_review_comments", []))}, "computer_memory": {"available_count": len(computer_memory)}, "boundary": context.get("boundary")}
