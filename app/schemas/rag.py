"""API schemas for the independent multi-paper RAG question flow."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResearchQuestionRequest(BaseModel):
    question: str
    paper_ids: list[str] = Field(default_factory=list)


class RagSource(BaseModel):
    paper_id: str
    paper_title: str
    section: str
    content: str
    score: float


class ResearchQuestionResponse(BaseModel):
    answer: str
    sources: list[RagSource]
    confidence: str
    source_quality: dict[str, object] = Field(default_factory=dict)
    agent_plan: dict[str, str] = Field(default_factory=dict)
    agent_trace: dict[str, object] = Field(default_factory=dict)
    retrieval_evaluation: dict[str, object] = Field(default_factory=dict)


class ResearchReportRequest(BaseModel):
    report_type: str
    paper_ids: list[str] = Field(default_factory=list)


class ResearchReportResponse(BaseModel):
    report_type: str
    report: dict[str, object]
    sources: list[RagSource]
    confidence: str
    source_quality: dict[str, object] = Field(default_factory=dict)
    agent_trace: dict[str, object] = Field(default_factory=dict)
    retrieval_evaluation: dict[str, object] = Field(default_factory=dict)


class RagQueryHistoryItem(BaseModel):
    id: str
    question: str
    answer: str
    task_type: str
    created_at: datetime


class RagQueryHistoryDetail(RagQueryHistoryItem):
    sources: list[RagSource]
    paper_ids: list[str]
