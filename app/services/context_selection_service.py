"""Selects the smallest authorized context slice needed for one Mission."""

from __future__ import annotations

import re
from collections.abc import Mapping


class ContextSelectionService:
    """Ranks safe, pre-authorized summaries; it never retrieves global memory."""

    MAX_MEMORIES = 6
    MAX_EVIDENCE_REFS = 12

    def select(
        self,
        mission: Mapping[str, object],
        memories: list[Mapping[str, object]],
        artifacts: list[Mapping[str, object]] | None = None,
    ) -> dict[str, object]:
        goal = str(mission.get("goal") or mission.get("title") or "")
        goal_terms = self._terms(goal)
        ranked = []
        for memory in memories:
            score, reason = self._score(memory, goal_terms, str(mission.get("id") or ""))
            if score <= 0:
                continue
            ranked.append((score, memory, reason))
        ranked.sort(key=lambda item: (-item[0], str(item[1].get("updated_at") or "")), reverse=False)
        selected = [
            {
                "id": row.get("id"), "memory_type": row.get("memory_type"),
                "title": row.get("title"), "summary": row.get("summary"),
                "importance_score": row.get("importance_score", 50),
                "lifecycle_state": row.get("lifecycle_state", "CREATED"),
                "selection_reason": reason,
            }
            for _, row, reason in ranked[: self.MAX_MEMORIES]
        ]
        refs = mission.get("evidence_refs") if isinstance(mission.get("evidence_refs"), list) else []
        ranked_artifacts = []
        for artifact in artifacts or []:
            score, reason = self._score_artifact(artifact, goal_terms)
            if score > 0:
                ranked_artifacts.append((score, artifact, reason))
        ranked_artifacts.sort(key=lambda item: (-item[0], str(item[1].get("updated_at") or "")), reverse=False)
        return {
            "selected": selected,
            "selected_ids": [str(item["id"]) for item in selected if item.get("id")],
            "evidence_refs": refs[: self.MAX_EVIDENCE_REFS],
            "artifact_summaries": [
                {
                    "id": artifact.get("id"), "title": artifact.get("title"),
                    "artifact_type": artifact.get("artifact_type"), "status": artifact.get("status"),
                    "summary": artifact.get("summary"), "evidence_count": artifact.get("evidence_count", 0),
                    "selection_reason": reason,
                }
                for _, artifact, reason in ranked_artifacts[:3]
            ],
            "project_included": bool(mission.get("solution_project_id")),
            "selection_summary": "Context includes only relevant, authorized Workspace summaries and traceable Evidence references.",
        }

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {term for term in re.findall(r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", value.lower()) if term}

    def _score(self, memory: Mapping[str, object], goal_terms: set[str], mission_id: str) -> tuple[int, str]:
        memory_type = str(memory.get("memory_type") or "")
        lifecycle = str(memory.get("lifecycle_state") or "CREATED")
        if lifecycle == "ARCHIVED":
            return 0, "Archived memory is excluded."
        score = int(memory.get("importance_score") or 50)
        if memory_type == "MISSION" and str(memory.get("mission_id") or "") == mission_id:
            score += 50; reason = "This is the current Mission history."
        elif memory_type == "KNOWLEDGE":
            score += 25; reason = "This is approved Workspace knowledge."
        elif memory_type == "WORKSPACE":
            score += 15; reason = "This captures persistent Workspace context."
        else:
            score += 10; reason = "This is the current user's confirmed working preference."
        text_terms = self._terms(f"{memory.get('title') or ''} {memory.get('summary') or ''}")
        overlap = len(goal_terms & text_terms)
        if overlap:
            score += min(overlap * 12, 36)
            reason = "Its summary is relevant to the current Mission goal."
        if lifecycle == "VERIFIED":
            score += 15
        return score, reason

    def _score_artifact(self, artifact: Mapping[str, object], goal_terms: set[str]) -> tuple[int, str]:
        if str(artifact.get("status") or "").upper() != "APPROVED":
            return 0, "Unapproved artifacts are excluded."
        score = 45 + min(int(artifact.get("evidence_count") or 0) * 3, 25)
        text_terms = self._terms(f"{artifact.get('title') or ''} {artifact.get('summary') or ''}")
        overlap = len(goal_terms & text_terms)
        if overlap:
            return score + min(overlap * 12, 36), "Its approved delivery summary is relevant to the current Mission goal."
        return score, "This is an approved, evidence-linked Workspace delivery."
