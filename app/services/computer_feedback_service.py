"""Deterministic feedback for approval-bounded Computer Skill actions."""

from __future__ import annotations

from collections.abc import Mapping

from app.services.computer_observation_service import ComputerObservationService


class ComputerFeedbackService:
    """Evaluates observable state changes only; it never assumes an action succeeded."""

    def __init__(self, observations: ComputerObservationService | None = None) -> None:
        self.observations = observations or ComputerObservationService()

    def evaluate_action_result(
        self,
        action: Mapping[str, object],
        before_state: Mapping[str, object],
        after_state: Mapping[str, object],
    ) -> dict[str, object]:
        comparison = self.observations.compare_environment(before_state, after_state)
        verification = str(after_state.get("verification_status") or after_state.get("status") or "").upper()
        if comparison["status"] == "UNEXPECTED_CHANGE":
            return self._result("NEEDS_REVIEW", comparison, "环境出现未预期变化，已停止后续自动动作并请求人工审核。")
        if verification in {"FAIL", "FAILED"}:
            return self._result("FAILED", comparison, "固定验证未通过，不能将本次受控动作标记为成功。")
        if comparison["status"] == "NO_CHANGE":
            return self._result("RETRY", comparison, "动作后未观察到目标状态变化；仅可进行有限恢复。")
        return self._result("SUCCESS", comparison, "已观察到符合预期的环境状态变化。")

    @staticmethod
    def _result(status: str, comparison: Mapping[str, object], summary: str) -> dict[str, object]:
        return {"status": status, "summary": summary, "comparison": dict(comparison)}
