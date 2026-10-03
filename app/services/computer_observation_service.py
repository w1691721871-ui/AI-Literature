"""Read-only, explicitly non-vision observations for the Computer Skill."""

from __future__ import annotations

from app.services.computer_environment_service import ComputerEnvironmentScanner


class ComputerObservationService:
    def __init__(self, scanner: ComputerEnvironmentScanner | None = None) -> None:
        self.scanner = scanner or ComputerEnvironmentScanner()

    def observe_environment(self, context: dict[str, object] | None = None) -> dict[str, object]:
        """Return metadata observations without claiming live visual perception.

        The product currently has no connected browser or screenshot input.
        ``vision_mode=demo_only`` is therefore explicit in every result.
        """
        context = context or {}
        supplied_profile = context.get("workspace_profile")
        if isinstance(supplied_profile, dict):
            profile = supplied_profile
        else:
            profile = self.scanner.scan()
        workspace = profile.get("workspace", {})
        project = profile.get("project", profile)
        technologies = project.get("technology", []) if isinstance(project, dict) else []
        return {
            "status": "OBSERVED",
            "vision_mode": "demo_only",
            "page_state": "workspace_metadata_available",
            "visible_elements": [
                {"name": "Workspace metadata", "kind": "metadata", "available": True},
                {"name": "Controlled approval gate", "kind": "safety_control", "available": True},
            ],
            "available_actions": ["NAVIGATE", "CLICK", "WAIT", "VERIFY"],
            "risk_level": "LOW",
            "verification_points": ["approval status", "Diff hash", "fixed verification allow-list"],
            "environment": {
                "workspace": workspace.get("root", "research_workspace"),
                "files": workspace.get("file_count", 0),
                "documents": workspace.get("document_count", 0),
                "project_type": technologies,
                "project_name": project.get("project_name", ""),
                "status": "ready_for_controlled_action",
            },
            "profile": profile,
            "boundary": "仅完成只读环境观察；没有真实视觉输入，未读取敏感文件正文、未修改环境。",
        }

    def observe(self) -> dict[str, object]:
        """Backward-compatible alias for older Computer Operator callers."""
        return self.observe_environment()

    @staticmethod
    def compare_environment(before_state: dict[str, object], after_state: dict[str, object]) -> dict[str, object]:
        """Compare public-safe state summaries, never screenshots or raw page content."""
        keys = ("page_state", "risk_level", "verification_target", "current_state")
        before = {key: str(before_state.get(key) or "") for key in keys}
        after = {key: str(after_state.get(key) or "") for key in keys}
        after_page = after["page_state"] or after["current_state"]
        if str(after_state.get("unexpected_change") or "").lower() == "true" or after_page.lower() in {"error", "blocked", "unexpected"}:
            return {"status": "UNEXPECTED_CHANGE", "summary": "检测到需人工确认的环境变化。"}
        if before == after or not any(after.values()):
            return {"status": "NO_CHANGE", "summary": "前后环境状态未出现可验证变化。"}
        return {"status": "STATE_CHANGED", "summary": "已检测到可验证的环境状态变化。"}
