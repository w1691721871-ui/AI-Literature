"""Public contracts for the advisory-only Research Copilot layer."""

from pydantic import BaseModel, Field


class CopilotActionCreate(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=300)
    rationale: str = Field(min_length=1, max_length=2_000)
    evidence_refs: list[dict[str, object]] = Field(default_factory=list)


class CopilotActionReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected|later)$")


class DocumentCommentCreate(BaseModel):
    reviewer_comment: str = Field(min_length=1, max_length=2_000)
