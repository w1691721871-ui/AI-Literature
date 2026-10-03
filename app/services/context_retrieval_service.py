"""Retrieves the smallest relevant, authorized context slice for an AI Worker Mission."""

from __future__ import annotations

from collections.abc import Mapping

from app.services.context_selection_service import ContextSelectionService


class ContextRetrievalService:
    """An explainable adapter over context ranking; never a global-memory search."""

    def __init__(self, selector: ContextSelectionService | None = None):
        self._selector = selector or ContextSelectionService()

    def retrieve(
        self,
        mission: Mapping[str, object],
        memories: list[Mapping[str, object]],
        artifacts: list[Mapping[str, object]],
        project: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        selection = self._selector.select(mission, memories, artifacts)
        selected = selection.get("selected") if isinstance(selection.get("selected"), list) else []
        artifact_summaries = selection.get("artifact_summaries") if isinstance(selection.get("artifact_summaries"), list) else []
        project_context = self._project_context(mission, project)
        return {
            **selection,
            "project_context": project_context,
            "explainability": {
                "candidate_counts": {
                    "authorized_memory": len(memories),
                    "approved_artifacts": len(artifacts),
                    "traceable_evidence": len(selection.get("evidence_refs") or []),
                    "linked_project": 1 if project_context else 0,
                },
                "selected_context": [
                    {"kind": "Research Memory", "title": item.get("title"), "reason": item.get("selection_reason"), "score": item.get("context_score")}
                    for item in selected
                ] + [
                    {"kind": "Approved Delivery", "title": item.get("title"), "reason": item.get("selection_reason"), "score": item.get("context_score")}
                    for item in artifact_summaries
                ],
                "ranking_criteria": ["Mission relevance", "Verified or approved trust", "Recency", "Task value"],
                "boundary": "Only current-Workspace records authorized for this Mission are considered. Prompts, reasoning, credentials and raw source bodies are excluded.",
            },
        }

    @staticmethod
    def _project_context(mission: Mapping[str, object], project: Mapping[str, object] | None) -> dict[str, object] | None:
        if not mission.get("solution_project_id") or not isinstance(project, Mapping):
            return None
        return {
            "id": project.get("id"), "title": project.get("title"), "industry": project.get("industry"),
            "status": project.get("status"), "review_status": project.get("review_status"),
            "objective": project.get("objective"),
        }
