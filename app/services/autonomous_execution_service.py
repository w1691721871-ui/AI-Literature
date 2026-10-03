"""Finite, deterministic decisions for the unified AI Worker runtime.

This service never invokes a model or tool.  It turns user-readable runtime
observations into a bounded next action that the existing Skill adapters may
perform.  It deliberately does not replace approval, RBAC, or evidence gates.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class AutonomousExecutionService:
    """Select the next existing Skill action while enforcing finite stops."""

    MAX_STEPS = 5

    _ACTION_SKILLS = {
        "RETRIEVE_EVIDENCE": "research",
        "ANALYZE_GAP": "research",
        "GENERATE_INSIGHT": "research",
        "CREATE_ARTIFACT": "delivery",
        "REQUEST_APPROVAL": "review",
        "FINISH": "review",
    }

    def decide_next_step(
        self,
        mission_contract: Mapping[str, Any] | object,
        mission_state: Mapping[str, Any] | object,
        observation: Mapping[str, Any] | object,
        *,
        workspace_id: str | None = None,
    ) -> dict[str, object]:
        """Apply finite replan policy without executing or approving work."""
        contract = self._as_mapping(mission_contract)
        state = self._as_mapping(mission_state)
        observed = self._as_mapping(observation)
        if workspace_id and str(contract.get("workspace_id") or "") not in {"", workspace_id}:
            return self._result("STOP", "FINISH", "WORKSPACE_SCOPE_DENIED", "The requested workspace does not own this Mission Contract.")
        status = str(observed.get("status") or "").upper()
        if status in {"FAILED", "ERROR"}:
            return self._result("STOP", "FINISH", "EXECUTION_EXCEPTION", "A controlled Skill failed; automatic recovery is not permitted.")
        if str(contract.get("execution_state") or "").upper() == "COMPLETED":
            return self._result("COMPLETE", "FINISH", "TASK_COMPLETED", "The Mission Contract has completed its bounded workflow.")
        evidence_count = self._evidence_count(contract)
        replan_count = int(state.get("replan_count") or 0)
        max_replans = min(int(state.get("max_replan_count") or 2), 2)
        if status in {"NEEDS_EVIDENCE", "INSUFFICIENT_EVIDENCE"} or evidence_count == 0:
            if replan_count < max_replans:
                return self._result("REPLAN", "RETRIEVE_EVIDENCE", "INSUFFICIENT_EVIDENCE", "Traceable Evidence is insufficient; one bounded retrieval replan is available.")
            return self._result("REQUEST_REVIEW", "REQUEST_APPROVAL", "REPLAN_LIMIT_REACHED", "Evidence remains insufficient after the permitted replans.")
        if status in {"WAITING_REVIEW", "WAITING_APPROVAL"}:
            return self._result("REQUEST_REVIEW", "REQUEST_APPROVAL", "HUMAN_REVIEW_REQUIRED", "The existing workflow requires an explicit human decision.")
        return self._result("CONTINUE", "ANALYZE_GAP", "", "Traceable Evidence is available for the next bounded evaluation step.")

    def evaluate_current_state(
        self,
        mission_contract: Mapping[str, Any] | object,
        runtime_state: Mapping[str, Any] | object,
        observation: Mapping[str, Any] | object,
        *,
        workspace_id: str | None = None,
    ) -> dict[str, object]:
        """Return a safe next decision without retaining internal reasoning."""
        contract = self._as_mapping(mission_contract)
        state = self._as_mapping(runtime_state)
        observed = self._as_mapping(observation)
        contract_workspace = str(contract.get("workspace_id") or "")
        if workspace_id and contract_workspace and workspace_id != contract_workspace:
            return self._result("STOP", "FINISH", "WORKSPACE_SCOPE_DENIED", "The requested workspace does not own this Mission Contract.")

        completed_steps = int(state.get("completed_steps") or state.get("step_count") or 0)
        max_steps = int(state.get("max_steps") or self.MAX_STEPS)
        if completed_steps >= max_steps:
            return self._result("STOP", "FINISH", "MAX_STEPS_REACHED", "The controlled execution limit was reached before another action could begin.")

        observation_status = str(observed.get("status") or "").upper()
        action_type = str(observed.get("action_type") or "").upper()
        if observation_status in {"FAILED", "ERROR"}:
            return self._result("REQUEST_REVIEW", "REQUEST_APPROVAL", "EXECUTION_EXCEPTION", "A controlled Skill action did not complete and requires human review.")
        if observation_status in {"NEEDS_EVIDENCE", "INSUFFICIENT_EVIDENCE"}:
            return self._result("REQUEST_REVIEW", "REQUEST_APPROVAL", "INSUFFICIENT_EVIDENCE", "No traceable Evidence is available for a grounded research conclusion.")
        if observation_status in {"WAITING_REVIEW", "WAITING_APPROVAL"}:
            return self._result("REQUEST_REVIEW", "REQUEST_APPROVAL", "HUMAN_REVIEW_REQUIRED", "The existing workflow requires an explicit human decision.")

        evidence_count = self._evidence_count(contract)
        if evidence_count == 0 and action_type in {"", "COLLECT_EVIDENCE", "RETRIEVE_EVIDENCE"}:
            return self._result("CONTINUE", "RETRIEVE_EVIDENCE", "", "Evidence collection is the next bounded action.")
        if evidence_count > 0 and action_type in {"COLLECT_EVIDENCE", "RETRIEVE_EVIDENCE"}:
            return self._result("CONTINUE", "ANALYZE_GAP", "", "Traceable Evidence is available for an evidence-bounded gap assessment.")
        if evidence_count > 0 and action_type == "ANALYZE_GAP":
            return self._result("CONTINUE", "GENERATE_INSIGHT", "", "The evidence assessment can now prepare a reviewable research insight.")
        if str(contract.get("approval_state") or "").upper() in {"APPROVED", "APPROVE"} and evidence_count > 0:
            return self._result("CONTINUE", "CREATE_ARTIFACT", "", "Approved, traceable Evidence may be passed to the existing Delivery Skill.")
        if str(contract.get("execution_state") or "").upper() == "COMPLETED":
            return self._result("STOP", "FINISH", "TASK_COMPLETED", "The Mission Contract is already complete.")
        return self._result("CONTINUE", "FINISH", "", "The current bounded Skill plan may continue to its existing review boundary.")

    def select_next_action(self, decision: Mapping[str, object]) -> dict[str, object]:
        """Map a decision only to a registered, existing Skill category."""
        action = str(decision.get("action") or "FINISH")
        return {"action": action, "skill": self._ACTION_SKILLS[action], "reason": str(decision.get("reason") or "")}

    @classmethod
    def progress(cls, mission: Mapping[str, Any], records: list[Mapping[str, Any]]) -> list[dict[str, str]]:
        """Return a product-safe progress view; no prompts or model internals."""
        mission_status = str(mission.get("status") or "").upper()
        record_statuses = {str(record.get("status") or "").upper() for record in records}
        has_research = any(str(record.get("skill") or "") == "Research Skill" for record in records)
        validating = any(str(record.get("action_type") or "").upper() in {"COLLECT_EVIDENCE", "CHECK_EVIDENCE"} for record in records)
        review = "ACTIVE" if "WAITING_REVIEW" in record_statuses else "PENDING"
        completed = "COMPLETE" if mission_status == "COMPLETED" else "PENDING"
        return [
            {"label": "Planning", "status": "COMPLETE" if records else "ACTIVE"},
            {"label": "Researching", "status": "COMPLETE" if has_research and "WAITING_REVIEW" in record_statuses else "ACTIVE" if has_research else "PENDING"},
            {"label": "Validating", "status": "COMPLETE" if validating else "PENDING"},
            {"label": "Review Required", "status": review},
            {"label": "Completed", "status": completed},
        ]

    def _result(self, decision: str, action: str, stop_reason: str, reason: str) -> dict[str, object]:
        result = {"decision": decision, "action": action, "reason": reason, "stop_reason": stop_reason}
        result.update(self.select_next_action(result))
        return result

    @staticmethod
    def _as_mapping(value: Mapping[str, Any] | object) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        return {key: getattr(value, key) for key in dir(value) if not key.startswith("_") and not callable(getattr(value, key, None))}

    @staticmethod
    def _evidence_count(contract: Mapping[str, Any]) -> int:
        refs = contract.get("evidence_refs")
        if isinstance(refs, list):
            return len(refs)
        context = contract.get("context") or contract.get("input_context") or {}
        if isinstance(context, Mapping):
            return int(context.get("evidence_count") or 0)
        return 0
