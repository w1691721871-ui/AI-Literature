"""Product-level coordination of existing AI Worker Skills."""

from __future__ import annotations

from collections.abc import Mapping


class AITeamOrchestrator:
    """Selects a finite Skill sequence; it is not another autonomous Agent."""

    def plan(self, registry, mission: Mapping[str, object], context: Mapping[str, object]) -> list[tuple[str, object]]:
        workspace = context.get("workspace") if isinstance(context.get("workspace"), Mapping) else {}
        if not workspace.get("id") or workspace.get("id") != mission.get("workspace_id"):
            raise PermissionError("AI Team plan requires the Mission Workspace context.")
        return registry.plan(mission)

    def presentation(self, registry, mission: Mapping[str, object], context: Mapping[str, object]) -> list[dict[str, object]]:
        return [
            {
                "skill_id": skill_id,
                "name": adapter.name,
                "description": adapter.description,
                "required_permission": adapter.required_permission(),
                "capability": adapter.capability_metadata() if hasattr(adapter, "capability_metadata") else None,
                "status": "READY",
            }
            for skill_id, adapter in self.plan(registry, mission, context)
        ]
