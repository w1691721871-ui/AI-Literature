"""Public, approval-first contracts for P24 Computer Missions."""

from typing import Literal

from pydantic import BaseModel, Field


class ComputerMissionCreate(BaseModel):
    mission_id: str | None = Field(default=None, max_length=36)
    task: str = Field(min_length=1, max_length=2_000)
    reason: str = Field(default="", max_length=2_000)


class ComputerMissionApproval(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "NEEDS_REVISION"]
    note: str = Field(default="", max_length=2_000)
