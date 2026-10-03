"""Builds the only context projection injected into the AI Worker Runtime."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select

from app.models.enterprise_memory import DecisionRecord, KnowledgeAsset
from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.services.database import SessionLocal, initialize_database
from app.services.workspace_memory_service import WorkspaceMemoryService


class WorkspaceContextService:
    """Joins identity, workspace, mission, knowledge and memory without raw content."""

    def __init__(self, sessions=SessionLocal, *, initialize=True, memories=None):
        if initialize:
            initialize_database()
        self._sessions = sessions
        self._memories = memories or WorkspaceMemoryService(sessions, initialize=False)

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
        finally:
            session.close()
        evidence_refs = mission.get("evidence_refs") if isinstance(mission.get("evidence_refs"), list) else []
        return {
            "identity": {"user_id": user_id, "role": getattr(actor, "role", "SYSTEM"), "source": "SESSION" if actor else "MISSION_OWNER_OR_SYSTEM"},
            "workspace": {"id": workspace_id, "name": workspace_name, "member_count": member_count, "is_demo": workspace_name == "ResearchOS Demo Workspace"},
            "project": {"id": mission.get("solution_project_id"), "status": "linked" if mission.get("solution_project_id") else "not_linked"},
            "mission": {"id": mission_id, "goal": str(mission.get("goal") or mission.get("title") or ""), "status": mission.get("status"), "evidence_count": len(evidence_refs)},
            "knowledge": {"traceable_evidence_refs": evidence_refs[:20], "approved_assets": approved_assets, "approved_decisions": approved_decisions},
            "memory": self._memories.context_slice(workspace_id, user_id=user_id, mission_id=mission_id),
            "boundary": "Context contains only authorized workspace metadata, approved knowledge summaries and traceable Evidence references. Prompts, CoT, credentials and source-document bodies are excluded.",
        }

    @staticmethod
    def presentation(context: Mapping[str, object]) -> dict[str, object]:
        workspace = context.get("workspace") if isinstance(context.get("workspace"), Mapping) else {}
        mission = context.get("mission") if isinstance(context.get("mission"), Mapping) else {}
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), Mapping) else {}
        memory = context.get("memory") if isinstance(context.get("memory"), Mapping) else {}
        return {"workspace": workspace, "mission": mission, "knowledge": {"traceable_evidence_count": len(knowledge.get("traceable_evidence_refs", [])), "approved_assets": knowledge.get("approved_assets", 0), "approved_decisions": knowledge.get("approved_decisions", 0)}, "memory_counts": {name: len(items) for name, items in memory.items() if isinstance(items, list)}, "boundary": context.get("boundary")}
