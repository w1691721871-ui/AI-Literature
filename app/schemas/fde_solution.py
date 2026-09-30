"""Request contracts for the FDE Solution Delivery Studio."""

from typing import Literal

from pydantic import BaseModel, Field


class SolutionProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    customer_need: str = Field(min_length=1, max_length=8_000)
    industry: str = Field(default="Research", min_length=1, max_length=120)
    objective: str = Field(default="", max_length=2_000)


class SolutionReviewRequest(BaseModel):
    status: Literal["PENDING", "APPROVED", "REJECTED", "NEEDS_REVISION"]
    reviewer_note: str = Field(default="", max_length=2_000)


class FDEProjectCreate(BaseModel):
    """Compatibility request for the explicit /api/fde product surface."""

    name: str = Field(min_length=1, max_length=240)
    customer_need: str = Field(min_length=1, max_length=8_000)
    industry: str = Field(default="Research", min_length=1, max_length=120)
    objective: str = Field(default="", max_length=2_000)
