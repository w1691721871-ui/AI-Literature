"""The capability catalog used by Mission Intelligence, not a second Agent registry."""

from __future__ import annotations


class SkillCapabilityRegistry:
    _CAPABILITIES = {
        "research": ("retrieve_evidence", "analyze_gap", "generate_insight"),
        "computer": ("navigate", "interact", "verify"),
        "delivery": ("generate_artifact", "release"),
        "review": ("request_approval", "record_review"),
    }

    def capabilities_for(self, skill: str) -> list[str]:
        return list(self._CAPABILITIES.get(skill, ()))

    def supports(self, skill: str, capability: str) -> bool:
        return capability in self._CAPABILITIES.get(skill, ())

    def skill_for(self, capability: str) -> str | None:
        return next((skill for skill, capabilities in self._CAPABILITIES.items() if capability in capabilities), None)
