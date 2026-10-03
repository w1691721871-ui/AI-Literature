"""Product-level coordination of existing AI Worker Skills."""

from __future__ import annotations

from collections.abc import Mapping


class AITeamOrchestrator:
    """Selects a finite Skill sequence; it is not another autonomous Agent."""

    def plan(self, registry, mission: Mapping[str, object], context: Mapping[str, object], *, understanding: Mapping[str, object] | None = None) -> list[tuple[str, object]]:
        workspace = context.get("workspace") if isinstance(context.get("workspace"), Mapping) else {}
        if not workspace.get("id") or workspace.get("id") != mission.get("workspace_id"):
            raise PermissionError("AI Team plan requires the Mission Workspace context.")
        allowed = registry.plan(mission)
        requested = understanding.get("required_capabilities", []) if isinstance(understanding, Mapping) else []
        requested_ids = [str(item) for item in requested if str(item)]
        # Existing adapters remain the authority. Goal understanding can only
        # order runnable Skills; it cannot manufacture a tool or bypass a gate.
        priority = {skill_id: index for index, skill_id in enumerate(requested_ids)}
        return sorted(allowed, key=lambda item: (priority.get(item[0], len(priority)), item[0] == "review"))

    def presentation(self, registry, mission: Mapping[str, object], context: Mapping[str, object], *, understanding: Mapping[str, object] | None = None) -> list[dict[str, object]]:
        return [
            {
                "skill_id": skill_id,
                "name": adapter.name,
                "description": adapter.description,
                "required_permission": adapter.required_permission(),
                "capability": adapter.capability_metadata() if hasattr(adapter, "capability_metadata") else None,
                "plan_reason": self._reason(skill_id, understanding),
                "status": "READY",
            }
            for skill_id, adapter in self.plan(registry, mission, context, understanding=understanding)
        ]

    @staticmethod
    def _reason(skill_id: str, understanding: Mapping[str, object] | None) -> str:
        requested = understanding.get("required_capabilities", []) if isinstance(understanding, Mapping) else []
        if skill_id in requested:
            return "Selected because this Mission goal requires this approved capability."
        if skill_id == "review":
            return "Included to preserve the required human decision boundary."
        return "Included because the current Mission state has an existing runnable Skill."
