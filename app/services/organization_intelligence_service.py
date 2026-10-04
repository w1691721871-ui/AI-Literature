"""Read-only, Workspace-scoped organizational learning projections."""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import func, select

from app.models.ai_mission import AIMission
from app.models.approval import ApprovalRequest
from app.models.artifact import Artifact
from app.models.enterprise_memory import KnowledgeAsset
from app.models.workspace_memory import WorkspaceMemory
from app.services.database import SessionLocal, initialize_database


class OrganizationIntelligenceService:
    """Summarize persisted organizational assets without inferring outcomes."""

    def __init__(self, sessions=SessionLocal, *, initialize: bool = True):
        if initialize:
            initialize_database()
        self._sessions = sessions

    def overview(self, workspace_id: str) -> dict[str, object]:
        """Return counts and plain-language value only for one Workspace."""
        session = self._sessions()
        try:
            missions = list(session.scalars(select(AIMission).where(AIMission.workspace_id == workspace_id)).all())
            mission_ids = [item.id for item in missions]
            artifact_count = int(session.scalar(select(func.count(Artifact.id)).where(
                Artifact.mission_id.in_(mission_ids)
            )) or 0) if mission_ids else 0
            review_count = int(session.scalar(select(func.count(ApprovalRequest.id)).where(
                ApprovalRequest.workspace_id == workspace_id
            )) or 0)
            approved_evidence = int(session.scalar(select(func.count(func.distinct(ApprovalRequest.source_id))).where(
                ApprovalRequest.workspace_id == workspace_id,
                ApprovalRequest.request_type == "EVIDENCE_VERIFY",
                ApprovalRequest.status == "APPROVED",
            )) or 0)
            memory_count = int(session.scalar(select(func.count(WorkspaceMemory.id)).where(
                WorkspaceMemory.workspace_id == workspace_id,
                WorkspaceMemory.status == "ACTIVE",
            )) or 0)
            reusable_knowledge = int(session.scalar(select(func.count(KnowledgeAsset.id)).where(
                KnowledgeAsset.workspace_id == workspace_id,
                KnowledgeAsset.status == "VERIFIED",
            )) or 0)
            metrics = {
                "missions": len(missions),
                "completed_missions": sum(item.status == "COMPLETED" for item in missions),
                "evidence": len(self._unique_evidence(missions)),
                "approved_evidence": approved_evidence,
                "artifacts": artifact_count,
                "reviews": review_count,
                "research_memory": memory_count,
            }
            data_state = "READY" if any(metrics.values()) else "NO_DATA"
            return {
                "workspace_id": workspace_id,
                "data_state": data_state,
                "metrics": metrics,
                "knowledge_assets": {
                    "research_progress": self._item(metrics["completed_missions"], "completed Mission", "No completed research work yet."),
                    "evidence_growth": self._item(metrics["evidence"], "traceable Evidence reference", "No traceable Evidence has been recorded yet."),
                    "delivery_history": self._item(metrics["artifacts"], "reviewable Artifact", "No delivery Artifact has been created yet."),
                    "reusable_knowledge": self._item(reusable_knowledge + metrics["research_memory"], "reusable knowledge record", "No active Research Memory or verified knowledge asset exists yet."),
                },
                "long_term_value": self._value_summary(metrics, reusable_knowledge),
                "boundary": (
                    "Organizational learning is calculated only from persisted records in the current Workspace. "
                    "Candidate sources, prompts, internal reasoning, credentials, and other Workspaces are excluded."
                ),
            }
        finally:
            session.close()

    @staticmethod
    def _item(value: int, singular: str, empty: str) -> dict[str, object]:
        return {
            "count": value,
            "label": singular if value == 1 else f"{singular}s",
            "summary": empty if value == 0 else f"{value} persisted {singular}{'' if value == 1 else 's'} in this Workspace.",
        }

    @classmethod
    def _unique_evidence(cls, missions: Iterable[AIMission]) -> set[str]:
        keys: set[str] = set()
        for mission in missions:
            try:
                refs = json.loads(mission.evidence_refs_json or "[]")
            except json.JSONDecodeError:
                refs = []
            if not isinstance(refs, list):
                continue
            for reference in refs:
                if isinstance(reference, dict):
                    key = json.dumps(reference, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                elif isinstance(reference, str) and reference.strip():
                    key = reference.strip()
                else:
                    continue
                keys.add(key)
        return keys

    @staticmethod
    def _value_summary(metrics: dict[str, int], reusable_knowledge: int) -> dict[str, str]:
        if not any(metrics.values()) and reusable_knowledge == 0:
            return {
                "title": "No organizational learning data yet",
                "summary": "Complete a reviewable Mission to begin building traceable Evidence, delivery, and Workspace Memory.",
            }
        return {
            "title": "AI Employee Memory & Organizational Learning",
            "summary": (
                f"This Workspace has completed {metrics['completed_missions']} Mission(s), recorded "
                f"{metrics['evidence']} traceable Evidence reference(s), and created {metrics['artifacts']} reviewable Artifact(s). "
                f"{metrics['research_memory'] + reusable_knowledge} reusable knowledge record(s) remain available within this Workspace."
            ),
        }
