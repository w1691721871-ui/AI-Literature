"""Public, user-readable contract for one AI Worker mission.

This schema is intentionally a compatibility envelope.  It describes the
existing Mission services without persisting prompts, model traces, or hidden
reasoning.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WorkerSkill(BaseModel):
    """A product capability backed by one or more legacy services."""

    id: str
    name: str
    description: str
    evidence_required: bool = False
    approval_required: bool = False


class MissionContract(BaseModel):
    """Stable boundary shared by the AI Worker user experience."""

    objective: str = Field(min_length=1, max_length=8_000)
    context: dict[str, object] = Field(default_factory=dict)
    available_skills: list[WorkerSkill] = Field(default_factory=list)
    evidence_requirement: str
    approval_requirement: str
    outputs: list[str] = Field(default_factory=list)
    status: str
    stop_reason: str | None = None
