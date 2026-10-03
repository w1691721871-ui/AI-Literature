"""Evidence- and review-bounded Mission completion quality summaries."""

from __future__ import annotations

from collections.abc import Mapping


class MissionQualityService:
    def evaluate_completion(self, mission: Mapping[str, object], state: Mapping[str, object]) -> dict[str, object]:
        evidence = mission.get("evidence_refs")
        evidence_count = len(evidence) if isinstance(evidence, list) else 0
        pending = state.get("pending_tasks")
        pending_count = len(pending) if isinstance(pending, list) else 0
        blocked = str(state.get("blocked_reason") or "")
        status = str(mission.get("status") or "").upper()
        if blocked or evidence_count == 0:
            return {"quality": "NEEDS_EVIDENCE", "confidence": "Evidence is insufficient for a grounded completion claim.", "next_action": "REPLAN_OR_REVIEW"}
        if status in {"WAITING_REVIEW", "APPROVED"}:
            return {"quality": "REVIEW_REQUIRED", "confidence": "Traceable Evidence is available, but human review remains required.", "next_action": "REQUEST_REVIEW"}
        if status == "COMPLETED" and pending_count == 0:
            return {"quality": "READY_FOR_DELIVERY", "confidence": "Completed tasks and reviewable Evidence are recorded.", "next_action": "COMPLETE"}
        return {"quality": "IN_PROGRESS", "confidence": "Mission work is still bounded by its remaining tasks.", "next_action": "CONTINUE"}
