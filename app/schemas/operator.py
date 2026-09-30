"""Public request contracts for the Research Operator execution layer."""

from pydantic import BaseModel, Field


class OperatorTaskCreate(BaseModel):
    user_goal: str = Field(min_length=1, max_length=2_000)
    workspace_id: str | None = Field(default=None, max_length=36)


class OperatorApprovalRequest(BaseModel):
    reviewer_note: str = Field(default="", max_length=1_000)
