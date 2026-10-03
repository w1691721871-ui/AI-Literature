"""Deterministic action selection for the approval-bounded Computer Skill."""

from __future__ import annotations

from collections.abc import Mapping


class ComputerActionPlanner:
    """Plans only a small allow-list; it never performs the selected action."""

    ALLOWED_ACTIONS = {"CLICK", "INPUT", "UPLOAD", "NAVIGATE", "WAIT", "VERIFY"}
    _HIGH_RISK_TERMS = ("upload", "上传", "submit", "提交", "write", "写入", "modify", "修改", "update", "更新", "delete", "删除")
    _NAVIGATE_TERMS = ("browse", "browser", "navigate", "search", "打开", "浏览", "检索", "搜索")

    def plan_next_action(self, observation: Mapping[str, object], mission_goal: str, environment: Mapping[str, object] | None = None) -> dict[str, object]:
        goal = str(mission_goal or "").strip()
        lowered = goal.lower()
        if not goal:
            return self._plan("VERIFY", "controlled workspace", "A missing goal cannot authorize any computer action.", "LOW", False)
        if any(term in lowered for term in self._HIGH_RISK_TERMS):
            action = "UPLOAD" if any(term in lowered for term in ("upload", "上传")) else "INPUT"
            return self._plan(action, "approved controlled target", "The goal may change data or external state, so explicit approval is required.", "HIGH", True)
        if any(term in lowered for term in self._NAVIGATE_TERMS) and "NAVIGATE" in observation.get("available_actions", []):
            return self._plan("NAVIGATE", "authorized public workspace view", "The goal is limited to read-only navigation.", "LOW", False)
        if str(observation.get("page_state") or "") == "workspace_metadata_available":
            return self._plan("VERIFY", "controlled workspace state", "Verify the current state before proposing a modification.", "LOW", False)
        return self._plan("WAIT", "controlled workspace", "No safe action can be selected from the current observation.", "LOW", False)

    @staticmethod
    def _plan(action_type: str, target: str, reason_summary: str, risk_level: str, requires_approval: bool) -> dict[str, object]:
        checks = {
            "UPLOAD": ("FILE_AVAILABLE", "CHECK_FILE_LIST", "REQUEST_REVIEW"),
            "INPUT": ("TARGET_UPDATED", "CHECK_TARGET_STATE", "REQUEST_REVIEW"),
            "NAVIGATE": ("PAGE_STATE_CHANGED", "COMPARE_ENVIRONMENT", "WAIT"),
            "VERIFY": ("VERIFIED_STATE", "FIXED_VERIFICATION", "REQUEST_REVIEW"),
            "WAIT": ("ENVIRONMENT_STABLE", "COMPARE_ENVIRONMENT", "REQUEST_REVIEW"),
        }
        expected_change, verification_method, fallback_action = checks[action_type]
        return {"action_name": action_type.title(), "action_type": action_type, "purpose": reason_summary, "target": target, "reason_summary": reason_summary, "input": "Authorized Mission context", "risk_level": risk_level,
                "requires_approval": requires_approval, "expected_change": expected_change,
                "verification_method": verification_method, "fallback_action": fallback_action}
