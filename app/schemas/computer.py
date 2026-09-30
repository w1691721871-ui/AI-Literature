"""Contracts for the explicit Computer Agent approval boundary."""

from pydantic import BaseModel, Field


class ComputerTaskCreate(BaseModel):
    user_goal: str = Field(min_length=1, max_length=2_000)
    workspace_id: str | None = Field(default=None, max_length=36)
    external_urls: list[str] = Field(default_factory=list, max_length=5)


class ComputerActionReview(BaseModel):
    reviewer_note: str = Field(default="", max_length=1_000)
