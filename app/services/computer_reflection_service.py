"""Safe post-task reflection for the controlled Computer Skill."""

from __future__ import annotations

from collections.abc import Mapping


class ComputerReflectionService:
    """Creates concise, auditable learnings; it never stores raw task inputs."""

    def reflect(self, mission: Mapping[str, object], intelligence: Mapping[str, object]) -> dict[str, str]:
        execution = intelligence.get("workspace_state") if isinstance(intelligence.get("workspace_state"), Mapping) else {}
        strategy = intelligence.get("strategy") if isinstance(intelligence.get("strategy"), Mapping) else {}
        decision = intelligence.get("decision") if isinstance(intelligence.get("decision"), Mapping) else {}
        quality = intelligence.get("quality") if isinstance(intelligence.get("quality"), Mapping) else {}
        result = "Completed a controlled Computer task." if execution.get("completed_task") else "No completed Computer task is available for a success learning."
        issue = "Verification or approval requires human follow-up." if execution.get("failed_task") or execution.get("requires_user_action") else "No unresolved Computer issue is recorded."
        return {
            "task_goal": str(mission.get("goal") or mission.get("title") or "")[:240],
            "strategy": str(strategy.get("label") or "Safe controlled route"),
            "result": result,
            "issue": issue,
            "resolution": str(decision.get("reason") or "Continue only through the existing controlled workflow."),
            "future_advice": self._advice(strategy, quality),
            "memory_type": "FAILURE_LEARNING" if execution.get("failed_task") else "TASK_EXPERIENCE",
        }

    @staticmethod
    def _advice(strategy: Mapping[str, object], quality: Mapping[str, object]) -> str:
        if quality.get("status") == "NEEDS_REVIEW":
            return "Resolve the existing review before choosing a different route."
        if strategy.get("id") == "PUBLIC_DISCOVERY":
            return "Validate public candidates through the Evidence workflow before reusing them."
        if strategy.get("id") == "AUTHORIZED_MATERIAL":
            return "Reuse only material explicitly attached to the next Mission."
        return "Keep the next task bounded and confirm any modifying action with a human reviewer."

    def remember(self, workspace_id: str, reflection: Mapping[str, object], memory_service) -> dict[str, object] | None:
        """Persist one safe, compact learning through the existing Memory service."""
        if not workspace_id or not reflection.get("task_goal"):
            return None
        content = " | ".join([
            "Computer task experience",
            f"Strategy: {str(reflection.get('strategy') or '')[:180]}",
            f"Outcome: {str(reflection.get('result') or '')[:180]}",
            f"Future: {str(reflection.get('future_advice') or '')[:180]}",
        ])
        return memory_service.remember(workspace_id, str(reflection.get("memory_type") or "TASK_EXPERIENCE"), content)
