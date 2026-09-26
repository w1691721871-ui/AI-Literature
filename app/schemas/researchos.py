"""Request schemas for the ResearchOS multi-Agent task center."""

from pydantic import BaseModel, Field


class ResearchOSTaskRequest(BaseModel):
    """One user-created research organization task."""

    user_goal: str = Field(min_length=1, max_length=2_000)
    selected_agents: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)


class ResearchValueRequest(BaseModel):
    """Request an evidence-grounded Value Agent assessment."""

    research_goal: str = Field(min_length=1, max_length=2_000)
    paper_ids: list[str] = Field(default_factory=list)
