"""Public contracts for the AI Mission Center."""

from pydantic import BaseModel, Field


class AIMissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    mission_type: str = Field(default="RESEARCH", min_length=1, max_length=80)
    goal: str = Field(default="", max_length=8_000)


class AIMissionReview(BaseModel):
    status: str = Field(pattern="^(APPROVED|REJECTED|NEEDS_REVISION)$")
    review_comment: str = Field(default="", max_length=2_000)


class AIMissionRevision(BaseModel):
    change_summary: str = Field(min_length=1, max_length=2_000)
