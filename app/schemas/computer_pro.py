"""Request contracts for the P14 Computer Operator Pro API."""

from typing import Literal

from pydantic import BaseModel, Field


class ComputerProTaskCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=2_000)
    execution_mode: Literal["assist", "supervised", "research"] = "assist"
    workspace_id: str | None = Field(default=None, max_length=36)
    external_urls: list[str] = Field(default_factory=list, max_length=5)


class ComputerProActionReview(BaseModel):
    reviewer_note: str = Field(default="", max_length=1_000)


class ComputerRuntimeTaskCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=2_000)
    execution_mode: Literal["assist", "supervised", "research"] = "supervised"
    workspace_id: str | None = Field(default=None, max_length=36)


class ComputerRuntimeApproval(BaseModel):
    reviewer_note: str = Field(default="", max_length=1_000)


class AutonomousComputerTaskCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=2_000)
    execution_mode: Literal["assist", "supervised", "research"] = "supervised"
    workspace_id: str | None = Field(default=None, max_length=36)


class ComputerUseTaskCreate(AutonomousComputerTaskCreate):
    pass


class ComputerProjectMemoryCreate(BaseModel):
    """A small, non-sensitive project preference or runtime convention."""

    memory_type: Literal["PROJECT_STYLE", "TECH_STACK", "TEST_COMMAND", "USER_PREFERENCE"]
    content: str = Field(min_length=1, max_length=1_000)
