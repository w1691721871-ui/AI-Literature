"""Response schemas for research workspace overview and report history."""

from datetime import datetime

from pydantic import BaseModel


class ResearchOverview(BaseModel):
    paper_count: int
    parsed_count: int
    analysis_count: int
    last_analysis_time: datetime | None


class ResearchReportListItem(BaseModel):
    id: str
    paper_id: str
    paper_title: str
    task: str
    scenario: str
    role: str
    source_type: str
    created_at: datetime


class ResearchReportDetail(ResearchReportListItem):
    """A report wrapper; analysis_result remains the unchanged Agent response."""

    analysis_result: dict[str, object]
