"""Finite, non-destructive recovery choices for controlled Computer Skill work."""

from __future__ import annotations

from collections.abc import Mapping


class ComputerRecoveryService:
    MAX_RECOVERY_ATTEMPTS = 2

    def recover_failed_action(
        self,
        feedback: Mapping[str, object],
        action: Mapping[str, object],
        recovery_count: int,
    ) -> dict[str, object]:
        status = str(feedback.get("status") or "FAILED")
        if recovery_count >= self.MAX_RECOVERY_ATTEMPTS:
            return self._result("REQUEST_REVIEW", recovery_count, "已达到最多两次恢复限制，需要人工决定下一步。")
        if status == "NEEDS_REVIEW":
            return self._result("REQUEST_REVIEW", recovery_count, "未预期环境变化不能自动恢复。")
        if status == "RETRY":
            return self._result("RETRY", recovery_count + 1, "未检测到状态变化，可在受控边界内重试一次。")
        fallback = str(action.get("fallback_action") or "").upper()
        if fallback in {"WAIT", "VERIFY", "NAVIGATE"}:
            return self._result("ALTERNATIVE_ACTION", recovery_count + 1, f"建议改用受控 {fallback} 验证路径。", fallback)
        return self._result("STOP", recovery_count, "没有安全的自动恢复路径，任务保持待人工修订。")

    @staticmethod
    def _result(action: str, count: int, summary: str, fallback: str = "") -> dict[str, object]:
        return {"action": action, "recovery_count": count, "summary": summary, "fallback_action": fallback}
