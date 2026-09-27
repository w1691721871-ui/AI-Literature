"""Public contracts for the separate, bounded Research Worker execution layer."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResearchWorkerRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2_000)


class ResearchWorkerRunResponse(BaseModel):
    run_id: str
    user_goal: str
    status: Literal["pending", "planning", "running", "completed", "failed", "need_confirmation"]
    current_step: str
    current_phase: Literal["planning", "executing", "observing", "evaluating", "replanning", "completed", "failed"]
    plan: list[dict[str, object]]
    tools: list[dict[str, object]]
    result: dict[str, object]
    reflection: dict[str, object]
    execution_history: list[dict[str, object]]
    context: dict[str, object]
    output_file: str
    created_time: datetime
    updated_time: datetime
