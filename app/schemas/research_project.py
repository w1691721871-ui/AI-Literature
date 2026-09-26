"""Pydantic contracts for the ResearchOS project lifecycle."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResearchProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    enterprise_requirement: str = ""
    research_goal: str = ""
    technology_route: str = ""
    paper_plan: str = ""
    patent_plan: str = ""
    outcome_management: str = ""
    status: str = "planning"


class EnterpriseMatchRequest(BaseModel):
    enterprise_requirement: str = Field(min_length=1, max_length=2_000)
    paper_ids: list[str] = Field(default_factory=list)


class ResearchProjectResponse(ResearchProjectInput):
    id: str
    created_at: datetime
    updated_at: datetime
