"""Request schemas for the ResearchOS multi-Agent task center."""

from typing import Literal

from pydantic import BaseModel, Field


class ResearchOSTaskRequest(BaseModel):
    """One user-created research organization task."""

    user_goal: str = Field(min_length=1, max_length=2_000)
    selected_agents: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    # Optional, backwards-compatible binding for continuing a saved workspace.
    workspace_id: str | None = Field(default=None, max_length=36)


class ResearchValueRequest(BaseModel):
    """Request an evidence-grounded Value Agent assessment."""

    research_goal: str = Field(min_length=1, max_length=2_000)
    paper_ids: list[str] = Field(default_factory=list)


class WorkspaceReviewRequest(BaseModel):
    """A display-role human review; no login system is implied."""

    reviewer_role: Literal["researcher", "reviewer", "leader"]
    status: Literal["approved", "rejected"]
    reviewer_note: str = Field(default="", max_length=2_000)


class WorkspaceCompleteRequest(BaseModel):
    role: Literal["leader"]


class WorkflowCreateRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2_000)
    workspace_id: str | None = Field(default=None, max_length=36)
    workflow_type: Literal["literature_review", "research_gap", "experiment_design", "proposal_generation", "project_delivery"] | None = None
    paper_ids: list[str] = Field(default_factory=list)
