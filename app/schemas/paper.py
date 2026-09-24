"""Public API schemas that intentionally never expose full paper text."""

from datetime import datetime

from pydantic import BaseModel


class PaperListItem(BaseModel):
    """Small paper record used in the research library list."""

    paper_id: str
    title: str
    filename: str
    upload_time: datetime
    analysis_status: str
    quality_status: str
    chunk_count: int
    updated_at: datetime
    text_length: int


class PaperDetail(PaperListItem):
    """Paper metadata for a detail page, excluding text_content by design."""

    file_path: str


class LibraryPaperAnalysisRequest(BaseModel):
    """Task input for analyzing a paper already stored in the research library."""

    task: str
    scenario: str = "paper"
    role: str = "researcher"
