"""Adapters that expose existing ResearchOS services as AI Worker skills.

The adapters deliberately keep execution in the mature services.  They only
translate inputs and safe, user-readable outcomes for the unified runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkillResult:
    status: str
    observation_summary: str
    result_summary: str
    action_type: str = "EXECUTE"


class SkillAdapter:
    name = ""
    description = ""

    def validate(self, mission: Mapping[str, Any]) -> None:
        if not str(mission.get("id") or ""):
            raise ValueError("Mission 标识缺失。")

    def required_permission(self) -> str | None:
        return None

    def execute(self, mission: Mapping[str, Any]) -> SkillResult:
        raise NotImplementedError

    def observe(self, result: SkillResult) -> str:
        """Return only a user-readable observation, never raw tool/model output."""
        return result.observation_summary

    def evaluate(self, result: SkillResult) -> str:
        return result.status

    def rollback(self, mission: Mapping[str, Any]) -> SkillResult:
        return SkillResult("WAITING_REVIEW", "Rollback requires the existing controlled service.", "AI Worker will not automatically revert a Skill action.", "REQUEST_REVIEW")


class ResearchSkillAdapter(SkillAdapter):
    name = "Research Skill"
    description = "Uses the existing evidence-bounded Mission and RAG workflow."

    def __init__(self, mission_service):
        self._missions = mission_service

    def required_permission(self) -> str | None:
        return "KNOWLEDGE_ACCESS"

    def validate(self, mission: Mapping[str, Any]) -> None:
        super().validate(mission)
        if not str(mission.get("goal") or mission.get("title") or "").strip():
            raise ValueError("Research Skill 需要明确研究目标。")

    def execute(self, mission: Mapping[str, Any]) -> SkillResult:
        state = str(mission.get("status") or "CREATED")
        if state not in {"CREATED", "PLANNING", "NEEDS_REVISION"}:
            return SkillResult("SUCCESS", "Existing research state observed.", "Research Skill has no runnable evidence step in the current mission state.")
        detail = self._missions.run(str(mission["id"]))
        refs = detail.get("evidence_refs", []) if isinstance(detail, Mapping) else []
        evidence_count = len(refs) if isinstance(refs, list) else 0
        if evidence_count == 0:
            return SkillResult("NEEDS_EVIDENCE", "Evidence retrieval completed without traceable references.", "No traceable Evidence is available; the AI Worker cannot form a research conclusion.", "COLLECT_EVIDENCE")
        return SkillResult("WAITING_REVIEW", f"Collected {evidence_count} traceable Evidence reference(s).", "Evidence-backed research is ready for human review.", "COLLECT_EVIDENCE")


class ComputerSkillAdapter(SkillAdapter):
    name = "Computer Skill"
    description = "Observes controlled computer work and preserves Diff approval gates."

    def required_permission(self) -> str | None:
        return "COMPUTER_USE"

    def __init__(self, observation_service=None, action_planner=None):
        from app.services.computer_action_planner import ComputerActionPlanner
        from app.services.computer_observation_service import ComputerObservationService

        self._observation = observation_service or ComputerObservationService()
        self._planner = action_planner or ComputerActionPlanner()

    def capability_metadata(self) -> dict[str, object]:
        return {"mode": "controlled", "requires_approval": True, "supports_rollback": True, "vision": "demo_only"}

    def execute(self, mission: Mapping[str, Any]) -> SkillResult:
        tasks = mission.get("computer_missions", [])
        tasks = tasks if isinstance(tasks, list) else []
        if not tasks:
            return SkillResult("SUCCESS", "No controlled computer action is attached.", "Computer Skill was not required for this mission.")
        current = tasks[-1] if isinstance(tasks[-1], Mapping) else {}
        observation = self._observation.observe_environment({
            "mission_id": current.get("id"), "goal": current.get("task") or mission.get("goal") or mission.get("title"),
        })
        plan = self._planner.plan_next_action(observation, str(current.get("task") or mission.get("goal") or ""))
        waiting = next((item for item in tasks if str(item.get("approval_status", "")).upper() != "APPROVED"), None)
        if waiting or bool(plan["requires_approval"]):
            return SkillResult("WAITING_REVIEW", "Environment observed and a controlled action is awaiting human approval.", "Computer Skill stopped before modification; Diff approval and verification remain required.", "REQUEST_APPROVAL")
        return SkillResult("WAITING_REVIEW", "A low-risk controlled action was observed; verification remains required.", "Computer Skill will not bypass existing verification or rollback safeguards.", "VERIFY")


class DeliverySkillAdapter(SkillAdapter):
    name = "Delivery Skill"
    description = "Uses the existing Artifact service to create a reviewable delivery draft."

    def __init__(self, artifact_service):
        self._artifacts = artifact_service

    def required_permission(self) -> str | None:
        return "ARTIFACT_REVIEW"

    def execute(self, mission: Mapping[str, Any]) -> SkillResult:
        if str(mission.get("status") or "") != "APPROVED":
            return SkillResult("WAITING_REVIEW", "Delivery requires an approved Mission.", "No Artifact was generated before human approval.", "REQUEST_APPROVAL")
        refs = mission.get("evidence_refs", [])
        if not isinstance(refs, list) or not refs:
            return SkillResult("WAITING_REVIEW", "No traceable Evidence is attached.", "Delivery remains blocked because a research conclusion cannot be generated without Evidence.", "CHECK_EVIDENCE")
        artifact = self._artifacts.generate(str(mission["id"]), "DELIVERY_PACKAGE")
        return SkillResult("WAITING_REVIEW", "Created a versioned delivery draft.", f"Delivery Artifact {artifact.get('id', '')} requires human review before formal release.", "GENERATE_ARTIFACT")


class ReviewSkillAdapter(SkillAdapter):
    name = "Review Skill"
    description = "Presents evidence, changes, and deliveries for explicit human decisions."

    def required_permission(self) -> str | None:
        return "MISSION_APPROVE"

    def execute(self, mission: Mapping[str, Any]) -> SkillResult:
        state = str(mission.get("status") or "")
        if state in {"COMPLETED", "REJECTED", "FAILED"}:
            return SkillResult("SUCCESS", "Mission lifecycle is closed.", "Review status is already recorded.")
        return SkillResult("WAITING_REVIEW", "Human decision is required for the current mission state.", "AI Worker will not approve Evidence, changes, or delivery on behalf of a reviewer.", "REQUEST_REVIEW")


class SkillRegistry:
    """Single capability registry; adapters preserve legacy service ownership."""

    def __init__(self, *, mission_service=None, artifact_service=None, adapters: Mapping[str, SkillAdapter] | None = None):
        if adapters is not None:
            self._adapters = dict(adapters)
            return
        from app.services.ai_mission_service import AIMissionService
        from app.services.artifact_service import ArtifactService

        mission_service = mission_service or AIMissionService()
        artifact_service = artifact_service or ArtifactService()
        self._adapters = {
            "research": ResearchSkillAdapter(mission_service),
            "computer": ComputerSkillAdapter(),
            "delivery": DeliverySkillAdapter(artifact_service),
            "review": ReviewSkillAdapter(),
        }

    def adapter(self, skill_id: str) -> SkillAdapter:
        try:
            return self._adapters[skill_id]
        except KeyError as error:
            raise ValueError(f"Unsupported AI Worker skill: {skill_id}") from error

    def plan(self, mission: Mapping[str, Any]) -> list[tuple[str, SkillAdapter]]:
        """Choose a bounded sequence without inventing or auto-approving work."""
        state = str(mission.get("status") or "CREATED")
        steps: list[str] = []
        if state in {"CREATED", "PLANNING", "NEEDS_REVISION"}:
            steps.append("research")
        if mission.get("computer_missions"):
            steps.append("computer")
        if state == "APPROVED":
            steps.append("delivery")
        if not steps or state not in {"COMPLETED", "REJECTED", "FAILED"}:
            steps.append("review")
        return [(skill_id, self.adapter(skill_id)) for skill_id in steps]
