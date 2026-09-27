"""Public contracts for the bounded autonomous Research Brain."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AutonomousResearchRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2_000)
    paper_ids: list[str] = Field(default_factory=list)
    generate_docx: bool = False


class AutonomousResearchRunResponse(BaseModel):
    id: str
    goal: str
    status: Literal["pending", "running", "completed", "needs_evidence", "failed"]
    task_plan: dict[str, object]
    execution_timeline: list[dict[str, object]]
    tool_results: dict[str, object]
    environment_profile: dict[str, object]
    memory_snapshot: dict[str, object]
    reflection: dict[str, object]
    final_output: dict[str, object]
    current_step: str
    current_tool: str
    completed_tasks: list[str]
    next_plan: list[dict[str, object]]
    failure_reason: str
    created_at: datetime
    updated_at: datetime
