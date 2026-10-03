"""Mission-bound planning for existing controlled Computer Skills."""

from __future__ import annotations

from collections.abc import Mapping

from app.services.computer_skill_registry import ComputerSkillRegistry


class ComputerTaskPlanner:
    """Builds a finite, explainable plan and never executes it."""

    MAX_STEPS = 4

    def __init__(self, registry: ComputerSkillRegistry | None = None):
        self._registry = registry or ComputerSkillRegistry()

    def plan(self, mission: Mapping[str, object], context: Mapping[str, object]) -> dict[str, object]:
        workspace = context.get("workspace") if isinstance(context.get("workspace"), Mapping) else {}
        if workspace.get("id") != mission.get("workspace_id"):
            raise PermissionError("Computer planning requires the current Mission Workspace context.")
        goal = str(mission.get("goal") or mission.get("title") or "")
        matched_skills = self._registry.match(goal)
        # Browser research is never allowed to bypass the existing Evidence
        # boundary. Reserve space for its validation step before truncating a
        # multi-skill plan, rather than appending it and accidentally dropping
        # it at the final finite-plan limit.
        requires_evidence_validation = any(skill["id"] == "browser_research" for skill in matched_skills)
        skill_limit = self.MAX_STEPS - (1 if requires_evidence_validation else 0)
        skills = matched_skills[:skill_limit]
        evidence_count = len((context.get("knowledge") or {}).get("traceable_evidence_refs") or []) if isinstance(context.get("knowledge"), Mapping) else 0
        steps = [
            {"order": index, "skill": skill["name"], "skill_id": skill["id"], "purpose": self._purpose(skill["id"]),
             "inputs": skill["inputs"], "outputs": skill["outputs"], "permission": skill["permission"],
             "risk_level": skill["risk_level"], "approval_required": skill["approval_required"], "status": "PLANNED"}
            for index, skill in enumerate(skills, start=1)
        ]
        if requires_evidence_validation:
            steps.append({"order": len(steps) + 1, "skill": "Evidence Validation", "skill_id": "evidence_validation", "purpose": "Validate externally discovered candidates before any knowledge reuse.", "inputs": ["Candidate source references"], "outputs": ["Traceable Evidence or an evidence gap"], "permission": "KNOWLEDGE_ACCESS", "risk_level": "LOW", "approval_required": False, "status": "PLANNED"})
        return {"mission_id": mission.get("id"), "steps": steps[: self.MAX_STEPS], "context_basis": {"traceable_evidence": evidence_count}, "boundary": "Computer observations and external candidates never enter Research Memory without the existing Evidence validation and human review boundaries."}

    @staticmethod
    def _purpose(skill_id: str) -> str:
        return {
            "browser_research": "Find authorized external research candidates without claiming they are Evidence.",
            "document_preparation": "Prepare an approval-gated document draft from authorized material.",
            "data_operation": "Prepare a reviewable result from an approved read-only source.",
            "report_preparation": "Prepare an Evidence-linked delivery draft for human review.",
        }[skill_id]
