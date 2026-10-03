"""User-readable lifecycle projection for existing controlled Computer Missions.

This module is an adapter, not a second executor.  All writes, approval,
verification and rollback remain owned by ``ControlledComputerMissionService``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class ComputerMissionRuntime:
    """Translate persisted controlled-Mission state into a finite Worker view."""

    _STAGES = (
        ("UNDERSTAND", "Understand", "AI has received the workspace-bound task."),
        ("PLAN", "Plan", "A controlled action is prepared from authorized context."),
        ("APPROVAL", "Approval", "Human confirmation is required before any modifying action."),
        ("EXECUTION", "Execution", "Only an approved action may run in the controlled workspace."),
        ("VERIFICATION", "Verification", "The result is checked through the existing allow-listed verification."),
    )

    def summarize(self, computer_missions: Sequence[Mapping[str, object]] | object) -> dict[str, object] | None:
        if not isinstance(computer_missions, Sequence) or isinstance(computer_missions, (str, bytes)) or not computer_missions:
            return None
        current = computer_missions[-1]
        if not isinstance(current, Mapping):
            return None
        action_plan = current.get("action_plan") if isinstance(current.get("action_plan"), Mapping) else {}
        observation = action_plan.get("normalized_observation") if isinstance(action_plan.get("normalized_observation"), Mapping) else {}
        controlled_action = action_plan.get("controlled_action") if isinstance(action_plan.get("controlled_action"), Mapping) else {}
        verification = current.get("verification") if isinstance(current.get("verification"), Mapping) else {}
        recovery = verification.get("recovery") if isinstance(verification.get("recovery"), Mapping) else {}
        status = str(current.get("status") or "CREATED").upper()
        approval = str(current.get("approval_status") or "PENDING").upper()
        verify = verification.get("controlled_verification") if isinstance(verification.get("controlled_verification"), Mapping) else {}
        verification_status = str(verify.get("status") or verification.get("status") or "PENDING").upper()
        return {
            "mission_id": current.get("id"),
            "task": str(current.get("task") or ""),
            "status": self._product_status(status, approval, verification_status),
            "next_action": self._next_action(status, approval, verification_status),
            "current_action": str(controlled_action.get("action_type") or "Observe"),
            "observation": {
                "state": str(observation.get("page_state") or "not observed"),
                "vision_mode": str(observation.get("vision_mode") or "demo_only"),
                "available_actions": list(observation.get("available_actions") or []),
            },
            "verification": {
                "status": self._verification_status(verification_status),
                "summary": str(verify.get("summary") or "Verification has not completed."),
            },
            "recovery": self._recovery(recovery),
            "stages": self._stages(status, approval, verification_status),
            "asset_status": "No delivery asset was created by this Computer Mission." if not current.get("artifact_id") else "A linked delivery asset is available.",
            "boundary": "This is a controlled Computer Skill: modifying actions require approval; verification and existing rollback safeguards remain mandatory.",
        }

    def _stages(self, status: str, approval: str, verification: str) -> list[dict[str, str]]:
        progress = {
            "CREATED": 0, "ANALYZING": 1, "PLAN_READY": 2, "WAITING_APPROVAL": 2,
            "APPROVED": 3, "EXECUTING": 3, "VERIFYING": 4, "COMPLETED": 5,
            "NEEDS_REVISION": 2, "FAILED": 2,
        }.get(status, 0)
        stages = []
        for index, (identifier, title, description) in enumerate(self._STAGES, start=1):
            state = "COMPLETED" if index < progress else "ACTIVE" if index == progress else "PENDING"
            if identifier == "APPROVAL" and status == "WAITING_APPROVAL":
                state = "REQUIRED"
            if identifier == "VERIFICATION" and verification in {"FAILED", "NEEDS_REVIEW"}:
                state = "NEEDS_REVIEW"
            stages.append({"id": identifier, "title": title, "description": description, "status": state})
        return stages

    @staticmethod
    def _product_status(status: str, approval: str, verification: str) -> str:
        if status in {"FAILED", "NEEDS_REVISION"} or verification in {"FAILED", "NEEDS_REVIEW"}:
            return "NEEDS_REVIEW"
        if status == "COMPLETED":
            return "COMPLETED"
        if status == "WAITING_APPROVAL" or approval == "PENDING":
            return "WAITING_APPROVAL"
        if status in {"EXECUTING", "VERIFYING", "ANALYZING"}:
            return "RUNNING"
        return "READY"

    @staticmethod
    def _next_action(status: str, approval: str, verification: str) -> str:
        if status in {"FAILED", "NEEDS_REVISION"} or verification in {"FAILED", "NEEDS_REVIEW"}:
            return "Review the controlled change and choose the next safe action."
        if status == "WAITING_APPROVAL" or approval == "PENDING":
            return "Human approval is required before execution."
        if status == "COMPLETED":
            return "Review the verified result before any formal delivery."
        return "Continue within the existing controlled Computer workflow."

    @staticmethod
    def _verification_status(status: str) -> str:
        return {"SUCCESS": "VERIFIED", "PASS": "VERIFIED", "FAILED": "NEEDS_REVIEW", "NEEDS_REVIEW": "NEEDS_REVIEW"}.get(status, "PENDING")

    @staticmethod
    def _recovery(recovery: Mapping[str, object]) -> dict[str, str] | None:
        if not recovery:
            return None
        return {"status": str(recovery.get("action") or "REQUEST_REVIEW"), "summary": str(recovery.get("summary") or "A controlled recovery decision requires review.")}
